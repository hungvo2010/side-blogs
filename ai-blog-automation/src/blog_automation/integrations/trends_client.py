"""Keyword research via pytrends (Google Trends) — free, no API key.

Drop-in replacement for GoogleSearchClient / AhrefsClient.
Implements the same interface so pipeline code works unchanged.
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
from pytrends.request import TrendReq

from blog_automation.errors import InvalidKeywordError
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)

# Supported geos — map country codes to pytrends geo param
_GEO_MAP = {
    "us": "US",
    "vn": "VN",
    "au": "AU",
    "gb": "GB",
    "ca": "CA",
    "de": "DE",
    "fr": "FR",
    "jp": "JP",
    "sg": "SG",
    "in": "IN",
}

# Default interests for quick scoring
_TOP_INTERESTS = {
    "VN": [
        "bóng đá", "giải trí", "du lịch", "thời trang",
        "công nghệ", "sức khỏe", "giáo dục", "tài chính",
        "bất động sản", "ô tô", "game", "phim",
    ],
    "US": [
        "ai tools", "crypto", "stocks", "healthy recipes",
        "workout", "remote jobs", "travel deals", "streaming",
        "electric car", "house plants", "pet food", "meditation",
    ],
    "AU": [
        "coffee", "superannuation", "property", "cricket",
        "vegemite", "netflix", "bunnings", "spotify",
        "iphone", "tesla", "vegan", "hiking",
    ],
    "GB": [
        "premier league", "brexit", "tea", "pub",
        "weather", "train strikes", "fish and chips", "nhs",
        "bitcoin", "spotify", "air fryer", "aldi",
    ],
}

_RETRY_DELAYS = [5, 10, 30]  # seconds before retry on 429


class TrendsClient:
    """Google Trends keyword research — free, no API key required.

    Drop-in for ``GoogleSearchClient`` — same public API surface so pipeline
    code works with ``SEARCH_PROVIDER=trends``.
    """

    def __init__(self, geo: str = "us"):
        self.geo = geo.upper()
        self._pytrends = TrendReq(hl="en-US", tz=420, retries=2, backoff_factor=1)

    # ── drop-in interface (matches GoogleSearchClient) ─────────────────

    def get_keyword_overview(
        self, keyword: str, country: str = "us"
    ) -> dict[str, Any]:
        """Interest-based keyword overview (no real volume, but relative interest)."""
        keyword = self._validate(keyword)
        geo = _GEO_MAP.get(country, country.upper())
        iot = self._interest_over_time([keyword], geo)
        avg = int(iot[keyword].mean()) if not iot.empty and keyword in iot.columns else 0

        # Rough difficulty = 100 - avg (higher interest = more competition)
        difficulty = max(10, min(90, 100 - avg))

        return {
            "keyword": keyword,
            "volume": avg * 100,  # Scale trend → approximate volume
            "difficulty": difficulty,
            "interest": avg,
            "cpc": 0,
            "country": country,
            "source": "pytrends",
        }

    def search_volume(self, keyword: str, country: str = "us") -> dict:
        overview = self.get_keyword_overview(keyword, country)
        return {
            "keyword": keyword,
            "volume": overview["volume"],
            "trend_score": overview["interest"],
            "estimated": True,
        }

    def keyword_difficulty(self, keyword: str, country: str = "us") -> dict:
        overview = self.get_keyword_overview(keyword, country)
        return {
            "keyword": keyword,
            "difficulty": overview["difficulty"],
            "source": "pytrends_estimate",
        }

    def top_pages(
        self, keyword: str, country: str = "us", limit: int = 10
    ) -> list[dict]:
        """Returns related queries as pseudo 'top pages' for KeywordAnalyzer."""
        keyword = self._validate(keyword)
        geo = _GEO_MAP.get(country, country.upper())
        rq = self._related_queries(keyword, geo)
        pages = []
        for qtype in ["top", "rising"]:
            for _, row in rq.get(qtype, pd.DataFrame()).head(limit // 2).iterrows():
                pages.append({
                    "url": f"https://www.google.com/search?q={row['query']}",
                    "title": row["query"],
                    "snippet": f"{qtype} query · value: {row['value']}",
                })
        return pages[:limit]

    def get_keyword_metrics(self, keyword: str, country: str = "us") -> dict:
        return {
            "overview": self.get_keyword_overview(keyword, country),
            "volume": self.search_volume(keyword, country),
            "difficulty": self.keyword_difficulty(keyword, country),
            "top_pages": self.top_pages(keyword, country=country),
        }

    def competitor_analysis(
        self, keyword: str, country: str = "us"
    ) -> dict[str, Any]:
        """Related queries as competitors."""
        pages = self.top_pages(keyword, country, limit=10)
        queries = [p["title"] for p in pages if p["title"]]
        return {
            "keyword": keyword,
            "related_queries": queries[:5],
            "total_competitors": len(queries),
            "top_pages": pages[:3],
        }

    def serp_features(self, keyword: str, country: str = "us") -> dict:
        return {"source": "pytrends", "note": "SERP features not available via Trends"}

    # ── trends-specific methods ────────────────────────────────────────

    def trending_topics(self, geo: str = "VN", limit: int = 20) -> list[dict]:
        """Get daily trending searches for a country (no keyword input).
        Uses pytrends-modern RSS feed — no rate limit, no API key."""
        try:
            from pytrends_modern import TrendsRSS
            geo_map = {"VN": "vietnam", "US": "united-states", "AU": "australia",
                       "GB": "united-kingdom", "CA": "canada", "DE": "germany",
                       "JP": "japan", "SG": "singapore", "IN": "india"}
            geo_rss = geo_map.get(geo.upper(), geo.lower())
            rss = TrendsRSS()
            trends = rss.get_trends(geo=geo_rss)
            topics = []
            for t in trends[:limit]:
                topics.append({
                    "title": t.get("title", ""),
                    "traffic": t.get("traffic", ""),
                    "source": "rss",
                })
            return topics
        except Exception:
            # Fallback to pytrends
            geo_name = _GEO_MAP.get(geo, geo.upper())
            try:
                df = self._call(lambda: self._pytrends.trending_searches(pn=geo_name.lower()))
                if not df.empty:
                    return [{"title": row.get("title", ""), "source": "trends"}
                            for _, row in df.head(limit).iterrows()]
            except Exception:
                pass
            fallback = _TOP_INTERESTS.get(geo_name, _TOP_INTERESTS["US"])
            return [{"title": t, "source": "fallback"} for t in fallback[:limit]]

    def compare_keywords(
        self, keywords: list[str], geo: str = "US", timeframe: str = "today 12-m"
    ) -> pd.DataFrame:
        """Compare interest for up to 5 keywords. Returns DataFrame."""
        keywords = [self._validate(k) for k in keywords[:5]]
        self._call(
            lambda: self._pytrends.build_payload(
                kw_list=keywords, geo=geo, timeframe=timeframe
            )
        )
        return self._pytrends.interest_over_time()

    def interest_overtime(
        self, keyword: str | list[str], geo: str = "US", timeframe: str = "today 12-m"
    ) -> pd.DataFrame:
        """Get interest-over-time data for one or more keywords."""
        if isinstance(keyword, str):
            keyword = [keyword]
        keyword = [self._validate(k) for k in keyword]
        self._call(
            lambda: self._pytrends.build_payload(
                kw_list=keyword, geo=geo, timeframe=timeframe
            )
        )
        return self._pytrends.interest_over_time()

    def related_queries(
        self, keyword: str, geo: str = "US"
    ) -> dict[str, pd.DataFrame]:
        """Get top + rising related queries."""
        keyword = self._validate(keyword)
        return self._related_queries(keyword, geo)

    def related_topics(
        self, keyword: str, geo: str = "US"
    ) -> dict[str, pd.DataFrame]:
        """Get top + rising related topics."""
        keyword = self._validate(keyword)
        self._call(
            lambda: self._pytrends.build_payload(
                kw_list=[keyword], geo=geo, timeframe="today 12-m"
            )
        )
        return self._pytrends.related_topics()

    # ── helpers ────────────────────────────────────────────────────────

    def _validate(self, keyword: str) -> str:
        if not keyword or not keyword.strip():
            raise InvalidKeywordError(message="Keyword cannot be empty", keyword=keyword)
        return keyword.strip()

    def _interest_over_time(self, keywords: list[str], geo: str) -> pd.DataFrame:
        self._call(
            lambda: self._pytrends.build_payload(
                kw_list=keywords, geo=geo, timeframe="today 12-m"
            )
        )
        return self._pytrends.interest_over_time()

    def _related_queries(
        self, keyword: str, geo: str
    ) -> dict[str, pd.DataFrame]:
        self._call(
            lambda: self._pytrends.build_payload(
                kw_list=[keyword], geo=geo, timeframe="today 12-m"
            )
        )
        raw = self._pytrends.related_queries()
        result: dict[str, pd.DataFrame] = {"top": pd.DataFrame(), "rising": pd.DataFrame()}
        for _, data in raw.items():
            if data.get("top") is not None:
                result["top"] = data["top"]
            if data.get("rising") is not None:
                result["rising"] = data["rising"]
        return result

    def _call(self, fn, retries: int = 0):
        """Execute pytrends call with retry on 429 AND connection errors.

        Google Trends throttles bursts of rapid requests (blocked IP returns
        connection resets, not HTTP 429). Retry both cases — connection errors
        recover after a short cooldown.
        """
        import requests as _requests

        for attempt in range(len(_RETRY_DELAYS) + 1):
            try:
                return fn()
            except Exception as e:
                resp = getattr(e, "response", None)
                code = resp.status_code if resp else 0
                is_conn = isinstance(e, (_requests.exceptions.ConnectionError, _requests.exceptions.Timeout))
                if (code == 429 or is_conn) and attempt < len(_RETRY_DELAYS):
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        f"pytrends {'429' if code == 429 else 'conn error'}, retrying in {delay}s (attempt {attempt+1})"
                    )
                    time.sleep(delay)
                    self._pytrends = TrendReq(hl="en-US", tz=420)
                    continue
                raise
