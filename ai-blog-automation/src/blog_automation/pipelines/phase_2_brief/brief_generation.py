"""Content brief generation pipeline.

Generates detailed content briefs with sections, LSI keywords,
sources, and unique angles.
"""

from typing import Any

from blog_automation.errors import InvalidBriefError, ProcessingError
from blog_automation.integrations.openrouter_client import OpenRouterClient
from blog_automation.logging_config import get_logger
from blog_automation.models import ContentBrief, get_session
from blog_automation.pipelines.phase_1_research.keyword_research import research_keyword

logger = get_logger(__name__)


# Prompts for brief generation
SECTION_GENERATION_PROMPT = """\
Based on this keyword research, suggest H2 sections for a comprehensive blog post.

Keyword: {keyword}
Search Intent: {intent}
Difficulty: {difficulty}
Search Volume: {volume}

Top competitor H2 patterns:
{competitor_h2s}

Requirements:
- Suggest 4-6 H2 sections that cover the topic comprehensively
- Each section should serve a clear purpose
- Include a FAQ section at the end
- Consider the search intent when structuring

Return JSON:
{{
  "sections": [
    {{
      "h2": "Section Title",
      "purpose": "Why this section is important",
      "target_length": "200-300 words",
      "key_points": ["point1", "point2", "point3"]
    }}
  ]
}}"""

LSI_KEYWORD_PROMPT = """\
Generate LSI (Latent Semantic Indexing) keywords related to the main keyword.

Main keyword: {keyword}
Search intent: {intent}

Requirements:
- Generate 10-15 related keywords and phrases
- Include synonyms, related concepts, and common questions
- Focus on terms that would naturally appear in comprehensive content

Return JSON:
{{
  "lsi_keywords": ["keyword1", "keyword2", ...]
}}"""

UNIQUE_ANGLE_PROMPT = """\
Analyze these competitor articles and suggest a unique angle for our content.

Keyword: {keyword}
Intent: {intent}

Competitor content summaries:
{competitor_summaries}

Requirements:
- Identify gaps in existing content
- Suggest a fresh perspective or approach
- Consider what would make our content stand out
- Be specific and actionable

Return a single paragraph describing the unique angle."""


