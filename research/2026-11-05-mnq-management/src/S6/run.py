"""
S6 Skeptical portfolio manager -- regenerates every table in reports/S6_skeptic.md
from data/synthetic/.  Everything computed here is SYNTHETIC.

    python3 src/S6/run.py            # full run (~2-3 min)

Sections:
  0. engine validation vs journal
  1. policy grid (Stage A, paired, entries fixed)        -> pick the strongest
  2. battery (a) session concentration, LOSO, session bootstrap
  3. battery (b) parameter neighbourhood
  4. battery (c) fills: extra slippage, same-bar ordering, touch-vs-through stops
  5. battery (d) strategy version / family
  6. battery (e) Stage B chronological replay with the 4-contract limit
  7. battery (f) drawdown and worst session
"""
import os
import sys
import json
import itertools
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from replay import (SessionBars, load_bars, load_trades, replay_all, replay_trade, rt, TICK,  # noqa: E402
                    COMM, PT_VALUE)
from stageb import stage_b  # noqa: E402

DATA = os.path.join(ROOT, "data", "synthetic")
CHARTS = os.path.join(ROOT, "charts")
OUT = {}  # everything printed is also stored here and dumped to src/S6/output.json

rng = np.random.default_rng(20261105)


def say(*a):
    print(*a)


def hdr(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


# -----------------------------------------------------------------------------
# data
# -----------------------------------------------------------------------------
bars = load_bars(os.path.join(DATA, "bars_MNQ_1min.csv"))
sb = SessionBars(bars)
trades = load_trades(os.path.join(DATA, "trades.csv"))
signals = pd.read_csv(os.path.join(DATA, "signals.csv"))
signals["signal_ts"] = pd.to_datetime(signals["signal_ts"], utc=True).dt.tz_convert("America/New_York")
N_TRADES = len(trades)
N_SESS = trades["session"].nunique()

# -----------------------------------------------------------------------------
# 0. validation
# -----------------------------------------------------------------------------
hdr("0. ENGINE VALIDATION vs trades.csv (original policy, S6 engine) -- SYNTHETIC")
base = replay_all(trades, sb, {})
m = trades.merge(base, on="trade_id", suffixes=("", "_r"))
nm = m[m["exit_reason"] != "MANUAL"]
val = dict(
    n_trades=int(N_TRADES), n_sessions=int(N_SESS), n_manual=int((m["exit_reason"] == "MANUAL").sum()),
    exit_ts_match=float((nm["exit_ts"] == nm["exit_ts_r"]).mean()),
    exit_px_match=float((np.abs(nm["exit_px"] - nm["exit_px_r"]) < 1e-9).mean()),
    net_match_1c=float((np.abs(nm["net_pnl_usd"] - nm["net"]) < 0.01).mean()),
    add_match=float(((nm["added_contracts"] > 0) == (nm["add"] == 1)).mean()),
    journal_net_nonmanual=float(nm["net_pnl_usd"].sum()), replay_net_nonmanual=float(nm["net"].sum()),
    journal_net_all=float(m["net_pnl_usd"].sum()), replay_net_all=float(m["net"].sum()),
    journal_manual_net=float(m.loc[m["exit_reason"] == "MANUAL", "net_pnl_usd"].sum()),
    replay_manual_mech_net=float(m.loc[m["exit_reason"] == "MANUAL", "net"].sum()),
)
for k, v in val.items():
    say(f"  {k:28s} {v:,.4f}" if isinstance(v, float) else f"  {k:28s} {v}")
OUT["validation"] = val

# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------
def paired(alt, base=base):
    """Paired per-trade differences alt - base (USD and R), plus session sums."""
    d = base[["trade_id", "session", "strategy", "family"]].copy()
    d["base_usd"] = base["net"].values
    d["alt_usd"] = alt["net"].values
    d["base_R"] = base["net_R"].values
    d["alt_R"] = alt["net_R"].values
    d["d_usd"] = d["alt_usd"] - d["base_usd"]
    d["d_R"] = d["alt_R"] - d["base_R"]
    d["changed"] = (np.abs(d["d_usd"]) > 1e-9)
    return d


def summarize(d, label=""):
    s = d.groupby("session")["d_usd"].sum()
    changed = d[d["changed"]]
    return dict(
        label=label, n_trades=int(len(d)), n_sessions=int(d["session"].nunique()),
        n_changed_trades=int(len(changed)), n_changed_sessions=int(changed["session"].nunique()),
        sum_d_usd=float(d["d_usd"].sum()), mean_d_usd=float(d["d_usd"].mean()),
        sum_d_R=float(d["d_R"].sum()), mean_d_R=float(d["d_R"].mean()),
        alt_total_usd=float(d["alt_usd"].sum()), base_total_usd=float(d["base_usd"].sum()),
        pct_sessions_pos=float((s > 0).mean()), pct_sessions_neg=float((s < 0).mean()),
        median_d_session=float(s.median()),
    )


def session_bootstrap(d, n=2000, seed=1):
    """Resample whole sessions with replacement; return mean per-session benefit CI and P(sum<=0)."""
    s = d.groupby("session")["d_usd"].sum().values
    k = len(s)
    r = np.random.default_rng(seed)
    idx = r.integers(0, k, size=(n, k))
    sums = s[idx].sum(axis=1)
    return dict(boot_draws=n, n_sessions=k, mean_sum=float(sums.mean()), ci05=float(np.percentile(sums, 5)),
                ci95=float(np.percentile(sums, 95)), ci2_5=float(np.percentile(sums, 2.5)),
                ci97_5=float(np.percentile(sums, 97.5)), p_sum_le_0=float((sums <= 0).mean()))


def dd_stats(pnl_by_trade_order):
    c = np.cumsum(pnl_by_trade_order)
    peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]
    dd = c - peak
    return float(dd.min()), float(c[-1])


