"""
訂單流服務
Order Flow Service

整合訂單流模式識別系統到現有 API
提供實時模式檢測和歷史分析功能
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.ml.order_flow import (
    MarketPattern,
    MARKET_MICRO_PATTERNS,
    PatternThresholds,
    OrderFlowFeatureExtractor,
    PatternLabeler,
    OrderFlowDataset,
)
from app.ml.order_flow.features import TickData, OrderBookSnapshot
from app.ml.order_flow.patterns import PatternDetection, PatternStatistics

logger = logging.getLogger(__name__)


class OrderFlowService:
    """
    訂單流服務
    
    整合模式識別系統，提供：
    1. 實時模式檢測
    2. 特徵提取
    3. 歷史分析
    4. 與現有 API 的整合
    """
    
    def __init__(
        self,
        thresholds: Optional[PatternThresholds] = None,
        large_order_threshold: int = 100,
    ):
        self.thresholds = thresholds or PatternThresholds()
        self.large_order_threshold = large_order_threshold
        
        # 各股票的特徵提取器和標註器
        self._extractors: Dict[str, OrderFlowFeatureExtractor] = {}
        self._labelers: Dict[str, PatternLabeler] = {}
        self._statistics: Dict[str, PatternStatistics] = {}
        
        # 最近檢測結果緩存
        self._recent_detections: Dict[str, List[PatternDetection]] = {}
        self._max_cache_size = 100
        
        logger.info("✅ 訂單流服務初始化完成")
    
    def _get_extractor(self, symbol: str) -> OrderFlowFeatureExtractor:
        """獲取或創建股票的特徵提取器"""
        if symbol not in self._extractors:
            self._extractors[symbol] = OrderFlowFeatureExtractor(
                large_order_threshold=self.large_order_threshold
            )
        return self._extractors[symbol]
    
    def _get_labeler(self, symbol: str) -> PatternLabeler:
        """獲取或創建股票的模式標註器"""
        if symbol not in self._labelers:
            self._labelers[symbol] = PatternLabeler(
                thresholds=self.thresholds,
                feature_extractor=self._get_extractor(symbol),
            )
        return self._labelers[symbol]
    
    def _get_statistics(self, symbol: str) -> PatternStatistics:
        """獲取或創建股票的統計資訊"""
        if symbol not in self._statistics:
            self._statistics[symbol] = PatternStatistics()
        return self._statistics[symbol]
    
    async def process_realtime_quote(
        self,
        symbol: str,
        quote_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        處理實時報價數據
        
        從報價中提取特徵並更新緩衝區
        """
        extractor = self._get_extractor(symbol)
        
        tick = extractor.parse_api_quote(quote_data)
        if tick:
            extractor.add_tick(tick)
            
            return {
                "success": True,
                "symbol": symbol,
                "tick_added": True,
                "buffer_size": extractor.get_buffer_stats()["tick_count"],
            }
        
        return {"success": False, "error": "無法解析報價數據"}
    
    async def process_orderbook(
        self,
        symbol: str,
        orderbook_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理五檔訂單簿數據"""
        extractor = self._get_extractor(symbol)
        
        snapshot = extractor.parse_api_orderbook(orderbook_data)
        if snapshot:
            extractor.add_orderbook(snapshot)
            
            return {
                "success": True,
                "symbol": symbol,
                "orderbook_added": True,
                "buffer_size": extractor.get_buffer_stats()["orderbook_count"],
            }
        
        return {"success": False, "error": "無法解析訂單簿數據"}
    
    async def detect_patterns(
        self,
        symbol: str,
        include_features: bool = False,
    ) -> Dict[str, Any]:
        """
        檢測當前市場模式
        
        Returns:
            包含檢測結果的字典
        """
        extractor = self._get_extractor(symbol)
        labeler = self._get_labeler(symbol)
        stats = self._get_statistics(symbol)
        
        # 獲取緩衝區數據
        ticks = extractor._tick_buffer
        orderbooks = extractor._orderbook_buffer
        
        if len(ticks) < 5:
            return {
                "success": False,
                "error": "數據量不足，需要更多成交數據",
                "buffer_stats": extractor.get_buffer_stats(),
            }
        
        # 執行模式檢測
        timestamp = datetime.now()
        detections = labeler.detect_patterns(
            symbol=symbol,
            ticks=ticks,
            orderbooks=orderbooks,
            timestamp=timestamp,
        )
        
        # 更新統計
        for det in detections:
            stats.update(det)
        
        # 緩存結果
        if symbol not in self._recent_detections:
            self._recent_detections[symbol] = []
        self._recent_detections[symbol].extend(detections)
        
        # 限制緩存大小
        if len(self._recent_detections[symbol]) > self._max_cache_size:
            self._recent_detections[symbol] = self._recent_detections[symbol][-self._max_cache_size:]
        
        # 獲取主要模式
        primary = labeler.get_primary_pattern(detections)
        
        # 🆕 自動記錄預測到準確率評估器
        try:
            from app.ml.order_flow.accuracy_evaluator import accuracy_evaluator
            
            # 獲取當前價格作為入場價
            entry_price = 0.0
            if ticks:
                entry_price = ticks[-1].price
            
            # 只記錄非中性且有意義的預測
            pattern_dict = primary.to_dict()
            if primary.pattern.value != 6 and primary.confidence >= 0.6:  # 非中性且信心度>=60%
                accuracy_evaluator.record_prediction(
                    symbol=symbol,
                    pattern=pattern_dict.get("pattern", ""),
                    pattern_name=pattern_dict.get("pattern_name", ""),
                    confidence=primary.confidence,
                    action=pattern_dict.get("trading_hint", {}).get("action", "HOLD"),
                    entry_price=entry_price,
                    timestamp=timestamp,
                )
        except Exception as e:
            logger.debug(f"記錄預測失敗: {e}")
        
        result = {
            "success": True,
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
            "primary_pattern": primary.to_dict(),
            "all_patterns": [d.to_dict() for d in detections],
            "pattern_count": len(detections),
            "statistics": stats.to_dict(),
        }
        
        if include_features:
            features = extractor.extract_features(timestamp)
            result["features"] = {k: round(v, 6) for k, v in features.items()}
        
        return result
    
    async def get_features(
        self,
        symbol: str,
    ) -> Dict[str, Any]:
        """獲取當前特徵向量"""
        extractor = self._get_extractor(symbol)
        
        if len(extractor._tick_buffer) < 2:
            return {
                "success": False,
                "error": "數據量不足",
            }
        
        features = extractor.extract_features()
        
        return {
            "success": True,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "features": {k: round(v, 6) for k, v in features.items()},
            "feature_count": len(features),
            "buffer_stats": extractor.get_buffer_stats(),
        }
    
    async def get_pattern_history(
        self,
        symbol: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """獲取模式檢測歷史"""
        detections = self._recent_detections.get(symbol, [])
        
        return {
            "success": True,
            "symbol": symbol,
            "history": [d.to_dict() for d in detections[-limit:]],
            "total_count": len(detections),
        }
    
    async def get_statistics(
        self,
        symbol: str,
    ) -> Dict[str, Any]:
        """獲取統計資訊"""
        stats = self._get_statistics(symbol)
        extractor = self._get_extractor(symbol)
        
        return {
            "success": True,
            "symbol": symbol,
            "statistics": stats.to_dict(),
            "buffer_stats": extractor.get_buffer_stats(),
        }
    
    async def analyze_with_existing_data(
        self,
        symbol: str,
        quote_data: Dict[str, Any],
        orderbook_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        使用現有 API 數據進行完整分析
        
        整合報價和五檔數據，執行模式檢測
        """
        # 處理報價
        await self.process_realtime_quote(symbol, quote_data)
        
        # 處理五檔
        await self.process_orderbook(symbol, orderbook_data)
        
        # 檢測模式
        result = await self.detect_patterns(symbol, include_features=True)
        
        # 添加原始數據摘要
        result["input_data"] = {
            "quote_price": quote_data.get("price"),
            "quote_volume": quote_data.get("volume"),
            "orderbook_spread": orderbook_data.get("asks", [{}])[0].get("price", 0) - 
                               orderbook_data.get("bids", [{}])[0].get("price", 0)
                               if orderbook_data.get("bids") and orderbook_data.get("asks") else 0,
        }
        
        return result
    
    def reset_symbol(self, symbol: str):
        """重置指定股票的所有緩衝區和統計"""
        if symbol in self._extractors:
            self._extractors[symbol].reset_buffers()
        if symbol in self._statistics:
            self._statistics[symbol] = PatternStatistics()
        if symbol in self._recent_detections:
            self._recent_detections[symbol] = []
        
        logger.info(f"已重置 {symbol} 的訂單流數據")
    
    def get_monitored_symbols(self) -> List[str]:
        """獲取正在監控的股票列表"""
        return list(self._extractors.keys())
    
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        return {
            "monitored_symbols": len(self._extractors),
            "symbols": self.get_monitored_symbols(),
            "thresholds": {
                "large_order_volume": self.thresholds.large_order_volume_threshold,
                "min_confidence": self.thresholds.min_confidence,
            },
            "timestamp": datetime.now().isoformat(),
        }


# 全域服務實例
order_flow_service = OrderFlowService()


# ==================== 便捷函數 ====================

async def analyze_order_flow(
    symbol: str,
    quote_data: Dict[str, Any],
    orderbook_data: Dict[str, Any],
) -> Dict[str, Any]:
    """使用訂單流分析股票"""
    return await order_flow_service.analyze_with_existing_data(
        symbol, quote_data, orderbook_data
    )


async def detect_market_pattern(symbol: str) -> Dict[str, Any]:
    """檢測市場模式"""
    return await order_flow_service.detect_patterns(symbol)


async def get_order_flow_features(symbol: str) -> Dict[str, Any]:
    """獲取訂單流特徵"""
    return await order_flow_service.get_features(symbol)
