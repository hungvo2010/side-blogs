"""Rank Math API client for SEO analysis.

Provides SEO scoring and optimization recommendations.
"""

from typing import Any

from blog_automation.logging_config import get_logger

logger = get_logger(__name__)


class RankMathClient:
    """Rank Math SEO analysis client.

    Note: Rank Math doesn't have a public API, so this provides
    local SEO analysis based on Rank Math's scoring criteria.
    """

    def __init__(self):
        """Initialize Rank Math client."""
        logger.info("RankMath client initialized (local analysis)")

    def analyze_content(
        self,
        content: str,
        keyword: str,
        title: str | None = None,
        meta_description: str | None = None,
    ) -> dict[str, Any]:
        """Analyze content for SEO.

        Args:
            content: Article content
            keyword: Target keyword
            title: Article title
            meta_description: Meta description

        Returns:
            SEO analysis with score and recommendations
        """
        issues = []
        suggestions = []
        score = 0
        max_score = 100

        # Word count check
        word_count = len(content.split())
        if word_count >= 1500:
            score += 15
        elif word_count >= 1000:
            score += 10
            suggestions.append(f"Add {1500 - word_count} more words for optimal length")
        else:
            issues.append(f"Content too short ({word_count} words, need 1500+)")

        # Keyword in content
        keyword_lower = keyword.lower()
        content_lower = content.lower()
        keyword_count = content_lower.count(keyword_lower)

        if 3 <= keyword_count <= 10:
            score += 15
        elif keyword_count < 3:
            issues.append(f"Keyword appears only {keyword_count} times (need 3-5)")
        else:
            issues.append(f"Keyword stuffing detected ({keyword_count} occurrences)")

        # Keyword density
        density = (keyword_count / word_count) * 100 if word_count > 0 else 0
        if 0.5 <= density <= 1.5:
            score += 10
        elif density < 0.5:
            suggestions.append("Increase keyword density (target 0.5-1.5%)")
        else:
            issues.append(f"Keyword density too high ({density:.1f}%)")

        # Title checks
        if title:
            if keyword_lower in title.lower():
                score += 10
            else:
                issues.append("Keyword not in title")

            if len(title) <= 60:
                score += 5
            else:
                issues.append(f"Title too long ({len(title)} chars, max 60)")

            # Keyword at start of title
            if title.lower().startswith(keyword_lower):
                score += 5
            elif keyword_lower in title.lower()[:30]:
                score += 3
        else:
            issues.append("No title provided")

        # Meta description checks
        if meta_description:
            if keyword_lower in meta_description.lower():
                score += 10
            else:
                suggestions.append("Add keyword to meta description")

            if 150 <= len(meta_description) <= 160:
                score += 5
            elif len(meta_description) < 150:
                suggestions.append(
                    f"Meta description too short ({len(meta_description)} chars)"
                )
            else:
                issues.append(
                    f"Meta description too long ({len(meta_description)} chars)"
                )
        else:
            issues.append("No meta description provided")

        # Heading structure
        h2_count = content.count("## ") + content.count("<h2")
        if h2_count >= 3:
            score += 10
        elif h2_count >= 1:
            score += 5
            suggestions.append("Add more H2 headings (target 3-5)")
        else:
            issues.append("No H2 headings found")

        # Internal links (check for markdown links)
        internal_links = content.count("](/") + content.count('href="/')
        if internal_links >= 3:
            score += 10
        elif internal_links >= 1:
            score += 5
            suggestions.append("Add more internal links (target 3-5)")
        else:
            suggestions.append("Add internal links to related content")

        # External links
        external_links = content.count("](http") + content.count('href="http')
        if external_links >= 3:
            score += 5
        elif external_links >= 1:
            score += 3
        else:
            suggestions.append("Add external links to authoritative sources")

        return {
            "score": min(score, max_score),
            "max_score": max_score,
            "grade": self._score_to_grade(score),
            "issues": issues,
            "suggestions": suggestions,
            "metrics": {
                "word_count": word_count,
                "keyword_count": keyword_count,
                "keyword_density": round(density, 2),
                "h2_count": h2_count,
                "internal_links": internal_links,
                "external_links": external_links,
            },
        }

    def _score_to_grade(self, score: int) -> str:
        """Convert score to letter grade.

        Args:
            score: Numeric score

        Returns:
            Letter grade
        """
        if score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        return "F"

    def get_recommendations(
        self,
        analysis: dict[str, Any],
    ) -> list[str]:
        """Get prioritized recommendations.

        Args:
            analysis: Analysis result from analyze_content

        Returns:
            List of prioritized recommendations
        """
        recommendations = []

        # High priority: issues
        for issue in analysis.get("issues", []):
            recommendations.append(f"🔴 {issue}")

        # Medium priority: suggestions
        for suggestion in analysis.get("suggestions", []):
            recommendations.append(f"🟡 {suggestion}")

        return recommendations
