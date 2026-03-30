"""
缓存层 - 统一缓存访问接口

层级：
- L0: 感觉缓冲（5 分钟）- Redis
- L1: 工作记忆（30 分钟）- Redis
- L2: 情景缓冲（24 小时）- Redis
- L3: 长期存储（永久）- LanceDB
"""

import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheLayer:
    """统一缓存访问层"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._connected = redis_client is not None
    
    def connect_redis(self, host='localhost', port=6379) -> bool:
        """连接 Redis"""
        try:
            import redis
            self.redis = redis.Redis(host=host, port=port, decode_responses=True)
            self.redis.ping()
            self._connected = True
            logger.info("Redis connected")
            return True
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            self._connected = False
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self._connected:
            return None
        try:
            data = self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """设置缓存"""
        if not self._connected:
            return False
        try:
            self.redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as e:
            logger.debug(f"Cache set error: {e}")
            return False
    
    async def get_with_fallback(self, key: str, fallback, ttl: int) -> Any:
        """获取缓存，未命中时调用 fallback"""
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        value = await fallback()
        await self.set(key, value, ttl)
        return value
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """获取 Hash 所有字段"""
        if not self._connected:
            return {}
        try:
            return self.redis.hgetall(key) or {}
        except Exception as e:
            logger.debug(f"Cache hgetall error: {e}")
            return {}
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """设置 Hash 字段"""
        if not self._connected:
            return False
        try:
            self.redis.hset(key, field, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value))
            return True
        except Exception as e:
            logger.debug(f"Cache hset error: {e}")
            return False
    
    async def hincrby(self, key: str, field: str, increment: int = 1) -> int:
        """Hash 字段自增"""
        if not self._connected:
            return increment
        try:
            return self.redis.hincrby(key, field, increment)
        except Exception as e:
            logger.debug(f"Cache hincrby error: {e}")
            return increment
    
    async def expire(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        if not self._connected:
            return False
        try:
            return self.redis.expire(key, ttl)
        except Exception as e:
            logger.debug(f"Cache expire error: {e}")
            return False
    
    async def keys(self, pattern: str) -> list:
        """匹配 key"""
        if not self._connected:
            return []
        try:
            return self.redis.keys(pattern)
        except Exception as e:
            logger.debug(f"Cache keys error: {e}")
            return []
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
