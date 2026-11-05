# B3 — Backtest Audit and Skeptical Replication

Scratch code and output: `/tmp/claude-0/-home-user-Testing/7cf3ca0b-ccdf-5806-aa57-684759b9781e/scratchpad/B3/` (`sim_selection.py`, `sim_variants.py`, `*_output.txt`). OBSERVED: no data, code, logs or Study 66/71 documents exist in the workspace, so every check below is a specification plus a SYNTHETIC calibration, not a finding about the user's system.

## 1. Strongest finding or proposal, and the decision it would change

HYPOTHESIS (ranked): the improvement most likely to vanish is **any result selected from a search** (parameter grid, shifted calendar, strategy-slot variant) that is then judged against a single-rule null. Second: **same-bar stop/target resolution** when the stop is smaller than the typical 1-minute bar range — which is exactly the MNQ scalping regime. Third: look-ahead in session statistics.

Decision it changes: before any slot, filter, or sizing rule from Study 66/71 is promoted to live trading, it must clear the **max-of-N null** (not the single-rule null) *and* survive the conservative fill convention. If it fails either, the "improvement" is an artefact of accounting, not of the market.

## 2. Evidence (with labels) and the strongest competing explanation

SYNTHETIC (run today, seed 66): 200 parameter sets of pure noise, 250 trading days each, 2000 replications.
- Preselected rule (index 0, chosen before looking): mean t = +0.01; P(t > 1.96) = 0.026 (nominal 0.025). Honest.
- Best of 200: mean t = +2.75; **P(t > 1.96) = 0.992**; median naive p = 0.0035. The 95th percentile of the max-of-200 null is **t = 3.50** vs 1.72 for one rule.
- One realized search: best set t = 3.27, naive p = 5e-4; sign-flip reality-check p = **0.127**.

SYNTHETIC same-bar ambiguity (1R stop, 1.5R target, 1-min OHLC built from 5-s ticks, 60-bar horizon). Share of trades where one bar touches both levels, and the mean R/trade under conservative / tick-truth / optimistic ordering:
- stop = 2× average 1-min range: 0.0% ambiguous; spread 0.000 R.
- stop = 1× range: 0.4%; spread +0.009 R.
- stop = 0.5× range: **9.4%; conservative −0.018, truth +0.067, optimistic +0.217** (spread 0.235 R/trade).
- stop = 0.33× range: 25.1%; spread 0.626 R/trade.
A fill convention alone can manufacture a 0.2–0.6 R/trade "edge" at MNQ scalping stop sizes.

SYNTHETIC overlap: 30-bar forward-return labels on every bar with an iid noise signal are *not* inflated (4% false positives, nominal 5%). With a **persistent** noise signal (AR(1) ρ = 0.98 — what any smoothed feature, VWAP distance, or session-ATR ratio looks like), naive n calls **66%** of noise signals significant; n/H brings it to 3%.

EXTERNALLY SUPPORTED (general knowledge, not fetched): White (2000) Reality Check; Hansen (2005) SPA; Bailey & López de Prado (2014) deflated Sharpe ratio; CME daily maintenance halt 17:00–18:00 ET (public, verify against CME specs).

Strongest competing explanation: the user's Study 66 may already report the preselected rule's percentile against a *random-entry* distribution, which is valid for that one rule. It does not become valid for the best slot among many once slots are compared. Random-entry nulls address "is this rule better than chance entries"; they do not address "how good does the best of K rules look under chance".

## 3. Worked example / reproducible check / formula / data spec

