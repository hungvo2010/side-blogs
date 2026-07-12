"""Unit tests for error classes."""

from blog_automation.errors import (
    APIAuthenticationError,
    APIRateLimitError,
    APIServerError,
    APITimeoutError,
    AppError,
    ConfigurationError,
    ConstraintViolationError,
    DatabaseConnectionError,
    ErrorCode,
    GenerationFailureError,
    InvalidArticleError,
    InvalidBriefError,
    InvalidKeywordError,
    MissingFieldError,
    NotFoundError,
    ProcessingError,
    PublishingFailureError,
    Severity,
    VerificationFailureError,
)


class TestAppError:
    """Tests for base AppError class."""

    def test_create_basic_error(self):
        """Test creating a basic error."""
        error = AppError("Test error message")
        assert error.message == "Test error message"
        assert error.error_code == "unknown"
        assert error.severity == Severity.ERROR.value

    def test_create_error_with_code(self):
        """Test creating error with error code."""
        error = AppError(
            "Test error",
            error_code=ErrorCode.API_TIMEOUT,
            severity=Severity.WARNING,
        )
        assert error.error_code == "api_001"
        assert error.severity == "warning"

    def test_error_to_dict(self):
        """Test error serialization to dict."""
        error = AppError(
            "Test error",
            error_code=ErrorCode.API_TIMEOUT,
            context={"service": "openai"},
        )
        result = error.to_dict()

        assert result["error_type"] == "AppError"
        assert result["message"] == "Test error"
        assert result["error_code"] == "api_001"
        assert result["context"]["service"] == "openai"
        assert "timestamp" in result

    def test_error_str(self):
        """Test error string representation."""
        error = AppError("Test error", error_code=ErrorCode.API_TIMEOUT)
        assert str(error) == "[api_001] Test error"

    def test_error_repr(self):
        """Test error repr."""
        error = AppError("Test error", error_code=ErrorCode.API_TIMEOUT)
        repr_str = repr(error)
        assert "AppError" in repr_str
        assert "Test error" in repr_str


class TestAPIErrors:
    """Tests for API error classes."""

    def test_api_timeout_error(self):
        """Test APITimeoutError."""
        error = APITimeoutError(service="openai")
        assert error.error_code == "api_001"
        assert error.service == "openai"
        assert error.context["service"] == "openai"

    def test_api_rate_limit_error(self):
        """Test APIRateLimitError with retry_after."""
        error = APIRateLimitError(service="openai", retry_after=60)
        assert error.error_code == "api_002"
        assert error.retry_after == 60
        assert error.status_code == 429
        assert error.severity == "warning"

    def test_api_auth_error(self):
        """Test APIAuthenticationError."""
        error = APIAuthenticationError(service="openai")
        assert error.error_code == "api_003"
        assert error.severity == "critical"
        assert error.status_code == 401

    def test_api_server_error(self):
        """Test APIServerError."""
        error = APIServerError(service="openai", status_code=503)
        assert error.error_code == "api_005"
        assert error.status_code == 503


class TestValidationErrors:
    """Tests for validation error classes."""

    def test_invalid_keyword_error(self):
        """Test InvalidKeywordError."""
        error = InvalidKeywordError(keyword="test")
        assert error.error_code == "val_001"
        assert error.context["keyword"] == "test"

    def test_invalid_brief_error(self):
        """Test InvalidBriefError."""
        error = InvalidBriefError(missing_fields=["sections", "sources"])
        assert error.error_code == "val_002"
        assert "sections" in error.context["missing_fields"]

    def test_invalid_article_error(self):
        """Test InvalidArticleError."""
        error = InvalidArticleError(issues=["Too short", "Missing keyword"])
        assert error.error_code == "val_003"
        assert len(error.context["issues"]) == 2

    def test_missing_field_error(self):
        """Test MissingFieldError."""
        error = MissingFieldError("title")
        assert error.error_code == "val_004"
        assert error.field == "title"
        assert "title" in error.message


class TestProcessingErrors:
    """Tests for processing error classes."""

    def test_generation_failure_error(self):
        """Test GenerationFailureError."""
        error = GenerationFailureError(step="drafting")
        assert error.error_code == "proc_001"
        assert error.step == "drafting"

    def test_verification_failure_error(self):
        """Test VerificationFailureError."""
        error = VerificationFailureError(step="fact_checking")
        assert error.error_code == "proc_002"

    def test_publishing_failure_error(self):
        """Test PublishingFailureError."""
        error = PublishingFailureError(step="wordpress")
        assert error.error_code == "proc_003"


