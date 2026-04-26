"""
訂單流 API 端點
Order Flow API Endpoints

提供訂單流模式識別系統的 REST API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import logging

from app.services.order_flow_service import order_flow_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/order-flow", tags=["訂單流分析"])


# ==================== 請求模型 ====================

class QuoteInput(BaseModel):
    """報價數據輸入"""
    symbol: str
    price: float
    volume: int
    open: Optional[float] = None
    prevClose: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    timestamp: Optional[str] = None


class OrderBookInput(BaseModel):
    """訂單簿數據輸入"""
    symbol: str
    bids: List[dict]  # [{"price": 100, "volume": 50}, ...]
    asks: List[dict]
    lastPrice: Optional[float] = None
    timestamp: Optional[str] = None


class AnalysisInput(BaseModel):
    """完整分析輸入"""
    symbol: str
    quote: dict
    orderbook: dict


# ==================== API 端點 ====================

@router.get("/status")
async def get_system_status():
    """
    獲取訂單流分析系統狀態
    """
    return order_flow_service.get_system_status()


@router.get("/patterns/types")
async def get_pattern_types():
    """
    獲取所有支援的模式類型
    """
    from app.ml.order_flow.patterns import (
        MARKET_MICRO_PATTERNS, PATTERN_TRADING_HINTS, MarketPattern
    )
    
    patterns = []
    for pattern in MarketPattern:
        patterns.append({
            "id": pattern.value,
            "name": MARKET_MICRO_PATTERNS.get(pattern, "未知"),
            "trading_hint": PATTERN_TRADING_HINTS.get(pattern, {}),
        })
    
    return {"patterns": patterns}


@router.get("/patterns/{symbol}")
async def detect_patterns(
    symbol: str,
    include_features: bool = Query(False, description="是否包含特徵向量"),
):
    """
    檢測指定股票的市場模式
    
    返回當前識別到的市場微觀模式（積極買盤、賣盤攻擊、支撐測試等）
    """
    try:
        result = await order_flow_service.detect_patterns(
            symbol=symbol.replace(".TW", "").replace(".TWO", ""),
            include_features=include_features,
        )
        return result
    except Exception as e:
        logger.error(f"模式檢測失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/{symbol}")
async def get_features(symbol: str):
    """
    獲取指定股票的訂單流特徵向量
    
    返回成交、訂單簿、動量、時間等多維度特徵
    """
    try:
        result = await order_flow_service.get_features(
            symbol=symbol.replace(".TW", "").replace(".TWO", ""),
        )
        return result
    except Exception as e:
        logger.error(f"特徵提取失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_pattern_history(
    symbol: str,
    limit: int = Query(50, ge=1, le=200, description="返回筆數限制"),
):
    """
    獲取模式檢測歷史記錄
    """
    try:
        result = await order_flow_service.get_pattern_history(
            symbol=symbol.replace(".TW", "").replace(".TWO", ""),
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"獲取歷史失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{symbol}")
async def get_statistics(symbol: str):
    """
    獲取統計資訊
    
    包含各模式的出現次數、平均信心度等
    """
    try:
        result = await order_flow_service.get_statistics(
            symbol=symbol.replace(".TW", "").replace(".TWO", ""),
        )
        return result
    except Exception as e:
        logger.error(f"獲取統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quote")
async def process_quote(data: QuoteInput):
    """
    處理報價數據
    
    將報價數據添加到緩衝區，用於後續模式檢測
    """
    try:
        quote_dict = {
            "price": data.price,
            "volume": data.volume,
            "open": data.open or data.price,
            "prevClose": data.prevClose or data.price,
            "high": data.high or data.price,
            "low": data.low or data.price,
            "timestamp": data.timestamp or datetime.now().isoformat(),
        }
        
        result = await order_flow_service.process_realtime_quote(
            symbol=data.symbol.replace(".TW", "").replace(".TWO", ""),
            quote_data=quote_dict,
        )
        return result
    except Exception as e:
        logger.error(f"處理報價失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orderbook")
async def process_orderbook(data: OrderBookInput):
    """
    處理五檔訂單簿數據
    """
    try:
        ob_dict = {
            "bids": data.bids,
            "asks": data.asks,
            "lastPrice": data.lastPrice or 0,
            "timestamp": data.timestamp or datetime.now().isoformat(),
        }
        
        result = await order_flow_service.process_orderbook(
            symbol=data.symbol.replace(".TW", "").replace(".TWO", ""),
            orderbook_data=ob_dict,
        )
        return result
    except Exception as e:
        logger.error(f"處理訂單簿失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_order_flow(data: AnalysisInput):
    """
    完整訂單流分析
    
    整合報價和五檔數據，執行模式檢測和特徵提取
    """
    try:
        result = await order_flow_service.analyze_with_existing_data(
            symbol=data.symbol.replace(".TW", "").replace(".TWO", ""),
            quote_data=data.quote,
            orderbook_data=data.orderbook,
        )
        return result
    except Exception as e:
        logger.error(f"訂單流分析失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset/{symbol}")
async def reset_symbol(symbol: str):
    """
    重置指定股票的緩衝區和統計數據
    """
    try:
        order_flow_service.reset_symbol(
            symbol=symbol.replace(".TW", "").replace(".TWO", "")
        )
        return {
            "success": True,
            "message": f"已重置 {symbol} 的訂單流數據",
        }
    except Exception as e:
        logger.error(f"重置失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols")
async def get_monitored_symbols():
    """
    獲取正在監控的股票列表
    """
    return {
        "symbols": order_flow_service.get_monitored_symbols(),
        "count": len(order_flow_service.get_monitored_symbols()),
    }


@router.get("/realtime/{symbol}")
async def analyze_with_realtime(symbol: str):
    """
    一站式實時分析
    
    自動獲取實時報價和五檔數據，執行模式檢測
    """
    try:
        from app.services.order_flow_integrator import order_flow_integrator
        
        result = await order_flow_integrator.fetch_and_analyze(
            symbol=symbol.replace(".TW", "").replace(".TWO", "")
        )
        return result
    except Exception as e:
        logger.error(f"實時分析失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/start")
async def start_monitoring(symbols: List[str]):
    """
    開始自動監控股票列表
    
    系統會定期獲取數據並更新模式檢測
    """
    try:
        from app.services.order_flow_integrator import order_flow_integrator
        
        await order_flow_integrator.start(symbols)
        
        return {
            "success": True,
            "message": f"開始監控 {len(symbols)} 檔股票",
            "symbols": symbols,
        }
    except Exception as e:
        logger.error(f"啟動監控失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/stop")
async def stop_monitoring():
    """
    停止自動監控
    """
    try:
        from app.services.order_flow_integrator import order_flow_integrator
        
        await order_flow_integrator.stop()
        
        return {
            "success": True,
            "message": "已停止監控",
        }
    except Exception as e:
        logger.error(f"停止監控失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitor/status")
async def get_monitor_status():
    """
    獲取監控狀態
    """
    from app.services.order_flow_integrator import order_flow_integrator
    
    return {
        "running": order_flow_integrator.is_running(),
        "watchlist": order_flow_integrator.get_watchlist(),
        "watchlist_count": len(order_flow_integrator.get_watchlist()),
    }


# ==================== 準確率評估 API ====================

@router.get("/accuracy/report")
async def get_accuracy_report():
    """
    獲取模式識別準確率報告
    
    返回各時間段（5秒/30秒/60秒/5分鐘）的準確率統計
    """
    from app.ml.order_flow.accuracy_evaluator import accuracy_evaluator
    
    return accuracy_evaluator.get_accuracy_report()


@router.get("/accuracy/recent")
async def get_recent_predictions(limit: int = Query(20, ge=1, le=100)):
    """
    獲取最近的預測記錄
    """
    from app.ml.order_flow.accuracy_evaluator import accuracy_evaluator
    
    return {
        "predictions": accuracy_evaluator.get_recent_predictions(limit),
    }


@router.post("/accuracy/record")
async def record_prediction(
    symbol: str,
    pattern: str,
    pattern_name: str,
    confidence: float,
    action: str,
    entry_price: float,
):
    """
    手動記錄一次預測（用於測試）
    """
    from app.ml.order_flow.accuracy_evaluator import accuracy_evaluator
    
    record_id = accuracy_evaluator.record_prediction(
        symbol=symbol,
        pattern=pattern,
        pattern_name=pattern_name,
        confidence=confidence,
        action=action,
        entry_price=entry_price,
    )
    
    return {
        "success": True,
        "record_id": record_id,
        "message": f"已記錄預測 {pattern_name} @ {entry_price}",
    }


@router.post("/accuracy/export")
async def export_accuracy_data():
    """
    導出準確率數據到文件
    """
    from app.ml.order_flow.accuracy_evaluator import accuracy_evaluator
    from datetime import datetime
    
    filepath = f"/Users/Mac/Documents/ETF/AI/Ａi-catch/data/accuracy_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        accuracy_evaluator.export_records(filepath)
        return {
            "success": True,
            "filepath": filepath,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
