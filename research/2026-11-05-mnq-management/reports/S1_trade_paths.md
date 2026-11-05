# S1 — Trade-path statistician: "given what was observable at this point, what happened next?"

**Every number here is SYNTHETIC** (`data/synthetic/`, 2025-05-01 → 2026-04-30, 332 trades / 242 sessions); results are about the method, not the market. Code: `src/S1/run.py` (full tables in `src/S1/output/`). Figures: `charts/S1_milestone_curves.png`, `charts/S1_kx_stall_paired.png`.

**Conventions.** 1R = `planned_risk_usd` of the initial leg, fixed for the trade. Path = initial-leg price path `dir × (px − entry_px) / stop_dist` on MNQ bars; "at minute k" = close of the k-th bar after entry (bar k closes at entry_ts + k min); "touched" uses bar high/low; decision time = open of bar k. **Conditional cells contain only trades still open at the decision time under the ORIGINAL policy.** Final R = `net_pnl_usd / planned_risk_usd`, all legs, after commissions. For trades with an add the path is the initial leg's; the add leg is reported separately (§2.4).

**Execution assumptions.** *Exit-now*: market order at the open of the decision bar, 1 tick adverse, $0.74/side/contract on every leg, whole position closed (add included only if filled before that bar). *Breakeven stop (BE)*: from the decision bar on, the stop of all legs sits at `entry_px`, target unchanged; stop fill = entry − 1 tick, or the bar open if gapped through; target = limit, 0 slippage; both in one bar → both orderings (never occurred, `be_ambig` = 0); flat at the 15:55 open. Neither counterfactual holds past the original exit except after the 10 MANUAL exits (`be_longer`), so no later-entry overlap arises. Uncertainty: 2,000 whole-session bootstrap draws.

## 1. Strongest finding and the decision it changes

**OBSERVED (SYNTHETIC).** For the concrete decision — a KX trade reaches ≥ +0.8R and retraces to ≤ +0.3R — *holding the original bracket* beats both active responses. In 60 stall trades / 60 sessions, mean final R under the original policy is **+0.41R** [−0.10, 0.88] (+$60/trade after costs; P(target) 0.47; median −0.67R; P(R < −0.5R) 0.50). Exiting at the stall bar: −0.09R (−$13), paired Δ **−0.50R [−0.99, +0.01]**. Tightening to breakeven: +0.09R, Δ **−0.31R [−0.76, +0.11]**; BE cuts the tail (P(R < −0.5) 0.50 → 0.18; worst decile −2.45R → −0.87R) at ~0.3R per stall trade.

In every KX state with n ≥ 20 the expected gain from continuing to hold is positive (original − exit-now ≈ −0.4 to −1.0R, Table A); no observable state isolates trades with negative remaining expectancy. **Decision changed:** no stall-exit or stall-tighten rule for KX; the only cost-neutral candidate is a late (≥ 15–20 min), profit-conditional breakeven stop whose benefit is tail reduction (§8, C1). For PX the +0.8R stall state does not occur (median target +0.70R; < +0.8R in 61/92 trades).

## 2. Evidence (labelled) and the strongest competing explanation

### 2.1 Baseline (OBSERVED; denominator = trades; net of costs)

| group | n | sessions | P_target | mean_R | mean_R_CI | median_R | P_R_lt_m05 | mean_usd | total_usd |
|---|---|---|---|---|---|---|---|---|---|
| KX (all) | 240 | 240 | 0.40 | 0.36 | [0.12, 0.58] | -1.02 | 0.58 | 52.86 | 12685.72 |
| KX_ORB_v1 | 162 | 162 | 0.41 | 0.31 | [0.04, 0.57] | -1.02 | 0.57 | 46.76 | 7575.56 |
| KX_ORB_v2 | 78 | 78 | 0.37 | 0.44 | [-0.01, 0.89] | -1.02 | 0.62 | 65.51 | 5110.16 |
| PX_REV_v1 | 92 | 92 | 0.67 | 0.19 | [0.05, 0.34] | 0.50 | 0.26 | 29.17 | 2683.98 |

