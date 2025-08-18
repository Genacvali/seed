# -*- coding: utf-8 -*-
import os
import time
import redis
from typing import Optional

class RedisThrottler:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Подключение к Redis"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Проверяем соединение
            self.redis_client.ping()
        except Exception as e:
            print(f"[REDIS WARNING] Failed to connect to Redis: {e}")
            print("[REDIS WARNING] Falling back to in-memory throttling")
            self.redis_client = None
            # Fallback к in-memory throttling
            self._seen = {}
    
    def suppressed(self, key: str, ttl_seconds: int) -> bool:
        """Проверка, был ли алерт недавно отправлен"""
        if self.redis_client:
            return self._redis_suppressed(key, ttl_seconds)
        else:
            return self._memory_suppressed(key, ttl_seconds)
    
    def mark(self, key: str, ttl_seconds: int = 120):
        """Отметка алерта как отправленного"""
        if self.redis_client:
            self._redis_mark(key, ttl_seconds)
        else:
            self._memory_mark(key)
    
    def _redis_suppressed(self, key: str, ttl_seconds: int) -> bool:
        """Redis-based проверка подавления"""
        try:
            redis_key = f"seed:throttle:{key}"
            return self.redis_client.exists(redis_key) > 0
        except Exception as e:
            print(f"[REDIS ERROR] suppressed check failed: {e}")
            return False
    
    def _redis_mark(self, key: str, ttl_seconds: int):
        """Redis-based отметка"""
        try:
            redis_key = f"seed:throttle:{key}"
            self.redis_client.setex(redis_key, ttl_seconds, int(time.time()))
        except Exception as e:
            print(f"[REDIS ERROR] mark failed: {e}")
    
    def _memory_suppressed(self, key: str, ttl_seconds: int) -> bool:
        """Fallback in-memory проверка"""
        now = time.time()
        ts = self._seen.get(key, 0)
        return now - ts < ttl_seconds
    
    def _memory_mark(self, key: str):
        """Fallback in-memory отметка"""
        self._seen[key] = time.time()
    
    def get_stats(self) -> dict:
        """Статистика throttling"""
        if self.redis_client:
            try:
                keys = self.redis_client.keys("seed:throttle:*")
                return {
                    "backend": "redis",
                    "suppressed_count": len(keys),
                    "redis_connected": True
                }
            except:
                return {"backend": "redis", "redis_connected": False}
        else:
            return {
                "backend": "memory", 
                "suppressed_count": len(getattr(self, '_seen', {})),
                "redis_connected": False
            }