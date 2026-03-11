# ai-blog-automation/Makefile
.PHONY: deploy setup clean test

deploy:
	@echo "🚀 Deploying AI Blog Automation Platform..."
	docker-compose up -d --build
	@echo "✅ Deployment complete!"
	@echo "📊 Dashboard: http://localhost:8501"

setup:
	@echo "🛠️  Setting up environment..."
	cp .env.example .env
	@echo "⚠️  Please edit .env with your API keys before running 'make deploy'."

test:
	docker-compose run app pytest

clean:
	docker-compose down -v
