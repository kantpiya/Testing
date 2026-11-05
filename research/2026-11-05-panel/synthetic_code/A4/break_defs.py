"""SYNTHETIC: two break definitions on the same random-walk-with-ranges path.

Path: 1-minute 'bars' for N sessions. Each session = 390 bars. First 30 bars
define the opening range (OR). Price is a Gaussian random walk whose step
size is scaled by a per-session volatility draw, plus occasional 'ranges'
(mean-reverting segments) so that there are both breaks and failures.

Break definitions compared on identical paths:
  B1 (touch):  any bar whose CLOSE is beyond OR high/low by >= 1 tick.
  B2 (hold):   two consecutive CLOSES beyond OR high/low by >= 0.25*OR_width.
Follow-through (FT), same for both: within K=10 bars after the break bar,
price reaches break level + 1.0*OR_width in the break direction before
re-entering the OR by >= 0.25*OR_width ('failed break').
Denominators reported: sessions, breaks/session, FT per break.
"""
import numpy as np

rng = np.random.default_rng(71)
N_SESS, BARS, OR_BARS, K = 500, 390, 30, 10
TICK = 0.25

def make_session():
    vol = rng.lognormal(mean=np.log(2.0), sigma=0.4)      # points per bar
    steps = rng.normal(0, vol, BARS)
    # inject mean-reverting 'range' segments ~50% of the time after the OR
    regime = rng.random() < 0.5
    px = np.empty(BARS); px[0] = 20000.0
    for t in range(1, BARS):
        px[t] = px[t-1] + steps[t]
        if regime and t > OR_BARS:
            px[t] -= 0.15 * (px[t-1] - px[OR_BARS])      # pull toward post-OR anchor
    return np.round(px / TICK) * TICK

def classify(px, defn):
    orh, orl = px[:OR_BARS].max(), px[:OR_BARS].min()
    w = max(orh - orl, TICK)
    events = []
    t = OR_BARS
    while t < BARS - K - 1:
        d = 0
        if defn == "B1":
            if px[t] >= orh + TICK: d = +1
            elif px[t] <= orl - TICK: d = -1
        elif defn == "B2":
            if px[t] >= orh + 0.25*w and px[t-1] >= orh + 0.25*w: d = +1
            elif px[t] <= orl - 0.25*w and px[t-1] <= orl - 0.25*w: d = -1
        if d == 0:
            t += 1; continue
        lvl = orh if d > 0 else orl
        target = lvl + d*1.0*w
        fail_lvl = lvl - d*0.25*w
        ft, failed = False, False
        for u in range(t+1, t+1+K):
            if d*(px[u]-target) >= 0: ft = True; break
            if d*(px[u]-fail_lvl) <= 0: failed = True; break
        events.append((d, ft, failed))
        # one event per side per session: skip until price re-enters OR
        u = t + 1
        while u < BARS and d*(px[u]-lvl) > 0: u += 1
        t = u + 1
    return events

paths = [make_session() for _ in range(N_SESS)]
for defn in ("B1", "B2"):
    ev = [e for p in paths for e in classify(p, defn)]
    n_ev = len(ev)
    sess_with = sum(1 for p in paths if classify(p, defn))
    ft = sum(e[1] for e in ev); fl = sum(e[2] for e in ev)
    print(f"{defn}: sessions={N_SESS}  sessions_with_break={sess_with}  "
          f"breaks={n_ev}  breaks/session={n_ev/N_SESS:.2f}  "
          f"FT/break={ft/n_ev:.3f}  failed/break={fl/n_ev:.3f}  "
          f"unresolved/break={(n_ev-ft-fl)/n_ev:.3f}  FT/session={ft/N_SESS:.3f}")
