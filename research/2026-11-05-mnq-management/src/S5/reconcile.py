"""
Reconcile the ORIGINAL policy (reconstructed from strategy_versions.csv + bars)
against trades.csv and fills.csv, trade by trade.

    python3 src/S5/reconcile.py [data_dir] [out_dir]

For each trade the replay's exit time, exit price, exit reason and net P&L are
compared with the journal.  A trade that does not match under the reference
fill model is pushed through a ladder of fill-model variants; the first variant
under which it matches exactly names the convention that explains it.  Trades
that match under no variant are UNEXPLAINED and are classified by inspection
(MANUAL exits, intra-bar prices, timestamp issues).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay as R  # noqa: E402


def _replay_original(data: R.Data, fm: R.FillModel) -> pd.DataFrame:
    ents = R.entries_from_trades(data)
    res = pd.DataFrame([R.simulate_trade(e, data, R.OriginalBracket(), fm).row() for e in ents])
    return res.set_index("trade_id")


def compare(res: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    """Per-trade comparison columns: time/px/reason/net match flags and differences."""
    tr = trades.set_index("trade_id")
    m = res.join(tr[["exit_t", "exit_px", "exit_reason", "net_pnl_usd", "added_contracts", "add_t"]], rsuffix="_act")
    m["time_match"] = m.exit_time == m.exit_t
    m["px_diff_ticks"] = ((m.exit_px - m.exit_px_act) / R.TICK).round(2)
    m["px_match"] = np.isclose(m.exit_px, m.exit_px_act)
    m["reason_match"] = m.exit_reason == m.exit_reason_act
    m["add_match"] = m.contracts_added == m.added_contracts
    m["net_diff_usd"] = (m.net_pnl_usd - m.net_usd).round(2)   # actual - replay
    m["net_match"] = m.net_diff_usd.abs() < 0.005
    m["exact"] = m.time_match & m.px_match & m.reason_match & m.net_match & m.add_match
    return m


# Ladder from the reference model towards the generator's conventions: each step toggles ONE
# convention; a trade is labelled by the first step under which it matches exactly.
LADDER = [
    ("reference", {}),
    ("MKT fills priced off NQ (signal instrument) not MNQ", dict(price_instrument="NQ")),
    ("stop/target evaluated on NQ bars", dict(price_instrument="NQ", trigger_instrument="NQ")),
    ("bracket not armed in entry bar", dict(price_instrument="NQ", trigger_instrument="NQ", bracket_in_entry_bar=False)),
    ("exact touch does NOT fire stop (penetration rule)", dict(price_instrument="NQ", trigger_instrument="NQ",
                                                               bracket_in_entry_bar=False, stop_trigger="penetrate")),
    ("gapped-through limit filled at limit, not open", dict(price_instrument="NQ", trigger_instrument="NQ",
                                                            bracket_in_entry_bar=False, stop_trigger="penetrate",
                                                            limit_gap_fill="limit")),
    ("add skipped when trade exits in the add bar", dict(price_instrument="NQ", trigger_instrument="NQ",
                                                         bracket_in_entry_bar=False, stop_trigger="penetrate",
                                                         limit_gap_fill="limit", skip_add_if_exit_same_bar=True)),
    ("exact touch DOES fire stop (touch rule)", dict(price_instrument="NQ", trigger_instrument="NQ",
                                                     bracket_in_entry_bar=False, stop_trigger="touch",
                                                     limit_gap_fill="limit", skip_add_if_exit_same_bar=True)),
]


def classify_unexplained(row, data: R.Data) -> str:
    sess = row.session
    b = data.session_bars["MNQ"][sess]
    if row.exit_t not in b.index:
        return "timestamp not a bar open"
    bar = b.loc[row.exit_t]
    inside = bar.low - R.TICK <= row.exit_px_act <= bar.high + R.TICK
    if row.exit_reason_act == "MANUAL":
        return "MANUAL exit at intra-bar price" + ("" if inside else " (outside bar range)")
    if not inside:
        return "exit price outside exit-bar range"
    return "unclassified"


def run_reconcile(data: R.Data, out_dir: str, verbose: bool = True) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    out = {}
    tr = data.trades
    # --- 1. reference and generator models ------------------------------------------------------
    res_ref = _replay_original(data, R.FillModel.reference())
    res_gen = _replay_original(data, R.FillModel.generator())
    cmp_ref, cmp_gen = compare(res_ref, tr), compare(res_gen, tr)

    # --- 2. ladder classification --------------------------------------------------------------
    label = pd.Series("UNEXPLAINED", index=cmp_ref.index)
    matched = pd.Series(False, index=cmp_ref.index)
    for name, kw in LADDER:
        c = compare(_replay_original(data, R.FillModel.reference(**kw)), tr)
        newly = c.exact & ~matched
        label[newly] = name
        matched |= c.exact
    cmp_ref["explained_by"] = label
    unexpl = cmp_ref[label == "UNEXPLAINED"].copy()
    unexpl["class"] = [classify_unexplained(r, data) for r in unexpl.itertuples()]
    cmp_ref.loc[unexpl.index, "explained_by"] = "UNEXPLAINED: " + unexpl["class"]

    # --- 3. summary counts -----------------------------------------------------------------------
    def counts(c):
        return dict(trades=len(c), exact=int(c.exact.sum()), time_mismatch=int((~c.time_match).sum()),
                    px_mismatch_any=int((~c.px_match).sum()),
                    px_mismatch_le_2ticks=int(((~c.px_match) & (c.px_diff_ticks.abs() <= 2)).sum()),
                    reason_mismatch=int((~c.reason_match).sum()), add_mismatch=int((~c.add_match).sum()),
                    net_mismatch=int((~c.net_match).sum()),
                    sum_actual_minus_replay_usd=round(c.net_diff_usd.sum(), 2),
                    sum_abs_diff_usd=round(c.net_diff_usd.abs().sum(), 2))
    summary = pd.DataFrame({"reference model": counts(cmp_ref), "generator model": counts(cmp_gen)})
    out["summary"] = summary
    expl = (cmp_ref.groupby("explained_by")
            .agg(trades=("net_diff_usd", "size"), sessions=("session", "nunique"),
                 sum_actual_minus_replay_usd=("net_diff_usd", "sum"), sum_abs_usd=("net_diff_usd", lambda s: s.abs().sum()))
            .round(2).sort_values("trades", ascending=False))
    out["explained"] = expl
    un = cmp_ref[cmp_ref.explained_by.str.startswith("UNEXPLAINED")]
    out["unexplained_usd"] = round(un.net_diff_usd.sum(), 2)
    out["unexplained_abs_usd"] = round(un.net_diff_usd.abs().sum(), 2)
    out["unexplained_n"] = int(len(un))
    cols = ["session", "family", "direction", "exit_time", "exit_t", "exit_reason", "exit_reason_act", "exit_px", "exit_px_act",
            "px_diff_ticks", "net_usd", "net_pnl_usd", "net_diff_usd", "explained_by"]
    mism = cmp_ref[~cmp_ref.exact][cols].copy()
    mism["exit_time"] = mism.exit_time.dt.strftime("%H:%M"); mism["exit_t"] = mism.exit_t.dt.strftime("%H:%M")
    mism = mism.rename(columns={"exit_time": "replay_exit", "exit_t": "actual_exit", "exit_reason": "replay_reason",
                                "exit_reason_act": "actual_reason", "exit_px": "replay_px", "exit_px_act": "actual_px",
                                "net_usd": "replay_net", "net_pnl_usd": "actual_net"})
    out["mismatches"] = mism
    out["generator_mismatches"] = cmp_gen[~cmp_gen.exact][cols[:-1]].copy()

    # --- 4. fill-level comparison under the generator model ------------------------------------
    rows = []
    for e in R.entries_from_trades(data):
        r = R.simulate_trade(e, data, R.OriginalBracket(), R.FillModel.generator())
        for f in r.fills:
            rows.append(dict(trade_id=f.trade_id, leg_id=f.leg_id, role=f.role, t=f.time, qty=f.qty, price=f.price,
                             commission=f.commission, side=f.side))
    rf = pd.DataFrame(rows)
    af = data.fills.rename(columns={"fill_role": "role"})[["trade_id", "leg_id", "role", "t", "qty", "price", "commission", "side"]]
    j = af.merge(rf, on=["trade_id", "leg_id", "role"], how="outer", suffixes=("_act", "_rep"), indicator=True)
    fill_summary = dict(actual_fills=len(af), replay_fills=len(rf), paired=int((j._merge == "both").sum()),
                        time_match=int((j.t_act == j.t_rep).sum()), price_match=int(np.isclose(j.price_act, j.price_rep).sum()),
                        qty_match=int((j.qty_act == j.qty_rep).sum()), side_match=int((j.side_act == j.side_rep).sum()),
                        commission_match=int(np.isclose(j.commission_act, j.commission_rep).sum()),
                        all_match=int(((j.t_act == j.t_rep) & np.isclose(j.price_act, j.price_rep) & (j.qty_act == j.qty_rep)
                                       & np.isclose(j.commission_act, j.commission_rep)).sum()))
    out["fills"] = pd.Series(fill_summary)

    # --- 5. save --------------------------------------------------------------------------------
    cmp_ref.drop(columns=["entry_time"], errors="ignore").to_csv(os.path.join(out_dir, "reconcile_reference_per_trade.csv"))
    cmp_gen.to_csv(os.path.join(out_dir, "reconcile_generator_per_trade.csv"))
    mism.to_csv(os.path.join(out_dir, "reconcile_mismatches.csv"))
    summary.to_csv(os.path.join(out_dir, "reconcile_summary.csv"))
    expl.to_csv(os.path.join(out_dir, "reconcile_explained_by.csv"))
    if verbose:
        print("## Reconciliation: original policy replay vs trades.csv (SYNTHETIC, n=332 trades, 242 sessions)\n")
        print(R.md_table(summary), "\n")
        print("### Mismatches under the reference model, classified by the first fill-model convention that explains them\n")
        print(R.md_table(expl), "\n")
        print(f"UNEXPLAINED: {out['unexplained_n']} trades, sum(actual - replay) = ${out['unexplained_usd']}, sum|diff| = ${out['unexplained_abs_usd']}\n")
        print("### Per-trade mismatch table (reference model)\n")
        print(R.md_table(mism), "\n")
        print("### Fill-level comparison vs fills.csv (generator model)\n")
        print(R.md_table(out["fills"].to_frame("count")), "\n")
    return out


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "..", "data", "synthetic")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "out")
    data = R.load_data(data_dir, require_trades=True)
    run_reconcile(data, out_dir)
