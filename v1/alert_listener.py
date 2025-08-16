# -*- coding: utf-8 -*-
"""
SEED Alert Listener - HTTP webhook service that receives alerts and forwards them to RabbitMQ.
Supports multiple input formats: Zabbix, Prometheus, custom JSON.
"""
import json
import logging
import os
import sys
import pathlib
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
import pika
from dotenv import load_dotenv

sys.path.append(str(pathlib.Path(__file__).resolve().parents[0]))

load_dotenv("../seed.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# RabbitMQ Configuration
RABBIT_HOST = os.getenv("RABBIT_HOST", "127.0.0.1")
RABBIT_USER = os.getenv("RABBIT_USER", "seed")
RABBIT_PASS = os.getenv("RABBIT_PASS", "seedpass")
RABBIT_QUEUE = os.getenv("RABBIT_QUEUE", "seed-inbox")
RABBIT_VHOST = os.getenv("RABBIT_VHOST", "/")

# Listener Configuration
LISTENER_HOST = os.getenv("LISTENER_HOST", "0.0.0.0")
LISTENER_PORT = int(os.getenv("LISTENER_PORT", "8080"))

def get_rabbit_connection():
    """Create RabbitMQ connection."""
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        virtual_host=RABBIT_VHOST,
        credentials=pika.PlainCredentials(RABBIT_USER, RABBIT_PASS),
        heartbeat=30
    )
    return pika.BlockingConnection(params)

def send_to_rabbit(alert: Dict[str, Any]) -> bool:
    """Send alert to RabbitMQ queue."""
    try:
        conn = get_rabbit_connection()
        ch = conn.channel()
        ch.queue_declare(queue=RABBIT_QUEUE, durable=True)
        
        message = json.dumps(alert, ensure_ascii=False)
        ch.basic_publish(
            exchange="",
            routing_key=RABBIT_QUEUE,
            body=message.encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2)  # persistent
        )
        
        conn.close()
        logger.info(f"Alert sent to RabbitMQ: {alert.get('type', 'unknown')} @ {alert.get('host', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send alert to RabbitMQ: {e}")
        return False

def normalize_zabbix_alert(data: Dict) -> Optional[Dict[str, Any]]:
    """Convert Zabbix webhook format to SEED format."""
    try:
        return {
            "type": "zabbix_alert",
            "host": data.get("hostname", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "severity": data.get("severity", "unknown"),
            "payload": {
                "trigger_name": data.get("trigger_name"),
                "item_key": data.get("item_key"),
                "item_value": data.get("item_value"),
                "trigger_status": data.get("trigger_status"),
                "event_id": data.get("event_id")
            }
        }
    except Exception as e:
        logger.error(f"Failed to normalize Zabbix alert: {e}")
        return None

def normalize_prometheus_alert(data: Dict) -> Optional[Dict[str, Any]]:
    """Convert Prometheus webhook format to SEED format."""
    try:
        alerts = []
        for alert in data.get("alerts", []):
            labels = alert.get("labels", {})
            alerts.append({
                "type": "prometheus_alert",
                "host": labels.get("instance", "unknown").split(":")[0],
                "timestamp": alert.get("startsAt", datetime.now().isoformat()),
                "severity": labels.get("severity", "unknown"),
                "payload": {
                    "alertname": labels.get("alertname"),
                    "job": labels.get("job"),
                    "instance": labels.get("instance"),
                    "description": alert.get("annotations", {}).get("description"),
                    "summary": alert.get("annotations", {}).get("summary"),
                    "status": alert.get("status")
                }
            })
        return alerts
    except Exception as e:
        logger.error(f"Failed to normalize Prometheus alert: {e}")
        return None

def normalize_custom_alert(data: Dict) -> Optional[Dict[str, Any]]:
    """Validate and normalize custom SEED alert format."""
    required_fields = ["type", "host"]
    
    for field in required_fields:
        if field not in data:
            logger.error(f"Missing required field: {field}")
            return None
    
    return {
        "type": data["type"],
        "host": data["host"],
        "timestamp": data.get("timestamp", datetime.now().isoformat()),
        "severity": data.get("severity", "info"),
        "payload": data.get("payload", {})
    }

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "seed-alert-listener"})

@app.route("/webhook/zabbix", methods=["POST"])
def zabbix_webhook():
    """Zabbix webhook endpoint."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        alert = normalize_zabbix_alert(data)
        if not alert:
            return jsonify({"error": "Failed to normalize Zabbix alert"}), 400
        
        if send_to_rabbit(alert):
            return jsonify({"status": "success", "message": "Alert forwarded to RabbitMQ"})
        else:
            return jsonify({"error": "Failed to send alert to RabbitMQ"}), 500
            
    except Exception as e:
        logger.error(f"Error processing Zabbix webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/webhook/prometheus", methods=["POST"])
def prometheus_webhook():
    """Prometheus Alertmanager webhook endpoint."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        alerts = normalize_prometheus_alert(data)
        if not alerts:
            return jsonify({"error": "Failed to normalize Prometheus alerts"}), 400
        
        success_count = 0
        for alert in alerts:
            if send_to_rabbit(alert):
                success_count += 1
        
        return jsonify({
            "status": "success", 
            "message": f"Forwarded {success_count}/{len(alerts)} alerts to RabbitMQ"
        })
        
    except Exception as e:
        logger.error(f"Error processing Prometheus webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/webhook/custom", methods=["POST"])
def custom_webhook():
    """Custom SEED format webhook endpoint."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        # Handle both single alert and array of alerts
        alerts = data if isinstance(data, list) else [data]
        
        success_count = 0
        for alert_data in alerts:
            alert = normalize_custom_alert(alert_data)
            if alert and send_to_rabbit(alert):
                success_count += 1
        
        return jsonify({
            "status": "success",
            "message": f"Forwarded {success_count}/{len(alerts)} alerts to RabbitMQ"
        })
        
    except Exception as e:
        logger.error(f"Error processing custom webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def index():
    """Service information endpoint."""
    return jsonify({
        "service": "SEED Alert Listener",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "zabbix_webhook": "/webhook/zabbix",
            "prometheus_webhook": "/webhook/prometheus", 
            "custom_webhook": "/webhook/custom"
        },
        "rabbitmq": {
            "host": RABBIT_HOST,
            "queue": RABBIT_QUEUE
        }
    })

if __name__ == "__main__":
    logger.info(f"Starting SEED Alert Listener on {LISTENER_HOST}:{LISTENER_PORT}")
    logger.info(f"RabbitMQ: {RABBIT_HOST}, Queue: {RABBIT_QUEUE}")
    
    app.run(
        host=LISTENER_HOST,
        port=LISTENER_PORT,
        debug=False
    )