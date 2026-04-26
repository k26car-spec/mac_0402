"""
訂單流模式準確率評估系統
Order Flow Pattern Accuracy Evaluator

功能：
1. 記錄每次預測信號
2. 追蹤後續價格變化（5秒/30秒/60秒/5分鐘）
3. 計算預測準確率
4. 生成評估報告
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    """交易方向"""
    LONG = "long"       # 做多
    SHORT = "short"     # 做空
    HOLD = "hold"       # 觀望


@dataclass
class PredictionRecord:
    """預測記錄"""
    id: str                           # 唯一識別碼
    symbol: str                       # 股票代碼
    timestamp: datetime               # 預測時間
    pattern: str                      # 預測模式
    pattern_name: str                 # 模式名稱
    confidence: float                 # 信心度
    action: str                       # 建議動作
    
    # 預測時的價格
    entry_price: float = 0.0
    
    # 後續價格追蹤
    price_5s: Optional[float] = None
    price_30s: Optional[float] = None
    price_60s: Optional[float] = None
    price_5m: Optional[float] = None
    
    # 評估結果
    direction_correct_5s: Optional[bool] = None
    direction_correct_30s: Optional[bool] = None
    direction_correct_60s: Optional[bool] = None
    direction_correct_5m: Optional[bool] = None
    
    # 收益率
    return_5s: Optional[float] = None
    return_30s: Optional[float] = None
    return_60s: Optional[float] = None
    return_5m: Optional[float] = None
    
    evaluated: bool = False


@dataclass
class AccuracyStats:
    """準確率統計"""
    total_predictions: int = 0
    evaluated_predictions: int = 0
    
    # 各時間段準確率
    accuracy_5s: float = 0.0
    accuracy_30s: float = 0.0
    accuracy_60s: float = 0.0
    accuracy_5m: float = 0.0
    
    # 各模式準確率
    pattern_accuracy: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # 平均收益率
    avg_return_5s: float = 0.0
    avg_return_30s: float = 0.0
    avg_return_60s: float = 0.0
    avg_return_5m: float = 0.0
    
    # 按信心度分層的準確率
    high_confidence_accuracy: float = 0.0  # confidence >= 0.8
    medium_confidence_accuracy: float = 0.0  # 0.6 <= confidence < 0.8
    low_confidence_accuracy: float = 0.0   # confidence < 0.6
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_predictions": self.total_predictions,
            "evaluated_predictions": self.evaluated_predictions,
            "accuracy": {
                "5s": round(self.accuracy_5s * 100, 2),
                "30s": round(self.accuracy_30s * 100, 2),
                "60s": round(self.accuracy_60s * 100, 2),
                "5m": round(self.accuracy_5m * 100, 2),
            },
            "avg_return": {
                "5s": round(self.avg_return_5s * 100, 4),
                "30s": round(self.avg_return_30s * 100, 4),
                "60s": round(self.avg_return_60s * 100, 4),
                "5m": round(self.avg_return_5m * 100, 4),
            },
            "by_confidence": {
                "high (>=80%)": round(self.high_confidence_accuracy * 100, 2),
                "medium (60-80%)": round(self.medium_confidence_accuracy * 100, 2),
                "low (<60%)": round(self.low_confidence_accuracy * 100, 2),
            },
            "by_pattern": self.pattern_accuracy,
        }


class PatternAccuracyEvaluator:
    """
    模式準確率評估器
    
    使用方式：
    1. 每次預測時調用 record_prediction()
    2. 定期調用 evaluate_pending() 評估歷史預測
    3. 調用 get_accuracy_report() 獲取報告
    """
    
    # 模式對應的預期方向
    PATTERN_DIRECTIONS = {
        "AGGRESSIVE_BUYING": TradeDirection.LONG,
        "AGGRESSIVE_SELLING": TradeDirection.SHORT,
        "SUPPORT_TESTING": TradeDirection.LONG,
        "RESISTANCE_TESTING": TradeDirection.SHORT,
        "LIQUIDITY_DRYING": TradeDirection.HOLD,
        "FAKE_OUT": TradeDirection.HOLD,  # 方向反轉
        "NEUTRAL": TradeDirection.HOLD,
    }
    
    # 動作對應的預期方向
    ACTION_DIRECTIONS = {
        "BUY": TradeDirection.LONG,
        "STRONG_BUY": TradeDirection.LONG,
        "WEAK_BUY": TradeDirection.LONG,
        "WATCH_FOR_BUY": TradeDirection.LONG,
        "SELL": TradeDirection.SHORT,
        "STRONG_SELL": TradeDirection.SHORT,
        "WEAK_SELL": TradeDirection.SHORT,
        "WATCH_FOR_SELL": TradeDirection.SHORT,
        "HOLD": TradeDirection.HOLD,
        "WAIT": TradeDirection.HOLD,
        "REVERSE": TradeDirection.HOLD,
    }
    
    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self._records: List[PredictionRecord] = []
        self._pending_evaluation: List[PredictionRecord] = []
        self._record_count = 0
    
    def record_prediction(
        self,
        symbol: str,
        pattern: str,
        pattern_name: str,
        confidence: float,
        action: str,
        entry_price: float,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """記錄一次預測"""
        self._record_count += 1
        record_id = f"{symbol}_{self._record_count}_{datetime.now().strftime('%H%M%S')}"
        
        record = PredictionRecord(
            id=record_id,
            symbol=symbol,
            timestamp=timestamp or datetime.now(),
            pattern=pattern,
            pattern_name=pattern_name,
            confidence=confidence,
            action=action,
            entry_price=entry_price,
        )
        
        self._records.append(record)
        self._pending_evaluation.append(record)
        
        # 限制記錄數量
        if len(self._records) > self.max_records:
            self._records.pop(0)
        
        logger.info(f"📝 記錄預測: {symbol} - {pattern_name} @ {entry_price}")
        return record_id
    
    async def evaluate_with_price(
        self,
        record: PredictionRecord,
        current_price: float,
        elapsed_seconds: float,
    ):
        """用當前價格評估預測"""
        if record.entry_price <= 0:
            return
        
        price_return = (current_price - record.entry_price) / record.entry_price
        expected_direction = self.ACTION_DIRECTIONS.get(record.action, TradeDirection.HOLD)
        
        # 判斷方向是否正確
        if expected_direction == TradeDirection.LONG:
            is_correct = price_return > 0
        elif expected_direction == TradeDirection.SHORT:
            is_correct = price_return < 0
        else:
            is_correct = abs(price_return) < 0.001  # HOLD 時價格變動小於 0.1%
        
        # 根據時間段記錄
        if elapsed_seconds <= 10 and record.price_5s is None:
            record.price_5s = current_price
            record.return_5s = price_return
            record.direction_correct_5s = is_correct
        elif elapsed_seconds <= 40 and record.price_30s is None:
            record.price_30s = current_price
            record.return_30s = price_return
            record.direction_correct_30s = is_correct
        elif elapsed_seconds <= 70 and record.price_60s is None:
            record.price_60s = current_price
            record.return_60s = price_return
            record.direction_correct_60s = is_correct
        elif elapsed_seconds <= 350 and record.price_5m is None:
            record.price_5m = current_price
            record.return_5m = price_return
            record.direction_correct_5m = is_correct
            record.evaluated = True
    
    async def evaluate_pending(self, get_price_func) -> int:
        """
        評估待處理的預測
        
        Args:
            get_price_func: async function(symbol) -> float，獲取當前價格
        
        Returns:
            已評估的記錄數
        """
        now = datetime.now()
        evaluated = 0
        still_pending = []
        
        for record in self._pending_evaluation:
            elapsed = (now - record.timestamp).total_seconds()
            
            if elapsed > 300:  # 超過 5 分鐘，標記為已完成
                record.evaluated = True
                evaluated += 1
                continue
            
            try:
                current_price = await get_price_func(record.symbol)
                if current_price and current_price > 0:
                    await self.evaluate_with_price(record, current_price, elapsed)
                    
                    if record.evaluated:
                        evaluated += 1
                    else:
                        still_pending.append(record)
            except Exception as e:
                logger.debug(f"獲取價格失敗: {e}")
                still_pending.append(record)
        
        self._pending_evaluation = still_pending
        return evaluated
    
    def calculate_stats(self) -> AccuracyStats:
        """計算準確率統計"""
        stats = AccuracyStats()
        stats.total_predictions = len(self._records)
        
        evaluated = [r for r in self._records if r.evaluated]
        stats.evaluated_predictions = len(evaluated)
        
        if not evaluated:
            return stats
        
        # 各時間段準確率
        correct_5s = [r for r in evaluated if r.direction_correct_5s]
        correct_30s = [r for r in evaluated if r.direction_correct_30s]
        correct_60s = [r for r in evaluated if r.direction_correct_60s]
        correct_5m = [r for r in evaluated if r.direction_correct_5m]
        
        with_5s = [r for r in evaluated if r.direction_correct_5s is not None]
        with_30s = [r for r in evaluated if r.direction_correct_30s is not None]
        with_60s = [r for r in evaluated if r.direction_correct_60s is not None]
        with_5m = [r for r in evaluated if r.direction_correct_5m is not None]
        
        stats.accuracy_5s = len(correct_5s) / len(with_5s) if with_5s else 0
        stats.accuracy_30s = len(correct_30s) / len(with_30s) if with_30s else 0
        stats.accuracy_60s = len(correct_60s) / len(with_60s) if with_60s else 0
        stats.accuracy_5m = len(correct_5m) / len(with_5m) if with_5m else 0
        
        # 平均收益率
        returns_5s = [r.return_5s for r in evaluated if r.return_5s is not None]
        returns_30s = [r.return_30s for r in evaluated if r.return_30s is not None]
        returns_60s = [r.return_60s for r in evaluated if r.return_60s is not None]
        returns_5m = [r.return_5m for r in evaluated if r.return_5m is not None]
        
        stats.avg_return_5s = sum(returns_5s) / len(returns_5s) if returns_5s else 0
        stats.avg_return_30s = sum(returns_30s) / len(returns_30s) if returns_30s else 0
        stats.avg_return_60s = sum(returns_60s) / len(returns_60s) if returns_60s else 0
        stats.avg_return_5m = sum(returns_5m) / len(returns_5m) if returns_5m else 0
        
        # 按信心度分層
        high_conf = [r for r in with_5m if r.confidence >= 0.8]
        med_conf = [r for r in with_5m if 0.6 <= r.confidence < 0.8]
        low_conf = [r for r in with_5m if r.confidence < 0.6]
        
        high_correct = len([r for r in high_conf if r.direction_correct_5m])
        med_correct = len([r for r in med_conf if r.direction_correct_5m])
        low_correct = len([r for r in low_conf if r.direction_correct_5m])
        
        stats.high_confidence_accuracy = high_correct / len(high_conf) if high_conf else 0
        stats.medium_confidence_accuracy = med_correct / len(med_conf) if med_conf else 0
        stats.low_confidence_accuracy = low_correct / len(low_conf) if low_conf else 0
        
        # 按模式分類
        patterns = set(r.pattern for r in with_5m)
        for pattern in patterns:
            pattern_records = [r for r in with_5m if r.pattern == pattern]
            pattern_correct = len([r for r in pattern_records if r.direction_correct_5m])
            stats.pattern_accuracy[pattern] = {
                "count": len(pattern_records),
                "accuracy": round(pattern_correct / len(pattern_records) * 100, 2) if pattern_records else 0,
            }
        
        return stats
    
    def get_accuracy_report(self) -> Dict[str, Any]:
        """獲取準確率報告"""
        stats = self.calculate_stats()
        
        return {
            "report_time": datetime.now().isoformat(),
            "summary": {
                "total_predictions": stats.total_predictions,
                "evaluated_predictions": stats.evaluated_predictions,
                "pending_evaluation": len(self._pending_evaluation),
            },
            "accuracy": stats.to_dict(),
            "interpretation": self._generate_interpretation(stats),
        }
    
    def _generate_interpretation(self, stats: AccuracyStats) -> Dict[str, str]:
        """生成解讀"""
        interpretation = {}
        
        if stats.accuracy_5m >= 0.6:
            interpretation["overall"] = "✅ 系統表現良好，5分鐘準確率達到60%以上"
        elif stats.accuracy_5m >= 0.5:
            interpretation["overall"] = "⚠️ 系統表現一般，準確率略高於隨機"
        else:
            interpretation["overall"] = "❌ 系統需要優化，準確率低於50%"
        
        if stats.high_confidence_accuracy > stats.low_confidence_accuracy:
            interpretation["confidence"] = "✅ 高信心度信號表現優於低信心度，信心度可作為參考"
        else:
            interpretation["confidence"] = "⚠️ 信心度與準確率不相關，需要調整閾值"
        
        return interpretation
    
    def get_recent_predictions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """獲取最近的預測記錄"""
        records = self._records[-limit:]
        return [
            {
                "id": r.id,
                "symbol": r.symbol,
                "timestamp": r.timestamp.isoformat(),
                "pattern": r.pattern_name,
                "confidence": r.confidence,
                "action": r.action,
                "entry_price": r.entry_price,
                "evaluated": r.evaluated,
                "direction_correct_5m": r.direction_correct_5m,
                "return_5m": round(r.return_5m * 100, 4) if r.return_5m else None,
            }
            for r in reversed(records)
        ]
    
    def export_records(self, filepath: str):
        """導出記錄到 JSON 文件"""
        data = {
            "export_time": datetime.now().isoformat(),
            "records": [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "timestamp": r.timestamp.isoformat(),
                    "pattern": r.pattern,
                    "pattern_name": r.pattern_name,
                    "confidence": r.confidence,
                    "action": r.action,
                    "entry_price": r.entry_price,
                    "price_5s": r.price_5s,
                    "price_30s": r.price_30s,
                    "price_60s": r.price_60s,
                    "price_5m": r.price_5m,
                    "return_5m": r.return_5m,
                    "direction_correct_5m": r.direction_correct_5m,
                    "evaluated": r.evaluated,
                }
                for r in self._records
            ],
            "stats": self.calculate_stats().to_dict(),
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📊 導出 {len(self._records)} 條預測記錄到 {filepath}")


# 全域評估器實例
accuracy_evaluator = PatternAccuracyEvaluator()
