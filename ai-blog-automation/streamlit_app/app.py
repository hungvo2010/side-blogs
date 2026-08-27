"""
AI Blog Automation - Streamlit Dashboard
=========================================
Web UI for reviewing articles, managing content calendar, and monitoring pipeline.

Run with: streamlit run streamlit_app/app.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="AI Blog Automation",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .article-card {
        border: 1px solid #ddd;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .status-pending { color: #ff9800; }
    .status-approved { color: #4caf50; }
    .status-rejected { color: #f44336; }
</style>
""",
    unsafe_allow_html=True,
)

# Disable Streamlit's built-in bare "C" -> Clear cache shortcut.
# Streamlit hardcodes this in its bundled JS with no setting to disable it,
# so we intercept the keydown in the capture phase on the parent window and
# swallow it when the user is not typing in an input/textarea/contenteditable.
components.html(
    """
<script>
(function () {
  const win = window.parent;
  if (win.__cClearCacheDisabled) return;
  win.__cClearCacheDisabled = true;
  win.addEventListener('keydown', function (e) {
    if ((e.key === 'c' || e.key === 'C') &&
        !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
      const t = e.target;
      const tag = t && t.tagName;
      const editing = tag === 'INPUT' || tag === 'TEXTAREA' ||
                      tag === 'SELECT' || (t && t.isContentEditable);
      if (!editing) {
        e.stopPropagation();
        e.stopImmediatePropagation();
        e.preventDefault();
      }
    }
  }, true);
})();
</script>
""",
    height=0,
)


def init_db():
    """Initialize database connection.

    DATABASE_URL (and all other settings) are loaded from .env by
    blog_automation.config at import time, so we just build the engine.
    """
    import os

    os.environ.setdefault("ENVIRONMENT", "development")

    from blog_automation.models import get_engine

    engine = get_engine()
    return engine


def get_articles():
    """Get all articles from database."""
    from blog_automation.models import Article, get_session

    with get_session() as session:
        articles = session.query(Article).order_by(Article.created_at.desc()).all()
        return [
            {
                "id": a.id,
                "title": a.title,
                "keyword": a.keyword,
                "status": a.status,
                "word_count": a.word_count,
                "seo_score": a.seo_score,
                "created_at": a.created_at,
                "content_draft": a.content_draft,
                "meta_title": a.meta_title,
                "meta_description": a.meta_description,
                "fact_check_report": a.fact_check_report,
                "seo_analysis": a.seo_analysis,
            }
            for a in articles
        ]


def get_pending_reviews():
    """Get pending review tasks."""
    from blog_automation.models import get_session
    from blog_automation.review.task_queue import ReviewTask

    with get_session() as session:
        tasks = (
            session.query(ReviewTask)
            .filter(ReviewTask.status.in_(["pending", "in_review"]))
            .all()
        )
        return [
            {
                "id": t.id,
                "article_id": t.article_id,
                "status": t.status,
                "assigned_reviewer": t.assigned_reviewer,
                "deadline": t.deadline,
                "created_at": t.created_at,
            }
            for t in tasks
        ]


def update_article_status(article_id: int, new_status: str, feedback: str = None):
    """Update article status."""
    from blog_automation.models import Article, get_session

    with get_session() as session:
        article = session.query(Article).get(article_id)
        if article:
            article.status = new_status
            if feedback:
                article.reviewer_feedback = feedback
            session.commit()
            return True
    return False


def _load_cloudflare_env() -> None:
    """Load Cloudflare credentials from Streamlit secrets into env.

    On Streamlit Cloud there is no .env file — secrets are configured in the
    dashboard (Settings → Secrets). Streamlit exposes them via st.secrets, not
    os.environ, so copy them into env for publish_article (wrangler / Direct
    Upload API both read os.environ).
    """
    import os

    for key in (
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "CLOUDFLARE_PROJECT_NAME",
        "CLOUDFLARE_ZONE_ID",
    ):
        if key in os.environ:
            continue
        try:
            val = st.secrets.get(key)
        except Exception:
            val = None
        if val:
            os.environ[key] = str(val)


def _load_llm_env() -> None:
    """Load OPENCODE_* LLM credentials (deepseek-v4-flash) into env from secrets."""
    secrets = st.secrets if hasattr(st, "secrets") else {}
    for env_key in ("OPENCODE_BASE_URL", "OPENCODE_API_KEY", "OPENCODE_MODEL"):
        if env_key not in os.environ:
            try:
                val = secrets.get(env_key)
            except Exception:
                val = None
            if val:
                os.environ[env_key] = str(val)


