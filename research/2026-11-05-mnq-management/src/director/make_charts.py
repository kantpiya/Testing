#!/usr/bin/env python3
"""Four charted trade replays (SYNTHETIC data). Trade choices come from the specialists' worked examples:
S2 trade 130 (failed breakout exited well), S2 trade 306 (winner cut too early), director-selected PX trade 186
(reversal that needed time), S4 trade 265 (pyramid where protecting the add damaged a major winner)."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plot_replay import plot_trade

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tr = pd.read_csv(os.path.join(ROOT, "data/synthetic/trades.csv")).set_index("trade_id")
b = pd.read_csv(os.path.join(ROOT, "data/synthetic/bars_MNQ_1min.csv"))
b["ts"] = pd.to_datetime(b["ts"], utc=True).dt.tz_convert("America/New_York")
out = os.path.join(ROOT, "charts")


def bar_at(trade, minutes):
    return pd.Timestamp(trade["entry_ts"]) + pd.Timedelta(minutes=minutes)


def open_at(ts):
    return float(b.loc[b["ts"] == ts, "open"].iloc[0])

# 1. failed breakout exited well (S2 nominated rule: no progress at minute 15 -> exit at open of bar 15)
t = tr.loc[130]
dec = bar_at(t, 15)  # close of bar 14 == open of bar 15
plot_trade(t, b, events=[("first knowable: close of bar 14 (<0R at 15 min)", dec, "C3")],
           policy_exits=[("failure rule", dec, open_at(dec) - 0.25, "C3")],
           out=os.path.join(out, "replay_1_failed_breakout_exited_well.png"),
           title="Replay 1 — failed breakout exited well: KX trade 130, 2025-09-17 LONG (rule exits −0.62R; original stop −1.95R)",
           window=(-8, 30))

# 2. winner cut too early (same rule, S2 costly false alarm)
t = tr.loc[306]
dec = bar_at(t, 15)
plot_trade(t, b, events=[("first knowable: close of bar 14 (<0R at 15 min)", dec, "C3")],
           policy_exits=[("failure rule", dec, open_at(dec) + 0.25, "C3")],
           out=os.path.join(out, "replay_2_winner_cut_too_early.png"),
           title="Replay 2 — winner cut too early: KX trade 306, 2026-03-19 SHORT (rule −1.15R; original target +2.99R at 203 min)",
           window=(-8, 210))

# 3. reversal that needed time (PX trade 186): breakout-style rule at min 10 and time exit at min 30 both lose
t = tr.loc[186]
d10, d30 = bar_at(t, 10), bar_at(t, 30)
d = 1 if t["direction"] == "LONG" else -1
plot_trade(t, b, events=[("no +0.3R by min 10 → breakout rule would exit", d10, "C3"),
                         ("30-min time exit", d30, "C1"),
                         ("+0.3R first touched (min 52)", bar_at(t, 52), "C4")],
           policy_exits=[("no-progress rule", d10, open_at(d10) - d * 0.25, "C3"), ("time exit 30", d30, open_at(d30) - d * 0.25, "C1")],
           out=os.path.join(out, "replay_3_reversal_needed_time.png"),
           title="Replay 3 — reversal that needed time: PX trade 186, 2025-11-10 (min −0.62R, +0.3R at 52 min, target +0.48R at 92 min)",
           window=(-8, 100))

# 4. pyramid where leg management mattered (S4 trade 265): add-only breakeven stop exits the add on a 1-tick retrace
t = tr.loc[265]
dec = pd.Timestamp("2026-02-04 10:28:00-05:00")  # close of 10:27 bar
add_exit = pd.Timestamp("2026-02-04 10:37:00-05:00")
plot_trade(t, b, events=[("add fills 10:23", pd.Timestamp(t["add_ts"]), "C1"),
                         ("first knowable: add ≥ +0.5R at 10:27 close", dec, "C3"),
                         ("add-only BE stop hit 10:37 (−$124 vs original)", add_exit, "C3")],
           policy_exits=[("add leg BE", add_exit, 23833.25, "C3")],
           out=os.path.join(out, "replay_4_pyramid_leg_management.png"),
           title="Replay 4 — pyramid: KX trade 265, 2026-02-04 SHORT, add-only breakeven cuts the add; both legs reach target at 11:05 (+3.16R)",
           window=(-8, 60))
print("charts written")
