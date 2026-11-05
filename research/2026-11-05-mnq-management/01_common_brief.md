# Common Factual Brief — MNQ post-entry management panel, 2026-11-05

Issued by the research director to six specialists and two reviewers. Everyone receives this identical file. Work independently.

## 0. The question

> After one of the desk's existing MNQ entries fills, can a simple, executable management policy improve net results or materially reduce drawdown at an acceptable cost in profits?

Three candidate drivers are open questions: the original **setup** (breakout vs reversal), **what price does after entry**, and **elapsed time**. Concrete decision to answer: an MNQ long reaches +0.8R, stalls, and retraces to +0.3R. Hold the original bracket, tighten the stop, exit, or follow a predefined time rule? The answer may differ by setup; any distinction must be observable at decision time and supported by enough independent sessions.

**1R = planned dollar risk of the initial entry** (`planned_risk_usd` in `trades.csv` = initial contracts × stop distance × $2). This denominator is fixed for the whole trade, including after a pyramid add. Report every result in R **and** in dollars after costs.

## 1. Workspace inventory (OBSERVED by the director, 2026-11-05 07:20 ET)

| Looked for | Result |
|---|---|
| Repository `kantpiya/Testing` | One prior branch with a text-only research panel (different question). **No data, no strategy code, no logs.** |
| Signal logs, fill logs, stops/targets, strategy versions, position sizes, commissions | **None.** |
| Timestamped MNQ/NQ/ES market data | **None.** |
| User's computer via Remote Control | **Not linked.** |
| Toolchain | Python 3 with pandas 3.0, numpy 2.5, scipy 1.18, matplotlib 3.11. **No R.** |

**Consequence.** The empirical replay cannot be run here. The panel runs on a **SYNTHETIC test case** (Section 2) built in the exact schema the user will be asked to export. Every numeric result in this panel is therefore a result *about the method on synthetic data*, never about the market or the user's strategies. Label every number SYNTHETIC. The deliverables that transfer to the real data are: the replay code, the field list, the pre-registered policies, and the forward-simulation specification.

## 2. The SYNTHETIC development data set

Path: `data/synthetic/` (relative to this folder). Development window **2025-05-01 → 2026-04-30**, 242 RTH sessions, 332 executed trades. A chronological holdout (2026-05-01 onward) is **sealed**; the director opens it only after challengers are pre-registered. Do **not** open anything under `sealed/`, and do not read other files under `reports/`.

What the generator did (disclosed): a 1-minute random-walk price path with intraday volatility seasonality and session-level volatility, two signal families with explicit rules (`strategy_versions.csv`), and the original management policy executed on it with fixed cost and slippage assumptions. Some structure **may or may not** have been planted in what happens after entry; that is what you are testing. Treat the data the way you would treat the user's export.

### Files and fields

`bars_NQ_1min.csv`, `bars_MNQ_1min.csv` — 1-minute OHLCV, RTH 09:30–15:59 ET (390 bars/session). `ts` = bar **open** time, ISO 8601 with ET offset. NQ is the signal instrument for KX; MNQ is the execution instrument for everything. Market data continue after every historical exit (full session every day).

`signals.csv` — every signal emitted, executed or not: `signal_id, strategy, family, signal_instrument, exec_instrument, signal_ts (bar close time, ET), direction, ref_level, ref_width, planned_stop_dist_pts, planned_target_mult_R (KX only), planned_contracts, planned_risk_usd, executed, reject_reason, planned_target_px, planned_stop_px (PX only)`.

`fills.csv` — every fill under the original policy: `fill_id, trade_id, leg_id (1 = initial, 2 = add), ts_utc (UTC!), side, qty, price, order_type (MKT/STP/LMT), fill_role (ENTRY/ADD/EXIT), exit_reason, commission`.

`trades.csv` — the desk journal: `trade_id, signal_id, session, strategy, family, direction, entry_ts, entry_px, initial_contracts, added_contracts, add_px, add_ts, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason (STOP/TARGET/STOP_GAP/TIME_EOD/MANUAL), gross_pnl_usd, commission_usd, net_pnl_usd`. Exit timestamps are the **open** of the bar in which the exit occurred.

`strategy_versions.csv` — entry, stop, target, time exit, pyramiding and sizing rules per version with validity dates. KX_ORB_v1 → v2 on 2026-01-01 (target multiple 2.0R → 2.5R). PX_REV_v1 throughout. PX target is a structural level (opening-range midpoint) known at entry, so PX target R-multiples vary by trade.

`costs.csv` — commission $0.74 per contract per side all-in (ASSUMPTION), MNQ $2/pt, tick 0.25, assumed slippage 1 tick on market and stop fills, 0 on limits, position limit 4 MNQ across all strategies, flat at the 15:55 ET bar open.

Original policy, as documented: OCO bracket (stop + target) from entry; KX adds 1 contract at the next open after price reaches entry ± 1.0 × stop distance within 20 minutes of entry and before 12:00 ET, and the add **shares** the original stop and target; everything flat at 15:55. Whether the fills obey this exactly is for you to verify.

## 3. Public instrument facts (general knowledge; verify against CME specs)

MNQ $2/pt, tick 0.25 ($0.50). NQ $20/pt. RTH 09:30–16:00 ET. Integer contracts only: a 1-contract position cannot scale out half.

