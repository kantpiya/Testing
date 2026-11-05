"""
B5 prop-account path simulator (SYNTHETIC).
Two policies with IDENTICAL net P&L over 40 trades, different ordering/variance,
run over 1000 shuffled paths under three drawdown types and three data granularities.

All account parameters below are LABELED HYPOTHETICAL unless the report marks them
EXTERNALLY SUPPORTED.
"""
import random, statistics, json, sys
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------- account-state model
@dataclass
class Rule:
    firm: str
    product: str
    stage: str            # evaluation | funded
    name: str             # drawdown_type, max_drawdown, daily_loss_limit, profit_target,
                          # consistency_max_day_share, min_trading_days, payout_cadence, payout_buffer
    parameter: object
    effective_date: str
    source_url: str
    label: str            # HYPOTHETICAL | EXTERNALLY SUPPORTED

@dataclass
class Account:
    rules: list
    def p(self, name, default=None):
        for r in self.rules:
            if r.name == name:
                return r.parameter
        return default

def hyp(name, param):
    return Rule("HYPOTHETICAL_FIRM", "HYPOTHETICAL_50K", "evaluation", name, param,
                "n/a", "n/a", "HYPOTHETICAL")

BASE = [
    hyp("start_balance", 50_000),
    hyp("max_drawdown", 1_000),          # trailing or static amount
    hyp("daily_loss_limit", 600),        # realized (+unrealized if intraday data) per day
    hyp("profit_target", 800),           # evaluation pass / payout request threshold
    hyp("consistency_max_day_share", 0.50),  # best day <= 50% of total profit at request
    hyp("min_trading_days", 5),
    hyp("payout_buffer", 100),           # balance must exceed start + buffer at request (funded)
    hyp("trades_per_day", 4),
]

# ---------------------------------------------------------------- synthetic trades
def make_policy(kind, rng):
    """Returns list of trades: dict(pnl, mfe, mae). Net P&L identical across policies (+1000)."""
    if kind == "X_many_small_wins_rare_big_loss":
        pnls = [100] * 34 + [-400] * 6         # 34*100 - 6*400 = +1000
    elif kind == "Y_rare_big_wins_many_small_losses":
        pnls = [400] * 10 + [-100] * 30        # 10*400 - 30*100 = +1000
    else:
        raise ValueError(kind)
    trades = []
    for p in pnls:
        if p > 0:
            mfe = p + rng.uniform(0, 100)      # ran further than exit before closing
            mae = -rng.uniform(0, 150)         # adverse excursion before the win
        else:
            mfe = rng.uniform(0, 150)          # was in profit before stop
            mae = p - rng.uniform(0, 100)      # slipped beyond final loss then partially recovered
        trades.append({"pnl": p, "mfe": mfe, "mae": mae})
    return trades

