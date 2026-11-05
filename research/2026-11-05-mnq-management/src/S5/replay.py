"""
S5 reference replay engine for MNQ post-entry management policies.

Everything here is instrument-agnostic 1-minute bar replay with an explicit,
parameterised fill model.  Nothing in this file knows about the synthetic
generator except the two named FillModel presets (`reference`, `generator`).

Main objects
------------
load_data(data_dir)                 -> Data   (bars ET-aligned, fills UTC->ET, signals, trades)
Entry                                an entry fill (price, time, contracts, direction, planned risk, bracket)
entries_from_trades(data)            Stage A entries (identical to the desk's actual fills)
entry_from_signal(sig, data, fm, bars_px) Stage B entry built from signals.csv + strategy rules
FillModel                            slippage / ordering / touch rule / commission parameters
Policy, rules (TimeExit, NoProgressExit, BreakevenStop, TrailingStop,
               StructuralTarget, StructuralStop, AddLegStop, KXAddRule)
OriginalBracket()                    the documented policy (bracket + KX add + 15:55 flat)
simulate_trade(entry, bars_trig, bars_px, policy, fm) -> TradeResult
run_stage_a(data, policies, fm)      paired table, identical entries
run_stage_b(data, policy, fm)        chronological portfolio replay from signals.csv
session_bootstrap(df, col, ...)      whole-session resampling CI

Timing conventions (1-minute bars, `ts` = bar OPEN time, ET)
-------------------------------------------------------------
* Bar i of a trade: i = 0 is the entry bar (entry fills at its open).
* A decision "at minute T" is taken at the open of bar T and may use only
  bars 0..T-1 (whose close time <= that open time).
* Market-order fills at a bar open use that bar's open +/- slippage.
* Stop fills: stop price +/- adverse slippage; if the bar OPENS beyond the
  stop, fill at the open +/- `slippage_ticks_gap` (reason STOP_GAP).
* Limit (target) fills: at the target, 0 slippage; if the bar opens beyond
  the target, fill at the open (price improvement) when limit_gap_fill='open'.
* Flat at the open of the `eod_flat_time` bar (15:55 ET), market order.
"""
from __future__ import annotations

import datetime as _dt
import math
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

ET = "America/New_York"
TICK = 0.25
POINT_VALUE = 2.0


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def round_tick(x, tick: float = TICK):
    """Round to the nearest tick (numpy half-to-even, as the generator does)."""
    return np.round(np.asarray(x, dtype=float) / tick) * tick


def md_table(df: pd.DataFrame, index: bool = True, floatfmt: str = ".2f") -> str:
    """Dependency-free markdown table (tabulate is not installed here)."""
    if isinstance(df, pd.Series):
        df = df.to_frame()
    d = df.reset_index() if index else df.copy()

    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if np.isnan(v) else format(v, floatfmt)
        if isinstance(v, pd.Timestamp):
            return v.strftime("%Y-%m-%d %H:%M")
        return "" if v is None else str(v)
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in d.itertuples(index=False):
        lines.append("| " + " | ".join(fmt(v) for v in row) + " |")
    return "\n".join(lines)


def to_et(s: pd.Series) -> pd.Series:
    """Parse any ISO-8601 column (with offset or trailing Z) to tz-aware ET."""
    return pd.to_datetime(s, utc=True).dt.tz_convert(ET)


def _parse_time(s: str) -> _dt.time:
    h, m = s.split(":")
    return _dt.time(int(h), int(m))


# ----------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------
@dataclass
class Data:
    bars: Dict[str, pd.DataFrame]          # instrument -> bars indexed by ET bar-open time
    session_bars: Dict[str, Dict[_dt.date, pd.DataFrame]]
    signals: pd.DataFrame
    trades: Optional[pd.DataFrame]
    fills: Optional[pd.DataFrame]
    costs: dict
    versions: pd.DataFrame
    target_mult: Dict[str, Optional[float]]  # strategy -> target multiple parsed from strategy_versions
    sessions: List[_dt.date]


def _load_bars(path: str) -> pd.DataFrame:
    b = pd.read_csv(path)
    b["t"] = to_et(b["ts"])
    b = b.set_index("t").sort_index()
    b["session"] = b.index.date
    return b[["open", "high", "low", "close", "volume", "session"]]


def parse_target_multiple(text: str) -> Optional[float]:
    """'entry +/- 2.5 * stop distance' -> 2.5 ; structural targets -> None."""
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*\*\s*stop", str(text))
    return float(m.group(1)) if m else None