def _regenerate_layout_block(article_id: int, block_idx: int, instruction: str) -> dict:
    """Regenerate ONE layout block via the LLM and persist updated content_draft.

    Returns the new block dict. Other content is untouched.
    """
    from blog_automation.integrations.openrouter_client import OpenRouterClient
    from blog_automation.layouts import regenerate_block
    from blog_automation.models import Article, get_session

    _load_llm_env()
    llm = OpenRouterClient()
    with get_session() as s:
        a = s.query(Article).get(article_id)
        md = a.content_draft or ""
        new_md, new_block = regenerate_block(
            llm, md, block_idx, instruction or "Improve this layout block"
        )
        a.content_draft = new_md
        s.commit()
    return new_block


def _approve_and_publish(article_id: int) -> dict:
    """Approve article and deploy to Cloudflare Pages.

    Returns the publish result dict (slug/url/deploy_method) and marks the
    article published in the DB **only if the deploy was confirmed**. Raises
    RuntimeError with an actionable message otherwise (article stays pending
    review so it can be retried).
    """
    _load_cloudflare_env()

    from datetime import datetime, timezone

    from blog_automation.models import Article, get_session
    from blog_automation.pipelines.phase_8_publish import publish_article

    with get_session() as s:
        a = s.get(Article, article_id)
        if not a:
            raise RuntimeError(f"Article {article_id} not found")
        result = publish_article(
            title=a.title or a.keyword,
            content=a.content_draft or "",
            keyword=a.keyword or "",
            image=a.featured_image_url or "",
            auto_push=True,
        )
        if not result.get("pushed"):
            raise RuntimeError(
                "Article was built but the Cloudflare deploy was NOT confirmed "
                f"(deploy method: {result.get('deploy_method', 'none')}). "
                "Add `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` to "
                "**Streamlit secrets** (Settings → Secrets) or `.env`, then click "
                "Approve again. The article is still pending review."
            )
        a.status = "published"
        a.published_date = datetime.now(timezone.utc)
        s.commit()
        return result


def _run_pipeline_inprocess(keyword: str) -> None:
    """Run full pipeline inside Streamlit — no subprocess needed."""
    import traceback

    from blog_automation.models import get_session
    from blog_automation.pipelines import (
        content_brief_to_draft,
        generate_content_brief,
        research_keyword,
        run_quality_gates,
    )

    progress = st.status(f"Running pipeline: **{keyword}**", expanded=True)

    try:
        progress.write("🔍 Phase 1: Research...")
        brief = research_keyword(keyword)
        progress.write(f"✅ Research done — volume: {brief.search_volume}, difficulty: {brief.difficulty}")

        progress.write("📝 Phase 2: Content brief...")
        full_brief = generate_content_brief(keyword, brief.id)
        progress.write(f"✅ Brief done — {len(full_brief.get_sections())} sections")

        progress.write("✍️ Phase 3: Drafting...")
        article = content_brief_to_draft(full_brief)
        progress.write(f"✅ Draft done — {article.word_count} words")

        progress.write("🔬 Phase 4: Fact checking... ⏭️ skipped (free model)")
        progress.write("📈 Phase 5: SEO optimization... ⏭️ skipped (free model)")

        progress.write("🛡️ Phase 6: Quality gates...")
        run_quality_gates(article)
        progress.write(f"✅ Quality done — status: {article.status}")

        # Stop here — human must approve in Review Queue before publishing
        from blog_automation.models import get_session
        with get_session() as s:
            a = s.merge(article)
            a.status = "pending_review"
            s.commit()
        progress.write("⏳ Go to Review Queue → Approve to publish")

        progress.update(label=f"✅ Ready for review: **{keyword}**", state="complete")
        st.session_state["show_new_article"] = False

    except Exception as e:
        progress.update(label=f"❌ Failed: {str(e)[:100]}", state="error")
        st.error(f"```\n{traceback.format_exc()[:1000]}\n```")


PIPELINE_STEPS = ["research", "brief", "draft", "fact_check", "seo", "quality_gates"]

_STEP_LABELS = {
    "research": "Research",
    "brief": "Brief",
    "draft": "Draft",
    "fact_check": "Fact-check",
    "seo": "SEO",
    "quality_gates": "Quality gates",
}