def generate_content_brief(
    keyword: str,
    brief_id: int | None = None,
) -> ContentBrief:
    """Generate a detailed content brief.

    Args:
        keyword: Target keyword
        brief_id: Optional existing brief ID to enhance

    Returns:
        ContentBrief with full brief data

    Raises:
        ProcessingError: If brief generation fails
    """
    logger.info("Starting content brief generation", keyword=keyword)

    try:
        # Get or create initial brief
        with get_session() as session:
            if brief_id:
                brief = session.query(ContentBrief).get(brief_id)
                if not brief:
                    raise InvalidBriefError(
                        message=f"Brief {brief_id} not found",
                        context={"brief_id": brief_id},
                    )
            else:
                # Create new brief with keyword research
                brief = research_keyword(keyword)
                session.add(brief)

            # Initialize LLM client (single OpenRouter gateway)
            llm = OpenRouterClient()

            # Release the DB connection BEFORE the slow LLM phase. Neon
            # (serverless Postgres) kills idle connections after ~5 minutes;
            # brief generation calls the LLM 5+ times (minutes each), so the
            # session would otherwise hold a dead connection into the final
            # commit. Commit now → connection returns to pool → pool_pre_ping
            # validates it fresh at the next checkout.
            session.commit()

            # Get existing brief data
            brief_data = brief.brief_data or {}
            intent = brief.intent or "informational"
            difficulty = brief.difficulty or 50
            volume = brief.search_volume or 0

            # Generate H2 sections
            logger.info("Generating H2 sections", keyword=keyword)
            sections = _generate_sections(
                llm, keyword, intent, difficulty, volume, brief_data
            )
            brief_data["sections"] = sections

            # Generate LSI keywords
            logger.info("Generating LSI keywords", keyword=keyword)
            lsi_keywords = _generate_lsi_keywords(llm, keyword, intent)
            brief_data["lsi_keywords"] = lsi_keywords

            # Collect external sources (soft-fail on free models)
            try:
                sources = _collect_sources(llm, keyword)
                brief_data["sources"] = sources
                logger.info("Sources collected", count=len(sources))
            except Exception as e:
                logger.warning("Source collection skipped", error=str(e)[:80])
                brief_data["sources"] = []

            # Generate unique angle
            logger.info("Generating unique angle", keyword=keyword)
            unique_angle = _generate_unique_angle(
                llm, keyword, intent, brief_data.get("competitor_analysis", {})
            )
            brief_data["unique_angle"] = unique_angle

            # Generate target audience description
            audience = _generate_audience_description(keyword, intent)
            brief_data["target_audience"] = audience

            # Update brief
            brief.brief_data = brief_data

            # Validate brief
            is_valid, errors = brief.validate()
            if not is_valid:
                logger.warning(
                    "Brief validation failed",
                    keyword=keyword,
                    errors=errors,
                )

            # Commit with retry — Neon serverless can still drop the connection
            # between pool checkout and this write. Retry once on
            # OperationalError (stale SSL connection) by re-checking out.
            from sqlalchemy.exc import OperationalError as _OperationalError

            for _attempt in range(2):
                try:
                    session.commit()
                    break
                except _OperationalError:
                    session.rollback()
                    if _attempt == 0:
                        logger.warning(
                            "DB connection dropped during brief commit, retrying",
                            keyword=keyword,
                        )
                        continue
                    raise

            logger.info(
                "Content brief generation complete",
                keyword=keyword,
                brief_id=brief.id,
                sections=len(sections),
                sources=len(sources),
            )

            return brief

    except InvalidBriefError:
        raise
    except Exception as e:
        raise ProcessingError(
            message=f"Brief generation failed: {str(e)}",
            step="brief_generation",
            context={"keyword": keyword},
        ) from e


def _generate_sections(
    llm: OpenRouterClient,
    keyword: str,
    intent: str,
    difficulty: int,
    volume: int,
    brief_data: dict,
) -> list[dict[str, Any]]:
    """Generate H2 sections using Claude."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return [
            {
                "h2": f"Understanding {keyword}",
                "purpose": "Introduction",
                "target_length": "200 words",
                "key_points": ["Point 1"],
            },
            {
                "h2": f"Benefits of {keyword}",
                "purpose": "Value",
                "target_length": "300 words",
                "key_points": ["Point A"],
            },
            {
                "h2": f"How to get started with {keyword}",
                "purpose": "Guide",
                "target_length": "400 words",
                "key_points": ["Step 1"],
            },
            {
                "h2": "Conclusion",
                "purpose": "Wrap up",
                "target_length": "100 words",
                "key_points": ["Summary"],
            },
        ]

    # Extract competitor H2s if available
    competitor_h2s = ""
    competitor_analysis = brief_data.get("competitor_analysis", {})
    if competitor_analysis.get("top_pages"):
        competitor_h2s = "\n".join(
            f"- {p.get('title', 'Unknown')}" for p in competitor_analysis["top_pages"]
        )

    prompt = SECTION_GENERATION_PROMPT.format(
        keyword=keyword,
        intent=intent,
        difficulty=difficulty,
        volume=volume,
        competitor_h2s=competitor_h2s or "No competitor data available",
    )

    response = llm.extract_json(prompt)
    sections = response.get("sections", [])

    # Ensure we have at least 4 sections
    if len(sections) < 4:
        # Add default sections
        default_sections = [
            {
                "h2": f"What is {keyword.title()}?",
                "purpose": "Introduction and definition",
                "target_length": "200-300 words",
                "key_points": ["Definition", "Overview", "Importance"],
            },
            {
                "h2": f"How to Use {keyword.title()}",
                "purpose": "Practical guide",
                "target_length": "300-400 words",
                "key_points": ["Step-by-step", "Examples", "Tips"],
            },
            {
                "h2": f"Benefits of {keyword.title()}",
                "purpose": "Value proposition",
                "target_length": "200-300 words",
                "key_points": ["Key benefits", "Use cases"],
            },
            {
                "h2": "Frequently Asked Questions",
                "purpose": "Address common questions",
                "target_length": "300-400 words",
                "key_points": ["Common questions", "Quick answers"],
            },
        ]
        sections = default_sections

    return sections


def _generate_lsi_keywords(
    llm: OpenRouterClient,
    keyword: str,
    intent: str,
) -> list[str]:
    """Generate LSI keywords using Claude."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return [
            f"{keyword} tips",
            f"{keyword} guide",
            f"best {keyword}",
            f"{keyword} reviews",
        ]

    prompt = LSI_KEYWORD_PROMPT.format(keyword=keyword, intent=intent)

    response = llm.extract_json(prompt)
    lsi_keywords = response.get("lsi_keywords", [])

    # Ensure we have at least 5 keywords
    if len(lsi_keywords) < 5:
        # Add some generic related terms
        lsi_keywords.extend(
            [
                f"{keyword} guide",
                f"{keyword} tutorial",
                f"best {keyword}",
                f"{keyword} examples",
                f"how to {keyword}",
            ]
        )

    return lsi_keywords[:15]  # Limit to 15


