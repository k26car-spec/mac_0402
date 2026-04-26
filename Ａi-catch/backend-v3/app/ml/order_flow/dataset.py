"""
訂單流資料集
Order Flow Dataset

用於構建訓練用的時間序列資料集
支援序列化特徵提取和標籤生成
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import json

from .patterns import MarketPattern, PatternThresholds
from .features import TickData, OrderBookSnapshot, OrderFlowFeatureExtractor
from .labeler import PatternLabeler

logger = logging.getLogger(__name__)


@dataclass
class DatasetConfig:
    """資料集配置"""
    sequence_length: int = 100          # 序列長度
    stride: int = 10                    # 滑動步長
    prediction_horizon_sec: int = 10    # 預測前瞻時間（秒）
    train_split: float = 0.7            # 訓練集比例
    val_split: float = 0.15             # 驗證集比例
    min_samples_per_class: int = 50     # 每個類別最少樣本數
    normalize: bool = True              # 是否標準化


class OrderFlowDataset:
    """
    訂單流資料集
    
    創建用於訓練模式識別模型的時間序列資料集
    整合現有 API 數據
    """
    
    def __init__(
        self,
        config: Optional[DatasetConfig] = None,
        thresholds: Optional[PatternThresholds] = None,
    ):
        self.config = config or DatasetConfig()
        self.thresholds = thresholds or PatternThresholds()
        
        self.extractor = OrderFlowFeatureExtractor()
        self.labeler = PatternLabeler(thresholds=self.thresholds)
        
        # 原始數據存儲
        self._ticks: List[TickData] = []
        self._orderbooks: List[OrderBookSnapshot] = []
        
        # 處理後的資料集
        self._sequences: Optional[np.ndarray] = None
        self._labels: Optional[np.ndarray] = None
        self._timestamps: List[datetime] = []
        
        # 標準化參數
        self._feature_means: Optional[np.ndarray] = None
        self._feature_stds: Optional[np.ndarray] = None
        self._feature_names: List[str] = []
    
    def add_raw_data(
        self,
        ticks: List[TickData],
        orderbooks: List[OrderBookSnapshot],
    ):
        """添加原始數據"""
        self._ticks.extend(ticks)
        self._orderbooks.extend(orderbooks)
        
        # 同時更新特徵提取器的緩衝區
        for tick in ticks:
            self.extractor.add_tick(tick)
        for ob in orderbooks:
            self.extractor.add_orderbook(ob)
    
    def add_from_api_data(
        self,
        quote_list: List[Dict[str, Any]],
        orderbook_list: List[Dict[str, Any]],
    ):
        """
        從 API 數據格式添加
        
        支援現有富邦 API 和模擬數據格式
        """
        ticks = []
        orderbooks = []
        
        for q in quote_list:
            tick = self.extractor.parse_api_quote(q)
            if tick:
                ticks.append(tick)
        
        for ob in orderbook_list:
            snapshot = self.extractor.parse_api_orderbook(ob)
            if snapshot:
                orderbooks.append(snapshot)
        
        self.add_raw_data(ticks, orderbooks)
        logger.info(f"添加了 {len(ticks)} 筆成交和 {len(orderbooks)} 個訂單簿快照")
    
    def build_dataset(self, symbol: str = "") -> Tuple[np.ndarray, np.ndarray]:
        """
        構建完整資料集
        
        Returns:
            (sequences, labels) - 特徵序列和標籤
        """
        if len(self._ticks) < self.config.sequence_length + 10:
            raise ValueError(
                f"數據量不足，需要至少 {self.config.sequence_length + 10} 筆成交，"
                f"目前只有 {len(self._ticks)} 筆"
            )
        
        # 按時間排序
        self._ticks.sort(key=lambda t: t.timestamp)
        self._orderbooks.sort(key=lambda ob: ob.timestamp)
        
        # 獲取時間戳列表
        timestamps = [t.timestamp for t in self._ticks]
        
        sequences = []
        labels = []
        self._timestamps = []
        
        config = self.config
        
        for i in range(0, len(timestamps) - config.sequence_length, config.stride):
            seq_end_idx = i + config.sequence_length
            seq_end_time = timestamps[seq_end_idx - 1]
            
            # 提取序列特徵
            seq_features = []
            for j in range(i, seq_end_idx):
                # 對每個時間點提取特徵
                features = self._extract_features_at_index(j)
                seq_features.append(list(features.values()))
                
                # 記錄特徵名稱（只在第一次）
                if not self._feature_names:
                    self._feature_names = list(features.keys())
            
            # 獲取標籤（序列結束後的模式）
            label_time = seq_end_time + timedelta(seconds=config.prediction_horizon_sec)
            
            # 獲取標籤時間點附近的數據
            label_ticks = [
                t for t in self._ticks
                if seq_end_time < t.timestamp <= label_time
            ]
            label_obs = [
                ob for ob in self._orderbooks
                if seq_end_time < ob.timestamp <= label_time
            ]
            
            if label_ticks:
                # 檢測模式
                detections = self.labeler.detect_patterns(
                    symbol=symbol,
                    ticks=label_ticks,
                    orderbooks=label_obs,
                    timestamp=label_time,
                )
                
                # 獲取主要模式
                primary = self.labeler.get_primary_pattern(detections)
                label = primary.pattern.value
            else:
                label = MarketPattern.NEUTRAL.value
            
            sequences.append(seq_features)
            labels.append(label)
            self._timestamps.append(seq_end_time)
        
        # 轉換為 numpy 陣列
        self._sequences = np.array(sequences, dtype=np.float32)
        self._labels = np.array(labels, dtype=np.int32)
        
        # 標準化
        if self.config.normalize:
            self._normalize_features()
        
        logger.info(
            f"資料集構建完成: {len(sequences)} 個樣本, "
            f"序列長度 {config.sequence_length}, "
            f"特徵數 {len(self._feature_names)}"
        )
        
        # 顯示類別分佈
        self._log_class_distribution()
        
        return self._sequences, self._labels
    
    def _extract_features_at_index(self, tick_index: int) -> Dict[str, float]:
        """在指定索引位置提取特徵"""
        if tick_index < 0 or tick_index >= len(self._ticks):
            return {}
        
        timestamp = self._ticks[tick_index].timestamp
        
        # 獲取時間窗口內的數據
        lookback = timedelta(seconds=self.extractor.lookback_seconds)
        start_time = timestamp - lookback
        
        window_ticks = [
            t for t in self._ticks
            if start_time <= t.timestamp <= timestamp
        ]
        window_obs = [
            ob for ob in self._orderbooks
            if start_time <= ob.timestamp <= timestamp
        ]
        
        # 臨時設置緩衝區
        old_tick_buffer = self.extractor._tick_buffer
        old_ob_buffer = self.extractor._orderbook_buffer
        
        self.extractor._tick_buffer = window_ticks
        self.extractor._orderbook_buffer = window_obs
        
        features = self.extractor.extract_features(timestamp)
        
        # 恢復緩衝區
        self.extractor._tick_buffer = old_tick_buffer
        self.extractor._orderbook_buffer = old_ob_buffer
        
        return features
    
    def _normalize_features(self):
        """標準化特徵"""
        if self._sequences is None:
            return
        
        # 計算均值和標準差（沿序列維度展平）
        flat_features = self._sequences.reshape(-1, self._sequences.shape[-1])
        
        self._feature_means = np.mean(flat_features, axis=0)
        self._feature_stds = np.std(flat_features, axis=0)
        
        # 避免除以零
        self._feature_stds = np.where(
            self._feature_stds > 1e-6,
            self._feature_stds,
            1.0
        )
        
        # 標準化
        self._sequences = (self._sequences - self._feature_means) / self._feature_stds
        
        logger.info("特徵標準化完成")
    
    def _log_class_distribution(self):
        """記錄類別分佈"""
        if self._labels is None:
            return
        
        unique, counts = np.unique(self._labels, return_counts=True)
        
        from .patterns import MARKET_MICRO_PATTERNS
        
        logger.info("類別分佈:")
        for label, count in zip(unique, counts):
            name = MARKET_MICRO_PATTERNS.get(MarketPattern(label), "未知")
            pct = count / len(self._labels) * 100
            logger.info(f"  {name}: {count} ({pct:.1f}%)")
    
    def split_dataset(
        self
    ) -> Tuple[Tuple[np.ndarray, np.ndarray], 
               Tuple[np.ndarray, np.ndarray], 
               Tuple[np.ndarray, np.ndarray]]:
        """
        按時間順序分割資料集
        
        Returns:
            (train_X, train_y), (val_X, val_y), (test_X, test_y)
        """
        if self._sequences is None or self._labels is None:
            raise ValueError("請先調用 build_dataset()")
        
        n = len(self._sequences)
        train_end = int(n * self.config.train_split)
        val_end = int(n * (self.config.train_split + self.config.val_split))
        
        train_X = self._sequences[:train_end]
        train_y = self._labels[:train_end]
        
        val_X = self._sequences[train_end:val_end]
        val_y = self._labels[train_end:val_end]
        
        test_X = self._sequences[val_end:]
        test_y = self._labels[val_end:]
        
        logger.info(
            f"資料集分割: 訓練 {len(train_X)}, 驗證 {len(val_X)}, 測試 {len(test_X)}"
        )
        
        return (train_X, train_y), (val_X, val_y), (test_X, test_y)
    
    def get_feature_names(self) -> List[str]:
        """獲取特徵名稱列表"""
        return self._feature_names
    
    def get_class_weights(self) -> Dict[int, float]:
        """計算類別權重（用於處理不平衡）"""
        if self._labels is None:
            return {}
        
        unique, counts = np.unique(self._labels, return_counts=True)
        total = len(self._labels)
        n_classes = len(unique)
        
        weights = {}
        for label, count in zip(unique, counts):
            weights[label] = total / (n_classes * count)
        
        return weights
    
    def save(self, filepath: str):
        """保存資料集到文件"""
        data = {
            "sequences": self._sequences.tolist() if self._sequences is not None else [],
            "labels": self._labels.tolist() if self._labels is not None else [],
            "feature_names": self._feature_names,
            "feature_means": self._feature_means.tolist() if self._feature_means is not None else [],
            "feature_stds": self._feature_stds.tolist() if self._feature_stds is not None else [],
            "config": {
                "sequence_length": self.config.sequence_length,
                "stride": self.config.stride,
                "prediction_horizon_sec": self.config.prediction_horizon_sec,
            },
            "timestamps": [ts.isoformat() for ts in self._timestamps],
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f)
        
        logger.info(f"資料集已保存到 {filepath}")
    
    def load(self, filepath: str):
        """從文件載入資料集"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self._sequences = np.array(data["sequences"], dtype=np.float32) if data["sequences"] else None
        self._labels = np.array(data["labels"], dtype=np.int32) if data["labels"] else None
        self._feature_names = data["feature_names"]
        self._feature_means = np.array(data["feature_means"]) if data["feature_means"] else None
        self._feature_stds = np.array(data["feature_stds"]) if data["feature_stds"] else None
        self._timestamps = [
            datetime.fromisoformat(ts) for ts in data.get("timestamps", [])
        ]
        
        if data.get("config"):
            self.config.sequence_length = data["config"]["sequence_length"]
            self.config.stride = data["config"]["stride"]
            self.config.prediction_horizon_sec = data["config"]["prediction_horizon_sec"]
        
        logger.info(f"資料集已從 {filepath} 載入")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取資料集統計資訊"""
        stats = {
            "total_ticks": len(self._ticks),
            "total_orderbooks": len(self._orderbooks),
            "total_samples": len(self._sequences) if self._sequences is not None else 0,
            "sequence_length": self.config.sequence_length,
            "num_features": len(self._feature_names),
            "feature_names": self._feature_names[:10],  # 只顯示前10個
        }
        
        if self._labels is not None:
            unique, counts = np.unique(self._labels, return_counts=True)
            stats["class_distribution"] = {
                int(label): int(count) for label, count in zip(unique, counts)
            }
        
        if self._timestamps:
            stats["time_range"] = {
                "start": self._timestamps[0].isoformat() if self._timestamps else None,
                "end": self._timestamps[-1].isoformat() if self._timestamps else None,
            }
        
        return stats
