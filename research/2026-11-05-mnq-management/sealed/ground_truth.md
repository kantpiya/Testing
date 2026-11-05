# SEALED — planted structure of the SYNTHETIC test case (director only during the panel)

Written before any specialist report was read. Opened for the synthesis only after all six first-pass reports and both reviews were saved.

Generator: `sealed/make_synthetic.py`, seed 20261105. Every bar, signal and fill is SYNTHETIC.

## What was planted

| Family | Latent variable | Planted effect |
|---|---|---|
| KX (opening-range breakout, signal on NQ, executes MNQ) | `genuine` ~ Bernoulli(0.40) | Genuine: +0.27σ per-minute drift in trade direction for 60 bars starting the bar after the signal. Not genuine: −0.16σ drift (fade back into the range) for 40 bars. |
| KX | `slow` (18% of genuine) | Drift delayed by 12 minutes (flat first 12 min, then strong). These are the "costly false alarms" for any early no-progress exit. |
| PX (reversal from an extension, signal on MNQ) | `genuine` ~ Bernoulli(0.58) | Genuine: drift toward the OR midpoint. `slow` (50%, independent of genuine): 0.14σ for 90 bars; fast: 0.30σ for 40 bars. Not genuine: −0.18σ for 40 bars (trend resumes). |

Consequences the methods should recover:

1. **KX**: early progress is informative. A no-progress exit at ~10–15 min should improve KX net results, at the cost of the `slow` subgroup (24 of 95 genuine KX trades in the development set, mean +1.0R under the original policy).
2. **PX**: "slow reversal = bad reversal" is FALSE by construction (slow and fast genuine reversals have the same expectancy; speed is independent of `genuine`). A time/no-progress rule tuned on KX should harm or not help PX.
3. **Pyramiding (KX only)**: the add fires on reaching +1R within 20 min. Adds therefore land disproportionately on `genuine` trades; the add shares the original stop, so its own risk is ~2R of the original planned risk. Protecting the add (breakeven on the add) will cut the largest winners in the `slow`/noisy genuine subgroup.
4. **Strategy version**: KX_ORB_v2 (from 2026-01-01) has target 2.5R instead of 2.0R; nothing else differs. Any benefit must hold in both.

## Deliberate data wrinkles

- `fills.csv` timestamps are UTC; `bars_*` and `signals.csv` are ET (ISO with offset). Entry bar open == signal bar close (signal_ts) — the entry fills at the open of the bar that starts at signal_ts.
- MNQ bars = NQ bars with ±1-tick basis noise on ~1/3 of bars. KX signals are computed on NQ closes; fills are on MNQ.
- Slippage in the original fills: 1 tick adverse on every market and stop fill; 0 on target limits. Commission $0.74 per contract per side (both sides charged in `trades.csv`'s commission column).
- Stop and target touched in the same bar: resolved STOP FIRST by the generator. In the baseline this happened 0 times (stop + target span ≈ 3R ≈ 110 pts vs ≈10-pt bars). It becomes relevant for challengers with tightened stops.
- `STOP_GAP`: 5 trades where a bar opened through the stop; filled at the open − 1 tick.
- `MANUAL`: 11 trades (5% draw) exited at a random bar with no logged rationale. A faithful reconstruction should explain every non-MANUAL exit exactly and flag these 11 as unexplained.
- 14 signals rejected by the 4-contract position limit (`executed=False`, `reject_reason=position_limit`). Stage B must respect this.
- Holdout: sessions from 2026-05-01 (60 sessions, 88 trades) in `sealed/holdout/`. Specialists received only the development set (2025-05-01 → 2026-04-30, 242 sessions, 332 trades).

## Baseline (development set, original policy, after costs)

KX: 240 trades, mean +0.36R; PX: 92 trades, mean +0.19R. Net $15,370 total ($12,686 KX, $2,684 PX). 1R = planned_risk_usd of the initial leg.
