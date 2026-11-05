#!/usr/bin/env python3
"""Reference run of the pre-registered policies (prereg/challengers.md) with the S5 engine.

Runs on a data directory (development or sealed holdout): Stage A paired replay of P0 and C1-C4 plus
diagnostics D1-D4, the fill-assumption grid, comparison-table metrics, profit-vs-protection accounting,
and Stage B (chronological, 4-contract limit, rejected signals eligible) for P0 and every challenger.

Usage: python3 holdout_run.py --data sealed/holdout --tag holdout
"""
import argparse, os, sys, math
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "S5"))
import replay as R  # noqa: E402


# ---------------------------------------------------------------- custom rules (pre-registered)
class StallBreakeven(R.Rule):
    """C1: once closed-bar MFE >= trig_R and the last closed bar's close <= stall_R, stop of all legs -> entry."""
    def __init__(self, trig_R=0.8, stall_R=0.3, action="BE"):
        self.trig_R, self.stall_R, self.action, self.fired = trig_R, stall_R, action, False

    def on_bar_open(self, state, i):
        if i == 0 or self.fired:
            return []
        if state.progress_R(i, "extreme") >= self.trig_R and state.progress_R(i, "close") <= self.stall_R:
            self.fired = True
            state.stall_bar = i
            if self.action == "EXIT":
                return [R.ExitAction("all", "STALL_EXIT")]
            return [R.SetStop(state.legs[0].entry_px, "all", "STOP_BE")]
        return []


class LateCondBreakeven(R.Rule):
    """C2: at minute k (open of bar index k), if close of the last closed bar >= min_R, stop of all legs -> entry."""
    def __init__(self, minute=20, min_R=0.3):
        self.minute, self.min_R, self.fired = minute, min_R, False

    def on_bar_open(self, state, i):
        if i == self.minute and state.progress_R(i, "close") >= self.min_R:
            self.fired = True
            state.cond_bar = i
            return [R.SetStop(state.legs[0].entry_px, "all", "STOP_BE")]
        return []


class AddStopAtEntry(R.Rule):
    """C3: the add leg gets its own stop at the ORIGINAL entry price."""
    def on_add(self, state, leg):
        leg.stop_px = float(R.round_tick(state.legs[0].entry_px)); leg.stop_label = "STOP_ADD"
        state.add_protected = True


class FarTarget(R.Rule):
    """C4 (PX only): target at the opposite OR boundary = or_mid + sgn * ref_width/2."""
    def on_entry(self, state):
        e = state.entry
        if e.family != "PX":
            return
        px = e.levels["or_mid"] + e.sgn * e.levels["ref_width"] / 2.0
        for leg in state.legs:
            leg.target_px = float(R.round_tick(px))


def policies():
    add = R.KXAddRule
    return {
        "P0": R.OriginalBracket("P0"),
        "C1_stall_BE": R.Policy("C1_stall_BE", [StallBreakeven(0.8, 0.3, "BE")], add()),
        "C2_late_BE20": R.Policy("C2_late_BE20", [LateCondBreakeven(20, 0.3)], add()),
        "C3_add_stop_entry": R.Policy("C3_add_stop_entry", [AddStopAtEntry()], add()),
        "C4_PX_far_target": R.Policy("C4_PX_far_target", [FarTarget()], add()),
        "D1_KX_notarget_BE2R": R.Policy("D1_KX_notarget_BE2R", [R.StructuralTarget(None), R.BreakevenStop(2.0)], add()),
        "D2_PX_notarget": R.Policy("D2_PX_notarget", [R.StructuralTarget(None)], add()),
        "D3_stall_EXIT": R.Policy("D3_stall_EXIT", [StallBreakeven(0.8, 0.3, "EXIT")], add()),
        "D4_fail15": R.Policy("D4_fail15", [R.NoProgressExit(15, 0.0, "close")], add()),
        "D4b_time15": R.Policy("D4b_time15", [R.TimeExit(15)], add()),
    }


FAMILY = {"C4_PX_far_target": "PX", "D2_PX_notarget": "PX"}   # others KX; P0 both


def simulate(entry, data, pol, fm):
    bt = R.trade_bars(data, fm.trigger_instrument, entry.session, entry.entry_time)
    bp = bt if fm.price_instrument == fm.trigger_instrument else R.trade_bars(data, fm.price_instrument, entry.session, entry.entry_time)
    sim = R.TradeSim(entry, bt, bp, pol, fm)
    sim.stall_bar = None; sim.cond_bar = None; sim.add_protected = False
    res = sim.run().row()
    res["stall_bar"], res["cond_bar"], res["add_protected"] = sim.stall_bar, sim.cond_bar, sim.add_protected
    return res


