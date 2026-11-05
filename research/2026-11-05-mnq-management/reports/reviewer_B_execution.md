# Reviewer B — MNQ execution trader: executability and materiality of C1–C4

**Every number is SYNTHETIC** (development set 2025-05-01 → 2026-04-30 = exactly one trading year, 240 KX / 92 PX trades; sealed holdout 60 KX (all v2) / 28 PX). Development Δ$ therefore *is* $ per year at the desk's historical frequency. My own checks: `src/reviewerB/run.py` → `src/reviewerB/run_output.txt` (my replay reproduces the director's C1 figures exactly: −$3,399, −0.346R). I did not read Reviewer A or `sealed/`.

## 1. Executability

Contract facts (OBSERVED): KX initial lots {1: 56, 2: 70, 3: 64, 4: 50}, 23 % one-lot, 73 adds; PX {1: 72, 2: 14, 4: 6}, **78 % one-lot**. Mean 1R ≈ $152 both families.

| Candidate | Live order action | Next-bar-open feasibility | Stop touched in the bar it is moved (OBSERVED, dev) | Integer-lot constraint |
|---|---|---|---|---|
| C1 stall → BE | Modify the resting OCO stop leg to `entry_px` (cancel/replace on most platforms; verify the OCO link survives the modify). | Auto: modify lands 0.5–2 s after the open; manual: 5–20 s. Fine for a stop modify. | **13/60** triggers: the placement bar already opens through entry → the modify is *rejected* (sell-stop above market) and a market order is the only option; the engine's "open − 1 tick" is the right model. **34/60**: BE stop hit in its first live bar. Net: in 47/60 cases C1 is an exit one bar after the stall, not a stop. 3 exact-touch exits. 2 single-bar triggers. | None (whole position). |
| C2 BE at min 20 if ≥ +0.3R | Same modify, once, at bar-21 open (10:21–11:39 ET). | Clean: **0** gaps at placement, **0** first-bar hits, 1 exact touch. | — | None. |
| C3 add stop at entry | **Separate OCO for the add** (stop qty 1 at entry + limit qty 1 at the shared target). The spec's "own stop, shared target" is unsafe: if the shared target (qty n+1) fills, the add stop is orphaned (would open a reverse position); if the add stop fills, the shared target is over-quantity by 1. | Placed with the add fill; no decision latency. 0/19 hits in the add bar; 1/19 exact touch. | — | Applies only to trades that could add (initial ≤ 3; the 50 four-lot KX trades never add). 1+1 works. |
| C4 PX far target | Place the limit at the OR boundary at entry. Nothing else. | Trivial. | n/a; 1/58 far-target exits was an exact touch (limit may not fill) — immaterial. | None. |

**Fill conventions.** On Globex a stop is elected by a trade *at or through* the stop price, so "touch" is the correct convention for stops **provided bars are built from MNQ trades** (S5 found the synthetic fills priced off NQ; the real export must be MNQ bars). A limit touched at the bar extreme is *not* guaranteed a fill (queue), so "penetrate" for limits is the conservative one; the journal's limit-on-touch is optimistic. S5's 16 exact-touch events swinging $1,038 (6.8 % of net) is the honest resolution floor of 1-minute replay: a candidate whose edge is below ~$1,000/yr is a convention, not a result. Slippage: 1 tick is fair on a calm bar, 2–4 ticks on a 10:00 breakout stop; the candidates are insensitive (C1 at 3 ticks −$3,471; C2 +$90). The only exposure the data cannot resolve is the exit-now market fill 1–2 s into the bar (±2 ticks ≈ ±$1/contract; ≤ $150/yr over 60 stalls). Fix on real data: `fills.csv` with seconds and the platform's trigger source (last trade vs bid/ask).

## 2. Does it matter after costs

**Materiality threshold:** |Δ| ≥ **$1,000/yr net** (≈ 6.5 % of the $15.3k baseline, ≈ 0.04R per KX trade, ≈ the $1,038 that 16 exact-touch events swing, ≈ two MANUAL exits — trade 273 alone is −$446), **and** for a drawdown-first candidate a max-drawdown or worst-session improvement ≥ **2R (≈ $300)** at a P&L cost ≤ $1,000/yr. Below that the number is inside fill-convention and discretion noise at 1–4 lots.

