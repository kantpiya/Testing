# B5 — Prop-account risk and path simulation

**Question:** Could two policies with similar net P&L have materially different drawdown-breach or payout-eligibility outcomes?
**Short answer:** Yes, and the gap is dominated by the drawdown *type* and by the *data granularity* used to simulate it, not by net P&L. Simulator: `/tmp/claude-0/-home-user-Testing/7cf3ca0b-ccdf-5806-aa57-684759b9781e/scratchpad/B5/prop_sim.py`.

## 1. Strongest finding or proposal, and the decision it would change

SYNTHETIC (1000 shuffled paths, 40 trades, identical net +$1,000, HYPOTHETICAL $50K account: trailing/static max drawdown $1,000, daily loss limit $600, target $800, 50% best-day consistency, 5 min days, 4 trades/day):

- Policy X (34 wins of +$100, 6 losses of −$400) vs Policy Y (10 wins of +$400, 30 losses of −$100) breach at **51% vs 24%** under an EOD-trailing rule evaluated per trade, and at **83% vs 67%** under an intraday trailing-on-unrealized rule evaluated with MFE/MAE. Same net P&L, 2× difference in ruin.
- The same policy's breach probability moves from **12% to 51%** (X, EOD trailing) and from **4% to 67%** (Y, intraday rule) purely by changing the simulation granularity from daily closes to per-trade with excursions. This is larger than any policy effect.

**Decision changed:** account selection and sizing must be chosen *per policy* using a path simulator fed with per-trade (ideally intra-trade) P&L, not from the backtest's net P&L or daily equity curve. A policy that is better on expectancy can be worse for funding survival; the two should be scored separately (OBSERVED in the simulator output; HYPOTHESIS that this holds for the user's real strategies, since no trade logs exist — common brief §1).

## 2. Evidence (with labels) and the strongest competing explanation

**OBSERVED (simulator output, SYNTHETIC inputs):**

| Policy | DD type | Granularity | P(breach) | P(eligible by day 10) | Breach cause |
|---|---|---|---|---|---|
| X small wins/big loss | static | per-trade | 0.473 | 0.527 | DLL 462, DD 11 |
| X | EOD trailing | EOD close only | 0.118 | 0.882 | DD 118 |
| X | EOD trailing | per-trade | 0.506 | 0.494 | DLL 440, DD 66 |
| X | intraday on unrealized | per-trade + MFE/MAE | 0.826 | 0.174 | DLL-unreal 573, DD-unreal 253 |
| Y big wins/small losses | static | per-trade | 0.062 | 0.299 | DD 62 |
| Y | EOD trailing | EOD close only | 0.183 | 0.274 | DD 183 |
| Y | EOD trailing | per-trade | 0.236 | 0.265 | DD 236 |
| Y | intraday on unrealized | per-trade + MFE/MAE | 0.671 | 0.150 | DD-unreal 671 |

Mechanisms visible in the breach-cause column: X dies of the **daily loss limit** (two −$400 losses in one day = −$800 > $600), which a daily-close simulation under-counts because the day's other trades mask the intraday trough. Y dies of the **trailing drawdown ratchet**: each +$400 winner (plus its MFE) lifts the high-water mark, so a subsequent run of −$100 losses hits the threshold even though cumulative P&L is still positive. Under the unrealized rule, Y's MFE on winners raises the mark *without being banked*, which is why Y jumps from 24% to 67%.

Y also has lower payout eligibility (≈27–30% vs ≈50–90% for X when X survives) because the consistency rule (best day ≤ 50% of profit) is often violated when one day holds two +$400 trades. Both policies reach the target in median 6–7 trading days when eligible.

**EXTERNALLY SUPPORTED — search result only (2026-11-05; pages not opened, fetch blocked):**
- Topstep 50K Trading Combine, per third-party summaries: $3,000 profit target, $2,000 maximum loss limit, $1,000 daily loss limit; consistency objective "best day < 50% of total profit"; DLL reportedly not a violation on some platforms and absent on TopstepX after Aug 2024. Sources disagree whether the maximum loss limit trails EOD or intraday. https://blog.traderspost.io/article/how-to-get-funded-with-topstep ; https://intercom.help/topstep-llc/en/articles/8284099-topstep-program-overview-glossary (official help center, not opened) ; https://proptradingvibes.com/blog/topstep-consistency-rule
- Apex Trader Funding, per third-party summaries: both EOD-trailing and intraday ("rises with unrealized profits, never falls back") products; a 30% rule described inconsistently (open-loss cap vs consistency cap); 50% consistency stated to apply only at Performance-Account payout; payouts every 5 trading days / 5 profitable days required. https://blog.traderspost.io/article/apex-trader-funding-payout-rules-what-prop-traders-must-know ; https://proptradingvibes.com/blog/apex-trader-funding-rules-overview ; https://topstepbrokerage.com/blog/topstep-vs-apex

Because sources conflict on the single parameter that matters most (EOD vs intraday trailing), **no firm row in the model below is marked verified**.

**Strongest competing explanation:** the policy gap is an artifact of my synthetic loss sizes relative to the hypothetical limits (−$400 ≈ 67% of DLL; +$400 ≈ 40% of DD). With real limits (e.g., $1,000 DLL / $2,000 DD) and real MNQ trade sizes the ordering could reverse. The granularity effect, however, is structural: daily closes cannot contain the intraday extremes, so it cannot be an artifact.

## 3. Worked example / reproducible check / formula / data spec