# -----------------------------------------------------------------------------
# 1. policy grid
# -----------------------------------------------------------------------------
hdr("1. POLICY GRID -- Stage A paired replay, entries fixed, S6 engine, SYNTHETIC, costs included")
grid = []
# (family label, dict policy)
for T in (10, 15, 20, 30, 45, 60, 90):
    grid.append((f"time_exit T={T}", dict(time_exit_min=T)))
for T, X in itertools.product((5, 10, 15, 20, 30), (0.2, 0.3, 0.5)):
    grid.append((f"noprog T={T} X={X}", dict(noprog_min=T, noprog_R=X)))
for Y, L in itertools.product((0.5, 0.6, 0.8, 1.0, 1.2), (0.0, 0.1, 0.3)):
    grid.append((f"breakeven Y={Y} lock={L}", dict(be_trigger_R=Y, be_lock_R=L)))
for Y, Z in itertools.product((0.5, 0.8, 1.0), (0.3, 0.5, 0.8)):
    grid.append((f"trail Y={Y} dist={Z}", dict(trail_trigger_R=Y, trail_dist_R=Z)))
for mlt in (1.0, 1.5, 2.0, 3.0):
    grid.append((f"target_mult m={mlt}", dict(target_mult=mlt)))
for mlt in (3.0, 3.5, 4.0, 5.0, 6.0, None):
    grid.append((f"kx_target m={mlt}", dict(kx_target_mult=mlt)))
for mlt in (1.0, 1.5, 2.0, 3.0, None):
    grid.append((f"px_target m={mlt}", dict(px_target_mult=mlt)))
for cap in (1.0, 1.5, 2.0):
    grid.append((f"px_cap {cap}R", dict(px_cap_R=cap)))
for Y, Z in itertools.product((2.0, 2.5), (0.5, 1.0, 1.5)):
    grid.append((f"kx_notarget+trail Y={Y} dist={Z}", dict(kx_target_mult=None, trail_trigger_R=Y, trail_dist_R=Z)))
grid.append(("add_be", dict(add_be=True)))
grid.append(("add_trail 0.3", dict(add_trail_R=0.3)))
grid.append(("add_trail 0.5", dict(add_trail_R=0.5)))
grid.append(("no_add", dict(no_add=True)))

results = {}
rows = []
for label, pol in grid:
    alt = replay_all(trades, sb, pol)
    d = paired(alt)
    s = summarize(d, label)
    s["policy"] = json.dumps(pol)
    bs = session_bootstrap(d, n=1000, seed=7)
    s["boot_p_le_0"] = bs["p_sum_le_0"]
    s["boot_ci05"] = bs["ci05"]
    results[label] = (pol, alt, d)
    rows.append(s)
G = pd.DataFrame(rows)
G["sum_d_usd"] = G["sum_d_usd"].round(2)
G["mean_d_R"] = G["mean_d_R"].round(4)
cols = ["label", "n_changed_trades", "n_changed_sessions", "sum_d_usd", "mean_d_R", "pct_sessions_pos",
        "pct_sessions_neg", "boot_ci05", "boot_p_le_0"]
say(G.sort_values("sum_d_usd", ascending=False)[cols].to_string(index=False))
say(f"\n  grid cells examined in section 1: {len(grid)}")
OUT["grid"] = G.to_dict(orient="records")
OUT["grid_cells"] = len(grid)
G.to_csv(os.path.join(HERE, "grid.csv"), index=False)

best_label = G.sort_values("sum_d_usd", ascending=False)["label"].iloc[0]
best_pol, best_alt, best_d = results[best_label]
say(f"\n  STRONGEST on development data (by paired sum of net USD): {best_label}  policy={best_pol}")
OUT["best_label"] = best_label
OUT["best_policy"] = best_pol

if os.environ.get("S6_GRID_ONLY"):
    json.dump(OUT, open(os.path.join(HERE, "output.json"), "w"), indent=1, default=str)
    sys.exit(0)


