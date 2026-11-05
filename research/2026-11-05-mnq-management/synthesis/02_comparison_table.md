# Comparison table — original policy vs pre-registered challengers (SYNTHETIC data)

Source: `src/director/holdout_run.py` with the S5 reference engine (`src/S5/replay.py`); outputs in `src/director/out/comparison_{development,holdout}.csv`. Reference fill model: MNQ bars, stop fires on touch at stop − 1 tick (bar open − 1 tick if gapped), limit fills on penetration at the limit, 1 tick on market exits, $0.74 per contract per side on every fill, same-bar stop+target resolved as the worse outcome (0 such bars occurred for any policy). Stage A: identical entries, identical initial size, paired per trade. Confidence intervals: 2,000-draw bootstrap over whole sessions.

**Definitions.** 1R = planned risk of the initial leg, fixed. *Largest winners* = the top 10% of trades by **baseline (P0) net R within the family**, chosen once on P0 and held fixed across policies (development: 24 KX trades with net R ≥ 2.97, 9 PX trades; holdout: 6 KX, 3 PX). *Losses avoided* = Σ paired Δ$ on trades that lost under P0 and did better under the challenger. *Winners cut short* = Σ paired Δ$ on trades that won under P0 and did worse under the challenger. Worst session and max drawdown are on the challenger's own cumulative net P&L for the family. Every number is SYNTHETIC: it tests the method, not the market.

## Development set (2025-05-01 → 2026-04-30; 240 KX trades / 240 sessions; 92 PX / 92)

| Policy | Family | Net $ | Mean R / entry | Δ$ vs P0 [95% CI] | ΔR / entry [95% CI] | Worst session $ | Max DD $ | Losses avoided $ (n) | Winners cut $ (n) | Largest-winner P&L $ (of baseline) | Largest winners cut |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **P0 original bracket** | KX | 12,638 | +0.357 | — | — | −392 | −1,994 | — | — | 11,116 (24) | — |
| **P0 original bracket** | PX | 2,676 | +0.191 | — | — | −196 | −528 | — | — | 1,455 (9) | — |
| C1 stall → breakeven | KX | 9,238 | +0.270 | −3,400 [−7,892, +783] | −0.086 [−0.200, +0.025] | −224 | −3,180 | +5,543 (31) | −8,943 (22) | 9,438 | 3 of 24 |
| C2 late profit-conditional BE (min 20, ≥ +0.3R) | KX | 12,760 | +0.367 | +121 [−2,633, +2,504] | +0.010 [−0.064, +0.073] | −341 | −1,823 | +2,676 (15) | −2,555 (6) | 9,958 | 2 of 24 |
| C3 add-leg stop at entry | KX | 12,318 | +0.351 | −320 [−1,407, +618] | −0.006 [−0.035, +0.019] | −272 | −1,936 | +888 (11) | −1,208 (8) | 10,648 | 3 of 24 |
| C4 PX far target | PX | 8,138 | +0.587 | +5,462 [+3,547, +7,157] | +0.396 [+0.260, +0.515] | −196 | −457 | 0 (0) | −1,183 (5) | 2,482 | 1 of 9 |
| *D1 KX no target + BE at 2R (drift probe, not a candidate)* | KX | 73,750 | +2.116 | +61,112 [+39,766, +82,018] | +1.760 [+1.156, +2.341] | −392 | −1,997 | +258 (1) | −12,503 (34) | 24,315 | 7 of 24 |
| *D3 stall → exit now* | KX | 7,969 | +0.224 | −4,669 [−9,568, −158] | −0.133 [−0.268, −0.007] | −224 | −3,559 | +6,414 (31) | −11,084 (29) | 8,632 | 5 of 24 |
| *D4 no progress at 15 min → exit* | KX | 9,767 | +0.278 | −2,871 [−6,148, +143] | −0.079 [−0.169, +0.004] | −392 | −1,996 | +2,642 (29) | −5,514 (14) | 10,481 | 1 of 24 |
| *D4b unconditional 15-min exit* | KX | 623 | +0.029 | −12,015 [−17,206, −6,378] | −0.328 [−0.470, −0.174] | −326 | −3,262 | +8,127 (50) | −20,142 (77) | 5,862 | 19 of 24 |

Stage B on the development set (chronological, 4-contract limit, rejected signals eligible, all strategies together): P0 $15,664; C1 −$3,843 vs P0 (its earlier breakeven stops free room for 12 extra signals and block 2); C2 +$56; C3 −$450; C4 +$5,251; D1 +$74,068.

