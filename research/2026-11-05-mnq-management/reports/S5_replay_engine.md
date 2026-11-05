# S5 — Execution and replay engineer: reference replay engine and reconciliation

**Everything below is computed on the SYNTHETIC development set** (`data/synthetic/`, 2025-05-01 → 2026-04-30, 332 trades, 242 sessions with trades, 251 bar sessions). No number here is market evidence. What transfers to the real export is the code (`src/S5/replay.py`, `src/S5/reconcile.py`, `src/S5/run.py`, `src/S5/README.md`), the field list, and the fill-assumption grid in section 8. Dollar figures are net of $0.74/contract/side commission unless stated; R = net P&L / `planned_risk_usd` (initial contracts × unrounded stop distance × $2, fixed per trade).

## 1. Strongest finding and the decision it changes

**OBSERVED.** The original policy reconstructed from `strategy_versions.csv` + bars reproduces the journal to the tick for **282/332 trades under a realistic MNQ fill model and 316/332 under the generator's own conventions**. Every remaining difference but one class is explained by a named fill convention (instrument used to price market orders, touch-vs-penetration, bracket not armed in the entry bar, gap-limit fill, one skipped add). The only **unexplained** class is **10 MANUAL exits** at intra-bar prices: journal − replay = **+$160.50 net** (sum of absolute differences $1,282.50, 10 trades, 10 sessions). The engine is therefore fit to run the holdout and Stage B.

The decision it changes: **every pre-registered policy must be reported under two stop-trigger conventions (touch and penetration), not one.** In the baseline, 16 exact-touch events on NQ (a level printed exactly at a bar extreme without penetration) resolved 6 fired : 10 did not; two of them (trades 102, 177) decide whether a trade is a 2R winner or a 1R loser and together swing **$1,038 = 6.8 % of the baseline's $15.3k net** (section 3, "stop fires only on penetration"). A 1-minute bar cannot resolve this, and a tightened stop touches levels more often than the original does.

**OBSERVED (engine validation, not a recommendation).** A stop-only, no-target, flat-at-15:55 policy earns +1.74R/trade on KX (95 % session-bootstrap CI [1.12, 2.34], 240 trades/240 sessions) and +0.88R on PX. That is the generator's planted post-entry drift (136 EOD exits averaging +6.1R). Any specialist who "finds" that removing the target helps is reading the generator, not a market; on the real export this is exactly the kind of result that must survive Stage B and the fill grid before anyone believes it.

## 2. Evidence (labelled) and the strongest competing explanation

Verification checklist, all **OBSERVED** on the synthetic export (full output in `src/S5/out/run_output.md`, section 1):

