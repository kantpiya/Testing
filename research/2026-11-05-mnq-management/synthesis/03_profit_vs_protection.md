# Profit versus protection — every tighter exit examined (SYNTHETIC data)

For each policy that exits earlier or tightens the stop relative to the original bracket: dollars of losing trades avoided (trades that lost under P0 and lost less or won under the challenger), dollars surrendered on trades that later recovered (trades that won under P0 and did worse under the challenger), incremental costs, and the net after costs. Paired on identical entries, reference fill model, costs on every fill. Source: `src/director/out/per_trade_{development,holdout}.csv`.

**Incremental costs.** Every policy here closes each leg exactly once, so the commission count is identical to P0 ($0 incremental). The only cost difference is fill type: a breakeven stop fills at stop − 1 tick while the target it replaces is a limit at 0 slippage; a rule exit fills at the next open − 1 tick. That slippage is inside the net figures, and the fill grid shows that 0–2 ticks move no result by more than $350. C4 is listed last for completeness; it is a looser policy and buys nothing in protection.

## Development set (240 KX trades / 240 sessions; 92 PX / 92)

| Tighter exit | Trades changed | Losing trades avoided $ (n) | Surrendered on recovered winners $ (n) | Incremental commission $ | Net difference $ | Net per entry R | Five sessions contributing most (signed Δ$) |
|---|---|---|---|---|---|---|---|
| C1 stall → breakeven | 53 | +5,543 (31) | −8,943 (22) | 0 | **−3,400** | −0.086 | 2025-06-11 −603; 2026-02-26 −582; 2026-03-19 −576; 2026-02-12 −520; 2025-11-06 −510 (largest gains: 2025-09-17 +262; 2026-02-11 +249) |
| C2 late profit-conditional BE | 21 | +2,676 (15) | −2,555 (6) | 0 | **+121** | +0.010 | 2026-02-26 −582; 2026-03-19 −576; 2025-10-16 −426; 2025-05-09 −356; 2025-08-20 −347 (largest gains: 2026-02-11 +258; 2026-03-24 +250) |
| C3 add-leg stop at entry | 19 | +888 (11) | −1,208 (8) | 0 | **−320** | −0.006 | 2025-06-11 −199; 2026-03-19 −192; 2025-11-06 −169; 2026-02-26 −146; 2025-06-18 −146 (largest gains: 2025-07-17 +120; 2026-04-08 +120) |
| D3 stall → exit now | 60 | +6,414 (31) | −11,084 (29) | 0 | **−4,669** | −0.133 | 2025-06-11 −603; 2026-02-26 −572; 2026-03-19 −561; 2026-03-05 −516; 2025-11-06 −510 |
| D4 no progress at 15 min → exit | 43 | +2,642 (29) | −5,514 (14) | 0 | **−2,871** | −0.079 | 2026-03-19 −634; 2025-11-06 −522; 2025-11-26 −465; 2025-12-15 −462; 2025-06-18 −448 |
| D4b unconditional 15-min exit | 127 | +8,127 (50) | −20,142 (77) | 0 | **−12,015** | −0.328 | 2026-03-19 −634; 2025-06-11 −562; 2025-11-06 −522; 2025-11-26 −465; 2025-12-15 −462 |
| *C4 PX far target (looser)* | 64 | 0 (0) | −1,183 (5 winners that stopped out after passing the midpoint) | 0 | **+5,462** (from 59 winners improved) | +0.396 | 2025-05-15 −349; 2025-09-17 −270; 2025-08-29 −256; 2026-04-06 −232 (gains spread: largest 2026-04-08 +207) |

The same handful of sessions (2025-06-11, 2025-11-06, 2026-02-26, 2026-03-19) dominate the cost of every KX tightening rule: each is a trade that stalled or retraced early and then ran to a 2–2.5R target. The protective side is spread thinly across many sessions (≈ $180 per avoided loser for C1), which is why no tightening rule wins on net in development.

## Sealed holdout (60 KX trades / 60 sessions; 28 PX / 28)

| Tighter exit | Trades changed | Losing trades avoided $ (n) | Surrendered on recovered winners $ (n) | Incremental commission $ | Net difference $ | Net per entry R | Five sessions contributing most (signed Δ$) |
|---|---|---|---|---|---|---|---|
| C1 stall → breakeven | 10 | +1,562 (8) | −696 (2) | 0 | **+866** | +0.098 | 2026-06-26 −660; 2026-05-26 +274; 2026-05-08 +254; 2026-07-13 +240; 2026-05-06 +238 |
| C2 late profit-conditional BE | 1 | +274 (1) | 0 (0) | 0 | **+274** | +0.025 | 2026-05-26 +274 (only session) |
| C3 add-leg stop at entry | 5 | +354 (4) | −200 (1) | 0 | **+154** | +0.018 | 2026-06-26 −200; 2026-07-13 +120; 2026-05-26 +92; 2026-05-06 +80; 2026-05-08 +64 |
| D3 stall → exit now | 13 | +1,987 (8) | −1,808 (5) | 0 | **+179** | +0.020 | 2026-06-26 +660; 2026-05-01 +516; 2026-07-13 +394; 2026-06-01 +380; 2026-05-26 +350 |
| D4 no progress at 15 min → exit | 12 | +858 (10) | −824 (2) | 0 | **+34** | −0.016 | 2026-05-28 +484; 2026-06-24 +340; 2026-06-08 +170; 2026-05-08 +106; 2026-05-13 +95 |
| D4b unconditional 15-min exit | 31 | +2,086 (13) | −4,235 (18) | 0 | **−2,149** | −0.323 | 2026-05-06 −596; 2026-05-26 −507; 2026-05-28 −484; 2026-05-01 −446; 2026-07-06 −418 |
| *C4 PX far target (looser)* | 16 | 0 (0) | −716 (4) | 0 | **+812** | +0.197 | 2026-06-04 −362; 2026-07-17 −272; 2026-07-28 +282; 2026-06-12 +159; 2026-05-20 +148 |

On the holdout the stall rules are carried by a single session, 2026-06-26, which contributes −$660 to C1 and +$660 to D3 (the one stall trade that recovered to target after breakeven would have stopped it... and the one that exit-now caught before a full loss). With 13 stall trades, one session is 76% of C1's net. This is the concrete reason the holdout cannot settle the stall question.

## What the two periods agree on

1. Unconditional time exits at 15 minutes lose in both periods, on both the P&L and the largest-winner count. Time alone is not the driver.
2. Setup matters only in one direction: the breakout-style no-progress rule has a negative or null effect on breakouts and a negative effect on reversals (S3: all 13 variants ≤ 0). Reversals do not need their own tightening rule; they need to be excluded from the breakout one.
3. The protective rules that change few trades (C2, C3) cost nothing measurable in either period; their value is tail reduction, which only development had enough trades to show.