# =============================================================================
# The policy under attack
# =============================================================================
hdr(f"POLICY UNDER ATTACK: {best_label}  {best_pol}")
B_POL = best_pol
B = best_alt
D = best_d
chg = D[D["changed"]]
say(f"  changed trades {len(chg)} in {chg['session'].nunique()} sessions; "
    f"paired sum ${D['d_usd'].sum():,.0f} ({D['d_R'].sum():.1f} R over {N_TRADES} trades / {N_SESS} sessions, costs incl.)")
say(f"  base total ${D['base_usd'].sum():,.0f}  alt total ${D['alt_usd'].sum():,.0f}")
# what happens to the changed trades
bb = base.set_index("trade_id").loc[chg["trade_id"]]
aa = B.set_index("trade_id").loc[chg["trade_id"]]
xt = pd.crosstab(bb["exit_reason"], aa["exit_reason"])
say("  exit reason, base (rows) -> alt (cols) among changed trades:\n" + xt.to_string())
say(f"  changed trades: d_usd mean {chg['d_usd'].mean():,.1f} median {chg['d_usd'].median():,.1f} "
    f"min {chg['d_usd'].min():,.1f} max {chg['d_usd'].max():,.1f}; share with d<0: {(chg['d_usd']<0).mean():.3f}")
say(f"  alt hold minutes among changed trades: mean {aa['hold_min'].mean():.0f}, base {bb['hold_min'].mean():.0f}")
# top-10% largest winners defined on baseline
thr = base["net_R"].quantile(0.9)
lw = base["net_R"] >= thr
say(f"  largest winners (top 10% baseline net R, n={int(lw.sum())}, thr {thr:.2f}R): base ${base.loc[lw,'net'].sum():,.0f} -> alt ${B.loc[lw.values,'net'].sum():,.0f}")
OUT["attack_summary"] = dict(changed=int(len(chg)), changed_sessions=int(chg["session"].nunique()),
                             sum_d=float(D["d_usd"].sum()), sum_dR=float(D["d_R"].sum()),
                             share_neg=float((chg["d_usd"] < 0).mean()), crosstab=xt.to_dict())

# post-target continuation (the mechanism): for base TARGET exits of KX, where is price at 15:55?
hdr("MECHANISM CHECK: KX trades that hit the ORIGINAL target -- MNQ price at 15:55 open relative to target (R units)")
rows = []
for _, tr in trades.iterrows():
    b0 = base[base["trade_id"] == tr["trade_id"]].iloc[0]
    if tr["family"] != "KX" or b0["exit_reason"] != "TARGET":
        continue
    S = sb.get(tr["session"])
    d = 1.0 if tr["direction"] == "LONG" else -1.0
    R_pts = abs(tr["entry_px"] - tr["initial_stop_px"])
    eod_i = next(i for i in range(len(S["o"])) if S["ts_list"][i].time() >= pd.Timestamp("15:55").time())
    cont = d * (S["o"][eod_i] - b0["exit_px"]) / R_pts
    rows.append(dict(trade_id=tr["trade_id"], session=tr["session"], strategy=tr["strategy"], cont_R=cont))
C = pd.DataFrame(rows)
say(f"  n={len(C)} target-hit KX trades in {C['session'].nunique()} sessions: mean continuation {C['cont_R'].mean():.2f} R, "
    f"median {C['cont_R'].median():.2f} R, SD {C['cont_R'].std():.2f} R, share >0: {(C['cont_R']>0).mean():.2f}")
say(C.groupby("strategy")["cont_R"].agg(["count", "mean", "median", "std"]).round(2).to_string())
OUT["continuation"] = dict(n=int(len(C)), mean=float(C["cont_R"].mean()), sd=float(C["cont_R"].std()),
                           share_pos=float((C["cont_R"] > 0).mean()))
# same for PX
rows = []
for _, tr in trades.iterrows():
    b0 = base[base["trade_id"] == tr["trade_id"]].iloc[0]
    if tr["family"] != "PX" or b0["exit_reason"] != "TARGET":
        continue
    S = sb.get(tr["session"])
    d = 1.0 if tr["direction"] == "LONG" else -1.0
    R_pts = abs(tr["entry_px"] - tr["initial_stop_px"])
    eod_i = next(i for i in range(len(S["o"])) if S["ts_list"][i].time() >= pd.Timestamp("15:55").time())
    rows.append(d * (S["o"][eod_i] - b0["exit_px"]) / R_pts)
say(f"  PX target-hit trades n={len(rows)}: mean continuation {np.mean(rows):.2f} R, SD {np.std(rows, ddof=1):.2f} R")
OUT["continuation_px"] = dict(n=len(rows), mean=float(np.mean(rows)), sd=float(np.std(rows, ddof=1)))

# =============================================================================
# (a) session concentration
# =============================================================================
hdr("(a) SESSION CONCENTRATION -- SYNTHETIC")
s_ben = D.groupby("session")["d_usd"].sum().sort_values(ascending=False)
tot = s_ben.sum()
a_res = {}
for k in (1, 3, 5, 10):
    rem = tot - s_ben.iloc[:k].sum()
    a_res[f"remove_top_{k}"] = dict(remaining_usd=float(rem), fraction=float(rem / tot))
    say(f"  remove top {k:2d} sessions by benefit: remaining ${rem:,.0f} = {rem/tot:.1%} of total")
