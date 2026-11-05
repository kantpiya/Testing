#!/usr/bin/env python3
"""
S2 - Breakout / failed-follow-through specialist.
Stage A paired replay of KX (directional breakout) entries on MNQ 1-minute bars.

Policies replayed on the IDENTICAL entries (trade_id, entry_px, initial_contracts, journal add):
  (a) ORIGINAL bracket : OCO stop + target, original add, flat at 15:55 open.
  (b) FAILURE rule     : at decision time entry+T min (close of bar T-1), if progress < X R -> exit at the
                         open of bar T, 1 tick adverse. Otherwise continue under (a).
  (c) TIME comparator  : unconditional exit at the open of bar T regardless of progress.
  (d) BREAKEVEN variant: at entry+T min, progress < X -> exit (as b); progress >= X -> stop moved to entry px.
Progress definitions (both knowable at decision time, use only bars whose close <= decision time):
  'mtm' : (close[T-1] - entry_px) * dir / stop_dist_pts  (open profit of the INITIAL leg, in R)
  'mfe' : max over bars 0..T-1 of favourable excursion / stop_dist_pts (in R)
1R = planned_risk_usd = initial_contracts * stop_dist_pts * $2 (unrounded stop distance), fixed per trade.

ALL DATA ARE SYNTHETIC (data/synthetic). Every number produced here is a statement about the method, not the market.

Run:  python3 src/S2/run.py     (from the research folder; paths are resolved relative to this file)
"""
import os, sys, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DATA = os.path.join(ROOT, 'data', 'synthetic')
OUT = os.path.join(HERE, 'out')
CHARTS = os.path.join(ROOT, 'charts')
os.makedirs(OUT, exist_ok=True); os.makedirs(CHARTS, exist_ok=True)

# ---------------------------------------------------------------- constants (ASSUMPTIONS from costs.csv / brief)
TICK = 0.25
PTVAL = 2.0
COMM = 0.74            # $/contract/side, every fill
SLIP_TICKS = 1         # market and stop fills; 0 on limit (target) fills
EOD_HHMM = (15, 55)    # flat at the 15:55 ET bar open
TZ = 'America/New_York'
ENTRY_BAR_EXITS = False  # journal convention: stop/target are not evaluated inside the entry bar (verified: trades 174, 332)

# ---------------------------------------------------------------- PRE-REGISTERED NOMINATION (fixed before any grid result was computed)
NOMINATED = dict(kind='fail', T=15, X=0.0, prog='mtm')     # "no open profit 15 minutes after entry -> exit"
COMPARATOR = dict(kind='time', T=15)                        # unconditional exit at the same horizon
T_GRID = [5, 10, 15, 20, 30]
X_GRID = [0.0, 0.2, 0.3, 0.5]
PROG_DEFS = ['mtm', 'mfe']
N_BOOT = 2000
SEED = 20261105

# ---------------------------------------------------------------- data
def load():
    bars = pd.read_csv(os.path.join(DATA, 'bars_MNQ_1min.csv'))
    bars['ts'] = pd.to_datetime(bars.ts, utc=True).dt.tz_convert(TZ)
    bars['session'] = bars.ts.dt.strftime('%Y-%m-%d')
    bars['min_et'] = bars.ts.dt.hour * 60 + bars.ts.dt.minute      # ET minute of day of the bar open
    trades = pd.read_csv(os.path.join(DATA, 'trades.csv'))
    for c in ['entry_ts', 'exit_ts', 'add_ts']:
        trades[c + '_dt'] = pd.to_datetime(trades[c], utc=True).dt.tz_convert(TZ)
    trades['dir'] = np.where(trades.direction == 'LONG', 1, -1)
    trades['stop_dist'] = trades.planned_risk_usd / (trades.initial_contracts * PTVAL)   # unrounded, pts per 1R
    kx = trades[trades.family == 'KX'].reset_index(drop=True).copy()
    sess = {s: g.reset_index(drop=True) for s, g in bars.groupby('session')}
    return bars, trades, kx, sess


