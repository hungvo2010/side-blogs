#!/usr/bin/env python3
"""Trend chart + compare — real pytrends data.

Usage: python scripts/chart.py "keyword1" "keyword2"
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_automation.integrations.trends_client import TrendsClient

client = TrendsClient(geo="US")
keywords = sys.argv[1:6] if len(sys.argv) > 1 else ["coffee", "cold brew", "french press"]

print(f"📊 TREND COMPARISON\n{'='*60}")

# Fetch interest over time
try:
    df = client.compare_keywords(keywords, geo="US")
    for kw in keywords:
        if kw in df.columns:
            avg = int(df[kw].mean())
            peak = int(df[kw].max())
            now = int(df[kw].iloc[-1])
            trend = "📈 UP" if now > avg * 1.2 else "📉 DOWN" if now < avg * 0.8 else "➡️ STABLE"
            bar = "█" * (avg // 5) if avg > 0 else "▏"
            print(f"  {kw:<25s} avg={avg:>4} peak={peak:>4} now={now:>4} {trend}  {bar}")
except Exception as e:
    print(f"  ⚠️ pytrends: {str(e)[:60]}")

# Real keyword overview via TrendsClient
print(f"\n📈 KEYWORD METRICS\n{'='*60}")
try:
    for kw in keywords:
        ov = client.get_keyword_overview(kw, "us")
        vol = ov["volume"]
        diff = ov["difficulty"]
        score = vol * (100 - diff) / 100
        icon = "🟢" if score > 5000 else "🟡" if score > 1500 else "🟠" if score > 500 else "🔴"
        print(f"  {icon} {kw:<25s} vol={vol:>6,}  diff={diff:>3}  score={score:>8,.0f}")
        time.sleep(2)
except Exception as e:
    print(f"  ⚠️ {str(e)[:60]}")
