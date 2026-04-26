"""
Volume Profile 籌碼分析 API
提供大量支撐/壓力位分析
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/volume-profile", tags=["Volume Profile Analysis"])


@router.get("/analyze/{stock_code}")
async def analyze_volume_profile(
    stock_code: str,
    period: str = Query("3mo", description="分析期間: 1mo, 3mo, 6mo")
):
    """
    Volume Profile 籌碼分析
    
    計算：
    - POC (Point of Control): 成交量最大價位
    - VAH (Value Area High): 大量壓力位
    - VAL (Value Area Low): 大量支撐位
    - 籌碼密集區分布
    
    Args:
        stock_code: 股票代碼
        period: 分析期間 (1mo, 3mo, 6mo)
    """
    try:
        from app.services.volume_profile_analyzer import volume_profile_analyzer
        
        result = await volume_profile_analyzer.analyze(stock_code, period)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"無法取得 {stock_code} 的籌碼資料"
            )
        
        return {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Volume Profile 分析失敗 {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"分析失敗: {str(e)}"
        )


@router.get("/summary/{stock_code}")
async def get_volume_profile_summary(stock_code: str):
    """
    取得籌碼摘要（大量支撐/壓力）
    
    快速取得：
    - 上方大量壓力
    - 下方大量支撐
    - 籌碼位置判斷
    """
    try:
        from app.services.volume_profile_analyzer import volume_profile_analyzer
        
        result = await volume_profile_analyzer.analyze(stock_code, "3mo")
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"無法取得 {stock_code} 的籌碼資料"
            )
        
        return {
            "success": True,
            "stock_code": stock_code,
            "current_price": result["current_price"],
            "major_resistance": result["major_resistance"],
            "major_support": result["major_support"],
            "poc": result["poc"],
            "position_analysis": result["position_analysis"],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"籌碼摘要失敗 {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"分析失敗: {str(e)}"
        )
