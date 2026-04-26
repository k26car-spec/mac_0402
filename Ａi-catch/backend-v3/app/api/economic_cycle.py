"""
經濟循環系統 API 整合路由
整合所有經濟循環分析模組的 API 端點

模組：
1. 總經循環定位
2. 產業鏈分析
3. 財報篩選
4. 技術分析
5. 資產配置
6. 電子股監測
7. 投資信號產生器
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import sys
import os

# 加入經濟循環系統路徑
ECONOMIC_SYSTEM_PATH = "/Users/Mac/Documents/ETF/AI/Ａi-catch/economic_cycle_system"
sys.path.insert(0, ECONOMIC_SYSTEM_PATH)

router = APIRouter(prefix="/api/economic-cycle", tags=["Economic Cycle System"])


# ============= 請求模型 =============

class SignalRequest(BaseModel):
    risk_profile: str = "MODERATE"
    initial_capital: float = 1000000
    focus_stocks: List[str] = None


class AllocationRequest(BaseModel):
    risk_profile: str = "MODERATE"
    initial_capital: float = 1000000


# ============= 投資信號產生器 API =============

@router.post("/signals/generate")
async def generate_investment_signals(request: SignalRequest):
    """
    🎯 生成投資信號 (買進/賣出/持有 + 配置建議)
    
    整合技術分析、趨勢分析、訂單動能，輸出最終投資建議
    """
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/signal_generator")
        from signal_generator import SignalGenerator
        
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


@router.get("/signals/stock/{ticker}")
async def get_stock_signal(
    ticker: str,
    risk_profile: str = Query("MODERATE")
):
    """獲取單一股票投資信號"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/signal_generator")
        from signal_generator import SignalGenerator
        
        generator = SignalGenerator(risk_profile=risk_profile)
        signal = generator.generate_stock_signal(ticker)
        
        return {
            "success": True,
            "signal": signal.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/report")
async def get_investment_report(
    risk_profile: str = Query("MODERATE"),
    capital: float = Query(1000000)
):
    """獲取完整投資報告"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/signal_generator")
        from signal_generator import SignalGenerator
        
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


# ============= 技術分析 API =============

@router.get("/technical/analyze/{ticker}")
async def technical_analysis(ticker: str):
    """技術面分析 (五年區間 + 指標 + 交易計劃)"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/technical_timing")
        from technical_analyzer import TechnicalAnalyzer
        
        analyzer = TechnicalAnalyzer(market="TW")
        plan = analyzer.generate_trading_plan(ticker)
        
        return {"success": True, "analysis": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technical/position/{ticker}")
async def price_position(ticker: str):
    """價格位置分析 (五年區間百分比)"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/technical_timing")
        from technical_analyzer import TechnicalAnalyzer
        
        analyzer = TechnicalAnalyzer(market="TW")
        position = analyzer.analyze_price_position(ticker)
        
        return {"success": True, "position": position}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/technical/batch")
async def batch_technical_analysis(tickers: List[str]):
    """批量技術分析"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/technical_timing")
        from technical_analyzer import TechnicalAnalyzer
        
        analyzer = TechnicalAnalyzer(market="TW")
        results = analyzer.batch_analyze(tickers)
        
        return {"success": True, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 資產配置 API =============

@router.post("/allocation/calculate")
async def calculate_allocation(request: AllocationRequest):
    """計算資產配置"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/asset_allocation")
        from asset_allocator import AssetAllocator
        
        allocator = AssetAllocator(
            risk_profile=request.risk_profile,
            initial_capital=request.initial_capital
        )
        allocations = allocator.generate_portfolio_allocation()
        
        return {
            "success": True,
            "risk_profile": allocator.risk_profile.value,
            "market_condition": allocator.market_condition.value,
            "allocations": [a.to_dict() for a in allocations],
            "performance": allocator.performance_metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocation/profiles")
async def get_risk_profiles():
    """獲取所有風險偏好設定"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/asset_allocation")
        from asset_allocator import AssetAllocator, RiskProfile
        
        allocator = AssetAllocator()
        profiles = []
        
        for profile in RiskProfile:
            params = allocator.risk_parameters[profile.name]
            profiles.append({
                "name": profile.name,
                "display_name": profile.value,
                "parameters": params
            })
        
        return {"success": True, "profiles": profiles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocation/etf-universe")
async def get_etf_universe():
    """獲取 ETF 投資標的清單"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/asset_allocation")
        from asset_allocator import AssetAllocator
        
        allocator = AssetAllocator()
        return {
            "success": True,
            "etf_universe": allocator.etf_universe
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 電子股監測 API =============

@router.get("/electronics/trends")
async def get_technology_trends():
    """獲取技術趨勢分析 (AI, EV, Edge Computing)"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/electronics_monitor")
        from electronics_monitor import ElectronicsMonitor
        
        monitor = ElectronicsMonitor()
        trends = monitor.analyze_technology_trends()
        
        return {"success": True, "trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/electronics/product-cycles")