_PROGRESS_STATUSES = [
    "researching",
    "briefing",
    "drafting",
    "fact_checking",
    "seo_review",
    "quality_gates",
    "draft",
    "failed",
]


def get_failed_pipeline_articles(limit: int = 10) -> list[dict]:
    """Get articles whose pipeline run failed (for toast notifications)."""
    from blog_automation.models import Article, get_session

    with get_session() as session:
        rows = (
            session.query(Article)
            .filter(Article.status == "failed")
            .order_by(Article.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": a.id,
                "keyword": a.keyword,
                "title": a.title,
                "pipeline_error": a.pipeline_error,
            }
            for a in rows
        ]


def get_pipeline_progress_articles(limit: int = 10) -> list[dict]:
    """Get in-progress / recently run articles for the progress view."""
    from blog_automation.models import Article, get_session

    with get_session() as session:
        rows = (
            session.query(Article)
            .filter(Article.status.in_(_PROGRESS_STATUSES))
            .order_by(Article.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": a.id,
                "keyword": a.keyword,
                "title": a.title,
                "status": a.status,
                "pipeline_progress": a.pipeline_progress or {},
                "pipeline_error": a.pipeline_error,
            }
            for a in rows
        ]


def render_pipeline_toasts():
    """Surface failed pipeline runs as non-blocking toast notifications.

    Each failed article is toasted only once per Streamlit session (tracked
    via session_state) to avoid repeating on every rerun. The persistent
    banner (render_pipeline_failure_banner) remains the always-visible display.
    """
    if not db_connected:
        return
    try:
        toasted = st.session_state.setdefault("_toasted_article_ids", set())
        for a in get_failed_pipeline_articles(limit=5):
            if a["id"] in toasted:
                continue
            st.toast(a["pipeline_error"] or "Pipeline failed", icon="❌")
            toasted.add(a["id"])
    except Exception:
        pass


def render_pipeline_failure_banner():
    """Show a persistent, prominent banner of recent failed pipeline runs.

    Unlike toasts, this stays visible on every dashboard render so the user
    always sees what failed (even if they were away when it happened).
    """
    if not db_connected:
        return
    try:
        failed = get_failed_pipeline_articles(limit=5)
    except Exception:
        return
    if not failed:
        return
    with st.container(border=True):
        st.warning(f"⚠️ {len(failed)} pipeline run(s) failed recently")
        for a in failed:
            st.error(
                f"**{a['title'] or a['keyword']}** (keyword: {a['keyword']}) — "
                f"{a['pipeline_error'] or 'Pipeline failed'}"
            )


def render_pipeline_progress_view():
    """Render a progress bar + per-step list for in-progress (non-failed) articles."""
    if not db_connected:
        return
    try:
        articles = [
            a
            for a in get_pipeline_progress_articles(limit=5)
            if a["status"] != "failed"
        ]
    except Exception:
        return
    if not articles:
        return
    st.subheader("🛠️ Pipeline Progress")
    for a in articles:
        prog = a["pipeline_progress"] or {}
        done = sum(1 for s in PIPELINE_STEPS if prog.get(s) == "done")
        total = len(PIPELINE_STEPS)
        with st.container():
            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown(f"**{a['title'] or a['keyword']}**")
                st.caption(f"Keyword: {a['keyword']} · Status: {a['status']}")
            with col2:
                st.progress(done / total)
                st.caption(f"{done}/{total} steps done")
            parts = []
            for step in PIPELINE_STEPS:
                state = prog.get(step, "pending")
                icon = {"done": "✅", "failed": "❌", "pending": "⏳"}.get(state, "⏳")
                parts.append(f"{icon} {_STEP_LABELS[step]}")
            st.markdown("  ·  ".join(parts))
            st.markdown("---")


# Sidebar Navigation
st.sidebar.title("📝 AI Blog Automation")
page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "📋 Review Queue",
        "📄 All Articles",
        "📅 Content Calendar",
        "⚙️ Settings",
    ],
)

# Initialize database
try:
    init_db()
    db_connected = True
except Exception as e:
    db_connected = False
    st.sidebar.error(f"DB Error: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Stats")