| check | result |
|---|---|
| Signal (NQ) vs execution (MNQ) instrument | NQ − MNQ basis: mean 0.00 pt, sd 0.14, max abs 0.25 pt, 33 % of bars differ. **Every market-order fill (409/409 non-MANUAL ENTRY/ADD/TIME_EOD/STOP_GAP) equals the NQ open + 1 tick adverse**, not the MNQ open (only 292/421 match MNQ + 1 tick). Dollar effect vs an MNQ-open+1-tick model: −$11.00 over 409 fills (Σabs $120). Immaterial, but the fills file was priced off the signal instrument. |
| Tick rounding | 0 off-grid bar or fill prices. `initial_stop_px = entry ∓ round_tick(raw dist)` 332/332; KX target = entry ± round_tick(mult × raw dist) 240/240 (mult × round_tick(dist) fails 92); PX target = `planned_target_px` 92/92. `planned_risk_usd` uses the unrounded distance (max gap to executable risk $0.99). Target multiples parsed from `strategy_versions.csv` (2.0 / 2.5) equal those in `signals.csv`. Sizing rule reproduces contracts 332/332. |
| Session cutoff | All 4 exits at/after 15:55 are TIME_EOD at the 15:55 open (NQ open + 1 tick, 4/4); no bracket fills in 15:55–15:59; last entry 14:54; latest add 11:04 (rule: before 12:00). |
| Gaps through stops | 3 STOP_GAP (5, 11, 34 ticks beyond the stop), filled at the exit-bar open + 1 tick adverse (brief says "bar open"; both are parameters). **2 of 3 are stop touches inside the entry bar that the generator ignored** — the bracket was not armed until the next bar. |
| Same-bar stop + target | Original bracket: 0/332 exit bars touched both; 0 bars during holds spanned both levels (median bar range 0.25R, 90th pct 0.40R; the bracket is ≥ 2.4R wide). For a tightened stop see section 3 table. |
| UTC/ET alignment | `fills.ts_utc` → ET equals `trades.entry_ts` 332/332; entry fill time is the entry bar's open 332/332; entry bar = signal bar (`signal_ts` is the previous close = this open) 332/332; last EXIT fill = `exit_ts` 332/332; ADD = `add_ts` 73/73; both −04:00 and −05:00 offsets present (DST crossed). |
| Costs on every leg | `commission = 0.74 × qty` on 810/810 fills; trade commission = 0.74 × 2 × (initial + added) 332/332; gross from fills = journal gross 332/332. The replay charges each `Fill` (entry, add, every leg exit). |
| Pyramiding rule | Add trigger = raw (unrounded) stop distance on the closed bar's extreme, bars 1–20 after entry, add at the next open, before 12:00, one attempt: 73/73 add times and prices reproduced (73/73 at NQ open + 1 tick); 1 add skipped by the generator because the trade exited in the add bar (trade 224). |
| Position limit (Stage B) | Reject iff open contracts + planned > 4, no partial sizing; a trade exiting in bar *t* frees its contracts for a signal at bar *t* (optimistic look-ahead, 5 cases). Reproduces the executed flag for 342/346 signals; the 4 differences are downstream of 2 MANUAL exits and 2 exact-touch stops (section 3). |

**Strongest competing explanation** for the "unexplained" MANUAL class: a hidden rule rather than discretion — 8/10 MANUAL exits occur 14–23 minutes after entry, 7/10 while under water (−0.24R to −0.81R by the exit print). **HYPOTHESIS**, untestable here: a 1-minute bar contains the fill price but not the rule that produced it; on the real export the trader must label each MANUAL exit with its reason or the class stays unexplained. For the exact-touch class the competing explanation is that the generator evaluated an unrounded continuous path and rounded the bars afterwards; the engine's `touch`/`penetrate` switch brackets both possibilities.

## 3. Reproducible check (code path + pasted output)

```
python3 src/S5/reconcile.py            # reconciliation only (≈10 s)
python3 src/S5/run.py                  # all tables below → src/S5/out/run_output.md (≈60 s)
```

Reference fill model = MNQ bars for triggers and prices, stop fires on a touch, limit needs penetration, bracket live in the entry bar, 1 tick slippage on MKT/STP, gap = open + 1 tick, same-bar = worst. Generator model = NQ bars, penetration for both, bracket armed from the next bar, gapped limit at the limit, add skipped if the trade exits in the add bar.

### Reconciliation: original policy replay vs `trades.csv` (SYNTHETIC, 332 trades, 242 sessions)

| | reference model | generator model |
|---|---|---|
| trades | 332 | 332 |
| exact (time, price, reason, add, net) | 282 | 316 |
| exit-time mismatch | 20 | 16 |
| exit-price mismatch (any) | 17 | 12 |
| of which ≤ 2 ticks | 4 | 0 |
| exit-reason mismatch | 13 | 12 |
| add mismatch | 1 | 1 |
| net mismatch | 43 | 12 |
| Σ (journal − replay) net $ | +55.48 | −877.52 |
| Σ \|journal − replay\| $ | 1,407.52 | 2,320.52 |

Mismatches under the reference model, classified by the first fill-model convention under which the trade matches exactly:

| explained_by | trades | sessions | Σ(journal − replay) $ | Σ\|diff\| $ |
|---|---|---|---|---|
| reference (exact) | 282 | 216 | 0.00 | 0.00 |
| MKT fills priced off NQ (signal instrument) not MNQ | 27 | 27 | +5.50 | 13.50 |
| **UNEXPLAINED: MANUAL exit at intra-bar price** | **10** | **10** | **+160.50** | **1,282.50** |
| exact touch does NOT fire stop (penetration rule) | 5 | 5 | 0.00 | 0.00 |
| stop/target evaluated on NQ bars | 4 | 4 | 0.00 | 1.00 |
| bracket not armed in entry bar | 2 | 2 | −26.50 | 26.50 |
| add skipped when trade exits in the add bar | 1 | 1 | −32.02 | 32.02 |
| gapped-through limit filled at limit, not open | 1 | 1 | −52.00 | 52.00 |

