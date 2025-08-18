# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import signal
from typing import Dict, Any
from aio_pika.abc import AbstractIncomingMessage

import core.config as config
import core.notify as notify
import core.plugins as plugins
from core.queue import queue_manager

class AlertWorker:
    def __init__(self):
        self.running = True
        
    async def process_alert_message(self, message: AbstractIncomingMessage):
        """Обработка одного сообщения из очереди"""
        async with message.process():
            try:
                alert_data = json.loads(message.body.decode())
                retry_count = int(message.headers.get("retry_count", 0))
                
                # Обрабатываем алерт (перенесено из app.py)
                result = self.process_one_alert(alert_data)
                
                if result:
                    notify.send_mm(result)
                    notify.log(f"[WORKER] Alert processed successfully")
                else:
                    notify.log(f"[WORKER] Alert processed but no message generated")
                    
            except Exception as e:
                notify.log(f"[WORKER ERROR] {e}")
                retry_count += 1
                
                if retry_count < 3:  # Максимум 3 попытки
                    # Отправляем в retry очередь
                    await self.retry_alert(alert_data, retry_count)
                    notify.log(f"[WORKER] Alert sent to retry queue (attempt {retry_count})")
                else:
                    # После 3 попыток сообщение попадет в DLQ автоматически
                    notify.log(f"[WORKER] Alert failed after {retry_count} attempts, going to DLQ")
                    raise  # Это отправит сообщение в DLQ
                    
    async def retry_alert(self, alert_data: Dict[str, Any], retry_count: int):
        """Отправка алерта в retry очередь"""
        import aio_pika
        
        message = aio_pika.Message(
            json.dumps(alert_data).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"retry_count": retry_count}
        )
        
        # Отправляем в retry очередь
        await queue_manager.channel.default_exchange.publish(
            message, 
            routing_key="seed.alerts.retry"
        )
    
    def process_one_alert(self, a: Dict[str, Any]) -> str:
        """Обработка одного алерта (перенесено из app.py)"""
        labels = a.get("labels", {})
        annotations = a.get("annotations", {})
        alertname = labels.get("alertname") or "unknown"

        host = self._host_from_labels(labels)
        route = config.route_for(alertname, labels)
        if not route:
            return f"SEED: 🤷 не найден маршрут для alertname='{alertname}'"

        plugin_name = route["plugin"]
        payload = route.get("payload", {})
        payload = config.enrich_with_host_overrides(host, payload)

        fn = plugins.get_plugin(plugin_name)
        if not fn:
            return f"SEED: 🤷 не найден плагин '{plugin_name}'"

        return fn(host=host, labels=labels, annotations=annotations, payload=payload)
    
    def _host_from_labels(self, labels: Dict[str, str]) -> str:
        """Извлечение host из labels (перенесено из app.py)"""
        host = labels.get("host") or labels.get("nodename") or labels.get("instance")
        if host and ":" in host:
            host = host.split(":")[0]
        return host or "unknown"
        
    async def start(self):
        """Запуск worker'а"""
        notify.log("[WORKER] Starting alert worker...")
        
        # Подключаемся к RabbitMQ
        await queue_manager.connect()
        
        # Начинаем обработку сообщений
        await queue_manager.queues["alerts"].consume(self.process_alert_message)
        
        notify.log("[WORKER] Worker started, waiting for alerts...")
        
        # Ждем сигнала остановки
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            notify.log("[WORKER] Received shutdown signal")
        finally:
            await queue_manager.close()
            notify.log("[WORKER] Worker stopped")
    
    def stop(self):
        """Остановка worker'а"""
        self.running = False

async def main():
    worker = AlertWorker()
    
    # Обработка сигналов для graceful shutdown
    def signal_handler():
        worker.stop()
    
    if os.name != 'nt':  # Unix/Linux
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(sig, signal_handler)
    
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())