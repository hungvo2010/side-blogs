"""Custom exception hierarchy for the AI Blog Automation Platform.

This module defines all custom exceptions used throughout the application,
organized by category with unique error codes for tracking and debugging.
"""

from datetime import datetime
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Enumeration of all error codes in the system."""

    # API Errors (api_xxx)
    API_TIMEOUT = "api_001"
    API_RATE_LIMIT = "api_002"
    API_AUTH_FAILED = "api_003"
    API_INVALID_RESPONSE = "api_004"
    API_SERVER_ERROR = "api_005"
    API_CONNECTION_ERROR = "api_006"
    API_NOT_FOUND = "api_007"

    # Validation Errors (val_xxx)
    INVALID_KEYWORD = "val_001"
    INVALID_BRIEF = "val_002"
    INVALID_ARTICLE = "val_003"
    MISSING_FIELD = "val_004"
    INVALID_FORMAT = "val_005"
    VALIDATION_FAILED = "val_006"

    # Processing Errors (proc_xxx)
    GENERATION_FAILED = "proc_001"
    VERIFICATION_FAILED = "proc_002"
    PUBLISHING_FAILED = "proc_003"
    EXTRACTION_FAILED = "proc_004"
    OPTIMIZATION_FAILED = "proc_005"
    PIPELINE_FAILED = "proc_006"

    # Database Errors (db_xxx)
    DB_CONNECTION = "db_001"
    DB_CONSTRAINT = "db_002"
    DB_NOT_FOUND = "db_003"
    DB_INTEGRITY = "db_004"
    DB_MIGRATION = "db_005"

    # Review Errors (rev_xxx)
    REVIEW_NOT_FOUND = "rev_001"
    REVIEW_ALREADY_COMPLETED = "rev_002"
    REVIEW_INVALID_STATUS = "rev_003"

    # Configuration Errors (cfg_xxx)
    CONFIG_MISSING = "cfg_001"
    CONFIG_INVALID = "cfg_002"


class Severity(str, Enum):
    """Error severity levels."""

    CRITICAL = "critical"  # System cannot continue
    ERROR = "error"  # Operation failed but system can continue
    WARNING = "warning"  # Recoverable issue


class AppError(Exception):
    """Base exception class for all application errors.

    Attributes:
        message: Human-readable error message
        error_code: Unique error code for tracking
        severity: Error severity level
        context: Additional context about the error
        timestamp: When the error occurred
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode | str = "unknown",
        severity: Severity = Severity.ERROR,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = (
            error_code.value if isinstance(error_code, ErrorCode) else error_code
        )
        self.severity = severity.value if isinstance(severity, Severity) else severity
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "severity": self.severity,
            "context": self.context,
            "timestamp": self.timestamp,
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"severity={self.severity!r})"
        )


# =============================================================================
# API Errors
# =============================================================================


