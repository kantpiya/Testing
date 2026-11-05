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
| Net | after commission on every fill at the desk's actual rate and the slippage actually observed on live fills (not an assumption) |

## 2. Triggers and order actions per candidate (shadow)

### P0 — original bracket (live; the control)
Live OCO stop + target; KX add rule; flat 15:55. Logged as-is.

### C1 — KX stall → breakeven
- **Trigger.** KX only. MFE ≥ +0.8R has occurred (any earlier bar) **and** the current bar closes ≤ +0.3R **and** the trade is still open under P0.
- **Shadow action.** At the next bar open: stop of all legs = entry fill (tick-rounded). Target unchanged. Record the paper exit when the shadow stop or target is touched on subsequent bars (stop − 1 tick, bar open if gapped), or the 15:55 open.
- **Live equivalent if promoted.** Modify the resting stop order (OCO leg) to the entry price; no new order; the target stays.

### C2 — KX late profit-conditional breakeven
- **Trigger.** KX only. At the close of bar 20 after entry, open profit ≥ +0.3R and the trade is open under P0.
- **Shadow action / live equivalent.** As C1, at the open of bar 21.

### C3 — add-leg stop at the original entry
- **Trigger.** KX add fill (leg 2).
- **Shadow action.** Leg 2 gets a paper stop at the entry fill of leg 1; leg 1 unchanged. Paper exit of leg 2 only when touched.
- **Live equivalent if promoted.** Submit the add with its own stop order (not joined to the original OCO) at the leg-1 entry price; the add's target order remains the shared target.

### C4 — PX far target
- **Trigger.** PX entry.
- **Shadow action.** Paper target at the opposite opening-range boundary; paper exit at the first touch of that level, the stop, or 15:55. The live midpoint target still exits the live position; the shadow continues on bars after the live exit.
- **Live equivalent if promoted.** Place the target limit at the boundary instead of the midpoint.

### Shadow continuation audit (observational, every target exit, both families)
For every live TARGET exit record `cont_R = direction × (15:55 open − target fill) / stop distance` and the path after exit (MFE, MAE in R, time to re-touch the entry). This is the one cheapest measurement that separates "the generator's drift" from the real market: if `cont_R` is centred near 0 on live data, every "hold longer / drop the target" result in this panel is void.

## 3. Fields to log (one row per trade per candidate, plus one row per decision event)

**Trade row:** `trade_id, signal_id, session, strategy_version, family, direction, entry_ts, entry_fill, initial_contracts, planned_stop, planned_target, planned_risk_usd, add_ts, add_fill, add_contracts, live_exit_ts, live_exit_px, live_exit_reason, live_net_usd, live_net_R, candidate, shadow_trigger_ts, shadow_action, shadow_exit_ts, shadow_exit_px, shadow_exit_reason, shadow_net_usd, shadow_net_R, paired_delta_R, paired_delta_usd, overlap_flag (shadow still open when a later live entry fired), position_limit_block_flag, manual_intervention_flag, bars_missing_flag`.

**Decision-event row:** `trade_id, candidate, event (TRIGGER/BE_SET/STOP_HIT/TARGET_HIT/EOD), bar_close_ts, open_profit_R, mfe_R, mae_R, minutes_since_entry, price, note`.

**Session row:** `session, n_live_trades, n_shadow_triggers per candidate, live_session_net, shadow_session_net per candidate, max_concurrent_contracts, n_signals_rejected_by_limit`.

Logging the rejected signals (`signals.csv` schema in `02_inventory_and_export_fields.md`) stays mandatory so Stage B can be re-run on the forward period.

## 4. Sample and duration

Estimated from the desk's historical frequency (to be replaced by the real numbers once the export is in): roughly one KX trade per session, a stall state in about a quarter of KX trades, an add in about a third, one PX trade every 2.6 sessions.

| Candidate | Unit | Minimum sample before any read | Why |
|---|---|---|---|
| C1 | stall trades, distinct sessions | 40 / 40 | the synthetic holdout's 13 stall trades gave a CI from −0.5R to +1.1R, useless; 40 brings the CI half-width near ±0.45R at the observed SD ≈ 1.5R |
| C2 | conditioned trades at minute 20 | 60 / 60 | tail-halving test needs ≥ 15 trades in the worst decile |
| C3 | add trades | 40 / 40 | S4's break-even count P(target \| retrace to entry after add) needs ≥ 15 retraces |
| C4 | PX trades | 90 / 90 | ±0.1R per entry resolution (S3) |
| Continuation audit | target exits | 100 | SD of cont_R ≈ 2–6R in the synthetic set; 100 gives ±0.5–1.2R |

At the historical rate that is about 6–9 months of trading. **One pre-planned interim read at half the sample**, reported but not acted on unless the stopping rule below fires.

## 5. Predetermined criteria

**Promote a candidate to a live A/B (half the contracts under the candidate, half under P0, alternating by session parity) only if all hold at the full sample:**
1. Paired mean Δ net R per conditioned trade vs P0 has a 95% session-bootstrap CI excluding 0 **in the pre-registered direction** (C1, C4: Δ > 0; C2, C3: Δ ≥ −0.10R with the tail metric halved).
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
