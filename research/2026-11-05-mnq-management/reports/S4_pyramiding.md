# S4 — Pyramiding / winner retention (KX adds): manage legs together or separately?

**Every number below is SYNTHETIC** (`data/synthetic/`, 2025-05-01 → 2026-04-30); none is market evidence. Denominators: 240 KX trades = 240 sessions (one per session); 73 carry a 1-contract add ("add trades", 73 sessions). $ are net of $0.74/contract/side on every fill including each leg's exit unless marked gross. 1R = initial-leg `planned_risk_usd`, fixed. PX excluded.

## 1. Strongest finding and the decision it changes

**OBSERVED (synthetic):** every way of managing the add separately costs money versus the shared bracket; only one buys a meaningful drawdown reduction in return.

- Add-only breakeven after +0.5R further progress (c): −$960 (95% session-bootstrap CI −1,640 to −262; −0.085R per add trade). Of the 14 trades where its stop fired, **13 then reached the original target**.
- Add stop at the original entry price (b): −$320 (CI −1,350 to +670), but add-trade worst session −$392 → −$272, max drawdown $392 → $272, mean give-back 0.59R → 0.51R. The only variant whose drawdown benefit is not dominated by its cost.
- Whole-position breakeven on the add (d): −$1,466 (CI −4,851 to +1,802) and *higher* all-KX max drawdown ($1,994 → $2,254): leg 1 becomes a scratch instead of a 2R winner on 8 trades.
- Scale-out of the add at +1R from the add price (e): a near no-op for KX_ORB_v1 (the level sits 0–2 ticks beyond the 2.0R target); it only bites on v2.

**Decision changed:** keep the add on the shared bracket; do not adopt add-only or whole-position breakeven. If the desk wants a drawdown-first variant, only (b) merits a holdout slot, with an explicit P&L budget (Section 8).

**Does the add earn money net of its own risk? (leg 2 only, original policy, OBSERVED):** +$3,581 over 73 adds (mean +$49, 62 target / 11 stop; journal fills +$3,485, the gap being the two MANUAL adds replayed by rule). The add's own risk to the shared stop averages $172 = 1.21 × initial 1R, so the add earns **+0.29R of its own risk** per add. Bootstrap 95% CI for the total [$1,831, $5,206]. Pyramiding is retained.

## 2. Evidence (labelled) and the strongest competing explanation

**OBSERVED — structure.** The original bracket has no intermediate exit, so add-trade baseline net R is bimodal: all 73 lie in [−3.27, −1.5] or [+2.0, +3.98]. Protecting the add can only save about one stop-distance on the 11 losers or forfeit about (target − entry) on winners that retrace through the protection level first. Add trades, stop-first:

