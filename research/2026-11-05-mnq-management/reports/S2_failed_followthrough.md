# S2 — Breakout / failed-follow-through: "little progress by minute T ⇒ exit" for KX entries

**All numbers are SYNTHETIC** (`data/synthetic/`, 2025-05-01 → 2026-04-30; 240 KX trades in 240 sessions; 242 sessions in total): they describe the method, not the market. Labels: OBSERVED = computed on the synthetic data; HYPOTHESIS = interpretation; SYNTHETIC EXAMPLE = case drawn from the synthetic journal. Code: `src/S2/run.py`. Charts: `charts/S2_grid_delta_usd.png`, `charts/S2_worked_examples.png`, `charts/S2_cumulative_delta.png`.

**Pre-registered nomination, fixed in code before any grid cell was computed:** `FAIL_mtm_T15_X+0.0` — *at entry + 15 min (close of bar 14), if the initial leg's close-to-close open profit is < 0 R, exit at the open of bar 15, market, 1 tick adverse.* Comparator: unconditional exit at the open of bar 15 (`TIME_T15`).

## 1. Strongest finding and the decision it changes

OBSERVED. The nominated failure rule **does not improve** KX results. Paired against the original bracket on all 240 entries: **−$2,871 (95 % session-bootstrap CI −$6,134 … +$157; −0.079 R/entry, CI −0.169 … +0.004)**, costs included. 43 fires (43 sessions): $2,643 of losses avoided against $5,514 of winners surrendered. The unconditional time exit at the same horizon is far worse (−$12,015, CI −$17,469 … −$6,439). No cell of the 46-cell grid is positive with a CI excluding zero.

Decision changed: for KX, **no early failure exit, no 15-min breakeven stop, no time stop at any horizon ≤ 30 min**. The cells that would exit the brief's +0.8 R → +0.3 R stall (X = +0.3/+0.5 R, T = 15–20) are the grid's worst (−$2,145 … −$6,063). Hold the bracket.

## 2. Evidence (labelled) and the strongest competing explanation

**Replay conventions (ASSUMPTIONS, identical in every arm).** Entries fixed at journal `entry_px`/`initial_contracts`. Stops fill at stop − 1 tick adverse (bar open if gapped through); targets at the limit, 0 slippage; every market exit (rule, time, 15:55 flat) at the next bar open − 1 tick adverse; $0.74/contract/side on every fill. Like the journal (trades 174, 332), stop/target are not evaluated inside the entry bar. A decision at minute *T* uses only bars closing ≤ entry + *T* min. **Adds:** the journal add is taken in every arm whenever the trade is still open at `add_ts`; a rule exit at the same open cancels it. In all 43 fired trades any add was already on and is closed by the rule (adds not taken 0, incremental commission $0). Progress is measured on the **initial leg only**. No alternative holds longer than the original (no overlap flags).

**Reconciliation vs `trades.csv` (OBSERVED):** 231/240 KX trades net-identical (replay $12,589.22 vs journal $12,685.72). Differences: 6 journal `MANUAL` exits at prices not on the exit bar (my baseline holds the bracket), 3 gap fills where the journal adds a tick. Nine journal `exit_ts` lag the first bar touching the identical exit price by 1–4 min (for S5/Reviewer A). Same-bar stop + target never occurs in KX; ordering is moot (0 trades, also for the breakeven variant).

**Table 1 — Paired difference vs original, 240 KX entries / 240 sessions, costs included (OBSERVED, SYNTHETIC).** Baseline +$12,589, +0.355 R/entry. 2,000 bootstrap draws over 242 sessions.

