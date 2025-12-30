"""Perplexity API client for web search and evidence retrieval.

Provides web search capabilities for fact-checking and research.
"""

from typing import Any

from blog_automation.config import get_settings
from blog_automation.errors import APIAuthenticationError
from blog_automation.integrations.base_client import HTTPClient
from blog_automation.integrations.cache import get_cache
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class PerplexityClient(HTTPClient):
    """Perplexity API client for web search.

    Provides methods for:
    - Web search with source citations
    - Evidence retrieval for fact-checking
    """

    BASE_URL = "https://api.perplexity.ai"

    def __init__(self, api_key: str | None = None):
        """Initialize Perplexity client.

        Args:
            api_key: Perplexity API key
        """
        settings = get_settings()
        self.api_key = api_key or settings.perplexity_api_key

        if not self.api_key:
            raise APIAuthenticationError(
                message="Perplexity API key not configured",
                service="perplexity",
            )

        super().__init__(
            base_url=self.BASE_URL,
            timeout=60,
            max_retries=3,
            rate_limit=20,
        )

        self.set_auth_header("Authorization", f"Bearer {self.api_key}")
        self.cache = get_cache()
        logger.info("Perplexity client initialized")

    def search(
        self,
        query: str,
        source_count: int = 5,
        focus: str = "internet",
    ) -> dict[str, Any]:
        """Search the web for information.

        Args:
            query: Search query
            source_count: Number of sources to return
            focus: Search focus (internet, academic, news)

        Returns:
            Dict with answer and sources
        """
        # Check cache
        cache_key = f"perplexity:{query}:{focus}"
        cached = self.cache.get_cached(cache_key, "search_results")
        if cached:
            return cached

        response = self.post(
            "chat/completions",
            json={
                "model": "pplx-7b-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a research assistant. Provide accurate, well-sourced information.",
                    },
                    {"role": "user", "content": query},
                ],
                "max_tokens": 1024,
                "temperature": 0.2,
                "return_citations": True,
            },
        )

        # Extract answer and sources
        answer = ""
        sources = []

        if "choices" in response and response["choices"]:
            answer = response["choices"][0].get("message", {}).get("content", "")

        if "citations" in response:
            for i, citation in enumerate(response["citations"][:source_count]):
                sources.append(
                    {
                        "url": citation.get("url", ""),
                        "title": citation.get("title", ""),
                        "snippet": citation.get("snippet", ""),
                        "position": i + 1,
                    }
                )

        result = {
            "query": query,
            "answer": answer,
            "sources": sources,
            "source_count": len(sources),
        }

        self.cache.set_cache(cache_key, result, "search_results")
        return result

    def get_evidence(
        self,
        claim: str,
        source_count: int = 3,
    ) -> dict[str, Any]:
        """Get evidence for a factual claim.

        Args:
            claim: Claim to find evidence for
            source_count: Number of sources

        Returns:
            Dict with evidence and sources
        """
        query = f"What is the evidence for: {claim}"
        return self.search(query, source_count=source_count)

    def verify_fact(
        self,
        fact: str,
    ) -> dict[str, Any]:
        """Verify a factual statement.

        Args:
            fact: Fact to verify

        Returns:
            Dict with verification result
        """
        query = f"Is this statement accurate? Provide sources: {fact}"
        result = self.search(query, source_count=3)

        # Add verification metadata
        result["fact"] = fact
        result["verified"] = len(result.get("sources", [])) > 0

        return result
