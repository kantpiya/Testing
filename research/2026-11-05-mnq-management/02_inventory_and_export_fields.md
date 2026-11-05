# Inventory, replayability, and the exact fields to export

Director's audit, 2026-11-05 07:20 ET. Repository `kantpiya/Testing`, branch `claude/affectionate-pasteur-l43w3y`.

## 1. What exists

| Item | Status | Where looked |
|---|---|---|
| Signal log (eligible and rejected signals) | **Missing** | whole repo, both branches |
| Fill log (entries, adds, partial/final exits) | **Missing** | " |
| Original stops and targets per trade | **Missing** | " |
| Strategy definitions and version history (KX, PX, engulfing, weak reversal, sell-off recovery) | **Missing** (names only, from your earlier context) | " |
| Position sizes, contract counts, position limits | **Missing** | " |
| Commission and fee schedule | **Missing** | " |
| Timestamped MNQ / NQ / ES market data | **Missing** | " |
| Your computer (Remote Control folder) | **Not linked** | `list_computer_folders` |
| Earlier panel (2026-11-05, other branch) | Text only, no data; different question | `research/2026-11-05-panel/` |

**Verdict:** nothing can be replayed empirically in this session. The panel therefore ran on a synthetic test case in the schema below, with a sealed ground truth, to produce a tested replay engine, pre-registered policies and a forward-simulation specification you can run on your own export in minutes.

## 2. Replayability requirements (what the real data must satisfy)

A management policy can only be evaluated if the **market path after each historical exit** is available. A fill log, or an MFE/MAE number per trade, cannot establish that path. Concretely:

1. **Continuous 1-minute MNQ bars** (or trades) covering every session in which a trade was open, from entry through the session close (15:55 ET cutoff or your actual flat time), not just through the historical exit.
2. **Exchange-stamped timestamps** on signals and fills, in one declared zone (UTC preferred), so that "the first instant the decision was knowable" can be placed on a bar close.
3. **Signal instrument separate from execution instrument** (NQ or ES signal, MNQ fill) with both bar series available over the same window.
4. **Original planned stop and target at entry**, so 1R is fixed from the plan, not inferred from the realised exit.
5. **Rejected signals**, so Stage B (position limits, overlapping entries) can be replayed.
6. **Strategy version per signal**, so parameter changes are not mistaken for management effects.

Items the replay must **assume** if not exported (each is a parameter in `src/S5/replay.py`): slippage per fill type, same-bar stop/target ordering, commission per side, how a MANUAL exit is treated (excluded from Stage A pairs, or replayed as if the policy had been in force).

## 3. Exact export: one CSV per table, UTF-8, ISO 8601 timestamps with offset

### 3.1 `signals.csv` — one row per signal emitted, executed or not

| Field | Type | Notes |
|---|---|---|
| signal_id | string | unique |
| strategy | string | versioned name, e.g. KX_ORB_v2 |
| family | string | breakout / reversal / other, your taxonomy |
| strategy_version_valid_from | date | or join on `strategy_versions.csv` |
| signal_instrument | string | NQ, ES, MNQ |
| exec_instrument | string | MNQ |
| signal_ts | timestamp | the **bar close** (or tick) at which the condition became true |
| direction | LONG/SHORT | |
| ref_level | float | the level the setup keyed on (OR high, prior high, etc.) |
| ref_width | float | the width used for stop/target scaling if any |
| planned_entry_type | MKT/LMT/STP | |
| planned_entry_px | float | if a limit/stop entry |
| planned_stop_px | float | **required** |
| planned_target_px | float | required if a target exists; blank if none |
| planned_contracts | int | |
| planned_risk_usd | float | = contracts × |entry − stop| × $2; this defines 1R |
| executed | bool | |
| reject_reason | string | position_limit, session_cutoff, discretionary, … |

### 3.2 `fills.csv` — one row per fill, every leg

| Field | Type | Notes |
|---|---|---|
| fill_id, trade_id, signal_id | string | |
| leg_id | int | 1 = initial, 2.. = adds |
| ts | timestamp | exchange fill time |
| side | BUY/SELL | |
| qty | int | contracts |
| price | float | |
| order_type | MKT/LMT/STP/STP-LMT | |
| fill_role | ENTRY/ADD/PARTIAL_EXIT/EXIT | |
| exit_reason | string | STOP/TARGET/TIME/MANUAL/TRAIL/other |
| commission_usd | float | per fill, all-in |
| order_submit_ts | timestamp | optional; distinguishes latency from decision time |

### 3.3 `trades.csv` — journal, one row per trade (derivable from fills but export it, so reconciliation can detect journal errors)

`trade_id, signal_id, session, strategy, family, direction, entry_ts, entry_px, initial_contracts, added_contracts, add_px, add_ts, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason, gross_pnl_usd, commission_usd, net_pnl_usd, manual_flag, notes`

### 3.4 `strategy_versions.csv`

`strategy, family, valid_from, valid_to, signal_instrument, entry_rule, stop_rule, target_rule, time_exit_rule, pyramiding_rule, sizing_rule, position_limit`

### 3.5 `bars_<INSTRUMENT>_1min.csv` for MNQ, NQ, ES as applicable

`ts (bar open, with offset), open, high, low, close, volume`, continuous contract with roll dates in a sidecar `rolls.csv` (`instrument, roll_date, old_contract, new_contract, adjustment`). Include the full RTH session for every session with a signal, plus the globex session if any strategy trades it.

### 3.6 `costs.csv`

`instrument, commission_per_side_usd, exchange_fees_included, point_value_usd, tick, position_limit_contracts, eod_flat_time_et`

### 3.7 Optional but valuable

- `account_rules.csv`: daily loss limit, trailing drawdown, max contracts, which account each trade ran in.
- Tick data or 1-second bars for the entry and exit minutes only, to settle same-bar stop/target ordering.

## 4. Minimum sample for the decision

The panel's sample-size arithmetic (reports S2, S6 and the holdout result in `synthesis/02_comparison_table.md`) is on synthetic data, but the arithmetic transfers: to distinguish a policy difference of 0.10R per trade with a per-trade SD of ~1.5R at 80% power and session-clustered errors you need roughly 400–600 paired trades per family, i.e. on the order of 300+ sessions in which that family fired. Export everything you have, including the earliest versions, and let the replay decide what is comparable.
