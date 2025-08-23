# -*- coding: utf-8 -*-
"""
SEED Agent v4 Notification System
Centralized notification handling with proper configuration management
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
import httpx
from .config import Config
from .formatter import AlertMessageFormatter

logger = logging.getLogger(__name__)


class NotificationManager:
    """Unified notification manager using centralized configuration"""
    
    def __init__(self, config: Config):
        self.config = config
        self.notification_config = config.notification_config
        
        # Initialize backend configurations
        self.mattermost_config = self.notification_config.get("mattermost", {})
        self.slack_config = self.notification_config.get("slack", {})
        self.email_config = self.notification_config.get("email", {})
    
    async def initialize(self):
        """Initialize notification manager"""
        enabled_channels = []
        
        if self.mattermost_config.get("enabled") and self.mattermost_config.get("webhook_url"):
            enabled_channels.append("Mattermost")
        
        if self.slack_config.get("enabled") and self.slack_config.get("webhook_url"):
            enabled_channels.append("Slack")
        
        if self.email_config.get("enabled") and self._validate_email_config():
            enabled_channels.append("Email")
        
        if enabled_channels:
            logger.info(f"Notification channels enabled: {', '.join(enabled_channels)}")
        else:
            logger.warning("No notification channels configured")
    
    async def close(self):
        """Cleanup notification manager"""
        pass
    
    def _validate_email_config(self) -> bool:
        """Validate email configuration"""
        required_fields = ["smtp_host", "smtp_user", "smtp_password", "from_email", "to_emails"]
        return all(self.email_config.get(field) for field in required_fields)
    
    async def send_mattermost_message(self, text: str, channel: Optional[str] = None, severity: str = "info") -> bool:
        """Send message to Mattermost with color attachments"""
        if not self.mattermost_config.get("enabled") or not self.mattermost_config.get("webhook_url"):
            logger.debug("Mattermost not configured, skipping notification")
            return False
        
        channel = channel or self.mattermost_config.get("channel", "alerts")
        
        # Создаем payload с цветными attachments
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
                    return True
                else:
                    # Get response body for detailed error info
                    error_body = response.text
                    logger.error(f"❌ Mattermost API error {response.status_code}: {error_body}")
                    logger.error(f"   Webhook URL: {self.mattermost_config['webhook_url'][:50]}...")
                    logger.error(f"   Payload size: {len(str(payload))} chars")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Mattermost message: {e}")
            return False
    
    async def send_slack_message(self, text: str, channel: Optional[str] = None) -> bool:
        """Send message to Slack"""
        if not self.slack_config.get("enabled") or not self.slack_config.get("webhook_url"):
            logger.debug("Slack not configured, skipping notification")
            return False
        
        channel = channel or self.slack_config.get("channel", "#alerts")
        
        payload = {
            "text": text,
            "channel": channel,
            "username": self.slack_config.get("username", "SEED-Agent")
        }
        
        try:
            timeout = httpx.Timeout(10.0)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.slack_config["webhook_url"],
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.debug(f"Slack message sent to {channel}")
                    return True
                else:
                    logger.error(f"Slack API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    async def send_alert_notification(self, alert_data: Dict[str, Any], llm_result: Dict[str, Any]):
        """Send alert notification through all enabled channels (SEED Agent v5)"""
        # Extract alert information from new format
        labels = alert_data.get("labels", {})
        annotations = alert_data.get("annotations", {})
        
        alertname = labels.get("alertname", "Unknown Alert") 
        instance = llm_result.get("instance", "unknown")
        severity = llm_result.get("severity", "unknown")
        success = llm_result.get("success", False)
        
        # Use the pre-formatted message produced upstream (SeedAgent.process_alert_with_llm)
        notification_message = llm_result.get("message") or (
            f"*{alertname}* on `{instance}` (severity: {severity})"
        )
        
        # Send to all enabled channels
        sent_channels = []
        
        # Debug info
        logger.info(f"📤 Sending notification for {alertname} to enabled channels...")
        
        # Try Mattermost
        if self.mattermost_config.get("enabled"):
            logger.debug(f"   Trying Mattermost (webhook: {self.mattermost_config.get('webhook_url', 'not set')[:50]}...)")
            if await self.send_mattermost_message(notification_message, severity=severity):
                sent_channels.append("Mattermost")
        else:
            logger.debug("   Mattermost disabled in config")
        
        # Try Slack
        if self.slack_config.get("enabled"):
            logger.debug(f"   Trying Slack (webhook: {self.slack_config.get('webhook_url', 'not set')[:50]}...)")
            if await self.send_slack_message(notification_message):
                sent_channels.append("Slack")
        else:
            logger.debug("   Slack disabled in config")
        
        if sent_channels:
            logger.info(f"🎉 Alert notification sent to: {', '.join(sent_channels)}")
        else:
            logger.warning(f"⚠️ Failed to send alert notification for {alertname} - no channels succeeded")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification manager statistics"""
        return {
            "channels": {
                "mattermost": {
                    "enabled": self.mattermost_config.get("enabled", False),
                    "configured": bool(self.mattermost_config.get("webhook_url"))
                },
                "slack": {
                    "enabled": self.slack_config.get("enabled", False),
                    "configured": bool(self.slack_config.get("webhook_url"))
                },
                "email": {
                    "enabled": self.email_config.get("enabled", False),
                    "configured": self._validate_email_config()
                }
            }
        }


# Legacy compatibility functions for backward compatibility with v3 code
def log(message: str):
    """Legacy log function for compatibility"""
    logger.info(message)


async def send_mm(message: str):
    """Legacy Mattermost send function for compatibility"""
    # This would need a global notification manager instance
    logger.info(f"Legacy MM call: {message}")