#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED Agent v4 - Unified Monitoring System

Improvements in v4:
- Unified configuration management with environment variable interpolation
- Centralized service discovery and connection management
- Proper configuration validation at startup
- Eliminated hardcoded URLs and connection strings
- Consistent error handling and logging
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

# Core modules
from core.config import Config
from core.queue import QueueManager
from core.redis_throttle import RedisThrottler
from core.notify import NotificationManager
from plugins import PluginManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SeedAgent:
    """Main SEED Agent application"""
    
    def __init__(self, config_path: str = "seed.yaml"):
        # Load configuration
        self.config = Config(config_path)
        self._setup_logging()
        
        # Initialize components
        self.queue_manager = QueueManager(self.config)
        self.redis_throttler = RedisThrottler(self.config)
        self.notification_manager = NotificationManager(self.config)
        self.plugin_manager = PluginManager(self.config)
        
        # Runtime state
        self.is_running = False
        
        logger.info(f"SEED Agent v4 initialized with config: {config_path}")
        logger.info(f"Environment: {self.config.get('environment', 'unknown')}")
    
    def _setup_logging(self):
        """Setup logging based on configuration"""
        log_level = self.config.log_level
        log_format = self.config.log_format
        
        # Update root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Update handler format if needed
        for handler in root_logger.handlers:
            handler.setFormatter(logging.Formatter(log_format))
        
        # Enable debug mode if configured
        if self.config.debug:
            root_logger.setLevel(logging.DEBUG)
            logger.info("Debug mode enabled")
    
    async def startup(self):
        """Initialize all services"""
        logger.info("Starting SEED Agent v4...")
        
        # Validate configuration
        self._validate_startup_config()
        
        # Connect to services
        await self.queue_manager.connect()
        logger.info("✅ Connected to RabbitMQ")
        
        # Test Redis connection (non-blocking)
        redis_stats = self.redis_throttler.get_stats()
        if redis_stats["redis_connected"]:
            logger.info("✅ Connected to Redis")
        else:
            logger.warning("⚠️ Redis not available, using in-memory throttling")
        
        # Initialize notification manager
        await self.notification_manager.initialize()
        logger.info("✅ Notification manager initialized")
        
        self.is_running = True
        logger.info("🚀 SEED Agent v4 is ready!")
    
    async def shutdown(self):
        """Cleanup all services"""
        logger.info("Shutting down SEED Agent...")
        
        self.is_running = False
        
        if self.queue_manager:
            await self.queue_manager.close()
        
        if self.notification_manager:
            await self.notification_manager.close()
        
        logger.info("✅ SEED Agent shutdown complete")
    
    def _validate_startup_config(self):
        """Validate critical configuration at startup"""
        try:
            # Test configuration access
            rabbitmq_config = self.config.rabbitmq_config
            redis_config = self.config.redis_config
            
            logger.info(f"RabbitMQ: {rabbitmq_config['username']}@{rabbitmq_config['host']}:{rabbitmq_config['port']}")
            logger.info(f"Redis: {redis_config['host']}:{redis_config['port']}/{redis_config['db']}")
            
            # Check notification channels
            notif_config = self.config.notification_config
            enabled_channels = []
            
            if notif_config.get("mattermost", {}).get("enabled"):
                enabled_channels.append("Mattermost")
            if notif_config.get("slack", {}).get("enabled"):
                enabled_channels.append("Slack")
            if notif_config.get("email", {}).get("enabled"):
                enabled_channels.append("Email")
            
            if enabled_channels:
                logger.info(f"Notification channels: {', '.join(enabled_channels)}")
            else:
                logger.warning("⚠️ No notification channels enabled")
            
            # Check plugin configuration
            plugin_info = self.plugin_manager.get_plugin_info()
            logger.info(f"Loaded {plugin_info['total_plugins']} plugins")
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    async def process_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming alert"""
        try:
            alertname = alert_data.get("alertname", "UnknownAlert")
            instance = alert_data.get("instance", "unknown")
            labels = alert_data.get("labels", {})
            
            # Extract hostname from instance or labels
            hostname = self._extract_hostname(instance, labels)
            
            logger.info(f"Processing alert: {alertname} for {hostname}")
            
            # Check throttling
            throttle_key = f"{alertname}:{hostname}"
            if self.redis_throttler.suppressed(throttle_key, self.config.alert_ttl):
                logger.info(f"Alert {alertname} for {hostname} is throttled")
                return {
                    "success": True,
                    "action": "throttled",
                    "throttle_key": throttle_key
                }
            
            # Get alert routing
            route = self.config.get_alert_route(alertname, labels)
            if not route:
                logger.warning(f"No routing found for alert: {alertname}")
                return {
                    "success": False,
                    "error": f"No routing configuration for alert: {alertname}"
                }
            
            plugin_name = route["plugin"]
            payload = route["payload"]
            
            # Execute plugin
            result = await self.plugin_manager.execute_plugin(plugin_name, hostname, payload)
            
            if result.get("success"):
                # Mark as processed to prevent throttling
                self.redis_throttler.mark(throttle_key, self.config.alert_ttl)
                
                # Send notifications
                await self.notification_manager.send_alert_notification(
                    alert_data, result
                )
                
                logger.info(f"Successfully processed alert {alertname} for {hostname}")
            else:
                logger.error(f"Plugin execution failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Alert processing failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_hostname(self, instance: str, labels: Dict[str, str]) -> str:
        """Extract hostname from instance or labels"""
        # Try to get from labels first
        hostname = labels.get("hostname") or labels.get("instance") or labels.get("host")
        
        if hostname:
            return hostname
        
        # Extract from instance field (format: "hostname:port" or "ip:port")
        if ":" in instance:
            return instance.split(":")[0]
        
        return instance or "unknown"


# Global agent instance
seed_agent: Optional[SeedAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager"""
    global seed_agent
    
    try:
        # Startup
        seed_agent = SeedAgent()
        await seed_agent.startup()
        yield
    finally:
        # Shutdown
        if seed_agent:
            await seed_agent.shutdown()