# ---------------------------------------------------------------- replay engine (one trade, one policy)
def replay(tr, sb, pol, order='stop_first'):
    """tr: trade row; sb: session bars DataFrame; pol: policy dict.
    Returns dict with exit info, legs, gross/commission/net, fired flag, progress at decision time."""
    d = int(tr.dir); n0 = int(tr.initial_contracts)
    ent = float(tr.entry_px); stop = float(tr.initial_stop_px); tgt = float(tr.initial_target_px)
    sd = float(tr.stop_dist)
    o = sb.open.values; h = sb.high.values; l = sb.low.values; c = sb.close.values
    mins_et = sb['min_et'].values                      # ET minute-of-day of each bar OPEN (tz-aware source)
    i0 = int(np.where(sb.ts == tr.entry_ts_dt)[0][0])
    has_add = tr.added_contracts > 0
    add_i = int(np.where(sb.ts == tr.add_ts_dt)[0][0]) if has_add else -1
    kind = pol['kind']; T = pol.get('T', None); X = pol.get('X', None); prog_def = pol.get('prog', 'mtm')
    legs = [(ent, n0)]            # (price, qty)
    comm = COMM * n0              # entry commission
    fired = False; progress = np.nan; mfe = -np.inf
    be_set = False
    exit_px = None; exit_reason = None; exit_i = None
    eod_min = EOD_HHMM[0] * 60 + EOD_HHMM[1]
    for i in range(i0, len(sb)):
        k = i - i0
        fav = (h[i] - ent) * d if d == 1 else (ent - l[i])
        # ---- actions decided at the close of bar k-1, executed at the open of bar k (market, 1 tick adverse)
        if k >= 1 and kind in ('fail', 'time', 'be') and k == T:
            mtm = (c[i - 1] - ent) * d / sd
            progress = mtm if prog_def == 'mtm' else mfe / sd
            do_exit = (kind == 'time') or (progress < X)
            if do_exit:
                exit_px = o[i] - d * SLIP_TICKS * TICK; exit_reason = 'RULE'; exit_i = i; fired = True
                break
            elif kind == 'be':
                stop = ent; be_set = True
        # ---- EOD flat at 15:55 ET open
        if mins_et[i] >= eod_min:
            exit_px = o[i] - d * SLIP_TICKS * TICK; exit_reason = 'TIME_EOD'; exit_i = i
            break
        # ---- journal add executes at this bar's open (only if still open and not exiting)
        if has_add and i == add_i:
            legs.append((float(tr.add_px), int(tr.added_contracts))); comm += COMM * int(tr.added_contracts)
        # ---- intrabar stop / target on bar k (entry bar skipped unless ENTRY_BAR_EXITS; the journal skips it)
        if k == 0 and not ENTRY_BAR_EXITS:
            mfe = max(mfe, fav); continue
        if d == 1:
            hit_s = l[i] <= stop; hit_t = h[i] >= tgt
            s_px = o[i] if o[i] <= stop else stop - TICK
        else:
            hit_s = h[i] >= stop; hit_t = l[i] <= tgt
            s_px = o[i] if o[i] >= stop else stop + TICK
        if hit_s and hit_t:
            if order == 'stop_first':
                exit_px, exit_reason = s_px, ('STOP_GAP' if s_px == o[i] else 'STOP')
            else:
                exit_px, exit_reason = tgt, 'TARGET'
            exit_i = i; break
        if hit_s:
            exit_px, exit_reason, exit_i = s_px, ('STOP_GAP' if s_px == o[i] else 'STOP'), i; break
        if hit_t:
            exit_px, exit_reason, exit_i = tgt, 'TARGET', i; break
        mfe = max(mfe, fav)
    qty = sum(q for _, q in legs)
    comm += COMM * qty
    gross = sum(q * (exit_px - p) * d * PTVAL for p, q in legs)
    return dict(exit_i=exit_i, exit_min=exit_i - i0, exit_ts=sb.ts.iloc[exit_i], exit_px=exit_px,
                exit_reason=exit_reason, qty=qty, add_included=len(legs) > 1, gross=gross, comm=comm,
                net=gross - comm, fired=fired, progress=progress, be_set=be_set)


