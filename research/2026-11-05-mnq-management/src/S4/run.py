"""S4 Pyramiding / winner retention -- regenerates every table in reports/S4_pyramiding.md
from data/synthetic/.  Everything printed here is SYNTHETIC (development set only).

Run:  python3 src/S4/run.py   (from the panel folder)
"""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "synthetic")
OUT = os.path.join(HERE, "output")
CHARTS = os.path.join(ROOT, "charts")
os.makedirs(OUT, exist_ok=True); os.makedirs(CHARTS, exist_ok=True)
sys.path.insert(0, HERE)
from engine import load_bars, replay_trade, COMM, PT_VALUE  # noqa: E402

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
N_BOOT = 2000
SEED = 20261105
TOP_FRAC = 0.10

POLICIES = {
    "a_orig": "(a) original: all legs share stop+target",
    "b_add_stop_entry": "(b) add stop at original entry px",
    "c_add_be_after": "(c) add BE at add px after +0.5R",
    "c_add_be_after_1R": "(c') add BE at add px after +1.0R",
    "d_all_be_on_add": "(d) whole position BE on add fill",
    "e_scaleout_add": "(e) add exits +1R from add px; leg1 to target",
}


def log(*a):
    print(*a); LOG.append(" ".join(str(x) for x in a))


LOG = []

# --------------------------------------------------------------------------- data
bars = load_bars(os.path.join(DATA, "bars_MNQ_1min.csv"))
trades = pd.read_csv(os.path.join(DATA, "trades.csv"))
fills = pd.read_csv(os.path.join(DATA, "fills.csv"))
for c in ["entry_ts", "exit_ts", "add_ts"]:
    trades[c] = pd.to_datetime(trades[c], utc=True)
kx = trades[trades.family == "KX"].sort_values("entry_ts").reset_index(drop=True)
kx["sgn"] = np.where(kx.direction == "LONG", 1, -1)
kx["stopd"] = (kx.entry_px - kx.initial_stop_px) * kx.sgn
add_ids = set(kx.loc[kx.added_contracts > 0, "trade_id"])
log(f"KX trades {len(kx)} in {kx.session.nunique()} sessions; with add {len(add_ids)} "
    f"(all adds = 1 contract); MANUAL exits {int((kx.exit_reason=='MANUAL').sum())} "
    f"(with add: {int(((kx.exit_reason=='MANUAL')&(kx.added_contracts>0)).sum())})")


def run_policy(policy, **kw):
    pol = policy
    extra = {}
    if policy == "c_add_be_after_1R":
        pol = "c_add_be_after"; extra = {"be_trigger_R": 1.0}
    rows = [replay_trade(tr, bars, pol, **extra, **kw) for _, tr in kx.iterrows()]
    df = pd.DataFrame(rows); df["policy"] = policy
    return df


# --------------------------------------------------------------------------- 0. reconcile
log("\n=== 0. Original policy replay vs journal (KX, non-MANUAL) ===")
base = run_policy("a_orig")
chk = base.merge(kx[["trade_id", "exit_ts", "exit_px", "exit_reason", "net_pnl_usd"]], on="trade_id")
chk["exit_hhmm_j"] = chk.exit_ts.dt.tz_convert("America/New_York").dt.strftime("%H:%M")
nm = chk[chk.exit_reason != "MANUAL"]
same_t = (nm.exit_hhmm == nm.exit_hhmm_j); same_n = (nm.net_usd - nm.net_pnl_usd).abs() < 0.011
log(f"non-MANUAL trades {len(nm)}: exit bar identical {int(same_t.sum())}, net P&L identical {int(same_n.sum())}, "
    f"sum |net diff| ${float((nm.net_usd-nm.net_pnl_usd).abs().sum()):.2f}")
log(nm[~same_n][["trade_id", "session", "exit_hhmm", "exit_hhmm_j", "leg1_exit_reason", "exit_reason", "net_usd", "net_pnl_usd"]].to_string(index=False))
man = chk[chk.exit_reason == "MANUAL"]
log("MANUAL trades (journal vs rule replay):")
log(man[["trade_id", "session", "has_add", "exit_hhmm", "exit_hhmm_j", "leg1_exit_reason", "net_usd", "net_pnl_usd"]].to_string(index=False))
log(f"Journal KX net total ${kx.net_pnl_usd.sum():.2f}; rule-replay original ${base.net_usd.sum():.2f}")