| Policy | fired (trades = sessions) | Δ net $ | 95 % CI $ | Δ mean R/entry | CI R | top-10 % winners cut | $ surrendered on them |
|---|---|---|---|---|---|---|---|
| **FAIL mtm T15 X0 (nominated)** | 43 | **−2,871** | −6,134 … +157 | −0.079 | −0.169 … +0.004 | 1 of 24 | 635 |
| TIME T15 (comparator) | 127 | −12,015 | −17,469 … −6,439 | −0.328 | −0.477 … −0.171 | 19 of 24 | 5,254 |
| BE variant T15 X0 (exit if < 0, else stop → entry) | 43 (+84 BE stops) | −3,221 | −7,621 … +1,157 | −0.081 | −0.200 … +0.036 | 1 of 24 | 635 |
| FAIL mtm T30 X+0.3 (best non-degenerate cell, post hoc) | 24 | +654 | −2,106 … +3,137 | +0.027 | −0.048 … +0.094 | 2 of 24 | 1,304 |

Full grid: `src/S2/out/grid_summary.csv`, `charts/S2_grid_delta_usd.png`. OBSERVED: harm shrinks monotonically with T (mtm, X = 0: −$5,659, −$2,373, −$2,871, −$1,291, −$1,302 for T = 5 … 30) and grows with X at T ≤ 20. MFE rules with X = 0 never fire at T ≥ 15.

**Profit-vs-protection, nominated rule, 43 fired trades (OBSERVED):** losses avoided +$2,642.50 (29 trades, all original STOP; −$4,924 → −$2,281); losses worsened $0; winners surrendered −$5,513.50 (14, all original TARGET); incremental commissions $0; net −$2,871. Exits shortly before a *large* winner (top 10 % by baseline net R, n = 24, ≥ +2.97 R): **1** (trade 306, $634.50). The damage is ordinary 2–2.5 R winners, not the tail.

**Splits (OBSERVED):** v1 −$2,285 (162 trades; CI −5,294 … +274); v2 −$587 (78; −2,289 … +676); first half −$1,023 (121; −3,340 … +957); second half −$1,849 (119; −4,710 … +274). Negative in all four, as is the comparator (−$4,298 … −$7,717).

**Why it fails (OBSERVED; 127 trades open at minute 15 under the bracket):**

| progress at T = 15 (initial-leg mtm) | trades = sessions | P(target) | mean forward R | median forward R |
|---|---|---|---|---|
| < −0.5 R | 12 | 0.08 | −0.13 | −0.34 |
| −0.5 … 0 R | 31 | 0.42 | +0.50 | −0.59 |
| 0 … +0.5 R | 25 | 0.60 | +0.72 | +1.77 |
| +0.5 … +1 R | 23 | 0.52 | −0.28 | +1.04 |
| ≥ +1 R | 36 | 1.00 | +1.36 | +1.24 |

