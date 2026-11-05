#!/usr/bin/env python3
"""Director's INDEPENDENT replay (written without reading any specialist's code) for the two results the
decision turns on:
  C1  KX stall -> breakeven   (MFE touched >= +0.8R, then a close <= +0.3R  =>  stop of all legs to entry at next open)
  D3  KX stall -> exit now    (same trigger, market exit at next open)
  D1  KX no target + breakeven once +2.0R touched (S6's drift probe)
  P0  original bracket
Conventions (chosen from the data dictionary, then checked against the journal): bracket not live on the entry bar;
stop fills on touch at stop - 1 tick, or bar open - 1 tick if the bar opens through it; target fills at the limit on touch;
same-bar stop+target -> parameter; the journal's add (if any) is taken at the journal add bar if still open; market exits
at next bar open - 1 tick; flat at the 15:55 open; $0.74 per contract per side on every fill.

Usage: python3 reproduce.py --data <dir with trades.csv and bars_MNQ_1min.csv> [--order stop_first|target_first] [--slip 1]
"""
import argparse, os, sys
import numpy as np, pandas as pd

TICK, PT, COMM = 0.25, 2.0, 0.74


def rt(x):
    return np.round(x / TICK) * TICK


def load(d):
    tr = pd.read_csv(os.path.join(d, "trades.csv"))
    b = pd.read_csv(os.path.join(d, "bars_MNQ_1min.csv"))
    b["ts"] = pd.to_datetime(b["ts"], utc=True).dt.tz_convert("America/New_York")
    b["session"] = b["ts"].dt.strftime("%Y-%m-%d")
    b["hhmm"] = b["ts"].dt.strftime("%H:%M")
    return tr, {s: g.reset_index(drop=True) for s, g in b.groupby("session")}


def replay(tr, bars, policy, order="stop_first", slip=1):
    """Return dict with net_usd, R, exit_reason, exit_ts, exit_px, stall_bar (first trigger bar index or None)."""
    d = 1 if tr["direction"] == "LONG" else -1
    b = bars[tr["session"]]
    ets = pd.Timestamp(tr["entry_ts"])
    i0 = int(np.where(b["ts"] == ets)[0][0])
    e, stop, tgt = tr["entry_px"], tr["initial_stop_px"], tr["initial_target_px"]
    sd = abs(e - stop)
    legs = [[tr["initial_contracts"], e, None, None]]  # qty, entry, exit_px, exit_reason
    add_ts = pd.Timestamp(tr["add_ts"]) if isinstance(tr.get("add_ts"), str) and tr["add_ts"] else None
    use_tgt = policy != "D1"
    be_live = False; stall_bar = None; pending = None  # pending: ("BE"|"EXIT") to act at next bar open
    mfe = -np.inf
    sl = slip * TICK
    for i in range(i0 + 1, len(b)):
        row = b.iloc[i]
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        # act on a pending decision at this bar's open
        if pending == "EXIT":
            px = rt(o - d * sl)
            for lg in legs:
                if lg[2] is None: lg[2], lg[3] = px, "STALL_EXIT"
            return finish(tr, legs, d, sd, row["ts"], stall_bar)
        if pending == "BE":
            stop = e; be_live = True; pending = None
        # journal add fills at this bar's open if still open
        if add_ts is not None and row["ts"] == add_ts:
            legs.append([tr["added_contracts"], tr["add_px"], None, None])
        # EOD
        if row["hhmm"] >= "15:55":
            px = rt(o - d * sl)
            for lg in legs:
                if lg[2] is None: lg[2], lg[3] = px, "TIME_EOD"
            return finish(tr, legs, d, sd, row["ts"], stall_bar)
        gap = (o <= stop) if d > 0 else (o >= stop)
        hs = (l <= stop) if d > 0 else (h >= stop)
        ht = use_tgt and ((h >= tgt) if d > 0 else (l <= tgt))
        reason = None
        if gap:
            px, reason = rt(o - d * sl), "STOP_GAP"
        elif hs and ht:
            if order == "stop_first": px, reason = rt(stop - d * sl), "STOP"
            else: px, reason = tgt, "TARGET"
        elif hs:
            px, reason = rt(stop - d * sl), ("STOP_BE" if be_live else "STOP")
        elif ht:
            px, reason = tgt, "TARGET"
        if reason:
            for lg in legs:
                if lg[2] is None: lg[2], lg[3] = px, reason
            return finish(tr, legs, d, sd, row["ts"], stall_bar)
        # decisions at this bar's close (only bars that closed)
        mfe = max(mfe, d * ((h if d > 0 else l) - e) / sd)
        close_r = d * (c - e) / sd
        if policy in ("C1", "D3") and stall_bar is None and mfe >= 0.8 and close_r <= 0.3:
            stall_bar = i
            pending = "BE" if policy == "C1" else "EXIT"
        if policy == "D1" and not be_live and mfe >= 2.0 and pending is None:
            pending = "BE"
    raise RuntimeError("ran off session")


