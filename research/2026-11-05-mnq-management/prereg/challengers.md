# Pre-registration — original policy and four challengers (written BEFORE the sealed holdout was opened)

Status: drafted after reading the six first-pass reports; frozen before any file under `sealed/holdout/` was read. Director's choice among nine proposals (S1 ×2, S2 ×2, S3 ×2, S4 ×1, S6 ×1, S5 none). Changes after this point are logged in `prereg/CHANGELOG.md`.

All development numbers are SYNTHETIC and are quoted only as the prediction each challenger must match on the holdout.

## Baseline — P0 Original bracket (as reconstructed by S5)

Stop and target from `trades.csv`; KX add 1 contract at the next open after price reaches entry ± 1.0 × stop distance within 20 min and before 12:00 ET, add shares stop and target; flat at the 15:55 open. Bracket not live on the entry bar; stop fills on touch at stop − 1 tick (bar open − 1 tick if gapped through); target fills at the limit on touch; $0.74 per contract per side on every fill. MANUAL journal exits are replayed mechanically (the bracket runs through them) so they cancel in paired differences.

## C1 — KX stall → breakeven (the user's concrete question) — proposed by S1

- **Mechanism.** Once the initial leg's maximum favourable excursion has touched ≥ +0.8R and a bar then **closes** ≤ +0.3R while the trade is open, move the stop of all legs to `entry_px` (tick-rounded) at the next bar open; target unchanged.
- **Decision time.** Close of the trigger bar; action at the next bar open. Observable without future bars.
- **Parameters.** 0.8R trigger, 0.3R stall level, stop at 0R. No tuning on the holdout.
- **Fill assumptions.** As P0; same-bar stop + target → both orderings reported; a breakeven stop touched in the bar it becomes live counts.
- **Objective.** Paired mean net R per entry vs P0 on the stall set (KX only). Development prediction: Δ −0.31R [−0.76, +0.11], n = 60 / 60 sessions. Exit-now at the stall is dominated by breakeven on the same trades in development (−0.50R), so a holdout Δ ≤ 0 retires **both** "tighten" and "exit" for the stall and the answer becomes "hold the bracket". Advance only if Δ > 0 with the 95% session-bootstrap CI excluding 0.
- **Applies to.** KX_ORB_v1 and v2. Not PX (the state does not occur under P0).

## C2 — KX late profit-conditional breakeven (drawdown candidate) — proposed by S1

- **Mechanism.** At the open of bar entry + 20 min, if the close of bar 20 is ≥ entry + 0.3 × stop distance (mirrored for shorts) and the trade is open, move the stop of all legs to `entry_px`; target unchanged.
- **Decision time.** entry_ts + 20 min (close of bar 20); action at the open of bar 21.
- **Parameters.** k = 20, +0.3R, stop at 0R.
- **Fill assumptions.** As C1.
- **Objective.** Primary: P(final R < −0.5R) and worst-decile mean R at least halved on the conditioned set with paired mean Δ net R ≥ −0.10R (lower CI > −0.30R). Development: n = 63 / 63, Δ +0.04R [−0.25, +0.29], P(R < −0.5R) 0.24 → 0.06. Retire if the P&L cost exceeds −0.10R or the tail is not halved.
- **Applies to.** KX both versions.

## C3 — Add-leg stop at the original entry price — proposed by S4

- **Mechanism.** On the add fill, the add leg gets its own stop at `entry_px` (tick-rounded); leg 1 keeps the original stop and target; the add keeps the original target. Caps the add's risk at ≈ 1 initial-R instead of ≈ 2.
- **Decision time.** The add fill (next bar open after the add trigger). No free parameters.
- **Fill assumptions.** As P0; the add's stop is live from its fill bar; commissions on each leg's exit separately.
- **Objective.** In order: (1) worst-session loss and max drawdown of cumulative KX net P&L reduced by ≥ 0.5R; (2) paired Δ net $ vs P0 with 95% session-bootstrap CI not entirely below −0.05R per KX trade. Development: −$320 [−1,350, +670] on 240 KX trades, worst session −$392 → −$272. Retire if (1) fails or if P(reach target | retrace to entry after the add) ≥ 0.35 on the holdout add trades.
- **Applies to.** KX trades with an add.

## C4 — PX far target (setup-specific candidate) — proposed by S3

- **Mechanism.** PX target limit at the opposite opening-range boundary (`initial_target_px` + direction × OR_width/2, tick-rounded) instead of the midpoint; stop unchanged; flat at 15:55.
- **Decision time.** Entry. No free parameters.
- **Fill assumptions.** Limit fills at the limit price with 0 slippage (also when the bar opens through it); otherwise as P0.
- **Objective.** Paired mean net R per entry vs P0; secondary total net $, max drawdown, worst session, and Stage B net under the 4-contract limit (mean hold rises 28 → 50 min). Development: +0.40R [0.27, 0.52], +$5,514 on 92 PX trades / 92 sessions. Retire if the 95% CI includes 0 **or** if the Stage B portfolio difference is ≤ 0.
- **Pre-registered reading.** S3 and S6 both argue the development gain is generic post-entry drift, not the boundary acting as a level. The holdout shares the generator, so a replication is expected and is **not** evidence about the market; the diagnostic that separates "level" from "drift" is the no-target probe below.

## Diagnostic probes run alongside (not challengers; no decision rides on them)

- **D1 KX no-target with breakeven at 2R** (S6's proposal). Run to measure the size of the generator's post-target drift on the holdout; reported as the "drift probe". Explicitly not a candidate for forward simulation because its development benefit (+$61k on a $15k base) is an artefact of the synthetic drift.
- **D2 PX no-target** (S3's probe). Same purpose for PX.
- **D3 Exit-now at the stall** (S1). To confirm it is dominated by C1 on the holdout.
- **D4 S2's nominated failure rule** (no progress at 15 min ⇒ exit) and its unconditional 15-min comparator. Negative control: expected harm.

## Not pre-registered and why

- S2-C1 "late failure exit" (T = 30, +0.3R): best of 46 cells, post hoc, +$654 with CI spanning zero. Low prior; one slot would be spent on noise.
- S3-C2 PX no target: run as D2.
- S6 KX_NOTARGET_BE: run as D1.

## Holdout protocol

1. Engine: `src/S5/replay.py` (reference). Independent cross-check: director's own replay (`src/director/reproduce.py`) for C1 and D1, the two results on which the decision turns.
2. Data: `sealed/holdout/` (2026-05-01 → 2026-07-30, 60 sessions, 88 trades; counts verified after opening).
3. Statistics: paired per-trade differences; 2,000-draw session bootstrap; both same-bar orderings; slippage 1 and 3 ticks.
4. Stage B: chronological replay of the leading candidate with position limit 4, pyramiding, 15:55 cutoff, rejected signals eligible.
5. Count of policies and thresholds examined in development, including discarded (from the six reports): S1 192 conditional evaluations (100 cells × 2 actions), S2 46 cells, S3 29 policies + 1 sensitivity, S4 6 policies × 4 sensitivities = 24 runs, S6 92 cells + 12 fill variants + 1 lock variant. S5 to be added. The holdout evaluates 5 policies (P0 + 4) and 4 diagnostics.