## 4. Experiment design everyone must respect

- **Stage A (paired, entries fixed):** replay the identical set of executed entries (same `trade_id`s, same initial size, same entry fill) under the original policy and under each alternative. Paired differences per trade; resample **whole sessions** for uncertainty. If an alternative holds longer and overlaps a later entry in the same session, flag it.
- **Stage B (chronological, portfolio):** replay the leading candidate in time order with the 4-contract limit, pyramiding rule, 15:55 cutoff and subsequent-signal eligibility (`signals.csv` includes rejected signals).
- A decision rule evaluated at minute *k* may use only bars whose close time ≤ decision time, and only trades still open at minute *k* under the policy being evaluated. Report trade count **and** distinct session count for every conditional statistic.
- Original policy + at most **four** challengers will be pre-registered for the holdout. Propose your challengers with: mechanism, decision time, parameters, fill assumptions, objective. **Count every policy and threshold you examined, including discarded ones**, and list them.
- Costs on every entry, add, partial exit and final exit. Stop fills: stop price − 1 tick adverse (or the bar open if it gapped through). Tightened stops that end in a bar which also touches the target: report both orderings.
- "Largest winners": define explicitly when you use the term (default: top 10% of trades by baseline net R, defined on the **baseline** policy and held fixed across policies).

## 5. Rules

1. Independence: do not read other reports; judges have not been convened.
2. Label every claim OBSERVED (computed on the synthetic data), HYPOTHESIS, or SYNTHETIC EXAMPLE (an illustrative case you constructed). Nothing here is EXTERNALLY SUPPORTED market evidence.
3. Code goes in `src/<your_id>/` with a `run.py` that regenerates your tables from `data/synthetic/`. Paste key output into your report. Save any figure to `charts/<your_id>_*.png`.
4. Report ≤ 1,500 words plus tables and code output, written to `reports/<your_id>_<slug>.md`, then reply with a 5-line summary and your proposed challengers.
5. The user is a physician-researcher fluent in causal inference and out-of-sample validation; do not explain those. **Do** explain market-execution assumptions.
6. Any R or dollar number must state its denominator (trades, sessions) and whether costs are included.

## 6. Required report sections

1. Strongest finding and the decision it changes
2. Evidence (labelled) and the strongest competing explanation
3. Reproducible check (code path + pasted output)
4. When following this would make the decision worse
5. Cheapest decisive test on the user's real data, and the result that retires the idea
6. What the real export must contain for this test (exact fields)
7. Policies and thresholds examined (complete count, including discarded)
8. Proposed challenger(s) for pre-registration: mechanism, decision time, parameters, fill assumptions, objective

## 7. Specialist mandates (each specialist executes only their own)

**S1 Trade-path statistician.** Map post-entry paths per family: time to +0.3R/+0.8R/−0.5R milestones, revisits of entry, outcome distribution after a stall (e.g., reached ≥+0.8R then back to ≤+0.3R). For a decision at minute *k*, include only trades still open at minute *k*. Deliverable: a table answering "given what was observable at this point, what happened next?", with trades and sessions per cell.

**S2 Breakout / failed-follow-through.** Test one simple early-exit rule for directional entries: little progress within a fixed time ⇒ exit. Define progress without future bars. Compare with an unconditional time exit at the same horizon. Show how often the rule exits shortly before a large winner. Deliverable: one executable failure rule, one simpler comparator, and worked examples of a useful exit and a costly false alarm.

**S3 Reversal / profit-taking.** For PX: original structural target vs time exit vs structural exit tied to a level known at entry. Test "a slow reversal is a bad reversal". Check whether a rule developed on breakouts harms reversals. Deliverable: setup-specific recommendation, or a finding that separate management is not justified.

**S4 Pyramiding / winner retention.** Separate initial leg from the add. Compare managing all legs together vs managing the add separately (e.g., add-only breakeven, add-only trail). Give-back from peak open profit and earnings from the largest winners, per policy. Integer contracts. Deliverable: leg-by-leg replays of a trade where protecting the add helps and one where it damages a major winner.

**S5 Execution / replay engineer.** Reconstruct the original policy from `strategy_versions.csv` and the bars; compare reconstructed exits and net P&L with `trades.csv`/`fills.csv`; quantify unexplained differences. Verify signal vs execution instrument, tick rounding, session cutoffs, gaps through stops, stop/target same-bar ordering, UTC/ET alignment, costs on every leg. Deliverable: a reproducible replay engine (`src/S5/replay.py`) usable for any policy, and a list of policies the data are too coarse to distinguish.

**S6 Skeptical portfolio manager.** Try to defeat the strongest plausible improvement (your own best guess of it, built independently): single exceptional sessions, narrow parameters, optimistic fills, one strategy version, position limits and overlapping signals (Stage B). Deliverable: the strongest reason to keep the original policy, and the cheapest experiment that settles it.

## 8. Reviewer mandates (convened after all six reports are saved)

**Reviewer A (quantitative methods):** timestamp integrity, comparison fairness, uncertainty, selection bias.
**Reviewer B (MNQ execution trader):** executability with integer contracts and 1-minute data; whether the benefit is large enough to matter after costs.
Each independently gives one verdict per candidate: advance to forward simulation / revise and retest / retire.
