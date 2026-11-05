# B4 — Portfolio construction and tail risk: which slots are duplicates, which help on bad days

**Specialist:** B4 · **Panel:** 2026-11-05 · **Inputs OBSERVED:** only `00_common_brief.md` (no data, code, logs or study reports exist in the workspace). Everything numerical below is SYNTHETIC unless labeled otherwise. Scratch code: `/tmp/claude-0/-home-user-Testing/7cf3ca0b-ccdf-5806-aa57-684759b9781e/scratchpad/B4/synthetic_portfolio.py` (output in `output.txt` beside it).

## 1. Strongest finding or proposal, and the decision it would change

**Proposal (HYPOTHESIS):** Evaluate every strategy slot by its *marginal* contribution to a fixed baseline book on a *fixed* set of sessions, not by its standalone statistics. The decision it changes: whether a second same-direction MNQ signal is *taken* while an MNQ and an MES long are already open. Two slots that load on the same intraday NQ move are duplicates in the sense that matters: their stops are hit in the same minutes and their losses land on the same sessions. A slot earns a place only if it is positive (or materially less negative than its share of exposure) on the baseline book's worst-10% days.

Market-specific assumption: MES and MNQ are not two instruments here. ES and NQ intraday returns are highly correlated (HYPOTHESIS; estimate on the user's own sessions), so "1 MES + 1 MNQ long" is one directional bet of roughly 1.5 MNQ-equivalents.

## 2. Evidence (with labels) and the strongest competing explanation

- OBSERVED: no logs, so it is unknown whether rejected/skipped signals are recorded. Without them the "skip" arm of every comparison below is unobservable (see §6).
- Public, verify against CME specs: MNQ $2/pt, MES $5/pt (brief §3).
- SYNTHETIC (script above): with placeholder levels NQ=20,000 and ES=5,500 and placeholder beta_ES|NQ=0.75, adding a second MNQ long raises the NQ-equivalent book delta from $606 to $1,006 per 1% move (+66%). On the fixed worst-10% baseline days, adding the duplicate slot moves the mean from −$350 to −$488; a counter-factor slot with the *same* standalone mean moves it to −$132. P(all three slots lose) = 0.23 vs 0.11 under independence (ratio 2.1). P(B stopped | A stopped) = 0.53 vs unconditional 0.24.
- HYPOTHESIS: the user's KX/PX/engulfing/weak-reversal/sell-off-recovery slots have unknown factor loadings; similar names do not imply similar exposures (brief §2), nor do different names imply different ones.

**Strongest competing explanation:** the second signal may carry genuine incremental information (different timing or trigger) so that its conditional expectancy, given the first is open, exceeds the first's. Then taking it is right in expectation and the question becomes sizing (half-size add, or replacing the MES leg). The marginal-contribution test in §3 resolves this; exposure arithmetic alone cannot.

## 3. Worked example / reproducible check / formula / data spec

**Definitions (compute specs).**

1. *Net directional exposure* at minute t: `D_t = Σ_i q_i · M_i · P_i · β_i` in $ per 1% NQ move, where q = signed contracts, M = $/pt multiplier (MNQ 2, MES 5), P = index level, β = 1 for NQ-based, β_ES|NQ for ES-based. β_ES|NQ = slope of 5-min ES % returns on NQ % returns over the prior 20 sessions, RTH only (excluding the first 5 min after 08:30 and 14:00 ET releases). Report β's standard error; if it drifts, re-estimate per session.
2. *Correlation-adjusted exposure*: `σ_book = sqrt(wᵀ Σ w)` with Σ the slot P&L covariance from prior sessions; diversification ratio = σ_book / Σσ_i. A slot whose addition leaves the ratio ≈ unchanged while raising D_t is a duplicate.
3. *Joint stop-out*: pairs (i, j) whose stop fills occur within k = 15 minutes (also report k = 5, 60). Statistic: P(j stopped within k | i stopped) vs unconditional P(j stopped in any k-min window), using session-level block bootstrap for the interval.
4. *Loss clustering*: per session, count of losing slots among the active set. Compare P(all active lose) and var(count) with the independence values Π p_i and Σ p_i(1−p_i). P(≥2 of 3) is uninformative when p_i ≈ 0.5 (SYNTHETIC: 0.474 vs 0.470 while P(all lose) is 2.1× independence).
5. *Marginal contribution*: fix the baseline book B (all currently approved slots, fixed sizes). Define W = the 10% of sessions with the lowest B P&L. For candidate slot S, report mean P&L of (B) and (B+S) on W, on all sessions, and S alone on W. The day set W is frozen before S is examined and is identical for every candidate. Also report the "swap" arm (B − MES + S) so sizing alternatives are visible.

```
SYNTHETIC output (abridged)
Baseline NQ-equiv delta $606/1%; +second MNQ $1006/1% (+66%)
Diversification ratio: base 0.87 | +duplicate 0.83 | +counter-factor 0.56
P(all 3 lose): obs 0.232 vs indep 0.111 (ratio 2.09); var(#losing) 1.24 vs 0.75
P(B stop | A stop) 0.53 vs P(B stop) 0.24 ; P(C stop | A stop) 0.10 vs 0.22
Fixed worst-10% baseline days:   baseline mean -350 | +dup -488 | +counter -132
Pyramiding pair (trail d, pyramid): captured-MFE(>=3R) / give-back frac(>=1R -> <=0)
  d=0.5: 0.16 / 0.00   d=1.0: 0.35 / 0.07   d=2.0: 0.72 / 0.19   (no pyramid)
  d=0.5: 0.15 / 0.04   d=1.0: 0.31 / 0.18   d=2.0: 0.67 / 0.30   (add 1 unit at +1R)
```

**Pyramiding as a portfolio question (USER-SUPPLIED context: retain large winners vs give back open profit).** Metric pair, both computed per trade on the same trade set:
- *Captured-MFE fraction* = realized P&L / potential MFE, averaged over trades whose potential MFE (initial stop only, no trail) ≥ 3R. Measures retention of large winners.
- *Give-back fraction* = share of trades that reached ≥ 1R open profit and closed ≤ 0.

A trailing-stop tightening is a single control that improves the second metric and harms the first monotonically (SYNTHETIC: d 2.0→0.5 cuts give-back 0.19→0.00 but capture 0.72→0.16). Pyramiding moves both in the bad direction in this synthetic setting because added units are bought at higher prices and raise the give-back on the same path. The user must choose a target on *one* metric and accept the other, or optimize session-level CVaR directly; no control improves both.

## 4. When following this proposal would make the decision worse

- If the baseline's worst-10% days are dominated by a few event sessions (CPI/FOMC), W is small and regime-specific; a slot that merely avoids those days looks protective without being so next regime. Run an event-day-excluded sensitivity arm and refresh W on rolling windows.
- If the second signal is systematically later and better timed, skipping it discards alpha; report the swap arm (replace MES with S), not only take/skip.
- If β_ES|NQ is estimated across a sector rotation, the NQ-equivalent delta is biased; report with and without the β adjustment.
- With 2–3 years of sessions, W holds ~50–70 sessions; differences under ~1 stop-loss per session are noise.

## 5. Cheapest decisive test, and the result that would retire the idea

Test: from the trade log, reconstruct per-session slot P&L; fix B; compute W; for the second-MNQ-signal slot compute (B+S) − B on W and on W's complement with a session-block bootstrap (1,000 resamples). Retirement result: if mean (B+S) − B on W is ≥ 0 (or ≥ −0.3 × S's mean absolute daily P&L) with a 90% interval excluding a large negative value, S is not a duplicate in the sense that matters; the take/skip rule is retired in favor of a sizing rule. Cost: one afternoon if the log contains the fields in §6.

