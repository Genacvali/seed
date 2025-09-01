# -*- coding: utf-8 -*-
import json, pika
from typing import Dict, Iterator
from core.config import CFG
from core.log import get_logger

log = get_logger("amqp")

def _params() -> pika.ConnectionParameters:
    cred = pika.PlainCredentials(CFG.rabbit_user, CFG.rabbit_pass)
    return pika.ConnectionParameters(
        host=CFG.rabbit_host,
        port=CFG.rabbit_port,
        virtual_host=CFG.rabbit_vhost,
        credentials=cred,
        ssl=CFG.rabbit_ssl
    )

def consume_json() -> Iterator[Dict]:
    conn = pika.BlockingConnection(_params())
    ch = conn.channel()
    ch.queue_declare(queue=CFG.rabbit_queue, durable=True)

    for method, properties, body in ch.consume(CFG.rabbit_queue, inactivity_timeout=1):
        if body is None:
            continue
        try:
            msg = json.loads(body.decode("utf-8"))
            ch.basic_ack(method.delivery_tag)
            yield msg
        except Exception as e:
            log.exception("bad message: %s", e)
            ch.basic_nack(method.delivery_tag, requeue=False)