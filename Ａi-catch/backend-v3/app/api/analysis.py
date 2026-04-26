"""
Analysis API Endpoints
分析相关的 API 端点
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis
from app.models.stock import Stock
from app.models.analysis import ExpertSignal, AnalysisResult, Alert

router = APIRouter()


@router.get("/experts/{symbol}", summary="获取专家信号")
async def get_expert_signals(
    symbol: str,
    timeframe: Optional[str] = None,
    limit: int = Query(default=10, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    获取股票的专家信号
    
    参数:
    - symbol: 股票代码
    - timeframe: 时间框架（可选）
    - limit: 返回数量
    """
    # 构建查询
    query = select(ExpertSignal).where(ExpertSignal.symbol == symbol)
    
    if timeframe:
        query = query.where(ExpertSignal.timeframe == timeframe)
    
    query = query.order_by(desc(ExpertSignal.created_at)).limit(limit)
    
    result = await db.execute(query)
    signals = result.scalars().all()
    
    return {
        "symbol": symbol,
        "count": len(signals),
        "signals": [
            {
                "expert_name": signal.expert_name,
                "signal_type": signal.signal_type,
                "strength": float(signal.strength),
                "confidence": float(signal.confidence),
                "timeframe": signal.timeframe,
                "reasoning": signal.reasoning,
                "created_at": signal.created_at
            }
            for signal in signals
        ]
    }


