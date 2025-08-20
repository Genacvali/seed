# SEED Agent v4 - Architecture Documentation

## 🏗️ Overview

SEED Agent v4 is a production-ready monitoring and alerting system with a unified architecture designed for scalability, reliability, and ease of deployment.

## 🎯 Core Concept

**Event-Driven Alert Processing System** that receives alerts via HTTP API, processes them through specialized plugins, and delivers notifications via multiple channels with optional LLM enhancement.

## 📋 Tech Stack

### Core Technologies
- **Runtime**: Python 3.8+ (compiled to standalone binary via PyInstaller)
- **Web Framework**: Built-in HTTP server (lightweight, no external dependencies)
- **Message Queue**: RabbitMQ (for reliable alert processing)
- **Caching/Throttling**: Redis (for alert deduplication and throttling)
- **Configuration**: YAML-based configuration management
- **Containerization**: Docker Compose for infrastructure services

### Integration Stack
- **Monitoring Data**: Telegraf (Prometheus metrics)
- **Database Monitoring**: MongoDB (performance and slow query analysis)
- **Notifications**: Mattermost, Slack, Email (SMTP)
- **LLM Enhancement**: GigaChat (Sber AI) for intelligent alert analysis
- **Deployment**: Single binary with Docker Compose infrastructure

## 🏛️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   HTTP Client   │───▶│   SEED Agent     │───▶│  Notifications  │
│  (curl/webhook) │    │   Port: 8080     │    │   (Mattermost)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Alert Queue    │
                    │   (RabbitMQ)     │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Plugin System  │
                    │                  │
                    │  ┌─────────────┐ │    ┌─────────────────┐
                    │  │host_inventory│─├───▶│ Telegraf Metrics│
                    │  │             │ │    │   (HTTP API)    │
                    │  └─────────────┘ │    └─────────────────┘
                    │                  │
                    │  ┌─────────────┐ │    ┌─────────────────┐
                    │  │ mongo_hot   │─├───▶│   MongoDB       │
                    │  │             │ │    │ (Connection)    │
                    │  └─────────────┘ │    └─────────────────┘
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │  Redis Throttle  │───▶│   GigaChat LLM  │
                    │  (Deduplication) │    │   (Optional)    │
                    └──────────────────┘    └─────────────────┘
```

## 🔧 Component Architecture

### 1. **SEED Agent Core** (`seed-agent.py`)
- **HTTP Server**: Receives alerts on port 8080
- **Request Validation**: JSON schema validation for incoming alerts
- **Alert Routing**: Routes alerts to appropriate plugins based on configuration
- **Queue Management**: Publishes alerts to RabbitMQ for processing
- **Health Checks**: System health monitoring and metrics

### 2. **Plugin System** (`plugins.py`)
- **host_inventory**: System monitoring via Telegraf metrics
  - Disk usage, CPU load, memory utilization
  - Connects to Telegraf Prometheus endpoint
- **mongo_hot**: MongoDB performance monitoring  
  - Slow query analysis, performance profiling
  - Direct MongoDB connection with authentication

### 3. **Data Fetchers** (`fetchers/`)
- **Telegraf Fetcher** (`telegraf.py`): HTTP client for Prometheus metrics
- **MongoDB Fetcher** (`mongo.py`): MongoDB client with connection pooling

### 4. **Notification System** (`notify.py`)
- **Multi-channel support**: Mattermost, Slack, Email
- **Template-based formatting**: Customizable message templates
- **SSL/TLS configuration**: Flexible security settings
- **Webhook integration**: HTTP POST notifications

### 5. **LLM Integration** (`llm.py`)
- **GigaChat API**: Sber AI integration for alert enhancement
- **Token management**: OAuth2 token caching and refresh
- **Alert analysis**: Intelligent alert description and recommendations

### 6. **Infrastructure Services**
- **RabbitMQ**: Message queuing with retry and dead letter queues
- **Redis**: Alert throttling, deduplication, and caching
- **Docker Compose**: Automated infrastructure deployment

## 📊 Data Flow

```
1. Alert Received (HTTP POST /alert)
   ↓
2. Alert Validation & Routing 
   ↓
3. Queue Processing (RabbitMQ)
   ↓
4. Plugin Execution
   ├─ host_inventory → Telegraf API
   └─ mongo_hot → MongoDB
   ↓
5. Data Collection & Analysis
   ↓
6. Redis Throttling Check
   ↓  
7. LLM Enhancement (Optional)
   ↓
8. Notification Delivery
   └─ Mattermost/Slack/Email
```

## 🎛️ Configuration Management

### Single Configuration File (`seed.yaml`)
- **System Settings**: Port, workers, debug mode
- **Infrastructure**: RabbitMQ, Redis, Telegraf endpoints
- **Host Groups**: Target system organization
- **Alert Routing**: Plugin mapping and parameters
- **Notifications**: Webhook URLs and settings
- **LLM Settings**: GigaChat credentials and preferences

### Environment-Based Overrides
- Docker Compose environment variables
- Group-based configuration overrides
- Runtime parameter customization

## 🚀 Deployment Architecture

### Single Binary Deployment
```bash
# Build standalone binary
./build-agent.sh

# Deploy infrastructure
docker-compose up -d

# Start agent
./dist/seed-agent --config seed.yaml
```

### Service Management
- **start.sh**: Complete stack startup with health checks
- **stop.sh**: Graceful shutdown with cleanup
- **services.sh**: Docker service management

## 🔍 Monitoring & Observability

### Health Checks
- **System Health**: `/health` endpoint
- **Configuration**: `/config` endpoint  
- **Metrics**: `/metrics` endpoint (Prometheus format)

### Logging
- **Structured logging**: Configurable levels and formats
- **File rotation**: Size-based log rotation
- **Console output**: Colored terminal output

### Metrics
- Alert processing rates
- Plugin execution times
- Queue sizes and processing delays
- Error rates and success ratios

## 🛡️ Security Features

### Authentication & Authorization
- MongoDB authentication support
- RabbitMQ user management
- SSL/TLS configuration options

### Data Protection
- Credential masking in logs
- Secure token storage for LLM integration
- Configurable SSL verification

## 📈 Scalability Design

### Horizontal Scaling
- Multiple worker processes
- Queue-based processing
- Stateless plugin architecture

### Performance Optimization
- Redis-based throttling
- Connection pooling for external services
- Asynchronous processing capabilities

## 🎯 Key Strengths

1. **Production Ready**: Complete infrastructure automation
2. **Plugin Architecture**: Easily extensible monitoring capabilities  
3. **Unified Configuration**: Single YAML file for all settings
4. **Container First**: Docker-based infrastructure
5. **LLM Enhanced**: AI-powered alert analysis
6. **Multi-channel Notifications**: Flexible notification delivery
7. **Built-in Reliability**: Queue-based processing with retries
8. **Single Binary**: Easy deployment without dependencies