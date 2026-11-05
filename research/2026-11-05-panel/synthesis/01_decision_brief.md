# Decision Brief — Research Panel, 2026-11-05

**Scope and honesty note.** The workspace contained no datasets, strategy code, logs, study reports or account rules (verified at 02:13 ET). Everything about Study 66, Study 71/71-A, KX/PX, the sizing idea, SMT, pyramiding and prop rules is user-supplied context. The panel therefore delivered *specifications and synthetic stress tests*, not findings about your system. 18 independent agent runs occurred (15 specialists in one concurrent wave, then 3 blind judges). The judges' verdicts are summarized in §5; consequential disagreements are preserved.

## 1. What you can use now (no new data needed)
1. **Separate the gate from the ranking** (B1). "Trade at all in this condition?" is a portfolio-level decision; "which slot first?" only matters when slots compete for a constrained position or risk budget. In three of four playbook sessions the gate does the work. Default when slots do not compete: both remain eligible.
2. **Account constraint ≠ strategy quality** (B5, C3). Show "ACCOUNT LIMIT REACHED" as a hard-locked banner, never as evidence against the setup. The prototype encodes this ordering: evidence state → input availability → account gates → duplicate-exposure.
3. **Four screen states with different enabled actions, denominators and shapes** (C3, C1): FAVORABLE / HISTORICALLY UNFAVORABLE (n ≥ 20 sessions, CI sign) / INSUFFICIENT EVIDENCE (trade the pre-registered baseline, log) / INPUT UNAVAILABLE (cannot evaluate; never reinterpret as unfavorable). No confidence score; show (n sessions, net effect after costs, CI, cost assumption).
4. **Cost regime tables** (A3): the conditions that look best in bar data (09:30–09:35, releases) have the largest, most asymmetric execution cost; a stop-market exit pays the worst slippage when the trade is losing. Use three regimes, not one slippage number.
5. **Event timing facts** (A1, externally supported): only the scheduled-event flag is knowable with zero look-ahead; earliest executable time for an 08:30/14:00/14:30-anchored slot is the close of the first full 1-min bar (5-min close conservative); never pool the 14:00 statement and 14:30 presser windows.
6. **MES + MNQ same direction is one slot** (A6, B4): at ρ ≥ 0.8 over the holding horizon, two same-direction legs carry ~90% of doubled single-leg variance; size by beta-weighted notional and show $ per +1% NQ on the main screen.

## 2. What needs validation before it changes a trade
- **Condition-based slot selector** (B1, B2): naive per-condition sorting names *different* "best strategies" in 85% of synthetic runs when the condition is a pure main effect. Requires the strategy × condition interaction test with session-clustered SEs, and same-opportunity support (rejected signals logged). Until then: research candidate.
- **"Two micros when calm"** (A5): synthetic stress test says size-up doubles the weakest $/contract trades (+10% P&L, +46% drawdown, lower Sharpe). The likely real problem is stop placement on quiet entries. Test $/contract by nATR quintile before any live change.
- **SMT / ES–NQ** (A2, A6): replace direction-only rules with a beta-adjusted ES residual, nested on an NQ-only comparator; "NQ/ES ratio given NQ" is the identical regressor as "ES given NQ". Needs ≥ 250 aligned sessions and a stale rule (drop if either leg > 30 s old in RTH).
- **Study 71 "chop"** (A4): a touch-vs-two-close break definition changed events/session 16.8 → 4.2 on identical synthetic paths while follow-through *per session* was flat. Version definitions with denominators; report definition changes as denominator changes.
- **Pyramiding** (B4): captured-MFE fraction and give-back fraction move in opposite directions under every trailing rule tested; choose which one is the target and report both.

## 3. What to drop (as currently framed)
- **Any result selected from a search and judged against a single-rule or random-entry null** (B3). Best-of-200 pure-noise parameter sets pass t = 1.96 in 99% of synthetic worlds; the honest max-of-N critical value is t ≈ 3.5. Re-run Study 66 with the reality-check null before trusting any grid winner.
- **Single-number confidence scores** on the trader screen (C3, C1).
- **EOD-equity simulation of intraday-trailing prop rules** (B5): understates breach 4–15× in synthetic paths; per-trade MFE/MAE is the minimum.
- **Direction-only SMT** once a magnitude term is present (A6 synthetic: direction t drops from 5.6 to 1.8).

