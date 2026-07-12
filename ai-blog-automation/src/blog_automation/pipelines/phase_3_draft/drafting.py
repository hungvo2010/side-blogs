"""Article drafting pipeline.

Generates article outlines and full drafts using GPT-4.
"""

import re
from datetime import datetime
from typing import Any

from blog_automation.errors import GenerationFailureError, ProcessingError
from blog_automation.integrations.openrouter_client import OpenRouterClient
from blog_automation.logging_config import get_logger
from blog_automation.models import Article, ContentBrief, get_session

logger = get_logger(__name__)


# Prompts for drafting
OUTLINE_GENERATION_PROMPT = """Create a detailed article outline for: {keyword}

Sections to include:
{sections}

Requirements:
- H1: Main title (compelling, includes keyword)
- H2 for each section
- 2-3 H3 subsections per H2
- FAQ section at end with 3-5 questions
- Include internal link opportunities marked as [INTERNAL: topic]

Return markdown outline only."""

ARTICLE_SYSTEM_PROMPT = """You are a professional blog writer creating engaging, well-researched content.

Guidelines:
- Conversational tone, avoid robotic language
- Short paragraphs (2-3 sentences max)
- Include real-world examples and use cases
- Natural keyword integration (3-5 times total)
- No keyword stuffing
- Cite sources where appropriate using [Source: URL] format
- Internal link anchors: [anchor text](article-slug)
- Use bullet points and numbered lists where appropriate
- Include actionable takeaways
- Write for humans first, SEO second"""

ARTICLE_USER_PROMPT = """Write a complete blog post following this outline:

{outline}

Target keyword: {keyword}
Unique angle: {unique_angle}
Target word count: {word_count} words minimum

LSI keywords to include naturally:
{lsi_keywords}

External sources to cite:
{sources}

Requirements:
- Minimum {word_count} words
- Include the keyword naturally 3-5 times
- Use LSI keywords throughout
- Cite at least 3 external sources
- Include a compelling introduction
- End with a clear conclusion and call-to-action"""


def generate_outline(brief: ContentBrief) -> str:
    """Generate article outline from content brief."""
    from blog_automation.config import get_settings
    if get_settings().mock_mode:
        return f"# {brief.keyword.title()}\n\n## Introduction\n\n## Section 1\n\n### Sub 1\n\n## Section 2\n\n## Conclusion"

    logger.info("Generating outline", keyword=brief.keyword)
    llm = OpenRouterClient()
    # ... rest of the original logic ...
    # Format sections for prompt
    sections_text = ""
    for section in brief.get_sections():
        sections_text += f"\n- {section.get('h2', 'Section')}"
        sections_text += f"\n  Purpose: {section.get('purpose', '')}"
        sections_text += f"\n  Key points: {', '.join(section.get('key_points', []))}"

    prompt = OUTLINE_GENERATION_PROMPT.format(
        keyword=brief.keyword,
        sections=sections_text,
    )

    response = llm.complete(prompt, temperature=0.7, max_tokens=1500)
    outline = response.get("content", "")

    logger.info(
        "Outline generated",
        keyword=brief.keyword,
        tokens=response.get("total_tokens", 0),
    )

    return outline


