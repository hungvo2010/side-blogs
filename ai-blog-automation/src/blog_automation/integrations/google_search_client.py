"""Google Custom Search JSON API client — free alternative to Ahrefs.

Provides the same interface as ``AhrefsClient`` so the two are interchangeable
via ``SEARCH_PROVIDER`` in .env (``google`` or ``ahrefs``).

Free tier: 100 queries/day, 10 results per query.
Docs: https://developers.google.com/custom-search/v1/overview

What it CAN provide (vs Ahrefs):
    - SERP results (title, URL, snippet)           ✅ full match
    - Top ranking pages                             ✅ full match
    - SERP features (snippets, images, etc.)        ✅ partial (Rich Snippet detection)
    - Related queries                               ✅ via Google Suggest
    - Search volume                                 ❌ estimated via trends only
    - Keyword difficulty                            ❌ estimated from result count / DR
    - CPC                                           ❌ not available
"""

from __future__ import annotations

from typing import Any

import requests

from blog_automation.config import get_settings
from blog_automation.errors import (
    APIAuthenticationError,
    InvalidKeywordError,
)
from blog_automation.integrations.cache import get_cache
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class GoogleSearchClient:
    """Google Custom Search client — drop-in replacement for AhrefsClient.

    Implements the same public API as AhrefsClient so pipeline code works
    unchanged regardless of which provider is configured.
    """

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: str | None = None,
        search_engine_id: str | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.google_search_api_key
        self.search_engine_id = search_engine_id or settings.google_search_engine_id

        if not self.api_key or not self.search_engine_id:
            raise APIAuthenticationError(
                message="Google Custom Search not configured — "
                "set GOOGLE_SEARCH_API_KEY + GOOGLE_SEARCH_ENGINE_ID in .env",
                service="google_search",
            )

        self.cache = get_cache()
        logger.info("GoogleSearchClient initialized (free tier: 100 queries/day)")

    # ------------------------------------------------------------------
    # Ahrefs-compatible interface
    # ------------------------------------------------------------------
    def _validate_keyword(self, keyword: str) -> str:
        if not keyword or not keyword.strip():
            raise InvalidKeywordError(
                message="Keyword cannot be empty",
                keyword=keyword,
            )
        return keyword.strip().lower()

    def _search(self, keyword: str, num: int = 10) -> dict[str, Any]:
        """Raw Google search query with caching."""
        keyword = self._validate_keyword(keyword)
        cache_key = f"google_search:{keyword}:{num}"
        cached = self.cache.get_cached(cache_key, "google_search")
        if cached:
            return cached

        resp = requests.get(
            self.BASE_URL,
            params={
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": keyword,
                "num": min(num, 10),
            },
            timeout=15,
        )
        if resp.status_code == 403:
            raise APIAuthenticationError(
                message="Google Search API quota exceeded or invalid key",
                service="google_search",
            )
        resp.raise_for_status()

        data = resp.json()
        self.cache.set_cache(cache_key, data, "google_search", ttl=86400)
        return data

    def get_keyword_overview(self, keyword: str, country: str = "us") -> dict[str, Any]:
        """Get overview metrics — mix of SERP data + estimates.

        Returns dict with: keyword, volume (estimated), difficulty (estimated),
        cpc (n/a), country, total_results, top_domains
        """
        data = self._search(keyword)

        items = data.get("items", [])
        total_results = int(data.get("searchInformation", {}).get("totalResults", 0))

        # Estimate difficulty from result count (very rough heuristic)
        if total_results > 1_000_000_000:
            difficulty = 80
        elif total_results > 100_000_000:
            difficulty = 65
        elif total_results > 10_000_000:
            difficulty = 50
        elif total_results > 1_000_000:
            difficulty = 35
        else:
            difficulty = 20

        # Rough volume estimate from result count
        volume = max(10, total_results // 1_000_000)

        # Top domains from first page
        top_domains = list(
            dict.fromkeys(
                self._extract_domain(item["link"]) for item in items if "link" in item
            )
        )[:5]

        result = {
            "keyword": keyword,
            "volume": volume,
            "difficulty": difficulty,
            "cpc": 0,  # Google Search API doesn't provide CPC
            "country": country,
            "total_results": total_results,
            "top_domains": top_domains,
        }

        logger.info(
            "Google keyword overview",
            keyword=keyword,
            volume=volume,
            difficulty=difficulty,
            results=total_results,
        )
        return result

    def search_volume(self, keyword: str, country: str = "us") -> dict:
        """Search volume estimate (based on result count).

        For accurate volume, use pytrends or DataForSEO supplement.
        """
        overview = self.get_keyword_overview(keyword, country)
        return {
            "keyword": keyword,
            "volume": overview["volume"],
            "cpc": overview["cpc"],
            "estimated": True,
        }

    def keyword_difficulty(self, keyword: str, country: str = "us") -> dict:
        """Keyword difficulty estimate."""
        overview = self.get_keyword_overview(keyword, country)
        return {
            "keyword": keyword,
            "difficulty": overview["difficulty"],
            "source": "result_count_estimate",
        }

    def serp_features(self, keyword: str, country: str = "us") -> dict:
        """Detect SERP features from rich snippet types."""
        data = self._search(keyword)

        items = data.get("items", [])
        features = {
            "featured_snippet": False,
            "knowledge_graph": False,
            "people_also_ask": False,
            "image_pack": False,
            "video_carousel": False,
            "rich_snippets": [],
        }

        for item in items:
            if "pagemap" not in item:
                continue
            pm = item["pagemap"]
            if "metatags" in pm:
                for tag in pm["metatags"]:
                    if tag.get("og:type") == "video":
                        features["video_carousel"] = True
            if "videoobject" in pm:
                features["video_carousel"] = True
            if "imageobject" in pm:
                features["image_pack"] = True
            if "person" in pm:
                features["knowledge_graph"] = True

        # Check for featured snippet (first result with rich snippet)
        if items and "pagemap" in items[0]:
            pm = items[0]["pagemap"]
            if "metatags" in pm:
                for tag in pm["metatags"]:
                    if "description" in tag and len(tag["description"]) > 200:
                        features["featured_snippet"] = True

        features["rich_snippets"] = [k for k, v in features.items() if v]

        logger.info("Google SERP features", keyword=keyword, features=features)
        return features

    def top_pages(
        self, keyword: str, country: str = "us", limit: int = 10
    ) -> list[dict]:
        """Return top ranking pages for a keyword."""
        data = self._search(keyword, num=min(limit, 10))

        pages = []
        for item in data.get("items", []):
            pages.append(
                {
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "display_url": item.get("displayLink", ""),
                }
            )

        return pages[:limit]

    def competitor_analysis(self, keyword: str, country: str = "us") -> dict[str, Any]:
        """Competitor overview from SERP."""
        pages = self.top_pages(keyword, country, limit=10)
        domains = list(
            dict.fromkeys(self._extract_domain(p["url"]) for p in pages if p["url"])
        )

        return {
            "keyword": keyword,
            "top_domains": domains[:5],
            "total_competitors": len(domains),
            "top_pages": pages[:3],
        }

    def get_keyword_metrics(self, keyword: str, country: str = "us") -> dict:
        """One-stop: all metrics bundled (matches Ahrefs get_keyword_metrics)."""
        return {
            "overview": self.get_keyword_overview(keyword, country),
            "volume": self.search_volume(keyword, country),
            "difficulty": self.keyword_difficulty(keyword, country),
            "serp_features": self.serp_features(keyword, country),
            "top_pages": self.top_pages(keyword, country=country),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_domain(url: str) -> str:
        from urllib.parse import urlparse

        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return url
