# =============================================================================
# SEED Agent Makefile - Development and deployment commands
# =============================================================================

.PHONY: help build up down logs test clean dev prod metrics

# Default target
help:
	@echo "SEED Agent - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  dev          - Start development environment"
	@echo "  logs         - Show logs from all services"
	@echo "  test         - Run tests"
	@echo "  shell        - Open shell in agent container"
	@echo ""
	@echo "Production:"
	@echo "  build        - Build Docker images"
	@echo "  up           - Start production environment"
	@echo "  down         - Stop all services"
	@echo "  restart      - Restart all services"
	@echo ""
	@echo "Monitoring:"
	@echo "  metrics      - Start with Prometheus and Grafana"
	@echo "  stats        - Show agent statistics"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean        - Clean up Docker resources"
	@echo "  backup       - Backup configuration and data"
	@echo ""

# Development commands
dev:
	@echo "🚀 Starting SEED Agent in development mode..."
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build

dev-daemon:
	@echo "🚀 Starting SEED Agent in development mode (daemon)..."
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up --build -d

# Production commands
build:
	@echo "🏗️  Building SEED Agent..."
	docker-compose build --no-cache

up:
	@echo "🚀 Starting SEED Agent in production mode..."
	docker-compose up -d

down:
	@echo "🛑 Stopping SEED Agent..."
	docker-compose down

restart:
	@echo "🔄 Restarting SEED Agent..."
	docker-compose restart

# Monitoring commands
metrics:
	@echo "📊 Starting SEED Agent with metrics..."
	docker-compose --profile metrics up -d

logs:
	@echo "📋 Showing logs..."
	docker-compose logs -f

logs-agent:
	@echo "📋 Showing agent logs..."
	docker-compose logs -f seed-agent

stats:
	@echo "📊 Agent statistics:"
	@curl -s http://localhost:8080/stats | python -m json.tool || echo "Agent not running"

# Testing and debugging
test:
	@echo "🧪 Running tests..."
	docker-compose exec seed-agent python -m pytest tests/ -v

test-plugins:
	@echo "🔌 Testing plugins..."
	docker-compose exec seed-agent python plugins.py list
	docker-compose exec seed-agent python plugins.py test host_inventory
	docker-compose exec seed-agent python plugins.py test mongo_hot

shell:
	@echo "🐚 Opening shell in agent container..."
	docker-compose exec seed-agent /bin/bash

shell-rabbitmq:
	@echo "🐚 Opening shell in RabbitMQ container..."
	docker-compose exec rabbitmq /bin/bash

shell-redis:
	@echo "🐚 Opening shell in Redis container..."
	docker-compose exec redis /bin/sh

# Health checks
health:
	@echo "🏥 Health check:"
	@curl -s http://localhost:8080/health | python -m json.tool || echo "Agent not healthy"

health-all:
	@echo "🏥 Full health check:"
	@echo "Agent:"
	@curl -s http://localhost:8080/health | python -m json.tool || echo "Agent not healthy"
	@echo ""
	@echo "RabbitMQ:"
	@docker-compose exec rabbitmq rabbitmq-diagnostics ping || echo "RabbitMQ not healthy"
	@echo ""
	@echo "Redis:"
	@docker-compose exec redis redis-cli ping || echo "Redis not healthy"

# Configuration management
reload-config:
	@echo "🔄 Reloading configuration..."
	@curl -s http://localhost:8080/config/reload | python -m json.tool || echo "Failed to reload config"

validate-config:
	@echo "✅ Validating configuration..."
	@python -c "import yaml; yaml.safe_load(open('seed.yaml'))" && echo "Configuration is valid"

# Maintenance commands
clean:
	@echo "🧹 Cleaning up Docker resources..."
	docker-compose down --volumes --remove-orphans
	docker system prune -f
	docker volume prune -f

backup:
	@echo "💾 Creating backup..."
	@mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	@cp seed.yaml backups/$(shell date +%Y%m%d_%H%M%S)/
	@cp plugins.py backups/$(shell date +%Y%m%d_%H%M%S)/
	@cp docker-compose.yml backups/$(shell date +%Y%m%d_%H%M%S)/
	@echo "Backup created in backups/$(shell date +%Y%m%d_%H%M%S)/"

# Monitoring and debugging
monitor:
	@echo "👁️  Monitoring agent (Ctrl+C to stop)..."
	@watch -n 5 'curl -s http://localhost:8080/stats | python -m json.tool'

tail-logs:
	@echo "📜 Tailing logs..."
	@tail -f logs/seed-agent.log

# Quick start
quick-start: build up
	@echo "✅ SEED Agent started!"
	@echo "📊 Dashboard: http://localhost:15672 (seed/seed123)"
	@echo "🔧 API: http://localhost:8080"
	@echo "📋 Health: http://localhost:8080/health"
	@echo "📊 Stats: http://localhost:8080/stats"

# Development workflow
dev-workflow:
	@echo "🔧 Starting development workflow..."
	@make dev-daemon
	@sleep 10
	@make health-all
	@make test-plugins
	@echo "✅ Development environment ready!"