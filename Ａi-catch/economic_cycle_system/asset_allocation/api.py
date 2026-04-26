"""
資產配置與風險控制模組 - FastAPI 整合
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from asset_allocator import AssetAllocator, RiskProfile

router = APIRouter(prefix="/api/allocation", tags=["Asset Allocation"])

_allocator_cache = {}


class AllocationRequest(BaseModel):
    risk_profile: str = "MODERATE"
    initial_capital: float = 1000000


class DCARequest(BaseModel):
    monthly_investment: float = 30000
    investment_period: int = 60


def get_allocator(risk_profile: str = "MODERATE", 
                  initial_capital: float = 1000000) -> AssetAllocator:
    key = f"{risk_profile}_{initial_capital}"
    if key not in _allocator_cache:
        _allocator_cache[key] = AssetAllocator(
            risk_profile=risk_profile, 
            initial_capital=initial_capital
        )
    return _allocator_cache[key]


@router.post("/calculate")
async def calculate_allocation(request: AllocationRequest):
    """計算資產配置"""
    try:
        allocator = get_allocator(request.risk_profile, request.initial_capital)
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


@router.get("/profiles")
async def get_risk_profiles():
    """獲取所有風險偏好設定"""
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


@router.get("/etf-universe")
async def get_etf_universe():
    """獲取ETF投資標的清單"""
    allocator = AssetAllocator()
    return {
        "success": True,
        "etf_universe": allocator.etf_universe,
        "asset_classes": {
            k: {"name": v.name, "category": v.category, 
                "expected_return": v.expected_return, "volatility": v.volatility}
            for k, v in allocator.asset_classes.items()
        }
    }


@router.post("/simulate/{risk_profile}")
async def simulate_performance(risk_profile: str, 
                               initial_capital: float = Query(1000000),
                               period: str = Query("3y")):
    """模擬投資組合績效"""
    try:
        allocator = get_allocator(risk_profile, initial_capital)
        allocations = allocator.generate_portfolio_allocation()
        perf = allocator.simulate_portfolio_performance(allocations, period)
        
        return {
            "success": True,
            "risk_profile": allocator.risk_profile.value,
            "simulation_period": period,
            "initial_capital": initial_capital,
            "final_value": allocator.performance_metrics.get("final_value", 0),
            "total_return": allocator.performance_metrics.get("total_return", 0),
            "annual_return": allocator.performance_metrics.get("simulated_annual_return", 0),
            "max_drawdown": allocator.performance_metrics.get("max_drawdown", 0),
            "sharpe_ratio": allocator.performance_metrics.get("sharpe_ratio", 0),
            "allocations": [a.to_dict() for a in allocations]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dca-plan/{risk_profile}")
async def create_dca_plan(risk_profile: str, request: DCARequest):
    """創建定期定額投資計劃"""
    try:
        allocator = get_allocator(risk_profile)
        allocations = allocator.generate_portfolio_allocation()
        dca_plan = allocator.create_dca_plan(
            allocations, 
            monthly_investment=request.monthly_investment,
            investment_period=request.investment_period
        )
        
        return {
            "success": True,
            "risk_profile": allocator.risk_profile.value,
            "dca_plan": dca_plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{risk_profile}")
async def get_report(risk_profile: str, 
                     initial_capital: float = Query(1000000)):
    """獲取資產配置報告"""
    try:
        allocator = get_allocator(risk_profile, initial_capital)
        allocator.generate_portfolio_allocation()
        report = allocator.generate_report()
        
        return {
            "success": True,
            "report": report,
            "data": allocator.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare-profiles")
async def compare_profiles(initial_capital: float = Query(1000000)):
    """比較不同風險偏好的配置"""
    try:
        allocator = AssetAllocator(initial_capital=initial_capital)
        results = allocator.batch_analyze()
        
        return {
            "success": True,
            "initial_capital": initial_capital,
            "profiles": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebalance-check")
async def check_rebalance(risk_profile: str = "MODERATE",
                          tolerance: float = Query(0.05)):
    """檢查再平衡需求"""
    try:
        allocator = get_allocator(risk_profile)
        target = allocator.generate_portfolio_allocation()
        
        # 模擬當前配置有偏離
        import random
        current = []
        for a in target:
            from asset_allocator import PortfolioAllocation
            deviation = random.uniform(-0.03, 0.03)
            current.append(PortfolioAllocation(
                asset_class=a.asset_class, ticker=a.ticker,
                allocation=max(0, a.allocation + deviation),
                expected_return=a.expected_return, risk=a.risk,
                description=a.description
            ))
        
        # 正規化
        total = sum(a.allocation for a in current)
        for a in current:
            a.allocation = a.allocation / total
        
        needed, adjustments = allocator.check_rebalancing_needed(current, tolerance)
        
        return {
            "success": True,
            "rebalance_needed": needed,
            "tolerance": tolerance,
            "adjustments": adjustments
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
