# -*- coding: utf-8 -*-
"""
Enhanced SEED Agent v5 Notification System with Message Editing
Добавляет возможность редактирования сообщений при resolved alerts
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
import httpx
from .config import Config
from .formatter import AlertMessageFormatter
from .message_tracker import MessageTracker

logger = logging.getLogger(__name__)


class EnhancedNotificationManager:
    """Расширенный менеджер уведомлений с поддержкой редактирования сообщений"""
    
    def __init__(self, config: Config, message_tracker: MessageTracker):
        self.config = config
        self.notification_config = config.notification_config
        self.message_tracker = message_tracker
        
        # Initialize backend configurations
        self.mattermost_config = self.notification_config.get("mattermost", {})
        self.slack_config = self.notification_config.get("slack", {})
        self.email_config = self.notification_config.get("email", {})
    
    async def send_mattermost_message(self, text: str, channel: Optional[str] = None, 
                                    severity: str = "info") -> Optional[str]:
        """Send message to Mattermost and return message_id for future editing"""
        if not self.mattermost_config.get("enabled") or not self.mattermost_config.get("webhook_url"):
            logger.debug("Mattermost not configured, skipping notification")
            return None
        
        channel = channel or self.mattermost_config.get("channel", "alerts")
        
        payload = {
            "username": self.mattermost_config.get("username", "🌌 SEED"),
            "icon_emoji": self.mattermost_config.get("icon_emoji", ":crystal_ball:"),
            "attachments": [{
                "color": AlertMessageFormatter.get_severity_color(severity),
                "text": text,
                "mrkdwn_in": ["text"]
            }]
        }
        if self.mattermost_config.get("channel"):
            payload["channel"] = self.mattermost_config["channel"]
        
        try:
            timeout = httpx.Timeout(10.0)
            verify_ssl = self.mattermost_config.get("verify_ssl", True)
            
            async with httpx.AsyncClient(timeout=timeout, verify=verify_ssl) as client:
                response = await client.post(
                    self.mattermost_config["webhook_url"],
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Mattermost message sent successfully to {channel}")
                    # TODO: Mattermost webhooks не возвращают message_id
                    # Для полной реализации нужен Bot Token и Posts API
                    return "webhook_message"
                else:
                    logger.error(f"❌ Mattermost API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to send Mattermost message: {e}")
            return None
    
    def _create_resolved_message(self, original_message: str, alert_data: Dict[str, Any], 
                               llm_result: Dict[str, Any]) -> str:
        """Создаёт текст resolved сообщения на основе оригинального"""
        labels = alert_data.get("labels", {})
        alertname = labels.get("alertname", "Unknown Alert")
        instance = labels.get("instance", "unknown")
        
        # Заменяем эмодзи на resolved версию
        resolved_emoji = "✅"
        if "💎🔥" in original_message:
            resolved_emoji = "💎✅"  # Critical resolved
        elif "⚔️" in original_message:
            resolved_emoji = "⚔️✅"  # High resolved  
        elif "🛡️" in original_message:
            resolved_emoji = "🛡️✅"  # Warning resolved
        elif "✨" in original_message:
            resolved_emoji = "✨✅"  # Info resolved
        
        # Создаём resolved версию сообщения
        resolved_message = f"""🌌 SEED
{resolved_emoji} {alertname} (RESOLVED)

📍 Сервер: {instance}
⏰ Resolved: {alert_data.get('endsAt', 'just now')}
📝 Описание: {alert_data.get('annotations', {}).get('summary', 'Alert resolved')}

✅ **Статус: РАЗРЕШЕНО**

🔍 Рекомендации:
• Проверь что проблема действительно устранена
• Убедись что система работает в штатном режиме
• Мониторь метрики в течение следующих 15-30 минут

📊 **Оригинальная проблема:**
{original_message.split('🔍 Возможные проблемы:')[1] if '🔍 Возможные проблемы:' in original_message else 'См. выше'}

— Powered by 🌌 SEED ✅"""
        
        return resolved_message
    
    async def send_alert_notification(self, alert_data: Dict[str, Any], llm_result: Dict[str, Any]):
        """Отправляет уведомление или обновляет существующее при resolved"""
        labels = alert_data.get("labels", {})
        annotations = alert_data.get("annotations", {})
        
        alertname = labels.get("alertname", "Unknown Alert") 
        instance = llm_result.get("instance", "unknown")
        severity = llm_result.get("severity", "unknown")
        status = alert_data.get("status", "firing")
        
        # Проверяем, нужно ли обновить существующее сообщение
        should_update, message_info = self.message_tracker.should_update_message(alert_data)
        
        if should_update and message_info:
            # Обновляем существующее сообщение для resolved alert
            logger.info(f"🔄 Updating existing message for resolved alert: {alertname}")
            
            # Создаём resolved версию сообщения
            resolved_message = self._create_resolved_message(
                message_info.get("message_text", ""), alert_data, llm_result
            )
            
            # TODO: Реальное обновление сообщения через API
            # Пока что отправляем новое сообщение с отметкой об обновлении
            update_message = f"🔄 **UPDATE:** {resolved_message}"
            
            # Отправляем в тот же канал
            channel = message_info.get("channel", "alerts")
            message_id = await self.send_mattermost_message(update_message, channel, "info")
            
            # Очищаем старую запись
            self.message_tracker.cleanup_resolved_message(alert_data)
            
            logger.info(f"✅ Updated message for resolved alert: {alertname}")
            return
        
        # Обычная отправка нового сообщения
        notification_message = llm_result.get("message") or (
            f"*{alertname}* on `{instance}` (severity: {severity})"
        )
        
        # Отправляем в Mattermost
        if self.mattermost_config.get("enabled"):
            channel = self.mattermost_config.get("channel", "alerts")
            message_id = await self.send_mattermost_message(notification_message, channel, severity)
            
            if message_id and status == "firing":
                # Сохраняем информацию о сообщении для возможного обновления
                self.message_tracker.store_message_info(
                    alert_data, channel, message_id, notification_message, severity
                )
        
        logger.info(f"📤 Alert notification sent for {alertname}")