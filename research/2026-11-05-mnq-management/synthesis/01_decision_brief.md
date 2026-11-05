# Decision brief — post-entry management for MNQ entries (panel of 2026-11-05)

**Evidence status.** No signals, fills or market data exist in the workspace, so nothing here is market evidence. The panel ran on a SYNTHETIC test case in your export schema with a sealed holdout and planted ground truth. What transfers: the replay engine, the field list, four pre-registered policies with their decision rules, and a shadow-mode forward specification. Nine independent runs: six specialists, two reviewers, one director replay.

## Recommendation

**No management policy deserves promotion to live trading from this evidence. Two deserve a zero-cost shadow forward simulation, and one observational audit should run first.**

1. **Run the drift gauge and the continuation audit before anything else** (observational; no order changes). On the real export, compute the paired difference between exiting at the minute-10 open and the original outcome for every KX trade still open at minute 10 (≈ 150 per year), and `cont_R` (how far price continues past the target by 15:55) for every target exit. Every "hold the bracket" result in this panel rests on the synthetic data's post-entry drift; if the real gauge is within ±0.10R, those results do not transfer and breakeven rules become near-free insurance. If it is ≤ −0.25R with the CI excluding zero, hold-the-bracket is the right default and no tightening rule is worth running.
2. **Shadow C2 (KX late profit-conditional breakeven: at entry + 20 min, if open profit ≥ +0.3R, stop to entry).** Reviewer B: advance; Reviewer A: revise and retest. Both agree it costs nothing measurable (+0.01R per entry, CI ±0.07R) and that it executes exactly as modelled (one stop modify, zero rejected modifies, zero first-bar hits). Its value is tail reduction: P(final R < −0.5R) on the conditioned set 0.24 → 0.06 in development. The holdout changed one trade, so it is unproven either way. Decide at 60 conditioned and 15 changed trades.
3. **Shadow-log, do not act on, C1 (the +0.8R → +0.3R stall).** Your concrete question has no answer at this sample. Development (60 stalls): tightening to breakeven costs −0.35R per stall [−0.80, +0.11] and exiting costs −0.53R [−1.05, −0.02]; the holdout (13 stalls, all v2) shows +0.45R [−0.44, +1.12]. Reviewer A: revise and retest (undecidable by design at n = 13). Reviewer B: retire (materially harmful in development, worse drawdown, and 34 of 60 triggers are an exit one bar late because the next open is already at or through entry or the stop is hit in its first bar; director-verified count, Reviewer B's own count was 47). Resolution: ≈ 100 real stall trades, which at your frequency is about 20 months, and the v2 sign must hold on its own. The breakout and reversal answers differ only in that the stall state never occurs for reversals under the original policy (the midpoint target is a median 0.70R away).
4. **Retire C3 (add-leg stop at entry) as a P&L idea; keep the add.** The add earns +0.29R of its own risk and carries every top-decile winner. Protecting it costs −$320 per year and buys 0.4R of drawdown (Reviewer A: retire; Reviewer B: revise as a pure risk-policy count). If you want it for risk reasons, it must be a separate OCO for the add; a separate stop with a shared target orphans an order.
5. **Retire C4 (PX far target) as pre-registered; re-propose only after the continuation audit.** Development +0.40R per PX entry replicated in sign (+0.20R) but the holdout CI includes zero, and the no-target probe beats it on both sets, which means the gain is drift, not the level. Reviewer A: retire (rule fired as written). Reviewer B: advance conditional on the audit (rule fired on 28 of the 90 pre-registered trades). Preserved disagreement; the audit settles it.

**Setup, path, or time?** Time alone is the wrong driver: unconditional time exits lose in both periods and cut 19 of 24 largest winners. Path matters but the asymmetric bracket means "no progress" is not "failure" (trades at −0.5…0R at minute 15 still hit the 2–2.5R target 42% of the time). Setup matters in one direction only: breakout-style no-progress rules harm reversals, so reversals should be excluded from any breakout rule rather than given their own.

## The strongest reason to keep the original policy unchanged

Nothing beats it by a resolvable margin on data built in its own schema, and the only thing that did (dropping the target) is an artefact. Every tightening rule examined (≈ 381 cells across six specialists) loses or is null in development; the few that are null buy drawdown you cannot yet measure. Reviewer B's materiality floor ($1,000 per year or 2R of drawdown) is roughly what 16 exact-touch fill ambiguities alone move, so anything smaller is a convention, not a result.

## Reviewer verdicts (independent, preserved)

| Candidate | Reviewer A (methods) | Reviewer B (execution) | What resolves it |
|---|---|---|---|
| C1 stall → breakeven | Revise and retest | Retire | ≈ 100 real stall trades; drift gauge; v2-only sign |
| C2 late conditional breakeven | Revise and retest | Advance | 60 conditioned / 15 changed trades in shadow; tail metric on whole position with CI |
| C3 add-leg stop at entry | Retire | Revise and retest | P(target \| retrace to entry after add) on ≥ 15 retraces; separate-OCO structure |
| C4 PX far target | Retire | Advance, conditional | `cont_R` on real PX target exits; D2 − C4 as primary statistic at 90 trades |
| P0 original | Advance as control | Advance as control | A real MANUAL-exit rate well above 3% makes the desk's behaviour, not the bracket, the control |

## What to do next, in order

1. Export the fields in `02_inventory_and_export_fields.md`; run `src/S5/reconcile.py` (retire the replay if exact matches < 90% or unexplained dollars > 10% of net).
2. Run `src/director/holdout_run.py --data data/real --tag real --stage_b` and `src/S1/run.py` for the drift gauge; read the minute-10 cell and `cont_R` first.
3. Start the shadow log per `05_forward_simulation_spec.md` for C2 and C1 (log only), with the C3 count and the continuation audit as free by-products.
4. Reconvene when the drift gauge has 150 trades.

Numbers: `02_comparison_table.md`, `03_profit_vs_protection.md`; charts `charts/replay_1..4_*.png`; audit of the synthetic design `04_ground_truth_audit.md`.
