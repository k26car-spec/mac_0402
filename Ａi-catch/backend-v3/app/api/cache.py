"""
Cache API Endpoints  
缓存相关的 API 端点
"""

from fastapi import APIRouter, HTTPException
from app.database import get_redis

router = APIRouter()


@router.get("/test", summary="测试 Redis 连接")
async def test_redis():
    """测试 Redis 是否正常工作"""
    try:
        redis = await get_redis()
        
        # 设置测试值
        await redis.set("test_key", "Hello Redis!")
        
        # 获取值
        value = await redis.get("test_key")
        
        # 删除测试键
        await redis.delete("test_key")
        
        return {
            "status": "success",
            "message": "Redis 连接正常",
            "test_value": value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis 错误: {str(e)}")


@router.post("/cache/set", summary="设置缓存")
async def set_cache(key: str, value: str, ttl: int = 3600):
    """
    设置缓存
    
    参数:
    - key: 缓存键
    - value: 缓存值
    - ttl: 过期时间（秒），默认1小时
    """
    try:
        redis = await get_redis()
        await redis.setex(key, ttl, value)
        
        return {
            "status": "success",
            "key": key,
            "value": value,
            "ttl": ttl
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置缓存失败: {str(e)}")


@router.get("/cache/get/{key}", summary="获取缓存")
async def get_cache(key: str):
    """
    获取缓存值
    
    参数:
    - key: 缓存键
    """
    try:
        redis = await get_redis()
        value = await redis.get(key)
        
        if value is None:
            raise HTTPException(status_code=404, detail="缓存键不存在")
        
        return {
            "status": "success",
            "key": key,
            "value": value
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存失败: {str(e)}")


@router.delete("/cache/delete/{key}", summary="删除缓存")
async def delete_cache(key: str):
    """
    删除缓存
    
    参数:
    - key: 缓存键
    """
    try:
        redis = await get_redis()
        deleted = await redis.delete(key)
        
        return {
            "status": "success",
            "key": key,
            "deleted": bool(deleted)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除缓存失败: {str(e)}")
