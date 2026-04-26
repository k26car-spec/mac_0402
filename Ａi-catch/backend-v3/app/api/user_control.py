
"""
User Control API
允許用戶直接干預系統邏輯與背景監控任務
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.services.influence_service import influence_service
from app.services.support_watcher import support_watcher

router = APIRouter(prefix="/api/user-control", tags=["User Control & Influence"])

@router.post("/bias/global")
async def set_global_bias(score: int = Query(..., ge=-30, le=30)):
    """設定全局 AI 評分偏置 (-30 to +30)"""
    influence_service.set_global_bias(score)
    return {"success": True, "message": f"全局偏置已設定為 {score}"}

@router.post("/bias/stock")
async def set_stock_bias(symbol: str, score: int = Query(..., ge=-50, le=50)):
    """設定特定股票的 AI 評分偏置"""
    influence_service.set_stock_bias(symbol, score)
    return {"success": True, "message": f"{symbol} 的偏置已設定為 {score}"}

@router.post("/support/pin")
async def pin_support(symbol: str, price: float):
    """為股票釘標自定義支撐位"""
    influence_service.set_custom_support(symbol, price)
    return {"success": True, "message": f"已為 {symbol} 新增自定義支撐位 ${price}"}

@router.post("/watch/support")
async def watch_support(
    symbol: str, 
    price: float, 
    duration: int = Query(60, description="監控時長(分鐘)")
):
    """啟動背景支撐監控任務"""
    success = await support_watcher.start_watching(symbol, price, duration)
    return {
        "success": success, 
        "message": f"已啟動 {symbol} 的背景支撐監控 (${price})，時長 {duration} 分鐘"
    }

@router.get("/influence/status")
async def get_influence_status():
    """獲取目前的用戶影響力設定"""
    return influence_service.influence

@router.post("/narrative")
async def set_user_narrative(text: str):
    """提供用戶的主觀市場見解"""
    influence_service.set_narrative(text)
    return {"success": True, "message": "已更新用戶主觀見解"}
