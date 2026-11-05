"""
SYNTHETIC simulation: session/minute-normalized volatility and position sizing.
Panel A5, 2026-11-05. All numbers are SYNTHETIC. No real MNQ data were used.

Model (1-minute resolution, one trade per simulated "signal"):
  - Seasonal baseline sigma_m (minute-of-day profile, U-shaped over 390 RTH minutes).
  - Latent regime multiplier R at entry ~ lognormal (quiet / normal / loud days).
  - ATR14_entry measured from the last 14 one-minute true ranges (noisy).
  - Normalized ATR  nATR = ATR14_entry / baseline_ATR(minute)  (baseline assumed known;
    in production it is the median of ATR14 at the same minute over the prior 20 sessions).
  - Stop = 1.5 * ATR14_entry (points); target = 2 * stop; time stop = 30 minutes.
  - Drift edge: +0.04 sigma per minute in trade direction (an orderly "follow-through" edge).
  - Regime switch: with probability p_exp (depends on quiet flag in scenario A, flat in B),
    sigma multiplies by 2.5 from a random minute u in [1, 25] until exit. Expansion is
    direction-symmetric; it hurts only because the stop was sized to the pre-expansion ATR,
    the time-stop bites, and stop slippage scales with vol.
  - Costs: $2.50 per contract round trip (commission + 1 tick each side) + stop slippage.

Policies:
  FIX1    : 1 MNQ always
  RISK$   : contracts = clip(floor(risk$ / (stop_pts * $2)), 1, 4), risk$ = 100
  CALM2   : 2 MNQ if nATR < 0.70 else 1 MNQ   (user's hypothesis)
  CALM2+R : same as CALM2 but stop widened to 1.5 * baseline_ATR when nATR < 0.70
            (a control: is the harm from size, or from stops sized to a compressed ATR?)
"""
import numpy as np

rng = np.random.default_rng(20261105)
PT_VALUE = 2.0           # $/pt MNQ (public; verify vs CME)
N_TRADES = 40_000
HOLD = 30
COST_RT = 2.50           # $/contract round trip
ATR_WIN = 14

# minute-of-day baseline sigma (pts per 1-min bar), U-shaped over 390 RTH minutes
m = np.arange(390)
base_sigma = 6.0 + 10.0 * np.exp(-m / 45.0) + 4.0 * np.exp(-(389 - m) / 40.0)
# baseline ATR14 ~ E[true range] ~ 1.6 * sigma for a 1-min bar of a Gaussian walk (rough)
base_atr = 1.6 * base_sigma


