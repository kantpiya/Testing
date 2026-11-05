#!/usr/bin/env python3
"""
SYNTHETIC test case for the MNQ post-entry management study (panel 2026-11-05).

Everything produced here is SYNTHETIC. Nothing is derived from real market data,
real signals, or real fills. The purpose is (1) to give every specialist an identical,
fully specified data set in the exact schema the user is asked to export, and
(2) to plant known structure so that methods can be checked against a sealed
ground truth (sealed/ground_truth.md), which is NOT given to specialists.

Outputs (development set = sessions before HOLDOUT_START; holdout = from HOLDOUT_START):
  data/synthetic/bars_NQ_1min.csv        1-min OHLCV, NQ (signal instrument for KX)
  data/synthetic/bars_MNQ_1min.csv       1-min OHLCV, MNQ (execution instrument)
  data/synthetic/signals.csv             every signal emitted, executed or not
  data/synthetic/fills.csv               every fill under the ORIGINAL management policy
  data/synthetic/trades.csv              trade-level summary as the desk's journal records it
  data/synthetic/strategy_versions.csv   parameter sets by version and date range
  data/synthetic/costs.csv               commission/fee schedule
  sealed/holdout/...                     same files for the holdout window (director-only)
  sealed/ground_truth.md                 planted structure (director-only)

Usage: python3 make_synthetic.py [--seed 20261105] [--out <dir>]
"""
import argparse, math, os, json
import numpy as np
import pandas as pd

TICK = 0.25
MNQ_PT = 2.0          # $ per index point per contract
NQ_PT = 20.0
COMMISSION_PER_SIDE = 0.74   # $ per contract per side, all-in (ASSUMPTION; user must supply actual)
SLIP_TICKS_MARKET = 1        # adverse ticks on market/stop fills (ASSUMPTION)
RISK_BUDGET = 200.0          # $ planned risk per initial entry (ASSUMPTION)
MAX_CONTRACTS = 4            # position limit, all strategies combined
SESSION_END_EXIT = "15:55"   # flat by this bar's open
HOLDOUT_START = "2026-05-01"
ET = "America/New_York"


def round_tick(x):
    return np.round(np.asarray(x) / TICK) * TICK


def u_shape(n=390):
    t = np.linspace(0, 1, n)
    return 0.9 * np.exp(-6 * t) + 0.7 + 0.4 * np.exp(-8 * (1 - t))


def make_sessions(start="2025-05-01", end="2026-07-31"):
    days = pd.bdate_range(start, end)
    # drop a few US holidays (approximate list; SYNTHETIC calendar)
    hol = {"2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
           "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03"}
    return [d for d in days if d.strftime("%Y-%m-%d") not in hol]