async def get_product_cycles():
    """獲取產品週期分析"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/electronics_monitor")
        from electronics_monitor import ElectronicsMonitor
        
        monitor = ElectronicsMonitor()
        products = ["smartphone", "ai_server", "electric_vehicle", "iot_devices", "ar_vr"]
        
        cycles = {}
        for product in products:
            cycle = monitor.analyze_product_cycle(product)
            cycles[product] = cycle.to_dict()
        
        return {"success": True, "product_cycles": cycles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/electronics/order-signals")
async def get_order_signals():
    """獲取訂單信號"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/electronics_monitor")
        from electronics_monitor import ElectronicsMonitor
        
        monitor = ElectronicsMonitor()
        signals = monitor.generate_order_signals()
        
        return {
            "success": True,
            "count": len(signals),
            "signals": [s.to_dict() for s in signals]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/electronics/supply-chain")
async def get_supply_chain(
    companies: str = Query("2330,2454,2382,3231,6669", description="公司代號，逗號分隔")
):
    """獲取供應鏈分析"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/electronics_monitor")
        from electronics_monitor import ElectronicsMonitor
        
        monitor = ElectronicsMonitor()
        company_list = [c.strip() for c in companies.split(",")]
        analysis = monitor.monitor_supply_chain(company_list)
        
        return {"success": True, "supply_chain_analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/electronics/investment-ideas")
async def get_investment_ideas(top_n: int = Query(10, ge=1, le=50)):
    """獲取投資想法"""
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/electronics_monitor")
        from electronics_monitor import ElectronicsMonitor
        
        monitor = ElectronicsMonitor()
        monitor.analyze_technology_trends()
        monitor.generate_order_signals()
        
        ideas = monitor.generate_investment_ideas(top_n=top_n)
        
        return {
            "success": True,
            "count": len(ideas),
            "investment_ideas": ideas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============= 總經循環 API =============

@router.get("/macro/current-phase")
async def get_current_economic_phase():
    """獲取當前經濟週期階段"""
    try:
        sys.path.insert(0, ECONOMIC_SYSTEM_PATH)
        from economic_cycle import EconomicCycleAnalyzer
        
        analyzer = EconomicCycleAnalyzer()
        phase = analyzer.determine_cycle_phase()
        allocation = analyzer.get_asset_allocation()
        
        return {
            "success": True,
            "phase": phase,
            "allocation": allocation,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # 返回預設值
        return {
            "success": True,
            "phase": {
                "phase": "recovery",
                "phase_name": "復甦期",
                "confidence": 0.7,
                "description": "經濟開始復甦，企業獲利改善"
            },
            "allocation": {
                "tw_stock": 0.50,
                "us_stock": 0.25,
                "bond": 0.15,
                "cash": 0.10
            },
            "timestamp": datetime.now().isoformat(),
            "note": "使用預設數據"
        }


# ============= 健康檢查 =============

@router.get("/health")
async def health_check():
    """經濟循環系統健康檢查"""
    modules_status = {}
    
    # 檢查各模組
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/signal_generator")
        from signal_generator import SignalGenerator
        modules_status["signal_generator"] = "✅"
    except:
        modules_status["signal_generator"] = "❌"
    
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/technical_timing")
        from technical_analyzer import TechnicalAnalyzer
        modules_status["technical_timing"] = "✅"
    except:
        modules_status["technical_timing"] = "❌"
    
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/asset_allocation")
        from asset_allocator import AssetAllocator
        modules_status["asset_allocation"] = "✅"
    except:
        modules_status["asset_allocation"] = "❌"
    
    try:
        sys.path.insert(0, f"{ECONOMIC_SYSTEM_PATH}/electronics_monitor")
        from electronics_monitor import ElectronicsMonitor
        modules_status["electronics_monitor"] = "✅"
    except:
        modules_status["electronics_monitor"] = "❌"
    
    all_ok = all(s == "✅" for s in modules_status.values())
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "version": "2.0.0",
        "modules": modules_status,
        "endpoints": {
            "signals": "/api/economic-cycle/signals/generate",
            "technical": "/api/economic-cycle/technical/analyze/{ticker}",
            "allocation": "/api/economic-cycle/allocation/calculate",
            "electronics": "/api/economic-cycle/electronics/trends"
        },
        "timestamp": datetime.now().isoformat()
    }