| Candidate (dev, OBSERVED) | Triggers / changed per yr | Paired Δ$ / yr (Stage A) | Stage B Δ$ | Added commission | Added slippage | Max DD (KX $1,994; PX $528) | Worst trade / tail | Material? |
|---|---|---|---|---|---|---|---|---|
| C1 | 60 / 53 | **−3,399** [−7,892, +783]; penetrate −3,744; 3 ticks −3,471 | −3,843 | $0 | ~22 target→stop conversions ≈ $25 | **worse: −$3,179** | worst trade −392 → −224; P(R<−0.5) on stalls 0.52 → 0.18 | Yes — materially harmful |
| C2 | 61 / 18 | +107 to +121 [−2,633, +2,504] | +56 | $0 | ≈ $6 | −$1,823 (−1.1R) | worst −392 → −341; P(R<−0.5) on conditioned 63: 0.24 → 0.06 (≈ 11 trades/yr) | P&L no; DD below 2R; tail halved as pre-registered |
| C3 | 73 adds / 19 | −320 [−1,407, +618]; penetrate −320 | −450 | $0 | $0 | −$1,936 (−0.4R) | worst session −392 → −272 (+0.8R) | No, either way |
| C4 | 92 / 64 | **+5,514** [+3,547, +7,157]; +0.40R/entry; penetrate-limit +5,514 | +5,251 | $0 | ≈ $5 | −$457 (−0.5R) | worst session unchanged; holds 28 → 50 min | Yes — but it is the generator's drift (D2 no-target +0.88R > C4 +0.40R) |

No candidate adds a single contract-side of commission; slippage differences are tens of dollars a year. The $ question is decided by the mechanism, not by costs.

## 3. The +0.8R → +0.3R stall

**Breakout (KX): hold the original bracket.** Dev Δ_BE −0.35R [−0.80, +0.11] on 60/60; exit-now −0.53R [−1.05, −0.02]; every time exit ≤ 30 min loses (S2, S6). Execution adds a point the statistics miss: because the stop is placed at the next open and the market is already at or through entry in 47/60 cases, "tighten" and "exit" are the *same action one bar apart* — the data cannot and need not separate them. The tail reduction (P(R<−0.5) 0.52 → 0.18) is bought at −0.35R per stall and a *larger* portfolio drawdown (−$1,994 → −$3,179), because stalls that would have reached 2–2.5R are scratched. The sub-cell caveat: v1 −0.57 [−1.08, −0.04] vs v2 +0.14 [−0.76, +0.91], holdout (all v2) +0.45 [−0.44, +1.12], n = 13. A time rule is dominated (S2 grid, T15–20 at X = 0.3–0.5R is the worst region).

**Reversal (PX): the state does not occur** under P0 (0/92; target median 0.70R) and appears only if the target is extended (10/92 under C4). Hold to the structural target; no stall rule.

**What would change my answer on real data:** (a) ≥ 40 KX stalls / 40 sessions with Δ_BE lower CI > 0 — and the v2 sign holding, since the desk now runs v2 only; (b) the "minute 10, all open" cell showing Δ_exit ≈ −0.05R (no post-entry drift): then holding has no support and the tail argument wins; (c) real stop slippage ≥ 3 ticks on the original −1R stops, which raises the value of scratching early.

## 4. Pyramiding

Keep the add: leg 2 earns +$3,581/yr on 73 adds, CI [1,831, 5,206], +0.29R of its own risk; all 24 top-decile KX trades carry an add. Its cost is where the add sits when a stall turns: 37 % of stalls carry an add ~0.7 stop-distances under water, so stall losses land at −2R/−3R. C3 buys worst-session +$120 (0.8R) and max DD −$58 for −$320/yr; dev P(target | retrace to entry after add) = 8/19 = 0.42 vs the 0.35 break-even, holdout 1/5. Below my 2R drawdown threshold and inside P&L noise; as an order structure it is cheap and safe only as a separate OCO (§1).

