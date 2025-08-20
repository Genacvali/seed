# SEED Production Deployment Guide

## Overview

This guide covers production deployment of the SEED monitoring system with:
- **Secure external access** via HTTPS only
- **Internal service isolation** with separate networks
- **SSL termination** at reverse proxy level
- **Secrets management** via Docker Secrets
- **Resource limits** and health checks
- **Persistent data storage**

## Architecture

```
Internet → Nginx (SSL) → SEED Agent (Internal)
                      ↓
              RabbitMQ + Redis (Internal)
                      ↓
            Optional: Grafana + Prometheus
```

## Quick Start

### 1. Prerequisites

```bash
# Create deployment directory
sudo mkdir -p /opt/seed
cd /opt/seed

# Copy production files
cp docker-compose.production.yml docker-compose.yml
cp -r config/ .
cp -r secrets/ .
cp seed.yaml .
cp plugins.py .
```

### 2. Configure Domain and SSL

**Option A: Self-signed certificate (Testing)**
```bash
./scripts/generate-ssl.sh your-domain.com
```

**Option B: Let's Encrypt (Production)**
```bash
# Install certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Link certificates
sudo ln -s /etc/letsencrypt/live/your-domain.com/fullchain.pem config/nginx/ssl/server.crt
sudo ln -s /etc/letsencrypt/live/your-domain.com/privkey.pem config/nginx/ssl/server.key
```

### 3. Update Configuration

Edit `config/nginx/nginx.conf`:
```nginx
server_name your-domain.com;  # Replace with your domain
```

Update IP whitelists for admin interfaces:
```nginx
# Allow your admin networks
allow 203.0.113.0/24;    # Your office network
allow 198.51.100.50/32;  # Your home IP
```

### 4. Set Production Passwords

```bash
# Generate strong passwords
openssl rand -base64 32 > secrets/redis_password.txt
openssl rand -base64 32 > secrets/rabbitmq_password.txt
openssl rand -base64 32 > secrets/grafana_password.txt

# Secure the secrets directory
sudo chmod 600 secrets/*.txt
sudo chown root:root secrets/*.txt
```

### 5. Create Data Directories

```bash
# Create persistent data directories
sudo mkdir -p /opt/seed/data/{rabbitmq,redis,prometheus,grafana}
sudo chown -R 999:999 /opt/seed/data/rabbitmq
sudo chown -R 999:999 /opt/seed/data/redis
sudo chown -R 65534:65534 /opt/seed/data/prometheus
sudo chown -R 472:472 /opt/seed/data/grafana
```

### 6. Deploy

```bash
# Start core services
docker-compose up -d

# Start with metrics (optional)
docker-compose --profile metrics up -d

# Check status
docker-compose ps
docker-compose logs -f seed-agent
```

## Service Endpoints

| Service | Internal | External | Description |
|---------|----------|----------|-------------|
| SEED Agent | `http://seed-agent:8080` | `https://your-domain.com/api/` | Main monitoring API |
| Health Check | - | `https://your-domain.com/health` | System health status |
| RabbitMQ UI | `http://seed-rabbitmq:15672` | `https://your-domain.com/rabbitmq/` | Queue management (admin only) |
| Grafana | `http://seed-grafana:3000` | `https://your-domain.com/grafana/` | Dashboards (admin only) |
| Prometheus | `http://seed-prometheus:9090` | `https://your-domain.com/prometheus/` | Metrics (admin only) |

## Security Features

### Network Isolation
- **seed-network**: Internal communication only
- **seed-external**: Nginx proxy access only
- No direct external access to backend services

### Access Control
- HTTPS only (HTTP redirected)
- Admin interfaces restricted by IP whitelist
- Rate limiting on API endpoints
- Strong SSL configuration (TLS 1.2+)

### Secrets Management
- Passwords stored in Docker Secrets
- No hardcoded credentials in compose files
- Separate secret files with restricted permissions

### Security Headers
```
- Strict-Transport-Security
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection
```

## Monitoring and Health Checks

### Health Check Endpoints
```bash
# System health
curl https://your-domain.com/health

# Service metrics
curl https://your-domain.com/metrics

# Component status
docker-compose ps
```

### Log Management
```bash
# Application logs
docker-compose logs -f seed-agent

# Nginx access logs
docker-compose exec nginx tail -f /var/log/nginx/access.log

# System logs
journalctl -u docker -f
```

## Backup and Maintenance

### Data Backup
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/seed-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Stop services
docker-compose stop

# Backup data
cp -r /opt/seed/data/ $BACKUP_DIR/
cp -r /opt/seed/config/ $BACKUP_DIR/
cp /opt/seed/seed.yaml $BACKUP_DIR/

# Restart services
docker-compose start
```

### SSL Certificate Renewal
```bash
# Auto-renewal with Let's Encrypt
echo "0 12 * * * /usr/bin/certbot renew --quiet && docker-compose exec nginx nginx -s reload" | sudo crontab -
```

### Updates
```bash
# Pull latest images
docker-compose pull

# Recreate containers
docker-compose up -d --force-recreate
```

## Firewall Configuration

```bash
# UFW example
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 5672/tcp     # Block direct RabbitMQ access
sudo ufw deny 6379/tcp     # Block direct Redis access
sudo ufw deny 8080/tcp     # Block direct app access
sudo ufw enable
```

## Performance Tuning

### Resource Limits
Current limits in `docker-compose.production.yml`:
- **SEED Agent**: 1 CPU, 1GB RAM
- **RabbitMQ**: 1 CPU, 2GB RAM  
- **Redis**: 0.5 CPU, 512MB RAM
- **Nginx**: Default (lightweight)

### Scaling Considerations
```bash
# Scale SEED agent (if needed)
docker-compose up -d --scale seed-agent=2

# Load balancer configuration in nginx.conf:
upstream seed-agent {
    server seed-agent_1:8080;
    server seed-agent_2:8080;
    keepalive 32;
}
```

## Troubleshooting

### Common Issues

**1. SSL Certificate Errors**
```bash
# Check certificate
openssl x509 -in config/nginx/ssl/server.crt -text -noout

# Test SSL configuration
docker-compose exec nginx nginx -t
```

**2. Service Connection Issues**
```bash
# Check internal networking
docker-compose exec seed-agent ping seed-rabbitmq
docker-compose exec seed-agent ping seed-redis

# Check service health
docker-compose exec seed-agent curl http://localhost:8080/health
```

**3. Permission Issues**
```bash
# Fix data directory permissions
sudo chown -R 999:999 /opt/seed/data/rabbitmq
sudo chown -R 999:999 /opt/seed/data/redis
```

### Debug Mode
```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose up -d
```

## Production Checklist

- [ ] Domain name configured and DNS pointing to server
- [ ] SSL certificate installed (Let's Encrypt recommended)
- [ ] All default passwords changed to strong passwords
- [ ] IP whitelists updated for admin interfaces
- [ ] Firewall configured to block direct service access
- [ ] Data directories created with proper permissions
- [ ] Backup strategy implemented
- [ ] Monitoring and alerting configured
- [ ] SSL certificate auto-renewal configured
- [ ] Resource limits appropriate for your load
- [ ] Log rotation configured

## Support

For issues:
1. Check service logs: `docker-compose logs [service-name]`
2. Verify health checks: `docker-compose ps`
3. Test internal connectivity between services
4. Review nginx configuration and SSL certificates