"""Fact-checking pipeline.

Extracts claims from articles and verifies them against web evidence.
"""

from datetime import datetime
from typing import Any

from blog_automation.errors import ProcessingError, VerificationFailureError
from blog_automation.integrations.openrouter_client import OpenRouterClient
from blog_automation.logging_config import get_logger
from blog_automation.models import Article, get_session

logger = get_logger(__name__)


# Prompts for fact-checking
CLAIM_EXTRACTION_PROMPT = """Extract factual, verifiable claims from this article.
Filter out common knowledge, opinions, and subjective statements.

Article:
{content}

Requirements:
- Extract at most 12 of the most distinctive, verifiable factual claims
- Keep each claim concise (max 25 words)
- Include statistics, dates, technical specifications, quotes
- Exclude obvious common knowledge and subjective opinions
- Prioritize specific, checkable claims over general statements

Return JSON:
{{
  "claims": [
    {{
      "claim": "Exact claim text from article",
      "type": "historical|statistic|technical|definition|quote",
      "confidence": "high|medium|low",
      "context": "Brief context of where this appears"
    }}
  ]
}}"""

CLAIM_VERIFICATION_PROMPT = """Verify this claim against the provided evidence.

Claim: {claim}

Evidence:
{evidence}

Analyze the evidence and determine:
1. Does the evidence support, contradict, or neither support nor contradict the claim?
2. How confident are you in this assessment?
3. If the claim is inaccurate, what would be the correct information?

Return JSON:
{{
  "verdict": "supported|contradicted|unclear",
  "confidence": 0-100,
  "explanation": "Brief explanation of your reasoning",
  "suggested_revision": "Corrected claim if needed, or null if accurate"
}}"""


def extract_claims(content: str) -> list[dict[str, Any]]:
    """Extract factual claims from article content."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return [
            {
                "claim": "The first computer was invented in 1943.",
                "type": "historical",
                "confidence": "high",
            },
            {
                "claim": "Python was created by Guido van Rossum.",
                "type": "historical",
                "confidence": "high",
            },
        ]

    logger.info("Extracting claims from content")

    llm = OpenRouterClient()

    # Truncate content if too long
    max_content = 15000  # ~4000 tokens
    if len(content) > max_content:
        content = content[:max_content] + "..."

    prompt = CLAIM_EXTRACTION_PROMPT.format(content=content)

    response = llm.extract_json(prompt)
    claims = response.get("claims", [])

    logger.info(f"Extracted {len(claims)} claims")
    return claims


def filter_checkworthy_claims(claims: list[dict]) -> list[dict]:
    """Filter to keep only checkworthy claims.

    Args:
        claims: List of extracted claims

    Returns:
        Filtered list of checkworthy claims
    """
    # Common knowledge patterns to filter out
    common_knowledge_patterns = [
        "is a programming language",
        "is a framework",
        "is used for",
        "was created",
        "is popular",
        "is widely used",
    ]

    filtered = []
    for claim in claims:
        claim_text = claim.get("claim", "").lower()

        # Skip low confidence claims
        if claim.get("confidence") == "low":
            continue

        # Skip common knowledge
        is_common = any(pattern in claim_text for pattern in common_knowledge_patterns)
        if is_common and claim.get("confidence") != "high":
            continue

        # Keep the claim
        filtered.append(claim)

    # Limit to 10 claims max
    filtered = filtered[:10]

    logger.info(f"Filtered to {len(filtered)} checkworthy claims")
    return filtered


def retrieve_evidence(claim: str) -> list[dict[str, Any]]:
    """Retrieve evidence for a claim using web search."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return [
            {
                "url": "https://wikipedia.org",
                "title": "Wikipedia",
                "snippet": "Evidence supports this claim.",
            }
        ]

    llm = OpenRouterClient()

    result = llm.get_evidence(claim, source_count=3)
    sources = result.get("sources", [])

    # Add the answer as context
    if result.get("answer"):
        sources.insert(
            0,
            {
                "url": "perplexity_synthesis",
                "title": "Web Search Summary",
                "snippet": result["answer"][:500],
            },
        )

    return sources


def verify_claim(claim: str, evidence: list[dict]) -> dict[str, Any]:
    """Verify a claim against evidence."""
    from blog_automation.config import get_settings

    if get_settings().mock_mode:
        return {
            "verdict": "supported",
            "confidence": 100,
            "explanation": "Mock verification.",
            "suggested_revision": None,
        }

    llm = OpenRouterClient()

    # Format evidence
    evidence_text = ""
    for source in evidence:
        evidence_text += f"\nSource: {source.get('url', 'Unknown')}\n"
        evidence_text += f"Title: {source.get('title', 'N/A')}\n"
        evidence_text += f"Content: {source.get('snippet', 'N/A')}\n"

    prompt = CLAIM_VERIFICATION_PROMPT.format(
        claim=claim,
        evidence=evidence_text or "No evidence found",
    )

    result = llm.extract_json(prompt)

    return {
        "verdict": result.get("verdict", "unclear"),
        "confidence": result.get("confidence", 50),
        "explanation": result.get("explanation", ""),
        "suggested_revision": result.get("suggested_revision"),
    }


