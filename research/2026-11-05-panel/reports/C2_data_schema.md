# C2 — Research Application and Data Engineer: bitemporal schema and replay

**Question:** How would a decision-support application calculate and replay every displayed field as it was known at the time?

**Status of inputs (OBSERVED, 02:13 ET):** repository empty, no data, no strategy code, no logs. Everything below is a design spec; all rows and numbers are SYNTHETIC.

## 1. Strongest finding or proposal, and the decision it would change

**Proposal (HYPOTHESIS, engineering):** Every table is *bitemporal*: `event_time` (exchange/market clock) and `ingest_time` (app's clock when the row became available). Rows are append-only; corrections are new rows with a later `ingest_time`, never updates. Display at wall-clock *t* uses `ingest_time ≤ t`; replay of "the screen at *t*" uses the same rule — **not** `event_time ≤ t` alone, which silently shows the app things it had not yet received. Every rendered field carries a status (`ok / stale / missing / not_applicable`) and the screen carries a provenance tuple (`strategy_version_hash, feature_config_hash, vendor_snapshot_id, app_build_id`).

**Decision it changes:** whether any post-hoc study of "signals seen vs. signals taken" is admissible. Without `ingest_time` the user cannot distinguish "the rule said no" from "the data had not arrived," and Study-66-style comparisons of a preselected rule vs. a searched one (USER-SUPPLIED CONTEXT, unverified) are contaminated by look-ahead.

## 2. Evidence (with labels) and the strongest competing explanation

- OBSERVED: a stdlib simulation (section 3) shows a 09:42 bar ingested 195 ms late is invisible at 09:42:00.100 and visible at 09:42:00.300; an `event_time`-only join would show it at both instants.
- EXTERNALLY SUPPORTED (general knowledge; "search result only", no page opened): bitemporal modelling (valid time vs. transaction time) is the standard for auditable financial records; pandas `merge_asof` and R `data.table` rolling joins implement the one-sided as-of join directly.
- HYPOTHESIS: for a one-trader intraday system, the dominant replay error is not feed latency but *configuration drift* — parameters edited between the day and the replay. Hence hashes, not just timestamps.

**Strongest competing explanation:** "Latency is sub-second on 1-minute bars, so `event_time` suffices." True for bars; false for account state (broker pushes are sparse — the SYNTHETIC run shows account 12 min stale) and for vendor-corrected bars. The cheap fix is to record `ingest_time` always and let the staleness threshold decide when it matters.

## 3. Worked example / reproducible check / formula / data spec

```sql
-- Minimal relational schema. Every table: event_time TIMESTAMPTZ (market clock),
-- ingest_time TIMESTAMPTZ (app receipt), append-only, PK includes ingest_time where corrections occur.
-- DISPLAY rule: latest row with ingest_time <= now.  REPLAY rule: latest row with ingest_time <= t.
-- event_time is used only for ordering/aging within the visible set, never as the visibility cut.
strategy_version (strategy_version_hash PK, strategy_slot, code_hash, params_json, feature_config_hash,
                  created_time)                                    -- immutable; no event/ingest distinction
market_snapshot  (symbol, bar_interval, event_time, ingest_time, vendor_snapshot_id, o,h,l,c,v,
                  correction_seq, PK(symbol,bar_interval,event_time,ingest_time))
feature_value    (symbol, feature_name, feature_config_hash, event_time, ingest_time, value,
                  status ENUM(ok,stale,missing,not_applicable))     -- derived (ATR, VWAP, SMT); optional cache
signal           (signal_id PK, strategy_version_hash FK, symbol, event_time, ingest_time,
                  direction, strength, inputs_json, inputs_max_event_time, app_build_id)
position         (position_id PK, account_id, symbol, qty, avg_px, event_time, ingest_time, source ENUM(broker,derived))
account_state    (account_id, event_time, ingest_time, equity, realized_pnl, open_pnl, dd_room,
                  rule_set_hash, PK(account_id, ingest_time))
decision         (decision_id PK, signal_id FK, strategy_version_hash FK, event_time, ingest_time,
                  action ENUM(take,skip,size_down,manual_override), reason_code, field_status_json,
                  screen_hash, app_build_id, operator ENUM(auto,human))
"order"          (order_id PK, decision_id FK, account_id, symbol, side, qty, order_type, limit_px,
                  event_time /*sent*/, ingest_time, broker_order_id, state ENUM(new,ack,partial,filled,cancelled,rejected))
fill             (fill_id PK, order_id FK, event_time /*exchange ts*/, ingest_time, qty, px, fee)
outcome          (decision_id FK, horizon ENUM(exit,5m,15m,close), event_time /*horizon end*/, ingest_time,
                  pnl_ticks, pnl_usd, mae_ticks, mfe_ticks, status)   -- recomputable; never drives display

-- REPLAY ALGORITHM (pseudo-code)
function replay_screen(t, fields, prov):
    assert prov.app_build_id == running_build or load_build(prov.app_build_id)
    for each field f in fields:
        src   = f.source_table;  key = f.key
        rows  = SELECT * FROM src WHERE key=f.key AND ingest_time <= t          -- visibility cut
                ORDER BY event_time DESC, ingest_time DESC LIMIT 1             -- latest known, latest correction
        if rows empty:                      f.status = missing;  f.value = NULL
        elif t - rows.event_time > STALE[src]: f.status = stale; f.value = rows.value
        else:                               f.status = ok;      f.value = rows.value
        if f.requires(state) and not applicable(state): f.status = not_applicable
    derived = compute_features(prov.feature_config_hash, visible_market_rows(t))  -- deterministic
    sig     = evaluate(prov.strategy_version_hash, derived)                       -- deterministic
    screen  = render(fields, derived, sig, prov)
    assert hash(screen) == decision.screen_hash   -- bit-for-bit check; mismatch => provenance drift
    return screen
```

Staleness thresholds (HYPOTHESIS, tune per feed): bars = interval + 5 s; quotes/trades = 2 s; account_state = 60 s (or broker heartbeat × 2); position = 10 s after any fill, else 60 s; vendor economic calendar = 24 h. `not_applicable` is for fields whose precondition fails (e.g., SMT when ES feed is disabled for that slot; dd_room when the account is not a prop evaluation).

```text
SYNTHETIC EXAMPLE — one KX-family signal at 09:42 ET, 2026-11-04 (five rows across tables)
market_snapshot : MNQZ6, 1m, event 09:42:00.000, ingest 09:42:00.195, vendor_snapshot_id=V1-20261104-0942, c=25409.75, corr=0
signal          : sig_0042, strat=KX:a3f9c1, event 09:42:00.195, ingest 09:42:00.201, dir=short, inputs_max_event_time=09:42:00.000
account_state   : acct_P1, event 09:30:00.000, ingest 09:30:01.000, equity=51240, dd_room=1240   (last broker push)
decision        : dec_0042, sig_0042, event 09:42:00.230, ingest 09:42:00.230, action=take,
                  field_status={market:ok, atr_session:ok, smt_es:not_applicable, account:stale}, screen_hash=9b1e…, build=b.2026.11.04-3
order / fill    : ord_0042 sent 09:42:00.240 (ingest .241) MNQ sell 2 MKT -> fill_0042 exch 09:42:00.312, ingest .338, 2 @ 25409.25

Replay check (python3, stdlib; threshold bars 65 s, account 60 s):
t=09:42:00.100  market={'close': 25418.5}  [ok]  account={...dd_room 1240} [stale]   <- 09:42 bar not yet ingested
t=09:42:00.300  market={'close': 25409.75} [ok]  account={...dd_room 1240} [stale]
```

**File layout (parquet, R `arrow`/`data.table`, Python `pyarrow`/`polars`):**
`data/{table}/date=YYYY-MM-DD/symbol=MNQ/part-*.parquet` for `market_snapshot`, `feature_value`, `signal`; `data/{table}/date=YYYY-MM-DD/account_id=…/` for `account_state`, `position`, `order`, `fill`; `data/decision/date=…/` and `data/outcome/date=…/horizon=…/`; `data/strategy_version/` unpartitioned (small, immutable); `data/manifest/date=…/manifest.json` listing every file's sha256, `vendor_snapshot_id`, `app_build_id`. All timestamps stored as UTC `timestamp[ns]` with an `et_date` partition key derived from the CME trading date (18:00 ET roll), so a partition contains one Globex session, not one calendar day. Store `ingest_time` as a first-class column, never in file names.

## 4. When following this proposal would make the decision worse

- If the user's only goal is a quick backtest of bar-close rules, bitemporal plumbing delays the first result by days with no change in conclusions (latency ≪ bar interval).
- If `ingest_time` is assigned by a non-monotonic or unsynchronised clock (laptop sleep, NTP jumps), replay becomes *less* faithful than event-time-only replay. Clock discipline is a precondition.
- Storing `outcome` with the same rigor invites treating it as a display input; it must never gate a decision at *t* (look-ahead).

## 5. Cheapest decisive test, and the result that would retire the idea

Log `ingest_time` for one week (no other change). Compute, per feed, the distribution of `ingest_time − event_time` and the count of corrections (`correction_seq > 0`). **Retire** the bitemporal design (keep hashes only) if the 99.9th percentile lag is < 10 % of the smallest bar interval *and* there are zero corrections *and* account-state pushes arrive at least every 60 s. Otherwise it stays.

## 6. Missing inputs that materially limit the conclusion

Unknown (OBSERVED absent): broker/vendor API semantics (push vs. poll, correction messages), whether rejected signals are logged at all, clock source of the existing app, the strategy-parameter storage format (needed to define `feature_config_hash` canonically), and prop-firm rule text (needed for `rule_set_hash` and `dd_room`). The logs *must* contain, for every evaluated signal: `strategy_version_hash`, `inputs_max_event_time`, `ingest_time`, and the full `field_status` vector — otherwise "skipped because stale" is indistinguishable from "skipped by rule."

## 7. Filter accounting (the seven quantities in rule 3)

This report proposes no trading filter; the schema *enables* the accounting for any filter. Spec: **eligible signals** = `signal` rows whose decision has every required field `ok` (status vector stored, so eligibility is auditable); **trades retained** = decisions with `action=take` joined to ≥1 `fill`; **losses avoided** and **winners discarded** = `outcome` rows for `action=skip` decisions, split by sign of `pnl_usd`, with the skip `reason_code`; **net change after costs** = Σ fill fees + slippage (`fill.px − order.limit_px` or bar close) over retained minus simulated for skipped; **independent sessions** = distinct `et_date` partitions with ≥1 eligible signal; **portfolio contribution** = per-`strategy_slot` Σ `pnl_usd` grouped by `account_id`, with any stale-input decision flagged so sensitivity runs can exclude it.