# --------------------------------------------------------------------------- 1. all policies
res = {}
for ordering in ["stop_first", "target_first"]:
    for p in POLICIES:
        res[(p, ordering)] = run_policy(p, ordering=ordering)
        res[(p, ordering)]["ordering"] = ordering
allres = pd.concat(res.values()).reset_index(drop=True)
allres.to_csv(os.path.join(OUT, "per_trade_all_policies.csv"), index=False)

# fixed "largest winners" sets from the BASELINE (replayed original, stop_first)
base = res[("a_orig", "stop_first")].set_index("trade_id")
n_top_all = int(round(TOP_FRAC * len(base)))
top_all = set(base.net_R.sort_values(ascending=False).index[:n_top_all])
base_add = base[base.has_add]
n_top_add = int(round(TOP_FRAC * len(base_add)))
top_add = set(base_add.net_R.sort_values(ascending=False).index[:n_top_add])
log(f"\nLargest winners (baseline net R, held fixed): all-KX top {n_top_all} (min net R {base.loc[list(top_all)].net_R.min():.2f}); "
    f"add-subset top {n_top_add} (min net R {base.loc[list(top_add)].net_R.min():.2f}); "
    f"adds among all-KX top set: {len(top_all & add_ids)}")


def max_dd(net_series_chrono):
    cum = np.cumsum(net_series_chrono)
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    return float(np.max(peak - cum))


def metrics(df, top_set):
    d = df.sort_values("session")
    sess = d.groupby("session").net_usd.sum()
    return {
        "n_trades": len(d), "n_sessions": d.session.nunique(),
        "net_usd": d.net_usd.sum(), "mean_R": d.net_R.mean(), "median_R": d.net_R.median(),
        "win_rate": (d.net_usd > 0).mean(),
        "giveback_usd_mean": d.giveback_usd.mean(), "giveback_usd_sum": d.giveback_usd.sum(),
        "giveback_R_mean": d.giveback_R.mean(), "giveback_R_sum": d.giveback_R.sum(),
        "top_usd": d[d.trade_id.isin(top_set)].net_usd.sum(),
        "top_R_mean": d[d.trade_id.isin(top_set)].net_R.mean(),
        "max_dd_usd": max_dd(sess.values), "worst_session_usd": sess.min(),
        "worst_session": sess.idxmin(),
    }


def boot_ci(diff_by_session: pd.Series, stat="mean", n=N_BOOT, seed=SEED):
    """Session bootstrap of a paired per-session difference (one KX trade per session)."""
    rng = np.random.default_rng(seed)
    v = diff_by_session.values; k = len(v)
    draws = np.empty(n)
    for b in range(n):
        s = v[rng.integers(0, k, k)]
        draws[b] = s.mean() if stat == "mean" else s.sum()
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)), float((draws <= 0).mean())


def compare(ordering, subset_name, subset_ids, top_set):
    base_df = res[("a_orig", ordering)]
    base_df = base_df[base_df.trade_id.isin(subset_ids)]
    rows = []; diffs = []
    for p in POLICIES:
        d = res[(p, ordering)]; d = d[d.trade_id.isin(subset_ids)]
        m = metrics(d, top_set); m["policy"] = p
        bd = base_df.set_index("trade_id"); dd = d.set_index("trade_id").loc[bd.index]
        m["n_changed"] = int((np.abs(dd.net_usd - bd.net_usd) > 0.005).sum())
        if p != "a_orig":
            sess_diff_usd = (dd.net_usd - bd.net_usd).groupby(dd.session).sum()
            sess_diff_R = (dd.net_R - bd.net_R).groupby(dd.session).sum()
            sess_diff_gb = (dd.giveback_R - bd.giveback_R).groupby(dd.session).sum()
            top_diff = (dd.net_usd - bd.net_usd)[dd.trade_id.isin(top_set) if "trade_id" in dd else dd.index.isin(top_set)]
            lo, hi, p0 = boot_ci(sess_diff_usd, "sum")
            loR, hiR, pR = boot_ci(sess_diff_R, "mean")
            logb, higb, _ = boot_ci(sess_diff_gb, "mean")
            m.update({"d_net_usd": sess_diff_usd.sum(), "d_net_usd_ci": (lo, hi), "p_le0_usd": p0,
                      "d_mean_R": sess_diff_R.mean(), "d_mean_R_ci": (loR, hiR), "p_le0_R": pR,
                      "d_giveback_R_mean": sess_diff_gb.mean(), "d_giveback_R_ci": (logb, higb),
                      "d_top_usd": float((dd.net_usd - bd.net_usd)[dd.index.isin(top_set)].sum()),
                      "d_max_dd_usd": m["max_dd_usd"] - metrics(base_df, top_set)["max_dd_usd"]})
        rows.append(m)
    return pd.DataFrame(rows).set_index("policy")


