# Quick Production Deployment After Git Clone

## 1. Clone and Setup

```bash
# Clone repository
git clone <your-repo-url> seed-monitoring
cd seed-monitoring/v3

# Create production directories
sudo mkdir -p /opt/seed
sudo cp -r . /opt/seed/
cd /opt/seed
```

## 2. Configure Domain

```bash
# Edit nginx configuration with your domain
sudo nano config/nginx/nginx.conf

# Replace 'your-domain.com' with your actual domain
sed -i 's/your-domain.com/monitoring.example.com/g' config/nginx/nginx.conf
```

## 3. Generate SSL Certificate

**For testing/development:**
```bash
chmod +x scripts/generate-ssl.sh
./scripts/generate-ssl.sh monitoring.example.com
```

**For production with Let's Encrypt:**
```bash
# Install certbot
sudo apt update && sudo apt install certbot -y

# Stop any services using port 80/443
sudo systemctl stop apache2 nginx || true

# Generate certificate
sudo certbot certonly --standalone -d monitoring.example.com

# Link certificates
sudo mkdir -p config/nginx/ssl
sudo ln -sf /etc/letsencrypt/live/monitoring.example.com/fullchain.pem config/nginx/ssl/server.crt
sudo ln -sf /etc/letsencrypt/live/monitoring.example.com/privkey.pem config/nginx/ssl/server.key
```

## 4. Set Production Passwords

```bash
# Generate secure passwords
openssl rand -base64 32 > secrets/redis_password.txt
openssl rand -base64 32 > secrets/rabbitmq_password.txt
openssl rand -base64 32 > secrets/grafana_password.txt

# Secure permissions
sudo chmod 600 secrets/*.txt
sudo chown root:root secrets/*.txt
```

## 5. Configure Access Control

Edit IP whitelist in `config/nginx/nginx.conf`:
```bash
# Replace with your admin IP addresses
sudo nano config/nginx/nginx.conf

# Update these sections:
# allow 203.0.113.0/24;    # Your office network
# allow 198.51.100.50/32;  # Your home IP
```

## 6. Create Data Directories

```bash
# Create persistent storage
sudo mkdir -p /opt/seed/data/{rabbitmq,redis,prometheus,grafana}

# Set correct ownership
sudo chown -R 999:999 /opt/seed/data/rabbitmq
sudo chown -R 999:999 /opt/seed/data/redis
sudo chown -R 65534:65534 /opt/seed/data/prometheus
sudo chown -R 472:472 /opt/seed/data/grafana

# Set permissions
sudo chmod 755 /opt/seed/data/*
```

## 7. Deploy Services

```bash
# Use production compose file
cp docker-compose.production.yml docker-compose.yml

# Start core services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f seed-agent
```

## 8. Start with Metrics (Optional)

```bash
# Start all services including Grafana/Prometheus
docker-compose --profile metrics up -d

# Check all services
docker-compose --profile metrics ps
```

## 9. Configure Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 5672/tcp     # Block direct RabbitMQ
sudo ufw deny 6379/tcp     # Block direct Redis
sudo ufw deny 8080/tcp     # Block direct app access
sudo ufw enable
```

## 10. Test Deployment

```bash
# Test health endpoint
curl -k https://monitoring.example.com/health

# Test API endpoint
curl -k https://monitoring.example.com/api/health

# Check SSL certificate
openssl s_client -connect monitoring.example.com:443 -servername monitoring.example.com
```

## 11. Setup SSL Auto-Renewal (Let's Encrypt)

```bash
# Add cron job for certificate renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet && docker-compose exec nginx nginx -s reload" | sudo crontab -

# Test renewal
sudo certbot renew --dry-run
```

## 12. Final Configuration Check

```bash
# Verify all services are healthy
docker-compose ps

# Check service connectivity
docker-compose exec seed-agent curl http://seed-rabbitmq:15672
docker-compose exec seed-agent redis-cli -h seed-redis ping

# Test external access
curl https://monitoring.example.com/health
```

## Access URLs

After successful deployment:

| Service | URL | Access |
|---------|-----|--------|
| API Health | `https://monitoring.example.com/health` | Public |
| Main API | `https://monitoring.example.com/api/` | Public |
| RabbitMQ UI | `https://monitoring.example.com/rabbitmq/` | IP Restricted |
| Grafana | `https://monitoring.example.com/grafana/` | IP Restricted |
| Prometheus | `https://monitoring.example.com/prometheus/` | IP Restricted |

## Credentials

- **RabbitMQ**: `seed` / (password from `secrets/rabbitmq_password.txt`)
- **Grafana**: `admin` / (password from `secrets/grafana_password.txt`)
- **Redis**: (password from `secrets/redis_password.txt`)

## Troubleshooting

**Services not starting:**
```bash
docker-compose logs -f [service-name]
```

**SSL errors:**
```bash
# Check certificate
openssl x509 -in config/nginx/ssl/server.crt -text -noout

# Test nginx config
docker-compose exec nginx nginx -t
```

**Permission errors:**
```bash
# Fix data directory permissions
sudo chown -R 999:999 /opt/seed/data/rabbitmq
sudo chown -R 999:999 /opt/seed/data/redis
```

**Cannot connect to services:**
```bash
# Check internal networking
docker network ls
docker-compose exec seed-agent ping seed-rabbitmq
```

## Maintenance Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Update images
docker-compose pull && docker-compose up -d --force-recreate

# Backup data
sudo tar -czf /opt/backups/seed-backup-$(date +%Y%m%d).tar.gz /opt/seed/data/

# Stop all services
docker-compose down
```

## Production Checklist

- [ ] Domain DNS configured and pointing to server
- [ ] SSL certificate installed and working
- [ ] All default passwords changed
- [ ] IP whitelist configured for admin access
- [ ] Firewall rules applied
- [ ] Data directories created with correct permissions
- [ ] Services starting and healthy
- [ ] External API accessible via HTTPS
- [ ] SSL auto-renewal configured (if Let's Encrypt)
- [ ] Backup strategy implemented