def finish(tr, legs, d, sd, ts, stall_bar):
    gross = sum((lg[2] - lg[1]) * d * lg[0] * PT for lg in legs)
    qty = sum(lg[0] for lg in legs)
    net = gross - COMM * 2 * qty
    return dict(net_usd=net, R=net / tr["planned_risk_usd"], exit_reason=legs[0][3], exit_ts=ts, exit_px=legs[0][2],
                stall_bar=stall_bar)


def boot(df, col, n=2000, seed=1):
    rng = np.random.default_rng(seed)
    sess = df["session"].unique(); g = df.groupby("session")[col].agg(["sum", "count"])
    out = []
    for _ in range(n):
        s = rng.choice(sess, len(sess), replace=True)
        out.append(g.loc[s, "sum"].sum() / max(1, g.loc[s, "count"].sum()))
    return np.percentile(out, [2.5, 97.5])


def boot_sum(df, col, n=2000, seed=1):
    rng = np.random.default_rng(seed)
    sess = df["session"].unique(); g = df.groupby("session")[col].sum()
    out = [g.loc[rng.choice(sess, len(sess), replace=True)].sum() for _ in range(n)]
    return np.percentile(out, [2.5, 97.5])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--order", default="stop_first")
    ap.add_argument("--slip", type=int, default=1); a = ap.parse_args()
    tr, bars = load(a.data)
    kx = tr[tr["family"] == "KX"].reset_index(drop=True)
    res = {}
    for pol in ["P0", "C1", "D3", "D1"]:
        rows = [replay(r, bars, pol, a.order, a.slip) for _, r in kx.iterrows()]
        res[pol] = pd.DataFrame(rows)
    base = res["P0"]
    print(f"DATA={a.data}  order={a.order}  slip={a.slip} ticks   KX trades={len(kx)} sessions={kx.session.nunique()}")
    # reconciliation
    nonman = kx["exit_reason"] != "MANUAL"
    diff = (base["net_usd"] - kx["net_pnl_usd"]).abs()
    print(f"P0 vs journal: exact net on {(diff[nonman] < 0.01).sum()}/{nonman.sum()} non-MANUAL trades; "
          f"journal net ${kx.net_pnl_usd.sum():,.0f} vs replay ${base.net_usd.sum():,.0f}; MANUAL={int((~nonman).sum())}")
    for pol in ["C1", "D3", "D1"]:
        r = res[pol]
        d = pd.DataFrame(dict(session=kx["session"], dR=r["R"] - base["R"], dusd=r["net_usd"] - base["net_usd"],
                              changed=(r["net_usd"] - base["net_usd"]).abs() > 0.01, strategy=kx["strategy"]))
        if pol in ("C1", "D3"):
            m = r["stall_bar"].notna()
            sub = d[m]
            lo, hi = boot(sub, "dR"); print(f"{pol}: stall set n={m.sum()} sessions={sub.session.nunique()}  "
                                            f"P0 mean R={base.R[m].mean():+.2f}  {pol} mean R={r.R[m].mean():+.2f}  "
                                            f"paired dR={sub.dR.mean():+.3f} [{lo:+.2f},{hi:+.2f}]  d$={sub.dusd.sum():+,.0f}")
            for sv, g in sub.groupby("strategy"):
                lo, hi = boot(g, "dR"); print(f"      {sv}: n={len(g)} dR={g.dR.mean():+.3f} [{lo:+.2f},{hi:+.2f}]")
        else:
            lo, hi = boot_sum(d, "dusd"); lo2, hi2 = boot(d, "dR")
            print(f"{pol}: changed={d.changed.sum()}  paired d$={d.dusd.sum():+,.0f} [{lo:+,.0f},{hi:+,.0f}]  "
                  f"dR/entry={d.dR.mean():+.3f} [{lo2:+.2f},{hi2:+.2f}]  P0 total ${base.net_usd.sum():,.0f} -> ${r.net_usd.sum():,.0f}")
            for sv, g in d.groupby("strategy"):
                print(f"      {sv}: n={len(g)} d$={g.dusd.sum():+,.0f}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"); os.makedirs(out, exist_ok=True)
    tag = os.path.basename(os.path.normpath(a.data))
    pd.concat({k: v for k, v in res.items()}, axis=1).assign(trade_id=kx["trade_id"].values).to_csv(
        os.path.join(out, f"reproduce_{tag}_{a.order}_slip{a.slip}.csv"), index=False)


if __name__ == "__main__":
    main()
