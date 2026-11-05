# B2 — Heterogeneous effects: does a condition *distinguish* strategies, or just move all of them?

B2, 2026-11-05. Inputs: common brief only; no data, code, logs or study reports exist in the workspace (OBSERVED). KX/PX/engulfing and Studies 66/71 are USER-SUPPLIED CONTEXT (unverified). Simulation code and output (SYNTHETIC): `/tmp/claude-0/-home-user-Testing/7cf3ca0b-ccdf-5806-aa57-684759b9781e/scratchpad/B2/`.

## 1. Strongest finding or proposal, and the decision it would change

**Proposal (HYPOTHESIS, supported by SYNTHETIC check):** Replace "best strategy per condition" tables with one model: per-trade net P&L in R (risk units; ticks net of commission and assumed slippage, divided by initial stop in ticks)

  y_i = α + Σ_s β_s·Strat_s + Σ_c γ_c·Cond_c + Σ_{s,c} δ_sc·Strat_s·Cond_c + ε_i, SE clustered by trading session.

The decision it changes: **a strategy slot is switched off (or resized) in a condition only if the interaction block δ is non-zero and the specific δ_sc is large relative to its clustered SE.** If only γ (condition main effect) is non-zero, the right action is portfolio-level (size everything down or up in that condition, or skip it), not strategy-specific routing. Per-strategy sorting cannot make this distinction; SYNTHETIC: it manufactures a different "winner" per condition 85% of the time when no interaction exists.

## 2. Evidence (with labels) and the strongest competing explanation

- OBSERVED: no logs exist, so whether rejected/eligible signals are recorded is unknown. This decides which estimand is reachable (section 3).
- SYNTHETIC (Monte Carlo, 400 reps, ~250 sessions, 3 strategies × 3 conditions, session random shock shared across strategies, t(5) noise, 1,400 trades/rep):
  - Null interaction: naive per-condition sorting names *different* best strategies across conditions in **84.8%** of replications and names a non-best strategy in ≥1 condition in 88.2%. Cluster-robust Wald test of the δ block rejects at **6.5%** (nominal 5%).
  - True interaction (ENG −0.45R in Calm, +0.60R in Volatile): power **88%**. At half that size (−0.225/+0.30R): power **34%** — so ~250 sessions detect only large interactions.
  - Strong session shocks (SD 0.8R, ~6 trades/strategy/session): iid SEs reject a *true-null condition main effect* **25.7%** of the time vs 7.3% clustered. The interaction block stayed near nominal under iid SEs (5.0%) **because strategies co-traded the same sessions, so the interaction is a within-session contrast and the session shock differences out.** This protection disappears under non-overlapping support (section 3).
- EXTERNALLY SUPPORTED (general knowledge, no page opened): CR1 cluster-robust inference is adequate at G≈250; below ~40 clusters use a wild-cluster bootstrap.

**Strongest competing explanation for any apparent "strategy × condition" effect: differential opportunity sets.** If KX fires 0.4×/session in Calm and ENG 3×/session, their Calm cells hold different bars, times-of-day and (via session shocks) effectively different sessions; a nonzero δ then reflects *when each strategy chose to fire*, not performance under the same condition. Second competitor: condition defined from the same price path that generates the trade (look-ahead); it must be computable at signal time from a fixed anchor (e.g., session-relative ATR at the bar close before entry).

## 3. Worked example / reproducible check / formula / data spec

**Fixed-effects specification (per trade or per eligible signal):**
- Outcome: net P&L in R. Per-signal version: assign 0R to rejected-but-eligible signals only if "rejected" means a deliberate filter; otherwise analyse executed trades and state the selection.
- Fixed effects: strategy (reference = largest), condition (reference = "Normal"), full interaction. Add session-type and time-of-day block indicators as covariates *if* condition is not already session-specific.
- Variance: CR1 by session ID (one session = one Globex day, or RTH day if all trades are RTH). Report for each cell: n_trades, **n_unique_sessions**, mean R, cluster SE. Rule: do not report a cell with < 20 unique sessions as a point estimate; report it as "insufficient" or only via the shrinkage model.
- Test: joint Wald F on δ (q = (S−1)(C−1), denominator df = G−1). Then, only if the block rejects, inspect individual δ_sc with Holm or a max-|t| bootstrap.

**Hierarchical version:** δ_sc ~ N(0, τ²) (REML or empirical Bayes); each cell deviation is shrunk toward the additive fit with weight τ²/(τ² + SE_sc²). In the SYNTHETIC run the 20-session KX-Calm cell got weight 0.10, 90-session cells ~0.5: sparse cells are discounted automatically. **It earns its place when (a) cells are many or sparse (≥ 4 × 4, or any cell < 40 sessions) or (b) the decision is a continuous sizing rule rather than a yes/no switch.** With 9 well-populated cells the fixed-effects Wald test is sufficient and more transparent; with only 9 cells τ² is itself poorly estimated (0 in the null draw; 0.011 in the interaction draw, shrinking a true +0.60R effect to +0.08R), so use a prior on τ² or report both versions.

