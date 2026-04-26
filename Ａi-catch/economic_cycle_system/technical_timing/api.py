"""
技術面與線型時機模組 - FastAPI 整合
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from technical_analyzer import TechnicalAnalyzer

router = APIRouter(prefix="/api/technical", tags=["Technical Analysis"])

_analyzer_cache = {}


def get_analyzer(market: str = "TW") -> TechnicalAnalyzer:
    if market not in _analyzer_cache:
        _analyzer_cache[market] = TechnicalAnalyzer(market=market)
    return _analyzer_cache[market]


@router.get("/analyze/{market}/{ticker}")
async def analyze_stock(market: str, ticker: str):
    """分析單一股票技術指標"""
    try:
        analyzer = get_analyzer(market)
        plan = analyzer.generate_trading_plan(ticker)
        return {"success": True, "data": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position/{market}/{ticker}")
async def get_price_position(market: str, ticker: str):
    """獲取股票的五年區間價格位置"""
    try:
        analyzer = get_analyzer(market)
        position = analyzer.analyze_price_position(ticker)
        return {"success": True, "data": position}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/{market}/{ticker}")
async def get_technical_indicators(market: str, ticker: str):
    """獲取技術指標分析"""
    try:
        analyzer = get_analyzer(market)
        tech = analyzer.analyze_technical_indicators(ticker)
        return {"success": True, "data": tech}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/support-resistance/{market}/{ticker}")
async def get_support_resistance(market: str, ticker: str):
    """獲取支撐阻力位"""
    try:
        analyzer = get_analyzer(market)
        sr = analyzer.detect_support_resistance(ticker)
        return {"success": True, "data": sr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/{market}/{ticker}")
async def get_trading_signals(market: str, ticker: str):
    """獲取交易信號"""
    try:
        analyzer = get_analyzer(market)
        signals = analyzer.generate_trading_signals(ticker)
        return {
            "success": True,
            "count": len(signals),
            "signals": [s.to_dict() for s in signals]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/{market}/{ticker}")
async def get_trading_plan(market: str, ticker: str):
    """獲取完整交易計劃"""
    try:
        analyzer = get_analyzer(market)
        plan = analyzer.generate_trading_plan(ticker)
        return {"success": True, "data": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-analyze/{market}")
async def batch_analyze(market: str, tickers: List[str]):
    """批量分析多檔股票"""
    try:
        analyzer = get_analyzer(market)
        results = analyzer.batch_analyze(tickers)
        return {
            "success": True,
            "count": len(results),
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{market}/{ticker}")
async def get_report(market: str, ticker: str):
    """獲取技術分析報告"""
    try:
        analyzer = get_analyzer(market)
        report = analyzer.generate_report(ticker)
        return {"success": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener/{market}")
async def screen_stocks(
    market: str,
    signal_type: str = Query("buy", description="buy, sell, strong_buy, strong_sell, hold"),
    min_strength: float = Query(0.5, ge=0, le=1)
):
    """篩選符合條件的股票"""
    try:
        analyzer = get_analyzer(market)
        
        # 預設股票池
        if market == "TW":
            tickers = ["2330", "2454", "2317", "2308", "2382", "3231", "6669", "3017", "2379", "3034"]
        else:
            tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        
        results = analyzer.batch_analyze(tickers)
        
        # 篩選
        filtered = [
            r for r in results
            if r["final_signal"] == signal_type and r["signal_strength"] >= min_strength
        ]
        
        return {
            "success": True,
            "signal_type": signal_type,
            "min_strength": min_strength,
            "count": len(filtered),
            "stocks": filtered
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
