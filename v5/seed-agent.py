#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED Agent v5 - Universal LLM-powered Alert Processing System

Improvements in v5:
- Simplified architecture: no plugins, no routing configuration
- Universal LLM-powered alert analysis with specialized prompts
- Dynamic message formatting based on alert type and severity
- Intelligent priority scoring and time-based context
- Alert lifecycle management (firing/resolved states)
- All features work with incoming data only from Alertmanager
"""

import asyncio
import logging
import re
import signal
import socket
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

# Core modules
from core.config import Config
from core.queue import QueueManager
from core.redis_throttle import RedisThrottler
from core.notify import NotificationManager
from core.llm import LLMClient
from core.formatter import AlertMessageFormatter

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
        self.llm_client = LLMClient(self.config)
        
        # Runtime state
        self.is_running = False
        
        logger.info(f"🌌 SEED v5 initialized with config: {config_path}")
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
        import datetime
        self.start_time = datetime.datetime.now()
        
        logger.info("🚀 Starting 🌌 SEED v5...")
        
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
        
        # Initialize LLM client
        if hasattr(self.llm_client, 'initialize'):
            await self.llm_client.initialize()
        logger.info("✅ LLM client initialized")
        
        self.is_running = True
        logger.info("🚀 🌌 SEED v5 is ready! Universal LLM processing enabled")
    
    async def shutdown(self):
        """Cleanup all services"""
        logger.info("Shutting down 🌌 SEED...")
        
        self.is_running = False
        
        if self.queue_manager:
            await self.queue_manager.close()
        
        if self.notification_manager:
            await self.notification_manager.close()
        
        logger.info("✅ 🌌 SEED shutdown complete")
    
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
            
            # LLM client configured
            if self.llm_client.enabled:
                logger.info("✅ LLM client enabled for universal processing")
            else:
                logger.warning("⚠️ LLM client disabled - responses will be basic")
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    def _convert_custom_payload_to_alertmanager(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert custom payload (subject/message format) to Alertmanager format"""
        try:
            subject = payload.get("subject", "")
            message = payload.get("message", "")
            
            # Parse severity from subject or message
            severity = self._parse_severity_from_text(subject + " " + message)
            
            # Try to extract alertname from subject
            alertname = subject.replace("SEED Alert: ", "").strip()
            if not alertname:
                alertname = "Custom Alert"
            
            # Try to extract instance/hostname from message or subject
            instance = self._parse_instance_from_text(message)
            
            logger.info(f"[CUSTOM PAYLOAD] Converting: subject='{subject}' -> severity='{severity}', alertname='{alertname}', instance='{instance}'")
            
            # Convert to Alertmanager format
            alertmanager_format = {
                "labels": {
                    "alertname": alertname,
                    "severity": severity,
                    "instance": instance,
                    "job": "custom-script",
                    "source": "custom"
                },
                "annotations": {
                    "summary": subject,
                    "description": message
                },
                "status": "firing"
            }
            
            return alertmanager_format
            
        except Exception as e:
            logger.error(f"Custom payload conversion failed: {e}")
            # Return original if conversion fails
            return payload
    
    def _parse_severity_from_text(self, text: str) -> str:
        """Parse severity from text content"""
        text_upper = text.upper()
        
        # Check for severity keywords
        if any(word in text_upper for word in ["CRITICAL", "DISASTER", "💎🔥", "🔥"]):
            return "critical"
        elif any(word in text_upper for word in ["HIGH", "MAJOR", "⚔️", "🤒"]):
            return "high"  
        elif any(word in text_upper for word in ["WARNING", "WARN", "AVERAGE", "🛡️", "⚠️"]):
            return "warning"
        elif any(word in text_upper for word in ["INFO", "INFORMATION", "✨", "ℹ️"]):
            return "info"
        else:
            # Default based on alert keywords
            if any(word in text_upper for word in ["ERROR", "FAIL", "DOWN", "UNAVAILABLE", "ПРОЦЕССОВ НЕТ"]):
                return "high"  # Treat errors as high severity
            return "warning"  # Safe default
    
    def _parse_instance_from_text(self, text: str) -> str:
        """Extract instance/hostname from text"""
        import re
        
        # Look for hostname patterns in text
        hostname_patterns = [
            r'([a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*):(\d+)',  # hostname:port
            r'([a-zA-Z0-9\-]{3,}(?:\-[a-zA-Z0-9\-]+)*)',     # hostname-like strings
        ]
        
        for pattern in hostname_patterns:
            match = re.search(pattern, text)
            if match:
                if ':' in match.group(0):
                    return match.group(0)  # hostname:port
                else:
                    return f"{match.group(0)}:0"  # hostname:0
        
        return "unknown:0"
    
    async def process_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming alert"""
        try:
            # Detect and convert custom payload format (subject/message) to Alertmanager format
            if "subject" in alert_data and "message" in alert_data:
                alert_data = self._convert_custom_payload_to_alertmanager(alert_data)
            
            # Extract from labels (Alertmanager format)
            labels = alert_data.get("labels", {})
            annotations = alert_data.get("annotations", {})
            
            alertname = labels.get("alertname", alert_data.get("alertname", "UnknownAlert"))
            instance = labels.get("instance", alert_data.get("instance", "unknown"))
            
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
            
            # Universal LLM-powered alert processing
            result = await self.process_alert_with_llm(alert_data)
            
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
    
    def _rulebook_steps(self, labels: Dict[str, str], annotations: Dict[str, str]) -> Optional[List[str]]:
        """Rule-engine for common alert patterns - deterministic and instant"""
        name = (labels.get("alertname","") + " " + annotations.get("summary","")).lower()
        item_key = annotations.get("item_key","").lower() if isinstance(annotations.get("item_key"), str) else ""
        
        rules = [
            # MongoDB down / порт
            (lambda: "mongo" in name and ("not running" in name or "нет процессов" in name or ":27017" in name or "недоступен" in name),
             [
                "systemctl status mongod",
                "journalctl -u mongod --since '-15min'",
                "ss -lntp | grep :27017 || netstat -lntp | grep :27017"
             ]),
            # Zabbix agent
            (lambda: "zabbix" in name and ("agent" in name or "zabbix_agentd" in name),
             [
                "systemctl status zabbix-agent",
                "journalctl -u zabbix-agent --since '-30min'",
                "zabbix_agentd -t agent.ping"
             ]),
            # systemd service по шаблону  
            (lambda: "service" in name or "systemctl" in name or "служба" in name,
             [
                f"systemctl status {labels.get('service', '<service>')}",
                f"journalctl -u {labels.get('service', '<service>')} --since '-30min'"
             ]),
            # TCP доступность
            (lambda: "tcp" in name or "порт" in name or "port" in name or "connection" in name,
             [
                "ss -tnlp | head",
                f"nc -vz {labels.get('host', '<host>')} {labels.get('port', '<port>')}"
             ]),
            # Disk space
            (lambda: "disk" in name or "space" in name or "место" in name or "диск" in name,
             [
                "df -h",
                "du -sh /var/log/* | sort -hr | head -10",
                f"find {annotations.get('mountpoint', '/')} -type f -size +100M | head -10"
             ]),
            # High CPU/Load
            (lambda: "cpu" in name or "load" in name or "нагрузка" in name,
             [
                "top -bn1 | head -20",
                "ps aux --sort=-%cpu | head -10",
                "uptime"
             ]),
            # Memory issues
            (lambda: "memory" in name or "ram" in name or "память" in name or "oom" in name,
             [
                "free -h",
                "ps aux --sort=-%mem | head -10", 
                "dmesg | grep -i 'killed process' | tail -5"
             ]),
        ]
        
        for cond, steps in rules:
            try:
                if cond():
                    return steps
            except Exception:
                pass
        return None

    def _sanitize(self, text: str) -> str:
        """Post-processing: remove garbage and empty blocks"""
        lines = [l.rstrip() for l in text.splitlines()]

        # Remove banned words/markers  
        banned = {"```", "bash", "Bash", "Нет команд", "shell", "console"}
        lines = [l for l in lines if l.strip() and l.strip() not in banned]

        # Limit length: max 10 lines
        lines = lines[:10]

        # Remove empty section headers
        drop_next_if_header = {"Возможные причины:", "Возможные проблемы:", "Рекомендации:"}
        cleaned = []
        for i, l in enumerate(lines):
            if l.strip() in drop_next_if_header:
                # Empty header without content - skip
                if i == len(lines)-1 or not lines[i+1].strip().startswith(("•", "1.", "2.", "3.", "-")):
                    continue
            cleaned.append(l)
        return "\n".join(cleaned)

    async def process_alert_with_llm(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Universal LLM-powered alert processing with rule-engine"""
        try:
            labels = alert_data.get("labels", {})
            annotations = alert_data.get("annotations", {})
            alertname = labels.get("alertname", "Unknown Alert")
            severity = labels.get("severity", "unknown")
            instance = labels.get("instance", "unknown")
            
            # 🔄 Check if this is a resolution
            status = alert_data.get("status", "firing")
            if status == "resolved":
                return await self._handle_alert_resolution(alert_data)
            
            # 📋 Rule-engine: check for deterministic responses
            pre_steps = self._rulebook_steps(labels, annotations)
            pre_section = ""
            if pre_steps:
                pre_section = "Рекомендации:\n" + "\n".join(f"{i+1}. {cmd}" for i, cmd in enumerate(pre_steps))
            
            # 🎯 Priority scoring
            priority_score = self._calculate_priority(labels, annotations)
            
            # ⚡ Compact, strict LLM prompt
            llm_input = f"""
Ты SRE-инженер. Дай короткий, практичный ответ для онколла.

Контекст (используй только его, не выдумывай):
- alertname: {alertname}
- severity: {severity}
- instance: {instance}
- labels: {labels}
- annotations: {annotations}

Требования к ответу (строго):
- До 6 строк. Без префиксов 'Bash', без ```.
- Разделы ровно такие (если пусто — раздел НЕ выводить):
  1) "Возможные проблемы:" — 2–3 лаконичных буллета.
  2) "Рекомендации:" — нумерованный список 1–3 точных команд/действий.
- Команды только применимые к контексту (item.key, trigger.name, tags). Никаких placeholder'ов.
- Если информации недостаточно — вместо фантазий напиши одну строку: "Контекст недостаточен для точной диагностики."

Верни только текст сообщения без лишних пояснений.
"""
            
            # Send to LLM
            llm_response = ""
            if hasattr(self, 'llm_client') and self.llm_client:
                llm_response = await self.llm_client.get_completion(llm_input, max_tokens=300)
                # Sanitize LLM response
                llm_response = self._sanitize(llm_response)
            
            # Get current time for timestamp
            import datetime
            current_time = datetime.datetime.now()
            
            # Merge rule-engine and LLM responses
            final_response = ""
            if pre_steps:
                final_response = pre_section
                # If LLM also gave recommendations, add unique ones (max 3 total)
                if llm_response and "Рекомендации:" in llm_response:
                    llm_parts = llm_response.split("Рекомендации:")
                    if len(llm_parts) > 1:
                        llm_recommendations = llm_parts[1].strip().split('\n')[:3]  # Max 3 additional
                        # Add problems section if exists
                        if "Возможные проблемы:" in llm_response:
                            problems_section = llm_response.split("Рекомендации:")[0].strip()
                            if problems_section:
                                final_response = problems_section + "\n\n" + final_response
                else:
                    # Add LLM problems section if no recommendations conflict
                    if llm_response and "Возможные проблемы:" in llm_response:
                        problems_only = llm_response.split("Рекомендации:")[0].strip()
                        final_response = problems_only + "\n\n" + final_response
            else:
                final_response = llm_response or "Контекст недостаточен для точной диагностики."
            
            # Final sanitization
            final_response = self._sanitize(final_response)
            
            # Format final message using new formatter
            formatted_message = AlertMessageFormatter.format_alert_message(
                alertname=alertname,
                instance=instance,
                severity=severity,
                priority=priority_score,
                labels=labels,
                annotations=annotations,
                llm_response=final_response,
                time_context="",  # Remove time context for cleaner output
                status=status
            )
            
            return {
                "success": True,
                "message": formatted_message,
                "priority": priority_score,
                "alert_type": alertname,
                "severity": severity,
                "instance": instance,
                "timestamp": current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process alert with LLM: {e}")
            return {
                "success": False,
                "error": f"LLM processing failed: {str(e)}"
            }
    
    def _calculate_priority(self, labels: Dict[str, str], annotations: Dict[str, str]) -> int:
        """🎯 Calculate alert priority score (0-3)"""
        priority = 0
        
        # Severity mapping
        severity_scores = {
            "critical": 3, "high": 2, "warning": 1, "info": 0
        }
        priority += severity_scores.get(labels.get("severity", "").lower(), 0)
        
        # Business impact keywords
        business_critical = ["prod", "production", "critical", "payment", "auth"]
        text_to_check = f"{labels} {annotations}".lower()
        if any(keyword in text_to_check for keyword in business_critical):
            priority += 1
            
        # Service type boost
        if any(service in text_to_check for service in ["database", "mongodb", "mysql", "postgres"]):
            priority += 1
            
        return min(priority, 3)  # Cap at 3
    
    def _get_specialized_prompt(self, alertname: str, labels: Dict[str, str]) -> str:
        """💡 Get specialized prompt based on alert type"""
        alert_lower = alertname.lower()
        
        if "mongodb" in alert_lower or "mongo" in alert_lower:
            return "Ты эксперт по MongoDB в production среде. Сосредоточься на диагностике базы данных, репликации, производительности и операционных аспектах."
        elif "disk" in alert_lower or "space" in alert_lower:
            return "Ты системный администратор. Анализируй проблемы с дисковым пространством, файловой системой и возможными причинами роста."
        elif "cpu" in alert_lower or "load" in alert_lower:
            return "Ты эксперт по производительности серверов. Фокусируйся на CPU нагрузке, процессах и оптимизации производительности."
        elif "memory" in alert_lower or "ram" in alert_lower:
            return "Ты специалист по управлению памятью. Анализируй использование RAM, возможные утечки памяти и оптимизацию."
        elif "network" in alert_lower or "connection" in alert_lower:
            return "Ты сетевой инженер. Диагностируй сетевые проблемы, подключения и пропускную способность."
        else:
            return "Ты опытный DevOps инженер. Предоставь общие рекомендации по диагностике и решению проблемы."
    
    async def _handle_alert_resolution(self, alert_data: Dict[str, str]) -> Dict[str, Any]:
        """🔄 Handle alert resolution"""
        labels = alert_data.get("labels", {})
        alertname = labels.get("alertname", "Unknown Alert")
        instance = labels.get("instance", "unknown")
        
        # Use the new formatter for resolved messages
        resolved_message = AlertMessageFormatter.format_alert_message(
            alertname=alertname,
            instance=instance,
            severity="info",
            priority=0,
            labels=labels,
            annotations={},
            llm_response="",
            time_context="",
            status="resolved"
        )
        
        return {
            "success": True,
            "message": resolved_message,
            "action": "resolved",
            "alert_type": alertname,
            "instance": instance
        }


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
    title="SEED Agent v5",
    description="Universal LLM-powered Alert Processing System",
    version="5.0.0",
    lifespan=lifespan
)


