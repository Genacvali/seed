# SEED Agent v4 - Offline Deployment Guide

This guide explains how to deploy SEED Agent in environments without internet access using pre-exported Docker images.

## 🚀 Quick Start

### 1. Export Images (on system with internet)
```bash
# Export Docker images to tar files
./export-images.sh
```

### 2. Transfer Files
Copy the entire `v4/` directory to the target system, including:
- `images/redis-7.2-alpine.tar`
- `images/rabbitmq-3.13-management.tar`
- All SEED Agent files

### 3. Load Images (on offline system)  
```bash
# Load Docker images from tar files
./load-images.sh
```

### 4. Deploy
```bash
# Start complete SEED Agent stack
./start.sh
```

## 📦 Image Details

| Component | Image | Size (approx) |
|-----------|-------|---------------|
| Redis | `redis:7.2-alpine` | ~30MB |
| RabbitMQ | `rabbitmq:3.13-management` | ~180MB |

## 📁 Directory Structure

```
v4/
├── images/                           # Docker image archives
│   ├── redis-7.2-alpine.tar        # Redis image
│   └── rabbitmq-3.13-management.tar # RabbitMQ image
├── export-images.sh                 # Export script
├── load-images.sh                   # Load script  
├── start.sh                         # Deployment script
├── seed.yaml                        # Configuration
└── ... (other SEED Agent files)
```

## 🔧 Manual Commands

### Export Images
```bash
# Export Redis
docker save redis:7.2-alpine -o images/redis-7.2-alpine.tar

# Export RabbitMQ  
docker save rabbitmq:3.13-management -o images/rabbitmq-3.13-management.tar
```

### Load Images
```bash
# Load Redis
docker load -i images/redis-7.2-alpine.tar

# Load RabbitMQ
docker load -i images/rabbitmq-3.13-management.tar
```

### Verify
```bash
# List loaded images
docker images | grep -E "(redis|rabbitmq)"

# Check image details
docker image inspect redis:7.2-alpine
docker image inspect rabbitmq:3.13-management
```

## 🚫 Offline Requirements

The offline system needs:
- **Docker Engine** (or compatible runtime)
- **Docker Compose** (or docker compose plugin)
- **Python 3.8+** (for SEED Agent binary)
- **Basic tools**: bash, curl, awk

No internet connectivity required after images are loaded.

## 🔍 Troubleshooting

### Images not found
```bash
# Check if images exist
ls -la images/

# Verify file integrity
file images/*.tar
```

### Load failures
```bash
# Check Docker daemon
docker info

# Manual load with verbose output
docker load -i images/redis-7.2-alpine.tar --quiet=false
```

### Service startup issues
```bash
# Check loaded images
docker images

# Manual container start
docker run --rm redis:7.2-alpine redis-cli --version
docker run --rm rabbitmq:3.13-management rabbitmq-diagnostics status
```

## 📋 Deployment Checklist

- [ ] Export images with `./export-images.sh`
- [ ] Transfer `v4/` directory to target system  
- [ ] Verify `images/*.tar` files exist
- [ ] Load images with `./load-images.sh`
- [ ] Verify images with `docker images`
- [ ] Deploy with `./start.sh`
- [ ] Test with `curl http://HOST_IP:8080/health`

## 🔄 Updates

To update images:
1. Export new images with updated tags
2. Transfer to offline system
3. Load new images (old images will be replaced)
4. Restart services with `./start.sh`