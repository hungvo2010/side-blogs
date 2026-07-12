#!/usr/bin/env python3
"""
Pipeline Runner Script
======================
Run individual pipelines from the command line.

Usage:
    poetry run python scripts/run_pipeline.py research "your keyword"
    poetry run python scripts/run_pipeline.py brief <brief_id>
    poetry run python scripts/run_pipeline.py draft <brief_id>
    poetry run python scripts/run_pipeline.py factcheck <article_id>
    poetry run python scripts/run_pipeline.py seo <article_id>
    poetry run python scripts/run_pipeline.py publish <article_id>
    poetry run python scripts/run_pipeline.py full "your keyword"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()


def cmd_research(keyword: str):
    """Run keyword research pipeline."""
    print(f"🔍 Researching keyword: {keyword}")

    from blog_automation.pipelines import research_keyword

    brief = research_keyword(keyword)

    print(f"✅ Brief created: ID={brief.id}")
    print(f"   Volume: {brief.search_volume}")
    print(f"   Difficulty: {brief.difficulty}")
    return brief


def cmd_brief(keyword: str):
    """Generate full content brief."""
    print(f"📝 Generating brief for: {keyword}")

    from blog_automation.pipelines import research_keyword_full

    brief = research_keyword_full(keyword)

    print(f"✅ Full brief created: ID={brief.id}")
    print(f"   Sections: {len(brief.get_sections())}")
    print(f"   LSI Keywords: {len(brief.get_lsi_keywords())}")
    return brief


def cmd_draft(brief_id: int):
    """Generate article draft from brief."""
    print(f"✍️  Generating draft from brief ID: {brief_id}")

    from blog_automation.models import ContentBrief, get_session
    from blog_automation.pipelines import content_brief_to_draft

    with get_session() as session:
        brief = session.query(ContentBrief).get(brief_id)
        if not brief:
            print(f"❌ Brief {brief_id} not found")
            return None

        article = content_brief_to_draft(brief, session)
        print(f"✅ Article created: ID={article.id}")
        print(f"   Title: {article.title}")
        print(f"   Words: {article.word_count}")
        return article


def cmd_factcheck(article_id: int):
    """Run fact-checking on article."""
    print(f"🔬 Fact-checking article ID: {article_id}")

    from blog_automation.models import Article, get_session
    from blog_automation.pipelines import fact_check_article

    with get_session() as session:
        article = session.query(Article).get(article_id)
        if not article:
            print(f"❌ Article {article_id} not found")
            return None

        report = fact_check_article(article, session)
        print("✅ Fact-check complete")
        print(f"   Claims checked: {report.get('total_claims', 0)}")
        print(f"   Accuracy: {report.get('accuracy_rate', 0):.1f}%")
        return report


def cmd_seo(article_id: int):
    """Run SEO optimization on article."""
    print(f"📈 Optimizing SEO for article ID: {article_id}")

    from blog_automation.models import Article, get_session
    from blog_automation.pipelines import seo_optimize_article

    with get_session() as session:
        article = session.query(Article).get(article_id)
        if not article:
            print(f"❌ Article {article_id} not found")
            return None

        result = seo_optimize_article(article, session)
        print("✅ SEO optimization complete")
        print(f"   Meta title: {article.meta_title}")
        print(f"   SEO score: {article.seo_score}")
        return result


def cmd_publish(article_id: int):
    """Publish article to WordPress."""
    print(f"🚀 Publishing article ID: {article_id}")

    from blog_automation.models import Article, get_session
    from blog_automation.pipelines import publish_article

    with get_session() as session:
        article = session.query(Article).get(article_id)
        if not article:
            print(f"❌ Article {article_id} not found")
            return None

        result = publish_article(article, session)
        print("✅ Published!")
        print(f"   URL: {article.wordpress_url}")
        print(f"   Post ID: {article.wordpress_post_id}")
        return result


def cmd_revise(article_id: int, feedback: str = None):
    """Revise article based on feedback."""
    print(f"✍️  Revising article ID: {article_id}")

    from blog_automation.models import Article, get_session
    from blog_automation.pipelines import revise_article_with_feedback

    with get_session() as session:
        article = session.query(Article).get(article_id)
        if not article:
            print(f"❌ Article {article_id} not found")
            return None

        # If no feedback provided as arg, use the one stored in DB from review interface
        if not feedback:
            feedback = getattr(article, "reviewer_feedback", None)
            if not feedback:
                print("❌ No feedback found in database or arguments")
                return None

        print(f"   Using feedback: {feedback}")
        article = revise_article_with_feedback(article, feedback)

        # Commit the changes
        session.add(article)
        session.commit()

        print("✅ Revision complete!")
        print(f"   New words: {article.word_count}")
        return article


def cmd_full(keyword: str):
    """Run full pipeline from keyword to draft.

    Tracks per-step progress on a stub ``Article`` row created at the start, so
    that a failure in any step (including step 1, keyword research) is recorded
    on the article for the dashboard to surface via toasts / progress view.
    """
    import re
    import uuid
    from datetime import datetime

    from blog_automation.errors import describe_error
    from blog_automation.models import Article, get_session
    from blog_automation.pipelines import (
        content_brief_to_draft,
        fact_check_article,
        generate_content_brief,
        research_keyword,
        run_quality_gates,
        seo_optimize_article,
    )

    pipeline_steps = [
        "research",
        "brief",
        "draft",
        "fact_check",
        "seo",
        "quality_gates",
    ]
    initial_progress = {step: "pending" for step in pipeline_steps}

    def _stub_slug(kw: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", kw.lower().strip())
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{slug}-stub-{ts}-{uuid.uuid4().hex[:4]}"

    def _update_progress(article_id, step, state, status=None, error=None):
        with get_session() as sess:
            a = sess.query(Article).get(article_id)
            if not a:
                return
            prog = dict(a.pipeline_progress or initial_progress)
            prog[step] = state
            a.pipeline_progress = prog
            if status:
                a.status = status
            if error is not None:
                a.pipeline_error = error

    print(f"🎯 Running full pipeline for: {keyword}")
    print("=" * 50)

    # Create a stub Article at the start so any step failure is recorded on it.
    with get_session() as session:
        stub = Article(
            title=keyword,
            slug=_stub_slug(keyword),
            keyword=keyword,
            status="researching",
            pipeline_progress=initial_progress,
        )
        session.add(stub)
        session.commit()
        session.refresh(stub)
        article_id = stub.id

    def _run_step(step, status_during, fn):
        """Run a step, marking progress. Returns result or None on failure."""
        _update_progress(article_id, step, "pending", status=status_during)
        try:
            result = fn()
            _update_progress(article_id, step, "done")
            return result
        except Exception as e:
            _update_progress(
                article_id, step, "failed", status="failed", error=describe_error(e)
            )
            print(f"❌ Step '{step}' failed: {describe_error(e)}")
            return None

    # Step 1: Keyword research
    print("\n🔍 Running keyword research...")
    brief = _run_step("research", "researching", lambda: research_keyword(keyword))
    if brief is None:
        return None
    print(f"✅ Research complete: ID={brief.id}")

    # Step 2: Brief generation
    print("\n📝 Generating content brief...")
    complete_brief = _run_step(
        "brief", "briefing", lambda: generate_content_brief(keyword, brief.id)
    )
    if complete_brief is None:
        return None
    print(f"✅ Brief complete: ID={complete_brief.id}")

    # Step 3: Draft (creates a new Article; transfer progress from the stub)
    print("\n✍️  Drafting Article...")
    drafted = _run_step(
        "draft", "drafting", lambda: content_brief_to_draft(complete_brief)
    )
    if drafted is None:
        return None
    with get_session() as session:
        stub_obj = session.query(Article).get(article_id)
        real = session.query(Article).get(drafted.id)
        prog = dict(stub_obj.pipeline_progress or initial_progress)
        prog["draft"] = "done"
        real.pipeline_progress = prog
        real.status = "draft"
        session.delete(stub_obj)
        session.commit()
        article_id = real.id
    print(f"✅ Draft created: ID={real.id} ({real.word_count} words)")

    # Steps 4-6: run within one session, updating progress after each step.
    with get_session() as session:
        article = session.query(Article).get(article_id)
        # Step 4: Fact-check
        print("\n🔬 Running Fact-checking...")
        prog = dict(article.pipeline_progress or initial_progress)
        prog["fact_check"] = "pending"
        article.pipeline_progress = prog
        article.status = "fact_checking"
        session.commit()
        try:
            report = fact_check_article(article)
            session.refresh(article)
            prog = dict(article.pipeline_progress or initial_progress)
            prog["fact_check"] = "done"
            article.pipeline_progress = prog
            session.commit()
            acc = report.get("accuracy_rate", 0)
            print(f"✅ Fact-check complete: {acc:.1f}% accuracy")
        except Exception as e:
            prog = dict(article.pipeline_progress or initial_progress)
            prog["fact_check"] = "failed"
            article.pipeline_progress = prog
            article.status = "failed"
            article.pipeline_error = describe_error(e)
            session.commit()
            print(f"❌ Fact-check failed: {describe_error(e)}")
            return None

        # Step 5: SEO Optimization
        print("\n📈 Running SEO Optimization...")
        prog = dict(article.pipeline_progress or initial_progress)
        prog["seo"] = "pending"
        article.pipeline_progress = prog
        article.status = "seo_review"
        session.commit()
        try:
            seo_optimize_article(article)
            session.refresh(article)
            prog = dict(article.pipeline_progress or initial_progress)
            prog["seo"] = "done"
            article.pipeline_progress = prog
            session.commit()
            print(f"✅ SEO optimized: Score={article.seo_score}")
        except Exception as e:
            prog = dict(article.pipeline_progress or initial_progress)
            prog["seo"] = "failed"
            article.pipeline_progress = prog
            article.status = "failed"
            article.pipeline_error = describe_error(e)
            session.commit()
            print(f"❌ SEO failed: {describe_error(e)}")
            return None

        # Step 6: Quality Gates
        print("\n🛡️  Running Quality Gates...")
        prog = dict(article.pipeline_progress or initial_progress)
        prog["quality_gates"] = "pending"
        article.pipeline_progress = prog
        article.status = "quality_gates"
        session.commit()
        try:
            run_quality_gates(article)
            session.refresh(article)
            prog = dict(article.pipeline_progress or initial_progress)
            prog["quality_gates"] = "done"
            article.pipeline_progress = prog
            session.commit()
            print(f"✅ Quality gates complete: Status={article.status}")
        except Exception as e:
            prog = dict(article.pipeline_progress or initial_progress)
            prog["quality_gates"] = "failed"
            article.pipeline_progress = prog
            article.status = "failed"
            article.pipeline_error = describe_error(e)
            session.commit()
            print(f"❌ Quality gates failed: {describe_error(e)}")
            return None

        print(f"\n{'=' * 50}")
        print("✅ COMPLETE!")
        print(f"   Article ID: {article.id}")
        print(f"   Title: {article.title}")
        print(f"   Final Status: {article.status}")
        print("\nReview this article in the dashboard: http://localhost:8501")
        print("\nTo publish, run:")
        print(f"   poetry run python scripts/run_pipeline.py publish {article.id}")

        return article


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1].lower()

    commands = {
        "research": (cmd_research, str, "keyword"),
        "brief": (cmd_brief, str, "keyword"),
        "draft": (cmd_draft, int, "brief_id"),
        "factcheck": (cmd_factcheck, int, "article_id"),
        "seo": (cmd_seo, int, "article_id"),
        "publish": (cmd_publish, int, "article_id"),
        "revise": (cmd_revise, int, "article_id"),
        "full": (cmd_full, str, "keyword"),
    }

    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print(f"   Available: {', '.join(commands.keys())}")
        return 1

    if len(sys.argv) < 3:
        func, arg_type, arg_name = commands[command]
        print(f"❌ Missing argument: {arg_name}")
        return 1

    func, arg_type, _ = commands[command]
    arg = arg_type(sys.argv[2])

    try:
        result = func(arg)
        return 0 if result else 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
