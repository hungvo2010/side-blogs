"""Unit tests for configuration management."""

import os
import pytest

from blog_automation.config import (
    DevelopmentSettings,
    ProductionSettings,
    Settings,
    TestingSettings,
    clear_settings_cache,
    get_settings,
)


class TestSettingsClass:
    """Tests for Settings class."""

    def setup_method(self):
        """Clear settings cache before each test."""
        clear_settings_cache()

    def test_default_settings(self, monkeypatch):
        """Test default settings values."""
        # Remove ENVIRONMENT and LOG_LEVEL to test defaults
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        settings = Settings()
        assert settings.environment == "development"
        assert settings.database_echo is False
        assert settings.log_level == "INFO"

    def test_settings_from_env(self, monkeypatch):
        """Test settings loaded from environment variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        settings = Settings()
        assert settings.database_url == "postgresql://test:test@localhost/testdb"
        assert settings.log_level == "DEBUG"

    def test_log_level_validation(self):
        """Test log level validation."""
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"

        with pytest.raises(ValueError):
            Settings(log_level="invalid")

    def test_log_path_creation(self, tmp_path, monkeypatch):
        """Test log directory creation."""
        log_dir = tmp_path / "logs"
        monkeypatch.setenv("LOG_DIR", str(log_dir))

        settings = Settings()
        path = settings.log_path

        assert path.exists()
        assert path.is_dir()

    def test_validate_required_for_production(self):
        """Test production validation."""
        settings = Settings(
            openai_api_key="",
            anthropic_api_key="",
            database_url="",
        )

        missing = settings.validate_required_for_production()
        assert "openai_api_key" in missing
        assert "anthropic_api_key" in missing
        assert "database_url" in missing


class TestDevelopmentSettings:
    """Tests for DevelopmentSettings."""

    def test_development_defaults(self, monkeypatch):
        """Test development environment defaults."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        settings = DevelopmentSettings()
        assert settings.environment == "development"
        assert settings.database_echo is True
        assert settings.log_level == "DEBUG"


class TestTestingSettingsClass:
    """Tests for TestingSettings."""

    def test_test_defaults(self, monkeypatch):
        """Test testing environment defaults."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        settings = TestingSettings()
        assert settings.environment == "testing"
        assert settings.database_echo is False
        assert settings.log_level == "WARNING"


class TestProductionSettings:
    """Tests for ProductionSettings."""

    def test_production_defaults(self, monkeypatch):
        """Test production environment defaults."""
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        settings = ProductionSettings()
        assert settings.environment == "production"
        assert settings.database_echo is False
        assert settings.log_level == "INFO"


class TestGetSettings:
    """Tests for get_settings factory function."""

    def setup_method(self):
        """Clear settings cache before each test."""
        clear_settings_cache()

    def test_get_development_settings(self, monkeypatch):
        """Test getting development settings."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        clear_settings_cache()

        settings = get_settings()
        assert isinstance(settings, DevelopmentSettings)

    def test_get_testing_settings(self, monkeypatch):
        """Test getting testing settings."""
        monkeypatch.setenv("ENVIRONMENT", "testing")
        clear_settings_cache()

        settings = get_settings()
        assert isinstance(settings, TestingSettings)

    def test_get_production_settings(self, monkeypatch):
        """Test getting production settings."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        clear_settings_cache()

        settings = get_settings()
        assert isinstance(settings, ProductionSettings)

    def test_settings_caching(self, monkeypatch):
        """Test that settings are cached."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        clear_settings_cache()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_clear_cache(self, monkeypatch):
        """Test clearing settings cache."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        clear_settings_cache()

        settings1 = get_settings()
        clear_settings_cache()
        settings2 = get_settings()

        assert settings1 is not settings2
