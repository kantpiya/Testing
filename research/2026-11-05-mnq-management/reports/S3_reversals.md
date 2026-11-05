# S3 — Reversal / profit-taking specialist: PX_REV_v1 post-entry management

**Everything below is SYNTHETIC** (development set 2025-05-01 → 2026-04-30; 92 PX trades in 92 distinct sessions). Code: `src/S3/run.py` + `src/S3/replay.py`; full output `src/S3/output.txt`; figures `charts/S3_*.png`.

Denominators unless stated: n = 92 trades = 92 sessions; dollars are net of $0.74/contract/side on every fill; R = `planned_risk_usd`.

## 1. Strongest finding and the decision it changes

**OBSERVED (synthetic).** For PX the only lever whose effect this sample can resolve is the **profit-taking level**. The structural target (OR midpoint) sits a median **0.70R** from entry (10–90%: 0.43–0.96R). Moving it to the opposite OR boundary (known at entry) adds **+$5,514 [95% CI 3,767; 7,207]**, **+0.40R/entry [0.27; 0.52]** on 64 changed trades; max drawdown of cumulative net P&L improves (−$528 → −$457); worst session unchanged (−$196). A **no-target** probe (stop only, flat 15:55) does better still: +$12,618 [7,217; 18,133], +0.88R [0.50; 1.28]. Every other policy (time exits, no-progress rule, structural stop tightening, partial/full exit at the OR quarter-line) is significantly harmful or indistinguishable from zero.

**Decision changed.** (a) Do not pre-register a time or no-progress rule for PX: the breakout rule ("no +0.3R by minute 10 ⇒ exit") has a negative point estimate in all 13 variants, significantly so in 4. (b) The brief's scenario (+0.8R, stall, back to +0.3R) **never occurs** for PX under the original policy (0/92): the midpoint target removes the trade first (only 31/92 targets are ≥0.8R). It appears only once the target is extended (10/92 under the far target). (c) Setup-specific management is justified only in keeping the breakout failure rule off reversals, not as grounds for a PX-specific timing rule.

## 2. Evidence (labelled) and the strongest competing explanation

**OBSERVED — paired Stage A, 2,000 session-bootstrap draws** (§3; `S3_paired_policies.png`):

- Time exits, bracket kept: T5 −$2,999 [−4,767; −1,226] … T30 −$1,076 [−2,003; −208]; T60 −$61 [−574; 498]; T90 +$327 [−46; 865]; shorter is monotonically worse.
- Structural: stop → re-entered OR boundary after a quarter-line touch −$668 [−1,542; 178] (16 trades; identical under both same-bar orderings); stop → entry −$426 [−1,303; 513]; full exit at quarter-line −$2,782 [−3,916; −1,507]; partial at quarter-line −$326 [−623; 38] — only the 20 multi-lot trades can scale out, 72 one-lot trades are unchanged.
- No-progress grid (k ∈ {5,10,15,20} × θ ∈ {0, 0.15, 0.30}R, plus 50%-of-target at k=10): all 13 point estimates ≤ 0; the mandated NP_k10_0.30R = −$1,213 [−2,826; 371], −0.08R [−0.19; 0.03] (fires on 52/92; five worst false alarms cost $166–$240 each, four of them top-10% baseline winners).
- Top-10% winners (10 trades, fixed on baseline net R) are $1,559 = 59% of P0; under the far target $2,694 = 33% — the gain is broad.

**"A slow reversal is a bad reversal" — OBSERVED, not supported.** When a trade touches +0.3R does not matter: P(target) = 0.93, 1.00, 0.90, 0.91 for ≤5, 6–10, 11–20, 21–60 min (n = 28, 19, 10, 11; the >60 cell has n = 2). At decision time: of trades still open at minute 10 that have **not** reached +0.3R (n = 41), final mean net R is −0.17 [−0.42; 0.06], but the **forward** value of holding from minute 10 (final net R minus the net R of a market exit at minute 10) is **+0.04 [−0.17; 0.26]** — exiting them gains nothing. Same at k = 5, 15, 20 (fwd_R +0.16, +0.10, +0.14; CIs span zero). Close-based progress at minute 10 ranks final outcomes (P(target) 0.39/0.81/1.00) but forward value is positive in every bin (`S3_slow_reversal.png`).

