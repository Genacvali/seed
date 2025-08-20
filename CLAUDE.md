# CLAUDE.md - SEED Agent v4

This file provides guidance to Claude Code when working with this repository.

## Project Overview

SEED Agent v4 is a production-ready monitoring and alerting system with a unified architecture. The agent listens on port 8080, processes alerts through specialized plugins, and sends notifications via multiple channels.

## Current Status

- **Active Version**: v4 (only version in repository)
- **Agent Status**: Running on port 8080
- **Infrastructure**: Docker Compose (Redis + RabbitMQ)
- **Configuration**: `v4/seed.yaml` (single unified config)

## Project Structure

```
v4/
├── seed-agent.py          # Main agent (HTTP server)
├── plugins.py             # Plugin implementations
├── core/                  # Core system modules
├── fetchers/              # Data fetching (MongoDB, Telegraf)
├── seed.yaml              # Main configuration
├── docker-compose.yml     # Infrastructure
├── start.sh              # Complete startup script
├── stop.sh               # Shutdown script
└── build-agent.sh        # Binary build script
```

## Key Components

### Plugins
- **host_inventory**: System monitoring via Telegraf metrics
- **mongo_hot**: MongoDB performance monitoring

### Notifications
- **Mattermost**: Enabled with webhook
- **Slack/Email**: Configured but disabled
- **GigaChat LLM**: Enabled for alert enhancement

### Infrastructure
- **RabbitMQ**: Message queuing (localhost:5672)
- **Redis**: Throttling and caching (localhost:6379)
- **HTTP API**: Alert ingestion (localhost:8080)

## Configuration

All settings are in `v4/seed.yaml`:
- Host groups with override support
- Alert routing to plugins
- Notification channels
- LLM integration (GigaChat)
- Infrastructure settings

## Development Guidelines

1. **Edit existing files** rather than creating new ones
2. **Use the unified configuration** in `seed.yaml`
3. **Follow the plugin architecture** for new monitoring capabilities  
4. **Test with curl** commands to `/alert` endpoint
5. **Use Docker Compose** for infrastructure services

## Testing

```bash
# Test alert processing
curl -X POST http://localhost:8080/alert \
    -H 'Content-Type: application/json' \
    -d '{"alertname": "TestAlert", "instance": "localhost"}'

# Check health
curl http://localhost:8080/health

# View configuration  
curl http://localhost:8080/config
```

## Service Management

```bash
# Start everything
./start.sh

# Stop everything
./stop.sh

# Build standalone binary
./build-agent.sh
```

The system is production-ready and actively processes alerts with notifications to Mattermost.