#!/usr/bin/env python3
"""Reviewer A (methods) - independent spot checks on data/synthetic/ used in reports/reviewer_A_methods.md.
Everything printed is SYNTHETIC. Run from the panel folder: python3 src/reviewerA/checks.py
1. Timestamp integrity: entry/exit on MNQ bar opens, fills.ts_utc -> ET agrees, DST offsets present.
2. Stall cell rebuilt from the brief's definition (MFE touched >= +0.8R, then a bar CLOSE <= +0.3R, trade open under P0).
3. Paired SDs backed out of the reported session-bootstrap CIs and the minimum detectable effect by n.
"""
import numpy as np, pandas as pd
from scipy import stats

D = "data/synthetic/"
t = pd.read_csv(D + "trades.csv"); f = pd.read_csv(D + "fills.csv"); b = pd.read_csv(D + "bars_MNQ_1min.csv")
b["ts"] = pd.to_datetime(b["ts"], utc=True).dt.tz_convert("America/New_York")
opens = set(b["ts"])
for c in ("entry_ts", "exit_ts"):
    t[c[:-3]] = pd.to_datetime(t[c], utc=True).dt.tz_convert("America/New_York")
print("entry_ts on MNQ bar open:", t["entry"].isin(opens).sum(), "/", len(t))
print("exit_ts  on MNQ bar open:", t["exit"].isin(opens).sum(), "/", len(t))
print("ET offsets in entry_ts:", t["entry_ts"].str[-6:].value_counts().to_dict())
f["ts"] = pd.to_datetime(f["ts_utc"], utc=True).dt.tz_convert("America/New_York")
ent = f[f.fill_role == "ENTRY"].set_index("trade_id")["ts"].reindex(t.trade_id).values
ex = f[f.fill_role == "EXIT"].groupby("trade_id")["ts"].max().reindex(t.trade_id).values
print("fills ENTRY (UTC->ET) == entry_ts:", (ent == t["entry"].values).sum(), "/", len(t))
print("fills last EXIT (UTC->ET) == exit_ts:", (ex == t["exit"].values).sum(), "/", len(t))
print("sessions with >1 KX trade:", (t[t.family == "KX"].groupby("session").size() > 1).sum(),
      "| sessions with >1 trade (any family):", (t.groupby("session").size() > 1).sum())

# ---- stall cell, independent rebuild
b = b.sort_values("ts").reset_index(drop=True); bidx = {ts: i for i, ts in enumerate(b["ts"])}
rows = []
for r in t[t.family == "KX"].itertuples():
    d = 1 if r.direction == "LONG" else -1
    sd = abs(r.entry_px - r.initial_stop_px); i0, i1 = bidx[r.entry], bidx[r.exit]
    mfe, k_st = -9.0, None
    for k in range(1, i1 - i0):                      # bars after the entry bar, trade still open (exit bar excluded)
        bar = b.iloc[i0 + k]
        mfe = max(mfe, d * ((bar.high if d == 1 else bar.low) - r.entry_px) / sd)
        if mfe >= 0.8 and d * (bar.close - r.entry_px) / sd <= 0.3:
            k_st = k; break
    rows.append((r.trade_id, r.strategy, r.exit_reason, k_st, r.net_pnl_usd / r.planned_risk_usd))
s = pd.DataFrame(rows, columns=["trade_id", "strategy", "exit_reason", "k", "R"]); st = s[s.k.notna()]
print(f"stall cell: n={len(st)} {st.strategy.value_counts().to_dict()} exits {st.exit_reason.value_counts().to_dict()} "
      f"mean R {st.R.mean():+.3f} median {st.R.median():+.3f} decision minute median {st.k.median():.0f}")

# ---- uncertainty arithmetic (SYNTHETIC CIs from the director's cross-checks)
se = lambda lo, hi: (hi - lo) / (2 * 1.96)
for name, (n, lo, hi) in {"dev C1 stall n=60": (60, -0.82, 0.10), "dev C1 v1 n=41": (41, -1.09, -0.07),
                          "dev C1 v2 n=19": (19, -0.69, 0.91), "holdout C1 n=13": (13, -0.53, 1.13),
                          "holdout D3 n=13": (13, -1.23, 1.29), "S1 min10 exit n=158": (158, -0.84, -0.37)}.items():
    print(f"{name}: SE {se(lo, hi):.2f}R, implied paired SD {se(lo, hi) * np.sqrt(n):.2f}R")
z = stats.norm.ppf(0.975) + stats.norm.ppf(0.8)
for sd in (1.5, 1.8):
    print(f"SD {sd}R: MDE(80% power, 5% two-sided) " + ", ".join(f"n={n}: {z * sd / np.sqrt(n):.2f}R" for n in (13, 40, 100, 280)))
    print(f"SD {sd}R: n for 0.5R = {(z * sd / 0.5) ** 2:.0f}, for 0.3R = {(z * sd / 0.3) ** 2:.0f} stall trades "
          f"(x4 for KX trades at a 25% stall rate)")