class APIError(AppError):
    """Base class for all API-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.API_SERVER_ERROR,
        severity: Severity = Severity.ERROR,
        context: dict[str, Any] | None = None,
        service: str | None = None,
        status_code: int | None = None,
    ):
        ctx = context or {}
        if service:
            ctx["service"] = service
        if status_code:
            ctx["status_code"] = status_code
        super().__init__(message, error_code, severity, ctx)
        self.service = service
        self.status_code = status_code


class APITimeoutError(APIError):
    """Raised when an API request times out."""

    def __init__(
        self,
        message: str = "API request timed out",
        context: dict[str, Any] | None = None,
        service: str | None = None,
    ):
        super().__init__(
            message,
            ErrorCode.API_TIMEOUT,
            Severity.ERROR,
            context,
            service,
        )


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "API rate limit exceeded",
        context: dict[str, Any] | None = None,
        service: str | None = None,
        retry_after: int | None = None,
    ):
        ctx = context or {}
        if retry_after:
            ctx["retry_after"] = retry_after
        super().__init__(
            message,
            ErrorCode.API_RATE_LIMIT,
            Severity.WARNING,
            ctx,
            service,
            429,
        )
        self.retry_after = retry_after


class APIAuthenticationError(APIError):
    """Raised when API authentication fails."""

    def __init__(
        self,
        message: str = "API authentication failed",
        context: dict[str, Any] | None = None,
        service: str | None = None,
    ):
        super().__init__(
            message,
            ErrorCode.API_AUTH_FAILED,
            Severity.CRITICAL,
            context,
            service,
            401,
        )


class APIInvalidResponseError(APIError):
    """Raised when API returns an invalid or unexpected response."""

    def __init__(
        self,
        message: str = "Invalid API response",
        context: dict[str, Any] | None = None,
        service: str | None = None,
    ):
        super().__init__(
            message,
            ErrorCode.API_INVALID_RESPONSE,
            Severity.ERROR,
            context,
            service,
        )


class APIServerError(APIError):
    """Raised when API returns a 5xx server error."""

    def __init__(
        self,
        message: str = "API server error",
        context: dict[str, Any] | None = None,
        service: str | None = None,
        status_code: int = 500,
    ):
        super().__init__(
            message,
            ErrorCode.API_SERVER_ERROR,
            Severity.ERROR,
            context,
            service,
            status_code,
        )


class APIConnectionError(APIError):
    """Raised when unable to connect to API."""

    def __init__(
        self,
        message: str = "Failed to connect to API",
        context: dict[str, Any] | None = None,
        service: str | None = None,
    ):
        super().__init__(
            message,
            ErrorCode.API_CONNECTION_ERROR,
            Severity.ERROR,
            context,
            service,
        )


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(AppError):
    """Base class for all validation errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.VALIDATION_FAILED,
        severity: Severity = Severity.ERROR,
        context: dict[str, Any] | None = None,
        field: str | None = None,
    ):
        ctx = context or {}
        if field:
            ctx["field"] = field
        super().__init__(message, error_code, severity, ctx)
        self.field = field


class InvalidKeywordError(ValidationError):
    """Raised when keyword validation fails."""

    def __init__(
        self,
        message: str = "Invalid keyword",
        context: dict[str, Any] | None = None,
        keyword: str | None = None,
    ):
        ctx = context or {}
        if keyword:
            ctx["keyword"] = keyword
        super().__init__(message, ErrorCode.INVALID_KEYWORD, Severity.ERROR, ctx)


class InvalidBriefError(ValidationError):
    """Raised when content brief validation fails."""

    def __init__(
        self,
        message: str = "Invalid content brief",
        context: dict[str, Any] | None = None,
        missing_fields: list[str] | None = None,
    ):
        ctx = context or {}
        if missing_fields:
            ctx["missing_fields"] = missing_fields
        super().__init__(message, ErrorCode.INVALID_BRIEF, Severity.ERROR, ctx)


class InvalidArticleError(ValidationError):
    """Raised when article validation fails."""

    def __init__(
        self,
        message: str = "Invalid article",
        context: dict[str, Any] | None = None,
        issues: list[str] | None = None,
    ):
        ctx = context or {}
        if issues:
            ctx["issues"] = issues
        super().__init__(message, ErrorCode.INVALID_ARTICLE, Severity.ERROR, ctx)


