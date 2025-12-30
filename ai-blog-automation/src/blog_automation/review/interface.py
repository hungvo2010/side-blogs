"""CLI interface for human review.

Provides command-line tools for reviewing articles.
"""

import argparse
import sys
from datetime import datetime

from blog_automation.logging_config import get_logger
from blog_automation.models import Article, ArticleReview, get_session
from blog_automation.pipelines.publishing import publish_article
from blog_automation.review.task_queue import (
    assign_task,
    complete_review,
    get_pending_tasks,
    get_review_stats,
    get_reviewer_tasks,
)

logger = get_logger(__name__)


def list_tasks(args: argparse.Namespace) -> None:
    """List pending review tasks."""
    if args.reviewer:
        tasks = get_reviewer_tasks(args.reviewer)
        print(f"\nTasks assigned to {args.reviewer}:")
    else:
        tasks = get_pending_tasks()
        print("\nPending review tasks:")

    if not tasks:
        print("  No tasks found.")
        return

    print("-" * 80)
    for task in tasks:
        overdue = "⚠️ OVERDUE" if task.get("is_overdue") else ""
        print(f"  Task #{task['task_id']}: {task['title']}")
        print(f"    Keyword: {task['keyword']}")
        print(f"    Status: {task['status']} {overdue}")
        print(f"    Deadline: {task.get('deadline', 'None')}")
        print(f"    Reviewer: {task.get('assigned_reviewer', 'Unassigned')}")
        print()


def review_article(args: argparse.Namespace) -> None:
    """Review a specific article."""
    task_id = args.task_id

    with get_session() as session:
        # Get task and article
        from blog_automation.review.task_queue import ReviewTask

        task = session.query(ReviewTask).get(task_id)
        if not task:
            print(f"Task #{task_id} not found.")
            return

        article = session.query(Article).get(task.article_id)
        if not article:
            print(f"Article not found for task #{task_id}.")
            return

        # Display article information
        print("\n" + "=" * 80)
        print(f"ARTICLE REVIEW - Task #{task_id}")
        print("=" * 80)

        print(f"\nTitle: {article.title}")
        print(f"Keyword: {article.keyword}")
        print(f"Word Count: {article.word_count or 'N/A'}")
        print(f"Status: {article.status}")

        # Display fact-check report
        if article.fact_check_report:
            report = article.fact_check_report
            print("\n--- FACT-CHECK REPORT ---")
            print(f"Claims Checked: {report.get('total_claims_checked', 0)}")
            print(f"Supported: {report.get('supported', 0)}")
            print(f"Contradicted: {report.get('contradicted', 0)}")
            print(f"Unclear: {report.get('unclear', 0)}")
            print(f"Accuracy: {report.get('accuracy_rate', 0):.1f}%")
            print(f"Passed: {'✅' if report.get('pass') else '❌'}")

            if report.get("issues_found"):
                print("\nIssues Found:")
                for issue in report["issues_found"]:
                    print(f"  - {issue.get('claim', 'Unknown')[:50]}...")
                    print(f"    Verdict: {issue.get('verdict')}")

        # Display SEO analysis
        if article.seo_analysis:
            analysis = article.seo_analysis
            print("\n--- SEO ANALYSIS ---")
            print(f"Score: {analysis.get('score', 0)}/100")
            print(f"Grade: {analysis.get('grade', 'N/A')}")

            if analysis.get("issues"):
                print("\nIssues:")
                for issue in analysis["issues"][:5]:
                    print(f"  - {issue}")

        # Display content preview
        content = article.content_draft or ""
        print("\n--- CONTENT PREVIEW ---")
        print(content[:1000] + "..." if len(content) > 1000 else content)

        # Get review decision
        print("\n" + "-" * 80)
        print("Review Options:")
        print("  1. APPROVE - Article passes review")
        print("  2. REVISE  - Request specific changes")
        print("  3. REJECT  - Needs complete rewrite")
        print("  4. SKIP    - Review later")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            verdict = "approve"
        elif choice == "2":
            verdict = "revise"
        elif choice == "3":
            verdict = "reject"
        else:
            print("Review skipped.")
            return

        # Get feedback
        feedback = input("Enter feedback (optional): ").strip() or None

        # Get scores
        scores = None
        if input("Enter quality scores? (y/n): ").lower() == "y":
            scores = {}
            scores["content_quality"] = int(input("Content Quality (1-10): ") or 7)
            scores["originality"] = int(input("Originality (1-10): ") or 7)
            scores["seo_quality"] = int(input("SEO Quality (1-10): ") or 7)
            scores["overall_score"] = int(input("Overall Score (1-10): ") or 7)

        # Complete review
        result = complete_review(task_id, verdict, feedback, scores)

        if result["success"]:
            print(f"\n✅ Review completed: {verdict.upper()}")
            print(f"Next step: {result['next_step']}")

            # Offer to publish if approved
            if verdict == "approve":
                if input("\nPublish article now? (y/n): ").lower() == "y":
                    try:
                        publish_article(article)
                        print("✅ Article published!")
                    except Exception as e:
                        print(f"❌ Publishing failed: {e}")
        else:
            print(f"\n❌ Review failed: {result.get('error')}")


def assign_reviewer(args: argparse.Namespace) -> None:
    """Assign a task to a reviewer."""
    if assign_task(args.task_id, args.reviewer):
        print(f"✅ Task #{args.task_id} assigned to {args.reviewer}")
    else:
        print(f"❌ Failed to assign task #{args.task_id}")


def show_stats(args: argparse.Namespace) -> None:
    """Show review queue statistics."""
    stats = get_review_stats()

    print("\n--- REVIEW QUEUE STATS ---")
    print(f"Pending: {stats['pending']}")
    print(f"In Review: {stats['in_review']}")
    print(f"Completed Today: {stats['completed_today']}")
    print(f"Overdue: {stats['overdue']}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Blog Automation - Review Interface"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List review tasks")
    list_parser.add_argument("--reviewer", "-r", help="Filter by reviewer")
    list_parser.set_defaults(func=list_tasks)

    # Review command
    review_parser = subparsers.add_parser("review", help="Review an article")
    review_parser.add_argument("task_id", type=int, help="Task ID to review")
    review_parser.set_defaults(func=review_article)

    # Assign command
    assign_parser = subparsers.add_parser("assign", help="Assign task to reviewer")
    assign_parser.add_argument("task_id", type=int, help="Task ID")
    assign_parser.add_argument("reviewer", help="Reviewer ID")
    assign_parser.set_defaults(func=assign_reviewer)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show queue statistics")
    stats_parser.set_defaults(func=show_stats)

    args = parser.parse_args()

    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