| policy | hits that changed outcome (trades = sessions) | original then reached TARGET | cost | original STOPPED | saving |
|---|---|---|---|---|---|
| (b) add stop @ entry | 19 | 8 | −$1,208 (mean −$151) | 11 | +$888 (mean +$81) |
| (c) add BE after +0.5R | 14 | 13 | −$1,134 (mean −$87) | 1 | +$174 |
| (c') add BE after +1.0R | 4 | 3 | −$244 | 1 | +$174 |
| (d) whole position BE | 19 | 8 | −$4,126 (mean −$516) | 11 | +$2,661 (mean +$242) |

Break-even for (b) needs P(target | retraced to entry after the add) < 81/(81+151) ≈ 0.35; observed 8/19 = 0.42. For (c) it needs < 0.67; observed 13/14 = 0.93.

**OBSERVED — largest winners.** All 24 all-KX top-10% trades (baseline net R ≥ 2.97) are add trades: the add is what lifts a 2R target to 3–4R net. The add-subset top 7 (net R ≥ 3.74) are untouched by (b), (c), (d) and lose $330 under (e); per-policy earnings on the top-24 set are the `top10% $` column below.

**Strongest competing explanation (HYPOTHESIS).** From +1R, a driftless random walk reaches a 2.0R target before the shared stop with probability 2/3 (v1) or 0.57 (v2). Synthetic add trades reached it 62/73 = 85%. Whether planted or produced by the generator's ORB structure, **that excess continuation is the whole reason protecting the add loses**; the sign flips if real continuation is at or below the martingale baseline (Section 5). Adds also occur only when initial size ≤ 3 (position limit 4; 50 KX trades at 4 contracts could never add), so add trades have wider stops (40.9 vs 35.3 pts) and are a selected sample.

**Uncertainty.** Session bootstrap, 2,000 draws. Only (c) at +0.5R has a CI excluding zero. Stop-first vs target-first ordering changes 0 trades in every policy.

## 3. Reproducible check

Code: `src/S4/engine.py` (leg-aware replay), `src/S4/run.py`. `python3 src/S4/run.py` from the panel folder regenerates `src/S4/output/*.csv`, `src/S4/output/run_output.txt`, `charts/S4_*.png`.

**Reconciliation (output section 0).** Rule replay of the original bracket on MNQ bars vs the journal, 234 non-MANUAL KX trades: net P&L identical on 233 (trade 332, a gap-through stop, differs by $1.50 of slippage); exit bar identical on 225, the other 9 being one-bar, same-price differences at sub-tick level. Conventions needed to reproduce the journal, applied to all policies: bracket **not live on the entry bar**; touch trigger at the tick-rounded level; stop fill = stop − 1 tick; gap through = open − 1 tick; target = exact limit on touch (optimistic versus a real limit that must trade through); forced exits = open − 1 tick; bar-close decisions act from the next bar; (b)/(d) stops live in the add bar. Six KX trades (two with adds) ended MANUAL at non-rule prices; the primary replay runs the bracket through them (journal KX net $12,686 vs replay $12,583); forcing a flat there changes no conclusion.

Pasted output (stop-first; `d` = paired difference vs (a); CI = 2,000 session-bootstrap draws; `gb` = give-back = peak gross open P&L of the whole position at the favourable intra-bar extreme minus realised net; `top10% $` = net $ on the fixed baseline top-10% set; `chg` = trades whose net differs from (a)):

```
--- ADD trades only | n=73 trades = 73 sessions | SYNTHETIC, net of commissions ---
policy                  n     net $   meanR   win%  gb$ mean gb R mean   gb$ sum  top10% $  maxDD $  worst $     d net $ [95% CI]      d meanR [95% CI]  d top $  d DD $  chg
a_orig                 73     22220   2.055    85%        93      0.59      6757      3045      392     -392
b_add_stop_entry       73     21900   2.036    85%        82      0.51      5971      3045      272     -272     -320 [-1350,+670]  -0.020 [-0.108,+0.064]      +0    -120   19
c_add_be_after         73     21261   1.971    85%        90      0.57      6601      3045      392     -392     -960 [-1640,-262]  -0.085 [-0.145,-0.025]      +0      +0   14
c_add_be_after_1R      73     22151   2.049    85%        92      0.58      6682      3045      392     -392       -70 [-487,+428]  -0.006 [-0.040,+0.034]      +0      +0    4
d_all_be_on_add        73     20755   1.946    74%        90      0.56      6588      3045      189     -152   -1466 [-4851,+1802]  -0.109 [-0.393,+0.158]      +0    -203   19
e_scaleout_add         73     21868   2.019    85%        91      0.58      6634      2716      392     -392     -353 [-997,+442]   -0.036 [-0.094,+0.031]    -330      +0   63

--- ALL KX trades | n=240 trades = 240 sessions ---
policy                  n     net $   meanR   win%  gb$ mean gb R mean   gb$ sum  top10% $  maxDD $  worst $     d net $ [95% CI]      d meanR [95% CI]  d top $  d DD $  chg
a_orig                240     12583   0.355    40%       147      0.96     35195     11119     1994     -392
b_add_stop_entry      240     12263   0.349    40%       143      0.94     34409     10651     1936     -272     -320 [-1397,+643]  -0.006 [-0.034,+0.019]    -468     -58   19
c_add_be_after        240     11623   0.329    40%       146      0.96     35039     10531     2071     -392     -960 [-1657,-235]  -0.026 [-0.045,-0.007]    -588     +78   14
c_add_be_after_1R     240     12513   0.353    40%       146      0.96     35119     11025     1994     -392       -70 [-487,+428]  -0.002 [-0.012,+0.010]     -94      +0    4
d_all_be_on_add       240     11117   0.322    37%       146      0.95     35025      9441     2254     -224   -1466 [-4929,+1633]  -0.033 [-0.121,+0.046]   -1678    +260   19
e_scaleout_add        240     12230   0.344    40%       146      0.96     35071     10398     2000     -392     -353 [-1036,+422]  -0.011 [-0.030,+0.010]    -721      +7   63

Same-bar stop+target ambiguity: 0 trades differ between orderings, every policy.

=== 3. Leg 2 only, original policy ===
Journal fills, leg 2: n=73, net total $3484.96, mean $47.74, wins 61
Replay (orig), leg 2: n=73, net total $3580.96, mean $49.05, median $75.52; mean own-risk $171.84 (= 1.21 x initial-leg 1R);
  mean leg-2 R on own risk +0.289, mean leg-2 R on initial 1R +0.364;  STOP 11 (-1854.28)  TARGET 62 (+5435.24)
Session-bootstrap 95% CI for leg-2 total net $: [1831, 5206], P(total<=0) = 0.000
Leg-2 net $ by policy: a=3581, b=3261, c=2621, c'=3511, d=3261, e=3228

=== 4. Sensitivities (ADD trades): manual exits honoured -> d vs a: b -250, c -960, c' -70, d -1188, e -325
                                    2-tick penetration trigger -> d vs a: b -320, c -845, c' -70, d -1466, e -352
=== 7. Stage-B: only (e) ever holds longer (13 trades, 70 extra minutes, 1 new overlap with a later PX entry); b/c/d never hold longer.
```

**Replay 1 — protecting the add helps (trade 271, 2026-02-11, SHORT, KX_ORB_v2).** Entry 10:20 @ 22903.5 ×2, stop 22946.5, target 22795.75, 1R = $172.29; add 1 @ 22859.5 at 10:24 (own risk $174). (a) both legs stopped 11:35 → −$351.94 (−2.04R), peak open +$545, give-back $897. (b) add stopped at entry 11:14 → −$265.94. (c) add stopped 10:31 @ 22859.75 → −$177.94 (−1.03R). **First instant the (c) decision was knowable: the 10:29 bar close**; for (b), the add fill at the 10:24 open. Gross open P&L per leg, $ (full minute tables in `src/S4/output/example_*.csv`, charts `charts/S4_replay_*.png`):

```
hhmm   close    a_leg1  a_leg2  c_leg2  c_leg2_stop
10:24 22862.00  166.0    -5.0    -5.0   22946.50   <- add fills
10:26 22853.00  202.0    13.0    13.0   22946.50
10:29 22835.00  274.0    49.0    49.0   22946.50   <- decision knowable (close >= add +0.5R)
10:30 22848.00  222.0    23.0    23.0   22859.50
10:31 22851.25  209.0    16.5     --    exited @ 22859.75
10:40 22805.50  392.0   108.0                       peak of the whole position
11:16 22916.50  -52.0  -114.0
11:35 22947.00  stopped: both legs @ 22946.75
```

**Replay 2 — protecting the add damages a major winner (trade 265, 2026-02-04, SHORT, KX_ORB_v2, baseline +3.16R, top-10% set).** Entry 10:12 @ 23884.0 ×2, stop 23929.0, target 23771.25, 1R = $180.47; add 1 @ 23833.0 at 10:23. (a) both legs hit target 11:05 → +$570.06, give-back $4. (b) unchanged. (c) add stopped 10:37 on a one-tick retrace to the add price; leg 1 ran to target → +$446.06 (+2.47R), −$124. **(c) decision knowable at the 10:27 close**; damage done 28 minutes before the target.

```
hhmm   close    a_leg1  a_leg2  c_leg2  c_leg2_stop
10:23 23824.00  240.0    18.0    18.0   23929.00   <- add fills
10:27 23802.00  328.0    62.0    62.0   23929.00   <- decision knowable
10:28 23790.00  376.0    86.0    86.0   23833.00
10:36 23813.50  282.0    39.0    39.0   23833.00
10:37 23833.25  203.0    -0.5     --    exited @ 23833.25 (one tick through the add price)
10:50 23831.50  210.0     3.0
11:05 23762.75  target: leg1 +450.5 (c) vs both legs +574.5 gross (a)
```

Figures: `charts/S4_cum_pnl_policies.png`, `charts/S4_paired_diff_vs_baseR.png`, and the two replay charts.

## 4. When following this would make the decision worse

- If real post-add continuation is weaker than the synthetic 85%: at the martingale 2/3 (v1), (b) is near break-even and pays for itself in drawdown; below ~55% it wins on P&L too.
- Targets fill at a touch here; if real limits must trade through, the shared bracket's edge shrinks (its add leg reaches the target on 62/73 trades).
- Frequent MANUAL interventions (6/240 here) make a paired comparison measure the desk, not the rule.
- (d) looks attractive on worst-session loss (−$392 → −$224) but raises portfolio drawdown at 0.11R per add trade.
- Initial sizes 1–3 only; at 4 contracts the add never happens.

## 5. Cheapest decisive test on the real data, and the retiring result

Export real KX trades with adds plus MNQ 1-minute bars; run `src/S4/run.py` unchanged. The decisive statistic is one conditional count, with trades and sessions: among real add trades (for power, all KX trades that reached entry + 1.0 × stop distance), **P(reach original target | price later retraced to the entry price)**. If ≥ 0.35 (v1) / 0.30 (v2), the (b) break-even for this geometry, (b) retires and the shared bracket stands; (b) also retires if the paired session-bootstrap 95% CI for Δnet $ lies entirely below zero and worst-session improvement is < 1R. For (c) the retiring result is P(target | retrace to add price after +0.5R) ≥ 0.67 (synthetic: 0.93). Fewer than ~40 real add trades cannot separate any variant from the original; (c') and (e) are indistinguishable at any realistic n (4 and 13 affected trades per 240).

## 6. What the real export must contain (exact fields)

- `bars_MNQ_1min.csv`: `ts` (bar open, ISO with ET offset), `open, high, low, close`; full session after every exit.
- `trades.csv`: `trade_id, signal_id, session, strategy, direction, entry_ts, entry_px, initial_contracts, added_contracts, add_px, add_ts, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason, commission_usd, net_pnl_usd`.
- `fills.csv`: `fill_id, trade_id, leg_id, ts_utc, side, qty, price, order_type, fill_role (ENTRY/ADD/EXIT), exit_reason, commission`, one exit fill **per leg**.
- `strategy_versions.csv` (target multiple and add rule by validity date); `costs.csv` (commission, tick, point value, slippage, position limit, flat time).
- Also: whether the add is its own OCO or attached to the original bracket; the broker's stop-trigger convention (last trade vs bid/ask); timestamp and reason of every manual intervention; whether order levels are tick-rounded.

## 7. Policies and thresholds examined (complete count)

Six policies: (a) original shared bracket; (b) add stop at entry price; (c) add breakeven at add price after +0.5R; (c') same at +1.0R; (d) whole-position breakeven at entry on the add fill; (e) add exits at +1R from the add price, leg 1 to target. Thresholds: breakeven trigger {0.5R, 1.0R}; scale-out {+1.0R}; protection level {entry price, add price}. Sensitivities, each on all six: ordering {stop-first, target-first}; trigger {touch, 2-tick penetration}; MANUAL exits {run through, forced flat}. Replay runs: 24. Largest-winner definitions: 2 (all-KX top 24; add-subset top 7). Nothing else was tried or tuned.

## 8. Proposed challenger for pre-registration (one; the second slot is deliberately left empty)

**S4-C1 — Add-leg stop at the original entry price (policy b).** Mechanism: cap the add's risk at ≈ 1 initial-R (one stop-distance) instead of ≈ 2; leg 1 keeps the original stop and target; the add keeps the original target. Decision time: the add fill (next bar open after the add trigger); the stop is live in that bar. Parameters: none free (level = recorded entry fill, tick-rounded). Fills: stop − 1 tick, bar open − 1 tick if gapped, $0.74/contract/side, same-bar ambiguity stop-first (target-first also reported). Objective, in order: (1) worst-session net loss and max drawdown of cumulative KX net P&L reduced by ≥ 0.5R; (2) paired Δnet $ vs original with session-bootstrap 95% CI not entirely below −0.05R per KX trade. Retire if (1) fails or P(target | retrace to entry after add) ≥ 0.35. Synthetic expectation: −$320 [−1,350, +670], worst session −$392 → −$272, 19 of 73 add trades affected.

Not proposed: (c) at +0.5R (CI excludes zero on the wrong side); (c') and (e) (indistinguishable from the original); (d) (raises portfolio drawdown).