### 2.2 Central Table A — state at decision time → what happened next (OBSERVED, SYNTHETIC)

`d_exit` = paired Δ (exit-now − original), CI from the session bootstrap. Selected rows; full table: `src/S1/output/central_table_full.csv`. Cells with n < 20 are not interpretable.

| group | state | n | sessions | P_target | mean_R | mean_R_CI | median_R | P_R_lt_m05 | mean_usd | cf_exit_mean_R | cf_exit_mean_usd | d_exit | d_exit_CI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KX (all) | min 5: all still open | 202 | 202 | 0.46 | 0.58 | [0.31, 0.82] | -1.02 | 0.52 | 86.41 | 0.07 | 10.03 | -0.51 | [-0.73, -0.26] |
| KX (all) | min 5: open profit <= 0R | 98 | 98 | 0.30 | 0.00 | [-0.31, 0.32] | -1.02 | 0.67 | 2.40 | -0.41 | -62.45 | -0.41 | [-0.72, -0.11] |
| KX (all) | min 5: not yet touched +0.3R | 83 | 83 | 0.24 | -0.20 | [-0.54, 0.12] | -1.02 | 0.72 | -31.32 | -0.34 | -53.77 | -0.14 | [-0.47, 0.20] |
| KX (all) | min 5: open profit >= +0.3R | 70 | 70 | 0.77 | 1.75 | [1.32, 2.13] | 2.37 | 0.21 | 261.10 | 0.72 | 107.86 | -1.03 | [-1.41, -0.62] |
| KX (all) | min 10: all still open | 158 | 158 | 0.53 | 0.80 | [0.51, 1.08] | 1.96 | 0.46 | 122.68 | 0.19 | 30.00 | -0.61 | [-0.84, -0.37] |
| KX (all) | min 10: open profit <= 0R | 68 | 68 | 0.22 | -0.27 | [-0.60, 0.06] | -1.02 | 0.75 | -35.68 | -0.45 | -67.36 | -0.17 | [-0.49, 0.13] |
| KX (all) | min 10: not yet touched +0.3R | 42 | 42 | 0.19 | -0.37 | [-0.75, 0.06] | -1.02 | 0.79 | -49.81 | -0.48 | -73.12 | -0.10 | [-0.50, 0.25] |
| KX (all) | min 15: open profit <= 0R | 42 | 42 | 0.33 | -0.00 | [-0.46, 0.48] | -1.02 | 0.64 | 0.26 | -0.49 | -75.77 | -0.49 | [-0.97, -0.04] |
| KX (all) | min 20: all still open | 94 | 94 | 0.63 | 1.13 | [0.72, 1.50] | 1.98 | 0.36 | 169.67 | 0.60 | 88.42 | -0.53 | [-0.86, -0.18] |
| KX (all) | min 30: all still open | 59 | 59 | 0.66 | 1.17 | [0.65, 1.64] | 1.98 | 0.34 | 177.64 | 0.77 | 115.07 | -0.40 | [-0.79, 0.01] |
| KX (all) | touched>=+0.8R then close<=+0.3R | 60 | 60 | 0.47 | 0.41 | [-0.10, 0.88] | -0.67 | 0.50 | 60.35 | -0.09 | -13.22 | -0.50 | [-0.99, 0.01] |
| KX (all) | touched>=+0.8R then close<=+0.5R | 72 | 72 | 0.56 | 0.77 | [0.32, 1.20] | 1.96 | 0.42 | 113.96 | 0.14 | 21.22 | -0.63 | [-1.06, -0.18] |
| KX (all) | touched>=+1.0R then close<=+0.5R | 47 | 47 | 0.57 | 0.73 | [0.10, 1.30] | 1.96 | 0.40 | 108.54 | 0.04 | 8.89 | -0.68 | [-1.24, -0.08] |
| KX (all) | touched>=+0.5R then close<=+0.2R | 92 | 92 | 0.41 | 0.25 | [-0.12, 0.61] | -1.02 | 0.57 | 39.26 | -0.12 | -18.62 | -0.37 | [-0.73, -0.01] |
| KX (all) | touched>=+0.3R then close<=0R (entry revisit) | 111 | 111 | 0.33 | 0.01 | [-0.31, 0.33] | -1.02 | 0.65 | 7.99 | -0.32 | -49.86 | -0.33 | [-0.64, -0.01] |
| KX_ORB_v1 | touched>=+0.8R then close<=+0.3R | 41 | 41 | 0.56 | 0.74 | [0.16, 1.31] | 1.96 | 0.41 | 106.56 | -0.06 | -8.00 | -0.80 | [-1.38, -0.24] |
| KX_ORB_v2 | touched>=+0.8R then close<=+0.3R | 19 | 19 | 0.26 | -0.30 | [-1.17, 0.64] | -1.02 | 0.68 | -39.37 | -0.16 | -24.47 | 0.15 | [-0.80, 0.97] |
| KX_ORB_v2 | min 10: open profit <= 0R | 20 | 20 | 0.15 | -0.38 | [-0.96, 0.30] | -1.02 | 0.80 | -38.61 | -0.43 | -59.49 | -0.05 | [-0.68, 0.50] |
| PX_REV_v1 | min 5: all still open | 87 | 87 | 0.68 | 0.20 | [0.04, 0.35] | 0.50 | 0.26 | 30.33 | -0.03 | -4.71 | -0.23 | [-0.35, -0.10] |
| PX_REV_v1 | min 5: open profit <= 0R | 47 | 47 | 0.45 | -0.22 | [-0.44, 0.01] | -0.47 | 0.49 | -31.22 | -0.25 | -37.74 | -0.03 | [-0.24, 0.18] |
| PX_REV_v1 | min 10: open profit <= 0R | 30 | 30 | 0.37 | -0.28 | [-0.56, 0.02] | -0.57 | 0.53 | -37.91 | -0.35 | -52.39 | -0.07 | [-0.35, 0.19] |
| PX_REV_v1 | min 10: not yet touched +0.3R | 40 | 40 | 0.45 | -0.15 | [-0.40, 0.10] | 0.06 | 0.45 | -18.52 | -0.21 | -31.26 | -0.06 | [-0.28, 0.18] |
| PX_REV_v1 | min 15: open profit <= 0R | 24 | 24 | 0.33 | -0.31 | [-0.59, 0.02] | -0.57 | 0.54 | -43.62 | -0.43 | -65.81 | -0.13 | [-0.41, 0.14] |
| PX_REV_v1 | min 20: all still open | 34 | 34 | 0.62 | 0.18 | [-0.11, 0.44] | 0.49 | 0.29 | 28.67 | -0.12 | -17.31 | -0.30 | [-0.54, -0.06] |
| PX_REV_v1 | touched>=+0.3R then close<=0R (entry revisit) | 15 | 15 | 0.67 | 0.20 | [-0.29, 0.64] | 0.57 | 0.33 | 22.56 | -0.14 | -22.81 | -0.34 | [-0.76, 0.13] |
| PX_REV_v1 | touched>=+0.5R then close<=+0.2R | 8 | 8 | 0.75 | 0.37 | [-0.30, 0.86] | 0.78 | 0.25 | 33.61 | 0.12 | 15.98 | -0.25 | [-0.76, 0.40] |
| PX_REV_v1 | touched>=+0.8R then close<=+0.3R | 0 | 0 | | | | | | | | | | |

