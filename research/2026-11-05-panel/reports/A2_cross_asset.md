# A2 — Nasdaq Index and Cross-Asset Strategist

**Question:** When might rates, broad equity participation, or concentrated Nasdaq leadership explain an NQ move in a way that changes strategy selection?

**Workspace status (OBSERVED):** No bars, logs, strategy code, or study reports exist in the container (confirmed by the common brief, section 1). Nothing below is backed by the user's data. Instrument facts are public (verify against CME specs). Everything else is HYPOTHESIS or SYNTHETIC EXAMPLE.

## 1. Strongest finding or proposal, and the decision it would change

**Proposal (HYPOTHESIS):** Treat the *source* of an NQ move as a gate on which strategy slot is eligible, not as a new entry signal. The same 40-point NQ rally at 10:05 ET admits three causal stories, and only one of them (concentrated mega-cap leadership) is cheaply distinguishable at entry from a futures-only feed. The decision it changes: whether a continuation slot (KX/PX-type breakouts, if those are continuation strategies — definitions unverified) or a fade slot (weak reversal / sell-off recovery) is eligible on that bar.

**Strong simple baseline first:** a rule that conditions only on NQ's own 5/15/30-minute returns and minute-of-day. Any cross-asset factor must beat that baseline *after* the baseline is partialled out (section 3). Most cross-asset "context" fails this test because it is a linear recombination of NQ's own return.

## 2. Evidence (with labels) and the strongest competing explanation

Three competing explanations for the same move (all HYPOTHESIS; the observable signatures are what I would expect from market structure, not from inspected data):

| Explanation | Mechanism | ES vs NQ | ZN (10y) | RTY | Breadth / leaders | VIX / VXN |
|---|---|---|---|---|---|---|
| **A. Rates relief** | Yields fall; long-duration growth rerates | NQ > ES, both up | ZN up sharply, *leading* NQ by 0–2 min | Up (rate-sensitive small caps) | Broad; leaders in line with index | Both fall |
| **B. Broad risk-on** | Common equity factor (flows, macro headline, squeeze) | NQ ≈ ES in beta-adjusted terms (NQ/ES ratio flat) | Flat or slightly down | Up, often > NQ | Broad advance; leaders not special | VIX falls more than VXN |
| **C. Concentrated leadership** | One or two mega-caps (news, options gamma, block) | NQ ≫ ES; ratio jumps | Flat | Flat or down | Narrow: 1–2 names explain most of NDX move; equal-weight NDX lags | VXN falls, VIX flat or VXN/VIX spread widens |

**Strongest competing explanation to the whole framework:** the move's source does not matter for a 5–30-minute horizon; what matters is magnitude relative to session-adjusted volatility and whether the move is an impulse or a reversion of a prior impulse. Under this view the cross-asset columns are noise plus collinearity, and the correct response is to stop at the baseline. I consider this the default until the test in section 5 rejects it.

**Availability at entry (public, verify with your data vendor):**

- *Typical CME futures feed (Rithmic/CQG/Tradovate-style):* ES, NQ, RTY, YM, ZN/ZB, micros, and VX (CFE, often a separate subscription). Supports ES/NQ ratio, RTY vs NQ, ZN direction, and a front-month VIX proxy if VX is enabled.
- *Needs an equity feed:* mega-cap prints (NVDA, AAPL, MSFT, etc.), equal-weight NDX proxies, TICK/ADD breadth, NDX cash.
- *Needs an options/index feed:* VIX and VXN cash (CBOE). VXN is rarely in a futures-only setup.
- Latency is immaterial at a 5-minute cadence; the question is whether the field exists at bar close.

For a futures-only trader, B and C collapse into one observable: **ES return conditional on NQ return** (equivalently the NQ/ES log-ratio change). A is partly observable via ZN. Breadth and leader concentration require an equity feed: buy it or drop them.

## 3. Worked example / reproducible check / formula / data spec

**Collinearity trap (OBSERVED, in a SYNTHETIC simulation I ran):** I generated 20,000 five-minute bars where NQ = common factor + Nasdaq-specific factor − 0.3×rates, ES = common factor − 0.1×rates, ZN = −rates, and forward 15-minute MNQ return continues *only* on the Nasdaq-specific factor. Regressions of forward return on candidates:

```
nq5 alone      coef=+0.0389 t=+4.38
ratio alone    coef=+0.1430 t=+8.45    # ratio = nq5 - es5
ratio | nq5    coef=+0.1478 t=+7.24
zn5 alone      coef=+0.0052 t=+0.48
zn5 | nq5      coef=-0.0070 t=-0.63
es5 | nq5      coef=-0.1478 t=-7.24    # identical test to "ratio | nq5", sign flipped
```

