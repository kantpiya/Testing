# S6 — Skeptical portfolio manager: trying to defeat the strongest management improvement

**Everything below is SYNTHETIC** (computed on `data/synthetic/`, development window 2025-05-01 → 2026-04-30, 332 trades / 242 sessions). No number here is market evidence. Labels: OBSERVED = computed on the synthetic data; HYPOTHESIS = my inference; SYNTHETIC EXAMPLE = constructed illustration.

Code: `src/S6/run.py` (+ `replay.py`, `stageb.py`); full console output in `src/S6/run_output.txt`; tables in `src/S6/grid.csv`, `neighbourhood.csv`, `output.json`. Charts: `charts/S6_session_concentration.png`, `charts/S6_target_neighbourhood.png`.

## 1. Strongest finding and the decision it changes

OBSERVED. I built an independent Stage A replay and screened 92 distinct simple policies. **Every policy that tightens management after entry loses money** on this data — time exits, no-progress exits, breakeven stops, trailing stops, tighter targets, add-leg protection — including the brief's own decision rule (stop to +0.3R after +0.8R: −$4,564 over 332 trades / 242 sessions, costs included). The only improvement is the opposite: **remove the KX profit target and hold to 15:55 with the original stop**: paired +$60,290 (+418 R) on a baseline of $15,201, 97 trades changed in 97 sessions.

I then tried to kill it six ways. **I could not.** It survives session removal, leave-one-session-out, 2,000-draw session bootstrap, a 30-cell neighbourhood (30/30 positive), 3 ticks of slippage, both strategy versions, the PX analogue, all four quarters, and Stage B with the 4-contract limit (portfolio +$59,726).

The decision it changes: on this data the answer to "reached +0.8R, stalled, back to +0.3R" is **hold the original bracket — and the bracket's target is the thing to drop, not the stop**. In that exact cell (60 KX trades / 60 sessions, still open, ≥+0.8R high then a close ≤+0.3R) the original yields +26 R, exiting at the stall ≈ +18 R, no-target +132 R.