The generator model's 16 mismatches are the 10 MANUAL exits plus 6 exact-touch stops that fired in the journal (34, 35, 57, 253 at $0 difference; 102 and 177 at −$516.00 and −$522.02, replay better than journal).

Per-trade mismatch table (reference model; `net_diff` = journal − replay):

| trade | session | fam | dir | replay exit | actual exit | replay reason | actual reason | replay px | actual px | Δticks | replay net | actual net | net_diff | explained_by |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2025-05-01 | KX | SHORT | 11:41 | 11:42 | STOP | MANUAL | 19934.25 | 19929.00 | 21 | −163.44 | −131.94 | +31.50 | UNEXPLAINED: MANUAL intra-bar |
| 2 | 2025-05-01 | PX | SHORT | 15:55 | 15:55 | TIME_EOD | TIME_EOD | 20030.25 | 20030.00 | 1 | −86.48 | −85.98 | +0.50 | MKT priced off NQ |
| 15 | 2025-05-15 | KX | LONG | 10:41 | 10:20 | STOP | MANUAL | 20088.50 | 20121.75 | −133 | −197.94 | 1.56 | +199.50 | UNEXPLAINED: MANUAL intra-bar |
| 23 | 2025-05-23 | KX | LONG | 11:15 | 11:19 | TARGET | TARGET | 20650.00 | 20650.00 | 0 | 443.08 | 442.58 | −0.50 | triggers on NQ bars |
| 29 | 2025-05-30 | KX | SHORT | 11:14 | 10:23 | STOP | MANUAL | 21027.75 | 21011.50 | 65 | −187.92 | −57.92 | +130.00 | UNEXPLAINED: MANUAL intra-bar |
| 39 | 2025-06-11 | KX | LONG | 11:14 | 11:14 | TARGET | TARGET | 20934.50 | 20934.50 | 0 | 507.06 | 506.56 | −0.50 | MKT priced off NQ (add) |
| 41 | 2025-06-12 | KX | LONG | 10:58 | 10:58 | TARGET | TARGET | 21725.25 | 21725.25 | 0 | 292.04 | 291.54 | −0.50 | MKT priced off NQ (add) |
| 43 | 2025-06-13 | KX | LONG | 10:43 | 10:43 | TARGET | TARGET | 21513.25 | 21513.25 | 0 | 332.56 | 333.06 | +0.50 | MKT priced off NQ (add) |
| 51 | 2025-06-25 | KX | LONG | 10:29 | 10:29 | TARGET | TARGET | 23425.25 | 23425.25 | 0 | 402.58 | 403.08 | +0.50 | MKT priced off NQ (add) |
| 65 | 2025-07-11 | KX | LONG | 10:20 | 10:21 | STOP | STOP | 22720.50 | 22720.50 | 0 | −190.96 | −190.96 | 0.00 | exact touch did not fire |
| 76 | 2025-07-22 | PX | LONG | 15:55 | 15:55 | TIME_EOD | TIME_EOD | 21352.00 | 21352.25 | −1 | −0.48 | 0.02 | +0.50 | MKT priced off NQ |
| 80 | 2025-07-25 | KX | SHORT | 10:52 | 10:52 | TARGET | TARGET | 21159.00 | 21159.00 | 0 | 480.56 | 481.06 | +0.50 | MKT priced off NQ (add) |
| 95 | 2025-08-08 | PX | LONG | 10:36 | 10:36 | TARGET | TARGET | 21414.75 | 21401.75 | 52 | 128.04 | 76.04 | −52.00 | gapped limit filled at limit |
| 101 | 2025-08-15 | KX | SHORT | 10:34 | 10:34 | TARGET | TARGET | 20468.25 | 20468.25 | 0 | 394.08 | 394.58 | +0.50 | MKT priced off NQ (add) |
| 108 | 2025-08-25 | PX | SHORT | 12:58 | 12:48 | STOP | MANUAL | 20795.25 | 20751.50 | 175 | −116.48 | −28.98 | +87.50 | UNEXPLAINED: MANUAL intra-bar |
| 109 | 2025-08-26 | KX | LONG | 10:22 | 10:22 | TARGET | TARGET | 21003.25 | 21003.25 | 0 | 339.54 | 340.04 | +0.50 | MKT priced off NQ (add) |
| 115 | 2025-09-02 | KX | SHORT | 10:16 | 10:16 | STOP_GAP | STOP | 21244.50 | 21244.50 | 0 | −155.92 | −155.92 | 0.00 | triggers on NQ bars |
| 125 | 2025-09-10 | KX | SHORT | 10:42 | 10:43 | STOP | STOP | 21142.50 | 21142.50 | 0 | −173.92 | −173.92 | 0.00 | exact touch did not fire |
| 127 | 2025-09-12 | KX | SHORT | 11:39 | 11:10 | STOP | MANUAL | 21080.00 | 21059.25 | 83 | −170.94 | −46.44 | +124.50 | UNEXPLAINED: MANUAL intra-bar |
| 128 | 2025-09-15 | KX | LONG | 10:06 | 10:06 | TARGET | TARGET | 21464.50 | 21464.50 | 0 | 301.54 | 302.04 | +0.50 | MKT priced off NQ (add) |
| 133 | 2025-09-19 | KX | LONG | 10:49 | 10:49 | TARGET | TARGET | 21884.25 | 21884.25 | 0 | 348.06 | 347.56 | −0.50 | MKT priced off NQ (add) |
| 157 | 2025-10-10 | PX | LONG | 15:55 | 15:55 | TIME_EOD | TIME_EOD | 22401.50 | 22401.75 | −1 | 17.52 | 18.02 | +0.50 | MKT priced off NQ |
| 163 | 2025-10-16 | PX | LONG | 15:35 | 15:13 | TARGET | MANUAL | 23036.00 | 23016.00 | 80 | 67.52 | 27.52 | −40.00 | UNEXPLAINED: MANUAL intra-bar |
| 168 | 2025-10-22 | PX | LONG | 15:55 | 15:55 | TIME_EOD | TIME_EOD | 23719.00 | 23718.75 | 1 | −96.48 | −96.98 | −0.50 | MKT priced off NQ |
| 174 | 2025-10-29 | KX | SHORT | 10:03 | 10:04 | STOP | STOP_GAP | 23261.50 | 23262.75 | −5 | −81.92 | −91.92 | −10.00 | bracket not armed in entry bar |
| 182 | 2025-11-06 | KX | SHORT | 10:30 | 10:30 | TARGET | TARGET | 23572.50 | 23572.50 | 0 | 410.06 | 410.56 | +0.50 | MKT priced off NQ (add) |
| 193 | 2025-11-18 | KX | LONG | 10:25 | 10:18 | STOP | MANUAL | 22597.75 | 22605.50 | −31 | −297.42 | −235.42 | +62.00 | UNEXPLAINED: MANUAL intra-bar |
| 201 | 2025-11-25 | KX | SHORT | 10:31 | 10:31 | TARGET | TARGET | 22311.75 | 22311.75 | 0 | 387.08 | 386.58 | −0.50 | MKT priced off NQ (add) |
| 210 | 2025-12-05 | KX | SHORT | 10:24 | 10:25 | STOP | STOP | 22103.75 | 22103.75 | 0 | −121.98 | −121.98 | 0.00 | exact touch did not fire |
| 218 | 2025-12-12 | KX | LONG | 10:44 | 10:44 | TARGET | TARGET | 21940.25 | 21940.25 | 0 | 357.04 | 357.54 | +0.50 | MKT priced off NQ (add) |
| 221 | 2025-12-16 | KX | LONG | 10:25 | 10:26 | TARGET | TARGET | 22514.50 | 22514.50 | 0 | 373.06 | 373.06 | 0.00 | triggers on NQ bars |
| 224 | 2025-12-18 | KX | LONG | 10:19 | 10:19 | TARGET | TARGET | 22778.50 | 22778.50 | 0 | 390.58 | 358.56 | −32.02 | add skipped in exit bar |
| 228 | 2025-12-22 | PX | LONG | 15:16 | 15:17 | STOP | STOP | 22559.00 | 22559.00 | 0 | −161.98 | −161.98 | 0.00 | exact touch did not fire |
| 256 | 2026-01-23 | PX | SHORT | 10:09 | 10:11 | STOP | STOP | 21961.50 | 21961.50 | 0 | −195.92 | −195.92 | 0.00 | exact touch did not fire |
| 259 | 2026-01-28 | KX | LONG | 10:25 | 10:25 | TARGET | TARGET | 22696.75 | 22696.75 | 0 | 504.58 | 505.08 | +0.50 | MKT priced off NQ (add) |
| 263 | 2026-02-02 | KX | LONG | 10:45 | 10:45 | TARGET | TARGET | 23696.75 | 23696.75 | 0 | 588.56 | 589.06 | +0.50 | MKT priced off NQ (add) |
| 264 | 2026-02-03 | KX | LONG | 10:48 | 10:48 | TARGET | TARGET | 23960.75 | 23960.75 | 0 | 456.06 | 455.56 | −0.50 | MKT priced off NQ (add) |
| 271 | 2026-02-11 | KX | SHORT | 11:35 | 11:35 | STOP | STOP | 22946.75 | 22946.75 | 0 | −352.44 | −351.94 | +0.50 | MKT priced off NQ (add) |
| 272 | 2026-02-11 | PX | LONG | 11:41 | 11:32 | TARGET | MANUAL | 22972.75 | 22935.25 | 150 | 93.02 | 18.02 | −75.00 | UNEXPLAINED: MANUAL intra-bar |
| 273 | 2026-02-12 | KX | LONG | 10:52 | 10:15 | TARGET | MANUAL | 23462.00 | 23406.25 | 223 | 462.08 | 16.08 | −446.00 | UNEXPLAINED: MANUAL intra-bar |
| 276 | 2026-02-17 | KX | SHORT | 10:23 | 10:23 | TARGET | TARGET | 23396.00 | 23396.00 | 0 | 541.58 | 542.08 | +0.50 | MKT priced off NQ (add) |
| 277 | 2026-02-18 | KX | LONG | 10:15 | 10:15 | TARGET | TARGET | 23411.50 | 23411.50 | 0 | 552.58 | 553.08 | +0.50 | MKT priced off NQ (add) |
| 294 | 2026-03-05 | KX | SHORT | 10:25 | 10:25 | TARGET | TARGET | 24146.25 | 24146.25 | 0 | 490.06 | 490.56 | +0.50 | MKT priced off NQ (add) |
| 305 | 2026-03-18 | KX | LONG | 10:23 | 10:24 | TARGET | TARGET | 24451.25 | 24451.25 | 0 | 471.54 | 472.04 | +0.50 | triggers on NQ bars |
| 312 | 2026-03-24 | KX | LONG | 11:22 | 11:22 | STOP | STOP | 24911.00 | 24911.00 | 0 | −320.42 | −320.92 | −0.50 | MKT priced off NQ (add) |
| 315 | 2026-03-26 | KX | LONG | 10:40 | 10:40 | TARGET | TARGET | 25262.50 | 25262.50 | 0 | 472.06 | 471.56 | −0.50 | MKT priced off NQ (add) |
| 318 | 2026-04-02 | KX | SHORT | 10:18 | 10:18 | TARGET | TARGET | 26251.25 | 26251.25 | 0 | 458.58 | 459.08 | +0.50 | MKT priced off NQ (add) |
| 330 | 2026-04-16 | KX | LONG | 11:47 | 11:47 | TARGET | TARGET | 27032.00 | 27032.00 | 0 | 500.08 | 500.58 | +0.50 | MKT priced off NQ (add) |
| 332 | 2026-04-20 | KX | LONG | 10:01 | 10:02 | STOP | STOP_GAP | 26750.75 | 26748.00 | 11 | −166.44 | −182.94 | −16.50 | bracket not armed in entry bar |
| 338 | 2026-04-23 | PX | LONG | 13:39 | 13:23 | STOP | MANUAL | 26482.50 | 26525.75 | −173 | −161.98 | −75.48 | +86.50 | UNEXPLAINED: MANUAL intra-bar |

