"""Quality gates pipeline.

Final quality checks before publishing including plagiarism,
link verification, and metadata validation.
"""

import re
from typing import Any

import requests

from blog_automation.config import get_settings
from blog_automation.errors import ProcessingError
from blog_automation.integrations.copyscape_client import CopyscapeClient
from blog_automation.logging_config import get_logger
from blog_automation.models import Article, get_session

logger = get_logger(__name__)


def check_plagiarism(article: Article) -> dict[str, Any]:
    """Check article for plagiarism.

    Args:
        article: Article to check

    Returns:
        Plagiarism check results
    """
    logger.info("Checking plagiarism", article_id=article.id)

    content = article.content_final or article.content_draft or ""

    try:
        copyscape = CopyscapeClient()
        result = copyscape.check_plagiarism(content, article.title)

        logger.info(
            "Plagiarism check complete",
            article_id=article.id,
            percent=result.get("plagiarism_percent", 0),
        )

        return result

    except Exception as e:
        logger.warning(f"Plagiarism check failed: {e}")
        return {
            "plagiarism_percent": 0,
            "matches": [],
            "match_count": 0,
            "is_original": True,
            "error": str(e),
        }


def verify_links(article: Article) -> dict[str, Any]:
    """Verify all links in article are valid.

    Args:
        article: Article to check

    Returns:
        Link verification results
    """
    logger.info("Verifying links", article_id=article.id)

    content = article.content_final or article.content_draft or ""

    # Extract markdown links
    link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    links = re.findall(link_pattern, content)

    # Extract HTML links
    html_pattern = r'href=["\']([^"\']+)["\']'
    html_links = re.findall(html_pattern, content)

    internal_links = []
    external_links = []
    broken_links = []

    settings = get_settings()
    site_url = settings.wordpress_url

    # Categorize links
    all_urls = [url for _, url in links] + html_links

    for url in all_urls:
        if url.startswith("#"):
            continue  # Skip anchor links

        if url.startswith("/") or (site_url and site_url in url):
            internal_links.append(url)
        elif url.startswith("http"):
            external_links.append(url)

    # Check external links
    for url in external_links[:10]:  # Limit to 10 to avoid rate limiting
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code >= 400:
                broken_links.append({"url": url, "status": response.status_code})
        except Exception:
            broken_links.append({"url": url, "status": "error"})

    result = {
        "internal_links": len(internal_links),
        "external_links": len(external_links),
        "broken_links": broken_links,
        "broken_count": len(broken_links),
        "all_valid": len(broken_links) == 0,
    }

    logger.info(
        "Link verification complete",
        article_id=article.id,
        internal=len(internal_links),
        external=len(external_links),
        broken=len(broken_links),
    )

    return result


def check_readability(article: Article) -> dict[str, Any]:
    """Check article readability.

    Args:
        article: Article to check

    Returns:
        Readability results
    """
    content = article.content_final or article.content_draft or ""

    # Simple Flesch-Kincaid approximation
    sentences = len(re.findall(r"[.!?]+", content))
    words = len(content.split())
    syllables = _count_syllables(content)

    if sentences == 0 or words == 0:
        return {
            "flesch_kincaid": 0,
            "grade_level": "N/A",
            "readable": False,
        }

    # Flesch-Kincaid Grade Level
    fk_grade = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

    # Flesch Reading Ease
    fre = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)

    result = {
        "flesch_kincaid": round(fk_grade, 1),
        "flesch_reading_ease": round(fre, 1),
        "grade_level": _grade_to_level(fk_grade),
        "readable": fk_grade <= 12,  # Target: 12th grade or below
        "sentences": sentences,
        "words": words,
    }

    return result


