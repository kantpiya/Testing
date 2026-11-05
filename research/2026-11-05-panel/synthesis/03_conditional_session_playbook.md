# Conditional Session Playbook

No current market data are available in this workspace (verified: empty repository, no feeds, network fetch blocked), so every session below is **SYNTHETIC**, with sample timestamps, and mirrors the four scenarios in the clickable prototype. Rule trace used throughout: evidence state (n ≥ 20 sessions and CI sign, unit = session) → input availability → account gates (contracts, daily loss, trailing DD) → duplicate-exposure check. Multipliers MNQ $2/pt, MES $5/pt (public, verify).

## Pre-session (applies to all four)
1. Load the vintage-correct event calendar; mark CPI/NFP 08:30, FOMC 14:00 and 14:30 separately (A1).
2. Compute nATR warm-up (prior 20 sessions, same minute-of-day) so it is ready at 09:30 (A5).
3. Freeze slot versions and the condition classifier before the open; the classifier's definitions are versioned with denominators (A4). Any change is a new cell, not a new result.
4. Account state from the broker, with ingest time; flag stale if > 60 s (C2).

## Session A — Orderly trend (sample 2026-11-04, 10:12 ET)
- **Initial read:** three 1-min closes above IB high; efficiency ratio 0.62; nATR 0.95; ES agrees in direction; no event ≤ 60 min.
- **Plan:** BO slot eligible at baseline size; MR slot ineligible (fading acceptance); FB armed only on a close back inside the IB.
- **Observation that changes the interpretation:** a close back inside the IB within 3 bars converts the state to Session B (failed break). Efficiency ratio falling below 0.3 with the price still outside the IB = *acceptance by rotation*, not trend: BO stays eligible but a second BO on the same leg is duplicate exposure (B4).
- **Filter accounting to log:** eligible = every slot that fired; retained = BO; the MR signal that was *not* taken must be logged with its counterfactual outcome, otherwise "losses avoided" cannot be reported (B6).

## Session B — Failed opening breakout (sample 09:42 ET, two NQ longs fire, MES already long, release 18 min away)
- **Initial read:** post-open expansion; break of overnight high at 09:36, not yet failed; nATR 1.35; ES lags NQ in magnitude; ISM-type release at 10:00 (sample).
- **Plan:** KX-class continuation with n = 38, CI > 0 → TAKE 1 MNQ. PX-class opening-drive with n = 23, CI straddles 0 → it *would* be baseline-size, but it adds to an existing same-direction MES position and a just-taken MNQ long with no evidence it adds value → SKIP as duplicate exposure. Added exposure shown in $ per +1% NQ.
- **Observation that changes the interpretation:** a 1-min close back below the broken high before 09:45 → the BO long is invalidated and the FB short becomes the eligible slot; evidence for FB must come from its own cell. Entering the 5-min pre-release blackout → all new entries SKIP; existing positions follow their stops (gate, not quality).
- **Execution note (A3):** stop-market slippage is worst exactly in this window; a stop at 20 points with 2–4 tick slippage is $4–8 of a $40 risk per MNQ. Cost regime must be the "open" table, not "ordinary".

## Session C — Quiet rotation (sample 11:27 ET, nATR 0.58)
- **Initial read:** range 0.6× median; no IB break; ES flat.
- **Plan:** MR/weak-reversal class eligible at **baseline size**. The "2 micros when calm" variant has 7 sessions of history → INSUFFICIENT EVIDENCE: trade the pre-registered baseline and log the variant's hypothetical fill, do not size up. A5's synthetic stress test shows size-up on quiet entries doubles the weakest $/contract trades and raises drawdown ~46% for ~10% more P&L.
- **Observation that changes the interpretation:** a quiet entry followed by volatility expansion (nATR crossing 1.2 within 10 bars of entry) → the *stop*, not the size, is the problem (A5): stops sized to baseline ATR performed best in the synthetic. Pre-register: if expansion begins, do not add.

## Session D — Scheduled release (sample FOMC day, 14:31 ET; ES feed stale 41 s)
- **Initial read:** statement at 14:00 already produced a 60-pt move; presser started 14:30; short MNQ open from 14:12, unrealized −$62; daily loss remaining $40.
- **Plan:** sell-off-recovery class has favorable evidence (n = 29, CI > 0) **but** ES input is stale → INPUT UNAVAILABLE: cannot evaluate; do not reinterpret as unfavorable (C3). Event-VWAP fade anchored at 14:00 is INSUFFICIENT (n = 12) and the 14:30 window must not be pooled with the 14:00 window (A1). Even if both were favorable, stop risk $40 vs $40 daily loss remaining → ACCOUNT LIMIT REACHED on the first and BLOCKED on the second. All three states are shown with different shapes and wording, not just colors.
- **Observation that changes the interpretation:** a fresh ES print → re-evaluate the first slot; closing the open short → daily-loss remaining changes and may unblock. Earliest executable time for any 14:30-anchored slot is 14:31 (1-min close) or 14:35 (conservative).
- **Power caveat:** 24 FOMC days in three years; MDE d ≈ 0.58 (A1). Nothing learned on this day can be generalized from this day alone.

## What the four sessions have in common
- The gate (trade at all) does more work than the ranking (which slot) in three of four sessions (B1).
- The decision changes most often because of *inputs and account state*, not because of strategy evidence — which is why the prototype shows "why did the decision change" as a diff of inputs.
- Every "do not take" must be logged with its counterfactual, or the playbook cannot be evaluated next quarter.
