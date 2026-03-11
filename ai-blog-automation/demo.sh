#!/bin/bash
set -e

echo "🎬 Preparing Sample Article..."

# 1. Start Platform (if not already running)
./start.sh --remove-orphans

# 2. Seed Sample Article with Full API Integrations (Pre-Generated Mock)
echo "🌱 Injecting Sample Article into Database..."
docker-compose exec -T app python scripts/seed_demo.py

# 3. Export to Static HTML (Separate Page)
echo "📄 Generating Standalone Blog Page..."
docker-compose exec -T app python scripts/export_static.py 1

echo "--------------------------------------------------------"
echo "🚀 DONE! You can now view the sample article."
echo "--------------------------------------------------------"
echo "👉 Dashboard: http://localhost:8501"
echo "👉 Static Page: file://$(pwd)/dist/ai-content-marketing-revolution-2024.html"
echo "👉 Select '📋 Review Queue' in the sidebar to view the sample article."
echo "👉 View the Article's Fact-Check Report and SEO Optimization results."
echo "--------------------------------------------------------"
