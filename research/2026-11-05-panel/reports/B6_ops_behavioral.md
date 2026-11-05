# B6 — Trading Operations and Behavioral Research

**Question:** Where do actual trading decisions depart from strategy intent, and which departures can we measure?
**Workspace status (OBSERVED):** no logs, trades, code or studies exist in the container; whether rejected signals are logged today is UNKNOWN. Everything about the user's strategies is USER-SUPPLIED CONTEXT (unverified).

## 1. Strongest finding or proposal, and the decision it would change

**Proposal (HYPOTHESIS):** The single highest-value change is to log *every eligible signal at the moment it fires*, with the decision taken and the state of all other strategy slots, so that each departure from intent becomes a measurable row rather than an anecdote. Without this, "discretion" is unmeasurable: skipped signals leave no trace, overrides look like strategy trades, and duplicate exposure (two slots triggering on the same move) is invisible in a fill-only ledger.

**Decision it changes:** whether to keep manual overrides at all. The journal makes override alpha (actual − intended P&L) an estimable quantity with a session-clustered CI; if the CI excludes zero on the negative side, overrides are retired or restricted to a named class (e.g., "system fault" only). It also decides whether duplicate exposure is an intended portfolio effect or a slot-coordination bug.

## 2. Evidence (with labels) and the strongest competing explanation

- **OBSERVED:** The workspace contains no journal, so the six departure categories below cannot be counted today.
- **EXTERNALLY SUPPORTED (general practice, no page opened; search result only):** Institutional transaction-cost analysis and prop-desk audit practice routinely compare executed trades against a "decision benchmark" (arrival price / intended order); the override-alpha design below is the same idea applied to a discretionary intervention instead of a broker.
- **HYPOTHESIS:** Overrides cluster in sessions (news days, drawdown days), so row-level CIs will be overconfident. In the SYNTHETIC run below, the naive i.i.d. CI covered zero while the session-clustered CI did not — the sign of the inference can change.
- **Strongest competing explanation:** overrides might be *informed* by information the strategy does not use (visible order flow, news). If that is true, override alpha is positive and the journal should capture `override_info_source` so the information can be turned into a rule. The design is agnostic: it measures, it does not presume the override is bad.

## 3. Worked example / reproducible check / formula / data spec

### Journal schema (one row per eligible signal; a signal that never fired is not a row)

| Field | Type | Example |
|---|---|---|
| signal_id | str, unique | `2026-11-04_KX-eng_v3_0931_001` |
| strategy_slot | str | `KX_engulfing` |
| strategy_version | str (git hash or semver) | `v3.2` |
| instrument_signal / instrument_exec | str | `NQ` / `MNQ` |
| session_id | date+session | `2026-11-04_RTH` |
| t_signal, t_decision, t_order, t_fill | UTC ts (ns) | `13:31:00.000 / 13:31:04.2 / 13:31:05.0 / 13:31:05.4` |
| intended_side, intended_size | enum{L,S}, int | `L`, `2` |
| intended_entry, intended_stop, intended_target | float (pts) | `20512.25 / 20492.25 / 20552.25` |
| decision | enum{TAKEN, SKIPPED, DUPLICATE_BLOCKED, DUPLICATE_TAKEN, OVERRIDE, DELAYED, EXEC_ERROR} | `OVERRIDE` |
| reason_code | enum (controlled list) | `OVR_NEWS_RISK`, `SKIP_MAX_SLOTS`, `ERR_WRONG_QTY` |
| reason_text | str, free | `"CPI in 4 min, cut size"` |
| actual_side, actual_size, actual_entry, actual_stop, actual_target | as intended | `L, 1, 20513.00, 20492.25, 20552.25` |
| fill_price, fill_qty, exit_price, exit_time, exit_reason | float/int/ts/enum | `20513.00, 1, 20552.25, 13:58, TARGET` |
| pnl_actual_usd | float | `78.50` |
| pnl_intended_usd | float (counterfactual, same bars + fill model) | `157.00` |
| override_alpha_usd | float = actual − intended | `-78.50` |
| other_slots_state | JSON | `{"PX_weak":"FLAT","KX_selloff":"LONG 1 @20490"}` |
| open_position_before | JSON | `{"MNQ": +1}` |
| account_id, dd_remaining_usd | str, float | `acctA`, `1240` |
| decided_by | enum{AUTO, MANUAL} | `MANUAL` |

Primary key: `signal_id`. Every category above is a value of `decision`; the schema never needs a separate table per category.

### Override evaluation (formula)

For each row with `decision ∈ {OVERRIDE, DELAYED, SKIPPED, EXEC_ERROR}`:

1. Replay the *intended* order (side, size, entry, stop, target) on the same bar series from `t_signal` using the **same fill model as the backtest** (explicit assumption: limit fills require trade-through by one tick; stops fill at stop price plus 1 tick slippage; market orders fill at next bar open). State this model in the journal header; it is the largest hidden parameter.
2. `pnl_intended` = P&L of that replay; `pnl_actual` = ledger P&L (zero for SKIPPED).
3. `override_alpha = pnl_actual − pnl_intended`, in USD after commissions on both legs.
4. Aggregate: mean alpha with a **session-clustered bootstrap** (resample sessions with replacement, recompute mean; 95% percentile CI). Report `n_overrides`, `n_sessions_with_overrides`, and the per-session count distribution — a few sessions supplying most overrides is itself a finding.
5. Stratify by `reason_code` only after the pooled estimate; a reason with fewer than ~20 overrides across ≥10 sessions is reported as "not estimable".