if db_connected:
    try:
        articles = get_articles()
        st.sidebar.metric("Total Articles", len(articles))
        st.sidebar.metric(
            "Pending Review",
            len([a for a in articles if a["status"] == "pending_review"]),
        )
        st.sidebar.metric(
            "Published", len([a for a in articles if a["status"] == "published"])
        )
    except Exception:
        st.sidebar.info("No articles yet")


# ============================================================================
# DASHBOARD PAGE
# ============================================================================
if page == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.markdown("Overview of your AI blog automation pipeline")

    render_pipeline_toasts()
    render_pipeline_failure_banner()

    col1, col2, col3, col4 = st.columns(4)

    if db_connected:
        try:
            articles = get_articles()
            with col1:
                st.metric("📄 Total Articles", len(articles))
            with col2:
                st.metric(
                    "⏳ Pending Review",
                    len([a for a in articles if a["status"] == "pending_review"]),
                )
            with col3:
                st.metric(
                    "✅ Published",
                    len([a for a in articles if a["status"] == "published"]),
                )
            with col4:
                avg_seo = sum(a["seo_score"] or 0 for a in articles) / max(
                    len(articles), 1
                )
                st.metric("📊 Avg SEO Score", f"{avg_seo:.0f}")
        except Exception:
            st.info("No data yet. Run the pipeline to generate articles.")

    st.markdown("---")

    render_pipeline_progress_view()

    # Recent Activity
    st.subheader("📈 Recent Activity")

    if db_connected:
        try:
            articles = get_articles()[:5]
            if articles:
                for article in articles:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            title = article['title'] or 'Untitled'
                            if article['status'] == 'published':
                                slug = (article.get('keyword', '') or '').replace(' ', '-').lower()
                                url = f"https://side-blogs.pages.dev/{slug}"
                                st.markdown(f"**[{title}]({url})**")
                            else:
                                st.markdown(f"**{title}**")
                            st.caption(f"Keyword: {article['keyword']}")
                        with col2:
                            status_color = {
                                "draft": "🟡",
                                "pending_review": "🟠",
                                "approved": "🟢",
                                "published": "✅",
                                "rejected": "🔴",
                            }.get(article["status"], "⚪")
                            st.markdown(f"{status_color} {article['status']}")
                        with col3:
                            st.markdown(f"SEO: {article['seo_score'] or 'N/A'}")
                        st.markdown("---")
            else:
                st.info("No articles yet. Start by running the pipeline!")
        except Exception:
            st.info("No articles yet.")

    # Quick Actions
    st.subheader("🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 New Article", use_container_width=True):
            st.session_state["show_new_article"] = True
            st.rerun()
    with col2:
        if st.button("🔄 Run Pipeline", use_container_width=True):
            st.session_state["show_new_article"] = True
            st.rerun()
    with col3:
        if st.button("📅 Plan Content", use_container_width=True):
            st.session_state["page"] = "📅 Content Calendar"
            st.rerun()

    if st.session_state.get("show_new_article"):
        with st.form("quick_new_article"):
            st.subheader("📝 Quick New Article")
            new_kw = st.text_input("Target Keyword")
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("🚀 Start Automation"):
                    if new_kw:
                        _run_pipeline_inprocess(new_kw)
                    else:
                        st.error("Please enter a keyword")
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    st.session_state["show_new_article"] = False
                    st.rerun()


