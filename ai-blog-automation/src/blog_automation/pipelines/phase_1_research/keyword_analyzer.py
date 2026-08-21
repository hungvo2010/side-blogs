"""Keyword opportunity scoring & backlink analysis.

Answers the two key questions Phase 1 must answer:

1. *Should I write about this keyword?*  → Opportunity Score
2. *Who can I get backlinks from?*        → Backlink Opportunities

Works with data from any search provider (Ahrefs, Google, or even mock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KeywordScore:
    """Quantified keyword opportunity."""

    keyword: str
    volume: int
    difficulty: int
    opportunity_score: float
    verdict: str  # "high", "medium", "low", "skip"
    why: str  # human-readable explanation


@dataclass
class BacklinkOpportunity:
    """A site worth targeting for a backlink."""

    url: str
    title: str
    domain: str
    approach: str  # "guest_post", "broken_link", "resource_page", "outreach"
    # 0-10 how easy it is to get a link from this site
    ease_score: int
    why: str


@dataclass
class KeywordAnalysis:
    """Full analysis result: scoring + backlink opps + recommendations."""

    keyword: str
    score: KeywordScore
    backlink_opportunities: list[BacklinkOpportunity] = field(default_factory=list)
    summary: str = ""  # 2-sentence action plan


class KeywordAnalyzer:
    """Score keywords and find backlink opportunities from search results.

    Uses data from any provider via a standard dict shape::

        {
            "keyword": "best coffee maker",
            "volume": 50000,
            "difficulty": 65,
            "top_pages": [
                {"url": "https://...", "title": "...", "snippet": "..."},
                ...
            ],
        }

    The analysis is heuristic-based (no real API for backlink analysis) but
    gives actionable direction.
    """

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def score_keyword(self, keyword_data: dict[str, Any]) -> KeywordScore:
        """Score a keyword for opportunity.

        Formula::

            opportunity = volume × (100 - difficulty) / 100

        High-volume, low-difficulty keywords score highest.
        """
        keyword = keyword_data["keyword"]
        volume = int(keyword_data.get("volume", 0))
        difficulty = int(keyword_data.get("difficulty", 50))

        # Clamp difficulty to meaningful range
        difficulty = max(0, min(100, difficulty))

        # Core score: 0-100000 (realistic range)
        score = volume * (100 - difficulty) / 100.0

        # Verdict thresholds
        if difficulty > 80:
            verdict = "skip"
            why = (
                f"Difficulty {difficulty}/100 — too competitive for a new site. "
                f"Even with {volume:,} monthly searches, you likely can't rank."
            )
        elif score > 5000:
            verdict = "high"
            why = (
                f"Excellent opportunity. {volume:,} searches/month, difficulty "
                f"{difficulty}/100. This keyword can drive significant traffic."
            )
        elif score > 1500:
            verdict = "medium"
            why = (
                f"Worth writing. {volume:,} searches/month at difficulty "
                f"{difficulty}/100. Good ROI for effort."
            )
        elif score > 500:
            verdict = "low"
            why = (
                f"Low priority. Only {volume:,} searches/month. Write it if "
                f"you have time, but don't prioritize it."
            )
        else:
            verdict = "skip"
            why = (
                f"Not worth it. {volume:,} searches/month at difficulty "
                f"{difficulty}/100 — traffic potential too small."
            )

        return KeywordScore(
            keyword=keyword,
            volume=volume,
            difficulty=difficulty,
            opportunity_score=round(score, 1),
            verdict=verdict,
            why=why,
        )

    # ------------------------------------------------------------------
    # Backlink opportunities
    # ------------------------------------------------------------------
    def find_backlink_opportunities(
        self,
        keyword_data: dict[str, Any],
        max_opps: int = 5,
    ) -> list[BacklinkOpportunity]:
        """Find backlink opportunities from competitor search results.

        Strategies:

        1. **Guest post targets** — sites that rank but aren't the top
           authority (nobody can guest-post on nytimes.com, but smaller
           blogs accept contributions).

        2. **Broken link opportunities** — pages that rank but likely have
           outdated content (detected by old dates in snippets).

        3. **Resource pages** — "best X" lists that already link out to
           multiple sources (they're primed to add another).
        """
        top_pages = keyword_data.get("top_pages", [])
        opportunities: list[BacklinkOpportunity] = []

        if not top_pages:
            return opportunities

        for page in top_pages[:10]:
            title = page.get("title", "")
            url = page.get("url", "")
            snippet = page.get("snippet", "")

            if not url:
                continue

            domain = self._extract_domain(url)

            # Skip mega-authority sites (near impossible to get links from)
            if self._is_mega_authority(domain):
                continue

            approach, ease, why = self._classify_page(title, snippet, domain)

            opportunities.append(
                BacklinkOpportunity(
                    url=url,
                    title=title,
                    domain=domain,
                    approach=approach,
                    ease_score=ease,
                    why=why,
                )
            )

        # Sort by ease (easiest first), return top N
        opportunities.sort(key=lambda o: o.ease_score, reverse=True)
        return opportunities[:max_opps]

    # ------------------------------------------------------------------
    # Full analysis
    # ------------------------------------------------------------------
    def analyze(self, keyword_data: dict[str, Any]) -> KeywordAnalysis:
        """Run full analysis: score + backlinks + summary."""
        score = self.score_keyword(keyword_data)
        opps = self.find_backlink_opportunities(keyword_data)

        keyword = keyword_data["keyword"]

        if score.verdict in ("skip", "low"):
            summary = (
                f"⏭️ {score.why} "
                f"Found {len(opps)} backlink opportunities but "
                f"keyword isn't a priority."
            )
        else:
            opp_summary = (
                f"📎 {len(opps)} backlink targets identified. "
                if opps
                else "No obvious backlink targets found. "
            )
            summary = f"✅ {score.why} {opp_summary}Start with a {score.difficulty}-difficulty long-form guide."

        return KeywordAnalysis(
            keyword=keyword,
            score=score,
            backlink_opportunities=opps,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Batch: score multiple keywords
    # ------------------------------------------------------------------
    def batch_analyze(
        self, keywords_data: list[dict[str, Any]], max_backlinks: int = 3
    ) -> list[KeywordAnalysis]:
        """Analyze multiple keywords, return sorted by opportunity (best first)."""
        results = []
        for kd in keywords_data:
            analysis = self.analyze(kd)
            # Keep only the top backlink opportunities per keyword
            analysis.backlink_opportunities = analysis.backlink_opportunities[
                :max_backlinks
            ]
            results.append(analysis)

        results.sort(key=lambda r: r.score.opportunity_score, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_domain(url: str) -> str:
        from urllib.parse import urlparse

        try:
            return urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            return url.lower()

    @staticmethod
    def _is_mega_authority(domain: str) -> bool:
        """Sites too big to realistically get links from."""
        mega = {
            "nytimes.com",
            "wsj.com",
            "forbes.com",
            "wikipedia.org",
            "amazon.com",
            "apple.com",
            "microsoft.com",
            "google.com",
            "youtube.com",
            "facebook.com",
            "twitter.com",
            "reddit.com",
            "bbc.com",
            "cnn.com",
            "theguardian.com",
            "washingtonpost.com",
        }
        return any(domain.endswith(d) for d in mega)

    @staticmethod
    def _classify_page(title: str, snippet: str, domain: str) -> tuple[str, int, str]:
        """Classify a competitor page for backlink opportunity type."""
        tl = title.lower()
        sl = snippet.lower()

        # Resource page: "best X of 2026", "top 10 X"
        if any(
            phrase in tl for phrase in ["best ", "top ", "ultimate guide", "review"]
        ):
            return (
                "resource_page",
                7,
                f"{domain} published a 'best X' list — they already link to "
                f"products/guides. Pitch your post as a worthy addition.",
            )

        # Outdated content signal
        if any(year in sl for year in ["2022", "2023", "2024"]):
            return (
                "broken_link",
                8,
                f"{domain}'s page references old data (detected year in snippet). "
                f"Create an updated version and ask them to link to it instead.",
            )

        # Blog — potential guest post target
        if any(word in tl for word in ["how to", "why ", "what is", "guide"]):
            return (
                "guest_post",
                5,
                f"{domain} writes how-to content — they likely accept "
                f"guest contributors. Pitch a related topic.",
            )

        # Generic outreach
        return (
            "outreach",
            4,
            f"General outreach to {domain}. Mention their article in your "
            f"post, then email them asking for a link.",
        )
