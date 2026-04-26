"""
電子股趨勢與訂單監測模組 - FastAPI 整合
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from electronics_monitor import ElectronicsMonitor

router = APIRouter(prefix="/api/electronics", tags=["Electronics Monitor"])

_monitor_cache = {}


def get_monitor(sectors: List[str] = None) -> ElectronicsMonitor:
    key = str(sectors) if sectors else "default"
    if key not in _monitor_cache:
        _monitor_cache[key] = ElectronicsMonitor(focus_sectors=sectors)
    return _monitor_cache[key]


@router.get("/trends")
async def get_technology_trends():
    """獲取技術趨勢分析"""
    try:
        monitor = get_monitor()
        trends = monitor.analyze_technology_trends()
        return {"success": True, "trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product-cycles")
async def get_product_cycles():
    """獲取產品週期分析"""
    try:
        monitor = get_monitor()
        products = ["smartphone", "ai_server", "electric_vehicle", "iot_devices", "ar_vr", "pc_nb"]
        
        cycles = {}
        for product in products:
            cycle = monitor.analyze_product_cycle(product)
            cycles[product] = cycle.to_dict()
        
        return {"success": True, "product_cycles": cycles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/order-signals")
async def get_order_signals():
    """獲取訂單信號"""
    try:
        monitor = get_monitor()
        signals = monitor.generate_order_signals()
        return {
            "success": True,
            "count": len(signals),
            "signals": [s.to_dict() for s in signals]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supply-chain")
async def get_supply_chain_analysis(
    companies: str = Query("2330,2454,2382,3231,6669", description="公司代號，逗號分隔")
):
    """獲取供應鏈分析"""
    try:
        monitor = get_monitor()
        company_list = [c.strip() for c in companies.split(",")]
        analysis = monitor.monitor_supply_chain(company_list)
        return {"success": True, "supply_chain_analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investment-ideas")
async def get_investment_ideas(top_n: int = Query(10, ge=1, le=50)):
    """獲取投資想法"""
    try:
        monitor = get_monitor()
        
        # 確保已分析趨勢和訂單
        if not monitor.technology_trends:
            monitor.analyze_technology_trends()
        if "latest" not in monitor.order_signals:
            monitor.generate_order_signals()
        
        ideas = monitor.generate_investment_ideas(top_n=top_n)
        return {
            "success": True,
            "count": len(ideas),
            "investment_ideas": ideas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{ticker}")
async def get_company_data(ticker: str):
    """獲取電子公司資料"""
    try:
        monitor = get_monitor()
        company = monitor.fetch_company_data(ticker)
        return {"success": True, "company": company.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors")
async def get_electronics_sectors():
    """獲取電子產業分類"""
    try:
        monitor = get_monitor()
        sectors = {}
        
        for sector, info in monitor.electronics_database.items():
            sectors[sector] = {
                "name": info["name"],
                "companies": [
                    {"ticker": t, **c} 
                    for t, c in info["companies"].items()
                ]
            }
        
        return {"success": True, "sectors": sectors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_monitoring_report():
    """獲取監測報告"""
    try:
        monitor = get_monitor()
        
        # 執行完整分析
        monitor.analyze_technology_trends()
        for product in ["smartphone", "ai_server", "electric_vehicle"]:
            monitor.analyze_product_cycle(product)
        monitor.generate_order_signals()
        monitor.monitor_supply_chain()
        
        report = monitor.generate_report()
        return {
            "success": True,
            "report": report,
            "data": monitor.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-analyze")
async def batch_analyze(tickers: List[str] = None):
    """批量分析電子股"""
    try:
        monitor = get_monitor()
        results = monitor.batch_analyze(tickers)
        return {
            "success": True,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