def load_data(data_dir: str, require_trades: bool = False) -> Data:
    """Load the export.  Required: bars_MNQ_1min.csv, signals.csv,
    strategy_versions.csv, costs.csv.  Optional: bars_NQ_1min.csv, trades.csv, fills.csv."""
    import os

    p = lambda f: os.path.join(data_dir, f)
    bars = {"MNQ": _load_bars(p("bars_MNQ_1min.csv"))}
    if os.path.exists(p("bars_NQ_1min.csv")):
        bars["NQ"] = _load_bars(p("bars_NQ_1min.csv"))
    session_bars = {k: {s: g for s, g in v.groupby("session", sort=True)} for k, v in bars.items()}

    sg = pd.read_csv(p("signals.csv"))
    sg["signal_t"] = to_et(sg["signal_ts"])
    sg["sgn"] = np.where(sg["direction"].str.upper() == "LONG", 1, -1)
    sg["session"] = sg["signal_t"].dt.date
    sg["executed"] = sg["executed"].astype(str).str.lower().isin(["true", "1", "yes"])

    trades = fills = None
    if os.path.exists(p("trades.csv")):
        trades = pd.read_csv(p("trades.csv"))
        for c in ("entry_ts", "exit_ts", "add_ts"):
            trades[c.replace("_ts", "_t")] = to_et(trades[c])
        trades["sgn"] = np.where(trades["direction"].str.upper() == "LONG", 1, -1)
        trades["session"] = trades["entry_t"].dt.date
    elif require_trades:
        raise FileNotFoundError("trades.csv required")
    if os.path.exists(p("fills.csv")):
        fills = pd.read_csv(p("fills.csv"))
        fills["t"] = to_et(fills["ts_utc"])

    costs = pd.read_csv(p("costs.csv")).iloc[0].to_dict()
    versions = pd.read_csv(p("strategy_versions.csv"))
    tmult = {r.strategy: parse_target_multiple(r.target) for r in versions.itertuples()}
    # "same as v1" inheritance
    for r in versions.itertuples():
        if tmult[r.strategy] is None and "same as" in str(r.target):
            base = re.search(r"same as (\w+)", r.target).group(1)
            for k in tmult:
                if k.endswith("_" + base):
                    tmult[r.strategy] = tmult[k]
    return Data(bars, session_bars, sg, trades, fills, costs, versions, tmult, sorted(session_bars["MNQ"]))


# ----------------------------------------------------------------------------
# fill model
# ----------------------------------------------------------------------------
@dataclass
class FillModel:
    name: str = "reference"
    trigger_instrument: str = "MNQ"      # bars used to decide whether stop/target/add levels were reached
    price_instrument: str = "MNQ"        # bars used to price market orders (open +/- slippage)
    slippage_ticks_market: float = 1.0   # entries, adds, time/EOD/rule exits
    slippage_ticks_stop: float = 1.0     # stop fills: stop price +/- this
    slippage_ticks_limit: float = 0.0    # target fills
    slippage_ticks_gap: float = 1.0      # stop gapped through: open +/- this
    commission_per_side: float = 0.74    # per contract per fill, all-in
    same_bar_order: str = "worst"        # stop_first | target_first | worst | ohlc
    stop_trigger: str = "touch"          # touch (low<=stop) | penetrate (low<stop)
    target_fill: str = "penetrate"       # touch (high>=tgt) | penetrate (high>tgt)
    bracket_in_entry_bar: bool = True    # can the bracket fire in the remainder of the entry bar?
    limit_gap_fill: str = "open"         # open | limit  (bar opens beyond the target)
    skip_add_if_exit_same_bar: bool = False  # generator quirk: no add when the trade exits in the add bar
    eod_flat_time: _dt.time = _dt.time(15, 55)
    tick: float = TICK
    point_value: float = POINT_VALUE

    @classmethod
    def reference(cls, **kw) -> "FillModel":
        """Conservative model for pre-registered policies: MNQ bars, stop fires on
        a touch, limit needs penetration, bracket live in the entry bar, 1 tick slippage,
        gap = open+1 tick, same-bar stop+target resolved as the worse outcome."""
        return cls(name="reference", **kw)

    @classmethod
    def generator(cls, **kw) -> "FillModel":
        """The conventions the synthetic fills were found to follow (see reconcile.py)."""
        d = dict(name="generator", trigger_instrument="NQ", price_instrument="NQ",
                 stop_trigger="penetrate", target_fill="penetrate",
                 bracket_in_entry_bar=False, same_bar_order="stop_first",
                 limit_gap_fill="limit", skip_add_if_exit_same_bar=True)
        d.update(kw)
        return cls(**d)

    def mkt(self, open_px: float, side_sgn: int, ticks: Optional[float] = None) -> float:
        t = self.slippage_ticks_market if ticks is None else ticks
        return open_px + side_sgn * t * self.tick

    def commission(self, qty: int) -> float:
        return round(self.commission_per_side * qty, 2)


# ----------------------------------------------------------------------------
# entries / legs / fills / results
# ----------------------------------------------------------------------------
@dataclass
class Entry:
    trade_id: int
    signal_id: int
    session: _dt.date
    strategy: str
    family: str
    sgn: int                     # +1 long, -1 short
    entry_time: pd.Timestamp     # bar open, ET
    entry_px: float
    contracts: int
    planned_risk_usd: float      # 1R, fixed for the trade
    stop_px: float
    target_px: Optional[float]
    stop_dist_pts: float         # raw (unrounded) planned stop distance, used for R<->price and add trigger
    levels: dict = field(default_factory=dict)   # structural levels known at entry
    max_position: int = 4        # contracts this trade may hold in Stage A (position limit)

    @property
    def direction(self) -> str:
        return "LONG" if self.sgn == 1 else "SHORT"

    def R_to_px(self, R: float) -> float:
        """Price at which the INITIAL position shows R multiples of planned risk."""
        return self.entry_px + self.sgn * R * self.planned_risk_usd / (self.contracts * POINT_VALUE)

    def px_to_R(self, px: float) -> float:
        return (px - self.entry_px) * self.sgn * self.contracts * POINT_VALUE / self.planned_risk_usd


@dataclass
class Fill:
    trade_id: int
    leg_id: int
    time: pd.Timestamp
    side: str
    qty: int
    price: float
    order_type: str
    role: str                    # ENTRY / ADD / EXIT
    reason: Optional[str]
    commission: float


