"""
S5 runner: regenerates every table in reports/S5_replay_engine.md from data/synthetic/.

    python3 src/S5/run.py [data_dir] [out_dir]

Sections printed (markdown) and saved to out_dir/run_output.md:
  1. verification checklist (instrument basis, tick rounding, session cutoff, gaps,
     same-bar stop/target, UTC/ET alignment, costs on every leg)
  2. reconciliation of the original policy vs trades.csv / fills.csv
  3. exact-touch ambiguity and same-bar ordering sensitivity for a tightened-stop policy
  4. Stage A demonstration (original vs time exit vs breakeven, KX and PX separately)
  5. Stage B demonstration (chronological replay with position limit)
  6. fill-assumption variants for the original policy
All numbers are SYNTHETIC (development set only).
"""
from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay as R  # noqa: E402
import reconcile as C  # noqa: E402


def section_verification(d: R.Data):
    tr, fi, sg = d.trades, d.fills, d.signals
    mnq, nq = d.bars["MNQ"], d.bars["NQ"]
    print("## 1. Verification checklist (OBSERVED on SYNTHETIC development data)\n")

    # 1.1 instrument basis ---------------------------------------------------------------------
    print("### 1.1 Signal instrument (NQ) vs execution instrument (MNQ)\n")
    basis = pd.DataFrame({c: (nq[c] - mnq[c]) for c in ("open", "high", "low", "close")})
    b = pd.DataFrame({"mean_pts": basis.mean(), "std_pts": basis.std(), "max_abs_pts": basis.abs().max(),
                      "pct_bars_nonzero": (basis != 0).mean() * 100}).round(4)
    print(f"Bars: {len(mnq)} per instrument, {len(d.sessions)} sessions (bars file), "
          f"{tr.session.nunique()} sessions with trades, {sg.session.nunique()} sessions with signals.\n")
    print(R.md_table(b), "\n")
    tr = tr.copy()
    tr["mnq_open"] = mnq.loc[tr.entry_t, "open"].to_numpy()
    tr["nq_open"] = nq.loc[tr.entry_t, "open"].to_numpy()
    sm = ((tr.entry_px - tr.mnq_open) * tr.sgn / R.TICK).round(2)
    sn = ((tr.entry_px - tr.nq_open) * tr.sgn / R.TICK).round(2)
    print("Entry fill minus bar open (adverse ticks), by instrument:\n")
    t = pd.DataFrame({"vs MNQ open": sm.value_counts().sort_index(), "vs NQ open": sn.value_counts().sort_index()}).fillna(0).astype(int)
    t.index.name = "ticks"
    print(R.md_table(t), "\n")
    # dollar impact of pricing every MKT fill off NQ instead of MNQ
    f = fi.copy()
    f["side_sgn"] = np.where(f.side == "BUY", 1, -1)
    mk = f[f.order_type == "MKT"].copy()
    mk["mnq_open"] = mnq.loc[mk.t, "open"].to_numpy()
    mk["nq_open"] = nq.loc[mk.t, "open"].to_numpy()
    mk["model_px_mnq"] = mk.mnq_open + mk.side_sgn * R.TICK
    mk["model_px_nq"] = mk.nq_open + mk.side_sgn * R.TICK
    mk["cash_diff_vs_mnq_model"] = -(mk.price - mk.model_px_mnq) * mk.side_sgn * mk.qty * R.POINT_VALUE
    exact_nq = int(np.isclose(mk.price, mk.model_px_nq).sum())
    exact_mnq = int(np.isclose(mk.price, mk.model_px_mnq).sum())
    non_manual = mk[mk.exit_reason.fillna("") != "MANUAL"]
    print(f"Market-order fills (ENTRY/ADD/TIME_EOD/STOP_GAP/MANUAL): {len(mk)}. Equal to NQ open +1 tick adverse: {exact_nq}; "
          f"equal to MNQ open +1 tick adverse: {exact_mnq}. Excluding the {int((mk.exit_reason=='MANUAL').sum())} MANUAL fills, "
          f"{int(np.isclose(non_manual.price, non_manual.model_px_nq).sum())}/{len(non_manual)} equal NQ open +1 tick.")
    print(f"Dollar effect of the NQ pricing vs an MNQ-open+1-tick model, summed over the {len(non_manual)} non-MANUAL market fills: "
          f"${non_manual.cash_diff_vs_mnq_model.sum():+.2f} (sum of absolute per-fill differences ${non_manual.cash_diff_vs_mnq_model.abs().sum():.2f}).\n")

    # 1.2 tick rounding ------------------------------------------------------------------------
    print("### 1.2 Tick rounding\n")
    off = {k: int(((v[["open", "high", "low", "close"]] / R.TICK).round() != v[["open", "high", "low", "close"]] / R.TICK).sum().sum())
           for k, v in d.bars.items()}
    off_fills = int(((fi.price / R.TICK).round() != fi.price / R.TICK).sum())
    s = sg.set_index("signal_id")
    dist = s.loc[tr.signal_id, "planned_stop_dist_pts"].to_numpy()
    stop_ok = int(np.isclose(tr.entry_px - tr.sgn * R.round_tick(dist), tr.initial_stop_px).sum())
    kx = tr.family == "KX"
    mult = s.loc[tr.signal_id, "planned_target_mult_R"].to_numpy()
    tgt_kx_ok = int(np.isclose(tr.entry_px[kx] + tr.sgn[kx] * R.round_tick(mult[kx] * dist[kx]), tr.initial_target_px[kx]).sum())
    tgt_kx_alt = int(np.isclose(tr.entry_px[kx] + tr.sgn[kx] * mult[kx] * R.round_tick(dist[kx]), tr.initial_target_px[kx]).sum())
    px = tr.family == "PX"
    tgt_px_ok = int(np.isclose(s.loc[tr.signal_id[px], "planned_target_px"].to_numpy(), tr.initial_target_px[px]).sum())
    risk_raw = tr.initial_contracts * dist * R.POINT_VALUE
    risk_rt = tr.initial_contracts * R.round_tick(dist) * R.POINT_VALUE
    vers_mult = {k: v for k, v in d.target_mult.items()}
    sig_mult = s.groupby("strategy").planned_target_mult_R.unique().to_dict()
    print(f"- Off-grid bar prices: {off}; off-grid fill prices: {off_fills}.")
    print(f"- initial_stop_px == entry -/+ round_tick(planned_stop_dist_pts): {stop_ok}/{len(tr)}.")
    print(f"- KX initial_target_px == entry +/- round_tick(mult x raw dist): {tgt_kx_ok}/{int(kx.sum())} "
          f"(alternative mult x round_tick(dist): {tgt_kx_alt}); PX target == planned_target_px: {tgt_px_ok}/{int(px.sum())}.")
    print(f"- Target multiples parsed from strategy_versions.csv: {vers_mult}; in signals.csv: { {k: list(v) for k, v in sig_mult.items()} }.")
    print(f"- planned_risk_usd == contracts x UNROUNDED dist x $2: {int(np.isclose(tr.planned_risk_usd, risk_raw.round(2)).sum())}/{len(tr)}; "
          f"max |planned_risk - risk at the tick-rounded stop| = ${np.abs(tr.planned_risk_usd - risk_rt).max():.2f} "
          f"(1R is the planned, unrounded figure; the executable stop differs by <= 0.125 pt).")
    print(f"- Sizing floor($200/(dist x $2)) clipped [1,4] reproduces initial_contracts: "
          f"{int((np.clip(np.floor(200/(dist*2)),1,4)==tr.initial_contracts).sum())}/{len(tr)}.\n")

    # 1.3 session cutoff -----------------------------------------------------------------------
    print("### 1.3 Session cutoff\n")
    eod = tr[tr.exit_reason == "TIME_EOD"]
    late = tr[tr.exit_t.dt.time >= pd.Timestamp("15:55").time()]
    print(f"- Latest exit bar: {tr.exit_t.dt.time.max()}; trades exiting at/after 15:55: {len(late)}, all TIME_EOD: {bool((late.exit_reason=='TIME_EOD').all())}; "
          f"TIME_EOD trades: {len(eod)}, exit price == NQ 15:55 open +1 tick adverse: "
          f"{int(np.isclose(eod.exit_px, nq.loc[eod.exit_t,'open'].to_numpy() - eod.sgn*R.TICK).sum())}/{len(eod)}.")
    print(f"- Bars per session: {mnq.groupby('session').size().unique().tolist()} (09:30-15:59); last entry time {tr.entry_t.dt.time.max()}; "
          f"last signal time {sg.signal_t.dt.time.max()}; latest add {tr.add_t.dropna().dt.time.max()} (rule: before 12:00).")
    print(f"- Bracket fills in the 15:55-15:59 bars: {int(((fi.t.dt.time >= pd.Timestamp('15:55').time()) & fi.order_type.isin(['STP','LMT'])).sum())}.\n")

    # 1.4 gaps ---------------------------------------------------------------------------------
    print("### 1.4 Gaps through stops\n")
    g = tr[tr.exit_reason == "STOP_GAP"].copy()
    g["nq_open"] = nq.loc[g.exit_t, "open"].to_numpy()
    g["mnq_open"] = mnq.loc[g.exit_t, "open"].to_numpy()
    g["gap_beyond_stop_ticks"] = ((g.nq_open - g.initial_stop_px) * (-g.sgn) / R.TICK)
    g["fill_vs_open_ticks"] = ((g.exit_px - g.nq_open) * (-g.sgn) / R.TICK)
    prev_touch = []
    for r in g.itertuples():
        b = nq.loc[r.entry_t]
        prev_touch.append(bool((b.low <= r.initial_stop_px) if r.sgn == 1 else (b.high >= r.initial_stop_px)))
    g["stop_touched_in_entry_bar"] = prev_touch
    print(R.md_table(g[["session", "direction", "entry_t", "exit_t", "initial_stop_px", "nq_open", "exit_px", "gap_beyond_stop_ticks",
                        "fill_vs_open_ticks", "stop_touched_in_entry_bar", "net_pnl_usd"]].assign(
        entry_t=lambda x: x.entry_t.dt.strftime("%H:%M"), exit_t=lambda x: x.exit_t.dt.strftime("%H:%M")), index=False), "\n")
    print("Fill convention observed: gap fills at the exit-bar open +1 tick adverse (the brief says 'bar open'; both are parameters). "
          "Two of the three gaps are really stop touches inside the entry bar that the generator ignored (bracket not armed until the next bar).\n")

    # 1.6 UTC / ET -----------------------------------------------------------------------------
    print("### 1.6 UTC/ET alignment\n")
    ent = fi[fi.fill_role == "ENTRY"].set_index("trade_id")
    ex = fi[fi.fill_role == "EXIT"].groupby("trade_id").t.max()
    t2 = tr.set_index("trade_id")
    print(f"- fills.csv ts_utc -> ET equals trades.csv entry_ts: {int((ent.t == t2.entry_t).sum())}/{len(t2)}; "
          f"entry fill time is a bar-open timestamp in bars_MNQ: {int(ent.t.isin(mnq.index).sum())}/{len(ent)}; "
          f"entry bar == signal bar (signal_ts = previous bar's close = this bar's open): {int((t2.entry_t == sg.set_index('signal_id').loc[t2.signal_id,'signal_t'].to_numpy()).sum())}/{len(t2)}.")
    print(f"- last EXIT fill time == trades.csv exit_ts: {int((ex == t2.exit_t).sum())}/{len(t2)}; ADD fill time == add_ts: "
          f"{int((fi[fi.fill_role=='ADD'].set_index('trade_id').t == t2.add_t.dropna()).sum())}/{int(t2.add_t.notna().sum())}.")
    offs = pd.Series(mnq.index.strftime("%z")).value_counts().to_dict()
    print(f"- ET offsets present in bars: {offs} (DST handled by tz conversion, not by a fixed offset); "
          f"fills.csv hours in UTC: {sorted(pd.to_datetime(fi.ts_utc).dt.hour.unique().tolist())}.\n")

    # 1.7 costs --------------------------------------------------------------------------------
    print("### 1.7 Costs on every leg\n")
    print(f"- fills.csv commission == $0.74 x qty on every fill: {int(np.isclose(fi.commission, 0.74*fi.qty).sum())}/{len(fi)}; "
          f"trades.csv commission == 0.74 x 2 x (initial + added): {int(np.isclose(tr.commission_usd, 0.74*2*(tr.initial_contracts+tr.added_contracts)).sum())}/{len(tr)}; "
          f"net == gross - commission: {int(np.isclose(tr.net_pnl_usd, tr.gross_pnl_usd-tr.commission_usd).sum())}/{len(tr)}.")
    fg = fi.copy(); fg["cash"] = -np.where(fg.side == "BUY", 1, -1) * fg.qty * fg.price * R.POINT_VALUE
    gross = fg.groupby("trade_id").cash.sum()
    print(f"- gross from fills == trades.csv gross: {int(np.isclose(gross.reindex(t2.index), t2.gross_pnl_usd).sum())}/{len(t2)}. "
          f"The replay charges `commission_per_side x qty` on every Fill object (entry, add, each leg's exit), so a policy that exits legs "
          f"separately pays two exit commissions.\n")


