"""Copyscape API client for plagiarism detection.

Provides plagiarism checking for article content.
"""

from typing import Any

from blog_automation.config import get_settings
from blog_automation.errors import APIAuthenticationError
from blog_automation.integrations.base_client import HTTPClient
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class CopyscapeClient(HTTPClient):
    """Copyscape API client for plagiarism detection.

    Provides methods for:
    - Plagiarism checking
    - Duplicate content detection
    """

    BASE_URL = "https://www.copyscape.com/api"

    def __init__(
        self,
        api_key: str | None = None,
        username: str | None = None,
    ):
        """Initialize Copyscape client.

        Args:
            api_key: Copyscape API key
            username: Copyscape username
        """
        settings = get_settings()
        self.api_key = api_key or settings.copyscape_api_key
        self.username = username or settings.copyscape_username

        if not self.api_key or not self.username:
            raise APIAuthenticationError(
                message="Copyscape credentials not configured",
                service="copyscape",
            )

        super().__init__(
            base_url=self.BASE_URL,
            timeout=60,
            max_retries=2,
            rate_limit=10,
        )

        logger.info("Copyscape client initialized")

    def check_plagiarism(
        self,
        content: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Check content for plagiarism.

        Args:
            content: Content to check
            title: Optional title

        Returns:
            Dict with plagiarism results
        """
        # Copyscape uses form data
        data = {
            "u": self.username,
            "o": self.api_key,
            "t": content[:25000],  # Copyscape limit
            "f": "json",
        }

        if title:
            data["a"] = title

        response = self.post("", data=data)

        # Parse response
        matches = []
        total_percent = 0.0

        if "result" in response:
            for match in response.get("result", []):
                match_data = {
                    "url": match.get("url", ""),
                    "title": match.get("title", ""),
                    "percent_matched": float(match.get("percentmatched", 0)),
                    "words_matched": int(match.get("wordsmatched", 0)),
                    "snippet": match.get("textsnippet", ""),
                }
                matches.append(match_data)
                total_percent = max(total_percent, match_data["percent_matched"])

        result = {
            "plagiarism_percent": total_percent,
            "matches": matches,
            "match_count": len(matches),
            "is_original": total_percent < 3.0,  # <3% threshold
            "words_checked": len(content.split()),
        }

        logger.info(
            "Plagiarism check complete",
            percent=total_percent,
            matches=len(matches),
        )

        return result

    def check_url(self, url: str) -> dict[str, Any]:
        """Check a URL for plagiarism.

        Args:
            url: URL to check

        Returns:
            Dict with plagiarism results
        """
        data = {
            "u": self.username,
            "o": self.api_key,
            "q": url,
            "f": "json",
        }

        response = self.post("", data=data)

        matches = []
        for match in response.get("result", []):
            matches.append(
                {
                    "url": match.get("url", ""),
                    "title": match.get("title", ""),
                    "percent_matched": float(match.get("percentmatched", 0)),
                }
            )

        return {
            "url": url,
            "matches": matches,
            "match_count": len(matches),
        }

    def get_credits(self) -> int:
        """Get remaining API credits.

        Returns:
            Number of credits remaining
        """
        data = {
            "u": self.username,
            "o": self.api_key,
            "f": "json",
            "c": "1",  # Credit check
        }

        response = self.post("", data=data)
        return int(response.get("value", 0))
