"""
每日交易檢討模組
Daily Trade Review Module

功能：
1. 分析今天的訊號表現
2. 計算勝率和平均獲利
3. 自動調整策略參數
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class DailyTradeReviewer:
    """每日交易檢討器"""
    
    def __init__(self):
        self.today_signals = []
        self.today_trades = []
        self.performance_history = []
    
    async def review_today(self) -> Dict:
        """檢討今日交易表現"""
        from app.database.connection import AsyncSessionLocal
        from app.models.ml_signal import TradingSignalRecord
        from app.models.portfolio import Portfolio
        from sqlalchemy import select, and_
        
        today = datetime.now().date()
        
        results = {
            "date": str(today),
            "signals": {
                "total": 0,
                "entry_signals": 0,
                "exit_signals": 0,
                "success_rate": 0
            },
            "trades": {
                "total": 0,
                "winning": 0,
                "losing": 0,
                "win_rate": 0,
                "total_profit": 0,
                "avg_profit": 0
            },
            "recommendations": []
        }
        
        async with AsyncSessionLocal() as db:
            try:
                # 統計今日訊號
                signal_result = await db.execute(
                    select(TradingSignalRecord).where(
                        TradingSignalRecord.timestamp >= datetime.combine(today, datetime.min.time())
                    )
                )
                signals = signal_result.scalars().all()
                
                entry_signals = [s for s in signals if s.signal_type == 'ENTRY_LONG']
                exit_signals = [s for s in signals if s.signal_type in ['EXIT_LONG', 'TAKE_PROFIT', 'STOP_LOSS']]
                
                # 計算訊號成功率
                successful_signals = [s for s in entry_signals if s.is_success_30min]
                
                results["signals"]["total"] = len(signals)
                results["signals"]["entry_signals"] = len(entry_signals)
                results["signals"]["exit_signals"] = len(exit_signals)
                results["signals"]["success_rate"] = (
                    len(successful_signals) / len(entry_signals) * 100 
                    if entry_signals else 0
                )
                
                # 統計今日交易
                trade_result = await db.execute(
                    select(Portfolio).where(
                        and_(
                            Portfolio.entry_date >= datetime.combine(today, datetime.min.time()),
                            Portfolio.is_simulated == True
                        )
                    )
                )
                trades = trade_result.scalars().all()
                
                winning = [t for t in trades if t.unrealized_profit_percent and float(t.unrealized_profit_percent) > 0]
                losing = [t for t in trades if t.unrealized_profit_percent and float(t.unrealized_profit_percent) < 0]
                
                total_profit = sum(
                    float(t.unrealized_profit_percent or 0) for t in trades
                )
                
                results["trades"]["total"] = len(trades)
                results["trades"]["winning"] = len(winning)
                results["trades"]["losing"] = len(losing)
                results["trades"]["win_rate"] = (
                    len(winning) / len(trades) * 100 if trades else 0
                )
                results["trades"]["total_profit"] = round(total_profit, 2)
                results["trades"]["avg_profit"] = round(total_profit / len(trades), 2) if trades else 0
                
                # 生成建議
                results["recommendations"] = self._generate_recommendations(results)
                
            except Exception as e:
                logger.error(f"檢討失敗: {e}")
                results["error"] = str(e)
        
        # 儲存歷史
        self.performance_history.append(results)
        
        return results
    
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """根據表現生成調整建議"""
        recommendations = []
        
        signals = results["signals"]
        trades = results["trades"]
        
        # 訊號量分析
        if signals["total"] < 5:
            recommendations.append("📉 訊號量過少，建議降低信心度門檻或增加監控股票")
        elif signals["total"] > 50:
            recommendations.append("📈 訊號量過多，可能有雜訊，建議提高信心度門檻")
        
        # 勝率分析
        if trades["win_rate"] < 40:
            recommendations.append("⚠️ 勝率偏低 (<40%)，建議檢查進場條件是否過於激進")
        elif trades["win_rate"] > 70:
            recommendations.append("✅ 勝率良好 (>70%)，可考慮提高倉位或擴大監控範圍")
        
        # 平均獲利分析
        if trades["avg_profit"] < 0:
            recommendations.append("🔴 平均虧損，建議收緊停損或檢查進場時機")
        elif trades["avg_profit"] < 1:
            recommendations.append("🟡 平均獲利偏低，可考慮調高停利目標")
        elif trades["avg_profit"] > 2:
            recommendations.append("🟢 平均獲利良好，策略表現佳")
        
        # 訊號成功率分析
        if signals["success_rate"] < 50:
            recommendations.append("📊 訊號準確率偏低，需要優化進場條件")
        
        if not recommendations:
            recommendations.append("📋 今日無特別建議，持續監控")
        
        return recommendations
    
    async def auto_adjust_parameters(self) -> Dict:
        """根據歷史表現自動調整參數"""
        if len(self.performance_history) < 3:
            return {"message": "需要至少 3 天的資料才能自動調整"}
        
        # 計算近期平均勝率
        recent = self.performance_history[-3:]
        avg_win_rate = sum(r["trades"]["win_rate"] for r in recent) / 3
        avg_profit = sum(r["trades"]["avg_profit"] for r in recent) / 3
        
        adjustments = []
        
        # 根據勝率調整信心度門檻
        if avg_win_rate < 40:
            adjustments.append({
                "parameter": "min_confidence",
                "old_value": 60,
                "new_value": 65,
                "reason": "勝率偏低，提高門檻"
            })
        elif avg_win_rate > 70:
            adjustments.append({
                "parameter": "min_confidence", 
                "old_value": 60,
                "new_value": 55,
                "reason": "勝率良好，可降低門檻增加機會"
            })
        
        # 根據平均獲利調整停利
        if avg_profit < 1:
            adjustments.append({
                "parameter": "take_profit_pct",
                "old_value": 3,
                "new_value": 2,
                "reason": "平均獲利低，降低停利目標"
            })
        
        return {
            "avg_win_rate": round(avg_win_rate, 2),
            "avg_profit": round(avg_profit, 2),
            "adjustments": adjustments
        }


# 全域實例
daily_reviewer = DailyTradeReviewer()


async def run_daily_review() -> Dict:
    """執行每日檢討"""
    return await daily_reviewer.review_today()
