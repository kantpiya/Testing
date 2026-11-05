#!/usr/bin/env python3
"""
S1 - Trade-path statistician.  Regenerates every table/figure in reports/S1_trade_paths.md
from data/synthetic/ (SYNTHETIC development set only; sealed/ is never touched).

Run:  python3 src/S1/run.py
Outputs: stdout (markdown tables), src/S1/output/*.md|csv, charts/S1_*.png

Conventions (see report section 2 for the execution assumptions):
  * 1R = planned_risk_usd of the initial leg (fixed for the trade, also after an add).
  * Path of the INITIAL leg: R_price(t) = dir * (px - entry_px) / stop_dist.  "At minute k" uses the
    close of the k-th bar after entry (bar open time = entry_ts + (k-1) min, close time = entry_ts + k min).
    "Touched" milestones use bar high (favourable, long) / low (short) and vice-versa for adverse.
  * Decision time for minute k = entry_ts + k min = the OPEN of bar k.  Conditional sets include only
    trades still open at that time under the ORIGINAL policy (exit bar index >= k).
  * Counterfactual "exit now": market order at the open of bar k, 1 tick adverse slippage, $0.74/side
    commission on every contract (initial leg + any add already filled before the decision time).
  * Counterfactual "breakeven stop": stop for all legs moved to entry_px from bar k on, original target kept.
    Stop fill = entry_px - 1 tick adverse, or the bar open if it gapped through; target = limit at target
    px, 0 slippage; both in the same bar -> both orderings reported; flat at the 15:55 bar open (1 tick).
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(ROOT, "data", "synthetic")
CH = os.path.join(ROOT, "charts")
OUT = os.path.join(ROOT, "src", "S1", "output")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CH, exist_ok=True)

TICK, PT, COMM = 0.25, 2.0, 0.74          # from costs.csv
SLIP = 1 * TICK                           # 1 tick on market/stop fills, 0 on limits
HORIZONS = [5, 10, 15, 20, 30]            # decision minutes examined
STALLS = [                                # (name, touched >= a, then close <= b)
    ("touched>=+0.8R then close<=+0.3R", 0.8, 0.3),
    ("touched>=+0.8R then close<=+0.5R", 0.8, 0.5),
    ("touched>=+0.5R then close<=+0.2R", 0.5, 0.2),
    ("touched>=+1.0R then close<=+0.5R", 1.0, 0.5),
    ("touched>=+0.3R then close<=0R (entry revisit)", 0.3, 0.0),
]
MILESTONES_UP = [0.3, 0.8]
MILESTONE_DN = -0.5
N_BOOT = 2000
SEED = 20261105
LOG = []


def say(s=""):
    print(s)
    LOG.append(s)


def md_table(df, floatfmt="{:.2f}"):
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- load
def load():
    t = pd.read_csv(os.path.join(D, "trades.csv"))
    b = pd.read_csv(os.path.join(D, "bars_MNQ_1min.csv"))
    b["ts"] = pd.to_datetime(b["ts"], utc=True).dt.tz_convert("America/New_York")
    b = b.sort_values("ts").reset_index(drop=True)
    b["session"] = b["ts"].dt.strftime("%Y-%m-%d")
    for c in ["entry_ts", "exit_ts", "add_ts"]:
        t[c] = pd.to_datetime(t[c], utc=True).dt.tz_convert("America/New_York")
    bars = {}
    for s, g in b.groupby("session"):
        bars[s] = {k: g[k].to_numpy(dtype=float) for k in ["open", "high", "low", "close"]}
        bars[s]["ts"] = g["ts"].to_numpy().astype("datetime64[ns]").astype(np.int64)
        assert len(g) == 390, s
    return t, bars


# --------------------------------------------------------------------------- paths
def build_paths(t, bars):
    P = []
    for tr in t.itertuples(index=False):
        S = bars[tr.session]
        e_ns = np.datetime64(tr.entry_ts.tz_convert("UTC").tz_localize(None), "ns").astype(np.int64)
        x_ns = np.datetime64(tr.exit_ts.tz_convert("UTC").tz_localize(None), "ns").astype(np.int64)
        i0 = int(np.searchsorted(S["ts"], e_ns))
        assert S["ts"][i0] == e_ns, tr.trade_id
        d = 1.0 if tr.direction == "LONG" else -1.0
        sd = abs(tr.entry_px - tr.initial_stop_px)
        o, h, l, c = (S[k][i0:] for k in ["open", "high", "low", "close"])
        fav = h if d > 0 else l
        adv = l if d > 0 else h
        p = dict(
            trade_id=tr.trade_id, session=tr.session, strategy=tr.strategy, family=tr.family, d=d,
            entry=tr.entry_px, sd=sd, risk=tr.planned_risk_usd, ic=int(tr.initial_contracts),
            ac=int(tr.added_contracts), add_px=tr.add_px, tgt=tr.initial_target_px,
            tgtR=d * (tr.initial_target_px - tr.entry_px) / sd,
            exit_px=tr.exit_px, exit_reason=tr.exit_reason, net=tr.net_pnl_usd,
            o=o, rc=d * (c - tr.entry_px) / sd, mfe=d * (fav - tr.entry_px) / sd, mae=d * (adv - tr.entry_px) / sd,
            exit_idx=int(round((x_ns - e_ns) / 60e9)), eod_idx=len(o) - 5,
        )
        p["add_idx"] = None
        if p["ac"] > 0:
            a_ns = np.datetime64(tr.add_ts.tz_convert("UTC").tz_localize(None), "ns").astype(np.int64)
            p["add_idx"] = int(round((a_ns - e_ns) / 60e9))
        p["R"] = p["net"] / p["risk"]
        # initial-leg-only net R under the original policy (same exit px for all legs)
        p["R_init"] = (p["ic"] * d * (tr.exit_px - tr.entry_px) * PT - 2 * COMM * p["ic"]) / p["risk"]
        p["cummfe"] = np.maximum.accumulate(p["mfe"])
        p["cummae"] = np.minimum.accumulate(p["mae"])
        assert p["exit_idx"] <= p["eod_idx"]
        P.append(p)
    return P


# --------------------------------------------------------------------------- counterfactuals
def pnl_legs(p, fill, exit_i):
    """Net $ of the whole position closed at `fill` in bar exit_i (add leg included if filled before that bar)."""
    d = p["d"]
    pnl = p["ic"] * d * (fill - p["entry"]) * PT - 2 * COMM * p["ic"]
    if p["ac"] > 0 and p["add_idx"] is not None and p["add_idx"] < exit_i:
        pnl += p["ac"] * d * (fill - p["add_px"]) * PT - 2 * COMM * p["ac"]
    return pnl


def cf_exit_now(p, k):
    fill = p["o"][k] - p["d"] * SLIP
    return pnl_legs(p, fill, k)


def cf_breakeven(p, k):
    """Returns (net$ stop-first, net$ target-first, exit_idx, ambiguous, reason)."""
    d, e = p["d"], p["entry"]
    for i in range(k, p["eod_idx"] + 1):
        if i == p["eod_idx"]:
            fill = p["o"][i] - d * SLIP
            v = pnl_legs(p, fill, i)
            return v, v, i, False, "EOD"
        gap = d * (p["o"][i] - e) < 0
        stop_hit = gap or (p["mae"][i] <= 0)
        tgt_hit = p["mfe"][i] >= p["tgtR"]
        if stop_hit or tgt_hit:
            stop_fill = p["o"][i] if gap else e - d * SLIP
            tgt_fill = p["tgt"]
            if stop_hit and tgt_hit and not gap:
                return pnl_legs(p, stop_fill, i), pnl_legs(p, tgt_fill, i), i, True, "AMBIG"
            if stop_hit:
                v = pnl_legs(p, stop_fill, i)
                return v, v, i, False, "STOP_BE"
            v = pnl_legs(p, tgt_fill, i)
            return v, v, i, False, "TARGET"
    raise RuntimeError


# --------------------------------------------------------------------------- states
def state_rows(P):
    """One row per (trade, state) where the state is observed and the trade is still open at decision time."""
    rows = []

    def add(p, state, k):
        if k > p["exit_idx"]:          # not still open under ORIGINAL policy at decision time
            return
        cfx = cf_exit_now(p, k)
        be_s, be_t, be_i, amb, be_reason = cf_breakeven(p, k)
        rows.append(dict(
            trade_id=p["trade_id"], session=p["session"], strategy=p["strategy"], family=p["family"],
            state=state, k=k, R=p["R"], net=p["net"], target=int(p["exit_reason"] == "TARGET"),
            lt_m05=int(p["R"] < -0.5), cfx_R=cfx / p["risk"], cfx_net=cfx,
            be_s_R=be_s / p["risk"], be_t_R=be_t / p["risk"], be_ambig=int(amb), be_reason=be_reason,
            be_hold_longer_than_orig=int(be_i > p["exit_idx"]),
            add_before=int(p["add_idx"] is not None and p["add_idx"] < k),
        ))

    for p in P:
        n = len(p["rc"])
        for k in HORIZONS:
            if k > p["exit_idx"]:
                continue
            r_k = p["rc"][k - 1]
            add(p, f"min {k}: all still open", k)
            if r_k <= 0:
                add(p, f"min {k}: open profit <= 0R", k)
            if p["cummfe"][k - 1] < 0.3:
                add(p, f"min {k}: not yet touched +0.3R", k)
            if r_k >= 0.3:
                add(p, f"min {k}: open profit >= +0.3R", k)
        for name, a, b in STALLS:
            hit = np.where((p["cummfe"] >= a) & (p["rc"] <= b))[0]
            hit = hit[hit <= p["exit_idx"] - 1]      # trigger bar must be a fully-held bar
            if len(hit):
                add(p, name, int(hit[0]) + 1)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- bootstrap
class SessionBoot:
    def __init__(self, sessions, n_boot=N_BOOT, seed=SEED):
        self.sess = np.array(sorted(set(sessions)))
        self.S = len(self.sess)
        self.idx = {s: i for i, s in enumerate(self.sess)}
        rng = np.random.default_rng(seed)
        self.W = rng.multinomial(self.S, np.full(self.S, 1.0 / self.S), size=n_boot).astype(float)

    def ci(self, sess_labels, values):
        si = np.array([self.idx[s] for s in sess_labels])
        v = np.asarray(values, dtype=float)
        sums = np.bincount(si, weights=v, minlength=self.S)
        cnts = np.bincount(si, minlength=self.S).astype(float)
        num, den = self.W @ sums, self.W @ cnts
        with np.errstate(invalid="ignore", divide="ignore"):
            m = np.where(den > 0, num / den, np.nan)
        return np.nanpercentile(m, 2.5), np.nanpercentile(m, 97.5)


def summarize(rows, boot, groups):
    out = []
    for gname, gmask in groups:
        g = rows[gmask(rows)]
        for state in list(dict.fromkeys(rows["state"])):
            c = g[g["state"] == state]
            if len(c) == 0:
                continue
            dx = c["cfx_R"] - c["R"]
            db = c["be_s_R"] - c["R"]
            lo, hi = boot.ci(c["session"], c["R"])
            xlo, xhi = boot.ci(c["session"], dx)
            blo, bhi = boot.ci(c["session"], db)
            out.append(dict(
                group=gname, state=state, n=len(c), sessions=c["session"].nunique(),
                P_target=c["target"].mean(), mean_R=c["R"].mean(), median_R=c["R"].median(),
                P_R_lt_m05=c["lt_m05"].mean(), mean_R_CI=f"[{lo:.2f}, {hi:.2f}]",
                mean_usd=c["net"].mean(),
                cf_exit_mean_R=c["cfx_R"].mean(), cf_exit_mean_usd=c["cfx_net"].mean(),
                d_exit=dx.mean(), d_exit_CI=f"[{xlo:.2f}, {xhi:.2f}]",
                be_stopfirst_R=c["be_s_R"].mean(), be_tgtfirst_R=c["be_t_R"].mean(),
                d_be=db.mean(), d_be_CI=f"[{blo:.2f}, {bhi:.2f}]",
                be_P_R_lt_m05=(c["be_s_R"] < -0.5).mean(),
                orig_worst10=c["R"].nsmallest(max(1, int(np.ceil(0.1 * len(c))))).mean(),
                be_worst10=c["be_s_R"].nsmallest(max(1, int(np.ceil(0.1 * len(c))))).mean(),
                be_ambig=int(c["be_ambig"].sum()), be_longer=int(c["be_hold_longer_than_orig"].sum()),
                share_add_before=c["add_before"].mean(),
            ))
    return pd.DataFrame(out)


# --------------------------------------------------------------------------- milestones
def milestone_table(P):
    recs = []
    for p in P:
        for scope, last in [("within original hold", p["exit_idx"]), ("unmanaged path to 15:54 close", p["eod_idx"] - 1)]:
            cm, ca, rc = p["cummfe"][: last + 1], p["cummae"][: last + 1], p["rc"][: last + 1]
            r = dict(trade_id=p["trade_id"], session=p["session"], family=p["family"], strategy=p["strategy"], scope=scope)
            for m in MILESTONES_UP:
                w = np.where(cm >= m)[0]
                r[f"t_up{m}"] = (w[0] + 1) if len(w) else np.nan
            w = np.where(ca <= MILESTONE_DN)[0]
            r["t_dn0.5"] = (w[0] + 1) if len(w) else np.nan
            w = np.where((cm >= 0.3) & (rc <= 0))[0]
            r["t_revisit"] = (w[0] + 1) if len(w) else np.nan
            recs.append(r)
    M = pd.DataFrame(recs)
    rows = []
    for (fam, scope), g in M.groupby(["family", "scope"]):
        for col, lab in [("t_up0.3", "+0.3R touched"), ("t_up0.8", "+0.8R touched"), ("t_dn0.5", "-0.5R touched"),
                         ("t_revisit", "close<=0R after touching +0.3R")]:
            v = g[col].dropna()
            rows.append(dict(family=fam, scope=scope, milestone=lab, n_trades=len(g), n_sessions=g["session"].nunique(),
                             share_reached=len(v) / len(g), n_reached=len(v),
                             q25_min=v.quantile(.25) if len(v) else np.nan, median_min=v.median() if len(v) else np.nan,
                             q75_min=v.quantile(.75) if len(v) else np.nan, p_within_10min=(v <= 10).mean() if len(v) else np.nan))
    return M, pd.DataFrame(rows)


# --------------------------------------------------------------------------- figures
def figures(M, rows):
    C = {"KX": "#2a78d6", "PX": "#eb6834"}
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    U = M[M["scope"] == "unmanaged path to 15:54 close"]
    grid = np.arange(1, 121)
    for ax, (col, lab) in zip(axes, [("t_up0.3", "touched +0.3R"), ("t_up0.8", "touched +0.8R"), ("t_dn0.5", "touched -0.5R")]):
        for fam in ["KX", "PX"]:
            v = U.loc[U["family"] == fam, col].to_numpy()
            y = [(np.nan_to_num(v, nan=1e9) <= m).mean() for m in grid]
            ax.plot(grid, y, color=C[fam], lw=2, label=f"{fam} (n={len(v)})")
        ax.set_title(lab, fontsize=10)
        ax.set_xlabel("minutes since entry")
        ax.grid(alpha=.25)
    axes[0].set_ylabel("share of trades")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("SYNTHETIC - cumulative share having touched a milestone (initial-leg price path, exits ignored)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "S1_milestone_curves.png"), dpi=130)
    plt.close(fig)

    st = rows[(rows["state"] == STALLS[0][0]) & (rows["family"] == "KX")]
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.scatter(st["R"], st["cfx_R"], s=28, color="#2a78d6", alpha=.8, edgecolor="white", lw=.5)
    lim = [min(st["R"].min(), -1.5) - .2, max(st["R"].max(), 1) + .2]
    ax.plot(lim, lim, color="#999", lw=1, ls="--")
    ax.set_xlabel("final net R, original policy")
    ax.set_ylabel("net R if exited at the stall decision bar")
    ax.set_title(f"SYNTHETIC - KX stall (>= +0.8R then <= +0.3R), n={len(st)} trades / {st['session'].nunique()} sessions", fontsize=9)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "S1_kx_stall_paired.png"), dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------- main
def main():
    t, bars = load()
    say("# S1 run.py output - ALL NUMBERS SYNTHETIC (development set 2025-05-01 .. 2026-04-30)")
    say(f"trades={len(t)}  sessions={t['session'].nunique()}  bar sessions={len(bars)}")
    # sanity: gross P&L recomputation from journal fields, all legs
    d = np.where(t["direction"] == "LONG", 1.0, -1.0)
    gross = t["initial_contracts"] * d * (t["exit_px"] - t["entry_px"]) * PT + \
        t["added_contracts"].fillna(0) * d * (t["exit_px"] - t["add_px"].fillna(t["entry_px"])) * PT
    say(f"max |recomputed gross - gross_pnl_usd| = {np.abs(gross - t['gross_pnl_usd']).max():.4f} USD")
    say(f"max |initial_contracts*stop_dist*2 - planned_risk_usd| = {np.abs(t['initial_contracts']*(t['entry_px']-t['initial_stop_px']).abs()*2 - t['planned_risk_usd']).max():.2f} USD")
    say("exit_reason counts: " + str(t["exit_reason"].value_counts().to_dict()))
    say("trades with add: " + str(t.groupby("strategy")["added_contracts"].apply(lambda x: int((x > 0).sum())).to_dict()))

    P = build_paths(t, bars)
    pd.DataFrame([{k: v for k, v in p.items() if not isinstance(v, np.ndarray)} for p in P]).to_csv(os.path.join(OUT, "trade_paths.csv"), index=False)

    # PX target geometry (why +0.8R is rarely reachable for PX under the original policy)
    tg = pd.DataFrame([dict(family=p["family"], strategy=p["strategy"], tgtR=p["tgtR"]) for p in P])
    say("\n## Target distance in R by strategy (OBSERVED)")
    say(md_table(tg.groupby("strategy")["tgtR"].describe()[["count", "mean", "min", "25%", "50%", "75%", "max"]].reset_index()))
    say(f"PX trades with target >= +0.8R: {int((tg[tg.family=='PX'].tgtR >= 0.8).sum())} of {int((tg.family=='PX').sum())}")

    rows = state_rows(P)
    rows.to_csv(os.path.join(OUT, "state_rows.csv"), index=False)
    boot = SessionBoot(t["session"])
    groups = [("KX (all)", lambda r: r["family"] == "KX"),
              ("KX_ORB_v1", lambda r: r["strategy"] == "KX_ORB_v1"),
              ("KX_ORB_v2", lambda r: r["strategy"] == "KX_ORB_v2"),
              ("PX_REV_v1", lambda r: r["family"] == "PX")]
    summ = summarize(rows, boot, groups)
    summ.to_csv(os.path.join(OUT, "central_table_full.csv"), index=False)

    say("\n## Unconditional outcome by group (OBSERVED, net of costs, denominator = trades)")
    base = []
    for gname, gmask in groups:
        sub = pd.DataFrame([{k: p[k] for k in ["session", "family", "strategy", "R", "net", "exit_reason"]} for p in P])
        sub = sub[gmask(sub)]
        lo, hi = boot.ci(sub["session"], sub["R"])
        base.append(dict(group=gname, n=len(sub), sessions=sub["session"].nunique(), P_target=(sub["exit_reason"] == "TARGET").mean(),
                         mean_R=sub["R"].mean(), mean_R_CI=f"[{lo:.2f}, {hi:.2f}]", median_R=sub["R"].median(),
                         P_R_lt_m05=(sub["R"] < -0.5).mean(), mean_usd=sub["net"].mean(), total_usd=sub["net"].sum()))
    say(md_table(pd.DataFrame(base)))

    cols_a = ["group", "state", "n", "sessions", "P_target", "mean_R", "mean_R_CI", "median_R", "P_R_lt_m05", "mean_usd",
              "cf_exit_mean_R", "cf_exit_mean_usd", "d_exit", "d_exit_CI"]
    cols_b = ["group", "state", "n", "sessions", "mean_R", "be_stopfirst_R", "be_tgtfirst_R", "d_be", "d_be_CI",
              "P_R_lt_m05", "be_P_R_lt_m05", "orig_worst10", "be_worst10", "be_ambig", "be_longer", "share_add_before"]
    say("\n## CENTRAL TABLE A - given the state at decision time, what happened next under the ORIGINAL policy, and the "
        "counterfactual 'exit now' (market at next bar open, 1 tick, commissions). Only trades still open at decision time. "
        "R net of costs; mean_usd = mean net $ per trade. CIs: 2000 whole-session bootstraps. SYNTHETIC.")
    say(md_table(summ[cols_a]))
    say("\n## CENTRAL TABLE B - counterfactual 'tighten stop to entry (breakeven) at decision time', target unchanged. "
        "be_ambig = trades where stop and target were touched in the same bar (both orderings shown); "
        "be_longer = trades where the BE replay holds past the ORIGINAL exit (only possible after MANUAL exits). SYNTHETIC.")
    say(md_table(summ[cols_b]))

    # Stall detail
    say("\n## Stall detail (KX, touched>=+0.8R then close<=+0.3R): exit reasons under original policy, adds, decision minute")
    st = rows[(rows["state"] == STALLS[0][0])]
    for fam in ["KX", "PX"]:
        s = st[st["family"] == fam]
        if len(s) == 0:
            say(f"{fam}: n=0")
            continue
        er = t.set_index("trade_id").loc[s["trade_id"], "exit_reason"].value_counts().to_dict()
        say(f"{fam}: n={len(s)} trades / {s['session'].nunique()} sessions; original exit reasons {er}; "
            f"decision minute median {s['k'].median():.0f} (IQR {s['k'].quantile(.25):.0f}-{s['k'].quantile(.75):.0f}); "
            f"share with add already filled {s['add_before'].mean():.2f}; BE outcomes {s['be_reason'].value_counts().to_dict()}")
        rl = pd.DataFrame([dict(trade_id=p["trade_id"], R=p["R"], R_init=p["R_init"]) for p in P if p["trade_id"] in set(s["trade_id"])])
        say(f"{fam}: mean final R whole position {rl['R'].mean():.2f} vs initial leg only {rl['R_init'].mean():.2f} "
            f"(add leg contributes {rl['R'].mean()-rl['R_init'].mean():+.2f}R per trade on average)")
        say(f"{fam}: final R quantiles under original policy: " + ", ".join(f"q{int(q*100)}={s['R'].quantile(q):.2f}" for q in [.1, .25, .5, .75, .9]))
        say(f"{fam}: exit-now R: mean {s['cfx_R'].mean():.2f}, median {s['cfx_R'].median():.2f}")

    # Milestones
    M, mt = milestone_table(P)
    M.to_csv(os.path.join(OUT, "milestones.csv"), index=False)
    say("\n## Time-to-milestone (minutes after entry; minute m = first bar whose high/low touched it, counted from 1). "
        "'within original hold' is censored at the original exit; 'unmanaged path' ignores the exit and is HYPOTHETICAL. SYNTHETIC.")
    say(md_table(mt))

    # Adds: how they change the picture for trades in time-states
    say("\n## Adds and the initial-leg path (KX only; PX never adds)")
    kx = [p for p in P if p["family"] == "KX"]
    wa = [p for p in kx if p["ac"] > 0]
    say(f"KX trades with add: {len(wa)} of {len(kx)}; add fill minute median {np.median([p['add_idx'] for p in wa]):.0f}; "
        f"mean final R with add {np.mean([p['R'] for p in wa]):.2f} (initial leg only {np.mean([p['R_init'] for p in wa]):.2f}); "
        f"without add {np.mean([p['R'] for p in kx if p['ac']==0]):.2f}")
    say(f"KX trades that touched +1.0R within 20 min: {sum(1 for p in kx if (p['cummfe'][:min(20,p['exit_idx']+1)]>=1.0).any())} "
        f"(adds observed: {len(wa)})")

    figures(M, rows)
    with open(os.path.join(OUT, "run_output.md"), "w") as f:
        f.write("\n".join(LOG) + "\n")
    say(f"\nwrote {OUT}/run_output.md, central_table_full.csv, state_rows.csv, milestones.csv, trade_paths.csv; charts/S1_*.png")


if __name__ == "__main__":
    main()
