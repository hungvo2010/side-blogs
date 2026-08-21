#!/usr/bin/env python3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blog_automation.models import Article, get_session


def seed_demo():
    print("🌱 Seeding high-quality demo article...")

    with get_session() as session:
        # Create a sample article with full integration data
        article = Article(
            title="How AI is Revolutionizing Content Marketing in 2024",
            slug="ai-content-marketing-revolution-2024",
            keyword="AI content marketing",
            status="pending_review",
            ai_model_used="gpt-4-turbo",
            ai_generation_cost=0.45,
            word_count=1850,
            seo_score=88,
            meta_title="AI Content Marketing Revolution 2024: The Ultimate Guide",
            meta_description="Discover how AI is transforming content marketing in 2024. Learn to leverage GPT-4, Claude 3, and automated pipelines for 10x growth.",
            content_draft="""
# How AI is Revolutionizing Content Marketing in 2024

The landscape of digital marketing is shifting under our feet. In 2024, the integration of Artificial Intelligence (AI) is no longer a luxury—it's a survival requirement for content marketers.

## 1. The Shift to Automated Quality

Gone are the days when AI meant low-quality, repetitive text. With the advent of large language models like GPT-4 and Claude 3, the focus has shifted from quantity to *quality at scale*.

### Leveraging E-E-A-T
Google's emphasis on Experience, Expertise, Authoritativeness, and Trustworthiness (E-E-A-T) means that AI content must be more than just grammatically correct. It needs to provide real value and verifiable facts.

## 2. Fact-Checking: The New Frontier

One of the biggest risks of AI content is hallucination. Modern pipelines now include automated fact-checking layers. By using evidence retrieval tools like Perplexity AI, we can verify claims against real-world data in real-time.

## 3. SEO Optimization Beyond Keywords

SEO in 2024 is about user intent and content depth. Tools like Rank Math and SurferSEO help ensure that our AI-generated content matches the topical authority required to rank on the first page of Google.

## Conclusion

As we look forward, the synergy between human creativity and AI efficiency will define the next decade of marketing success.
            """,
            fact_check_report={
                "total_claims_checked": 12,
                "accuracy_rate": 100.0,
                "pass": True,
                "issues_found": [],
            },
            seo_analysis={
                "score": 88,
                "grade": "A",
                "issues": ["Add more internal links", "Include a featured image"],
                "suggestions": [
                    "Add an H3 subheading about 'Claude 3' technical details",
                    "Increase keyword density slightly in the conclusion",
                ],
            },
        )

        session.add(article)
        session.commit()

        print(f"✅ Demo article created with ID: {article.id}")
        print("🔗 View it at: http://localhost:8501")


if __name__ == "__main__":
    seed_demo()
