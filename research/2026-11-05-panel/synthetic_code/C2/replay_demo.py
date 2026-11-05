# SYNTHETIC replay demo: as-of join on (event_time <= t) AND (ingest_time <= t), pure stdlib.
from datetime import datetime, timedelta, timezone
ET = timezone(timedelta(hours=-5))
T = lambda h, m, s=0, ms=0: datetime(2026, 11, 4, h, m, s, ms * 1000, tzinfo=ET)

# feed rows: (event_time, ingest_time, payload); ingest lag is deliberately non-zero
market = [  # 1-min MNQ bars, vendor id V1
    (T(9, 40), T(9, 40, 0, 180), {"close": 25412.25}),
    (T(9, 41), T(9, 41, 0, 210), {"close": 25418.50}),
    (T(9, 42), T(9, 42, 0, 195), {"close": 25409.75}),   # arrives 195 ms after 09:42:00
]
account = [(T(9, 30), T(9, 30, 1), {"equity": 51240.0, "dd_room": 1240.0})]  # last broker push 09:30
STALE = {"market_snapshot": timedelta(seconds=65), "account_state": timedelta(seconds=60)}  # bar interval + 5 s grace

def asof(rows, t, feed):
    vis = [r for r in rows if r[0] <= t and r[1] <= t]
    if not vis:
        return None, "missing"
    ev, ing, p = max(vis, key=lambda r: (r[0], r[1]))
    return p, ("ok" if t - ev <= STALE[feed] else "stale")

for t in [T(9, 42, 0, 100), T(9, 42, 0, 300)]:
    m, ms = asof(market, t, "market_snapshot")
    a, as_ = asof(account, t, "account_state")
    print(f"t={t.time()}  market={m} [{ms}]  account={a} [{as_}]")