# ============================================================================
# REVIEW QUEUE PAGE
# ============================================================================
elif page == "📋 Review Queue":
    st.title("📋 Review Queue")
    st.markdown("Review and approve articles, then push them live to Cloudflare Pages")

    # Surface the result of the last Approve & Publish action across reruns.
    _review_msg = st.session_state.pop("_review_msg", None)
    if _review_msg:
        kind, text = _review_msg
        if kind == "success":
            st.success(text)
        else:
            st.error(text)

    render_pipeline_toasts()
    render_pipeline_failure_banner()

    if not db_connected:
        st.error("Database not connected")
    else:
        try:
            articles = [
                a
                for a in get_articles()
                if a["status"]
                in ["pending_review", "draft", "fact_checked", "seo_optimized"]
            ]

            if not articles:
                st.success("🎉 No articles pending review!")
                st.info("All caught up! Run the pipeline to generate new articles.")
            else:
                st.info(f"📬 {len(articles)} article(s) awaiting review")

                for article in articles:
                    with st.expander(
                        f"📄 {article['title'] or 'Untitled'} - {article['keyword']}",
                        expanded=False,
                    ):
                        # Article Info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Word Count", article["word_count"] or "N/A")
                        with col2:
                            st.metric("SEO Score", article["seo_score"] or "N/A")
                        with col3:
                            st.metric("Status", article["status"])

                        # Tabs for different views
                        tab1, tab2, tab3, tab4, tab5 = st.tabs(
                            [
                                "📝 Content",
                                "✅ Fact-Check",
                                "📊 SEO",
                                "🎯 Decision",
                                "🧩 Layout Blocks",
                            ]
                        )

                        with tab1:
                            st.markdown("### Content Preview")
                            if article["meta_title"]:
                                st.markdown(f"**Meta Title:** {article['meta_title']}")
                            if article["meta_description"]:
                                desc = article["meta_description"]
                                st.markdown(f"**Meta Description:** {desc}")
                            st.markdown("---")
                            content = article["content_draft"] or "No content yet"
                            st.markdown(
                                content[:3000] + "..."
                                if len(content) > 3000
                                else content
                            )

                        with tab2:
                            st.markdown("### Fact-Check Report")
                            if article["fact_check_report"]:
                                report = article["fact_check_report"]
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric(
                                        "Claims Checked",
                                        report.get("total_claims_checked", 0),
                                    )
                                with col2:
                                    st.metric(
                                        "Accuracy",
                                        f"{report.get('accuracy_rate', 0):.1f}%",
                                    )
                                with col3:
                                    passed = report.get("pass", False)
                                    st.metric(
                                        "Status", "✅ Passed" if passed else "❌ Failed"
                                    )

                                if report.get("issues_found"):
                                    st.markdown("#### Issues Found")
                                    for issue in report["issues_found"]:
                                        claim = issue.get("claim", "Unknown")[:100]
                                        verdict = issue.get("verdict")
                                        st.warning(
                                            f"**Claim:** {claim}...\n\n"
                                            f"**Verdict:** {verdict}"
                                        )
                            else:
                                st.info("No fact-check report available")

                        with tab3:
                            st.markdown("### SEO Analysis")
                            if article["seo_analysis"]:
                                analysis = article["seo_analysis"]
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric(
                                        "Score", f"{analysis.get('score', 0)}/100"
                                    )
                                with col2:
                                    st.metric("Grade", analysis.get("grade", "N/A"))

                                if analysis.get("issues"):
                                    st.markdown("#### Issues")
                                    for issue in analysis["issues"][:5]:
                                        st.warning(issue)

                                if analysis.get("suggestions"):
                                    st.markdown("#### Suggestions")
                                    for suggestion in analysis["suggestions"][:5]:
                                        st.info(suggestion)
                            else:
                                st.info("No SEO analysis available")

                        with tab4:
                            st.markdown("### Make Decision")

                            feedback = st.text_area(
                                "Feedback (optional)",
                                key=f"feedback_{article['id']}",
                                placeholder="Enter any feedback or revision notes...",
                            )

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button(
                                    "🚀 Approve & Publish to Cloudflare",
                                    key=f"approve_{article['id']}",
                                    type="primary",
                                    use_container_width=True,
                                    help="Build the static site and deploy it to Cloudflare Pages",
                                ):
                                    try:
                                        with st.spinner(
                                            "Building site & deploying to Cloudflare Pages…"
                                        ):
                                            result = _approve_and_publish(
                                                article["id"]
                                            )
                                        method = result.get("deploy_method", "none")
                                        url = result.get("url", "")
                                        if result.get("pushed"):
                                            msg = (
                                                f"✅ **Published & pushed live** — "
                                                f"[{result.get('slug', 'article')}]({url}) "
                                                f"via {method}"
                                            )
                                        else:
                                            msg = (
                                                "⚠️ Article saved & marked published, "
                                                f"but the Cloudflare deploy wasn't confirmed "
                                                f"(deploy method: {method}). Set "
                                                "`CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` "
                                                "in **Streamlit secrets** (Settings → Secrets) "
                                                "or `.env`, then deploy again."
                                            )
                                        st.session_state["_review_msg"] = ("success", msg)
                                    except Exception as e:
                                        st.session_state["_review_msg"] = (
                                            "error",
                                            f"❌ Publish failed: {e}",
                                        )
                                    st.rerun()
                            with col2:
                                if st.button(
                                    "📝 Request Revision",
                                    key=f"revise_{article['id']}",
                                    use_container_width=True,
                                ):
                                    if update_article_status(
                                        article["id"], "revision_requested", feedback
                                    ):
                                        st.warning("Revision requested")
                                        st.rerun()
                            with col3:
                                if st.button(
                                    "❌ Reject",
                                    key=f"reject_{article['id']}",
                                    use_container_width=True,
                                ):
                                    if update_article_status(
                                        article["id"], "rejected", feedback
                                    ):
                                        st.error("Article rejected")
                                        st.rerun()

                            with tab5:
                                st.markdown("### 🧩 Layout Blocks")
                                from blog_automation.layouts import parse_directives

                                _blocks = parse_directives(
                                    article.get("content_draft") or ""
                                )
                                if not _blocks:
                                    st.info(
                                        "Bài chưa có layout block. Bài mới chạy pipeline "
                                        "(Phase 3.5) sẽ tự sinh bảng so sánh / "
                                        "recipe / FAQ."
                                    )
                                else:
                                    _llm_ok = bool(
                                        os.environ.get("OPENCODE_API_KEY")
                                        or getattr(st, "secrets", {}).get(
                                            "OPENCODE_API_KEY"
                                        )
                                    )
                                    if not _llm_ok:
                                        st.warning(
                                            "⚠️ Chưa cấu hình OPENCODE_API_KEY trong "
                                            "Streamlit secrets (Settings → Secrets) — "
                                            "chưa regenerate block được."
                                        )
                                    for bi, blk in enumerate(_blocks):
                                        _btype = blk.get("type", "?")
                                        with st.expander(
                                            f"Block {bi + 1}: {_btype}", expanded=False
                                        ):
                                            st.json(
                                                {k: v for k, v in blk.items() if k != "type"}
                                            )
                                            _inst = st.text_input(
                                                "Hướng dẫn regenerate (bỏ trống = cải thiện)",
                                                key=f"regen_inst_{article['id']}_{bi}",
                                            )
                                            if st.button(
                                                f"♻️ Regenerate block {bi + 1}",
                                                key=f"regen_btn_{article['id']}_{bi}",
                                            ):
                                                if not _llm_ok:
                                                    st.error("Thiếu OPENCODE_API_KEY secret")
                                                else:
                                                    try:
                                                        with st.spinner(
                                                            "Đang regenerate block…"
                                                        ):
                                                            nb = _regenerate_layout_block(
                                                                article["id"], bi, _inst
                                                            )
                                                        st.session_state["_review_msg"] = (
                                                            "success",
                                                            f"Regenerate block {bi + 1} "
                                                            f"({_btype}) ✅ — mới: "
                                                            f"{list(nb.keys())}",
                                                        )
                                                    except Exception as e2:
                                                        st.session_state["_review_msg"] = (
                                                            "error",
                                                            f"Regenerate lỗi: {e2}",
                                                        )
                                                    st.rerun()

        except Exception as e:
            st.error(f"Error loading articles: {e}")


