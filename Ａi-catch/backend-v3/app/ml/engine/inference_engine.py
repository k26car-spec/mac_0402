"""
實時推理引擎
Real-time Inference Engine

整合多個模型進行實時決策：
1. 模式分類器推理
2. 市場狀態分類器推理
3. 決策融合
4. 風險過濾
5. 警報觸發
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, time
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class TradingAction(Enum):
    """交易動作"""
    NO_ACTION = "NO_ACTION"
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    HOLD = "HOLD"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class RiskLevel(Enum):
    """風險等級"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class InferenceConfig:
    """推理配置"""
    # 閾值
    pattern_confidence_threshold: float = 0.6
    state_confidence_threshold: float = 0.6
    action_confidence_threshold: float = 0.7
    
    # 風險過濾
    max_volatility: float = 0.03  # 3%
    min_liquidity_depth: int = 500  # 最低掛單量
    close_market_buffer_minutes: int = 5  # 收盤前緩衝
    
    # 冷卻時間
    signal_cooldown_seconds: int = 60
    
    # 模型權重
    pattern_model_weight: float = 0.6
    state_model_weight: float = 0.4


@dataclass
class Decision:
    """推理決策結果"""
    timestamp: datetime
    symbol: str
    action: TradingAction = TradingAction.NO_ACTION
    confidence: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    primary_signal: Optional[str] = None
    secondary_signals: List[str] = field(default_factory=list)
    market_state: Optional[str] = None
    
    reasoning: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # 風險過濾結果
    filtered: bool = False
    filter_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "action": self.action.value,
            "confidence": round(self.confidence, 4),
            "risk_level": self.risk_level.value,
            "primary_signal": self.primary_signal,
            "secondary_signals": self.secondary_signals,
            "market_state": self.market_state,
            "reasoning": self.reasoning,
            "filtered": self.filtered,
            "filter_reason": self.filter_reason,
        }