def fmt_table(T, ordering, subset_name):
    lines = [f"\n--- {subset_name} | same-bar ordering = {ordering} | SYNTHETIC, net of $0.74/contract/side ---",
             f"{'policy':<20}{'n':>5}{'sess':>6}{'net $':>10}{'meanR':>8}{'win%':>7}{'gb$ mean':>10}{'gb R mean':>10}{'gb$ sum':>10}"
             f"{'top10% $':>10}{'maxDD $':>9}{'worst $':>9}{'  d net $ [95% CI]':>28}{'  d meanR [95% CI]':>26}{'  d top $':>9}{'  d DD $':>9}{' chg':>5}"]
    for p, r in T.iterrows():
        dn = "" if p == "a_orig" else f"{r.d_net_usd:+8.0f} [{r.d_net_usd_ci[0]:+.0f},{r.d_net_usd_ci[1]:+.0f}]"
        dr = "" if p == "a_orig" else f"{r.d_mean_R:+6.3f} [{r.d_mean_R_ci[0]:+.3f},{r.d_mean_R_ci[1]:+.3f}]"
        dt = "" if p == "a_orig" else f"{r.d_top_usd:+8.0f}"
        dd = "" if p == "a_orig" else f"{r.d_max_dd_usd:+8.0f}"
        lines.append(f"{p:<20}{r.n_trades:>5}{r.n_sessions:>6}{r.net_usd:>10.0f}{r.mean_R:>8.3f}{100*r.win_rate:>6.0f}%{r.giveback_usd_mean:>10.0f}{r.giveback_R_mean:>10.2f}{r.giveback_usd_sum:>10.0f}"
                     f"{r.top_usd:>10.0f}{r.max_dd_usd:>9.0f}{r.worst_session_usd:>9.0f}{dn:>28}{dr:>26}{dt:>9}{dd:>9}{r.n_changed:>5}")
    return "\n".join(lines)


log("\n=== 1-2. Policy comparison (paired, entries and add fills fixed) ===")
log("give-back (gb) = peak gross open P&L of the whole position (favourable intra-bar extreme, legs marked together) minus realised NET P&L; "
    "R denominator = planned_risk_usd of the initial leg; 'top10% $' = net $ earned on the fixed baseline top-10% set; "
    "maxDD on chronological per-session net P&L; d = paired difference vs (a); CI = 2000 session-bootstrap draws; chg = trades whose net differs from (a)")
tables = {}
for ordering in ["stop_first", "target_first"]:
    for name, ids, top in [("ADD trades only", add_ids, top_add), ("ALL KX trades", set(kx.trade_id), top_all)]:
        T = compare(ordering, name, ids, top); tables[(ordering, name)] = T
        log(fmt_table(T, ordering, name))
        T.to_csv(os.path.join(OUT, f"metrics_{ordering}_{name.split()[0]}.csv"))

# how often does a tightened stop end in a bar that also touches the target?
log("\nSame-bar stop+target ambiguity: trades whose net differs between orderings, per policy:")
for p in POLICIES:
    a = res[(p, "stop_first")].set_index("trade_id").net_usd; b = res[(p, "target_first")].set_index("trade_id").net_usd
    log(f"  {p:<20} {int((np.abs(a-b)>0.005).sum())} trades, $ difference (target_first - stop_first) = {float((b-a).sum()):+.2f}")

