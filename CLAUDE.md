# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

This is a Python-based monitoring/alerting system called "seed" with a plugin-based architecture:

```
v1/
├── core/           # Core system components (currently empty placeholders)
│   ├── agent.py    # Main agent orchestrator
│   ├── bus.py      # Event bus/messaging system
│   ├── config.py   # Configuration management
│   ├── llm.py      # LLM integration
│   └── notifier.py # Notification handling
├── plugins/        # Plugin implementations (currently empty placeholders)
│   ├── mongo_hot.py    # MongoDB hotspot monitoring
│   └── os_basic.py     # Basic OS monitoring
└── configs/
    └── seed.yaml   # Main configuration file with alert routing
```

## Configuration System

The system uses YAML-based configuration (`v1/configs/seed.yaml`) with:
- **Groups**: Host grouping for targeted overrides (mongo-prod, mongo-stage)
- **Alerts**: Plugin routing with payload configuration
  - `os_basic`: OS inventory monitoring
  - `mongo_hotspots`: MongoDB performance monitoring with configurable thresholds

Alert configurations support:
- Default payloads for plugins
- Group-based overrides for different environments
- MongoDB connection strings and performance thresholds

## Development Status

This appears to be an early-stage project with:
- Empty Python module files (placeholders for future implementation)
- Well-defined configuration structure
- Plugin-based architecture design
- MongoDB monitoring focus with authentication

## Architecture Patterns

The system follows a plugin-based event-driven architecture where:
1. Configuration defines alert routing to plugins
2. Plugins handle specific monitoring tasks (OS, MongoDB)
3. Core modules provide orchestration, messaging, and notification capabilities
4. Environment-specific configurations via group overrides

When implementing code, follow the established pattern of separating core functionality from plugins, and ensure MongoDB connections use the configured authentication parameters from the YAML configuration.