"""
訂單流特徵工程器
Order Flow Feature Extractor

從逐筆成交數據和五檔訂單簿提取高質量特徵用於模式識別
"""

import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


def parse_datetime(value: Any) -> datetime:
    """解析時間字符串，確保返回 naive datetime"""
    if value is None:
        return datetime.now()
    
    if isinstance(value, datetime):
        # 移除時區信息
        return value.replace(tzinfo=None) if value.tzinfo else value
    
    if isinstance(value, str):
        try:
            # 處理帶 Z 後綴的 ISO 格式
            if value.endswith('Z'):
                value = value[:-1]
            # 處理帶時區偏移的格式
            if '+' in value and value.count(':') >= 2:
                # 移除時區部分 (如 +08:00)
                parts = value.rsplit('+', 1)
                if len(parts) == 2 and ':' in parts[1]:
                    value = parts[0]
            
            dt = datetime.fromisoformat(value)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            return datetime.now()
    
    return datetime.now()


@dataclass
class TickData:
    """逐筆成交數據結構"""
    timestamp: datetime
    price: float
    volume: int
    direction: str  # 'BUY' or 'SELL'
    order_type: str = 'NORMAL'  # 'NORMAL', 'LARGE', 'BLOCK'


@dataclass
class OrderBookSnapshot:
    """五檔訂單簿快照"""
    timestamp: datetime
    bids: List[Dict[str, float]]
    asks: List[Dict[str, float]]
    last_price: float = 0
    
    @property
    def bid_volumes(self) -> List[float]:
        return [b.get("volume", 0) for b in self.bids[:5]]
    
    @property
    def ask_volumes(self) -> List[float]:
        return [a.get("volume", 0) for a in self.asks[:5]]
    
    @property
    def spread(self) -> float:
        if self.asks and self.bids:
            return self.asks[0].get("price", 0) - self.bids[0].get("price", 0)
        return 0
    
    @property
    def mid_price(self) -> float:
        if self.asks and self.bids:
            return (self.asks[0].get("price", 0) + self.bids[0].get("price", 0)) / 2
        return self.last_price