## 6. Missing inputs that materially limit the conclusion

- Trade log fields required: slot id, instrument, signed size, entry/exit timestamps to the minute, stop price and whether exit was a stop fill, per-trade MFE/MAE (or minute bars to recompute them), and — critically — **rejected/skipped signals with their hypothetical entry, stop and exit**, else the "skip" arm is unobservable.
- Minute bars for NQ/ES over the same sessions, for β and joint-stop windows.
- The actual approved slot list and sizes that define the baseline book.
- Index levels at trade time (roll dates).

## 7. Filter accounting (the seven quantities in rule 3)

| Quantity | Definition for "skip second same-direction MNQ signal while MES+MNQ long are open" |
|---|---|
| Eligible signals | Second-slot signals firing while ≥1 same-direction MNQ or MES position is open (from log, including rejected) |
| Trades retained | Eligible signals with no open same-direction position, plus all other slots unchanged |
| Losses avoided | Σ of negative hypothetical P&L of skipped signals, by session |
| Winners discarded | Σ of positive hypothetical P&L of skipped signals, by session |
| Net change after costs | (B) − (B+S) per session, commissions and 1-tick slippage per side included for S |
| Independent sessions | Sessions with ≥1 eligible signal; block-bootstrap by session; report n in W and in its complement |
| Portfolio contribution | Mean and CVaR10 of (B+S) − B on fixed W and overall; diversification ratio with/without S |

Prose word count ≈ 1,190 (excluding the one code block and one table).
