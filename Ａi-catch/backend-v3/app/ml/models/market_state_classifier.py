"""
XGBoost 市場狀態分類器
Market State Classifier using XGBoost

高階特徵工程 + XGBoost 用於：
1. 訂單流衍生特徵
2. 價格-成交量關係特徵
3. 訂單簿動態特徵
4. 市場微觀結構特徵
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

logger = logging.getLogger(__name__)

# 嘗試導入 XGBoost
try:
    import xgboost as xgb
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        classification_report, confusion_matrix
    )
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logger.warning("⚠️ XGBoost 或 scikit-learn 未安裝")


class MarketState(IntEnum):
    """市場狀態枚舉"""
    TRENDING_UP = 0      # 上漲趨勢
    TRENDING_DOWN = 1    # 下跌趨勢
    RANGING = 2          # 區間震盪
    VOLATILE = 3         # 高波動
    QUIET = 4            # 低波動/冷清
    BREAKOUT = 5         # 突破狀態


MARKET_STATE_NAMES = {
    MarketState.TRENDING_UP: "上漲趨勢",
    MarketState.TRENDING_DOWN: "下跌趨勢",
    MarketState.RANGING: "區間震盪",
    MarketState.VOLATILE: "高波動",
    MarketState.QUIET: "低波動",
    MarketState.BREAKOUT: "突破狀態",
}


@dataclass
class XGBConfig:
    """XGBoost 配置"""
    # XGBoost 參數
    max_depth: int = 6
    learning_rate: float = 0.05
    n_estimators: int = 300
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    gamma: float = 0.1
    min_child_weight: int = 3
    reg_alpha: float = 0.1
    reg_lambda: float = 0.1
    
    # 訓練配置
    early_stopping_rounds: int = 20
    cv_folds: int = 5
    random_state: int = 42
    
    # 特徵工程
    use_advanced_features: bool = True


class AdvancedFeatureEngineer:
    """
    高階特徵工程器
    
    創建用於市場狀態分類的進階特徵
    """
    
    def __init__(self):
        self.scaler = StandardScaler() if XGB_AVAILABLE else None
        self._is_fitted = False
    
    def create_features(
        self,
        tick_data: pd.DataFrame,
        orderbook_data: pd.DataFrame,
        price_data: pd.DataFrame,
        lookback_periods: List[int] = [5, 10, 20, 60],
    ) -> pd.DataFrame:
        """
        創建高階特徵
        
        Args:
            tick_data: 逐筆成交數據 (timestamp, price, volume, direction)
            orderbook_data: 訂單簿數據
            price_data: OHLCV 數據
        
        Returns:
            特徵 DataFrame
        """
        features = pd.DataFrame()
        
        # 1. 訂單流衍生特徵
        features = pd.concat([
            features,
            self._create_order_flow_features(tick_data, lookback_periods)
        ], axis=1)
        
        # 2. 價格-成交量關係特徵
        features = pd.concat([
            features,
            self._create_price_volume_features(price_data, lookback_periods)
        ], axis=1)
        
        # 3. 訂單簿動態特徵
        if not orderbook_data.empty:
            features = pd.concat([
                features,
                self._create_orderbook_features(orderbook_data)
            ], axis=1)
        
        # 4. 波動率特徵
        features = pd.concat([
            features,
            self._create_volatility_features(price_data, lookback_periods)
        ], axis=1)
        
        # 5. 技術指標特徵
        features = pd.concat([
            features,
            self._create_technical_features(price_data)
        ], axis=1)
        
        # 填充缺失值
        features = features.fillna(0)
        
        return features
    
    def _create_order_flow_features(
        self,
        tick_data: pd.DataFrame,
        lookback_periods: List[int],
    ) -> pd.DataFrame:
        """訂單流衍生特徵"""
        features = {}
        
        if tick_data.empty:
            return pd.DataFrame()
        
        for period in lookback_periods:
            suffix = f"_{period}"
            
            # 滾動窗口
            if len(tick_data) >= period:
                window = tick_data.tail(period)
                
                buy_volume = window[window['direction'] == 'BUY']['volume'].sum()
                sell_volume = window[window['direction'] == 'SELL']['volume'].sum()
                total_volume = buy_volume + sell_volume
                
                features[f'buy_ratio{suffix}'] = buy_volume / (total_volume + 1e-6)
                features[f'sell_ratio{suffix}'] = sell_volume / (total_volume + 1e-6)
                features[f'flow_imbalance{suffix}'] = (buy_volume - sell_volume) / (total_volume + 1e-6)
                
                # 大單分析
                large_orders = window[window['volume'] > window['volume'].quantile(0.9)]
                features[f'large_order_ratio{suffix}'] = len(large_orders) / (len(window) + 1e-6)
                
                # 成交密度
                if 'timestamp' in window.columns:
                    time_span = (window['timestamp'].max() - window['timestamp'].min()).total_seconds()
                    features[f'tick_density{suffix}'] = len(window) / (time_span + 1)
        
        return pd.DataFrame([features])
    
    def _create_price_volume_features(
        self,
        price_data: pd.DataFrame,
        lookback_periods: List[int],
    ) -> pd.DataFrame:
        """價格-成交量關係特徵"""
        features = {}
        
        if price_data.empty or 'close' not in price_data.columns:
            return pd.DataFrame()
        
        close = price_data['close']
        volume = price_data.get('volume', pd.Series([0] * len(close)))
        
        for period in lookback_periods:
            suffix = f"_{period}"
            
            if len(close) >= period:
                # 價格變化
                features[f'return{suffix}'] = (close.iloc[-1] / close.iloc[-period] - 1)
                
                # 成交量變化
                avg_vol = volume.tail(period).mean()
                features[f'vol_ratio{suffix}'] = volume.iloc[-1] / (avg_vol + 1e-6)
                
                # 價量相關性
                if len(close) >= period:
                    price_changes = close.tail(period).pct_change().dropna()
                    vol_changes = volume.tail(period).pct_change().dropna()
                    
                    if len(price_changes) > 1:
                        corr = np.corrcoef(price_changes, vol_changes[:len(price_changes)])[0, 1]
                        features[f'pv_corr{suffix}'] = corr if not np.isnan(corr) else 0
        
        return pd.DataFrame([features])
    
    def _create_orderbook_features(
        self,
        orderbook_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """訂單簿動態特徵"""
        features = {}
        
        if orderbook_data.empty:
            return pd.DataFrame()
        
        latest = orderbook_data.iloc[-1]
        
        # 基本不平衡
        bid_vol = sum([latest.get(f'bid{i}_vol', 0) for i in range(1, 6)])
        ask_vol = sum([latest.get(f'ask{i}_vol', 0) for i in range(1, 6)])
        
        features['ob_imbalance'] = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-6)
        features['ob_total_depth'] = bid_vol + ask_vol
        
        # 價差
        bid1 = latest.get('bid1_price', 0)
        ask1 = latest.get('ask1_price', 0)
        if bid1 > 0 and ask1 > 0:
            features['spread_bps'] = (ask1 - bid1) / ((ask1 + bid1) / 2) * 10000
        
        # 訂單簿斜率（深度隨價格的變化）
        bid_vols = [latest.get(f'bid{i}_vol', 0) for i in range(1, 6)]
        ask_vols = [latest.get(f'ask{i}_vol', 0) for i in range(1, 6)]
        
        if sum(bid_vols) > 0:
            features['bid_slope'] = np.polyfit(range(5), bid_vols, 1)[0] / (sum(bid_vols) + 1e-6)
        if sum(ask_vols) > 0:
            features['ask_slope'] = np.polyfit(range(5), ask_vols, 1)[0] / (sum(ask_vols) + 1e-6)
        
        return pd.DataFrame([features])
    
    def _create_volatility_features(
        self,
        price_data: pd.DataFrame,
        lookback_periods: List[int],
    ) -> pd.DataFrame:
        """波動率特徵"""
        features = {}
        
        if price_data.empty or 'close' not in price_data.columns:
            return pd.DataFrame()
        
        close = price_data['close']
        high = price_data.get('high', close)
        low = price_data.get('low', close)
        
        for period in lookback_periods:
            suffix = f"_{period}"
            
            if len(close) >= period:
                returns = close.pct_change().tail(period).dropna()
                
                # 標準差
                features[f'volatility{suffix}'] = returns.std()
                
                # 真實波幅 (ATR-like)
                tr = (high - low).tail(period)
                features[f'atr{suffix}'] = tr.mean() / (close.iloc[-1] + 1e-6)
                
                # Parkinson 波動率
                if len(high) >= period:
                    hl_ratio = np.log(high.tail(period) / low.tail(period))
                    features[f'parkinson_vol{suffix}'] = np.sqrt(
                        (1 / (4 * np.log(2))) * (hl_ratio ** 2).mean()
                    )
        
        return pd.DataFrame([features])
    
    def _create_technical_features(
        self,
        price_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """技術指標特徵"""
        features = {}
        
        if price_data.empty or 'close' not in price_data.columns:
            return pd.DataFrame()
        
        close = price_data['close']
        
        # 移動平均線
        for period in [5, 10, 20, 60]:
            if len(close) >= period:
                ma = close.rolling(period).mean().iloc[-1]
                features[f'ma{period}_ratio'] = close.iloc[-1] / (ma + 1e-6) - 1
        
        # RSI
        if len(close) >= 14:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain.iloc[-1] / (loss.iloc[-1] + 1e-6)
            features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        if len(close) >= 26:
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9).mean()
            features['macd_hist'] = (macd.iloc[-1] - signal.iloc[-1]) / (close.iloc[-1] + 1e-6)
        
        # Bollinger Bands 位置
        if len(close) >= 20:
            ma20 = close.rolling(20).mean().iloc[-1]
            std20 = close.rolling(20).std().iloc[-1]
            upper = ma20 + 2 * std20
            lower = ma20 - 2 * std20
            features['bb_position'] = (close.iloc[-1] - lower) / (upper - lower + 1e-6)
        
        return pd.DataFrame([features])
    
    def fit_transform(self, features: pd.DataFrame) -> np.ndarray:
        """標準化特徵"""
        if self.scaler is None:
            return features.values
        
        scaled = self.scaler.fit_transform(features)
        self._is_fitted = True
        return scaled
    
    def transform(self, features: pd.DataFrame) -> np.ndarray:
        """轉換特徵"""
        if not self._is_fitted:
            raise ValueError("請先調用 fit_transform()")
        
        return self.scaler.transform(features)


class MarketStateClassifier:
    """
    市場狀態分類器
    
    使用 XGBoost 進行市場狀態分類
    """
    
    def __init__(self, config: Optional[XGBConfig] = None):
        if not XGB_AVAILABLE:
            raise ImportError("XGBoost 未安裝，請執行: pip install xgboost scikit-learn")
        
        self.config = config or XGBConfig()
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_engineer = AdvancedFeatureEngineer()
        self.feature_importances_: Optional[np.ndarray] = None
        self.feature_names_: List[str] = []
    
    def _create_model(self) -> xgb.XGBClassifier:
        """創建 XGBoost 模型"""
        config = self.config
        
        return xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=len(MarketState),
            max_depth=config.max_depth,
            learning_rate=config.learning_rate,
            n_estimators=config.n_estimators,
            subsample=config.subsample,
            colsample_bytree=config.colsample_bytree,
            gamma=config.gamma,
            min_child_weight=config.min_child_weight,
            reg_alpha=config.reg_alpha,
            reg_lambda=config.reg_lambda,
            random_state=config.random_state,
            tree_method='hist',
            use_label_encoder=False,
            eval_metric='mlogloss',
        )
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        eval_set: Optional[Tuple[np.ndarray, np.ndarray]] = None,
    ) -> Dict[str, Any]:
        """
        訓練模型
        
        Args:
            X: 特徵矩陣
            y: 標籤
            feature_names: 特徵名稱
            eval_set: 驗證集 (X_val, y_val)
        """
        self.model = self._create_model()
        self.feature_names_ = feature_names or [f"f_{i}" for i in range(X.shape[1])]
        
        logger.info(f"🚀 開始訓練 XGBoost 模型...")
        logger.info(f"   訓練樣本: {len(X)}")
        logger.info(f"   特徵數: {X.shape[1]}")
        
        # 準備評估集
        if eval_set is not None:
            eval_list = [(X, y), eval_set]
        else:
            eval_list = [(X, y)]
        
        self.model.fit(
            X, y,
            eval_set=eval_list,
            verbose=False,
        )
        
        # 保存特徵重要性
        self.feature_importances_ = self.model.feature_importances_
        
        # 計算訓練指標
        train_pred = self.model.predict(X)
        train_accuracy = accuracy_score(y, train_pred)
        
        logger.info(f"✅ 訓練完成，訓練準確率: {train_accuracy:.4f}")
        
        return {
            "train_accuracy": train_accuracy,
            "feature_importances": dict(zip(self.feature_names_, self.feature_importances_.tolist())),
        }
    
    def train_with_cv(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        使用時間序列交叉驗證訓練
        """
        self.feature_names_ = feature_names or [f"f_{i}" for i in range(X.shape[1])]
        
        tscv = TimeSeriesSplit(n_splits=self.config.cv_folds)
        cv_scores = []
        feature_importances_list = []
        
        logger.info(f"🚀 開始 {self.config.cv_folds} 折交叉驗證...")
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            model = self._create_model()
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )
            
            score = accuracy_score(y_val, model.predict(X_val))
            cv_scores.append(score)
            feature_importances_list.append(model.feature_importances_)
            
            logger.info(f"   Fold {fold + 1}: 準確率 = {score:.4f}")
        
        # 平均特徵重要性
        self.feature_importances_ = np.mean(feature_importances_list, axis=0)
        
        # 最終模型（使用全部數據）
        self.model = self._create_model()
        self.model.fit(X, y, verbose=False)
        
        avg_score = np.mean(cv_scores)
        std_score = np.std(cv_scores)
        
        logger.info(f"✅ 交叉驗證完成")
        logger.info(f"   平均準確率: {avg_score:.4f} ± {std_score:.4f}")
        
        return {
            "cv_scores": cv_scores,
            "mean_accuracy": avg_score,
            "std_accuracy": std_score,
            "feature_importances": self.get_feature_importance(),
        }
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """預測類別"""
        if self.model is None:
            raise ValueError("模型未訓練")
        return self.model.predict(X)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """預測機率"""
        if self.model is None:
            raise ValueError("模型未訓練")
        return self.model.predict_proba(X)
    
    def evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Dict[str, Any]:
        """評估模型"""
        y_pred = self.predict(X)
        
        return {
            "accuracy": accuracy_score(y, y_pred),
            "precision_macro": precision_score(y, y_pred, average='macro', zero_division=0),
            "recall_macro": recall_score(y, y_pred, average='macro', zero_division=0),
            "f1_macro": f1_score(y, y_pred, average='macro', zero_division=0),
            "classification_report": classification_report(
                y, y_pred,
                target_names=[MARKET_STATE_NAMES[MarketState(i)] for i in range(len(MarketState))],
                zero_division=0
            ),
        }
    
    def get_feature_importance(self, top_n: int = 20) -> Dict[str, float]:
        """獲取特徵重要性"""
        if self.feature_importances_ is None:
            return {}
        
        importance_dict = dict(zip(self.feature_names_, self.feature_importances_.tolist()))
        sorted_importance = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        
        return dict(sorted_importance[:top_n])
    
    def save(self, filepath: str):
        """保存模型"""
        if self.model is None:
            raise ValueError("模型未訓練")
        
        self.model.save_model(filepath)
        logger.info(f"✅ 模型已保存到 {filepath}")
    
    def load(self, filepath: str):
        """載入模型"""
        self.model = xgb.XGBClassifier()
        self.model.load_model(filepath)
        logger.info(f"✅ 模型已從 {filepath} 載入")
