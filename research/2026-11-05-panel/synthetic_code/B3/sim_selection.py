"""SYNTHETIC: best-of-200 parameter sets on pure noise vs one preselected rule.
Also: same-bar stop/target ambiguity spread, and overlapping-label inflation.
Run: python3 -I sim_selection.py
"""
import numpy as np

rng = np.random.default_rng(66)

# ---------- 1. Selection effect (Study 66 context) ----------
N_DAYS, N_TRIALS, N_SIM = 250, 200, 2000
# daily P&L of a rule = sum of N trades/day of iid noise; mean 0, sd 1 (in R units)
def sharpe_like(x):  # annualized t-stat-ish: mean/sd*sqrt(n)
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x))

pre_t, best_t, pre_p_naive, best_p_naive = [], [], [], []
for _ in range(N_SIM):
    pnl = rng.standard_normal((N_TRIALS, N_DAYS))        # 200 parameter sets, all pure noise
    t = pnl.mean(1) / pnl.std(1, ddof=1) * np.sqrt(N_DAYS)
    pre_t.append(t[0])                                    # rule chosen BEFORE looking = index 0
    best_t.append(t.max())
pre_t, best_t = np.array(pre_t), np.array(best_t)
from math import erf, sqrt
def p_one_sided(t): return 0.5 * (1 - erf(t / sqrt(2)))
print("=== SYNTHETIC selection simulation: pure noise, 250 days, 200 parameter sets ===")
print(f"Preselected rule: mean t={pre_t.mean():+.2f}, P(t>1.96)={np.mean(pre_t>1.96):.3f}  (nominal 0.025)")
print(f"Best-of-200     : mean t={best_t.mean():+.2f}, P(t>1.96)={np.mean(best_t>1.96):.3f}, "
      f"median naive p={np.median([p_one_sided(x) for x in best_t]):.2e}")
print(f"Max-of-200 null 95th pct of t = {np.quantile(best_t,0.95):.2f}  <- honest critical value for a searched result")
print(f"Preselected null 95th pct of t = {np.quantile(pre_t,0.95):.2f}")

# Reality-check style procedure on ONE realized search (what the user should report)
pnl = rng.standard_normal((N_TRIALS, N_DAYS))
t_obs = pnl.mean(1) / pnl.std(1, ddof=1) * np.sqrt(N_DAYS)
k_best = int(t_obs.argmax())
# permutation of the max statistic: sign-flip days (preserves cross-parameter dependence)
B = 1000
max_null = np.empty(B)
for b in range(B):
    s = rng.choice([-1.0, 1.0], size=N_DAYS)
    tb = (pnl * s).mean(1) / (pnl * s).std(1, ddof=1) * np.sqrt(N_DAYS)
    max_null[b] = tb.max()
print(f"\nOne realized search: best params #{k_best} t={t_obs[k_best]:.2f}, naive p={p_one_sided(t_obs[k_best]):.1e}")
print(f"  reality-check p (max-of-N sign-flip null) = {np.mean(max_null >= t_obs[k_best]):.3f}")
print(f"  preselected rule #0 t={t_obs[0]:.2f}, naive p={p_one_sided(t_obs[0]):.2f}; its pct in max-of-N null = {np.mean(max_null < t_obs[0]):.2f}")

# ---------- 2. Same-bar stop/target ambiguity ----------
print("\n=== SYNTHETIC same-bar stop/target: 1-min GBM bars, 1R stop, 1.5R target, 60-bar horizon ===")
def one_trade(path, stop, tgt):
    """returns (conservative, optimistic, truth) R outcomes using 1-min OHLC built from 5-s ticks."""
    bars = path.reshape(-1, 12)
    for bar in bars:
        hi, lo = bar.max(), bar.min()
        hit_s, hit_t = lo <= -stop, hi >= tgt
        if hit_s and hit_t:
            # truth from 5-s ticks
            i_s = np.argmax(bar <= -stop); i_t = np.argmax(bar >= tgt)
            truth = -stop if i_s < i_t else tgt
            return -stop, tgt, truth
        if hit_s: return -stop, -stop, -stop
        if hit_t: return tgt, tgt, tgt
    return (path[-1],) * 3
sd_tick = 0.35  # R per 5s step chosen so both touched in same minute happens a few % of trades
cons, opt, tru = [], [], []
for _ in range(20000):
    path = np.cumsum(rng.standard_normal(60 * 12) * sd_tick)
    c, o, t = one_trade(path, 1.0, 1.5)
    cons.append(c); opt.append(o); tru.append(t)
cons, opt, tru = map(np.array, (cons, opt, tru))
amb = (cons != opt).mean()
print(f"ambiguous bars: {amb*100:.1f}% of trades")
print(f"mean R/trade  conservative={cons.mean():+.3f}  tick-truth={tru.mean():+.3f}  optimistic={opt.mean():+.3f}")
print(f"spread optimistic-conservative = {opt.mean()-cons.mean():+.3f} R/trade  (a 'edge' of this size is pure fill assumption)")

# ---------- 3. Overlapping forward-return labels ----------
print("\n=== SYNTHETIC overlapping labels: 30-bar forward return, signal every bar, 5000 bars ===")
r = rng.standard_normal(5000)
px = np.cumsum(r)
H = 30
fwd = px[H:] - px[:-H]
sig = rng.standard_normal(len(fwd))  # pure-noise signal
corr = np.corrcoef(sig, fwd)[0, 1]
n_naive = len(fwd); n_eff = n_naive / H
print(f"corr(signal,fwd)={corr:+.3f}; naive t={corr*np.sqrt(n_naive):+.2f}; overlap-adjusted t={corr*np.sqrt(n_eff):+.2f}")
# empirical: fraction of noise signals that look 'significant' under naive n
hits = 0
for _ in range(500):
    s = rng.standard_normal(len(fwd)); c = np.corrcoef(s, fwd)[0, 1]
    hits += abs(c * np.sqrt(n_naive)) > 1.96
print(f"noise signals called significant at naive n: {hits/500:.2f} (nominal 0.05)")
