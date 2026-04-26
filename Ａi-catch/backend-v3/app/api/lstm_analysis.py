"""
LSTM Analysis API
用於 LSTM AI 助手頁面
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/smart-entry", tags=["LSTM Analysis"])


class AnalyzeRequest(BaseModel):
    stock_code: str


@router.post("/analyze")
async def analyze_stock(request: AnalyzeRequest):
    """
    分析股票並返回包含 LSTM AI 的綜合判斷
    """
    try:
        stock_code = request.stock_code
        
        if not stock_code:
            raise HTTPException(status_code=400, detail="請提供股票代碼")
        
        # 導入 SmartEntrySystem
        from app.services.smart_entry_system import SmartEntrySystem
        import yfinance as yf
        
        system = SmartEntrySystem()
        
        # 獲取股票數據
        ticker = yf.Ticker(f"{stock_code}.TW")
        hist = ticker.history(period="3mo")
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"無法取得 {stock_code} 的數據")
        
        # 構造 stock_data
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else latest
        
        ma5 = hist['Close'].rolling(5).mean().iloc[-1]
        ma20 = hist['Close'].rolling(20).mean().iloc[-1]
        
        stock_data = {
            'symbol': stock_code,
            'price': float(latest['Close']),
            'change_pct': float((latest['Close'] - prev['Close']) / prev['Close'] * 100),
            'volume': int(latest['Volume']),
            'volume_ratio': 1.2,
            'ma5': float(ma5),
            'ma20': float(ma20),
            'above_ma5': float(latest['Close']) > float(ma5),
            'above_ma20': float(latest['Close']) > float(ma20),
            'trend': '上升' if float(latest['Close']) > float(ma5) else '盤整'
        }
        
        # 風險檢查
        risk_check = system.check_entry_risk(stock_data)
        
        # 調用核心方法
        result = system.calculate_confidence(stock_data, risk_check)
        
        return {
            "success": True,
            "stock_code": stock_code,
            "confidence": result['confidence'],
            "factors": result['factors'],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析失敗 {stock_code}: {e}")
        raise HTTPException(status_code=500, detail=f"分析失敗: {str(e)}")
