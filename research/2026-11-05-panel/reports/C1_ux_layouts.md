# C1 — Trader Workstation and UX: What the trader must see within ten seconds of a signal

**Panel:** 2026-11-05 · **Role:** C1, workstation/UX designer · **Inputs inspected:** only `00_common_brief.md` (OBSERVED: workspace is empty — no logs, no strategy code, no account rules). Every scenario number below is a **SYNTHETIC EXAMPLE** unless labeled otherwise.

## 1. Strongest finding or proposal, and the decision it would change

**Proposal (HYPOTHESIS):** The ten-second screen should answer exactly four questions, in this order: (a) *what action*, (b) *what blocks or shortens it* (event clock, account headroom), (c) *what the action adds to correlated exposure*, (d) *what would change the recommendation*. Everything that explains *why a strategy is believed to work* (expectancy, n, Study 66/71 material) belongs one click away.

**Decision it changes:** whether to ship a "decision card" (one recommended action) or a "slot board" (all eligible slots). Recommendation: **slot board as the resident screen, decision card as a collapsible header**, because the card alone hides the second-best option and why the engine ranked it — exactly where judgment is needed when several strategies fire on one move (user-supplied context: this happens).

## 2. Evidence (with labels) and the strongest competing explanation

- **OBSERVED:** No logs exist, so nothing here is measured trader behaviour; it is design reasoning.
- **EXTERNALLY SUPPORTED (general HCI knowledge; no page fetched):** ambiguous status language and unexplained numeric "confidence" raise decision latency and error. Remedy: a fixed, defined status vocabulary (Section 3) and *n* plus window instead of a score.
- **HYPOTHESIS:** Long MNQ and long MES co-move strongly intraday, so two MNQ entries on top of an MES long are one directional bet, not three; the screen reports **correlated long exposure** as one number. The correlation must be measured from the user's bars; the UI only displays it.
- **Strongest competing explanation:** the bottleneck is execution speed, not comprehension. If so, a one-line ticket ("BUY 1 MNQ KX-A, bracket on") beats both layouts. Section 5 distinguishes these.

## 3. Worked example / wireframes

**Scenario (SYNTHETIC):** 09:42 ET. Slots `KX-A` and `PX-B` (names are placeholders; definitions unavailable) both fire **long MNQ** on an NQ signal. Account already **long 1 MES**. Scheduled release: **ISM Services PMI, 10:00 ET → 18 min away** (labeled example; verify the real date against the calendar). Index levels assumed: NQ 25,000 (1% = 250 pt), ES 6,800 (1% = 68 pt). Multipliers (public, verify against CME): MNQ $2/pt, MES $5/pt.

Exposure arithmetic: existing MES long = $5/pt ES = **$340 per 1% ES move**. Each MNQ long adds $2/pt NQ = **$500 per 1% NQ move**. Taking both slots: +$4/pt, +$1,000/1%; correlated long total ≈ $1,340 per 1% co-move. Taking one: +$2/pt, +$500/1%; total ≈ $840/1%.

Example policy that produces the recommendation (SYNTHETIC, user must replace with own rule): correlated-long cap = $1,000 per 1% co-move; no new entries inside 10 min before a scheduled release; when two slots fire on the same move take the one with the larger logged net expectancy *only if* its evidence status is better than "insufficient".

### Layout 1 — Decision card

```
+------------------------------------------------------------------+
| 09:42:07 ET   RELEASE: ISM Services PMI 10:00 ET  [18 min]        |
| ACCOUNT: daily-loss headroom $1,150 | contracts free 3/5 | OK     |
+------------------------------------------------------------------+
|  ACTION   BUY 1 MNQ  (slot KX-A)   bracket: stop -40 pt / tgt +80 |
|  SKIP     PX-B  -> EXPOSURE CAP (would take corr-long to $1,340/1%)|
+------------------------------------------------------------------+
|  WHY      KX-A: n=142 signals / 61 sessions, net +$9/trade (last  |
|           18 mo). PX-B: n=19 -> INSUFFICIENT EVIDENCE.            |
|  ADDS     +$2/pt NQ  (+$500 per 1% NQ)                            |
|  AFTER    corr-long: $840 per 1% co-move (MES $340 + MNQ $500)    |
+------------------------------------------------------------------+
|  CHANGES IF  09:50 -> EVENT WINDOW (no new entries)               |
|              MES flat -> PX-B becomes ELIGIBLE                    |
|              daily-loss headroom < $500 -> ACCOUNT LIMIT REACHED  |
+------------------------------------------------------------------+
|  [T] take   [S] skip all   [B] open slot board   [D] drill-down   |
+------------------------------------------------------------------+
```

### Layout 2 — Slot board