def generate_fact_check_report(
    article: Article,
    claims: list[dict],
) -> dict[str, Any]:
    """Generate comprehensive fact-check report.

    Args:
        article: Article being checked
        claims: List of claims to verify

    Returns:
        Fact-check report dictionary
    """
    logger.info(
        "Generating fact-check report",
        article_id=article.id,
        claim_count=len(claims),
    )

    report = {
        "total_claims_checked": len(claims),
        "supported": 0,
        "contradicted": 0,
        "unclear": 0,
        "issues_found": [],
        "claims_verified": [],
        "generated_at": datetime.utcnow().isoformat(),
    }

    for claim in claims:
        claim_text = claim.get("claim", "")

        # Retrieve evidence
        evidence = retrieve_evidence(claim_text)

        # Verify claim
        verification = verify_claim(claim_text, evidence)

        # Update counts
        verdict = verification.get("verdict", "unclear").lower()
        if verdict == "supported":
            report["supported"] += 1
        elif verdict == "contradicted":
            report["contradicted"] += 1
        else:
            report["unclear"] += 1

        # Record verification
        claim_record = {
            "claim": claim_text,
            "type": claim.get("type", "unknown"),
            "verdict": verdict,
            "confidence": verification.get("confidence", 50),
            "explanation": verification.get("explanation", ""),
            "sources_checked": len(evidence),
        }
        report["claims_verified"].append(claim_record)

        # Track issues
        if verdict != "supported":
            report["issues_found"].append(
                {
                    "claim": claim_text,
                    "verdict": verdict,
                    "confidence": verification.get("confidence", 50),
                    "explanation": verification.get("explanation", ""),
                    "suggested_revision": verification.get("suggested_revision"),
                }
            )

    # Calculate accuracy rate
    if report["total_claims_checked"] > 0:
        report["accuracy_rate"] = (
            report["supported"] / report["total_claims_checked"]
        ) * 100
    else:
        report["accuracy_rate"] = 100.0

    # Determine pass/fail
    report["pass"] = report["contradicted"] == 0 and report["accuracy_rate"] >= 95

    logger.info(
        "Fact-check report generated",
        article_id=article.id,
        accuracy=f"{report['accuracy_rate']:.1f}%",
        passed=report["pass"],
    )

    return report


def fact_check_article(article: Article) -> dict[str, Any]:
    """Complete fact-checking pipeline for an article.

    Args:
        article: Article to fact-check

    Returns:
        Fact-check report

    Raises:
        ProcessingError: If fact-checking fails
    """
    logger.info("Starting fact-check pipeline", article_id=article.id)

    try:
        with get_session() as session:
            # Get fresh article from session
            article = session.query(Article).get(article.id)
            if not article:
                raise VerificationFailureError(
                    message=f"Article {article.id} not found",
                )

            # Update status
            article.status = "fact_checking"
            session.commit()

            content = article.content_draft or ""
            if not content:
                raise VerificationFailureError(
                    message="Article has no content to fact-check",
                    context={"article_id": article.id},
                )

            # Extract claims
            claims = extract_claims(content)
            logger.info(f"Extracted {len(claims)} claims", article_id=article.id)

            # Filter to checkworthy claims
            checkworthy = filter_checkworthy_claims(claims)
            logger.info(
                f"Filtered to {len(checkworthy)} checkworthy claims",
                article_id=article.id,
            )

            # Generate report
            report = generate_fact_check_report(article, checkworthy)

            # Update article
            article.fact_check_report = report
            article.fact_check_passed = report["pass"]
            article.fact_check_date = datetime.utcnow()
            article.fact_check_issues = len(report["issues_found"])

            # Update status based on result
            if report["pass"]:
                article.status = "editing"
            else:
                article.status = "fact_checking_issues"

            session.commit()

            logger.info(
                "Fact-check complete",
                article_id=article.id,
                passed=report["pass"],
                issues=len(report["issues_found"]),
            )

            return report

    except VerificationFailureError:
        raise
    except Exception as e:
        raise ProcessingError(
            message=f"Fact-checking failed: {str(e)}",
            step="fact_checking",
            context={"article_id": article.id if article else None},
        ) from e
