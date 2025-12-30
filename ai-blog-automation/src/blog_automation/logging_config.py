"""Logging configuration for the AI Blog Automation Platform.

Provides structured logging with JSON output for files and human-readable
console output. Includes log rotation and request ID tracking.
"""

import logging
import logging.handlers
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get current request ID or generate a new one."""
    rid = request_id_var.get()
    if not rid:
        rid = str(uuid.uuid4())[:8]
        request_id_var.set(rid)
    return rid


def set_request_id(request_id: str) -> None:
    """Set the current request ID."""
    request_id_var.set(request_id)


def add_request_id(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add request ID to log event."""
    event_dict["request_id"] = get_request_id()
    return event_dict


def add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO timestamp to log event."""
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


class LogConfig:
    """Logging configuration settings."""

    def __init__(
        self,
        log_level: str = "INFO",
        log_dir: str = "logs",
        log_file: str = "app.log",
        max_bytes: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 5,
        json_logs: bool = True,
    ):
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_dir = Path(log_dir)
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.json_logs = json_logs

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def log_path(self) -> Path:
        return self.log_dir / self.log_file


def setup_logging(
    log_level: str | None = None,
    log_dir: str | None = None,
    json_logs: bool = True,
) -> None:
    """Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        json_logs: Whether to use JSON format for file logs
    """
    level = log_level or os.getenv("LOG_LEVEL", "INFO")
    directory = log_dir or os.getenv("LOG_DIR", "logs")

    config = LogConfig(log_level=level, log_dir=directory, json_logs=json_logs)

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        add_timestamp,
        add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(config.log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    root_logger = logging.getLogger()
    root_logger.setLevel(config.log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.log_level)
    console_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    console_handler.setFormatter(logging.Formatter(console_format))
    root_logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        config.log_path,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
    )
    file_handler.setLevel(config.log_level)

    if json_logs:
        file_format = (
            '{"timestamp": "%(asctime)s", "name": "%(name)s", '
            '"level": "%(levelname)s", "message": "%(message)s"}'
        )
    else:
        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    file_handler.setFormatter(logging.Formatter(file_format))
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Convenience function for standard library logger
def get_std_logger(name: str) -> logging.Logger:
    """Get a standard library logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logging.Logger
    """
    return logging.getLogger(name)
