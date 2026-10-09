from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from fubon_client import fubon_client
from models import CandlesResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["candles"])

@router.get("/candles/{symbol}", response_model=CandlesResponse)
async def get_candles(
    symbol: str,
    from_date: str = Query(..., alias="from", description="開始日期 (YYYY-MM-DD)"),
    to_date: str = Query(..., alias="to", description="結束日期 (YYYY-MM-DD)"),
    timeframe: str = Query("D", description="時間範圍 (D=日, 1=1分, 5=5分...)")
):
    """
    取得歷史 K 線數據
    
    - **symbol**: 股票代號
    - **from**: 開始日期 (YYYY-MM-DD)
    - **to**: 結束日期 (YYYY-MM-DD)
    - **timeframe**: 時間範圍 (D/1/5/10/15/30/60)
    """
    try:
        candles = await fubon_client.get_candles(
            symbol=symbol,
            from_date=from_date,
            to_date=to_date,
            timeframe=timeframe
        )
        
        if not candles:
            # 如果沒有數據，返回空列表而不是 404，方便前端處理
            return {"success": True, "data": []}
        
        return {"success": True, "data": candles}
        
    except Exception as e:
        logger.error(f"Error getting candles for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
