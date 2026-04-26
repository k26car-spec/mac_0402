"""
投資信號產生器 - FastAPI 整合
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_generator import SignalGenerator

router = APIRouter(prefix="/api/signals", tags=["Investment Signals"])


class SignalRequest(BaseModel):
    risk_profile: str = "MODERATE"
    initial_capital: float = 1000000
    focus_stocks: List[str] = None


@router.post("/generate")
async def generate_investment_signals(request: SignalRequest):
    """生成投資信號"""
    try:
        generator = SignalGenerator(
            risk_profile=request.risk_profile,
            initial_capital=request.initial_capital
        )
        
        focus_stocks = request.focus_stocks or [
            "2330", "2454", "2382", "3231", "6669", "2317", "3008", "2308"
        ]
        
        recommendation = generator.generate_portfolio_recommendation(focus_stocks)
        
        return {
            "success": True,
            "recommendation": recommendation.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{ticker}")
async def get_stock_signal(
    ticker: str,
    risk_profile: str = Query("MODERATE")
):
    """獲取單一股票投資信號"""
    try:
        generator = SignalGenerator(risk_profile=risk_profile)
        signal = generator.generate_stock_signal(ticker)
        
        return {
            "success": True,
            "signal": signal.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_investment_report(
    risk_profile: str = Query("MODERATE"),
    capital: float = Query(1000000)
):
    """獲取完整投資報告"""
    try:
        generator = SignalGenerator(
            risk_profile=risk_profile,
            initial_capital=capital
        )
        
        recommendation = generator.generate_portfolio_recommendation()
        report = generator.generate_report(recommendation)
        
        return {
            "success": True,
            "report": report,
            "recommendation": recommendation.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick-summary")
async def get_quick_summary(risk_profile: str = Query("MODERATE")):
    """獲取快速摘要"""
    try:
        generator = SignalGenerator(risk_profile=risk_profile)
        
        focus_stocks = ["2330", "2454", "2382", "6669", "3008"]
        signals = []
        
        for ticker in focus_stocks:
            try:
                signal = generator.generate_stock_signal(ticker)
                signals.append({
                    "ticker": ticker,
                    "name": signal.name,
                    "signal": signal.signal.value,
                    "score": signal.score,
                    "action": signal.action
                })
            except:
                pass
        
        # 分類
        buy_signals = [s for s in signals if "買" in s["signal"]]
        sell_signals = [s for s in signals if "賣" in s["signal"]]
        hold_signals = [s for s in signals if s["signal"] == "持有"]
        
        return {
            "success": True,
            "summary": {
                "buy": buy_signals,
                "hold": hold_signals,
                "sell": sell_signals,
                "total_analyzed": len(signals)
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