# --------------------------------------------------------------------------- 2b. conditional outcomes
log("\n=== 2b. Given the protective stop on the add was hit, what happened next? (add trades, stop_first) ===")
A0 = res[("a_orig", "stop_first")].set_index("trade_id")
for p in ["b_add_stop_entry", "c_add_be_after", "c_add_be_after_1R", "d_all_be_on_add"]:
    D = res[(p, "stop_first")].set_index("trade_id"); D = D[D.has_add]
    hit = D[(D.leg2_exit_reason.isin(["STOP", "STOP_GAP"])) & (np.abs(D.net_usd - A0.loc[D.index, "net_usd"]) > 0.005)]
    orig = A0.loc[hit.index]
    won = orig[orig.leg2_exit_reason == "TARGET"]; lost = orig[orig.leg2_exit_reason != "TARGET"]
    dusd = (hit.net_usd - orig.net_usd)
    log(f"  {p:<20} protective stop hit AND outcome changed: {len(hit)} trades / {hit.session.nunique()} sessions; "
        f"original then reached TARGET in {len(won)} (cost {dusd.loc[won.index].sum():+.0f} $, mean {dusd.loc[won.index].mean() if len(won) else 0:+.0f}), "
        f"original STOPPED in {len(lost)} (saving {dusd.loc[lost.index].sum():+.0f} $, mean {dusd.loc[lost.index].mean() if len(lost) else 0:+.0f})")
log(f"  Baseline add trades: {int((A0[A0.has_add].leg2_exit_reason=='TARGET').sum())} reached target, {int((A0[A0.has_add].leg2_exit_reason!='TARGET').sum())} stopped; "
    f"baseline net R of add trades lies in [{A0[A0.has_add].net_R.min():.2f},{A0[A0.has_add].net_R.max():.2f}] with NO trade between -1.5R and +2.0R "
    f"(count in (-1.5, 2.0): {int(A0[A0.has_add].net_R.between(-1.5, 2.0).sum())}) -- the original bracket has no intermediate exit.")

# --------------------------------------------------------------------------- 3. leg-2 economics
log("\n=== 3. Does the add earn money net of its own risk? (original policy, leg 2 only) ===")
b2 = res[("a_orig", "stop_first")]; b2 = b2[b2.has_add].copy()
b2["leg2_R_own"] = b2.leg2_net_usd / b2.leg2_risk_usd   # own risk = 1 contract x (add px - original stop) x $2
b2["leg2_R_init"] = b2.leg2_net_usd / kx.set_index("trade_id").loc[b2.trade_id, "planned_risk_usd"].values
f2 = fills[fills.leg_id == 2].copy(); f2["cash"] = np.where(f2.side == "BUY", -1, 1) * f2.price * f2.qty * PT_VALUE - f2.commission
j2 = f2.groupby("trade_id").cash.sum()
log(f"Journal fills, leg 2: n={len(j2)}, net total ${j2.sum():.2f}, mean ${j2.mean():.2f}, wins {int((j2>0).sum())}")
log(f"Replay (orig), leg 2: n={len(b2)}, net total ${b2.leg2_net_usd.sum():.2f}, mean ${b2.leg2_net_usd.mean():.2f}, median ${b2.leg2_net_usd.median():.2f}; "
    f"mean own-risk ${b2.leg2_risk_usd.mean():.2f} (= {float((b2.leg2_risk_usd/kx.set_index('trade_id').loc[b2.trade_id,'planned_risk_usd'].values).mean()):.2f} x initial-leg 1R); "
    f"mean leg-2 R on own risk {b2.leg2_R_own.mean():+.3f}, mean leg-2 R on initial 1R {b2.leg2_R_init.mean():+.3f}")
log(b2.groupby("leg2_exit_reason").agg(n=("leg2_net_usd", "size"), net_usd=("leg2_net_usd", "sum"), mean_usd=("leg2_net_usd", "mean")).to_string())
lo, hi, p0 = boot_ci(b2.set_index("session").leg2_net_usd, "sum")
log(f"Session-bootstrap 95% CI for leg-2 total net $: [{lo:.0f}, {hi:.0f}], P(total<=0) = {p0:.3f}")
log(f"Leg 1 of the same {len(b2)} add trades: net ${b2.leg1_net_usd.sum():.2f}; whole trade ${b2.net_usd.sum():.2f}")
# leg-2 of policies b/c/d/e
log("Leg-2 net $ by policy (add trades, stop_first): " + ", ".join(
    f"{p}={res[(p,'stop_first')][res[(p,'stop_first')].has_add].leg2_net_usd.sum():.0f}" for p in POLICIES))
