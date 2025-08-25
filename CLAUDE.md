# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEED Agent v4/v5 - компактная система мониторинга и уведомлений с единой архитектурой.

## Project Structure

The project contains two main versions:
- **v4/**: Current stable version with simplified architecture
- **v5/**: Next version with enhanced features

### Core Architecture (v4)
- **seed-agent.py**: Main FastAPI HTTP server (port 8080)  
- **core/**: Core modules for alert processing
  - `config.py`: Configuration management with YAML and .env support
  - `alert_processor.py`: Alert processing and lifecycle management
  - `llm.py`: LLM integration (GigaChat) for intelligent alert analysis
  - `notify.py`: Multi-channel notification system (Mattermost, Slack, Email)
  - `queue.py`: RabbitMQ queue management
  - `redis_throttle.py`: Redis-based throttling and caching
- **fetchers/**: Data fetchers for external systems (MongoDB, Telegraf)
- **seed.yaml**: Main configuration file
- **seed.env**: Environment variables (credentials)

## Development Commands

### Starting/Stopping the System
```bash
cd v4/
./start.sh    # Start full stack (Redis, RabbitMQ, SEED Agent)
./stop.sh     # Stop all services
```

### Testing
```bash
# Comprehensive smoke test
./smoke-test.sh

# Manual test alerts
python3 test_alerts.py

# Health check
curl http://localhost:8080/health

# Test alert via API
curl -X POST http://localhost:8080/alert \
  -H 'Content-Type: application/json' \
  -d '{"alerts":[{"labels":{"alertname":"Test","instance":"localhost","severity":"warning"},"annotations":{"summary":"Test alert"},"status":"firing"}]}'
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
# Setup environment file
cp seed.env.example seed.env
# Edit seed.env with actual credentials (GIGACHAT_CLIENT_ID, etc.)

# Reload configuration (hot reload)
curl -X POST http://localhost:8080/config/reload
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
- LLM requires GigaChat credentials (GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET)
- System ready for production deployment
- Hot configuration reload supported via API
- Comprehensive logging with emoji markers for easy filtering