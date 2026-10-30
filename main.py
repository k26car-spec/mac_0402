from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import uvicorn
import asyncio

from config import settings
from fubon_client import fubon_client
from models import HealthResponse
from routers import quote, candles

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)
logger = logging.getLogger(__name__)

# 生命週期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時
    logger.info("🚀 Starting Fubon API Service...")
    
    if settings.use_fubon_api:
        logger.info("Attempting to connect to Fubon API...")
        # 在背景嘗試連線，避免阻塞啟動
        asyncio.create_task(connect_fubon())
    else:
        logger.info("Fubon API disabled in settings")
    
    yield
    
    # 關閉時
    logger.info("Shutting down Fubon API Service...")
    fubon_client.disconnect()

async def connect_fubon():
    """背景連線任務"""
    try:
        success = await fubon_client.connect()
        if success:
            logger.info("✅ Fubon API connected successfully")
        else:
            logger.warning("⚠️  Fubon API connection failed")
    except Exception as e:
        logger.error(f"Connection task error: {e}")

# 建立 FastAPI 應用
app = FastAPI(
    title="Fubon API Service",
    description="Python microservice for Fubon Securities API integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 開發環境允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(quote.router)
app.include_router(candles.router)

# 健康檢查端點
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康檢查端點"""
    return HealthResponse(
        status="ok" if fubon_client.is_connected else "disconnected",
        connected=fubon_client.is_connected,
        message="Fubon API service is running"
    )

@app.get("/")
async def root():
    """根路徑"""
    return {
        "service": "Fubon API Service",
        "version": "1.0.0",
        "status": "running",
        "connected": fubon_client.is_connected
    }

# 全域錯誤處理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info"
    )
