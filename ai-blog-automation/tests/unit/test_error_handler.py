"""Unit tests for error handler decorators."""

import pytest
import time

from blog_automation.error_handler import (
    ErrorContext,
    RetryStrategy,
    handle_errors,
    retry,
)
from blog_automation.errors import (
    APIRateLimitError,
    APIServerError,
    APITimeoutError,
    AppError,
    ValidationError,
)


class TestHandleErrorsDecorator:
    """Tests for @handle_errors decorator."""

    def test_successful_function(self):
        """Test decorator with successful function."""

        @handle_errors()
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_catches_exception(self):
        """Test decorator catches and wraps exceptions."""

        @handle_errors(error_type=ValidationError, reraise=True)
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValidationError) as exc_info:
            failing_func()

        assert "Test error" in str(exc_info.value)

    def test_returns_default_on_error(self):
        """Test decorator returns default when not reraising."""

        @handle_errors(reraise=False, default_return={"error": True})
        def failing_func():
            raise ValueError("Test error")

        result = failing_func()
        assert result == {"error": True}

    def test_preserves_app_error(self):
        """Test decorator preserves AppError subclasses."""

        @handle_errors()
        def app_error_func():
            raise ValidationError("Validation failed")

        with pytest.raises(ValidationError):
            app_error_func()

    def test_includes_context(self):
        """Test decorator includes function context in error."""

        @handle_errors(error_type=ValidationError, reraise=True)
        def context_func(arg1, kwarg1=None):
            raise ValueError("Test")

        with pytest.raises(ValidationError) as exc_info:
            context_func("test_arg", kwarg1="test_kwarg")

        assert "context_func" in exc_info.value.context["function"]


class TestRetryDecorator:
    """Tests for @retry decorator."""

    def test_successful_first_attempt(self):
        """Test retry with successful first attempt."""
        call_count = 0

        @retry(max_attempts=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Test retry attempts on failure."""
        call_count = 0

        @retry(max_attempts=3, backoff_factor=0.01)
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APITimeoutError("Timeout")
            return "success"

        result = sometimes_fails()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test exception raised after max retries."""
        call_count = 0

        @retry(max_attempts=3, backoff_factor=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise APITimeoutError("Timeout")

        with pytest.raises(APITimeoutError):
            always_fails()

        assert call_count == 3

    def test_no_retry_on_non_retryable(self):
        """Test no retry on non-retryable exceptions."""
        call_count = 0

        @retry(max_attempts=3, retryable_exceptions=(APITimeoutError,))
        def non_retryable():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            non_retryable()

        assert call_count == 1

    def test_rate_limit_retry_after(self):
        """Test retry respects rate limit retry_after."""
        call_count = 0
        start_time = time.time()

        @retry(max_attempts=2, backoff_factor=0.01)
        def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise APIRateLimitError(retry_after=0.1)
            return "success"

        result = rate_limited()
        elapsed = time.time() - start_time

        assert result == "success"
        assert elapsed >= 0.1


class TestRetryStrategy:
    """Tests for RetryStrategy class."""

    def test_should_retry_timeout(self):
        """Test should_retry for timeout errors."""
        strategy = RetryStrategy(max_attempts=3)
        error = APITimeoutError("Timeout")

        assert strategy.should_retry(error, 1) is True
        assert strategy.should_retry(error, 2) is True
        assert strategy.should_retry(error, 3) is False

    def test_should_not_retry_auth_error(self):
        """Test should_retry returns False for auth errors."""
        from blog_automation.errors import APIAuthenticationError

        strategy = RetryStrategy(max_attempts=3)
        error = APIAuthenticationError("Auth failed")

        assert strategy.should_retry(error, 1) is False

    def test_get_wait_time_exponential(self):
        """Test exponential backoff calculation."""
        strategy = RetryStrategy(backoff_factor=2.0, jitter=False)

        wait1 = strategy.get_wait_time(1)
        wait2 = strategy.get_wait_time(2)
        wait3 = strategy.get_wait_time(3)

        assert wait1 == 1.0  # 2^0
        assert wait2 == 2.0  # 2^1
        assert wait3 == 4.0  # 2^2

    def test_get_wait_time_max_delay(self):
        """Test max delay is respected."""
        strategy = RetryStrategy(backoff_factor=2.0, max_delay=5.0, jitter=False)

        wait = strategy.get_wait_time(10)  # Would be 512 without max
        assert wait == 5.0

    def test_get_wait_time_with_jitter(self):
        """Test jitter adds variation."""
        strategy = RetryStrategy(backoff_factor=2.0, jitter=True)

        waits = [strategy.get_wait_time(2) for _ in range(10)]

        # With jitter, not all waits should be identical
        assert len(set(waits)) > 1

    def test_execute_success(self):
        """Test execute with successful function."""
        strategy = RetryStrategy(max_attempts=3)

        def success():
            return "success"

        result = strategy.execute(success)
        assert result == "success"

    def test_execute_with_retry(self):
        """Test execute with retries."""
        strategy = RetryStrategy(max_attempts=3, backoff_factor=0.01)
        call_count = 0

        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIServerError("Server error")
            return "success"

        result = strategy.execute(sometimes_fails)
        assert result == "success"
        assert call_count == 2


class TestErrorContext:
    """Tests for ErrorContext context manager."""

    def test_context_added_to_error(self):
        """Test context is added to errors."""
        with pytest.raises(AppError) as exc_info:
            with ErrorContext(operation="test", keyword="python"):
                raise AppError("Test error")

        assert exc_info.value.context["operation"] == "test"
        assert exc_info.value.context["keyword"] == "python"

    def test_context_restored_after_block(self):
        """Test context is restored after block."""
        with ErrorContext(operation="outer"):
            with ErrorContext(operation="inner"):
                ctx = ErrorContext.get_context()
                assert ctx["operation"] == "inner"

            ctx = ErrorContext.get_context()
            assert ctx["operation"] == "outer"

    def test_nested_context(self):
        """Test nested context managers."""
        with ErrorContext(level1="a"):
            with ErrorContext(level2="b"):
                ctx = ErrorContext.get_context()
                assert ctx["level1"] == "a"
                assert ctx["level2"] == "b"

    def test_exception_not_suppressed(self):
        """Test exceptions are not suppressed."""
        with pytest.raises(ValueError):
            with ErrorContext(operation="test"):
                raise ValueError("Test")