## 4. Three highest-value next actions
1. **Log every eligible signal, including rejected ones** (B6 13-field schema; C2 bitemporal event/ingest times). This is the prerequisite for computing "losses avoided / winners discarded" for *any* filter. First check whether your platform already does it (grep logs for a strategy name on a no-fill day).
2. **Re-run Study 66 honestly** (E1 in the backlog): conservative fills, stop-first on ambiguous bars, reality-check null. The single check most likely to reverse an existing conclusion.
3. **Versioned break/follow-through definitions + decision-time efficiency terciles** (E2), then the nATR sizing quintile test (E3). Both change decision 2 ("which observable conditions change the EV of this setup").

## 5. Judges' verdicts (three independent, blind; full text in `verdicts/`)

| Proposal | J1 quant director | J2 capital PM | J3 head trader | Director's reading |
|---|---|---|---|---|
| Condition-based slot selector (matrix) | REVISE — gate only for clock-defined conditions; ranking research-only | REVISE — gate only; ranking "barely covers costs", pre-emption doubles cost | REVISE — research; only clock/nATR conditions computable at bar close | **Gate now, ranking later.** All three independently reduced it to the gate. |
| Gate-vs-ranking split | (folded into above) | ADVANCE — zero cost | ADVANCE gate; DROP live pre-emption | **Use now.** |
| nATR "calm → 2 micros" | DROP live; REVISE as stop-placement research | DROP live; 2-hour quintile test first | DROP live; prototype must not execute size 2 at n = 7 | **Do not size up.** Test $/contract by quintile; the stop is the likelier lever. |
| β-adjusted ES residual (SMT) | ADVANCE research; premature live | ADVANCE research; payoff is *removing* fragile HH/LH rules | ADVANCE stale rule now; signal research-only; forecast likely below an MNQ round trip | **Stale rule now; nested test when ≥ 250 aligned sessions exist.** |
| Event-VWAP playbook | ADVANCE layer (a); DROP (b)–(d) for now — MDES ≈ 0.5, consensus-vintage leakage | ADVANCE flag; DROP (b)–(d) — release-window cost exceeds edge uncertainty | ADVANCE blackout flag; (b)–(d) research — retail stop-markets slip 15–40 ticks at releases | **Event flag / blackout now. Event-window entries are not a live strategy.** |
| Study 66 max-of-N reality check | ADVANCE — most decision-changing finding | ADVANCE — top value per hour | ADVANCE — prerequisite for any slot on screen | **Run first.** |
| Same-bar stop/target resolution | ADVANCE | ADVANCE | ADVANCE; live corollary: server-side brackets | **Run with E1.** |
| Strategy × condition interaction | REVISE — fixed effects + clustered Wald; drop shrinkage (τ² unstable with 9 cells) | REVISE — same; power 34% at half-size effects | REVISE — research only, ≥ 20 sessions/cell | **Fixed-effects Wald only, after the eligible-signal log.** |
| Fixed worst-10%-day marginal contribution | REVISE — diagnostic with bootstrap/CVaR, not a take/skip rule (W ≈ 50–70 heavy-tailed sessions) | ADVANCE — "this *is* the capital metric" | ADVANCE nightly, offline; live derivative is one number | **Disagreement preserved:** J1 says diagnostic only; J2/J3 say decision metric. Resolution: compute nightly, use as a *sizing* input with a bootstrap interval, not a hard skip, until W is stable across rolling windows. |
| Log every eligible signal (13 fields) | ADVANCE core; never retire | ADVANCE — unlocks every other test | ADVANCE now; shadow mode 20 sessions | **Unanimous, and the only item all three called a prerequisite.** |
| Bitemporal replay schema | REVISE — ingest_time + hashes now; full replay after lag test | REVISE — same; full plumbing exceeds edge at 1–5 micros | REVISE — same; account pushes are the real stale source | **Two columns now; defer the rest.** |
| Four states / no confidence score | ADVANCE, with a multiplicity caveat on the displayed cell estimate + hysteresis | ADVANCE vocabulary; DROP the N = 80–160 replay study (costs more than a micro book's edge) | ADVANCE vocabulary; REVISE layout (glyph + button differences; account limit as routing-enforced banner) | **Adopt the vocabulary. Disagreement preserved:** J2 would skip the formal replay study; J1/C3 want it. Director: run the cheap 30-moment paper replay (C1), not the N = 160 study. |
| Prop-account per-trade path simulator | REVISE — granularity result survives; policy ranking does not (trade shuffling assumes exchangeability; rules unverified) | ADVANCE — the one proposal that changes account selection | ADVANCE research; blocked live until rules verified | **Build it; resample by session block, not by trade; populate only verified rules.** |
| Duplicate-exposure skip (same-direction MNQ/MES) | (within B4 verdict) | REVISE — interim NQ-equivalent delta cap; decide skip vs half-size after the worst-day test | (show correlated-long $ per 1% live) | **Delta cap now; skip-vs-half-size later.** |

**Consequential disagreements worth your attention**
1. *Worst-10%-day contribution as a rule vs a diagnostic* (J1 vs J2/J3) — hinges on whether ~60 heavy-tailed sessions can rank slots; the bootstrap interval decides.
2. *Formal replay study of the interface* (J2 drop vs J1/C3 keep) — hinges on the dollar size of the book; J2's point that the study may cost more than a micro book's annual edge is well taken.
3. *Prototype readiness* — J3 found six concrete defects (account limit never renders; scenario 3 executes the untested size-2 variant; every slot requires every input; reversals against an open position unhandled; headline lacks side/qty/price; "R-ticks" unreadable). The first four are fixed in the committed prototype; the last two are noted as open.

**What the judges said the director failed to ask**
- J1: **a program-wide power budget and holdout.** Ten tests on the same ~750 sessions with no untouched period is Study 66 one level up. Freeze the last ~125 sessions before opening any log; rank proposals by minimum detectable effect against an economic threshold (e.g., 0.1 R/session net); do not run tests that cannot detect it.
- J2: **the total addressable edge in dollars** (Σ net $/yr by slot, session-bootstrap CI; one hour from the executed log). It is the research budget; at ~$3k/yr only the audits, the log, the delta cap and the path simulator are rational. Also: copy-trading the same signals into several prop accounts makes breaches perfectly correlated and multiplies fees.
- J3: **whether the 10-second human loop should exist per slot.** Measure (fill − intended) and t_fill − t_signal by slot over 30 sessions; auto-route with server-side brackets where drift exceeds 25% of net edge.

## 6. Answers to the five decisions
1. **Pre-session families by scenario:** see playbook; BO in orderly trend, FB/MR in failed break and quiet rotation, nothing pre-release, PR/event-MR after the earliest executable time. All are mechanism classes until KX/PX/etc. are mapped by their actual triggers.
2. **Conditions that change a specific setup's EV:** decision-time path efficiency (A4), nATR quintile (A5), minutes-to-release and cost regime (A1, A3), stale inputs (A6). Each is a hypothesis with a stated retirement criterion.
3. **Incremental exposure and portfolio value:** $ per +1% NQ with MES via β̂; marginal contribution on a FIXED worst-10% session set (B4). Synthetic: a same-direction duplicate moved worst-day mean −$350 → −$488; a counter-factor slot with the same standalone mean moved it to −$132.
4. **Main screen vs drill-down:** main = action, blockers (release clock, account headroom), correlated exposure delta, "what changes it", evidence tuple; drill-down = filter accounting, provenance, cost tables, interaction estimates (C1, C2).
5. **Three experiments:** E1 Study 66 reality check → E2 Study 71 definitions/efficiency → E3 nATR sizing + prop path. Retirement criteria in the backlog.

## 7. What the director failed to ask (panel's answers, filtered for a concrete decision + feasible test)
- **Override alpha** (B6): manual departures from intent may be the largest unmeasured "strategy". Synthetic: 39 overrides, clustered CI excluded zero where a naive CI did not. Test: 20 sessions of shadow logging.
- **Simulation granularity for account survival** (B5) dominates policy choice; treat the account path as a first-class research object.
- **The classifier inherits Study 71's definition sensitivity** (B1, A4): a selector built on an unversioned "condition" can look great for the same reason "chop" counts moved.

## 8. Unfinished items (precise)
- Prototype: headline still lacks entry/stop/target inline and signal age / engine heartbeat (J3 items 5–6); evidence is shown as net R-ticks, not $/trade.
- The prototype uses hand-written sample evidence; it does not compute evidence from a log. Wiring it to the B6/C2 schema is the next build step.
- No dated live example in the playbook (no market data available); all four sessions are synthetic.
- Prop-firm rule parameters were not verified against primary sources (B5 found conflicting third-party summaries); all are labeled hypothetical.
