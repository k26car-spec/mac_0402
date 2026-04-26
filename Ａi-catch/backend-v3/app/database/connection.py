"""
Database Connection
数据库连接管理
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://Mac@localhost/ai_stock_db"
)

# 创建异步引擎
connect_args = {}
if "postgresql" in DATABASE_URL:
    connect_args = {
        "server_settings": {
            "application_name": "ai_stock_api"
        }
    }

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 设为 True 可以看到 SQL 日志
    poolclass=NullPool,  # 使用 NullPool 避免连接问题
    connect_args=connect_args
)

# 创建异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 別名（兼容其他模組）
AsyncSessionLocal = async_session


async def get_db() -> AsyncSession:
    """
    获取数据库会话
    用于 FastAPI 依赖注入
    
    用法:
    ```python
    @app.get("/stocks")
    async def get_stocks(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Stock))
        return result.scalars().all()
    ```
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_async_session():
    """
    取得 async session (用於非 FastAPI 場景)
    
    用法:
    ```python
    async with get_async_session() as session:
        result = await session.execute(select(Model))
        ...
    ```
    """
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db():
    """
    初始化数据库
    创建所有表（仅用于开发/测试）
    生产环境应使用 Alembic 迁移
    """
    from .base import Base
    from app.models import stock  # noqa: 导入所有 models
    
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)  # 谨慎使用
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