def section_same_bar(d: R.Data):
    print("## 3. Same-bar stop/target touches and exact-touch ambiguity (SYNTHETIC)\n")
    ents = R.entries_from_trades(d)
    fm = R.FillModel.reference()
    base = [R.simulate_trade(e, d, R.OriginalBracket(), fm) for e in ents]
    nb = sum(r.both_touched_bars for r in base)
    amb = sum(r.exit_bar_ambiguous for r in base)
    # bars during holds spanning both levels (any bar, not only the exit bar)
    span = 0
    for e, r in zip(ents, base):
        b = R.trade_bars(d, "MNQ", e.session, e.entry_time).iloc[: r.minutes_held + 1]
        s = e.sgn
        both = ((b.low <= e.stop_px) & (b.high >= e.target_px)) if s == 1 else ((b.high >= e.stop_px) & (b.low <= e.target_px))
        span += int(both.sum())
    print(f"- Original bracket, reference model: exit bars that touched both stop and target: {amb}/{len(base)}; "
          f"bars during holds whose range spanned both levels: {span}. (Stop and target are >= 2.4R apart, wider than any 1-min bar here.)")
    # exact-touch ambiguity: trades where first touch bar != first penetration bar for the actual exit level
    tr = d.trades.set_index("trade_id")
    rows = []
    for e in ents:
        a = tr.loc[e.trade_id]
        if a.exit_reason not in ("STOP", "TARGET"):
            continue
        lvl = e.stop_px if a.exit_reason == "STOP" else e.target_px
        for ins in ("MNQ", "NQ"):
            b = R.trade_bars(d, ins, e.session, e.entry_time).iloc[1:]
            adv = (b.low if e.sgn == 1 else b.high) if a.exit_reason == "STOP" else (b.high if e.sgn == 1 else b.low)
            sgn = -e.sgn if a.exit_reason == "STOP" else e.sgn
            touch = (adv - lvl) * sgn >= 0
            pen = (adv - lvl) * sgn > 0
            if touch.any() and (not pen.any() or touch.idxmax() != pen.idxmax()):
                rows.append(dict(trade_id=e.trade_id, instrument=ins, level=a.exit_reason, first_touch=touch.idxmax().strftime("%H:%M"),
                                 first_penetration=(pen.idxmax().strftime("%H:%M") if pen.any() else None),
                                 actual_exit=a.exit_t.strftime("%H:%M"), fired_on_touch=bool(a.exit_t == touch.idxmax())))
    amb_df = pd.DataFrame(rows)
    print(f"- Exact-touch events on the actual exit level before penetration (baseline STOP/TARGET trades): "
          f"{len(amb_df)} instrument-events on {amb_df.trade_id.nunique()} trades; on NQ (the generator's trigger bars) "
          f"{int((amb_df.instrument=='NQ').sum())} events of which the exit fired on the touch in {int(amb_df[amb_df.instrument=='NQ'].fired_on_touch.sum())}. "
          f"A 1-minute bar cannot say whether a level printed exactly at its extreme was traded through.\n")
    print(R.md_table(amb_df[amb_df.instrument == "NQ"], index=False), "\n")
    # tightened-stop policy under the orderings
    pol = R.Policy("trail_0.5R_after_0.8R", [R.TrailingStop(trail_R=0.5, activate_R=0.8)], R.KXAddRule(),
                   "KX add as original; once closed-bar extreme >= +0.8R, stop trails 0.5R behind the best closed extreme")
    out = []
    for order in ("stop_first", "target_first", "worst", "ohlc"):
        fmo = R.FillModel.reference(same_bar_order=order)
        rs = [R.simulate_trade(e, d, pol, fmo) for e in ents]
        df = pd.DataFrame([r.row() for r in rs])
        out.append(dict(ordering=order, trades=len(df), sessions=df.session.nunique(), net_usd_sum=round(df.net_usd.sum(), 2),
                        net_R_mean=round(df.net_R.mean(), 4), ambiguous_exit_bars=int(df.exit_bar_ambiguous.sum()),
                        bars_both_touched=int(df.both_touched_bars.sum())))
    print(f"Tightened-stop policy `{pol.name}` ({pol.description}) under each same-bar ordering, reference model otherwise:\n")
    print(R.md_table(pd.DataFrame(out), index=False), "\n")
    print("`worst` equals `stop_first` whenever the live stop is below the target (always, for a long); it differs only for "
          "policies that place an exit order on the favourable side of another. `ohlc` assumes the bar moved toward its close last.\n")


