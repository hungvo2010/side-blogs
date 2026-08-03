#!/usr/bin/env python3
"""Scan trending keywords — pytrends-modern RSS + TrendsClient."""
import sys, os, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ["MOCK_MODE"] = "false"

from blog_automation.integrations.trends_client import TrendsClient, _GEO_MAP

GEOS = ["VN", "US", "AU", "GB", "CA", "JP", "SG", "IN", "DE", "FR"]

def main():
    ap = argparse.ArgumentParser(description="Trending keyword scanner")
    ap.add_argument("--geo", default="all")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    geos = GEOS if args.geo == "all" else [args.geo.upper()]

    print("=" * 60)
    print("🔥 TRENDING TOPICS (pytrends-modern RSS)")
    print("=" * 60)

    client = TrendsClient()
    all_topics = {}

    for geo in geos:
        topics = client.trending_topics(geo, limit=10)
        code = _GEO_MAP.get(geo, geo)
        source = topics[0].get("source", "?") if topics else "?"
        print(f"\n  {code} ({geo})  [{source}]")
        for i, t in enumerate(topics[:10], 1):
            traffic = t.get("traffic", "")
            traffic_str = f" ({traffic})" if traffic else ""
            print(f"  {i:>2}. {t['title']}{traffic_str}")
        all_topics[geo] = topics

    if args.json:
        import json
        print("\n" + json.dumps(
            {g: [t["title"] for t in ts] for g, ts in all_topics.items()},
            indent=2, ensure_ascii=False,
        ))


if __name__ == "__main__":
    main()