The rule fires on the first two buckets. The "−0.5 … 0 R" bucket still reaches the 2–2.5 R target 42 % of the time, so its forward expectation is positive; exiting converts a ≈ 0 R subset (fired trades' baseline mean −0.05 R) into a certain −0.49 R. HYPOTHESIS: under an asymmetric bracket "no progress" is not "failure"; only "< −0.5 R" is, and that is 12 trades worth ≈ $250.

**Strongest competing explanation.** The generator may have planted a uniform positive post-entry drift for KX (+0.355 R/entry, ~3 SE above zero). Under uniform drift any early exit forfeits expectation whatever the path, so this result cannot separate "early progress is uninformative" from "no path dependence was generated"; only the real export can. The CI admits a tiny benefit (+0.004 R/entry) but excludes one worth having (≥ +0.05).

## 3. Reproducible check (code path + pasted output)

`python3 src/S2/run.py` (≈ 10 s), verbatim:

```
NOMINATED (fixed before results): FAIL_mtm_T15_X+0.0; COMPARATOR: TIME_T15
exit reason identical: 233/240; exit bar identical: 225/240; |net diff|<=$0.01: 231/240
journal KX net $12,685.72 vs replay $12,589.22
Largest winners = top 10% by BASELINE net R: n=24, threshold net R >= 2.972
T=15: open 127 trades / 127 sessions; original exits before T: 113
== Policy cells examined: 46 (= 2x5x4 failure cells + 5 time exits + 1 breakeven variant) ==
            policy  n_fired  delta_net_usd  ci_usd_lo  ci_usd_hi  delta_meanR  ci_R_lo  ci_R_hi  n_top10_fired  usd_surrendered_top10
FAIL_mtm_T15_X+0.0       43       -2871.00  -6134.062    156.550       -0.079   -0.169    0.004              1                 634.50
          TIME_T15      127      -12014.82 -17468.974  -6438.696       -0.328   -0.477   -0.171             19                5254.04
  BE_mtm_T15_X+0.0       43       -3221.04  -7620.720   1157.055       -0.081   -0.200    0.036              1                 634.50
FAIL_mtm_T30_X+0.3       24         653.50  -2105.625   3137.262        0.027   -0.048    0.094              2                1303.50
rule fired on 43 trades / 43 sessions; among them original outcome: {'STOP': 29, 'TARGET': 14}
  losses avoided   (orig loser,  gross delta>0): n=29, $2,642.50
  winners surrendered (orig winner, gross delta<0): n=14, $-5,513.50
  incremental commissions (rule - orig): $0.00  (adds not taken: 0)
  NET paired delta on fired trades: $-2,871.00; on all 240 entries: $-2,871.00
  exits shortly before a large winner: 1 of the 24 top-10% baseline winners were exited by the rule; dollars surrendered on them $634.50
Overlap check: trades where the nominated rule holds LONGER than the original: 0
```

**Worked examples (SYNTHETIC EXAMPLE; initial-leg R at bar close, MFE so far; `k` = bar after entry).**

*Useful exit (add at k = 8 on in both arms; rule closes 3 contracts; first instant knowable 10:17):*

```
USEFUL EXIT: trade_id=130 session=2025-09-17 KX_ORB_v1 LONG entry 10:02 @ 22333.5 n0=2 stop 22289.75 target 22421.25 1R=$175.47 add=yes @22370.0 10:10
  ORIGINAL: exit STOP at minute 24 px 22289.5 net $-341.44 (-1.95 R)
  RULE    : progress at decision -0.114 R (< +0.0) -> exit minute 15 px 22328.25 net $-108.94 (-0.62 R); paired delta $232.50
 k bar_open  close_R  mfe_R  worst_R
 6    10:08    0.843  0.855    0.450
 9    10:11    0.866  1.071    0.513
12    10:14    0.393  1.071    0.393
13    10:15    0.097  1.071    0.097
14    10:16   -0.114  1.071   -0.125 <- decision knowable at this bar close (10:17)
15    10:17   -0.057  1.071   -0.410 <- rule exit at this bar open (1 tick adverse)
19    10:21   -0.325  1.071   -0.325
24    10:26   -0.889  1.071   -1.083   (original stop fills here)
```

*Costly false alarm (top-10 % baseline winner; add at k = 6 on in both arms, alone loses $132 under the rule; first instant knowable 10:51):*

```
COSTLY FALSE ALARM: trade_id=306 session=2026-03-19 KX_ORB_v2 SHORT entry 10:36 @ 24784.25 n0=2 stop 24822.5 target 24688.5 1R=$153.16 add=yes @24728.25 10:42
  ORIGINAL: exit TARGET at minute 203 px 24688.5 net $458.06 (+2.99 R)
  RULE    : progress at decision -0.261 R (< +0.0) -> exit minute 15 px 24794.25 net $-176.44 (-1.15 R); paired delta $-634.50
 k bar_open  close_R  mfe_R  worst_R
 5    10:41    1.463  1.463    0.790
 6    10:42    1.064  1.541    1.064
10    10:46    0.052  1.541    0.052
12    10:48   -0.046  1.541   -0.281
14    10:50   -0.261  1.541   -0.261 <- decision knowable at this bar close (10:51)
15    10:51    0.490  1.541   -0.255 <- rule exit at this bar open (1 tick adverse)
19    10:55    0.894  1.541    0.725
25    11:01    0.170  1.541    0.039   (target reached ~3 h later)
```

## 4. When following this would make the decision worse

- If the real KX edge is **front-loaded** (realised in the first 15 min, later holding pure variance), early exits cut only losers and "hold" is wrong; the conditional table on the real export (section 5) detects this.
- If real stop fills slip more than 1 tick in fast markets while a voluntary exit on a calm bar does not, the rule's cost advantage is understated here (incremental cost $0).
- Wider real stops than the synthetic 8–60 pt clip raise the losses avoided per fire and could tip the balance.

## 5. Cheapest decisive test on the user's real data, and the result that retires the idea

Run `src/S2/run.py` unchanged on the real export, KX only; two pre-registered cells, `FAIL_mtm_T15_X+0.0` and `TIME_T15`. **Retire the failed-follow-through family for KX if** the failure rule's paired mean ΔR/entry has a 95 % session-bootstrap CI upper bound < +0.05 R/entry **and** the "−0.5 … 0 R at minute 15" bucket's mean forward R is ≥ 0 (P(target) above the breakeven ≈ 0.35 for a 2 R target, (1 + c)/3 with c ≈ 0.03 R). Needs ≥ 40 fired trades in ≥ 40 sessions; one replay.

## 6. What the real export must contain for this test (exact fields)

`trades.csv`: `trade_id, session, strategy, family, direction, entry_ts (ET; state bar-open vs fill time), entry_px, initial_contracts, added_contracts, add_px, add_ts, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason, commission_usd, net_pnl_usd`. `bars_MNQ_1min.csv`: `ts` with explicit offset (DST-safe), `open, high, low, close`, full session after every exit. `fills.csv`: `trade_id, leg_id, ts_utc, side, qty, price, order_type, fill_role`. `costs.csv`: commission/side, tick, point value, slippage, EOD flat time. `strategy_versions.csv` with validity dates. State how MANUAL exits are to be treated and whether exits inside the entry bar are possible live.

## 7. Policies and thresholds examined (complete count, including discarded)

**46 policy cells**, all replayed, all in `src/S2/out/grid_summary.csv`: failure rule, 2 progress definitions (mtm close, MFE) × T ∈ {5, 10, 15, 20, 30} × X ∈ {0, +0.2, +0.3, +0.5} R = 40; unconditional time exit, T ∈ {5, 10, 15, 20, 30} = 5; breakeven variant at (T 15, X 0) = 1. Plus two baseline orderings (stop-first / target-first; identical on 240/240). Discarded on sight: MFE cells with X = 0 at T ≥ 15 (never fire). Not examined (HYPOTHESIS only): X < 0, suggested by the "< −0.5 R" bucket (12 trades).

## 8. Proposed challenger(s) for pre-registration

**S2-C1 "late failure exit" (primary; post hoc best of 46 cells, low prior).** Mechanism: a breakout that has not retained +0.3 R after 30 min has lost its impulse. Decision time: close of bar 29 after entry (entry + 30 min), initial-leg close-to-close open profit in R. Parameters: T = 30, X = +0.3 R, KX only, both versions. Fill assumptions: market exit of all open contracts at the open of bar 30, 1 tick adverse, $0.74/contract/side; original add rule unchanged (an add already on is closed with the position); otherwise the original bracket and 15:55 flat continue. Objective: paired mean Δ net R/entry vs original ≥ +0.03 with 95 % session-bootstrap CI excluding 0; retire if the CI upper bound < +0.03. Development: +$654 (CI −2,106 … +3,137), 24 fired trades, consistent with noise.

**S2-C2 "nominated failure exit" (optional, negative control).** `FAIL_mtm_T15_X+0.0` with `TIME_T15` as comparator, exactly as in section 5. Objective: confirm on the holdout that the development harm (−0.079 R/entry) is real; if Δ ≤ 0 again, retire the family. Recommendation: at most one of the four slots for this family — S2-C1 if one; S2-C2 only if a slot is spare.