log("Leg-2 exit reasons by policy: " + "; ".join(
    f"{p}: {res[(p,'stop_first')][res[(p,'stop_first')].has_add].leg2_exit_reason.value_counts().to_dict()}" for p in POLICIES))

# --------------------------------------------------------------------------- 4. sensitivities
log("\n=== 4. Sensitivities (ADD trades, stop_first) ===")
sens = {}
for label, kw in [("manual exits honoured (forced flat at journal MANUAL bar)", {"honour_manual": True}),
                  ("2-tick penetration trigger instead of touch", {"trigger_ticks": 2})]:
    r = {p: run_policy(p, **kw) for p in POLICIES}
    ba = r["a_orig"]; ba = ba[ba.has_add].set_index("trade_id")
    s = []
    for p in POLICIES:
        d = r[p]; d = d[d.has_add].set_index("trade_id").loc[ba.index]
        s.append(f"{p}: net ${d.net_usd.sum():.0f} (d vs a {d.net_usd.sum()-ba.net_usd.sum():+.0f}), meanR {d.net_R.mean():.3f}, gbR {d.giveback_R.mean():.2f}")
    log(f"- {label}:\n    " + "\n    ".join(s))

# --------------------------------------------------------------------------- 5. examples
log("\n=== 5. Leg-by-leg replays (SYNTHETIC, add trades) ===")
A = res[("a_orig", "stop_first")].set_index("trade_id"); C = res[("c_add_be_after", "stop_first")].set_index("trade_id")
B = res[("b_add_stop_entry", "stop_first")].set_index("trade_id")
cmpdf = pd.DataFrame({"a": A.net_usd, "b": B.net_usd, "c": C.net_usd, "has_add": A.has_add, "baseR": A.net_R,
                      "a_leg2": A.leg2_exit_reason, "c_leg2": C.leg2_exit_reason, "session": A.session})
cmpdf = cmpdf[cmpdf.has_add]
cmpdf["dc"] = cmpdf.c - cmpdf.a; cmpdf["db"] = cmpdf.b - cmpdf.a
helps = cmpdf.sort_values("dc", ascending=False).head(5); hurts = cmpdf[cmpdf.index.isin(top_all)].sort_values("dc").head(5)
log("Policy (c) helps most:\n" + helps.to_string()); log("Policy (c) hurts a baseline top-10% winner most:\n" + hurts.to_string())
ex_help = int(helps.index[0]); ex_hurt = int(hurts.index[0])


def leg_path(tid, policy):
    tr = kx[kx.trade_id == tid].iloc[0]
    r = replay_trade(tr, bars, policy, record_path=True)
    return tr, r


