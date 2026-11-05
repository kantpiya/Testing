# SYNTHETIC variant: strong session shocks + many trades/session -> show iid SE over-rejects on CONDITION main effect,
# and that interaction contrasts are partly protected (within-session differencing) when strategies co-trade sessions.
import numpy as np
from scipy import stats
import importlib.util, sys
spec = importlib.util.spec_from_file_location("sim", "sim_interaction.py")
# avoid re-running module body: copy the needed functions instead
exec(open("sim_interaction.py").read().split("# ---------- Single illustrative draws ----------")[0])
rng = np.random.default_rng(7)
def wald_block(b, V, names, G, key):
    idx = [i for i, nm in enumerate(names) if nm.startswith(key) and "x" not in nm]
    bi = b[idx]; Vi = V[np.ix_(idx, idx)]
    W = bi @ np.linalg.solve(Vi, bi); q = len(idx)
    return 1 - stats.f.cdf(W / q, q, G - 1)
rate_hi = np.array([[1.5, 6.0, 9.0],[6.0, 6.0, 6.0],[9.0, 6.0, 3.0]])
for label, cond_eff in [("cond main effect NULL", (0,0,0)), ("cond main effect present", (-0.25,0,0.30))]:
    rc = ri = rci = rii = 0; reps = 300
    for r in range(reps):
        y, s, c, k = simulate(interaction=None, sess_sd=0.8, rate=rate_hi, cond_eff=cond_eff, rng=rng)
        X, names = design(s, c); b, Vi, Vc, G = ols_cluster(X, y, k)
        rc += wald_block(b, Vc, names, G, "C") < 0.05; ri += wald_block(b, Vi, names, G, "C") < 0.05
        rci += wald_inter(b, Vc, names, G)[1] < 0.05; rii += wald_inter(b, Vi, names, G)[1] < 0.05
    print(f"[{label}; sess_sd=0.8, ~6 trades/strat/session] condition-main-effect rejection: cluster={rc/reps:.3f} iid={ri/reps:.3f} | interaction(null) rejection: cluster={rci/reps:.3f} iid={rii/reps:.3f}")
