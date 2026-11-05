# S5 run output (SYNTHETIC development data, 2025-05-01 .. 2026-04-30)

## 1. Verification checklist (OBSERVED on SYNTHETIC development data)

### 1.1 Signal instrument (NQ) vs execution instrument (MNQ)

Bars: 97890 per instrument, 251 sessions (bars file), 242 sessions with trades, 242 sessions with signals.

| index | mean_pts | std_pts | max_abs_pts | pct_bars_nonzero |
|---|---|---|---|---|
| open | 0.00 | 0.14 | 0.25 | 33.40 |
| high | -0.08 | 0.12 | 0.25 | 33.40 |
| low | 0.08 | 0.12 | 0.25 | 33.40 |
| close | 0.00 | 0.14 | 0.25 | 33.40 | 

Entry fill minus bar open (adverse ticks), by instrument:

| ticks | vs MNQ open | vs NQ open |
|---|---|---|
| -0.00 | 44 | 0 |
| 1.00 | 228 | 332 |
| 2.00 | 60 | 0 | 

Market-order fills (ENTRY/ADD/TIME_EOD/STOP_GAP/MANUAL): 421. Equal to NQ open +1 tick adverse: 410; equal to MNQ open +1 tick adverse: 292. Excluding the 12 MANUAL fills, 409/409 equal NQ open +1 tick.
Dollar effect of the NQ pricing vs an MNQ-open+1-tick model, summed over the 409 non-MANUAL market fills: $-11.00 (sum of absolute per-fill differences $120.00).

### 1.2 Tick rounding

- Off-grid bar prices: {'MNQ': 0, 'NQ': 0}; off-grid fill prices: 0.
- initial_stop_px == entry -/+ round_tick(planned_stop_dist_pts): 332/332.
- KX initial_target_px == entry +/- round_tick(mult x raw dist): 240/240 (alternative mult x round_tick(dist): 148); PX target == planned_target_px: 92/92.
- Target multiples parsed from strategy_versions.csv: {'KX_ORB_v1': 2.0, 'KX_ORB_v2': 2.5, 'PX_REV_v1': None}; in signals.csv: {'KX_ORB_v1': [np.float64(2.0)], 'KX_ORB_v2': [np.float64(2.5)], 'PX_REV_v1': [np.float64(nan)]}.
- planned_risk_usd == contracts x UNROUNDED dist x $2: 332/332; max |planned_risk - risk at the tick-rounded stop| = $0.99 (1R is the planned, unrounded figure; the executable stop differs by <= 0.125 pt).
- Sizing floor($200/(dist x $2)) clipped [1,4] reproduces initial_contracts: 332/332.

### 1.3 Session cutoff

- Latest exit bar: 15:55:00; trades exiting at/after 15:55: 4, all TIME_EOD: True; TIME_EOD trades: 4, exit price == NQ 15:55 open +1 tick adverse: 4/4.
- Bars per session: [390] (09:30-15:59); last entry time 14:54:00; last signal time 14:54:00; latest add 11:04:00 (rule: before 12:00).
- Bracket fills in the 15:55-15:59 bars: 0.

### 1.4 Gaps through stops

| session | direction | entry_t | exit_t | initial_stop_px | nq_open | exit_px | gap_beyond_stop_ticks | fill_vs_open_ticks | stop_touched_in_entry_bar | net_pnl_usd |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-06-10 | SHORT | 10:45 | 10:56 | 20886.50 | 20895.00 | 20895.25 | 34.00 | 1.00 | False | -223.96 |
| 2025-10-29 | SHORT | 10:03 | 10:04 | 23261.25 | 23262.50 | 23262.75 | 5.00 | 1.00 | True | -91.92 |
| 2026-04-20 | LONG | 10:01 | 10:02 | 26751.00 | 26748.25 | 26748.00 | 11.00 | 1.00 | True | -182.94 | 

Fill convention observed: gap fills at the exit-bar open +1 tick adverse (the brief says 'bar open'; both are parameters). Two of the three gaps are really stop touches inside the entry bar that the generator ignored (bracket not armed until the next bar).

### 1.6 UTC/ET alignment