def write_example(tid, tag):
    tr, ra = leg_path(tid, "a_orig"); _, rc = leg_path(tid, "c_add_be_after"); _, rb = leg_path(tid, "b_add_stop_entry")
    pa, pc = ra["path"], rc["path"]
    m = pa[["hhmm", "close", "leg1_open_pnl", "leg2_open_pnl", "leg2_stop"]].rename(columns={"leg1_open_pnl": "a_leg1", "leg2_open_pnl": "a_leg2", "leg2_stop": "a_leg2_stop"})
    m = m.merge(pc[["hhmm", "leg2_open_pnl", "leg2_stop", "realised_gross"]].rename(columns={"leg2_open_pnl": "c_leg2", "leg2_stop": "c_leg2_stop", "realised_gross": "c_realised"}), on="hhmm", how="left")
    m.to_csv(os.path.join(OUT, f"example_{tag}_trade{tid}.csv"), index=False)
    leg2c = rc["legs"][1]
    knowable = pc.hhmm.iloc[max(0, leg2c.stop_moved_idx - rc['legs'][0].entry_idx - 1)] if leg2c.stop_moved_idx else None
    hdr = (f"trade {tid} session {tr.session} {tr.direction} {tr.strategy} entry {tr.entry_ts.tz_convert('America/New_York').strftime('%H:%M')} @ {tr.entry_px} "
           f"x{tr.initial_contracts}, stop {tr.initial_stop_px}, target {tr.initial_target_px}, 1R=${tr.planned_risk_usd:.2f}; add 1 @ {tr.add_px} at {ra['add_hhmm']} "
           f"(add's own risk to original stop ${ra['leg2_risk_usd']:.0f})\n"
           f"  (a) original: leg1 {ra['leg1_exit_reason']} @ {ra['leg1_exit_px']} {ra['leg1_exit_hhmm']}, leg2 {ra['leg2_exit_reason']} @ {ra['leg2_exit_px']} {ra['leg2_exit_hhmm']}; "
           f"net ${ra['net_usd']:.2f} ({ra['net_R']:+.2f}R), peak open ${ra['peak_open_gross_usd']:.0f}, give-back ${ra['giveback_usd']:.0f}\n"
           f"  (b) add stop @ entry: leg2 {rb['leg2_exit_reason']} @ {rb['leg2_exit_px']} {rb['leg2_exit_hhmm']}; net ${rb['net_usd']:.2f} ({rb['net_R']:+.2f}R)\n"
           f"  (c) add BE after +0.5R: leg2 {rc['leg2_exit_reason']} @ {rc['leg2_exit_px']} {rc['leg2_exit_hhmm']}; net ${rc['net_usd']:.2f} ({rc['net_R']:+.2f}R), give-back ${rc['giveback_usd']:.0f}\n"
           f"  first instant the (c) decision was knowable: close of the {knowable} bar (leg-2 stop moved to {tr.add_px} effective next bar); "
           f"for (b) it is the add fill at {ra['add_hhmm']} bar open")
    log(hdr)
    # compact minute table: every minute from add bar to last exit (cap at 40 rows by sampling if long)
    i_add = int(np.where(m.hhmm.values == ra["add_hhmm"])[0][0])
    seg = m.iloc[max(0, i_add - 2):].copy()
    if len(seg) > 36:
        keep = list(range(0, 12)) + list(range(12, len(seg) - 10, max(1, (len(seg) - 22) // 14))) + list(range(len(seg) - 10, len(seg)))
        seg = seg.iloc[sorted(set(keep))]
    log(seg.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    # chart
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(pa))
    ax.plot(x, pa.leg1_open_pnl, color="#1f4e79", lw=1.6, label=f"leg 1 ({tr.initial_contracts}c) open P&L")
    ax.plot(x, pa.leg2_open_pnl, color="#c0504d", lw=1.6, label="leg 2 (add, 1c) open P&L, (a) original")
    if len(pc) <= len(pa):
        ax.plot(np.arange(len(pc)), pc.leg2_open_pnl, color="#e8a33d", lw=1.6, ls="--", label="leg 2 open P&L, (c) add BE after +0.5R")
    ax.axhline(0, color="grey", lw=0.6)
    ax.axvline(i_add, color="k", lw=0.8, ls=":"); ax.text(i_add, ax.get_ylim()[1] * 0.95, " add fills", fontsize=8, va="top")
    if leg2c.stop_moved_idx:
        kx_i = leg2c.stop_moved_idx - 1 - rc["legs"][0].entry_idx
        ax.axvline(kx_i, color="#e8a33d", lw=0.8, ls=":"); ax.text(kx_i, ax.get_ylim()[0] * 0.95, " (c) decision knowable", fontsize=8, va="bottom", color="#e8a33d")
    ticks = list(range(0, len(pa), max(1, len(pa) // 8)))
    ax.set_xticks(ticks); ax.set_xticklabels(pa.hhmm.iloc[ticks], fontsize=8)
    ax.set_ylabel("open P&L per leg, $ (gross)"); ax.set_title(f"SYNTHETIC trade {tid} ({tr.session}, {tr.direction}): {tag}", fontsize=10)
    ax.legend(fontsize=8, loc="best"); ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, f"S4_replay_{tag}_trade{tid}.png"), dpi=130); plt.close(fig)


write_example(ex_help, "protect_helps")
write_example(ex_hurt, "protect_hurts")

# --------------------------------------------------------------------------- 6. chart: cumulative net P&L
fig, ax = plt.subplots(figsize=(9, 4.5))
cols = {"a_orig": "#1f4e79", "b_add_stop_entry": "#c0504d", "c_add_be_after": "#e8a33d", "c_add_be_after_1R": "#9c7bb5",
        "d_all_be_on_add": "#4f8f4f", "e_scaleout_add": "#7f7f7f"}
for p in POLICIES:
    d = res[(p, "stop_first")].sort_values("session")
    ax.plot(pd.to_datetime(d.session), d.net_usd.cumsum(), color=cols[p], lw=1.4, label=POLICIES[p])
ax.set_title("SYNTHETIC: cumulative net P&L, all 240 KX trades, by add-management policy (stop_first)", fontsize=10)
ax.set_ylabel("$ net of commissions"); ax.grid(alpha=0.25); ax.legend(fontsize=7.5)
fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "S4_cum_pnl_policies.png"), dpi=130); plt.close(fig)

# per-trade scatter of paired difference (c) vs (a) against baseline R, add trades
fig, ax = plt.subplots(figsize=(7, 4))
ax.scatter(cmpdf.baseR, cmpdf.dc, s=22, color="#e8a33d", label="(c) add BE after +0.5R minus (a)")
ax.scatter(cmpdf.baseR, cmpdf.db, s=22, color="#c0504d", marker="x", label="(b) add stop at entry minus (a)")
ax.axhline(0, color="grey", lw=0.6); ax.set_xlabel("baseline net R of the trade (original policy)"); ax.set_ylabel("paired net $ difference vs original")
ax.set_title("SYNTHETIC: where protecting the add helps/hurts (73 add trades)", fontsize=10); ax.legend(fontsize=8); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "S4_paired_diff_vs_baseR.png"), dpi=130); plt.close(fig)

