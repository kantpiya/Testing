# A1 — Macro releases (CPI, NFP, FOMC): what was knowable, when

Panel 2026-11-05 · A1, macro/monetary-policy specialist · Independent (no other `reports/` file opened).

## 1. Strongest finding or proposal, and the decision it would change

The only event information with zero look-ahead risk is the **scheduled-event flag** (date, time, type), known weeks ahead. The surprise, first reaction and confirmation each arrive at a clock time and must be timestamped. **Proposal:** split any event-VWAP/event-day idea into four layers (a–d), anchor the VWAP at the exchange-timestamped first trade at/after 08:30:00.000 ET (14:00:00.000 for the FOMC statement; 14:30:00.000 separately for the presser), and set the **earliest executable time at the close of the first full 1-minute bar after the anchor** (08:31 / 14:01 / 14:31), with 5-minute closes as the conservative default. Decision changed: event days as a *filter* on existing slots (layer a; cheap, adequately powered when pooled) versus a *new strategy* driven by surprise or initial response (layers b–d; under-powered with 3 years).

## 2. Evidence (with labels) and the strongest competing explanation

- **EXTERNALLY SUPPORTED (search result only, 2026-11-05):** BLS schedules CPI and the Employment Situation at 08:30 ET; next NFP Fri 2026-11-06, next CPI Tue 2026-11-10 ([BLS 2026 schedule](https://www.bls.gov/schedule/2026/home.htm); [CPI schedule](https://www.bls.gov/schedule/news_release/cpi.htm)). The search summary notes the 2026 calendar was **revised** (Sept-2025 vs Feb-2026 vintages differ). Implication: the event-flag file must be vintage-correct, and delayed/rescheduled releases (e.g., around the autumn-2025 shutdown — general knowledge, verify) are not ordinary event days.
- **EXTERNALLY SUPPORTED (search result only, 2026-11-05):** Fed lists eight 2026 meetings (Jan 27–28, Mar 17–18, Apr 28–29, Jun 16–17, Jul 28–29, Sep 15–16, Oct 27–28, Dec 8–9) ([FOMC calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm); [tentative schedule](https://www.federalreserve.gov/newsevents/pressreleases/monetary20240809a.htm)). Fed calendar pages label the item 2:00 p.m.; statement 14:00 ET, Chair's presser ~14:30 ET (public, verify per meeting). Mar/Jun/Sep/Dec add the SEP/dot plot at 14:00 — heterogeneity within the 8/yr sample.
- **OBSERVED:** workspace has no bar/trade data, logs or study reports. Everything below is a spec or SYNTHETIC.
- **HYPOTHESIS (market lore, untested):** (i) CPI reaction loads on core m/m vs consensus; NFP on payrolls, unemployment, AHE and revisions jointly — a vector, not a scalar; (ii) FOMC decisions are usually fully priced, so statement/SEP wording and the presser carry the news; (iii) the 14:00 move often reverses during the presser.
- **EXTERNALLY SUPPORTED (memory, not searched):** Lucca & Moench (2015, J. Finance) document a positive pre-FOMC equity drift in the 24h before 14:00 — FOMC-day mornings may differ from afternoons.
- **Strongest competing explanation:** any event-day "edge" is a volatility effect, not an information effect. Larger ranges mechanically change fill rates, stop distances and R-multiples for every slot; normalize by event-day realized volatility (session-aware ATR) before attributing anything to the release.

## 3. Worked example / reproducible check / formula / data spec

Timeline and the four layers (times ET; exchange timestamps, not local PC clock):

| Layer | Available from | Content | Usable for | Anchor / earliest execution |
|---|---|---|---|---|
| (a) Scheduled-event flag | Weeks ahead (vintage calendar) | type, date, 08:30/14:00/14:30, SEP yes/no | Filter on any slot; pre-event positioning rules | n/a — a day-level covariate |
| (b-pre) Consensus + prior print | T-1 close (freeze then) | survey median, previous value, implied FF rate | Defines surprise; needs stored vintage | Frozen at T-1 16:00 |
| (b) Release surprise | 08:30:00 + wire latency (seconds) | actual − consensus, revisions | Direction/size conditioning | First full 1-min bar close 08:31:00 |
| (c) Initial response | 08:31 / 08:35 | return from last pre-release trade (≤08:29:59.999) to bar close; VWAP(08:30→t) | Market's own surprise measure | Execute at 08:35:00 close (conservative) |
| (d) Confirmation | 09:30–10:00 | price vs event-VWAP, vs initial-bar range | Continuation vs fade | RTH open onwards |
| FOMC statement | 14:00:00 | decision, statement text, SEP (quarterly) | Same as (b)–(c) with 14:00 anchor | 14:01 / 14:05 close |
| FOMC presser | ~14:30–15:30, rolling | Q&A, no single timestamp | Separate anchor; treat as a window, not a point | 14:31 close; re-anchor VWAP at 14:30:00 |

Event-VWAP spec: VWAP_t = Σ(p·v)/Σv over trades with exchange timestamp ≥ anchor; undefined until the first trade; information at the anchor = layers (a) and (b-pre) only — the print is *not* known at 08:30:00.000. A rule evaluated on bar t may use only bars closed ≤ t. Slippage: fill at the next trade plus an explicit tick penalty (SYNTHETIC default 2–4 MNQ ticks; calibrate from the user's own event-day fills).

Sample size and power (SYNTHETIC, closed-form two-sample test on session-level R vs ~660 non-event sessions, α=0.05, 80% power): 3 years give CPI 36, NFP 36, FOMC 24 (96). Minimum detectable standardized difference: CPI or NFP alone **d≈0.48**, FOMC **d≈0.58**, CPI+NFP pooled (n=72) **d≈0.35**, all pooled **d≈0.31**. Power at d=0.2 is 0.16–0.22 — nil. Splitting FOMC into SEP vs non-SEP (12 vs 12) or by surprise sign halves n again.

## 4. When following this proposal would make the decision worse

- Logs without *rejected* signals: the filter has no correct denominator and looks good merely because retained trades are fewer and larger.
- Local/broker timestamps instead of exchange stamps: seconds-level look-ahead leaks the first bar's direction into the "pre-release" reference.
- Consensus pulled retroactively from a vendor (revised surveys): surprise mis-measured; vintage data required.
- Treating the presser as a point event, or pooling 14:00 and 14:30 reactions: a one-shot shock mixed with a rolling one and a frequent reversal — pooled effect near zero while each window may not be.
- Pooling the zero-rate regime with 2022–24 hiking/cutting: CPI surprises mattered far more in the latter; a 3-year window is one regime.

## 5. Cheapest decisive test, and the result that would retire the idea

Test layer (a) only, from existing logs: per slot, session-level net R on event days vs same-weekday non-event days (96 vs matched controls), normalized by session-aware ATR, session as unit. Retire the event *filter* if the pooled difference has |d|<0.3 with the 95% CI covering zero — anything smaller is undetectable and not worth a slot rule. For the event-VWAP *strategy*: sign-agreement between the 08:30→08:35 and 08:35→10:00 returns over 72 CPI+NFP days; retire if ≤55% (n=72 cannot separate 55% from 50%; it can separate ~65%).

## 6. Missing inputs that materially limit the conclusion

Exchange-timestamped trades/1-min bars for MNQ/NQ/MES/ES (2023-11 to 2026-11); vintage consensus and first-release prints (with NFP revisions); the user's event-day fills and slippage; logs with eligible *and* rejected signals and the originating slot; whether any slot already references news times; presser start time per meeting.

## 7. Filter accounting (event-day flag applied to a strategy slot)

| Quantity | Computation spec |
|---|---|
| Eligible signals | All signals the slot emitted on event days (needs rejected-signal logging); count by event type |
| Trades retained | Eligible signals that the filter still permits (e.g., after 08:35 / outside 14:00–14:35) |
| Losses avoided | Σ negative R of discarded trades, after costs, at the slot's actual sizing |
| Winners discarded | Σ positive R of discarded trades, same basis |
| Net change after costs | (Losses avoided − Winners discarded) − cost delta; report per event type and pooled |
| Independent sessions | 36/36/24 event sessions per 3 yrs (≈96, fewer if same-day collisions); unit = session, not trade |
| Portfolio contribution | Change in portfolio session-R mean/SD and max drawdown with the filter on vs off, all slots jointly |

