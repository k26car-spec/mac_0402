"""
市場微觀模式定義
Market Micro-pattern Definitions

定義6種核心市場行為模式，這些模式比純價格預測更有交易意義

模式說明：
1. AGGRESSIVE_BUYING: 積極買盤攻擊 - 大量主動買入
2. AGGRESSIVE_SELLING: 積極賣盤攻擊 - 大量主動賣出
3. SUPPORT_TESTING: 測試支撐 - 賣單被吸收，價格守穩
4. RESISTANCE_TESTING: 測試阻力 - 買單被吸收，價格受壓
5. LIQUIDITY_DRYING: 流動性枯竭 - 掛單變薄，市場冷清
6. FAKE_OUT: 假突破 - 大單撤單或快速反轉
"""

from enum import Enum, IntEnum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


class MarketPattern(IntEnum):
    """市場微觀模式枚舉"""
    AGGRESSIVE_BUYING = 0      # 積極買盤攻擊
    AGGRESSIVE_SELLING = 1     # 積極賣盤攻擊
    SUPPORT_TESTING = 2        # 測試支撐（賣單被吸收）
    RESISTANCE_TESTING = 3     # 測試阻力（買單被吸收）
    LIQUIDITY_DRYING = 4       # 流動性枯竭（掛單變薄）
    FAKE_OUT = 5               # 假突破（大單撤單/反轉）
    NEUTRAL = 6                # 中性/無明顯模式


# 模式名稱映射（繁體中文）
MARKET_MICRO_PATTERNS: Dict[int, str] = {
    MarketPattern.AGGRESSIVE_BUYING: "積極買盤攻擊",
    MarketPattern.AGGRESSIVE_SELLING: "積極賣盤攻擊",
    MarketPattern.SUPPORT_TESTING: "測試支撐",
    MarketPattern.RESISTANCE_TESTING: "測試阻力",
    MarketPattern.LIQUIDITY_DRYING: "流動性枯竭",
    MarketPattern.FAKE_OUT: "假突破",
    MarketPattern.NEUTRAL: "中性",
}

# 模式對應的交易建議
PATTERN_TRADING_HINTS: Dict[int, Dict[str, Any]] = {
    MarketPattern.AGGRESSIVE_BUYING: {
        "action": "BUY",
        "urgency": "HIGH",
        "description": "主力積極進場，可考慮跟進",
        "risk_level": "MEDIUM",
    },
    MarketPattern.AGGRESSIVE_SELLING: {
        "action": "SELL",
        "urgency": "HIGH",
        "description": "主力積極出貨，注意風險",
        "risk_level": "HIGH",
    },
    MarketPattern.SUPPORT_TESTING: {
        "action": "WATCH_FOR_BUY",
        "urgency": "MEDIUM",
        "description": "支撐位測試中，守穩可布局",
        "risk_level": "LOW",
    },
    MarketPattern.RESISTANCE_TESTING: {
        "action": "WATCH_FOR_SELL",
        "urgency": "MEDIUM",
        "description": "阻力位測試中，突破可追進",
        "risk_level": "MEDIUM",
    },
    MarketPattern.LIQUIDITY_DRYING: {
        "action": "WAIT",
        "urgency": "LOW",
        "description": "流動性不足，避免大單操作",
        "risk_level": "HIGH",
    },
    MarketPattern.FAKE_OUT: {
        "action": "REVERSE",
        "urgency": "HIGH",
        "description": "假突破信號，可能反向操作",
        "risk_level": "HIGH",
    },
    MarketPattern.NEUTRAL: {
        "action": "HOLD",
        "urgency": "LOW",
        "description": "無明顯信號，維持觀望",
        "risk_level": "LOW",
    },
}