## 5. Position limits and overlaps

C1, C2 and C3 can only exit *earlier* than P0, so they free contracts: director's Stage B executes 342 / 330 / 331 vs 327 under P0 (C1 frees 12 signals, blocks 2; C2, C3 free 3). Handled correctly; the freed trades move C1 from −$3,400 to −$3,843. C4 and D1 lengthen holds. My check: **0 later same-session signals arrive inside the C4 extension in dev, 0 blocked** (23 holds exceed 60 min); director's Stage B shows C4 blocking the same 5 signals as P0 (dev) and 0 (holdout). D1 blocks 9 PX signals (S6) but is a probe. **Unknown:** the synthetic desk fires ~1.4 trades/session with KX confined to 10:00–11:30; a real desk with several PX signals per afternoon, or strategies outside the export, would change this; the 5 "exit frees contracts in the same bar" look-ahead cases; Stage B re-prices entries so MANUAL exits differ.

## 6. Forward-simulation spec critique

| As written | Cannot be executed/logged because | Fix |
|---|---|---|
| Net uses "slippage actually observed on live fills" | A paper stop never fills; there is no observed slippage for it | Log the exit bar OHLC and the first at-or-through trade time (seconds); apply the desk's empirical slip distribution by order type from live STOP/MKT fills; columns `assumed_slip_ticks`, `empirical_slip_p50/p90` |
| C1 live equivalent "modify the resting stop" | 13/60 placements are already through the market → modify rejected | Rule: if the open is through the level, send market; log `order_action ∈ {MODIFY, CANCEL_REPLACE, MKT}`, `modify_rejected_flag`, and whether the OCO link survived |
| C3 "own stop, target remains the shared target" | Orphan stop / over-quantity target (§1) | Separate OCO for the add |
| Promotion A/B: "half the contracts under the candidate, half under P0, alternating by session parity" | Contradictory, and impossible for 1-lots (23 % KX, 78 % PX) | Whole trades by session parity; assignment logged before entry |
| C1 trigger "MFE has occurred (any earlier bar)" | Director's engine counts the current bar (2/60 single-bar triggers) | State "MFE through and including bar k" |
| `manual_intervention_flag` with no rule | Paired delta vs *live* net measures the trader | Paired delta vs the mechanical P0 replay; live net logged separately |
| Same-bar ordering for shadow exits unstated | C4 far target and stop can share a wide bar | Log `both_touched_flag`, report both orderings |
| "6–9 months" | C4 needs 90 PX ≈ 234 sessions ≈ 11 months; continuation audit 100 target exits ≈ 8 months | Per-candidate months in the table |
| Decision-event row | No `leg_id, qty, order_action, exact_touch_flag, action_sent_ts, action_ack_ts` | Add them; latency then enters the paired delta |
| Unit for C2/C3 | Holdout C2 "n = 13" changed **1** trade | Minimum on *changed* trades (≥ 15), not conditioned trades |
| Header | Trigger source and bar-timestamp convention unknown | One-time `stop_trigger_source` (last/bid-ask), `bar_ts_labels` (open/close) |

## 7. Verdicts

**C1 — RETIRE.** Materially harmful in development (−$3.4k/yr, Stage B −$3.8k, drawdown worse), fails the pre-registered advance criterion on the holdout (+0.45R, CI [−0.44, +1.12], n = 13), and operationally it is an exit with a one-bar delay in 47/60 cases, so it cannot be the "tighten" the user asked about. Would change: ≥ 40 real v2 stalls with Δ_BE lower CI > 0, or a real stall cell with P0 mean R ≤ 0.

**C2 — ADVANCE to forward simulation.** The one candidate that executes exactly as modelled (one stop modify, 0 rejections, 0 first-bar hits, insensitive to every fill convention), costs nothing in P&L (+$107/yr, CI spanning ±$2.5k) and halves the pre-registered tail metric (0.24 → 0.06 on 63 conditioned trades). Holdout changed one trade, so it is unproven, but shadowing it is free. Would change: tail not halved on ≥ 15 changed real trades, or P&L cost < −0.10R.