Reading: (i) KX — exit-now loses in every state with n ≥ 20; smallest (CI straddles 0) in the most failure-like states, never positive. (ii) PX — in losing states holding and exiting are indistinguishable (Δ −0.03 to −0.13R): PX losers carry no remaining edge, but exiting recovers nothing after costs. (iii) Unconditional time exits at ≤ 30 min lose for both families.

### 2.3 Central Table B — tighten to breakeven at decision time (OBSERVED, SYNTHETIC)

| group | state | n | sessions | mean_R | be_stopfirst_R | be_tgtfirst_R | d_be | d_be_CI | P_R_lt_m05 | be_P_R_lt_m05 | orig_worst10 | be_worst10 | be_ambig | be_longer | share_add_before |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KX (all) | min 5: all still open | 202 | 202 | 0.58 | 0.33 | 0.33 | -0.25 | [-0.45, -0.05] | 0.52 | 0.18 | -1.62 | -0.81 | 0 | 0 | 0.07 |
| KX (all) | min 10: all still open | 158 | 158 | 0.80 | 0.59 | 0.59 | -0.22 | [-0.42, -0.01] | 0.46 | 0.23 | -1.67 | -0.86 | 0 | 0 | 0.25 |
| KX (all) | min 15: all still open | 125 | 125 | 1.08 | 0.93 | 0.93 | -0.15 | [-0.38, 0.06] | 0.38 | 0.18 | -1.79 | -0.96 | 0 | 0 | 0.35 |
| KX (all) | min 20: all still open | 94 | 94 | 1.13 | 1.07 | 1.07 | -0.06 | [-0.30, 0.18] | 0.36 | 0.13 | -1.92 | -0.94 | 0 | 0 | 0.43 |
| KX (all) | min 30: all still open | 59 | 59 | 1.17 | 1.17 | 1.17 | -0.00 | [-0.34, 0.30] | 0.34 | 0.10 | -2.18 | -0.97 | 0 | 0 | 0.46 |
| KX (all) | min 10: open profit >= +0.3R | 65 | 65 | 1.95 | 1.71 | 1.71 | -0.24 | [-0.54, 0.05] | 0.15 | 0.09 | -2.04 | -0.77 | 0 | 0 | 0.52 |
| KX (all) | min 15: open profit >= +0.3R | 68 | 68 | 1.85 | 1.96 | 1.96 | 0.11 | [-0.10, 0.30] | 0.19 | 0.04 | -1.97 | -0.66 | 0 | 0 | 0.53 |
| KX (all) | min 20: open profit >= +0.3R | 63 | 63 | 1.66 | 1.70 | 1.70 | 0.04 | [-0.25, 0.29] | 0.24 | 0.06 | -2.01 | -0.71 | 0 | 0 | 0.57 |
| KX (all) | min 30: open profit >= +0.3R | 39 | 39 | 2.09 | 1.95 | 1.95 | -0.15 | [-0.48, 0.13] | 0.10 | 0.03 | -1.46 | -0.40 | 0 | 0 | 0.59 |
| KX (all) | touched>=+0.8R then close<=+0.3R | 60 | 60 | 0.41 | 0.09 | 0.09 | -0.31 | [-0.76, 0.11] | 0.50 | 0.18 | -2.45 | -0.87 | 0 | 0 | 0.37 |
| KX_ORB_v1 | touched>=+0.8R then close<=+0.3R | 41 | 41 | 0.74 | 0.14 | 0.14 | -0.60 | [-1.14, -0.10] | 0.41 | | | | 0 | 0 | 0.29 |
| KX_ORB_v2 | touched>=+0.8R then close<=+0.3R | 19 | 19 | -0.30 | -0.00 | -0.00 | 0.30 | [-0.50, 0.99] | 0.68 | | | | 0 | 0 | 0.53 |
| PX_REV_v1 | min 5: all still open | 87 | 87 | 0.20 | 0.08 | 0.08 | -0.12 | [-0.25, 0.00] | 0.26 | 0.07 | -1.03 | -0.57 | 0 | 1 | 0.00 |
| PX_REV_v1 | min 10: open profit <= 0R | 30 | 30 | -0.28 | -0.35 | -0.35 | -0.07 | [-0.35, 0.19] | 0.53 | 0.20 | -1.04 | -0.80 | 0 | 0 | 0.00 |
| PX_REV_v1 | min 20: all still open | 34 | 34 | 0.18 | -0.08 | -0.08 | -0.26 | [-0.50, -0.02] | 0.29 | 0.15 | -1.02 | -0.72 | 0 | 1 | 0.00 |

