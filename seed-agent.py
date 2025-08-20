#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED Agent - Single binary monitoring system
"""
import sys
import os
import asyncio
import signal
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
import uvicorn
from aio_pika.abc import AbstractIncomingMessage

# Import core modules
from core.config import Config
from core.queue import QueueManager
from core.redis_throttle import RedisThrottler
from core.notify import Notifier
from core.alert_processor import AlertProcessor


class SeedAgent:
    def __init__(self, config_path: str = "seed.yaml", plugins_path: str = "plugins.py"):
        self.config = Config(config_path)
        self.queue_manager = QueueManager()
        self.throttler = RedisThrottler()
        self.notifier = Notifier()
        self.alert_processor = AlertProcessor(plugins_path)
        self.running = True
        
        # FastAPI app
        self.app = FastAPI(
            title="SEED Agent",
            version="3.0",
            lifespan=self.lifespan
        )
        self._setup_routes()
    
    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifespan manager"""
        # Startup
        try:
            await self.queue_manager.connect()
            self.notifier.info("SEED Agent started")
            yield
        finally:
            # Shutdown
            await self.queue_manager.close()
            self.notifier.info("SEED Agent stopped")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        def health():
            return {
                "status": "healthy",
                "timestamp": int(time.time()),
                "version": "3.0"
            }
        
        @self.app.get("/stats")
        async def stats():
            queue_stats = {}
            try:
                if self.queue_manager.channel:
                    for name, queue in self.queue_manager.queues.items():
                        queue_info = await self.queue_manager.channel.queue_declare(
                            queue.name, passive=True
                        )
                        queue_stats[name] = {"message_count": queue_info.message_count}
            except Exception as e:
                queue_stats = {"error": str(e)}
            
            return {
                "throttle": self.throttler.get_stats(),
                "queues": queue_stats,
                "plugins": self.alert_processor.list_plugins(),
                "timestamp": int(time.time())
            }
        
        @self.app.post("/alert")
        async def alert_webhook(req: Request):
            """Alertmanager webhook endpoint"""
            body = await req.json()
            alerts: List[Dict[str, Any]] = body.get("alerts", [])
            queued = 0
            
            for alert in alerts:
                try:
                    fingerprint = self.alert_processor.fingerprint(alert)
                    
                    # Check throttling
                    if self.throttler.is_suppressed(fingerprint, self.config.alert_ttl):
                        continue
                    
                    # Queue alert for processing
                    await self.queue_manager.publish_alert(alert)
                    self.throttler.mark(fingerprint, self.config.alert_ttl)
                    queued += 1
                    
                except Exception as e:
                    self.notifier.error(f"Failed to queue alert: {e}")
            
            return {"ok": True, "queued": queued}
        
        @self.app.get("/config/reload")
        def reload_config():
            """Reload configuration and plugins"""
            try:
                self.config.reload()
                self.alert_processor.reload_plugins()
                return {"ok": True, "message": "Configuration reloaded"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
    
    async def process_alert_message(self, message: AbstractIncomingMessage):
        """Process a single alert message from queue"""
        async with message.process():
            try:
                alert_data = json.loads(message.body.decode())
                retry_count = int(message.headers.get("retry_count", 0))
                
                # Process alert through plugins
                result = await self.alert_processor.process_alert(alert_data)
                
                if result:
                    # Send notification
                    await self.notifier.send_notification(result)
                    self.notifier.debug(f"Alert processed successfully: {result.get('title', 'Unknown')}")
                else:
                    self.notifier.debug("Alert processed but no notification generated")
                    
            except Exception as e:
                self.notifier.error(f"Alert processing failed: {e}")
                retry_count += 1
                
                if retry_count < 3:
                    # Retry with exponential backoff
                    await self._retry_alert(alert_data, retry_count)
                    self.notifier.warning(f"Alert sent to retry queue (attempt {retry_count})")
                else:
                    # Send to DLQ after max retries
                    self.notifier.error(f"Alert failed after {retry_count} attempts, sending to DLQ")
                    raise
    
    async def _retry_alert(self, alert_data: Dict[str, Any], retry_count: int):
        """Send alert to retry queue with delay"""
        import aio_pika
        
        # Calculate delay (exponential backoff)
        delay_seconds = min(300, 2 ** retry_count * 10)  # Max 5 minutes
        
        message = aio_pika.Message(
            json.dumps(alert_data).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={
                "retry_count": retry_count,
                "x-delay": delay_seconds * 1000  # RabbitMQ delay in milliseconds
            }
        )
        
        await self.queue_manager.channel.default_exchange.publish(
            message, 
            routing_key="seed.alerts.retry"
        )
    
    async def start_worker(self):
        """Start the alert processing worker"""
        self.notifier.info("Starting alert worker...")
        
        await self.queue_manager.connect()
        await self.queue_manager.queues["alerts"].consume(self.process_alert_message)
        
        self.notifier.info("Worker started, waiting for alerts...")
        
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.notifier.info("Received shutdown signal")
        finally:
            await self.queue_manager.close()
    
    def stop(self):
        """Stop the agent"""
        self.running = False
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the FastAPI server"""
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        await server.serve()


def setup_signal_handlers(agent: SeedAgent):
    """Setup graceful shutdown signal handlers"""
    def signal_handler():
        agent.stop()
    
    if os.name != 'nt':  # Unix/Linux
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(sig, signal_handler)


async def main():
    parser = argparse.ArgumentParser(description="SEED Agent - Monitoring System")
    parser.add_argument("--config", default="seed.yaml", help="Configuration file path")
    parser.add_argument("--plugins", default="plugins.py", help="Plugins file path")
    parser.add_argument("--mode", choices=["server", "worker", "both"], default="both",
                       help="Run mode: server only, worker only, or both")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = SeedAgent(args.config, args.plugins)
    setup_signal_handlers(agent)
    
    # Start based on mode
    if args.mode == "server":
        await agent.start_server(args.host, args.port)
    elif args.mode == "worker":
        await agent.start_worker()
    else:  # both
        # Run server and worker concurrently
        await asyncio.gather(
            agent.start_server(args.host, args.port),
            agent.start_worker()
        )


if __name__ == "__main__":
    asyncio.run(main())