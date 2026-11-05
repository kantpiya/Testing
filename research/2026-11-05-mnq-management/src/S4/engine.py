"""S4 leg-aware replay engine for KX pyramided trades (SYNTHETIC data only).

Conventions (all stated in the report):
  * Entries and add fills are taken from the journal (identical across policies).
  * Stop fills: stop price - 1 tick adverse; if the bar OPEN already gapped through
    the stop, fill at the open - 1 tick adverse (1-tick slippage on all stop/market fills).
  * Target fills: exact limit price when the bar touches it (journal convention).
  * Market exits (15:55 flat, forced exits): bar open - 1 tick adverse.
  * Commission $0.74 per contract per side on every fill (entry, add, each leg's exit).
  * A decision made on bar i's close becomes effective on bar i+1 (no look-ahead).
  * Same-bar stop AND target touch: `ordering` = 'stop_first' (conservative, primary)
    or 'target_first' (optimistic). Both are reported for the tightened-stop policies.
  * Journal trigger convention (verified on trades.csv/fills.csv, see run.py section 0):
    the bracket is NOT live on the entry bar; a stop/limit level triggers when the bar
    extreme touches the tick-rounded level (penetration >= TRIGGER_TICKS = 0 ticks).
    The generator appears to test sub-tick (unrounded) levels, so ~9/234 journal exits
    differ by one bar; net P&L differs on 3 trades (reconciled in run.py section 0).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

TICK = 0.25
PT_VALUE = 2.0
COMM = 0.74
EOD_MIN = "15:55"
TRIGGER_TICKS = 0  # touch trigger at the tick-rounded level (best MNQ-bar match to the journal)


def _ns(x) -> np.int64:
    """UTC timestamp -> int64 nanoseconds (avoids tz-aware datetime64 warnings)."""
    return np.int64(pd.Timestamp(x).tz_convert("UTC").value)


def load_bars(path: str) -> dict:
    b = pd.read_csv(path)
    b["ts"] = pd.to_datetime(b.ts, utc=True)
    et = b.ts.dt.tz_convert("America/New_York")
    b["session"] = et.dt.strftime("%Y-%m-%d")
    b["hhmm"] = et.dt.strftime("%H:%M")
    out = {}
    for s, g in b.groupby("session", sort=True):
        g = g.sort_values("ts").reset_index(drop=True)
        out[s] = {
            "ts": g.ts.dt.tz_convert("UTC").values.astype("datetime64[ns]").astype(np.int64),
            "hhmm": g.hhmm.values,
            "open": g.open.values.astype(float),
            "high": g.high.values.astype(float),
            "low": g.low.values.astype(float),
            "close": g.close.values.astype(float),
            "eod_idx": int(np.where(g.hhmm.values == EOD_MIN)[0][0]),
        }
    return out


class Leg:
    def __init__(self, leg_id, qty, entry_px, entry_idx, stop, target):
        self.leg_id = leg_id
        self.qty = qty
        self.entry_px = entry_px
        self.entry_idx = entry_idx
        self.stop = stop
        self.target = target
        self.open = True
        self.exit_px = None
        self.exit_idx = None
        self.exit_reason = None
        self.stop_moved_idx = None  # bar index at which a tightened stop became effective

    def gross(self, px, sgn):
        return self.qty * (px - self.entry_px) * sgn * PT_VALUE


def _exit(leg, px, idx, reason):
    leg.open = False
    leg.exit_px = px
    leg.exit_idx = idx
    leg.exit_reason = reason


def replay_trade(tr, bars, policy: str, ordering: str = "stop_first",
                 be_trigger_R: float = 0.5, scale_R: float = 1.0,
                 honour_manual: bool = False, record_path: bool = False,
                 trigger_ticks: int = TRIGGER_TICKS) -> dict:
    """Replay one KX trade under one policy.

    policy in {'a_orig','b_add_stop_entry','c_add_be_after','d_all_be_on_add','e_scaleout_add'}
    tr: a row of trades.csv with parsed timestamps (UTC) and helper fields.
    """
    S = bars[tr.session]
    sgn = 1 if tr.direction == "LONG" else -1
    ts = S["ts"]
    entry_idx = int(np.searchsorted(ts, _ns(tr.entry_ts)))
    assert ts[entry_idx] == _ns(tr.entry_ts)
    eod_idx = S["eod_idx"]
    stop0, tgt0 = float(tr.initial_stop_px), float(tr.initial_target_px)
    stopd = (tr.entry_px - stop0) * sgn  # points
    has_add = tr.added_contracts > 0
    add_idx = int(np.searchsorted(ts, _ns(tr.add_ts))) if has_add else None
    manual_idx = None
    if honour_manual and tr.exit_reason == "MANUAL":
        manual_idx = int(np.searchsorted(ts, _ns(tr.exit_ts)))
    pen = trigger_ticks * TICK  # required penetration beyond a level

    legs = [Leg(1, int(tr.initial_contracts), float(tr.entry_px), entry_idx, stop0, tgt0)]
    commissions = COMM * legs[0].qty  # entry
    path = []  # per-minute open profit per leg
    peak_open = -np.inf
    realised_gross = 0.0
    leg2 = None
    be_armed = False

    def mark(i):
        nonlocal peak_open
        fav = S["high"][i] if sgn == 1 else S["low"][i]
        m = realised_gross + sum(l.gross(fav, sgn) for l in legs if l.open)
        peak_open = max(peak_open, m)
        if record_path:
            c = S["close"][i]
            path.append({
                "idx": i, "hhmm": S["hhmm"][i], "close": c,
                "leg1_open_pnl": legs[0].gross(c, sgn) if legs[0].open else np.nan,
                "leg2_open_pnl": (leg2.gross(c, sgn) if (leg2 is not None and leg2.open) else np.nan),
                "leg1_stop": legs[0].stop if legs[0].open else np.nan,
                "leg2_stop": (leg2.stop if (leg2 is not None and leg2.open) else np.nan),
                "realised_gross": realised_gross,
            })

    for i in range(entry_idx, eod_idx + 1):
        o, h, l, c = S["open"][i], S["high"][i], S["low"][i], S["close"][i]
        # forced flat at the 15:55 open or at the journal's manual exit bar
        if i == eod_idx or (manual_idx is not None and i == manual_idx):
            px = o - sgn * TICK
            reason = "TIME_EOD" if i == eod_idx else "MANUAL_FORCED"
            for lg in legs:
                if lg.open:
                    _exit(lg, px, i, reason)
                    realised_gross += lg.gross(px, sgn)
                    commissions += COMM * lg.qty
            mark(i)
            break
        # the add fills at this bar's open (journal price), policy sets its bracket
        if has_add and i == add_idx and legs[0].open:
            leg2 = Leg(2, int(tr.added_contracts), float(tr.add_px), i, stop0, tgt0)
            commissions += COMM * leg2.qty
            if policy == "b_add_stop_entry":
                leg2.stop = float(tr.entry_px); leg2.stop_moved_idx = i
            elif policy == "d_all_be_on_add":
                for lg in legs:
                    lg.stop = float(tr.entry_px); lg.stop_moved_idx = i
                leg2.stop = float(tr.entry_px); leg2.stop_moved_idx = i
            elif policy == "e_scaleout_add":
                leg2.target = float(tr.add_px) + sgn * scale_R * stopd
            legs.append(leg2)
        # evaluate exits on this bar (journal convention: bracket not live on the entry bar)
        for lg in legs:
            if not lg.open or i == entry_idx:
                continue
            stop_hit = (l <= lg.stop - pen) if sgn == 1 else (h >= lg.stop + pen)
            tgt_hit = (h >= lg.target + pen) if sgn == 1 else (l <= lg.target - pen)
            gapped = (o <= lg.stop) if sgn == 1 else (o >= lg.stop)
            if gapped:
                stop_hit = True
            if stop_hit and tgt_hit:
                first = "stop" if ordering == "stop_first" else "target"
                if gapped:
                    first = "stop"
            elif stop_hit:
                first = "stop"
            elif tgt_hit:
                first = "target"
            else:
                continue
            if first == "stop":
                px = (o - sgn * TICK) if gapped else (lg.stop - sgn * TICK)
                _exit(lg, px, i, "STOP_GAP" if gapped else "STOP")
            else:
                _exit(lg, lg.target, i, "TARGET")
            realised_gross += lg.gross(lg.exit_px, sgn)
            commissions += COMM * lg.qty
        mark(i)
        # decisions on this bar's close, effective next bar
        if policy == "c_add_be_after" and leg2 is not None and leg2.open and not be_armed:
            if (c - leg2.entry_px) * sgn >= be_trigger_R * stopd:
                leg2.stop = leg2.entry_px
                leg2.stop_moved_idx = i + 1
                be_armed = True
        if not any(lg.open for lg in legs):
            break

    net = realised_gross - commissions
    R = float(tr.planned_risk_usd)
    last_exit = max(lg.exit_idx for lg in legs)
    out = {
        "trade_id": int(tr.trade_id), "session": tr.session, "policy": policy,
        "has_add": bool(has_add), "n_legs": len(legs),
        "gross_usd": realised_gross, "commission_usd": commissions, "net_usd": net,
        "net_R": net / R, "peak_open_gross_usd": peak_open,
        "giveback_usd": peak_open - net, "giveback_R": (peak_open - net) / R,
        "exit_idx": last_exit, "exit_hhmm": S["hhmm"][last_exit],
        "leg1_exit_reason": legs[0].exit_reason, "leg1_exit_px": legs[0].exit_px,
        "leg1_exit_hhmm": S["hhmm"][legs[0].exit_idx],
        "leg1_net_usd": legs[0].gross(legs[0].exit_px, sgn) - 2 * COMM * legs[0].qty,
    }
    if leg2 is not None:
        out.update({
            "leg2_exit_reason": leg2.exit_reason, "leg2_exit_px": leg2.exit_px,
            "leg2_exit_hhmm": S["hhmm"][leg2.exit_idx],
            "leg2_net_usd": leg2.gross(leg2.exit_px, sgn) - 2 * COMM * leg2.qty,
            "leg2_risk_usd": leg2.qty * (leg2.entry_px - stop0) * sgn * PT_VALUE,
            "add_hhmm": S["hhmm"][leg2.entry_idx],
        })
    else:
        out.update({"leg2_exit_reason": None, "leg2_exit_px": np.nan, "leg2_exit_hhmm": None,
                    "leg2_net_usd": np.nan, "leg2_risk_usd": np.nan, "add_hhmm": None})
    if record_path:
        out["path"] = pd.DataFrame(path)
        out["legs"] = legs
    return out
