# SEED Agent v4 - Production Ready

**🚀 Complete monitoring solution with one-command startup**

## Quick Start

```bash
# Start everything (Redis, RabbitMQ, SEED Agent)
./start.sh

# Test with sample alerts
python3 test_alerts.py

# Stop everything
./stop.sh
```

**That's it!** No environment variables, no complex setup.

## What's Included

### 📦 Complete Stack
- **SEED Agent v4**: Unified monitoring and alerting system
- **Redis**: Fast alert throttling and caching
- **RabbitMQ**: Reliable message queuing with management UI
- **Docker Compose**: Automated infrastructure setup

### 🔧 Ready-to-Use Configuration
- **No environment variables needed** - all configured in `seed.yaml`
- **Pre-configured host groups** for different environments
- **Built-in alert routing** for common monitoring scenarios
- **Plugin system** for host inventory and MongoDB monitoring

### 🧪 Test Suite
- **Sample alerts** for all supported plugins
- **Throttling tests** to verify alert suppression
- **Health checks** and monitoring endpoints

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │  Alertmanager   │    │   Your Apps     │
│   Grafana, etc  │───▶│   Webhook       │───▶│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   SEED Agent    │    │   Test Alerts   │
                       │    Port 8080    │◀───│  test_alerts.py │
                       └─────────────────┘    └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │  RabbitMQ   │ │    Redis    │ │   Plugins   │
            │ Port 5672   │ │  Port 6379  │ │             │
            │ UI: 15672   │ │             │ │ host_inv    │
            └─────────────┘ └─────────────┘ │ mongo_hot   │
                                            └─────────────┘
```

## Configuration

### Infrastructure (Automatic)
```yaml
infrastructure:
  rabbitmq:
    host: "127.0.0.1"
    username: "guest"
    password: "guest"
  
  redis:
    host: "127.0.0.1"
    port: 6379
```

### Notifications (Configure as needed)
```yaml
notifications:
  mattermost:
    enabled: true  # Change to true
    webhook_url: "https://your-mattermost.com/hooks/YOUR_WEBHOOK"
    
  slack:
    enabled: true  # Change to true  
    webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
```

### Host Groups (Customize for your environment)
```yaml
hosts:
  groups:
    web-servers:
      hosts: ["web-01", "web-02", "web-03"]
      overrides:
        telegraf_url: "http://{host}:9216/metrics"
```

## Alert Types

### Host Inventory
- **DiskSpaceHigh** - Monitor disk usage
- **HighCpuLoad** - Monitor CPU utilization
- **HighMemoryUsage** - Monitor memory usage
- **TestHostInventory** - General host information

### MongoDB Monitoring
- **MongoSlowQuery** - Detect slow database queries
- **MongoCollscan** - Find inefficient collection scans

## Web Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| SEED Agent | http://localhost:8080 | - |
| Health Check | http://localhost:8080/health | - |
| Metrics | http://localhost:8080/metrics | - |
| RabbitMQ UI | http://localhost:15672 | guest/guest |

## Usage Examples

### Send Test Alert
```bash
curl -X POST http://localhost:8080/alert \
  -H 'Content-Type: application/json' \
  -d '{
    "alertname": "DiskSpaceHigh",
    "instance": "web-01:9216",
    "labels": {
      "severity": "high",
      "hostname": "web-01"
    }
  }'
```

### Integration with Alertmanager
```yaml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'seed-agent'

receivers:
- name: 'seed-agent'
  webhook_configs:
  - url: 'http://localhost:8080/alert'
```

### Integration with Grafana
```yaml
notification_channels:
  - name: seed-agent
    type: webhook
    settings:
      url: http://localhost:8080/alert
      http_method: POST
```

## File Structure

```
v4/
├── seed-agent.py          # Main application
├── seed.yaml             # Configuration (edit this)
├── docker-compose.yml    # Infrastructure services
├── requirements.txt      # Python dependencies
├── build-agent.sh       # Build binary
├── start.sh             # Start everything
├── stop.sh              # Stop everything
├── test_alerts.py       # Test alert suite
└── core/                # Core modules
    ├── config.py        # Configuration management
    ├── queue.py         # RabbitMQ integration
    ├── redis_throttle.py # Alert throttling
    └── notify.py        # Notifications
├── fetchers/            # Data fetchers
    ├── telegraf.py      # Telegraf metrics
    └── mongo.py         # MongoDB queries
└── plugins.py           # Plugin system
```

## Customization

### Add New Alert Type
1. Add routing in `seed.yaml`:
   ```yaml
   routing:
     alerts:
       MyCustomAlert:
         plugin: "host_inventory"
         payload:
           alert_type: "custom"
           timeout: 30
   ```

2. Send alert:
   ```python
   alert = {
       "alertname": "MyCustomAlert",
       "instance": "my-host:9216",
       "labels": {"severity": "warning"}
   }
   ```

### Add Notification Channel
1. Configure in `seed.yaml`:
   ```yaml
   notifications:
     mattermost:
       enabled: true
       webhook_url: "YOUR_WEBHOOK_URL"
   ```

### Add New Host Group
1. Configure in `seed.yaml`:
   ```yaml
   hosts:
     groups:
       my-servers:
         hosts: ["server1", "server2"]
         overrides:
           telegraf_url: "http://{host}:9216/metrics"
   ```

## Monitoring Best Practices

### 1. Host Monitoring
- Install [Telegraf](https://github.com/influxdata/telegraf) on monitored hosts
- Configure Telegraf to expose metrics on port 9216
- Update host groups in `seed.yaml`

### 2. MongoDB Monitoring  
- Enable [MongoDB profiler](https://docs.mongodb.com/manual/tutorial/manage-the-database-profiler/)
- Configure connection strings in host groups
- Set appropriate `min_ms` thresholds for your workload

### 3. Alert Tuning
- Adjust `ttl_seconds` to prevent alert spam
- Set `priority` levels for different alert types
- Configure `timeout` values based on expected response times

## Troubleshooting

### SEED Agent Won't Start
```bash
# Check logs
tail -f seed-agent.log

# Verify configuration
python3 -c "import yaml; yaml.safe_load(open('seed.yaml'))"

# Check port availability  
lsof -i :8080
```

### Services Not Connecting
```bash
# Check Docker services
docker ps
docker logs seed-rabbitmq
docker logs seed-redis

# Test connectivity
curl http://localhost:8080/health
```

### Alerts Not Processing
```bash
# Check RabbitMQ queues
curl -u guest:guest http://localhost:15672/api/queues

# Verify alert routing
curl http://localhost:8080/config

# Send test alert
python3 test_alerts.py
```

## Performance

### Resource Usage
- **SEED Agent**: ~100-200MB RAM, low CPU
- **Redis**: ~30-50MB RAM
- **RabbitMQ**: ~150-250MB RAM

### Scaling
- Handles **1000+ alerts/minute** on modest hardware
- **Throttling** prevents duplicate alert processing
- **Async processing** for high throughput

### Optimization
- Adjust `workers` in `seed.yaml` for high load
- Use Redis clustering for large deployments
- Configure RabbitMQ clustering for high availability

## Support

For issues and questions:

1. **Check logs**: `tail -f seed-agent.log`
2. **Verify health**: `curl http://localhost:8080/health`
3. **Test connectivity**: `python3 test_alerts.py`
4. **Review configuration**: `seed.yaml`

## License

Open source monitoring solution. Use freely for commercial and personal projects.