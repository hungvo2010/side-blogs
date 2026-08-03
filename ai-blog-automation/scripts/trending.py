#!/usr/bin/env python3
"""Scan trending keywords — daily/weekly, multi-geo.

Usage: python scripts/trending.py           # today's trending
       python scripts/trending.py --geo US  # specific country
       python scripts/trending.py --monthly # past 30 days
"""
import sys, time, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ["MOCK_MODE"] = "false"

import argparse
from pytrends.request import TrendReq

p = TrendReq(hl="en-US", tz=420)

# ─── Trending topics ─────────────────────────────────────────────────
_TRENDING_PNS = {
    "vietnam": "VN", "united_states": "US", "australia": "AU",
    "united_kingdom": "GB", "canada": "CA", "japan": "JP",
    "singapore": "SG", "india": "IN", "germany": "DE", "france": "FR",
}

# Fallback trending data when API rate limits
_FALLBACK = {
    "vietnam": ["du lịch hè", "iPhone 17", "bóng đá Việt Nam", "thời tiết", "cà phê"],
    "united_states": ["ai tools", "nfl scores", "hurricane season", "stock market", "taylor swift"],
    "australia": ["afl finals", "weather radar", "interest rates", "netflix", "property prices"],
}

# ─── Interest over time ──────────────────────────────────────────────
def compare_keywords(keywords: list[str], geo: str = "US", months: int = 12):
    """Compare interest for up to 5 keywords over time."""
    frame = f"today {months}-m" if months <= 12 else "today 5-y"
    try:
        p.build_payload(kw_list=keywords[:5], geo=geo, timeframe=frame)
        df = p.interest_over_time()
        if not df.empty:
            return {
                kw: round(df[kw].mean(), 1) for kw in keywords if kw in df.columns
            }
    except Exception as e:
        print(f"  ⚠️ {e}")
    return {}

# ─── Output ───────────────────────────────────────────────────────────
def print_trending(pn: str, fallback: bool = False):
    """Print trending topics for a country."""
    code = _TRENDING_PNS.get(pn, pn.upper())
    source = "fallback" if fallback else "trends"

    if fallback:
        topics = _FALLBACK.get(pn, _FALLBACK["united_states"])
    else:
        try:
            df = p.trending_searches(pn=pn)
            topics = list(df["title"].head(10))
            time.sleep(2)
        except Exception:
            topics = _FALLBACK.get(pn, _FALLBACK["united_states"])
            source = "fallback"

    print(f"\n  {code} ({pn})")
    for i, t in enumerate(topics[:10], 1):
        print(f"  {i:>2}. {t}")
    return topics

# ─── Main ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Trending keyword scanner")
    ap.add_argument("--geo", default="all", help="Country: VN, US, AU, or 'all'")
    ap.add_argument("--compare", nargs="+", help="Compare keywords: --compare 'ai tools' 'crypto'")
    ap.add_argument("--monthly", action="store_true", help="Show monthly trend")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    args = ap.parse_args()

    geos = ["vietnam", "united_states", "australia"] if args.geo == "all" else [args.geo.lower()]

    # ── Trending topics ──
    print("=" * 60)
    print("🔥 TRENDING TOPICS")
    print("=" * 60)
    all_topics = {}
    for geo in geos:
        pn = {"vn": "vietnam", "us": "united_states", "au": "australia"}.get(
            geo.lower(), geo.lower()
        )
        all_topics[pn] = print_trending(pn, fallback=False)
        time.sleep(2)

    # ── Compare mode ──
    if args.compare:
        print("\n" + "=" * 60)
        print("📊 KEYWORD COMPARISON (US, 12 months)")
        print("=" * 60)
        scores = compare_keywords(args.compare, "US", 12)
        for kw, score in sorted(scores.items(), key=lambda x: -x[1]):
            bar = "█" * int(score / 5)
            print(f"  {kw:<30s} {score:>5.0f} {bar}")

    # ── JSON output ──
    if args.json:
        import json
        out = {pn: topics for pn, topics in all_topics.items()}
        if args.compare:
            out["compare"] = compare_keywords(args.compare, "US", 12)
        print("\n" + json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
