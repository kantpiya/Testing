#!/usr/bin/env python3
"""Reviewer B (execution trader) -- small executability checks on the SYNTHETIC development set.

Independent mini-replay (conventions as the director's reproduce.py: bracket not live on the entry bar; stop fills on
touch at stop - 1 tick, or bar open - 1 tick if the bar opens through it; target at the limit on touch; journal add taken
at the journal add bar if still open; market exits at next open - 1 tick; flat at 15:55 open; $0.74/contract/side).

Questions answered (all SYNTHETIC):
  A. contract-count distribution per family (integer-lot constraints)
  B. C1 / C2: how often the breakeven level is already through the market at the bar the stop is placed (a modify would
     be rejected -> market exit), how often the new stop is hit in its first live bar, single-bar triggers, decision time
     of day, touch-vs-penetration swing on the tightened stop, $ per year
  C. C3: add-leg stop at entry -- exact-touch exposure, hit in the add bar, $ per year
  D. C4: PX far target -- $ per year, exact-touch target fills (limit-on-touch optimism), Stage B overlap with later
     signals under the 4-contract limit
Usage: python3 run.py [--data ../../data/synthetic]
"""
import argparse, os
import numpy as np, pandas as pd

TICK, PT, COMM = 0.25, 2.0, 0.74
HERE = os.path.dirname(os.path.abspath(__file__))


def rt(x):
    return np.round(x / TICK) * TICK


def load(d):
    tr = pd.read_csv(os.path.join(d, "trades.csv"))
    sg = pd.read_csv(os.path.join(d, "signals.csv"))
    b = pd.read_csv(os.path.join(d, "bars_MNQ_1min.csv"))
    b["ts"] = pd.to_datetime(b["ts"], utc=True).dt.tz_convert("America/New_York")
    b["session"] = b["ts"].dt.strftime("%Y-%m-%d")
    b["hhmm"] = b["ts"].dt.strftime("%H:%M")
    return tr, sg, {s: g.reset_index(drop=True) for s, g in b.groupby("session")}