say(f"  top 1 session {s_ben.index[0]} ${s_ben.iloc[0]:,.0f}; top-5 sessions sum ${s_ben.iloc[:5].sum():,.0f} ({s_ben.iloc[:5].sum()/tot:.1%})")
say(f"  sessions with benefit>0: {(s_ben>0).sum()}, <0: {(s_ben<0).sum()}, =0: {(s_ben==0).sum()} of {len(s_ben)}")
# how many sessions needed to reach 50% of the benefit
cs = s_ben[s_ben > 0].cumsum()
n50 = int((cs < 0.5 * tot).sum() + 1)
say(f"  sessions needed to reach 50% of the benefit: {n50} (of {int((s_ben>0).sum())} positive sessions)")
loso = np.array([tot - v for v in s_ben.values])
say(f"  leave-one-session-out: min ${loso.min():,.0f} max ${loso.max():,.0f} (all >0: {bool((loso>0).all())})")
bs = session_bootstrap(D, n=2000, seed=11)
say(f"  session bootstrap {bs['boot_draws']} draws: sum mean ${bs['mean_sum']:,.0f}, 90% CI [{bs['ci05']:,.0f}, {bs['ci95']:,.0f}], "
    f"95% CI [{bs['ci2_5']:,.0f}, {bs['ci97_5']:,.0f}], P(sum<=0)={bs['p_sum_le_0']:.4f}")
# trade-level concentration: top 10% of changed trades by d
cd = chg["d_usd"].sort_values(ascending=False)
k10 = max(1, int(np.ceil(0.1 * len(cd))))
say(f"  top 10% of changed trades (n={k10}) carry ${cd.iloc[:k10].sum():,.0f} = {cd.iloc[:k10].sum()/tot:.1%} of the benefit")
a_res.update(n50=n50, loso_min=float(loso.min()), loso_max=float(loso.max()), boot=bs,
             top10pct_trades_share=float(cd.iloc[:k10].sum() / tot))
OUT["a"] = a_res

# =============================================================================
# (b) parameter neighbourhood
# =============================================================================
hdr("(b) PARAMETER NEIGHBOURHOOD of the policy under attack -- SYNTHETIC")
nb = []
if "kx_target_mult" in B_POL:
    for mlt in (2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, None):
        nb.append((f"KX target m={mlt}", dict(kx_target_mult=mlt)))
    for clk in ("12:00", "13:00", "14:00", "15:00", "15:30"):
        nb.append((f"KX no target, flat at {clk}", dict(kx_target_mult=None, time_exit_et=clk, family_filter="KX")))
    for Y, Z in itertools.product((2.0, 2.5, 3.0), (0.5, 1.0, 1.5, 2.0)):
        nb.append((f"KX no target + trail Y={Y} dist={Z}", dict(kx_target_mult=None, trail_trigger_R=Y, trail_dist_R=Z, family_filter="KX")))
    for Y, L in ((2.0, 0.0), (2.0, 1.0), (2.5, 1.0), (2.0, 1.5)):
        nb.append((f"KX no target + lock Y={Y} L={L}", dict(kx_target_mult=None, be_trigger_R=Y, be_lock_R=L, family_filter="KX")))
rows = []
nb_results = {}
for label, pol in nb:
    alt = replay_all(trades, sb, pol)
    d = paired(alt)
    s = summarize(d, label)
    bs = session_bootstrap(d, n=1000, seed=3)
    s["boot_ci05"] = bs["ci05"]
    s["boot_p_le_0"] = bs["p_sum_le_0"]
    rows.append(s)
    nb_results[label] = d
NB = pd.DataFrame(rows)
say(NB[["label", "n_changed_trades", "n_changed_sessions", "sum_d_usd", "mean_d_R", "pct_sessions_pos", "pct_sessions_neg", "boot_ci05", "boot_p_le_0"]].round(3).to_string(index=False))
say(f"  neighbourhood cells examined: {len(nb)}; sign positive in {(NB['sum_d_usd']>0).sum()} of {len(nb)}")
OUT["b"] = NB.to_dict(orient="records")
OUT["b_cells"] = len(nb)
NB.to_csv(os.path.join(HERE, "neighbourhood.csv"), index=False)