class OrderFlowFeatureExtractor:
    """訂單流特徵提取器"""
    
    def __init__(
        self,
        large_order_threshold: int = 100,
        lookback_seconds: int = 60,
    ):
        self.large_order_threshold = large_order_threshold
        self.lookback_seconds = lookback_seconds
        self._tick_buffer: List[TickData] = []
        self._orderbook_buffer: List[OrderBookSnapshot] = []
        self._max_buffer_size = 1000
        self._baseline_spread: Optional[float] = None
        self._baseline_depth: Optional[float] = None
    
    def add_tick(self, tick: TickData):
        self._tick_buffer.append(tick)
        if len(self._tick_buffer) > self._max_buffer_size:
            self._tick_buffer.pop(0)
    
    def add_orderbook(self, snapshot: OrderBookSnapshot):
        self._orderbook_buffer.append(snapshot)
        if len(self._orderbook_buffer) > self._max_buffer_size:
            self._orderbook_buffer.pop(0)
    
    def parse_api_quote(self, quote_data: Dict[str, Any]) -> Optional[TickData]:
        """從現有 API 報價解析為 TickData"""
        try:
            price = quote_data.get("price", 0)
            prev_close = quote_data.get("prevClose", quote_data.get("open", price))
            direction = "BUY" if price >= prev_close else "SELL"
            volume = quote_data.get("volume", 0)
            order_type = "LARGE" if volume >= self.large_order_threshold else "NORMAL"
            
            return TickData(
                timestamp=parse_datetime(quote_data.get("timestamp")),
                price=price, volume=volume, direction=direction, order_type=order_type,
            )
        except Exception as e:
            logger.error(f"解析報價數據失敗: {e}")
            return None
    
    def parse_api_orderbook(self, data: Dict[str, Any]) -> Optional[OrderBookSnapshot]:
        """從現有 API 五檔數據解析"""
        try:
            return OrderBookSnapshot(
                timestamp=parse_datetime(data.get("timestamp")),
                bids=data.get("bids", []),
                asks=data.get("asks", []),
                last_price=data.get("lastPrice", 0),
            )
        except Exception as e:
            logger.error(f"解析訂單簿數據失敗: {e}")
            return None
    
    def extract_features(self, timestamp: Optional[datetime] = None) -> Dict[str, float]:
        """提取完整特徵向量"""
        if timestamp is None:
            timestamp = datetime.now()
        
        start_time = timestamp - timedelta(seconds=self.lookback_seconds)
        ticks = [t for t in self._tick_buffer if start_time <= t.timestamp <= timestamp]
        obs = [ob for ob in self._orderbook_buffer if start_time <= ob.timestamp <= timestamp]
        
        features = {}
        features.update(self._extract_trade_features(ticks))
        features.update(self._extract_orderbook_features(obs))
        features.update(self._extract_momentum_features(ticks))
        features.update(self._extract_time_features(timestamp))
        return features
    
    def _extract_trade_features(self, ticks: List[TickData]) -> Dict[str, float]:
        """提取成交特徵"""
        if not ticks:
            return {"buy_volume_ratio": 0.5, "sell_volume_ratio": 0.5, 
                    "large_net_flow": 0.0, "tick_frequency": 0.0, "trade_imbalance": 0.0}
        
        buy_ticks = [t for t in ticks if t.direction == "BUY"]
        sell_ticks = [t for t in ticks if t.direction == "SELL"]
        
        total_vol = sum(t.volume for t in ticks)
        buy_vol = sum(t.volume for t in buy_ticks)
        sell_vol = sum(t.volume for t in sell_ticks)
        
        large_buy = sum(t.volume for t in buy_ticks if t.volume >= self.large_order_threshold)
        large_sell = sum(t.volume for t in sell_ticks if t.volume >= self.large_order_threshold)
        
        return {
            "buy_volume_ratio": buy_vol / (total_vol + 1e-6),
            "sell_volume_ratio": sell_vol / (total_vol + 1e-6),
            "large_net_flow": (large_buy - large_sell) / (large_buy + large_sell + 1e-6),
            "tick_frequency": len(ticks) / self.lookback_seconds,
            "trade_imbalance": (buy_vol - sell_vol) / (buy_vol + sell_vol + 1e-6),
        }
    
    def _extract_orderbook_features(self, obs: List[OrderBookSnapshot]) -> Dict[str, float]:
        """提取訂單簿特徵"""
        if not obs:
            return {"order_book_imbalance": 0.0, "bid_ask_spread": 0.0, "depth_ratio": 1.0}
        
        latest = obs[-1]
        bid_vol = sum(latest.bid_volumes)
        ask_vol = sum(latest.ask_volumes)
        
        return {
            "order_book_imbalance": (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-6),
            "bid_ask_spread": latest.spread,
            "depth_ratio": bid_vol / (ask_vol + 1e-6),
        }
    
    def _extract_momentum_features(self, ticks: List[TickData]) -> Dict[str, float]:
        """提取動量特徵"""
        if len(ticks) < 2:
            return {"price_return": 0.0, "price_volatility": 0.0, "price_momentum": 0.0}
        
        prices = [t.price for t in ticks]
        return {
            "price_return": (prices[-1] - prices[0]) / (prices[0] + 1e-6),
            "price_volatility": np.std(prices) / (np.mean(prices) + 1e-6),
            "price_momentum": (np.mean(prices[-len(prices)//2:]) - np.mean(prices[:len(prices)//2])) / (np.mean(prices) + 1e-6),
        }
    
    def _extract_time_features(self, ts: datetime) -> Dict[str, float]:
        """提取時間特徵"""
        trading_min = (ts.hour - 9) * 60 + ts.minute
        return {
            "intraday_position": min(max(trading_min / 270, 0), 1),
            "is_open_period": 1.0 if trading_min < 30 else 0.0,
            "is_close_period": 1.0 if trading_min > 240 else 0.0,
        }
    
    def reset_buffers(self):
        self._tick_buffer.clear()
        self._orderbook_buffer.clear()
    
    def get_buffer_stats(self) -> Dict[str, int]:
        """獲取緩衝區統計"""
        return {
            "tick_count": len(self._tick_buffer),
            "orderbook_count": len(self._orderbook_buffer),
            "max_buffer_size": self._max_buffer_size,
        }
