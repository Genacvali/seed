# -*- coding: utf-8 -*-
import asyncio
import json
import os
from typing import Dict, Any, Optional
import aio_pika
from aio_pika import Connection, Channel, Queue, Exchange
from aio_pika.abc import AbstractIncomingMessage

class QueueManager:
    def __init__(self):
        self.connection: Optional[Connection] = None
        self.channel: Optional[Channel] = None
        self.queues: Dict[str, Queue] = {}
        self.exchange: Optional[Exchange] = None
        
    async def connect(self):
        """Подключение к RabbitMQ"""
        rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection = await aio_pika.connect_robust(rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        
        # Создаем exchange для alerts
        self.exchange = await self.channel.declare_exchange(
            "seed.alerts", 
            aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        
        # Основная очередь для алертов
        self.queues["alerts"] = await self.channel.declare_queue(
            "seed.alerts.incoming",
            durable=True,
            arguments={
                "x-dead-letter-exchange": "seed.alerts.dlx",
                "x-dead-letter-routing-key": "dead"
            }
        )
        await self.queues["alerts"].bind(self.exchange, "incoming")
        
        # Dead Letter Exchange и очередь
        dlx = await self.channel.declare_exchange(
            "seed.alerts.dlx",
            aio_pika.ExchangeType.DIRECT,
            durable=True
        )
        
        self.queues["dlq"] = await self.channel.declare_queue(
            "seed.alerts.dead",
            durable=True
        )
        await self.queues["dlq"].bind(dlx, "dead")
        
        # Retry очередь с TTL
        self.queues["retry"] = await self.channel.declare_queue(
            "seed.alerts.retry",
            durable=True,
            arguments={
                "x-message-ttl": 30000,  # 30 секунд
                "x-dead-letter-exchange": "seed.alerts",
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

# Глобальный экземпляр
queue_manager = QueueManager()