def _collect_sources(
    llm: OpenRouterClient,
    keyword: str,
    source_count: int = 10,
) -> list[dict[str, Any]]:
    """Collect external sources using Perplexity."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return [{"url": "https://wikipedia.org", "title": "Wikipedia"}]

    # Search for authoritative sources
    result = llm.search(
        f"authoritative sources about {keyword}",
        source_count=source_count,
    )

    sources = result.get("sources", [])

    # Ensure we have at least 5 sources
    if len(sources) < 5:
        # Try additional search
        additional = llm.search(
            f"{keyword} research studies statistics",
            source_count=5,
        )
        sources.extend(additional.get("sources", []))

    return sources[:source_count]


def _generate_unique_angle(
    llm: OpenRouterClient,
    keyword: str,
    intent: str,
    competitor_analysis: dict,
) -> str:
    """Generate unique angle using Claude."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return f"A fresh look at {keyword} from a data-driven perspective."

    # Create competitor summaries
    competitor_summaries = ""
    if competitor_analysis.get("top_pages"):
        competitor_summaries = "\n".join(
            f"- {p.get('title', 'Unknown')} ({p.get('word_count', 'N/A')} words)"
            for p in competitor_analysis["top_pages"][:5]
        )

    prompt = UNIQUE_ANGLE_PROMPT.format(
        keyword=keyword,
        intent=intent,
        competitor_summaries=competitor_summaries or "No competitor data available",
    )

    response = llm.message(prompt, max_tokens=500)
    return response.get("content", "").strip()


def _generate_audience_description(keyword: str, intent: str) -> str:
    """Generate target audience description.

    Args:
        keyword: Target keyword
        intent: Search intent

    Returns:
        Audience description
    """
    intent_audiences = {
        "informational": (
            f"People seeking to learn about {keyword}, including"
            " beginners and those looking to deepen their understanding."
        ),
        "commercial": (
            f"Potential buyers researching {keyword} options,"
            " comparing features and looking for recommendations."
        ),
        "transactional": (
            f"Ready-to-buy customers looking for the best deals on {keyword}."
        ),
        "navigational": f"Users specifically looking for information about {keyword}.",
    }

    return intent_audiences.get(intent, intent_audiences["informational"])


def research_keyword_full(
    keyword: str,
    article_id: int | None = None,
) -> ContentBrief:
    """Complete keyword research and brief generation.

    Combines keyword research (step 4.1) and brief generation (step 4.2).

    Args:
        keyword: Target keyword
        article_id: Optional article ID to link

    Returns:
        Complete ContentBrief
    """
    logger.info("Starting full keyword research", keyword=keyword)

    # Step 1: Keyword research
    brief = research_keyword(keyword, article_id)

    # Step 2: Generate full brief
    complete_brief = generate_content_brief(keyword, brief.id)

    return complete_brief
