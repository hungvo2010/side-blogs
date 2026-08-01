#!/usr/bin/env python3
"""Standalone keyword analysis tool — run anytime, no API keys needed.

Uses mock data by default so you can see the analysis immediately.
With real API keys, it hits Google Custom Search / Ahrefs.

Usage::

    python scripts/analyze_keyword.py "best coffee maker"
    python scripts/analyze_keyword.py "how to clean coffee maker" --real
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(_SRC))

from blog_automation.pipelines.phase_1_research.keyword_analyzer import (
    BacklinkOpportunity,
    KeywordAnalysis,
    KeywordAnalyzer,
    KeywordScore,
)

# ---------------------------------------------------------------------------
# Mock data — realistic examples so the analyzer works without API keys
# ---------------------------------------------------------------------------
MOCK_DATA = {
    "best coffee maker": {
        "keyword": "best coffee maker",
        "volume": 49500,
        "difficulty": 65,
        "top_pages": [
            {"url": "https://www.nytimes.com/wirecutter/reviews/best-coffee-maker/",
             "title": "The 4 Best Coffee Makers of 2026 | Reviews by Wirecutter",
             "snippet": "After testing over 50 models in 2024... we recommend the Cafe Specialty Drip."},
            {"url": "https://www.seriouseats.com/best-coffee-makers-2026",
             "title": "Best Coffee Makers 2026 — Top 10 Tested by Serious Eats",
             "snippet": "Our test kitchen spent 300 hours evaluating drip machines."},
            {"url": "https://coffeegeek.com/guides/best-coffee-maker/",
             "title": "Best Coffee Maker Guide — CoffeeGeek Reviews",
             "snippet": "Honest reviews from coffee enthusiasts since 2016."},
            {"url": "https://www.techradar.com/best/best-coffee-maker",
             "title": "Best Coffee Maker 2026 — Top Picks | TechRadar",
             "snippet": "We compare the best drip, pour-over, and espresso machines."},
            {"url": "https://beansandbrews.net/best-drip-coffee-maker-2024/",
             "title": "Best Drip Coffee Maker 2024 — Beans & Brews Blog",
             "snippet": "Updated for 2024: our top 5 picks for home brewing."},
            {"url": "https://homebrewguide.com/top-coffee-makers/",
             "title": "Top Coffee Makers: How to Choose the Right One",
             "snippet": "A beginner-friendly guide to picking your first serious coffee maker."},
        ],
    },
    "how to clean coffee maker": {
        "keyword": "how to clean coffee maker",
        "volume": 8100,
        "difficulty": 25,
        "top_pages": [
            {"url": "https://www.tasteofhome.com/article/how-to-clean-coffee-maker/",
             "title": "How to Clean a Coffee Maker the Right Way | Taste of Home",
             "snippet": "Simple step-by-step guide with vinegar and water. Updated 2023."},
            {"url": "https://www.allrecipes.com/article/how-to-clean-coffee-maker/",
             "title": "How to Clean Your Coffee Maker | Allrecipes",
             "snippet": "Expert tips from 2022 on descaling and maintaining your machine."},
            {"url": "https://cleanandbrew.com/coffee-maker-cleaning-guide/",
             "title": "Ultimate Coffee Maker Cleaning Guide — Clean & Brew",
             "snippet": "Deep cleaning techniques for every type of machine."},
            {"url": "https://www.kitchenaid.com/blog/how-to-clean-coffee-maker.html",
             "title": "How to Clean a Coffee Maker | KitchenAid Blog",
             "snippet": "Official guide from KitchenAid. Covers drip and espresso."},
        ],
    },
    "nespresso vs keurig": {
        "keyword": "nespresso vs keurig",
        "volume": 3300,
        "difficulty": 42,
        "top_pages": [
            {"url": "https://www.techradar.com/nespresso-vs-keurig",
             "title": "Nespresso vs Keurig: which pod coffee maker is best?",
             "snippet": "We compare both systems head-to-head in 2024."},
            {"url": "https://coffeeblog.co.uk/nespresso-vs-keurig/",
             "title": "Nespresso vs Keurig 2025 Comparison — Coffee Blog",
             "snippet": "Honest comparison from a coffee shop owner."},
        ],
    },
    "coffee subscription box": {
        "keyword": "coffee subscription box",
        "volume": 2200,
        "difficulty": 30,
        "top_pages": [
            {"url": "https://www.foodandwine.com/best-coffee-subscriptions",
             "title": "Best Coffee Subscriptions 2026 | Food & Wine",
             "snippet": "We tested 30+ coffee subscription boxes to find the best."},
            {"url": "https://beanbox.com/blog/best-coffee-subscriptions/",
             "title": "Best Coffee Subscriptions of 2026 — Bean Box",
             "snippet": "Curated list from a subscription company themselves."},
            {"url": "https://coffeereview.com/subscriptions/",
             "title": "Coffee Subscription Reviews — Coffee Review",
             "snippet": "Independent reviews of subscription services."},
        ],
    },
    "coffee maker": {
        "keyword": "coffee maker",
        "volume": 201000,
        "difficulty": 91,
        "top_pages": [
            {"url": "https://www.amazon.com/coffee-makers/b?ie=UTF8&node=289745",
             "title": "Coffee Makers — Amazon.com",
             "snippet": "Online shopping for coffee makers from a great selection."},
            {"url": "https://www.walmart.com/browse/home/coffee-makers/",
             "title": "Coffee Makers — Walmart.com",
             "snippet": "Shop for coffee makers at Walmart. Free shipping on orders $35+."},
        ],
    },
}


# ---------------------------------------------------------------------------
# Pretty-print helpers
# ---------------------------------------------------------------------------
def _divider(char: str = "─", width: int = 60) -> str:
    return char * width


def _emoji_score(score: float) -> str:
    if score > 5000:
        return "🟢"
    if score > 1500:
        return "🟡"
    if score > 500:
        return "🟠"
    return "🔴"


def _emoji_ease(score: int) -> str:
    if score >= 7:
        return "🟢 Easy"
    if score >= 5:
        return "🟡 Medium"
    return "🔴 Hard"


def print_score(s: KeywordScore) -> None:
    print(f"\n{'='*60}")
    print(f"  📊 KEYWORD SCORE: {s.keyword}")
    print(f"  {'='*60}")
    print(f"  Volume:        {s.volume:>12,} searches/month")
    print(f"  Difficulty:    {s.difficulty:>12}/100")
    print(f"  {_emoji_score(s.opportunity_score)} Opportunity:  {s.opportunity_score:>12,.1f}")
    print(f"  Verdict:       {s.verdict:>12}")
    print(f"\n  💡 {s.why}")


def print_backlinks(opps: list[BacklinkOpportunity]) -> None:
    if not opps:
        print(f"\n  📎 No backlink targets identified.")
        return

    print(f"\n  📎 BACKLINK OPPORTUNITIES ({len(opps)} found):")
    for i, opp in enumerate(opps, 1):
        print(f"  {_divider()}")
        print(f"  #{i} {opp.domain}")
        print(f"      URL:     {opp.url}")
        print(f"      Type:    {opp.approach}")
        print(f"      Ease:    {_emoji_ease(opp.ease_score)} ({opp.ease_score}/10)")
        print(f"      Why:     {opp.why}")


def print_analysis(analysis: KeywordAnalysis) -> None:
    print_score(analysis.score)
    print_backlinks(analysis.backlink_opportunities)
    print(f"\n  📝 SUMMARY: {analysis.summary}")
    print(f"\n{'='*60}\n")


def print_batch(results: list[KeywordAnalysis]) -> None:
    print(f"\n{'='*60}")
    print(f"  🏆 KEYWORD RANKING (best opportunity first)")
    print(f"  {'='*60}\n")

    for i, r in enumerate(results, 1):
        icon = _emoji_score(r.score.opportunity_score)
        print(
            f"  {i:>2}. {icon} {r.score.keyword:<35s} "
            f"Score: {r.score.opportunity_score:>8,.1f}  "
            f"Vol: {r.score.volume:>6,}  "
            f"Diff: {r.score.difficulty:>3}"
        )

    print(f"\n  💡 Pick the top 1–2 keywords with 🟢 scores.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description="Analyze keyword opportunity + backlink potential"
    )
    p.add_argument(
        "keyword",
        nargs="?",
        help="Keyword to analyze (omit to run batch demo with mock data)",
    )
    p.add_argument(
        "--real",
        action="store_true",
        help="Use real search API (needs GOOGLE_SEARCH_API_KEY or AHREFS_API_KEY)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of pretty-print",
    )
    args = p.parse_args()

    analyzer = KeywordAnalyzer()

    # ------------------------------------------------------------------
    # Batch mode — demo with multiple keywords
    # ------------------------------------------------------------------
    if not args.keyword:
        print("🚀 Running batch keyword analysis (mock data)\n")
        batch_data = list(MOCK_DATA.values())
        results = analyzer.batch_analyze(batch_data)

        if args.json:
            out = []
            for r in results:
                out.append(
                    {
                        "keyword": r.score.keyword,
                        "verdict": r.score.verdict,
                        "score": r.score.opportunity_score,
                        "volume": r.score.volume,
                        "difficulty": r.score.difficulty,
                        "backlinks": [
                            {"domain": b.domain, "approach": b.approach, "ease": b.ease_score}
                            for b in r.backlink_opportunities
                        ],
                        "summary": r.summary,
                    }
                )
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print_batch(results)
            # Also show detail for the top pick
            print(f"\n{'─'*60}")
            print("  📋 DETAILED ANALYSIS: TOP PICK")
            print_analysis(results[0])
        return

    # ------------------------------------------------------------------
    # Single keyword mode
    # ------------------------------------------------------------------
    keyword = args.keyword.strip().lower()

    if args.real:
        # Use the configured search provider
        try:
            from blog_automation.integrations.search_factory import get_search_client

            client = get_search_client()
            print(f"🔍 Searching with {type(client).__name__}...")
            overview = client.get_keyword_overview(keyword)
            top_pages = client.top_pages(keyword, limit=10)
            keyword_data = {
                "keyword": keyword,
                "volume": overview.get("volume", 0),
                "difficulty": overview.get("difficulty", 50),
                "top_pages": top_pages,
            }
        except Exception as e:
            print(f"❌ Search failed: {e}")
            print("Falling back to mock data...")
            keyword_data = MOCK_DATA.get(keyword)
            if not keyword_data:
                print(f"❌ No mock data for '{keyword}'. Try one of: {list(MOCK_DATA.keys())}")
                return 1
    else:
        keyword_data = MOCK_DATA.get(keyword)
        if not keyword_data:
            print(f"❌ No mock data for '{keyword}'. Available keywords:")
            for k in MOCK_DATA:
                print(f"   • {k}")
            print(f"\nUse --real to search with Google API instead.")
            return 1

    analysis = analyzer.analyze(keyword_data)

    if args.json:
        print(
            json.dumps(
                {
                    "keyword": analysis.score.keyword,
                    "verdict": analysis.score.verdict,
                    "score": analysis.score.opportunity_score,
                    "volume": analysis.score.volume,
                    "difficulty": analysis.score.difficulty,
                    "backlinks": [
                        {
                            "domain": b.domain,
                            "approach": b.approach,
                            "ease": b.ease_score,
                        }
                        for b in analysis.backlink_opportunities
                    ],
                    "summary": analysis.summary,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print_analysis(analysis)

    return 0


if __name__ == "__main__":
    sys.exit(main())
