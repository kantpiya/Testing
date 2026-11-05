# Forward-simulation specification (shadow mode; live settings unchanged)

Purpose: decide, on the desk's own forward data, whether any post-entry management policy beats the original bracket. Nothing here changes live orders. Every candidate runs as a **paper overlay** on the live position, computed from the same 1-minute MNQ bars the live system sees, and logged alongside the live fills.

Candidates carried forward from the pre-registration (`prereg/challengers.md`) are listed in the decision brief (`synthesis/01_decision_brief.md`). The spec below is written so that any of P0 / C1 / C2 / C3 / C4 can be switched on as a shadow without code changes to the live stack.

## 1. Definitions (fixed for the whole study)

| Term | Definition |
|---|---|
| 1R | `planned_risk_usd` at entry = initial contracts × \|entry fill − planned stop\| × $2. Never recomputed after an add. |
| Open profit at minute k | direction × (close of bar k − entry fill) / stop distance, bar k = the k-th full 1-minute bar after the entry bar |
| MFE at minute k | max over bars 1..k of direction × (favourable extreme − entry fill) / stop distance |
| Decision time | the close of the bar that satisfies the trigger; the action is executable at the next bar open |
| Net | after commission on every fill at the desk's actual rate. A paper exit never fills, so its slippage is **imputed** from the desk's own live fills of the same order type (median and 90th percentile of observed STOP and MKT slippage, recomputed monthly, columns `assumed_slip_ticks`, `empirical_slip_p50`, `empirical_slip_p90`); report the paired delta under both p50 and p90. |
| Paired delta | shadow net minus the **mechanical P0 replay** of the same trade (not minus the live net), so that discretionary interventions do not enter the comparison; live net is logged separately |
| Changed trade | a trade on which the shadow's exit differs from mechanical P0 by more than one tick; sample minima below count changed trades, not conditioned trades |
| One-time header | `stop_trigger_source` (last trade vs bid/ask, from the broker), `bar_ts_label` (open or close), bar source instrument (must be MNQ trades) |

## 2. Triggers and order actions per candidate (shadow)

### P0 — original bracket (live; the control)
Live OCO stop + target; KX add rule; flat 15:55. Logged as-is.

### C1 — KX stall → breakeven
- **Trigger.** KX only. MFE through and including bar k ≥ +0.8R **and** bar k closes ≤ +0.3R **and** the trade is still open under P0. Decision time = close of bar k.
- **Shadow action.** At the open of bar k+1: if that open is still on the favourable side of the entry fill, stop of all legs = entry fill (tick-rounded), target unchanged; if the open is at or through the entry fill, the shadow records a market exit at that open (imputed slippage). Record the paper exit when the shadow stop or target is touched on subsequent bars, or at the 15:55 open. Log `order_action ∈ {MODIFY, CANCEL_REPLACE, MKT}`, `modify_rejected_flag`, `first_bar_hit_flag`, `both_touched_flag` (report both orderings when set).
- **What this rule is in practice (SYNTHETIC finding, director-verified).** In development 13 of 60 triggers had the next open already through entry and 21 more were stopped in the first live bar: 34 of 60 shadow actions are an exit one bar after the stall, not a tightened stop. Log both outcomes separately; the forward decision is on the whole rule.
- **Live equivalent if promoted.** Modify the resting OCO stop leg to the entry price (cancel/replace where the platform requires; confirm the OCO link survives); if the modify is rejected because the market is through the level, send a market order.

