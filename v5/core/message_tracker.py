# -*- coding: utf-8 -*-
"""
Message Tracker для отслеживания и обновления отправленных сообщений
Хранит mapping alert_id -> message_id для возможности редактирования
"""
import json
import hashlib
import logging
from typing import Dict, Optional, Any
from .redis_throttle import RedisThrottler

logger = logging.getLogger(__name__)

class MessageTracker:
    """Отслеживание отправленных сообщений для возможности редактирования"""
    
    def __init__(self, throttler: RedisThrottler):
        self.throttler = throttler
        self.redis_client = throttler.redis_client
        
    def _get_alert_key(self, alert_data: Dict[str, Any]) -> str:
        """Создаёт уникальный ключ для алерта на основе labels"""
        labels = alert_data.get("labels", {})
        # Используем alertname + instance для уникальности
        key_parts = [
            labels.get("alertname", "unknown"),
            labels.get("instance", "unknown"),
            labels.get("job", "unknown")
        ]
        key_string = "|".join(key_parts)
        # Создаём короткий hash для использования в Redis
        return f"msg:{hashlib.md5(key_string.encode()).hexdigest()[:16]}"
    
    def store_message_info(self, alert_data: Dict[str, Any], channel: str, message_id: str, 
                          message_text: str, severity: str) -> None:
        """Сохраняет информацию об отправленном сообщении"""
        if not self.redis_client:
            return
            
        alert_key = self._get_alert_key(alert_data)
        message_info = {
            "channel": channel,
            "message_id": message_id,
            "message_text": message_text,
            "severity": severity,
            "status": alert_data.get("status", "firing"),
            "timestamp": alert_data.get("startsAt", ""),
            "labels": alert_data.get("labels", {}),
            "annotations": alert_data.get("annotations", {})
        }
        
        try:
            # Храним 24 часа (достаточно для большинства алертов)
            self.redis_client.setex(
                alert_key, 
                86400,  # 24 hours
                json.dumps(message_info, ensure_ascii=False)
            )
            logger.debug(f"Stored message info for {alert_key}: {message_id}")
        except Exception as e:
            logger.error(f"Failed to store message info: {e}")
    
    def get_message_info(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Получает информацию о ранее отправленном сообщении"""
        if not self.redis_client:
            return None
            
        alert_key = self._get_alert_key(alert_data)
        
        try:
            stored_data = self.redis_client.get(alert_key)
            if stored_data:
                return json.loads(stored_data)
        except Exception as e:
            logger.error(f"Failed to get message info: {e}")
        
        return None
    
    def should_update_message(self, alert_data: Dict[str, Any]) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Определяет, нужно ли обновить существующее сообщение
        Возвращает (should_update: bool, message_info: dict)
        """
        current_status = alert_data.get("status", "firing")
        
        # Если алерт resolved, ищем существующее сообщение для обновления
        if current_status == "resolved":
            message_info = self.get_message_info(alert_data)
            if message_info and message_info.get("status") == "firing":
                return True, message_info
        
        return False, None
    
    def cleanup_resolved_message(self, alert_data: Dict[str, Any]) -> None:
        """Удаляет информацию о resolved сообщении из Redis"""
        if not self.redis_client:
            return
            
        alert_key = self._get_alert_key(alert_data)
        try:
            self.redis_client.delete(alert_key)
            logger.debug(f"Cleaned up message info for {alert_key}")
        except Exception as e:
            logger.error(f"Failed to cleanup message info: {e}")