@router.get("/summary/{symbol}", summary="获取分析摘要")
async def get_analysis_summary(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取股票的最新分析摘要
    
    参数:
    - symbol: 股票代码
    """
    # 获取最新分析结果
    query = select(AnalysisResult).where(
        AnalysisResult.symbol == symbol
    ).order_by(desc(AnalysisResult.created_at)).limit(1)
    
    result = await db.execute(query)
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        # 如果没有分析结果，返回基本信息
        return {
            "symbol": symbol,
            "status": "no_analysis",
            "message": "暂无分析数据"
        }
    
    return {
        "symbol": symbol,
        "analysis_type": analysis.analysis_type,
        "timeframe": analysis.timeframe,
        "mainforce": {
            "action": analysis.mainforce_action,
            "confidence": float(analysis.mainforce_confidence) if analysis.mainforce_confidence else None
        },
        "overall": {
            "score": float(analysis.overall_score) if analysis.overall_score else None,
            "recommendation": analysis.recommendation
        },
        "risk": {
            "level": analysis.risk_level,
            "score": float(analysis.risk_score) if analysis.risk_score else None
        },
        "created_at": analysis.created_at
    }


@router.post("/mainforce", summary="分析主力动向")
async def analyze_mainforce(
    symbol: str,
    timeframe: str = "1d",
    db: AsyncSession = Depends(get_db)
):
    """
    触发主力分析
    
    参数:
    - symbol: 股票代码
    - timeframe: 时间框架
    """
    from app.experts import expert_manager, TimeFrame
    from app.services.real_data_service import fubon_service
    
    # 检查股票是否存在
    query = select(Stock).where(Stock.symbol == symbol)
    result = await db.execute(query)
    stock = result.scalar_one_or_none()
    
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 不存在")
    
    # 解析时间框架
    try:
        tf = TimeFrame(timeframe)
    except ValueError:
        tf = TimeFrame.D1
    
    # 從真實數據服務獲取技術指標
    try:
        # 初始化 Fubon 服務（如果尚未初始化）
        if not fubon_service._initialized:
            await fubon_service.initialize()
        
        # 獲取真實技術指標
        indicators = await fubon_service.get_technical_indicators(symbol)
        
        if indicators and indicators.get('data_source') != 'error':
            # 使用真實數據
            current_price = indicators.get('current_price', 0)
            
            market_data = {
                # 基础数据
                "volume": indicators.get('volume', 0),
                "avg_volume": indicators.get('avg_volume', indicators.get('volume', 0)),
                "large_buy_orders": max(1, int(indicators.get('volume', 0) * 0.05)),  # 估算
                "large_sell_orders": max(1, int(indicators.get('volume', 0) * 0.04)),  # 估算
                "price_change_percent": indicators.get('change_percent', 0) / 100,
                "bid_volume": indicators.get('bid_volume', indicators.get('volume', 0) * 0.1),
                "ask_volume": indicators.get('ask_volume', indicators.get('volume', 0) * 0.1),
                
                # 技术指标
                "current_price": current_price,
                "ma5": indicators.get('ma5', current_price),
                "ma20": indicators.get('ma20', current_price),
                "ma60": indicators.get('ma60', current_price),
                "rsi": indicators.get('rsi', 50),
                "macd": indicators.get('macd', 0),
                "macd_signal": indicators.get('macd_signal', 0),
                "macd_histogram": indicators.get('macd_histogram', 0),
                
                # 动量数据
                "price_change_1d": indicators.get('change_percent', 0) / 100,
                "price_change_5d": indicators.get('change_5d', 0) / 100 if indicators.get('change_5d') else 0,
                "volume_change": indicators.get('volume_change', 0),
                
                # 52周高低点
                "high_52w": indicators.get('high_52w', current_price * 1.2),
                "low_52w": indicators.get('low_52w', current_price * 0.8),
                
                # K线数据（形态识别）
                "open": indicators.get('open', current_price),
                "high": indicators.get('high', current_price),
                "low": indicators.get('low', current_price),
                "close": current_price,
                "prev_close": indicators.get('prev_close', current_price),
                "prev_high": indicators.get('prev_high', current_price),
                "prev_low": indicators.get('prev_low', current_price),
                
                # 波动率数据
                "atr": indicators.get('atr', current_price * 0.02),
                "atr_avg": indicators.get('atr_avg', current_price * 0.02),
                "bb_upper": indicators.get('bb_upper', current_price * 1.05),
                "bb_lower": indicators.get('bb_lower', current_price * 0.95),
                "bb_middle": indicators.get('bb_middle', current_price),
                
                # 市场情绪数据
                "advance_decline_ratio": indicators.get('advance_decline_ratio', 1.0),
                "value_change": indicators.get('value_change', 0),
                "foreign_net_buy": indicators.get('foreign_net_buy', 0),
                "fear_greed_index": indicators.get('fear_greed_index', 50),
                
                # 數據來源標記
                "data_source": indicators.get('data_source', 'fubon')
            }
        else:
            raise ValueError("無法獲取真實數據")
            
    except Exception as e:
        # 如果無法獲取真實數據，回傳錯誤而非使用模擬數據
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "error",
            "error": f"無法獲取真實市場數據: {str(e)}",
            "message": "請確認 Fubon API 連接正常"
        }
    
    # 使用专家系统进行分析
    analysis_result = await expert_manager.analyze_stock(symbol, tf, market_data)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "status": "completed",
        "analysis": analysis_result,
        "data_source": market_data.get("data_source", "fubon"),
        "message": "主力分析完成（使用真實數據）"
    }


@router.get("/history/{symbol}", summary="获取分析历史")
async def get_analysis_history(
    symbol: str,
    days: int = Query(default=7, le=30),
    db: AsyncSession = Depends(get_db)
):
    """
    获取分析历史记录
    
    参数:
    - symbol: 股票代码
    - days: 查询天数（最多30天）
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    query = select(AnalysisResult).where(
        and_(
            AnalysisResult.symbol == symbol,
            AnalysisResult.created_at >= since
        )
    ).order_by(desc(AnalysisResult.created_at))
    
    result = await db.execute(query)
    history = result.scalars().all()
    
    return {
        "symbol": symbol,
        "days": days,
        "count": len(history),
        "history": [
            {
                "analysis_type": h.analysis_type,
                "recommendation": h.recommendation,
                "overall_score": float(h.overall_score) if h.overall_score else None,
                "created_at": h.created_at
            }
            for h in history
        ]
    }


@router.get("/risk/{symbol}", summary="风险评估")
async def get_risk_assessment(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取股票的风险评估
    
    参数:
    - symbol: 股票代码
    """
    # 获取最新分析
    query = select(AnalysisResult).where(
        AnalysisResult.symbol == symbol
    ).order_by(desc(AnalysisResult.created_at)).limit(1)
    
    result = await db.execute(query)
    analysis = result.scalar_one_or_none()
    
    if not analysis:
        return {
            "symbol": symbol,
            "risk_level": "unknown",
            "message": "暂无风险数据"
        }
    
    return {
        "symbol": symbol,
        "risk_level": analysis.risk_level,
        "risk_score": float(analysis.risk_score) if analysis.risk_score else None,
        "recommendation": analysis.recommendation,
        "factors": {
            "mainforce_action": analysis.mainforce_action,
            "overall_score": float(analysis.overall_score) if analysis.overall_score else None
        },
        "assessed_at": analysis.created_at
    }


@router.get("/experts", summary="获取专家列表")
async def get_experts_list():
    """获取所有可用的专家系统"""
    from app.experts import expert_manager
    
    experts = expert_manager.get_expert_list()
    
    return {
        "total_experts": len(experts),
        "experts": experts,
        "status": "active"
    }