**Strongest competing explanation (HYPOTHESIS).** The generator may have planted directional drift after PX entries. The no-target probe beating every structural level says the gain is **generic drift to 15:55, not the opposite boundary acting as a level** (far target +0.40R < no target +0.88R; the 3/4-line sits between at +0.21R). A real market drifting +0.88R for 2.7 hours after a mean-reversion entry would be extraordinary; expect it to shrink toward zero on real data. Also: no-target hold time is 162 min (vs 28), colliding with the 4-contract limit (14 PX signals already rejected for it; 15 PX trades concurrent with open KX trades), so Stage B can erode it; and 4 journal exits are undocumented MANUAL exits ($59 better than the bracket).

## 3. Reproducible check (code path + pasted output)

`python3 src/S3/run.py` regenerates everything (≈1 min). Conventions: entries fixed at the journal fill; bracket live from the entry bar; stop fills at stop −1 tick (bar open if gapped — 0 cases); limits fill at the limit price even when the bar opens through it (journal convention, trade 95); market exits decided at a bar close fill at the next open −1 tick; 15:55 open −1 tick for anything still open; stop-first on same-bar touches; $0.74/side on every fill. A decision at minute k uses bars closing ≤ entry + k min and fills at the open of minute k.

Reconstruction vs `trades.csv`: **80/92 exact** (net $ and exit bar). Differences: 4 TIME_EOD fills (journal books the bar open, replay applies −1 tick: ±$0.50), 4 MANUAL exits (journal −$58.92 vs bracket −$117.92), 4 trades whose journal exit bar is 1–2 min after the first touch at the same price (131, 228, 248, 256; for S5). Reconstructed P0 $2,623.98 vs journal $2,683.98.