Reading: a breakeven stop costs mean R at minute 5–10 and is cost-neutral by minute 15–20 **if the trade is already ≥ +0.3R**, while cutting P(R < −0.5) ~4× and the worst-decile mean by ~1.3R — the only "drawdown at acceptable cost" candidate here.

### 2.4 Stall detail, adds, milestones (OBSERVED, SYNTHETIC)

```
KX stall (>= +0.8R then close <= +0.3R): n=60 trades / 60 sessions; original exit reasons {STOP: 29, TARGET: 28, MANUAL: 3};
  decision minute median 11 (IQR 6-17); share with add already filled 0.37; BE outcomes {STOP_BE: 53, TARGET: 7}
  mean final R whole position 0.41 vs initial leg only 0.45 (add leg contributes -0.05R per trade on average)
  final R quantiles under original policy: q10=-1.95, q25=-1.04, q50=-0.67, q75=2.33, q90=2.79
  exit-now R: mean -0.09, median -0.01
PX stall: n=0  (PX target >= +0.8R in only 31 of 92 trades; target distance median 0.70R, IQR 0.54-0.84)
KX trades with add: 73 of 240; add fill minute median 8; mean final R with add 2.02 (initial leg only 1.67); without add -0.37
KX trades that touched +1.0R within 20 min: 92 (adds observed: 73)
```

