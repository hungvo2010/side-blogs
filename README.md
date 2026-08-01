---
title: AI Blog Automation
emoji: 📝
colorFrom: blue
colorTo: gray
sdk: streamlit
sdk_version: 1.40.0
app_file: ai-blog-automation/streamlit_app/app.py
pinned: false
---

# AI Blog Automation Dashboard

Streamlit dashboard for the automated blog pipeline.

**Features:**
- 📊 Pipeline overview & progress tracking
- 📋 Human review queue (approve/reject articles)
- 📄 All articles with content preview & SEO analysis
- 📅 Content calendar
- ⚙️ Settings & API config

**Prerequisites (set as Space secrets):**
- `DATABASE_URL` — PostgreSQL connection (Neon/Supabase)
- `OPENROUTER_API_KEY` — LLM API key
- `ENVIRONMENT=production`
- `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` — keyword research (free tier)