```python
# Each returns PASS/FAIL. Inputs: bars (ts_open, O,H,L,C) in ET tz-aware; features f(ts); trades (entry_ts, exit_ts, stop, tgt, pnl).
def chk_lookahead(features, bars):          # FAIL if any feature at t uses close of bar t or later
    shifted = features.recompute(bars.shift_close_by_one())   # feature at t from bars <= t-1
    return "PASS" if (features == shifted).all() else "FAIL"
def chk_session_stats(stats, bars):          # session VWAP/ATR/range must be expanding, not full-session
    full = stats.compute(bars_full_session); exp = stats.compute_expanding(bars)
    return "FAIL" if (full == exp).mean() > 0.99 else "PASS"   # identical => computed with the future
def chk_overlap(trades, H):                   # effective n for labels / shared-bar trades
    n_eff = n_distinct_nonoverlapping(trades.entry_ts, trades.exit_ts)   # or n/H for fixed-horizon
    return "FAIL" if reported_n > 1.5 * n_eff else "PASS"
def chk_same_bar(trades, bars):              # report three P&Ls; FAIL if the sign of the edge depends on them
    amb = bars_touching_both(trades); pnl_c = resolve(trades, stop_first=True)
    pnl_o = resolve(trades, target_first=True); pnl_t = resolve_with_lower_tf(trades)  # ticks or 5-s bars
    return "FAIL" if (sign(mean(pnl_c)) != sign(mean(pnl_o))) or amb.mean() > 0.02 else "PASS"
def chk_session_boundaries(bars, trades):    # all in America/New_York; DST transitions, halt, roll
    assert bars.ts.tz == "America/New_York"; assert no_bars_between(bars, "17:00", "18:00")
    assert no_trade_spans(trades, "17:00")  # no overnight carry across halt unless intended
    assert rth_entries.min_time() >= "09:30"; assert contract_roll_days_flagged(trades)
    return "FAIL" if any_dst_day_has_shifted_open(bars) else "PASS"
def chk_selection(pnl_matrix, k_pre):        # rows = every rule/param/calendar tried, cols = days
    t = tstat(pnl_matrix, axis=1); k_best = t.argmax()
    null_max = [tstat(pnl_matrix * signflip(ncols), axis=1).max() for _ in range(1000)]
    p_pre  = pct(null_max < t[k_pre]); p_best = mean(null_max >= t[k_best])   # report BOTH
    return "FAIL" if p_best > 0.05 else "PASS"
```

Study 66 procedure: (a) freeze the preselected rule's index *k_pre* in writing before the grid runs; (b) build the full matrix of every trial, including shifted calendars and abandoned variants (the denominator is trials *run*, not trials *reported*); (c) report k_pre's percentile against the random-entry null **and** against the max-of-N sign-flip null; (d) report the best trial against the max-of-N null only. A rule that is "99th percentile vs random entries" but below the 95th percentile of the max-of-N null is not distinguishable from search noise.

## 4. When following this proposal would make the decision worse

- The grid is small and nested (e.g., 5 stop widths) and results are smooth across neighbours: max-of-N on correlated trials is conservative; the sign-flip null preserves that correlation, so use it rather than Bonferroni.
- Conservative same-bar resolution on a *mean-reversion* entry that legitimately tags the target first in tick data would discard real edge; that is why the lower-timeframe resolution is required, not just the pessimistic one.
- Treating all overlapping trades as one observation loses power when the strategy genuinely fires on independent moves; use n_eff by non-overlapping *bars held*, not by day.

## 5. Cheapest decisive test, and the result that would retire the idea

Cheapest: rerun the existing Study 66 grid once with (i) the conservative fill convention and (ii) the max-of-N sign-flip null (chk_selection, ~minutes on a P&L matrix). Retire the result if the best slot's reality-check p > 0.05 **or** if the edge changes sign between conservative and optimistic fills.

## 6. Missing inputs that materially limit the conclusion

OBSERVED missing: bar timestamps and their convention (open- or close-stamped), the list of *all* trials run in Study 66, the fill convention in the backtester, tick or sub-minute data for ambiguous bars, contract-roll handling, the timezone of stored bars, and whether logs record rejected signals (needed for any filter accounting).

## 7. Filter accounting (the seven quantities in rule 3)

| Quantity | Spec for a "selected rule" audit |
|---|---|
| Eligible signals | All signals of the preselected rule *and* every trial in the grid, by day |
| Trades retained | Signals surviving conservative fill, session-boundary and roll-day exclusions |
| Losses avoided | Not applicable to an audit; for any filter, count only under conservative fills |
| Winners discarded | Trades whose outcome flips target→stop under conservative or tick resolution |
| Net change after costs | R/trade under conservative fills minus 1 tick + commission per side (MNQ $0.50/tick, public) |
| Independent sessions | Days with ≥1 non-overlapping trade; n_eff from chk_overlap |
| Portfolio contribution | Marginal t-stat of adding the slot to the existing slot P&L matrix, under the same max-of-N null |

**Single check most likely to reverse the conclusion: chk_selection.** The synthetic run shows the best of 200 noise rules exceeds t = 1.96 in 99% of worlds while a preselected rule does so 2.6% of the time; nothing else in the audit moves a result by that much unless stops are below one bar's range, in which case chk_same_bar is a close second.

(Prose ≈ 900 words excluding the one code block and one table.)
