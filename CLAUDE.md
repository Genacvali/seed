# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEED Agent v5 - универсальная LLM-powered система обработки алертов с поддержкой мониторинга production окружений. Компактная архитектура с поддержкой GigaChat LLM, цветными уведомлениями и Final Fantasy стилизацией.

## Project Structure

This repository contains:
- **v5/**: Production-ready enhanced version with FF-styled branding, colored notifications, and compact formatting
- **zabbix-webhook scripts**: Integration scripts for Zabbix monitoring systems
- **Docker configuration files**: For infrastructure setup and deployment

### Core Architecture
- **seed-agent.py**: Main FastAPI HTTP server (port 8080)  
- **core/**: Core modules for alert processing
  - `config.py`: Configuration management with YAML and .env support
  - `alert_processor.py`: Alert processing and lifecycle management with plugin support
  - `llm.py`: LLM integration (GigaChat) for intelligent alert analysis
  - `notify.py` & `notify_enhanced.py`: Multi-channel notification system (Mattermost, Slack, Email)
  - `queue.py`: RabbitMQ queue management
  - `redis_throttle.py`: Redis-based throttling and caching
  - `formatter.py`: Message formatting with FF-style emoji icons and color support
  - `message_tracker.py`: Message tracking and deduplication
- **seed.yaml**: Main configuration file
- **seed.env**: Environment variables (credentials)
- **docker-compose.yml**: Infrastructure services (Redis, RabbitMQ)

### v5 Enhancements
- **🌌 SEED Branding**: Final Fantasy themed bot identity with crystal ball icon
- **Colored Notifications**: Severity-based color coding for Mattermost (red=critical, orange=high, yellow=warning, blue=info)
- **Compact Formatting**: Auto-truncated LLM recommendations (500 chars) with full text logged
- **FF Emoji Icons**: 💎🔥 Critical, ⚔️ High, 🛡️ Warning, ✨ Info, ❔ Unknown

## Development Commands

### Starting/Stopping the System
```bash
cd v5/
./start.sh    # Start full stack (Redis, RabbitMQ, SEED Agent with FF branding)
./stop.sh     # Stop all services
```

### Testing
```bash
# Comprehensive smoke test with LLM and Mattermost verification
./smoke-test.sh

# Test new compact message format
python3 test_new_format.py

# Enhanced format demo
python3 enhanced_format_demo.py

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
# Install Python dependencies (from v5/ directory)
cd v5/
pip3 install -r requirements.txt

# Check Python dependencies availability
python3 -c "import fastapi, uvicorn, aio_pika, redis, pymongo, yaml, requests, dotenv"
```

### Docker Management
```bash
# Fix Docker daemon issues (if needed)
sudo ./fix-docker-tmp.sh      # Fix Docker temp space issues

# Setup Docker configuration
./setup-docker-config.sh      # Configure Docker daemon settings

# Check Docker services status
docker ps --filter "name=seed-*"

# Manual Docker operations
docker-compose up -d redis rabbitmq    # Start infrastructure only
docker-compose down                     # Stop all Docker services
docker-compose logs -f                  # Follow all container logs
```

### Configuration
```bash
# IMPORTANT: Always work from the v5/ directory
cd v5/

# Setup environment file (required)
cp seed.env.example seed.env
# Edit seed.env with actual GigaChat credentials (GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET)

# Reload configuration (hot reload) - recreates LLM and notification clients
curl -X POST http://localhost:8080/config/reload

# View current configuration (without secrets)
curl http://localhost:8080/config

# LLM diagnostics and self-test
curl http://localhost:8080/llm/selftest
```

## Key API Endpoints

- `POST /alert` - Receive alerts from Alertmanager
- `POST /zabbix` - Receive alerts from Zabbix (both v4 and v5)
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

## Zabbix Integration

Multiple webhook scripts are available for Zabbix integration:
- `zabbix-webhook.py` - Basic webhook for standard Zabbix setups
- `zabbix-webhook-5.4.py` - Enhanced webhook for Zabbix 5.4.9 with URL parameter support
- `zabbix-webhook-enriched.py` - **NEW**: Optimized webhook that proxies enriched JSON directly to /zabbix
- `zabbix-script-adapted.py` - Adapted webhook script with enhanced error handling
- `zabbix-to-seed.py` - General purpose Zabbix to SEED converter

### Zabbix 5.4.9 Webhook Usage
```bash
# Via environment variable
SEED_URL="http://host:8080/zabbix" python3 zabbix-webhook-5.4.py '<json_data>'

# Via URL argument
python3 zabbix-webhook-5.4.py "http://host:8080/zabbix" '<json_data>'

# Test with manual alert
SEED_URL="http://p-dba-seed-adv-msk01:8080/zabbix" \
python3 zabbix-webhook-5.4.py \
'{"event":{"value":"1"},"trigger":{"name":"Test","severity_text":"High"},"host":{"name":"db01"}}'

# Using adapted script with enhanced features
python3 zabbix-script-adapted.py '<json_data>'

# Using enriched webhook (RECOMMENDED for best LLM context)
SEED_URL="http://host:8080/zabbix" python3 zabbix-webhook-enriched.py '<enriched_json>'
python3 zabbix-webhook-enriched.py "http://host:8080/zabbix" '<enriched_json>'
```

All webhooks convert Zabbix alerts to SEED Agent format and send to `/zabbix` endpoint.

### Enriched Zabbix Template
For optimal LLM analysis, use the enriched JSON template in `ZABBIX_JSON_TEMPLATE.md`. This provides:
- Host IP addresses and groups for infrastructure context
- Trigger tags and descriptions for precise diagnostics  
- Item keys and last values for specific command recommendations
- Event timing data for recovery tracking

## Core Architecture Patterns

### Alert Processing Flow
1. **Input**: Alerts received via `/alert` (Alertmanager) or `/zabbix` (Zabbix)
2. **Processing**: `alert_processor.py` handles lifecycle, throttling, and enrichment
3. **LLM Analysis**: `llm.py` performs intelligent analysis using GigaChat
4. **Formatting**: `formatter.py` creates platform-specific messages (v5 has FF-style emojis)
5. **Delivery**: `notify.py` sends to configured channels (Mattermost, Slack, Email)
6. **Queuing**: `queue.py` manages RabbitMQ for reliable delivery
7. **Throttling**: `redis_throttle.py` prevents duplicate alerts

### Module Dependencies
- **seed-agent.py**: Main FastAPI application, orchestrates all components
- **core/config.py**: YAML configuration loader with environment variable support
- **core/llm.py**: GigaChat client with token management and environment validation
- **core/alert_processor.py**: Plugin-based alert processing (though v5 uses universal LLM handler)
- **core/formatter.py**: Message formatting with platform-specific templates
- **core/notify.py & notify_enhanced.py**: Multi-channel notification delivery
- **core/queue.py**: Async RabbitMQ queue management
- **core/redis_throttle.py**: Redis-based alert deduplication and caching
- **core/message_tracker.py**: Message tracking and deduplication

### Configuration System
- Main config: `seed.yaml` (application settings)
- Secrets: `seed.env` (credentials and sensitive data) 
- Hot reload: `POST /config/reload` recreates all clients without restart
- Environment loading: `start.sh` automatically sources `seed.env`

### Key Features
- **Rule Engine**: Deterministic rule-based responses for common alert patterns (MongoDB, Zabbix agent, TCP, disk space, CPU, memory)
- **LLM Integration**: GigaChat-powered intelligent analysis with strict formatting requirements and low temperature (0.0) for consistent responses
- **Enhanced Zabbix Integration**: Enriched JSON template with host IP, groups, trigger tags, item keys for precise LLM context
- **Post-Processing**: Automatic sanitization to remove code fences, "bash" keywords, and empty sections
- **Micro-Cosmetic Formatting**: Simplified emoji usage (🟥🟧🟨🟦 severity boxes, 💎 problems, 🛠 recommendations)
- **Message Tracking**: Comprehensive message tracking and deduplication via `message_tracker.py`
- **FF-Style Branding**: Final Fantasy themed bot identity with crystal ball icon

## Important Notes

- All configuration in `seed.yaml` with secrets in `seed.env`
- **CRITICAL**: LLM requires ALL GigaChat credentials in `seed.env` (GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET, GIGACHAT_SCOPE, etc.)
- Without complete GigaChat config, LLM will be disabled (`llm: false` in health check)
- System ready for production deployment 
- Hot configuration reload supported via API - recreates LLM and notification clients
- Comprehensive logging with emoji markers for easy filtering: 📁 📤 ✅ ❌ 🎉
- Docker volumes mounted to `/data/{redis,rabbitmq}` for persistent storage
- Alert deduplication and throttling handled automatically via Redis
- Multiple input sources supported: Alertmanager, Zabbix, direct API calls
- Enhanced format testing available via `test_new_format.py` and `enhanced_format_demo.py`
- Smoke testing with `./smoke-test.sh` verifies LLM functionality and Mattermost connectivity

## Troubleshooting

### Common Issues
```bash
# LLM disabled (llm: false in health check)
curl http://localhost:8080/llm/selftest | jq .
# Check that all GIGACHAT_* environment variables are present: true

# Mattermost notifications not working
tail -f seed-agent.log | grep -E "(📤|✅|❌).*[Mm]attermost"
curl http://localhost:8080/config | jq .notifications.mattermost

# Services not starting
docker logs seed-redis
docker logs seed-rabbitmq

# Agent crashes on startup
tail -20 seed-agent.log

# Check system health
curl http://localhost:8080/health | jq .
curl http://localhost:8080/dashboard | jq .
```

### Log Analysis
- **📁** Configuration and file operations
- **📤** Outgoing notifications
- **✅** Successful operations
- **❌** Errors and failures
- **🎉** System events