def simulate(seed):
    rng = np.random.default_rng(seed)
    sessions = make_sessions()
    n_bars = 390
    minutes = pd.timedelta_range("09:30:00", periods=n_bars, freq="1min")
    ush = u_shape(n_bars)
    price = 20000.0
    bars_nq, bars_mnq, signals, fills, trades, truth = [], [], [], [], [], []
    sig_id = 0
    trade_id = 0
    fill_id = 0

    for d in sessions:
        date = d.strftime("%Y-%m-%d")
        ts = pd.DatetimeIndex([pd.Timestamp(f"{date} 00:00:00") + m for m in minutes]).tz_localize(ET)
        # overnight gap
        price *= math.exp(rng.normal(0, 0.004))
        sess_vol = math.exp(rng.normal(0, 0.35)) * 0.0080 / math.sqrt(n_bars)
        drift = np.zeros(n_bars)
        # latent day trend
        day_trend = rng.normal(0, 0.03) * sess_vol
        drift += day_trend
        # occasional news jump bar between 10:00 and 14:00
        jump_bar = int(rng.integers(32, 200)) if rng.random() < 0.15 else -1
        jump_size = rng.choice([-1, 1]) * rng.uniform(2.0, 4.0) * sess_vol
        o = np.zeros(n_bars); h = np.zeros(n_bars); l = np.zeros(n_bars); c = np.zeros(n_bars); v = np.zeros(n_bars)
        p = price
        # per-session state
        orh = orl = None
        kx_done = False
        px_done = False
        open_trades = []   # dicts
        ver = "KX_ORB_v1" if date < "2026-01-01" else "KX_ORB_v2"
        kx_target_mult = 2.0 if ver == "KX_ORB_v1" else 2.5

        def total_open():
            return sum(t["contracts"] for t in open_trades if t["status"] == "open")

        for i in range(n_bars):
            sig = sess_vol * ush[i]
            r = rng.normal(drift[i], sig)
            if i == jump_bar:
                r += jump_size
            o[i] = p if i == 0 else c[i - 1]
            # intrabar path: 4 sub-steps for high/low
            sub = rng.normal(drift[i] / 4, sig / 2, 4)
            sub = sub - sub.mean() + r / 4
            path = o[i] * np.exp(np.cumsum(sub))
            if i == jump_bar:
                o[i] = o[i] * math.exp(jump_size * 0.8)   # gap at the open of the bar
                path = o[i] * np.exp(np.cumsum(sub - jump_size / 4 * 0.8))
            c[i] = path[-1]
            h[i] = max(o[i], path.max())
            l[i] = min(o[i], path.min())
            v[i] = int(rng.lognormal(7.5, 0.5) * ush[i])
            p = c[i]
            # --- original policy: manage open trades on this bar (MNQ == NQ path here; basis added later)
            tbar = ts[i]
            for t in open_trades:
                if t["status"] != "open":
                    continue
                dirn = t["dir"]
                stop, target = t["stop"], t["target"]
                exit_px = None; reason = None
                hit_stop = (l[i] <= stop) if dirn > 0 else (h[i] >= stop)
                hit_tgt = (h[i] >= target) if dirn > 0 else (l[i] <= target)
                gap_through = (o[i] <= stop) if dirn > 0 else (o[i] >= stop)
                if tbar.strftime("%H:%M") >= SESSION_END_EXIT:
                    exit_px = o[i] - dirn * SLIP_TICKS_MARKET * TICK; reason = "TIME_EOD"
                elif gap_through:
                    exit_px = o[i] - dirn * SLIP_TICKS_MARKET * TICK; reason = "STOP_GAP"
                elif hit_stop and hit_tgt:
                    # TRUE sequence unknown to the log; generator resolves STOP FIRST (sealed)
                    exit_px = stop - dirn * SLIP_TICKS_MARKET * TICK; reason = "STOP"
                    t["both_touched"] = True
                elif hit_stop:
                    exit_px = stop - dirn * SLIP_TICKS_MARKET * TICK; reason = "STOP"
                elif hit_tgt:
                    exit_px = target; reason = "TARGET"
                # discretionary interventions (unlogged rationale) 4%
                if exit_px is None and t["manual_bar"] == i:
                    exit_px = c[i] - dirn * SLIP_TICKS_MARKET * TICK; reason = "MANUAL"
                # pyramiding add (KX only, original policy: add shares stop/target)
                if exit_px is None and t["family"] == "KX" and not t["added"] and (i - t["entry_bar"]) <= 20 \
                        and tbar.strftime("%H:%M") < "12:00" and total_open() < MAX_CONTRACTS:
                    add_level = t["entry_px"] + dirn * 1.0 * t["stop_dist"]
                    if (h[i] >= add_level) if dirn > 0 else (l[i] <= add_level):
                        t["added"] = True
                        t["add_pending_bar"] = i + 1
                if exit_px is not None:
                    exit_px = round_tick(exit_px)
                    t["status"] = "closed"; t["exit_bar"] = i; t["exit_px"] = float(exit_px); t["exit_reason"] = reason
                    t["exit_ts"] = tbar if reason not in ("TIME_EOD", "STOP_GAP") else tbar
                    # fills for every leg
                    for leg in t["legs"]:
                        fill_id += 1
                        fills.append(dict(fill_id=fill_id, trade_id=t["trade_id"], leg_id=leg["leg_id"], ts_utc=tbar.tz_convert("UTC"),
                                          side=("SELL" if dirn > 0 else "BUY"), qty=leg["qty"], price=float(exit_px),
                                          order_type=("STP" if reason.startswith("STOP") else "LMT" if reason == "TARGET" else "MKT"),
                                          fill_role="EXIT", exit_reason=reason, commission=COMMISSION_PER_SIDE * leg["qty"]))
            # pending adds fill at this bar's open
            for t in open_trades:
                if t["status"] == "open" and t.get("add_pending_bar") == i:
                    dirn = t["dir"]
                    add_px = float(round_tick(o[i] + dirn * SLIP_TICKS_MARKET * TICK))
                    fill_id += 1
                    leg = dict(leg_id=2, qty=1, entry_px=add_px, entry_bar=i)
                    t["legs"].append(leg)
                    t["contracts"] += 1
                    t["add_pending_bar"] = None
                    fills.append(dict(fill_id=fill_id, trade_id=t["trade_id"], leg_id=2, ts_utc=ts[i].tz_convert("UTC"),
                                      side=("BUY" if dirn > 0 else "SELL"), qty=1, price=add_px, order_type="MKT",
                                      fill_role="ADD", exit_reason="", commission=COMMISSION_PER_SIDE))
            # pending entries fill at this bar's open
            for t in open_trades:
                if t["status"] == "pending" and t["entry_bar"] == i:
                    dirn = t["dir"]
                    if total_open() + t["contracts"] > MAX_CONTRACTS:
                        t["status"] = "rejected_limit"
                        continue
                    ep = float(round_tick(o[i] + dirn * SLIP_TICKS_MARKET * TICK))
                    t["entry_px"] = ep
                    t["stop"] = float(round_tick(ep - dirn * t["stop_dist"]))
                    if t["family"] == "KX":
                        t["target"] = float(round_tick(ep + dirn * kx_target_mult * t["stop_dist"]))
                    t["status"] = "open"
                    t["legs"] = [dict(leg_id=1, qty=t["contracts"], entry_px=ep, entry_bar=i)]
                    t["entry_ts"] = ts[i]
                    fill_id += 1
                    fills.append(dict(fill_id=fill_id, trade_id=t["trade_id"], leg_id=1, ts_utc=ts[i].tz_convert("UTC"),
                                      side=("BUY" if dirn > 0 else "SELL"), qty=t["contracts"], price=ep, order_type="MKT",
                                      fill_role="ENTRY", exit_reason="", commission=COMMISSION_PER_SIDE * t["contracts"]))
            # --- signal generation (uses closed bars only)
            if i == 29:
                orh, orl = h[:30].max(), l[:30].min()
                orw = orh - orl
            if i >= 30 and orh is not None:
                hhmm = tbar.strftime("%H:%M")
                # KX breakout: first close beyond OR between 10:00 and 11:30, NQ bars
                if not kx_done and "10:00" <= hhmm <= "11:30":
                    dirn = 1 if c[i] > orh else (-1 if c[i] < orl else 0)
                    if dirn != 0:
                        kx_done = True
                        sig_id += 1
                        stop_dist = float(np.clip(0.35 * orw, 8.0, 60.0))
                        contracts = int(max(1, min(MAX_CONTRACTS, math.floor(RISK_BUDGET / (stop_dist * MNQ_PT)))))
                        genuine = rng.random() < 0.40
                        slow = genuine and rng.random() < 0.18
                        # plant regime
                        if genuine:
                            start = i + 1 + (12 if slow else 0)
                            drift[start:start + 60] += dirn * 0.27 * sess_vol
                        else:
                            drift[i + 1:i + 41] += -dirn * 0.16 * sess_vol
                        trade_id += 1
                        manual_bar = int(i + 2 + rng.integers(2, 25)) if rng.random() < 0.05 else -1
                        t = dict(trade_id=trade_id, signal_id=sig_id, family="KX", strategy=ver, dir=dirn, status="pending",
                                 entry_bar=i + 1, stop_dist=stop_dist, contracts=contracts, added=False, legs=[],
                                 level=float(orh if dirn > 0 else orl), orw=float(orw), manual_bar=manual_bar, both_touched=False,
                                 signal_ts=tbar + pd.Timedelta(minutes=1) - pd.Timedelta(seconds=1))
                        open_trades.append(t)
                        signals.append(dict(signal_id=sig_id, strategy=ver, family="KX", signal_instrument="NQ", exec_instrument="MNQ",
                                            signal_ts=(tbar + pd.Timedelta(minutes=1)).isoformat(), direction=("LONG" if dirn > 0 else "SHORT"),
                                            ref_level=float(round_tick(orh if dirn > 0 else orl)), ref_width=float(round_tick(orw)), planned_stop_dist_pts=stop_dist,
                                            planned_target_mult_R=kx_target_mult, planned_contracts=contracts,
                                            planned_risk_usd=round(stop_dist * MNQ_PT * contracts, 2), executed=None))
                        truth.append(dict(trade_id=trade_id, family="KX", genuine=genuine, slow=slow, manual_bar=manual_bar))
                # PX reversal: extension >= 1.0*ORW beyond OR, then a close back inside; 10:00-14:30
                if not px_done and "10:00" <= hhmm <= "15:00":
                    ext_up = h[30:i + 1].max() >= orh + 0.35 * orw
                    ext_dn = l[30:i + 1].min() <= orl - 0.35 * orw
                    dirn = 0
                    if ext_up and c[i] < orh and c[i - 1] >= orh:
                        dirn = -1
                    elif ext_dn and c[i] > orl and c[i - 1] <= orl:
                        dirn = 1
                    if dirn != 0:
                        px_done = True
                        sig_id += 1
                        extreme = h[30:i + 1].max() if dirn < 0 else l[30:i + 1].min()
                        stop_px = extreme + (-dirn) * 0.1 * orw
                        est_entry = c[i]
                        stop_dist = float(np.clip(abs(stop_px - est_entry), 8.0, 80.0))
                        target_px = (orh + orl) / 2   # structural level known at entry
                        contracts = int(max(1, min(MAX_CONTRACTS, math.floor(RISK_BUDGET / (stop_dist * MNQ_PT)))))
                        genuine = rng.random() < 0.58
                        slow = rng.random() < 0.5
                        if genuine:
                            if slow:
                                drift[i + 1:i + 91] += dirn * 0.14 * sess_vol
                            else:
                                drift[i + 1:i + 41] += dirn * 0.30 * sess_vol
                        else:
                            drift[i + 1:i + 41] += -dirn * 0.18 * sess_vol
                        trade_id += 1
                        manual_bar = int(i + 2 + rng.integers(2, 25)) if rng.random() < 0.05 else -1
                        t = dict(trade_id=trade_id, signal_id=sig_id, family="PX", strategy="PX_REV_v1", dir=dirn, status="pending",
                                 entry_bar=i + 1, stop_dist=stop_dist, contracts=contracts, added=True, legs=[],
                                 level=float(orh if dirn < 0 else orl), orw=float(orw), manual_bar=manual_bar, both_touched=False,
                                 target=float(round_tick(target_px)), signal_ts=tbar + pd.Timedelta(minutes=1) - pd.Timedelta(seconds=1))
                        open_trades.append(t)
                        signals.append(dict(signal_id=sig_id, strategy="PX_REV_v1", family="PX", signal_instrument="MNQ", exec_instrument="MNQ",
                                            signal_ts=(tbar + pd.Timedelta(minutes=1)).isoformat(), direction=("LONG" if dirn > 0 else "SHORT"),
                                            ref_level=float(round_tick(extreme)), ref_width=float(round_tick(orw)), planned_stop_dist_pts=stop_dist,
                                            planned_target_mult_R=float("nan"), planned_contracts=contracts,
                                            planned_risk_usd=round(stop_dist * MNQ_PT * contracts, 2), executed=None,
                                            planned_target_px=float(round_tick(target_px)), planned_stop_px=float(round_tick(stop_px))))
                        truth.append(dict(trade_id=trade_id, family="PX", genuine=genuine, slow=slow, manual_bar=manual_bar))
        price = c[-1]
        # bars
        oo, hh, ll, cc = round_tick(o), round_tick(h), round_tick(l), round_tick(c)
        bars_nq.append(pd.DataFrame(dict(ts=ts, open=oo, high=hh, low=ll, close=cc, volume=v.astype(int) * 3)))
        # MNQ: same path with occasional 1-tick basis noise (SYNTHETIC)
        noise = rng.choice([0, 0, 0, 0, -TICK, TICK], size=n_bars)
        bars_mnq.append(pd.DataFrame(dict(ts=ts, open=round_tick(oo + noise), high=round_tick(hh + np.abs(noise)),
                                          low=round_tick(ll - np.abs(noise)), close=round_tick(cc + noise), volume=v.astype(int))))
        # trades journal
        for t in open_trades:
            srow = next(s for s in signals if s["signal_id"] == t["signal_id"])
            if t["status"] in ("pending", "rejected_limit"):
                srow["executed"] = False
                srow["reject_reason"] = "position_limit" if t["status"] == "rejected_limit" else "no_fill"
                continue
            srow["executed"] = True
            for tr in truth:
                if tr["trade_id"] == t["trade_id"]:
                    tr["both_touched_exit_bar"] = bool(t.get("both_touched", False)); tr["exit_reason"] = t["exit_reason"]
            legs = t["legs"]
            qty = sum(lg["qty"] for lg in legs)
            gross = sum((t["exit_px"] - lg["entry_px"]) * t["dir"] * lg["qty"] * MNQ_PT for lg in legs)
            comm = COMMISSION_PER_SIDE * 2 * qty
            trades.append(dict(trade_id=t["trade_id"], signal_id=t["signal_id"], session=date, strategy=t["strategy"], family=t["family"],
                               direction=("LONG" if t["dir"] > 0 else "SHORT"), entry_ts=t["entry_ts"].isoformat(), entry_px=t["entry_px"],
                               initial_contracts=legs[0]["qty"], added_contracts=qty - legs[0]["qty"],
                               add_px=(legs[1]["entry_px"] if len(legs) > 1 else np.nan),
                               add_ts=(ts[legs[1]["entry_bar"]].isoformat() if len(legs) > 1 else ""),
                               initial_stop_px=t["stop"], initial_target_px=t["target"],
                               planned_risk_usd=round(t["stop_dist"] * MNQ_PT * legs[0]["qty"], 2),
                               exit_ts=ts[t["exit_bar"]].isoformat(), exit_px=t["exit_px"], exit_reason=t["exit_reason"],
                               gross_pnl_usd=round(gross, 2), commission_usd=round(comm, 2), net_pnl_usd=round(gross - comm, 2)))
    bars_nq = pd.concat(bars_nq, ignore_index=True)
    bars_mnq = pd.concat(bars_mnq, ignore_index=True)
    return bars_nq, bars_mnq, pd.DataFrame(signals), pd.DataFrame(fills), pd.DataFrame(trades), pd.DataFrame(truth)