### C2 — KX late profit-conditional breakeven
- **Trigger.** KX only. At clock time entry + 20 minutes (the close of the bar that ends then; state clock time, not bar index, to avoid the off-by-one between reports), open profit ≥ +0.3R and the trade is open under P0.
- **Shadow action / live equivalent.** As C1, at the following bar open. In development this rule had 0 rejected modifies and 0 first-bar hits (Reviewer B), so it executes as modelled. Tail metric is defined on the **whole position** (an add leg's breakeven-at-entry is about one stop distance below its own fill), with a session-bootstrap CI.

### C3 — add-leg stop at the original entry
- **Trigger.** KX add fill (leg 2).
- **Shadow action.** Leg 2 gets a paper stop at the entry fill of leg 1; leg 1 unchanged. Paper exit of leg 2 only when touched.
- **Live equivalent if promoted.** The add gets its **own OCO**: stop (qty = add) at the leg-1 entry price and limit (qty = add) at the shared target price. A single shared target with a separate add stop is unsafe: if the shared target fills, the add stop is orphaned and would open a reverse position; if the add stop fills, the shared target is over-quantity (Reviewer B).
- **Primary statistic (revised per both reviewers).** The logged count P(reach target \| price retraced to the leg-1 entry after the add), with its CI, decided at ≥ 40 add trades and ≥ 15 retraces; no P&L objective.

### C4 — PX far target
- **Trigger.** PX entry.
- **Shadow action.** Paper target at the opposite opening-range boundary; paper exit at the first touch of that level, the stop, or 15:55. The live midpoint target still exits the live position; the shadow continues on bars after the live exit.
- **Live equivalent if promoted.** Place the target limit at the boundary instead of the midpoint.

### Shadow continuation audit (observational, every target exit, both families)
For every live TARGET exit record `cont_R = direction × (15:55 open − target fill) / stop distance` and the path after exit (MFE, MAE in R, time to re-touch the entry). This is the one cheapest measurement that separates "the generator's drift" from the real market: if `cont_R` is centred near 0 on live data, every "hold longer / drop the target" result in this panel is void.

## 3. Fields to log (one row per trade per candidate, plus one row per decision event)

**Trade row:** `trade_id, signal_id, session, strategy_version, family, direction, entry_ts, entry_fill, initial_contracts, planned_stop, planned_target, planned_risk_usd, add_ts, add_fill, add_contracts, live_exit_ts, live_exit_px, live_exit_reason, live_net_usd, live_net_R, candidate, shadow_trigger_ts, shadow_action, shadow_exit_ts, shadow_exit_px, shadow_exit_reason, shadow_net_usd, shadow_net_R, paired_delta_R, paired_delta_usd, overlap_flag (shadow still open when a later live entry fired), position_limit_block_flag, manual_intervention_flag, bars_missing_flag`.

**Decision-event row:** `trade_id, candidate, leg_id, qty, event (TRIGGER/BE_SET/MKT_EXIT/STOP_HIT/TARGET_HIT/EOD), bar_close_ts, action_sent_ts, action_ack_ts, order_action, modify_rejected_flag, first_bar_hit_flag, exact_touch_flag, both_touched_flag, open_profit_R, mfe_R, mae_R, minutes_since_entry, price, exit_bar_ohlc, first_at_or_through_trade_ts, note`.

**Session row:** `session, n_live_trades, n_shadow_triggers per candidate, live_session_net, shadow_session_net per candidate, max_concurrent_contracts, n_signals_rejected_by_limit`.

Logging the rejected signals (`signals.csv` schema in `02_inventory_and_export_fields.md`) stays mandatory so Stage B can be re-run on the forward period.

## 4. Sample and duration

Estimated from the synthetic desk's frequency (to be replaced by the real numbers once the export is in): roughly one KX trade per session, a stall state in about a quarter of KX trades, an add in about a third, one PX trade every 2.6 sessions. Development was exactly one trading year, so development Δ$ reads as $ per year.

| Candidate | Unit | Minimum sample before any read | Months at the synthetic rate | Why |
|---|---|---|---|---|
| Drift gauge (first) | KX trades open at minute 10 | 150 | ≈ 12 | Reviewer A: paired (exit at minute-10 open − P0) ≤ −0.25R with CI excluding 0 ⇒ drift present; within ±0.10R ⇒ absent. Decides whether any "hold" result transfers |
| C1 | stall trades / changed trades | 100 / 60 | ≈ 20 | MDE 0.42–0.50R at the observed paired SD 1.5–1.8R (Reviewer A); 40 stalls can only detect 0.7–0.8R |
| C2 | conditioned trades / changed trades | 60 / 15 | ≈ 12 | tail metric needs ≥ 15 changed trades; the holdout's 13 conditioned trades changed 1 |
| C3 | add trades / retraces to entry | 40 / 15 | ≈ 7 | the decisive proportion needs ≥ 15 retrace events |
| C4 | PX trades | 90 | ≈ 11 | ±0.1R per entry resolution (S3); the retire rule may not fire before this sample (Reviewer B) |
| Continuation audit | target exits | 100 | ≈ 8 | SD of cont_R ≈ 2–6R in the synthetic set; 100 gives ±0.5–1.2R |

**One pre-planned interim read at half the sample**, reported but not acted on unless the stopping rule below fires (99% CI at the interim).

## 5. Predetermined criteria

**Promote a candidate to a live A/B (whole trades assigned by session parity, assignment logged before entry; never split contracts, since 23% of KX and 78% of PX trades are one-lots) only if all hold at the full sample:**
1. Paired mean Δ net R per conditioned trade vs mechanical P0 has a 95% session-bootstrap CI excluding 0 **in the pre-registered direction** (C1, C4: Δ > 0; C2: Δ ≥ −0.10R with the tail metric halved; C3: the retrace proportion below 0.35 with CI), **and** the point estimate clears the materiality floor of $1,000 per year or 2R of drawdown reduction (Reviewer B).
2. The sign holds in each strategy version with ≥ 20 trades.
3. Removing the top 3 sessions by benefit leaves ≥ 60% of the benefit.
4. Stage B replay of the forward period (position limit, rejected signals) shows portfolio Δ ≥ 0.
5. Slippage on the shadow's implied fills, measured from the live fills of the same order type, does not erase the benefit at 2× the observed median slippage.

**Retire a candidate if any holds at the full sample, or at the interim with the stricter 99% CI:**
- The CI lies entirely on the wrong side of the retirement threshold stated in the pre-registration.
- More than 30% of the benefit sits in a single session.
- The continuation audit shows `cont_R` centred ≤ 0 for the family (for C4 and any "hold longer" idea).

**Retire the whole programme** (keep P0) if, at the full sample, no candidate meets criterion 1. Do not add new candidates to the shadow during the study; log ideas for the next cycle.

## 6. Integrity checks run weekly on the log

- Every `entry_ts` equals a bar open; every shadow trigger uses only bars with close ≤ trigger time (assert in code).
- `live_net_usd` reconciles to the broker statement to the cent; count and list MANUAL interventions.
- Bars present through 15:55 for every session with an open trade.
- Signal instrument (NQ/ES) bars and MNQ bars aligned to the same exchange clock (max timestamp skew logged).

## 7. Runnable artefacts

- `src/S5/replay.py` — reference engine; policies P0, C1–C4 and diagnostics as policy objects.
- `src/director/reproduce.py` — independent engine for P0, C1, D3, D1 (cross-check).
- `src/S1/run.py`, `src/S2/run.py`, `src/S3/run.py`, `src/S4/run.py`, `src/S6/run.py` — the specialists' analyses; each runs unchanged on the real export placed at `data/real/` with the same file names.
