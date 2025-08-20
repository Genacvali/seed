# -*- coding: utf-8 -*-
"""
SEED Agent Notification System
Unified notification handling with multiple backends
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Notifier:
    """Unified notification system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup structured logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self.logger.debug(message, extra=extra or {})
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self.logger.info(message, extra=extra or {})
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self.logger.warning(message, extra=extra or {})
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log error message"""
        self.logger.error(message, extra=extra or {})
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log critical message"""
        self.logger.critical(message, extra=extra or {})
    
    async def send_notification(self, message: str, title: Optional[str] = None, 
                              priority: str = "normal") -> bool:
        """Send notification through configured backends"""
        success = False
        
        # Try Mattermost first
        if self._is_enabled("mattermost"):
            try:
                if await self._send_mattermost(message, title, priority):
                    success = True
                    self.debug("Notification sent via Mattermost")
            except Exception as e:
                self.error(f"Mattermost notification failed: {e}")
        
        # Try Slack as fallback
        if not success and self._is_enabled("slack"):
            try:
                if await self._send_slack(message, title, priority):
                    success = True
                    self.debug("Notification sent via Slack")
            except Exception as e:
                self.error(f"Slack notification failed: {e}")
        
        # Try email as final fallback
        if not success and self._is_enabled("email"):
            try:
                if await self._send_email(message, title, priority):
                    success = True
                    self.debug("Notification sent via email")
            except Exception as e:
                self.error(f"Email notification failed: {e}")
        
        if not success:
            self.warning(f"Failed to send notification: {title or 'Untitled'}")
        
        return success
    
    def _is_enabled(self, backend: str) -> bool:
        """Check if notification backend is enabled"""
        backend_config = self.config.get(backend, {})
        return backend_config.get("enabled", False)
    
    async def _send_mattermost(self, message: str, title: Optional[str] = None, 
                             priority: str = "normal") -> bool:
        """Send notification to Mattermost"""
        config = self.config.get("mattermost", {})
        webhook_url = config.get("webhook_url")
        
        if not webhook_url:
            return False
        
        # Prepare payload
        payload = {
            "text": f"**{title}**\n{message}" if title else message,
            "channel": config.get("channel", "alerts"),
            "username": config.get("username", "SEED-Agent"),
            "icon_emoji": self._get_emoji_for_priority(priority)
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            return True
    
    async def _send_slack(self, message: str, title: Optional[str] = None, 
                        priority: str = "normal") -> bool:
        """Send notification to Slack"""
        config = self.config.get("slack", {})
        webhook_url = config.get("webhook_url")
        
        if not webhook_url:
            return False
        
        # Prepare payload
        payload = {
            "text": f"*{title}*\n{message}" if title else message,
            "channel": config.get("channel", "#alerts"),
            "username": config.get("username", "SEED-Agent"),
            "icon_emoji": self._get_emoji_for_priority(priority)
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            return True
    
    async def _send_email(self, message: str, title: Optional[str] = None, 
                        priority: str = "normal") -> bool:
        """Send notification via email"""
        config = self.config.get("email", {})
        
        smtp_host = config.get("smtp_host")
        smtp_port = config.get("smtp_port", 587)
        smtp_user = config.get("smtp_user")
        smtp_password = config.get("smtp_password")
        from_email = config.get("from_email")
        to_emails = config.get("to_emails", [])
        
        if not all([smtp_host, smtp_user, smtp_password, from_email, to_emails]):
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = f"[SEED Alert] {title or 'Notification'}"
        
        # Add priority header
        if priority in ["critical", "high"]:
            msg['X-Priority'] = '1'
            msg['Importance'] = 'High'
        
        # Add body
        body = f"{title}\n\n{message}" if title else message
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email (run in thread pool to avoid blocking)
        def send_email_sync():
            try:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                return True
            except Exception:
                return False
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, send_email_sync)
    
    def _get_emoji_for_priority(self, priority: str) -> str:
        """Get emoji based on alert priority"""
        emoji_map = {
            "critical": ":red_circle:",
            "high": ":orange_circle:", 
            "warning": ":yellow_circle:",
            "normal": ":blue_circle:",
            "low": ":green_circle:"
        }
        return emoji_map.get(priority, ":robot_face:")
    
    # Legacy compatibility methods
    def log(self, message: str):
        """Legacy log method for compatibility"""
        self.info(message)
    
    def send_mm(self, message: str):
        """Legacy Mattermost send method"""
        # This would need to be called from an async context
        # For now, just log the message
        self.info(f"MM: {message}")
        
    # Metrics and health
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return {
            "backends": {
                "mattermost": self._is_enabled("mattermost"),
                "slack": self._is_enabled("slack"),
                "email": self._is_enabled("email")
            },
            "timestamp": datetime.utcnow().isoformat()
        }


# Global notifier instance for backward compatibility
_global_notifier = None

def get_global_notifier() -> Notifier:
    """Get global notifier instance"""
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = Notifier()
    return _global_notifier

def log(message: str):
    """Legacy global log function"""
    get_global_notifier().info(message)

def send_mm(message: str):
    """Legacy global Mattermost function"""
    get_global_notifier().info(f"MM: {message}")