@app.post("/alert")
async def receive_alert(alert_payload: Dict[str, Any]):
    """Receive and process alert from Alertmanager"""
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")
    
    try:
        # Handle Alertmanager format: {"alerts": [...]}
        alerts = alert_payload.get("alerts", [])
        if not alerts:
            # Fallback: single alert format
            alerts = [alert_payload]
        
        results = []
        for alert in alerts:
            result = await seed_agent.process_alert(alert)
            results.append(result)
        
        # Return result of first alert
        if results:
            first_result = results[0]
            return JSONResponse(content=first_result, status_code=200 if first_result.get("success") else 422)
        else:
            return JSONResponse(content={"success": False, "error": "No alerts to process"}, status_code=400)
            
    except Exception as e:
        logger.error(f"Alert processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not seed_agent or not seed_agent.is_running:
        raise HTTPException(status_code=503, detail="SEED Agent not ready")
    
    try:
        # Check Redis health
        redis_stats = seed_agent.redis_throttler.get_stats()
        
        health = {
            "status": "healthy",
            "version": "5.0.0",
            "environment": seed_agent.config.get("environment", "unknown"),
            "services": {
                "rabbitmq": True,  # If we're running, RabbitMQ is connected
                "redis": redis_stats["redis_connected"],
                "llm": seed_agent.llm_client.enabled
            },
            "redis_stats": redis_stats
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
        f'seed_agent_info{{version="5.0.0",environment="{seed_agent.config.get("environment", "unknown")}"}} 1',
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
        "llm": {
            "enabled": seed_agent.llm_client.enabled,
            "provider": "GigaChat"
        },
        "notifications": {
            "mattermost_enabled": seed_agent.config.notification_config.get("mattermost", {}).get("enabled", False),
            "slack_enabled": seed_agent.config.notification_config.get("slack", {}).get("enabled", False),
            "email_enabled": seed_agent.config.notification_config.get("email", {}).get("enabled", False)
        }
    }
    
    return JSONResponse(content=config_summary)


@app.get("/llm/selftest")
async def llm_selftest():
    """LLM diagnostics endpoint"""
    import os
    
    def check_env_var(key):
        value = os.getenv(key)
        return {
            "present": bool(value),
            "length": len(value) if value else 0,
            "value": value[:8] + "..." if value and len(value) > 8 else value if value else None
        }
    
    env_vars = {}
    for key in ["GIGACHAT_CLIENT_ID", "GIGACHAT_CLIENT_SECRET", "GIGACHAT_OAUTH_URL", "GIGACHAT_API_URL", "GIGACHAT_MODEL", "GIGACHAT_SCOPE", "GIGACHAT_VERIFY_SSL", "GIGACHAT_TOKEN_CACHE"]:
        env_vars[key] = check_env_var(key)
    
    # Check config file values
    config_file_path = Path("seed.yaml").resolve()
    config_file_exists = config_file_path.exists()
    
    result = {
        "llm_client_enabled": seed_agent.llm_client.enabled if seed_agent else False,
        "gigachat_instance": seed_agent.llm_client.gigachat is not None if seed_agent else False,
        "gigachat_enabled": seed_agent.llm_client.gigachat.enabled if seed_agent and seed_agent.llm_client.gigachat else False,
        "env_vars": env_vars,
        "config_file": {
            "path": str(config_file_path),
            "exists": config_file_exists
        },
        "working_directory": str(Path.cwd())
    }
    
    return result


@app.post("/config/reload")
async def reload_config():
    """Reload configuration"""
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")
    
    try:
        # Reload configuration
        seed_agent.config.reload()
        logger.info("Configuration reloaded successfully")
        
        # Recreate LLM client with new config
        from core.llm import LLMClient
        seed_agent.llm_client = LLMClient(seed_agent.config)
        logger.info("LLM client recreated")
        
        # Reinitialize notification manager
        await seed_agent.notification_manager.initialize()
        logger.info("Notification manager reinitialized")
        
        return {
            "success": True, 
            "message": "Configuration reloaded and clients recreated",
            "llm_enabled": seed_agent.llm_client.enabled
        }
    except Exception as e:
        logger.error(f"Configuration reload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard")
async def dashboard():
    """Live dashboard with system status"""
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")
    
    try:
        import psutil
        import datetime
        import socket
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network info
        hostname = socket.getfqdn()
        
        # Redis stats
        redis_stats = seed_agent.redis_throttler.get_stats()
        
        # LLM health
        llm_health = {
            "enabled": seed_agent.llm_client.enabled,
            "provider": "GigaChat"
        }
        
        dashboard_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "system": {
                "hostname": hostname,
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": round(disk.used / disk.total * 100, 1)
                }
            },
            "agent": {
                "version": "5.0.0",
                "status": "running" if seed_agent.is_running else "stopped",
                "environment": seed_agent.config.get("environment", "unknown"),
                "uptime_seconds": int((datetime.datetime.now() - seed_agent.start_time).total_seconds()) if hasattr(seed_agent, 'start_time') else 0
            },
            "services": {
                "rabbitmq": True,
                "redis": redis_stats["redis_connected"],
                "llm": llm_health["enabled"]
            },
            "redis": redis_stats,
            "llm": llm_health,
            "alerts": {
                "throttled_count": redis_stats.get("suppressed_count", 0),
                "universal_processing": True
            }
        }
        
        return JSONResponse(content=dashboard_data)
        
    except ImportError:
        # Fallback without psutil
        return JSONResponse(content={
            "error": "Install psutil for full system metrics: pip install psutil",
            "basic_status": {
                "agent_running": seed_agent.is_running,
                "redis_connected": seed_agent.redis_throttler.get_stats()["redis_connected"]
            }
        })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/test")