def replay(tr, bars, policy, stop_trigger="touch", target_fill="touch", slip=1, far_tgt=None):
    """policy in P0, C1, C2, C3, C4. Returns dict with net, R, exit info and execution diagnostics."""
    d = 1 if tr["direction"] == "LONG" else -1
    b = bars[tr["session"]]
    i0 = int(np.where(b["ts"] == pd.Timestamp(tr["entry_ts"]))[0][0])
    e, stop0, tgt = tr["entry_px"], tr["initial_stop_px"], tr["initial_target_px"]
    if policy == "C4" and far_tgt is not None:
        tgt = far_tgt
    sd = abs(e - stop0)
    # legs: [qty, entry_px, stop_px, exit_px, exit_reason]
    legs = [[tr["initial_contracts"], e, stop0, None, None]]
    add_ts = pd.Timestamp(tr["add_ts"]) if isinstance(tr.get("add_ts"), str) and tr["add_ts"] else None
    sl = slip * TICK
    diag = dict(trigger_bar=None, trigger_hhmm=None, trigger_min=None, single_bar_trigger=False,
                be_gap_at_place=False, be_hit_first_bar=False, be_exact_touch=False, be_stop_live=False,
                add_stop_hit=False, add_stop_exact=False, add_stop_hit_add_bar=False, tgt_exact_touch=False,
                exit_bar=None)
    pending = None; mfe = -np.inf; be_bar = None
    for i in range(i0 + 1, len(b)):
        row = b.iloc[i]
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        if pending == "BE":
            for lg in legs:
                lg[2] = e
            diag["be_stop_live"] = True; be_bar = i; pending = None
            if (o <= e) if d > 0 else (o >= e):
                diag["be_gap_at_place"] = True
        if add_ts is not None and row["ts"] == add_ts and all(lg[3] is None for lg in legs):
            legs.append([tr["added_contracts"], tr["add_px"], e if policy == "C3" else stop0, None, None])
        if row["hhmm"] >= "15:55":
            px = rt(o - d * sl)
            for lg in legs:
                if lg[3] is None: lg[3], lg[4] = px, "TIME_EOD"
            diag["exit_bar"] = i
            return finish(tr, legs, d, row["ts"], diag)
        # evaluate each open leg's stop; shared target
        ht = ((h >= tgt) if d > 0 else (l <= tgt)) if target_fill == "touch" else ((h > tgt) if d > 0 else (l < tgt))
        tgt_exact = ((h == tgt) if d > 0 else (l == tgt))
        any_exit = False
        for k, lg in enumerate(legs):
            if lg[3] is not None:
                continue
            s = lg[2]
            gap = (o <= s) if d > 0 else (o >= s)
            if stop_trigger == "touch":
                hs = (l <= s) if d > 0 else (h >= s)
            else:
                hs = (l < s) if d > 0 else (h > s)
            exact = (l == s) if d > 0 else (h == s)
            if gap:
                lg[3], lg[4] = rt(o - d * sl), "STOP_GAP"
            elif hs and ht:
                lg[3], lg[4] = rt(s - d * sl), "STOP"   # stop_first (worst) ordering
            elif hs:
                lg[3], lg[4] = rt(s - d * sl), "STOP"
            elif ht:
                lg[3], lg[4] = tgt, "TARGET"
                if tgt_exact and not (((h > tgt) if d > 0 else (l < tgt))):
                    diag["tgt_exact_touch"] = True
            if lg[3] is not None:
                any_exit = True
                if lg[4] in ("STOP", "STOP_GAP") and s == e and policy in ("C1", "C2") and diag["be_stop_live"]:
                    if i == be_bar: diag["be_hit_first_bar"] = True
                    if exact and not gap and not (((l < s) if d > 0 else (h > s))): diag["be_exact_touch"] = True
                if lg[4] in ("STOP", "STOP_GAP") and policy == "C3" and k == 1:
                    diag["add_stop_hit"] = True
                    if exact and not gap and not (((l < s) if d > 0 else (h > s))): diag["add_stop_exact"] = True
                    if row["ts"] == add_ts: diag["add_stop_hit_add_bar"] = True
        if any_exit and all(lg[3] is not None for lg in legs):
            diag["exit_bar"] = i
            return finish(tr, legs, d, row["ts"], diag)
        # decisions at this bar's close
        mfe_prev = mfe
        mfe = max(mfe, d * ((h if d > 0 else l) - e) / sd)
        close_r = d * (c - e) / sd
        k = i - i0
        if policy == "C1" and diag["trigger_bar"] is None and mfe >= 0.8 and close_r <= 0.3:
            diag["trigger_bar"] = i; diag["trigger_hhmm"] = row["hhmm"]; diag["trigger_min"] = k
            diag["single_bar_trigger"] = mfe_prev < 0.8
            pending = "BE"
        if policy == "C2" and k == 20 and close_r >= 0.3:
            diag["trigger_bar"] = i; diag["trigger_hhmm"] = row["hhmm"]; diag["trigger_min"] = k
            pending = "BE"
    raise RuntimeError("ran off session")


