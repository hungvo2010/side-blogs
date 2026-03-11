"""
AI Blog Automation - Streamlit Dashboard
=========================================
Web UI for reviewing articles, managing content calendar, and monitoring pipeline.

Run with: streamlit run streamlit_app/app.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(
    page_title="AI Blog Automation",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
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
""", unsafe_allow_html=True)


def init_db():
    """Initialize database connection."""
    import os
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./blog_automation.db")
    
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
        tasks = session.query(ReviewTask).filter(
            ReviewTask.status.in_(["pending", "in_review"])
        ).all()
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


# Sidebar Navigation
st.sidebar.title("📝 AI Blog Automation")
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "📋 Review Queue", "📄 All Articles", "📅 Content Calendar", "⚙️ Settings"]
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
        st.sidebar.metric("Pending Review", len([a for a in articles if a["status"] == "pending_review"]))
        st.sidebar.metric("Published", len([a for a in articles if a["status"] == "published"]))
    except:
        st.sidebar.info("No articles yet")


# ============================================================================
# DASHBOARD PAGE
# ============================================================================
if page == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.markdown("Overview of your AI blog automation pipeline")
    
    col1, col2, col3, col4 = st.columns(4)
    
    if db_connected:
        try:
            articles = get_articles()
            with col1:
                st.metric("📄 Total Articles", len(articles))
            with col2:
                st.metric("⏳ Pending Review", len([a for a in articles if a["status"] == "pending_review"]))
            with col3:
                st.metric("✅ Published", len([a for a in articles if a["status"] == "published"]))
            with col4:
                avg_seo = sum(a["seo_score"] or 0 for a in articles) / max(len(articles), 1)
                st.metric("📊 Avg SEO Score", f"{avg_seo:.0f}")
        except Exception as e:
            st.info("No data yet. Run the pipeline to generate articles.")
    
    st.markdown("---")
    
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
                            st.markdown(f"**{article['title'] or 'Untitled'}**")
                            st.caption(f"Keyword: {article['keyword']}")
                        with col2:
                            status_color = {
                                "draft": "🟡",
                                "pending_review": "🟠",
                                "approved": "🟢",
                                "published": "✅",
                                "rejected": "🔴"
                            }.get(article["status"], "⚪")
                            st.markdown(f"{status_color} {article['status']}")
                        with col3:
                            st.markdown(f"SEO: {article['seo_score'] or 'N/A'}")
                        st.markdown("---")
            else:
                st.info("No articles yet. Start by running the pipeline!")
        except:
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
            st.info("Run: `poetry run python scripts/run_pipeline.py full --keyword 'your-keyword'`")
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
                        import subprocess
                        st.info(f"🚀 Launching pipeline for: {new_kw}...")
                        try:
                            # Run as background process so it doesn't block UI
                            subprocess.Popen(["python", "scripts/run_pipeline.py", "full", new_kw])
                            st.success("Pipeline started! Check back in a few minutes.")
                            st.session_state["show_new_article"] = False
                        except Exception as e:
                            st.error(f"Failed to start pipeline: {e}")
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
    st.markdown("Review and approve articles before publishing")
    
    if not db_connected:
        st.error("Database not connected")
    else:
        try:
            articles = [a for a in get_articles() if a["status"] in ["pending_review", "draft", "fact_checked", "seo_optimized"]]
            
            if not articles:
                st.success("🎉 No articles pending review!")
                st.info("All caught up! Run the pipeline to generate new articles.")
            else:
                st.info(f"📬 {len(articles)} article(s) awaiting review")
                
                for article in articles:
                    with st.expander(f"📄 {article['title'] or 'Untitled'} - {article['keyword']}", expanded=False):
                        
                        # Article Info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Word Count", article["word_count"] or "N/A")
                        with col2:
                            st.metric("SEO Score", article["seo_score"] or "N/A")
                        with col3:
                            st.metric("Status", article["status"])
                        
                        # Tabs for different views
                        tab1, tab2, tab3, tab4 = st.tabs(["📝 Content", "✅ Fact-Check", "📊 SEO", "🎯 Decision"])
                        
                        with tab1:
                            st.markdown("### Content Preview")
                            if article["meta_title"]:
                                st.markdown(f"**Meta Title:** {article['meta_title']}")
                            if article["meta_description"]:
                                st.markdown(f"**Meta Description:** {article['meta_description']}")
                            st.markdown("---")
                            content = article["content_draft"] or "No content yet"
                            st.markdown(content[:3000] + "..." if len(content) > 3000 else content)
                        
                        with tab2:
                            st.markdown("### Fact-Check Report")
                            if article["fact_check_report"]:
                                report = article["fact_check_report"]
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Claims Checked", report.get("total_claims_checked", 0))
                                with col2:
                                    st.metric("Accuracy", f"{report.get('accuracy_rate', 0):.1f}%")
                                with col3:
                                    passed = report.get("pass", False)
                                    st.metric("Status", "✅ Passed" if passed else "❌ Failed")
                                
                                if report.get("issues_found"):
                                    st.markdown("#### Issues Found")
                                    for issue in report["issues_found"]:
                                        st.warning(f"**Claim:** {issue.get('claim', 'Unknown')[:100]}...\n\n**Verdict:** {issue.get('verdict')}")
                            else:
                                st.info("No fact-check report available")
                        
                        with tab3:
                            st.markdown("### SEO Analysis")
                            if article["seo_analysis"]:
                                analysis = article["seo_analysis"]
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Score", f"{analysis.get('score', 0)}/100")
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
                                placeholder="Enter any feedback or revision notes..."
                            )
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("✅ Approve", key=f"approve_{article['id']}", type="primary", use_container_width=True):
                                    if update_article_status(article["id"], "approved", feedback):
                                        st.success("Article approved!")
                                        st.rerun()
                            with col2:
                                if st.button("📝 Request Revision", key=f"revise_{article['id']}", use_container_width=True):
                                    if update_article_status(article["id"], "revision_requested", feedback):
                                        st.warning("Revision requested")
                                        st.rerun()
                            with col3:
                                if st.button("❌ Reject", key=f"reject_{article['id']}", use_container_width=True):
                                    if update_article_status(article["id"], "rejected", feedback):
                                        st.error("Article rejected")
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
                    ["All", "draft", "pending_review", "approved", "published", "rejected"]
                )
            with col2:
                search = st.text_input("Search by keyword")
            
            # Apply filters
            if status_filter != "All":
                articles = [a for a in articles if a["status"] == status_filter]
            if search:
                articles = [a for a in articles if search.lower() in (a["keyword"] or "").lower()]
            
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
                        if st.button("📄 Export to Static HTML", use_container_width=True):
                            import subprocess
                            try:
                                # Run the export script
                                subprocess.run(["python", "scripts/export_static.py", str(article["id"])], check=True)
                                st.success(f"Successfully exported to dist/{article['keyword'].replace(' ', '-')}.html")
                                st.info(f"View at: file://{Path(__file__).parent.parent}/dist/{article['keyword'].replace(' ', '-')}.html")
                            except Exception as e:
                                st.error(f"Export failed: {e}")
                    
                    with col_act2:
                        st.button("🚀 Publish to WordPress", disabled=True, use_container_width=True, help="Configure WordPress API keys to enable")

                    tab1, tab2, tab3 = st.tabs(["📝 Content", "✅ Fact-Check", "📊 SEO"])
                    
                    with tab1:
                        st.markdown("### Content Preview")
                        if article["meta_title"]:
                            st.markdown(f"**Meta Title:** {article['meta_title']}")
                        if article["meta_description"]:
                            st.markdown(f"**Meta Description:** {article['meta_description']}")
                        st.markdown("---")
                        st.markdown(article["content_draft"] or "No content yet")
                    
                    with tab2:
                        st.markdown("### Fact-Check Report")
                        if article["fact_check_report"]:
                            report = article["fact_check_report"]
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Claims Checked", report.get("total_claims_checked", 0))
                            c2.metric("Accuracy", f"{report.get('accuracy_rate', 0):.1f}%")
                            c3.metric("Status", "✅ Passed" if report.get("pass") else "❌ Failed")
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
                            st.markdown(f"**{article['title'] or 'Untitled'}**")
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
                                "rejected": "🔴"
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
            date_input = st.date_input("Scheduled Date", datetime.now() + timedelta(days=7))
        
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
                        status="planned"
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
        entries = session.query(ContentCalendar).order_by(ContentCalendar.scheduled_date.asc()).all()
        
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
                            subprocess.Popen(["python", "scripts/run_pipeline.py", "full", entry.keyword])
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
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
AHREFS_API_KEY=...
PERPLEXITY_API_KEY=...
COPYSCAPE_API_KEY=...
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=...
WORDPRESS_APP_PASSWORD=...
        """)
    
    st.subheader("🗄️ Database")
    st.code(f"DATABASE_URL: {st.session_state.get('db_url', 'sqlite:///./blog_automation.db')}")
    
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


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Made with ❤️ using Streamlit")
