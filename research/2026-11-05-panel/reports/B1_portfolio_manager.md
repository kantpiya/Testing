# B1 — Systematic Strategy Portfolio Manager

**Question:** Under what conditions should one strategy slot outrank another, and when should both remain eligible?

**Scope note (OBSERVED):** No strategy code, logs, or study files exist in the workspace. Everything about KX, PX, engulfing, weak reversal, sell-off recovery and event-VWAP is USER-SUPPLIED CONTEXT (unverified). I therefore build the matrix over **mechanism classes**, not names. **Similar names do not establish similar exposures**: two "engulfing" variants can be a continuation entry and a reversal entry; the user must map each real slot to a class by its entry trigger, stop placement and invalidation, not its label.

## 1. Strongest finding or proposal, and the decision it would change

**Proposal (HYPOTHESIS):** Separate two decisions that are currently conflated in "which strategy is allowed now":

- **Gate** — trade at all in this condition? (binary, per instrument, per condition)
- **Ranking** — if more than one slot is eligible and they compete for the same position/risk budget, which fires first and which may pre-empt?

Ranking only matters when (a) two slots are eligible simultaneously and (b) a constraint (one position per instrument, daily loss cap, margin) means they cannot both be taken. Otherwise "both remain eligible" is the default and ranking is a no-op. The decision this changes: stop asking "KX or PX?" globally; ask, per condition, "gate open? if yes, who has priority on the first position?" In the synthetic run below most expected value comes from the **gate** in adverse conditions, not from ranking.

**Mechanism-class matrix (HYPOTHESIS; ✔ eligible, ★ ranks first, ✖ gated):**

| Condition \ Class | Breakout / continuation | Failed-break reversal | Mean-reversion to VWAP | Post-release momentum |
|---|---|---|---|---|
| Orderly trend (persistent directional drift, pullbacks hold) | ★ with-trend only | ✔ counter-trend, lower priority | ✖ (fades the drift) | n/a |
| Failed opening breakout (range extreme taken, re-entered within N bars) | ✖ until a new range forms | ★ | ✔ second priority (target = VWAP) | n/a |
| Quiet rotation (low range vs session-ATR, price oscillating around VWAP) | ✖ | ✔ low priority | ★ | n/a |
| Scheduled release pending (T−X min to release) | ✖ | ✖ | ✖ | ✖ (gate closed) |
| Release just passed (T+0 to T+Y min) | ✔ if aligned with post-release direction | ✖ until first post-release pullback | ✖ | ★ (earliest executable time explicit) |

**Mapping template** (the user fills one row per real slot): `slot_name | family | entry trigger (what must print) | direction relative to prior N-bar drift | stop location | invalidation | holding horizon | mechanism class | notes on why the class, not the name`. If two slots land in the same class with the same direction they are **redundant** in ranking terms and only one should hold priority; if they land in opposite classes they are **hedging** and the condition decides which is gated.

## 2. Evidence (with labels) and the strongest competing explanation

- OBSERVED: nothing — no logs, no definitions. All matrix entries are HYPOTHESIS from setup mechanics (continuation needs drift; reversal needs a failed extension; VWAP reversion needs oscillation; post-release needs the release).
- EXTERNALLY SUPPORTED (public, not re-fetched today): CPI/NFP 08:30 ET, FOMC 14:00/14:30 ET; RTH 09:30–16:00 ET. Verify against CME/BLS/Fed calendars.
- SYNTHETIC: section 3.

**Strongest competing explanation:** the condition labels are themselves outputs of the price path, so a condition-based selector can look good in-sample because "orderly trend" is partly defined by the trades having worked. Study 71's lesson (user-supplied) that changing the break definition changed the event count applies directly: the condition classifier must be fixed, time-stamped, and computable from information available before each signal's earliest executable time. A second competitor: a **time-of-day policy (P1)** may capture most of the same benefit if conditions are strongly clock-dependent (e.g. release windows), with far fewer degrees of freedom.

## 3. Worked example / reproducible check / formula / wireframe / data spec

**Policies compared on one shared signal log:**
P0 = allow all eligible signals (first-come takes the single position); P1 = session-only (first 60 min of window, any slot); P2 = matrix above (gate + ranking, higher-ranked slot may pre-empt a lower-ranked open position).

**Data spec (required):** a log of **ALL eligible signals, including rejected ones**, with: timestamp, slot, instrument, condition label (computed ex-ante), reason-rejected (`policy` / `position_open` / `risk_cap`), hypothetical outcome in R if taken (mark-to-rule, same exit logic), and realized outcome if filled. Without rejected-signal outcomes, P1 and P2 cannot be compared with P0 on the same denominator.