def finish(tr, legs, d, ts, diag):
    gross = sum((lg[3] - lg[1]) * d * lg[0] * PT for lg in legs)
    qty = sum(lg[0] for lg in legs)
    net = gross - COMM * 2 * qty
    out = dict(net=net, R=net / tr["planned_risk_usd"], exit_ts=ts, exit_reason=legs[0][4], n_legs=len(legs))
    out.update(diag)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default=os.path.join(HERE, "..", "..", "data", "synthetic"))
    a = ap.parse_args()
    tr, sg, bars = load(a.data)
    print("ALL NUMBERS SYNTHETIC -- development set", a.data)
    kx = tr[tr.family == "KX"].reset_index(drop=True); px = tr[tr.family == "PX"].reset_index(drop=True)

    # ---------- A. contract counts ----------
    print("\n== A. integer-lot facts ==")
    for fam, g in tr.groupby("family"):
        dist = g.initial_contracts.value_counts().sort_index().to_dict()
        print(f"{fam}: n={len(g)} initial_contracts dist={dist}  one-lot share={(g.initial_contracts==1).mean():.2f}  "
              f"with add={int((g.added_contracts>0).sum())}  mean 1R=${g.planned_risk_usd.mean():.0f}")
    print(f"KX trades at 4 contracts (can never add): {(kx.initial_contracts==4).sum()}")

    # ---------- B. C1 / C2 ----------
    base = pd.DataFrame([replay(r, bars, "P0") for _, r in kx.iterrows()])
    for pol in ["C1", "C2"]:
        res = pd.DataFrame([replay(r, bars, pol) for _, r in kx.iterrows()])
        m = res.trigger_bar.notna()
        dusd = (res.net - base.net); dR = (res.R - base.R)
        print(f"\n== B. {pol}: triggers n={m.sum()} trades / {kx.session[m].nunique()} sessions ==")
        print(f"  paired d$ (dev year) = {dusd[m].sum():+,.0f}   dR per triggered trade = {dR[m].mean():+.3f}   "
              f"changed trades = {int((dusd.abs()>0.01).sum())}")
        print(f"  P0 exit reasons on triggered set: {base.exit_reason[m].value_counts().to_dict()}")
        print(f"  {pol} exit reasons on triggered set: {res.exit_reason[m].value_counts().to_dict()}")
        print(f"  BE level already through the market at the placement bar open (modify rejected -> market): "
              f"{int(res.be_gap_at_place[m].sum())}")
        print(f"  BE stop hit in its first live bar: {int(res.be_hit_first_bar[m].sum())}")
        print(f"  BE stop exits that were EXACT touches (no penetration): {int(res.be_exact_touch[m].sum())}")
        if pol == "C1":
            print(f"  single-bar triggers (same bar touched +0.8R and closed <= +0.3R): {int(res.single_bar_trigger[m].sum())}")
        tm = res.trigger_min[m]
        print(f"  trigger minute after entry: median {tm.median():.0f} IQR {tm.quantile(.25):.0f}-{tm.quantile(.75):.0f}; "
              f"trigger time of day: min {res.trigger_hhmm[m].min()} max {res.trigger_hhmm[m].max()}")
        # touch vs penetration swing on the tightened stop
        resp = pd.DataFrame([replay(r, bars, pol, stop_trigger="penetrate") for _, r in kx.iterrows()])
        basep = pd.DataFrame([replay(r, bars, "P0", stop_trigger="penetrate") for _, r in kx.iterrows()])
        print(f"  touch-vs-penetrate swing: {pol} net ${res.net.sum():,.0f} (touch) vs ${resp.net.sum():,.0f} (penetrate); "
              f"P0 ${base.net.sum():,.0f} vs ${basep.net.sum():,.0f}; paired d$ under penetrate = "
              f"{(resp.net-basep.net).sum():+,.0f}")
        # slippage 3 ticks
        res3 = pd.DataFrame([replay(r, bars, pol, slip=3) for _, r in kx.iterrows()])
        base3 = pd.DataFrame([replay(r, bars, "P0", slip=3) for _, r in kx.iterrows()])
        print(f"  paired d$ at 3-tick slippage: {(res3.net-base3.net).sum():+,.0f}")
        # drawdown
        def maxdd(s):
            c = s.cumsum(); return (c - c.cummax()).min()
        print(f"  max DD of cumulative KX net: P0 ${maxdd(base.net):,.0f} -> {pol} ${maxdd(res.net):,.0f}; "
              f"worst trade P0 ${base.net.min():,.0f} -> ${res.net.min():,.0f}; "
              f"P(R<-0.5) on triggered set {(base.R[m]<-0.5).mean():.2f} -> {(res.R[m]<-0.5).mean():.2f}")

    # ---------- C. C3 ----------
    res = pd.DataFrame([replay(r, bars, "C3") for _, r in kx.iterrows()])
    m = kx.added_contracts > 0
    dusd = res.net - base.net
    print(f"\n== C. C3 add-leg stop at entry: add trades n={m.sum()} / {kx.session[m].nunique()} sessions ==")
    print(f"  paired d$ (dev year) = {dusd.sum():+,.0f}  changed = {int((dusd.abs()>0.01).sum())}  "
          f"add-stop hits = {int(res.add_stop_hit.sum())}  of which EXACT touches = {int(res.add_stop_exact.sum())}  "
          f"hit inside the add fill bar = {int(res.add_stop_hit_add_bar.sum())}")
    resp = pd.DataFrame([replay(r, bars, "C3", stop_trigger="penetrate") for _, r in kx.iterrows()])
    basep = pd.DataFrame([replay(r, bars, "P0", stop_trigger="penetrate") for _, r in kx.iterrows()])
    print(f"  paired d$ under penetrate = {(resp.net-basep.net).sum():+,.0f}")
    def maxdd(s):
        c = s.cumsum(); return (c - c.cummax()).min()
    print(f"  max DD KX: P0 ${maxdd(base.net):,.0f} -> C3 ${maxdd(res.net):,.0f}; worst trade ${base.net.min():,.0f} -> ${res.net.min():,.0f}")

    # ---------- D. C4 ----------
    sgi = sg.set_index("signal_id")
    pxb = pd.DataFrame([replay(r, bars, "P0") for _, r in px.iterrows()])
    far = []
    for _, r in px.iterrows():
        w = sgi.loc[r.signal_id, "ref_width"]; d = 1 if r.direction == "LONG" else -1
        far.append(rt(r.initial_target_px + d * w / 2))
    res = pd.DataFrame([replay(r, bars, "C4", far_tgt=f) for (_, r), f in zip(px.iterrows(), far)])
    resp = pd.DataFrame([replay(r, bars, "C4", far_tgt=f, target_fill="penetrate") for (_, r), f in zip(px.iterrows(), far)])
    pxbp = pd.DataFrame([replay(r, bars, "P0", target_fill="penetrate") for _, r in px.iterrows()])
    dusd = res.net - pxb.net
    print(f"\n== D. C4 PX far target: n={len(px)} / {px.session.nunique()} sessions ==")
    print(f"  paired d$ (dev year) = {dusd.sum():+,.0f}  dR/entry = {(res.R-pxb.R).mean():+.3f}  changed = {int((dusd.abs()>0.01).sum())}")
    print(f"  exit reasons P0 {pxb.exit_reason.value_counts().to_dict()}  C4 {res.exit_reason.value_counts().to_dict()}")
    print(f"  far-target exits that were EXACT touches (limit may not fill): {int(res.tgt_exact_touch.sum())}  "
          f"(P0 midpoint exact touches: {int(pxb.tgt_exact_touch.sum())})")
    print(f"  limit-needs-penetration: C4 ${resp.net.sum():,.0f} vs P0 ${pxbp.net.sum():,.0f}; paired d$ = {(resp.net-pxbp.net).sum():+,.0f}")
    ent = pd.to_datetime(px.entry_ts, utc=True)
    hold0 = (pd.to_datetime(pxb.exit_ts, utc=True) - ent).dt.total_seconds() / 60
    hold4 = (pd.to_datetime(res.exit_ts, utc=True) - ent).dt.total_seconds() / 60
    print(f"  mean hold min: P0 {hold0.mean():.0f} -> C4 {hold4.mean():.0f}; C4 holds > 60 min: {int((hold4>60).sum())}")
    # Stage B overlap: signals (executed or rejected) arriving while the C4 position is still open but P0 would have been flat
    sg["signal_ts"] = pd.to_datetime(sg.signal_ts, utc=True).dt.tz_convert("America/New_York")
    tr_ts = tr.assign(entry=pd.to_datetime(tr.entry_ts, utc=True).dt.tz_convert("America/New_York"),
                      exit=pd.to_datetime(tr.exit_ts, utc=True).dt.tz_convert("America/New_York"))
    blocked, lost_usd, new_overlap = [], 0.0, 0
    for i, r in px.iterrows():
        p0x, c4x = pd.Timestamp(pxb.exit_ts[i]), pd.Timestamp(res.exit_ts[i])
        if c4x <= p0x: continue
        later = sg[(sg.signal_ts > p0x) & (sg.signal_ts <= c4x) & (sg.signal_ts.dt.strftime("%Y-%m-%d") == r.session)]
        for _, s in later.iterrows():
            new_overlap += 1
            # contracts open at that time under C4: this PX trade + other journal trades open at the signal time
            others = tr_ts[(tr_ts.session == r.session) & (tr_ts.trade_id != r.trade_id) & (tr_ts.entry <= s.signal_ts) & (tr_ts.exit > s.signal_ts)]
            open_ct = r.initial_contracts + (others.initial_contracts + others.added_contracts).sum()
            if open_ct + s.planned_contracts > 4:
                blocked.append(int(s.signal_id))
                if s.executed:
                    lost_usd += float(tr[tr.signal_id == s.signal_id].net_pnl_usd.iloc[0])
    print(f"  Stage B: later same-session signals arriving inside the C4 extension: {new_overlap}; "
          f"blocked by the 4-contract limit: {len(blocked)} {blocked}; journal net of blocked executed trades = ${lost_usd:,.0f}")
    print(f"  journal: PX signals rejected for the limit = {int(((sg.family=='PX') & (~sg.executed)).sum())}, "
          f"all rejected = {int((~sg.executed).sum())}")


if __name__ == "__main__":
    main()