# ============================================================================
# ALL ARTICLES PAGE
# ============================================================================
elif page == "📄 All Articles":
    st.title("📄 All Articles")

    if not db_connected:
        st.error("Database not connected")
    else:
        try:
            articles = get_articles()

            # Filters
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    [
                        "All",
                        "draft",
                        "pending_review",
                        "approved",
                        "published",
                        "rejected",
                    ],
                )
            with col2:
                search = st.text_input("Search by keyword")

            # Apply filters
            if status_filter != "All":
                articles = [a for a in articles if a["status"] == status_filter]
            if search:
                articles = [
                    a
                    for a in articles
                    if search.lower() in (a["keyword"] or "").lower()
                ]

            st.markdown(f"**{len(articles)} article(s) found**")

            # Show article details if one is selected
            if "selected_article" in st.session_state:
                selected_id = st.session_state["selected_article"]
                article = next((a for a in articles if a["id"] == selected_id), None)

                if article:
                    st.markdown("---")
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.subheader(f"📄 {article['title'] or 'Untitled'}")
                    with col2:
                        if st.button("⬅️ Back to List"):
                            del st.session_state["selected_article"]
                            st.rerun()

                    # Article Info Metrics
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Status", article["status"])
                    m2.metric("Word Count", article["word_count"] or 0)
                    m3.metric("SEO Score", article["seo_score"] or "N/A")
                    m4.metric("Keyword", article["keyword"])

                    # Quick Actions for Article
                    st.markdown("### 🛠️ Article Actions")
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if st.button(
                            "📄 Export to Static HTML", use_container_width=True
                        ):
                            import subprocess

                            try:
                                # Run the export script
                                subprocess.run(
                                    [
                                        "python",
                                        "scripts/export_static.py",
                                        str(article["id"]),
                                    ],
                                    check=True,
                                )
                                slug = article["keyword"].replace(" ", "-")
                                st.success(f"Successfully exported to dist/{slug}.html")
                                dist_dir = Path(__file__).parent.parent / "dist"
                                st.info(f"View at: file://{dist_dir / f'{slug}.html'}")
                            except Exception as e:
                                st.error(f"Export failed: {e}")

                    with col_act2:
                        st.button(
                            "🚀 Publish to WordPress",
                            disabled=True,
                            use_container_width=True,
                            help="Configure WordPress API keys to enable",
                        )

                    tab1, tab2, tab3 = st.tabs(
                        ["📝 Content", "✅ Fact-Check", "📊 SEO"]
                    )

                    with tab1:
                        st.markdown("### Content Preview")
                        if article["meta_title"]:
                            st.markdown(f"**Meta Title:** {article['meta_title']}")
                        if article["meta_description"]:
                            st.markdown(
                                f"**Meta Description:** {article['meta_description']}"
                            )
                        st.markdown("---")
                        st.markdown(article["content_draft"] or "No content yet")

                    with tab2:
                        st.markdown("### Fact-Check Report")
                        if article["fact_check_report"]:
                            report = article["fact_check_report"]
                            c1, c2, c3 = st.columns(3)
                            c1.metric(
                                "Claims Checked", report.get("total_claims_checked", 0)
                            )
                            c2.metric(
                                "Accuracy", f"{report.get('accuracy_rate', 0):.1f}%"
                            )
                            c3.metric(
                                "Status",
                                "✅ Passed" if report.get("pass") else "❌ Failed",
                            )
                        else:
                            st.info("No fact-check report available")

                    with tab3:
                        st.markdown("### SEO Analysis")
                        if article["seo_analysis"]:
                            analysis = article["seo_analysis"]
                            st.metric("Score", f"{analysis.get('score', 0)}/100")
                            if analysis.get("suggestions"):
                                for sug in analysis["suggestions"][:5]:
                                    st.info(sug)
                        else:
                            st.info("No SEO analysis available")

                    st.markdown("---")

            # Articles table
            if articles:
                for article in articles:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                        with col1:
                            title = article['title'] or 'Untitled'
                            if article['status'] == 'published':
                                slug = (article.get('keyword', '') or '').replace(' ', '-').lower()
                                url = f"https://side-blogs.pages.dev/{slug}"
                                st.markdown(f"**[{title}]({url})**")
                            else:
                                st.markdown(f"**{title}**")
                            st.caption(f"Keyword: {article['keyword']}")
                        with col2:
                            st.markdown(f"📊 {article['word_count'] or 0} words")
                        with col3:
                            st.markdown(f"SEO: {article['seo_score'] or 'N/A'}")
                        with col4:
                            status_emoji = {
                                "draft": "🟡",
                                "pending_review": "🟠",
                                "approved": "🟢",
                                "published": "✅",
                                "rejected": "🔴",
                            }.get(article["status"], "⚪")
                            st.markdown(f"{status_emoji} {article['status']}")
                        with col5:
                            if st.button("View", key=f"view_{article['id']}"):
                                st.session_state["selected_article"] = article["id"]
                                st.rerun()
                        st.markdown("---")
            else:
                st.info("No articles found")

        except Exception as e:
            st.error(f"Error: {e}")