def generate_article_draft(
    brief: ContentBrief,
    outline: str,
) -> Article:
    """Generate full article draft from brief and outline."""
    from blog_automation.config import get_settings
    if get_settings().mock_mode:
        mock_content = f"# {brief.keyword.title()}\n\nThis is a mock article about {brief.keyword}.\n\n## Introduction\nWelcome to our guide about {brief.keyword}.\n\n## Benefits\nThere are many benefits to {brief.keyword}.\n\n## Conclusion\nIn summary, {brief.keyword} is great. [Source: https://wikipedia.org]"
        return Article(
            title=brief.keyword.title(),
            slug=_generate_slug(brief.keyword),
            keyword=brief.keyword,
            content_draft=mock_content,
            outline=outline,
            status="draft",
            ai_model_used="mock-model",
            ai_generation_cost=0.0,
            word_count=len(mock_content.split()),
        )

    logger.info("Generating article draft", keyword=brief.keyword)
    llm = OpenRouterClient()
    # ... rest of original logic ...
    # Prepare prompt data
    word_count = brief.get_target_word_count()
    unique_angle = brief.get_unique_angle() or "Provide comprehensive, actionable information"
    lsi_keywords = ", ".join(brief.get_lsi_keywords()[:10])

    sources_text = ""
    for source in brief.get_sources()[:5]:
        sources_text += f"\n- {source.get('title', 'Source')}: {source.get('url', '')}"

    user_prompt = ARTICLE_USER_PROMPT.format(
        outline=outline,
        keyword=brief.keyword,
        unique_angle=unique_angle,
        word_count=word_count,
        lsi_keywords=lsi_keywords,
        sources=sources_text or "Use authoritative sources",
    )

    response = llm.chat_complete(
        messages=[
            {"role": "system", "content": ARTICLE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4000,
    )

    draft_content = response.get("content", "")

    # Create article
    article = Article(
        title=_extract_title(draft_content, brief.keyword),
        slug=_generate_slug(brief.keyword),
        keyword=brief.keyword,
        content_draft=draft_content,
        outline=outline,
        status="draft",
        ai_model_used=response.get("model", "gpt-4-turbo"),
        ai_generation_cost=response.get("cost", 0),
        ai_tokens_used={
            "input": response.get("input_tokens", 0),
            "output": response.get("output_tokens", 0),
        },
    )

    # Update word count
    article.update_word_count()

    logger.info(
        "Article draft generated",
        keyword=brief.keyword,
        word_count=article.word_count,
        cost=f"${response.get('cost', 0):.4f}",
    )

    return article


def validate_draft_quality(
    article: Article,
    brief: ContentBrief,
) -> tuple[bool, list[str]]:
    """Validate draft meets quality standards.

    Args:
        article: Article with draft content
        brief: ContentBrief with requirements

    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []
    content = article.content_draft or ""
    content_lower = content.lower()
    keyword_lower = brief.keyword.lower()

    # Check word count
    word_count = len(content.split())
    min_words = brief.get_target_word_count()
    if word_count < min_words:
        errors.append(f"Only {word_count} words, need {min_words}")

    # Check keyword presence
    keyword_count = content_lower.count(keyword_lower)
    if keyword_count < 3:
        errors.append(f"Keyword appears {keyword_count} times, need 3-5")
    elif keyword_count > 10:
        errors.append(f"Keyword stuffing detected ({keyword_count} occurrences)")

    # Check for obvious AI patterns
    ai_phrases = [
        "as an ai",
        "i don't have",
        "please note that",
        "it's important to note",
        "in conclusion,",
        "in summary,",
    ]
    for phrase in ai_phrases:
        if phrase in content_lower:
            errors.append(f"Found AI pattern: '{phrase}'")

    # Check for heading structure
    h2_count = len(re.findall(r"^##\s", content, re.MULTILINE))
    if h2_count < 3:
        errors.append(f"Only {h2_count} H2 headings, need at least 3")

    # Check for external links/sources
    source_count = content.count("[Source:") + content.count("](http")
    if source_count < 2:
        errors.append(f"Only {source_count} source citations, need at least 2")

    is_valid = len(errors) == 0

    if not is_valid:
        logger.warning(
            "Draft validation failed",
            keyword=brief.keyword,
            errors=errors,
        )

    return is_valid, errors


REVISION_SYSTEM_PROMPT = """You are a professional blog editor. Your task is to revise an existing blog post based on specific human feedback.

Maintain the original structure where possible, but strictly address all points in the feedback.
Ensure the final output is high-quality, follows the original guidelines, and improves upon the initial draft.

Guidelines:
- Address ALL points in the feedback
- Maintain the conversational tone
- Keep short paragraphs
- Ensure proper markdown formatting
- Do not add meta-commentary about the changes (just return the revised article)"""

REVISION_USER_PROMPT = """Please revise the following blog post.

--- ORIGINAL CONTENT ---
{content}
--- END ORIGINAL CONTENT ---

--- HUMAN FEEDBACK ---
{feedback}
--- END HUMAN FEEDBACK ---

Target keyword: {keyword}

Requirements for the revision:
- Address all feedback points
- Keep the length similar unless requested otherwise
- Ensure all H2/H3 headings are still present and improved
- Return the full revised article in markdown format."""


def revise_article_with_feedback(
    article: Article,
    feedback: str,
) -> Article:
    """Revise an article based on human feedback.

    Args:
        article: Article to revise
        feedback: Human feedback string

    Returns:
        Updated Article with revised content
    """
    logger.info("Revising article with feedback", article_id=article.id)

    llm = OpenRouterClient()

    user_prompt = REVISION_USER_PROMPT.format(
        content=article.content_draft or "",
        feedback=feedback,
        keyword=article.keyword,
    )

    response = llm.chat_complete(
        messages=[
            {"role": "system", "content": REVISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,  # Lower temperature for more focused revision
        max_tokens=4000,
    )

    revised_content = response.get("content", "")

    # Update article
    article.content_draft = revised_content
    article.status = "draft"  # Reset to draft status for re-validation/review
    article.ai_generation_cost += response.get("cost", 0)
    
    # Update word count
    article.update_word_count()

    logger.info(
        "Article revised",
        article_id=article.id,
        new_word_count=article.word_count,
        cost=f"${response.get('cost', 0):.4f}",
    )

    return article


def content_brief_to_draft(brief: ContentBrief) -> Article:
    """Complete pipeline: brief → outline → draft.

    Args:
        brief: ContentBrief with all data

    Returns:
        Article with validated draft

    Raises:
        ProcessingError: If drafting fails
    """
    logger.info("Starting brief to draft pipeline", keyword=brief.keyword)

    try:
        # Step 1: Generate outline
        outline = generate_outline(brief)
        logger.info("Outline generated", keyword=brief.keyword)

        # Step 2: Generate draft
        article = generate_article_draft(brief, outline)
        logger.info(
            "Draft generated",
            keyword=brief.keyword,
            word_count=article.word_count,
        )

        # Step 3: Validate quality
        is_valid, errors = validate_draft_quality(article, brief)

        if not is_valid:
            article.status = "draft_validation_failed"
            logger.warning(
                "Draft validation failed",
                keyword=brief.keyword,
                errors=errors,
            )
        else:
            article.status = "draft"

        # Step 4: Save to database
        with get_session() as session:
            session.add(article)

            # Link brief to article
            brief_obj = session.query(ContentBrief).get(brief.id)
            if brief_obj:
                brief_obj.article_id = article.id

            session.commit()

            logger.info(
                "Draft saved to database",
                keyword=brief.keyword,
                article_id=article.id,
            )

            return article

    except Exception as e:
        raise ProcessingError(
            message=f"Drafting pipeline failed: {str(e)}",
            step="drafting",
            context={"keyword": brief.keyword},
        ) from e


def _extract_title(content: str, keyword: str) -> str:
    """Extract title from content or generate from keyword.

    Args:
        content: Article content
        keyword: Target keyword

    Returns:
        Article title
    """
    # Try to find H1 in content
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    # Generate from keyword
    return keyword.title()


def _generate_slug(keyword: str) -> str:
    """Generate URL slug from keyword."""
    import uuid
    # Convert to lowercase and replace spaces with hyphens
    slug = keyword.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)

    # Add timestamp and random suffix for uniqueness
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = str(uuid.uuid4())[:4]
    return f"{slug}-{timestamp}-{random_suffix}"
