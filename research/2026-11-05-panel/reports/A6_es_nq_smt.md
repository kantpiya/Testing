# A6 — Cross-index relative value: does ES–NQ divergence ("SMT") add information for MNQ?

Panel 2026-11-05 · Author: A6 (cross-index RV quant) · Inputs: common brief only. No bars, logs, or strategy code exist in the workspace (OBSERVED), so everything below is a specification plus a labelled SYNTHETIC check.

## 1. Strongest finding or proposal, and the decision it would change

**Proposal (HYPOTHESIS):** Replace any direction-only SMT rule (higher-high / lower-high, sign agreement) with a *continuous, beta-adjusted ES residual* and test it as a nested addition to an NQ-only baseline. Direction is a coarsening of magnitude: once the residual is in the model, the sign flag should carry nothing. In the synthetic run this is exactly what happens (direction t = 1.8 vs magnitude t = 5.6 when both are present).

**Decision changed:** whether SMT remains a condition in any strategy slot, and *in what form*. If the nested test (Section 3) shows no out-of-sample incremental R² for magnitude, SMT should be removed as a condition entirely; if magnitude wins but direction does not, every HH/LH rule should be rewritten as a residual z-score threshold — which also fixes the event-count fragility the user saw in Study 71 (USER-SUPPLIED CONTEXT).

## 2. Evidence (with labels) and the strongest competing explanation

- OBSERVED: workspace contains no data; no claim about real ES–NQ behaviour can be made from files.
- EXTERNALLY SUPPORTED (general knowledge, not fetched tonight): ES and NQ are both CME Globex equity-index futures with 0.25-tick grids and share a daily halt 17:00–18:00 ET (common brief §3). Their minute-level return correlation is high; treat the exact level as unverified.
- HYPOTHESIS: most "SMT" that traders see is NQ's own momentum/mean-reversion plus a vol regime, which an NQ-only model already captures. The ES residual is the only part that can be new.
- SYNTHETIC: Section 3 shows the nested test recovering a small injected ES signal and correctly rejecting a null.

