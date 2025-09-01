# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEED Agent - dual-architecture alert processing system with two distinct versions:
- **v5**: Production-ready LLM-powered universal alert processor with Final Fantasy branding
- **v6**: Lightweight plugin-based modular architecture for specialized alert handling

## High-Level Architecture

### v5: Universal LLM Processing
- **Philosophy**: Monolithic FastAPI application with centralized LLM analysis
- **Processing Model**: Single GigaChat-powered handler processes all alert types
- **Dependencies**: Full infrastructure stack (Redis, RabbitMQ, MongoDB)
- **Features**: FF-themed branding, colored notifications, comprehensive monitoring
- **Size**: ~54KB main file with 13 core modules

### v6: Plugin-Based Specialization  
- **Philosophy**: Minimal HTTP agent with modular plugin system
- **Processing Model**: Route alerts to specialized plugins based on alert type/labels
- **Dependencies**: Minimal Python-only stack (6 packages)
- **Features**: Extensible plugin architecture, lightweight deployment
- **Size**: ~24KB main file with optional components

## Development Commands

### v5 (Production System)
```bash
# Working directory
cd v5/

# Start/stop full stack with infrastructure
./start.sh    # Redis + RabbitMQ + SEED Agent
./stop.sh     # Graceful shutdown

# Configuration setup (required for LLM)
cp seed.env.example seed.env
# Edit seed.env with GigaChat credentials: GIGACHAT_CLIENT_ID, GIGACHAT_CLIENT_SECRET

# Hot configuration reload (recreates clients without restart)
curl -X POST http://localhost:8080/config/reload

# Dependencies
pip3 install -r requirements.txt
python3 -c "import fastapi, uvicorn, aio_pika, redis, pymongo, yaml, requests, dotenv"
```

### v6 (Lightweight System)
```bash
# Working directory  
cd v6/

# Start/stop lightweight agent
./start.sh    # Interactive setup or use existing config
./stop.sh     # Simple process termination

# Configuration setup
cp configs/seed.env.example configs/seed.env
# Edit configs/seed.env with MM_WEBHOOK (required), optional LLM credentials

# Dependencies (minimal)
pip3 install -r requirements.txt
python3 -c "import fastapi, requests, dotenv"
```

### Testing Framework

#### v5 Testing
```bash
cd v5/
./smoke-test.sh                 # Comprehensive LLM + Mattermost verification
python3 test_new_format.py      # Compact message format testing
python3 enhanced_format_demo.py # FF-style formatting demonstration
```

#### v6 Testing  
```bash
cd v6/
python3 test_llm.py             # Full-featured LLM integration test
python3 test_plugin_system.py   # Plugin system end-to-end testing
python3 test_prometheus.py      # Prometheus metrics integration
python3 test_realistic.py       # Complex alert scenarios
python3 test_format_fix.py      # Message formatting validation
python3 debug_llm.py           # LLM debugging utilities
```

### Health Checks and Diagnostics
```bash
# Both versions support these endpoints
curl http://localhost:8080/health
curl -X POST http://localhost:8080/test

# v5 additional diagnostics
curl http://localhost:8080/llm/selftest
curl http://localhost:8080/dashboard
curl http://localhost:8080/config | jq .

# Alert testing (both versions)
curl -X POST http://localhost:8080/alert \
  -H 'Content-Type: application/json' \
  -d '{"alerts":[{"labels":{"alertname":"Test","instance":"localhost","severity":"warning"},"annotations":{"summary":"Test alert"},"status":"firing"}]}'
```

## Core Architecture Patterns

### Alert Processing Flow

#### v5 Flow (Universal LLM)
1. **Input**: `/alert` (Alertmanager) or `/zabbix` (Zabbix webhooks)
2. **Processing**: `core/alert_processor.py` handles lifecycle and enrichment
3. **LLM Analysis**: `core/llm.py` performs GigaChat-powered intelligent analysis
4. **Formatting**: `core/formatter.py` creates FF-styled messages with color coding
5. **Delivery**: `core/notify.py` sends to Mattermost/Slack/Email
6. **Infrastructure**: Redis throttling, RabbitMQ queuing, message tracking

#### v6 Flow (Plugin Routing)
1. **Input**: `/alertmanager` or optional RabbitMQ consumer
2. **Routing**: `plugin_router.py` maps alerts to specialized plugins via YAML rules
3. **Processing**: Plugin-specific handlers in `plugins/` directory
4. **Enrichment**: Optional Prometheus data fetching via `fetchers/telegraf.py`
5. **Formatting**: Plugin-specific formatters in `formatters/` directory
6. **Delivery**: Lightweight Mattermost client

### Configuration Systems

#### v5 Configuration
- **Main Config**: `seed.yaml` - Hierarchical YAML with hot reload support
- **Secrets**: `seed.env` - Environment variables for credentials
- **Validation**: Runtime validation with comprehensive startup checks
- **Management**: `/config/reload` API endpoint for zero-downtime updates

#### v6 Configuration
- **Main Config**: `configs/seed.env` - Flat key-value environment variables
- **Alert Routing**: `configs/alerts.yaml` - Plugin routing rules
- **Secrets**: `configs/secrets.env` - Credential storage with 600 permissions
- **Management**: Interactive setup via `start.sh`