# ---------------------------------------------------------------- path simulation
def simulate(trades, acct, dd_type, granularity):
    """
    dd_type: 'eod_trailing' | 'intraday_trailing_unrealized' | 'static'
    granularity: 'eod_close' | 'per_trade_realized' | 'per_trade_mfe_mae'
    Returns dict(breached, breach_day, breach_rule, eligible_day).
    """
    start = acct.p("start_balance"); dd = acct.p("max_drawdown")
    dll = acct.p("daily_loss_limit"); target = acct.p("profit_target")
    cons = acct.p("consistency_max_day_share"); min_days = acct.p("min_trading_days")
    buf = acct.p("payout_buffer"); tpd = acct.p("trades_per_day")

    bal = start
    peak = start                      # high-water mark used by the trailing rule
    threshold = start - dd            # static threshold; trailing rules move it up
    day_pnls = []
    eligible_day = None
    days = [trades[i:i + tpd] for i in range(0, len(trades), tpd)]

    for d, day in enumerate(days, start=1):
        day_start_bal = bal
        day_pnl = 0.0
        if granularity == "eod_close":
            # only the day's close is visible
            day_pnl = sum(t["pnl"] for t in day)
            bal += day_pnl
            if dd_type == "intraday_trailing_unrealized":
                peak = max(peak, bal)     # WRONG by construction: cannot see intraday peaks
            if bal < threshold or day_pnl < -dll:
                return dict(breached=True, breach_day=d,
                            breach_rule="dd" if bal < threshold else "dll", eligible_day=None)
        else:
            for t in day:
                if granularity == "per_trade_mfe_mae" and dd_type == "intraday_trailing_unrealized":
                    # unrealized equity path: peak may be set by MFE, breach by MAE
                    peak = max(peak, bal + t["mfe"])
                    threshold = max(threshold, peak - dd)
                    if bal + t["mae"] < threshold:
                        return dict(breached=True, breach_day=d, breach_rule="dd_unrealized", eligible_day=None)
                    if day_pnl + t["mae"] < -dll:
                        return dict(breached=True, breach_day=d, breach_rule="dll_unrealized", eligible_day=None)
                bal += t["pnl"]; day_pnl += t["pnl"]
                if dd_type == "intraday_trailing_unrealized":
                    peak = max(peak, bal)                 # realized high also counts
                    threshold = max(threshold, peak - dd)
                if bal < threshold:
                    return dict(breached=True, breach_day=d, breach_rule="dd", eligible_day=None)
                if day_pnl < -dll:
                    return dict(breached=True, breach_day=d, breach_rule="dll", eligible_day=None)
        # end of day
        day_pnls.append(day_pnl)
        if dd_type == "eod_trailing":
            peak = max(peak, bal)
            threshold = max(threshold, peak - dd)
        # payout / pass eligibility check at EOD
        profit = bal - start
        if eligible_day is None and d >= min_days and profit >= target and profit >= buf:
            best = max(day_pnls)
            if profit > 0 and best / profit <= cons:
                eligible_day = d
    return dict(breached=False, breach_day=None, breach_rule=None, eligible_day=eligible_day)

def run(n_paths=1000, seed=7):
    rng = random.Random(seed)
    acct = Account(BASE)
    out = {}
    for pol in ["X_many_small_wins_rare_big_loss", "Y_rare_big_wins_many_small_losses"]:
        base_trades = make_policy(pol, rng)
        assert sum(t["pnl"] for t in base_trades) == 1000
        for dd_type in ["static", "eod_trailing", "intraday_trailing_unrealized"]:
            for gran in ["eod_close", "per_trade_realized", "per_trade_mfe_mae"]:
                if gran == "per_trade_mfe_mae" and dd_type != "intraday_trailing_unrealized":
                    continue   # MFE/MAE only matter for the unrealized rule
                res = []
                r2 = random.Random(seed + 1)
                for _ in range(n_paths):
                    tr = base_trades[:]
                    r2.shuffle(tr)
                    res.append(simulate(tr, acct, dd_type, gran))
                nb = sum(r["breached"] for r in res)
                elig = [r["eligible_day"] for r in res if r["eligible_day"] is not None]
                rules = {}
                for r in res:
                    if r["breached"]:
                        rules[r["breach_rule"]] = rules.get(r["breach_rule"], 0) + 1
                out[(pol, dd_type, gran)] = dict(
                    breach_prob=nb / n_paths,
                    breach_rules=rules,
                    p_eligible=len(elig) / n_paths,
                    median_days_to_eligible=(statistics.median(elig) if elig else None),
                    p_eligible_by_day10=len(elig) / n_paths,
                )
    return out

if __name__ == "__main__":
    out = run()
    print(f"{'policy':<36}{'dd_type':<30}{'granularity':<20}{'P(breach)':>10}{'P(elig)':>9}{'med_days':>9}  breach_rules")
    for (pol, dd, g), v in out.items():
        print(f"{pol:<36}{dd:<30}{g:<20}{v['breach_prob']:>10.3f}{v['p_eligible']:>9.3f}"
              f"{str(v['median_days_to_eligible']):>9}  {v['breach_rules']}")
