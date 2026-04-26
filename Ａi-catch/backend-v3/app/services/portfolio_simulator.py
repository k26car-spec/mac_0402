"""
Portfolio Simulator Service
AI 模擬交易服務 - 從分析數據模擬進出場結果
"""

import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import logging

logger = logging.getLogger(__name__)


async def get_stock_history(symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    取得股票歷史數據
    """
    try:
        # 處理台股代碼
        yf_symbol = symbol if ".TW" in symbol else f"{symbol}.TW"
        
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            # 嘗試上櫃股票
            yf_symbol = f"{symbol.replace('.TW', '')}.TWO"
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(start=start_date, end=end_date)
        
        if df.empty:
            return []
        
        history = []
        for date, row in df.iterrows():
            history.append({
                "date": date.to_pydatetime(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            })
        
        return history
        
    except Exception as e:
        logger.error(f"取得股票歷史數據失敗 {symbol}: {e}")
        return []


async def simulate_trade_outcome(
    symbol: str,
    analysis_source: str,
    entry_price: float,
    entry_date: datetime,
    target_price: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    simulation_days: int = 30
) -> Dict[str, Any]:
    """
    模擬交易結果
    
    使用歷史數據來模擬從進場點開始的交易結果
    """
    # 如果沒有設定目標價或停損，使用預設值
    if target_price is None:
        target_price = entry_price * 1.08  # 預設 8% 目標
    
    if stop_loss_price is None:
        stop_loss_price = entry_price * 0.95  # 預設 5% 停損
    
    # 取得歷史數據
    end_date = entry_date + timedelta(days=simulation_days + 7)  # 多抓幾天以防假日
    history = await get_stock_history(symbol, entry_date, end_date)
    
    if not history:
        return {
            "success": False,
            "error": "無法取得歷史數據",
            "symbol": symbol
        }
    
    # 模擬交易
    result = {
        "success": True,
        "symbol": symbol,
        "analysis_source": analysis_source,
        "entry_date": entry_date.isoformat(),
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_loss_price": stop_loss_price,
        "closed": False,
        "daily_prices": []
    }
    
    holding_days = 0
    max_profit_percent = 0
    max_drawdown_percent = 0
    
    for day_data in history:
        holding_days += 1
        current_high = day_data["high"]
        current_low = day_data["low"]
        current_close = day_data["close"]
        
        # 計算當日損益
        profit_percent = ((current_close - entry_price) / entry_price) * 100
        high_profit = ((current_high - entry_price) / entry_price) * 100
        low_profit = ((current_low - entry_price) / entry_price) * 100
        
        # 追蹤最大獲利和回撤
        max_profit_percent = max(max_profit_percent, high_profit)
        max_drawdown_percent = min(max_drawdown_percent, low_profit)
        
        result["daily_prices"].append({
            "date": day_data["date"].isoformat(),
            "close": current_close,
            "profit_percent": round(profit_percent, 2)
        })
        
        # 檢查是否觸及停損
        if current_low <= stop_loss_price:
            result["closed"] = True
            result["status"] = "stopped"
            result["exit_date"] = day_data["date"].isoformat()
            result["exit_price"] = stop_loss_price
            result["profit"] = (stop_loss_price - entry_price) * 1000
            result["profit_percent"] = ((stop_loss_price - entry_price) / entry_price) * 100
            result["holding_days"] = holding_days
            result["exit_reason"] = "觸及停損價"
            break
        
        # 檢查是否觸及目標價
        if current_high >= target_price:
            result["closed"] = True
            result["status"] = "target_hit"
            result["exit_date"] = day_data["date"].isoformat()
            result["exit_price"] = target_price
            result["profit"] = (target_price - entry_price) * 1000
            result["profit_percent"] = ((target_price - entry_price) / entry_price) * 100
            result["holding_days"] = holding_days
            result["exit_reason"] = "達到目標價"
            break
        
        # 檢查是否超過模擬天數
        if holding_days >= simulation_days:
            break
    
    # 如果沒有觸及停損或目標價
    if not result["closed"]:
        if history:
            last_price = history[-1]["close"]
            result["current_price"] = last_price
            result["profit"] = (last_price - entry_price) * 1000
            result["profit_percent"] = round(((last_price - entry_price) / entry_price) * 100, 2)
            result["holding_days"] = holding_days
            result["status"] = "open"
    
    # 添加統計數據
    result["max_profit_percent"] = round(max_profit_percent, 2)
    result["max_drawdown_percent"] = round(max_drawdown_percent, 2)
    
    # 生成摘要
    if result["closed"]:
        status_text = "停損出場" if result["status"] == "stopped" else "達標出場"
        profit_text = f"{'獲利' if result['profit'] > 0 else '虧損'} {abs(result['profit_percent']):.2f}%"
        result["summary"] = f"{status_text}，持有 {result['holding_days']} 天，{profit_text}"
    else:
        profit_text = f"{'獲利' if result['profit'] > 0 else '虧損'} {abs(result['profit_percent']):.2f}%"
        result["summary"] = f"持有中，{result['holding_days']} 天，當前 {profit_text}"
    
    return result


async def auto_simulate_from_signals(
    db: AsyncSession,
    source: str,
    days_back: int = 7
) -> List[Dict[str, Any]]:
    """
    自動從分析信號中提取並模擬交易
    """
    from app.models.analysis import ExpertSignal, AnalysisResult
    from app.models.big_order import BigOrderSignal
    from app.models.prediction import LSTMPrediction
    from app.models.portfolio import Portfolio, TradeRecord
    
    start_date = datetime.utcnow() - timedelta(days=days_back)
    simulations = []
    
    # 根據不同來源查詢信號
    if source == "expert_signal":
        result = await db.execute(
            select(ExpertSignal)
            .where(
                and_(
                    ExpertSignal.created_at >= start_date,
                    ExpertSignal.signal_type == "buy",
                    ExpertSignal.confidence >= 0.7
                )
            )
            .order_by(desc(ExpertSignal.created_at))
            .limit(20)
        )
        signals = result.scalars().all()
        
        for signal in signals:
            # 檢查是否已經有模擬紀錄
            existing = await db.execute(
                select(Portfolio).where(
                    and_(
                        Portfolio.symbol == signal.symbol,
                        Portfolio.analysis_source == source,
                        Portfolio.is_simulated == True,
                        Portfolio.entry_date >= signal.created_at - timedelta(hours=1),
                        Portfolio.entry_date <= signal.created_at + timedelta(hours=1)
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            # 從 meta_data 取得價格資訊
            meta = signal.meta_data or {}
            entry_price = meta.get("price", 0)
            
            if entry_price <= 0:
                continue
            
            sim_result = await simulate_trade_outcome(
                symbol=signal.symbol,
                analysis_source=source,
                entry_price=entry_price,
                entry_date=signal.created_at,
                simulation_days=30
            )
            
            if sim_result["success"]:
                # 創建模擬持有紀錄
                position = Portfolio(
                    symbol=signal.symbol,
                    entry_date=signal.created_at,
                    entry_price=Decimal(str(entry_price)),
                    entry_quantity=1000,
                    analysis_source=source,
                    analysis_confidence=signal.confidence,
                    analysis_details={
                        "expert_name": signal.expert_name,
                        "signal_type": signal.signal_type,
                        "reasoning": signal.reasoning
                    },
                    is_simulated=True,
                    status=sim_result.get("status", "open"),
                    notes=f"自動模擬 - {signal.expert_name}\n{sim_result.get('summary', '')}"
                )
                
                if sim_result.get("closed"):
                    position.exit_date = datetime.fromisoformat(sim_result["exit_date"])
                    position.exit_price = Decimal(str(sim_result["exit_price"]))
                    position.realized_profit = Decimal(str(sim_result["profit"]))
                    position.realized_profit_percent = Decimal(str(sim_result["profit_percent"]))
                    position.exit_reason = sim_result.get("exit_reason")
                else:
                    position.current_price = Decimal(str(sim_result.get("current_price", entry_price)))
                    position.unrealized_profit = Decimal(str(sim_result["profit"]))
                    position.unrealized_profit_percent = Decimal(str(sim_result["profit_percent"]))
                
                db.add(position)
                simulations.append(sim_result)
    
    elif source == "main_force":
        result = await db.execute(
            select(AnalysisResult)
            .where(
                and_(
                    AnalysisResult.created_at >= start_date,
                    AnalysisResult.analysis_type == "main_force",
                    AnalysisResult.mainforce_action == "entry",
                    AnalysisResult.mainforce_confidence >= 0.7
                )
            )
            .order_by(desc(AnalysisResult.created_at))
            .limit(20)
        )
        analyses = result.scalars().all()
        
        for analysis in analyses:
            # 檢查是否已經有模擬紀錄
            existing = await db.execute(
                select(Portfolio).where(
                    and_(
                        Portfolio.symbol == analysis.symbol,
                        Portfolio.analysis_source == source,
                        Portfolio.is_simulated == True,
                        Portfolio.entry_date >= analysis.created_at - timedelta(hours=1),
                        Portfolio.entry_date <= analysis.created_at + timedelta(hours=1)
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            details = analysis.details or {}
            entry_price = details.get("price", 0)
            
            if entry_price <= 0:
                continue
            
            sim_result = await simulate_trade_outcome(
                symbol=analysis.symbol,
                analysis_source=source,
                entry_price=entry_price,
                entry_date=analysis.created_at,
                simulation_days=30
            )
            
            if sim_result["success"]:
                position = Portfolio(
                    symbol=analysis.symbol,
                    entry_date=analysis.created_at,
                    entry_price=Decimal(str(entry_price)),
                    entry_quantity=1000,
                    analysis_source=source,
                    analysis_confidence=analysis.mainforce_confidence,
                    analysis_details=details,
                    is_simulated=True,
                    status=sim_result.get("status", "open"),
                    notes=f"主力進場信號模擬\n{sim_result.get('summary', '')}"
                )
                
                if sim_result.get("closed"):
                    position.exit_date = datetime.fromisoformat(sim_result["exit_date"])
                    position.exit_price = Decimal(str(sim_result["exit_price"]))
                    position.realized_profit = Decimal(str(sim_result["profit"]))
                    position.realized_profit_percent = Decimal(str(sim_result["profit_percent"]))
                    position.exit_reason = sim_result.get("exit_reason")
                else:
                    position.current_price = Decimal(str(sim_result.get("current_price", entry_price)))
                    position.unrealized_profit = Decimal(str(sim_result["profit"]))
                    position.unrealized_profit_percent = Decimal(str(sim_result["profit_percent"]))
                
                db.add(position)
                simulations.append(sim_result)
    
    elif source == "lstm_prediction":
        result = await db.execute(
            select(LSTMPrediction)
            .where(
                and_(
                    LSTMPrediction.created_at >= start_date,
                    LSTMPrediction.direction == "up"
                )
            )
            .order_by(desc(LSTMPrediction.created_at))
            .limit(20)
        )
        predictions = result.scalars().all()
        
        for pred in predictions:
            # 檢查是否已經有模擬紀錄
            existing = await db.execute(
                select(Portfolio).where(
                    and_(
                        Portfolio.symbol == pred.symbol,
                        Portfolio.analysis_source == source,
                        Portfolio.is_simulated == True,
                        Portfolio.entry_date >= pred.created_at - timedelta(hours=1),
                        Portfolio.entry_date <= pred.created_at + timedelta(hours=1)
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            entry_price = float(pred.current_price) if pred.current_price else 0
            target_price = float(pred.predicted_price) if pred.predicted_price else None
            
            if entry_price <= 0:
                continue
            
            sim_result = await simulate_trade_outcome(
                symbol=pred.symbol,
                analysis_source=source,
                entry_price=entry_price,
                entry_date=pred.created_at,
                target_price=target_price,
                simulation_days=30
            )
            
            if sim_result["success"]:
                position = Portfolio(
                    symbol=pred.symbol,
                    entry_date=pred.created_at,
                    entry_price=Decimal(str(entry_price)),
                    entry_quantity=1000,
                    analysis_source=source,
                    analysis_details={
                        "predicted_price": float(pred.predicted_price) if pred.predicted_price else None,
                        "direction": pred.direction
                    },
                    target_price=Decimal(str(target_price)) if target_price else None,
                    is_simulated=True,
                    status=sim_result.get("status", "open"),
                    notes=f"LSTM 預測模擬\n{sim_result.get('summary', '')}"
                )
                
                if sim_result.get("closed"):
                    position.exit_date = datetime.fromisoformat(sim_result["exit_date"])
                    position.exit_price = Decimal(str(sim_result["exit_price"]))
                    position.realized_profit = Decimal(str(sim_result["profit"]))
                    position.realized_profit_percent = Decimal(str(sim_result["profit_percent"]))
                    position.exit_reason = sim_result.get("exit_reason")
                else:
                    position.current_price = Decimal(str(sim_result.get("current_price", entry_price)))
                    position.unrealized_profit = Decimal(str(sim_result["profit"]))
                    position.unrealized_profit_percent = Decimal(str(sim_result["profit_percent"]))
                
                db.add(position)
                simulations.append(sim_result)
    
    await db.commit()
    
    return simulations


async def calculate_source_accuracy(
    db: AsyncSession,
    source: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    計算特定分析來源的準確性
    """
    from app.models.portfolio import Portfolio
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(Portfolio)
        .where(
            and_(
                Portfolio.analysis_source == source,
                Portfolio.status != "open",
                Portfolio.exit_date >= start_date
            )
        )
    )
    positions = result.scalars().all()
    
    if not positions:
        return {
            "source": source,
            "total_trades": 0,
            "message": "沒有已結束的交易紀錄"
        }
    
    wins = [p for p in positions if p.realized_profit and p.realized_profit > 0]
    losses = [p for p in positions if p.realized_profit and p.realized_profit <= 0]
    
    total_profit = sum(float(p.realized_profit) for p in positions if p.realized_profit)
    avg_win = sum(float(p.realized_profit_percent) for p in wins) / len(wins) if wins else 0
    avg_loss = sum(float(p.realized_profit_percent) for p in losses) / len(losses) if losses else 0
    
    # 計算勝率
    win_rate = len(wins) / len(positions) * 100
    
    # 計算獲利因子 (profit factor)
    total_win = sum(float(p.realized_profit) for p in wins) if wins else 0
    total_loss = abs(sum(float(p.realized_profit) for p in losses)) if losses else 1
    profit_factor = total_win / total_loss if total_loss > 0 else total_win
    
    # 計算期望值
    expected_value = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)
    
    return {
        "source": source,
        "period_days": days,
        "total_trades": len(positions),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(win_rate, 2),
        "total_profit": round(total_profit, 2),
        "average_win_percent": round(avg_win, 2),
        "average_loss_percent": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "expected_value_percent": round(expected_value, 2),
        "rating": _get_accuracy_rating(win_rate, profit_factor, expected_value)
    }