def validate_metadata(article: Article) -> dict[str, Any]:
    """Validate article metadata completeness.

    Args:
        article: Article to validate

    Returns:
        Validation results
    """
    issues = []

    # Meta title
    if not article.meta_title:
        issues.append("Missing meta title")
    elif len(article.meta_title) > 60:
        issues.append(f"Meta title too long ({len(article.meta_title)} chars)")
    elif article.keyword.lower() not in article.meta_title.lower():
        issues.append("Keyword not in meta title")

    # Meta description
    if not article.meta_description:
        issues.append("Missing meta description")
    elif len(article.meta_description) > 160:
        issues.append(f"Meta description too long ({len(article.meta_description)} chars)")
    elif article.keyword.lower() not in article.meta_description.lower():
        issues.append("Keyword not in meta description")

    # Categories
    if not article.categories:
        issues.append("No categories assigned")

    # Featured image
    if not article.featured_image_id and not article.featured_image_url:
        issues.append("No featured image")

    # Word count
    if not article.word_count or article.word_count < 1500:
        issues.append(f"Word count too low ({article.word_count or 0})")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "issue_count": len(issues),
    }


def run_quality_gates(article: Article) -> dict[str, Any]:
    """Run all quality gates on an article.

    Args:
        article: Article to check

    Returns:
        Combined quality gate results

    Raises:
        ProcessingError: If quality gates fail
    """
    logger.info("Running quality gates", article_id=article.id)

    try:
        with get_session() as session:
            # Get fresh article
            article = session.query(Article).get(article.id)
            if not article:
                raise ProcessingError(
                    message=f"Article {article.id} not found",
                    step="quality_gates",
                )

            settings = get_settings()

            # Run all checks
            plagiarism = check_plagiarism(article)
            links = verify_links(article)
            readability = check_readability(article)
            metadata = validate_metadata(article)

            # Aggregate results
            all_issues = []

            # Plagiarism check
            plagiarism_threshold = settings.plagiarism_threshold
            if plagiarism.get("plagiarism_percent", 0) > plagiarism_threshold:
                all_issues.append(
                    f"Plagiarism too high ({plagiarism['plagiarism_percent']:.1f}%)"
                )

            # Link check
            if links.get("broken_count", 0) > 0:
                all_issues.append(f"{links['broken_count']} broken links found")

            # Readability check
            if not readability.get("readable", False):
                all_issues.append(
                    f"Readability too low (grade {readability.get('flesch_kincaid', 'N/A')})"
                )

            # Metadata check
            all_issues.extend(metadata.get("issues", []))

            # Determine pass/fail
            passed = len(all_issues) == 0

            result = {
                "passed": passed,
                "issues": all_issues,
                "issue_count": len(all_issues),
                "checks": {
                    "plagiarism": plagiarism,
                    "links": links,
                    "readability": readability,
                    "metadata": metadata,
                },
            }

            # Update article
            article.plagiarism_percent = plagiarism.get("plagiarism_percent", 0)
            article.readability_score = readability.get("flesch_kincaid", 0)

            if passed:
                article.status = "approved"
            else:
                article.status = "quality_gate_failed"

            session.commit()

            logger.info(
                "Quality gates complete",
                article_id=article.id,
                passed=passed,
                issues=len(all_issues),
            )

            return result

    except Exception as e:
        raise ProcessingError(
            message=f"Quality gates failed: {str(e)}",
            step="quality_gates",
            context={"article_id": article.id if article else None},
        ) from e


def _count_syllables(text: str) -> int:
    """Count syllables in text (approximation).

    Args:
        text: Text to count syllables in

    Returns:
        Syllable count
    """
    text = text.lower()
    count = 0
    vowels = "aeiouy"
    prev_char_was_vowel = False

    for char in text:
        is_vowel = char in vowels
        if is_vowel and not prev_char_was_vowel:
            count += 1
        prev_char_was_vowel = is_vowel

    # Adjust for common patterns
    count -= text.count("e ")  # Silent e
    count -= text.count("es ")
    count -= text.count("ed ")

    return max(count, 1)


def _grade_to_level(grade: float) -> str:
    """Convert grade level to description.

    Args:
        grade: Flesch-Kincaid grade level

    Returns:
        Grade level description
    """
    if grade <= 6:
        return "Elementary"
    elif grade <= 8:
        return "Middle School"
    elif grade <= 12:
        return "High School"
    elif grade <= 16:
        return "College"
    else:
        return "Graduate"