# =============================================================================
# (c) fills
# =============================================================================
hdr("(c) FILL ASSUMPTIONS -- extra slippage on every market/stop fill (both policies), same-bar ordering, stop touch vs through -- SYNTHETIC")
c_rows = []
for extra in (0, 1, 2):  # 1,2,3 ticks total
    for order in ("stop_first", "target_first"):
        for ss in (False, True):
            b2 = replay_all(trades, sb, {}, extra_slip_ticks=extra, order=order, strict_stop=ss)
            a2 = replay_all(trades, sb, B_POL, extra_slip_ticks=extra, order=order, strict_stop=ss)
            d2 = paired(a2, b2)
            bs = session_bootstrap(d2, n=1000, seed=5)
            c_rows.append(dict(total_slip_ticks=1 + extra, same_bar=order, stop_fill="through" if ss else "touch",
                               base_usd=round(b2["net"].sum(), 0), alt_usd=round(a2["net"].sum(), 0),
                               sum_d_usd=round(d2["d_usd"].sum(), 0), boot_ci05=round(bs["ci05"], 0), p_le_0=bs["p_sum_le_0"]))
CR = pd.DataFrame(c_rows)
say(CR.to_string(index=False))
OUT["c"] = CR.to_dict(orient="records")

# =============================================================================
# (d) strategy version / family
# =============================================================================
hdr("(d) STRATEGY VERSION and FAMILY -- SYNTHETIC")
d_rows = []
for strat, g in D.groupby("strategy"):
    bs = session_bootstrap(g, n=1000, seed=9)
    d_rows.append(dict(strategy=strat, n_trades=len(g), n_sessions=g["session"].nunique(), n_changed=int(g["changed"].sum()),
                       base_usd=round(g["base_usd"].sum(), 0), alt_usd=round(g["alt_usd"].sum(), 0),
                       sum_d_usd=round(g["d_usd"].sum(), 0), mean_d_R=round(g["d_R"].mean(), 3),
                       pct_sess_pos=round((g.groupby("session")["d_usd"].sum() > 0).mean(), 3),
                       boot_ci05=round(bs["ci05"], 0), p_le_0=bs["p_sum_le_0"]))
# PX analogue (no target, hold to EOD) for the family comparison
alt_px = replay_all(trades, sb, dict(px_target_mult=None))
d_px = paired(alt_px)
g = d_px[d_px["family"] == "PX"]
bs = session_bootstrap(g, n=1000, seed=9)
d_rows.append(dict(strategy="PX_REV_v1 (PX analogue: no target)", n_trades=len(g), n_sessions=g["session"].nunique(),
                   n_changed=int(g["changed"].sum()), base_usd=round(g["base_usd"].sum(), 0), alt_usd=round(g["alt_usd"].sum(), 0),
                   sum_d_usd=round(g["d_usd"].sum(), 0), mean_d_R=round(g["d_R"].mean(), 3),
                   pct_sess_pos=round((g.groupby("session")["d_usd"].sum() > 0).mean(), 3),
                   boot_ci05=round(bs["ci05"], 0), p_le_0=bs["p_sum_le_0"]))
DR = pd.DataFrame(d_rows)
say(DR.to_string(index=False))
# split by half-year within v1 to check time stability
D2 = D.copy()
D2["half"] = np.where(D2["session"] < "2025-08-01", "May-Jul25", np.where(D2["session"] < "2025-11-01", "Aug-Oct25",
                      np.where(D2["session"] < "2026-02-01", "Nov25-Jan26", "Feb-Apr26")))
say("\n  by quarter (all strategies):")
say(D2.groupby("half").agg(n=("d_usd", "size"), sessions=("session", "nunique"), changed=("changed", "sum"),
                            sum_d_usd=("d_usd", "sum")).round(0).to_string())
OUT["d"] = DR.to_dict(orient="records")
OUT["d_quarter"] = D2.groupby("half")["d_usd"].sum().round(0).to_dict()

# =============================================================================
# (e) Stage B
# =============================================================================
hdr("(e) STAGE B -- chronological replay, 4-contract limit, pyramiding, 15:55 cutoff, rejected signals eligible -- SYNTHETIC")
exB0, rjB0 = stage_b(signals, sb, {})
exB1, rjB1 = stage_b(signals, sb, B_POL)
jr = set(signals.loc[signals["executed"] == False, "signal_id"])
say(f"  journal: executed {int(signals['executed'].sum())}, rejected {len(jr)} -> {sorted(jr)}")
say(f"  Stage B original: executed {len(exB0)}, rejected {len(rjB0)} -> {sorted(rjB0['signal_id'])}; net ${exB0['net'].sum():,.0f}")
say(f"  Stage B alt     : executed {len(exB1)}, rejected {len(rjB1)} -> {sorted(rjB1['signal_id'])}; net ${exB1['net'].sum():,.0f}")
set0, set1 = set(exB0["trade_id"]), set(exB1["trade_id"])
blocked = sorted(set0 - set1)
freed = sorted(set1 - set0)
sig_ix = signals.set_index("signal_id")
say(f"  signals BLOCKED by the alternative (executed under original, rejected under alt): {len(blocked)} -> {blocked}")
if blocked:
    bl = exB0.set_index("trade_id").loc[blocked]
    say(f"     their net under the original Stage B: ${bl['net'].sum():,.0f}; strategies {sig_ix.loc[blocked,'strategy'].value_counts().to_dict()}")