**Strongest competing explanation:** apparent SMT edge is (a) a stale-leg artefact (one leg's last print is old, so divergence is manufactured), or (b) a time-of-day effect (opening drive, 10:00 data, 14:00 FOMC) that *both* legs share and which a time-of-day control absorbs. The nested design tests both directly: control for time of day, drop stale bars, and ask whether anything is left.

## 3. Worked example / reproducible check / formula / data spec

**Synchronised feature definition (spec):**

1. *Alignment.* Use exchange transaction timestamps (Globex, UTC), never receipt time. Build a common 1-minute grid; each leg's bar close = last trade with ts ≤ grid boundary; store `last_trade_ts` per leg. Map both legs to the same contract month via a per-leg volume roll and flag the roll session.
2. *Tick grids.* At NQ ≈ 20,000 one tick is 1.25 bp; at ES ≈ 6,000 it is 0.42 bp (public, verify). Use log returns; for HH/LH logic require excursions ≥ 2 NQ ticks / ≥ 1 ES tick (or ≥ 0.1 session-minute ATR) so a one-tick wobble is not a "divergence".
3. *Direction.* `smt_dir ∈ {−1, 0, +1}`: NQ up over k bars and ES not = −1 (bearish), NQ down and ES not = +1, agreement = 0. HH/LH variant: compare each leg's k-bar high to its prior-swing high.
4. *Magnitude.* `smt_mag = r_ES,k − β̂·r_NQ,k`, where β̂ is OLS of ES on NQ k-bar returns using only the previous 20 sessions; z-score by the prior-session residual std. Session-minute-of-day vol normalises both legs.
5. *Stale-data check.* `age_leg = bar_close − last_trade_ts`. If either age > 30 s in RTH (5 min overnight) or |age_ES − age_NQ| > 30 s, set all `smt_*` to NaN for that bar. Never forward-fill the stale leg; if quotes exist, use mid-quote change for the stale leg instead. Report the stale fraction by minute-of-day.
6. *NQ-only comparator.* `y_{t,h} = α + Σ(tod bins) + b₁·mom_k + b₂·vol₂₀ + b₃·mom_k×vol₂₀`, forward MNQ return h bars ahead, non-overlapping windows, session-clustered SEs.
7. *Direction vs magnitude.* Nested: M0, M0+dir, M0+mag, M0+both. Cluster-robust Wald on the added terms; session-blocked expanding-window OOS incremental R²; decile table of after-cost forward return by `smt_mag` z.

**SYNTHETIC run** (`/tmp/claude-0/-home-user-Testing/7cf3ca0b-ccdf-5806-aa57-684759b9781e/scratchpad/A6/smt_nested_test.py`, 150 sessions × 390 bars, k = 10, h = 5, β = 0.85, ES residual injected with γ = 0.15 in the signal case, γ = 0 in the null):

```
=== SIGNAL CASE: gamma=0.15, n=10877, sessions=149 ===
  +direction | cluster-Wald p=0.0000 | OOS dR2=+0.0039 | smt_dir=+1.6e-4 (t=+6.65)
  +magnitude | cluster-Wald p=0.0000 | OOS dR2=+0.0092 | smt_mag=+0.144 (t=+7.41)
  +both      | cluster-Wald p=0.0000 | OOS dR2=+0.0095 | smt_dir (t=+1.81), smt_mag=+0.13 (t=+5.55)
=== NULL CASE: gamma=0.0 ===
  +direction | cluster-Wald p=0.7603 | OOS dR2=-0.0002 | smt_dir (t=-0.31)
  +magnitude | cluster-Wald p=0.1730 | OOS dR2=+0.0001 | smt_mag=+0.027 (t=+1.36)
  +both      | cluster-Wald p=0.1718 | OOS dR2=+0.0001 | smt_dir (t=-1.28), smt_mag (t=+1.75)
=== MES/MNQ near-duplicate check (ES vs NQ corr, sign agreement by horizon) ===
  h=  1: corr=0.883 sign-agree=0.846   h=  5: corr=0.887 sign-agree=0.845
  h= 15: corr=0.884 sign-agree=0.853   h= 60: corr=0.891 sign-agree=0.848
=== Stale-data check: ES prints older than 30s on 5.0% of bars -> smt_* set NaN ===
```

The signal case is recovered by magnitude (cluster-Wald p ≈ 0, positive OOS ΔR²); direction adds little once magnitude is present. The null case produces p > 0.1 and OOS ΔR² ≈ 0 — the test does not manufacture an edge. The near-duplicate block shows that with ES idiosyncratic vol at ~45% of NQ's, ES–NQ correlation sits near 0.88 at every horizon from 1 to 60 minutes.

**MES/MNQ near-duplicate rule (HYPOTHESIS + test):** a long MES and a long MNQ held over the same horizon are the same directional view when ρ(ES,NQ at horizon h) ≥ 0.80. Variance of the two-leg book relative to a doubled single leg is (1+ρ)/2 = 0.90 at ρ = 0.80 — ~10% diversification, i.e. almost none. Test: compute ρ and sign-agreement by horizon on the user's RTH bars, out of sample by month; if ρ ≥ 0.80 at the strategy's holding horizon, count the pair as one slot for risk limits and size the combination by beta-weighted notional, not by contract count.

## 4. When following this proposal would make the decision worse

- Any (k, h, β-window) chosen by a grid search (Study 66's warning, USER-SUPPLIED CONTEXT): pre-register three (k, h) pairs and report all three.
- Stale or roll-mismatched legs not excluded: divergence is then an artefact and the test will "find" it in-sample.
- The residual is partly genuine sector news (mega-cap idiosyncratic moves); if that persists rather than mean-reverts, the sign of the coefficient flips across regimes and a single β̂ window hides it. Check coefficient stability by quarter.
- Costs: a residual that forecasts 0.5 NQ ticks over 5 minutes is real and worthless after an MNQ round trip (≈1 tick spread + commissions; public, verify).
- Removing SMT from a slot changes which signals trigger; if several strategies share that condition, their correlated losses may rise.

## 5. Cheapest decisive test, and the result that would retire the idea

On ≥ 250 RTH sessions of 1-minute NQ/ES bars with per-bar last-trade timestamps: run Section 3 for (k, h) ∈ {(5,5), (10,15), (20,30)}, β̂ from prior 20 sessions. **Retire SMT** if, at all three pairs, (i) magnitude's session-blocked OOS ΔR² ≤ 0 and (ii) the top-minus-bottom decile spread of after-cost forward MNQ return has a cluster-robust t < 2. **Retire direction-only rules** if, with magnitude present, the direction term's cluster-Wald p > 0.05 at all pairs. Cost: one afternoon; no new data vendor.

## 6. Missing inputs that materially limit the conclusion

Bars with exchange timestamps and last-trade age per leg; the actual SMT definitions used by KX/PX slots (which legs, lookbacks, HH/LH rule); whether logs record *rejected* signals (needed for losses avoided / winners discarded); MNQ and MES commission schedule; which strategies currently read ES; overnight vs RTH coverage. Without the rejected-signal log, only the regression test is possible, not the filter accounting.

## 7. Filter accounting (the seven quantities in rule 3)

| Quantity | How to compute (SMT as a slot condition) |
|---|---|
| Eligible signals | All slot triggers in the test window, before any SMT condition, with stale-flagged bars counted separately |
| Trades retained | Eligible signals whose `smt_mag` z passes the pre-registered threshold (or whose `smt_dir` agrees, for the legacy rule) |
| Losses avoided | Sum of after-cost losses on rejected signals, from the rejected-signal log (not reconstructable otherwise) |
| Winners discarded | Sum of after-cost gains on rejected signals |
| Net change after costs | (losses avoided − winners discarded) − change in round-trip costs from altered trade count |
| Independent sessions | Number of sessions with ≥1 eligible signal; all SEs clustered at session; report net change per session with 95% CI |
| Portfolio contribution | Change in daily P&L correlation between this slot and the others; MES/MNQ pairs with ρ ≥ 0.80 counted as one position |