```
| policy             | total_net_usd | mean_net_R | win_pct | d_total_usd | d_usd_CI      | d_mean_R | d_R_CI         | trades_changed | worst_session_usd | maxDD_usd | top10_usd | top10_share | mean_hold_min |
|--------------------|---------------|------------|---------|-------------|---------------|----------|----------------|----------------|-------------------|-----------|-----------|-------------|---------------|
| P0_original        | 2623.98       | 0.19       | 70.65   | 0.00        | [0,0]         | 0.00     | [0.000,0.000]  | 0              | -195.92           | -527.62   | 1559.32   | 0.59        | 28.05         |
| T5                 | -375.02       | -0.02      | 44.57   | -2999.00    | [-4767,-1226] | -0.21    | [-0.334,-0.082]| 88             | -195.92           | -671.24   | 187.32    |             | 4.93          |
| T10                | 848.48        | 0.07       | 59.78   | -1775.50    | [-3397,-167]  | -0.12    | [-0.235,-0.005]| 66             | -195.92           | -656.88   | 496.32    | 0.58        | 9.08          |
| T15                | 1077.98       | 0.08       | 63.04   | -1546.00    | [-2954,-120]  | -0.11    | [-0.203,-0.011]| 47             | -195.92           | -570.38   | 588.32    | 0.55        | 12.09         |
| T20                | 1071.48       | 0.08       | 58.70   | -1552.50    | [-2906,-225]  | -0.11    | [-0.202,-0.017]| 36             | -195.92           | -477.74   | 631.32    | 0.59        | 14.33         |
| T30                | 1548.48       | 0.11       | 65.22   | -1075.50    | [-2003,-208]  | -0.08    | [-0.148,-0.017]| 26             | -195.92           | -387.40   | 868.82    | 0.56        | 17.51         |
| T45                | 2131.48       | 0.15       | 66.30   | -492.50     | [-1081,55]    | -0.04    | [-0.088,0.001] | 14             | -195.92           | -410.12   | 1362.82   | 0.64        | 20.49         |
| T60                | 2562.98       | 0.18       | 70.65   | -61.00      | [-574,498]    | -0.01    | [-0.049,0.031] | 10             | -195.92           | -435.12   | 1460.82   | 0.57        | 22.47         |
| T90                | 2950.48       | 0.21       | 71.74   | 326.50      | [-46,865]     | 0.02     | [-0.003,0.060] | 6              | -195.92           | -379.12   | 1559.32   | 0.53        | 24.65         |
| S_stop_to_boundary | 1955.98       | 0.14       | 58.70   | -668.00     | [-1542,178]   | -0.05    | [-0.112,0.009] | 16             | -195.92           | -443.18   | 1450.82   | 0.74        | 21.50         |
| S_stop_to_entry    | 2198.48       | 0.15       | 57.61   | -425.50     | [-1303,513]   | -0.03    | [-0.097,0.030] | 17             | -195.92           | -399.86   | 1453.32   | 0.66        | 21.27         |
| S_exit_quarter     | -158.02       | -0.02      | 75.00   | -2782.00    | [-3916,-1507] | -0.20    | [-0.281,-0.118]| 70             | -195.92           | -760.50   | 726.32    |             | 15.66         |
| S_partial_quarter  | 2298.48       | 0.16       | 70.65   | -325.50     | [-623,38]     | -0.02    | [-0.043,-0.001]| 15             | -195.92           | -498.40   | 1402.32   | 0.61        | 28.05         |
| S_far_target       | 8137.98       | 0.59       | 66.30   | 5514.00     | [3767,7207]   | 0.40     | [0.273,0.519]  | 64             | -195.92           | -457.34   | 2693.82   | 0.33        | 49.60         |
| S_target_3q        | 5574.98       | 0.40       | 68.48   | 2951.00     | [1735,3922]   | 0.21     | [0.133,0.282]  | 64             | -195.92           | -445.90   | 1952.32   | 0.35        | 38.49         |
| S_no_target        | 15241.48      | 1.07       | 56.52   | 12617.50    | [7217,18133]  | 0.88     | [0.495,1.280]  | 64             | -195.92           | -517.88   | 3031.82   | 0.20        | 162.37        |
| NP_k5_0.00R        | 2556.98       | 0.19       | 47.83   | -67.00      | [-1585,1543]  | 0.00     | [-0.102,0.115] | 47             | -195.92           | -264.30   | 991.32    | 0.39        | 12.10         |
| NP_k5_0.15R        | 999.48        | 0.08       | 44.57   | -1624.50    | [-3351,142]   | -0.11    | [-0.225,0.015] | 64             | -195.92           | -491.38   | 563.32    | 0.56        | 8.88          |
| NP_k5_0.30R        | 282.48        | 0.03       | 44.57   | -2341.50    | [-4130,-575]  | -0.16    | [-0.287,-0.037]| 74             | -195.92           | -491.38   | 362.32    | 1.28        | 5.50          |
| NP_k10_0.00R       | 2263.98       | 0.17       | 57.61   | -360.00     | [-1685,883]   | -0.02    | [-0.109,0.069] | 31             | -195.92           | -341.80   | 1120.82   | 0.50        | 16.33         |
| NP_k10_0.15R       | 1233.98       | 0.10       | 57.61   | -1390.00    | [-2905,95]    | -0.09    | [-0.196,0.011] | 43             | -195.92           | -539.82   | 770.32    | 0.62        | 13.40         |
| NP_k10_0.30R       | 1410.98       | 0.11       | 59.78   | -1213.00    | [-2826,371]   | -0.08    | [-0.188,0.033] | 52             | -195.92           | -526.38   | 770.32    | 0.55        | 10.38         |
| NP_k15_0.00R       | 2178.98       | 0.16       | 60.87   | -445.00     | [-1621,574]   | -0.03    | [-0.104,0.043] | 24             | -195.92           | -484.86   | 1075.82   | 0.49        | 18.23         |
| NP_k15_0.15R       | 1615.48       | 0.12       | 61.96   | -1008.50    | [-2261,199]   | -0.06    | [-0.148,0.017] | 33             | -195.92           | -388.86   | 895.32    | 0.55        | 14.88         |
| NP_k15_0.30R       | 1130.98       | 0.08       | 61.96   | -1493.00    | [-2860,-251]  | -0.10    | [-0.196,-0.017]| 39             | -195.92           | -399.32   | 695.82    | 0.62        | 12.83         |
| NP_k20_0.00R       | 1651.98       | 0.12       | 57.61   | -972.00     | [-2154,195]   | -0.06    | [-0.145,0.018] | 23             | -195.92           | -477.74   | 899.32    | 0.54        | 17.07         |
| NP_k20_0.15R       | 1362.98       | 0.10       | 57.61   | -1261.00    | [-2494,-69]   | -0.09    | [-0.175,-0.003]| 26             | -195.92           | -477.74   | 797.32    | 0.58        | 16.01         |
| NP_k20_0.30R       | 1025.48       | 0.08       | 57.61   | -1598.50    | [-2848,-398]  | -0.11    | [-0.200,-0.027]| 31             | -195.92           | -477.74   | 631.32    | 0.62        | 14.97         |
| NP_k10_50pctTgt    | 1323.98       | 0.10       | 59.78   | -1300.00    | [-2904,321]   | -0.09    | [-0.197,0.026] | 51             | -195.92           | -621.38   | 618.82    | 0.47        | 9.89          |
| S_stop_to_boundary_TGTFIRST | 1955.98 | 0.14     | 58.70   | -668.00     | [-1542,178]   | -0.05    | [-0.112,0.009] | 16             | -195.92           | -443.18   | 1450.82   | 0.74        | 21.50         |
```

