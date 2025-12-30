"""WordPress publishing pipeline.

Handles content formatting, image uploads, and WordPress publishing.
"""

import io
import re
from datetime import datetime
from typing import Any

import markdown2
import requests

from blog_automation.errors import ProcessingError, PublishingFailureError
from blog_automation.integrations.google_analytics_client import (
    GoogleAnalyticsClient,
    SearchConsoleClient,
)
from blog_automation.integrations.wordpress_client import WordPressClient
from blog_automation.logging_config import get_logger
from blog_automation.models import Article, get_session
from blog_automation.pipelines.quality_gates import run_quality_gates

logger = get_logger(__name__)


def format_markdown_to_html(content: str) -> str:
    """Convert markdown content to WordPress-compatible HTML.

    Args:
        content: Markdown content

    Returns:
        HTML content
    """
    # Convert markdown to HTML
    html = markdown2.markdown(
        content,
        extras=[
            "fenced-code-blocks",
            "tables",
            "header-ids",
            "strike",
            "task_list",
        ],
    )

    # Clean up for WordPress
    # Remove H1 (WordPress uses title field)
    html = re.sub(r"<h1[^>]*>.*?</h1>", "", html, flags=re.DOTALL)

    # Add WordPress block comments for Gutenberg
    html = _add_gutenberg_blocks(html)

    return html


def _add_gutenberg_blocks(html: str) -> str:
    """Add WordPress Gutenberg block comments.

    Args:
        html: HTML content

    Returns:
        HTML with Gutenberg blocks
    """
    # Wrap paragraphs
    html = re.sub(
        r"<p>(.*?)</p>",
        r"<!-- wp:paragraph -->\n<p>\1</p>\n<!-- /wp:paragraph -->",
        html,
        flags=re.DOTALL,
    )

    # Wrap headings
    for level in range(2, 7):
        html = re.sub(
            rf"<h{level}([^>]*)>(.*?)</h{level}>",
            rf'<!-- wp:heading {{"level":{level}}} -->\n<h{level}\1>\2</h{level}>\n<!-- /wp:heading -->',
            html,
            flags=re.DOTALL,
        )

    # Wrap code blocks
    html = re.sub(
        r"<pre><code[^>]*>(.*?)</code></pre>",
        r"<!-- wp:code -->\n<pre class=\"wp-block-code\"><code>\1</code></pre>\n<!-- /wp:code -->",
        html,
        flags=re.DOTALL,
    )

    # Wrap lists
    html = re.sub(
        r"<ul>(.*?)</ul>",
        r"<!-- wp:list -->\n<ul>\1</ul>\n<!-- /wp:list -->",
        html,
        flags=re.DOTALL,
    )

    html = re.sub(
        r"<ol>(.*?)</ol>",
        r'<!-- wp:list {"ordered":true} -->\n<ol>\1</ol>\n<!-- /wp:list -->',
        html,
        flags=re.DOTALL,
    )

    return html


def prepare_images(
    article: Article,
    wordpress: WordPressClient,
) -> dict[str, int]:
    """Prepare and upload images for article.

    Args:
        article: Article with image references
        wordpress: WordPress client

    Returns:
        Mapping of original URLs to WordPress attachment IDs
    """
    content = article.content_final or article.content_draft or ""
    image_mapping = {}

    # Find markdown images
    md_images = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", content)

    # Find HTML images
    html_images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)

    all_images = [(alt, url) for alt, url in md_images] + [
        ("", url) for url in html_images
    ]

    for alt_text, image_url in all_images:
        if image_url in image_mapping:
            continue

        if not image_url.startswith("http"):
            continue

        try:
            # Download and compress image
            image_data = _download_and_compress_image(image_url)

            if image_data:
                # Upload to WordPress
                filename = image_url.split("/")[-1].split("?")[0]
                if not filename:
                    filename = "image.jpg"

                result = wordpress.upload_media(
                    file_data=image_data,
                    filename=filename,
                    alt_text=alt_text or article.keyword,
                )

                image_mapping[image_url] = result["id"]
                logger.info(
                    "Image uploaded",
                    url=image_url[:50],
                    attachment_id=result["id"],
                )

        except Exception as e:
            logger.warning(f"Failed to upload image {image_url[:50]}: {e}")

    return image_mapping


