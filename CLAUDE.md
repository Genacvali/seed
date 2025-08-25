# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEED Agent v4/v5 - компактная система мониторинга и уведомлений с единой архитектурой.

## Project Structure

The project contains two main versions:
- **v4/**: Current stable version with simplified architecture
- **v5/**: Enhanced version with FF-styled branding, colored notifications, and compact formatting

### Core Architecture (Both Versions)
- **seed-agent.py**: Main FastAPI HTTP server (port 8080)  
- **core/**: Core modules for alert processing
  - `config.py`: Configuration management with YAML and .env support
  - `alert_processor.py`: Alert processing and lifecycle management
  - `llm.py`: LLM integration (GigaChat) for intelligent alert analysis
  - `notify.py`: Multi-channel notification system (Mattermost, Slack, Email)
  - `queue.py`: RabbitMQ queue management
  - `redis_throttle.py`: Redis-based throttling and caching
  - `formatter.py`: Message formatting (v5 has enhanced FF-style formatting)
- **fetchers/**: Data fetchers for external systems (MongoDB, Telegraf) - v4 only
- **seed.yaml**: Main configuration file
- **seed.env**: Environment variables (credentials)

### v5 Enhancements
- **🌌 SEED Branding**: Final Fantasy themed bot identity with crystal ball icon
- **Colored Notifications**: Severity-based color coding for Mattermost (red=critical, orange=high, yellow=warning, blue=info)
- **Compact Formatting**: Auto-truncated LLM recommendations (500 chars) with full text logged
- **FF Emoji Icons**: 💎🔥 Critical, ⚔️ High, 🛡️ Warning, ✨ Info, ❔ Unknown

## Development Commands

### Starting/Stopping the System
```bash
# For v4
cd v4/
./start.sh    # Start full stack (Redis, RabbitMQ, SEED Agent)
./stop.sh     # Stop all services

# For v5 (same commands)
cd v5/
./start.sh    # Start with enhanced FF branding
./stop.sh     # Stop all services
```

### Testing
```bash
# Comprehensive smoke test (available in both versions)
./smoke-test.sh

# Manual test alerts (v4 only)
python3 test_alerts.py

# Health check
curl http://localhost:8080/health

# Test alert via API
curl -X POST http://localhost:8080/alert \
  -H 'Content-Type: application/json' \
  -d '{"alerts":[{"labels":{"alertname":"Test","instance":"localhost","severity":"warning"},"annotations":{"summary":"Test alert"},"status":"firing"}]}'

# Watch logs with emoji filtering (useful for troubleshooting)
tail -f seed-agent.log | grep -E "(📁|✅|❌|📤)"
```

### Dependencies
```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Check Python dependencies availability
python3 -c "import fastapi, uvicorn, aio_pika, redis, pymongo, yaml, requests, dotenv"
```

### Build and Deployment
```bash
# Build binary (requires PyInstaller)
./build-agent.sh

# Service installation
sudo ./install-service.sh      # Linux
./install-service.ps1          # Windows PowerShell

# Docker image management
./export-images.sh            # Export images to tar files
./load-images.sh             # Load images from tar files
```

### Configuration
```bash
# Setup environment file (required for both versions)
cp seed.env.example seed.env
# Edit seed.env with actual GigaChat credentials (GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET)

# Reload configuration (hot reload) - recreates LLM and notification clients
curl -X POST http://localhost:8080/config/reload

# View current configuration (without secrets)
curl http://localhost:8080/config

# LLM diagnostics
curl http://localhost:8080/llm/selftest
```

## Key API Endpoints

- `POST /alert` - Receive alerts from Alertmanager
- `GET /health` - System health status  
- `GET /dashboard` - Live metrics and status
- `GET /config` - Current configuration view
- `GET /llm/selftest` - LLM service diagnostics
- `POST /config/reload` - Hot configuration reload
- `GET /metrics` - Prometheus-style metrics
- `GET /alerts/test` - Available test alerts

## System Components

- **SEED Agent**: FastAPI server on port 8080
- **Redis**: Caching and throttling (port 6379)
- **RabbitMQ**: Message queues (ports 5672/15672) 
- **GigaChat LLM**: Intelligent alert analysis and formatting
- **Notification Channels**: Mattermost, Slack, Email
- **Data Fetchers**: MongoDB, Telegraf integration

## Performance Characteristics

- **Memory**: ~100MB agent + 450MB infrastructure
- **CPU**: <1% idle, scales with alert volume  
- **Throughput**: >1000 alerts/second
- **Dependencies**: Docker for Redis/RabbitMQ, Python 3.8+

## Important Notes

- All configuration in `seed.yaml` with secrets in `seed.env`
- **CRITICAL**: LLM requires ALL GigaChat credentials in `seed.env` (GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET, GIGACHAT_SCOPE, etc.)
- Without complete GigaChat config, LLM will be disabled (`llm: false` in health check)
- System ready for production deployment (both v4 and v5)
- Hot configuration reload supported via API - recreates LLM and notification clients
- Comprehensive logging with emoji markers for easy filtering
- v5 features colored Mattermost notifications and compact LLM recommendations