Conditional outcomes under the original policy (trades = sessions in every cell):

```
| group               | trades | sessions | P_target | mean_net_R | net_R_CI     | net_usd  | mean_target_R |
| <=5 min to +0.3R    | 28     | 28       | 0.93     | 0.64       | [0.44,0.80]  | 2597.38  | 0.79 |
| 6-10                | 19     | 19       | 1.00     | 0.55       | [0.47,0.65]  | 1563.92  | 0.57 |
| 11-20               | 10     | 10       | 0.90     | 0.50       | [0.09,0.81]  | 802.24   | 0.73 |
| 21-60               | 11     | 11       | 0.91     | 0.47       | [0.12,0.71]  | 836.80   | 0.63 |
| >60                 | 2      | 2        | 0.00     | -0.45      | [-1.01,0.11] | -144.46  | 0.61 |
| never reached +0.3R | 22     | 22       | 0.00     | -0.93      | [-1.02,-0.82]| -3031.90 | 0.72 |

| decision at k                  | trades | sessions | P_target | mean_net_R | fwd_R | fwd_R_CI     | fwd_usd |
| k=5: reached +0.3R by k        | 25     | 25       | 0.92     | 0.64       | 0.37  | [0.18,0.54]  | 1346.00 |
| k=5: NOT reached +0.3R by k    | 63     | 63       | 0.60     | 0.01       | 0.16  | [-0.00,0.32] | 1653.00 |
| k=10: reached +0.3R by k       | 25     | 25       | 0.96     | 0.67       | 0.37  | [0.22,0.53]  | 1341.00 |
| k=10: NOT reached +0.3R by k   | 41     | 41       | 0.46     | -0.17      | 0.04  | [-0.17,0.26] | 434.50  |
| k=15: reached +0.3R by k       | 20     | 20       | 0.90     | 0.57       | 0.35  | [0.08,0.58]  | 1046.50 |
| k=15: NOT reached +0.3R by k   | 27     | 27       | 0.41     | -0.21      | 0.10  | [-0.15,0.35] | 499.50  |
| k=20: reached +0.3R by k       | 15     | 15       | 0.87     | 0.53       | 0.47  | [0.09,0.78]  | 1010.00 |
| k=20: NOT reached +0.3R by k   | 21     | 21       | 0.48     | -0.09      | 0.14  | [-0.12,0.42] | 542.50  |

| close-based progress at min 10 | trades | sessions | P_target | mean_net_R | fwd_R | fwd_R_CI     |
| close < 0R                     | 31     | 31       | 0.39     | -0.30      | 0.05  | [-0.22,0.32] |
| 0R <= close < 0.3R             | 21     | 21       | 0.81     | 0.38       | 0.26  | [-0.04,0.53] |
| close >= 0.3R                  | 14     | 14       | 1.00     | 0.79       | 0.28  | [0.20,0.37]  |
Brief scenario (>= +0.8R then close <= +0.3R while open): P0 = 0/92; S_far_target = 10/92.
```

## 4. When following this would make the decision worse

- If the real path mean-reverts around the midpoint, extending the target converts ~0.7R winners into stops: even here the far target raises stops 24 → 27, EOD exits 4 → 7, and creates the +0.8R→+0.3R stall in 10 trades.
- Holding 50–162 min instead of 28 means more time inside the 4-contract limit (Stage B rejections).
- "No timing rule for PX" is a within-sample null: ±0.1R/entry (≈ ±$15/trade, ≈ ±$1,400/year) lies inside every CI; the sample rejects only effects ≳0.15R per entry.
- 72 one-lot trades make scale-outs a non-policy for most PX entries; partial-exit results rest on 20 trades.