# --------------------------------------------------------------------------- 7. stage-B flags
log("\n=== 7. Stage-B flags ===")
a = res[("a_orig", "stop_first")].set_index("trade_id")
for p in POLICIES:
    d = res[(p, "stop_first")].set_index("trade_id").loc[a.index]
    longer = d[d.exit_idx.values > a.exit_idx.values]
    overlap = 0
    for tid, r in longer.iterrows():
        S = bars[r.session]
        new_exit_ns = S["ts"][int(r.exit_idx)]
        old_exit_ns = S["ts"][int(a.loc[tid, "exit_idx"])]
        later_entries = trades[(trades.session == r.session) & (trades.trade_id != tid)]
        ent = later_entries.entry_ts.dt.tz_convert("UTC").values.astype("datetime64[ns]").astype(np.int64)
        overlap += int(((ent > old_exit_ns) & (ent <= new_exit_ns)).sum())
    extra_min = int((d.exit_idx.values - a.exit_idx.values)[d.exit_idx.values > a.exit_idx.values].sum())
    log(f"  {p:<20} trades holding LONGER than original: {len(longer):>2} (total extra minutes {extra_min:>3}); new overlaps with a later entry in the same session: {overlap}")
log("Only (e) ever holds longer: for KX_ORB_v1 (2.0R target) the add fills at entry+1.0R plus 0-2 ticks slippage, so '+1R from the add' sits a few ticks beyond the original target. "
    "All other alternatives exit legs earlier or on the same bar. Earlier leg-2 exits free one contract under the 4-contract limit, which could change later PX eligibility in the same session (Stage B, not replayed here).")
nonadd4 = kx[(kx.added_contracts == 0) & (kx.initial_contracts == 4)]
log(f"Add selection: adds occur only when initial size <= 3 (position limit 4); {len(nonadd4)} KX trades had 4 contracts and could never add. "
    f"Mean initial stop distance: add trades {kx[kx.added_contracts>0].stopd.mean():.1f} pts vs non-add {kx[kx.added_contracts==0].stopd.mean():.1f} pts.")

with open(os.path.join(OUT, "run_output.txt"), "w") as fh:
    fh.write("\n".join(LOG))
print(f"\nwrote {OUT}/run_output.txt and charts to {CHARTS}")