Adds: 22 stall trades (37%) already carry an add filled near +1.0R, ~0.7 stop-distances underwater at the stall bar; stalls that later stop out land at −2R/−3R (`charts/S1_kx_stall_paired.png`). 92 trades qualified for an add, 73 added (for S5).

Time-to-milestone (minutes after entry; "within original hold" is censored at the exit; "unmanaged" ignores the exit, HYPOTHETICAL):

| family | scope | milestone | n_trades | n_sessions | share_reached | n_reached | q25_min | median_min | q75_min | p_within_10min |
|---|---|---|---|---|---|---|---|---|---|---|
| KX | within original hold | +0.3R touched | 240 | 240 | 0.71 | 171 | 1.00 | 2.00 | 5.00 | 0.92 |
| KX | within original hold | +0.8R touched | 240 | 240 | 0.53 | 128 | 3.00 | 7.00 | 12.00 | 0.70 |
| KX | within original hold | -0.5R touched | 240 | 240 | 0.72 | 173 | 3.00 | 5.00 | 9.00 | 0.79 |
| KX | within original hold | close<=0R after touching +0.3R | 240 | 240 | 0.47 | 112 | 4.00 | 7.00 | 11.00 | 0.73 |
| KX | unmanaged path to 15:54 close | +0.3R touched | 240 | 240 | 0.90 | 215 | 2.00 | 3.00 | 10.00 | 0.75 |
| KX | unmanaged path to 15:54 close | +0.8R touched | 240 | 240 | 0.80 | 192 | 5.00 | 11.00 | 41.00 | 0.48 |
| KX | unmanaged path to 15:54 close | -0.5R touched | 240 | 240 | 0.79 | 190 | 3.00 | 5.00 | 13.00 | 0.72 |
| KX | unmanaged path to 15:54 close | close<=0R after touching +0.3R | 240 | 240 | 0.67 | 160 | 5.00 | 9.00 | 31.50 | 0.54 |
| PX | within original hold | +0.3R touched | 92 | 92 | 0.75 | 69 | 4.00 | 8.00 | 14.00 | 0.68 |
| PX | within original hold | +0.8R touched | 92 | 92 | 0.34 | 31 | 10.00 | 14.00 | 34.00 | 0.35 |
| PX | within original hold | -0.5R touched | 92 | 92 | 0.39 | 36 | 5.00 | 11.00 | 17.25 | 0.47 |
| PX | within original hold | close<=0R after touching +0.3R | 92 | 92 | 0.17 | 16 | 7.25 | 18.00 | 29.50 | 0.31 |
| PX | unmanaged path to 15:54 close | +0.3R touched | 92 | 92 | 0.84 | 77 | 4.00 | 9.00 | 21.00 | 0.61 |
| PX | unmanaged path to 15:54 close | +0.8R touched | 92 | 92 | 0.75 | 69 | 11.00 | 20.00 | 36.00 | 0.20 |
| PX | unmanaged path to 15:54 close | -0.5R touched | 92 | 92 | 0.54 | 50 | 6.25 | 15.50 | 57.75 | 0.34 |
| PX | unmanaged path to 15:54 close | close<=0R after touching +0.3R | 92 | 92 | 0.40 | 37 | 20.00 | 43.00 | 118.00 | 0.14 |

