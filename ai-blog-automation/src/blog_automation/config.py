"""Configuration management for the AI Blog Automation Platform.

Uses Pydantic Settings for type-safe configuration with environment
variable loading and validation.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "testing", "production"] = "development"

    # Database
    database_url: str = Field(
        default="postgresql://localhost:5432/blog_db",
        description="PostgreSQL connection URL",
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL queries to stdout",
    )
    database_pool_size: int = Field(default=5, description="Connection pool size")
    database_max_overflow: int = Field(
        default=10, description="Max overflow connections"
    )

    # OpenAI API
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_organization_id: str | None = Field(
        default=None, description="OpenAI organization ID"
    )
    openai_default_model: str = Field(
        default="gpt-4-turbo-preview", description="Default OpenAI model"
    )

    # Anthropic (Claude) API
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_default_model: str = Field(
        default="claude-3-sonnet-20240229", description="Default Claude model"
    )

    # Ahrefs API
    ahrefs_api_key: str = Field(default="", description="Ahrefs API key")

    # Perplexity API
    perplexity_api_key: str = Field(default="", description="Perplexity API key")

    # Copyscape API
    copyscape_api_key: str = Field(default="", description="Copyscape API key")
    copyscape_username: str = Field(default="", description="Copyscape username")

    # WordPress
    wordpress_url: str = Field(default="", description="WordPress site URL")
    wordpress_username: str = Field(default="", description="WordPress username")
    wordpress_app_password: str = Field(
        default="", description="WordPress application password"
    )

    # Google APIs
    google_analytics_property_id: str = Field(
        default="", description="GA4 property ID"
    )
    google_search_console_site_url: str = Field(
        default="", description="GSC site URL"
    )
    google_service_account_json: str = Field(
        default="", description="Path to service account JSON"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_dir: str = Field(default="logs", description="Log directory")

    # Alerts
    slack_webhook_url: str | None = Field(
        default=None, description="Slack webhook URL"
    )
    alert_email: str | None = Field(default=None, description="Alert email address")
    smtp_host: str | None = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_username: str | None = Field(default=None, description="SMTP username")
    smtp_password: str | None = Field(default=None, description="SMTP password")

    # Content Generation
    default_word_count: int = Field(
        default=2000, description="Default target word count"
    )
    max_generation_cost: float = Field(
        default=1.0, description="Max cost per article in USD"
    )
    plagiarism_threshold: float = Field(
        default=3.0, description="Max plagiarism percentage"
    )

    # Paths
    migrations_dir: Path = Field(
        default=Path("migrations"), description="Migrations directory"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v

    @property
    def log_path(self) -> Path:
        """Get the log directory path."""
        path = Path(self.log_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def validate_required_for_production(self) -> list[str]:
        """Validate required settings for production.

        Returns:
            List of missing required settings
        """
        missing = []
        required = [
            ("database_url", self.database_url),
            ("openai_api_key", self.openai_api_key),
            ("anthropic_api_key", self.anthropic_api_key),
        ]

        for name, value in required:
            if not value or value.startswith("sk-..."):
                missing.append(name)

        return missing


class DevelopmentSettings(Settings):
    """Development environment settings."""

    environment: Literal["development", "testing", "production"] = "development"
    database_echo: bool = True
    log_level: str = "DEBUG"


class TestingSettings(Settings):
    """Testing environment settings."""

    environment: Literal["development", "testing", "production"] = "testing"
    database_url: str = "postgresql://localhost:5432/blog_db_test"
    database_echo: bool = False
    log_level: str = "WARNING"


class ProductionSettings(Settings):
    """Production environment settings."""

    environment: Literal["development", "testing", "production"] = "production"
    database_echo: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get settings instance based on environment.

    Returns:
        Settings instance for current environment
    """
    env = os.getenv("ENVIRONMENT", "development").lower()

    settings_map = {
        "development": DevelopmentSettings,
        "testing": TestingSettings,
        "production": ProductionSettings,
    }

    settings_class = settings_map.get(env, DevelopmentSettings)
    return settings_class()


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for testing)."""
    get_settings.cache_clear()
