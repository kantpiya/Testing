# A5 — Volatility normalization and position sizing

Panel 2026-11-05 · A5 · Inputs: common brief only; no data, code, logs or studies available (OBSERVED, brief §1). Strategy details are USER-SUPPLIED CONTEXT (unverified). All numbers are SYNTHETIC unless labelled otherwise. Scripts and raw output: `/tmp/claude-0/-home-user-Testing/7cf3ca0b-ccdf-5806-aa57-684759b9781e/scratchpad/A5/` (`sim_vol_sizing.py`, `sim_output.txt`, `sim_output_C.txt`).

## 1. Strongest finding or proposal, and the decision it would change

HYPOTHESIS (supported by the synthetic model): "two micros when calm" bundles three claims — (a) calm entries have a better edge, (b) stops sized from a compressed ATR are correct, (c) more size on calm entries improves risk-adjusted return. In the simulation (c) is false even with a real edge, for a mechanical reason: if the edge scales with volatility (follow-through in points ∝ ATR) while commissions and slippage do not, *dollar* expectancy per contract on quiet entries is the lowest of any regime. Doubling size there doubles the weakest trades. SYNTHETIC: CALM2 raised net P&L 10% over FIX1 but raised max drawdown 46% and lowered per-trade Sharpe (0.101 → 0.095).

The one normalized-vol use that improved risk-adjusted return in the model was **stop placement**: when quiet, size the stop from the minute-of-day *baseline* ATR rather than the compressed current ATR (CALM2+R: Sharpe 0.117, net P&L +73% vs FIX1, drawdown +30%). The decision this changes: do not implement calm size-up as a sizing rule; test it as a stop-placement rule first, and test entry selection and sizing separately with the specs in §3.

## 2. Evidence (with labels) and the strongest competing explanation

- OBSERVED: no user data. Nothing here is evidence about the user's strategies.
- EXTERNALLY SUPPORTED (general knowledge; verify): intraday equity-index volatility is U-shaped by minute-of-day, so raw ATR mixes time-of-day with regime; volatility clusters, and compression is often followed by expansion whose direction is not predictable from compression alone.
- SYNTHETIC (table below): three scenarios differing only in how expansion relates to quiet entries. Across all three, (i) quiet-entry trades have the lowest $/contract, (ii) quiet-then-expansion trades are worse than quiet-no-expansion trades (stop-hit rate 55.8% → 58.7% symmetric; → 62.0% with an adverse jump; per-contract mean $1.44 → $0.89 → −$1.05), (iii) CALM2 raises the share of total losses borne by quiet-then-expansion trades from ~10% to ~16%, and RISK$ (fixed-dollar risk) does the same because it also sizes up when the stop is small.

Strongest competing explanation: in real data the calm edge may *not* scale with ATR — e.g. a weak-reversal setup may produce a fixed point follow-through regardless of regime, in which case quiet entries have higher $/contract and size-up is right. That is exactly the quantity test (1) in §3 measures; the synthetic model assumes the unfavorable case, so treat it as a stress test, not a prediction.

## 3. Worked example / reproducible check / formula / data spec

**Normalized ATR (definition).** 1-minute bars; `TR_t = max(H−L, |H−C_{t−1}|, |L−C_{t−1}|)`; `ATR14_t = mean(TR_{t−13..t})` (or Wilder). Baseline `B(m, d) = median{ATR14 at minute-of-day m on sessions d−20 … d−1}` (20 prior sessions, same minute, current session excluded). `nATR_t = ATR14_t / B(m(t), d)`. Quiet := `nATR_t < 0.70` (threshold to be tuned once, out-of-sample). Known at the close of bar t; usable for an order at the open of bar t+1.

**Earliest availability.** Baseline: needs 20 completed prior sessions, so after a 20-session warm-up it is always available at 09:30. Current ATR14: if bars are continuous Globex, available at 09:30:00 (uses 09:16–09:29 pre-open bars, which measure pre-open volatility, not RTH volatility); if RTH-only bars, earliest 09:44:00. Recommend computing B separately for the first 15 RTH minutes from Globex bars and flag the 09:30–09:44 window. Decide in advance whether CPI/NFP/FOMC sessions enter the baseline; the 08:30 release contaminates B for minutes 09:30–10:00 if they do.

**Three experiment specs (one per hypothesis).**