**SYNTHETIC simulation** (`b1_sim.py`, 400 sessions/condition, 3 slots BO/FB/MR, cost 0.10R; expected R per slot×condition is *assumed* in the script — it encodes the selector's own hypothesis, so P2 winning is by construction; the point is *where* the win comes from):

```
condition             pol    elig  fill rejPol rejPos winDisc lossAv     netR  R/sess
orderly_trend         P0     1223   634      0    589       0      0    -94.0  -0.235
orderly_trend         P1     1166   346    570    250     260    310    -22.8  -0.057
orderly_trend         P2     1227   568    408    251     147    261     21.3   0.053
failed_open_breakout  P0     1158   628      0    530       0      0    -22.9  -0.057
failed_open_breakout  P2     1234   793      0    441       0      0      0.1   0.000
quiet_rotation        P0     1196   625      0    571       0      0    -27.2  -0.068
quiet_rotation        P2     1209   569    407    233     146    261     34.5   0.086
release_pending       P0     1235   652      0    583       0      0   -132.2  -0.331
release_pending       P1     1235   353    623    259     259    364    -53.3  -0.133
release_pending       P2     1256     0   1256    0      548    708      0.0   0.000
```

Reading it: **Scenario A (orderly trend)** — ranking changes the outcome: P0 and P2 fill similar counts, but P2 gives the position to BO and pre-empts FB/MR, flipping sign. **Scenario B (release pending)** — only the gate matters: all three slots are negative, so no ordering helps; P2's entire gain is "don't trade" (0 fills, 708 losses avoided, 548 winners discarded). **Failed-open-breakout** shows the honest case: correct ranking with no gate barely covers costs (0.000 R/session) — ranking alone is not a money-maker when edges are thin.

## 4. When following this proposal would make the decision worse

- Condition classifier uses look-ahead (e.g. "orderly trend" judged on the full session) → P2 is in-sample fiction.
- Slots are mis-mapped to classes by name → a reversal variant gets ranked as continuation and is fired into the drift it was built to fade.
- Pre-emption (flatten lower-ranked, enter higher-ranked) doubles transaction costs; with MNQ at $0.50/tick plus commissions this can erase thin edges — in the synthetic run it helped only because the scratched trade had negative expected value.
- Conditions are rare: a four-condition × four-class matrix with per-cell thresholds is 16+ parameters fitted on hundreds of sessions; Study 66's random-entry/shifted-calendar baseline (user-supplied) must be applied to the selector itself.
- Ranking is applied when slots do **not** actually compete (separate instruments, separate risk budgets): then it only discards signals.

## 5. Cheapest decisive test, and the result that would retire the idea

Replay the full eligible-signal log under P0, P1, P2 with a **frozen, ex-ante** condition classifier; unit of analysis = trading session (independent); metric = net R per session after costs, plus the decomposition "gate contribution" vs "ranking contribution" (run P2 with gate only, ranking disabled, as P2a). **Retire condition-based ranking** if P2 − P2a is ≤ 0 across a shifted-calendar/random-condition-label control; **retire the whole selector** if P1 (session-only) achieves ≥ 80% of P2's gain with a block-bootstrap CI over sessions that overlaps P2's. Minimum: ≥ 150 sessions per condition with ≥ 2 simultaneous eligible signals; below that only the gate test is meaningful.

## 6. Missing inputs that materially limit the conclusion

1. Strategy definitions (entry, stop, invalidation) — without them the mapping template is empty and the matrix is unverifiable.
2. Whether logs record **rejected** signals with hypothetical outcomes.
3. The actual constraint that makes slots compete (one position? account daily loss? margin?). If none, ranking is moot.
4. Ex-ante condition definitions and their event counts (Study 71 sensitivity).
5. Cost model per instrument (commission + slippage per side) — determines whether pre-emption is ever affordable.

## 7. Filter accounting (the seven quantities in rule 3)

Per policy, per condition, per session:
- **Eligible signals** — all signals any slot emitted (denominator; includes rejected).
- **Trades retained** — filled under the policy.
- **Losses avoided** — rejected-by-policy signals with hypothetical R ≤ 0 (`lossAv` above).
- **Winners discarded** — rejected-by-policy signals with hypothetical R > 0 (`winDisc`).
- **Net change after costs** — Σ realized R(filled) − Σ hypothetical R(P0 fills), costs per side included.
- **Independent trading sessions** — count of sessions with ≥ 1 eligible signal; CI by session block-bootstrap.
- **Contribution to portfolio** — per-condition net R × condition frequency, plus correlation of P2 session returns with the P0 baseline (a selector that only removes trades cannot add diversification; one that re-orders can change exposure direction).

Win-rate alone is not reported: in Scenario B the selector "wins" by trading nothing.
