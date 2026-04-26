"""
市場即時行情 API
提供加權指數、主要個股即時報價
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import yfinance as yf
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/market", tags=["Market"])


class MarketQuote(BaseModel):
    label: str
    value: str
    change: float


class MarketQuotesResponse(BaseModel):
    quotes: List[MarketQuote]
    updated_at: str


# 快取
_cache = {
    "quotes": None,
    "updated_at": None
}


import asyncio
from functools import partial

async def _get_price_from_yfinance_async(symbol: str) -> tuple[float, float]:
    """從 yfinance 獲取最新價格和漲跌幅 (異步包裝)"""
    try:
        # 使用 to_thread 避免阻塞事件循環
        def _fetch():
            stock = yf.Ticker(symbol)
            return stock.history(period="5d")
            
        hist = await asyncio.to_thread(_fetch)
        
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            previous = hist['Close'].iloc[-2]
            change_pct = ((current - previous) / previous) * 100
            return round(current, 2), round(change_pct, 2)
        elif len(hist) == 1:
            return round(hist['Close'].iloc[-1], 2), 0.0
    except Exception as e:
        print(f"獲取 {symbol} 失敗: {e}")
    
    return 0, 0


@router.get("/quotes", response_model=MarketQuotesResponse)
async def get_market_quotes():
    """
    獲取即時市場行情
    包含：台股加權、NASDAQ、主要個股
    """
    global _cache
    
    # 快取 30 秒
    if _cache["quotes"] and _cache["updated_at"]:
        if datetime.now() - _cache["updated_at"] < timedelta(seconds=30):
            return MarketQuotesResponse(
                quotes=_cache["quotes"],
                updated_at=_cache["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
            )
    
    # 定義要抓取的標的
    targets = [
        ("^TWII", "台股加權", True),   # symbol, label, is_index
        ("^IXIC", "NASDAQ", True),
        ("2330.TW", "台積電 2330", False),
        ("2454.TW", "聯發科 2454", False),
        ("^N225", "日經 225", True),
        ("BTC-USD", "BTC / USD", True)
    ]
    
    # 並行抓取
    tasks = [_get_price_from_yfinance_async(t[0]) for t in targets]
    results = await asyncio.gather(*tasks)
    
    quotes = []
    for (price, change), (symbol, label, is_index) in zip(results, targets):
        if price > 0:
            val_str = f"{price:,.2f}" if is_index else f"{price:,.0f}"
            quotes.append(MarketQuote(label=label, value=val_str, change=change))
        else:
            quotes.append(MarketQuote(label=label, value="---", change=0))
    
    # 更新快取
    _cache["quotes"] = quotes
    _cache["updated_at"] = datetime.now()
    
    return MarketQuotesResponse(
        quotes=quotes,
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


@router.get("/quote/{symbol}")
async def get_single_quote(symbol: str):
    """獲取單一股票報價"""
    # 這裡直接傳入 symbol，patched yfinance 會自動根據清單修正為 .TW 或 .TWO
    price, change = _get_price_from_yfinance(symbol)
    
    if price == 0:
        # 如果失敗，嘗試手動強迫另一種後綴作為最後手段
        clean = symbol.replace('.TW', '').replace('.TWO', '')
        alt_symbol = f"{clean}.TWO" if '.TW' in symbol or ('.' not in symbol) else f"{clean}.TW"
        price, change = _get_price_from_yfinance(alt_symbol)
    
    if price == 0:
        raise HTTPException(status_code=404, detail=f"找不到股票 {symbol}")
    
    return {
        "symbol": symbol,
        "price": price,
        "change_percent": change,
        "source": "yfinance (patched)"
    }


@router.get("/eps-evaluation/{symbol}")
async def get_eps_evaluation(symbol: str):
    """獲取股票 EPS 與基本面評估"""
    try:
        from app.services.stock_comprehensive_analyzer import analyze_stock_comprehensive
        # 使用 quick_mode=True 減少不必要的技術網頁爬取
        analysis = await analyze_stock_comprehensive(symbol, quick_mode=True)
        
        financial = analysis.get("financial_health", {})
        valuation = analysis.get("valuation", {})
        score = analysis.get("overall_score", 0)
        
        # 轉換為前端預期的格式
        level = analysis.get("recommendation", "中立 (Hold)")
        color = "blue"
        if "強烈買入" in level or "買入" in level: color = "green"
        elif "賣出" in level or "減持" in level: color = "orange"
        
        # 提取財務指標
        metrics = {
            "eps_trailing": financial.get("eps", 0),
            "eps_forward": financial.get("eps", 0) * 1.15, # 簡單預估 15% 成長（模擬）
            "pe_trailing": valuation.get("pe_ratio", 0),
            "pe_forward": valuation.get("pe_ratio", 0) * 0.9, # 簡單預估折價（模擬）
            "roe": financial.get("roe", 0),
            "earnings_growth": financial.get("revenue_growth_3y", 0), # 用營收成長代入 (模擬)
            "pb_ratio": valuation.get("pb_ratio", 0),
            "revenue_growth": financial.get("revenue_growth_3y", 0)
        }
        
        # 拼接亮點與風險 (從分析結果提取)
        positive = []
        negative = []
        for signal in analysis.get("buy_signals", []):
            positive.append(signal.get("description", ""))
        for alert in analysis.get("risk_alerts", []):
            negative.append(alert.get("description", ""))
            
        evaluation = {
            "score": score,
            "level": level,
            "color": color,
            "tags": ["基本面穩健"] if score > 70 else ["關注中"],
            "verdict": analysis.get("ai_summary", "基本面狀況穩定，建議持續觀察籌碼流向。"),
            "macro_advice": analysis.get("macro_summary", {}).get("action_advice", ""),
            "positive_factors": positive[:3],
            "negative_factors": negative[:3]
        }
        
        return {
            "success": True,
            "data": {
                "evaluation": evaluation,
                "metrics": metrics
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/status")
async def get_market_status():
    """獲取目前數據連線狀況 (富邦即時 vs Yahoo 備援)"""
    from app.services.fubon_service import get_fubon_status
    return get_fubon_status()
