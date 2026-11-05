# A4 — Intraday Auction and Price-Action Researcher

**Question:** At the instant of decision, can we distinguish acceptance outside a range, failed breakout, directional expansion, and rotation?

**Short answer (HYPOTHESIS):** Not at the instant of the break itself; the four states are defined by what happens *after* the level is crossed, so any measurement is a lagged, partial read. What can be done at decision time is (i) measure the pre-break path shape (rotation vs expansion), and (ii) commit to a versioned break/follow-through definition so that definition changes show up as denominator changes, not as "results".

## 1. Strongest finding or proposal, and the decision it would change

**Proposal:** Replace the single word "chop" with four versioned, denominator-explicit quantities, and compute them for every eligible signal, not only for executed trades. The decision it changes: whether Study 71's "changing the break definition changed the event count" is a finding about the market or an artifact of the denominator. In my SYNTHETIC run (Section 3), a stricter break definition cut breaks per session by 4x and raised follow-through per break from 2.6% to 11.2%, while follow-through per *session* barely moved (0.44 vs 0.47). If the user's Study 71 shows the same pattern, the "chop" result is mostly a per-break denominator effect and should not change any trading rule.

## 2. Evidence (with labels) and the strongest competing explanation

- **OBSERVED:** Workspace has no bars, logs, or Study 71 files (brief §1). Nothing below is a data result.
- **USER-SUPPLIED CONTEXT (unverified):** "chop" = poor follow-through after an entry; event count was sensitive to break definition.
- **EXTERNALLY SUPPORTED (general knowledge, no page opened):** Kaufman's efficiency ratio (|net move| / sum of |bar moves|) is a standard, lookback-explicit measure of directional vs oscillatory movement. Market-profile vocabulary ("acceptance" = time spent beyond a level; "failed auction" = rapid return inside) is descriptive, not formally tested.
- **HYPOTHESIS:** Four measurements below separate the four states only after a lag of n bars; the trade-off is confirmation vs entry price.
- **Strongest competing explanation:** Follow-through rates per break are mechanically tied to how many breaks a definition generates. A loose definition fires on noise crossings; each has low follow-through; the ratio collapses. No market behaviour needed to explain the Study 71 observation.

## 3. Worked example / reproducible check / formula / data spec

**Candidate measurements** (W = reference range width, e.g. opening-range width or session-adjusted ATR; L = break level; d = +1/−1 direction; bars are 1-minute).

| # | Name | Formula | Lookback / earliest availability | Separates | Path A vs Path B (closes relative to L, W=10) |
|---|---|---|---|---|---|
| M1 | Hold fraction | share of closes in bars [t+1, t+n] with d·(close−L) > 0 | n=5; 5 min after break bar | acceptance vs failed break | A: +1,+2,+2,+3,+3 → 1.0 (acceptance). B: +1,+2,−1,−2,−1 → 0.4 (failed). Identical at bar t. |
| M2 | Path efficiency (ER) | \|close_t − close_{t−n}\| / Σ\|close_i − close_{i−1}\| | n=10; 10 min after open (pre-break, usable at decision) | expansion vs rotation | A: ten bars +2 each → net 20, path 20, ER 1.0. B: +6,−4,+6,−4,+6,−4,+6,−4,+6,−4 → net 10, path 50, ER 0.2. Both "up" at decision. |
| M3 | Excursion asymmetry | MFE_K / max(MAE_K, 1 tick), MFE/MAE measured from L over K bars | K=10; 10 min after break | directional expansion vs rotation around L | A: +3,+6,+8,+9,+10 (MFE 10, MAE 0). B: +3,−3,+4,−4,+3 (MFE 4, MAE 4 → ratio 1). Same first bar. |
| M4 | Crossing count | number of sign changes of (close−L) in bars [t−n, t+n] | n=5 each side; 5 min after break | rotation vs acceptance | A: −2,−1,+1,+2,+3,+3,+4 → 1 crossing. B: −1,+1,−1,+1,−1,+1,+2 → 5 crossings. Same last close. |

Only M2 is available *at* the decision instant; M1, M3, M4 require waiting n bars and therefore cost entry price (Section 4).

**Versioned definition template** (HYPOTHESIS; fill once, change by version only):