@dataclass
class PatternThresholds:
    """
    模式識別閾值配置
    
    這些閾值需要根據實際市場數據進行調整
    建議：使用回測數據找到最優閾值
    """
    
    # ===== 積極買盤攻擊閾值 =====
    aggressive_buy_volume_ratio: float = 0.70        # 大量買入佔比 (>70%)
    aggressive_buy_price_change: float = 0.003       # 價格上漲幅度 (>0.3%)
    aggressive_buy_min_large_orders: int = 3         # 最少大單筆數
    aggressive_buy_time_window_sec: int = 30         # 時間窗口（秒）
    
    # ===== 積極賣盤攻擊閾值 =====
    aggressive_sell_volume_ratio: float = 0.70       # 大量賣出佔比 (>70%)
    aggressive_sell_price_change: float = -0.003     # 價格下跌幅度 (<-0.3%)
    aggressive_sell_min_large_orders: int = 3        # 最少大單筆數
    aggressive_sell_time_window_sec: int = 30        # 時間窗口（秒）
    
    # ===== 測試支撐閾值 =====
    support_test_sell_pressure: float = 0.60         # 賣壓佔比 (>60%)
    support_test_price_recovery: float = 0.001       # 價格恢復幅度 (>0.1%)
    support_test_absorption_ratio: float = 0.50      # 賣單被吸收比例 (>50%)
    support_test_time_window_sec: int = 60           # 時間窗口（秒）
    
    # ===== 測試阻力閾值 =====
    resistance_test_buy_pressure: float = 0.60       # 買壓佔比 (>60%)
    resistance_test_price_rejection: float = -0.001  # 價格回落幅度 (<-0.1%)
    resistance_test_absorption_ratio: float = 0.50   # 買單被吸收比例 (>50%)
    resistance_test_time_window_sec: int = 60        # 時間窗口（秒）
    
    # ===== 流動性枯竭閾值 =====
    liquidity_dry_spread_increase: float = 1.5       # 價差擴大倍數 (>1.5x)
    liquidity_dry_depth_decrease: float = 0.50       # 掛單深度減少 (<50%)
    liquidity_dry_tick_interval_increase: float = 2.0  # 成交間隔增加倍數 (>2x)
    liquidity_dry_time_window_sec: int = 120         # 時間窗口（秒）
    
    # ===== 假突破閾值 =====
    fakeout_initial_move: float = 0.005              # 初始突破幅度 (>0.5%)
    fakeout_reversal_move: float = -0.003            # 反轉幅度 (<-0.3%)
    fakeout_large_order_cancel_ratio: float = 0.30   # 大單撤單比例 (>30%)
    fakeout_time_window_sec: int = 60                # 時間窗口（秒）
    
    # ===== 大單定義 =====
    large_order_volume_threshold: int = 100          # 大單門檻（張）- 需根據個股調整
    large_order_value_threshold: float = 5000000     # 大單金額門檻（台幣）
    
    # ===== 通用閾值 =====
    min_confidence: float = 0.60                     # 最低信心度
    min_pattern_strength: float = 0.50               # 最低模式強度


@dataclass
class PatternDetection:
    """
    模式偵測結果
    """
    pattern: MarketPattern
    confidence: float                      # 信心度 (0-1)
    strength: float                        # 強度 (0-1)
    timestamp: datetime
    symbol: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    trading_hint: Dict[str, Any] = field(default_factory=dict)
    raw_features: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """自動填充交易建議"""
        if not self.trading_hint:
            self.trading_hint = PATTERN_TRADING_HINTS.get(
                self.pattern, 
                PATTERN_TRADING_HINTS[MarketPattern.NEUTRAL]
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "pattern": self.pattern.value,
            "pattern_name": MARKET_MICRO_PATTERNS.get(self.pattern, "未知"),
            "confidence": round(self.confidence, 4),
            "strength": round(self.strength, 4),
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "evidence": self.evidence,
            "trading_hint": self.trading_hint,
        }
    
    @property
    def is_bullish(self) -> bool:
        """是否為看多信號"""
        return self.pattern in [
            MarketPattern.AGGRESSIVE_BUYING,
            MarketPattern.SUPPORT_TESTING,
        ]
    
    @property
    def is_bearish(self) -> bool:
        """是否為看空信號"""
        return self.pattern in [
            MarketPattern.AGGRESSIVE_SELLING,
            MarketPattern.RESISTANCE_TESTING,
        ]
    
    @property
    def is_warning(self) -> bool:
        """是否為警告信號"""
        return self.pattern in [
            MarketPattern.LIQUIDITY_DRYING,
            MarketPattern.FAKE_OUT,
        ]


@dataclass
class PatternStatistics:
    """
    模式統計資訊
    """
    total_detections: int = 0
    pattern_counts: Dict[int, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_strength: float = 0.0
    last_update: Optional[datetime] = None
    
    def update(self, detection: PatternDetection):
        """更新統計資訊"""
        self.total_detections += 1
        
        # 更新模式計數
        pattern_key = detection.pattern.value
        self.pattern_counts[pattern_key] = self.pattern_counts.get(pattern_key, 0) + 1
        
        # 更新平均信心度和強度（滾動平均）
        n = self.total_detections
        self.avg_confidence = ((n - 1) * self.avg_confidence + detection.confidence) / n
        self.avg_strength = ((n - 1) * self.avg_strength + detection.strength) / n
        
        self.last_update = datetime.now()
    
    def get_dominant_pattern(self) -> Optional[MarketPattern]:
        """獲取主導模式"""
        if not self.pattern_counts:
            return None
        
        max_pattern = max(self.pattern_counts.items(), key=lambda x: x[1])
        return MarketPattern(max_pattern[0])
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "total_detections": self.total_detections,
            "pattern_counts": {
                MARKET_MICRO_PATTERNS.get(MarketPattern(k), "未知"): v
                for k, v in self.pattern_counts.items()
            },
            "avg_confidence": round(self.avg_confidence, 4),
            "avg_strength": round(self.avg_strength, 4),
            "dominant_pattern": MARKET_MICRO_PATTERNS.get(
                self.get_dominant_pattern(), "無"
            ) if self.get_dominant_pattern() else "無",
            "last_update": self.last_update.isoformat() if self.last_update else None,
        }
