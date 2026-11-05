"""
S6 independent Stage A / Stage B replay engine for the SYNTHETIC MNQ data set.

Conventions (all stated in the common brief unless marked S6 ASSUMPTION):
  * Entry fill, entry time, initial size and planned risk are taken from trades.csv
    (Stage A: identical entries).  In Stage B the entry is re-simulated at the next
    MNQ bar open + 1 tick adverse slippage.
  * Stop fills: stop price -/+ 1 tick adverse, or the bar open if the bar gapped
    through the stop.  Extra slippage ticks can be added (robustness (c)).
  * Target (limit) fills at the limit price, 0 slippage, only when the bar trades THROUGH
    the level (journal convention, verified: a bar whose high equals the target does not fill).
  * The entry bar itself is not checked for stop/target (journal convention, verified on
    trades 174 and 332); the add trigger is also strict (through, not touch) and its
    20-minute window is inclusive (verified on trades 36, 56, 340).
  * Market exits (time / no-progress / EOD): a decision taken at the close of bar k
    is filled at the open of bar k+1 minus 1 tick adverse (+ extra slippage).
  * Same-bar stop AND target touch: `order` = 'stop_first' (pessimistic) or
    'target_first' (optimistic).  Both are reported for tightened stops.
  * Commissions $0.74 per contract per side on every fill (entry, add, exit).
  * KX add: 1 contract at the next bar open (+1 tick) after a bar whose high/low
    reaches entry +/- 1.0 x stop distance, within 20 min of entry and before
    12:00 ET, only if total position stays <= 4.  Add shares stop and target.
  * EOD: everything flat at the 15:55 bar open (minus 1 tick).
  * A decision rule evaluated at minute k uses only bars whose close <= decision
    time; a stop moved on the strength of bar k is live from bar k+1.
"""
import numpy as np
import pandas as pd

TICK = 0.25
PT_VALUE = 2.0
COMM = 0.74
EOD = pd.Timestamp("15:55").time()


def rt(x):
    """Round to tick."""
    return np.round(np.asarray(x, dtype=float) / TICK) * TICK


def load_bars(path):
    b = pd.read_csv(path)
    b["ts"] = pd.to_datetime(b["ts"], utc=True).dt.tz_convert("America/New_York")
    b["session"] = b["ts"].dt.strftime("%Y-%m-%d")
    return b


def load_trades(path):
    t = pd.read_csv(path)
    for c in ("entry_ts", "exit_ts", "add_ts"):
        t[c] = pd.to_datetime(t[c], utc=True).dt.tz_convert("America/New_York")
    return t


class SessionBars:
    """Per-session numpy arrays for speed."""

    def __init__(self, bars):
        self.by_session = {}
        for s, g in bars.groupby("session", sort=True):
            g = g.sort_values("ts")
            ts_list = list(g["ts"])
            self.by_session[s] = dict(
                ts=g["ts"].values,
                o=g["open"].values.astype(float),
                h=g["high"].values.astype(float),
                l=g["low"].values.astype(float),
                c=g["close"].values.astype(float),
                idx={x: i for i, x in enumerate(ts_list)},
                ts_list=ts_list,
            )

    def get(self, session):
        return self.by_session[session]


# ----------------------------------------------------------------------------
# Policy description
# ----------------------------------------------------------------------------
# A policy is a dict with keys (all optional; missing = original behaviour):
#   time_exit_min      : int   -> exit at open of bar (entry_bar + T) if still open
#   noprog_min, noprog_R : exit at open of bar entry+T if MFE (high/low based, in R) < noprog_R by then
#   be_trigger_R, be_lock_R : after a bar touches +trigger R, stop moves to entry + lock R (lock may be 0)
#   trail_trigger_R, trail_dist_R : after +trigger R, stop = peak - dist R (ratcheted), live next bar
#   target_mult        : float -> override target multiple (KX); for PX use min(structural, entry + mult*R)
#   kx_target_mult     : float or None -> KX target multiple (None = no target, EOD only); PX unchanged
#   time_exit_et       : "HH:MM" -> market exit at the open of the first bar at/after that ET clock time
#   family_filter      : "KX"/"PX" -> policy applies to that family only; the other family keeps the original
#   px_target_mult     : float or None -> PX target replaced by entry + m*R (None = no target)
#   px_cap_R           : float -> PX structural target capped at entry + cap*R
#   target_cap_R       : float -> cap target at entry + cap R (both families)
#   add_be             : bool  -> once the add fills, the add leg gets its own stop at the add price
#                                (exit 1 contract on a touch); initial leg keeps the original stop
#   no_add             : bool  -> suppress pyramiding
#   add_trail_R        : float -> add leg trails at (peak - R) once add filled


