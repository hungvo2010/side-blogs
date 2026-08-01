"""Shared helpers for real-API integration tests.

Every test module under ``tests/integration/real_api/`` hits a real external
service. To avoid accidental spend / network calls in normal test runs, all of
these tests are SKIPPED unless:

1. ``RUN_REAL_API_TESTS=1`` is set in the environment, AND
2. the credentials for that specific service are present.

Run them explicitly, e.g.::

    RUN_REAL_API_TESTS=1 pytest tests/integration/real_api/ -v

or just one service::

    RUN_REAL_API_TESTS=1 pytest tests/integration/real_api/test_openrouter_real.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Real API tests must NOT inherit the testing env (sqlite, warning log level)
# that the root conftest forces. We explicitly re-enable development settings
# so get_settings() reads the real .env values for API keys.
os.environ["ENVIRONMENT"] = "development"
os.environ.pop("DATABASE_URL", None)

from blog_automation.config import clear_settings_cache, get_settings

clear_settings_cache()
_settings = get_settings()

RUN_REAL_API = os.getenv("RUN_REAL_API_TESTS", "").lower() in {"1", "true", "yes"}

# Hard gate: everything in this package skips without the global opt-in flag.
pytestmark = pytest.mark.skipif(
    not RUN_REAL_API,
    reason="Real API tests disabled — set RUN_REAL_API_TESTS=1 to enable",
)


def has_creds(*values: object) -> bool:
    """True when every credential value is present and non-placeholder."""
    for v in values:
        if v is None:
            return False
        s = str(v).strip()
        if not s or s.endswith("...") or s.startswith("sk-..."):
            return False
    return True


def require_creds(marker: str, *values: object):
    """Return a pytest mark skipping the test when creds are missing."""
    return pytest.mark.skipif(
        not has_creds(*values),
        reason=f"Missing credentials for {marker} — fill them in .env",
    )


def service_account_path() -> Path | None:
    """Resolve the configured Google service-account JSON if it exists."""
    raw = _settings.google_service_account_json
    if not raw:
        return None
    p = Path(raw).expanduser()
    return p if p.is_file() else None


settings = _settings
