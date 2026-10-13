# Redis 连接（PRD 9.3 缓存策略 / 15.4 优雅降级）
# 注意：Redis 不可用时业务必须能直连 DB 降级运行（PRD 15.2），所以这里所有缓存调用都要 try/except
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from .config import settings

redis_client: Optional[aioredis.Redis] = aioredis.from_url(
    settings.redis_url, decode_responses=True
)

CACHE_TTL_LEVELS = 3600        # 等级列表 1 小时
CACHE_TTL_LESSONS = 1800       # 已发布课时 30 分钟


async def cache_get(key: str) -> Optional[Any]:
    """缓存读取；Redis 挂了返回 None 降级（PRD 15.4 L1）"""
    try:
        v = await redis_client.get(key)
        return json.loads(v) if v else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        # 雪崩防护：TTL 加随机偏移（PRD 9.4）
        import random
        await redis_client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl + random.randint(0, 300))
    except Exception:
        pass


async def cache_delete(*keys: str) -> None:
    try:
        await redis_client.delete(*keys)
    except Exception:
        pass