async def test_alerts():
    """Get list of available test alerts"""
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")
    
    hostname = socket.getfqdn()
    
    # Sample test alerts for universal processing
    test_alerts = [
        {
            "name": "Сервер MongoDB не запущен",
            "severity": "critical",
            "type": "database",
            "curl_command": f'''curl -X POST http://{hostname}:8080/alert -H "Content-Type: application/json" -d '{{"alerts":[{{"labels":{{"alertname":"Сервер MongoDB не запущен","instance":"{hostname}","severity":"critical"}},"annotations":{{"summary":"MongoDB недоступен"}},"status":"firing"}}]}}\'''',
            "description": "Test MongoDB availability alert with LLM analysis"
        },
        {
            "name": "DiskSpaceCritical",
            "severity": "critical", 
            "type": "system",
            "curl_command": f'''curl -X POST http://{hostname}:8080/alert -H "Content-Type: application/json" -d '{{"alerts":[{{"labels":{{"alertname":"DiskSpaceCritical","instance":"{hostname}","severity":"critical"}},"annotations":{{"summary":"Критически мало места на диске"}},"status":"firing"}}]}}\'''',
            "description": "Test disk space alert with LLM recommendations"
        },
        {
            "name": "HighCPULoad",
            "severity": "warning",
            "type": "performance", 
            "curl_command": f'''curl -X POST http://{hostname}:8080/alert -H "Content-Type: application/json" -d '{{"alerts":[{{"labels":{{"alertname":"HighCPULoad","instance":"{hostname}","severity":"warning"}},"annotations":{{"summary":"Высокая нагрузка на CPU"}},"status":"firing"}}]}}\'''',
            "description": "Test CPU performance alert with specialized analysis"
        }
    ]
    
    return JSONResponse(content={
        "message": "🚀 SEED Agent v5 - Universal LLM Processing",
        "note": "All alerts are processed universally without routing configuration",
        "test_alerts": test_alerts,
        "total_count": len(test_alerts)
    })