KX paths are fast (median 2 min to +0.3R, 5 min to −0.5R, 7 min to an entry revisit); PX paths are 2–4× slower with larger stop distances (1R up to 80 pts).

### 2.5 Strongest competing explanation

**HYPOTHESIS.** The KX picture is what *planted positive post-entry drift* looks like: P(target) 0.40 and mean +0.36R with a 2–2.5R target vs 1R stop (a driftless path gives ≈ 1/3 at 2R and mean ≈ −costs), and a hold-minus-exit gap of −0.4 to −1.0R in every state. Then "hold beats exit everywhere" is the drift, the stall state is uninformative, and the conclusion transfers only if real KX paths drift the same way. PX (holding ≈ exiting in losing states) looks like a driftless path with a structural target. Secondary: 10 MANUAL exits (3 in the stall set) sit inside the "original" arm, and conditioning on "still open under the original policy" survivor-selects the cells for any policy that exits earlier.

## 3. Reproducible check (code path + pasted output)

`python3 src/S1/run.py` (~30 s) regenerates `src/S1/output/run_output.md` (all tables above), the four CSVs in `src/S1/output/` and both charts. Integrity checks printed first:

```
trades=332  sessions=242  bar sessions=251
max |recomputed gross - gross_pnl_usd| = 0.0000 USD
max |initial_contracts*stop_dist*2 - planned_risk_usd| = 0.99 USD
exit_reason counts: {'TARGET': 158, 'STOP': 157, 'MANUAL': 10, 'TIME_EOD': 4, 'STOP_GAP': 3}
trades with add: {'KX_ORB_v1': 43, 'KX_ORB_v2': 30, 'PX_REV_v1': 0}
```

Every `entry_ts` matches an MNQ bar open; stop fills are stop − 1 tick (157/157), target fills exact (158/158).

## 4. When following this would make the decision worse

- If real KX paths lack the synthetic drift, "hold through the stall" has no support; the stall CIs already reach +0.01R (exit) and +0.11R (BE).
- KX_ORB_v2 stalls (n = 19 / 19) point the other way (Δ_BE +0.30 [−0.50, 0.99]); if the 2.5R target makes stalls worse, a pooled rule is wrong, and 19 trades cannot tell.
- 28 of 96 non-empty cells have n < 20; do not act on them.
- 37% of stall trades carry an add; managing the add leg separately (S4) changes the stall arithmetic.
- 1-minute bars cannot order a +0.8R touch and a ≤ +0.3R close inside one bar, and the next-open fill is far from +0.3R (stall exit-now R: mean −0.09, median −0.01). MANUAL exits: skill flatters the original arm, errors penalise it.

## 5. Cheapest decisive test on the user's real data, and the result that retires the idea

Run `src/S1/run.py` unchanged on the real export and read two cells. (a) KX stall cell: **retire active stall management** (exit and tighten; exit-now is dominated by BE on the same trades, −0.50 vs −0.31) if, on ≥ 40 stall trades / 40 sessions, Δ_BE ≤ 0 with upper CI < +0.2R; **retire "hold"** if Δ_BE > 0 with lower CI > 0. (b) KX "minute 10: all still open": if Δ_exit ≈ −0.05R (costs only) rather than ≈ −0.6R, the synthetic drift is absent and none of the KX conditional means transfer.

