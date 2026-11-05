"""
SYNTHETIC EXAMPLE (A6). Does ES-NQ divergence ("SMT") add information for MNQ
after controlling for NQ momentum, volatility and time of day?

Simulated 1-min RTH bars (390/session) for NQ and ES. ES = beta*NQ + idio.
Forward MNQ return (h bars) = a*NQ_mom + GAMMA*ES_residual + noise.
GAMMA>0  -> ES carries a small incremental signal (should be recovered).
GAMMA=0  -> null (should NOT be recovered).

Nested models, session-clustered errors, and session-blocked out-of-sample
incremental R^2. Beta for the residual is estimated on PRIOR sessions only.
Run:  python3 -I smt_nested_test.py
"""
import numpy as np, pandas as pd, statsmodels.api as sm

rng = np.random.default_rng(7)
S, N, K, H = 150, 390, 10, 5            # sessions, bars/session, lookback, horizon
BETA_TRUE = 0.85                         # ES ret per unit NQ ret (ES less volatile)

def simulate(gamma, stale_frac=0.0):
    rows = []
    tod = np.arange(N)
    volprof = 1.0 + 0.8*np.exp(-tod/40) + 0.6*np.exp(-(N-1-tod)/40)   # U-shape
    for s in range(S):
        sv = 0.0004 * np.exp(rng.normal(0, 0.3))                        # session vol level
        nq = rng.normal(0, sv*volprof)                                  # NQ 1-min log ret
        es = BETA_TRUE*nq + rng.normal(0, 0.45*sv*volprof)              # ES: beta*NQ + idio
        ts = pd.Timestamp("2026-01-05 09:30") + pd.Timedelta(days=s) + pd.to_timedelta(tod, "min")
        # last-print age (seconds since bar close) -- stale-data simulation on ES leg
        age_es = np.where(rng.random(N) < stale_frac, rng.integers(60, 300, N), rng.integers(0, 3, N))
        rows.append(pd.DataFrame(dict(session=s, ts=ts, tod=tod, r_nq=nq, r_es=es, age_es=age_es)))
    return pd.concat(rows, ignore_index=True), gamma

