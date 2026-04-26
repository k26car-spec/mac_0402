"""
市場決策 API
Market Decision API
"""

from fastapi import APIRouter, Depends, Query
from typing import Dict, List, Any, Optional
from app.services.market_decision_service import market_decision_service
from app.services.market_condition_filter import market_filter
from app.services.macro_economy_service import macro_service

router = APIRouter(prefix="/api/market-decision", tags=["Market Decision"])

@router.get("/macro")
async def get_global_macro_status():
    """獲取最新的全球政經總匯"""
    return await macro_service.get_global_macro_status()

@router.get("/status")
async def get_market_decision_status(symbol: Optional[str] = None):
    """獲取大盤狀態與聯合決策"""
    # 1. 獲取大盤數據
    market_data = await market_decision_service.get_market_data()
    
    # 2. 獲取大盤狀況 (BULL/BEAR/NEUTRAL)
    market_cond_res = market_filter.get_market_condition()
    market_cond = market_cond_res["condition"]
    
    # 3. 獲取個股狀況 (如果提供 symbol)
    # 這裡可以用現有的指標判斷，暫時模擬
    stock_cond = "NEUTRAL"
    if symbol:
        # TODO: 串接實際個股分析邏輯
        # 這裡簡單判斷：若 symbol 在監控清單且漲幅 > 1% 則為 STRONG
        try:
            from app.services.fubon_service import get_realtime_quote
            quote = await get_realtime_quote(symbol)
            if quote and quote.get("change", 0) > 1.0:
                stock_cond = "STRONG"
            elif quote and quote.get("change", 0) < -1.0:
                stock_cond = "WEAK"
        except:
            pass
            
    # 4. 獲取聯合決策
    decision = market_decision_service.get_trading_decision(market_cond, stock_cond)
    
    # 5. 獲取全球總經狀態
    macro_res = await macro_service.get_global_macro_status()
    
    # 6. 獲取預警消息
    warnings = await market_decision_service.get_market_warnings()
    
    return {
        "market_data": market_data,
        "market_condition": market_cond,
        "stock_condition": stock_cond,
        "decision": decision,
        "warnings": warnings,
        "macro_result": macro_res,
        "summary": macro_res.get("summary", market_cond_res["reason"])
    }

@router.get("/warnings")
async def get_market_warnings():
    """僅獲取預警消息"""
    warnings = await market_decision_service.get_market_warnings()
    return {"warnings": warnings}
