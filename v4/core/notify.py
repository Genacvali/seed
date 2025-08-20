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
    
    async def send_mattermost_message(self, text: str, channel: Optional[str] = None) -> bool:
        """Send message to Mattermost"""
        if not self.mattermost_config.get("enabled") or not self.mattermost_config.get("webhook_url"):
            logger.debug("Mattermost not configured, skipping notification")
            return False
        
        channel = channel or self.mattermost_config.get("channel", "alerts")
        
        payload = {
            "text": text,
            "channel": channel,
            "username": self.mattermost_config.get("username", "SEED-Agent"),
            "icon_emoji": self.mattermost_config.get("icon_emoji", ":robot_face:")
        }
        
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
                    logger.debug(f"Mattermost message sent to {channel}")
                    return True
                else:
                    logger.error(f"Mattermost API error: {response.status_code} - {response.text}")
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
    
    async def send_alert_notification(self, alert_data: Dict[str, Any], plugin_result: Dict[str, Any]):
        """Send alert notification through all enabled channels"""
        # Extract alert information
        alertname = alert_data.get("alertname", "Unknown Alert")
        hostname = plugin_result.get("hostname", "unknown")
        plugin = plugin_result.get("plugin", "unknown")
        success = plugin_result.get("success", False)
        
        # Determine severity emoji
        severity = alert_data.get("labels", {}).get("severity", "warning")
        emoji_map = {
            "critical": "🔴",
            "high": "🟠", 
            "warning": "🟡",
            "info": "🔵"
        }
        emoji = emoji_map.get(severity, "⚠️")
        
        # Build notification message
        if success:
            status_icon = "✅"
            status_text = "Processed"
        else:
            status_icon = "❌"
            status_text = "Failed"
            
        message = f"{emoji} **{alertname}**\n"
        message += f"{status_icon} Status: {status_text}\n"
        message += f"🏠 Host: `{hostname}`\n"
        message += f"🔧 Plugin: `{plugin}`\n"
        
        if success:
            execution_time = plugin_result.get("execution_time", 0)
            message += f"⏱️ Execution: {execution_time:.2f}s\n"
            
            # Add plugin-specific details
            if plugin == "host_inventory":
                data = plugin_result.get("data", {})
                if "disk_usage" in data:
                    disk_info = data["disk_usage"]
                    if disk_info:
                        message += f"💾 Disk usage: {disk_info[0].get('used_percent', 0):.1f}%\n"
                
                if "cpu_usage_percent" in data:
                    cpu_usage = data["cpu_usage_percent"]
                    message += f"🖥️ CPU usage: {cpu_usage:.1f}%\n"
                
                if "memory_usage_gb" in data:
                    memory = data["memory_metrics"]
                    message += f"💾 Memory: {memory.get('used_percent', 0):.1f}%\n"
                    
            elif plugin == "mongo_hot":
                data = plugin_result.get("data", {})
                query_count = data.get("query_count", 0)
                message += f"🔍 Slow queries found: {query_count}\n"
        else:
            error = plugin_result.get("error", "Unknown error")
            message += f"❌ Error: {error}\n"
        
        # Add timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"🕐 Time: {timestamp}"
        
        # Send to all enabled channels
        sent_channels = []
        
        # Try Mattermost
        if await self.send_mattermost_message(message):
            sent_channels.append("Mattermost")
        
        # Try Slack
        if await self.send_slack_message(message):
            sent_channels.append("Slack")
        
        if sent_channels:
            logger.info(f"Alert notification sent to: {', '.join(sent_channels)}")
        else:
            logger.warning(f"Failed to send alert notification for {alertname}")
    
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