say(f"  signals FREED by the alternative: {len(freed)} -> {freed}")
if freed:
    fr = exB1.set_index("trade_id").loc[freed]
    say(f"     their net under the alt Stage B: ${fr['net'].sum():,.0f}; strategies {sig_ix.loc[freed,'strategy'].value_counts().to_dict()}")
common = sorted(set0 & set1)
c0 = exB0.set_index("trade_id").loc[common, "net"]
c1 = exB1.set_index("trade_id").loc[common, "net"]
say(f"  common trades {len(common)}: original ${c0.sum():,.0f} -> alt ${c1.sum():,.0f} (diff ${c1.sum()-c0.sum():,.0f})")
say(f"  adds: original {int(exB0['add'].sum())}, alt {int(exB1['add'].sum())}")
say(f"  PORTFOLIO net: original ${exB0['net'].sum():,.0f} vs alt ${exB1['net'].sum():,.0f} -> diff ${exB1['net'].sum()-exB0['net'].sum():,.0f}  "
    f"(Stage A paired diff was ${D['d_usd'].sum():,.0f})")
# per-session Stage B diff and bootstrap
sB0 = exB0.groupby("session")["net"].sum()
sB1 = exB1.groupby("session")["net"].sum()
sB = pd.DataFrame({"o": sB0, "a": sB1}).fillna(0.0)
sB["d"] = sB["a"] - sB["o"]
r = np.random.default_rng(13)
idx = r.integers(0, len(sB), size=(2000, len(sB)))
sums = sB["d"].values[idx].sum(axis=1)
say(f"  Stage B session bootstrap 2000 draws: 90% CI [{np.percentile(sums,5):,.0f}, {np.percentile(sums,95):,.0f}], P(<=0)={(sums<=0).mean():.4f}; sessions pos {(sB['d']>0).sum()} neg {(sB['d']<0).sum()}")
OUT["e"] = dict(orig_exec=len(exB0), orig_rej=len(rjB0), alt_exec=len(exB1), alt_rej=len(rjB1),
                orig_net=float(exB0["net"].sum()), alt_net=float(exB1["net"].sum()), blocked=blocked, freed=freed,
                blocked_net=float(bl["net"].sum()) if blocked else 0.0, freed_net=float(fr["net"].sum()) if freed else 0.0,
                common_diff=float(c1.sum() - c0.sum()), boot_ci05=float(np.percentile(sums, 5)), boot_ci95=float(np.percentile(sums, 95)),
                p_le_0=float((sums <= 0).mean()))
exB0.to_csv(os.path.join(HERE, "stageB_original.csv"), index=False)
exB1.to_csv(os.path.join(HERE, "stageB_alt.csv"), index=False)

# Stage A overlap flag: alt holds longer and overlaps a later entry in the same session
ov = 0
ov_list = []
for sess, g in trades.groupby("session"):
    if len(g) < 2:
        continue
    g = g.sort_values("entry_ts")
    for i in range(len(g) - 1):
        a_exit = B.loc[B["trade_id"] == g.iloc[i]["trade_id"], "exit_ts"].iloc[0]
        b_exit = base.loc[base["trade_id"] == g.iloc[i]["trade_id"], "exit_ts"].iloc[0]
        nxt = g.iloc[i + 1]["entry_ts"]
        if a_exit > nxt and b_exit <= nxt:
            ov += 1
            ov_list.append(int(g.iloc[i]["trade_id"]))
say(f"  Stage A overlap flag: alt holds past a later same-session entry in {ov} cases (base did not): {ov_list}")
OUT["overlap_flag"] = ov_list

# =============================================================================
# (f) drawdown
# =============================================================================
hdr("(f) DRAWDOWN and WORST SESSION -- cumulative net P&L in chronological trade order -- SYNTHETIC")
ordr = trades.sort_values("entry_ts")["trade_id"].values
bI = base.set_index("trade_id").loc[ordr, "net"].values
aI = B.set_index("trade_id").loc[ordr, "net"].values
f_rows = []
for name, v, df_ in (("Stage A original", bI, base), ("Stage A alt", aI, B)):
    mdd, fin = dd_stats(v)
    ss = df_.groupby("session")["net"].sum()
    f_rows.append(dict(replay=name, total_usd=round(fin, 0), max_dd_usd=round(mdd, 0), worst_session=ss.idxmin(), worst_session_usd=round(ss.min(), 0),
                       best_session_usd=round(ss.max(), 0), sd_session=round(ss.std(), 0), worst_trade_usd=round(df_["net"].min(), 0),
                       n_sessions_lt_minus300=int((ss < -300).sum())))
for name, df_ in (("Stage B original", exB0), ("Stage B alt", exB1)):
    df_ = df_.sort_values(["session", "entry_i"])
    mdd, fin = dd_stats(df_["net"].values)
    ss = df_.groupby("session")["net"].sum()
    f_rows.append(dict(replay=name, total_usd=round(fin, 0), max_dd_usd=round(mdd, 0), worst_session=ss.idxmin(), worst_session_usd=round(ss.min(), 0),
                       best_session_usd=round(ss.max(), 0), sd_session=round(ss.std(), 0), worst_trade_usd=round(df_["net"].min(), 0),
                       n_sessions_lt_minus300=int((ss < -300).sum())))