- fills.csv ts_utc -> ET equals trades.csv entry_ts: 332/332; entry fill time is a bar-open timestamp in bars_MNQ: 332/332; entry bar == signal bar (signal_ts = previous bar's close = this bar's open): 332/332.
- last EXIT fill time == trades.csv exit_ts: 332/332; ADD fill time == add_ts: 73/73.
- ET offsets present in bars: {'-0400': 64740, '-0500': 33150} (DST handled by tz conversion, not by a fixed offset); fills.csv hours in UTC: [14, 15, 16, 17, 18, 19, 20].

### 1.7 Costs on every leg

- fills.csv commission == $0.74 x qty on every fill: 810/810; trades.csv commission == 0.74 x 2 x (initial + added): 332/332; net == gross - commission: 332/332.
- gross from fills == trades.csv gross: 332/332. The replay charges `commission_per_side x qty` on every Fill object (entry, add, each leg's exit), so a policy that exits legs separately pays two exit commissions.

## 2. Reconciliation

## Reconciliation: original policy replay vs trades.csv (SYNTHETIC, n=332 trades, 242 sessions)

| index | reference model | generator model |
|---|---|---|
| trades | 332.00 | 332.00 |
| exact | 282.00 | 316.00 |
| time_mismatch | 20.00 | 16.00 |
| px_mismatch_any | 17.00 | 12.00 |
| px_mismatch_le_2ticks | 4.00 | 0.00 |
| reason_mismatch | 13.00 | 12.00 |
| add_mismatch | 1.00 | 1.00 |
| net_mismatch | 43.00 | 12.00 |
| sum_actual_minus_replay_usd | 55.48 | -877.52 |
| sum_abs_diff_usd | 1407.52 | 2320.52 | 

### Mismatches under the reference model, classified by the first fill-model convention that explains them

| explained_by | trades | sessions | sum_actual_minus_replay_usd | sum_abs_usd |
|---|---|---|---|---|
| reference | 282 | 216 | 0.00 | 0.00 |
| MKT fills priced off NQ (signal instrument) not MNQ | 27 | 27 | 5.50 | 13.50 |
| UNEXPLAINED: MANUAL exit at intra-bar price | 10 | 10 | 160.50 | 1282.50 |
| exact touch does NOT fire stop (penetration rule) | 5 | 5 | 0.00 | 0.00 |
| stop/target evaluated on NQ bars | 4 | 4 | 0.00 | 1.00 |
| bracket not armed in entry bar | 2 | 2 | -26.50 | 26.50 |
| add skipped when trade exits in the add bar | 1 | 1 | -32.02 | 32.02 |
| gapped-through limit filled at limit, not open | 1 | 1 | -52.00 | 52.00 | 

UNEXPLAINED: 10 trades, sum(actual - replay) = $160.5, sum|diff| = $1282.5

### Per-trade mismatch table (reference model)

| trade_id | session | family | direction | replay_exit | actual_exit | replay_reason | actual_reason | replay_px | actual_px | px_diff_ticks | replay_net | actual_net | net_diff_usd | explained_by |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2025-05-01 | KX | SHORT | 11:41 | 11:42 | STOP | MANUAL | 19934.25 | 19929.00 | 21.00 | -163.44 | -131.94 | 31.50 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 2 | 2025-05-01 | PX | SHORT | 15:55 | 15:55 | TIME_EOD | TIME_EOD | 20030.25 | 20030.00 | 1.00 | -86.48 | -85.98 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 15 | 2025-05-15 | KX | LONG | 10:41 | 10:20 | STOP | MANUAL | 20088.50 | 20121.75 | -133.00 | -197.94 | 1.56 | 199.50 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 23 | 2025-05-23 | KX | LONG | 11:15 | 11:19 | TARGET | TARGET | 20650.00 | 20650.00 | 0.00 | 443.08 | 442.58 | -0.50 | stop/target evaluated on NQ bars |
| 29 | 2025-05-30 | KX | SHORT | 11:14 | 10:23 | STOP | MANUAL | 21027.75 | 21011.50 | 65.00 | -187.92 | -57.92 | 130.00 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 39 | 2025-06-11 | KX | LONG | 11:14 | 11:14 | TARGET | TARGET | 20934.50 | 20934.50 | 0.00 | 507.06 | 506.56 | -0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 41 | 2025-06-12 | KX | LONG | 10:58 | 10:58 | TARGET | TARGET | 21725.25 | 21725.25 | 0.00 | 292.04 | 291.54 | -0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 43 | 2025-06-13 | KX | LONG | 10:43 | 10:43 | TARGET | TARGET | 21513.25 | 21513.25 | 0.00 | 332.56 | 333.06 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 51 | 2025-06-25 | KX | LONG | 10:29 | 10:29 | TARGET | TARGET | 23425.25 | 23425.25 | 0.00 | 402.58 | 403.08 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 65 | 2025-07-11 | KX | LONG | 10:20 | 10:21 | STOP | STOP | 22720.50 | 22720.50 | 0.00 | -190.96 | -190.96 | 0.00 | exact touch does NOT fire stop (penetration rule) |
| 76 | 2025-07-22 | PX | LONG | 15:55 | 15:55 | TIME_EOD | TIME_EOD | 21352.00 | 21352.25 | -1.00 | -0.48 | 0.02 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 80 | 2025-07-25 | KX | SHORT | 10:52 | 10:52 | TARGET | TARGET | 21159.00 | 21159.00 | 0.00 | 480.56 | 481.06 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 95 | 2025-08-08 | PX | LONG | 10:36 | 10:36 | TARGET | TARGET | 21414.75 | 21401.75 | 52.00 | 128.04 | 76.04 | -52.00 | gapped-through limit filled at limit, not open |
| 101 | 2025-08-15 | KX | SHORT | 10:34 | 10:34 | TARGET | TARGET | 20468.25 | 20468.25 | 0.00 | 394.08 | 394.58 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 108 | 2025-08-25 | PX | SHORT | 12:58 | 12:48 | STOP | MANUAL | 20795.25 | 20751.50 | 175.00 | -116.48 | -28.98 | 87.50 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 109 | 2025-08-26 | KX | LONG | 10:22 | 10:22 | TARGET | TARGET | 21003.25 | 21003.25 | 0.00 | 339.54 | 340.04 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 115 | 2025-09-02 | KX | SHORT | 10:16 | 10:16 | STOP_GAP | STOP | 21244.50 | 21244.50 | 0.00 | -155.92 | -155.92 | 0.00 | stop/target evaluated on NQ bars |
| 125 | 2025-09-10 | KX | SHORT | 10:42 | 10:43 | STOP | STOP | 21142.50 | 21142.50 | 0.00 | -173.92 | -173.92 | 0.00 | exact touch does NOT fire stop (penetration rule) |
| 127 | 2025-09-12 | KX | SHORT | 11:39 | 11:10 | STOP | MANUAL | 21080.00 | 21059.25 | 83.00 | -170.94 | -46.44 | 124.50 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 128 | 2025-09-15 | KX | LONG | 10:06 | 10:06 | TARGET | TARGET | 21464.50 | 21464.50 | 0.00 | 301.54 | 302.04 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 133 | 2025-09-19 | KX | LONG | 10:49 | 10:49 | TARGET | TARGET | 21884.25 | 21884.25 | 0.00 | 348.06 | 347.56 | -0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 157 | 2025-10-10 | PX | LONG | 15:55 | 15:55 | TIME_EOD | TIME_EOD | 22401.50 | 22401.75 | -1.00 | 17.52 | 18.02 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 163 | 2025-10-16 | PX | LONG | 15:35 | 15:13 | TARGET | MANUAL | 23036.00 | 23016.00 | 80.00 | 67.52 | 27.52 | -40.00 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 168 | 2025-10-22 | PX | LONG | 15:55 | 15:55 | TIME_EOD | TIME_EOD | 23719.00 | 23718.75 | 1.00 | -96.48 | -96.98 | -0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 174 | 2025-10-29 | KX | SHORT | 10:03 | 10:04 | STOP | STOP_GAP | 23261.50 | 23262.75 | -5.00 | -81.92 | -91.92 | -10.00 | bracket not armed in entry bar |
| 182 | 2025-11-06 | KX | SHORT | 10:30 | 10:30 | TARGET | TARGET | 23572.50 | 23572.50 | 0.00 | 410.06 | 410.56 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 193 | 2025-11-18 | KX | LONG | 10:25 | 10:18 | STOP | MANUAL | 22597.75 | 22605.50 | -31.00 | -297.42 | -235.42 | 62.00 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 201 | 2025-11-25 | KX | SHORT | 10:31 | 10:31 | TARGET | TARGET | 22311.75 | 22311.75 | 0.00 | 387.08 | 386.58 | -0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 210 | 2025-12-05 | KX | SHORT | 10:24 | 10:25 | STOP | STOP | 22103.75 | 22103.75 | 0.00 | -121.98 | -121.98 | 0.00 | exact touch does NOT fire stop (penetration rule) |
| 218 | 2025-12-12 | KX | LONG | 10:44 | 10:44 | TARGET | TARGET | 21940.25 | 21940.25 | 0.00 | 357.04 | 357.54 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 221 | 2025-12-16 | KX | LONG | 10:25 | 10:26 | TARGET | TARGET | 22514.50 | 22514.50 | 0.00 | 373.06 | 373.06 | 0.00 | stop/target evaluated on NQ bars |
| 224 | 2025-12-18 | KX | LONG | 10:19 | 10:19 | TARGET | TARGET | 22778.50 | 22778.50 | 0.00 | 390.58 | 358.56 | -32.02 | add skipped when trade exits in the add bar |
| 228 | 2025-12-22 | PX | LONG | 15:16 | 15:17 | STOP | STOP | 22559.00 | 22559.00 | 0.00 | -161.98 | -161.98 | 0.00 | exact touch does NOT fire stop (penetration rule) |
| 256 | 2026-01-23 | PX | SHORT | 10:09 | 10:11 | STOP | STOP | 21961.50 | 21961.50 | 0.00 | -195.92 | -195.92 | 0.00 | exact touch does NOT fire stop (penetration rule) |
| 259 | 2026-01-28 | KX | LONG | 10:25 | 10:25 | TARGET | TARGET | 22696.75 | 22696.75 | 0.00 | 504.58 | 505.08 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 263 | 2026-02-02 | KX | LONG | 10:45 | 10:45 | TARGET | TARGET | 23696.75 | 23696.75 | 0.00 | 588.56 | 589.06 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 264 | 2026-02-03 | KX | LONG | 10:48 | 10:48 | TARGET | TARGET | 23960.75 | 23960.75 | 0.00 | 456.06 | 455.56 | -0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 271 | 2026-02-11 | KX | SHORT | 11:35 | 11:35 | STOP | STOP | 22946.75 | 22946.75 | 0.00 | -352.44 | -351.94 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 272 | 2026-02-11 | PX | LONG | 11:41 | 11:32 | TARGET | MANUAL | 22972.75 | 22935.25 | 150.00 | 93.02 | 18.02 | -75.00 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 273 | 2026-02-12 | KX | LONG | 10:52 | 10:15 | TARGET | MANUAL | 23462.00 | 23406.25 | 223.00 | 462.08 | 16.08 | -446.00 | UNEXPLAINED: MANUAL exit at intra-bar price |
| 276 | 2026-02-17 | KX | SHORT | 10:23 | 10:23 | TARGET | TARGET | 23396.00 | 23396.00 | 0.00 | 541.58 | 542.08 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 277 | 2026-02-18 | KX | LONG | 10:15 | 10:15 | TARGET | TARGET | 23411.50 | 23411.50 | 0.00 | 552.58 | 553.08 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 294 | 2026-03-05 | KX | SHORT | 10:25 | 10:25 | TARGET | TARGET | 24146.25 | 24146.25 | 0.00 | 490.06 | 490.56 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 305 | 2026-03-18 | KX | LONG | 10:23 | 10:24 | TARGET | TARGET | 24451.25 | 24451.25 | 0.00 | 471.54 | 472.04 | 0.50 | stop/target evaluated on NQ bars |
| 312 | 2026-03-24 | KX | LONG | 11:22 | 11:22 | STOP | STOP | 24911.00 | 24911.00 | 0.00 | -320.42 | -320.92 | -0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 315 | 2026-03-26 | KX | LONG | 10:40 | 10:40 | TARGET | TARGET | 25262.50 | 25262.50 | 0.00 | 472.06 | 471.56 | -0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 318 | 2026-04-02 | KX | SHORT | 10:18 | 10:18 | TARGET | TARGET | 26251.25 | 26251.25 | 0.00 | 458.58 | 459.08 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 330 | 2026-04-16 | KX | LONG | 11:47 | 11:47 | TARGET | TARGET | 27032.00 | 27032.00 | 0.00 | 500.08 | 500.58 | 0.50 | MKT fills priced off NQ (signal instrument) not MNQ |
| 332 | 2026-04-20 | KX | LONG | 10:01 | 10:02 | STOP | STOP_GAP | 26750.75 | 26748.00 | 11.00 | -166.44 | -182.94 | -16.50 | bracket not armed in entry bar |
| 338 | 2026-04-23 | PX | LONG | 13:39 | 13:23 | STOP | MANUAL | 26482.50 | 26525.75 | -173.00 | -161.98 | -75.48 | 86.50 | UNEXPLAINED: MANUAL exit at intra-bar price | 

### Fill-level comparison vs fills.csv (generator model)

| index | count |
|---|---|
| actual_fills | 810 |
| replay_fills | 812 |
| paired | 810 |
| time_match | 792 |
| price_match | 796 |
| qty_match | 810 |
| side_match | 810 |
| commission_match | 810 |
| all_match | 792 | 

## 3. Same-bar stop/target touches and exact-touch ambiguity (SYNTHETIC)

- Original bracket, reference model: exit bars that touched both stop and target: 0/332; bars during holds whose range spanned both levels: 0. (Stop and target are >= 2.4R apart, wider than any 1-min bar here.)
- Exact-touch events on the actual exit level before penetration (baseline STOP/TARGET trades): 28 instrument-events on 19 trades; on NQ (the generator's trigger bars) 16 events of which the exit fired on the touch in 6. A 1-minute bar cannot say whether a level printed exactly at its extreme was traded through.

| trade_id | instrument | level | first_touch | first_penetration | actual_exit | fired_on_touch |
|---|---|---|---|---|---|---|
| 23 | NQ | TARGET | 11:15 | 11:19 | 11:19 | False |
| 34 | NQ | STOP | 10:21 | 10:22 | 10:21 | True |
| 35 | NQ | STOP | 10:33 | 10:34 | 10:33 | True |
| 57 | NQ | STOP | 11:09 | 11:10 | 11:09 | True |
| 65 | NQ | STOP | 10:20 | 10:21 | 10:21 | False |
| 102 | NQ | STOP | 10:03 |  | 10:03 | True |
| 125 | NQ | STOP | 10:42 | 10:43 | 10:43 | False |
| 131 | NQ | TARGET | 10:31 | 10:32 | 10:32 | False |
| 177 | NQ | STOP | 10:04 |  | 10:04 | True |
| 210 | NQ | STOP | 10:24 | 10:25 | 10:25 | False |
| 221 | NQ | TARGET | 10:25 | 10:26 | 10:26 | False |
| 227 | NQ | TARGET | 10:28 | 10:29 | 10:29 | False |
| 228 | NQ | STOP | 15:16 | 15:17 | 15:17 | False |
| 253 | NQ | STOP | 10:19 | 10:20 | 10:19 | True |
| 256 | NQ | STOP | 10:09 | 10:11 | 10:11 | False |
| 305 | NQ | TARGET | 10:23 | 10:24 | 10:24 | False | 

- Median 1-min bar range in the first 60 minutes after entry, in units of the stop distance: 0.25R (90th pct of trade medians 0.40R). Stop and target must be closer than about one bar range for same-bar ambiguity to arise.

Tightened-stop policies under each same-bar ordering (reference model otherwise; costs included):

| policy | ordering | trades | sessions | net_usd_sum | net_R_mean | ambiguous_exit_bars | bars_both_touched |
|---|---|---|---|---|---|---|---|
| stop_to_+0.3R_after_+0.8R | stop_first | 332 | 242 | 10716.98 | 0.21 | 0 | 0 |
| stop_to_+0.3R_after_+0.8R | target_first | 332 | 242 | 10716.98 | 0.21 | 0 | 0 |
| stop_to_+0.3R_after_+0.8R | worst | 332 | 242 | 10716.98 | 0.21 | 0 | 0 |
| stop_to_+0.3R_after_+0.8R | ohlc | 332 | 242 | 10716.98 | 0.21 | 0 | 0 |
| trail_0.1R_after_1.0R | stop_first | 332 | 242 | 3055.20 | 0.06 | 1 | 1 |
| trail_0.1R_after_1.0R | target_first | 332 | 242 | 3077.70 | 0.06 | 1 | 1 |
| trail_0.1R_after_1.0R | worst | 332 | 242 | 3055.20 | 0.06 | 1 | 1 |
| trail_0.1R_after_1.0R | ohlc | 332 | 242 | 3077.70 | 0.06 | 1 | 1 | 

`worst` equals `stop_first` whenever the live stop is on the adverse side of the target (always for a plain bracket); `ohlc` assumes the bar moved toward its close last. Same-bar ambiguity is rare on this synthetic path because bars are small relative to R; the exact-touch ambiguity above is the binding limitation.

## 4. Stage A demonstration: identical entries, paired (SYNTHETIC, costs included, reference fill model)

PX structural targets in R (1R = planned risk): median 0.70, IQR [0.54, 0.84], 61/92 below +0.8R, so a +0.8R breakeven can only arm on 31 PX trades. KX targets are 2.0R (v1) / 2.5R (v2) by construction.

### KX: per-policy summary (trades = 240, sessions = 240)

| policy | trades | sessions | net_usd_sum | net_usd_mean | net_R_mean | win_rate | max_dd_usd | eod_exits | avg_minutes |
|---|---|---|---|---|---|---|---|---|---|
| breakeven_0.8R | 240 | 240 | 9490.64 | 39.54 | 0.28 | 0.31 | -3178.32 | 0 | 19.30 |
| no_target_hold_eod | 240 | 240 | 72928.24 | 303.87 | 2.10 | 0.32 | -2408.86 | 78 | 134.10 |
| original | 240 | 240 | 12638.24 | 52.66 | 0.36 | 0.40 | -1993.64 | 0 | 24.70 |
| time_exit_30 | 240 | 240 | 8854.74 | 36.89 | 0.25 | 0.44 | -1534.64 | 0 | 16.70 | 

Paired difference vs original (alternative minus original, net of costs), whole-session bootstrap 95% CI:

| policy | trades | sessions | mean_dnet_usd | ci95_usd | mean_dnet_R | ci95_R | trades_changed | overlaps_next_entry | new_overlaps_vs_original |
|---|---|---|---|---|---|---|---|---|---|
| time_exit_30 | 240 | 240 | -15.76 | [-32.3, 0.8] | -0.10 | [-0.207, 0.003] | 63 | 9 | 0 |
| breakeven_0.8R | 240 | 240 | -13.12 | [-31.7, 4.3] | -0.08 | [-0.195, 0.033] | 53 | 0 | 0 |
| no_target_hold_eod | 240 | 240 | 251.21 | [161.7, 340.3] | 1.74 | [1.115, 2.338] | 97 | 32 | 15 | 

### PX: per-policy summary (trades = 92, sessions = 92)

| policy | trades | sessions | net_usd_sum | net_usd_mean | net_R_mean | win_rate | max_dd_usd | eod_exits | avg_minutes |
|---|---|---|---|---|---|---|---|---|---|
| breakeven_0.8R | 92 | 92 | 2675.98 | 29.09 | 0.19 | 0.71 | -527.62 | 4 | 28.10 |
| no_target_hold_eod | 92 | 92 | 15241.48 | 165.67 | 1.07 | 0.56 | -517.88 | 58 | 162.40 |
| original | 92 | 92 | 2675.98 | 29.09 | 0.19 | 0.71 | -527.62 | 4 | 28.10 |
| time_exit_30 | 92 | 92 | 1600.48 | 17.40 | 0.11 | 0.65 | -387.40 | 0 | 17.50 | 

Paired difference vs original (alternative minus original, net of costs), whole-session bootstrap 95% CI:

| policy | trades | sessions | mean_dnet_usd | ci95_usd | mean_dnet_R | ci95_R | trades_changed | overlaps_next_entry | new_overlaps_vs_original |
|---|---|---|---|---|---|---|---|---|---|
| time_exit_30 | 92 | 92 | -11.69 | [-21.8, -2.5] | -0.08 | [-0.146, -0.020] | 26 | 0 | 0 |
| breakeven_0.8R | 92 | 92 | 0.00 | [0.0, 0.0] | 0.00 | [0.000, 0.000] | 0 | 0 | 0 |
| no_target_hold_eod | 92 | 92 | 136.58 | [76.7, 198.0] | 0.88 | [0.482, 1.282] | 64 | 0 | 0 | 

## 5. Stage B demonstration: chronological replay from signals.csv (SYNTHETIC)

| policy | fill_model | exit_frees_same_bar | signals | executed | rejected | executed_flag_agrees_with_export | net_usd_sum | journal_net_usd_sum | sessions |
|---|---|---|---|---|---|---|---|---|---|
| original | generator | True | 346 | 328 | 18 | 342/346 | 16390.04 | 15369.70 | 242 |
| original | reference | False | 346 | 327 | 19 | 341/346 | 15664.46 | 15369.70 | 242 |
| time_exit_30 | reference | False | 346 | 332 | 14 | 338/346 | 10624.62 | 15369.70 | 242 |
| hold_to_eod_no_target | reference | False | 346 | 317 | 29 | 331/346 | 85546.24 | 15369.70 | 242 | 

Signals whose executed flag differs from the export under the generator model (each is downstream of an exit the replay cannot reproduce: a MANUAL exit or an exact-touch stop that fired in the journal):

| signal_id | session | signal_t | executed_in_export | replay_executed | blocking_replay_trade_exit | journal_exit_of_that_trade |
|---|---|---|---|---|---|---|
| 35 | 2025-06-04 | 10:21 | True | False | 10:22 STOP | 10:21 STOP |
| 58 | 2025-07-03 | 11:09 | True | False | 11:10 STOP | 11:09 STOP |
| 194 | 2025-11-18 | 10:19 | True | False | 10:25 STOP | 10:18 MANUAL |
| 274 | 2026-02-12 | 10:31 | True | False | 10:52 TARGET | 10:15 MANUAL | 

Stage B entries are re-priced from the bars (open +1 tick), so even the original policy differs from the journal by the MANUAL exits and the fill conventions listed in section 2; the executed/rejected set is the check that the position-limit logic is right. Longer holds (`hold_to_eod_no_target`) change which later signals are blocked.

## 6. Fill-assumption variants, original policy, Stage A entries (SYNTHETIC, net of costs)

| variant | trades | sessions | net_usd_sum | net_R_mean | stop_exits | target_exits | gaps |
|---|---|---|---|---|---|---|---|
| reference | 332 | 242 | 15314.22 | 0.31 | 167 | 161 | 2 |
| slippage 0 ticks (MKT, STP, gap) | 332 | 242 | 15549.22 | 0.32 | 167 | 161 | 2 |
| slippage 2 ticks (MKT, STP, gap) | 332 | 242 | 15079.22 | 0.31 | 167 | 161 | 2 |
| gap fill at open (0 extra ticks) | 332 | 242 | 15317.22 | 0.31 | 167 | 161 | 2 |
| stop fires only on penetration | 332 | 242 | 15830.22 | 0.32 | 166 | 162 | 1 |
| target fills on touch | 332 | 242 | 15314.22 | 0.31 | 167 | 161 | 2 |
| bracket not armed in entry bar | 332 | 242 | 15286.22 | 0.31 | 167 | 161 | 4 |
| triggers + MKT prices on NQ bars | 332 | 242 | 15318.22 | 0.31 | 167 | 161 | 1 |
| same-bar: target_first | 332 | 242 | 15314.22 | 0.31 | 167 | 161 | 2 |
| same-bar: stop_first | 332 | 242 | 15314.22 | 0.31 | 167 | 161 | 2 | 

Entry fills are the journal's (Stage A), so entry slippage is not varied here; Stage B re-prices entries and is affected by `slippage_ticks_market` on both sides.

