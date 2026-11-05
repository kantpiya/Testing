"""SYNTHETIC EXAMPLE (B4). No real data. All prices/betas are placeholders.
Book: 1 MES long + 1 MNQ long (slot A). Candidate: second MNQ long (slot B).
Computes: $ exposure per 1% move, beta/correlation-adjusted exposure,
loss clustering vs independence, joint stop-outs, marginal contribution
on a FIXED worst-10% day set, and a pyramiding metric pair."""
import numpy as np
rng = np.random.default_rng(7)

# ---- 1. Static exposure ------------------------------------------------------
NQ, ES = 20000.0, 5500.0          # placeholder index levels
MNQ_MULT, MES_MULT = 2.0, 5.0     # $/point (public; verify vs CME)
BETA_ES_ON_NQ = 0.75              # pct-return beta, "estimated on prior sessions" (placeholder)
mnq_1pct = MNQ_MULT * NQ * 0.01   # $ per 1% NQ move, 1 contract
mes_1pct = MES_MULT * ES * 0.01   # $ per 1% ES move, 1 contract
mes_nq_equiv = mes_1pct * BETA_ES_ON_NQ
base = mnq_1pct + mes_nq_equiv
print("== Static exposure ($ per 1% index move) ==")
print(f"1 MNQ: ${mnq_1pct:.0f}/1% NQ   1 MES: ${mes_1pct:.0f}/1% ES  -> NQ-equiv ${mes_nq_equiv:.0f}")
print(f"Baseline book NQ-equiv delta: ${base:.0f}/1%   with slot B: ${base+mnq_1pct:.0f}/1%  (+{100*mnq_1pct/base:.0f}%)")

# ---- 2. Session simulation ---------------------------------------------------
N = 4000
m = rng.standard_t(4, N) * 0.8                     # common intraday NQ move, % (fat-tailed)
es_move = BETA_ES_ON_NQ * m + rng.normal(0, 0.35, N)
corr_es_nq = np.corrcoef(m, es_move)[0, 1]
# slot P&L = exposure * (load*factor + alpha + noise), floored at -stop (stop-out)
def slot(exposure, factor, load, alpha, noise_sd, stop):
    raw = exposure * (load * factor + alpha + rng.normal(0, noise_sd, N))
    return np.maximum(raw, -stop), raw <= -stop
MES_pl, MES_stop = slot(mes_1pct, es_move, 0.6, 0.04, 0.5, 150)
A_pl,   A_stop   = slot(mnq_1pct, m,       0.6, 0.04, 0.5, 200)
B_pl,   B_stop   = slot(mnq_1pct, m,       0.6, 0.04, 0.5, 200)   # same-direction MNQ long
C_pl,   C_stop   = slot(mnq_1pct, m,      -0.3, 0.04, 0.6, 200)   # contrast: counter-factor slot
print(f"\nSYNTHETIC corr(ES,NQ moves)={corr_es_nq:.2f}; corr(A,B)={np.corrcoef(A_pl,B_pl)[0,1]:.2f}; corr(A,C)={np.corrcoef(A_pl,C_pl)[0,1]:.2f}")

# correlation-adjusted exposure: portfolio sd vs sum of sds
def sd_ratio(parts):
    return np.std(sum(parts)) / sum(np.std(p) for p in parts)
print(f"Diversification ratio (sd(book)/sum sd): base={sd_ratio([MES_pl,A_pl]):.2f}  +B={sd_ratio([MES_pl,A_pl,B_pl]):.2f}  +C={sd_ratio([MES_pl,A_pl,C_pl]):.2f}")

# ---- 3. Loss clustering & joint stop-outs ------------------------------------
loss = np.c_[MES_pl < 0, A_pl < 0, B_pl < 0]
p = loss.mean(0)
obs2 = (loss.sum(1) >= 2).mean()
# expected P(>=2 of 3) under independence
q = 1 - p
exp2 = 1 - (q[0]*q[1]*q[2] + p[0]*q[1]*q[2] + q[0]*p[1]*q[2] + q[0]*q[1]*p[2])
obs3, exp3 = (loss.sum(1) == 3).mean(), p.prod()
cnt = loss.sum(1)
print(f"\nLoss clustering: marginal P(loss)={np.round(p,2)}; P(>=2 losing) obs={obs2:.3f} vs indep={exp2:.3f}; "
      f"P(all 3 lose) obs={obs3:.3f} vs indep={exp3:.3f} ratio={obs3/exp3:.2f}; "
      f"var(#losing) obs={cnt.var():.2f} vs indep={(p*q).sum():.2f}")
print(f"Joint stop-out: P(B stop | A stop)={B_stop[A_stop].mean():.2f} vs P(B stop)={B_stop.mean():.2f}; "
      f"P(C stop | A stop)={C_stop[A_stop].mean():.2f} vs P(C stop)={C_stop.mean():.2f}")

# ---- 4. Marginal contribution on FIXED worst-10% days ------------------------
basepl = MES_pl + A_pl
worst = basepl <= np.quantile(basepl, 0.10)        # FIXED day set from baseline
def summarize(name, pl):
    w = pl[worst]
    return f"{name:<14} all-day mean={pl.mean():7.1f}  worst10% mean={w.mean():8.1f}  worst10% p5={np.quantile(w,0.05):8.1f}  CVaR10(own)={pl[pl<=np.quantile(pl,0.1)].mean():8.1f}"
print("\nMarginal contribution (same fixed worst-10% baseline days):")
print(summarize("baseline", basepl))
print(summarize("baseline+B", basepl + B_pl))
print(summarize("baseline+C", basepl + C_pl))
print(f"Slot B alone on those days: mean={B_pl[worst].mean():.1f}; slot C alone: mean={C_pl[worst].mean():.1f}")

# ---- 5. Pyramiding metric pair ------------------------------------------------
# trade paths: 120 one-minute steps, drift+noise in R units; trailing stop d; optional add at +1R
def run(d, pyramid, T=120, n=6000):
    steps = rng.normal(0.02, 0.25, (n, T)).cumsum(1)
    out = []
    for path in steps:
        # potential MFE: 1 unit, initial -1R stop only, no trail (the "large winner" that exists to be retained)
        dead = np.argmax(path <= -1.0) if (path <= -1.0).any() else T
        pot = max(0.0, path[:dead].max()) if dead > 0 else 0.0
        realized, added, hi = None, False, 0.0
        for t, x in enumerate(path):
            pl = x if not added else x + (x - add_px)   # 2 units after add
            hi = max(hi, pl)
            if pyramid and not added and x >= 1.0:
                added, add_px = True, x
            if pl <= -1.0 or (hi > 0 and hi - pl >= d):
                realized = pl; break
        if realized is None: realized = pl
        out.append((pot, hi, realized))
    pot, hi, re = np.array(out).T
    big = pot >= 3.0
    captured_big = np.mean(re[big] / pot[big]) if big.any() else np.nan   # realized / potential MFE on big-run trades
    gaveback = np.mean(re[hi >= 1.0] <= 0)         # went >=1R green (open), closed flat/red
    return captured_big, gaveback, re.mean()
print("\nPyramiding metric pair (R units):")
print(f"{'trail d':>8} {'pyramid':>8} {'captured-MFE(>=3R)':>19} {'give-back frac(>=1R->0)':>24} {'mean R':>7}")
for d in (0.5, 1.0, 2.0):
    for pyr in (False, True):
        c, g, mu = run(d, pyr)
        print(f"{d:>8.1f} {str(pyr):>8} {c:>19.2f} {g:>24.2f} {mu:>7.2f}")
