"""
產業鏈與定價權分析模組 - FastAPI 整合
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional
import sys
import os

# 添加路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from industry_chain_analyzer import IndustryChainAnalyzer

# 創建路由
router = APIRouter(prefix="/api/industry-chain", tags=["Industry Chain"])

# 緩存
_analyzer_cache = {}


def get_analyzer(industry: str, force_refresh: bool = False) -> IndustryChainAnalyzer:
    """獲取分析器實例（帶緩存）"""
    now = datetime.now()
    cache_key = industry
    
    # 檢查緩存
    if cache_key in _analyzer_cache and not force_refresh:
        cached = _analyzer_cache[cache_key]
        # 緩存有效期1小時
        if (now - cached['timestamp']).seconds < 3600:
            return cached['analyzer']
    
    # 創建新分析器
    analyzer = IndustryChainAnalyzer(industry=industry)
    analyzer.analyze_industry_chain(fetch_real_data=True)
    
    _analyzer_cache[cache_key] = {
        'analyzer': analyzer,
        'timestamp': now
    }
    
    return analyzer


@router.get("/industries")
async def list_industries():
    """列出支援的產業"""
    analyzer = IndustryChainAnalyzer()
    industries = []
    
    for key, value in analyzer.industry_chains.items():
        industries.append({
            "id": key,
            "name": value["name"],
            "description": value.get("description", ""),
            "segment_count": len(value["segments"])
        })
    
    return {
        "success": True,
        "count": len(industries),
        "industries": industries
    }


@router.get("/analyze/{industry}")
async def analyze_industry(
    industry: str,
    refresh: bool = Query(False, description="是否強制刷新數據")
):
    """
    分析指定產業的產業鏈結構
    
    Parameters:
    - industry: 產業代碼 (semiconductor, electric_vehicle, ai_server, smartphone)
    - refresh: 是否強制刷新數據
    """
    try:
        valid_industries = ["semiconductor", "electric_vehicle", "ai_server", "smartphone"]
        if industry not in valid_industries:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的產業: {industry}。支援的產業: {', '.join(valid_industries)}"
            )
        
        analyzer = get_analyzer(industry, force_refresh=refresh)
        
        return {
            "success": True,
            "data": analyzer.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/segments/{industry}")
async def get_segments(industry: str):
    """獲取產業環節結構"""
    try:
        analyzer = get_analyzer(industry)
        
        segments_info = {}
        for segment, data in analyzer.chain_structure.get("segments", {}).items():
            segments_info[segment] = {
                "subsegments": data.get("subsegments", []),
                "company_count": data.get("company_count", 0),
                "avg_pricing_power": data.get("avg_pricing_power", 0),
                "top_company": data["top_companies"][0] if data.get("top_companies") else None
            }
        
        return {
            "success": True,
            "industry": industry,
            "industry_name": analyzer.chain_structure.get("industry_name", ""),
            "segments": segments_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-stocks/{industry}")
async def get_top_stocks(
    industry: str,
    limit: int = Query(10, ge=1, le=50, description="返回數量")
):
    """獲取產業中定價權最高的股票"""
    try:
        analyzer = get_analyzer(industry)
        top_stocks = analyzer.get_top_stocks(limit)
        
        return {
            "success": True,
            "industry": industry,
            "count": len(top_stocks),
            "stocks": top_stocks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bottlenecks/{industry}")
async def get_bottlenecks(industry: str):
    """獲取產業鏈瓶頸分析"""
    try:
        analyzer = get_analyzer(industry)
        bottlenecks = analyzer.chain_structure.get("bottlenecks", [])
        
        return {
            "success": True,
            "industry": industry,
            "count": len(bottlenecks),
            "bottlenecks": bottlenecks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investment-advice/{industry}")
async def get_investment_advice(industry: str):
    """獲取投資建議"""
    try:
        analyzer = get_analyzer(industry)
        advice = analyzer.chain_structure.get("investment_advice", [])
        
        return {
            "success": True,
            "industry": industry,
            "advice": advice
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{ticker}")
async def get_company_info(ticker: str):
    """獲取單一公司的定價權分析"""
    try:
        # 搜索所有產業找到該公司
        for industry in ["semiconductor", "electric_vehicle", "ai_server", "smartphone"]:
            analyzer = get_analyzer(industry)
            
            for segment, data in analyzer.chain_structure.get("segments", {}).items():
                for company in data.get("companies", []):
                    if company["ticker"] == ticker:
                        return {
                            "success": True,
                            "industry": industry,
                            "segment": segment,
                            "company": company
                        }
        
        raise HTTPException(status_code=404, detail=f"找不到股票代碼: {ticker}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{industry}")
async def get_report(industry: str):
    """獲取完整分析報告"""
    try:
        analyzer = get_analyzer(industry)
        report = analyzer.generate_report()
        
        return {
            "success": True,
            "industry": industry,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 整合說明
# 在 backend-v3/app/main.py 中加入:
# sys.path.insert(0, '/path/to/economic_cycle_system/industry_chain')
# from api import router as industry_chain_router
# app.include_router(industry_chain_router)