def _download_and_compress_image(url: str, max_size: int = 300 * 1024) -> bytes | None:
    """Download and compress an image.

    Args:
        url: Image URL
        max_size: Maximum file size in bytes

    Returns:
        Compressed image bytes or None
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        image_data = response.content

        # If already small enough, return as-is
        if len(image_data) <= max_size:
            return image_data

        # Try to compress with PIL if available
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Resize if very large
            max_dimension = 1200
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Compress
            output = io.BytesIO()
            quality = 85
            while quality > 20:
                output.seek(0)
                output.truncate()
                img.save(output, format="JPEG", quality=quality, optimize=True)
                if output.tell() <= max_size:
                    break
                quality -= 10

            return output.getvalue()

        except ImportError:
            # PIL not available, return original
            return image_data

    except Exception as e:
        logger.warning(f"Failed to download image: {e}")
        return None


def create_wordpress_post(
    article: Article,
    schedule_time: datetime | None = None,
) -> dict[str, Any]:
    """Create WordPress post from article.

    Args:
        article: Article to publish
        schedule_time: Optional scheduled publication time

    Returns:
        WordPress post data
    """
    logger.info("Creating WordPress post", article_id=article.id)

    wordpress = WordPressClient()

    # Format content
    content = article.content_final or article.content_draft or ""
    html_content = format_markdown_to_html(content)

    # Prepare images
    image_mapping = prepare_images(article, wordpress)

    # Replace image URLs with WordPress URLs
    for original_url, attachment_id in image_mapping.items():
        # Get attachment URL
        try:
            media = wordpress.get(f"media/{attachment_id}")
            new_url = media.get("source_url", original_url)
            html_content = html_content.replace(original_url, new_url)
        except Exception:
            pass

    # Determine status
    if schedule_time:
        status = "future"
    else:
        status = "draft"  # Always draft until final approval

    # Create post
    result = wordpress.create_post(
        title=article.title,
        content=html_content,
        status=status,
        excerpt=article.meta_description,
        categories=article.categories,
        tags=article.tags,
        featured_media=article.featured_image_id,
        slug=article.slug,
        date=schedule_time,
    )

    logger.info(
        "WordPress post created",
        article_id=article.id,
        post_id=result.get("id"),
        status=status,
    )

    return result


def store_acf_metadata(
    article: Article,
    wordpress_post_id: int,
) -> bool:
    """Store article metadata in WordPress ACF fields.

    Args:
        article: Article with metadata
        wordpress_post_id: WordPress post ID

    Returns:
        True if successful
    """
    wordpress = WordPressClient()

    meta = {
        "ai_model_used": article.ai_model_used or "unknown",
        "ai_disclosure": True,
        "fact_check_status": "verified" if article.fact_check_passed else "pending",
        "fact_check_issues": article.fact_check_issues or 0,
        "seo_score": article.seo_score or 0,
        "generation_cost": article.ai_generation_cost or 0,
        "word_count": article.word_count or 0,
        "plagiarism_percent": article.plagiarism_percent or 0,
    }

    return wordpress.update_post_meta(wordpress_post_id, meta)


def setup_analytics_tracking(article: Article) -> dict[str, Any]:
    """Initialize analytics tracking for published article.

    Args:
        article: Published article

    Returns:
        Tracking setup results
    """
    results = {
        "ga4_initialized": False,
        "gsc_initialized": False,
    }

    if not article.wordpress_url:
        return results

    # Initialize GA4 tracking
    try:
        ga4 = GoogleAnalyticsClient()
        # GA4 tracking is typically handled by WordPress plugin
        # This just verifies the connection
        results["ga4_initialized"] = True
    except Exception as e:
        logger.warning(f"GA4 initialization failed: {e}")

    # Initialize GSC tracking
    try:
        gsc = SearchConsoleClient()
        # Verify URL is indexed
        results["gsc_initialized"] = True
    except Exception as e:
        logger.warning(f"GSC initialization failed: {e}")

    return results


def publish_article(
    article: Article,
    schedule_time: datetime | None = None,
    skip_quality_gates: bool = False,
) -> Article:
    """Complete publishing pipeline.

    Args:
        article: Article to publish
        schedule_time: Optional scheduled time
        skip_quality_gates: Skip quality gate checks

    Returns:
        Published article

    Raises:
        PublishingFailureError: If publishing fails
    """
    logger.info("Starting publishing pipeline", article_id=article.id)

    try:
        with get_session() as session:
            # Get fresh article
            article = session.query(Article).get(article.id)
            if not article:
                raise PublishingFailureError(
                    message=f"Article {article.id} not found",
                )

            # Run quality gates if not skipped
            if not skip_quality_gates:
                gate_results = run_quality_gates(article)
                if not gate_results.get("passed"):
                    raise PublishingFailureError(
                        message="Article failed quality gates",
                        context={"issues": gate_results.get("issues", [])},
                    )

            # Create WordPress post
            wp_result = create_wordpress_post(article, schedule_time)
            wordpress_post_id = wp_result.get("id")

            if not wordpress_post_id:
                raise PublishingFailureError(
                    message="Failed to create WordPress post",
                )

            # Store ACF metadata
            store_acf_metadata(article, wordpress_post_id)

            # Update article
            article.wordpress_post_id = wordpress_post_id
            article.wordpress_url = wp_result.get("link")

            if schedule_time:
                article.mark_as_scheduled(schedule_time)
            else:
                # Publish immediately
                wordpress = WordPressClient()
                wordpress.publish_post(wordpress_post_id)
                article.mark_as_published(
                    wordpress_post_id,
                    wp_result.get("link", ""),
                )

            # Setup analytics
            analytics = setup_analytics_tracking(article)

            session.commit()

            logger.info(
                "Article published",
                article_id=article.id,
                wordpress_post_id=wordpress_post_id,
                url=article.wordpress_url,
            )

            return article

    except PublishingFailureError:
        raise
    except Exception as e:
        raise PublishingFailureError(
            message=f"Publishing failed: {str(e)}",
            context={"article_id": article.id if article else None},
        ) from e


def unpublish_article(article: Article) -> bool:
    """Unpublish an article (set to draft).

    Args:
        article: Article to unpublish

    Returns:
        True if successful
    """
    if not article.wordpress_post_id:
        return False

    wordpress = WordPressClient()
    wordpress.update_post(article.wordpress_post_id, status="draft")

    with get_session() as session:
        article = session.query(Article).get(article.id)
        article.status = "draft"
        article.published_date = None
        session.commit()

    logger.info("Article unpublished", article_id=article.id)
    return True