def replay_trade(tr, bars, policy, slip_ticks=1, order="stop_first", include_entry_bar=False,
                 entry_px=None, entry_i=None, contracts=None, stop_px=None, target_px=None,
                 extra_slip_ticks=0, allow_add=True, add_cap=4, open_contracts_fn=None,
                 strict_limit=True, strict_add=True, strict_stop=False):
    """
    Replay one trade on its session bars under `policy`.
    Returns dict with exit info, net P&L in USD and in R, per-leg details.
    `open_contracts_fn(ts)` (Stage B) returns contracts held by OTHER trades at time ts
    (used to respect the 4-contract limit for the add).
    """
    d = 1.0 if tr["direction"] == "LONG" else -1.0
    S = bars
    e_i = entry_i if entry_i is not None else S["idx"][pd.Timestamp(tr["entry_ts"])]
    e_px = float(entry_px if entry_px is not None else tr["entry_px"])
    n0 = int(contracts if contracts is not None else tr["initial_contracts"])
    stop0 = float(stop_px if stop_px is not None else tr["initial_stop_px"])
    tgt0 = float(target_px if target_px is not None else tr["initial_target_px"])
    stop_dist = abs(e_px - stop0)
    risk_usd = float(tr["planned_risk_usd"])
    R_pts = stop_dist  # 1R in points (per contract) for the initial leg
    slip = (slip_ticks + extra_slip_ticks) * TICK
    adv_mkt = -d * slip  # adverse slippage for a market exit

    # policy
    p = policy
    if p.get("family_filter") and tr["family"] != p["family_filter"]:
        p = {}
    clock_exit = None
    if p.get("time_exit_et"):
        hh, mm = (int(v) for v in p["time_exit_et"].split(":"))
        clock_exit = pd.Timestamp(ts_tmp := bars["ts_list"][0]).replace(hour=hh, minute=mm)
    tgt = tgt0
    if p.get("target_mult") is not None:
        if tr["family"] == "KX":
            tgt = e_px + d * rt(p["target_mult"] * R_pts)
        else:
            cap = e_px + d * rt(p["target_mult"] * R_pts)
            tgt = cap if d * (cap - tgt0) < 0 else tgt0
    if tr["family"] == "KX" and "kx_target_mult" in p:
        km = p["kx_target_mult"]
        tgt = (e_px + d * 1e9) if km is None else e_px + d * rt(km * R_pts)   # None = no target (EOD only)
    if tr["family"] == "PX" and "px_target_mult" in p:
        pm = p["px_target_mult"]
        tgt = (e_px + d * 1e9) if pm is None else e_px + d * rt(pm * R_pts)
    if tr["family"] == "PX" and p.get("px_cap_R") is not None:
        cap = e_px + d * rt(p["px_cap_R"] * R_pts)
        tgt = cap if d * (cap - tgt) < 0 else tgt
    if p.get("target_cap_R") is not None:
        cap = e_px + d * rt(p["target_cap_R"] * R_pts)
        tgt = cap if d * (cap - tgt) < 0 else tgt
    stop = stop0
    be_trig = p.get("be_trigger_R")
    be_lock = p.get("be_lock_R", 0.0)
    tr_trig = p.get("trail_trigger_R")
    tr_dist = p.get("trail_dist_R")
    t_exit = p.get("time_exit_min")
    np_min = p.get("noprog_min")
    np_R = p.get("noprog_R")
    add_be = p.get("add_be", False)
    add_trail = p.get("add_trail_R")
    no_add = p.get("no_add", False)

    o, h, l, c, ts = S["o"], S["h"], S["l"], S["c"], S["ts_list"]
    nbar = len(o)
    eod_i = None
    for i in range(e_i, nbar):
        if ts[i].time() >= EOD:
            eod_i = i
            break
    if eod_i is None:
        eod_i = nbar - 1

    # state
    peak = e_px  # best favourable price (high/low based)
    add_pending_i = None  # bar index at which add fills (next open)
    add_i = None
    add_filled = False
    add_px = None
    add_n = 0
    add_stop = None  # separate stop for add leg
    add_exited = False
    add_exit_px = None
    add_exit_reason = None
    add_exit_i = None
    be_armed = False
    trail_on = False
    pending_stop = None  # stop that becomes live next bar
    fills = []  # (role, qty, price)
    fills.append(("ENTRY", n0, e_px))
    exit_px = None
    exit_reason = None
    exit_i = None
    mfe_R = 0.0
    mae_R = 0.0
    add_window_end = pd.Timestamp(ts[e_i]) + pd.Timedelta(minutes=20)
    noon = ts[e_i].replace(hour=12, minute=0)

    start = e_i if include_entry_bar else e_i + 1
    for i in range(start, nbar):
        t_i = ts[i]
        # ---- stop updates that become live at this bar open
        if pending_stop is not None:
            stop = pending_stop if d * (pending_stop - stop) > 0 else stop
            pending_stop = None
        # ---- add fill at this bar open
        if add_pending_i == i and not add_filled:
            room = add_cap - n0 - (open_contracts_fn(t_i) if open_contracts_fn else 0)
            if room >= 1:
                add_filled = True
                add_px = o[i] + d * slip
                add_n = 1
                add_i = i
                fills.append(("ADD", 1, add_px))
                if add_be:
                    add_stop = add_px
            add_pending_i = None
        # ---- EOD flat at 15:55 open
        if i >= eod_i:
            exit_px = o[i] + adv_mkt
            exit_reason = "TIME_EOD"
            exit_i = i
            break
        # ---- scheduled market exits at this bar open (decided at previous close)
        if t_exit is not None and i == e_i + t_exit:
            exit_px = o[i] + adv_mkt
            exit_reason = "TIME"
            exit_i = i
            break
        if clock_exit is not None and t_i >= clock_exit:
            exit_px = o[i] + adv_mkt
            exit_reason = "TIME_CLOCK"
            exit_i = i
            break
        if np_min is not None and i == e_i + np_min and mfe_R < np_R:
            exit_px = o[i] + adv_mkt
            exit_reason = "NOPROG"
            exit_i = i
            break
        # ---- intrabar: gap handling, stop, target
        gap_stop = d * (o[i] - stop) <= 0
        _adv = (l[i] if d > 0 else h[i])
        hit_stop = (d * (_adv - stop) < 0) if strict_stop else (d * (_adv - stop) <= 0)
        hit_tgt = (d * ((h[i] if d > 0 else l[i]) - tgt) > 0) if strict_limit else (d * ((h[i] if d > 0 else l[i]) - tgt) >= 0)
        # add-leg separate stop
        if add_filled and not add_exited and add_stop is not None:
            a_gap = d * (o[i] - add_stop) <= 0
            a_hit = (d * (_adv - add_stop) < 0) if strict_stop else (d * (_adv - add_stop) <= 0)
            if a_hit and not hit_stop:  # main stop takes precedence (handled below)
                add_exited = True
                add_exit_px = (o[i] if a_gap else add_stop) - d * slip
                add_exit_reason = "ADD_STOP"
                add_exit_i = i
                fills.append(("EXIT_ADD", 1, add_exit_px))
        if hit_stop and hit_tgt:
            if order == "stop_first":
                hit_tgt = False
            else:
                hit_stop = False
        if hit_stop:
            exit_px = (o[i] if gap_stop else stop) - d * slip
            exit_reason = "STOP_GAP" if gap_stop else ("STOP" if stop == stop0 else "STOP_TIGHT")
            exit_i = i
            break
        if hit_tgt:
            exit_px = tgt
            exit_reason = "TARGET"
            exit_i = i
            break
        # ---- end of bar: update observables
        fav = h[i] if d > 0 else l[i]
        advr = l[i] if d > 0 else h[i]
        if d * (fav - peak) > 0:
            peak = fav
        mfe_R = max(mfe_R, d * (fav - e_px) / R_pts)
        mae_R = min(mae_R, d * (advr - e_px) / R_pts)
        # add trigger (KX only, within 20 min, before noon)
        if (tr["family"] == "KX" and allow_add and not no_add and not add_filled
                and add_pending_i is None and t_i <= add_window_end and t_i < noon
                and ((d * (fav - (e_px + d * stop_dist)) > 0) if strict_add else (d * (fav - (e_px + d * stop_dist)) >= 0))):
            add_pending_i = i + 1
        # breakeven / lock
        if be_trig is not None and not be_armed and mfe_R >= be_trig:
            be_armed = True
            new_stop = e_px + d * rt(be_lock * R_pts)
            if d * (new_stop - stop) > 0:
                pending_stop = new_stop
        # trailing
        if tr_trig is not None and mfe_R >= tr_trig:
            trail_on = True
        if trail_on:
            new_stop = peak - d * rt(tr_dist * R_pts)
            if d * (new_stop - stop) > 0:
                pending_stop = new_stop if pending_stop is None else (
                    new_stop if d * (new_stop - pending_stop) > 0 else pending_stop)
        # add-leg trail
        if add_filled and not add_exited and add_trail is not None:
            ns = peak - d * rt(add_trail * R_pts)
            if add_stop is None or d * (ns - add_stop) > 0:
                add_stop = ns
    if exit_px is None:  # should not happen
        exit_px = c[-1]
        exit_reason = "END"
        exit_i = nbar - 1

    # P&L
    gross = n0 * d * (exit_px - e_px) * PT_VALUE
    if add_filled:
        a_exit = add_exit_px if add_exited else exit_px
        gross += add_n * d * (a_exit - add_px) * PT_VALUE
        if not add_exited:
            fills.append(("EXIT_ADD", 1, exit_px))
    fills.append(("EXIT", n0, exit_px))
    comm = sum(q for _, q, _ in fills) * COMM
    net = gross - comm
    return dict(
        trade_id=tr["trade_id"], session=tr["session"], strategy=tr["strategy"], family=tr["family"],
        exit_i=exit_i, exit_ts=ts[exit_i], exit_px=exit_px, exit_reason=exit_reason,
        gross=gross, comm=comm, net=net, net_R=net / risk_usd, add=int(add_filled),
        add_px=add_px, add_i=add_i, add_exit_reason=add_exit_reason, mfe_R=mfe_R, mae_R=mae_R,
        hold_min=exit_i - e_i, n0=n0, final_stop=stop, tgt=tgt,
    )


def replay_all(trades, sb, policy, **kw):
    out = []
    for _, tr in trades.iterrows():
        out.append(replay_trade(tr, sb.get(tr["session"]), policy, **kw))
    return pd.DataFrame(out)
