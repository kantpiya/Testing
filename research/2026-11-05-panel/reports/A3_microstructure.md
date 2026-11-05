# A3 — Futures Market Microstructure and Execution

**Question:** Could an apparently favorable market condition become uneconomic after spread, slippage, latency, and stop execution?
**Workspace status (OBSERVED):** no fills, bars, quotes, or depth data exist in the workspace; every number below is HYPOTHESIS (public, verify) or SYNTHETIC.

## 1. Strongest finding or proposal, and the decision it would change

HYPOTHESIS: the conditions that *look* most favorable in bar data — the opening five minutes and scheduled releases — are where execution cost is largest and asymmetric: the stop-market exit pays the worst slippage precisely when the trade is losing. An 8-point gross edge per MNQ trade survives ordinary RTH, is roughly halved at the open under conservative assumptions, and is negative at 08:30/14:00 under conservative assumptions. Decision changed: any strategy slot eligible in the first 5 minutes or within ±2 minutes of CPI/NFP/FOMC must be evaluated with regime-specific cost assumptions, not one blanket slippage number. Baseline: one conservative cost model per regime, applied to every backtest, beats any clever filter as a starting point.

## 2. Evidence (with labels) and the strongest competing explanation

- OBSERVED: nothing in the workspace; realized slippage is unmeasurable here.
- EXTERNALLY SUPPORTED (public, verify against CME specs; search result only): NQ $5/tick, MNQ $0.50/tick, both 0.25-point ticks; MNQ is 1/10 NQ notional. CME publishes depth/volume statistics; MNQ volume exceeds NQ in contract count but not in notional.
- HYPOTHESIS: in ordinary RTH the MNQ book is typically 1 tick wide with tens of contracts at the touch; NQ is 1 tick wide with single-digit to low-double-digit contracts. Market makers arbitrage the pair, so MNQ tracks NQ within ~1 tick at sub-second lag; the intraday basis is economically zero except in the first seconds after a release, when NQ reprices first and MNQ quotes are pulled or widen to several ticks.
- HYPOTHESIS: stop-market orders at releases fill at the next traded price, which after a 30–60-point NQ gap can be far from the trigger. Stop-limits avoid that but may never fill.
- Strongest competing explanation: the user's broker/routing may yield fills near my optimistic column (retail bridge ~100–300 ms; direct CME connection ~10 ms); only the user's fill log settles this. Second competitor: a slot that uses only limit entries and no stop-markets near events loses most of the cost asymmetry, at the price of missed fills (adverse selection: limits fill most reliably when price is about to go against you).

## 3. Worked example / reproducible check / formula / data spec

**Fill-assumption table (all rows HYPOTHESIS, public, verify with own fills).** Slippage in ticks beyond the touch; latency = signal-to-exchange-ack; values conservative / base / optimistic.

| Regime | Order | Spread (ticks) | Slippage (ticks) | Latency (ms) |
|---|---|---|---|---|
| RTH ordinary | Market entry | 1 / 1 / 1 | 2 / 1 / 0.5 | 300 / 100 / 20 |
| RTH ordinary | Limit entry | 1 / 1 / 1 | 0, but fill prob. 0.6 / 0.75 / 0.9 when touched | 300 / 100 / 20 |
| RTH ordinary | Stop-market | 1 / 1 / 1 | 4 / 2 / 1 | 300 / 100 / 20 |
| RTH ordinary | Target (limit) | 1 / 1 / 1 | requires trade-through 1 / 1 / 0 tick | n/a |
| Open 09:30–09:35 | Market entry | 2 / 1 / 1 | 6 / 3 / 1 | 500 / 150 / 30 |
| Open 09:30–09:35 | Limit entry | 2 / 1 / 1 | 0, fill prob. 0.5 / 0.7 / 0.85 | 500 / 150 / 30 |
| Open 09:30–09:35 | Stop-market | 2 / 1 / 1 | 12 / 6 / 2 | 500 / 150 / 30 |
| Open 09:30–09:35 | Target (limit) | 2 / 1 / 1 | trade-through 1 / 1 / 0 | n/a |
| Release 08:30/14:00 (±2 min) | Market entry | 6 / 3 / 2 | 20 / 8 / 3 | 1000 / 200 / 30 |
| Release 08:30/14:00 (±2 min) | Limit entry | 6 / 3 / 2 | 0, fill prob. 0.3 / 0.5 / 0.7 | 1000 / 200 / 30 |
| Release 08:30/14:00 (±2 min) | Stop-market | 6 / 3 / 2 | 40 / 15 / 5 | 1000 / 200 / 30 |
| Release 08:30/14:00 (±2 min) | Target (limit) | 6 / 3 / 2 | trade-through 2 / 1 / 1 | n/a |

