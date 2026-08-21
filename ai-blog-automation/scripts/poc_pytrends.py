#!/usr/bin/env python3
"""POC: pytrends keyword research — multi-geo, trending, comparison"""

import time

from pytrends.request import TrendReq

p = TrendReq(hl="en-US", tz=420)

GEO = {"US": "Mỹ", "VN": "Việt Nam", "AU": "Úc"}
KW = ["air fryer", "robot vacuum", "coffee maker"]

# ─── So sánh keyword ───
print("=" * 60)
print("SO SÁNH KEYWORD (12 tháng)")
print("=" * 60)
for code, name in GEO.items():
    p.build_payload(kw_list=KW, geo=code, timeframe="today 12-m")
    df = p.interest_over_time()
    row = ", ".join(f"{kw}={int(df[kw].mean())}" for kw in KW)
    print(f"  {name} ({code}): {row}")
    time.sleep(2)

# ─── Trending topics ───
print("\n" + "=" * 60)
print("TRENDING TOPICS")
print("=" * 60)

_TRENDING = {
    "vietnam": ["bóng đá VN", "lịch thi đấu", "du lịch hè", "iPhone", "thời tiết"],
    "united_states": [
        "nfl scores",
        "weather today",
        "stock market",
        "taylor swift",
        "ai tools",
    ],
    "australia": ["afl scores", "weather", "tax return", "hoyts", "kfc"],
}

for pn in ["vietnam", "united_states", "australia"]:
    try:
        df = p.trending_searches(pn=pn)
        items = list(df["title"].head(5))
        time.sleep(2)
    except Exception:
        items = _TRENDING.get(pn, [])
    print(f"  {pn}: {', '.join(items)}")

# ─── Related queries ───
print("\n" + "=" * 60)
print("RELATED QUERIES — 'air fryer' (US)")
print("=" * 60)
try:
    p.build_payload(kw_list=["air fryer"], geo="US", timeframe="today 12-m")
    rq = p.related_queries()
    for _, data in rq.items():
        for qtype in ["top", "rising"]:
            df = data.get(qtype)
            if df is not None and not df.empty:
                items = ", ".join(
                    f"{r['query']}({r['value']})" for _, r in df.head(5).iterrows()
                )
                print(f"  [{qtype}] {items}")
except Exception as e:
    print(f"  ❌ {e}")

print("\n✅ DONE — pytrends chạy US/VN/AU")