class RiskFilter:
    """
    風險過濾器
    
    在生成交易信號前過濾高風險情況
    """
    
    def __init__(self, config: Optional[InferenceConfig] = None):
        self.config = config or InferenceConfig()
    
    def check(
        self,
        symbol: str,
        decision: Decision,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        檢查是否應該過濾此決策
        
        Returns:
            (should_filter, reason)
        """
        market_data = market_data or {}
        
        # 1. 時間過濾（接近收盤）
        now = datetime.now().time()
        close_time = time(13, 30)
        buffer_minutes = self.config.close_market_buffer_minutes
        buffer_time = time(13, 30 - buffer_minutes)
        
        if now >= buffer_time:
            return True, f"接近收盤時間，距離收盤不足 {buffer_minutes} 分鐘"
        
        # 2. 波動率過濾
        volatility = market_data.get("volatility", 0)
        if volatility > self.config.max_volatility:
            return True, f"市場波動率過高 ({volatility:.2%} > {self.config.max_volatility:.2%})"
        
        # 3. 流動性過濾
        liquidity = market_data.get("total_depth", float('inf'))
        if liquidity < self.config.min_liquidity_depth:
            return True, f"流動性不足 ({liquidity} < {self.config.min_liquidity_depth})"
        
        # 4. 極端價格過濾
        price_change = abs(market_data.get("price_change_pct", 0))
        if price_change > 0.05:  # 漲跌幅超過 5%
            return True, f"價格變動過大 ({price_change:.2%})"
        
        # 5. 資訊不足過濾
        if decision.confidence < 0.4:
            return True, f"信心度過低 ({decision.confidence:.2%})"
        
        return False, None


class DecisionFusion:
    """
    決策融合器
    
    整合多個模型的輸出產生最終決策
    """
    
    def __init__(self, config: Optional[InferenceConfig] = None):
        self.config = config or InferenceConfig()
        
        # 模式到動作的映射
        self._pattern_action_map = {
            "AGGRESSIVE_BUYING": TradingAction.BUY,
            "AGGRESSIVE_SELLING": TradingAction.SELL,
            "SUPPORT_TESTING": TradingAction.WEAK_BUY,
            "RESISTANCE_TESTING": TradingAction.WEAK_SELL,
            "LIQUIDITY_DRYING": TradingAction.NO_ACTION,
            "FAKE_OUT": TradingAction.HOLD,
            "NEUTRAL": TradingAction.HOLD,
        }
        
        # 狀態到動作的映射
        self._state_action_map = {
            "TRENDING_UP": TradingAction.BUY,
            "TRENDING_DOWN": TradingAction.SELL,
            "RANGING": TradingAction.HOLD,
            "VOLATILE": TradingAction.NO_ACTION,
            "QUIET": TradingAction.HOLD,
            "BREAKOUT": TradingAction.WEAK_BUY,
        }
    
    def fuse(
        self,
        symbol: str,
        pattern_result: Dict[str, Any],
        state_result: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """
        融合多個模型結果
        
        Args:
            symbol: 股票代碼
            pattern_result: 模式檢測結果
            state_result: 市場狀態分類結果
        
        Returns:
            融合後的決策
        """
        decision = Decision(
            timestamp=datetime.now(),
            symbol=symbol,
        )
        
        signal_strength = {}
        
        # 處理模式檢測結果
        if pattern_result.get("success"):
            primary_pattern = pattern_result.get("primary_pattern", {})
            pattern_name = primary_pattern.get("pattern_name", "中性")
            pattern_confidence = primary_pattern.get("confidence", 0)
            
            if pattern_confidence >= self.config.pattern_confidence_threshold:
                decision.primary_signal = pattern_name
                
                # 映射到動作
                pattern_key = primary_pattern.get("pattern", "NEUTRAL")
                if isinstance(pattern_key, int):
                    pattern_key = ["AGGRESSIVE_BUYING", "AGGRESSIVE_SELLING", 
                                  "SUPPORT_TESTING", "RESISTANCE_TESTING",
                                  "LIQUIDITY_DRYING", "FAKE_OUT", "NEUTRAL"][pattern_key]
                
                action = self._pattern_action_map.get(pattern_key, TradingAction.HOLD)
                signal_strength[action] = pattern_confidence * self.config.pattern_model_weight
                
                decision.confidence += pattern_confidence * self.config.pattern_model_weight
        
        # 處理市場狀態結果
        if state_result and state_result.get("success"):
            state_name = state_result.get("state_name", "RANGING")
            state_confidence = state_result.get("confidence", 0)
            
            if state_confidence >= self.config.state_confidence_threshold:
                decision.market_state = state_name
                
                action = self._state_action_map.get(state_name, TradingAction.HOLD)
                signal_strength[action] = signal_strength.get(action, 0) + (
                    state_confidence * self.config.state_model_weight
                )
                
                decision.confidence += state_confidence * self.config.state_model_weight
        
        # 確定最終動作
        if signal_strength:
            best_action = max(signal_strength.items(), key=lambda x: x[1])
            decision.action = best_action[0]
        
        # 確定風險等級
        decision.risk_level = self._determine_risk_level(decision, pattern_result)
        
        # 生成推理說明
        decision.reasoning = self._generate_reasoning(decision, pattern_result)
        
        return decision
    
    def _determine_risk_level(
        self,
        decision: Decision,
        pattern_result: Dict[str, Any],
    ) -> RiskLevel:
        """確定風險等級"""
        # 根據動作類型
        strong_actions = [TradingAction.STRONG_BUY, TradingAction.STRONG_SELL]
        weak_actions = [TradingAction.WEAK_BUY, TradingAction.WEAK_SELL]
        
        if decision.action in strong_actions:
            if decision.confidence > 0.8:
                return RiskLevel.LOW
            else:
                return RiskLevel.MEDIUM
        elif decision.action in weak_actions:
            return RiskLevel.HIGH
        
        # 檢查警告模式
        primary_pattern = pattern_result.get("primary_pattern", {})
        pattern_name = primary_pattern.get("pattern_name", "")
        
        if pattern_name in ["流動性枯竭", "假突破"]:
            return RiskLevel.HIGH
        
        return RiskLevel.MEDIUM
    
    def _generate_reasoning(
        self,
        decision: Decision,
        pattern_result: Dict[str, Any],
    ) -> str:
        """生成推理說明"""
        parts = []
        
        if decision.primary_signal:
            parts.append(f"檢測到 {decision.primary_signal} 模式")
        
        if decision.market_state:
            parts.append(f"市場處於 {decision.market_state} 狀態")
        
        if decision.action != TradingAction.NO_ACTION:
            action_desc = {
                TradingAction.STRONG_BUY: "強烈建議買入",
                TradingAction.BUY: "建議買入",
                TradingAction.WEAK_BUY: "可考慮小量買入",
                TradingAction.HOLD: "建議持有觀望",
                TradingAction.WEAK_SELL: "可考慮減碼",
                TradingAction.SELL: "建議賣出",
                TradingAction.STRONG_SELL: "強烈建議賣出",
            }
            parts.append(action_desc.get(decision.action, ""))
        
        parts.append(f"信心度: {decision.confidence:.1%}")
        
        return "。".join(parts)


class RealTimeInferenceEngine:
    """
    實時推理引擎
    
    整合模式識別、市場狀態分類和決策融合
    """
    
    def __init__(self, config: Optional[InferenceConfig] = None):
        self.config = config or InferenceConfig()
        self.fusion = DecisionFusion(config)
        self.risk_filter = RiskFilter(config)
        
        # 決策歷史
        self._decision_history: Dict[str, List[Decision]] = {}
        self._last_signal_time: Dict[str, datetime] = {}
        
        # 警報回調
        self._alert_callbacks: List[Callable] = []
    
    def process(
        self,
        symbol: str,
        pattern_result: Dict[str, Any],
        state_result: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """
        處理新數據並產生決策
        
        Args:
            symbol: 股票代碼
            pattern_result: 模式檢測結果
            state_result: 市場狀態分類結果
            market_data: 市場數據（用於風險過濾）
        
        Returns:
            決策結果
        """
        # 1. 決策融合
        decision = self.fusion.fuse(symbol, pattern_result, state_result)
        
        # 2. 冷卻時間檢查
        last_time = self._last_signal_time.get(symbol)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < self.config.signal_cooldown_seconds:
                decision.filtered = True
                decision.filter_reason = f"冷卻時間內 ({elapsed:.0f}s < {self.config.signal_cooldown_seconds}s)"
        
        # 3. 風險過濾
        if not decision.filtered:
            should_filter, reason = self.risk_filter.check(symbol, decision, market_data)
            if should_filter:
                decision.filtered = True
                decision.filter_reason = reason
        
        # 4. 記錄決策
        self._record_decision(symbol, decision)
        
        # 5. 觸發警報
        if self._should_alert(decision):
            self._trigger_alerts(decision)
        
        return decision
    
    def _record_decision(self, symbol: str, decision: Decision):
        """記錄決策"""
        if symbol not in self._decision_history:
            self._decision_history[symbol] = []
        
        self._decision_history[symbol].append(decision)
        
        # 限制歷史大小
        if len(self._decision_history[symbol]) > 100:
            self._decision_history[symbol] = self._decision_history[symbol][-100:]
        
        # 更新最後信號時間
        if not decision.filtered and decision.action not in [TradingAction.NO_ACTION, TradingAction.HOLD]:
            self._last_signal_time[symbol] = decision.timestamp
    
    def _should_alert(self, decision: Decision) -> bool:
        """判斷是否應該觸發警報"""
        if decision.filtered:
            return False
        
        strong_actions = [
            TradingAction.STRONG_BUY, 
            TradingAction.STRONG_SELL,
            TradingAction.BUY,
            TradingAction.SELL,
        ]
        
        return (
            decision.action in strong_actions and
            decision.confidence >= self.config.action_confidence_threshold
        )
    
    def _trigger_alerts(self, decision: Decision):
        """觸發警報"""
        for callback in self._alert_callbacks:
            try:
                callback(decision)
            except Exception as e:
                logger.error(f"警報回調失敗: {e}")
    
    def register_alert_callback(self, callback: Callable):
        """註冊警報回調"""
        self._alert_callbacks.append(callback)
    
    def get_decision_history(
        self,
        symbol: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """獲取決策歷史"""
        history = self._decision_history.get(symbol, [])
        return [d.to_dict() for d in history[-limit:]]
    
    def get_stats(self, symbol: str) -> Dict[str, Any]:
        """獲取統計資訊"""
        history = self._decision_history.get(symbol, [])
        
        if not history:
            return {"error": "無歷史數據"}
        
        # 統計各動作次數
        action_counts = {}
        filtered_count = 0
        total_confidence = 0
        
        for d in history:
            action = d.action.value
            action_counts[action] = action_counts.get(action, 0) + 1
            
            if d.filtered:
                filtered_count += 1
            
            total_confidence += d.confidence
        
        return {
            "total_decisions": len(history),
            "filtered_count": filtered_count,
            "filter_rate": filtered_count / len(history),
            "avg_confidence": total_confidence / len(history),
            "action_distribution": action_counts,
            "last_decision": history[-1].to_dict() if history else None,
        }