FR = pd.DataFrame(f_rows)
say(FR.to_string(index=False))
# give-back: among changed trades, how many went from TARGET to STOP, and the worst reversal
gb = chg.copy()
gb["alt_reason"] = aa["exit_reason"].values
gb["base_reason"] = bb["exit_reason"].values
say(f"  changed trades ending at the ORIGINAL STOP under alt (2R winner -> full loser): {int((gb['alt_reason'].isin(['STOP','STOP_GAP'])).sum())}, "
    f"their paired cost ${gb.loc[gb['alt_reason'].isin(['STOP','STOP_GAP']),'d_usd'].sum():,.0f}")
say(f"  worst single paired reversal: ${gb['d_usd'].min():,.0f} (trade {int(gb.loc[gb['d_usd'].idxmin(),'trade_id'])})")
OUT["f"] = FR.to_dict(orient="records")

# =============================================================================
# sample-size for the cheapest real-data test
# =============================================================================
hdr("CHEAPEST REAL-DATA TEST -- sample size (uses SYNTHETIC SD only as a placeholder)")
from scipy import stats  # noqa: E402
sd = C["cont_R"].std()
for eff in (0.25, 0.5, 1.0):
    n = ((stats.norm.ppf(0.95) + stats.norm.ppf(0.8)) * sd / eff) ** 2
    say(f"  one-sided alpha 5%, power 80%, SD {sd:.2f}R (synthetic): detect mean post-target continuation {eff:.2f}R needs n={np.ceil(n):.0f} target-hit KX trades")
say(f"  session-level: {C['session'].nunique()} sessions carry the {len(C)} target hits here (~{len(C)/N_SESS:.2f} per session)")

# =============================================================================
# charts
# =============================================================================
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE, INK, INK2, SURF, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e1"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF})

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
sv = s_ben.sort_values(ascending=False).values
ax[0].bar(np.arange(len(sv)), sv, color=np.where(sv >= 0, BLUE, ORANGE), width=1.0, linewidth=0)
ax[0].axhline(0, color=INK2, lw=0.8)
ax[0].set_title("Paired benefit per session, sorted (alt - original, net USD)", loc="left", color=INK)
ax[0].set_xlabel("session rank"); ax[0].set_ylabel("USD"); ax[0].grid(axis="y", color=GRID, lw=0.6)
cum_b = np.cumsum(bI); cum_a = np.cumsum(aI)
ax[1].plot(cum_b, color=INK2, lw=2, label="original")
ax[1].plot(cum_a, color=BLUE, lw=2, label=best_label)
ax[1].set_title("Cumulative net P&L, Stage A, chronological trades", loc="left", color=INK)
ax[1].set_xlabel("trade #"); ax[1].set_ylabel("USD"); ax[1].grid(axis="y", color=GRID, lw=0.6); ax[1].legend(frameon=False)
fig.suptitle("SYNTHETIC development data -- S6", x=0.01, ha="left", color=INK2, fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS, "S6_session_concentration.png"), dpi=130)

fig, ax = plt.subplots(figsize=(8, 4.2))
lab = [str(x) for x in (2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, "none")]
vals = NB.iloc[:9]["sum_d_usd"].values
ax.bar(lab, vals, color=BLUE, width=0.6, linewidth=0)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_title("KX target multiple vs paired benefit (Stage A, net USD, 332 trades / 242 sessions)", loc="left", color=INK)
ax.set_xlabel("KX target multiple (R)"); ax.set_ylabel("USD vs original"); ax.grid(axis="y", color=GRID, lw=0.6)
fig.suptitle("SYNTHETIC development data -- S6", x=0.01, ha="left", color=INK2, fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS, "S6_target_neighbourhood.png"), dpi=130)

json.dump(OUT, open(os.path.join(HERE, "output.json"), "w"), indent=1, default=str)
say("\nDONE")


# =============================================================================
# EXTRAS used in the report
# =============================================================================
hdr("EXTRAS -- SYNTHETIC")
# (1) lock variant drawdown
LOCK = dict(kx_target_mult=None, be_trigger_R=2.0, be_lock_R=0.0, family_filter="KX")
alt_lock = replay_all(trades, sb, LOCK)
d_lock = paired(alt_lock)
lI = alt_lock.set_index("trade_id").loc[ordr, "net"].values
mdd, fin = dd_stats(lI)
ss = alt_lock.groupby("session")["net"].sum()
chg_l = d_lock[d_lock["changed"]]
say(f"  LOCK variant (KX: no target; stop->entry once +2.0R touched; flat 15:55): total ${fin:,.0f}, paired ${d_lock['d_usd'].sum():,.0f}, "
    f"max DD ${mdd:,.0f}, worst session ${ss.min():,.0f}, SD session ${ss.std():,.0f}, changed {len(chg_l)} trades, share d<0 {(chg_l['d_usd']<0).mean():.3f}, "
    f"ended at original stop: {int(alt_lock.set_index('trade_id').loc[chg_l['trade_id'],'exit_reason'].isin(['STOP','STOP_GAP']).sum())}")