def features(df, gamma, h=H, k=K):
    df = df.copy()
    g = df.groupby("session")
    df["mom_nq"] = g["r_nq"].transform(lambda x: x.rolling(k).sum())
    df["mom_es"] = g["r_es"].transform(lambda x: x.rolling(k).sum())
    df["vol_nq"] = g["r_nq"].transform(lambda x: x.rolling(20).std())
    # Walk-forward beta: OLS of ES on NQ k-bar returns using ONLY sessions < s
    beta = {}
    cum_xy = cum_xx = 0.0
    for s, grp in df.groupby("session"):
        beta[s] = cum_xy/cum_xx if cum_xx > 0 else np.nan
        v = grp[["mom_es", "mom_nq"]].dropna()
        cum_xy += (v.mom_es*v.mom_nq).sum(); cum_xx += (v.mom_nq**2).sum()
    df["beta_prior"] = df["session"].map(beta)
    # Magnitude: ES k-bar return minus beta_prior * NQ k-bar return (in NQ-return units)
    df["smt_mag"] = df["mom_es"] - df["beta_prior"]*df["mom_nq"]
    # Direction: sign agreement over k bars (+1 agree / -1 diverge), HH/LH style
    hi_nq = g["r_nq"].transform(lambda x: x.rolling(k).sum() > 0)
    hi_es = g["r_es"].transform(lambda x: x.rolling(k).sum() > 0)
    df["smt_dir"] = np.where(hi_nq == hi_es, 1.0, -1.0)
    # signed divergence: -1 if NQ up but ES not (bearish), +1 if NQ down but ES not (bullish), 0 agree
    df["smt_dir_signed"] = np.where(hi_nq == hi_es, 0.0, np.where(hi_nq, -1.0, 1.0))
    # Forward MNQ return: NQ path + gamma * (true ES idio innovation) -- MNQ tracks NQ
    fwd_nq = g["r_nq"].transform(lambda x: x[::-1].rolling(h).sum()[::-1].shift(-1))
    idio = df["r_es"] - BETA_TRUE*df["r_nq"]
    idio_k = idio.groupby(df["session"]).transform(lambda x: x.rolling(k).sum())
    noise = rng.normal(0, 1.0, len(df)) * df["vol_nq"].fillna(0)*np.sqrt(h)
    df["y"] = fwd_nq + gamma*idio_k + 0.0*noise      # fwd_nq already noisy; gamma injects ES info
    df["tod_bin"] = (df["tod"]//30).astype(int)
    df = df.dropna()
    df = df[df["tod"] % h == 0]                     # non-overlapping forward windows
    return df

def design(df, extra):
    X = pd.get_dummies(df["tod_bin"], prefix="tod", drop_first=True, dtype=float)
    X["mom_nq"] = df["mom_nq"]; X["vol_nq"] = df["vol_nq"]
    X["mom_x_vol"] = df["mom_nq"]*df["vol_nq"]
    for c in extra: X[c] = df[c]
    return sm.add_constant(X)

def fit(df, extra):
    m = sm.OLS(df["y"], design(df, extra)).fit(cov_type="cluster", cov_kwds={"groups": df["session"]})
    return m

def oos_r2(df, extra, min_train=40):
    """Session-blocked expanding-window OOS: fit on sessions < s, predict session s."""
    sse_m = sse_0 = sst = 0.0
    for s in range(min_train, S):
        tr, te = df[df.session < s], df[df.session == s]
        m0 = sm.OLS(tr["y"], design(tr, [])).fit(); m1 = sm.OLS(tr["y"], design(tr, extra)).fit()
        p0 = m0.predict(design(te, [])); p1 = m1.predict(design(te, extra))
        sse_0 += ((te.y-p0)**2).sum(); sse_m += ((te.y-p1)**2).sum(); sst += ((te.y-tr.y.mean())**2).sum()
    return 1-sse_0/sst, 1-sse_m/sst, (sse_0-sse_m)/sst

def run(label, gamma):
    df = features(*simulate(gamma))
    print(f"\n=== {label}: gamma={gamma}, n={len(df)}, sessions={df.session.nunique()} ===")
    base = fit(df, [])
    for name, extra in [("direction", ["smt_dir_signed"]), ("magnitude", ["smt_mag"]),
                        ("both", ["smt_dir_signed", "smt_mag"])]:
        m = fit(df, extra)
        w = m.wald_test(np.array([[1.0 if c == e else 0.0 for c in m.params.index] for e in extra]), scalar=True)
        r0, r1, dr = oos_r2(df, extra)
        coefs = ", ".join(f"{e}={m.params[e]:+.3g} (t={m.tvalues[e]:+.2f})" for e in extra)
        print(f"  +{name:9s} | cluster-Wald p={w.pvalue:.4f} | in-sample dR2={m.rsquared-base.rsquared:+.4f} "
              f"| OOS R2 base={r0:+.4f} model={r1:+.4f} dR2={dr:+.4f} | {coefs}")
    # Near-duplicate check: correlation of ES vs NQ forward returns by horizon
    return df

def dup_check():
    df, _ = simulate(0.0)
    print("\n=== MES/MNQ near-duplicate check (ES vs NQ return corr & sign agreement by horizon) ===")
    for h in [1, 5, 15, 30, 60]:
        a = df.groupby("session")["r_nq"].transform(lambda x: x.rolling(h).sum())
        b = df.groupby("session")["r_es"].transform(lambda x: x.rolling(h).sum())
        ok = a.notna() & b.notna() & (df.tod % h == 0)
        rho = np.corrcoef(a[ok], b[ok])[0, 1]; agree = (np.sign(a[ok]) == np.sign(b[ok])).mean()
        print(f"  h={h:3d} bars: corr={rho:.3f}  sign-agree={agree:.3f}  "
              f"var-reduction of long-MNQ/short-beta*MES vs long-MNQ = {1-(1-rho**2):.3f}")

def stale_check():
    df, _ = simulate(0.0, stale_frac=0.05)
    df["stale"] = df["age_es"] > 30
    print(f"\n=== Stale-data check: ES prints older than 30s on {df.stale.mean():.1%} of bars (synthetic) ===")
    print("  Rule: compute age = bar_close_ts - last_trade_ts per leg; if |age_ES - age_NQ| > 30s or either > 30s,")
    print("  set smt_* = NaN for that bar (do not carry forward the stale leg) and exclude from the fit.")

if __name__ == "__main__":
    import sys
    g = float(sys.argv[1]) if len(sys.argv) > 1 else 0.15
    run("SIGNAL CASE", gamma=g)
    run("NULL CASE", gamma=0.0)
    dup_check(); stale_check()