**SYNTHETIC result** (script at `/tmp/claude-0/-home-user-Testing/7cf3ca0b-ccdf-5806-aa57-684759b9781e/scratchpad/override_alpha.py`, 40 sessions, Poisson(1.2) overrides per session, shared session shock): 39 overrides across 24 sessions, mean alpha −$14.7; session-clustered 95% CI [−28.5, −1.9]; naive i.i.d. CI [−31.8, +2.4]. Numbers are invented; the point is that clustering changed the conclusion.

### SYNTHETIC journal rows (6, one per category)

| signal_id | slot/ver | intended (side,size,entry,stop,tgt) | decision / reason | actual | t_signal→t_fill | pnl_act / pnl_int / alpha |
|---|---|---|---|---|---|---|
| 1104_KXeng_001 | KX_eng v3.2 | L,2,20512.25,20492.25,20552.25 | TAKEN / OK | L,2,20512.50 | 13:31:00→13:31:01 | +158 / +160 / −2 |
| 1104_PXweak_002 | PX_weak v1.4 | S,1,20540.00,20552.00,20510.00 | SKIPPED / SKIP_DISCRETION_CHOP | none | 14:02:00→— | 0 / +58 / −58 |
| 1104_KXsell_003 | KX_sell v2.0 | L,1,20498.00,20486.00,20530.00 | DUPLICATE_TAKEN / DUP_SAME_DIR (KX_eng already L 2) | L,1,20498.25 | 13:33:00→13:33:02 | −24 / −24 / 0 (exposure 3 vs cap 2) |
| 1104_KXeng_004 | KX_eng v3.2 | S,2,20560.00,20572.00,20520.00 | OVERRIDE / OVR_NEWS_RISK | S,1,20560.00 | 15:26:00→15:26:03 | +40 / +80 / −40 |
| 1104_PXweak_005 | PX_weak v1.4 | L,1,20530.00,20518.00,20560.00 | DELAYED / DLY_MANUAL_LATE | L,1,20536.50 | 14:45:00→14:45:41 | +47 / +60 / −13 |
| 1104_KXsell_006 | KX_sell v2.0 | S,1,20545.00,20557.00,20515.00 | EXEC_ERROR / ERR_WRONG_QTY (sent 10) | S,10,20545.00, flattened 14:51 | 14:50:00→14:50:01 | −125 / +30 / −155 |

## 4. When following this proposal would make the decision worse

- **Counterfactual contamination (HYPOTHESIS):** if the intended order would itself have moved the market or been partially filled, the replay overstates `pnl_intended`; at MNQ sizes of 1–3 this is negligible, at NQ sizes it is not.
- **Reason-code mining:** stratifying alpha by reason after seeing the data reproduces the Study 66 problem (best-of-search vs preselected). Pre-register the reason list.
- **Behavioral backlash:** a journal that punishes every override can push the trader to disable rules instead of logging overrides; the categories must be judgement-free labels.
- **Changing fill model mid-sample** silently changes alpha; version the fill model.

## 5. Cheapest decisive test, and the result that would retire the idea

**Test:** For 20 trading sessions, run the strategy engine in "shadow" mode that writes every eligible signal to the journal while the trader trades as usual. Join the ledger to the journal on `signal_id` (or nearest `t_order` within 60 s if IDs do not exist yet).
**Retire if:** (a) >95% of ledger trades match a TAKEN row within one tick and one second, *and* (b) fewer than 1 non-TAKEN row per 5 sessions. Then departures from intent are rare and the journal is overhead; keep only EXEC_ERROR logging.
**Retain if:** any single non-TAKEN category exceeds 10% of eligible signals or cumulative |override_alpha| exceeds 10% of gross P&L.

## 6. Missing inputs that materially limit the conclusion

- **UNKNOWN whether rejected signals are logged today.** The user can check in three minutes: (1) grep the execution platform's log directory for the strategy name on a day with no fills for that strategy — a hit means eligibility is logged; (2) count distinct strategy names in the fill ledger versus in the signal log; (3) look for any field resembling `reason`/`reject`/`blocked`. If only fills exist, the shadow logger in §5 is required.
- Fill model used in backtests (unknown); slot cap and duplicate-exposure rule (unknown); whether `strategy_version` is tracked at all (unknown); account rule constraints that might legitimately cause SKIP (unknown).
- **Minimum logging change (concrete fields):** `signal_id, strategy_slot, strategy_version, t_signal, intended_side, intended_size, intended_entry, intended_stop, intended_target, decision, reason_code, other_slots_state (JSON), open_position_before (JSON), dd_remaining_usd, decided_by`. Thirteen fields written at `t_signal`, before any order; fill fields are joined later from the ledger.

## 7. Filter accounting

The journal is not a trading filter, but treating "no overrides" as a filter gives:

- **Eligible signals:** all journal rows per session.
- **Trades retained:** rows with decision TAKEN (and DUPLICATE_TAKEN if the slot cap permits).
- **Losses avoided:** sum over OVERRIDE/SKIPPED rows where `pnl_intended < 0` of `−pnl_intended`.
- **Winners discarded:** sum over OVERRIDE/SKIPPED rows where `pnl_intended > 0` of `pnl_intended`.
- **Net change after costs:** Σ override_alpha (includes commissions on both legs); report with session-clustered CI.
- **Independent sessions:** `n_sessions_with_overrides`; required ≥ 30 before any reason-level conclusion.
- **Portfolio contribution:** Σ override_alpha ÷ gross strategy P&L over the same sessions, and share of max-drawdown days on which an override occurred.
