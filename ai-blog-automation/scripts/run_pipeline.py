#!/usr/bin/env python3
"""
Pipeline Runner Script
======================
Run individual pipelines from the command line.

Usage:
    poetry run python scripts/run_pipeline.py research "your keyword"
    poetry run python scripts/run_pipeline.py brief <brief_id>
    poetry run python scripts/run_pipeline.py draft <brief_id>
    poetry run python scripts/run_pipeline.py factcheck <article_id>
    poetry run python scripts/run_pipeline.py seo <article_id>
    poetry run python scripts/run_pipeline.py publish <article_id>
    poetry run python scripts/run_pipeline.py full "your keyword"
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()


def cmd_research(keyword: str):
    """Run keyword research pipeline."""
    print(f"🔍 Researching keyword: {keyword}")
    
    from blog_automation.pipelines import research_keyword
    brief = research_keyword(keyword)
    
    print(f"✅ Brief created: ID={brief.id}")
    print(f"   Volume: {brief.search_volume}")
    print(f"   Difficulty: {brief.difficulty}")
    return brief


def cmd_brief(keyword: str):
    """Generate full content brief."""
    print(f"📝 Generating brief for: {keyword}")
    
    from blog_automation.pipelines import research_keyword_full
    brief = research_keyword_full(keyword)
    
    print(f"✅ Full brief created: ID={brief.id}")
    print(f"   Sections: {len(brief.get_sections())}")
    print(f"   LSI Keywords: {len(brief.get_lsi_keywords())}")
    return brief


def cmd_draft(brief_id: int):
    """Generate article draft from brief."""
    print(f"✍️  Generating draft from brief ID: {brief_id}")
    
    from blog_automation.models import get_session, ContentBrief
    from blog_automation.pipelines import content_brief_to_draft
    
    with get_session() as session:
        brief = session.query(ContentBrief).get(brief_id)
        if not brief:
            print(f"❌ Brief {brief_id} not found")
            return None
        
        article = content_brief_to_draft(brief, session)
        print(f"✅ Article created: ID={article.id}")
        print(f"   Title: {article.title}")
        print(f"   Words: {article.word_count}")
        return article


def cmd_factcheck(article_id: int):
    """Run fact-checking on article."""
    print(f"🔬 Fact-checking article ID: {article_id}")
    
    from blog_automation.models import get_session, Article
    from blog_automation.pipelines import fact_check_article
    
    with get_session() as session:
        article = session.query(Article).get(article_id)
        if not article:
            print(f"❌ Article {article_id} not found")
            return None
        
        report = fact_check_article(article, session)
        print(f"✅ Fact-check complete")
        print(f"   Claims checked: {report.get('total_claims', 0)}")
        print(f"   Accuracy: {report.get('accuracy_rate', 0):.1f}%")
        return report


def cmd_seo(article_id: int):
    """Run SEO optimization on article."""
    print(f"📈 Optimizing SEO for article ID: {article_id}")
    
    from blog_automation.models import get_session, Article
    from blog_automation.pipelines import seo_optimize_article
    
    with get_session() as session:
        article = session.query(Article).get(article_id)
        if not article:
            print(f"❌ Article {article_id} not found")
            return None
        
        result = seo_optimize_article(article, session)
        print(f"✅ SEO optimization complete")
        print(f"   Meta title: {article.meta_title}")
        print(f"   SEO score: {article.seo_score}")
        return result


def cmd_publish(article_id: int):
    """Publish article to WordPress."""
    print(f"🚀 Publishing article ID: {article_id}")
    
    from blog_automation.models import get_session, Article
    from blog_automation.pipelines import publish_article
    
    with get_session() as session:
        article = session.query(Article).get(article_id)
        if not article:
            print(f"❌ Article {article_id} not found")
            return None
        
        result = publish_article(article, session)
        print(f"✅ Published!")
        print(f"   URL: {article.wordpress_url}")
        print(f"   Post ID: {article.wordpress_post_id}")
        return result


def cmd_full(keyword: str):
    """Run full pipeline from keyword to draft."""
    print(f"🎯 Running full pipeline for: {keyword}")
    print("=" * 50)
    
    # Step 1: Research
    brief = cmd_brief(keyword)
    if not brief:
        return None
    
    print()
    
    # Step 2: Draft
    from blog_automation.models import get_session
    from blog_automation.pipelines import content_brief_to_draft
    
    with get_session() as session:
        session.add(brief)
        article = content_brief_to_draft(brief, session)
        
        print(f"\n{'=' * 50}")
        print(f"✅ COMPLETE!")
        print(f"   Article ID: {article.id}")
        print(f"   Title: {article.title}")
        print(f"   Words: {article.word_count}")
        print(f"\nNext steps:")
        print(f"   poetry run python scripts/run_pipeline.py factcheck {article.id}")
        print(f"   poetry run python scripts/run_pipeline.py seo {article.id}")
        print(f"   poetry run python scripts/run_pipeline.py publish {article.id}")
        
        return article


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    
    command = sys.argv[1].lower()
    
    commands = {
        "research": (cmd_research, str, "keyword"),
        "brief": (cmd_brief, str, "keyword"),
        "draft": (cmd_draft, int, "brief_id"),
        "factcheck": (cmd_factcheck, int, "article_id"),
        "seo": (cmd_seo, int, "article_id"),
        "publish": (cmd_publish, int, "article_id"),
        "full": (cmd_full, str, "keyword"),
    }
    
    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print(f"   Available: {', '.join(commands.keys())}")
        return 1
    
    if len(sys.argv) < 3:
        func, arg_type, arg_name = commands[command]
        print(f"❌ Missing argument: {arg_name}")
        return 1
    
    func, arg_type, _ = commands[command]
    arg = arg_type(sys.argv[2])
    
    try:
        result = func(arg)
        return 0 if result else 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
