# J3 — Head trader / product owner verdict

Lens: does the input exist on a retail feed at bar close, is it there every day, can the trader read it in 10 s, can the action be sent in that window. Judged on content; agreement earned nothing. Standing condition: nothing reaches the live screen until the eligible-signal log exists and the slot clears the max-of-N check under conservative fills.

## Verdict table

| Proposal | Verdict | Reason | Evidence that flips it |
|---|---|---|---|
| Condition-based slot selector | REVISE — research now, premature live | Condition labels are post hoc unless frozen as bar-close computations; a 16-cell matrix on hundreds of sessions is a search. Only clock- and nATR-based conditions are computable at bar close today. | Frozen ex-ante classifier beats session-only policy by >20% net R/session, bootstrap CI, ≥150 sessions per condition. |
| Gate vs ranking split | ADVANCE gate; DROP live pre-emption | Gates (blackout, nATR band, stale feed) are binary, known from calendar or bar close. Ranking matters only under a hard constraint; flattening A to enter B is two round trips inside 10 s — not executable by hand, doubles cost. | Gate+rank minus gate-only > 0 against a random-label control; pre-emption only via auto-routing with measured cost. |
| nATR "calm → 2 micros" | DROP as live sizing; REVISE as stop-placement test | nATR is computable (20-session baseline; unusable 09:30–09:44 on RTH-only bars). Sizing up the lowest-$/contract regime doubles the weakest trades; the prototype already leaks it (size 2 at n=7). | Lowest nATR quintile $/contract ≥ middle quintiles on executed trades, session-bootstrap CI excluding 0. |
| β-adjusted ES residual SMT + stale rule | ADVANCE stale rule; REVISE signal (research) | Leg age >30 s → slot off is executable. The residual needs per-leg exchange timestamps; most retail feeds give receipt time — verify. A ~0.5-tick/5-min forecast is below an MNQ round trip. | At all three (k,h) pairs: OOS ΔR² > 0 and top–bottom decile after-cost spread t ≥ 2. |
| Event-VWAP playbook / earliest executable time | ADVANCE blackout flag; REVISE VWAP layers (research) | The event flag is the one zero-latency input. "Executable at 08:31/14:01" ignores that retail stop-markets at releases slip 15–40 ticks; the conservative cost case is net negative. | ≥50 own release-window orders with 90th-pct slippage < 25% of slot edge; 08:30→08:35 vs 08:35→10:00 sign agreement ≥ 65% over 72 days. |
| Study 66 max-of-N reality check | ADVANCE (prerequisite) | Offline, minutes on a P&L matrix. Decides which slots may appear on the screen at all. | Only if Study 66 already reports the best trial against the sign-flip max-of-N null. |
| Same-bar stop/target resolution | ADVANCE | MNQ stops below one 1-min range give 9–25% ambiguous bars, enough to fabricate 0.2–0.6 R. Live corollary: server-side brackets, not platform stops. | Ambiguous-bar share < 2% and edge sign unchanged across fill conventions. |
| Strategy × condition interaction model | REVISE — research only | Decides whether routing exists; needs ≥250 sessions, ≥20 per cell. Never on the live screen; show only cell n/sessions. | Joint δ Wald p < 0.05 with some \|δ_sc\| > 0.3 R at ≥40 sessions → one per-slot condition rule. |
| Fixed worst-10%-day marginal contribution | ADVANCE (nightly, offline) | Computed overnight; its live derivative is one readable number, correlated-long $ per 1%. W holds 50–70 sessions; use the bootstrap. | (B+S) − B on W ≥ 0 (or ≥ −0.3×mean \|S\|) with 90% interval → sizing rule, not skip. |
| Log every eligible signal (13 fields at t_signal) | ADVANCE now | The denominator for every other row. Written by the engine asynchronously, no latency cost. Shadow mode changes nothing live. | >95% ledger↔TAKEN match and <1 non-TAKEN row per 5 sessions → keep EXEC_ERROR logging only. |
| Bitemporal replay schema | REVISE | Record ingest_time and version hashes now (cheap); defer full replay and screen-hash assertion. Retail platforms rarely emit bar corrections; sparse account pushes are the real stale source. | One-week lag log: 99.9th-pct lag < 10% of bar interval, zero corrections, account push ≤ 60 s → hashes only. |
| Two layouts / four states / no confidence score | ADVANCE vocabulary, no-score; REVISE layout | Status words with denominators read in 10 s; a score does not. Board beyond ~6 slots is unscannable; account limit must be a routing-enforced banner; states need glyph and button differences, not pills. | Replay: median key press > 10 s with ≤ 6 slots retires the board; engine matches unhurried decision > 95% → one-line ticket. |
| Prop-account per-trade path simulator | ADVANCE research; blocked live until rules verified | EOD data under-count breach 4–15×, structurally. Live derivative: headroom must count unrealized P&L per firm rule. Firm parameters unverified. | P(breach) differs < 5 pp across slots and EOD vs per-trade agree within 5 pp → ignore account mechanics in selection. |

## Prototype

In 10 s it shows headline, state pills, exposure delta and "what changes this". States differ in wording and denominator, not in shape or control: same pill shape, account limit in blue (information, not a lock), no buttons. Wrong or missing:

1. ACCOUNT LIMIT REACHED never renders: in scenario 4 both slots go INPUT UNAVAILABLE before the account gate runs, and the open MNQ short at −$62 unrealized against −$40 daily headroom is already a breach if open P&L counts. The screen should be LOCKED.
2. Scenario 3 says "TAKE (baseline size)" while order and risk are computed at size 2 — the untested calm-sizing hypothesis executes live.
3. Every input is required by every slot (`some(v!=='ok')`); a stale ES print kills sell-off-recovery, which may not read ES. Slots must declare required inputs.
4. Opposite-direction signals against an open position (scenario 4) are unhandled; a reversal doubles cost and risk.
5. Headline lacks side/qty/instrument/price; no signal age, no "valid until price X", no header release countdown, no engine heartbeat — NOT FIRED and "engine dead" look identical.
6. "R-ticks" is unreadable at speed; show net $/trade with n/sessions.

Main screen: time, release countdown, action line (side, qty, instrument, entry/stop/target), state word with n/sessions and $/trade, exposure before/after, headroom including unrealized, signal age, keys. Drill-down: CI, condition cells, Study 66/71, slippage, provenance, "why changed".

## What the director did not ask

Whether the 10-second human loop should exist per slot. Between t_signal and fill the entry drifts; a hand-confirmed order on an 8-point-edge slot loses a measurable share to it, and nobody measured that. Decision changed: which slots auto-route with a server-side bracket and which keep confirmation. Test: from the eligible-signal log over 30 sessions, median (fill − intended) and t_fill − t_signal by slot; auto-route any slot whose median drift exceeds 25% of net edge, keep confirmation under 10%. The schema already carries the fields.
