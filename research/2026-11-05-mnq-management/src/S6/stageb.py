"""
Stage B: chronological portfolio replay from signals.csv (executed AND rejected signals)
with the 4-contract limit, the KX pyramiding rule, and the 15:55 cutoff.

Entry re-simulated at the next MNQ bar open +1 tick adverse (S6 ASSUMPTION: deterministic
1 tick; the journal used 0/1/2 ticks).  Stop = entry -/+ stop distance rounded to tick;
KX target = entry +/- round_tick(mult x stop distance); PX target = planned_target_px.
Room check at the entry bar open: a signal executes only if (contracts already open,
including any add) + planned_contracts <= 4.  An open trade occupies its contracts from
its entry bar up to but excluding its exit bar (journal convention, verified on signals
35, 58, 336: a signal entering on the bar in which the previous trade exits is executed).
Journal MANUAL exits (trades 193, 273) freed room that no mechanical replay reproduces.  Solved by fixed-point iteration so that a later entry can
also block an earlier trade's add.
"""
import numpy as np
import pandas as pd
from replay import replay_trade, rt, TICK, EOD

LIMIT = 4


def _mk_trade(sig, S, d):
    e_i = S["idx"].get(sig["signal_ts"])
    if e_i is None:
        return None
    if S["ts_list"][e_i].time() >= EOD:
        return None
    e_px = S["o"][e_i] + d * TICK
    sd = float(rt(sig["planned_stop_dist_pts"]))
    stop = e_px - d * sd
    if sig["family"] == "KX":
        tgt = e_px + d * float(rt(sig["planned_target_mult_R"] * sig["planned_stop_dist_pts"]))
    else:
        tgt = float(sig["planned_target_px"])
    return dict(trade_id=int(sig["signal_id"]), signal_id=int(sig["signal_id"]), session=sig["session"],
                strategy=sig["strategy"], family=sig["family"], direction=sig["direction"],
                entry_ts=sig["signal_ts"], entry_px=e_px, initial_contracts=int(sig["planned_contracts"]),
                initial_stop_px=stop, initial_target_px=tgt, planned_risk_usd=float(sig["planned_risk_usd"]),
                entry_i=e_i)


def stage_b(signals, sb, policy, max_pass=6, **kw):
    sig = signals.copy()
    sig["session"] = sig["signal_ts"].dt.strftime("%Y-%m-%d")
    sig = sig.sort_values(["signal_ts", "signal_id"]).reset_index(drop=True)
    out_rows = []
    rejected = []
    for sess, g in sig.groupby("session", sort=True):
        S = sb.get(sess)
        n = len(S["o"])
        # state from previous pass: signal_id -> (entry_i, exit_i, n0, add_i)
        state = {}
        for _pass in range(max_pass):
            new_state = {}
            res = {}
            for _, s in g.iterrows():
                d = 1.0 if s["direction"] == "LONG" else -1.0
                tr = _mk_trade(s, S, d)
                if tr is None:
                    continue
                e_i = tr["entry_i"]

                def others_open(i, exclude=s["signal_id"]):
                    tot = 0
                    for sid, (ei, xi, n0, ai) in {**state, **new_state}.items():
                        if sid == exclude:
                            continue
                        if ei <= i < xi:
                            tot += n0 + (1 if (ai is not None and ai <= i) else 0)
                    return tot

                room = LIMIT - others_open(e_i)
                if room < tr["initial_contracts"]:
                    res[s["signal_id"]] = None
                    continue
                r = replay_trade(tr, S, policy, entry_px=tr["entry_px"], entry_i=e_i,
                                 open_contracts_fn=lambda ts, _e=e_i, _sid=s["signal_id"]:
                                 others_open(S["idx"][ts], exclude=_sid), **kw)
                add_i = r["add_i"] if r["add"] else None
                new_state[s["signal_id"]] = (e_i, r["exit_i"], tr["initial_contracts"], add_i)
                r["entry_i"] = e_i
                r["entry_px"] = tr["entry_px"]
                r["n0"] = tr["initial_contracts"]
                res[s["signal_id"]] = r
            if new_state == state:
                break
            state = new_state
        for sid, r in res.items():
            if r is None:
                rejected.append(dict(signal_id=sid, session=sess))
            else:
                out_rows.append(r)
    ex = pd.DataFrame(out_rows)
    rj = pd.DataFrame(rejected)
    return ex, rj
