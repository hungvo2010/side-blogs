"""Base HTTP client with retry logic and rate limiting.

Provides a foundation for all API client integrations with:
- Automatic retry with exponential backoff
- Rate limit handling
- Request/response logging
- Timeout management
"""

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from blog_automation.errors import (
    APIAuthenticationError,
    APIConnectionError,
    APIInvalidResponseError,
    APIRateLimitError,
    APIServerError,
    APITimeoutError,
)
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class RateLimitHandler:
    """Handles rate limiting for API calls."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times: list[float] = []
        self.retry_after: float | None = None

    def check_limit(self) -> bool:
        """Check if we're within rate limits.

        Returns:
            True if request can proceed
        """
        now = time.time()

        # Clean old requests (older than 1 minute)
        self.request_times = [t for t in self.request_times if now - t < 60]

        # Check if we're at the limit
        if len(self.request_times) >= self.requests_per_minute:
            return False

        return True

    def wait_if_limited(self) -> None:
        """Wait if rate limited."""
        if self.retry_after:
            logger.warning(f"Rate limited, waiting {self.retry_after}s")
            time.sleep(self.retry_after)
            self.retry_after = None
            return

        if not self.check_limit():
            # Wait until oldest request expires
            wait_time = 60 - (time.time() - self.request_times[0])
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                time.sleep(wait_time)

    def record_request(self) -> None:
        """Record a request timestamp."""
        self.request_times.append(time.time())

    def update_from_headers(self, headers: dict) -> None:
        """Update rate limit info from response headers.

        Args:
            headers: Response headers
        """
        if "Retry-After" in headers:
            self.retry_after = float(headers["Retry-After"])
        elif "X-RateLimit-Reset" in headers:
            reset_time = float(headers["X-RateLimit-Reset"])
            self.retry_after = max(0, reset_time - time.time())


class HTTPClient:
    """Base HTTP client with retry logic and error handling.

    Provides a foundation for all API integrations with:
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Request/response logging (without secrets)
    - Timeout management
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        rate_limit: int = 60,
    ):
        """Initialize HTTP client.

        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            backoff_factor: Exponential backoff multiplier
            rate_limit: Requests per minute limit
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.rate_limiter = RateLimitHandler(rate_limit)

        # Setup session with retry adapter
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Default headers
        self.session.headers.update(
            {
                "User-Agent": "BlogAutomation/1.0",
                "Accept": "application/json",
            }
        )

    def set_auth_header(self, header_name: str, value: str) -> None:
        """Set authentication header.

        Args:
            header_name: Header name (e.g., "Authorization")
            value: Header value (e.g., "Bearer token")
        """
        self.session.headers[header_name] = value

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
        data: Any = None,
        headers: dict | None = None,
        timeout: int | None = None,
    ) -> dict | list | str:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (appended to base_url)
            params: Query parameters
            json: JSON body
            data: Form data
            headers: Additional headers
            timeout: Request timeout override

        Returns:
            Response data (parsed JSON or text)

        Raises:
            APITimeoutError: Request timed out
            APIRateLimitError: Rate limit exceeded
            APIAuthenticationError: Authentication failed
            APIServerError: Server error (5xx)
            APIInvalidResponseError: Invalid response
            APIConnectionError: Connection failed
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_timeout = timeout or self.timeout

        # Check rate limit
        self.rate_limiter.wait_if_limited()

        # Log request (without sensitive data)
        logger.debug(
            f"API Request: {method} {endpoint}",
            params=params,
            has_body=bool(json or data),
        )

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                timeout=request_timeout,
            )

            # Record request for rate limiting
            self.rate_limiter.record_request()
            self.rate_limiter.update_from_headers(dict(response.headers))

            # Log response
            logger.debug(
                f"API Response: {response.status_code}",
                endpoint=endpoint,
                duration_ms=response.elapsed.total_seconds() * 1000,
            )

            # Handle errors
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", 60)
                raise APIRateLimitError(
                    message="Rate limit exceeded",
                    service=self.base_url,
                    retry_after=int(retry_after),
                )

            if response.status_code in [401, 403]:
                raise APIAuthenticationError(
                    message=f"Authentication failed: {response.text[:200]}",
                    service=self.base_url,
                )

            if response.status_code >= 500:
                raise APIServerError(
                    message=f"Server error: {response.text[:200]}",
                    service=self.base_url,
                    status_code=response.status_code,
                )

            if response.status_code >= 400:
                raise APIInvalidResponseError(
                    message=f"Request failed ({response.status_code}): {response.text[:200]}",
                    service=self.base_url,
                    context={"status_code": response.status_code},
                )

            # Parse response
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return response.json()
            return response.text

        except requests.Timeout as e:
            raise APITimeoutError(
                message=f"Request timed out after {request_timeout}s",
                service=self.base_url,
                context={"endpoint": endpoint},
            ) from e

        except requests.ConnectionError as e:
            raise APIConnectionError(
                message=f"Connection failed: {str(e)[:200]}",
                service=self.base_url,
            ) from e

    def get(
        self,
        endpoint: str,
        params: dict | None = None,
        **kwargs,
    ) -> dict | list | str:
        """Make a GET request."""
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        json: dict | None = None,
        data: Any = None,
        **kwargs,
    ) -> dict | list | str:
        """Make a POST request."""
        return self.request("POST", endpoint, json=json, data=data, **kwargs)

    def put(
        self,
        endpoint: str,
        json: dict | None = None,
        **kwargs,
    ) -> dict | list | str:
        """Make a PUT request."""
        return self.request("PUT", endpoint, json=json, **kwargs)

    def delete(
        self,
        endpoint: str,
        **kwargs,
    ) -> dict | list | str:
        """Make a DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self) -> "HTTPClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