## 6. What the real export must contain for this test (exact fields)

| file | fields | requirement |
|---|---|---|
| `trades.csv` | `trade_id, signal_id, session, strategy, family, direction, entry_ts, entry_px, initial_contracts, added_contracts, add_px, add_ts, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason, gross_pnl_usd, commission_usd, net_pnl_usd` | `entry_ts` with ET offset and equal to an MNQ bar OPEN; `exit_ts` = open of the exit bar; a reason text for every MANUAL exit |
| `bars_MNQ_1min.csv` | `ts, open, high, low, close` | `ts` = bar open, ISO 8601 with offset; full RTH session after every exit (390 bars/session) |
| `costs.csv` | commission per side, tick, point value, slippage assumption, EOD flat time | as in the synthetic schema |
| `fills.csv` | `trade_id, leg_id, ts_utc, side, qty, price, order_type, fill_role, commission` | to verify the add leg and per-leg commissions |

## 7. Policies and thresholds examined (complete count, including discarded)

Grid fixed before the run; nothing added or dropped afterwards.

- Horizons: 5 (k = 5, 10, 15, 20, 30 min) × 4 time-conditioned states (all open; ≤ 0R; not touched +0.3R; ≥ +0.3R) = 20 states.
- Path states: 5 (≥ +0.8R→≤ +0.3R; ≥ +0.8R→≤ +0.5R; ≥ +0.5R→≤ +0.2R; ≥ +1.0R→≤ +0.5R; ≥ +0.3R→≤ 0R).
- Profit thresholds: 7 (0, +0.2, +0.3, +0.5, +0.8, +1.0R; −0.5R milestone only).
- Actions: 2 (exit-now; breakeven at entry). Discarded before coding: trailing stops, partial exits (most positions 1–2 contracts), breakeven above entry.
- Groups: 4 (KX all, KX_ORB_v1, KX_ORB_v2, PX_REV_v1). Cells: 25 × 4 = 100 (96 non-empty) × 2 actions = 192 evaluations; 28 cells have n < 20. Milestones: 16 rows.

## 8. Proposed challenger(s) for pre-registration

**C1 — KX late profit-conditional breakeven (drawdown candidate).** Mechanism: at the open of bar entry + 20 min, if the close of bar 20 ≥ entry + 0.3 × stop_dist (mirrored for shorts) and the trade is open, move the stop of all legs to `entry_px`; target unchanged. Decision time: entry_ts + 20 min. Parameters: k = 20, +0.3R, stop at 0R. Fills: stop = entry − 1 tick or bar open if gapped; target limit, 0 slippage; same-bar both → both orderings; $0.74/side/contract. Objective: P(R < −0.5R) and worst-decile mean R at least halved with paired mean net R Δ ≥ −0.10R (lower CI > −0.30R); otherwise retire. Dev (SYNTHETIC): n = 63 / 63, Δ +0.04R [−0.25, 0.29], P(R < −0.5) 0.24 → 0.06, worst decile −2.01 → −0.71R.

**C2 — KX stall → breakeven (the user's concrete question, pre-registered to be falsified).** Mechanism: once cummax(MFE of the initial leg) ≥ +0.8R and a bar closes ≤ +0.3R while open, move the stop of all legs to `entry_px` at the next bar open; target unchanged. Decision time: close of the trigger bar. Parameters: 0.8R / 0.3R / stop at 0R. Fills: as C1. Objective: paired mean net R vs original on the stall set; dev prediction **negative** (Δ −0.31R [−0.76, 0.11], n = 60 / 60). Since exit-now is dominated by BE on the same trades, a holdout Δ ≤ 0 retires both "tighten" and "exit" for stalls and the answer becomes "hold the bracket". Not applicable to PX.