def run_policy(kx, sess, pol, order='stop_first'):
    rows = []
    for _, tr in kx.iterrows():
        r = replay(tr, sess[tr.session], pol, order)
        r['trade_id'] = tr.trade_id; rows.append(r)
    df = pd.DataFrame(rows).set_index('trade_id')
    df['netR'] = df.net / kx.set_index('trade_id').planned_risk_usd
    return df


def pol_name(p):
    if p['kind'] == 'bracket': return 'ORIGINAL'
    if p['kind'] == 'time': return f"TIME_T{p['T']}"
    return f"{p['kind'].upper()}_{p['prog']}_T{p['T']}_X{p['X']:+.1f}"


# ---------------------------------------------------------------- bootstrap over whole sessions
def session_bootstrap(delta_usd, delta_R, sessions_of_trade, all_sessions, n=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    S = np.asarray(all_sessions); m = len(S)
    sess_idx = {s: i for i, s in enumerate(S)}
    # per-session sums and counts
    su = np.zeros(m); sr = np.zeros(m); cnt = np.zeros(m)
    for du, dr, s in zip(delta_usd, delta_R, sessions_of_trade):
        j = sess_idx[s]; su[j] += du; sr[j] += dr; cnt[j] += 1
    sums = np.empty(n); means = np.empty(n)
    for b in range(n):
        pick = rng.integers(0, m, m)
        sums[b] = su[pick].sum(); nn = cnt[pick].sum()
        means[b] = sr[pick].sum() / nn if nn > 0 else np.nan
    return (np.nanpercentile(sums, [2.5, 97.5]), np.nanpercentile(means, [2.5, 97.5]))


def main():
    bars, trades, kx, sess = load()
    all_sessions = sorted(trades.session.unique())
    kxi = kx.set_index('trade_id')
    out = {}
    print(f"SYNTHETIC development set: {len(trades)} trades, {len(all_sessions)} sessions; KX trades = {len(kx)} in {kx.session.nunique()} sessions")
    print(f"NOMINATED (fixed before results): {pol_name(NOMINATED)}; COMPARATOR: {pol_name(COMPARATOR)}")

    # ------------------------------------------------------------ (a) baseline + reconciliation with journal
    base = run_policy(kx, sess, dict(kind='bracket'))
    base_tf = run_policy(kx, sess, dict(kind='bracket'), order='target_first')
    j = kxi
    rec = pd.DataFrame({'j_reason': j.exit_reason, 'r_reason': base.exit_reason, 'j_net': j.net_pnl_usd, 'r_net': base.net,
                        'j_exit_ts': j.exit_ts_dt, 'r_exit_ts': base.exit_ts})
    rec['same_reason'] = rec.j_reason == rec.r_reason
    rec['same_ts'] = rec.j_exit_ts == rec.r_exit_ts
    rec['dnet'] = rec.r_net - rec.j_net
    print("\n== Reconciliation of my ORIGINAL-bracket replay vs trades.csv (KX, SYNTHETIC) ==")
    print(f"exit reason identical: {rec.same_reason.sum()}/{len(rec)}; exit bar identical: {rec.same_ts.sum()}/{len(rec)}; "
          f"|net diff|<=$0.01: {(rec.dnet.abs() <= 0.01).sum()}/{len(rec)}")
    print(f"journal KX net ${j.net_pnl_usd.sum():,.2f} vs replay ${base.net.sum():,.2f}; stop-first vs target-first ordering identical on "
          f"{(base.net.values == base_tf.net.values).sum()}/{len(base)} trades (no same-bar stop+target bars in KX)")
    mism = rec[~rec.same_reason | (rec.dnet.abs() > 0.01)]
    print(mism[['j_reason', 'r_reason', 'j_net', 'r_net', 'dnet']].to_string())
    tsm = rec[~rec.same_ts & (rec.dnet.abs() <= 0.01)]
    print(f"exit-bar mismatches with identical net ({len(tsm)}): journal exit_ts vs replay (first 5):")
    print(tsm[['j_reason', 'j_exit_ts', 'r_exit_ts']].head(5).to_string())
    rec.to_csv(os.path.join(OUT, 'reconciliation.csv'))

    # baseline-defined largest winners (top 10% by baseline net R), fixed across policies
    n_top = int(np.ceil(0.10 * len(base)))
    top_ids = set(base.netR.sort_values(ascending=False).index[:n_top])
    thr = base.netR.sort_values(ascending=False).iloc[n_top - 1]
    print(f"\nLargest winners = top 10% by BASELINE net R: n={n_top}, threshold net R >= {thr:.3f}")

    # still-open counts at each T under the original bracket
    print("\n== Trades still open at minute T under the original bracket (trade count / session count) ==")
    for T in T_GRID:
        openT = base.exit_min >= T
        print(f"T={T:>2}: open {openT.sum():>3} trades / {kx.session[openT.values].nunique():>3} sessions; "
              f"original exits before T: {(~openT).sum()}")

    # ------------------------------------------------------------ grid of policies (every cell counted)
    cells = []
    for prog in PROG_DEFS:
        for T in T_GRID:
            for X in X_GRID:
                cells.append(dict(kind='fail', T=T, X=X, prog=prog))
    for T in T_GRID:
        cells.append(dict(kind='time', T=T))
    cells.append(dict(kind='be', T=NOMINATED['T'], X=NOMINATED['X'], prog=NOMINATED['prog']))
    results = {}
    summ = []
    for pol in cells:
        name = pol_name(pol)
        df = run_policy(kx, sess, pol)
        results[name] = df
        dusd = df.net - base.net; dR = df.netR - base.netR
        ci_usd, ci_R = session_bootstrap(dusd.values, dR.values, kx.session.values, all_sessions)
        fired = df.fired
        top_fired = [t for t in df.index[fired] if t in top_ids]
        summ.append(dict(policy=name, kind=pol['kind'], prog=pol.get('prog', ''), T=pol.get('T'), X=pol.get('X'),
                         n_trades=len(df), n_sessions=kx.session.nunique(), n_fired=int(fired.sum()),
                         sess_fired=kx.session[fired.values].nunique(),
                         orig_net_usd=base.net.sum(), pol_net_usd=df.net.sum(), delta_net_usd=dusd.sum(),
                         ci_usd_lo=ci_usd[0], ci_usd_hi=ci_usd[1],
                         orig_meanR=base.netR.mean(), pol_meanR=df.netR.mean(), delta_meanR=dR.mean(),
                         ci_R_lo=ci_R[0], ci_R_hi=ci_R[1],
                         n_top10_fired=len(top_fired), usd_surrendered_top10=float((base.net - df.net)[top_fired].sum()),
                         wins_delta=float(dusd[dusd > 0].sum()), losses_delta=float(dusd[dusd < 0].sum())))
    S = pd.DataFrame(summ)
    S.to_csv(os.path.join(OUT, 'grid_summary.csv'), index=False)
    print(f"\n== Policy cells examined: {len(cells)} (= {len(PROG_DEFS)}x{len(T_GRID)}x{len(X_GRID)} failure cells + {len(T_GRID)} time exits + 1 breakeven variant) ==")
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
    cols = ['policy', 'n_fired', 'sess_fired', 'delta_net_usd', 'ci_usd_lo', 'ci_usd_hi', 'delta_meanR', 'ci_R_lo', 'ci_R_hi', 'n_top10_fired', 'usd_surrendered_top10']
    print(S[cols].round(3).to_string(index=False))

    # ------------------------------------------------------------ nominated rule: deep dive
    nom = pol_name(NOMINATED); cmp_ = pol_name(COMPARATOR); be = pol_name(cells[-1])
    print(f"\n== NOMINATED rule {nom} vs ORIGINAL (paired, all {len(kx)} KX entries, {kx.session.nunique()} sessions, costs included) ==")
    df = results[nom]; d = df.net - base.net
    fired = df.fired
    row = S[S.policy == nom].iloc[0]
    print(f"original net ${base.net.sum():,.2f} (mean {base.netR.mean():+.4f} R/entry) -> rule net ${df.net.sum():,.2f} (mean {df.netR.mean():+.4f} R/entry)")
    print(f"paired delta: ${row.delta_net_usd:,.2f} total, 95% session-bootstrap CI [{row.ci_usd_lo:,.0f}, {row.ci_usd_hi:,.0f}]; "
          f"mean {row.delta_meanR:+.4f} R/entry, CI [{row.ci_R_lo:+.4f}, {row.ci_R_hi:+.4f}]  ({N_BOOT} draws over {len(all_sessions)} sessions)")
    print(f"rule fired on {fired.sum()} trades / {kx.session[fired.values].nunique()} sessions; among them original outcome: "
          f"{base.exit_reason[fired].value_counts().to_dict()}")
    print(f"comparator {cmp_}: delta ${S[S.policy == cmp_].iloc[0].delta_net_usd:,.2f}, CI [{S[S.policy == cmp_].iloc[0].ci_usd_lo:,.0f}, {S[S.policy == cmp_].iloc[0].ci_usd_hi:,.0f}]")
    print(f"breakeven variant {be}: delta ${S[S.policy == be].iloc[0].delta_net_usd:,.2f}, CI [{S[S.policy == be].iloc[0].ci_usd_lo:,.0f}, {S[S.policy == be].iloc[0].ci_usd_hi:,.0f}]; "
          f"BE stop set on {int(results[be].be_set.sum())} trades")
    # breakeven: both orderings when the BE stop and target share a bar
    be_tf = run_policy(kx, sess, cells[-1], order='target_first')
    print(f"  breakeven variant, target-first ordering: delta ${(be_tf.net - base.net).sum():,.2f}; trades where ordering matters: {int((be_tf.net != results[be].net).sum())}")

    # profit-vs-protection breakdown (fired trades only)
    f = df[fired]; b = base[fired]
    dg = f.gross - b.gross; dc = f.comm - b.comm
    orig_loser = b.net < 0; orig_winner = b.net > 0
    print("\n-- Profit-vs-protection breakdown, nominated rule, fired trades only (gross = price P&L incl. slippage; costs = commissions) --")
    print(f"  losses avoided   (orig loser,  gross delta>0): n={int((orig_loser & (dg > 0)).sum())}, ${dg[orig_loser & (dg > 0)].sum():,.2f}")
    print(f"  losses worsened  (orig loser,  gross delta<0): n={int((orig_loser & (dg < 0)).sum())}, ${dg[orig_loser & (dg < 0)].sum():,.2f}")
    print(f"  winners surrendered (orig winner, gross delta<0): n={int((orig_winner & (dg < 0)).sum())}, ${dg[orig_winner & (dg < 0)].sum():,.2f}")
    print(f"  winners improved (orig winner, gross delta>0): n={int((orig_winner & (dg > 0)).sum())}, ${dg[orig_winner & (dg > 0)].sum():,.2f}")
    print(f"  incremental commissions (rule - orig): ${dc.sum():,.2f}  (adds not taken: {int((b.add_included & ~f.add_included).sum())})")
    print(f"  NET paired delta on fired trades: ${(f.net - b.net).sum():,.2f}; on all {len(kx)} entries: ${d.sum():,.2f}")
    top_fired = [t for t in f.index if t in top_ids]
    print(f"  exits shortly before a large winner: {len(top_fired)} of the {n_top} top-10% baseline winners were exited by the rule; "
          f"dollars surrendered on them ${(base.net - df.net)[top_fired].sum():,.2f}; those winners' baseline net ${base.net[top_fired].sum():,.2f}")
    print(f"  original losing trades avoided (orig net<0 among fired): n={int(orig_loser.sum())}, their baseline net ${b.net[orig_loser].sum():,.2f}, under rule ${f.net[orig_loser].sum():,.2f}")
    # distribution of fired-trade original outcomes in R
    print(f"  fired trades: baseline net R mean {b.netR.mean():+.3f}, rule net R mean {f.netR.mean():+.3f}; baseline R quantiles {b.netR.quantile([.1,.5,.9]).round(2).to_dict()}")

    # ------------------------------------------------------------ competing explanation: is progress at T informative about what follows?
    T = NOMINATED['T']
    openT = base.exit_min >= T
    mtmT = pd.Series(np.nan, index=base.index)
    for tid in base.index[openT]:
        tr = kxi.loc[tid]; sb = sess[tr.session]; i0 = int(np.where(sb.ts == tr.entry_ts_dt)[0][0])
        mtmT[tid] = (sb.close.iloc[i0 + T - 1] - tr.entry_px) * tr.dir / tr.stop_dist
    buck = pd.cut(mtmT[openT], [-9, -0.5, 0.0, 0.5, 1.0, 9], labels=['< -0.5R', '-0.5..0R', '0..+0.5R', '+0.5..+1R', '>= +1R'])
    print(f"\n-- Conditional on being open at minute {T} under the original bracket: forward outcome by progress bucket (mtm, initial leg) --")
    print("   forward_R = baseline final net R minus initial-leg mtm R at T (includes add-leg P&L and costs; approximate), SYNTHETIC")
    ct = []
    for g in buck.cat.categories:
        ids = buck.index[buck == g]
        if len(ids) == 0: continue
        ct.append(dict(bucket=g, n_trades=len(ids), n_sessions=kxi.loc[ids, 'session'].nunique(), mean_mtm_T=mtmT[ids].mean(),
                       P_target=(base.exit_reason[ids] == 'TARGET').mean(), mean_final_R=base.netR[ids].mean(),
                       mean_forward_R=(base.netR[ids] - mtmT[ids]).mean(), median_forward_R=(base.netR[ids] - mtmT[ids]).median()))
    CT = pd.DataFrame(ct); CT.to_csv(os.path.join(OUT, 'conditional_T15.csv'), index=False)
    print(CT.round(3).to_string(index=False))
    allo = base.index[openT]
    print(f"   all open at T={T}: n={len(allo)} trades/{kxi.loc[allo,'session'].nunique()} sessions, P_target={(base.exit_reason[allo]=='TARGET').mean():.3f}, "
          f"mean forward R={(base.netR[allo]-mtmT[allo]).mean():+.3f}; corr(mtm_T, forward_R)={np.corrcoef(mtmT[allo], base.netR[allo]-mtmT[allo])[0,1]:+.3f}")

    # ------------------------------------------------------------ splits: version and half
    print("\n-- Splits (nominated rule vs original; paired delta, costs included) --")
    half_cut = '2025-11-01'
    kx['half'] = np.where(kx.session < half_cut, 'H1 (2025-05..2025-10)', 'H2 (2025-11..2026-04)')
    split_rows = []
    for col in ['strategy', 'half']:
        for g, idx in kx.groupby(col).groups.items():
            ids = kx.loc[idx, 'trade_id'].values
            dd = (df.net - base.net)[ids]; dR = (df.netR - base.netR)[ids]
            ci_u, ci_r = session_bootstrap(dd.values, dR.values, kx.loc[idx, 'session'].values, sorted(kx.loc[idx, 'session'].unique()))
            split_rows.append(dict(split=col, group=g, n_trades=len(ids), n_sessions=kx.loc[idx, 'session'].nunique(),
                                   n_fired=int(df.fired[ids].sum()), orig_net=base.net[ids].sum(), rule_net=df.net[ids].sum(),
                                   delta_usd=dd.sum(), ci_lo=ci_u[0], ci_hi=ci_u[1], delta_meanR=dR.mean(), ciR_lo=ci_r[0], ciR_hi=ci_r[1],
                                   cmp_delta_usd=(results[cmp_].net - base.net)[ids].sum()))
    SP = pd.DataFrame(split_rows); SP.to_csv(os.path.join(OUT, 'splits.csv'), index=False)
    print(SP.round(3).to_string(index=False))

    # ------------------------------------------------------------ worked examples
    print("\n== Worked examples (nominated rule) ==")
    ex_useful = (df.net - base.net)[fired & (base.exit_reason.isin(['STOP', 'STOP_GAP']))].idxmax()
    ex_false = (df.net - base.net)[fired & (base.exit_reason == 'TARGET')].idxmin()
    examples = {}
    for label, tid in [('USEFUL EXIT', ex_useful), ('COSTLY FALSE ALARM', ex_false)]:
        tr = kx[kx.trade_id == tid].iloc[0]; sb = sess[tr.session]
        i0 = int(np.where(sb.ts == tr.entry_ts_dt)[0][0]); T = NOMINATED['T']
        rows = []
        mfe = -np.inf
        for k in range(0, min(T + 11, len(sb) - i0)):
            i = i0 + k; brow = sb.iloc[i]
            fav = (brow.high - tr.entry_px) * tr.dir if tr.dir == 1 else (tr.entry_px - brow.low)
            mfe = max(mfe, fav)
            rows.append(dict(k=k, bar_open=brow.ts.strftime('%H:%M'), close_R=round((brow.close - tr.entry_px) * tr.dir / tr.stop_dist, 3),
                             mfe_R=round(mfe / tr.stop_dist, 3), worst_R=round((brow.low - tr.entry_px) * tr.dir / tr.stop_dist, 3) if tr.dir == 1 else round((tr.entry_px - brow.high) / tr.stop_dist, 3)))
        E = pd.DataFrame(rows)
        E['note'] = ''
        E.loc[E.k == T - 1, 'note'] = f'<- decision knowable at this bar close ({(tr.entry_ts_dt + pd.Timedelta(minutes=T)).strftime("%H:%M")})'
        E.loc[E.k == T, 'note'] = '<- rule exit at this bar open (1 tick adverse)'
        print(f"\n{label}: trade_id={tid} session={tr.session} {tr.strategy} {tr.direction} entry {tr.entry_ts_dt.strftime('%H:%M')} @ {tr.entry_px} "
              f"n0={tr.initial_contracts} stop {tr.initial_stop_px} target {tr.initial_target_px} 1R=${tr.planned_risk_usd:.2f} add={'yes @'+str(tr.add_px)+' '+tr.add_ts_dt.strftime('%H:%M') if tr.added_contracts>0 else 'no'}")
        print(f"  ORIGINAL: exit {base.exit_reason[tid]} at minute {base.exit_min[tid]} px {base.exit_px[tid]} net ${base.net[tid]:,.2f} ({base.netR[tid]:+.2f} R)")
        print(f"  RULE    : progress at decision {df.progress[tid]:+.3f} R (< {NOMINATED['X']:+.1f}) -> exit minute {df.exit_min[tid]} px {df.exit_px[tid]} net ${df.net[tid]:,.2f} ({df.netR[tid]:+.2f} R); paired delta ${df.net[tid]-base.net[tid]:,.2f}")
        print(E.to_string(index=False))
        examples[label] = dict(trade_id=int(tid), path=E, tr=tr)

    # ------------------------------------------------------------ charts
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        for ax, prog in zip(axes, PROG_DEFS):
            M = S[(S.kind == 'fail') & (S.prog == prog)].pivot(index='X', columns='T', values='delta_net_usd')
            im = ax.imshow(M.values, cmap='RdBu', vmin=-abs(S.delta_net_usd).max(), vmax=abs(S.delta_net_usd).max(), aspect='auto')
            ax.set_xticks(range(len(M.columns))); ax.set_xticklabels(M.columns); ax.set_yticks(range(len(M.index))); ax.set_yticklabels([f'{x:+.1f}R' for x in M.index])
            ax.set_xlabel('T (minutes after entry)'); ax.set_ylabel('X (progress threshold)')
            ax.set_title(f'progress = {prog} (SYNTHETIC)', fontsize=10)
            for (yi, xi), v in np.ndenumerate(M.values):
                ax.text(xi, yi, f'{v:,.0f}', ha='center', va='center', fontsize=8)
        fig.colorbar(im, ax=axes, shrink=0.8, label='delta net $ (240 KX entries, costs incl.)')
        fig.savefig(os.path.join(CHARTS, 'S2_grid_delta_usd.png'), dpi=130, bbox_inches='tight'); plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for ax, (label, ex) in zip(axes, examples.items()):
            E = ex['path']; T = NOMINATED['T']
            ax.plot(E.k, E.close_R, marker='o', ms=3, label='open profit at bar close (R)')
            ax.plot(E.k, E.mfe_R, ls='--', label='MFE so far (R)')
            ax.axhline(0, color='k', lw=0.6); ax.axhline(NOMINATED['X'], color='grey', lw=0.6, ls=':')
            ax.axvline(T - 1, color='red', lw=1, ls='--', label='decision knowable (close of bar T-1)')
            ax.axvline(T, color='orange', lw=1, ls=':', label='rule exit (open of bar T)')
            ax.set_title(f"{label}: trade {ex['trade_id']} {ex['tr'].session} (SYNTHETIC)", fontsize=10)
            ax.set_xlabel('minute after entry (bar index k)'); ax.set_ylabel('R'); ax.legend(fontsize=7)
        fig.tight_layout(); fig.savefig(os.path.join(CHARTS, 'S2_worked_examples.png'), dpi=130); plt.close(fig)

        # cumulative paired delta through time (nominated rule and comparator)
        fig, ax = plt.subplots(figsize=(9, 3.8))
        order_ = kx.sort_values('entry_ts_dt').trade_id.values
        for name in [nom, cmp_, be]:
            ax.plot(pd.to_datetime(kx.set_index('trade_id').loc[order_, 'session']), (results[name].net - base.net)[order_].cumsum().values, label=name)
        ax.axhline(0, color='k', lw=0.6); ax.set_ylabel('cumulative paired delta net $'); ax.set_title('Cumulative paired delta vs ORIGINAL, KX entries (SYNTHETIC, costs incl.)', fontsize=10)
        ax.axvline(pd.Timestamp('2026-01-01'), color='grey', ls=':', lw=0.8); ax.text(pd.Timestamp('2026-01-02'), ax.get_ylim()[0], 'v2', fontsize=8)
        ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(CHARTS, 'S2_cumulative_delta.png'), dpi=130); plt.close(fig)
        print("\ncharts written: charts/S2_grid_delta_usd.png, charts/S2_worked_examples.png, charts/S2_cumulative_delta.png")
    except Exception as e:
        print('chart error', e)

    # per-trade table for nominated rule
    PT = pd.DataFrame({'session': kxi.session, 'strategy': kxi.strategy, 'orig_reason': base.exit_reason, 'orig_min': base.exit_min, 'orig_net': base.net, 'orig_netR': base.netR,
                       'fired': df.fired, 'progress_at_T': df.progress, 'rule_reason': df.exit_reason, 'rule_net': df.net, 'delta_net': df.net - base.net, 'top10': [t in top_ids for t in base.index]})
    PT.to_csv(os.path.join(OUT, 'per_trade_nominated.csv'))
    # overlap flag: alternatives never hold longer than the original
    longer = int((df.exit_min > base.exit_min).sum())
    print(f"\nOverlap check: trades where the nominated rule holds LONGER than the original: {longer} (rule can only exit earlier or identically)")


if __name__ == '__main__':
    main()
