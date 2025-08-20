# SEED Agent v4

**Unified Configuration Monitoring System**

## What's New in v4

### 🔧 Fixed Configuration Issues

- **Eliminated hardcoded connection strings** - All database and service connections now come from configuration
- **Unified configuration system** - Single source of truth with environment variable interpolation
- **Proper validation** - Configuration is validated at startup with clear error messages
- **Centralized service discovery** - Consistent URL and connection string construction
- **Environment-aware** - Easy switching between dev/staging/production

### 🚀 Key Improvements

1. **Configuration Loading Fixed**: 
   - v3 issue: `os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")` 
   - v4 solution: Configuration loaded from `seed.yaml` with env overrides

2. **Environment Variable Interpolation**:
   ```yaml
   rabbitmq:
     host: "${SEED_RABBITMQ_HOST:localhost}"
     username: "${SEED_RABBITMQ_USERNAME:guest}"
   ```

3. **Service Connection Management**:
   - RabbitMQ: Built from host, port, username, password, vhost
   - Redis: Built from host, port, db, optional password
   - MongoDB: Dynamic connection strings per host group

4. **Plugin Configuration**:
   - Host-specific overrides from configuration
   - Group-based settings (mongo-prod, mongo-stage, etc.)
   - Consistent Telegraf URL generation

5. **Notification System**:
   - Multi-channel support (Mattermost, Slack, Email)
   - Configuration-driven channel selection
   - Rich alert formatting with emojis

## Quick Start

### 1. Configuration

Copy and customize `seed.yaml`:

```yaml
environment: "production"

infrastructure:
  rabbitmq:
    host: "${SEED_RABBITMQ_HOST:localhost}"
    username: "${SEED_RABBITMQ_USERNAME:guest}"
    password: "${SEED_RABBITMQ_PASSWORD:guest}"
  
  redis:
    host: "${SEED_REDIS_HOST:localhost}"

notifications:
  mattermost:
    enabled: true
    webhook_url: "${SEED_MATTERMOST_WEBHOOK_URL:}"
```

### 2. Environment Variables

Set environment-specific values:

```bash
export SEED_ENVIRONMENT=production
export SEED_RABBITMQ_HOST=rabbitmq.example.com
export SEED_RABBITMQ_USERNAME=seed_user
export SEED_RABBITMQ_PASSWORD=secure_password
export SEED_MATTERMOST_WEBHOOK_URL=https://mattermost.example.com/hooks/...
```

### 3. Build and Run

```bash
# Build binary
./build-agent.sh

# Run with configuration
./dist/seed-agent --config seed.yaml

# Or run in development mode
python3 seed-agent.py --debug
```

## Configuration Examples

### Development Environment

```yaml
environment: "development"
system:
  agent:
    debug: true

infrastructure:
  rabbitmq:
    host: "localhost"
    username: "guest"
    password: "guest"
    
notifications:
  mattermost:
    enabled: false  # Disable notifications in dev
```

### Production Environment

```yaml
environment: "production"

infrastructure:
  rabbitmq:
    host: "${SEED_RABBITMQ_HOST}"
    username: "${SEED_RABBITMQ_USERNAME}"
    password: "${SEED_RABBITMQ_PASSWORD}"
  
  redis:
    host: "${SEED_REDIS_HOST}"
    password: "${SEED_REDIS_PASSWORD}"

notifications:
  mattermost:
    enabled: true
    webhook_url: "${SEED_MATTERMOST_WEBHOOK_URL}"
    verify_ssl: true
```

## Host Groups Configuration

Define monitoring targets:

```yaml
hosts:
  groups:
    mongo-prod:
      hosts: ["mongo-01", "mongo-02", "mongo-03"]
      overrides:
        mongo_host: "${SEED_MONGO_PROD_HOST:mongo-01}"
        username: "${SEED_MONGO_PROD_USERNAME:monitoring}"
        password: "${SEED_MONGO_PROD_PASSWORD}"
        
    web-servers:
      hosts: ["web-01", "web-02"]
      overrides:
        telegraf_url: "https://{host}:9216/metrics"
```

## API Endpoints

- `POST /alert` - Receive alerts from monitoring systems
- `GET /health` - Health check with service status
- `GET /metrics` - Prometheus metrics
- `GET /config` - Current configuration (sanitized)
- `POST /config/reload` - Reload configuration

## Migration from v3

1. **Update environment variables**: Remove hardcoded URLs, use YAML config
2. **Configuration structure**: Single `seed.yaml` instead of multiple files  
3. **Service initialization**: Pass config objects to all services
4. **Error handling**: Startup validation will catch missing configuration

### Before (v3):
```python
rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
```

### After (v4):
```python
config = Config("seed.yaml") 
rabbitmq_config = config.rabbitmq_config
rabbitmq_url = f"amqp://{username}:{password}@{host}:{port}{vhost}"
```

## Docker Deployment

Use the provided `docker-compose.yml` for services:

```bash
# Start Redis and RabbitMQ
docker compose up -d

# Set connection details
export SEED_RABBITMQ_HOST=localhost
export SEED_REDIS_HOST=localhost

# Run SEED Agent
./dist/seed-agent
```

## Monitoring

### Health Check
```bash
curl http://localhost:8080/health
```

### Metrics
```bash
curl http://localhost:8080/metrics
```

### Configuration
```bash
curl http://localhost:8080/config
```

## Troubleshooting

### Configuration Issues

1. **Check configuration loading**:
   ```bash
   ./dist/seed-agent --config seed.yaml --debug
   ```

2. **Validate environment variables**:
   ```bash
   env | grep SEED_
   ```

3. **Test connections**:
   ```bash
   curl http://localhost:8080/health
   ```

### Common Errors

- **"Configuration not found"**: Ensure `seed.yaml` exists in working directory
- **"RabbitMQ connection failed"**: Check host, credentials, and network access
- **"No notification channels"**: Enable at least one notification method in config

## Architecture

v4 follows a clean layered architecture:

```
seed-agent.py          # Main application + FastAPI server
├── core/
│   ├── config.py      # Unified configuration management
│   ├── queue.py       # RabbitMQ integration  
│   ├── redis_throttle.py  # Redis-based throttling
│   └── notify.py      # Multi-channel notifications
├── fetchers/          # Data fetching (Telegraf, MongoDB)
├── plugins.py         # Plugin system (host_inventory, mongo_hot)
└── seed.yaml          # Configuration file
```

All components use the centralized `Config` class, eliminating configuration inconsistencies and hardcoded values that plagued earlier versions.

## Support

For configuration issues, check:
1. Configuration file syntax with `python -c "import yaml; yaml.safe_load(open('seed.yaml'))"`  
2. Environment variable interpolation
3. Service connectivity with health check endpoint
4. Log output for detailed error messages