class MissingFieldError(ValidationError):
    """Raised when a required field is missing."""

    def __init__(
        self,
        field: str,
        message: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        msg = message or f"Required field '{field}' is missing"
        super().__init__(msg, ErrorCode.MISSING_FIELD, Severity.ERROR, context, field)


# =============================================================================
# Processing Errors
# =============================================================================


class ProcessingError(AppError):
    """Base class for all processing errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.PIPELINE_FAILED,
        severity: Severity = Severity.ERROR,
        context: dict[str, Any] | None = None,
        step: str | None = None,
    ):
        ctx = context or {}
        if step:
            ctx["step"] = step
        super().__init__(message, error_code, severity, ctx)
        self.step = step


class GenerationFailureError(ProcessingError):
    """Raised when content generation fails."""

    def __init__(
        self,
        message: str = "Content generation failed",
        context: dict[str, Any] | None = None,
        step: str | None = None,
    ):
        super().__init__(
            message, ErrorCode.GENERATION_FAILED, Severity.ERROR, context, step
        )


class VerificationFailureError(ProcessingError):
    """Raised when fact verification fails."""

    def __init__(
        self,
        message: str = "Fact verification failed",
        context: dict[str, Any] | None = None,
        step: str | None = None,
    ):
        super().__init__(
            message, ErrorCode.VERIFICATION_FAILED, Severity.ERROR, context, step
        )


class PublishingFailureError(ProcessingError):
    """Raised when publishing to WordPress fails."""

    def __init__(
        self,
        message: str = "Publishing failed",
        context: dict[str, Any] | None = None,
        step: str | None = None,
    ):
        super().__init__(
            message, ErrorCode.PUBLISHING_FAILED, Severity.ERROR, context, step
        )


# =============================================================================
# Database Errors
# =============================================================================


class DatabaseError(AppError):
    """Base class for all database errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DB_CONNECTION,
        severity: Severity = Severity.ERROR,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, severity, context)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(
        self,
        message: str = "Database connection failed",
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message, ErrorCode.DB_CONNECTION, Severity.CRITICAL, context)


class ConstraintViolationError(DatabaseError):
    """Raised when a database constraint is violated."""

    def __init__(
        self,
        message: str = "Database constraint violation",
        context: dict[str, Any] | None = None,
        constraint: str | None = None,
    ):
        ctx = context or {}
        if constraint:
            ctx["constraint"] = constraint
        super().__init__(message, ErrorCode.DB_CONSTRAINT, Severity.ERROR, ctx)


class NotFoundError(DatabaseError):
    """Raised when a database record is not found."""

    def __init__(
        self,
        message: str = "Record not found",
        context: dict[str, Any] | None = None,
        model: str | None = None,
        id: int | str | None = None,
    ):
        ctx = context or {}
        if model:
            ctx["model"] = model
        if id:
            ctx["id"] = id
        super().__init__(message, ErrorCode.DB_NOT_FOUND, Severity.WARNING, ctx)


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(AppError):
    """Raised when configuration is missing or invalid."""

    def __init__(
        self,
        message: str = "Configuration error",
        context: dict[str, Any] | None = None,
        missing_vars: list[str] | None = None,
    ):
        ctx = context or {}
        if missing_vars:
            ctx["missing_vars"] = missing_vars
        super().__init__(message, ErrorCode.CONFIG_MISSING, Severity.CRITICAL, ctx)


# =============================================================================
# Error Description (human-readable grouping for UI notifications)
# =============================================================================


def describe_error(exc: Exception) -> str:
    """Return a human-readable, grouped description of a pipeline exception.

    Unwraps one level of ``__cause__`` (to get past ``ProcessingError``
    wrappers raised by pipeline steps) and classifies the underlying exception
    by type into a fixed, actionable message. Unknown exceptions fall back to a
    generic message that includes the exception's string representation.

    Args:
        exc: The exception raised by a pipeline step (possibly a
            ``ProcessingError`` wrapping the real cause).

    Returns:
        A short, human-readable string describing the failure.
    """
    target = (
        exc.__cause__ if isinstance(exc, ProcessingError) and exc.__cause__ else exc
    )

    if isinstance(target, APIAuthenticationError):
        return "API authentication failed — check your API keys in .env"
    if isinstance(target, APIRateLimitError):
        return "API rate limit reached — wait a moment and retry"
    if isinstance(target, APITimeoutError):
        return "Request to the API timed out — check your connection and retry"
    if isinstance(target, APIConnectionError):
        return "Could not connect to the API service"
    if isinstance(target, DatabaseError):
        return "Database error — check the database is running"
    if isinstance(target, ConfigurationError):
        return "Configuration missing — check your .env file"
    return f"Pipeline failed: {str(exc)}"
