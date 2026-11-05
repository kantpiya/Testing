# C3 — Human Factors and Decision Support

**Question:** Can the trader tell "historically unfavorable", "insufficient evidence", "input unavailable" and "account limit reached" apart under time pressure?

**Short answer (HYPOTHESIS):** Not if they share a card, a color scale, or a single "confidence" number. They are four different kinds of statement (a negative result, an absence of result, a broken measurement, a rule), so they need four different *actions*, not four colors. OBSERVED: no interface, logs or strategy code exist in the workspace, so everything below is a specification, not a review of an existing screen.

## 1. Strongest finding or proposal, and the decision it would change

Proposal: encode each state by **(a) a word, (b) a glyph, (c) screen position, (d) which button is enabled, (e) an explicit denominator**, and never by hue alone. Replace any 0–100 confidence score with the tuple **(n sessions, effect after costs, 95% CI, cost assumption)** or a three-level written evidence grade.

Decision changed: whether a *valid baseline signal is skipped*. The predicted dominant error is treating "insufficient evidence" as "unfavorable". That error silently removes trades from the most recent (least-sampled) slots, which is exactly where strategy drift would first show up, and it never appears in the P&L as a loss, so the trader does not learn from it.

## 2. Evidence (with labels) and the strongest competing explanation

- OBSERVED: workspace is empty; no screen, log or study to inspect.
- EXTERNALLY SUPPORTED (general HCI literature, not fetched; "search result only" level): redundant coding (shape + text + position) is the standard accessibility practice because ~8% of men have red–green deficiency and because hue discrimination degrades under time pressure and in peripheral vision. Treat as background knowledge, not a cited result.
- HYPOTHESIS: the four-way confusion is most likely between *unfavorable* and *insufficient*, because both are "the stats say something non-positive" and both are typically painted the same warning color.
- Strongest competing explanation: the trader does not confuse the states at all; the real cost is **time** (reading four fields per signal) and the overlay simply slows entries past the executable window. The replay task in §5 measures both, so this is testable rather than argued.

## 3. Worked example / wireframe / data spec

| State | Word + glyph | Position | Allowed / blocked | Denominator line (SYNTHETIC) | Trader does |
|---|---|---|---|---|---|
| **UNFAVORABLE** | `UNFAV` + filled down-triangle | inside signal card, left strip | Entry button disabled; **Override** button enabled, requires typed reason, logged | "14 of 19 sessions net-negative; −3.1 R-ticks/trade after costs; 95% CI [−5.2, −1.0]; window 2026-07-01→10-31" | Skip. Override only with a reason you would defend in the monthly review |
| **INSUFFICIENT** | `PENDING n=6/20` + hollow circle with "?" | inside signal card, same strip | Entry button **enabled and default-highlighted**: "TAKE per baseline rule" | "6 sessions (need ≥20); effect −0.8 R-ticks, CI [−6.1, +4.5]" | Take the signal at the baseline rule. Evidence is accumulating, not negative |
| **INPUT UNAVAILABLE** | `NO INPUT: ES` + hatched box | top of signal card, replaces the stat line | Filters that *require* the input are off; card says which slots are blocked and which still trade | "ES quote stale 47 s (last 09:41:13). Blocks: KX-SMT. Does not block: PX-engulf" | Trade slots that do not need the input; stand down on those that do; check feed |
| **ACCOUNT LIMIT** | `LOCKED` + padlock | **full-width banner across the top, not in the card** | Entry blocked at order routing; no override | "Daily loss used $412 of $500 (82%); next MNQ loss at 20 pt ≈ $40 + fees would breach" | Stop. Flatten if rule requires. Log. Separate *approaching* (amber, numbers only) from *reached* (lock) |

Design rules that make them unconfusable: four distinct words that are not synonyms; four distinct glyphs; account limit lives in a different screen region; and the *enabled button set differs for every state* (skip-with-override / take / partial / nothing). A trader who only sees shape or only reads the button still gets the right state.

Logging spec (needed for §7 and for the replay task): per signal, `signal_id, ts, strategy_slot, state_shown, n_sessions_shown, effect_shown, ci_shown, cost_assumption, action_taken, override_reason, decision_latency_ms`. The brief notes it is unknown whether current logs record rejected signals; without `state_shown` and `action_taken` for rejected signals, none of the accounting below is computable.