- (1) Entry selection. Unit: eligible signal of one strategy slot. Baseline: all eligible signals, unfiltered. Metric: net $ per signal and per session by nATR quintile, plus $/contract and R-multiple. Fails if: no monotone relation across quintiles; or Σ net$(retained) − Σ net$(discarded) ≤ 0 after costs; or not stable under session-level block bootstrap.
- (2) Stop placement. Unit: executed trade. Baseline: stop = k·ATR14_raw. Metric: expectancy per $ risked; fraction of stopped trades whose MFE later reached target; stop-hit rate split quiet/expanded. Fails if: stop = k·max(ATR14, B) on quiet entries does not raise expectancy per $ risked, or target-hit rate falls more than stop-hit rate.
- (3) Position size. Unit: trading session (daily P&L), because quiet trades cluster within days. Baseline: 1 MNQ fixed. Metric: net $ / max DD, daily Sharpe, share of losses on quiet-then-expansion days. Fails if: net$/maxDD below FIX1; drawdown grows faster than P&L; or 95th-percentile daily loss exceeds the account's daily-loss limit.

**SYNTHETIC sizing comparison** (40,000 trades, $2/pt, $2.50 RT cost/contract, stop 1.5×ATR14, target 2×stop, 30-min time stop, drift edge +0.04σ/min; expansion = σ×2.5 from a random minute; scenario A: P(expand|quiet)=0.35 vs 0.10; B: 0.15 flat; C: as A plus a 3σ jump, adverse 65% of the time):

```
Scen  Policy    netPnL$  Sharpe  maxDD$  avgCtr  %losses on quiet-then-expansion  Q&X $/trade
A     FIX1      206,836  0.101   1,778   1.00     9.8%                             0.89
A     RISK$     422,142  0.093   4,918   3.03    14.5%                             2.82
A     CALM2     227,616  0.095   2,604   1.42    15.5%                             1.79
A     CALM2+R   357,009  0.117   2,315   1.42    22.1%                             9.13
B     FIX1      209,603  0.102   1,658   1.00     4.2%                             0.49
B     CALM2     234,526  0.098   2,311   1.42     6.6%                             0.97
C     FIX1      186,641  0.091   1,455   1.00    10.3%                            -1.05
C     RISK$     362,172  0.080   4,525   3.03    15.2%                            -4.48
C     CALM2     196,104  0.082   2,212   1.42    16.2%                            -2.10
C     CALM2+R   293,868  0.097   2,495   1.42    23.6%                            -0.18
```

Quiet entry then expansion: the stop was sized to a compressed ATR, so a 2.5×σ shock reaches it within a few bars, stop slippage scales with the shock, and the orderly drift edge is swamped. Per contract (scenario C) win rate falls 42.8% → 37.9% and mean from +$1.44 to −$1.05. CALM2 holds 2 contracts on exactly these trades, RISK$ ~3. Under CALM2+R they become roughly break-even once the stop is sized to baseline ATR: the damage is a stop-placement problem, not a sizing opportunity.

## 4. When following this proposal would make the decision worse

- If the user's calm-entry edge is in fixed points (not ATR-scaled), quiet entries have the *best* $/contract and the "do not size up" conclusion inverts. Test (1) decides this.
- Widening quiet stops to baseline ATR (CALM2+R) increases $ risk per trade; under a prop-firm daily-loss or trailing-drawdown rule this can breach limits on expansion days even though long-run Sharpe is higher. Account constraints must be applied after test (3), per session.
- RISK$ with a 1-contract floor silently becomes "size up only when stops are tight", i.e. CALM2 with a different threshold; comparing the two is not a clean test.

## 5. Cheapest decisive test, and the result that would retire the idea

From the executed-trade log alone: compute nATR at entry for every trade; report $/contract and R-multiple by nATR quintile, with MAE/MFE. If the lowest quintile's $/contract is not at least that of the middle quintiles (session bootstrap, 95% CI excluding zero), retire "two micros when calm" as a sizing rule; if it is, proceed to test (3). Separately, if baseline-ATR stops on quiet trades do not raise expectancy per $ risked in test (2), retire the stop variant too.

## 6. Missing inputs that materially limit the conclusion

OBSERVED missing: 1-min bars with session timestamps; the executed-trade log with entry time, stop size, fills and slippage; the eligible/rejected-signal log (test 1's denominator); strategy definitions (is follow-through ATR-scaled?); account drawdown/daily-loss rules; the user's ATR variant and bar size. Without the signal log, test (1) runs only on executed trades and conditions on existing filters.

## 7. Filter accounting (for the entry-selection use, nATR < θ as a filter)

| Quantity | How to compute |
|---|---|
| Eligible signals | all signals of the slot in the eligible/rejected log, per session |
| Trades retained | eligible signals with nATR_entry < θ (or ≥ θ, for the inverse filter) |
| Losses avoided | Σ net $ of discarded signals with net $ < 0, at the policy's contract count |
| Winners discarded | Σ net $ of discarded signals with net $ > 0 |
| Net change after costs | Σ net$(retained) − Σ net$(all eligible), costs at $2.50 RT per contract plus measured slippage |
| Independent trading sessions | count of sessions with ≥1 eligible signal; block bootstrap by session |
| Portfolio contribution | change in the portfolio daily P&L Sharpe and max DD when this slot's filtered P&L replaces its unfiltered P&L, all other slots unchanged |
