"""Google Analytics 4 API client for performance tracking.

Provides GA4 integration for retrieving article performance metrics.
"""

from datetime import date, timedelta
from typing import Any

from blog_automation.config import get_settings
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class GoogleAnalyticsClient:
    """Google Analytics 4 API client.

    Provides methods for:
    - Retrieving page metrics
    - Getting engagement data
    - Tracking article performance
    """

    def __init__(
        self,
        property_id: str | None = None,
        service_account_json: str | None = None,
    ):
        """Initialize GA4 client.

        Args:
            property_id: GA4 property ID
            service_account_json: Path to service account JSON
        """
        settings = get_settings()
        self.property_id = property_id or settings.google_analytics_property_id
        self.service_account_json = (
            service_account_json or settings.google_service_account_json
        )

        self._client = None
        self._initialized = False

        if self.property_id and self.service_account_json:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the GA4 client with credentials."""
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_json,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )

            self._client = BetaAnalyticsDataClient(credentials=credentials)
            self._initialized = True
            logger.info("GA4 client initialized", property_id=self.property_id)

        except ImportError:
            logger.warning(
                "Google Analytics libraries not installed. "
                "Install with: pip install google-analytics-data"
            )
        except Exception as e:
            logger.error(f"Failed to initialize GA4 client: {e}")

    def get_metrics(
        self,
        page_path: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get metrics for a specific page.

        Args:
            page_path: Page path (e.g., /blog/article-slug)
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)

        Returns:
            Dict with page metrics
        """
        if not self._initialized:
            return self._mock_metrics(page_path)

        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        try:
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Filter,
                FilterExpression,
                Metric,
                RunReportRequest,
            )

            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[Dimension(name="pagePath")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="totalUsers"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="bounceRate"),
                    Metric(name="engagementRate"),
                ],
                date_ranges=[
                    DateRange(
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                    )
                ],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="pagePath",
                        string_filter=Filter.StringFilter(
                            match_type=Filter.StringFilter.MatchType.EXACT,
                            value=page_path,
                        ),
                    )
                ),
            )

            response = self._client.run_report(request)

            if response.rows:
                row = response.rows[0]
                return {
                    "page_path": page_path,
                    "views": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                    "avg_session_duration": float(row.metric_values[2].value),
                    "bounce_rate": float(row.metric_values[3].value),
                    "engagement_rate": float(row.metric_values[4].value),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                }

            return {
                "page_path": page_path,
                "views": 0,
                "users": 0,
                "avg_session_duration": 0,
                "bounce_rate": 0,
                "engagement_rate": 0,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get GA4 metrics: {e}")
            return self._mock_metrics(page_path)

    def get_daily_metrics(
        self,
        page_path: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get daily metrics for a page.

        Args:
            page_path: Page path
            days: Number of days to retrieve

        Returns:
            List of daily metric records
        """
        if not self._initialized:
            return []

        try:
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Filter,
                FilterExpression,
                Metric,
                RunReportRequest,
            )

            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="date"),
                    Dimension(name="pagePath"),
                ],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="totalUsers"),
                    Metric(name="bounceRate"),
                ],
                date_ranges=[
                    DateRange(
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                    )
                ],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="pagePath",
                        string_filter=Filter.StringFilter(
                            match_type=Filter.StringFilter.MatchType.EXACT,
                            value=page_path,
                        ),
                    )
                ),
            )

            response = self._client.run_report(request)

            results = []
            for row in response.rows:
                results.append(
                    {
                        "date": row.dimension_values[0].value,
                        "views": int(row.metric_values[0].value),
                        "users": int(row.metric_values[1].value),
                        "bounce_rate": float(row.metric_values[2].value),
                    }
                )

            return sorted(results, key=lambda x: x["date"])

        except Exception as e:
            logger.error(f"Failed to get daily GA4 metrics: {e}")
            return []

    def _mock_metrics(self, page_path: str) -> dict[str, Any]:
        """Return mock metrics when GA4 is not configured.

        Args:
            page_path: Page path

        Returns:
            Mock metrics dict
        """
        return {
            "page_path": page_path,
            "views": 0,
            "users": 0,
            "avg_session_duration": 0,
            "bounce_rate": 0,
            "engagement_rate": 0,
            "mock": True,
        }


class SearchConsoleClient:
    """Google Search Console API client.

    Provides methods for:
    - Search performance data
    - Keyword rankings
    - Click-through rates
    """

    def __init__(
        self,
        site_url: str | None = None,
        service_account_json: str | None = None,
    ):
        """Initialize GSC client.

        Args:
            site_url: Site URL in GSC
            service_account_json: Path to service account JSON
        """
        settings = get_settings()
        self.site_url = site_url or settings.google_search_console_site_url
        self.service_account_json = (
            service_account_json or settings.google_service_account_json
        )

        self._service = None
        self._initialized = False

        if self.site_url and self.service_account_json:
            self._initialize_service()

    def _initialize_service(self) -> None:
        """Initialize the GSC service."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_json,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
            )

            self._service = build("searchconsole", "v1", credentials=credentials)
            self._initialized = True
            logger.info("GSC client initialized", site_url=self.site_url)

        except ImportError:
            logger.warning(
                "Google API libraries not installed. "
                "Install with: pip install google-api-python-client"
            )
        except Exception as e:
            logger.error(f"Failed to initialize GSC client: {e}")

    def get_search_metrics(
        self,
        page_url: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get search metrics for a page.

        Args:
            page_url: Full page URL
            start_date: Start date
            end_date: End date

        Returns:
            Search metrics dict
        """
        if not self._initialized:
            return self._mock_search_metrics(page_url)

        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        try:
            request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["page"],
                "dimensionFilterGroups": [
                    {
                        "filters": [
                            {
                                "dimension": "page",
                                "operator": "equals",
                                "expression": page_url,
                            }
                        ]
                    }
                ],
            }

            response = (
                self._service.searchanalytics()
                .query(siteUrl=self.site_url, body=request)
                .execute()
            )

            if "rows" in response and response["rows"]:
                row = response["rows"][0]
                return {
                    "page_url": page_url,
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": row.get("ctr", 0) * 100,
                    "position": row.get("position", 0),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                }

            return self._mock_search_metrics(page_url)

        except Exception as e:
            logger.error(f"Failed to get GSC metrics: {e}")
            return self._mock_search_metrics(page_url)

    def get_top_queries(
        self,
        page_url: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get top search queries for a page.

        Args:
            page_url: Full page URL
            limit: Number of queries to return

        Returns:
            List of query data
        """
        if not self._initialized:
            return []

        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

            request = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["query"],
                "dimensionFilterGroups": [
                    {
                        "filters": [
                            {
                                "dimension": "page",
                                "operator": "equals",
                                "expression": page_url,
                            }
                        ]
                    }
                ],
                "rowLimit": limit,
            }

            response = (
                self._service.searchanalytics()
                .query(siteUrl=self.site_url, body=request)
                .execute()
            )

            queries = []
            for row in response.get("rows", []):
                queries.append(
                    {
                        "query": row["keys"][0],
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0),
                        "ctr": row.get("ctr", 0) * 100,
                        "position": row.get("position", 0),
                    }
                )

            return queries

        except Exception as e:
            logger.error(f"Failed to get top queries: {e}")
            return []

    def _mock_search_metrics(self, page_url: str) -> dict[str, Any]:
        """Return mock metrics when GSC is not configured.

        Args:
            page_url: Page URL

        Returns:
            Mock metrics dict
        """
        return {
            "page_url": page_url,
            "clicks": 0,
            "impressions": 0,
            "ctr": 0,
            "position": 0,
            "mock": True,
        }
