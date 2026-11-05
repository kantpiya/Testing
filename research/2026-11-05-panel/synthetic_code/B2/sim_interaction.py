"""
SYNTHETIC simulation: strategy x condition interaction vs. pure condition main effect.
Outcome: per-trade net P&L in R (risk units); 3 strategies x 3 conditions; ~250 sessions.
Session = unit of independence (a shared session shock hits every strategy that trades that session).
Pure numpy/scipy; cluster-robust OLS (CR1) implemented by hand.
"""
import numpy as np
from scipy import stats

rng = np.random.default_rng(20261105)
S, C = 3, 3
STRATS = ["KX", "PX", "ENG"]
CONDS = ["Calm", "Normal", "Volatile"]


def simulate(n_sess=250, interaction=None, sess_sd=0.35, noise_sd=1.2,
             cond_eff=(-0.25, 0.0, 0.30), strat_eff=(0.05, 0.10, 0.00),
             rate=None, rng=rng):
    """Return arrays trade-level: y, strat, cond, sess."""
    if rate is None:
        # trades per session per strategy, Poisson rate by (strat, cond): opportunity sets differ.
        rate = np.array([[0.4, 2.0, 3.0],    # KX rarely fires in Calm -> sparse cell
                         [2.0, 2.0, 2.0],
                         [3.0, 2.0, 1.0]])
    inter = np.zeros((S, C)) if interaction is None else np.asarray(interaction)
    cond_of_sess = rng.choice(C, size=n_sess, p=[0.3, 0.45, 0.25])
    u_sess = rng.normal(0, sess_sd, n_sess)
    ys, ss, cs, ks = [], [], [], []
    for k in range(n_sess):
        c = cond_of_sess[k]
        for s in range(S):
            n = rng.poisson(rate[s, c])
            if n == 0:
                continue
            mu = strat_eff[s] + cond_eff[c] + inter[s, c] + u_sess[k]
            y = mu + noise_sd * rng.standard_t(df=5, size=n)   # fat tails
            ys.append(y); ss.append(np.full(n, s)); cs.append(np.full(n, c)); ks.append(np.full(n, k))
    return (np.concatenate(ys), np.concatenate(ss), np.concatenate(cs), np.concatenate(ks))


def design(strat, cond, with_inter=True):
    n = len(strat)
    cols = [np.ones(n)]
    names = ["const"]
    for s in range(1, S):
        cols.append((strat == s).astype(float)); names.append(f"S{STRATS[s]}")
    for c in range(1, C):
        cols.append((cond == c).astype(float)); names.append(f"C{CONDS[c]}")
    if with_inter:
        for s in range(1, S):
            for c in range(1, C):
                cols.append(((strat == s) & (cond == c)).astype(float))
                names.append(f"S{STRATS[s]}xC{CONDS[c]}")
    return np.column_stack(cols), names


def ols_cluster(X, y, g):
    """OLS with CR1 cluster-robust covariance (clusters = g). Also returns iid covariance."""
    n, p = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    # iid
    V_iid = XtX_inv * (e @ e) / (n - p)
    # cluster
    G = len(np.unique(g))
    meat = np.zeros((p, p))
    for gid in np.unique(g):
        idx = g == gid
        sc = X[idx].T @ e[idx]
        meat += np.outer(sc, sc)
    adj = (G / (G - 1)) * ((n - 1) / (n - p))
    V_cl = adj * XtX_inv @ meat @ XtX_inv
    return b, V_iid, V_cl, G


def wald_inter(b, V, names, G):
    idx = [i for i, nm in enumerate(names) if "x" in nm]
    bi = b[idx]; Vi = V[np.ix_(idx, idx)]
    W = bi @ np.linalg.solve(Vi, bi)
    q = len(idx)
    # F-approx with G-1 denominator df (conservative for few clusters)
    F = W / q
    p = 1 - stats.f.cdf(F, q, G - 1)
    return W, p


def naive_best(y, strat, cond):
    """Per condition, rank strategies by mean per-trade P&L (the naive 'best strategy per condition')."""
    best = []
    for c in range(C):
        means = [y[(strat == s) & (cond == c)].mean() if ((strat == s) & (cond == c)).any() else -np.inf
                 for s in range(S)]
        best.append(int(np.argmax(means)))
    return best


def cell_table(y, strat, cond, sess):
    out = np.zeros((S, C, 3))
    for s in range(S):
        for c in range(C):
            m = (strat == s) & (cond == c)
            out[s, c] = [m.sum(), len(np.unique(sess[m])), y[m].mean() if m.any() else np.nan]
    return out


