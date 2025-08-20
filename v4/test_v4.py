#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test script for SEED Agent v4
Tests configuration loading and basic functionality
"""
import sys
import asyncio
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_config_loading():
    """Test configuration loading"""
    print("🧪 Testing configuration loading...")
    
    try:
        from core.config import Config
        
        config = Config("seed.yaml")
        print(f"✅ Config loaded from seed.yaml")
        
        # Test basic properties
        print(f"   Environment: {config.get('environment', 'unknown')}")
        print(f"   Agent host: {config.bind_host}")
        print(f"   Agent port: {config.bind_port}")
        print(f"   Debug mode: {config.debug}")
        
        # Test connection configs
        rabbitmq_config = config.rabbitmq_config
        print(f"   RabbitMQ: {rabbitmq_config['username']}@{rabbitmq_config['host']}:{rabbitmq_config['port']}")
        
        redis_config = config.redis_config
        print(f"   Redis: {redis_config['host']}:{redis_config['port']}/{redis_config['db']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

async def test_queue_manager():
    """Test queue manager initialization"""
    print("🧪 Testing queue manager...")
    
    try:
        from core.config import Config
        from core.queue import QueueManager
        
        config = Config("seed.yaml")
        queue_manager = QueueManager(config)
        
        print("✅ QueueManager created successfully")
        
        # Test connection URL building (don't actually connect)
        rabbitmq_config = config.rabbitmq_config
        host = rabbitmq_config["host"]
        port = rabbitmq_config["port"]
        username = rabbitmq_config["username"]
        password = rabbitmq_config["password"]
        vhost = rabbitmq_config["vhost"]
        
        if vhost == "/":
            vhost = ""
        else:
            vhost = f"/{vhost.strip('/')}"
        
        rabbitmq_url = f"amqp://{username}:{password}@{host}:{port}{vhost}"
        print(f"   Built RabbitMQ URL: {rabbitmq_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Queue manager test failed: {e}")
        return False

async def test_redis_throttler():
    """Test Redis throttler initialization"""
    print("🧪 Testing Redis throttler...")
    
    try:
        from core.config import Config
        from core.redis_throttle import RedisThrottler
        
        config = Config("seed.yaml")
        throttler = RedisThrottler(config)
        
        print("✅ RedisThrottler created successfully")
        
        # Test stats (should work even without Redis connection)
        stats = throttler.get_stats()
        print(f"   Backend: {stats['backend']}")
        print(f"   Redis connected: {stats.get('redis_connected', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis throttler test failed: {e}")
        return False

async def test_notification_manager():
    """Test notification manager initialization"""
    print("🧪 Testing notification manager...")
    
    try:
        from core.config import Config
        from core.notify import NotificationManager
        
        config = Config("seed.yaml")
        notif_manager = NotificationManager(config)
        
        await notif_manager.initialize()
        
        print("✅ NotificationManager created successfully")
        
        # Test stats
        stats = notif_manager.get_stats()
        for channel, info in stats['channels'].items():
            enabled = info['enabled']
            configured = info['configured']
            status = "✅" if (enabled and configured) else "⚠️" if enabled else "❌"
            print(f"   {channel.title()}: {status} (enabled: {enabled}, configured: {configured})")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification manager test failed: {e}")
        return False

async def test_plugin_manager():
    """Test plugin manager initialization"""
    print("🧪 Testing plugin manager...")
    
    try:
        from core.config import Config
        from plugins import PluginManager
        
        config = Config("seed.yaml")
        plugin_manager = PluginManager(config)
        
        print("✅ PluginManager created successfully")
        
        # Test plugin info
        plugin_info = plugin_manager.get_plugin_info()
        print(f"   Total plugins: {plugin_info['total_plugins']}")
        
        for name, info in plugin_info['plugins'].items():
            print(f"   - {name}: {info['name']}")
        
        # Test health check
        health = await plugin_manager.health_check()
        overall_health = "✅" if health['healthy'] else "❌"
        print(f"   Overall health: {overall_health}")
        
        return True
        
    except Exception as e:
        print(f"❌ Plugin manager test failed: {e}")
        return False

async def test_telegraf_fetcher():
    """Test Telegraf fetcher initialization"""
    print("🧪 Testing Telegraf fetcher...")
    
    try:
        from core.config import Config
        from fetchers.telegraf import TelegrafFetcher
        
        config = Config("seed.yaml")
        fetcher = TelegrafFetcher(config)
        
        print("✅ TelegrafFetcher created successfully")
        
        # Test URL generation
        test_host = "test-host"
        url = config.get_telegraf_url(test_host)
        print(f"   Generated Telegraf URL for {test_host}: {url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Telegraf fetcher test failed: {e}")
        return False

async def test_mongo_fetcher():
    """Test MongoDB fetcher initialization"""
    print("🧪 Testing MongoDB fetcher...")
    
    try:
        from core.config import Config
        from fetchers.mongo import MongoFetcher
        
        config = Config("seed.yaml")
        fetcher = MongoFetcher(config)
        
        print("✅ MongoFetcher created successfully")
        
        # Test connection string building
        conn_str = config.get_mongodb_connection_string("mongo-prod")
        if conn_str:
            masked = fetcher._mask_connection_string(conn_str)
            print(f"   MongoDB connection string: {masked}")
        else:
            print("   No MongoDB configuration found for mongo-prod")
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB fetcher test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 SEED Agent v4 Component Tests")
    print("=" * 40)
    
    tests = [
        test_config_loading,
        test_queue_manager,
        test_redis_throttler,
        test_notification_manager,
        test_plugin_manager,
        test_telegraf_fetcher,
        test_mongo_fetcher,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            success = await test()
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        
        print()  # Empty line between tests
    
    print("=" * 40)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! SEED Agent v4 is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Check configuration and dependencies.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)