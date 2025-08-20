# 🌱 SEED Project Structure

This repository contains two versions of the SEED monitoring system:

## 📁 Directory Layout

```
seed-1/
├── v2/                      # Working version (current)
│   ├── app.py              # FastAPI web server
│   ├── worker.py           # Alert processing worker
│   ├── core/               # Core modules (config, notify, queue, etc.)
│   ├── plugins/            # Individual plugin files
│   ├── configs/            # Separate config files
│   └── fetchers/           # Data fetching modules
│
└── v3/                      # 🚀 NEW: Redesigned architecture
    ├── seed-agent.py        # Single binary (server + worker)
    ├── seed.yaml            # Unified configuration
    ├── plugins.py           # All plugins in one file
    ├── docker-compose.yml   # Complete Docker environment
    ├── Dockerfile          # Optimized container build
    ├── Makefile            # Development workflow
    ├── README.md           # Complete documentation
    ├── MIGRATION.md        # v2 → v3 migration guide
    └── core/               # Refactored core modules
```

## 🎯 Version Comparison

| Feature | v2 | v3 |
|---------|----|----| 
| **Status** | Working | **Production Ready** |
| **Architecture** | Multi-process | Single binary |
| **Configuration** | Multiple files | Unified config |
| **Plugins** | Separate files | Single file |
| **Deployment** | Manual | **Docker native** |
| **Development** | Manual setup | **Make commands** |
| **Monitoring** | Basic | **Full observability** |
| **Documentation** | Basic | **Comprehensive** |

## 🚀 Quick Start

### For New Users (Recommended)
```bash
cd v3/
make dev                    # Start development environment
```

### For Current v2 Users
```bash
cd v2/                      # Continue with current version
# OR migrate to v3:
cd v3/
cat MIGRATION.md            # Read migration guide
```

## 🔄 Migration Path

**v2 → v3**: 
1. Read `v3/MIGRATION.md`
2. Consolidate configs into `v3/seed.yaml`
3. Merge plugins into `v3/plugins.py`
4. Test with `make dev`
5. Deploy with `make up`

## 📚 Documentation Locations

- **v2/**: See original CLAUDE.md and README files
- **v3/README.md**: Complete documentation for v3
- **v3/MIGRATION.md**: Detailed migration guide
- **v3/seed.yaml**: Configuration reference with comments
- **v3/Makefile**: All available development commands

## 🎨 Key Improvements in v3

### Architecture
- **Single Binary**: No more separate server/worker processes
- **External Config**: Configuration and plugins mounted as volumes
- **Container First**: Designed for Docker/Kubernetes deployment

### Developer Experience
- **One Command Setup**: `make dev` starts everything
- **Hot Reload**: Configuration changes without restart
- **Plugin Testing**: Individual plugin testing commands
- **Structured Logging**: Better debugging and monitoring

### Operations
- **Health Checks**: Automatic failure recovery
- **Resource Limits**: Optimized container resource usage
- **Metrics**: Prometheus-compatible metrics
- **Security**: Non-root containers, isolated networks

---

**Recommendation**: New projects should use **v3**. Existing v2 users can migrate when ready using the detailed migration guide.