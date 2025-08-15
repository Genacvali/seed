# -*- coding: utf-8 -*-
"""RabbitMQ message bus for SEED monitoring system."""
import os
from typing import Callable
import pika
from dotenv import load_dotenv

load_dotenv()

R_HOST  = os.getenv("RABBIT_HOST", "127.0.0.1")
R_USER  = os.getenv("RABBIT_USER", "seed")
R_PASS  = os.getenv("RABBIT_PASS", "seedpass")
R_QUEUE = os.getenv("RABBIT_QUEUE", "seed-inbox")
R_VHOST = os.getenv("RABBIT_VHOST", "/")

def consume(on_message: Callable[[bytes], None]) -> None:
    """Start consuming messages from RabbitMQ queue."""
    params = pika.ConnectionParameters(
        host=R_HOST,
        virtual_host=R_VHOST,
        credentials=pika.PlainCredentials(R_USER, R_PASS),
        heartbeat=30
    )
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue=R_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=5)

    def _cb(ch_, method, props, body):
        on_message(body)

    print(f"[*] SEED listening on queue '{R_QUEUE}' @ {R_HOST}")
    ch.basic_consume(queue=R_QUEUE, on_message_callback=_cb, auto_ack=True)
    ch.start_consuming()