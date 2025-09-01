# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEED Agent v6 - lightweight plugin-based alert processing system with Prometheus and Alertmanager integration

## High-Level Architecture

SEED Agent v6 uses a lightweight plugin-based architecture:
- **Philosophy**: Minimal HTTP agent with modular plugin system
- **Processing Model**: Route alerts to specialized plugins based on alert type/labels
- **Dependencies**: Minimal Python-only stack (6 packages)  
- **Features**: Extensible plugin architecture, Prometheus/Alertmanager integration
- **Size**: ~24KB main file with optional components

## Development Commands

### Basic Operations
```bash
# Working directory  
cd v6/

# Start/stop SEED Agent
./start.sh    # Interactive setup or use existing config
./stop.sh     # Simple process termination

# Configuration setup
cp configs/seed.env.example configs/seed.env
# Edit configs/seed.env with MM_WEBHOOK (required), ALERTMANAGER_TOKEN, etc.

# Dependencies (minimal)
pip3 install -r requirements.txt
python3 -c "import fastapi, requests, dotenv"
```

### Prometheus & Alertmanager Integration
```bash
# Start Alertmanager polling integration
python3 start_alertmanager_integration.py

# Test connections
python3 start_alertmanager_integration.py test

# Single polling cycle
python3 start_alertmanager_integration.py once
```

### Manual Testing
```bash
# Health check
curl http://localhost:8080/health

# Test notification
curl -X POST http://localhost:8080/test

# Send test alert
curl -X POST http://localhost:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{"alerts":[{"labels":{"alertname":"Test","instance":"localhost","severity":"warning"},"annotations":{"summary":"Test alert"},"status":"firing"}]}'
```

## Key API Endpoints

- `GET /health` - System health and component status
- `POST /test` - Quick notification delivery test  
- `POST /alertmanager` - Alert webhook for Alertmanager integration
- `GET /` - Basic info page

## Core Architecture Patterns

### Alert Processing Flow
1. **Input**: `/alertmanager` webhook or RabbitMQ consumer
2. **Routing**: `plugin_router.py` maps alerts to specialized plugins via YAML rules  
3. **Processing**: Plugin-specific handlers in `plugins/` directory
4. **Enrichment**: Optional Prometheus data fetching via `integration/prometheus_client.py`
5. **Formatting**: Plugin-specific formatters in `formatters/` directory
6. **Delivery**: Lightweight Mattermost client (`core/mm.py`)

### Prometheus & Alertmanager Integration
- **Alertmanager Client**: `integration/alertmanager_client.py` - Full API client with polling support
- **Prometheus Client**: `integration/prometheus_client.py` - Query engine for metrics context
- **Standalone Integration**: `start_alertmanager_integration.py` - Independent polling service

### Configuration System
- **Main Config**: `configs/seed.env` - Environment variables for all settings
- **Alert Routing**: `configs/alerts.yaml` - Plugin routing rules
- **Prometheus Config**: `configs/prometheus.yaml` - Prometheus/Alertmanager integration settings
- **Management**: Interactive setup via `start.sh`

### Module Dependencies

#### Core Modules (`/core/`)
- `config.py` (2KB) - Minimal environment configuration
- `llm.py` (4KB) - Optional GigaChat client  
- `dispatcher.py` (1KB) - Plugin dispatch logic
- `mm.py` (1KB) - Lightweight Mattermost client
- `log.py` (1KB) - Logging utilities
- `amqp.py` (1KB) - Optional RabbitMQ consumer

#### Integration Modules (`/integration/`)
- `alertmanager_client.py` - Full Alertmanager API client with polling
- `prometheus_client.py` - Prometheus query engine and helpers

#### Plugin System
- `plugin_router.py` (6KB) - Alert-to-plugin routing engine  
- `plugins/` - Specialized processors:
  - `echo.py` - Basic fallback plugin
  - `os_basic.py` (6KB) - OS metrics analysis (CPU/Memory/Disk)
  - `pg_slow.py` (9KB) - PostgreSQL slow query diagnostics
  - `mongo_hot.py` (3KB) - MongoDB performance analysis
  - `host_inventory.py` (3KB) - Host service inventory
- `fetchers/telegraf.py` (2KB) - Metrics enrichment from Telegraf
- `formatters/` - Plugin-specific message formatting

## Configuration Requirements

### Required Settings
- **Mattermost Webhook**: `MM_WEBHOOK` required in `configs/seed.env`
- **Alertmanager Integration**: `ALERTMANAGER_URL` and `ALERTMANAGER_TOKEN`
- **GigaChat Credentials**: Optional, only if `USE_LLM=1`
- **Working Directory**: Always operate from `v6/` directory

### Optional Settings
- **Prometheus Integration**: `PROMETHEUS_URL` for metrics enrichment
- **RabbitMQ**: Alternative to HTTP webhook for alert input
- **SSL Verification**: Configurable for all HTTP clients

## Performance Characteristics
- **Memory**: ~30MB agent only
- **Throughput**: Scales with plugin complexity and Prometheus queries
- **Features**: Minimal overhead, plugin-specific optimizations

## Troubleshooting

### Common Issues
```bash
# Health check
curl http://localhost:8080/health | jq .

# Check logs
tail -f logs/agent.log | grep -E "MM_|ERROR|WARN"

# Test Alertmanager integration
python3 start_alertmanager_integration.py test

# Test single alert processing
curl -X POST http://localhost:8080/test
```

### Log Analysis Markers
- **📁** Configuration and file operations
- **📤** Outgoing notifications  
- **✅** Successful operations
- **❌** Errors and failures
- **🎉** System events

### Integration Issues
- **Alertmanager 401/403**: Check `ALERTMANAGER_TOKEN` in config
- **Prometheus timeouts**: Verify `PROMETHEUS_URL` and network connectivity
- **Plugin failures**: Check plugin-specific logs and dependencies
- **Mattermost delivery fails**: Verify `MM_WEBHOOK` URL and SSL settings