bsl = session_bootstrap(d_lock, n=2000, seed=21)
say(f"  LOCK session bootstrap 95% CI [{bsl['ci2_5']:,.0f}, {bsl['ci97_5']:,.0f}]")
OUT["lock"] = dict(total=fin, paired=float(d_lock["d_usd"].sum()), mdd=mdd, worst=float(ss.min()), sd=float(ss.std()), boot=bsl)

# (2) paired SD over all KX trades and sample sizes
kx = D[D["family"] == "KX"]
sdk, mk = kx["d_R"].std(), kx["d_R"].mean()
say(f"  paired d_R over ALL KX trades n={len(kx)} ({kx['session'].nunique()} sessions): mean {mk:.2f}R SD {sdk:.2f}R; "
    f"per-trade t = {mk/(sdk/np.sqrt(len(kx))):.1f}")
z = stats.norm.ppf(0.95) + stats.norm.ppf(0.8)
for eff in (0.25, 0.5, 1.0, 1.5, mk):
    say(f"    detect mean paired benefit {eff:.2f}R/KX trade (SD {sdk:.2f}R): n={np.ceil((z*sdk/eff)**2):.0f} KX trades")
for n in (100, 240, 500):
    say(f"    MDE (one-sided 5%, 80% power) with n={n} KX trades: {z*sdk/np.sqrt(n):.2f}R per trade")
sdc = C["cont_R"].std()
for n in (50, 97, 200):
    say(f"    MDE post-target continuation with n={n} target hits (SD {sdc:.2f}R): {z*sdc/np.sqrt(n):.2f}R")
for eff in (1.5, 2.5):
    say(f"    detect continuation {eff:.1f}R needs n={np.ceil((z*sdc/eff)**2):.0f} target hits")
OUT["sample"] = dict(kx_n=len(kx), kx_mean=mk, kx_sd=sdk, cont_sd=sdc)

# (3) the brief's decision: reached >= +0.8R (high/low) then a bar CLOSE <= +0.3R while still open under the original
rows = []
for _, tr in trades.iterrows():
    S = sb.get(tr["session"])
    d = 1.0 if tr["direction"] == "LONG" else -1.0
    e_i = S["idx"][tr["entry_ts"]]
    R_pts = abs(tr["entry_px"] - tr["initial_stop_px"])
    b0 = base.set_index("trade_id").loc[tr["trade_id"]]
    a0 = B.set_index("trade_id").loc[tr["trade_id"]]
    x0 = int(b0["exit_i"])
    reached = None
    stall_i = None
    for i in range(e_i + 1, x0):  # bars fully inside the original holding period (closed before the original exit bar)
        fav = S["h"][i] if d > 0 else S["l"][i]
        if reached is None and d * (fav - tr["entry_px"]) / R_pts >= 0.8:
            reached = i
            continue
        if reached is not None and d * (S["c"][i] - tr["entry_px"]) / R_pts <= 0.3:
            stall_i = i
            break
    if stall_i is not None:
        rows.append(dict(trade_id=tr["trade_id"], session=tr["session"], family=tr["family"], stall_min=stall_i - e_i,
                         base_net=b0["net"], alt_net=a0["net"], base_R=b0["net_R"], alt_R=a0["net_R"], base_reason=b0["exit_reason"], alt_reason=a0["exit_reason"]))
ST = pd.DataFrame(rows)
say(f"\n  BRIEF DECISION CELL: reached >= +0.8R then closed <= +0.3R while still open under the original: {len(ST)} trades in {ST['session'].nunique()} sessions")
say(ST.groupby("family").agg(n=("trade_id", "size"), sessions=("session", "nunique"), base_usd=("base_net", "sum"), alt_usd=("alt_net", "sum"),
                             base_mean_R=("base_R", "mean"), alt_mean_R=("alt_R", "mean")).round(2).to_string())
say("  original exit reasons in this cell: " + ST["base_reason"].value_counts().to_dict().__str__())
# what an 'exit now at next open' would have yielded for this cell: approx = +0.3R gross minus costs (close-based), compare
say(f"  exiting at the stall (approx +0.3R gross): {len(ST)} trades x ~0.3R = {0.3*len(ST):.0f}R vs original {ST['base_R'].sum():.0f}R vs no-target {ST['alt_R'].sum():.0f}R")
OUT["stall_cell"] = dict(n=len(ST), sessions=int(ST["session"].nunique()), base_R=float(ST["base_R"].sum()), alt_R=float(ST["alt_R"].sum()))
json.dump(OUT, open(os.path.join(HERE, "output.json"), "w"), indent=1, default=str)