class TestDatabaseErrors:
    """Tests for database error classes."""

    def test_database_connection_error(self):
        """Test DatabaseConnectionError."""
        error = DatabaseConnectionError()
        assert error.error_code == "db_001"
        assert error.severity == "critical"

    def test_constraint_violation_error(self):
        """Test ConstraintViolationError."""
        error = ConstraintViolationError(constraint="unique_slug")
        assert error.error_code == "db_002"
        assert error.context["constraint"] == "unique_slug"

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError(model="Article", id=123)
        assert error.error_code == "db_003"
        assert error.context["model"] == "Article"
        assert error.context["id"] == 123


class TestConfigurationError:
    """Tests for configuration error."""

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError(missing_vars=["OPENROUTER_API_KEY", "DATABASE_URL"])
        assert error.error_code == "cfg_001"
        assert len(error.context["missing_vars"]) == 2


class TestErrorCodeUniqueness:
    """Test that all error codes are unique."""

    def test_error_codes_unique(self):
        """Verify all error codes are unique."""
        codes = [code.value for code in ErrorCode]
        assert len(codes) == len(set(codes)), "Duplicate error codes found"


class TestDescribeError:
    """Tests for the describe_error grouping helper."""

    def test_api_authentication_error(self):
        """APIAuthenticationError maps to the auth-failure message."""
        from blog_automation.errors import describe_error

        msg = describe_error(APIAuthenticationError(service="ahrefs"))
        assert "API authentication failed" in msg
        assert ".env" in msg

    def test_api_rate_limit_error(self):
        """APIRateLimitError maps to the rate-limit message."""
        from blog_automation.errors import describe_error

        msg = describe_error(APIRateLimitError(service="ahrefs", retry_after=60))
        assert "rate limit" in msg.lower()

    def test_api_timeout_error(self):
        """APITimeoutError maps to the timeout message."""
        from blog_automation.errors import describe_error

        msg = describe_error(APITimeoutError(service="ahrefs"))
        assert "timed out" in msg.lower()

    def test_api_connection_error(self):
        """APIConnectionError maps to the connection message."""
        from blog_automation.errors import APIConnectionError, describe_error

        msg = describe_error(APIConnectionError(service="ahrefs"))
        assert "connect" in msg.lower()

    def test_database_error(self):
        """DatabaseError maps to the database message."""
        from blog_automation.errors import describe_error

        msg = describe_error(DatabaseConnectionError())
        assert "database" in msg.lower()

    def test_configuration_error(self):
        """ConfigurationError maps to the configuration message."""
        from blog_automation.errors import describe_error

        msg = describe_error(ConfigurationError(missing_vars=["AHREFS_API_KEY"]))
        assert ".env" in msg

    def test_wrapped_cause_is_unwrapped(self):
        """A ProcessingError wrapping an APIAuthenticationError is unwrapped."""
        from blog_automation.errors import describe_error

        try:
            raise APIAuthenticationError(service="ahrefs")
        except APIAuthenticationError as e:
            wrapped = ProcessingError(
                message=f"Keyword research failed: {str(e)}",
                step="keyword_research",
            )
            wrapped.__cause__ = e
        msg = describe_error(wrapped)
        assert "API authentication failed" in msg

    def test_unknown_exception_falls_back(self):
        """Unknown exceptions fall back to a message including str(exc)."""
        from blog_automation.errors import describe_error

        msg = describe_error(ValueError("something broke"))
        assert "Pipeline failed" in msg
        assert "something broke" in msg

    def test_auth_error_includes_service_name_and_env_var(self):
        """A named service produces a service-specific message with env var."""
        from blog_automation.errors import describe_error

        msg = describe_error(APIAuthenticationError(service="ahrefs"))
        assert "Ahrefs" in msg
        assert "AHREFS_API_KEY" in msg

    def test_auth_error_resolves_url_based_service(self):
        """A base-URL service (from base_client) is resolved to a name."""
        from blog_automation.errors import describe_error

        msg = describe_error(
            APIAuthenticationError(service="https://api.ahrefs.com/v3")
        )
        assert "Ahrefs" in msg
        assert "AHREFS_API_KEY" in msg

    def test_auth_error_unknown_service_shows_raw_name(self):
        """An unrecognised service still names it in the message."""
        from blog_automation.errors import describe_error

        msg = describe_error(APIAuthenticationError(service="some-unknown-api"))
        assert "some-unknown-api" in msg

    def test_configuration_error_includes_missing_vars(self):
        """ConfigurationError lists the missing env vars."""
        from blog_automation.errors import describe_error

        msg = describe_error(
            ConfigurationError(missing_vars=["AHREFS_API_KEY", "OPENROUTER_API_KEY"])
        )
        assert "AHREFS_API_KEY" in msg
        assert "OPENROUTER_API_KEY" in msg