@dataclass
class Leg:
    leg_id: int
    qty: int
    entry_px: float
    entry_time: pd.Timestamp
    entry_bar: int
    stop_px: float
    target_px: Optional[float]
    stop_label: str = "STOP"     # exit reason used when this leg's stop fires
    is_open: bool = True
    exit_px: Optional[float] = None
    exit_time: Optional[pd.Timestamp] = None
    exit_bar: Optional[int] = None
    exit_reason: Optional[str] = None


@dataclass
class TradeResult:
    trade_id: int
    policy: str
    fill_model: str
    session: _dt.date
    strategy: str
    family: str
    direction: str
    entry_time: pd.Timestamp
    entry_px: float
    contracts_initial: int
    contracts_added: int
    add_time: Optional[pd.Timestamp]
    add_px: Optional[float]
    exit_time: pd.Timestamp
    exit_px: float               # qty-weighted average exit
    exit_reason: str
    gross_usd: float
    commission_usd: float
    net_usd: float
    net_R: float
    planned_risk_usd: float
    peak_open_usd: float
    peak_open_R: float
    trough_open_R: float
    peak_close_R: float
    minutes_held: int
    both_touched_bars: int       # bars (while open) whose range spanned both a live stop and a live target
    exit_bar_ambiguous: bool     # the exit bar itself touched both
    gapped_through_stop: bool
    fills: List[Fill] = field(default_factory=list)
    legs: List[Leg] = field(default_factory=list)

    def row(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k not in ("fills", "legs")}
        return d


# ----------------------------------------------------------------------------
# policy actions and rules
# ----------------------------------------------------------------------------
@dataclass
class ExitAction:
    legs: Sequence[int] | str = "all"
    reason: str = "RULE"


@dataclass
class SetStop:
    px: float
    legs: Sequence[int] | str = "all"
    label: str = "STOP"
    only_if_tighter: bool = True


@dataclass
class SetTarget:
    px: Optional[float]
    legs: Sequence[int] | str = "all"


@dataclass
class AddAction:
    qty: int = 1
    reason: str = "ADD"


class Rule:
    """Base class.  Rules see `state` (a TradeSim) and the bar index i at the
    open of bar i; they may only read bars[:i] (closed bars)."""

    def on_entry(self, state: "TradeSim") -> None:      # may edit leg[0].stop_px / target_px
        pass

    def on_add(self, state: "TradeSim", leg: Leg) -> None:  # may set the add leg's own bracket
        pass

    def on_bar_open(self, state: "TradeSim", i: int) -> List:
        return []


class TimeExit(Rule):
    """Exit all open legs at the open of bar `minute` (market order)."""

    def __init__(self, minute: int, reason: str = "TIME"):
        self.minute, self.reason = int(minute), reason

    def on_bar_open(self, state, i):
        return [ExitAction("all", self.reason)] if i == self.minute else []


class NoProgressExit(Rule):
    """At minute T, if progress (closed bars only) < min_R, exit at market.
    measure='close': last closed bar's close.  'extreme': best favourable extreme so far."""

    def __init__(self, minute: int, min_R: float, measure: str = "close", reason: str = "NOPROG"):
        self.minute, self.min_R, self.measure, self.reason = int(minute), float(min_R), measure, reason

    def on_bar_open(self, state, i):
        if i == self.minute and state.progress_R(i, self.measure) < self.min_R:
            return [ExitAction("all", self.reason)]
        return []


class BreakevenStop(Rule):
    """Once progress (closed bars) >= trigger_R, move the stop of `legs` to the
    leg's own entry price +/- offset_ticks (favourable offset positive)."""

    def __init__(self, trigger_R: float, offset_ticks: float = 0.0, legs: str = "all",
                 measure: str = "extreme", label: str = "STOP_BE"):
        self.trigger_R, self.offset_ticks, self.legs, self.measure, self.label = \
            float(trigger_R), float(offset_ticks), legs, measure, label
        self.armed = False

    def on_bar_open(self, state, i):
        if self.armed or i == 0:
            return []
        if state.progress_R(i, self.measure) >= self.trigger_R:
            self.armed = True
            out = []
            for leg in state.select_legs(self.legs):
                px = leg.entry_px + state.entry.sgn * self.offset_ticks * state.fm.tick
                out.append(SetStop(px, [leg.leg_id], self.label))
            return out
        return []


class TrailingStop(Rule):
    """Stop = best favourable closed-bar extreme -/+ trail distance, ratcheting only
    in the favourable direction, once progress >= activate_R.  Evaluated at bar opens
    only (a sub-minute trail cannot be represented on 1-minute bars)."""

    def __init__(self, trail_R: Optional[float] = None, trail_pts: Optional[float] = None,
                 activate_R: float = 0.0, legs: str = "all", label: str = "STOP_TRAIL"):
        assert (trail_R is None) != (trail_pts is None), "give trail_R or trail_pts"
        self.trail_R, self.trail_pts, self.activate_R, self.legs, self.label = trail_R, trail_pts, activate_R, legs, label

    def on_bar_open(self, state, i):
        if i == 0 or state.progress_R(i, "extreme") < self.activate_R:
            return []
        dist = self.trail_pts if self.trail_pts is not None else self.trail_R * state.entry.stop_dist_pts
        px = state.fav_extreme_closed(i) - state.entry.sgn * dist
        return [SetStop(px, self.legs, self.label, only_if_tighter=True)]


class StructuralTarget(Rule):
    """Replace the target with a level known at entry (entry.levels[key]); None removes the target."""

    def __init__(self, key: Optional[str]):
        self.key = key

    def on_entry(self, state):
        px = None if self.key is None else state.entry.levels.get(self.key)
        for leg in state.legs:
            leg.target_px = None if px is None or (isinstance(px, float) and math.isnan(px)) else float(round_tick(px))