def _get_accuracy_rating(win_rate: float, profit_factor: float, expected_value: float) -> Dict[str, Any]:
    """
    給予準確性評級
    """
    # 綜合評分
    score = 0
    
    # 勝率評分 (滿分 40)
    if win_rate >= 70:
        score += 40
    elif win_rate >= 60:
        score += 35
    elif win_rate >= 50:
        score += 25
    elif win_rate >= 40:
        score += 15
    else:
        score += 5
    
    # 獲利因子評分 (滿分 30)
    if profit_factor >= 2.0:
        score += 30
    elif profit_factor >= 1.5:
        score += 25
    elif profit_factor >= 1.2:
        score += 20
    elif profit_factor >= 1.0:
        score += 10
    else:
        score += 0
    
    # 期望值評分 (滿分 30)
    if expected_value >= 3:
        score += 30
    elif expected_value >= 2:
        score += 25
    elif expected_value >= 1:
        score += 20
    elif expected_value >= 0:
        score += 10
    else:
        score += 0
    
    # 評級
    if score >= 90:
        grade = "A+"
        description = "極佳，建議加大配置"
    elif score >= 80:
        grade = "A"
        description = "優秀，可信賴的分析來源"
    elif score >= 70:
        grade = "B+"
        description = "良好，可適度參考"
    elif score >= 60:
        grade = "B"
        description = "一般，需搭配其他指標"
    elif score >= 50:
        grade = "C"
        description = "及格，僅供參考"
    else:
        grade = "D"
        description = "不理想，建議調整或停用"
    
    return {
        "score": score,
        "grade": grade,
        "description": description,
        "suggestion": _get_improvement_suggestion(win_rate, profit_factor, expected_value)
    }


def _get_improvement_suggestion(win_rate: float, profit_factor: float, expected_value: float) -> str:
    """
    給予改進建議
    """
    suggestions = []
    
    if win_rate < 50:
        suggestions.append("勝率偏低，建議提高信號過濾門檻")
    
    if profit_factor < 1.0:
        suggestions.append("獲利因子不足，建議檢視停損/停利設定")
    elif profit_factor < 1.5:
        suggestions.append("可考慮適度放寬目標價，提高獲利因子")
    
    if expected_value < 0:
        suggestions.append("期望值為負，此分析策略需要大幅調整")
    elif expected_value < 1:
        suggestions.append("期望值偏低，建議優化進場條件")
    
    if not suggestions:
        suggestions.append("表現良好，可維持現有策略")
    
    return "；".join(suggestions)
