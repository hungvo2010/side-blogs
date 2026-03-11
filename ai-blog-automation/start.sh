#!/bin/bash
set -e

echo "🚀 Starting AI Blog Automation Platform..."

# 1. Ensure .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  WARNING: Using default/empty API keys. Some features will fail until you edit .env"
fi

# 2. Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# 3. Build and Start Services
echo "📦 Building and starting containers (this may take a minute)..."
docker-compose up -d --build "$@"

# 4. Wait for Database to be ready
echo "⏳ Waiting for database to initialize..."
MAX_RETRIES=30
COUNT=0
until docker-compose exec db pg_isready -U user -d blog_db >/dev/null 2>&1 || [ $COUNT -eq $MAX_RETRIES ]; do
    sleep 2
    COUNT=$((COUNT+1))
    echo -n "."
done

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Error: Database timed out."
    exit 1
fi

# 5. Run Migrations
echo -e "\n🛠️  Resetting database schema..."
docker-compose exec -T db psql -U user -d blog_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo -e "\n🛠️  Running database migrations..."
docker-compose exec -T app alembic upgrade head

echo "--------------------------------------------------------"
echo "✅ SUCCESS: Platform is running!"
echo "--------------------------------------------------------"
echo "📊 Human Review Dashboard: http://localhost:8501"
echo "--------------------------------------------------------"
echo "💡 To stop everything, run: docker-compose down"
echo "💡 To see logs, run: docker-compose logs -f"