class StructuralStop(Rule):
    """Use a structural level as the initial stop, only if it is on the adverse side."""

    def __init__(self, key: str, label: str = "STOP"):
        self.key, self.label = key, label

    def on_entry(self, state):
        px = state.entry.levels.get(self.key)
        if px is None or (isinstance(px, float) and math.isnan(px)):
            return
        px = float(round_tick(px))
        if (px - state.entry.entry_px) * state.entry.sgn < 0:
            for leg in state.legs:
                leg.stop_px, leg.stop_label = px, self.label


class AddLegStop(Rule):
    """Give the add leg its own stop instead of sharing the original one.
    mode: 'own_distance' (add_px -/+ rounded stop distance), 'breakeven' (add_px),
    'fixed_pts' (add_px -/+ pts)."""

    def __init__(self, mode: str = "own_distance", pts: Optional[float] = None, label: str = "STOP_ADD"):
        self.mode, self.pts, self.label = mode, pts, label

    def on_add(self, state, leg):
        e = state.entry
        if self.mode == "breakeven":
            leg.stop_px = leg.entry_px
        elif self.mode == "own_distance":
            leg.stop_px = leg.entry_px - e.sgn * float(round_tick(e.stop_dist_pts))
        elif self.mode == "fixed_pts":
            leg.stop_px = leg.entry_px - e.sgn * float(round_tick(self.pts))
        leg.stop_px = float(round_tick(leg.stop_px))
        leg.stop_label = self.label


class KXAddRule(Rule):
    """Documented pyramid: add `qty` at the next open after a closed bar (bars 1..window_min
    after entry) whose favourable extreme reaches entry +/- trigger_R * stop distance,
    if that open is before `latest_time` and position room allows.  One attempt only."""

    def __init__(self, trigger_R: float = 1.0, window_min: int = 20, latest_time: _dt.time = _dt.time(12, 0),
                 qty: int = 1, families: Sequence[str] = ("KX",)):
        self.trigger_R, self.window_min, self.latest_time, self.qty, self.families = \
            trigger_R, window_min, latest_time, qty, tuple(families)

    def on_bar_open(self, state, i):
        e = state.entry
        if e.family not in self.families or state.add_attempted:
            return []
        j = i - 1
        if j < 1 or j > self.window_min:
            return []
        lvl = e.entry_px + e.sgn * self.trigger_R * e.stop_dist_pts
        if state.fav_extreme(j) * e.sgn >= lvl * e.sgn:
            state.add_attempted = True
            if state.bars.index[i].time() < self.latest_time:
                return [AddAction(self.qty)]
        return []


@dataclass
class Policy:
    name: str
    rules: List[Rule] = field(default_factory=list)
    add_rule: Optional[Rule] = None
    description: str = ""

    def fresh(self) -> "Policy":
        """Rules hold per-trade state (e.g. breakeven armed) -> copy per trade."""
        import copy
        return copy.deepcopy(self)

    @property
    def all_rules(self) -> List[Rule]:
        return ([self.add_rule] if self.add_rule else []) + list(self.rules)


def OriginalBracket(name: str = "original", add: bool = True, **add_kw) -> Policy:
    """Documented policy: OCO bracket from entry, KX add sharing the bracket, 15:55 flat."""
    return Policy(name, [], KXAddRule(**add_kw) if add else None,
                  "OCO stop+target from entry; KX add 1 at next open after +1.0x stop dist within 20 min, before 12:00; flat 15:55")


