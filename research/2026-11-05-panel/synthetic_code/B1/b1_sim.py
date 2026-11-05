"""SYNTHETIC: 3 mechanism-class slots, 2 scenarios, 3 policies on ONE shared eligible-signal log.
Slots: BO = breakout/continuation, FB = failed-break reversal, MR = mean-reversion to VWAP.
Constraint: one open position per instrument; a signal that arrives while a position is open is REJECTED (logged).
Outcome per signal drawn from a per-(slot, condition) distribution in R multiples, minus cost 0.10R.
Nothing here is calibrated to real MNQ data. Numbers are illustrative only.
"""
import numpy as np
rng = np.random.default_rng(7)
COST = 0.10
N_SESS = 400
# expected R (before cost) by slot and condition; sd fixed at 1.0R
MU = {
 "orderly_trend":        {"BO": 0.35, "FB": -0.15, "MR": -0.20},
 "failed_open_breakout": {"BO": -0.25, "FB": 0.30, "MR": 0.05},
 "quiet_rotation":       {"BO": -0.20, "FB": 0.00, "MR": 0.25},
 "release_pending":      {"BO": -0.05, "FB": -0.10, "MR": -0.15},
}
RANK = {  # P2 ranking by condition (lower index = higher priority); None = gated out
 "orderly_trend": ["BO", "FB"], "failed_open_breakout": ["FB", "MR", "BO"],
 "quiet_rotation": ["MR", "FB"], "release_pending": [],
}
def session(cond):
    """Each slot emits 0-2 signals at random minutes in a 120-min window; returns shared log."""
    log = []
    for s in ["BO", "FB", "MR"]:
        for _ in range(rng.integers(0, 3)):
            t = rng.integers(0, 120)
            r = rng.normal(MU[cond][s], 1.0) - COST
            log.append(dict(slot=s, t=int(t), cond=cond, R=r))
    return sorted(log, key=lambda d: d["t"])
def run(policy, log, cond):
    taken, pos_until = [], -1
    for sig in log:
        sig = dict(sig)
        # policy filter
        if policy == "P1":   # session-only: trade minutes 0-60 only, any slot
            elig = sig["t"] < 60
        elif policy == "P2":
            elig = sig["slot"] in RANK[cond]
        else:
            elig = True
        if not elig: sig["status"] = "rejected_policy"; taken.append(sig); continue
        if sig["t"] < pos_until:
            # P2 only: a higher-ranked slot may pre-empt a lower-ranked open position (flatten + re-enter)
            if policy == "P2" and taken_open and RANK[cond].index(sig["slot"]) < RANK[cond].index(taken_open["slot"]):
                taken_open["R"] = taken_open["R"] * 0.3  # scratch the lower-ranked trade early (illustrative)
                taken_open["status"] = "preempted"
            else:
                sig["status"] = "rejected_position_open"; taken.append(sig); continue
        sig["status"] = "filled"; pos_until = sig["t"] + 45; taken_open = sig; taken.append(sig)
    return taken
res = {}
for cond in MU:
    for pol in ["P0", "P1", "P2"]:
        rows = []
        for _ in range(N_SESS):
            rows += run(pol, session(cond), cond)
        filled = [r for r in rows if r["status"] in ("filled", "preempted")]
        res[(cond, pol)] = dict(
            eligible=len(rows), filled=len(filled), rej_policy=sum(r["status"]=="rejected_policy" for r in rows),
            rej_pos=sum(r["status"]=="rejected_position_open" for r in rows),
            netR=sum(r["R"] for r in filled), winners_discarded=sum(1 for r in rows if r["status"]=="rejected_policy" and r["R"]>0),
            losses_avoided=sum(1 for r in rows if r["status"]=="rejected_policy" and r["R"]<=0))
print(f"{'condition':22}{'pol':5}{'elig':>6}{'fill':>6}{'rejPol':>7}{'rejPos':>7}{'winDisc':>8}{'lossAv':>7}{'netR':>9}{'R/sess':>8}")
for (cond, pol), v in res.items():
    print(f"{cond:22}{pol:5}{v['eligible']:6d}{v['filled']:6d}{v['rej_policy']:7d}{v['rej_pos']:7d}{v['winners_discarded']:8d}{v['losses_avoided']:7d}{v['netR']:9.1f}{v['netR']/N_SESS:8.3f}")