# Create FastAPI app
app = FastAPI(
    title="SEED Agent v4",
    description="Unified Monitoring and Alert Processing System",
    version="4.0.0",
    lifespan=lifespan
)


@app.post("/alert")
async def receive_alert(alert: Dict[str, Any]):
    """Receive and process alert from monitoring system"""
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")
    
    try:
        result = await seed_agent.process_alert(alert)
        
        if result.get("success"):
            return JSONResponse(content=result, status_code=200)
        else:
            return JSONResponse(content=result, status_code=422)
            
    except Exception as e:
        logger.error(f"Alert processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not seed_agent or not seed_agent.is_running:
        raise HTTPException(status_code=503, detail="SEED Agent not ready")
    
    try:
        # Check plugin health
        plugin_health = await seed_agent.plugin_manager.health_check()
        
        # Check Redis health
        redis_stats = seed_agent.redis_throttler.get_stats()
        
        health = {
            "status": "healthy",
            "version": "4.0.0",
            "environment": seed_agent.config.get("environment", "unknown"),
            "services": {
                "rabbitmq": True,  # If we're running, RabbitMQ is connected
                "redis": redis_stats["redis_connected"],
                "plugins": plugin_health["healthy"]
            },
            "redis_stats": redis_stats,
            "plugin_health": plugin_health
        }
        
        return JSONResponse(content=health)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")
    
    # Basic metrics in Prometheus format
    metrics_data = [
        "# HELP seed_agent_info Information about SEED Agent",
        "# TYPE seed_agent_info gauge",
        f'seed_agent_info{{version="4.0.0",environment="{seed_agent.config.get("environment", "unknown")}"}} 1',
        "",
        "# HELP seed_agent_up Whether SEED Agent is running",
        "# TYPE seed_agent_up gauge",
        f"seed_agent_up {int(seed_agent.is_running)}",
        ""
    ]
    
    # Add Redis metrics
    redis_stats = seed_agent.redis_throttler.get_stats()
    metrics_data.extend([
        "# HELP seed_redis_connected Whether Redis is connected",
        "# TYPE seed_redis_connected gauge",
        f"seed_redis_connected {int(redis_stats['redis_connected'])}",
        "",
        "# HELP seed_throttled_alerts Number of throttled alerts",
        "# TYPE seed_throttled_alerts gauge",
        f"seed_throttled_alerts {redis_stats['suppressed_count']}",
        ""
    ])
    
    return PlainTextResponse("\n".join(metrics_data))


@app.get("/config")
async def get_config():
    """Get current configuration (sanitized)"""
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")
    
    # Return sanitized config without sensitive data
    config_summary = {
        "environment": seed_agent.config.get("environment"),
        "agent": {
            "host": seed_agent.config.bind_host,
            "port": seed_agent.config.bind_port,
            "debug": seed_agent.config.debug
        },
        "plugins": seed_agent.plugin_manager.get_plugin_info(),
        "notifications": {
            "mattermost_enabled": seed_agent.config.notification_config.get("mattermost", {}).get("enabled", False),
            "slack_enabled": seed_agent.config.notification_config.get("slack", {}).get("enabled", False),
            "email_enabled": seed_agent.config.notification_config.get("email", {}).get("enabled", False)
        }
    }
    
    return JSONResponse(content=config_summary)


@app.post("/config/reload")
async def reload_config():
    """Reload configuration"""
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")
    
    try:
        seed_agent.config.reload()
        logger.info("Configuration reloaded successfully")
        return {"success": True, "message": "Configuration reloaded"}
    except Exception as e:
        logger.error(f"Configuration reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SEED Agent v4")
    parser.add_argument("--config", default="seed.yaml", help="Configuration file path")
    parser.add_argument("--host", default=None, help="Bind host")
    parser.add_argument("--port", type=int, default=None, help="Bind port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Load config to get defaults
    try:
        config = Config(args.config)
        
        # Use command line args if provided, otherwise use config defaults
        host = args.host or config.bind_host
        port = args.port or config.bind_port
        debug = args.debug or config.debug
        
        # Log level
        log_level = "debug" if debug else config.log_level.lower()
        
        logger.info(f"Starting SEED Agent v4 on {host}:{port}")
        logger.info(f"Config file: {args.config}")
        logger.info(f"Environment: {config.get('environment', 'unknown')}")
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start server
        uvicorn.run(
            app,  # Pass app object directly instead of module string
            host=host,
            port=port,
            log_level=log_level,
            reload=debug,
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start SEED Agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()