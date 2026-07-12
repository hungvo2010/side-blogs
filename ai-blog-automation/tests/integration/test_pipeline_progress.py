"""Integration tests for pipeline progress + failure tracking on Article.

Exercises ``scripts/run_pipeline.py:cmd_full`` against an in-memory SQLite DB
that shares a single connection across ``get_session()`` calls (StaticPool).
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

# Make scripts/ importable so we can import run_pipeline.cmd_full
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


@pytest.fixture
def shared_sqlite_engine(monkeypatch):
    """Point the global blog_automation engine at a single-connection sqlite DB."""
    from blog_automation.models import base as _base

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _base.Base.metadata.create_all(eng)
    monkeypatch.setattr(_base, "_engine", eng)
    monkeypatch.setattr(_base, "_SessionFactory", None)
    yield eng
    _base.reset_engine()
    eng.dispose()


def test_cmd_full_records_step1_failure_on_stub_article(
    shared_sqlite_engine, monkeypatch
):
    """A keyword-research (step 1) failure is recorded on the stub Article."""
    import run_pipeline

    from blog_automation.errors import APIAuthenticationError
    from blog_automation.models import Article, get_session

    def _raise_auth(*_args, **_kwargs):
        raise APIAuthenticationError(service="ahrefs")

    monkeypatch.setattr("blog_automation.pipelines.research_keyword", _raise_auth)

    result = run_pipeline.cmd_full("failing keyword")

    assert result is None

    with get_session() as session:
        articles = session.query(Article).filter_by(keyword="failing keyword").all()
        assert len(articles) == 1
        a = articles[0]
        assert a.status == "failed"
        assert a.pipeline_progress["research"] == "failed"
        assert "API authentication failed" in (a.pipeline_error or "")
        assert ".env" in (a.pipeline_error or "")
