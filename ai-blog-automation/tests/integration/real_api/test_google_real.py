"""Real API integration tests for Google Analytics 4 + Search Console
(phase: analytics/metrics tracking).

Requires: GOOGLE_ANALYTICS_PROPERTY_ID / GOOGLE_SEARCH_CONSOLE_SITE_URL
plus GOOGLE_SERVICE_ACCOUNT_JSON pointing at an existing service-account file.
Also needs the optional deps: google-analytics-data, google-api-python-client.

Run with: RUN_REAL_API_TESTS=1 pytest tests/integration/real_api/test_google_real.py
"""

import pytest

from . import require_creds, service_account_path, settings

_sa_file = service_account_path()

pytestmark = [pytest.mark.real_api]


@pytest.fixture(scope="module")
def ga_client():
    pytest.importorskip(
        "google.analytics.data_v1beta",
        reason="google-analytics-data not installed (poetry install -E google)",
    )
    from blog_automation.integrations.google_analytics_client import (
        GoogleAnalyticsClient,
    )

    return GoogleAnalyticsClient()


@pytest.fixture(scope="module")
def gsc_client():
    pytest.importorskip(
        "googleapiclient.discovery",
        reason="google-api-python-client not installed (poetry install -E google)",
    )
    from blog_automation.integrations.google_analytics_client import (
        SearchConsoleClient,
    )

    return SearchConsoleClient()


@pytest.mark.google_analytics
@require_creds("google_analytics", settings.google_analytics_property_id, _sa_file)
def test_ga4_client_initializes(ga_client):
    """GA4 client initializes with real service-account credentials."""
    assert ga_client._initialized, (
        "GA4 client failed to initialize — check service account JSON "
        "and that the SA has access to the GA4 property"
    )


@pytest.mark.google_analytics
@require_creds("google_analytics", settings.google_analytics_property_id, _sa_file)
def test_ga4_get_metrics_returns_structure(ga_client):
    """Metrics query for a page path returns a structured dict (may be zero rows)."""
    result = ga_client.get_metrics("/")

    assert isinstance(result, dict)


@pytest.mark.search_console
@require_creds(
    "search_console", settings.google_search_console_site_url, _sa_file
)
def test_gsc_client_initializes(gsc_client):
    """GSC client initializes with real service-account credentials."""
    assert gsc_client._initialized, (
        "GSC client failed to initialize — check service account JSON "
        "and that the SA is a user of the Search Console property"
    )


@pytest.mark.search_console
@require_creds(
    "search_console", settings.google_search_console_site_url, _sa_file
)
def test_gsc_get_search_metrics_returns_structure(gsc_client):
    """Search-metrics query returns a structured dict (may be zero rows)."""
    result = gsc_client.get_search_metrics(settings.google_search_console_site_url)

    assert isinstance(result, dict)
