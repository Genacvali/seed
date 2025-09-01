#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Alertmanager integration for SEED Agent v6
Run this to poll Alertmanager and forward alerts to SEED Agent
"""

import os
import sys
import logging
import signal
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integration.alertmanager_client import AlertmanagerClient, AlertmanagerPoller

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/alertmanager-integration.log')
    ]
)
logger = logging.getLogger(__name__)

class AlertmanagerIntegration:
    """Main Alertmanager integration service"""
    
    def __init__(self):
        self.poller = None
        self.running = False
        
        # Load configuration from environment
        self.load_config()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_config(self):
        """Load configuration from environment variables"""
        # Load from seed.env if it exists
        env_file = Path("configs/seed.env")
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
        
        self.alertmanager_url = os.getenv('ALERTMANAGER_URL', 'https://alertmanager.sberdevices.ru')
        self.auth_token = os.getenv('ALERTMANAGER_TOKEN')
        self.verify_ssl = os.getenv('ALERTMANAGER_VERIFY_SSL', 'true').lower() == 'true'
        self.timeout = int(os.getenv('ALERTMANAGER_TIMEOUT', '30'))
        
        self.seed_agent_url = os.getenv('SEED_AGENT_URL', 'http://localhost:8080')
        
        self.polling_enabled = os.getenv('ALERTMANAGER_POLLING_ENABLED', 'true').lower() == 'true'
        self.polling_interval = int(os.getenv('ALERTMANAGER_POLLING_INTERVAL', '60'))
        
        logger.info(f"Configuration loaded:")
        logger.info(f"  Alertmanager URL: {self.alertmanager_url}")
        logger.info(f"  SEED Agent URL: {self.seed_agent_url}")
        logger.info(f"  Polling enabled: {self.polling_enabled}")
        logger.info(f"  Polling interval: {self.polling_interval}s")
        logger.info(f"  SSL verification: {self.verify_ssl}")
    
    def create_clients(self):
        """Create Alertmanager client and poller"""
        try:
            # Create Alertmanager client
            client = AlertmanagerClient(
                base_url=self.alertmanager_url,
                auth_token=self.auth_token,
                verify_ssl=self.verify_ssl,
                timeout=self.timeout
            )
            
            # Test connection
            if not client.health_check():
                logger.warning("Alertmanager health check failed, continuing anyway...")
            else:
                logger.info("✅ Alertmanager connection OK")
            
            # Create poller
            self.poller = AlertmanagerPoller(
                alertmanager_client=client,
                seed_agent_url=self.seed_agent_url,
                poll_interval=self.polling_interval
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create clients: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the integration service"""
        if not self.polling_enabled:
            logger.info("Alertmanager polling is disabled")
            return
        
        logger.info("🚀 Starting Alertmanager integration service")
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Create clients
        if not self.create_clients():
            logger.error("Failed to initialize clients")
            return False
        
        # Start polling
        self.running = True
        try:
            self.poller.start_polling()
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error(f"Service error: {e}")
        
        return True
    
    def stop(self):
        """Stop the integration service"""
        if self.poller:
            self.poller.stop_polling()
        self.running = False
        logger.info("Alertmanager integration service stopped")
    
    def test_connection(self):
        """Test connection to both Alertmanager and SEED Agent"""
        logger.info("🧪 Testing connections...")
        
        success = True
        
        # Test Alertmanager
        try:
            client = AlertmanagerClient(
                base_url=self.alertmanager_url,
                auth_token=self.auth_token,
                verify_ssl=self.verify_ssl,
                timeout=self.timeout
            )
            
            if client.health_check():
                logger.info("✅ Alertmanager connection OK")
            else:
                logger.warning("⚠️  Alertmanager health check failed")
                success = False
                
            # Try to fetch alerts
            alerts = client.get_alerts(active_only=True)
            logger.info(f"📊 Found {len(alerts)} active alerts")
            
        except Exception as e:
            logger.error(f"❌ Alertmanager connection failed: {e}")
            success = False
        
        # Test SEED Agent
        try:
            import requests
            response = requests.get(f"{self.seed_agent_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("✅ SEED Agent connection OK")
            else:
                logger.error(f"❌ SEED Agent returned status {response.status_code}")
                success = False
                
        except Exception as e:
            logger.error(f"❌ SEED Agent connection failed: {e}")
            success = False
        
        return success
    
    def poll_once(self):
        """Perform one polling cycle"""
        if not self.create_clients():
            return False
        
        return self.poller.poll_once()

def main():
    """Main entry point"""
    integration = AlertmanagerIntegration()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            # Test connections
            success = integration.test_connection()
            sys.exit(0 if success else 1)
            
        elif command == 'once':
            # Poll once and exit
            logger.info("Performing single polling cycle...")
            success = integration.poll_once()
            logger.info("✅ Polling completed" if success else "❌ Polling failed")
            sys.exit(0 if success else 1)
            
        elif command == 'help':
            print("Usage: python3 start_alertmanager_integration.py [command]")
            print("Commands:")
            print("  start (default) - Start continuous polling")
            print("  test           - Test connections to Alertmanager and SEED Agent")
            print("  once           - Perform single polling cycle and exit")
            print("  help           - Show this help message")
            sys.exit(0)
    
    # Default: start continuous polling
    try:
        integration.start()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()