**Account-state model** (fields as requested; populated rows are HYPOTHETICAL unless noted):

| Firm | Product | Stage | Rule | Parameter | Effective | Source | Label |
|---|---|---|---|---|---|---|---|
| HYPOTHETICAL_FIRM | 50K | evaluation | drawdown_type | static / eod_trailing / intraday_trailing_unrealized | n/a | n/a | HYPOTHETICAL |
| HYPOTHETICAL_FIRM | 50K | evaluation | max_drawdown | 1,000 | n/a | n/a | HYPOTHETICAL |
| HYPOTHETICAL_FIRM | 50K | evaluation | daily_loss_limit | 600 | n/a | n/a | HYPOTHETICAL |
| HYPOTHETICAL_FIRM | 50K | evaluation | profit_target | 800 | n/a | n/a | HYPOTHETICAL |
| HYPOTHETICAL_FIRM | 50K | evaluation | consistency_max_day_share | 0.50 | n/a | n/a | HYPOTHETICAL |
| HYPOTHETICAL_FIRM | 50K | funded | min_trading_days | 5 | n/a | n/a | HYPOTHETICAL |
| HYPOTHETICAL_FIRM | 50K | funded | payout_buffer | 100 | n/a | n/a | HYPOTHETICAL |
| Topstep | 50K Combine | evaluation | profit_target / max_loss / DLL | 3,000 / 2,000 / 1,000 | unknown | traderspost.io (see §2) | EXTERNALLY SUPPORTED, search result only, unverified |
| Apex | 50K | funded (PA) | consistency / payout cadence | 50% / every 5 days | unknown | traderspost.io (see §2) | EXTERNALLY SUPPORTED, search result only, unverified |

Breach logic (per trade i on day d, balance B, high-water mark H, threshold T):
- static: T = start − DD.
- EOD trailing: at each EOD, H = max(H, B); T = max(T, H − DD). Breach if B < T at any trade close.
- intraday on unrealized: before trade i, H = max(H, B + MFE_i); T = max(T, H − DD). Breach if B + MAE_i < T, or daily P&L + MAE_i < −DLL.
- Eligibility at EOD d: d ≥ min_days, profit ≥ max(target, buffer), best_day/profit ≤ consistency.

**When EOD data are inadequate (precise statement):** a rule is EOD-simulable only if every quantity it references is a function of daily closes. Static DD and EOD-trailing DD *thresholds* are; but the *breach test* for any rule that fires intraday (DLL, any trailing DD checked in real time) needs the intra-day minimum of realized balance, which requires per-trade closes in time order. Any rule whose high-water mark or breach test includes *unrealized* P&L (Apex-style intraday trailing, Topstep's net-P&L including unrealized per the search summary) requires per-trade MFE and MAE at minimum, and strictly the tick path of unrealized equity when several positions overlap (pyramiding, multiple strategy slots): MFE/MAE per trade do not compose into the portfolio's unrealized path. The simulator shows the error direction: EOD-only simulation **under-states** breach by 4–15× here.

## 4. When following this proposal would make the decision worse

- If the user's real losses are small relative to the firm's DLL (e.g., −$100 on a $1,000 DLL), the X-vs-Y asymmetry collapses and account choice should follow fees/payout terms instead.
- If simulation uses unverified rule parameters (as here), it will rank accounts by my guesses. Ranking is only safe after primary-source confirmation.
- Over-fitting trade ordering: shuffling trades assumes exchangeability; real losses cluster (regime days), which raises breach probability for both policies and may change the ranking.

## 5. Cheapest decisive test, and the result that would retire the idea

Take the user's real per-trade log (entry/exit time, realized P&L, MFE, MAE) for each strategy slot; run the simulator with the firm's confirmed parameters under both DD types; compare P(breach) and P(eligible) across slots that have similar net P&L. **Retire** the proposal if, across slots, P(breach) differences are < 5 percentage points *and* the EOD-only and per-trade estimates agree within 5 points; then daily equity curves suffice and account mechanics can be ignored in strategy selection.

## 6. Missing inputs that materially limit the conclusion

- No trade logs; logs must contain per-trade timestamps, realized P&L net of fees, MFE, MAE, and overlapping-position flags (brief §1). Without MFE/MAE the intraday rule cannot be simulated.
- No verified firm parameters; need official rule pages (drawdown type, whether DLL is a violation, whether unrealized P&L counts, buffer and payout cadence, effective dates).
- Contract count per trade (sizing proposals in brief §2 change $ excursions directly).
- Whether evaluation and funded stages have different drawdown types (Apex search summary suggests yes).

## 7. Filter accounting (spec)

This is an account-selection decision, not a signal filter, so the quantities map as follows:
- Eligible signals: all trades the strategy would take (account rules do not change signals).
- Trades retained: trades executed before a breach; after breach, zero (account dead).
- Losses avoided: none directly; a lockout after DLL avoids the day's remaining trades (count them).
- Winners discarded: trades after breach/lockout that would have won; in the simulation X forfeits its remaining +$100 trades in 51–83% of paths.
- Net change after costs: expected realized P&L conditional on survival minus evaluation fee and reset fees (fees unknown).
- Independent trading sessions: 10 synthetic days; real test needs ≥ 100 days to estimate a 5-point breach difference.
- Contribution to portfolio: P(payout) × expected payout, per policy, per account type — the quantity the simulator reports as P(eligible).

(Word count ≈ 1,150.)
