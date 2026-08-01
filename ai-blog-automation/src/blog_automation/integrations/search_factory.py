"""Keyword research client factory — switches between providers via config.

Set ``SEARCH_PROVIDER=google`` or ``SEARCH_PROVIDER=ahrefs`` in .env.
"""

from blog_automation.config import get_settings
from blog_automation.errors import ConfigurationError
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


def get_search_client():
    """Return the configured keyword research client.

    Returns:
        AhrefsClient or GoogleSearchClient instance matching SEARCH_PROVIDER.
    """
    settings = get_settings()
    provider = settings.search_provider.lower()

    if provider == "ahrefs":
        from blog_automation.integrations.ahrefs_client import AhrefsClient

        if not settings.ahrefs_api_key:
            raise ConfigurationError(
                "AHREFS_API_KEY required when SEARCH_PROVIDER=ahrefs"
            )
        logger.info("Using Ahrefs for keyword research")
        return AhrefsClient()

    if provider == "google":
        from blog_automation.integrations.google_search_client import (
            GoogleSearchClient,
        )

        if not settings.google_search_api_key or not settings.google_search_engine_id:
            raise ConfigurationError(
                "GOOGLE_SEARCH_API_KEY + GOOGLE_SEARCH_ENGINE_ID required "
                "when SEARCH_PROVIDER=google"
            )
        logger.info("Using Google Custom Search for keyword research (free tier)")
        return GoogleSearchClient()

    raise ConfigurationError(
        f"Unknown SEARCH_PROVIDER: {provider}. Use 'ahrefs' or 'google'."
    )
