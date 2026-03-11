"""Ahrefs API client for keyword research.

Provides keyword metrics, SERP analysis, and competitor research using API v3.
"""

from typing import Any

from blog_automation.config import get_settings
from blog_automation.errors import APIAuthenticationError, InvalidKeywordError, APIInvalidResponseError
from blog_automation.integrations.base_client import HTTPClient
from blog_automation.integrations.cache import get_cache
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class AhrefsClient(HTTPClient):
    """Ahrefs API client for keyword research (v3).

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
            rate_limit=30,
        )

        self.set_auth_header("Authorization", f"Bearer {self.api_key}")
        self.cache = get_cache()
        logger.info("Ahrefs client initialized (v3)")

    def _validate_keyword(self, keyword: str) -> str:
        """Validate and clean keyword."""
        if not keyword or not keyword.strip():
            raise InvalidKeywordError(
                message="Keyword cannot be empty",
                keyword=keyword,
            )
        return keyword.strip().lower()

    def get_keyword_overview(
        self,
        keyword: str,
        country: str = "us",
    ) -> dict[str, Any]:
        """Get overview metrics for a keyword.

        Args:
            keyword: Target keyword
            country: Country code

        Returns:
            Dict with volume, difficulty, etc.
        """
        keyword = self._validate_keyword(keyword)
        cache_key = f"ahrefs_overview:{keyword}:{country}"
        cached = self.cache.get_cached(cache_key, "keyword_overview")
        if cached:
            return cached

        response = self.get(
            "keywords-explorer/overview",
            params={
                "keywords": keyword,
                "country": country,
                "select": "volume,difficulty,cpc,lowest_dr_top10"
            },
        )

        # v3 returns results in a list under "keywords"
        keywords_data = response.get("keywords", [])
        if not keywords_data:
            logger.warning(f"No keyword data returned for: {keyword}")
            return {"volume": 0, "difficulty": 50, "cpc": 0}

        data = keywords_data[0]
        result = {
            "keyword": keyword,
            "volume": data.get("volume", 0),
            "difficulty": data.get("difficulty", 50),
            "cpc": data.get("cpc", 0),
            "country": country,
        }

        self.cache.set_cache(cache_key, result, "keyword_overview")
        return result

    def get_serp_overview(
        self,
        keyword: str,
        country: str = "us",
    ) -> dict[str, Any]:
        """Get SERP overview for a keyword.

        Args:
            keyword: Target keyword
            country: Country code

        Returns:
            Dict with SERP data
        """
        keyword = self._validate_keyword(keyword)
        cache_key = f"ahrefs_serp_v3:{keyword}:{country}"
        cached = self.cache.get_cached(cache_key, "serp_overview")
        if cached:
            return cached

        response = self.get(
            "serp-overview",
            params={
                "keyword": keyword,
                "country": country,
                "select": "position,url,title,domain_rating,backlinks,word_count,serp_features"
            },
        )

        # v3 response structure for serp-overview
        serp_data = response.get("serp", [])
        result = {
            "keyword": keyword,
            "serp": serp_data,
            "serp_features": response.get("serp_features", {}),
            "country": country,
        }

        self.cache.set_cache(cache_key, result, "serp_overview")
        return result

    def search_volume(self, keyword: str, country: str = "us") -> dict[str, Any]:
        """Backward compatibility for search_volume."""
        overview = self.get_keyword_overview(keyword, country)
        return {"volume": overview.get("volume", 0), "cpc": overview.get("cpc", 0)}

    def keyword_difficulty(self, keyword: str, country: str = "us") -> dict[str, Any]:
        """Backward compatibility for keyword_difficulty."""
        overview = self.get_keyword_overview(keyword, country)
        return {"difficulty": overview.get("difficulty", 50)}

    def serp_features(self, keyword: str, country: str = "us") -> dict[str, Any]:
        """Backward compatibility for serp_features."""
        serp = self.get_serp_overview(keyword, country)
        features = serp.get("serp_features", {})
        return {
            "keyword": keyword,
            "featured_snippet": "featured_snippet" in features,
            "knowledge_panel": "knowledge_panel" in features,
            "people_also_ask": features.get("people_also_ask", []),
            "country": country,
        }

    def top_pages(self, keyword: str, country: str = "us", limit: int = 10) -> list[dict[str, Any]]:
        """Backward compatibility for top_pages."""
        serp = self.get_serp_overview(keyword, country)
        pages = []
        for item in serp.get("serp", [])[:limit]:
            pages.append({
                "position": item.get("position"),
                "url": item.get("url"),
                "title": item.get("title"),
                "domain_rating": item.get("domain_rating"),
                "backlinks": item.get("backlinks"),
                "word_count": item.get("word_count"),
            })
        return pages

    def competitor_analysis(self, keyword: str, country: str = "us") -> dict[str, Any]:
        """Analyze competitor content."""
        top_pages = self.top_pages(keyword, country, limit=10)
        if not top_pages:
            return {"keyword": keyword, "avg_word_count": 2000, "avg_domain_rating": 50, "competitors": []}

        word_counts = [p.get("word_count", 0) for p in top_pages if p.get("word_count")]
        domain_ratings = [p.get("domain_rating", 0) for p in top_pages if p.get("domain_rating")]

        return {
            "keyword": keyword,
            "avg_word_count": sum(word_counts) // len(word_counts) if word_counts else 2000,
            "avg_domain_rating": sum(domain_ratings) // len(domain_ratings) if domain_ratings else 50,
            "competitors": top_pages[:5],
        }

    def get_keyword_metrics(self, keyword: str, country: str = "us") -> dict[str, Any]:
        """Get combined keyword metrics."""
        overview = self.get_keyword_overview(keyword, country)
        serp = self.serp_features(keyword, country)
        return {
            "keyword": keyword,
            "volume": overview.get("volume", 0),
            "difficulty": overview.get("difficulty", 50),
            "cpc": overview.get("cpc", 0),
            "serp_features": serp,
            "country": country,
        }