def stage_a(data, fm, pols):
    entries = R.entries_from_trades(data)
    out = {}
    for name, pol in pols.items():
        fam = FAMILY.get(name, "KX") if name != "P0" else None
        rows = [simulate(e, data, pol, fm) for e in entries if fam is None or e.family == fam]
        out[name] = pd.DataFrame(rows).set_index("trade_id")
    return out


def max_dd(df):
    cum = df.sort_values("entry_time").net_usd.cumsum()
    return float((cum - cum.cummax()).min())


def metrics(base, alt, fam):
    """Comparison-table row for `alt` on the baseline-defined family set."""
    b = base[base.family == fam]; a = alt.loc[b.index]
    d = a.net_usd - b.net_usd; dR = a.net_R - b.net_R
    sess = pd.DataFrame(dict(session=b.session, d=d, aR=a.net_R, a=a.net_usd))
    top = b.net_R.sort_values(ascending=False).head(max(1, int(round(0.1 * len(b))))).index  # baseline-fixed top 10%
    bs_usd = R.session_bootstrap(pd.DataFrame(dict(session=b.session, v=d)), "v", agg="sum")
    bs_R = R.session_bootstrap(pd.DataFrame(dict(session=b.session, v=dR)), "v", agg="mean")
    changed = d.abs() > 0.005
    losers = b.net_usd < 0
    return dict(
        trades=len(b), sessions=b.session.nunique(), net_usd=round(a.net_usd.sum(), 0), mean_R=round(a.net_R.mean(), 3),
        d_usd=round(d.sum(), 0), d_usd_lo=round(bs_usd["lo"], 0), d_usd_hi=round(bs_usd["hi"], 0),
        dR_entry=round(dR.mean(), 3), dR_lo=round(bs_R["lo"], 3), dR_hi=round(bs_R["hi"], 3),
        worst_session=round(sess.groupby("session").a.sum().min(), 0), max_dd=round(max_dd(a), 0),
        changed=int(changed.sum()),
        losses_avoided_usd=round(d[changed & losers & (d > 0)].sum(), 0), n_losses_avoided=int((changed & losers & (d > 0)).sum()),
        winners_cut_usd=round(d[changed & ~losers & (d < 0)].sum(), 0), n_winners_cut=int((changed & ~losers & (d < 0)).sum()),
        losers_worsened_usd=round(d[changed & losers & (d < 0)].sum(), 0), winners_improved_usd=round(d[changed & ~losers & (d > 0)].sum(), 0),
        top10_usd_base=round(b.net_usd.loc[top].sum(), 0), top10_usd_alt=round(a.net_usd.loc[top].sum(), 0),
        top10_cut=int((d.loc[top] < -0.005).sum()), n_top10=len(top),
        pct_benefit_top3_sessions=(round(100 * sess.groupby("session").d.sum().sort_values(ascending=False).head(3).sum() / d.sum(), 0) if abs(d.sum()) > 1 else np.nan),
        top5_sessions=";".join(f"{s}:{v:+.0f}" for s, v in sess.groupby("session").d.sum().abs().sort_values(ascending=False).head(5).items()),
    )


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--tag", required=True)
    ap.add_argument("--stage_b", action="store_true"); a = ap.parse_args()
    data = R.load_data(a.data, require_trades=True)
    pols = policies()
    out_dir = os.path.join(HERE, "out"); os.makedirs(out_dir, exist_ok=True)
    lines = [f"# Reference run ({a.tag}) — {a.data}  [SYNTHETIC]", ""]
    fm = R.FillModel.reference()
    res = stage_a(data, fm, pols)
    base = res["P0"]
    lines.append(f"Trades {len(base)}, sessions {base.session.nunique()}; KX {int((base.family=='KX').sum())}, PX {int((base.family=='PX').sum())}; "
                 f"strategy versions: {base.strategy.value_counts().to_dict()}")
    lines.append(f"P0 net ${base.net_usd.sum():,.0f} (journal ${data.trades.net_pnl_usd.sum():,.0f}); KX mean R {base[base.family=='KX'].net_R.mean():+.3f}, PX mean R {base[base.family=='PX'].net_R.mean():+.3f}")
    # comparison table
    rows = []
    for name in pols:
        if name == "P0":
            for fam in ("KX", "PX"):
                b = base[base.family == fam]; top = b.net_R.sort_values(ascending=False).head(max(1, int(round(0.1 * len(b))))).index
                rows.append(dict(policy="P0", family=fam, trades=len(b), sessions=b.session.nunique(), net_usd=round(b.net_usd.sum(), 0),
                                 mean_R=round(b.net_R.mean(), 3), worst_session=round(b.groupby("session").net_usd.sum().min(), 0),
                                 max_dd=round(max_dd(b), 0), top10_usd_base=round(b.net_usd.loc[top].sum(), 0), n_top10=len(top)))
            continue
        fam = FAMILY.get(name, "KX")
        rows.append(dict(policy=name, family=fam, **metrics(base, res[name], fam)))
    comp = pd.DataFrame(rows); comp.to_csv(os.path.join(out_dir, f"comparison_{a.tag}.csv"), index=False)
    # per-trade paired results for every policy (for session attribution and charts)
    per = base[["session", "strategy", "family", "direction", "planned_risk_usd", "net_usd", "net_R", "exit_reason", "minutes_held"]].rename(
        columns={"net_usd": "P0_net_usd", "net_R": "P0_net_R", "exit_reason": "P0_exit", "minutes_held": "P0_min"})
    for name in pols:
        if name == "P0":
            continue
        r = res[name].reindex(base.index)
        per[f"{name}__net_usd"] = r.net_usd; per[f"{name}__net_R"] = r.net_R; per[f"{name}__exit"] = r.exit_reason
        per[f"{name}__d_usd"] = r.net_usd - base.net_usd
        if "stall_bar" in r: per[f"{name}__stall_bar"] = r.stall_bar
    per.to_csv(os.path.join(out_dir, f"per_trade_{a.tag}.csv"))
    lines += ["", "## Stage A comparison table (reference fill model; paired on identical entries; costs on every fill)", "",
              comp.drop(columns=["top5_sessions"]).to_markdown(index=False), ""]
    lines += ["### Five sessions contributing most to each paired difference (session: paired Δ$)", ""]
    for r in rows:
        if r["policy"] != "P0":
            lines.append(f"- {r['policy']}: {r['top5_sessions']}")
    # conditional sets
    c1 = res["C1_stall_BE"]; m = c1.stall_bar.notna()
    sub = pd.DataFrame(dict(session=c1.session[m], dR=(c1.net_R - base.net_R.loc[c1.index])[m], strategy=c1.strategy[m]))
    bs = R.session_bootstrap(sub, "dR")
    d3 = res["D3_stall_EXIT"]; sub3 = pd.DataFrame(dict(session=d3.session[m], dR=(d3.net_R - base.net_R.loc[d3.index])[m]))
    bs3 = R.session_bootstrap(sub3, "dR")
    lines += ["", "## The user's decision: KX reached >= +0.8R then closed <= +0.3R (stall set, trades still open under P0)", "",
              f"- stall set n = {int(m.sum())} trades / {sub.session.nunique()} sessions; P0 mean R {base.net_R.loc[c1.index][m].mean():+.3f}",
              f"- C1 tighten to breakeven: mean R {c1.net_R[m].mean():+.3f}; paired ΔR {bs['point']:+.3f} [{bs['lo']:+.2f}, {bs['hi']:+.2f}]",
              f"- D3 exit now: mean R {d3.net_R[m].mean():+.3f}; paired ΔR {bs3['point']:+.3f} [{bs3['lo']:+.2f}, {bs3['hi']:+.2f}]",
              f"- P(final R < -0.5R): P0 {(base.net_R.loc[c1.index][m] < -0.5).mean():.2f}, C1 {(c1.net_R[m] < -0.5).mean():.2f}"]
    for sv, g in sub.groupby("strategy"):
        b2 = R.session_bootstrap(g, "dR"); lines.append(f"  - {sv}: n={len(g)} ΔR {b2['point']:+.3f} [{b2['lo']:+.2f}, {b2['hi']:+.2f}]")
    c2 = res["C2_late_BE20"]; m2 = c2.cond_bar.notna()
    bK = base.loc[c2.index]
    sub2 = pd.DataFrame(dict(session=c2.session[m2], dR=(c2.net_R - bK.net_R)[m2]))
    bs2 = R.session_bootstrap(sub2, "dR")
    q = bK.net_R[m2].quantile(0.1)
    lines += ["", "## C2 conditioned set (open at minute 20 with close >= +0.3R)", "",
              f"- n = {int(m2.sum())} / {sub2.session.nunique()} sessions; paired ΔR {bs2['point']:+.3f} [{bs2['lo']:+.2f}, {bs2['hi']:+.2f}]",
              f"- P(R < -0.5R): P0 {(bK.net_R[m2] < -0.5).mean():.2f} -> C2 {(c2.net_R[m2] < -0.5).mean():.2f}; worst-decile mean R: P0 {bK.net_R[m2][bK.net_R[m2] <= q].mean():+.2f} -> C2 {c2.net_R[m2][bK.net_R[m2] <= q].mean():+.2f}"]
    c3 = res["C3_add_stop_entry"]; m3 = c3.add_protected
    bK3 = base.loc[c3.index]
    sub3b = pd.DataFrame(dict(session=c3.session[m3], d=(c3.net_usd - bK3.net_usd)[m3]))
    bs3b = R.session_bootstrap(sub3b, "d", agg="sum") if m3.sum() else dict(point=0, lo=0, hi=0)
    # P(target | retrace to entry after add) under P0, on add trades
    lines += ["", "## C3 add trades", "",
              f"- add trades n = {int(m3.sum())} / {sub3b.session.nunique()} sessions; paired Δ$ {bs3b['point']:+,.0f} [{bs3b['lo']:+,.0f}, {bs3b['hi']:+,.0f}]",
              f"- worst session KX: P0 {bK3.groupby('session').net_usd.sum().min():,.0f} -> C3 {c3.groupby('session').net_usd.sum().min():,.0f}; max DD KX: P0 {max_dd(bK3):,.0f} -> C3 {max_dd(c3):,.0f}",
              f"- among add trades, C3 changed {int(((c3.net_usd - bK3.net_usd).abs() > 0.005)[m3].sum())}; of those originally TARGET: {int(((c3.net_usd - bK3.net_usd).abs() > 0.005)[m3 & (bK3.exit_reason == 'TARGET')].sum())}"]
    # fill grid
    lines += ["", "## Fill-assumption grid (paired Δ$ vs P0 under the same fill model; KX candidates on KX, C4 on PX)", ""]
    grid = []
    variants = {"reference": {}, "penetrate_stop": dict(stop_trigger="penetrate"), "slip0": dict(slippage_ticks_market=0, slippage_ticks_stop=0, slippage_ticks_gap=0),
                "slip2": dict(slippage_ticks_market=2, slippage_ticks_stop=2, slippage_ticks_gap=2), "target_first": dict(same_bar_order="target_first"),
                "no_bracket_entry_bar": dict(bracket_in_entry_bar=False)}
    for vn, kw in variants.items():
        fmv = R.FillModel.reference(**kw)
        rv = stage_a(data, fmv, {k: pols[k] for k in ["P0", "C1_stall_BE", "C2_late_BE20", "C3_add_stop_entry", "C4_PX_far_target", "D1_KX_notarget_BE2R"]})
        row = dict(variant=vn)
        for k in ["C1_stall_BE", "C2_late_BE20", "C3_add_stop_entry", "C4_PX_far_target", "D1_KX_notarget_BE2R"]:
            fam = FAMILY.get(k, "KX"); bb = rv["P0"][rv["P0"].family == fam]; aa = rv[k].loc[bb.index]
            row[k] = round((aa.net_usd - bb.net_usd).sum(), 0)
            row[k + "_amb"] = int(aa.both_touched_bars.sum())
        grid.append(row)
    g = pd.DataFrame(grid); g.to_csv(os.path.join(out_dir, f"fillgrid_{a.tag}.csv"), index=False)
    lines += [g.to_markdown(index=False), "", "(`_amb` = bars in which a live stop and a live target were both touched; 0 means ordering is moot)"]
    # Stage B
    if a.stage_b:
        lines += ["", "## Stage B (chronological, position limit 4, rejected signals eligible, reference fill model)", ""]
        sb = []
        for k in ["P0", "C1_stall_BE", "C2_late_BE20", "C3_add_stop_entry", "C4_PX_far_target", "D1_KX_notarget_BE2R"]:
            r, lg = R.run_stage_b(data, pols[k], fm)
            sb.append(dict(policy=k, executed=int(lg.executed.sum()), rejected=int((~lg.executed).sum()), net_usd=round(r.net_usd.sum(), 0),
                           max_dd=round(max_dd(r), 0), worst_session=round(r.groupby("session").net_usd.sum().min(), 0),
                           blocked_vs_export=int((lg.executed_in_export & ~lg.executed).sum()), freed_vs_export=int((~lg.executed_in_export & lg.executed).sum())))
        sbd = pd.DataFrame(sb); sbd["d_net_vs_P0"] = sbd.net_usd - sbd.net_usd.iloc[0]
        sbd.to_csv(os.path.join(out_dir, f"stageb_{a.tag}.csv"), index=False)
        lines += [sbd.to_markdown(index=False)]
    txt = "\n".join(lines)
    with open(os.path.join(out_dir, f"reference_run_{a.tag}.md"), "w") as f:
        f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
