"""
財報與營收量化篩選模組 - FastAPI 整合
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from financial_screener import FinancialScreener

router = APIRouter(prefix="/api/financial-screener", tags=["Financial Screener"])

# 緩存
_screener_cache = {}


def get_screener(market: str, universe_type: str, min_score: float = 60, force_refresh: bool = False) -> FinancialScreener:
    """獲取篩選器實例"""
    now = datetime.now()
    cache_key = f"{market}_{universe_type}_{min_score}"
    
    if cache_key in _screener_cache and not force_refresh:
        cached = _screener_cache[cache_key]
        if (now - cached['timestamp']).seconds < 3600:
            return cached['screener']
    
    screener = FinancialScreener(market=market)
    screener.screen_companies(universe_type=universe_type, min_score=min_score)
    
    _screener_cache[cache_key] = {
        'screener': screener,
        'timestamp': now
    }
    
    return screener


@router.get("/markets")
async def list_markets():
    """列出支援的市場"""
    return {
        "success": True,
        "markets": [
            {"id": "TW", "name": "台灣股市", "description": "台灣證券交易所上市公司"},
            {"id": "US", "name": "美國股市", "description": "美國主要交易所上市公司"}
        ]
    }


@router.get("/universes/{market}")
async def list_universes(market: str):
    """列出市場的股票池"""
    screener = FinancialScreener(market=market)
    universes = []
    
    for name, stocks in screener.stock_universes.items():
        universes.append({
            "id": name,
            "name": name,
            "stock_count": len(stocks)
        })
    
    return {
        "success": True,
        "market": market,
        "universes": universes
    }


@router.get("/screen/{market}/{universe}")
async def screen_companies(
    market: str,
    universe: str,
    min_score: float = Query(60, ge=0, le=100),
    refresh: bool = Query(False)
):
    """執行財務篩選"""
    try:
        valid_markets = ["TW", "US"]
        if market not in valid_markets:
            raise HTTPException(status_code=400, detail=f"不支援的市場: {market}")
        
        screener = get_screener(market, universe, min_score, force_refresh=refresh)
        
        return {
            "success": True,
            "data": screener.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top/{market}/{universe}")
async def get_top_companies(
    market: str,
    universe: str,
    limit: int = Query(10, ge=1, le=50)
):
    """獲取評分最高的公司"""
    try:
        screener = get_screener(market, universe)
        top = screener.get_top_companies(limit)
        
        return {
            "success": True,
            "count": len(top),
            "companies": top
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{market}/{ticker}")
async def get_company_score(market: str, ticker: str):
    """獲取單一公司的財務評分"""
    try:
        screener = FinancialScreener(market=market)
        company_data = screener.fetch_financial_data(ticker)
        score, score_details = screener.calculate_financial_score(company_data)
        rating, rating_desc = screener.get_rating(score)
        
        return {
            "success": True,
            "ticker": ticker,
            "name": company_data.get("name", ticker),
            "score": round(score, 1),
            "rating": rating,
            "rating_description": rating_desc,
            "metrics": {
                "gross_margin": round(company_data.get("gross_margin", 0) * 100, 1),
                "revenue_growth": round(company_data.get("revenue_growth", 0) * 100, 1),
                "free_cash_flow_margin": round(company_data.get("free_cash_flow_margin", 0) * 100, 1),
                "roe": round(company_data.get("roe", 0) * 100, 1),
                "current_ratio": round(company_data.get("current_ratio", 0), 2),
                "debt_to_equity": round(company_data.get("debt_to_equity", 0) * 100, 1),
                "operating_margin": round(company_data.get("operating_margin", 0) * 100, 1),
                "dividend_yield": round(company_data.get("dividend_yield", 0) * 100, 2)
            },
            "score_details": score_details,
            "data_quality": company_data.get("data_quality", "unknown")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rating-scale")
async def get_rating_scale():
    """獲取評級標準說明"""
    screener = FinancialScreener()
    
    scale = []
    for rating, (low, high, desc) in screener.rating_scale.items():
        scale.append({
            "rating": rating,
            "min_score": low,
            "max_score": high,
            "description": desc
        })
    
    return {
        "success": True,
        "rating_scale": scale
    }


@router.get("/report/{market}/{universe}")
async def get_screening_report(market: str, universe: str):
    """獲取篩選報告"""
    try:
        screener = get_screener(market, universe)
        report = screener.generate_report()
        
        return {
            "success": True,
            "market": market,
            "universe": universe,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
