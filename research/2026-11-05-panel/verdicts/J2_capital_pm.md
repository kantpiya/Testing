# J2 — Portfolio manager responsible for capital

Mandate: incremental net $ after costs, concurrent exposure, drawdown path, implementation cost. Scale assumption: a 1–5 micro book (MNQ $2/pt) nets at best low thousands of $/yr; a proposal costing >20 hours must move worst days or breach risk, not just mean R. Every $ figure in the reports is SYNTHETIC. Agreement between reports earned no weight.

## Verdict table

| # | Proposal | Verdict | Reason (mandate) | Evidence that flips it |
|---|---|---|---|---|
| 1 | Condition-based slot selector (full matrix, ranking, pre-emption) | REVISE → gate only | Its own sim puts nearly all value in the *gate* (don't trade in adverse windows); ranking "barely covers costs" and pre-emption doubles round-trips at $0.50/tick. 16+ cell parameters on hundreds of sessions is Study-66 bait. Research-useful; premature live. | Replay with frozen ex-ante classifier showing P2 − P2a (ranking minus gate) > 0 per session with session-bootstrap CI excluding zero |
| 2 | Gate-vs-ranking split | ADVANCE | Zero implementation hours; a framing that stops the "KX or PX?" question until a binding constraint (one position, DLL, margin) exists. No downside. | None needed; it is a definition |
| 3 | nATR "calm → 2 micros" sizing | REVISE → stop-placement test; DROP as live sizing | Sizes up the lowest $/contract trades; sim: +10% P&L for +46% max DD. Raises $ risk exactly on quiet-then-expansion days, the ones that breach a DLL. 2-hour quintile test on executed log first. | Bottom nATR quintile $/contract ≥ middle quintiles, session-bootstrap CI excluding zero |
| 4 | Beta-adjusted ES residual (SMT) nested test | ADVANCE as research; not a live rule | One afternoon, no new vendor; the likely payoff is *removing* a fragile HH/LH condition (fewer spurious skips), not adding edge. A 0.5-tick/5-min forecast is worthless after an MNQ round trip. | Only matters if a slot currently uses SMT; if none does, skip entirely |
| 5 | Event-anchored VWAP timing playbook | REVISE → keep layer (a) event flag/no-entry window; DROP layers b–d | n=96 event sessions/3 yrs, MDE d≈0.31; release-window costs (−47% to +73% of edge kept, conservative vs optimistic) exceed the edge's uncertainty. Flag is cheap and protects worst days. | User's own release-window fills with median cost <25% of gross edge over ≥50 orders |
| 6 | Study 66 max-of-N reality check | ADVANCE | Minutes on an existing P&L matrix. Best-of-200 noise clears t=1.96 in 99% of worlds; promoting such a slot is the costliest capital error available. | Study 66 already reports the best trial against a max-of-N / sign-flip null, or only one rule was ever run |
| 7 | Same-bar stop/target conservative resolution | ADVANCE | One flag in the backtester; can manufacture 0.2–0.6 R/trade at stops below one bar's range (MNQ scalping). Report all three resolutions. | Ambiguous-bar share <2% (stops ≥2× 1-min range) → no effect, nothing lost |
| 8 | Strategy×condition interaction model with shrinkage | REVISE → fixed-effects Wald only; defer shrinkage | ~1 hour; prevents the 85%-spurious "best per condition" table. But power is 34% at half-size effects with ~250 sessions, so it will rarely license routing. Shrinkage adds little with 9 cells. | Joint δ Wald p<0.05 and a |δ_sc|>0.3R cell with ≥40 sessions |
| 9 | Fixed-worst-10%-day marginal contribution | ADVANCE | This *is* the capital metric: slot judged on (B+S)−B over frozen W. One afternoon once logs exist. Caveat: W≈50–70 sessions, so differences under one stop/session are noise. | n/a — it is the test; retire the *skip* rule if (B+S)−B on W ≥ −0.3×mean|S| |
| 10 | Log-every-eligible-signal schema (13 fields at t_signal) | ADVANCE | 1–2 days; precondition for every filter-accounting row in all 15 reports. Without it "losses avoided" is unobservable and every verdict above is unestimable. | 20-session shadow run with >95% TAKEN match and <1 non-TAKEN row/5 sessions → keep EXEC_ERROR only |
| 11 | Bitemporal replay schema | REVISE → `ingest_time` column + version hashes only | Full bitemporal plumbing is days of work with no $ change on 1-min bars; C2's own retire test says so. Keep the two columns, skip the rest. | One-week lag log: p99.9 lag ≥10% of bar interval, or any vendor corrections, or account pushes >60 s apart |
| 12 | Four screen states / no confidence score | ADVANCE vocabulary; DROP the N=80–160 replay study | Cheap wording change; prevents skipping valid INSUFFICIENT signals (a silent cost that never shows as a loss). A formal paired study costs more than a micro book's annual edge. | Logged `state_shown × action_taken` showing <5% of INSUFFICIENT signals skipped |
| 13 | Prop-account per-trade path simulator | ADVANCE | Directly my mandate: EOD-only simulation understates breach 4–15×; same net P&L, 2× ruin. Hours of work once per-trade MFE/MAE exist. Blocked until firm rules are verified from primary sources. | Per-trade and EOD breach estimates within 5 points *and* cross-slot differences <5 points |
| 14 | Duplicate-exposure skip rule (same-direction MNQ/MES) | REVISE → interim NQ-equivalent delta cap; decide skip vs half-size after #9 | 1 MES ≈ 0.7 MNQ-equiv; a second MNQ long raises book delta ~66% and P(all lose) 2×. Cap is one line of code and protects worst days and DLL. A hard skip may discard a better-timed signal; the swap arm must be reported. | #9 shows S positive on W, or swap arm (B − MES + S) dominates |

## Ranking by net value per implementation hour

1. **B3 audits (#6, #7)** — minutes to hours; the only items that can *stop* capital going into a non-edge. A false slot costs a prop evaluation fee plus drawdown.
2. **Eligible-signal log (#10)** — 1–2 days; every other test is unestimable without it. Zero direct P&L, maximal option value.
3. **Prop path simulator (#13)** — hours; the one proposal that changes account selection and sizing, where a 2× breach-probability gap dwarfs any filter's expectancy gain at this book size.

## Cost likely exceeds edge

Full bitemporal schema (#11), condition-matrix ranking with pre-emption (#1), event-VWAP layers b–d (#5), and calm size-up (#3). All four are plausible at a 50-contract book; at 1–5 micros the implementation hours or the added execution cost swamp the achievable $.

## What the director did not ask

**The total addressable edge in dollars.** No report, and no brief question, sizes the whole book: Σ net $/yr across approved slots with a session-block-bootstrap CI. That number is the research budget. If it is ~$3k/yr, only #2, #6, #7, #10, #14-cap and #13 are rational; everything else is negative at any opportunity cost of the user's time. Feasible test: from the executed log, net $ by slot by year, costs applied, CI by session bootstrap — one hour. It changes the concrete decision of which proposals to build at all.

Secondary failure mode nobody raised: if the same signals are copied into several prop accounts, breach events are perfectly correlated and evaluation/reset fees multiply; #13 must run on the *combined* account set, and the fee drag belongs in the edge calculation.