```
+------------------------------------------------------------------+
| 09:42:07 ET  | ISM Services PMI 10:00 ET [18 min] | window 09:50  |
+----------+------+-----+--------------------------+----------------+
| SLOT     | DIR  | QTY | STATUS                   | ADDS           |
+----------+------+-----+--------------------------+----------------+
| KX-A     | LONG | 1   | ELIGIBLE  n=142/61s +$9  | +$2/pt +$500/1%|
| PX-B     | LONG | 1   | EXPOSURE CAP ($1,340>cap)| +$2/pt +$500/1%|
| ENG-C    |  --  | --  | NOT FIRED                |  --            |
| WR-D     |  --  | --  | INPUT UNAVAILABLE (ES qt)|  --            |
| SOR-E    |  --  | --  | NOT FIRED                |  --            |
+----------+------+-----+--------------------------+----------------+
| POSITIONS  MES long 1 @ 6,802  (+$5/pt, $340/1%)  open P&L +$45   |
| CORR-LONG  now $340/1%  | if KX-A $840/1%  | if both $1,340/1%   |
| ACCOUNT    daily-loss headroom $1,150 | contracts free 3/5        |
+------------------------------------------------------------------+
| [1..5] select slot   [T] take   [S] skip   [D] drill-down         |
+------------------------------------------------------------------+
```

Both layouts give the same answer — take KX-A, skip PX-B — but only the board shows that PX-B's block is *exposure*, not *evidence*, and that WR-D is silently dead for want of an ES quote.

**Status vocabulary (every word on screen is one of these):**
- **ELIGIBLE** — conditions met, no block; shown with n (signals / independent sessions) and net $/trade after costs, never a score.
- **NOT FIRED** — conditions not met now.
- **HISTORICALLY UNFAVORABLE** — logged net expectancy after costs < 0 for this slot *in this condition bucket*, n ≥ threshold (default 30 sessions). A directional claim backed by n.
- **INSUFFICIENT EVIDENCE** — n below threshold; no directional claim. Distinct colour from "unfavorable".
- **INPUT UNAVAILABLE** — a required feed (ES quote, release calendar, ATR series) is missing or stale; names the input. Cannot evaluate ≠ bad.
- **EXPOSURE CAP** — the user's own correlated-exposure policy blocks the entry; internal, adjustable.
- **ACCOUNT LIMIT REACHED** — an external account rule (daily loss, max contracts, drawdown buffer) would be breached; not adjustable intraday; separate from strategy quality.
- **EVENT WINDOW** — inside the no-new-entry window before a scheduled release; shows the clock.

**Main screen vs drill-down.** Main: time, release + minutes, action/qty/instrument, bracket, status word, n and sessions, net $/trade, exposure delta ($/pt and $/1%), correlated-long before/after, account headroom, "changes if", keys. Drill-down only: expectancy interval, condition-bucket breakdown, Study 66 random-entry comparison, Study 71 chop rate under the current break definition, session-ATR percentile, event-VWAP state, fill/slippage history, raw signal log.

**Ten-second scan order (both layouts):** 0–2 s action line (what, qty, instrument); 2–4 s blockers (release clock, account headroom); 4–6 s exposure delta and correlated total after; 6–8 s "changes if" list; 8–10 s key press. On the board, the eye goes header → first ELIGIBLE row → CORR-LONG line → keys.

## 4. When following this proposal would make the decision worse

- **Authority bias:** one recommended action invites rubber-stamping; if the ranking rule is in-sample-selected (Study 66 concern) the card promotes the overfit slot daily. The board at least exposes PX-B's n=19.
- **Correlation fails:** on SMT/divergence days NQ and ES decouple and one "corr-long" number understates risk; show the estimate's window in drill-down and flag INPUT UNAVAILABLE when stale.
- **Board overflow:** beyond ~8 slots the board is unscannable in ten seconds; the card header becomes mandatory.
- **"Changes if" clutter:** cap at three triggers, soonest first.

## 5. Cheapest decisive test, and the result that would retire the idea

Replay 30 logged (or synthetic) signal moments on paper mock-ups with the trader. Record per layout: time to key press, agreement with the trader's unhurried full-information decision, and drill-down opens. **Retire the card** if drill-down opens on > 30% of moments or its disagreement rate exceeds the board's. **Retire the board** if median time to key press > 10 s with ≤ 6 slots. **Retire both** for a one-line ticket if the unhurried decision matches the engine on > 95% of moments.

## 6. Missing inputs that materially limit the conclusion

- No signal log: n, sessions, expectancy and status thresholds are invented.
- No strategy definitions: unknown whether KX-A and PX-B share exposure or only a trigger time.
- No account rules: headroom fields are placeholders; a prop account counting open P&L changes ACCOUNT LIMIT logic.
- NQ/ES intraday correlation unmeasured; corr-long is conditional on a hypothesis.
- Trader latency and error rate unknown; Section 5 is the first measurement.

## 7. Filter accounting (spec)

The UI filters nothing itself, but EXPOSURE CAP and EVENT WINDOW act as filters. The log must record every fired signal: timestamp, slot, status assigned, taken or not, realized outcome if taken, and a *counterfactual outcome* (bracket simulated on subsequent bars) if not. Then per status word, per slot:
1. **Eligible signals** — fired signals before any block.
2. **Trades retained** — ELIGIBLE and taken.
3. **Losses avoided** — blocked signals with counterfactual net < 0, in $.
4. **Winners discarded** — blocked signals with counterfactual net > 0, in $.
5. **Net change after costs** — (3) − (4), commissions and one tick slippage per side applied to counterfactuals.
6. **Independent sessions** — distinct days contributing to (5); report fraction of sessions where (5) > 0, not only the total.
7. **Portfolio contribution** — change in daily P&L variance and max daily drawdown on the combined MNQ + MES book; the cap exists to cut co-movement risk, not to raise win rate.

A block that raises win rate but makes (5) negative or leaves (7) unchanged is retired.