def write(outdir, sealed, bars_nq, bars_mnq, signals, fills, trades, truth):
    dev = os.path.join(outdir, "data", "synthetic"); hold = os.path.join(sealed, "holdout")
    os.makedirs(dev, exist_ok=True); os.makedirs(hold, exist_ok=True)
    cut = pd.Timestamp(HOLDOUT_START, tz=ET)
    for name, df, col in [("bars_NQ_1min", bars_nq, "ts"), ("bars_MNQ_1min", bars_mnq, "ts")]:
        d = df.copy(); d["ts"] = d["ts"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
        m = df[col] < cut
        d[m].to_csv(os.path.join(dev, name + ".csv"), index=False); d[~m].to_csv(os.path.join(hold, name + ".csv"), index=False)
    sig_ts = pd.to_datetime(signals["signal_ts"]).dt.tz_convert(ET) if signals["signal_ts"].dtype == object else signals["signal_ts"]
    sig_ts = pd.to_datetime(signals["signal_ts"], utc=True).dt.tz_convert(ET)
    m = sig_ts < cut
    signals[m].to_csv(os.path.join(dev, "signals.csv"), index=False); signals[~m].to_csv(os.path.join(hold, "signals.csv"), index=False)
    f = fills.copy(); f["ts_utc"] = pd.to_datetime(f["ts_utc"], utc=True)
    m = f["ts_utc"] < cut
    f["ts_utc"] = f["ts_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    f[m].to_csv(os.path.join(dev, "fills.csv"), index=False); f[~m].to_csv(os.path.join(hold, "fills.csv"), index=False)
    m = pd.to_datetime(trades["session"]) < pd.Timestamp(HOLDOUT_START)
    trades[m].to_csv(os.path.join(dev, "trades.csv"), index=False); trades[~m].to_csv(os.path.join(hold, "trades.csv"), index=False)
    pd.DataFrame([
        dict(strategy="KX_ORB_v1", family="KX", valid_from="2025-05-01", valid_to="2025-12-31", signal_instrument="NQ", entry="next 1-min open after first close beyond 09:30-09:59 opening range, 10:00-11:30 ET", stop="entry -/+ 0.35*OR width, clipped [8,60] pts", target="entry +/- 2.0 * stop distance", time_exit="15:55 ET open", pyramiding="add 1 MNQ at next open after price reaches entry +/- 1.0*stop distance within 20 min of entry and before 12:00; add shares original stop and target", sizing="floor($200 / (stop pts * $2)), min 1, max 4"),
        dict(strategy="KX_ORB_v2", family="KX", valid_from="2026-01-01", valid_to="", signal_instrument="NQ", entry="same as v1", stop="same as v1", target="entry +/- 2.5 * stop distance", time_exit="15:55 ET open", pyramiding="same as v1", sizing="same as v1"),
        dict(strategy="PX_REV_v1", family="PX", valid_from="2025-05-01", valid_to="", signal_instrument="MNQ", entry="next 1-min open after a close back inside the opening range following an extension >= 0.35*OR width beyond it, 10:00-15:00 ET", stop="session extreme since 09:30 +/- 0.1*OR width (level known at entry); risk clipped [8,80] pts", target="opening-range midpoint (structural level known at entry)", time_exit="15:55 ET open", pyramiding="none", sizing="floor($200 / (stop pts * $2)), min 1, max 4"),
    ]).to_csv(os.path.join(dev, "strategy_versions.csv"), index=False)
    pd.DataFrame([dict(instrument="MNQ", commission_per_side_usd=COMMISSION_PER_SIDE, exchange_fees_included=True, point_value_usd=MNQ_PT, tick=TICK,
                       assumed_slippage_ticks_market_and_stop=SLIP_TICKS_MARKET, assumed_slippage_ticks_limit=0, position_limit_contracts=MAX_CONTRACTS,
                       eod_flat_time_et=SESSION_END_EXIT)]).to_csv(os.path.join(dev, "costs.csv"), index=False)
    truth.to_csv(os.path.join(sealed, "ground_truth_trades.csv"), index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=20261105); ap.add_argument("--out", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # folder root = parent of sealed/
    a = ap.parse_args()
    res = simulate(a.seed)
    write(a.out, os.path.join(a.out, "sealed"), *res)
    bars_nq, bars_mnq, signals, fills, trades, truth = res
    print("sessions", bars_nq["ts"].dt.date.nunique(), "bars", len(bars_nq), "signals", len(signals), "fills", len(fills), "trades", len(trades))
    print(trades.groupby("family")["net_pnl_usd"].agg(["count", "sum", "mean"]))
    print(trades["exit_reason"].value_counts())
    print("adds:", (trades["added_contracts"] > 0).sum())