SEVERITY_MAP = {
    # Zabbix standard severities
    "disaster": "critical",
    "high": "high", 
    "average": "warning",
    "warning": "warning",
    "information": "info",
    "not classified": "info",
    
    # Additional mappings for different Zabbix versions/configs
    "critical": "critical",
    "major": "high",
    "minor": "warning",
    "info": "info",
    "low": "info",
    
    # Russian translations if they come from Zabbix
    "критическая": "critical",
    "высокая": "high",
    "средняя": "warning",
    "низкая": "info",
    "информационная": "info",
}

def _parse_text_alert(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Поддержка Script media type (subject/message).
    Сначала пытается распарсить JSON из message, потом текстовый парсинг
    """
    subject = (payload.get("subject") or payload.get("Subject") or "").strip()
    message = (payload.get("message") or payload.get("Message") or "").strip()

    # Отладочное логирование
    logger.info(f"[_parse_text_alert] subject: '{subject}'")
    logger.info(f"[_parse_text_alert] message: '{message}'")
    logger.info(f"[_parse_text_alert] message starts with {{: {message.startswith('{')}")
    logger.info(f"[_parse_text_alert] message ends with }}: {message.endswith('}')}")

    # Попытка 1: Если message содержит JSON между #SEED-JSON# тегами
    json_match = re.search(r'#SEED-JSON#\s*(\{.*?\})\s*#/SEED-JSON#', message, re.DOTALL)
    if json_match:
        try:
            import json
            json_data = json.loads(json_match.group(1))
            logger.info(f"[_parse_text_alert] Found SEED-JSON: {json_data}")
            
            # Извлекаем данные из корпоративной JSON структуры
            e = json_data.get("event", {}) or {}
            trg = json_data.get("trigger", {}) or {}
            h = json_data.get("host", {}) or {}
            items = json_data.get("items", [])
            
            logger.info(f"[_parse_text_alert] host from SEED-JSON: {h}")
            logger.info(f"[_parse_text_alert] trigger from SEED-JSON: {trg}")
            
            # Определяем статус
            event_value = str(e.get("value", "1"))
            severity_text = e.get("severity", "information").lower()
            if severity_text == "resolved":
                status = "resolved"
            else:
                status = "firing" if event_value == "1" else "resolved"
            
            # Маппинг severity
            severity = SEVERITY_MAP.get(severity_text, "info")
            logger.info(f"[ZABBIX] Severity mapping: '{severity_text}' -> '{severity}'")
            
            # Хост и порт
            host = h.get("name") or h.get("host", "unknown")
            
            # Пытаемся извлечь порт из items или trigger name
            port = "0"
            for item in items:
                if item and item.get("name"):
                    port_match = re.search(r':(\d{2,5})\b', item["name"])
                    if port_match:
                        port = port_match.group(1)
                        break
            
            if port == "0":  # Если не нашли в items, ищем в trigger name
                port_match = re.search(r':(\d{2,5})\b', trg.get("name", ""))
                if port_match:
                    port = port_match.group(1)
            
            instance = f"{host}:{port}"
            
            logger.info(f"[_parse_text_alert] Returning SEED-JSON result: host={host}, port={port}, status={status}")
            
            return {
                "status": status,
                "labels": {
                    "alertname": trg.get("name", "ZabbixAlert"),
                    "instance": instance,
                    "severity": severity,
                    "job": "zabbix",
                    "host": host,
                    "trigger_id": trg.get("id", ""),
                    "event_id": e.get("id", ""),
                    "host_ip": h.get("ip", "")
                },
                "annotations": {
                    "summary": trg.get("description") or trg.get("name") or subject or "Zabbix Alert",
                    "description": f"Event ID: {e.get('id', 'n/a')}, Host IP: {h.get('ip', 'n/a')}",
                    "trigger_url": trg.get("url", ""),
                    "event_age": e.get("age", "")
                }
            }
        except Exception as ex:
            logger.info(f"[_parse_text_alert] SEED-JSON parsing failed: {ex}")
            pass
    
    # Попытка 2: Обычный JSON в начале/конце message
    elif message.startswith('{') and message.endswith('}'):
        try:
            import json
            json_data = json.loads(message)
            logger.info(f"[_parse_text_alert] JSON parsed successfully: {json_data}")
            
            # Извлекаем данные из JSON структуры
            e = json_data.get("event", {}) or {}
            trg = json_data.get("trigger", {}) or {}
            h = json_data.get("host", {}) or {}
            it = json_data.get("item", {}) or {}
            
            logger.info(f"[_parse_text_alert] host from JSON: {h}")
            logger.info(f"[_parse_text_alert] trigger from JSON: {trg}")
            
            status = "firing" if str(e.get("value", "1")) == "1" else "resolved"
            severity = SEVERITY_MAP.get((trg.get("severity_text") or "information").lower(), "info")
            host = h.get("name", "unknown")
            port = it.get("port", "0")
            instance = f"{host}:{port}"
            
            logger.info(f"[_parse_text_alert] Returning JSON-based result: host={host}, port={port}")
            
            return {
                "status": status,
                "labels": {
                    "alertname": trg.get("name", "ZabbixAlert"),
                    "instance": instance,
                    "severity": severity,
                    "job": "zabbix",
                    "host": host,
                    "trigger_id": trg.get("id", ""),
                    "event_id": e.get("id", ""),
                    "host_ip": h.get("ip", "")
                },
                "annotations": {
                    "summary": trg.get("description") or trg.get("name") or subject or "Zabbix Alert",
                    "description": f"Item: {it.get('name','n/a')}, Value: {it.get('lastvalue','n/a')}"
                }
            }
        except Exception as ex:
            # Если JSON парсинг не удался - продолжаем с текстовым парсингом
            logger.info(f"[_parse_text_alert] JSON parsing failed: {ex}")
            pass

    # Попытка 2: Текстовый парсинг (оригинальная логика)
    logger.info("[_parse_text_alert] Falling back to text parsing")
    
    # Ищем хост в тексте, но не используем "Problem:" как хост
    host = "unknown"
    alertname = subject or "ZabbixAlert"
    
    # Ищем паттерн хоста в subject (что-то с дефисами и точками, но не "Problem")
    if subject:
        # Убираем "Problem:" в начале
        clean_subject = re.sub(r"^Problem:\s*", "", subject)
        logger.info(f"[_parse_text_alert] clean_subject after removing 'Problem:': '{clean_subject}'")
        
        # Ищем хост-паттерн
        host_match = re.search(r"([a-z0-9][\w\-\.]{3,})", clean_subject, re.IGNORECASE)
        if host_match:
            potential_host = host_match.group(1)
            logger.info(f"[_parse_text_alert] potential_host found: '{potential_host}'")
            # Убеждаемся что это не часть описания проблемы
            if not any(word in potential_host.lower() for word in ['процессов', 'mongodb', 'нет', 'тест']):
                host = potential_host
                logger.info(f"[_parse_text_alert] host accepted: '{host}'")
            else:
                logger.info(f"[_parse_text_alert] host rejected (contains problem words)")

    # Серьёзность из текста
    whole_text = f"{subject}\n{message}".upper()
    if "DISASTER" in whole_text or "CRITICAL" in whole_text:
        severity = "critical"
    elif "HIGH" in whole_text:
        severity = "high"
    elif "AVERAGE" in whole_text or "WARNING" in whole_text:
        severity = "warning"
    else:
        severity = "info"

    # Порт из текста (если есть)
    port = None
    port_match = re.search(r":(\d{2,5})\b", f"{subject} {message}")
    if port_match:
        port = port_match.group(1)
        logger.info(f"[_parse_text_alert] port found: '{port}'")
    
    instance = f"{host}:{port}" if port else host
    logger.info(f"[_parse_text_alert] Final text parsing result: host={host}, port={port}, instance={instance}")

    return {
        "status": "firing",
        "labels": {
            "alertname": alertname,
            "instance": instance,
            "severity": severity,
            "job": "zabbix",
            "host": host,
            "host_ip": payload.get("host_ip", "")
        },
        "annotations": {
            "summary": subject or "Zabbix Alert",
            "description": message or subject or "Zabbix Alert"
        }
    }

@app.post("/zabbix")
async def zabbix_webhook(payload: Dict[str, Any]):
    if not seed_agent:
        raise HTTPException(status_code=503, detail="SEED Agent not initialized")

    # Лог входящего — удобно для отладки
    logger.info(f"[/zabbix] got payload: {payload}")

    alert = None

    # 1) «Правильный» JSON от Webhook media type: {event, trigger, host, item}
    if isinstance(payload, dict) and all(k in payload for k in ("event", "trigger", "host")):
        e   = payload.get("event", {}) or {}
        trg = payload.get("trigger", {}) or {}
        h   = payload.get("host", {}) or {}
        it  = payload.get("item", {}) or {}

        status = "firing" if str(e.get("value", "1")) == "1" else "resolved"
        severity = SEVERITY_MAP.get((trg.get("severity_text") or "information").lower(), "info")
        instance = f"{h.get('name','unknown')}:{it.get('port','0')}"

        # Enrich annotations with Zabbix context for better LLM analysis
        annotations = {
            "summary": trg.get("description") or trg.get("name") or "Zabbix Alert",
            "description": f"Item: {it.get('name','n/a')}, Value: {it.get('lastvalue','n/a')}",
            # Add enriched Zabbix attributes for LLM context
            "host_ip": h.get("ip", ""),
            "host_groups": h.get("groups", ""),
            "trigger_tags": trg.get("tags", ""),
            "item_key": it.get("key", ""),
            "item_name": it.get("name", ""),
            "item_lastvalue": it.get("lastvalue", ""),
            "event_id": e.get("id", ""),
            "event_date": e.get("date", ""),
            "event_time": e.get("time", ""),
        }
        
        alert = {
            "status": status,
            "labels": {
                "alertname": trg.get("name", "ZabbixAlert"),
                "instance": instance,
                "severity": severity,
                "job": "zabbix",
                "host": h.get("name", "unknown"),
                "trigger_id": trg.get("id", ""),
                "event_id": e.get("id", ""),
                "host_ip": h.get("ip", "")
            },
            "annotations": annotations
        }

    # 2) «Скриптовый» формат (Script media type): {sendto, subject, message}
    elif any(k in payload for k in ("subject", "Subject", "message", "Message")):
        alert = _parse_text_alert(payload)

    # 3) Ничего не распознали — пусть будет дефолт
    else:
        alert = {
            "status": "firing",
            "labels": {
                "alertname": payload.get("alertname", "ZabbixAlert"),
                "instance": payload.get("instance", "unknown:0"),
                "severity": payload.get("severity", "info"),
                "job": "zabbix",
                "host": payload.get("host", "unknown")
            },
            "annotations": {
                "summary": payload.get("summary", "Zabbix Alert"),
                "description": payload.get("description", "No description")
            }
        }

    # ⛔️ ВАЖНО: передаём ВНУТРЬ ровно ОДИН alert-объект (без обёртки {"alerts":[...]})
    result = await seed_agent.process_alert(alert)
    return JSONResponse(content=result, status_code=200 if result.get("success") else 422)


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
        if debug:
            # In debug mode, use module string for reload functionality
            uvicorn.run(
                "seed-agent:app",
                host=host,
                port=port,
                log_level=log_level,
                reload=True,
                access_log=True
            )
        else:
            # In production mode, pass app object directly
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level=log_level,
                access_log=True
            )
        
    except Exception as e:
        logger.error(f"Failed to start SEED Agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()