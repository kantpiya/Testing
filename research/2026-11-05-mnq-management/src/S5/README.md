# S5 replay engine — how to run it on the real export

Everything in this folder was developed and tested on **SYNTHETIC** data
(`data/synthetic/`). Nothing here is market evidence. The code transfers; the numbers do not.

## Files

| file | purpose |
|---|---|
| `replay.py` | library: data loading (UTC fills aligned to ET bars), `FillModel`, policies/rules, bar-by-bar `TradeSim`, Stage A and Stage B runners, session bootstrap |
| `reconcile.py` | rebuilds the ORIGINAL policy from `strategy_versions.csv` + bars and compares it trade by trade with `trades.csv` / `fills.csv`; classifies every mismatch |
| `run.py` | regenerates every table in `reports/S5_replay_engine.md` (`out/run_output.md`) |
| `out/` | CSV/markdown outputs of the last run |

Requires Python 3 with pandas >= 2 and numpy. No other dependencies.

## Required export (put the files in one folder, e.g. `data/real/`)

| file | required columns | notes |
|---|---|---|
| `bars_MNQ_1min.csv` | `ts, open, high, low, close, volume` | `ts` = bar **open** time, ISO 8601 **with UTC offset** (e.g. `2026-05-01T09:30:00-04:00`). RTH only is fine; every session must run to at least the 15:55 bar. Prices on the 0.25 grid. |
| `bars_NQ_1min.csv` | same | optional; only needed to test the signal-instrument basis (`trigger_instrument="NQ"`) |
| `signals.csv` | `signal_id, strategy, family, signal_instrument, exec_instrument, signal_ts, direction, ref_level, ref_width, planned_stop_dist_pts, planned_target_mult_R, planned_contracts, planned_risk_usd, executed, reject_reason, planned_target_px, planned_stop_px` | **every** signal, rejected ones included; `signal_ts` = close time of the signal bar = open time of the entry bar; `planned_stop_dist_pts` unrounded; PX rows carry `planned_target_px` (structural target) and `planned_stop_px` |
| `trades.csv` | `trade_id, signal_id, session, strategy, family, direction, entry_ts, entry_px, initial_contracts, added_contracts, add_px, add_ts, initial_stop_px, initial_target_px, planned_risk_usd, exit_ts, exit_px, exit_reason, gross_pnl_usd, commission_usd, net_pnl_usd` | `entry_ts`/`exit_ts`/`add_ts` = **open** time of the bar in which the fill happened, with offset; `exit_reason` in `STOP, TARGET, STOP_GAP, TIME_EOD, MANUAL` (anything else is reported as unexplained) |
| `fills.csv` | `fill_id, trade_id, leg_id, ts_utc, side, qty, price, order_type, fill_role, exit_reason, commission` | `ts_utc` in UTC with trailing `Z`; `leg_id` 1 = initial, 2 = add; `fill_role` in `ENTRY, ADD, EXIT`; one row per leg per fill |
| `strategy_versions.csv` | `strategy, family, valid_from, valid_to, signal_instrument, entry, stop, target, time_exit, pyramiding, sizing` | the target multiple is parsed from the `target` text (`"entry +/- 2.5 * stop distance"`); structural targets leave it blank/None |
| `costs.csv` | `instrument, commission_per_side_usd, exchange_fees_included, point_value_usd, tick, assumed_slippage_ticks_market_and_stop, assumed_slippage_ticks_limit, position_limit_contracts, eod_flat_time` | one row for MNQ |

Timestamps: any mix of offsets is fine (DST handled by tz conversion); do **not** export
naive local times. If the real platform records fills at the actual fill second, keep the
second-level `ts_utc` in `fills.csv` — the loader floors nothing, so `reconcile.py` will
report "timestamp not a bar open" and you should add a `bar_ts` column or floor to the minute
before running.

## Commands

```bash
# 1. reconcile the original policy with the journal (prints match/mismatch tables)
python3 src/S5/reconcile.py data/real src/S5/out_real

# 2. full checklist + Stage A/B demonstrations
python3 src/S5/run.py data/real src/S5/out_real
```

## Using the library for a pre-registered policy

```python
import sys; sys.path.insert(0, "src/S5")
import replay as R

d  = R.load_data("data/real", require_trades=True)
fm = R.FillModel.reference()                 # MNQ bars, stop fires on touch, limit needs penetration,
                                             # 1 tick slippage on MKT/STP, gap = open +1 tick, same-bar = worst
pols = [R.OriginalBracket("original"),
        R.Policy("noprog_20m_0.3R", [R.NoProgressExit(20, 0.3)], R.KXAddRule()),
        R.Policy("be_0.8R_addonly", [R.BreakevenStop(0.8, legs="add")], R.KXAddRule()),
        R.Policy("px_struct_exit", [R.StructuralTarget("or_mid")], None)]

long, paired = R.run_stage_a(d, pols, fm)    # identical entries, paired per trade, overlap flags
R.summarize(long[long.family == "KX"], "policy")
R.session_bootstrap(paired[paired.family == "KX"], "dnet_usd__noprog_20m_0.3R")

res, log = R.run_stage_b(d, pols[1], fm)     # chronological, 4-contract limit, pyramiding, 15:55 flat
```

Fill-assumption variants a pre-registered policy must be reported under
(`R.FillModel.reference(**kw)`): `slippage_ticks_market/stop/gap` in {0, 1, 2};
`same_bar_order` in {`stop_first`, `target_first`} (and `worst`); `stop_trigger` in
{`touch`, `penetrate`}; `target_fill` in {`penetrate`, `touch`}; `bracket_in_entry_bar` in
{True, False}; `limit_gap_fill` in {`open`, `limit`}.

## Rule building blocks (`replay.py`)

| rule | decision time | parameters |
|---|---|---|
| `TimeExit(minute)` | open of bar `minute` after entry | — |
| `NoProgressExit(minute, min_R, measure)` | open of bar `minute` | progress from closed bars: `close` (last close) or `extreme` (best high/low) |
| `BreakevenStop(trigger_R, offset_ticks, offset_R, legs, measure)` | first bar open after a closed bar reaches `trigger_R` | `legs` = `all`/`initial`/`add`/[ids] |
| `TrailingStop(trail_R or trail_pts, activate_R, legs)` | every bar open | ratchets off the best closed extreme |
| `StructuralTarget(key)` / `StructuralStop(key)` | at entry | `key` in `entry.levels` (`or_mid`, `structural_stop`, `ref_level`, `ref_width`, `or_boundary`) |
| `AddLegStop(mode)` | when the add fills | `own_distance`, `breakeven`, `fixed_pts` |
| `KXAddRule(trigger_R, window_min, latest_time, qty)` | next open after the trigger bar | the documented pyramid |

Every rule sees only bars whose close time is at or before the decision bar's open.
Each `Fill` carries its own commission, so partial and per-leg exits are costed.

Known limitations (1-minute data): see report section 4 — exact touches of a level, sub-minute
trailing, same-minute exit-and-re-enter and intra-bar discretionary exits cannot be replayed.