## Sealed holdout (2026-05-01 → 2026-07-30; 60 KX trades / 60 sessions, all KX_ORB_v2; 28 PX / 28)

| Policy | Family | Net $ | Mean R / entry | Δ$ vs P0 [95% CI] | ΔR / entry [95% CI] | Worst session $ | Max DD $ | Losses avoided $ (n) | Winners cut $ (n) | Largest-winner P&L $ (of baseline) | Largest winners cut |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **P0 original bracket** | KX | 4,758 | +0.723 | — | — | −379 | −1,277 | — | — | 2,579 (6) | — |
| **P0 original bracket** | PX | 191 | +0.033 | — | — | −162 | −704 | — | — | 650 (3) | — |
| C1 stall → breakeven | KX | 5,625 | +0.821 | +866 [−1,005, +2,400] | +0.098 [−0.096, +0.265] | −218 | −1,166 | +1,562 (8) | −696 (2) | 2,579 | 0 of 6 |
| C2 late profit-conditional BE | KX | 5,033 | +0.748 | +274 [0, +824] | +0.025 [0, +0.075] | −377 | −1,277 | +274 (1) | 0 (0) | 2,579 | 0 of 6 |
| C3 add-leg stop at entry | KX | 4,912 | +0.741 | +154 [−418, +662] | +0.018 [−0.042, +0.074] | −287 | −1,277 | +354 (4) | −200 (1) | 2,579 | 0 of 6 |
| C4 PX far target | PX | 1,003 | +0.230 | +812 [−545, +1,993] | +0.197 [−0.109, +0.467] | −162 | −658 | 0 (0) | −716 (4) | 544 | 2 of 3 |
| *D1 drift probe* | KX | 23,895 | +3.184 | +19,137 [+4,741, +36,206] | +2.462 [+0.593, +4.744] | −379 | −1,084 | +238 (1) | −5,532 (11) | 4,929 | 2 of 6 |
| *D3 stall → exit now* | KX | 4,938 | +0.742 | +179 [−2,306, +2,387] | +0.020 [−0.253, +0.262] | −218 | −1,307 | +1,987 (8) | −1,808 (5) | 2,579 | 0 of 6 |
| *D4 no progress at 15 min → exit* | KX | 4,792 | +0.707 | +34 [−1,424, +1,162] | −0.016 [−0.215, +0.133] | −379 | −921 | +858 (10) | −824 (2) | 2,579 | 0 of 6 |
| *D4b unconditional 15-min exit* | KX | 2,609 | +0.400 | −2,149 [−4,893, +713] | −0.323 [−0.657, +0.007] | −283 | −1,160 | +2,086 (13) | −4,235 (18) | 1,764 | 4 of 6 |

Stage B on the holdout: P0 $4,945; C1 +$1,196; C2 +$435; C3 +$154; C4 +$813; D1 +$21,469.

## Reading the two tables together

- **The stall decision (C1 and D3) flips sign between development and holdout** and the holdout CIs span roughly ±1R per stall trade on 13 trades. Neither "tighten" nor "exit" is distinguishable from "hold" at this sample. Development evidence (60 stall trades) favours holding by 0.35R per stall trade for breakeven and 0.53R for exit-now, with the breakeven CI reaching +0.11R.
- **C2 and C3 change very few trades** (21 and 19 of 240 in development; 1 and 5 of 60 on the holdout). Their P&L effect is within ±0.07R per entry in every CI. C2 buys a tail reduction in development (P(R < −0.5R) on its conditioned set 0.24 → 0.06, worst-decile mean −2.01R → −0.56R) at a cost indistinguishable from zero; on the holdout it changed one trade.
- **C4 replicates in sign on the holdout** (+0.20R per PX entry) but its CI includes zero at 28 trades, and both S3 and S6 showed the development gain is explained by the generator's post-entry drift (the no-target probe D2 beats it: +0.88R development, +0.59R holdout). It cuts 2 of the 3 largest holdout winners.
- **D1 confirms the drift artefact**: +$19k on a $4.8k holdout base, as predicted in the pre-registration. It is not a candidate.
- The fill-assumption grid (`fillgrid_*.csv`) shows every candidate's Δ$ unchanged to within $350 under touch vs penetration, 0–2 ticks of slippage, and same-bar ordering; no policy's stop and target ever shared a bar.
