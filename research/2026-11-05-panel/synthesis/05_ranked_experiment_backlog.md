# Ranked Experiment Backlog (top three, in order)

**Feasibility with files already present:** none of the three can run on this workspace — it contains no data, code or logs (verified). Each is specified so that it runs the day the named files exist. Experiment 0 is the prerequisite that makes the others' "losses avoided / winners discarded" computable.

## Experiment 0 (prerequisite, ~1 day): log every eligible signal
Add the 13 fields from B6 (`signal_id, strategy_slot, strategy_version, t_signal, intended_side/size/entry/stop/target, decision, reason_code, other_slots_state, open_position_before, dd_remaining_usd, decided_by`) written **before** any order; join fills later. Check first whether the current platform already logs rejected signals (grep logs for a strategy name on a day it had no fills — B6). Without this, Experiments 1–3 can only use as-fired trades, which answers a weaker question (B2: descriptive sizing of an existing slot, not ranking).

---

## E1 — Study 66 honest re-run: is any preselected rule better than best-of-search noise?
| Field | Specification |
|---|---|
| Hypothesis | The preselected rule's session-level R exceeds the random-entry null **and** survives the max-of-N (sign-flip / reality-check) null; the "best grid result" does not. |
| Exact dataset | Study 66 trial matrix (every parameter set × every shifted calendar; the user's file) + 1-min MNQ bars for the same period with exchange timestamps; conservative fill table from A3 (stop-first on ambiguous bars, open/release regime costs). |
| Baseline | (a) random-entry distribution on the same calendar; (b) max-of-N distribution from sign-flipping session returns across all N trials. |
| Unit of analysis | Trading session (RTH date); trades within a session are not independent. |
| Validation split | Pre-registered rule index frozen *before* the grid is examined; time-blocked holdout = last 25% of sessions, reported separately. |
| Cost assumptions | A3 base case per regime: ordinary RTH 1 tick entry + 1–2 tick stop slippage; open 2–4 ticks; release 4–10 ticks; commissions per contract as billed. |
| Primary metric | Preselected rule's percentile vs (a) and vs (b); sign stability of mean session R across conservative vs optimistic fills. |
| Failure criterion (retire) | Reality-check p > 0.05 for the preselected rule, **or** the mean R changes sign between fill conventions (B3). |
| Effort | ~2 days if the trial matrix exists; ~1 week if the grid must be regenerated. |
| Why first | B3: this is the single check most likely to reverse an existing conclusion; synthetic best-of-200 pure noise passes t = 1.96 in 99% of worlds. It costs nothing new in data. |

## E2 — Is "chop" a definition artifact? Follow-through per session under versioned break definitions (Study 71/71-A)
| Field | Specification |
|---|---|
| Hypothesis | Follow-through *per session* is invariant to the break definition; the Study 71 event-count change is a denominator change, and decision-time path-efficiency (A4) separates post-entry follow-through terciles by more than round-trip cost. |
| Exact dataset | Study 71 and 71-A code/definitions (user's files); 1-min MNQ bars; the eligible-signal log from Experiment 0 (or, weaker, as-fired trades with MFE/MAE). |
| Baseline | "Touch" break definition vs "two-close hold", each reported per session, per break, per eligible signal (A4 template). |
| Unit of analysis | Session for rates; break for follow-through; signal for MFE/MAE. |
| Validation split | Definitions frozen first; estimate on first 70% of sessions, test tercile ordering on last 30%. |
| Cost assumptions | A3 ordinary-RTH base case; open-regime table for breaks before 09:45. |
| Primary metric | Follow-through per session (both definitions) and top-minus-bottom efficiency-tercile difference in post-entry MFE/MAE, session-clustered CI. |
| Failure criterion | Tercile difference < round-trip cost, or per-session follow-through differs by definition in a way that tracks event count (then the "chop" result is the denominator). |
| Effort | ~2–3 days. |
| Why second | Changes decision 2 (what changes the EV of a specific setup) and fixes the classifier that every selector depends on (B1 warns the classifier itself inherits Study 71's sensitivity). |

## E3 — Does calm-market sizing earn its place? nATR quintiles, three sizing policies, prop-account path
| Field | Specification |
|---|---|
| Hypothesis | Per-contract $ and R in the lowest nATR quintile are at least as good as the middle quintiles (A5); if not, "2 micros when calm" is retired before any portfolio test. Second stage: under the verified prop rules, the calm-size policy's breach probability does not exceed fixed-size by > 5 points (B5). |
| Exact dataset | Executed-trade log with per-trade MFE/MAE and fill timestamps (ms); 1-min bars for nATR (20-session warm-up, same minute-of-day median, current session excluded); verified firm rule text with effective dates. |
| Baseline | Fixed 1 MNQ; secondary comparator fixed-dollar-risk; stops sized to baseline ATR (A5 synthetic best Sharpe). |
| Unit of analysis | Trade for per-contract stats; session for bootstrap; account path for breach. |
| Validation split | nATR threshold chosen on first 60% of sessions; quintile ordering tested on last 40%; 1,000 session-shuffled paths for breach. |
| Cost assumptions | A3 base case; doubling size doubles slippage on stop-market exits in the open/release regimes. |
| Primary metric | $/contract by nATR quintile with session bootstrap CI; max drawdown and breach probability by policy. |
| Failure criterion | Lowest quintile not ≥ middle quintiles, **or** breach probability rises > 5 points for < 15% P&L gain, **or** losses on quiet-then-expansion trades exceed 15% of all losses (A5 synthetic showed 10% → 15–16%). |
| Effort | ~2 days (sizing); +1 day (path simulator exists as synthetic code in `synthetic_code/B5`). |
| Why third | Directly tests the user's stated sizing hypothesis; the synthetic stress test says the likely answer is "stop placement, not size", which would also change decision 2. |

## Deferred (research candidates; not in the top three)
- **SMT beta-adjusted residual, nested on NQ-only** (A6/A2): needs ≥ 250 RTH sessions of aligned ES/NQ bars; retire if OOS ΔR² ≤ 0 at all three pre-registered (k, h) pairs.
- **Strategy × condition interaction with shrinkage** (B2): only after Experiment 0 provides same-opportunity support; retire routing if joint p > 0.10 and no |δ| > 0.3 R with ≥ 40 sessions.
- **Event-VWAP sign-agreement test** (A1): 72 CPI+NFP days; retire if ≤ 55%. Low power (MDE d ≈ 0.35) is the reason it is deferred, not lack of interest.
- **Fixed-worst-10%-day marginal contribution** (B4): requires the rejected-signal log for the "skip" arm.