Three lessons (SYNTHETIC by construction, structurally general):

1. NQ's own return looks predictive (t=4.4) only because it carries the Nasdaq-specific component. A factor isolating that component survives partialling; a pure recombination would not.
2. "NQ/ES ratio given NQ" and "ES given NQ" are the *same* regressor. Never count them as two confirmations.
3. ZN adds nothing here because I built it that way; in real data it is the one factor with an independent driver (rates), so it is the likeliest to survive, *if* forward returns load on it, which is unknown.

**Test specification (real data):**

- Unit: each 5-minute RTH bar 09:35–15:55 ET; second run restricted to *eligible signal bars* per slot.
- Dependent: forward MNQ return at 15 and 30 min, points, winsorized at 1%.
- Controls (always): NQ 5/15/30-min returns, NQ 30-min range ÷ minute-of-day median range, 30-min time-of-day blocks.
- Candidates (singly, then jointly): ES, ZN, RTY 5-min returns; VX front-month change; with an equity feed, top-5 NDX constituent share of the 5-min NDX move and equal-weight-minus-cap-weight NDX return.
- Report coefficient, HAC t, incremental R² over controls, by year, clustered by day.
- Interaction: candidate × sign(NQ 5-min return); ES lagging an NQ rally and ES lagging an NQ sell-off need not be symmetric.

## 4. When following this proposal would make the decision worse

- **Event windows.** At 08:30 CPI/NFP and 14:00 FOMC every factor moves at once and the ZN lead is mechanical; the regression will show rates "explaining" NQ because both are co-caused. Exclude ±30 min around releases or treat them as a separate regime (that is the event-VWAP work, not this).
- **Rolls.** Ratios computed across mismatched front months, or during roll week, produce spurious jumps.
- **Regime drift.** NDX mega-cap concentration has changed across years; a leader rule fit on one regime will not transfer. Yearly stability is mandatory.
- **Search inflation.** Six candidates × two horizons × two signs × several slots is a Study-66-sized search. Pre-register one candidate per explanation and apply the user's shifted-calendar random-entry comparison.
- **Feed cost.** If the only survivor needs an equity/options subscription, net benefit must exceed the subscription plus the operational risk of a second data path.

## 5. Cheapest decisive test, and the result that would retire the idea

Run the section-3 regression with **only futures-feed candidates** (ES, ZN, RTY, VX) on all RTH bars first, then on eligible signal bars for each slot. **Retire the idea** if, after partialling NQ's own returns and session-ATR, no candidate has |t| > 3 with the same sign in at least 3 of 4 yearly subsamples and incremental R² ≥ 0.5% on the signal-bar subsample. Retire the *equity-feed* extension unless the futures-only candidates already show something, because breadth/leader proxies are mostly linear in ES-given-NQ anyway.

## 6. Missing inputs that materially limit the conclusion

- No bars exist in the workspace; nothing has been checked against real data.
- Strategy definitions (KX, PX, engulfing, weak reversal, sell-off recovery) are unknown, so I cannot say which slot is "continuation" vs "fade"; the gating map in section 1 is a placeholder.
- Logs must record, per signal: timestamp to the second, strategy slot, eligible/rejected flag and rejection reason, NQ/ES/ZN/RTY prices at the decision bar close, and the data source used. Without rejected signals, the "losses avoided" column is unestimable.
- Whether the user's feed carries VX, and whether any equity/index data exists.
- Contract roll convention used in the user's data.

## 7. Filter accounting (the seven quantities in rule 3)

Spec for a candidate gate G (e.g., "ES 5-min return given NQ below threshold → suppress continuation slot"):

- **Eligible signals:** slot signals on RTH bars with all inputs non-missing at bar close, by year.
- **Trades retained:** eligible signals where G passes.
- **Losses avoided:** sum of negative PnL (points × $2 MNQ) on signals G suppresses, at the slot's standard exit.
- **Winners discarded:** sum of positive PnL on signals G suppresses.
- **Net change after costs:** (losses avoided − winners discarded) + commission and slippage saved on suppressed trades (≥1 tick each side, $0.50 MNQ), by year.
- **Independent sessions:** distinct trading days with at least one G-affected signal; require ≥100 days and the same sign of net change in ≥3 yearly subsamples.
- **Portfolio contribution:** change in daily portfolio PnL mean and drawdown with G applied to the targeted slot only; report whether suppressed trades reappear in another slot (substitution) rather than disappearing.