HYPOTHESIS (the skeptic's residual case): the effect is a planted post-entry drift of a size no real intraday breakout has. It will replicate on the sealed holdout because the holdout shares the generator; that says nothing about the user's market. The strongest reason to retain the original on the **real** desk is sample size: at the synthetic dispersion (SD 6.2 R of post-target continuation), one year of KX target hits (~100) can only detect a continuation ≥ 1.6 R per trade; a modest 0.5 R needs ~940 target hits (~9 years). An effect too small to verify does not justify the policy's costs (31% of changed trades worse off, 19/97 two-R winners turned into full losers, session SD ×3, max drawdown +32%).

## 2. Evidence (labelled) and the strongest competing explanation

**Engine validation (OBSERVED).** My replay of the documented original policy matches `trades.csv` on 97.5% of exit timestamps and 98.1% of exit prices for the 322 non-MANUAL trades; net $15,874 vs journal $15,883. Residuals: the generator applies 0/1/2-tick random slippage on market fills (entry slippage 44/228/60 trades) and its fills are inconsistent at the 1-tick level. Conventions inferred and applied to both policies: entry bar not checked for stop/target; limit fills only when price trades *through* the level; stop fills on touch; add trigger strict-through, window inclusive of entry+20 min, cancelled if the fill bar is also the exit bar; Stage B room is freed at the exit bar's open. Ten journal exits are MANUAL (−$513 journal vs −$674 mechanical); both policies are replayed mechanically, so these cancel in paired differences.

**Policy grid, Stage A paired (OBSERVED, 332 trades / 242 sessions, costs on every fill).** Top and bottom of 74 grid cells (full table in `grid.csv`):

| policy | changed trades / sessions | paired Δ net $ | Δ R / trade | sessions + / − | boot 5th pct $ |
|---|---|---|---|---|---|
| KX no target (hold to 15:55) | 97 / 97 | **+60,290** | +1.26 | 27.7% / 12.4% | +42,956 |
| KX target 6R | 97 / 97 | +36,617 | +0.77 | 30.6% / 9.5% | +26,950 |
| PX no target (analogue) | 64 / 64 | +12,618 | +0.24 | 18.6% / 7.9% | +7,621 |
| KX target 3R | 97 / 97 | +11,044 | +0.23 | 36.8% / 3.3% | +7,452 |
| no-progress 30 min < 0.2R | 11 / 11 | −70 | 0.00 | 3.3% / 1.2% | −1,200 |
| time exit 60 min | 32 / 30 | −100 | −0.01 | 5.4% / 7.0% | −1,753 |
| breakeven after +0.8R, lock +0.3R (the brief's rule) | 66 / 65 | −4,564 | −0.10 | 12.8% / 14.0% | −8,828 |
| add-only breakeven | 74 / 74 | −3,759 | −0.08 | 4.5% / 26.0% | −5,289 |
| trail 0.5R after +0.8R | 99 / 98 | −9,635 | −0.20 | 12.8% / 27.7% | −14,588 |
| time exit 10 min | 227 / 187 | −16,179 | −0.32 | 32.6% / 44.6% | −21,766 |

**Mechanism (OBSERVED).** For the 97 KX trades that hit the original target, the MNQ 15:55 open sits a mean **+2.56 R beyond the target** (median +2.17 R, SD 6.17 R, 70% positive; v1 +2.41 R n=67, v2 +2.90 R n=30). PX target hits: +1.16 R (n=64, SD 2.47 R). This single mechanism explains every grid result: anything that exits earlier forfeits drift.

**Strongest competing explanation (HYPOTHESIS).** Not a management edge but an entry edge with a long horizon: sessions carry a directional drift the breakout catches, and the "improvement" merely exposes the entry to more of it. On real data 2.5 R of drift in 5 hours after a 2 R move is implausible; the honest prior is ≈ 0, at which the policy is pure variance plus 19 converted losers.

## 3. Reproducible check (code path + pasted output)

`python3 src/S6/run.py` (≈4 min). Pasted from `src/S6/run_output.txt`:

```
(a) SESSION CONCENTRATION -- SYNTHETIC
  remove top  1 sessions by benefit: remaining $56,306 = 93.4% of total
  remove top  3 sessions by benefit: remaining $50,572 = 83.9% of total
  remove top  5 sessions by benefit: remaining $45,520 = 75.5% of total
  remove top 10 sessions by benefit: remaining $35,049 = 58.1% of total
  sessions with benefit>0: 67, <0: 30, =0: 145 of 242
  sessions needed to reach 50% of the benefit: 13 (of 67 positive sessions)
  leave-one-session-out: min $56,306 max $61,150 (all >0: True)
  session bootstrap 2000 draws: 90% CI [42,388, 77,694], 95% CI [38,289, 81,776], P(sum<=0)=0.0000
  top 10% of changed trades (n=10) carry $25,241 = 41.9% of the benefit

(b) PARAMETER NEIGHBOURHOOD  (30 cells, sign positive in 30 of 30)
  KX target m=2.5 +3,535 | 3.0 +11,044 | 3.5 +17,717 | 4.0 +21,846 | 5.0 +28,772 | 6.0 +36,617
  | 8.0 +44,691 | 10.0 +51,354 | none +60,290
  KX no target, flat at 12:00 +41,319 | 13:00 +43,940 | 14:00 +51,038 | 15:00 +55,679 | 15:30 +56,321
  KX no target + trail (Y=2.0/2.5/3.0 x dist 0.5/1.0/1.5/2.0): +11,097 ... +44,487 (all positive)
  KX no target + stop->entry at +2.0R: +61,112 ; lock +1.0R: +53,863 ; lock +1.5R: +46,441

(c) FILL ASSUMPTIONS (both policies re-run)
 total_slip_ticks  stop_fill  base_usd  alt_usd  sum_d_usd  boot_ci05  p_le_0
      1             touch     15201.0  75491.0    60290.0    42861.0     0.0
      2             touch     14966.0  75103.0    60137.0    42695.0     0.0
      3             touch     14731.0  74715.0    59984.0    42531.0     0.0
      1-3           through   +60,512 / +60,358 / +60,203
 same-bar stop/target ordering: identical (no target exists under the alternative)

(d) STRATEGY VERSION / FAMILY
 KX_ORB_v1  162 trades/162 sessions, 67 changed: base $7,059 -> $47,255  (+40,196; boot 5th pct +24,291)
 KX_ORB_v2   78 / 78, 30 changed:               base $5,518 -> $25,612  (+20,094; boot 5th pct +11,778)
 PX_REV_v1   92 / 92: unchanged (PX analogue "no target": +12,618, boot 5th pct +8,441)
 by quarter: May-Jul25 +16,650 | Aug-Oct25 +20,427 | Nov25-Jan26 +6,384 | Feb-Apr26 +16,830

(e) STAGE B (chronological, 4-contract limit, pyramiding, 15:55, rejected signals eligible)
  journal: executed 332, rejected 14
  Stage B original: executed 330, rejected 16 (two extra: journal MANUAL exits 193/273 freed room); net $15,358
  Stage B alt     : executed 321, rejected 25; net $75,084
  BLOCKED by the alternative: 9 PX signals [24, 76, 78, 100, 111, 163, 225, 331, 341], worth $567 under the original
  FREED: none.  common 321 trades: $14,791 -> $75,084
  PORTFOLIO net diff +$59,726 (Stage A paired +$60,290); session bootstrap 90% CI [41,641, 78,975]
  Stage A overlap flag: alt holds past a later same-session entry in 15 cases

(f) DRAWDOWN
          replay  total_usd  max_dd_usd  worst_session_usd  best_session_usd  sd_session  n_sessions<-300
Stage A original    15201      -1804         -359               614             279            12
     Stage A alt    75491      -2373         -359              4404             856            13
Stage B original    15358      -1807         -359               614             280            12
     Stage B alt    75084      -2374         -359              4402             858            16
  changed trades ending at the ORIGINAL STOP under alt (2R winner -> full loser): 19, paired cost $-11,880
  LOCK variant (no target; stop->entry once +2.0R touched): paired +$61,112, max DD -$1,921, 0 full-loser conversions,
       34.7% of changed trades worse off, 95% CI [40,324, 83,446]
```

## 4. When following this would make the decision worse

OBSERVED costs even here: 30 of 97 changed sessions are worse; 19 trades go from +2 R to −1 R (−$11,880); worst reversal −$860 (trade 80); session SD triples ($279 → $856); max drawdown +32%; 9 PX signals blocked in Stage B; 15 overlaps with later same-session entries; hold time 35 → 305 minutes per changed trade, with a 1 R stop live all afternoon.

HYPOTHESIS, when the real decision is worse: (i) real continuation ≤ 0 — variance plus the 19 converted losers; (ii) continuation exists but is front-loaded (minutes, not hours) — then "flat at 12:00/13:00" (68–73% of the synthetic benefit here) is the wrong lesson and a late trail the right one; (iii) the add leg's exposure also runs to the close, so 4 contracts × stop distance sit for 5 hours and the limit blocks every afternoon PX signal; (iv) MANUAL exits: 10 of 332 here, possibly many more in the real journal; a mechanical replay cannot reproduce them.

The sealed holdout will not settle (i): it shares the generator.

## 5. Cheapest decisive test on the user's real data, and the result that retires the idea

**Test (observational, no trading changes):** a *shadow continuation audit*. For every historical KX trade that exited at TARGET, read the MNQ bars after the exit and compute `cont_R = direction × (15:55 open − target fill) / stop distance`; and run the paired replay (`src/S6/run.py`, `kx_target_mult=None`) on all real KX trades (n ≈ 240/yr), which has lower dispersion (SD 4.95 R vs 6.17 R).

**Decision rule, pre-specified:**
- Primary: paired Δ net R per KX trade (no-target vs original), session-bootstrap 90% CI (≥ 1,000 draws).
- **Retire** the idea if the CI includes 0, or if the point estimate is < +0.5 R per KX trade (the level below which the drawdown/blocking costs in section 4 exceed the gain at the user's size), or if more than 30% of the benefit comes from 3 sessions.
- **Advance to forward simulation** only if the CI lower bound > 0 *and* the estimate ≥ +0.5 R *and* the sign holds in both strategy versions.

**Sample needed (one-sided α 5%, power 80%, SD from synthetic data as placeholder):** 605 KX trades for a 0.5 R effect; 152 for 1.0 R; 50 for the synthetic 1.74 R. With one year (~240 KX trades) the minimum detectable effect is 0.79 R per trade. **With ≥ 2.5 years of KX trades the test is decisive at 0.5 R; with one year it can only confirm an effect as large as the synthetic one, a null is uninformative, and the original stays by default.**

## 6. What the real export must contain for this test

From `trades.csv`: `trade_id, session, strategy, direction, entry_ts, entry_px, initial_contracts, added_contracts, add_ts, add_px, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason` (MANUAL must be flagged as such). From `fills.csv`: every fill with `ts_utc, side, qty, price, order_type, fill_role, commission` (to recover real slippage per order type). `bars_MNQ_1min.csv` for the **full RTH session of every trade day, continuing after the historical exit** (`ts` as bar open, ET offset, OHLC). `signals.csv` with rejected signals and `reject_reason` (for Stage B blocking). `strategy_versions.csv` with validity dates. `costs.csv` with commission per side and position limit. Essential for the audit specifically: target fill price, stop distance (or `initial_stop_px`), direction, session date, and bars to 15:55.

## 7. Policies and thresholds examined (complete count, including discarded)

**92 distinct policy cells**, all Stage A paired on 332 trades / 242 sessions; 12 further fill-assumption variants of the winner; 1 lock variant for drawdown.

- Time exit, T ∈ {10, 15, 20, 30, 45, 60, 90} min — 7 (all ≤ 0; discarded)
- No-progress exit, T ∈ {5,10,15,20,30} × MFE < {0.2,0.3,0.5} R — 15 (all ≤ 0; discarded)
- Breakeven/lock, trigger {0.5,0.6,0.8,1.0,1.2} R × lock {0, +0.1, +0.3} R — 15 (all < 0; discarded)
- Trailing stop, trigger {0.5,0.8,1.0} R × distance {0.3,0.5,0.8} R — 9 (all < 0; discarded)
- Target multiple both families {1.0,1.5,2.0,3.0} — 4 (only 3.0 > 0)
- KX target multiple {2.5,3.0,3.5,4.0,5.0,6.0,8.0,10.0, none} — 9 (all > 0, monotone)
- PX target replaced by m·R {1.0,1.5,2.0,3.0, none} — 5 (all > 0); PX cap {1.0,1.5,2.0} R — 3 (≤ 0)
- Add-leg: add-only breakeven, add-only trail {0.3,0.5} R, no add — 4 (all < 0; discarded)
- KX no target + late trail, trigger {2.0,2.5,3.0} × distance {0.5,1.0,1.5,2.0} R — 12 (all > 0, all below pure no-target)
- KX no target, flat at clock {12:00,13:00,14:00,15:00,15:30} — 5 (all > 0, monotone in time)
- KX no target + lock at {2.0 R→entry, 2.0→+1.0, 2.5→+1.0, 2.0→+1.5} — 4 (all > 0)
- Fill variants of the winner: slippage {1,2,3} ticks × same-bar {stop-first, target-first} × stop {touch, through} — 12
- Session statistics: remove top {1,3,5,10}, LOSO (242), bootstrap 2,000 draws (Stage A) + 2,000 (Stage B) + 1,000 per grid cell.

## 8. Proposed challenger for pre-registration

One challenger, with the caveat that I expect it to replicate on the sealed holdout *because* the holdout shares the generator; that replication is not evidence about the user's market.

**KX_NOTARGET_BE** — *Mechanism:* KX trades carry no profit target; once any bar's high (long) / low (short) reaches entry ± 2.0 × stop distance (the v1 target level, same level for v2), the stop moves to the entry price, live from the next bar; the original stop applies before that; flat at the 15:55 bar open. PX unchanged. Pyramiding rule unchanged (the add shares the stop). *Decision time:* at every bar close ≤ decision time; stop changes live from the next bar open. *Parameters:* trigger 2.0 R, lock 0.0 R (entry), no target, EOD 15:55. *Fill assumptions:* stops filled on touch at stop − 1 tick adverse (or bar open if gapped); EOD exit at 15:55 open − 1 tick; $0.74/contract/side on every fill. *Objective:* paired net $ and R vs the original on identical KX entries; advance only if the session-bootstrap 95% CI excludes 0 **and** max drawdown ≤ 1.5 × original **and** Stage B portfolio net (4-contract limit, rejected signals eligible) exceeds the original. Development result (OBSERVED, SYNTHETIC): +$61,112, 95% CI [40,324, 83,446], max DD −$1,921 vs −$1,804, zero 2 R-winner-to-full-loser conversions.

The lock variant is preferred over pure no-target because it removes the one failure mode visible even here (19 full reversals) at no cost in development P&L, and 2.0 R is the strategy's own target level, not a fitted parameter.
