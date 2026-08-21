"""Error handling decorators and utilities.

Provides decorators for automatic error handling, retry logic with
exponential backoff, and error context tracking.
"""

import functools
import random
import time
from typing import Any, Callable, Type, TypeVar

from blog_automation.alerts import send_alert
from blog_automation.errors import (
    APIError,
    APIRateLimitError,
    APIServerError,
    APITimeoutError,
    AppError,
)
from blog_automation.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def handle_errors(
    error_type: Type[AppError] = AppError,
    alert: bool = False,
    reraise: bool = True,
    default_return: Any = None,
) -> Callable:
    """Decorator for automatic error handling.

    Args:
        error_type: Type of AppError to wrap exceptions in
        alert: Whether to send alerts on error
        reraise: Whether to reraise the exception
        default_return: Value to return if not reraising

    Returns:
        Decorated function

    Example:
        @handle_errors(error_type=ValidationError, alert=True)
        def parse_keyword(keyword: str):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except AppError:
                # Already an AppError, just handle it
                raise
            except Exception as e:
                # Wrap in AppError
                error = error_type(
                    message=str(e),
                    context={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                        "original_error": type(e).__name__,
                    },
                )

                logger.error(
                    f"Error in {func.__name__}: {error.message}",
                    error_code=error.error_code,
                    context=error.context,
                )

                if alert:
                    send_alert(
                        error.error_code,
                        error.message,
                        error.severity,
                        error.context,
                    )

                if reraise:
                    raise error from e
                return default_return

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: tuple[Type[Exception], ...] = (
        APITimeoutError,
        APIServerError,
        APIRateLimitError,
        ConnectionError,
        TimeoutError,
    ),
    on_retry: Callable[[Exception, int], None] | None = None,
) -> Callable:
    """Decorator for retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay between retries in seconds
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Tuple of exceptions to retry on
        on_retry: Optional callback called on each retry

    Returns:
        Decorated function

    Example:
        @retry(max_attempts=3, backoff_factor=2)
        def call_api():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"All {max_attempts} retry attempts failed for {func.__name__}",
                            error=str(e),
                        )
                        raise

                    # Calculate delay
                    delay = min(backoff_factor ** (attempt - 1), max_delay)

                    # Handle rate limit with Retry-After header
                    if isinstance(e, APIRateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)

                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Retry {attempt}/{max_attempts} for {func.__name__} "
                        f"after {delay:.2f}s",
                        error=str(e),
                        attempt=attempt,
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


class RetryStrategy:
    """Configurable retry strategy for API calls.

    Provides fine-grained control over retry behavior including
    exponential backoff, jitter, and custom predicates.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if the operation should be retried.

        Args:
            exception: The exception that was raised
            attempt: Current attempt number (1-indexed)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_attempts:
            return False

        # Don't retry authentication errors
        if isinstance(exception, APIError):
            if exception.status_code in [401, 403]:
                return False

        # Retry on server errors, timeouts, rate limits
        retryable = (
            APITimeoutError,
            APIServerError,
            APIRateLimitError,
            ConnectionError,
            TimeoutError,
        )
        return isinstance(exception, retryable)

    def get_wait_time(self, attempt: int, exception: Exception | None = None) -> float:
        """Calculate wait time before next retry.

        Args:
            attempt: Current attempt number (1-indexed)
            exception: The exception that was raised

        Returns:
            Wait time in seconds
        """
        delay = min(self.backoff_factor ** (attempt - 1), self.max_delay)

        # Respect Retry-After header
        if isinstance(exception, APIRateLimitError) and exception.retry_after:
            delay = max(delay, exception.retry_after)

        # Add jitter
        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if not self.should_retry(e, attempt):
                    raise

                if attempt < self.max_attempts:
                    wait_time = self.get_wait_time(attempt, e)
                    logger.warning(
                        f"Retry {attempt}/{self.max_attempts} after {wait_time:.2f}s",
                        error=str(e),
                    )
                    time.sleep(wait_time)

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry loop exit")


class ErrorContext:
    """Context manager for tracking error context.

    Provides a way to add context to errors that occur within a block.

    Example:
        with ErrorContext(operation="keyword_research", keyword="python"):
            # Any errors here will include the context
            research_keyword(keyword)
    """

    _context: dict[str, Any] = {}

    def __init__(self, **context: Any):
        self.context = context
        self._previous: dict[str, Any] = {}

    def __enter__(self) -> "ErrorContext":
        self._previous = ErrorContext._context.copy()
        ErrorContext._context.update(self.context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        ErrorContext._context = self._previous

        if exc_val is not None and isinstance(exc_val, AppError):
            exc_val.context.update(self.context)

        return False  # Don't suppress exceptions

    @classmethod
    def get_context(cls) -> dict[str, Any]:
        """Get current error context."""
        return cls._context.copy()
