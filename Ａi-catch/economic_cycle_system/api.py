"""
總經循環定位系統 - FastAPI 整合
與 backend-v3 整合的 API 端點
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Optional
import sys
import os

# 添加路徑以導入主模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from economic_cycle import EconomicCycleDetector

# 創建路由
router = APIRouter(prefix="/api/economic-cycle", tags=["Economic Cycle"])

# 全局檢測器實例（緩存）
_detector_cache = {
    'detector': None,
    'last_update': None,
    'cache_duration': 3600  # 1小時緩存
}


def get_detector(force_refresh: bool = False) -> EconomicCycleDetector:
    """獲取檢測器實例（帶緩存）"""
    now = datetime.now()
    
    # 檢查是否需要刷新
    if (
        _detector_cache['detector'] is None or
        force_refresh or
        _detector_cache['last_update'] is None or
        (now - _detector_cache['last_update']).seconds > _detector_cache['cache_duration']
    ):
        # 嘗試獲取 API 金鑰
        fred_api_key = ""
        try:
            from config import FRED_API_KEY
            fred_api_key = FRED_API_KEY
        except ImportError:
            pass
        
        detector = EconomicCycleDetector(fred_api_key=fred_api_key)
        detector.fetch_all_indicators()
        detector.analyze_cycle()
        
        _detector_cache['detector'] = detector
        _detector_cache['last_update'] = now
    
    return _detector_cache['detector']


@router.get("/status")
async def get_cycle_status(refresh: bool = False):
    """
    獲取當前經濟循環階段
    
    Parameters:
    - refresh: 是否強制刷新數據
    
    Returns:
    - 當前階段、信心度、配置建議
    """
    try:
        detector = get_detector(force_refresh=refresh)
        return {
            "success": True,
            "data": detector.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators")
async def get_indicators():
    """獲取所有經濟指標"""
    try:
        detector = get_detector()
        return {
            "success": True,
            "indicators": detector.indicators,
            "last_update": detector.last_update.isoformat() if detector.last_update else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocation")
async def get_allocation():
    """獲取資產配置建議"""
    try:
        detector = get_detector()
        return {
            "success": True,
            "stage": detector.current_stage,
            "stage_name": detector.stages.get(detector.current_stage, {}).get('name', ''),
            "confidence": detector.stage_confidence,
            "allocation": detector.get_asset_allocation(),
            "sectors": detector.get_sector_recommendations(),
            "stock_picks": detector.get_stock_picks()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors")
async def get_sector_recommendations():
    """獲取產業配置建議"""
    try:
        detector = get_detector()
        return {
            "success": True,
            "stage": detector.current_stage,
            "recommendations": detector.get_sector_recommendations()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-picks")
async def get_stock_picks():
    """獲取推薦股票"""
    try:
        detector = get_detector()
        return {
            "success": True,
            "stage": detector.current_stage,
            "picks": detector.get_stock_picks()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/warnings")
async def get_warnings():
    """獲取風險警告"""
    try:
        detector = get_detector()
        warnings = detector.check_warnings()
        return {
            "success": True,
            "count": len(warnings),
            "warnings": warnings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_report():
    """獲取完整分析報告"""
    try:
        detector = get_detector()
        report = detector.generate_report()
        return {
            "success": True,
            "report": report,
            "stage": detector.current_stage,
            "confidence": detector.stage_confidence
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-report")
async def save_report():
    """保存報告到檔案"""
    try:
        detector = get_detector()
        filepath = detector.save_report()
        return {
            "success": True,
            "filepath": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 若要整合到 backend-v3，請在 main.py 中加入：
# from economic_cycle_system.api import router as economic_cycle_router
# app.include_router(economic_cycle_router)