**C3 — REVISE and retest.** Effect inside noise both ways (−$320 / +$154), drawdown bought < 2R, dev retrace count 0.42 above the 0.35 retire line. Re-specify as the logged count P(target | retrace to entry after add) with the separate-OCO order structure, no P&L objective; decide at 40 add trades / 15 retraces.

**C4 — ADVANCE to forward simulation, conditional on the continuation audit.** The only material $ (+$5.5k/yr, +0.40R, Stage B +$5.3k), trivially executable, no position-limit blocking. The holdout CI includes 0 (+0.20R [−0.11, +0.47], n = 28 of the 90 required), and the benefit is the generator's drift; only `cont_R` on real PX target exits settles it. Would change: `cont_R` centred ≤ 0, or far-target exact-touch rate > 10 % live.

**P0 — ADVANCE (as the live control, unchanged).** Nothing beats it with a resolvable margin on data that was built in its own schema.

## 8. Expected disagreements with the methods reviewer

1. **C4 after a holdout CI that includes 0.** They will say the pre-registered retire rule fired; I say a rule without a minimum n fired on 28 trades, and the shadow costs nothing. Resolve: amend the rule to require the pre-registered sample (90) before it can retire.
2. **A $1,000/yr floor vs significance.** They may accept a $400 effect with a CI excluding 0; I will not, because 16 exact touches move $1,038. Resolve: pre-register both the CI and the effect-size floor.
3. **C2 advanced on a tail metric with P&L inside noise and 192 S1 cells behind it.** Resolve: C2 was pre-registered with the tail as primary; the shadow decides at 60 conditioned / 15 changed trades.
4. **Touch vs penetration as a "sensitivity".** For me touch is the stop convention and penetration the limit convention, not two equal options. Resolve: second-level fill times in the real export collapse the question per trade.
5. **A v2-only C1 after the holdout sign flip.** Post hoc; but the stall log in shadow is free, so decide at 40 v2 stalls rather than argue now.

---

## Addendum — reference-engine holdout run (`src/director/out/reference_run_holdout.md`, SYNTHETIC)

Received after the review above was drafted. Holdout 60 KX (all v2) / 28 PX, reference fill model.

| Candidate | Holdout Stage A | Holdout Stage B Δ$ | Fill grid (touch/penetrate, slip 0/1/2, ordering) | Verdict |
|---|---|---|---|---|
| C1 | +$866, +0.454R [−0.44, +1.12], n = 13 stalls, 10 changed; 89 % of benefit in top 3 sessions | +1,196 (frees 1) | identical in every cell; 0 ambiguous bars | **unchanged: RETIRE** — fails its own advance criterion; dev harm is material; the positive sign matches the dev v2 subset and is the observation to log, not to act on |
| C2 | +$274, +0.115R [0.00, +0.35], **1 trade changed** | +435 | identical | **unchanged: ADVANCE** — one trade is no evidence either way; executability is the reason to shadow it |
| C3 | +$154 [−418, +622], 5 changed (4 losses avoided, 1 winner cut); worst session −379 → −287, max DD unchanged | +154 | identical | **unchanged: REVISE** — below both thresholds again |
| C4 | +$812, +0.197R [−0.11, +0.47], 16 changed; D2 no-target +0.59R > C4 again | +813, 0 blocked | identical (1 exact touch at most) | **unchanged: ADVANCE conditional on `cont_R`**; the pre-registered retire clause fired on 28 of 90 trades — see §8.1 |
| P0 | $4,949 (journal $5,462; 1 MANUAL exit) | — | — | **unchanged** |

The fill grid confirms §1: on 88 holdout trades no candidate's result depends on touch vs penetration, slippage 0–2 ticks or same-bar ordering, and no bar ever held both a live stop and a live target. The remaining execution risks are therefore the ones the bars cannot show — the rejected modify when the open is through the breakeven level (dev 13/60 for C1, 0 for C2) and the C3 order structure — not fill conventions. D1 replicates (+$19,137, +2.46R/entry) exactly as the pre-registration predicted a generator artefact would; it is not a candidate.
