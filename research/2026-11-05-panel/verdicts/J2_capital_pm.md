# J2 — Portfolio manager responsible for capital

Mandate: incremental net $ after costs, concurrent exposure, drawdown path, implementation cost. Scale assumption: a 1–5 micro book (MNQ $2/pt) nets at best low thousands of $/yr; a proposal costing >20 hours must move worst days or breach risk, not just mean R. Every $ figure in the reports is SYNTHETIC. Agreement between reports earned no weight.

## Verdict table

| # | Proposal | Verdict | Reason (mandate) | Evidence that flips it |
|---|---|---|---|---|
| 1 | Condition-based slot selector (matrix, ranking, pre-emption) | REVISE → gate only | Its own sim puts nearly all value in the *gate*; ranking "barely covers costs" and pre-emption doubles round-trips at $0.50/tick. 16+ parameters on hundreds of sessions is Study-66 bait. Research-useful; premature live. | Frozen ex-ante replay with P2 − P2a (ranking minus gate) > 0/session, session-bootstrap CI excluding zero |
| 2 | Gate-vs-ranking split | ADVANCE | Zero hours; stops the "KX or PX?" question until a binding constraint (one position, DLL, margin) exists. | None; it is a definition |
| 3 | nATR "calm → 2 micros" sizing | REVISE → stop-placement test; DROP as live sizing | Sizes up the lowest $/contract trades: +10% P&L for +46% max DD in sim. Adds $ risk on quiet-then-expansion days, the ones that breach a DLL. 2-hour quintile test first. | Bottom nATR quintile $/contract ≥ middle quintiles, session-bootstrap CI excluding zero |
| 4 | Beta-adjusted ES residual (SMT) nested test | ADVANCE as research; not a live rule | One afternoon; payoff is *removing* a fragile HH/LH condition, not adding edge. A 0.5-tick/5-min forecast is worthless after an MNQ round trip. | If no slot uses SMT today, skip entirely |
| 5 | Event-anchored VWAP playbook | REVISE → keep layer (a) flag/no-entry window; DROP b–d | n=96 event sessions, MDE d≈0.31; release-window cost uncertainty (−47% to +73% of edge kept) exceeds the edge. Flag is cheap and protects worst days. | Own release-window fills: median cost <25% of gross edge over ≥50 orders |
| 6 | Study 66 max-of-N reality check | ADVANCE | Minutes on an existing P&L matrix. Best-of-200 noise clears t=1.96 in 99% of worlds; promoting such a slot is the costliest capital error available. | Study 66 already uses a max-of-N/sign-flip null, or only one rule was ever run |
| 7 | Same-bar conservative resolution | ADVANCE | One backtester flag; can manufacture 0.2–0.6 R/trade at stops below one bar's range. Report all three resolutions. | Ambiguous-bar share <2% (stops ≥2× 1-min range) |
| 8 | Strategy×condition interaction with shrinkage | REVISE → fixed-effects Wald only; defer shrinkage | ~1 hour; prevents the 85%-spurious "best per condition" table. Power 34% at half-size effects on ~250 sessions, so it rarely licenses routing. | Joint δ Wald p<0.05 and a |δ_sc|>0.3R cell with ≥40 sessions |
| 9 | Fixed-worst-10%-day marginal contribution | ADVANCE | This *is* the capital metric: (B+S)−B over frozen W. One afternoon once logs exist. W≈50–70 sessions; sub-one-stop differences are noise. | It is the test; retire the skip rule if (B+S)−B on W ≥ −0.3×mean|S| |
| 10 | Log-every-eligible-signal schema (13 fields) | ADVANCE | 1–2 days; precondition for every filter-accounting row above. Without it "losses avoided" is unobservable. | 20-session shadow: >95% TAKEN match, <1 non-TAKEN row/5 sessions → keep EXEC_ERROR only |
| 11 | Bitemporal replay schema | REVISE → `ingest_time` column + version hashes only | Full plumbing is days of work with no $ change on 1-min bars; C2's own retire test says so. | One-week lag log: p99.9 lag ≥10% of bar interval, any corrections, or account pushes >60 s apart |
| 12 | Four screen states / no confidence score | ADVANCE vocabulary; DROP the N=80–160 study | Cheap wording change; prevents skipping valid INSUFFICIENT signals, a cost that never shows as a loss. A paired study costs more than a micro book's annual edge. | `state_shown × action_taken` log showing <5% INSUFFICIENT skipped |
| 13 | Prop-account per-trade path simulator | ADVANCE | EOD-only simulation understates breach 4–15×; same net P&L, 2× ruin. Hours once MFE/MAE exist. Blocked until firm rules are verified. | Per-trade vs EOD breach within 5 points *and* cross-slot differences <5 points |
| 14 | Duplicate-exposure skip rule | REVISE → interim NQ-equivalent delta cap; skip vs half-size after #9 | 1 MES ≈ 0.7 MNQ-equiv; a second MNQ long raises book delta ~66%, P(all lose) 2×. Cap is one line and protects worst days and DLL; a hard skip may discard a better-timed signal. | #9 shows S positive on W, or swap arm (B − MES + S) dominates |

## Ranking by net value per implementation hour

1. **B3 audits (#6, #7)** — minutes to hours; the only items that can *stop* capital going into a non-edge. A false slot costs an evaluation fee plus drawdown.
2. **Eligible-signal log (#10)** — 1–2 days; zero direct P&L, maximal option value; every other test is unestimable without it.
3. **Prop path simulator (#13)** — hours; the one proposal that changes account choice and sizing, where a 2× breach gap dwarfs any filter's expectancy gain at this book size.

## Cost likely exceeds edge

Full bitemporal schema (#11), matrix ranking with pre-emption (#1), event-VWAP layers b–d (#5), calm size-up (#3). Plausible at 50 contracts; at 1–5 micros the hours or the added execution cost swamp the achievable $.

## What the director did not ask

**The total addressable edge in dollars.** Nothing sizes the whole book: Σ net $/yr across approved slots with a session-bootstrap CI. That number is the research budget. If it is ~$3k/yr, only #2, #6, #7, #10, #13 and the #14 cap are rational; the rest are negative at any opportunity cost of the user's time. Test: executed log, net $ by slot by year after costs, session-bootstrap CI — one hour. It decides which proposals get built at all.

Secondary failure mode: if the same signals are copied into several prop accounts, breaches are perfectly correlated and evaluation/reset fees multiply; #13 must run on the combined account set, with fee drag inside the edge calculation.