def section_stage_a(d: R.Data, out_dir: str):
    print("## 4. Stage A demonstration: identical entries, paired (SYNTHETIC, costs included, reference fill model)\n")
    pols = [R.OriginalBracket("original"),
            R.Policy("time_exit_30", [R.TimeExit(30)], R.KXAddRule(), "exit all at the open of minute 30 after entry (bracket live until then)"),
            R.Policy("breakeven_0.8R", [R.BreakevenStop(0.8)], R.KXAddRule(), "after a closed bar's extreme >= +0.8R, stop to entry (all legs)")]
    fm = R.FillModel.reference()
    long, paired = R.run_stage_a(d, pols, fm)
    long.to_csv(os.path.join(out_dir, "stage_a_long.csv"), index=False)
    paired.to_csv(os.path.join(out_dir, "stage_a_paired.csv"))
    for fam in ("KX", "PX"):
        sub = long[long.family == fam]
        print(f"### {fam}: per-policy summary (trades = {sub[sub.policy=='original'].shape[0]}, sessions = {sub.session.nunique()})\n")
        print(R.md_table(R.summarize(sub, "policy")), "\n")
        p = paired[paired.family == fam]
        rows = []
        for pol in pols[1:]:
            bs = R.session_bootstrap(p, f"dnet_usd__{pol.name}", n_boot=2000, seed=1)
            bsR = R.session_bootstrap(p, f"dnet_R__{pol.name}", n_boot=2000, seed=1)
            rows.append(dict(policy=pol.name, trades=bs["n_trades"], sessions=bs["n_sessions"],
                             mean_dnet_usd=round(bs["point"], 2), ci95_usd=f"[{bs['lo']:.1f}, {bs['hi']:.1f}]",
                             mean_dnet_R=round(bsR["point"], 3), ci95_R=f"[{bsR['lo']:.3f}, {bsR['hi']:.3f}]",
                             trades_changed=int((p[f"dnet_usd__{pol.name}"].abs() > 0.005).sum()),
                             overlaps_next_entry=int(p[f"overlaps_next_entry__{pol.name}"].sum()),
                             new_overlaps_vs_original=int((p[f"overlaps_next_entry__{pol.name}"] & ~p["overlaps_next_entry__original"]).sum())))
        print(f"Paired difference vs original (alternative minus original, net of costs), whole-session bootstrap 95% CI:\n")
        print(R.md_table(pd.DataFrame(rows), index=False), "\n")
    return long, paired