- BREAK v\<major.minor\>: level_source {OR high/low | prior-session high/low | IB | custom}; level_lookback \<bars or clock window\>; trigger {touch | 1 close | n closes}; threshold \<ticks | fraction of W\>; re_arm {never per side | after close back inside by \<fraction W\>}; session_window \<ET start–end\>; instrument.
- FOLLOW_THROUGH v\<major.minor\>: horizon K \<bars\>; target L + d·\<multiple\>·W; fail L − d·\<fraction\>·W; resolution = first hit of target (FT) or fail (FAILED), neither = UNRESOLVED.
- DENOMINATORS (always all): sessions; sessions_with_break; breaks per session; eligible_signals (strategy triggers inside a break episode); trades_retained; FT, FAILED, UNRESOLVED each per break, per session, per eligible signal.

A definition change is a new row in a table whose columns are these denominators; the per-session row is comparable across versions because sessions are the independent unit.

**SYNTHETIC EXAMPLE** (script and output at `/tmp/claude-0/-home-user-Testing/7cf3ca0b-ccdf-5806-aa57-684759b9781e/scratchpad/A4/break_defs.py`): 500 synthetic sessions of 390 one-minute bars, Gaussian random walk with lognormal per-session volatility, half the sessions given a mean-reverting pull after bar 30 to create ranges. Opening range = first 30 bars. B1 = one close ≥1 tick beyond OR; B2 = two consecutive closes ≥0.25·W beyond OR. Same follow-through rule (target 1.0·W, fail 0.25·W, K=10). Output:

```
B1: sessions=500 sessions_with_break=499 breaks=8380 breaks/session=16.76 FT/break=0.026 failed/break=0.464 unresolved/break=0.510 FT/session=0.442
B2: sessions=500 sessions_with_break=452 breaks=2114 breaks/session=4.23  FT/break=0.112 failed/break=0.259 unresolved/break=0.630 FT/session=0.472
```

The per-break follow-through rate quadruples; the per-session count is flat. The path is pure noise by construction, so the whole difference is denominator.

## 4. When following this proposal would make the decision worse

- **Lag cost (HYPOTHESIS):** M1/M3/M4 need 5–10 bars. In the expansions that pay most, the first 5–10 bars contain much of the move; waiting to confirm acceptance buys a worse price. The filter can lower loss count and still lower expectancy.
- **W mis-scaling:** If W is the raw OR width without session/minute-of-day normalisation, calm days produce "breaks" on noise and volatile days never break. Normalise W by the session-aware ATR the user already plans.
- **Over-versioning:** If versions are chosen after looking at results, Study 66's selection problem returns in a new coat. Pre-register the version used for each study.
- **Several strategies on one move:** counting FT per eligible signal double-counts a single break episode. The per-session denominator must be kept beside it.

## 5. Cheapest decisive test, and the result that would retire the idea

Test spec (needs only the user's bar data and signal log): for every eligible signal over ≥200 sessions, compute M2 at the decision bar (no lag), then post-entry MFE/MAE at K=10 and K=30 bars. Stratify by M2 tercile. Unit = session (cluster standard errors by session; signals within a session are not independent). **Retire** if the difference in mean post-entry net excursion between top and bottom M2 terciles is smaller than round-trip cost (MNQ: ~1 tick slippage each side + commission, roughly $2–4; public, verify) with a session-clustered 95% CI that includes zero. Repeat under two BREAK versions; if the tercile effect is stable but FT/break moves, the measurement survives and the denominator explanation stands.

## 6. Missing inputs that materially limit the conclusion

- Signal log must contain: timestamp of decision, instrument, strategy slot, the level and W used, and **rejected** signals (unknown whether logged, brief §1).
- 1-minute bars for MNQ (and NQ/ES where strategies read them) with session labels.
- Study 71's actual break definition and horizon; without it I cannot say which denominator moved.
- Whether entries occur at the break bar or later; the lag cost in Section 4 depends on this.
- Session-aware ATR definition from the sizing work, for W normalisation.

## 7. Filter accounting (the seven quantities)

Filter under test: "skip entry when M2 (10-bar ER at decision) is in the bottom tercile of the trailing 20-session distribution for that minute-of-day."

- Eligible signals: all strategy-slot triggers in the session window, executed or not.
- Trades retained: eligible signals with M2 ≥ tercile cut.
- Losses avoided: filtered-out signals whose unfiltered simulated outcome < 0; count and $ sum.
- Winners discarded: filtered-out signals whose outcome > 0; count and $ sum.
- Net change after costs: Σ(retained outcomes) − Σ(unfiltered outcomes), round-trip costs applied to both.
- Independent sessions: sessions with ≥1 eligible signal; all CIs clustered here.
- Portfolio contribution: change in daily P&L summed across all slots and in worst-day drawdown, since several slots fire on the same move.