**Positivity / non-overlapping support.** If strategy s never (or rarely) fires in condition c, δ_sc is not identified; any number there is extrapolation. Even with partial overlap, within-condition comparison compares strategies on different bars. Under non-overlap only the *descriptive* statement survives — "s, as it historically fired, earned x R per trade in c" — valid for sizing the existing slot, not for ranking strategies or claiming c *causes* s to beat s'. **Same-opportunity design requires:** every strategy's eligibility evaluated and logged at every bar (signal/no-signal; if signal, executed/rejected with reason) with the condition as computed at that bar. The estimand then becomes within-bar: on bars where ≥2 strategies were eligible, which rule earned more — fit the interaction model on the eligible-signal set with bar fixed effects, and the positivity check is bars per (s,c) cell.

```text
SYNTHETIC output (Case A: condition = pure main effect; 249 sessions, 1,430 trades)
Interaction Wald, cluster-robust: p = 0.262 (correctly not rejected)
Cell (n_trades/n_sessions/mean R):
  KX  Calm 30/24/+0.20   Normal 194/88/+0.14   Volatile 216/66/+0.51
  PX  Calm 156/69/-0.08  Normal 207/92/+0.28   Volatile 128/61/+0.17
  ENG Calm 227/75/-0.42  Normal 206/86/-0.05   Volatile 66/38/+0.18
Naive "best per condition": Calm=KX, Normal=PX, Volatile=KX   <- spurious; truth is PX everywhere
Monte Carlo (400 reps): null rejection 6.5%; naive sorting disagrees across conditions 84.8%
True interaction (-0.45/+0.60 R): power 88%; half-size: 34%
```

## 4. When following this proposal would make the decision worse

- If condition is session-level and strategies fire in disjoint sessions, cluster and cell coincide, there is no within-cluster contrast, and the Wald test is uninformative, not conservative.
- If heterogeneity lives in the tail (ENG's Volatile edge is a few +8R days), mean-R interactions miss it; add a trimmed or quantile outcome.
- If condition categories were chosen after seeing per-strategy results (the Study 71-type definition-sensitivity problem, USER-SUPPLIED), the p-value is post-selection and understated; pre-register the definition.
- If the trader only ever removes slots, shrinkage toward the main effect delays removing a genuinely bad cell; acceptable only when a false removal costs more than a false retention.

## 5. Cheapest decisive test, and the result that would retire the idea

Fit the fixed-effects model on all executed trades with session-clustered SEs and report the joint δ Wald p-value plus the table in section 3. **Retire strategy-specific condition routing if p > 0.10 and no |δ_sc| > 0.3R with ≥ 40 sessions.** Retire the hierarchical add-on if τ̂² = 0 or if its cell estimates differ from the fixed-effects estimates by < 0.1R everywhere. Retire the *same-opportunity* logging investment if fewer than ~25% of signal bars have ≥ 2 eligible strategies (then there is no overlap to exploit anyway).

## 6. Missing inputs that materially limit the conclusion

- Whether logs contain rejected/eligible signals (OBSERVED: unknown). Without them only the as-fired estimand is available.
- Condition definition, its information set at signal time, and whether it is bar- or session-level.
- Unique sessions per cell for the real strategies; ~250 sessions detect only interactions ≳ 0.5R.
- Cost model (commission + slippage per contract) for net R; gross-R interactions can flip after costs when trade frequency differs by strategy.
- Whether strategies share fills on the same move (brief §2): the session cluster handles that dependence; a per-strategy cluster would not.

## 7. Filter accounting (the seven quantities)

| Quantity | How computed for a "switch off strategy s in condition c" rule |
|---|---|
| Eligible signals | all logged signals of s where condition = c at signal time (requires eligible-signal log; else executed trades, stated as such) |
| Trades retained | signals of s outside c, plus all other strategies |
| Losses avoided | Σ negative-R trades of s in c (reported with n_sessions) |
| Winners discarded | Σ positive-R trades of s in c |
| Net change after costs | −(mean R_sc × n_sc) in net R, with cluster CI; compare to δ̂_sc CI, not to the raw cell mean |
| Independent sessions | unique sessions in cell (s,c); < 20 ⇒ no decision |
| Portfolio contribution | change in session-level portfolio R mean and its SD; a cell removal that lowers portfolio SD more than mean may be kept on Sharpe grounds even when δ_sc ≈ 0 |
