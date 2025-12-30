"""External API integrations package."""

from blog_automation.integrations.base_client import HTTPClient, RateLimitHandler
from blog_automation.integrations.cache import CacheManager, get_cache
from blog_automation.integrations.openai_client import OpenAIClient
from blog_automation.integrations.claude_client import ClaudeClient
from blog_automation.integrations.ahrefs_client import AhrefsClient
from blog_automation.integrations.perplexity_client import PerplexityClient
from blog_automation.integrations.copyscape_client import CopyscapeClient
from blog_automation.integrations.rankmath_client import RankMathClient
from blog_automation.integrations.wordpress_client import WordPressClient
from blog_automation.integrations.google_analytics_client import (
    GoogleAnalyticsClient,
    SearchConsoleClient,
)

__all__ = [
    "HTTPClient",
    "RateLimitHandler",
    "CacheManager",
    "get_cache",
    "OpenAIClient",
    "ClaudeClient",
    "AhrefsClient",
    "PerplexityClient",
    "CopyscapeClient",
    "RankMathClient",
    "WordPressClient",
    "GoogleAnalyticsClient",
    "SearchConsoleClient",
]
