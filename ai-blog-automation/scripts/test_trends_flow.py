#!/usr/bin/env python3
"""Test: pytrends → KeywordAnalyzer → publish-ready data"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_automation.integrations.trends_client import TrendsClient
from blog_automation.pipelines.phase_1_research.keyword_analyzer import KeywordAnalyzer

client = TrendsClient()
analyzer = KeywordAnalyzer()

# Test single keyword
print("=" * 60)
print("ANALYZE: 'air fryer' (US)")
print("=" * 60)

overview = client.get_keyword_overview("air fryer", "us")
pages = client.top_pages("air fryer", "us", limit=10)

data = {
    "keyword": "air fryer",
    "volume": overview["volume"],
    "difficulty": overview["difficulty"],
    "top_pages": pages,
}

analysis = analyzer.analyze(data)
print(f"  Score: {analysis.score.opportunity_score:,.0f}")
print(f"  Verdict: {analysis.score.verdict}")
print(f"  Backlinks: {len(analysis.backlink_opportunities)} found")
for b in analysis.backlink_opportunities[:3]:
    print(f"    - {b.domain}: {b.approach} (ease {b.ease_score}/10)")
print(f"  Summary: {analysis.summary}")

# Test batch from trending
print()
print("=" * 60)
print("BATCH: Trending VN → analyze")
print("=" * 60)

trending = client.trending_topics("VN", limit=5)
print(f"  Trending: {[t['title'] for t in trending]}")

batch_data = []
for t in trending[:3]:
    kw = t["title"]
    ov = client.get_keyword_overview(kw, "vn")
    pg = client.top_pages(kw, "vn", limit=5)
    import time; time.sleep(3)
    batch_data.append({
        "keyword": kw,
        "volume": ov["volume"],
        "difficulty": ov["difficulty"],
        "top_pages": pg,
    })

results = analyzer.batch_analyze(batch_data, max_backlinks=2)
print()
for r in results:
    icon = {"high":"🟢","medium":"🟡","low":"🟠","skip":"🔴"}.get(r.score.verdict,"⚪")
    print(f"  {icon} {r.score.keyword:<25s} score={r.score.opportunity_score:>8,.0f}  {r.score.verdict}")

print("\n✅ Full flow: pytrends → analyzer OK")