# ============================================================================
# CONTENT CALENDAR PAGE
# ============================================================================
elif page == "📅 Content Calendar":
    st.title("📅 Content Calendar")
    st.markdown("Plan and schedule your content")

    from blog_automation.models import ContentCalendar, get_session

    # Add new keyword
    st.subheader("➕ Add New Keyword")
    with st.form("new_keyword"):
        col1, col2 = st.columns(2)
        with col1:
            kw_input = st.text_input("Keyword")
        with col2:
            date_input = st.date_input(
                "Scheduled Date", datetime.now() + timedelta(days=7)
            )

        prio_input = st.selectbox("Priority", ["high", "medium", "low"])
        notes_input = st.text_area("Notes (optional)")

        if st.form_submit_button("Add to Calendar"):
            if kw_input:
                with get_session() as session:
                    new_entry = ContentCalendar(
                        keyword=kw_input,
                        scheduled_date=date_input,
                        priority=prio_input,
                        notes=notes_input,
                        status="planned",
                    )
                    session.add(new_entry)
                    session.commit()
                st.success(f"Added '{kw_input}' to calendar for {date_input}")
                st.rerun()
            else:
                st.error("Please enter a keyword")

    st.markdown("---")

    # Calendar view
    st.subheader("📆 Upcoming Content")
    with get_session() as session:
        entries = (
            session.query(ContentCalendar)
            .order_by(ContentCalendar.scheduled_date.asc())
            .all()
        )

        if not entries:
            st.info("No planned content yet.")
        else:
            for entry in entries:
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 1, 2])
                    c1.markdown(f"**{entry.keyword}**")
                    c2.markdown(f"📅 {entry.scheduled_date.strftime('%Y-%m-%d')}")
                    c3.markdown(f"[{entry.priority.upper()}]")

                    if entry.status == "planned":
                        if c4.button("🚀 Start Automation", key=f"start_{entry.id}"):
                            import subprocess

                            subprocess.Popen(
                                [
                                    "python",
                                    "scripts/run_pipeline.py",
                                    "full",
                                    entry.keyword,
                                ]
                            )
                            # Update status in DB
                            db_entry = session.query(ContentCalendar).get(entry.id)
                            db_entry.status = "in_progress"
                            session.commit()
                            st.success(f"Automation started for {entry.keyword}")
                            st.rerun()
                    else:
                        c4.markdown(f"Status: **{entry.status}**")
                st.markdown("---")