def section_stage_b(d: R.Data, out_dir: str):
    print("## 5. Stage B demonstration: chronological replay from signals.csv (SYNTHETIC)\n")
    sg = d.signals.set_index("signal_id")
    rows = []
    for fmname, fm, frees in (("generator", R.FillModel.generator(), True), ("reference", R.FillModel.reference(), False)):
        res, lg = R.run_stage_b(d, R.OriginalBracket(), fm, exit_frees_same_bar=frees)
        res.to_csv(os.path.join(out_dir, f"stage_b_original_{fmname}.csv"), index=False)
        lg.to_csv(os.path.join(out_dir, f"stage_b_signal_log_{fmname}.csv"), index=False)
        agree = int((lg.executed == lg.executed_in_export).sum())
        rows.append(dict(policy="original", fill_model=fmname, exit_frees_same_bar=frees, signals=len(lg), executed=int(lg.executed.sum()),
                         rejected=int((~lg.executed).sum()), executed_flag_agrees_with_export=f"{agree}/{len(lg)}",
                         net_usd_sum=round(res.net_usd.sum(), 2), journal_net_usd_sum=round(d.trades.net_pnl_usd.sum(), 2),
                         sessions=res.session.nunique()))
    for pol in (R.Policy("time_exit_30", [R.TimeExit(30)], R.KXAddRule()),
                R.Policy("hold_to_eod_no_target", [R.StructuralTarget(None)], R.KXAddRule(), "stop only, flat 15:55")):
        res, lg = R.run_stage_b(d, pol, R.FillModel.reference(), exit_frees_same_bar=False)
        rows.append(dict(policy=pol.name, fill_model="reference", exit_frees_same_bar=False, signals=len(lg), executed=int(lg.executed.sum()),
                         rejected=int((~lg.executed).sum()), executed_flag_agrees_with_export=f"{int((lg.executed == lg.executed_in_export).sum())}/{len(lg)}",
                         net_usd_sum=round(res.net_usd.sum(), 2), journal_net_usd_sum=round(d.trades.net_pnl_usd.sum(), 2),
                         sessions=res.session.nunique()))
    print(R.md_table(pd.DataFrame(rows), index=False), "\n")
    print("Stage B entries are re-priced from the bars (open +1 tick), so even the original policy differs from the journal by the "
          "MANUAL exits and the fill conventions listed in section 2; the executed/rejected set is the check that the position-limit "
          "logic is right. Longer holds (`hold_to_eod_no_target`) change which later signals are blocked.\n")


