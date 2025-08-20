# -*- coding: utf-8 -*-
import asyncio
import json
from typing import Dict, Any, Optional
import aio_pika
from aio_pika import Connection, Channel, Queue, Exchange
from aio_pika.abc import AbstractIncomingMessage
from .config import Config

class QueueManager:
    def __init__(self, config: Config):
        self.config = config
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.queues: Dict[str, Queue] = {}
        self.exchange: Optional[Exchange] = None
        
    async def connect(self):
        """Подключение к RabbitMQ"""
        rabbitmq_config = self.config.rabbitmq_config
        
        # Build connection URL from config
        host = rabbitmq_config["host"]
        port = rabbitmq_config["port"]
        username = rabbitmq_config["username"]
        password = rabbitmq_config["password"]
        vhost = rabbitmq_config["vhost"]
        
        if vhost == "/":
            vhost = ""
        else:
            vhost = f"/{vhost.strip('/')}"
        
        rabbitmq_url = f"amqp://{username}:{password}@{host}:{port}{vhost}"
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        
        # Get queue names from config
        queue_config = self.config.queue_config
        alerts_queue = queue_config.get("alerts", "seed.alerts")
        
        # Создаем exchange для alerts
        self.exchange = await self.channel.declare_exchange(
            alerts_queue, 
            aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        
        # Основная очередь для алертов
        self.queues["alerts"] = await self.channel.declare_queue(
            f"{alerts_queue}.incoming",
            durable=True,
            arguments={
                "x-dead-letter-exchange": f"{alerts_queue}.dlx",
                "x-dead-letter-routing-key": "dead"
            }
        )
        await self.queues["alerts"].bind(self.exchange, "incoming")
        
        # Dead Letter Exchange и очередь
        dlx = await self.channel.declare_exchange(
            f"{alerts_queue}.dlx",
            aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        
        dlq_queue = queue_config.get("dlq", "seed.alerts.dlq")
        self.queues["dlq"] = await self.channel.declare_queue(
            dlq_queue,
            durable=True
        )
        await self.queues["dlq"].bind(dlx, "dead")
        
        # Retry очередь с TTL
        retry_queue = queue_config.get("retry", "seed.alerts.retry")
        retry_ttl = self.config.retry_delay * 1000  # Convert to milliseconds
        
        self.queues["retry"] = await self.channel.declare_queue(
            retry_queue,
            durable=True,
            arguments={
                "x-message-ttl": retry_ttl,
                "x-dead-letter-exchange": alerts_queue,
                "x-dead-letter-routing-key": "incoming"
            }
        )
        
    async def publish_alert(self, alert: Dict[str, Any], routing_key: str = "incoming"):
        """Отправка алерта в очередь"""
        if not self.exchange:
            raise RuntimeError("Queue manager not connected")
            
        message = aio_pika.Message(
            json.dumps(alert).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"retry_count": 0}
        )
        
        await self.exchange.publish(message, routing_key=routing_key)
        
    async def close(self):
        """Закрытие соединения"""
        if self.connection:
            await self.connection.close()

# Global instance will be created with config in main application
queue_manager: Optional[QueueManager] = None