#!/usr/bin/env python3
"""Chart a single trade replay: price path with original bracket, open profit in R, and labelled decision instants.

Usage (library):
    from plot_replay import plot_trade
    plot_trade(trade_row, bars_mnq, events=[("first knowable: no +0.3R by min 12", ts, "C3")], out="charts/x.png", title="...")
"""
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MNQ_PT = 2.0


def session_bars(bars, session):
    b = bars[bars["ts"].dt.strftime("%Y-%m-%d") == session].reset_index(drop=True)
    return b


def plot_trade(tr, bars, events, out, title, policy_exits=None, window=(-10, 75), synthetic=True):
    """tr: a row of trades.csv (Series). bars: MNQ bars with tz-aware ts. events: list of (label, ts, color).
    policy_exits: list of (policy_name, exit_ts, exit_px, color)."""
    b = session_bars(bars, tr["session"])
    entry_ts = pd.Timestamp(tr["entry_ts"])
    i0 = int(np.searchsorted(b["ts"].values, np.datetime64(entry_ts.tz_convert("UTC").tz_localize(None))))
    lo, hi = max(0, i0 + window[0]), min(len(b), i0 + window[1])
    seg = b.iloc[lo:hi].reset_index(drop=True)
    d = 1 if tr["direction"] == "LONG" else -1
    risk_pts = abs(tr["entry_px"] - tr["initial_stop_px"])
    minutes = (seg["ts"] - entry_ts).dt.total_seconds() / 60.0
    open_r = d * (seg["close"] - tr["entry_px"]) / risk_pts
    hi_r = d * ((seg["high"] if d > 0 else seg["low"]) - tr["entry_px"]) / risk_pts
    lo_r = d * ((seg["low"] if d > 0 else seg["high"]) - tr["entry_px"]) / risk_pts

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True, gridspec_kw=dict(height_ratios=[2, 1.2]))
    # candles as hl bars + close line
    ax1.vlines(minutes, seg["low"], seg["high"], color="#777", lw=1)
    ax1.plot(minutes, seg["close"], color="#333", lw=1.2, label="MNQ close")
    ax1.axhline(tr["entry_px"], color="#1f77b4", ls="--", lw=1, label=f"entry {tr['entry_px']:.2f}")
    ax1.axhline(tr["initial_stop_px"], color="#d62728", ls="--", lw=1, label=f"orig stop {tr['initial_stop_px']:.2f}")
    ax1.axhline(tr["initial_target_px"], color="#2ca02c", ls="--", lw=1, label=f"orig target {tr['initial_target_px']:.2f}")
    if not pd.isna(tr.get("add_px", np.nan)):
        add_m = (pd.Timestamp(tr["add_ts"]) - entry_ts).total_seconds() / 60
        ax1.scatter([add_m], [tr["add_px"]], marker="^" if d > 0 else "v", color="#ff7f0e", s=70, zorder=5, label="add fill")
    ex_m = (pd.Timestamp(tr["exit_ts"]) - entry_ts).total_seconds() / 60
    ax1.scatter([ex_m], [tr["exit_px"]], marker="x", color="k", s=80, zorder=6, label=f"orig exit {tr['exit_reason']}")
    for name, ets, epx, col in (policy_exits or []):
        m = (pd.Timestamp(ets) - entry_ts).total_seconds() / 60
        ax1.scatter([m], [epx], marker="o", facecolors="none", edgecolors=col, s=110, lw=2, zorder=6, label=f"{name} exit")
    ax1.set_ylabel("MNQ price")
    ax1.legend(loc="best", fontsize=8, ncol=2)
    # R panel
    ax2.fill_between(minutes, lo_r, hi_r, color="#bbb", alpha=0.5, label="bar range (R)")
    ax2.plot(minutes, open_r, color="#333", lw=1.2, label="open profit at close (R)")
    for lvl, col in [(0, "#1f77b4"), (0.3, "#9467bd"), (0.8, "#8c564b"), (-1, "#d62728")]:
        ax2.axhline(lvl, color=col, ls=":", lw=0.9)
    y_top, y_bot = hi_r.max(), lo_r.min()
    step = (y_top - y_bot) * 0.11
    for k, (label, ets, col) in enumerate(events):
        m = (pd.Timestamp(ets) - entry_ts).total_seconds() / 60
        for ax in (ax1, ax2):
            ax.axvline(m, color=col, lw=1.2, alpha=0.9)
        ax2.annotate(f"{k + 1}. {label}", xy=(m, y_top - k * step), xytext=(m + 0.8, y_top - k * step),
                     fontsize=8, color=col, va="top", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    ax2.set_xlabel("minutes since entry fill")
    ax2.set_ylabel("open profit (R, initial leg)")
    ax2.legend(loc="lower left", fontsize=8)
    tag = "SYNTHETIC DATA — illustrative replay, not an empirical result" if synthetic else ""
    fig.suptitle(f"{title}\n{tag}", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out