**What each data class can support (HYPOTHESIS, standard backtest practice):**
- 1-minute OHLC: direction and magnitude only. Cannot resolve same-bar stop/target ambiguity (both inside one bar's range: order of touches unknown — resolve as stop-first and report the count of ambiguous bars). No spread; touch ≠ limit fill.
- Trades (time & sales): resolves intra-bar ordering, gives a true trade-through test for limit fills and realized paths for stop slippage. Still no spread.
- Quotes (BBO): adds spread and the side a market order hits; measures quote-pull episodes at releases. No queue position.
- Depth (L2/MBO): needed only for queue position and size beyond the touch. For 1–5 MNQ contracts, BBO plus trades is the economic minimum for a credible fill model.

**NQ signal, MNQ fill:** tick economics 10:1 ($5 vs $0.50). HYPOTHESIS: for 1–5 MNQ contracts, RTH depth is ample and the NQ–MNQ basis is within 1 tick, so signal-on-NQ/fill-on-MNQ is fine *if* the backtest fills at MNQ prices, not NQ. The lag matters at releases and in the first seconds of the open, when MNQ quotes are pulled; filling at the NQ print overstates MNQ fills there. MNQ is thin overnight (roughly 18:00–02:00 ET and around the 17:00 halt), in roll week, and inside the first second after a release.

**SYNTHETIC worked example** (script run in scratch; trade geometry p_win=0.5, target +30, stop −14 → gross +8 pts/trade; cost = half-spread + entry slippage + P(loss)×stop slippage + P(win)×target trade-through + $0.80–1.50 commission):

```
gross edge 8.0 pts = $16.00/contract
regime                case   cost pts  net pts   net $ edge kept
RTH ordinary          cons       2.00     6.00   12.00       75%
RTH ordinary          base       1.25     6.75   13.50       84%
RTH ordinary          opt        0.78     7.22   14.45       90%
Open 09:30-35         cons       4.12     3.88    7.75       48%
Open 09:30-35         base       2.25     5.75   11.50       72%
Open 09:30-35         opt        1.02     6.97   13.95       87%
Release 08:30/14:00   cons      11.75    -3.75   -7.50      -47%
Release 08:30/14:00   base       4.88     3.12    6.25       39%
Release 08:30/14:00   opt        2.15     5.85   11.70       73%
```

Reading: the same 8-point setup is worth $12–14 in RTH, $8–14 at the open, and −$7.50 to +$11.70 around releases. At releases the uncertainty exceeds the edge itself; it must be measured from the user's own fills, not tuned.

## 4. When following this proposal would make the decision worse

- If realized slippage in the user's fill log is near the optimistic column, the conservative column would wrongly retire a profitable open or release slot.
- If a slot's edge at the open is much larger than 8 points (plausible: largest ranges), conservative costs still leave it positive; cost must be compared with the slot's own edge, not a fixed 8.
- Replacing stop-market with stop-limit to avoid slippage converts a bounded loss into an unbounded one at a release gap; strictly worse.
- Over-conservative limit-fill probabilities (0.3) discard winners that would have filled; the balance is empirical.

## 5. Cheapest decisive test, and the result that would retire the idea

Test: from the user's executed-trade log, realized slippage = fill price − intended price (signal-bar close for market entries, trigger price for stops), in ticks, per order type, bucketed by regime (RTH ordinary / 09:30–09:35 / release ±2 min). Required fields: timestamp (ms), intended price, fill price, order type, side, instrument. Denominator: all filled orders per bucket. Metric: median and 90th-percentile slippage per bucket, weighted by order-type frequency to give net cost per trade. Retire the concern if the 90th-percentile cost in the open and release buckets is below 25% of the slot's gross edge; retire the slot if the median cost exceeds the gross edge. Minimum ~50 orders per bucket; fewer means report the range and keep the conservative column.

## 6. Missing inputs that materially limit the conclusion

Fill log (none); broker/routing latency (unknown); contracts per trade (table assumes 1–5 MNQ); server-side vs platform-side stops (the latter adds latency and disconnect risk); whether any slot trades inside release windows; whether backtests fill at NQ or MNQ prices; backtest bar resolution (1-minute OHLC requires reporting the same-bar ambiguity count). Instrument facts are "public, verify against CME specs."

## 7. Filter accounting (the seven quantities in rule 3)

Proposed filter: exclude or re-cost trades whose entry timestamp is within 09:30–09:35 or ±2 min of CPI/NFP/FOMC. Spec:
- Eligible signals: all signals per slot, with timestamp; count those inside each regime window.
- Trades retained: signals outside the windows (and, for the re-cost variant, all signals with regime-specific costs applied).
- Losses avoided: sum of net P&L of excluded trades that were net negative after regime-specific cost.
- Winners discarded: sum of net P&L of excluded trades that were net positive after regime-specific cost.
- Net change after costs: (winners discarded − losses avoided), sign-corrected, using the base column; report also under the conservative column.
- Independent trading sessions: distinct trading days containing excluded trades; one observation per day, since release-day trades are correlated.
- Contribution to the portfolio: change in daily portfolio P&L (mean, 5th percentile) with and without the filter across all slots sharing the windows; the portfolio figure, not the slot figure, decides.
