"""
Redis Connection
Redis 连接管理
"""

import os
from typing import Optional
from redis import asyncio as aioredis
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# 是否使用 FakeRedis（开发模式）
USE_FAKE_REDIS = os.getenv("USE_FAKE_REDIS", "true").lower() == "true"

# Redis 客户端
redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """
    获取 Redis 客户端
    
    开发环境使用 fakeredis，生产环境使用真实 Redis
    """
    global redis_client
    
    if redis_client is None:
        if USE_FAKE_REDIS:
            # 开发模式：使用 fakeredis
            from fakeredis import aioredis as fake_aioredis
            redis_client = fake_aioredis.FakeRedis(
                decode_responses=True,
                encoding="utf-8"
            )
            print("🔧 使用 FakeRedis (开发模式)")
        else:
            # 生产模式：连接真实 Redis
            redis_client = await aioredis.from_url(
                REDIS_URL,
                db=REDIS_DB,
                decode_responses=True,
                encoding="utf-8"
            )
            print(f"✅ 连接到 Redis: {REDIS_URL}")
    
    return redis_client


async def close_redis():
    """关闭 Redis 连接"""
    global redis_client
    if redis_client:
        await redis_client.close()
        print("✅ Redis 连接已关闭")
        redis_client = None


async def test_redis():
    """测试 Redis 连接"""
    redis = await get_redis()
    
    # 设置测试值
    await redis.set("test_key", "hello_redis")
    
    # 获取值
    value = await redis.get("test_key")
    
    # 删除测试键
    await redis.delete("test_key")
    
    return value == "hello_redis"
