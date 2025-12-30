"""Apache Airflow DAG for content generation pipeline.

Orchestrates the complete article generation workflow from
keyword research to publishing.
"""

from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from airflow.sensors.external_task import ExternalTaskSensor

# Default arguments for the DAG
default_args = {
    "owner": "blog_automation",
    "depends_on_past": False,
    "email": ["admin@example.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}


def fetch_keyword_task(**context) -> dict[str, Any]:
    """Fetch next keyword from content calendar."""
    from blog_automation.pipelines.keyword_research import get_next_keyword_from_calendar

    result = get_next_keyword_from_calendar()

    if not result:
        raise ValueError("No keywords available in calendar")

    # Push to XCom for downstream tasks
    context["ti"].xcom_push(key="keyword_data", value=result)
    return result


def generate_brief_task(**context) -> dict[str, Any]:
    """Generate content brief from keyword."""
    from blog_automation.pipelines.brief_generation import research_keyword_full

    # Get keyword from upstream
    keyword_data = context["ti"].xcom_pull(
        task_ids="fetch_keyword", key="keyword_data"
    )
    keyword = keyword_data["keyword"]

    brief = research_keyword_full(keyword)

    result = {
        "brief_id": brief.id,
        "keyword": brief.keyword,
        "sections": len(brief.get_sections()),
    }

    context["ti"].xcom_push(key="brief_data", value=result)
    return result


def generate_draft_task(**context) -> dict[str, Any]:
    """Generate article draft from brief."""
    from blog_automation.models import ContentBrief, get_session
    from blog_automation.pipelines.drafting import content_brief_to_draft

    # Get brief from upstream
    brief_data = context["ti"].xcom_pull(
        task_ids="generate_brief", key="brief_data"
    )

    with get_session() as session:
        brief = session.query(ContentBrief).get(brief_data["brief_id"])
        article = content_brief_to_draft(brief)

        result = {
            "article_id": article.id,
            "word_count": article.word_count,
            "cost": article.ai_generation_cost,
        }

    context["ti"].xcom_push(key="article_data", value=result)
    return result


def fact_check_task(**context) -> dict[str, Any]:
    """Run fact-checking on article."""
    from blog_automation.models import Article, get_session
    from blog_automation.pipelines.fact_checking import fact_check_article

    # Get article from upstream
    article_data = context["ti"].xcom_pull(
        task_ids="generate_draft", key="article_data"
    )

    with get_session() as session:
        article = session.query(Article).get(article_data["article_id"])
        report = fact_check_article(article)

        result = {
            "article_id": article.id,
            "passed": report["pass"],
            "accuracy": report["accuracy_rate"],
            "issues": len(report["issues_found"]),
        }

    context["ti"].xcom_push(key="fact_check_data", value=result)
    return result


def seo_optimize_task(**context) -> dict[str, Any]:
    """Run SEO optimization on article."""
    from blog_automation.models import Article, get_session
    from blog_automation.pipelines.seo_optimization import seo_optimize_article

    # Get article from upstream
    article_data = context["ti"].xcom_pull(
        task_ids="generate_draft", key="article_data"
    )

    with get_session() as session:
        article = session.query(Article).get(article_data["article_id"])
        optimized = seo_optimize_article(article)

        result = {
            "article_id": optimized.id,
            "seo_score": optimized.seo_score,
            "meta_title": optimized.meta_title,
        }

    context["ti"].xcom_push(key="seo_data", value=result)
    return result


def quality_gates_task(**context) -> dict[str, Any]:
    """Run quality gates on article."""
    from blog_automation.models import Article, get_session
    from blog_automation.pipelines.quality_gates import run_quality_gates

    # Get article from upstream
    article_data = context["ti"].xcom_pull(
        task_ids="generate_draft", key="article_data"
    )

    with get_session() as session:
        article = session.query(Article).get(article_data["article_id"])
        result = run_quality_gates(article)

    context["ti"].xcom_push(key="quality_data", value=result)
    return result


def create_review_task_op(**context) -> dict[str, Any]:
    """Create human review task."""
    from blog_automation.models import Article, get_session
    from blog_automation.review.task_queue import create_review_task

    # Get article from upstream
    article_data = context["ti"].xcom_pull(
        task_ids="generate_draft", key="article_data"
    )

    with get_session() as session:
        article = session.query(Article).get(article_data["article_id"])
        task = create_review_task(article)

        result = {
            "task_id": task.id,
            "article_id": article.id,
            "deadline": task.deadline.isoformat() if task.deadline else None,
        }

    context["ti"].xcom_push(key="review_task_data", value=result)
    return result


def check_review_status(**context) -> str:
    """Check if article has been reviewed and approved."""
    from blog_automation.models import Article, get_session

    article_data = context["ti"].xcom_pull(
        task_ids="generate_draft", key="article_data"
    )

    with get_session() as session:
        article = session.query(Article).get(article_data["article_id"])

        if article.status == "approved":
            return "publish_article"
        elif article.status == "rejected":
            return "handle_rejection"
        else:
            return "wait_for_review"


def publish_article_task(**context) -> dict[str, Any]:
    """Publish approved article to WordPress."""
    from blog_automation.models import Article, get_session
    from blog_automation.pipelines.publishing import publish_article

    article_data = context["ti"].xcom_pull(
        task_ids="generate_draft", key="article_data"
    )

    with get_session() as session:
        article = session.query(Article).get(article_data["article_id"])
        published = publish_article(article)

        result = {
            "article_id": published.id,
            "wordpress_post_id": published.wordpress_post_id,
            "url": published.wordpress_url,
        }

    context["ti"].xcom_push(key="publish_data", value=result)
    return result


def complete_task(**context) -> dict[str, Any]:
    """Mark pipeline as complete and log results."""
    article_data = context["ti"].xcom_pull(
        task_ids="generate_draft", key="article_data"
    )
    publish_data = context["ti"].xcom_pull(
        task_ids="publish_article", key="publish_data"
    )

    return {
        "status": "complete",
        "article_id": article_data["article_id"],
        "wordpress_url": publish_data.get("url") if publish_data else None,
    }


# Create the DAG
with DAG(
    dag_id="content_generation_pipeline",
    default_args=default_args,
    description="Automated blog content generation pipeline",
    schedule_interval="0 8 * * *",  # Daily at 8 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["content", "blog", "automation"],
) as dag:

    # Task 1: Fetch keyword from calendar
    fetch_keyword = PythonOperator(
        task_id="fetch_keyword",
        python_callable=fetch_keyword_task,
        provide_context=True,
    )

    # Task 2: Generate content brief
    generate_brief = PythonOperator(
        task_id="generate_brief",
        python_callable=generate_brief_task,
        provide_context=True,
    )

    # Task 3: Generate article draft
    generate_draft = PythonOperator(
        task_id="generate_draft",
        python_callable=generate_draft_task,
        provide_context=True,
    )

    # Task 4: Fact-check article
    fact_check = PythonOperator(
        task_id="fact_check",
        python_callable=fact_check_task,
        provide_context=True,
    )

    # Task 5: SEO optimization
    seo_optimize = PythonOperator(
        task_id="seo_optimize",
        python_callable=seo_optimize_task,
        provide_context=True,
    )

    # Task 6: Quality gates
    quality_gates = PythonOperator(
        task_id="quality_gates",
        python_callable=quality_gates_task,
        provide_context=True,
    )

    # Task 7: Create review task
    create_review = PythonOperator(
        task_id="create_review_task",
        python_callable=create_review_task_op,
        provide_context=True,
    )

    # Task 8: Publish article (after manual approval)
    publish_article_op = PythonOperator(
        task_id="publish_article",
        python_callable=publish_article_task,
        provide_context=True,
    )

    # Task 9: Complete pipeline
    complete = PythonOperator(
        task_id="complete",
        python_callable=complete_task,
        provide_context=True,
    )

    # Define task dependencies
    fetch_keyword >> generate_brief >> generate_draft
    generate_draft >> [fact_check, seo_optimize]
    [fact_check, seo_optimize] >> quality_gates
    quality_gates >> create_review
    create_review >> publish_article_op >> complete