def section_variants(d: R.Data):
    print("## 6. Fill-assumption variants, original policy, Stage A entries (SYNTHETIC, net of costs)\n")
    ents = R.entries_from_trades(d)
    variants = [("reference", {}), ("slippage 0 ticks (MKT, STP, gap)", dict(slippage_ticks_market=0, slippage_ticks_stop=0, slippage_ticks_gap=0)),
                ("slippage 2 ticks (MKT, STP, gap)", dict(slippage_ticks_market=2, slippage_ticks_stop=2, slippage_ticks_gap=2)),
                ("gap fill at open (0 extra ticks)", dict(slippage_ticks_gap=0)),
                ("stop fires only on penetration", dict(stop_trigger="penetrate")),
                ("target fills on touch", dict(target_fill="touch")),
                ("bracket not armed in entry bar", dict(bracket_in_entry_bar=False)),
                ("triggers + MKT prices on NQ bars", dict(trigger_instrument="NQ", price_instrument="NQ")),
                ("same-bar: target_first", dict(same_bar_order="target_first")),
                ("same-bar: stop_first", dict(same_bar_order="stop_first"))]
    rows = []
    for name, kw in variants:
        fm = R.FillModel.reference(**kw)
        df = pd.DataFrame([R.simulate_trade(e, d, R.OriginalBracket(), fm).row() for e in ents])
        rows.append(dict(variant=name, trades=len(df), sessions=df.session.nunique(), net_usd_sum=round(df.net_usd.sum(), 2),
                         net_R_mean=round(df.net_R.mean(), 4), stop_exits=int(df.exit_reason.str.startswith("STOP").sum()),
                         target_exits=int((df.exit_reason == "TARGET").sum()), gaps=int(df.gapped_through_stop.sum())))
    print(R.md_table(pd.DataFrame(rows), index=False), "\n")
    print("Entry fills are the journal's (Stage A), so entry slippage is not varied here; Stage B re-prices entries and is affected by "
          "`slippage_ticks_market` on both sides.\n")


def main(data_dir: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    d = R.load_data(data_dir, require_trades=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        print("# S5 run output (SYNTHETIC development data, 2025-05-01 .. 2026-04-30)\n")
        section_verification(d)
        print("## 2. Reconciliation\n")
        C.run_reconcile(d, out_dir, verbose=True)
        section_same_bar(d)
        section_stage_a(d, out_dir)
        section_stage_b(d, out_dir)
        section_variants(d)
    text = buf.getvalue()
    with open(os.path.join(out_dir, "run_output.md"), "w") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..", "data", "synthetic")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "out")
    main(data_dir, out_dir)