# ============================================================================
# SETTINGS PAGE
# ============================================================================
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.subheader("🔑 API Keys")
    st.info("API keys are configured via environment variables or .env file")

    with st.expander("View Required API Keys"):
        st.code("""
# Required API Keys (.env file)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_DEFAULT_MODEL=openai/gpt-4o
OPENROUTER_SEARCH_MODEL=perplexity/llama-3.1-sonar-large-128k-online
AHREFS_API_KEY=...
COPYSCAPE_API_KEY=...
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=...
WORDPRESS_APP_PASSWORD=...
        """)

    st.subheader("🗄️ Database")
    from blog_automation.config import get_settings

    st.code(f"DATABASE_URL: {get_settings().database_url}")

    st.subheader("📚 Documentation")
    st.markdown("""
    - [QUICKSTART.md](./QUICKSTART.md) - Setup guide
    - [ARTICLE_FLOW.md](./docs/ARTICLE_FLOW.md) - Pipeline documentation
    """)

    st.subheader("🔧 Commands")
    st.code("""
# Run the full pipeline
poetry run python scripts/run_pipeline.py --keyword "your keyword"

# Test integrations
poetry run python scripts/setup_integrations.py

# Run local tests
poetry run python scripts/test_local.py

# Run unit tests
poetry run pytest tests/unit/ -v
    """)

    st.markdown("---")
    st.subheader("⚠️ Danger Zone")
    with st.expander("Delete data — irreversible"):
        st.warning("These actions permanently delete data and cannot be undone.")

        st.markdown("**Delete a single article (cascade)**")
        del_id = st.number_input(
            "Article ID", min_value=1, step=1, key="danger_del_article_id"
        )
        if st.button("🗑️ Delete Article", key="danger_del_article_btn"):
            from blog_automation.models import delete_article_cascade

            if delete_article_cascade(int(del_id)):
                st.success(f"Article {int(del_id)} deleted.")
                st.rerun()
            else:
                st.error(f"Article {int(del_id)} not found.")

        st.markdown("**Clear ALL rows from ALL tables**")
        confirm_text = st.text_input(
            'Type "DELETE ALL" to confirm', key="danger_clear_confirm"
        )
        if st.button("💥 Clear All Tables", key="danger_clear_btn"):
            if confirm_text == "DELETE ALL":
                from blog_automation.models import clear_all_tables

                counts = clear_all_tables()
                deleted = ", ".join(f"{k}: {v}" for k, v in counts.items() if v)
                st.success(f"All tables cleared. Deleted: {deleted or 'nothing'}")
                st.rerun()
            else:
                st.error('You must type "DELETE ALL" exactly to confirm.')


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Made with ❤️ using Streamlit")