**Likely operator error and mitigation, one per state (HYPOTHESIS):**
- Unfavorable → "this one looks different", override. Mitigation: typed reason, override count displayed with its own realized P&L ("your 11 overrides: −4.2 R-ticks net").
- Insufficient → read as unfavorable, skip a valid signal. Mitigation: wording leads with the verb ("TAKE"), the button stays default, and the state is never painted the warning color.
- Input unavailable → read as "no filter, so everything is fine" (or the opposite: freeze entirely). Mitigation: each strategy slot declares required vs optional inputs in advance; the card lists blocked and unblocked slots by name.
- Account limit → "approaching" treated as "reached" (stops early) or "reached" treated as a soft warning (keeps trading). Mitigation: two visually separate states, and the hard block enforced in routing rather than by the screen.

**Confidence score:** a single 0–100 number cannot distinguish "n=6, big effect" from "n=40, tiny effect" from "feed stale". If a grade is wanted, use written criteria: **A** n≥30 sessions, CI excludes zero after costs, sign holds in the most recent 12 weeks; **B** n≥20, point estimate negative, CI includes zero; **C** n<20 or an input missing. Direction (favorable/unfavorable) is shown separately from grade. Grade C is "insufficient", never "unfavorable".

## 4. When following this proposal would make the decision worse

- If the "unfavorable" statistics come from the best slot in a parameter search (Study 66 concern, USER-SUPPLIED CONTEXT), the display will confidently show a selected-subset effect. The denominator line must state whether the slot was preselected.
- Thresholds (n≥20) create flicker near the boundary; without hysteresis the same slot alternates states day to day and trains the trader to ignore it.
- Four fields per card may push decision time past the executable window; then a two-state screen (TAKE / DON'T, with details one tap away) beats a correct four-state one.
- Replay without money at risk understates stress; good replay results are necessary, not sufficient.

## 5. Cheapest decisive test, and the result that would retire the idea

**Replay task.** N historical signals, each shown as bars up to signal time with a hard response deadline (e.g., 8 s). Two conditions, within-trader: overlay on vs. raw stats only; same signals, counterbalanced order, ≥1 week between passes. Ground truth = the strategy's intended action given the true state (take / skip / partial / blocked). Signals stratified so each state has ≥15 cases, including constructed account-limit and stale-feed cases, and including insufficient-evidence cases whose correct action is TAKE.

Outcomes: (1) agreement with intended action, primary, paired McNemar on discordant pairs; (2) median time-to-decision, log-scale; (3) a 4×4 confusion matrix of perceived vs true state, so error *types* are counted, not just totals.

Minimum N (SYNTHETIC simulation, paired design with correlated signal difficulty):

```
N=  40  power(err 0.25 -> 0.10)=0.52   power(0.25 -> 0.15)=0.21
N=  80  power(err 0.25 -> 0.10)=0.85   power(0.25 -> 0.15)=0.47
N= 120  power(err 0.25 -> 0.10)=0.96   power(0.25 -> 0.15)=0.63
N= 160  power(err 0.25 -> 0.10)=0.99   power(0.25 -> 0.15)=0.77
```

So N≈80 if the overlay is expected to cut errors by more than half, N≈160 for a modest gain. Retire the idea if agreement does not improve, or if it improves but median latency rises past the strategy's executable window, or if the overlay introduces a new error class (overrides) that the raw-stats condition did not produce.

## 6. Missing inputs that materially limit the conclusion

Strategy definitions and which inputs each slot requires (ES, NQ, depth); the actual account rules per prop account; whether logs record rejected signals and decision latency; the trader's real executable window per strategy; cost assumptions used in the "after costs" line; whether displayed statistics are preselected or search-selected.

## 7. Filter accounting

The overlay is not a filter, but it changes which signals get taken, so it must be accounted like one, using `state_shown` × `action_taken`:

- Eligible signals: all signals fired, by slot and session.
- Trades retained: `action_taken = take`.
- Losses avoided: skipped under UNFAVORABLE with negative counterfactual outcome at the baseline exit.
- Winners discarded: skipped under UNFAVORABLE *or INSUFFICIENT* with positive counterfactual; the INSUFFICIENT share is the operator-error cost.
- Net change after costs: Σ(retained realized) − Σ(baseline realized), ticks after commissions and assumed slippage, stated explicitly.
- Independent sessions: trading days, with the per-day sum as the unit.
- Portfolio contribution: net change attributed per slot, so a screen that helps one slot and harms another is visible.

Word count: 1,176 excluding the one table and one code block.
