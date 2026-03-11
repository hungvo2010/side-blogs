# Deployment & API Onboarding Guide

## 🚀 One-Command Deployment
Run the following from the `ai-blog-automation` directory:
```bash
make setup   # Creates .env file
# (Edit .env with API keys)
make deploy  # Builds and starts all services
```

---

## 🛠️ Deployment Checklist
- [ ] **Infrastructure:** Docker & Docker Compose installed.
- [ ] **Environment:** `.env` populated with all 3rd party API keys.
- [ ] **Database:** PostgreSQL container is healthy and migrations applied (via `make deploy`).
- [ ] **WordPress:** REST API and Application Passwords configured on target site.
- [ ] **Analytics:** Google Service Account JSON file path set in `src/blog_automation/config.py`.

---

## 🔌 Required 3rd Party APIs

| Service | Purpose | Get Key Link |
| :--- | :--- | :--- |
| **OpenAI** | Article Drafting (GPT-4) | [platform.openai.com](https://platform.openai.com/api-keys) |
| **Anthropic** | Fact-Checking (Claude 3) | [console.anthropic.com](https://console.anthropic.com/) |
| **Ahrefs** | Keyword Research & SERP | [ahrefs.com/api](https://ahrefs.com/api) |
| **Perplexity** | Real-time Evidence Retrieval | [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api) |
| **Copyscape** | Plagiarism Detection | [copyscape.com/api.php](https://www.copyscape.com/api.php) |
| **Rank Math** | SEO Scoring & Analysis | [rankmath.com](https://rankmath.com/) (Requires Plugin) |
| **WordPress** | Automated Publishing | Target Site Admin -> Users -> Profile |

### Steps to Automate Key Retrieval
To speed up onboarding, follow this sequence:

1.  **AI Bundle (OpenAI + Anthropic):**
    *   Create accounts on both.
    *   Set up a **Credit Balance** (min $5 each) to avoid initial rate limits.
    *   Generate keys and paste them into `.env` immediately.

2.  **Research Bundle (Ahrefs + Perplexity):**
    *   **Ahrefs:** Requires a paid plan for API v2 access.
    *   **Perplexity:** Join the "pplx-api" beta. It uses an OpenAI-compatible format, making integration seamless.

3.  **Publishing Bundle (WordPress + Google):**
    *   **WordPress:** Go to `Users -> Profile` on your WP site. Scroll to "Application Passwords". Name it "AI-Platform" and copy the generated 24-character string.
    *   **Google Cloud:** Go to [GCP Console](https://console.cloud.google.com/). Create a Project -> Service Account -> Keys -> Create New JSON Key. Save this file as `service-account.json` in the root directory.

---

## 🛑 Critical Monitoring
Once deployed, monitor the logs for these common failures:
- `429 (Too Many Requests)` on OpenAI: Upgrade your tier.
- `401 (Unauthorized)` on WordPress: Ensure the user has "Editor" or "Administrator" permissions.
- `Database Connection Refused`: Ensure the `db` container is fully started before the `app` container (handled by `depends_on`).
