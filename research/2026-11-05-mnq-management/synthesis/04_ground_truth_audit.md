# Ground-truth audit — what was planted, what the panel found, where the generator misled

Opened after all six specialist reports and both reviews were committed. Planted structure: `sealed/ground_truth.md`; labels per trade: `sealed/ground_truth_trades.csv`. All numbers SYNTHETIC.

## What was planted and what the methods recovered

| Planted | Recovered? | Evidence |
|---|---|---|
| KX: a latent `genuine` label (40%) with strong drift for 60 min; non-genuine trades fade for 40 min | **Yes, as a conditional structure.** P(target \| genuine) 0.79 vs 0.15 non-genuine. S2's minute-15 progress table ranks P(target) 0.08 → 1.00 across progress buckets; S1's Table A shows the same ordering. | per-trade merge with ground truth; S2 §2; S1 §2.2 |
| KX: early no-progress exit "should improve net results" (the director's expectation in the sealed note) | **No, and the methods were right.** The asymmetric 2–2.5R bracket makes a stop cheap relative to the target: trades at −0.5…0R at minute 15 still reach the target 42% of the time. The no-progress rule fired on 43 trades, 28% genuine; it gained +0.29R on non-genuine and lost −2.33R on genuine fires. Net −0.08R per entry. | S2 §1–2; audit tally |
| KX `slow` subgroup (18% of genuine, drift delayed 12 min) as costly false alarms | **Yes.** The worked false alarm (trade 306) and the sessions dominating the cost of every tightening rule are these trades. 10% of the stall set is `slow`. | S2 worked example; `03_profit_vs_protection.md` |
| PX: "slow reversal = bad reversal" is FALSE (speed independent of `genuine`) | **Yes.** S3: P(target \| touched +0.3R) 0.90–1.00 regardless of time to touch; forward value of holding slow trades +0.04R [−0.17, +0.26]; genuine-slow +0.55R vs genuine-fast +0.60R in the ground truth. | S3 §2; audit tally |
| PX: a rule developed on breakouts harms reversals | **Yes.** All 13 no-progress variants ≤ 0 on PX; the mandated rule −0.08R per entry. | S3 §2 |
| Pyramiding: adds land disproportionately on genuine trades; protecting the add cuts winners | **Yes.** 62/73 adds reached the target (85% vs a 2/3 martingale baseline); add-only breakeven fired on 14 trades of which 13 then reached the target. | S4 §1–2 |
| Version change v1 → v2 (target 2.0R → 2.5R) with nothing else different | **Detected and used.** S2 and S1 split by version; Reviewer A noted the holdout is 100% v2 and that the pooled development prediction for C1 was v1-dominated. | S1 §2.2; Reviewer A §3 |
| MANUAL exits (10 dev, 1 holdout) with no logged rationale | **Isolated exactly.** S5 reconciliation: 282/332 exact under the reference model, 316/332 under the generator's own conventions; the only unexplained class is the 10 MANUAL trades (+$160.50 net, Σ\|diff\| $1,282.50). | S5 §1, §3 |
| Fills priced off the signal instrument (NQ) with 1-tick slippage; bracket not armed in the entry bar | **Found.** S5: every market fill = NQ open + 1 tick; 27 trades explained by that convention; 2 by the entry-bar convention. | S5 §2 |
| Stop and target never in the same bar for the baseline | **Found.** 0/332; S5 constructed a 0.1R trail to force one case and showed the ordering parameter. | S5 §3 |

## Where the generator misled, and who caught it

The generator's planted drift (0.27σ per minute for 60 minutes after a genuine breakout; 0.14–0.30σ for 40–90 minutes after a genuine reversal) is far stronger and longer than any intraday edge a desk could expect, and it continues well past the bracket's target. Consequences:

1. Every "hold longer" policy wins hugely (no-target KX +1.76R per entry; no-target PX +0.88R). **S3, S5 and S6 each independently identified this as a generator artefact** and quarantined it; the pre-registration demoted it to a diagnostic (D1/D2), and the holdout replicated it exactly as predicted. The methods did not mistake it for an edge.
2. The planted "early progress is informative" structure is real but, under the asymmetric bracket, does not make an early exit profitable. The sealed note's expectation that it "should improve KX net results" was the director's error, not the methods'. Nobody tuned toward it.
3. The stall set (60 trades) is 37% genuine; breakeven at the stall gains +0.30R on non-genuine stalls and loses −1.45R on genuine ones. Whether that nets positive on real data depends entirely on the real mix and the real post-stall drift, which is why Reviewer A's "minute-10 drift gauge" is the first number to compute on the export.

## Holdout as a test of the pre-registration

| Prediction (frozen) | Holdout outcome | Verdict on the prediction |
|---|---|---|
| C1 Δ ≤ 0 (dev −0.31R) | +0.45R [−0.44, +1.12], n = 13, all v2 | Undecidable; the v2 development sub-cell (+0.14R) was already the better predictor |
| C2 cost ≥ −0.10R and tail halved | +0.12R, one trade changed | Undecidable; no power |
| C3 drawdown ≥ 0.5R better, cost not below −0.05R | +$154, max DD unchanged | Drawdown objective fails as in development |
| C4 Δ > 0 with CI excluding 0 | +0.20R [−0.11, +0.47], n = 28 | Retire rule fires as written (Reviewer A); Reviewer B objects that n = 28 of the 90 pre-registered |
| D1 replicates (generator drift) | +$19,137 [4,741, 36,206] | Replicated, as predicted |

## Count of everything examined

Policy and threshold cells (including discarded): S1 192 conditional evaluations, S2 46, S3 29 + 1 sensitivity, S4 6 policies × 4 sensitivities, S5 16 + 10 fill variants, S6 92 + 12 fill variants + 1 lock variant, director 10 policies × 6 fill variants × 2 data sets. **≈ 381 distinct policy or threshold cells in development** (Reviewer A's tally), 4 pre-registered, 4 diagnostics, evaluated once on the holdout.

Independent runs: 6 specialists, 2 reviewers, 1 director replay (three separate engines reproduce the C1 stall figure to within 0.05R and the no-target probe to within $300: S1, S6, S5-reference, director, Reviewer B).