Fill-level comparison with `fills.csv` (generator model): 810 journal fills, 810 paired on (trade, leg, role); qty, side and commission match 810/810; time 792/810 and price 796/810 (the 18 fills of the 10 MANUAL trades and the 2 exact-touch trades 102/177, plus 2 replay-only fills where 177 added and exited later).

### Exact-touch ambiguity and same-bar ordering (SYNTHETIC)

Exact-touch events on the actual exit level before penetration, NQ bars: 16 events on 16 trades, exit fired on the touch in 6 (34, 35, 57, 102, 177, 253), did not in 10 (23, 65, 125, 131, 210, 221, 227, 228, 256, 305). Median bar range in the first 60 minutes after entry = 0.25R (90th percentile of per-trade medians 0.40R), so stop and target must be < ~0.4R apart for one bar to contain both:

| policy | ordering | trades | sessions | net $ | mean R | ambiguous exit bars |
|---|---|---|---|---|---|---|
| stop → +0.3R after +0.8R (brief's scenario) | stop_first / target_first / worst / ohlc | 332 | 242 | 10,716.98 | 0.21 | 0 |
| trail 0.1R after +1.0R (forced case) | stop_first = worst | 332 | 242 | 3,055.20 | 0.06 | 1 |
| trail 0.1R after +1.0R | target_first = ohlc | 332 | 242 | 3,077.70 | 0.06 | 1 |

### Stage A demonstration (identical entries, paired, reference model, costs included)

Policies: `original`; `time_exit_30` (exit all at the open of minute 30, bracket live until then); `breakeven_0.8R` (after a closed bar's extreme ≥ +0.8R, stop to entry, all legs); `no_target_hold_eod` (validation only). PX structural targets: median 0.70R, IQR [0.54, 0.84], 61/92 below +0.8R, so a +0.8R breakeven can arm on only 31 PX trades (and changed none).

KX (240 trades, 240 sessions):

| policy | net $ | mean $ | mean R | win rate | max DD $ | EOD exits | avg min |
|---|---|---|---|---|---|---|---|
| original | 12,638.24 | 52.66 | 0.36 | 0.40 | −1,993.64 | 0 | 24.7 |
| time_exit_30 | 8,854.74 | 36.89 | 0.25 | 0.44 | −1,534.64 | 0 | 16.7 |
| breakeven_0.8R | 9,490.64 | 39.54 | 0.28 | 0.31 | −3,178.32 | 0 | 19.3 |
| no_target_hold_eod | 72,928.24 | 303.87 | 2.10 | 0.32 | −2,408.86 | 78 | 134.1 |

| paired vs original (KX) | mean Δ$ | 95 % CI (sessions) | mean ΔR | 95 % CI | trades changed | overlaps next entry (new) |
|---|---|---|---|---|---|---|
| time_exit_30 | −15.76 | [−32.3, 0.8] | −0.10 | [−0.207, 0.003] | 63 | 9 (0) |
| breakeven_0.8R | −13.12 | [−31.7, 4.3] | −0.08 | [−0.195, 0.033] | 53 | 0 (0) |
| no_target_hold_eod | +251.21 | [161.7, 340.3] | +1.74 | [1.115, 2.338] | 97 | 32 (15) |

PX (92 trades, 92 sessions):

| policy | net $ | mean $ | mean R | win rate | max DD $ | EOD exits | avg min |
|---|---|---|---|---|---|---|---|
| original | 2,675.98 | 29.09 | 0.19 | 0.71 | −527.62 | 4 | 28.1 |
| time_exit_30 | 1,600.48 | 17.40 | 0.11 | 0.65 | −387.40 | 0 | 17.5 |
| breakeven_0.8R | 2,675.98 | 29.09 | 0.19 | 0.71 | −527.62 | 4 | 28.1 |
| no_target_hold_eod | 15,241.48 | 165.67 | 1.07 | 0.56 | −517.88 | 58 | 162.4 |

| paired vs original (PX) | mean Δ$ | 95 % CI (sessions) | mean ΔR | 95 % CI | trades changed | overlaps next entry (new) |
|---|---|---|---|---|---|---|
| time_exit_30 | −11.69 | [−21.8, −2.5] | −0.08 | [−0.146, −0.020] | 26 | 0 (0) |
| breakeven_0.8R | 0.00 | [0.0, 0.0] | 0.00 | — | 0 | 0 (0) |
| no_target_hold_eod | +136.58 | [76.7, 198.0] | +0.88 | [0.482, 1.282] | 64 | 0 (0) |

### Stage B demonstration (chronological, `signals.csv` incl. 14 rejected, limit 4, pyramiding, 15:55 flat)

| policy | fill model | exit frees same bar | executed | rejected | executed flag = export | net $ | journal net $ |
|---|---|---|---|---|---|---|---|
| original | generator | yes | 328 | 18 | 342/346 | 16,390.04 | 15,369.70 |
| original | reference | no | 327 | 19 | 341/346 | 15,664.46 | 15,369.70 |
| time_exit_30 | reference | no | 332 | 14 | 338/346 | 10,624.62 | 15,369.70 |
| no_target_hold_eod | reference | no | 317 | 29 | 331/346 | 85,546.24 | 15,369.70 |

The 4 flag differences under the generator model: signals 35 and 58 (journal trade stopped on an exact touch at 10:21 / 11:09, replay one bar later), 194 and 274 (journal MANUAL exits at 10:18 / 10:15 freed the contracts). Stage B re-prices entries from the bars, so even the original differs from the journal by the MANUAL class and conventions above; the executed set is the position-limit check.

## 4. When following this would make the decision worse

Policies the 1-minute data are **too coarse to distinguish** — the engine will run them but the result is an artefact of a convention, not evidence:

1. **Any two policies whose difference is a stop level touched exactly** (touch vs penetration): 16 events in 332 baseline trades, 6:10 resolution; every tightened stop raises the rate.
2. **Sub-minute trailing stops** (trail distance < one bar range, ≈ 0.25R here): the fill depends on the intra-bar path; the engine only ratchets at bar opens off closed extremes.
3. **Stop and target inside one bar** (gap < ~0.4R): ordering parameter decides; 1 case already at a 0.1R trail.
4. **Same-minute exit-and-re-enter** (stop-and-reverse, re-entry on the next signal in the same bar): the position-limit result depends on whether contracts free in the exit bar (5 look-ahead cases in the export).
5. **Market exits "at the close" vs "at the next open"**: the engine fills at the next bar's open; a 15:54 close exit and a 15:55 open exit differ by one bar's gap.
6. **Intra-bar discretionary exits** (the MANUAL class): not reproducible; a policy that is "like what the trader does" cannot be validated.
7. **Limit fills on a gap** (open beyond the limit): price improvement vs limit price, $52 on one trade here.
8. **Entry-bar bracket**: whether the stop is live during the remainder of the entry bar changed 2 trades by $26.50.

Following the engine blindly makes the decision worse when a candidate's claimed edge is smaller than its spread across section 8's grid, or when it is driven by EOD holds under the generator's planted drift.

## 5. Cheapest decisive test on the user's real data, and the result that retires the idea

Run `python3 src/S5/reconcile.py data/real` on the export (minutes). The idea "we can replay management policies on this export" is **retired** if exact matches < 90 % of trades, or if the unexplained dollar sum exceeds 10 % of the journal's net, or if any mismatch class other than MANUAL is unexplained after the ladder. For the exact-touch problem the decisive test is cheap too: for every trade whose exit bar printed the level exactly, pull the platform's own fill time (seconds) from `fills.csv`; if second-level fill times exist, the touch question is answered per trade and the two conventions collapse to one.

## 6. What the real export must contain for this test (exact fields)

`bars_MNQ_1min.csv` (`ts` = bar open, ISO 8601 with offset, `open, high, low, close, volume`, every RTH session through 15:59); `bars_NQ_1min.csv` optional (basis check); `signals.csv` (`signal_id, strategy, family, signal_instrument, exec_instrument, signal_ts, direction, ref_level, ref_width, planned_stop_dist_pts` unrounded, `planned_target_mult_R, planned_contracts, planned_risk_usd, executed, reject_reason, planned_target_px, planned_stop_px`; **rejected signals included**); `trades.csv` (`trade_id, signal_id, session, strategy, family, direction, entry_ts, entry_px, initial_contracts, added_contracts, add_px, add_ts, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason ∈ {STOP, TARGET, STOP_GAP, TIME_EOD, MANUAL}, gross_pnl_usd, commission_usd, net_pnl_usd`; timestamps = bar-open of the fill bar); `fills.csv` (`fill_id, trade_id, leg_id, ts_utc` with seconds if the platform has them, `side, qty, price, order_type, fill_role, exit_reason, commission`; one row per leg); `strategy_versions.csv` (`strategy, family, valid_from, valid_to, signal_instrument, entry, stop, target` with the multiple written as `"k * stop distance"`, `time_exit, pyramiding, sizing`); `costs.csv` (`commission_per_side_usd, point_value_usd, tick, assumed_slippage_ticks_market_and_stop, assumed_slippage_ticks_limit, position_limit_contracts, eod_flat_time`). Plus one free-text `manual_reason` per MANUAL exit. Details and commands: `src/S5/README.md`.

## 7. Policies and thresholds examined (complete count, including discarded)

Ten management policies, all for engine demonstration, none proposed: original bracket; time exit at minute 30; breakeven (stop to entry) after +0.8R, all legs; breakeven after +0.8R, add leg only (smoke test); stop to +0.3R after +0.8R; trailing 0.5R after +0.8R, 0.25R after +1.0R, 0.25R after +1.5R, 0.5R after +1.5R, 0.1R after +1.0R (the five trails were tried only to find one that produces a same-bar stop/target case; four produced none); no-target hold to 15:55 (validation); no-progress exit at minute 20 below +0.3R, add-leg own stop, structural stop, structural target `or_mid` for all trades, 10-point trail after +0.5R (smoke tests in `README.md`, run once each, not tuned). Ten fill-model variants (section 8). No thresholds were optimised.

## 8. Fill-assumption variants the pre-registered policies must be evaluated under

Original policy, Stage A entries, under each single-change variant of the reference model (SYNTHETIC, 332 trades, 242 sessions, net of costs):

| variant | net $ | mean R | stop exits | target exits | gaps |
|---|---|---|---|---|---|
| reference | 15,314.22 | 0.31 | 167 | 161 | 2 |
| slippage 0 ticks (MKT, STP, gap) | 15,549.22 | 0.32 | 167 | 161 | 2 |
| slippage 2 ticks | 15,079.22 | 0.31 | 167 | 161 | 2 |
| gap fill at the open (0 extra ticks) | 15,317.22 | 0.31 | 167 | 161 | 2 |
| stop fires only on penetration | 15,830.22 | 0.32 | 166 | 162 | 1 |
| target fills on touch | 15,314.22 | 0.31 | 167 | 161 | 2 |
| bracket not armed in entry bar | 15,286.22 | 0.31 | 167 | 161 | 4 |
| triggers + MKT prices on NQ bars | 15,318.22 | 0.31 | 167 | 161 | 1 |
| same-bar target_first | 15,314.22 | 0.31 | 167 | 161 | 2 |
| same-bar stop_first | 15,314.22 | 0.31 | 167 | 161 | 2 |

Required grid for every pre-registered challenger and for the original (report each cell in R and $, with trades and sessions): `slippage_ticks_market/stop/gap ∈ {0, 1, 2}` (Stage B also re-prices entries); `stop_trigger ∈ {touch, penetrate}`; `same_bar_order ∈ {stop_first, target_first}` whenever a policy's stop and target can share a bar (report `worst` as the headline); `bracket_in_entry_bar ∈ {True, False}`; `limit_gap_fill ∈ {open, limit}`; `exit_frees_same_bar ∈ {False, True}` in Stage B. A challenger's advantage over the original must exceed its own range across this grid under the reference model's worst cell, otherwise it is a fill artefact. Commission stays at $0.74/side; a policy that exits legs separately pays it on each exit.