## 5. Cheapest decisive test on the user's real data, and the result that retires the idea

Run `src/S3/run.py` on the export (PX rows of `trades.csv`, `bars_MNQ_1min.csv`, OR width) and read two numbers: (i) paired ΔR of S_far_target vs P0 with its session-bootstrap CI; (ii) paired ΔR of S_no_target. **Retire** the extended target if (i)'s 95% CI includes 0; retire the "midpoint truncates drift" reading if (ii) ≤ 0; if (ii) ≥ (i) > 0 the boundary is not a level and the follow-up is a time-based hold. The breakout rule stays off PX unless NP_k10_0.30R shows ΔR > 0 with a CI excluding 0 (≳0.15R/entry at ~90 PX trades/year).

## 6. What the real export must contain for this test (exact fields)

- `trades.csv` (PX rows): `trade_id, session, strategy, family, direction, entry_ts` (entry-bar open, with offset), `entry_px, initial_contracts, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason, commission_usd, net_pnl_usd`; MANUAL exits with a reason code.
- `signals.csv` or per-session: `signal_id, ref_width` (OR width), or better `or_high, or_low`.
- `bars_MNQ_1min.csv`: `ts` (bar open, with offset), `open, high, low, close` for the **entire** RTH session of every PX day, past the exit.
- `costs.csv`: commission per side, tick, point value, EOD flat time, slippage convention per order type (journal shows 0–2 ticks on entries, 0 on EOD exits).

## 7. Policies and thresholds examined (complete count, including discarded)

**29 policies + 1 sensitivity run**, all in the §3 table; all but the three target-level variants discarded.

| Family | Variants | Count | Status |
|---|---|---|---|
| Original bracket | midpoint target, extreme-based stop, flat 15:55 | 1 | baseline |
| Time exit, bracket kept | H ∈ {5, 10, 15, 20, 30, 45, 60, 90} min | 8 | discarded |
| Structural stop/exit | stop → OR boundary after quarter-line touch; stop → entry after quarter-line touch; full exit at quarter-line; partial floor(q/2) at quarter-line | 4 | discarded |
| Same-bar ordering sensitivity | moved stop, target-first | 1 run | identical |
| Target level | opposite OR boundary; OR 3/4-line; no target | 3 | retained |
| No-progress (breakout-style) | k ∈ {5, 10, 15, 20} × θ ∈ {0, 0.15, 0.30}R; 50%-of-target at k = 10 | 13 | discarded |
| Conditioning thresholds | +0.3R intrabar; k ∈ {5, 10, 15, 20}; time-to-+0.3R bins {≤5, 6–10, 11–20, 21–60, >60, never}; close-progress bins at minute 10 {<0, 0–0.3, ≥0.3}R; the brief's +0.8R/+0.3R stall | — | reported |

## 8. Proposed challengers for pre-registration

**C1 — PX_FAR_TARGET.** Mechanism: PX target limit at the opposite OR boundary (`initial_target_px` + direction × OR_width/2, tick-rounded) instead of the midpoint; stop unchanged; flat at the 15:55 open. Decision time: entry (no free parameters). Fills: limit at the limit price, 0 slippage, also when the bar opens through it; stop at stop −1 tick or the bar open if gapped; EOD market at the 15:55 open −1 tick; $0.74/contract/side on every fill; stop-first on same-bar touches, target-first reported. Objective: primary — paired mean net R per entry vs original, 95% session-bootstrap CI (≥1,000 draws); secondary — total net $, max drawdown, worst session, Stage B net $ under the 4-contract limit. Retire if the primary CI includes 0.

**C2 — PX_NO_TARGET (drift probe).** Mechanism: PX bracket with the target removed; stop unchanged; flat at the 15:55 open. Decision time: entry. Fills and objective as C1, with the pre-registered reading: C2 ≥ C1 > 0 ⇒ generic drift (the level adds nothing); C1 > 0 ≥ C2 ⇒ the boundary is a real level; C1 ≤ 0 ⇒ keep the midpoint. Both go through Stage B (mean hold 28 → 50 and 162 min).
