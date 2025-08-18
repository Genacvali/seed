# -*- coding: utf-8 -*-
import time

class Throttler:
    def __init__(self):
        self._seen = {}  # key -> ts

    def suppressed(self, key: str, ttl_seconds: int) -> bool:
        now = time.time()
        ts = self._seen.get(key, 0)
        if now - ts < ttl_seconds:
            return True
        return False

    def mark(self, key: str):
        self._seen[key] = time.time()
