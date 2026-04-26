"""
模式標註器
Pattern Labeler

根據訂單流數據自動標註市場微觀模式
用於生成訓練數據集的標籤
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from .patterns import (
    MarketPattern, PatternThresholds, PatternDetection, MARKET_MICRO_PATTERNS
)
from .features import TickData, OrderBookSnapshot, OrderFlowFeatureExtractor

logger = logging.getLogger(__name__)


class PatternLabeler:
    """
    模式標註器
    
    根據訂單流數據識別和標註市場微觀模式
    支援實時檢測和離線批量標註
    """
    
    def __init__(
        self,
        thresholds: Optional[PatternThresholds] = None,
        feature_extractor: Optional[OrderFlowFeatureExtractor] = None,
    ):
        self.thresholds = thresholds or PatternThresholds()
        self.extractor = feature_extractor or OrderFlowFeatureExtractor()
        self._detection_history: List[PatternDetection] = []
    
    def detect_patterns(
        self,
        symbol: str,
        ticks: List[TickData],
        orderbooks: List[OrderBookSnapshot],
        timestamp: Optional[datetime] = None,
    ) -> List[PatternDetection]:
        """
        檢測當前時刻的市場模式
        
        一個時刻可能存在多個模式（非互斥）
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        detections = []
        
        # 檢測各種模式
        if det := self._detect_aggressive_buying(symbol, ticks, timestamp):
            detections.append(det)
        
        if det := self._detect_aggressive_selling(symbol, ticks, timestamp):
            detections.append(det)
        
        if det := self._detect_support_testing(symbol, ticks, orderbooks, timestamp):
            detections.append(det)
        
        if det := self._detect_resistance_testing(symbol, ticks, orderbooks, timestamp):
            detections.append(det)
        
        if det := self._detect_liquidity_drying(symbol, ticks, orderbooks, timestamp):
            detections.append(det)
        
        if det := self._detect_fake_out(symbol, ticks, timestamp):
            detections.append(det)
        
        # 如果沒有檢測到任何模式，返回中性
        if not detections:
            detections.append(PatternDetection(
                pattern=MarketPattern.NEUTRAL,
                confidence=0.7,
                strength=0.0,
                timestamp=timestamp,
                symbol=symbol,
            ))
        
        # 記錄歷史
        self._detection_history.extend(detections)
        
        return detections
    
    def _detect_aggressive_buying(
        self,
        symbol: str,
        ticks: List[TickData],
        timestamp: datetime,
    ) -> Optional[PatternDetection]:
        """
        檢測積極買盤攻擊模式
        
        條件：
        1. 時間窗口內主動買入大單佔總成交70%以上
        2. 價格上漲超過0.3%
        3. 至少3筆大單
        """
        th = self.thresholds
        window_sec = th.aggressive_buy_time_window_sec
        
        # 過濾時間窗口內的 ticks
        start_time = timestamp - timedelta(seconds=window_sec)
        window_ticks = [t for t in ticks if start_time <= t.timestamp <= timestamp]
        
        if len(window_ticks) < 3:
            return None
        
        # 計算買入量和大單
        buy_ticks = [t for t in window_ticks if t.direction == "BUY"]
        large_buys = [t for t in buy_ticks if t.volume >= th.large_order_volume_threshold]
        
        total_volume = sum(t.volume for t in window_ticks)
        large_buy_volume = sum(t.volume for t in large_buys)
        
        if total_volume == 0:
            return None
        
        volume_ratio = large_buy_volume / total_volume
        
        # 計算價格變化
        prices = [t.price for t in window_ticks]
        price_change = (prices[-1] / prices[0] - 1) if prices[0] > 0 else 0
        
        # 檢查條件
        if (volume_ratio >= th.aggressive_buy_volume_ratio and
            price_change >= th.aggressive_buy_price_change and
            len(large_buys) >= th.aggressive_buy_min_large_orders):
            
            # 計算信心度和強度
            confidence = min(
                volume_ratio / th.aggressive_buy_volume_ratio,
                1.0
            ) * 0.7 + 0.3
            
            strength = min(
                (price_change / th.aggressive_buy_price_change) * 0.5 +
                (len(large_buys) / 10) * 0.5,
                1.0
            )
            
            return PatternDetection(
                pattern=MarketPattern.AGGRESSIVE_BUYING,
                confidence=confidence,
                strength=strength,
                timestamp=timestamp,
                symbol=symbol,
                evidence={
                    "volume_ratio": round(volume_ratio, 4),
                    "price_change": round(price_change * 100, 4),
                    "large_buy_count": len(large_buys),
                    "large_buy_volume": large_buy_volume,
                    "window_seconds": window_sec,
                },
            )
        
        return None
    
    def _detect_aggressive_selling(
        self,
        symbol: str,
        ticks: List[TickData],
        timestamp: datetime,
    ) -> Optional[PatternDetection]:
        """檢測積極賣盤攻擊模式"""
        th = self.thresholds
        window_sec = th.aggressive_sell_time_window_sec
        
        start_time = timestamp - timedelta(seconds=window_sec)
        window_ticks = [t for t in ticks if start_time <= t.timestamp <= timestamp]
        
        if len(window_ticks) < 3:
            return None
        
        sell_ticks = [t for t in window_ticks if t.direction == "SELL"]
        large_sells = [t for t in sell_ticks if t.volume >= th.large_order_volume_threshold]
        
        total_volume = sum(t.volume for t in window_ticks)
        large_sell_volume = sum(t.volume for t in large_sells)
        
        if total_volume == 0:
            return None
        
        volume_ratio = large_sell_volume / total_volume
        
        prices = [t.price for t in window_ticks]
        price_change = (prices[-1] / prices[0] - 1) if prices[0] > 0 else 0
        
        if (volume_ratio >= th.aggressive_sell_volume_ratio and
            price_change <= th.aggressive_sell_price_change and
            len(large_sells) >= th.aggressive_sell_min_large_orders):
            
            confidence = min(volume_ratio / th.aggressive_sell_volume_ratio, 1.0) * 0.7 + 0.3
            strength = min(abs(price_change / th.aggressive_sell_price_change) * 0.5 +
                          (len(large_sells) / 10) * 0.5, 1.0)
            
            return PatternDetection(
                pattern=MarketPattern.AGGRESSIVE_SELLING,
                confidence=confidence,
                strength=strength,
                timestamp=timestamp,
                symbol=symbol,
                evidence={
                    "volume_ratio": round(volume_ratio, 4),
                    "price_change": round(price_change * 100, 4),
                    "large_sell_count": len(large_sells),
                },
            )
        return None
    
    def _detect_support_testing(
        self,
        symbol: str,
        ticks: List[TickData],
        orderbooks: List[OrderBookSnapshot],
        timestamp: datetime,
    ) -> Optional[PatternDetection]:
        """
        檢測測試支撐模式
        
        條件：賣壓大但價格守穩，買單吸收賣單
        """
        th = self.thresholds
        window_sec = th.support_test_time_window_sec
        
        start_time = timestamp - timedelta(seconds=window_sec)
        window_ticks = [t for t in ticks if start_time <= t.timestamp <= timestamp]
        
        if len(window_ticks) < 5:
            return None
        
        # 計算賣壓
        sell_ticks = [t for t in window_ticks if t.direction == "SELL"]
        total_volume = sum(t.volume for t in window_ticks)
        sell_volume = sum(t.volume for t in sell_ticks)
        
        if total_volume == 0:
            return None
        
        sell_pressure = sell_volume / total_volume
        
        # 計算價格恢復
        prices = [t.price for t in window_ticks]
        min_price = min(prices)
        final_price = prices[-1]
        start_price = prices[0]
        
        if min_price > 0 and start_price > 0:
            # 價格曾下跌但恢復
            dip = (min_price - start_price) / start_price
            recovery = (final_price - min_price) / min_price if min_price > 0 else 0
            
            if (sell_pressure >= th.support_test_sell_pressure and
                dip < -0.002 and  # 曾下跌超過0.2%
                recovery >= th.support_test_price_recovery):
                
                confidence = (sell_pressure * 0.4 + min(recovery / 0.005, 1) * 0.6)
                strength = min(abs(dip) / 0.01, 1.0)
                
                return PatternDetection(
                    pattern=MarketPattern.SUPPORT_TESTING,
                    confidence=confidence,
                    strength=strength,
                    timestamp=timestamp,
                    symbol=symbol,
                    evidence={
                        "sell_pressure": round(sell_pressure, 4),
                        "price_dip": round(dip * 100, 4),
                        "price_recovery": round(recovery * 100, 4),
                    },
                )
        return None
    
    def _detect_resistance_testing(
        self,
        symbol: str,
        ticks: List[TickData],
        orderbooks: List[OrderBookSnapshot],
        timestamp: datetime,
    ) -> Optional[PatternDetection]:
        """檢測測試阻力模式"""
        th = self.thresholds
        window_sec = th.resistance_test_time_window_sec
        
        start_time = timestamp - timedelta(seconds=window_sec)
        window_ticks = [t for t in ticks if start_time <= t.timestamp <= timestamp]
        
        if len(window_ticks) < 5:
            return None
        
        buy_ticks = [t for t in window_ticks if t.direction == "BUY"]
        total_volume = sum(t.volume for t in window_ticks)
        buy_volume = sum(t.volume for t in buy_ticks)
        
        if total_volume == 0:
            return None
        
        buy_pressure = buy_volume / total_volume
        
        prices = [t.price for t in window_ticks]
        max_price = max(prices)
        final_price = prices[-1]
        start_price = prices[0]
        
        if max_price > 0 and start_price > 0:
            spike = (max_price - start_price) / start_price
            rejection = (max_price - final_price) / max_price if max_price > 0 else 0
            
            if (buy_pressure >= th.resistance_test_buy_pressure and
                spike > 0.002 and rejection >= abs(th.resistance_test_price_rejection)):
                
                confidence = (buy_pressure * 0.4 + min(rejection / 0.005, 1) * 0.6)
                strength = min(spike / 0.01, 1.0)
                
                return PatternDetection(
                    pattern=MarketPattern.RESISTANCE_TESTING,
                    confidence=confidence,
                    strength=strength,
                    timestamp=timestamp,
                    symbol=symbol,
                    evidence={
                        "buy_pressure": round(buy_pressure, 4),
                        "price_spike": round(spike * 100, 4),
                        "price_rejection": round(rejection * 100, 4),
                    },
                )
        return None
    
    def _detect_liquidity_drying(
        self,
        symbol: str,
        ticks: List[TickData],
        orderbooks: List[OrderBookSnapshot],
        timestamp: datetime,
    ) -> Optional[PatternDetection]:
        """檢測流動性枯竭模式"""
        th = self.thresholds
        
        if len(orderbooks) < 2 or len(ticks) < 3:
            return None
        
        # 比較早期和近期訂單簿深度
        early_ob = orderbooks[0]
        recent_ob = orderbooks[-1]
        
        early_depth = sum(early_ob.bid_volumes) + sum(early_ob.ask_volumes)
        recent_depth = sum(recent_ob.bid_volumes) + sum(recent_ob.ask_volumes)
        
        if early_depth == 0:
            return None
        
        depth_ratio = recent_depth / early_depth
        
        # 價差變化
        early_spread = early_ob.spread
        recent_spread = recent_ob.spread
        
        spread_increase = (recent_spread / early_spread) if early_spread > 0 else 1
        
        # 成交間隔變化
        if len(ticks) >= 4:
            mid = len(ticks) // 2
            early_intervals = [
                (ticks[i].timestamp - ticks[i-1].timestamp).total_seconds()
                for i in range(1, mid)
            ]
            recent_intervals = [
                (ticks[i].timestamp - ticks[i-1].timestamp).total_seconds()
                for i in range(mid + 1, len(ticks))
            ]
            
            avg_early = sum(early_intervals) / len(early_intervals) if early_intervals else 1
            avg_recent = sum(recent_intervals) / len(recent_intervals) if recent_intervals else 1
            interval_increase = avg_recent / avg_early if avg_early > 0 else 1
        else:
            interval_increase = 1
        
        if (spread_increase >= th.liquidity_dry_spread_increase or
            depth_ratio <= th.liquidity_dry_depth_decrease or
            interval_increase >= th.liquidity_dry_tick_interval_increase):
            
            confidence = (max(spread_increase / 2, 0.5) * 0.3 +
                         max(1 - depth_ratio, 0.3) * 0.4 +
                         min(interval_increase / 3, 0.5) * 0.3)
            
            return PatternDetection(
                pattern=MarketPattern.LIQUIDITY_DRYING,
                confidence=min(confidence, 0.95),
                strength=min(1 - depth_ratio, 1.0),
                timestamp=timestamp,
                symbol=symbol,
                evidence={
                    "spread_increase": round(spread_increase, 4),
                    "depth_ratio": round(depth_ratio, 4),
                    "interval_increase": round(interval_increase, 4),
                },
            )
        return None
    
    def _detect_fake_out(
        self,
        symbol: str,
        ticks: List[TickData],
        timestamp: datetime,
    ) -> Optional[PatternDetection]:
        """檢測假突破模式"""
        th = self.thresholds
        window_sec = th.fakeout_time_window_sec
        
        start_time = timestamp - timedelta(seconds=window_sec)
        window_ticks = [t for t in ticks if start_time <= t.timestamp <= timestamp]
        
        if len(window_ticks) < 5:
            return None
        
        prices = [t.price for t in window_ticks]
        start_price = prices[0]
        
        if start_price == 0:
            return None
        
        # 尋找極值點
        max_idx = prices.index(max(prices))
        min_idx = prices.index(min(prices))
        
        # 假突破上漲：先漲後跌
        if max_idx < len(prices) - 2:  # 高點不在最後
            initial_move = (prices[max_idx] - start_price) / start_price
            reversal = (prices[-1] - prices[max_idx]) / prices[max_idx]
            
            if (initial_move >= th.fakeout_initial_move and
                reversal <= th.fakeout_reversal_move):
                
                confidence = min(initial_move / 0.01, 1.0) * 0.5 + min(abs(reversal) / 0.01, 1.0) * 0.5
                
                return PatternDetection(
                    pattern=MarketPattern.FAKE_OUT,
                    confidence=confidence,
                    strength=abs(reversal),
                    timestamp=timestamp,
                    symbol=symbol,
                    evidence={
                        "initial_move": round(initial_move * 100, 4),
                        "reversal": round(reversal * 100, 4),
                        "direction": "UP_THEN_DOWN",
                    },
                )
        
        # 假突破下跌：先跌後漲
        if min_idx < len(prices) - 2:
            initial_move = (prices[min_idx] - start_price) / start_price
            reversal = (prices[-1] - prices[min_idx]) / prices[min_idx]
            
            if (initial_move <= -th.fakeout_initial_move and
                reversal >= abs(th.fakeout_reversal_move)):
                
                confidence = min(abs(initial_move) / 0.01, 1.0) * 0.5 + min(reversal / 0.01, 1.0) * 0.5
                
                return PatternDetection(
                    pattern=MarketPattern.FAKE_OUT,
                    confidence=confidence,
                    strength=reversal,
                    timestamp=timestamp,
                    symbol=symbol,
                    evidence={
                        "initial_move": round(initial_move * 100, 4),
                        "reversal": round(reversal * 100, 4),
                        "direction": "DOWN_THEN_UP",
                    },
                )
        return None
    
    def get_primary_pattern(
        self, 
        detections: List[PatternDetection]
    ) -> PatternDetection:
        """獲取主要模式（信心度最高者）"""
        if not detections:
            return PatternDetection(
                pattern=MarketPattern.NEUTRAL,
                confidence=0.5,
                strength=0.0,
                timestamp=datetime.now(),
                symbol="",
            )
        return max(detections, key=lambda d: d.confidence * d.strength)
    
    def get_detection_history(self, limit: int = 100) -> List[Dict]:
        """獲取檢測歷史"""
        return [d.to_dict() for d in self._detection_history[-limit:]]
    
    def clear_history(self):
        """清除歷史記錄"""
        self._detection_history.clear()