def run(scenario, seed):
    rng = np.random.default_rng(seed)
    out = {}
    # entry minute: avoid first 15 minutes so ATR14 exists in RTH-only computation
    ent_min = rng.integers(15, 360, N_TRADES)
    # latent regime multiplier at entry (lognormal, sd 0.45): quiet days & loud days
    R = np.exp(rng.normal(0.0, 0.45, N_TRADES))
    sig0 = base_sigma[ent_min] * R
    # measured ATR14 from 14 noisy true ranges
    tr = np.abs(rng.normal(0, sig0[:, None], (N_TRADES, ATR_WIN))) * 1.6
    atr_entry = tr.mean(axis=1)
    natr = atr_entry / base_atr[ent_min]
    quiet = natr < 0.70

    if scenario == "A":      # expansion clusters after quiet entries (compression -> release)
        p_exp = np.where(quiet, 0.35, 0.10)
    else:                    # scenario B: expansion independent of quiet flag
        p_exp = np.full(N_TRADES, 0.15)
    expands = rng.random(N_TRADES) < p_exp
    u = rng.integers(1, 26, N_TRADES)

    # path simulation
    stop_pts = 1.5 * atr_entry
    tgt_pts = 2.0 * stop_pts
    t = np.arange(1, HOLD + 1)
    mult = np.where(expands[:, None] & (t[None, :] >= u[:, None]), 2.5, 1.0)
    sig_t = sig0[:, None] * mult
    drift = 0.04 * sig0[:, None]                 # edge does not scale with the shock
    steps = drift + sig_t * rng.standard_normal((N_TRADES, HOLD))
    path = np.cumsum(steps, axis=1)
    hit_stop = path <= -stop_pts[:, None]
    hit_tgt = path >= tgt_pts[:, None]
    t_stop = np.where(hit_stop.any(1), hit_stop.argmax(1), HOLD + 1)
    t_tgt = np.where(hit_tgt.any(1), hit_tgt.argmax(1), HOLD + 1)
    stopped = t_stop < t_tgt
    targeted = t_tgt < t_stop
    # slippage on stop scales with vol at the time of the stop
    slip = np.where(stopped, 0.5 * mult[np.arange(N_TRADES), np.minimum(t_stop, HOLD - 1)], 0.0)
    pnl_pts = np.where(stopped, -stop_pts - slip, np.where(targeted, tgt_pts, path[:, -1]))

    # sizing policies
    fix1 = np.ones(N_TRADES)
    riskd = np.clip(np.floor(100.0 / (stop_pts * PT_VALUE)), 1, 4)
    calm2 = np.where(quiet, 2.0, 1.0)
    # control: calm size-up but stop re-widened to baseline ATR (not the compressed ATR)
    stop_ctrl = np.where(quiet, 1.5 * base_atr[ent_min], stop_pts)
    tgt_ctrl = 2.0 * stop_ctrl
    hs = path <= -stop_ctrl[:, None]; ht = path >= tgt_ctrl[:, None]
    ts = np.where(hs.any(1), hs.argmax(1), HOLD + 1); tt = np.where(ht.any(1), ht.argmax(1), HOLD + 1)
    st_c = ts < tt; tg_c = tt < ts
    slip_c = np.where(st_c, 0.5 * mult[np.arange(N_TRADES), np.minimum(ts, HOLD - 1)], 0.0)
    pnl_ctrl = np.where(st_c, -stop_ctrl - slip_c, np.where(tg_c, tgt_ctrl, path[:, -1]))

    policies = {
        "FIX1": (fix1, pnl_pts),
        "RISK$": (riskd, pnl_pts),
        "CALM2": (calm2, pnl_pts),
        "CALM2+R": (calm2, pnl_ctrl),
    }
    qx = quiet & expands
    print(f"\n=== SYNTHETIC scenario {scenario}: "
          f"{'expansion clusters after quiet entries' if scenario=='A' else 'expansion independent of quiet'} ===")
    print(f"trades={N_TRADES}  quiet share={quiet.mean():.3f}  P(expand|quiet)={expands[quiet].mean():.3f}  "
          f"P(expand|not quiet)={expands[~quiet].mean():.3f}  quiet&expand share={qx.mean():.3f}")
    print(f"{'policy':8s} {'netPnL$':>9s} {'mean$/tr':>9s} {'sd$/tr':>8s} {'sharpe':>7s} {'maxDD$':>8s} "
          f"{'avgCtr':>7s} {'win%':>6s} {'loss$ on Q&X':>13s} {'%losses Q&X':>12s} {'Q&X mean$':>10s} {'Q~X mean$':>10s}")
    for name, (ctr, pts) in policies.items():
        pnl = ctr * (pts * PT_VALUE - COST_RT)
        eq = np.cumsum(pnl)
        dd = (np.maximum.accumulate(eq) - eq).max()
        losses = np.where(pnl < 0, -pnl, 0.0)
        frac_loss_qx = losses[qx].sum() / losses.sum()
        print(f"{name:8s} {pnl.sum():9.0f} {pnl.mean():9.2f} {pnl.std():8.2f} {pnl.mean()/pnl.std():7.3f} {dd:8.0f} "
              f"{ctr.mean():7.2f} {100*(pnl>0).mean():6.1f} {losses[qx].sum():13.0f} {100*frac_loss_qx:12.1f} "
              f"{pnl[qx].mean():10.2f} {pnl[quiet & ~expands].mean():10.2f}")
        out[name] = pnl
    # what happens on the quiet-entry-then-expansion trades, per contract
    pnl1 = pnl_pts * PT_VALUE - COST_RT
    print(f"per-contract: quiet&no-exp mean ${pnl1[quiet & ~expands].mean():.2f}, win {100*(pnl1[quiet & ~expands]>0).mean():.1f}% | "
          f"quiet&exp mean ${pnl1[qx].mean():.2f}, win {100*(pnl1[qx]>0).mean():.1f}% | "
          f"not-quiet mean ${pnl1[~quiet].mean():.2f}, win {100*(pnl1[~quiet]>0).mean():.1f}%")
    print(f"stop-hit rate: quiet&no-exp {100*stopped[quiet & ~expands].mean():.1f}%  quiet&exp {100*stopped[qx].mean():.1f}%  "
          f"not-quiet {100*stopped[~quiet].mean():.1f}%")
    return out


for sc in ("A", "B"):
    run(sc, seed=20261105)