def shrink_cells(y, strat, cond, sess):
    """Empirical-Bayes partial pooling: cell deviation from (strategy + condition) additive fit,
    shrunk toward 0 with weight tau2/(tau2 + se2_cell). Session-level means used so se respects clustering."""
    X0, _ = design(strat, cond, with_inter=False)
    b0 = np.linalg.lstsq(X0, y, rcond=None)[0]
    resid = y - X0 @ b0
    dev, se2, keys = [], [], []
    for s in range(S):
        for c in range(C):
            m = (strat == s) & (cond == c)
            if not m.any():
                dev.append(np.nan); se2.append(np.nan); keys.append((s, c)); continue
            # session-level mean residuals within cell -> cluster-respecting SE
            sids = np.unique(sess[m])
            smeans = np.array([resid[m & (sess == k)].mean() for k in sids])
            d = smeans.mean()
            v = smeans.var(ddof=1) / len(sids) if len(sids) > 1 else np.nan
            dev.append(d); se2.append(v); keys.append((s, c))
    dev, se2 = np.array(dev), np.array(se2)
    ok = np.isfinite(dev) & np.isfinite(se2)
    # method-of-moments tau^2 (DerSimonian-Laird style)
    tau2 = max(0.0, np.var(dev[ok], ddof=1) - np.mean(se2[ok]))
    w = tau2 / (tau2 + se2)
    shrunk = w * dev
    return dev, np.sqrt(se2), shrunk, tau2, w


def one_fit(y, strat, cond, sess, label):
    X, names = design(strat, cond)
    b, Vi, Vc, G = ols_cluster(X, y, sess)
    Wc, pc = wald_inter(b, Vc, names, G)
    Wi, pi = wald_inter(b, Vi, names, G)
    print(f"\n=== {label}: n_trades={len(y)}, sessions={G} ===")
    print("Interaction Wald (cluster-robust, F-approx):  p = %.4f" % pc)
    print("Interaction Wald (iid SE, WRONG):            p = %.4f" % pi)
    print("Coefficient  est  [cluster SE]  [iid SE]")
    for i, nm in enumerate(names):
        print(f"  {nm:18s} {b[i]:+.3f}   {np.sqrt(Vc[i,i]):.3f}   {np.sqrt(Vi[i,i]):.3f}")
    tab = cell_table(y, strat, cond, sess)
    print("Cell table: (n_trades / n_sessions / mean R)")
    for s in range(S):
        print("  " + STRATS[s].ljust(4) + "  ".join(f"{CONDS[c]}: {int(tab[s,c,0]):4d}/{int(tab[s,c,1]):3d}/{tab[s,c,2]:+.2f}" for c in range(C)))
    nb = naive_best(y, strat, cond)
    print("Naive 'best strategy per condition':", {CONDS[c]: STRATS[nb[c]] for c in range(C)})
    dev, se, shr, tau2, w = shrink_cells(y, strat, cond, sess)
    print(f"Shrinkage: tau^2 = {tau2:.4f};  raw cell deviation -> shrunk (weight)")
    k = 0
    for s in range(S):
        row = []
        for c in range(C):
            row.append(f"{dev[k]:+.2f}->{shr[k]:+.2f} (w={w[k]:.2f})"); k += 1
        print("  " + STRATS[s].ljust(4) + "   ".join(row))
    return pc, pi, nb


# ---------- Single illustrative draws ----------
yA, sA, cA, kA = simulate(interaction=None)
one_fit(yA, sA, cA, kA, "CASE A: condition is a PURE MAIN EFFECT (no interaction)")

true_inter = np.array([[0.0, 0.0, 0.0],
                       [0.0, 0.0, 0.0],
                       [-0.45, 0.0, +0.60]])   # ENG genuinely worse in Calm, better in Volatile
yB, sB, cB, kB = simulate(interaction=true_inter)
one_fit(yB, sB, cB, kB, "CASE B: TRUE interaction (ENG: -0.45R Calm, +0.60R Volatile)")

# ---------- Monte Carlo ----------
def mc(reps, interaction, label):
    rej_cl = rej_iid = 0
    spurious = 0          # naive sort names >1 distinct 'best' strategy across conditions
    not_truebest = 0      # naive picks a strategy other than the true best main-effect strategy (PX) in >=1 condition
    for r in range(reps):
        y, s, c, k = simulate(interaction=interaction, rng=rng)
        X, names = design(s, c)
        b, Vi, Vc, G = ols_cluster(X, y, k)
        rej_cl += wald_inter(b, Vc, names, G)[1] < 0.05
        rej_iid += wald_inter(b, Vi, names, G)[1] < 0.05
        nb = naive_best(y, s, c)
        spurious += len(set(nb)) > 1
        not_truebest += any(x != 1 for x in nb)
    print(f"\n--- Monte Carlo {label} ({reps} reps, ~250 sessions each) ---")
    print(f"Interaction test rejection rate @5%: cluster-robust = {rej_cl/reps:.3f}   iid SE = {rej_iid/reps:.3f}")
    print(f"Naive sort claims DIFFERENT best strategies across conditions: {spurious/reps:.3f}")
    print(f"Naive sort names a non-best (true main-effect best = PX) strategy in >=1 condition: {not_truebest/reps:.3f}")

mc(400, None, "CASE A (null interaction)")
mc(400, true_inter, "CASE B (true interaction)")
# smaller true interaction: power check
mc(400, true_inter / 2, "CASE B' (half-size interaction: -0.225/+0.30 R)")
