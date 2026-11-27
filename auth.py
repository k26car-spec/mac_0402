from fastapi import Header, HTTPException
from config import settings


async def verify_service_key(x_service_key: str = Header(default=None)):
    """驗證內部服務呼叫帶的 Key（環境變數 SERVICE_API_KEY 設定）"""
    if not settings.service_api_key:
        raise HTTPException(status_code=500, detail="SERVICE_API_KEY 未設定，拒絕所有請求")
    if x_service_key != settings.service_api_key:
        raise HTTPException(status_code=401, detail="缺少或錯誤的 X-Service-Key")
