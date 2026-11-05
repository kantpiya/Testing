"""S3 - Reversal / profit-taking specialist. Stage A paired replay of PX trades.

Run:  python3 src/S3/run.py          (from the panel folder)
Reads data/synthetic/ only. Writes charts/S3_*.png and src/S3/output.txt (pasted into the report).
ALL NUMBERS ARE SYNTHETIC (development set).
"""
from __future__ import annotations

import os
import sys
from collections import OrderedDict

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay import (Policy, load, max_drawdown, path_metrics, session_bootstrap, simulate,  # noqa: E402
                    trade_bars)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "synthetic")
CHARTS = os.path.join(ROOT, "charts")
N_BOOT = 2000
SEED = 11
PAL = {"s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "s4": "#eda100", "ink": "#0b0b0b",
       "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9", "surface": "#fcfcfb"}
_out = []


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    _out.append(s)


def fmt_tbl(df: pd.DataFrame, floatfmt="{:.3f}") -> str:
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else floatfmt.format(v))
    cols = list(d.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main():
    bars, px, trades, signals = load(DATA)
    tb = {int(r.trade_id): trade_bars(bars, r) for r in px.itertuples()}
    n = len(px)
    P("# S3 run output - SYNTHETIC development set, PX_REV_v1 trades only")
    P(f"PX trades: {n}; distinct sessions: {px.session.nunique()}; 1-lot trades: {(px.initial_contracts == 1).sum()}; "
      f"2-lot: {(px.initial_contracts == 2).sum()}; 4-lot: {(px.initial_contracts == 4).sum()}")
    P(f"Structural target distance in R (target = OR midpoint): quantiles 10/25/50/75/90 = "
      f"{px.tgt_R.quantile([.1, .25, .5, .75, .9]).round(2).tolist()}; targets >= 0.8R: {(px.tgt_R >= 0.8).sum()}/{n}")
    P(f"Entry sits inside the re-entered OR boundary by median {((px.entry_px - px.or_boundary_near) * px.sgn).median():.2f} pts "
      f"(so the boundary is a stop-side level, not a profit level). OR quarter-line to entry: median "
      f"{(((px.or_quarter - px.entry_px) * px.sgn) / px.stop_dist).median():.2f} R.")

    # ---------------- policies ----------------
    pols = OrderedDict()
    pols["P0_original"] = Policy("P0_original", note="bracket: stop (extreme+0.1w, clipped) + OR-midpoint target, flat 15:55")
    for H in (5, 10, 15, 20, 30, 45, 60, 90):
        pols[f"T{H}"] = Policy(f"T{H}", time_exit_min=H, note=f"bracket + market exit at open of minute {H}")
    pols["S_stop_to_boundary"] = Policy("S_stop_to_boundary", stop_move_trigger="quarter", stop_move_to="boundary_near",
                                        note="once OR quarter-line is touched, stop moves to the re-entered OR boundary (next bar)")
    pols["S_stop_to_entry"] = Policy("S_stop_to_entry", stop_move_trigger="quarter", stop_move_to="entry",
                                     note="once OR quarter-line is touched, stop moves to entry price (next bar)")
    pols["S_exit_quarter"] = Policy("S_exit_quarter", target_level="quarter", note="full exit (limit) at OR quarter-line instead of midpoint")
    pols["S_partial_quarter"] = Policy("S_partial_quarter", partial_at_quarter=True,
                                       note="floor(q/2) out at OR quarter-line, rest to midpoint; 1-lots unchanged")
    pols["S_far_target"] = Policy("S_far_target", target_level="far", note="target moved to the opposite OR boundary")
    pols["S_target_3q"] = Policy("S_target_3q", target_level="threeq", note="target at the OR 3/4-line (between midpoint and far boundary)")
    pols["S_no_target"] = Policy("S_no_target", target_level="none", note="PROBE: stop only, no target, flat 15:55 (tests generic post-entry drift)")
    for k in (5, 10, 15, 20):
        for th in (0.0, 0.15, 0.3):
            pols[f"NP_k{k}_{th:.2f}R"] = Policy(f"NP_k{k}_{th:.2f}R", noprog_k=k, noprog_theta=th,
                                                note=f"close-based progress < {th}R at minute {k} => market exit next open")
    pols["NP_k10_50pctTgt"] = Policy("NP_k10_50pctTgt", noprog_k=10, noprog_theta=0.5, noprog_mode="tgtfrac",
                                     note="progress < 50% of target distance at minute 10 => exit")
    P(f"\nPolicies examined (complete count incl. discarded): {len(pols)}  (+1 same-bar ordering sensitivity run)")

    res = {name: [simulate(tr, tb[int(tr.trade_id)], pol) for tr in px.itertuples()] for name, pol in pols.items()}
    # ordering sensitivity for the moved-stop policy
    res["S_stop_to_boundary_TGTFIRST"] = [simulate(tr, tb[int(tr.trade_id)], Policy("x", stop_move_trigger="quarter",
                                                                                     stop_move_to="boundary_near", ordering="target_first"))
                                          for tr in px.itertuples()]

    # ---------------- reconstruction check vs journal ----------------
    o = res["P0_original"]
    rec = pd.DataFrame({"trade_id": px.trade_id, "journal_net": px.net_pnl_usd, "journal_reason": px.exit_reason,
                        "rec_net": [r.net for r in o], "rec_reason": [r.exit_reason for r in o],
                        "journal_exit_ts": px.exit_ts, "rec_exit_ts": [r.exit_ts for r in o]})
    rec["d"] = rec.rec_net - rec.journal_net
    exact = ((rec.d.abs() < 0.005) & (rec.journal_exit_ts == rec.rec_exit_ts)).sum()
    P("\n## Reconstruction of the original policy vs trades.csv (PX)")
    P(f"exact match (net $ and exit bar): {exact}/{n}; journal total net ${px.net_pnl_usd.sum():.2f}; reconstructed ${rec.rec_net.sum():.2f}")
    P(fmt_tbl(rec[rec.d.abs() >= 0.005][["trade_id", "journal_reason", "journal_net", "rec_reason", "rec_net", "d"]], "{:.2f}"))
    P("Differences: the 4 MANUAL journal exits (undocumented, inside the exit bar's range) and TIME_EOD fills, which the "
      "journal books at the bar open (0 ticks slippage) while this replay applies the brief's -1 tick to every market exit.")

    # ---------------- summary table ----------------
    base = np.array([r.net for r in o]); baseR = np.array([r.net_R for r in o])
    top_idx = np.argsort(-baseR)[: int(np.ceil(0.10 * n))]  # top 10% by baseline net R, fixed
    P(f"\nTop-10% winners = top {len(top_idx)} trades by BASELINE net R (fixed across policies): trade_ids {px.trade_id.values[top_idx].tolist()}")
    rows = []
    paired = {}
    for name, rr in res.items():
        net = np.array([r.net for r in rr]); netR = np.array([r.net_R for r in rr])
        dnet = net - base; dR = netR - baseR
        paired[name] = (dnet, dR)
        lo, hi = session_bootstrap(dR, N_BOOT, SEED)
        lo_d, hi_d = session_bootstrap(dnet, N_BOOT, SEED, stat=np.sum)
        reasons = pd.Series([r.exit_reason for r in rr]).value_counts().to_dict()
        rows.append(dict(policy=name, total_net_usd=net.sum(), mean_net_R=netR.mean(), win_pct=100 * (net > 0).mean(),
                         d_total_usd=dnet.sum(), d_usd_CI=f"[{lo_d:.0f},{hi_d:.0f}]", d_mean_R=dR.mean(),
                         d_R_CI=f"[{lo:.3f},{hi:.3f}]", trades_changed=int((np.abs(dnet) > 0.005).sum()),
                         worst_session_usd=net.min(), maxDD_usd=max_drawdown(net),
                         top10_usd=net[top_idx].sum(), top10_share=net[top_idx].sum() / net.sum() if net.sum() > 0 else np.nan,
                         mean_hold_min=np.mean([r.hold_min for r in rr]), both_touched=int(sum(r.both_touched for r in rr)),
                         exits=str(reasons)))
    summ = pd.DataFrame(rows)
    P("\n## Stage A paired summary (n = 92 trades = 92 sessions; net of $0.74/contract/side; session bootstrap "
      f"{N_BOOT} draws, 95% percentile CI on paired difference vs P0)")
    P(fmt_tbl(summ[["policy", "total_net_usd", "mean_net_R", "win_pct", "d_total_usd", "d_usd_CI", "d_mean_R", "d_R_CI",
                    "trades_changed", "worst_session_usd", "maxDD_usd", "top10_usd", "top10_share", "mean_hold_min", "both_touched"]], "{:.2f}"))
    P("\nExit-reason mix per policy:")
    for _, r in summ.iterrows():
        P(f"  {r.policy}: {r.exits}")
    P("Note: PX has exactly one trade per session, so the session bootstrap equals a trade bootstrap here. "
      "'both_touched' = trades where one bar touched both the (moved) stop and the target/partial level; ordering reported.")
    P(f"Overlap flag: longer-holding policies never overlap a LATER PX/KX entry in the same session (0 later entries after any PX entry); "
      f"{sum(1 for tr in px.itertuples() if ((trades.session == tr.session) & (trades.trade_id != tr.trade_id) & (trades.entry_ts < tr.exit_ts) & (trades.exit_ts > tr.entry_ts)).any())} "
      "PX trades already ran concurrently with an open KX trade under the original policy (position limit is Stage B's problem).")
    P(f"Partial-exit policy S_partial_quarter: {(px.initial_contracts == 1).sum()} 1-lot trades cannot scale out and are identical to P0; "
      f"only {(px.initial_contracts >= 2).sum()} trades (2- or 4-lot) are affected.")

    # ---------------- 'slow reversal is a bad reversal' ----------------
    pm = pd.DataFrame([path_metrics(tr, tb[int(tr.trade_id)], o[i]) for i, tr in enumerate(px.itertuples())])
    pm["net_R"] = baseR; pm["net"] = base; pm["target"] = np.array([r.exit_reason == "TARGET" for r in o])
    pm["session"] = px.session.values; pm["tgt_R"] = px.tgt_R.values
    P("\n## 'A slow reversal is a bad reversal' - conditional outcomes under the ORIGINAL policy (SYNTHETIC)")
    P("Threshold +0.3R measured intrabar (high/low) in planned-risk units; time = minute of the bar close that first reaches it.")
    bins = [(0, 5, "<=5 min"), (6, 10, "6-10"), (11, 20, "11-20"), (21, 60, "21-60"), (61, 999, ">60")]
    rows = []
    for a, b, lab in bins:
        m = pm.t_reach_03.between(a, b)
        rows.append(cell(lab, pm[m]))
    rows.append(cell("never reached +0.3R", pm[pm.t_reach_03.isna()]))
    rows.append(cell("ALL", pm))
    P(fmt_tbl(pd.DataFrame(rows), "{:.2f}"))
    P("\nDecision at minute k (trades still open at k under P0). 'fwd_R' = final net R minus the net R of a market exit at the open of minute k "
      "(policy T_k), i.e. what holding from k earned; CI = session bootstrap of the mean.")
    rows = []
    for k in (5, 10, 15, 20):
        opened = pm[pm[f"open_k{k}"]]
        tk = np.array([r.net_R for r in res[f"T{k}"]])
        for lab, m in (("reached +0.3R by k", opened[opened[f"reached03_k{k}"] == True]),  # noqa: E712
                       ("NOT reached +0.3R by k", opened[opened[f"reached03_k{k}"] == False])):  # noqa: E712
            c = cell(f"k={k}: {lab}", m)
            fwd = m.net_R.values - tk[m.index.values]
            c["fwd_R"] = fwd.mean() if len(fwd) else np.nan
            c["fwd_R_CI"] = "[%.2f,%.2f]" % session_bootstrap(fwd, N_BOOT, SEED) if len(fwd) > 1 else ""
            c["fwd_usd"] = (m.net.values - np.array([r.net for r in res[f"T{k}"]])[m.index.values]).sum()
            rows.append(c)
    P(fmt_tbl(pd.DataFrame(rows), "{:.2f}"))
    P("\nClose-based progress at minute 10 (the breakout-style rule's input), trades still open at minute 10:")
    rows = []
    op = pm[pm.open_k10]
    t10 = np.array([r.net_R for r in res["T10"]])
    for lab, m in (("close < 0R", op[op.close_k10 < 0]), ("0R <= close < 0.3R", op[(op.close_k10 >= 0) & (op.close_k10 < 0.3)]),
                   ("close >= 0.3R", op[op.close_k10 >= 0.3])):
        c = cell(lab, m)
        fwd = m.net_R.values - t10[m.index.values]
        c["fwd_R"] = fwd.mean() if len(fwd) else np.nan
        c["fwd_R_CI"] = "[%.2f,%.2f]" % session_bootstrap(fwd, N_BOOT, SEED) if len(fwd) > 1 else ""
        rows.append(c)
    P(fmt_tbl(pd.DataFrame(rows), "{:.2f}"))

    # brief's concrete scenario: >= +0.8R then back to <= +0.3R
    stall = 0; stall_far = 0
    for i, tr in enumerate(px.itertuples()):
        d = tb[int(tr.trade_id)]
        for rr, cnt in ((o[i], "o"), (res["S_far_target"][i], "f")):
            hold = rr.hold_min
            fav = (((d.high - tr.entry_px) if tr.sgn == 1 else (tr.entry_px - d.low)) / tr.stop_dist).values[: hold + 1]
            clo = ((d.close - tr.entry_px) * tr.sgn / tr.stop_dist).values[: hold + 1]
            hit = False
            for j in range(len(fav)):
                if fav[: j + 1].max() >= 0.8 and clo[j] <= 0.3:
                    hit = True; break
            if cnt == "o": stall += hit
            else: stall_far += hit
    P(f"\nBrief scenario (reached >= +0.8R intrabar, later closed <= +0.3R while still open): P0 = {stall}/{n} PX trades; "
      f"with the far target (S_far_target) = {stall_far}/{n}. The midpoint target (median 0.70R) removes most PX trades before +0.8R exists.")

    # ---------------- worked examples ----------------
    P("\n## Worked examples (SYNTHETIC EXAMPLE, real trade_ids from the development set)")
    npr = res["NP_k10_0.30R"]
    dd = pd.DataFrame({"trade_id": px.trade_id, "P0_net": base, "NP_net": [r.net for r in npr], "P0_reason": [r.exit_reason for r in o],
                       "NP_reason": [r.exit_reason for r in npr], "close_k10": pm.close_k10, "hold": [r.hold_min for r in o]})
    dd["d"] = dd.NP_net - dd.P0_net
    P("NP_k10_0.30R: worst false alarms (rule exited, original went on to win):")
    P(fmt_tbl(dd.sort_values("d").head(5), "{:.2f}"))
    P("NP_k10_0.30R: best saves (rule exited, original went on to lose):")
    P(fmt_tbl(dd.sort_values("d", ascending=False).head(5), "{:.2f}"))

    # ---------------- charts ----------------
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": PAL["muted"], "axes.labelcolor": PAL["ink2"],
                         "xtick.color": PAL["ink2"], "ytick.color": PAL["ink2"], "axes.spines.top": False, "axes.spines.right": False})
    # 1 paired differences
    show = [p for p in summ.policy if p != "S_stop_to_boundary_TGTFIRST"]
    s2 = summ.set_index("policy").loc[show]
    ci = s2.d_R_CI.str.strip("[]").str.split(",", expand=True).astype(float)
    fig, ax = plt.subplots(figsize=(8, 7.5), facecolor=PAL["surface"])
    ax.set_facecolor(PAL["surface"])
    y = np.arange(len(s2))
    cols = [PAL["s2"] if p.startswith("T") else PAL["s3"] if p.startswith("S_") else PAL["s4"] if p.startswith("NP") else PAL["s1"] for p in s2.index]
    ax.barh(y, s2.d_mean_R, color=cols, height=0.6)
    ax.errorbar(s2.d_mean_R, y, xerr=[s2.d_mean_R - ci[0], ci[1] - s2.d_mean_R], fmt="none", ecolor=PAL["ink2"], elinewidth=1, capsize=2)
    ax.axvline(0, color=PAL["muted"], lw=1)
    ax.set_yticks(y); ax.set_yticklabels(s2.index); ax.invert_yaxis()
    ax.set_xlabel("Mean paired difference vs original, net R per entry (95% session-bootstrap CI)")
    ax.set_title("SYNTHETIC - PX reversals, Stage A: every policy vs original bracket (n=92 trades/sessions)", color=PAL["ink"], loc="left")
    ax.grid(axis="x", color=PAL["grid"], lw=0.8); ax.set_axisbelow(True)
    for lab, c in (("time exits", PAL["s2"]), ("structural", PAL["s3"]), ("no-progress", PAL["s4"]), ("original", PAL["s1"])):
        ax.bar([0], [0], color=c, label=lab)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "S3_paired_policies.png"), dpi=130); plt.close(fig)
    # 2 slow reversal
    labs = [b[2] for b in bins] + ["never"]
    pt = []; mr = []; ns = []
    for a, b, lab in bins:
        m = pm[pm.t_reach_03.between(a, b)]; pt.append(m.target.mean() if len(m) else np.nan); mr.append(m.net_R.mean() if len(m) else np.nan); ns.append(len(m))
    m = pm[pm.t_reach_03.isna()]; pt.append(m.target.mean()); mr.append(m.net_R.mean()); ns.append(len(m))
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), facecolor=PAL["surface"])
    for ax, v, ttl in ((axs[0], pt, "P(exit at target)"), (axs[1], mr, "Mean net R per entry")):
        ax.set_facecolor(PAL["surface"]); ax.bar(labs, v, color=PAL["s1"], width=0.6)
        ax.set_title(ttl, loc="left", color=PAL["ink"]); ax.grid(axis="y", color=PAL["grid"], lw=0.8); ax.set_axisbelow(True)
        ax.axhline(0, color=PAL["muted"], lw=1)
        for i, (vv, nn) in enumerate(zip(v, ns)):
            ax.text(i, vv + (0.02 if vv >= 0 else -0.08), f"n={nn}", ha="center", color=PAL["ink2"], fontsize=8)
        ax.set_xlabel("minutes to first touch of +0.3R (original policy)")
    fig.suptitle("SYNTHETIC - PX: outcome by time to +0.3R (n per bar = trades = sessions)", x=0.01, ha="left", color=PAL["ink"])
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "S3_slow_reversal.png"), dpi=130); plt.close(fig)
    # 3 cumulative pnl
    fig, ax = plt.subplots(figsize=(8, 4), facecolor=PAL["surface"]); ax.set_facecolor(PAL["surface"])
    for name, c in (("P0_original", PAL["s1"]), ("T30", PAL["s2"]), ("S_far_target", PAL["s3"]), ("NP_k10_0.30R", PAL["s4"])):
        ax.plot(np.cumsum([r.net for r in res[name]]), color=c, lw=2, label=name)
    ax.set_xlabel("PX trade (chronological)"); ax.set_ylabel("cumulative net P&L, $ (after commissions)")
    ax.grid(color=PAL["grid"], lw=0.8); ax.set_axisbelow(True); ax.legend(frameon=False)
    ax.set_title("SYNTHETIC - PX cumulative net P&L, four policies", loc="left", color=PAL["ink"])
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "S3_cum_pnl.png"), dpi=130); plt.close(fig)

    with open(os.path.join(HERE, "output.txt"), "w") as fh:
        fh.write("\n".join(_out) + "\n")


def cell(label, m: pd.DataFrame) -> dict:
    d = dict(group=label, trades=len(m), sessions=int(m.session.nunique()) if len(m) else 0)
    if len(m):
        d["P_target"] = m.target.mean(); d["mean_net_R"] = m.net_R.mean()
        d["net_R_CI"] = "[%.2f,%.2f]" % session_bootstrap(m.net_R.values, N_BOOT, SEED) if len(m) > 1 else ""
        d["net_usd"] = m.net.sum(); d["mean_target_R"] = m.tgt_R.mean()
    return d


if __name__ == "__main__":
    main()