# ----------------------------------------------------------------------------
# simulator
# ----------------------------------------------------------------------------
class TradeSim:
    """Bar-by-bar simulation of ONE trade under ONE policy.

    bars_trig / bars_px: session bars from the ENTRY bar onward (index 0 = entry bar),
    same index.  Call run() for Stage A, or step_open / step_intrabar / step_close
    from a portfolio loop (Stage B)."""

    def __init__(self, entry: Entry, bars_trig: pd.DataFrame, bars_px: pd.DataFrame,
                 policy: Policy, fm: FillModel):
        self.entry, self.policy, self.fm = entry, policy.fresh(), fm
        self.bars, self.bars_px = bars_trig, bars_px
        self.o, self.h, self.l, self.c = (bars_trig[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.po = bars_px["open"].to_numpy(float)
        self.fills: List[Fill] = []
        self.legs: List[Leg] = [Leg(1, entry.contracts, entry.entry_px, entry.entry_time, 0,
                                    float(round_tick(entry.stop_px)),
                                    None if entry.target_px is None or (isinstance(entry.target_px, float) and math.isnan(entry.target_px))
                                    else float(round_tick(entry.target_px)))]
        self.add_attempted = False
        self.done = False
        self.both_touched_bars = 0
        self.exit_bar_ambiguous = False
        self.gapped = False
        self.peak_open_usd = -math.inf
        self.trough_open_usd = math.inf
        self.peak_close_usd = -math.inf
        self.last_bar = -1
        self.eod_idx = next((k for k, t in enumerate(bars_trig.index) if t.time() >= fm.eod_flat_time), len(bars_trig))
        side = "BUY" if entry.sgn == 1 else "SELL"
        self.fills.append(Fill(entry.trade_id, 1, entry.entry_time, side, entry.contracts, entry.entry_px,
                               "MKT", "ENTRY", None, fm.commission(entry.contracts)))
        for r in self.policy.all_rules:
            r.on_entry(self)

    # ---- state accessors used by rules (closed bars only) -------------------
    def open_legs(self) -> List[Leg]:
        return [lg for lg in self.legs if lg.is_open]

    def open_contracts(self) -> int:
        return sum(lg.qty for lg in self.open_legs())

    def select_legs(self, which) -> List[Leg]:
        if which == "all":
            return self.open_legs()
        if which == "initial":
            return [lg for lg in self.open_legs() if lg.leg_id == 1]
        if which == "add":
            return [lg for lg in self.open_legs() if lg.leg_id > 1]
        return [lg for lg in self.open_legs() if lg.leg_id in which]

    def fav_extreme(self, j: int) -> float:
        return self.h[j] if self.entry.sgn == 1 else self.l[j]

    def adv_extreme(self, j: int) -> float:
        return self.l[j] if self.entry.sgn == 1 else self.h[j]

    def fav_extreme_closed(self, i: int) -> float:
        """Best favourable extreme over closed bars 0..i-1."""
        return self.h[:i].max() if self.entry.sgn == 1 else self.l[:i].min()

    def progress_R(self, i: int, measure: str = "close") -> float:
        """R-multiple of the INITIAL position from closed bars only (bars 0..i-1)."""
        if i <= 0:
            return 0.0
        if measure == "close":
            px = self.c[i - 1]
        elif measure == "extreme":
            px = self.fav_extreme_closed(i)
        elif measure == "adverse":
            px = self.l[:i].min() if self.entry.sgn == 1 else self.h[:i].max()
        else:
            raise ValueError(measure)
        return self.entry.px_to_R(px)

    # ---- fills ----------------------------------------------------------------
    def _exit_leg(self, leg: Leg, i: int, px: float, otype: str, reason: str):
        e = self.entry
        px = float(round_tick(px))
        leg.is_open, leg.exit_px, leg.exit_time, leg.exit_bar, leg.exit_reason = False, px, self.bars.index[i], i, reason
        side = "SELL" if e.sgn == 1 else "BUY"
        self.fills.append(Fill(e.trade_id, leg.leg_id, self.bars.index[i], side, leg.qty, px, otype, "EXIT",
                               reason, self.fm.commission(leg.qty)))

    def _exit_all_mkt(self, i: int, reason: str, legs="all"):
        e, fm = self.entry, self.fm
        px = fm.mkt(self.po[i], -e.sgn)
        for leg in list(self.select_legs(legs)):
            self._exit_leg(leg, i, px, "MKT", reason)

    def _add(self, i: int, qty: int, reason: str):
        e, fm = self.entry, self.fm
        px = float(round_tick(fm.mkt(self.po[i], e.sgn)))
        base = self.legs[0]
        leg = Leg(len(self.legs) + 1, qty, px, self.bars.index[i], i, base.stop_px, base.target_px, base.stop_label)
        self.legs.append(leg)
        side = "BUY" if e.sgn == 1 else "SELL"
        self.fills.append(Fill(e.trade_id, leg.leg_id, self.bars.index[i], side, qty, px, "MKT", "ADD", None, fm.commission(qty)))
        for r in self.policy.all_rules:
            r.on_add(self, leg)

    def _would_exit_in_bar(self, i: int) -> bool:
        """Look-ahead used only by the generator quirk flag."""
        return any(self._bar_hits(leg, i)[:2] != (False, False) for leg in self.open_legs())

    # ---- stepping ------------------------------------------------------------
    def step_open(self, i: int, room: Optional[int] = None) -> List[Fill]:
        """Bar-open phase: EOD flat, policy decisions, adds.  `room` = contracts that may be added."""
        if self.done:
            return []
        n0 = len(self.fills)
        e, fm = self.entry, self.fm
        if i >= self.eod_idx or i >= len(self.bars):
            self._exit_all_mkt(min(i, len(self.bars) - 1), "TIME_EOD")
            self._finish(min(i, len(self.bars) - 1))
            return self.fills[n0:]
        actions = []
        for r in self.policy.all_rules:
            actions += r.on_bar_open(self, i)
        exits = [a for a in actions if isinstance(a, ExitAction)]
        for a in exits:
            self._exit_all_mkt(i, a.reason, a.legs)
        if not self.open_legs():
            self._finish(i)
            return self.fills[n0:]
        for a in actions:
            if isinstance(a, SetStop):
                for leg in self.select_legs(a.legs):
                    px = float(round_tick(a.px))
                    if (not a.only_if_tighter) or (px - leg.stop_px) * e.sgn > 0:
                        leg.stop_px, leg.stop_label = px, a.label
            elif isinstance(a, SetTarget):
                for leg in self.select_legs(a.legs):
                    leg.target_px = None if a.px is None else float(round_tick(a.px))
            elif isinstance(a, AddAction):
                room_here = e.max_position - self.open_contracts() if room is None else room
                if a.qty <= room_here and not (fm.skip_add_if_exit_same_bar and self._would_exit_in_bar(i)):
                    self._add(i, a.qty, a.reason)
        return self.fills[n0:]

    def _bar_hits(self, leg: Leg, i: int):
        """(stop_hit, tgt_hit, gap_stop, gap_tgt) for leg in bar i on the trigger bars."""
        s, fm = self.entry.sgn, self.fm
        o, h, l = self.o[i], self.h[i], self.l[i]
        adv = l if s == 1 else h        # adverse extreme
        fav = h if s == 1 else l
        if fm.stop_trigger == "touch":
            stop_hit = (adv - leg.stop_px) * s <= 0
            gap_stop = (o - leg.stop_px) * s <= 0
        else:
            stop_hit = (adv - leg.stop_px) * s < 0
            gap_stop = (o - leg.stop_px) * s < 0
        if leg.target_px is None:
            tgt_hit = gap_tgt = False
        elif fm.target_fill == "touch":
            tgt_hit = (fav - leg.target_px) * s >= 0
            gap_tgt = (o - leg.target_px) * s >= 0
        else:
            tgt_hit = (fav - leg.target_px) * s > 0
            gap_tgt = (o - leg.target_px) * s > 0
        return stop_hit, tgt_hit, gap_stop, gap_tgt

    def step_intrabar(self, i: int) -> List[Fill]:
        """Intrabar phase: gaps, stops, targets for every open leg."""
        if self.done:
            return []
        n0 = len(self.fills)
        e, fm = self.entry, self.fm
        if i == 0 and not fm.bracket_in_entry_bar:
            return []
        if i >= self.eod_idx:
            return []
        for leg in list(self.open_legs()):
            stop_hit, tgt_hit, gap_stop, gap_tgt = self._bar_hits(leg, i)
            stop_px = leg.stop_px - e.sgn * fm.slippage_ticks_stop * fm.tick
            if gap_stop:
                self.gapped = True
                self._exit_leg(leg, i, self.po[i] - e.sgn * fm.slippage_ticks_gap * fm.tick, "STP", "STOP_GAP")
            elif gap_tgt:
                px = self.po[i] if fm.limit_gap_fill == "open" else leg.target_px
                self._exit_leg(leg, i, px - e.sgn * fm.slippage_ticks_limit * fm.tick, "LMT", "TARGET")
            elif stop_hit and tgt_hit:
                self.both_touched_bars += 1
                self.exit_bar_ambiguous = True
                tgt_px = leg.target_px - e.sgn * fm.slippage_ticks_limit * fm.tick
                order = fm.same_bar_order
                if order == "ohlc":   # close above open (long): assume O-L-H-C, stop first
                    order = "stop_first" if (self.c[i] - self.o[i]) * e.sgn >= 0 else "target_first"
                if order == "stop_first" or order == "worst":
                    self._exit_leg(leg, i, stop_px, "STP", leg.stop_label)
                elif order == "target_first":
                    self._exit_leg(leg, i, tgt_px, "LMT", "TARGET")
                else:
                    raise ValueError(fm.same_bar_order)
            elif stop_hit:
                self._exit_leg(leg, i, stop_px, "STP", leg.stop_label)
            elif tgt_hit:
                self._exit_leg(leg, i, leg.target_px - e.sgn * fm.slippage_ticks_limit * fm.tick, "LMT", "TARGET")
        if not self.open_legs():
            self._finish(i)
        return self.fills[n0:]

    def step_close(self, i: int) -> None:
        """Bar-close bookkeeping: open-profit excursions (legs open at the start of bar i)."""
        if self.last_bar >= i:
            return
        self.last_bar = i
        e = self.entry
        pk = tr = ck = 0.0
        for leg in self.legs:
            if leg.entry_bar > i or (not leg.is_open and leg.exit_bar < i):
                continue
            if not leg.is_open and leg.exit_bar == i:
                v = (leg.exit_px - leg.entry_px) * e.sgn * leg.qty * POINT_VALUE
                pk += v; tr += v; ck += v
            else:
                pk += (self.fav_extreme(i) - leg.entry_px) * e.sgn * leg.qty * POINT_VALUE
                tr += (self.adv_extreme(i) - leg.entry_px) * e.sgn * leg.qty * POINT_VALUE
                ck += (self.c[i] - leg.entry_px) * e.sgn * leg.qty * POINT_VALUE
        self.peak_open_usd = max(self.peak_open_usd, pk)
        self.trough_open_usd = min(self.trough_open_usd, tr)
        self.peak_close_usd = max(self.peak_close_usd, ck)

    def _finish(self, i: int):
        self.done = True
        self.step_close(i)

    def run(self) -> TradeResult:
        for i in range(len(self.bars) + 1):
            self.step_open(i)
            if self.done:
                break
            self.step_intrabar(i)
            self.step_close(i)
            if self.done:
                break
        return self.result()

    def result(self) -> TradeResult:
        e = self.entry
        assert self.done, "trade still open"
        gross = sum((lg.exit_px - lg.entry_px) * e.sgn * lg.qty * POINT_VALUE for lg in self.legs)
        comm = sum(f.commission for f in self.fills)
        net = gross - comm
        exit_time = max(lg.exit_time for lg in self.legs)
        last = [lg for lg in self.legs if lg.exit_time == exit_time]
        q = sum(lg.qty for lg in self.legs)
        exit_px = sum(lg.exit_px * lg.qty for lg in self.legs) / q
        reasons = sorted({lg.exit_reason for lg in last})
        adds = [lg for lg in self.legs if lg.leg_id > 1]
        pk = max(self.peak_open_usd, 0.0) if self.peak_open_usd == -math.inf else self.peak_open_usd
        return TradeResult(
            e.trade_id, self.policy.name, self.fm.name, e.session, e.strategy, e.family, e.direction,
            e.entry_time, e.entry_px, e.contracts, sum(a.qty for a in adds),
            adds[0].entry_time if adds else None, adds[0].entry_px if adds else None,
            exit_time, float(round_tick(exit_px)) if q == 1 else exit_px, "+".join(reasons),
            round(gross, 2), round(comm, 2), round(net, 2), net / e.planned_risk_usd, e.planned_risk_usd,
            round(pk, 2), pk / e.planned_risk_usd, self.trough_open_usd / e.planned_risk_usd,
            self.peak_close_usd / e.planned_risk_usd,
            int((exit_time - e.entry_time).total_seconds() // 60),
            self.both_touched_bars, self.exit_bar_ambiguous, self.gapped, self.fills, self.legs)


def trade_bars(data: Data, instrument: str, session: _dt.date, entry_time: pd.Timestamp) -> pd.DataFrame:
    b = data.session_bars[instrument][session]
    return b.loc[entry_time:]


def simulate_trade(entry: Entry, data: Data, policy: Policy, fm: FillModel) -> TradeResult:
    bt = trade_bars(data, fm.trigger_instrument, entry.session, entry.entry_time)
    bp = bt if fm.price_instrument == fm.trigger_instrument else trade_bars(data, fm.price_instrument, entry.session, entry.entry_time)
    if len(bt) == 0 or bt.index[0] != entry.entry_time:
        raise ValueError(f"trade {entry.trade_id}: entry time {entry.entry_time} is not a bar open")
    return TradeSim(entry, bt, bp, policy, fm).run()


# ----------------------------------------------------------------------------
# entries
# ----------------------------------------------------------------------------
def _levels_from_signal(sig) -> dict:
    lv = {"ref_level": sig.ref_level, "ref_width": sig.ref_width}
    if sig.family == "PX":
        lv["or_mid"] = sig.planned_target_px          # structural target known at entry
        lv["structural_stop"] = sig.planned_stop_px   # session extreme +/- 0.1 OR width (pre-clip)
    else:  # KX: ref_level is the OR boundary broken; mid = boundary -/+ half width (derived, see README)
        lv["or_mid"] = sig.ref_level - sig.sgn * sig.ref_width / 2.0
        lv["or_boundary"] = sig.ref_level
    return lv


def entries_from_trades(data: Data, trade_ids: Optional[Sequence[int]] = None) -> List[Entry]:
    """Stage A entries: the desk's actual entry fills, initial size and documented bracket."""
    tr = data.trades
    sg = data.signals.set_index("signal_id")
    if trade_ids is not None:
        tr = tr[tr.trade_id.isin(trade_ids)]
    out = []
    for r in tr.itertuples():
        s = sg.loc[r.signal_id]
        lv = _levels_from_signal(pd.Series({**s.to_dict(), "sgn": r.sgn, "family": r.family}))
        out.append(Entry(int(r.trade_id), int(r.signal_id), r.session, r.strategy, r.family, int(r.sgn),
                         r.entry_t, float(r.entry_px), int(r.initial_contracts), float(r.planned_risk_usd),
                         float(r.initial_stop_px), float(r.initial_target_px), float(s.planned_stop_dist_pts), lv,
                         int(data.costs.get("position_limit_contracts", 4))))
    return out


def entry_from_signal(sig, data: Data, fm: FillModel, entry_time: pd.Timestamp, open_px: float,
                      trade_id: int) -> Entry:
    """Stage B entry from a signal row: fill = price-instrument open +/- market slippage; bracket from
    strategy_versions (target multiple) and the signal's planned stop distance / structural levels."""
    sgn = int(sig.sgn)
    entry_px = float(round_tick(fm.mkt(open_px, sgn)))
    dist = float(sig.planned_stop_dist_pts)
    stop_px = entry_px - sgn * float(round_tick(dist))
    if sig.family == "KX":
        mult = data.target_mult.get(sig.strategy)
        if mult is None:
            mult = float(sig.planned_target_mult_R)
        target_px = entry_px + sgn * float(round_tick(mult * dist))
    else:
        target_px = float(sig.planned_target_px)
    lv = _levels_from_signal(sig)
    return Entry(trade_id, int(sig.signal_id), sig.session, sig.strategy, sig.family, sgn, entry_time, entry_px,
                 int(sig.planned_contracts), float(sig.planned_risk_usd), stop_px, target_px, dist, lv,
                 int(data.costs.get("position_limit_contracts", 4)))


# ----------------------------------------------------------------------------
# Stage A
# ----------------------------------------------------------------------------
def run_stage_a(data: Data, policies: Sequence[Policy], fm: FillModel,
                entries: Optional[Sequence[Entry]] = None):
    """Replay identical entries under each policy.  Returns (long_df, paired_df).
    paired_df: one row per trade with net_usd / net_R / exit_reason / minutes per policy, the
    paired difference vs the first policy, and an overlap flag (policy still open at the next
    executed entry of the same session)."""
    entries = entries_from_trades(data) if entries is None else entries
    rows = []
    for pol in policies:
        for e in entries:
            rows.append(simulate_trade(e, data, pol, fm).row())
    long = pd.DataFrame(rows)
    base = policies[0].name
    # next entry in the same session (from the executed trades)
    tr = data.trades.sort_values("entry_t")
    nxt = {}
    for s, g in tr.groupby("session"):
        ids, ts = g.trade_id.tolist(), g.entry_t.tolist()
        for k in range(len(ids)):
            nxt[ids[k]] = ts[k + 1] if k + 1 < len(ids) else pd.NaT
    long["next_entry_time"] = long.trade_id.map(nxt)
    long["overlaps_next_entry"] = long.next_entry_time.notna() & (long.exit_time > long.next_entry_time)
    paired = long.pivot(index="trade_id", columns="policy",
                        values=["net_usd", "net_R", "exit_reason", "minutes_held", "peak_open_R",
                                "both_touched_bars", "overlaps_next_entry"])
    paired.columns = [f"{a}__{b}" for a, b in paired.columns]
    meta = long[long.policy == base].set_index("trade_id")[["session", "strategy", "family", "direction", "planned_risk_usd"]]
    paired = meta.join(paired)
    for pol in policies[1:]:
        paired[f"dnet_usd__{pol.name}"] = paired[f"net_usd__{pol.name}"] - paired[f"net_usd__{base}"]
        paired[f"dnet_R__{pol.name}"] = paired[f"net_R__{pol.name}"] - paired[f"net_R__{base}"]
    return long, paired


def session_bootstrap(df: pd.DataFrame, value_col: str, session_col: str = "session", n_boot: int = 2000,
                      seed: int = 0, agg: str = "mean") -> dict:
    """Resample whole sessions with replacement; statistic = mean (or sum) over the trades of
    the resampled sessions.  Returns point estimate, 2.5/97.5 percentiles, n_trades, n_sessions."""
    rng = np.random.default_rng(seed)
    groups = [g[value_col].to_numpy(float) for _, g in df.groupby(session_col)]
    S = len(groups)
    f = np.mean if agg == "mean" else np.sum
    point = f(np.concatenate(groups))
    stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, S, S)
        stats[b] = f(np.concatenate([groups[k] for k in idx]))
    return dict(point=float(point), lo=float(np.percentile(stats, 2.5)), hi=float(np.percentile(stats, 97.5)),
                n_trades=int(len(df)), n_sessions=int(S), frac_boot_le_0=float((stats <= 0).mean()))


# ----------------------------------------------------------------------------
# Stage B
# ----------------------------------------------------------------------------
def run_stage_b(data: Data, policy: Policy, fm: FillModel, position_limit: Optional[int] = None,
                exit_frees_same_bar: bool = False, start_trade_id: int = 1):
    """Chronological portfolio replay from signals.csv (rejected signals included).
    Per bar: (1) open-phase for open trades (rule exits, adds subject to room), (2) new signals at
    this bar open executed if planned_contracts <= room (no partial sizing), (3) intrabar
    stop/target for all open trades.  With exit_frees_same_bar=True step (3) for trades that were
    already open runs before (2) — this is the (optimistic) convention found in the synthetic export.
    Returns (results_df, signal_log_df)."""
    limit = int(data.costs.get("position_limit_contracts", 4)) if position_limit is None else position_limit
    results, log = [], []
    tid = start_trade_id
    for session in data.sessions:
        sb = data.session_bars[fm.trigger_instrument][session]
        pb = sb if fm.price_instrument == fm.trigger_instrument else data.session_bars[fm.price_instrument][session]
        sigs = data.signals[data.signals.session == session].sort_values(["signal_t", "signal_id"])
        by_t = {t: g for t, g in sigs.groupby("signal_t")}
        open_sims: List[tuple] = []   # (sim, entry_bar_index)
        for k, t in enumerate(sb.index):
            def open_ctr():
                return sum(s.open_contracts() for s, _ in open_sims if not s.done)
            for s, k0 in open_sims:
                s.step_open(k - k0, room=limit - open_ctr())
            if exit_frees_same_bar:
                for s, k0 in open_sims:
                    s.step_intrabar(k - k0)
            for sig in by_t.get(t, pd.DataFrame()).itertuples():
                room = limit - open_ctr()
                if int(sig.planned_contracts) <= room and k < len(sb) and t.time() < fm.eod_flat_time:
                    e = entry_from_signal(sig, data, fm, t, float(pb["open"].iloc[k]), tid)
                    sim = TradeSim(e, sb.iloc[k:], pb.iloc[k:], policy, fm)
                    sim.step_open(0, room=limit - open_ctr() - e.contracts)
                    open_sims.append((sim, k))
                    log.append(dict(signal_id=sig.signal_id, session=session, signal_t=t, strategy=sig.strategy,
                                    planned_contracts=sig.planned_contracts, executed=True, trade_id=tid,
                                    reject_reason=None, room=room, executed_in_export=sig.executed))
                    tid += 1
                else:
                    log.append(dict(signal_id=sig.signal_id, session=session, signal_t=t, strategy=sig.strategy,
                                    planned_contracts=sig.planned_contracts, executed=False, trade_id=None,
                                    reject_reason="position_limit", room=room, executed_in_export=sig.executed))
            for s, k0 in open_sims:
                s.step_intrabar(k - k0)
                s.step_close(k - k0)
            finished = [s for s, _ in open_sims if s.done]
            for s in finished:
                results.append(s.result().row())
            open_sims = [(s, k0) for s, k0 in open_sims if not s.done]
        for s, k0 in open_sims:       # should be empty: EOD flat
            s.step_open(len(sb))
            results.append(s.result().row())
    res = pd.DataFrame(results)
    lg = pd.DataFrame(log)
    return res, lg


def summarize(df: pd.DataFrame, by: Optional[str] = None) -> pd.DataFrame:
    """Trades, sessions, net $ (sum, mean), net R (mean), win rate, max drawdown of cumulative net $."""
    def one(g):
        cum = g.sort_values("entry_time").net_usd.cumsum()
        dd = (cum - cum.cummax()).min()
        return pd.Series(dict(trades=len(g), sessions=g.session.nunique(), net_usd_sum=round(g.net_usd.sum(), 2),
                              net_usd_mean=round(g.net_usd.mean(), 2), net_R_mean=round(g.net_R.mean(), 3),
                              win_rate=round((g.net_usd > 0).mean(), 3), max_dd_usd=round(dd, 2),
                              avg_minutes=round(g.minutes_held.mean(), 1)))
    if by is None:
        return one(df).to_frame().T
    return df.groupby(by).apply(one, include_groups=False)
