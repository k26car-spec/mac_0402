"""
訊號追蹤引擎
追蹤被拒絕的訊號，記錄後續走勢
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

from app.services.rejected_signal import RejectedSignal, TrackingSnapshot

logger = logging.getLogger(__name__)


class SignalTracker:
    """訊號追蹤引擎"""
    
    def __init__(self):
        self.active_tracking: Dict[str, RejectedSignal] = {}
        self.completed_tracking: List[RejectedSignal] = []
        self.data_file = "/Users/Mac/Documents/ETF/AI/Ａi-catch/logs/rejected_signals.json"
        self._load_history()
        logger.info("📊 訊號追蹤引擎已初始化")
    
    def _load_history(self):
        """載入歷史追蹤數據"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 轉換回 RejectedSignal 物件
                    for item in data.get('completed', []):
                        signal = self._dict_to_signal(item)
                        if signal:
                            self.completed_tracking.append(signal)
                logger.info(f"載入 {len(self.completed_tracking)} 筆歷史追蹤記錄")
        except Exception as e:
            logger.error(f"載入追蹤歷史失敗: {e}")
    
    def _dict_to_signal(self, data: dict) -> Optional[RejectedSignal]:
        """字典轉換為 RejectedSignal"""
        try:
            reject_time = datetime.fromisoformat(data['reject_time']) if data.get('reject_time') else datetime.now()
            return RejectedSignal(
                signal_id=data.get('signal_id', ''),
                stock_code=data.get('stock_code', ''),
                stock_name=data.get('stock_name', ''),
                reject_time=reject_time,
                price_at_reject=data.get('price_at_reject', 0),
                vwap=data.get('vwap', 0),
                vwap_deviation=data.get('vwap_deviation', 0),
                kd_k=data.get('kd_k', 50),
                kd_d=data.get('kd_d', 50),
                ofi=data.get('ofi', 0),
                volume_trend=data.get('volume_trend', ''),
                price_trend=data.get('price_trend', ''),
                rejection_reasons=data.get('rejection_reasons', []),
                risk_score=data.get('risk_score', 0),
                virtual_entry_price=data.get('virtual_entry_price', 0),
                virtual_stop_loss=data.get('virtual_stop_loss', 0),
                virtual_take_profit=data.get('virtual_take_profit', 0),
                price_after_30min=data.get('price_after_30min'),
                price_after_1hour=data.get('price_after_1hour'),
                price_after_2hour=data.get('price_after_2hour'),
                highest_price=data.get('highest_price'),
                lowest_price=data.get('lowest_price'),
                would_profit=data.get('would_profit'),
                would_hit_stop_loss=data.get('would_hit_stop_loss'),
                would_hit_take_profit=data.get('would_hit_take_profit'),
                virtual_pnl_percent=data.get('virtual_pnl_percent'),
                decision_quality=data.get('decision_quality')
            )
        except Exception as e:
            logger.error(f"轉換訊號資料失敗: {e}")
            return None
    
    def _save_history(self):
        """保存追蹤數據"""
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'completed': [s.to_dict() for s in self.completed_tracking[-100:]]  # 保留最近 100 筆
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存追蹤歷史失敗: {e}")
    
    def add_rejected_signal(self, signal: RejectedSignal):
        """新增被拒絕的訊號到追蹤清單"""
        self.active_tracking[signal.signal_id] = signal
        logger.info(
            f"📍 開始追蹤 {signal.stock_code} {signal.stock_name} "
            f"@ ${signal.price_at_reject:.2f} "
            f"拒絕原因: {', '.join(signal.rejection_reasons)}"
        )
        
        # 啟動異步追蹤
        asyncio.create_task(self._track_signal(signal))
    
    async def _track_signal(self, signal: RejectedSignal):
        """追蹤單一訊號（2 小時）"""
        
        start_time = signal.reject_time
        tracking_duration = timedelta(hours=2)
        
        highest = signal.price_at_reject
        lowest = signal.price_at_reject
        
        # 追蹤時間點: 30分, 1小時, 2小時
        checkpoints = [
            (timedelta(minutes=30), 'price_after_30min'),
            (timedelta(hours=1), 'price_after_1hour'),
            (timedelta(hours=2), 'price_after_2hour')
        ]
        
        for wait_time, attr_name in checkpoints:
            # 計算需要等待的時間
            elapsed = datetime.now() - start_time
            remaining = wait_time - elapsed
            
            if remaining.total_seconds() > 0:
                await asyncio.sleep(remaining.total_seconds())
            
            # 獲取當前價格
            current_price = await self._get_current_price(signal.stock_code)
            
            if current_price and current_price > 0:
                setattr(signal, attr_name, current_price)
                highest = max(highest, current_price)
                lowest = min(lowest, current_price)
                
                logger.debug(f"📊 {signal.stock_code} @ {attr_name}: ${current_price:.2f}")
        
        # 追蹤結束，記錄最終數據
        signal.highest_price = highest
        signal.lowest_price = lowest
        
        # 分析結果
        self._analyze_tracking_result(signal)
        
        # 移到已完成清單
        if signal.signal_id in self.active_tracking:
            self.active_tracking.pop(signal.signal_id)
        self.completed_tracking.append(signal)
        
        # 保存
        self._save_history()
        
        logger.info(
            f"✅ 追蹤完成 {signal.stock_code}: "
            f"虛擬損益 {signal.virtual_pnl_percent:+.2f}% "
            f"決策品質: {signal.decision_quality}"
        )
    
    def _analyze_tracking_result(self, signal: RejectedSignal):
        """分析追蹤結果"""
        
        entry = signal.virtual_entry_price or signal.price_at_reject
        stop_loss = signal.virtual_stop_loss or entry * 0.97
        take_profit = signal.virtual_take_profit or entry * 1.05
        
        highest = signal.highest_price or entry
        lowest = signal.lowest_price or entry
        final_price = signal.price_after_2hour or entry
        
        # 檢查是否觸發停損/停利
        signal.would_hit_stop_loss = lowest <= stop_loss
        signal.would_hit_take_profit = highest >= take_profit
        
        # 計算虛擬損益
        if signal.would_hit_stop_loss and not signal.would_hit_take_profit:
            # 先觸發停損
            exit_price = stop_loss
            signal.would_profit = False
        elif signal.would_hit_take_profit:
            # 觸發停利
            exit_price = take_profit
            signal.would_profit = True
        else:
            # 都沒觸發，用 2 小時後價格
            exit_price = final_price
            signal.would_profit = exit_price > entry
        
        signal.virtual_pnl_percent = ((exit_price - entry) / entry) * 100 if entry > 0 else 0
        
        # 判斷決策品質
        pnl = signal.virtual_pnl_percent
        if signal.would_profit:
            if pnl > 3:
                signal.decision_quality = "❌ 錯誤拒絕（大利潤）"
            elif pnl > 1:
                signal.decision_quality = "⚠️ 可能錯誤（小利潤）"
            else:
                signal.decision_quality = "🤷 模糊地帶"
        else:
            if pnl < -3:
                signal.decision_quality = "✅ 正確拒絕（避免大虧）"
            elif pnl < -1:
                signal.decision_quality = "✅ 正確拒絕（避免小虧）"
            else:
                signal.decision_quality = "🤷 模糊地帶"
    
    async def _get_current_price(self, stock_code: str) -> Optional[float]:
        """獲取當前價格"""
        try:
            from app.services.fubon_service import get_realtime_quote
            quote = await get_realtime_quote(stock_code)
            if quote:
                return quote.get('price', 0)
        except Exception as e:
            logger.debug(f"獲取 {stock_code} 價格失敗: {e}")
        return None
    
    def get_statistics(self) -> dict:
        """獲取統計數據"""
        if not self.completed_tracking:
            return {'total': 0, 'message': '沒有追蹤數據'}
        
        total = len(self.completed_tracking)
        correct = sum(1 for s in self.completed_tracking if s.decision_quality and "正確" in s.decision_quality)
        incorrect = sum(1 for s in self.completed_tracking if s.decision_quality and "錯誤" in s.decision_quality)
        ambiguous = total - correct - incorrect
        
        # 計算平均損益
        pnl_values = [s.virtual_pnl_percent for s in self.completed_tracking if s.virtual_pnl_percent is not None]
        avg_pnl = sum(pnl_values) / len(pnl_values) if pnl_values else 0
        
        # 分原因統計
        reason_stats = {}
        for signal in self.completed_tracking:
            for reason in signal.rejection_reasons:
                if reason not in reason_stats:
                    reason_stats[reason] = {'count': 0, 'total_pnl': 0, 'correct': 0}
                reason_stats[reason]['count'] += 1
                if signal.virtual_pnl_percent:
                    reason_stats[reason]['total_pnl'] += signal.virtual_pnl_percent
                if signal.decision_quality and "正確" in signal.decision_quality:
                    reason_stats[reason]['correct'] += 1
        
        for reason, stats in reason_stats.items():
            stats['avg_pnl'] = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0
            stats['accuracy'] = stats['correct'] / stats['count'] if stats['count'] > 0 else 0
        
        return {
            'total': total,
            'correct_rejections': correct,
            'incorrect_rejections': incorrect,
            'ambiguous': ambiguous,
            'accuracy': correct / (correct + incorrect) if (correct + incorrect) > 0 else 0,
            'avg_pnl_if_entered': avg_pnl,
            'reason_stats': reason_stats,
            'active_tracking': len(self.active_tracking)
        }


# 全局追蹤器實例
signal_tracker = SignalTracker()
