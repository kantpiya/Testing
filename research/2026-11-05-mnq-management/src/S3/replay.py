"""S3 replay helpers: Stage A paired replay of PX (reversal) trades on MNQ 1-min bars.

Everything here operates on the SYNTHETIC development set only.

Conventions (stated in the report):
  * Entry fixed at the journal's entry_ts / entry_px / initial_contracts (Stage A).
  * Bracket is live from the entry bar onward (no entry bar touched stop or target, so
    'entry bar inclusive' vs 'next bar' are indistinguishable on this data).
  * Stop fill  = stop price - 1 tick adverse, or the bar open if the bar opened through it.
  * Limit fill = limit price (0 slippage), or the bar open if it opened through it (better).
  * Market exit decided at the close of bar m fills at the open of bar m+1, minus 1 tick adverse.
  * 15:55 bar: whatever is open is exited at that bar's open minus 1 tick (market).
  * Same bar touches stop and target: ordering parameter ('stop_first' default = conservative,
    'target_first' reported as sensitivity).
  * Commission $0.74 per contract per side on every fill (entry + each exit fill).
  * Integer contracts: a partial exit takes floor(q/2) contracts; q == 1 cannot scale out and
    is held unchanged (reported separately).
Minute k = k minutes after the entry bar's open. A decision 'at minute k' may use bars whose
open time < entry_ts + k min (close time <= entry_ts + k min) and fills at the open of the bar
whose open time == entry_ts + k min.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TICK = 0.25
PT_VALUE = 2.0
COMM = 0.74
EOD_HM = "15:55"
ET = "America/New_York"


def load(data_dir: str):
    bars = pd.read_csv(f"{data_dir}/bars_MNQ_1min.csv")
    bars["ts"] = pd.to_datetime(bars["ts"], utc=True).dt.tz_convert(ET)
    bars["date"] = bars["ts"].dt.strftime("%Y-%m-%d")
    bars["hm"] = bars["ts"].dt.strftime("%H:%M")
    trades = pd.read_csv(f"{data_dir}/trades.csv")
    signals = pd.read_csv(f"{data_dir}/signals.csv")
    for c in ("entry_ts", "exit_ts"):
        trades[c] = pd.to_datetime(trades[c], utc=True).dt.tz_convert(ET)
    px = trades[trades["family"] == "PX"].merge(
        signals[["signal_id", "ref_level", "ref_width"]], on="signal_id", how="left"
    )
    px = px.sort_values("entry_ts").reset_index(drop=True)
    px["sgn"] = np.where(px["direction"] == "LONG", 1, -1)
    px["stop_dist"] = (px["entry_px"] - px["initial_stop_px"]).abs()
    px["tgt_dist"] = (px["initial_target_px"] - px["entry_px"]).abs()
    px["tgt_R"] = px["tgt_dist"] / px["stop_dist"]
    # Structural levels known at entry, derived from journal fields (target = OR midpoint, ref_width = OR width)
    w = px["ref_width"]
    px["or_boundary_near"] = px["initial_target_px"] - px["sgn"] * w / 2  # boundary re-entered (behind entry)
    px["or_quarter"] = px["initial_target_px"] - px["sgn"] * w / 4  # between boundary and midpoint
    px["or_boundary_far"] = px["initial_target_px"] + px["sgn"] * w / 2  # opposite boundary
    px["or_three_quarter"] = px["initial_target_px"] + px["sgn"] * w / 4  # between midpoint and far boundary
    for c in ("or_boundary_near", "or_quarter", "or_boundary_far", "or_three_quarter"):
        px[c] = (px[c] / TICK).round() * TICK
    px["journal_net_R"] = px["net_pnl_usd"] / px["planned_risk_usd"]
    return bars, px, trades, signals


def trade_bars(bars: pd.DataFrame, tr) -> pd.DataFrame:
    """Bars from the entry bar through the 15:55 bar of the session (inclusive)."""
    d = bars[(bars["date"] == tr.session) & (bars["ts"] >= tr.entry_ts) & (bars["hm"] <= EOD_HM)]
    d = d.reset_index(drop=True)
    d["m"] = ((d["ts"] - tr.entry_ts).dt.total_seconds() / 60).astype(int)
    return d


@dataclass
class Policy:
    name: str
    time_exit_min: int | None = None  # market exit at the open of bar m == H
    stop_move_trigger: str | None = None  # 'quarter' | None : once price touches it, move stop ...
    stop_move_to: str | None = None  # 'boundary_near' | 'entry'
    target_level: str = "midpoint"  # 'midpoint' | 'quarter' | 'far'
    partial_at_quarter: bool = False  # floor(q/2) contracts out at the quarter line (q>=2 only)
    noprog_k: int | None = None  # no-progress check at minute k (close-based progress in R)
    noprog_theta: float | None = None
    noprog_mode: str = "R"  # 'R' = theta in R; 'tgtfrac' = theta as fraction of target distance
    ordering: str = "stop_first"  # same-bar stop & target ordering
    note: str = ""


@dataclass
class Result:
    trade_id: int
    fills: list = field(default_factory=list)  # (ts, px, qty, reason)
    gross: float = 0.0
    comm: float = 0.0
    net: float = 0.0
    net_R: float = 0.0
    exit_ts: pd.Timestamp | None = None
    exit_px: float | None = None
    exit_reason: str = ""
    hold_min: int = 0
    both_touched: bool = False  # a bar touched both stop and target at some point while open
    mfe_R: float = 0.0


def simulate(tr, bars_t: pd.DataFrame, pol: Policy) -> Result:
    sgn, q0 = int(tr.sgn), int(tr.initial_contracts)
    entry = float(tr.entry_px)
    stop = float(tr.initial_stop_px)
    sd = float(tr.stop_dist)
    tgt = {"midpoint": tr.initial_target_px, "quarter": tr.or_quarter, "far": tr.or_boundary_far,
           "threeq": tr.or_three_quarter, "none": sgn * math.inf}[pol.target_level]
    tgt = float(tgt)
    partial_level = float(tr.or_quarter)
    move_trigger = None if pol.stop_move_trigger is None else float(tr.or_quarter)
    move_to = None
    if pol.stop_move_to == "boundary_near":
        move_to = float(tr.or_boundary_near)
    elif pol.stop_move_to == "entry":
        move_to = entry
    res = Result(trade_id=int(tr.trade_id))
    q = q0
    partial_qty = q0 // 2 if (pol.partial_at_quarter and q0 >= 2) else 0
    partial_done = partial_qty == 0
    pending_mkt = None  # reason string for a market exit filling at the next bar open
    stop_moved = False
    o, h, l, c, hm, mm = (bars_t[k].values for k in ("open", "high", "low", "close", "hm", "m"))
    ts = list(bars_t["ts"])  # tz-aware Timestamps
    mfe = 0.0

    def book(i, px_fill, qty, reason):
        nonlocal q
        res.fills.append((ts[i], px_fill, qty, reason, int(mm[i])))
        res.gross += (px_fill - entry) * sgn * PT_VALUE * qty
        q -= qty

    for i in range(len(bars_t)):
        if q <= 0:
            break
        m = int(mm[i])
        # 1) pending market exit (decided at previous close) or time exit or EOD: fill at open - 1 tick
        reason = None
        if pending_mkt is not None:
            reason = pending_mkt
        elif pol.time_exit_min is not None and m >= pol.time_exit_min:
            reason = "TIME_H"
        elif hm[i] == EOD_HM:
            reason = "TIME_EOD"
        if reason is not None:
            book(i, o[i] - sgn * TICK, q, reason)
            break
        # 2) resting orders within the bar
        stop_hit = (l[i] <= stop) if sgn == 1 else (h[i] >= stop)
        tgt_hit = (h[i] >= tgt) if sgn == 1 else (l[i] <= tgt)
        part_hit = (not partial_done) and ((h[i] >= partial_level) if sgn == 1 else (l[i] <= partial_level))
        if stop_hit and (tgt_hit or part_hit):
            res.both_touched = True
        gapped_stop = (o[i] <= stop) if sgn == 1 else (o[i] >= stop)
        stop_px = o[i] if gapped_stop else stop - sgn * TICK
        # Journal convention (trade 95): a limit fills at the limit price even if the bar opened through it
        # (conservative: no better-than-limit fill credited).
        tgt_px = tgt
        order = ["stop", "tgt"] if pol.ordering == "stop_first" else ["tgt", "stop"]
        done = False
        for what in order:
            if what == "stop" and stop_hit:
                book(i, stop_px, q, "STOP" if not stop_moved else "STOP_MOVED")
                done = True
                break
            if what == "tgt":
                if part_hit and not partial_done:
                    book(i, partial_level, partial_qty, "PARTIAL")
                    partial_done = True
                if tgt_hit:
                    book(i, tgt_px, q, "TARGET")
                    done = True
                    break
        mfe = max(mfe, ((h[i] - entry) if sgn == 1 else (entry - l[i])) / sd)
        if done:
            break
        # 3) decisions at this bar's close (effective next bar)
        if move_trigger is not None and not stop_moved:
            touched = (h[i] >= move_trigger) if sgn == 1 else (l[i] <= move_trigger)
            if touched:
                stop = move_to
                stop_moved = True
        if pol.noprog_k is not None and m == pol.noprog_k - 1:
            prog = (c[i] - entry) * sgn / sd
            thr = pol.noprog_theta if pol.noprog_mode == "R" else pol.noprog_theta * (tgt_dist_R(tr))
            if prog < thr:
                pending_mkt = "NOPROG"
    res.mfe_R = mfe
    res.comm = COMM * (q0 + sum(f[2] for f in res.fills))
    res.net = res.gross - res.comm
    res.net_R = res.net / float(tr.planned_risk_usd)
    if res.fills:
        last = res.fills[-1]
        res.exit_ts, res.exit_px, res.exit_reason = last[0], last[1], last[3]
        res.hold_min = last[4]
    return res


def tgt_dist_R(tr) -> float:
    return float(tr.tgt_dist) / float(tr.stop_dist)


def path_metrics(tr, bars_t: pd.DataFrame, res_orig: Result, k_list=(5, 10, 15, 20), thr=0.3):
    """Observable-at-decision-time path features under the ORIGINAL policy."""
    sgn, entry, sd = int(tr.sgn), float(tr.entry_px), float(tr.stop_dist)
    hold = res_orig.hold_min
    h, l, c = bars_t["high"].values, bars_t["low"].values, bars_t["close"].values
    fav_hi = ((h - entry) if sgn == 1 else (entry - l)) / sd  # intrabar favourable excursion per bar
    close_R = (c - entry) * sgn / sd
    out = {"trade_id": int(tr.trade_id)}
    # time to reach +thr R intrabar (minute index of bar close = m+1), only while trade open
    t_reach = None
    for i in range(min(len(bars_t), hold + 1)):
        if fav_hi[i] >= thr:
            t_reach = int(bars_t["m"].iloc[i]) + 1
            break
    out["t_reach_03"] = t_reach
    # the exit bar itself may reach thr (e.g. target bar) - count it as reached only if it closes <= exit decision; keep simple
    for k in k_list:
        open_at_k = hold >= k  # exit bar open time >= entry + k
        out[f"open_k{k}"] = open_at_k
        if open_at_k:
            out[f"reached03_k{k}"] = bool(np.max(fav_hi[:k]) >= thr)
            out[f"close_k{k}"] = float(close_R[k - 1])
        else:
            out[f"reached03_k{k}"] = np.nan
            out[f"close_k{k}"] = np.nan
    return out


def max_drawdown(x: np.ndarray) -> float:
    cum = np.cumsum(x)
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    return float(np.min(cum - peak))


def session_bootstrap(values_by_session: np.ndarray, n_draws=2000, seed=11, stat=np.mean):
    """values_by_session: 1-D array with one value per session (PX has exactly one trade per session)."""
    rng = np.random.default_rng(seed)
    n = len(values_by_session)
    idx = rng.integers(0, n, size=(n_draws, n))
    draws = stat(values_by_session[idx], axis=1)
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))
