# Reviewer A — quantitative methods review (timestamps, fairness, uncertainty, selection)

**Every number in this review is SYNTHETIC** (development set `data/synthetic/`, 332 trades / 242 sessions; sealed holdout 88 trades / 60 sessions, seen only through the director's cross-checks and the reference run). Nothing here is market evidence. Spot checks: `src/reviewerA/checks.py`. I did not open `sealed/` or any Reviewer B file.

**Label note.** S1 §8 calls the *late* breakeven "C1" and the *stall* breakeven "C2"; `prereg/challengers.md` swaps them (C1 = stall → BE, C2 = late BE at 20 min). I use the pre-registration labels.

## 1. Timestamp integrity

**Pass, one documentation hazard.** OBSERVED (my check): all 332 `entry_ts` and `exit_ts` sit on MNQ bar opens; `fills.ts_utc` converted to `America/New_York` equals `entry_ts` 332/332 and the last EXIT fill equals `exit_ts` 332/332; both −04:00 and −05:00 offsets occur (DST crossed) and every replay parses with `utc=True` + `tz_convert` (S1 `run.py` l.77–81; director `reproduce.py` l.28). S5 §2 ("UTC/ET alignment") reaches the same 332/332.

Decision placement is closed-bar everywhere: S1 §0 ("decision time = open of bar k"), S2 §2 ("close of bar 14 … exit at the open of bar 15"), S3 §3 ("bars closing ≤ entry + k min … fills at the open of minute k"), S4 §3 ("bar-close decisions act from the next bar"), S5 §4 item 5, S6 §8, director `reproduce.py` l.85–90. In clock time all agree (decide at entry + T min, fill at that minute's open). The hazard is bar *indexing*: S2 counts the entry bar as bar 0 (its "bar 14" closes at entry + 15), S1 and the pre-registration count it as bar 1 (C2: "close of bar 20 … open of bar 21"). The port to the real export should specify clock time only.

Entry-bar convention: S1, S2, S4, S6 and the director leave the bracket un-armed in the entry bar (journal convention); S5's reference model arms it (2 trades, $26.50). The reference run's `no_bracket_entry_bar` row changes no candidate. The nine exits lagging the first touch by 1–4 min (S2 §2, S4 §3) are S5's exact-touch/NQ-trigger conventions, not timestamp errors.

## 2. Comparison fairness

**Pairing and costs.** All six replays pair on identical `trade_id`, entry fill and size; $0.74/side on every leg in every arm; same slippage in both arms. One systematic tilt, not an arm asymmetry: limits fill at touch with 0 slippage, so every target-keeping policy (P0, C1–C3) gains ≈ 1 tick per exit over market-exit comparators (D3, D4, time exits). S5 §8 bounds it (≤ $235 on $15.3k).

**MANUAL exits (10 dev, 1 holdout).**

| report | original arm | consequence |
|---|---|---|
| S1 | journal P&L (`net = net_pnl_usd`, `run.py` l.109); BE arm may hold past a MANUAL exit (`be_longer`) | 3 of 60 stall trades MANUAL; asymmetric by design |
| S2, S3, S4 (primary), S5, S6, director, reference run | bracket run mechanically through the MANUAL exit, both arms | cancels in paired Δ |

S5 §3: journal − mechanical = +$160.50 over the 10 trades, so S1's choice flatters the original arm slightly (stall Δ_BE −0.31 vs director's mechanical −0.346). On the holdout the one MANUAL exit is worth $581 (11 % of KX net): if the real desk intervenes often, no mechanical replay measures the policy actually run. Reason codes per MANUAL exit (S5 §6) are mandatory.

**Survivor selection.** S1 conditions on "still open under the ORIGINAL policy". C1/C2/C3/D3 coincide with P0 before their trigger, so trigger sets are identical under both arms — no bias. The bias is real for policies that hold *longer* (C4, D1, D2); S1 flagged it (§2.5) and no report misused Table A for them.

**"Largest winners."** Baseline-fixed in S2 (top 24, ≥ 2.97R), S3 (10 trades), S4 (all-KX 24; add-subset 7). Two non-baseline definitions are diagnostics only: S1's per-policy worst decile and S6's "top 10 % of changed trades" ranked by benefit.

## 3. Uncertainty

**Unit.** All reports resample whole sessions (2,000 draws). OBSERVED: no session has two KX trades (0/242) nor two PX trades, so for one-family statistics the session bootstrap *is* a trade bootstrap; it matters only for mixed sets (90 sessions hold one of each). S1's implementation (multinomial weights over 242 sessions, cell mean as ratio of weighted sums, l.207–223) is correct for conditional cells. None addresses between-session dependence (volatility regimes); on real data use a weekly block bootstrap.

**CIs at decisions.** Present for every paired Δ; absent for the tail metrics that judge C2 and C3 (P(R < −0.5R), worst decile, max DD, worst session). C2's tail clause is structural: a stop at entry caps a one-leg trade at ≈ −0.03R unless gapped, so "tail halved" is near-automatic and the decision rides on the P&L clause.

**Holdout stall cell, n = 13.** Implied paired SD from the CIs ≈ 1.5–1.8R. Minimum detectable paired effect (80 % power, 5 % two-sided):

| stall trades | MDE (SD 1.5R) | MDE (SD 1.8R) |
|---|---|---|
| 13 (holdout) | 1.17R | 1.40R |
| 40 (S1's threshold) | 0.66R | 0.80R |
| 100 | 0.42R | 0.50R |
| 280 | 0.25R | 0.30R |

The cell can reject |Δ| > ~1.3R and nothing else: it cannot separate the development prediction (−0.35R) from its own estimate (+0.45R) or from zero; the sign flip is what this SD predicts. The cell's P0 baseline itself moved 0.55R (dev +0.44, holdout −0.11), more than the effect under test. At a 22–25 % stall rate the real export needs ≈ 100 stall trades ≈ 400 KX trades (≈ 1.7 years at 240/yr) for 0.5R and ≈ 4.7 years for 0.3R. S1 §5's "retire if upper CI < +0.2R on ≥ 40 stall trades" needs a point estimate below −0.36R to fire; a null at n = 40 is uninformative.

**Heterogeneity.** Dev Δ_C1: v1 −0.57 [−1.09, −0.07] (n 41), v2 +0.14 [−0.69, +0.91] (n 19); the holdout is 100 % v2, so the pooled, v1-dominated prediction was never a prediction for the holdout population. Pooled v2 (≈ +0.27R, CI ≈ [−0.3, +0.9]) is still uninformative.

## 4. Selection bias

| report | distinct policy/threshold cells | with sensitivity reruns |
|---|---|---|
| S1 | 192 (100 cells × 2 actions) | 192 |
| S2 | 46 | 48 |
| S3 | 29 | 30 |
| S4 | 6 | 24 |
| S5 | 16 (engine demonstration) | 26 |
| S6 | 92 | 105 |
| **total** | **381** | **≈ 425** |

Four challengers and four diagnostics from ≈ 381 cells (≈ 1 : 95), frozen before the holdout (no `prereg/CHANGELOG.md` exists, so no post-freeze edits are recorded).

- **C1**: the brief's own question, pre-registered with a *negative* prediction. Not post hoc.
- **C2**: picked from S1 Table B's 10 "all open / ≥ +0.3R" cells; k = 20 was not the best (min 15: +0.11R), limiting winner's curse, but the family is post hoc; dev lower CI (−0.25R) sits just inside its −0.30R cutoff.
- **C3**: one of six pre-specified policies; mild selection. But objective (1) (max DD cut ≥ 0.5R) already failed on development (−$1,994 → −$1,936 ≈ 0.3R), and its retire threshold (0.35) equals the martingale value, judged on 19 events (SE ≈ 0.11).
- **C4**: the middle of a monotone target gradient (3/4-line +0.21R, far +0.40R, none +0.88R) — a point on a drift curve, post hoc in effect though parameter-free.
- **S2-C1 "late failure exit"**: correctly excluded — best of 46, +$654 [−2,106, +3,137], mechanism contradicting the family's own finding.
- **No-target (D1/D2)**: correctly quarantined — +1.76R/entry, 5× baseline, 136 EOD exits averaging +6.1R (S5 §1). Reported as a gauge, not acted on.

## 5. The generator problem

All six find one mechanism: hold-minus-exit ≈ −0.4 to −1.0R in every KX state (S1 Table A), post-target continuation +2.56R (S6), add-leg target rate 85 % vs martingale 2/3 (S4). The verdict "hold the bracket" rests entirely on it.

- **Drift real live:** the logic holds; any tightening forfeits expectancy; but the panel will have quarantined the best policy (D1), and the next step is S6's continuation audit, not a management rule.
- **Drift absent:** every KX "hold" advantage collapses to ≈ −costs. Under a martingale a breakeven stop from +0.3R has zero expected cost, so C1 and C2 become near-free tail insurance and the verdict flips to "adopt". The panel's logic does **not** survive this case.

**Separating observation (compute first on the real export):** among KX trades still open at minute 10 under P0 (≈ 65 % of KX trades, ≈ 150/yr), the paired mean of (exit at the minute-10 open − P0 outcome) in R. Dev −0.61R [−0.84, −0.37], n = 158, SD ≈ 1.5R. **≤ −0.25R with CI excluding 0 ⇒ drift present; within ±0.10R ⇒ absent.** One year (SE ≈ 0.12R) separates −0.6 from 0; −0.25 from 0 needs ≈ 2 years. The unconditional P0 KX mean net R (driftless value ≈ −0.03R; dev +0.36 [0.12, 0.58]) reads the same thing.

## 6. Verdicts

| candidate | verdict | justification | observation that changes it |
|---|---|---|---|
| **C1** KX stall → BE | **REVISE and retest** | The pre-registered rule covers "Δ > 0, CI excl. 0 → advance" and "Δ ≤ 0 → retire"; the holdout (+0.45 [−0.53, +1.13], n = 13) is in neither. Development evidence against C1 is v1-only and a function of synthetic drift. Unanswered, not answered "hold". Revision: pre-specify by target multiple; gate on the minute-10 drift gauge; require ≥ 100 stall trades. | Real stall cell: Δ_BE lower CI > 0 → advance; upper CI < +0.2R at n ≥ 100 → retire. |
| **C2** KX late BE at 20 min | **REVISE and retest** | Dev +0.04R [−0.25, +0.29]: P&L-neutral within power; tail reduction structural. Post hoc from a 10-cell grid. Revision: define the tail metric on the whole position (a BE stop at entry is −1 stop-distance for an add leg), give it a CI, fix k = 20 with no neighbourhood. | Δ lower CI < −0.30R → retire; lower CI > −0.10R with tail reduction replicated → advance. |
| **C3** add-leg stop at entry | **RETIRE** | Fails objective (1) on development; decisive proportion judged on ~19 events against the martingale value; ±0.02R/trade is below any attainable MDE (0.42 vs 0.35 needs ≈ 600 retrace events). A risk-policy choice, not an empirical one. | Real add trades with P(target \| retrace to entry) < 0.20 on ≥ 60 events, or an add-leg loss ≥ 2R in the real worst session. |
| **C4** PX far target | **RETIRE** (as pre-registered; see addendum — on development alone it was REVISE) | Dev +0.40R [0.27, 0.52] but D2 ≥ C4 on the same trades, so the gain is drift, not the level; the pre-registration already says a replication is not evidence. | On the real export, C4 > 0 with CI excl. 0 **and** C4 ≥ D2 (D2 − C4 as the primary statistic). |
| **P0** keep original | **ADVANCE** | The control arm every forward simulation needs; replay validated 282/332 (reference) and 316/332 (generator model). | A real MANUAL rate well above 3 %: then the control must be the desk's actual behaviour, not the documented bracket. |

## 7. Expected disagreements with the execution-trader reviewer

| B's likely position | resolution |
|---|---|
| Breakeven stops at entry get run intra-bar; 1-min bars understate it (S5: 16 exact-touch events, 6 : 10) | S5 §8's touch/penetrate grid is mandatory for C1/C2; seconds-level fill times in the export collapse the two conventions |
| C2 is ±$15/trade noise; retire outright | Pre-specify a minimum effect of interest (0.10R/trade ≈ $2,400/yr at 240 KX trades) and power to it, instead of arguing from priors |
| C4 should advance: parameter-free, large, Stage B-positive | D2 ≥ C4 is the test; without it the number is the generator's |
| Discretion is part of the policy (journal beat the bracket by $160 on 10 MANUAL trades) | Reason codes in the export; both treatments reported; paired Δ on the mechanical arm |
| Longer holds (C4: 28 → 50 min) block afternoon PX signals | Already in C4's Stage B objective; report blocked/freed counts per candidate |

---

## Addendum — reference-engine holdout run (`src/director/out/reference_run_holdout.md`, SYNTHETIC)

Received after the main review. Holdout: 60 KX (all v2), 28 PX, 60 sessions. P0 KX mean R +0.72 (dev +0.36); PX +0.03 (dev +0.19); D1 +2.46R/entry [0.59, 4.74] — the drift replicates, stronger than in development, as predicted.

| candidate | holdout paired Δ | n (changed) | pre-registered rule | status |
|---|---|---|---|---|
| C1 stall → BE | +0.454R [−0.44, +1.12]; Stage B +$1,196 | 13 (10) | advance if Δ > 0, CI excl. 0; retire if Δ ≤ 0 | neither; MDE ≈ 1.2R; 89 % of benefit in 3 sessions |
| C2 late BE20 | +0.115R [0.00, +0.35]; tail 0.08 → 0.08 | 13 (**1**) | retire if cost > −0.10R or tail not halved | zero information: one changed trade, one tail event |
| C3 add stop | +$154 [−418, +622]; max DD −1,277 → −1,277 | 23 (5) | retire if (1) fails | objective (1) fails again |
| C4 PX far target | +0.197R [−0.11, +0.47]; D2 +0.59 [−0.01, +1.24]; Stage B +$813 | 28 (16) | retire if 95 % CI includes 0 | **rule fires** |

Fill grid: every candidate identical under touch/penetrate, slippage 0/1/2, both orderings and entry-bar arming (0 ambiguous bars) — none is a fill artefact at this grain, which settles disagreement 1 for the holdout.

**Changed verdict — C4: RETIRE, as pre-registered.** The holdout had ≈ 78 % power for the development effect (0.40R; implied SD 0.78R, n = 28) and returned half of it with a CI through zero; D2 ≥ C4 on both sets, so the level adds nothing beyond drift. A rule frozen before the holdout is applied as written. It may be re-proposed on the real export under a new pre-registration with D2 − C4 as the primary statistic.

**Unchanged.** C1 stays REVISE and retest: the holdout lands in the pre-registration's gap and at n = 13 could not have decided; the sign flip is within one SE of each estimate. C2 stays REVISE and retest: the letter of its rule says "retire", but a test that changes one trade has no power against either clause; applying it would be a formality, not a test. C3 stays RETIRE (objective (1) failed on both sets). P0 stays ADVANCE. Note Stage B on development: C1 *frees* 12 signals (earlier BE exits release contracts) yet nets −$3,843 — a breakeven rule's portfolio effect is not its paired Δ, so the forward-simulation spec should carry Stage B for whichever stall rule survives the real export.