### Module Dependencies

#### v5 Core Modules (`/core/`)
- `config.py` (11KB) - YAML configuration with environment support
- `llm.py` (9KB) - GigaChat client with token management
- `formatter.py` (19KB) - FF-themed message formatting with color coding  
- `alert_processor.py` (6KB) - Alert lifecycle and enrichment
- `notify.py` + `notify_enhanced.py` - Multi-channel notification delivery
- `queue.py` (4KB) - Async RabbitMQ management
- `redis_throttle.py` (4KB) - Redis-based throttling and caching
- `message_tracker.py` (5KB) - Message deduplication

#### v6 Core Modules (`/core/`)
- `config.py` (2KB) - Minimal environment configuration
- `llm.py` (4KB) - Optional GigaChat client  
- `dispatcher.py` (1KB) - Plugin dispatch logic
- `mm.py` (1KB) - Lightweight Mattermost client
- `log.py` (1KB) - Logging utilities
- `amqp.py` (1KB) - Optional RabbitMQ consumer

#### v6 Plugin System
- `plugin_router.py` (6KB) - Alert-to-plugin routing engine
- `plugins/` - Specialized processors:
  - `os_basic.py` (6KB) - OS metrics analysis (CPU/Memory/Disk)
  - `pg_slow.py` (9KB) - PostgreSQL slow query diagnostics
  - `mongo_hot.py` (3KB) - MongoDB performance analysis
  - `host_inventory.py` (3KB) - Host service inventory
- `fetchers/telegraf.py` (2KB) - Metrics enrichment from Telegraf
- `formatters/` - Plugin-specific message formatting

## Key API Endpoints

### Both Versions
- `GET /health` - System health and component status
- `POST /test` - Quick notification delivery test
- `POST /alert` (v5) / `POST /alertmanager` (v6) - Alert webhook

### v5 Specific  
- `GET /dashboard` - Live metrics and system status
- `GET /config` - Configuration view (secrets redacted)
- `POST /config/reload` - Hot configuration reload
- `GET /llm/selftest` - LLM service diagnostics
- `GET /metrics` - Prometheus-style metrics
- `POST /zabbix` - Zabbix webhook integration

## Zabbix Integration

Multiple webhook scripts support various Zabbix versions:
- `zabbix-webhook.py` - Basic webhook for standard setups
- `zabbix-webhook-5.4.py` - Enhanced webhook for Zabbix 5.4.9 with URL parameters
- `zabbix-webhook-enriched.py` - **RECOMMENDED**: Optimized with enriched JSON context
- `zabbix-script-adapted.py` - Enhanced error handling
- `zabbix-to-seed.py` - General purpose converter

### Usage Examples
```bash
# Environment variable method
SEED_URL="http://host:8080/zabbix" python3 zabbix-webhook-5.4.py '<json_data>'

# URL argument method  
python3 zabbix-webhook-5.4.py "http://host:8080/zabbix" '<json_data>'

# Enriched webhook (best LLM context)
SEED_URL="http://host:8080/zabbix" python3 zabbix-webhook-enriched.py '<enriched_json>'
```

## Critical Requirements

### v5 Requirements
- **GigaChat Credentials**: ALL environment variables required in `seed.env`
  - `GIGACHAT_CLIENT_ID`, `GIGACHAT_CLIENT_SECRET`, `GIGACHAT_SCOPE`
  - Without complete config, LLM will be disabled (`llm: false` in health check)
- **Infrastructure**: Docker required for Redis + RabbitMQ
- **Working Directory**: Always operate from `v5/` directory

### v6 Requirements  
- **Mattermost Webhook**: `MM_WEBHOOK` required in `configs/seed.env`
- **GigaChat Credentials**: Optional, only if `USE_LLM=1`
- **Dependencies**: Python-only, no Docker required
- **Working Directory**: Always operate from `v6/` directory

## Performance Characteristics

### v5 Performance
- **Memory**: ~100MB agent + 450MB infrastructure (Redis/RabbitMQ)
- **Throughput**: >1000 alerts/second
- **Features**: Full monitoring, throttling, message tracking

### v6 Performance
- **Memory**: ~30MB agent only
- **Throughput**: Scales with plugin complexity
- **Features**: Minimal overhead, plugin-specific optimizations

## Troubleshooting

### Common Issues
```bash
# LLM not working (both versions)
curl http://localhost:8080/llm/selftest | jq .
# Check environment variables are set

# Notifications failing
tail -f seed-agent.log | grep -E "(📤|✅|❌)"  # v5
tail -f logs/agent.log | grep -E "MM_"        # v6

# Health checks
curl http://localhost:8080/health | jq .
```

### Log Analysis Markers  
- **📁** Configuration and file operations
- **📤** Outgoing notifications  
- **✅** Successful operations
- **❌** Errors and failures
- **🎉** System events

## Version Selection Guide

**Choose v5 when:**
- Need comprehensive production monitoring
- Want centralized LLM analysis for all alerts
- Require advanced features (throttling, message tracking, multi-channel notifications)
- Have infrastructure resources for Redis/RabbitMQ

**Choose v6 when:**
- Need lightweight deployment with minimal dependencies
- Want specialized handling for different alert types
- Prefer plugin-based extensibility
- Have resource constraints or simple notification requirements