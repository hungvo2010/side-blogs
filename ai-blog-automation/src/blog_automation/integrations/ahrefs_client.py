"""Ahrefs API client for keyword research.

Provides keyword metrics, SERP analysis, and competitor research.
"""

from typing import Any

from blog_automation.config import get_settings
from blog_automation.errors import APIAuthenticationError, InvalidKeywordError
from blog_automation.integrations.base_client import HTTPClient
from blog_automation.integrations.cache import get_cache
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class AhrefsClient(HTTPClient):
    """Ahrefs API client for keyword research.

    Provides methods for:
    - Search volume lookup
    - Keyword difficulty analysis
    - SERP feature detection
    - Top pages analysis
    - Competitor research
    """

    BASE_URL = "https://api.ahrefs.com/v3"

    def __init__(self, api_key: str | None = None):
        """Initialize Ahrefs client.

        Args:
            api_key: Ahrefs API key
        """
        settings = get_settings()
        self.api_key = api_key or settings.ahrefs_api_key

        if not self.api_key:
            raise APIAuthenticationError(
                message="Ahrefs API key not configured",
                service="ahrefs",
            )

        super().__init__(
            base_url=self.BASE_URL,
            timeout=30,
            max_retries=3,
            rate_limit=30,  # Ahrefs has strict rate limits
        )

        self.set_auth_header("Authorization", f"Bearer {self.api_key}")
        self.cache = get_cache()
        logger.info("Ahrefs client initialized")

    def _validate_keyword(self, keyword: str) -> str:
        """Validate and clean keyword.

        Args:
            keyword: Keyword to validate

        Returns:
            Cleaned keyword

        Raises:
            InvalidKeywordError: If keyword is invalid
        """
        if not keyword or not keyword.strip():
            raise InvalidKeywordError(
                message="Keyword cannot be empty",
                keyword=keyword,
            )

        keyword = keyword.strip().lower()

        if len(keyword) > 200:
            raise InvalidKeywordError(
                message="Keyword too long (max 200 characters)",
                keyword=keyword,
            )

        return keyword

    def search_volume(
        self,
        keyword: str,
        country: str = "us",
    ) -> dict[str, Any]:
        """Get search volume for a keyword.

        Args:
            keyword: Target keyword
            country: Country code (default: us)

        Returns:
            Dict with volume, cpc, and trend data
        """
        keyword = self._validate_keyword(keyword)

        # Check cache
        cache_key = f"ahrefs_volume:{keyword}:{country}"
        cached = self.cache.get_cached(cache_key, "keyword_volume")
        if cached:
            return cached

        response = self.get(
            "keywords-explorer/volume",
            params={
                "keyword": keyword,
                "country": country,
            },
        )

        result = {
            "keyword": keyword,
            "volume": response.get("volume", 0),
            "cpc": response.get("cpc", 0),
            "trend": response.get("trend", []),
            "country": country,
        }

        self.cache.set_cache(cache_key, result, "keyword_volume")
        return result

    def keyword_difficulty(
        self,
        keyword: str,
        country: str = "us",
    ) -> dict[str, Any]:
        """Get keyword difficulty score.

        Args:
            keyword: Target keyword
            country: Country code

        Returns:
            Dict with difficulty score and metrics
        """
        keyword = self._validate_keyword(keyword)

        cache_key = f"ahrefs_kd:{keyword}:{country}"
        cached = self.cache.get_cached(cache_key, "keyword_difficulty")
        if cached:
            return cached

        response = self.get(
            "keywords-explorer/difficulty",
            params={
                "keyword": keyword,
                "country": country,
            },
        )

        result = {
            "keyword": keyword,
            "difficulty": response.get("difficulty", 50),
            "clicks": response.get("clicks", 0),
            "clicks_per_search": response.get("clicks_per_search", 0),
            "country": country,
        }

        self.cache.set_cache(cache_key, result, "keyword_difficulty")
        return result

    def serp_features(
        self,
        keyword: str,
        country: str = "us",
    ) -> dict[str, Any]:
        """Get SERP features for a keyword.

        Args:
            keyword: Target keyword
            country: Country code

        Returns:
            Dict with SERP feature information
        """
        keyword = self._validate_keyword(keyword)

        cache_key = f"ahrefs_serp:{keyword}:{country}"
        cached = self.cache.get_cached(cache_key, "serp_features")
        if cached:
            return cached

        response = self.get(
            "keywords-explorer/serp-overview",
            params={
                "keyword": keyword,
                "country": country,
            },
        )

        # Extract SERP features
        features = response.get("serp_features", {})
        result = {
            "keyword": keyword,
            "featured_snippet": features.get("featured_snippet", False),
            "people_also_ask": features.get("people_also_ask", []),
            "knowledge_panel": features.get("knowledge_panel", False),
            "local_pack": features.get("local_pack", False),
            "images": features.get("images", False),
            "videos": features.get("videos", False),
            "shopping": features.get("shopping", False),
            "country": country,
        }

        self.cache.set_cache(cache_key, result, "serp_features")
        return result

    def top_pages(
        self,
        keyword: str,
        country: str = "us",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get top ranking pages for a keyword.

        Args:
            keyword: Target keyword
            country: Country code
            limit: Number of results

        Returns:
            List of top page data
        """
        keyword = self._validate_keyword(keyword)

        cache_key = f"ahrefs_top:{keyword}:{country}:{limit}"
        cached = self.cache.get_cached(cache_key, "top_pages")
        if cached:
            return cached

        response = self.get(
            "keywords-explorer/serp-overview",
            params={
                "keyword": keyword,
                "country": country,
                "limit": limit,
            },
        )

        pages = []
        for item in response.get("serp", [])[:limit]:
            pages.append(
                {
                    "position": item.get("position"),
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "domain_rating": item.get("domain_rating"),
                    "url_rating": item.get("url_rating"),
                    "backlinks": item.get("backlinks"),
                    "traffic": item.get("traffic"),
                    "word_count": item.get("word_count"),
                }
            )

        self.cache.set_cache(cache_key, pages, "top_pages")
        return pages

    def competitor_analysis(
        self,
        keyword: str,
        country: str = "us",
    ) -> dict[str, Any]:
        """Analyze competitor content for a keyword.

        Args:
            keyword: Target keyword
            country: Country code

        Returns:
            Aggregated competitor analysis
        """
        keyword = self._validate_keyword(keyword)

        # Get top pages
        top_pages = self.top_pages(keyword, country, limit=10)

        if not top_pages:
            return {
                "keyword": keyword,
                "avg_word_count": 2000,
                "avg_domain_rating": 50,
                "avg_backlinks": 100,
                "competitors": [],
            }

        # Calculate averages
        word_counts = [p.get("word_count", 0) for p in top_pages if p.get("word_count")]
        domain_ratings = [
            p.get("domain_rating", 0) for p in top_pages if p.get("domain_rating")
        ]
        backlinks = [p.get("backlinks", 0) for p in top_pages if p.get("backlinks")]

        return {
            "keyword": keyword,
            "avg_word_count": sum(word_counts) // len(word_counts) if word_counts else 2000,
            "avg_domain_rating": sum(domain_ratings) // len(domain_ratings) if domain_ratings else 50,
            "avg_backlinks": sum(backlinks) // len(backlinks) if backlinks else 100,
            "min_word_count": min(word_counts) if word_counts else 1000,
            "max_word_count": max(word_counts) if word_counts else 3000,
            "competitors": top_pages[:5],
        }

    def keyword_difficulty_batch(
        self,
        keywords: list[str],
        country: str = "us",
    ) -> list[dict[str, Any]]:
        """Get difficulty for multiple keywords.

        Args:
            keywords: List of keywords
            country: Country code

        Returns:
            List of difficulty results
        """
        results = []
        for keyword in keywords:
            try:
                result = self.keyword_difficulty(keyword, country)
                results.append(result)
            except InvalidKeywordError:
                results.append(
                    {
                        "keyword": keyword,
                        "difficulty": None,
                        "error": "Invalid keyword",
                    }
                )
        return results

    def get_keyword_metrics(
        self,
        keyword: str,
        country: str = "us",
    ) -> dict[str, Any]:
        """Get comprehensive keyword metrics.

        Combines volume, difficulty, and SERP data.

        Args:
            keyword: Target keyword
            country: Country code

        Returns:
            Combined keyword metrics
        """
        keyword = self._validate_keyword(keyword)

        volume_data = self.search_volume(keyword, country)
        difficulty_data = self.keyword_difficulty(keyword, country)
        serp_data = self.serp_features(keyword, country)

        return {
            "keyword": keyword,
            "volume": volume_data.get("volume", 0),
            "difficulty": difficulty_data.get("difficulty", 50),
            "cpc": volume_data.get("cpc", 0),
            "clicks": difficulty_data.get("clicks", 0),
            "serp_features": serp_data,
            "country": country,
        }
