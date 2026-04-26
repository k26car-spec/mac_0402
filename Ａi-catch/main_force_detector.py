# main_force_detector.py - 主力偵測演算法

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class MainForceDetector:
    """
    主力偵測器 - 多維度主力特徵工程
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        
    def extract_features(self, ticker_data: pd.DataFrame) -> pd.DataFrame:
        """
        提取9大主力特徵 (新增: 換手率)
        
        Args:
            ticker_data: 股票數據DataFrame，需包含OHLCV數據
            
        Returns:
            特徵DataFrame
        """
        features = {}
        
        try:
            # 1. 量能特徵
            features['volume_ratio'] = self._volume_anomaly(ticker_data)
            features['large_order_ratio'] = self._large_order_analysis_v2(ticker_data)  # 改進版
            features['turnover_rate'] = self._turnover_rate(ticker_data)  # 新增!
            
            # 2. 價格特徵
            features['price_momentum'] = self._price_momentum(ticker_data)
            features['bid_ask_spread'] = self._bid_ask_analysis(ticker_data)
            
            # 3. 資金流向特徵
            features['money_flow'] = self._money_flow_index(ticker_data)
            features['institutional_flow'] = self._institutional_tracking(ticker_data)
            
            # 4. 統計特徵
            features['volume_skewness'] = stats.skew(ticker_data['volume'])
            features['price_kurtosis'] = stats.kurtosis(ticker_data['close'])
            
            # 5. 時間序列特徵
            features['pattern_breakout'] = self._pattern_recognition(ticker_data)
            
        except Exception as e:
            logger.error(f"特徵提取錯誤: {e}")
            # 填充預設值
            for key in ['volume_ratio', 'large_order_ratio', 'turnover_rate', 'price_momentum', 
                       'bid_ask_spread', 'money_flow', 'institutional_flow',
                       'volume_skewness', 'price_kurtosis', 'pattern_breakout']:
                features.setdefault(key, 0.0)
        
        return pd.DataFrame([features])
    
    def _volume_anomaly(self, data: pd.DataFrame) -> float:
        """量能異常檢測"""
        if len(data) < 20:
            return 1.0
            
        volume_series = data['volume'].values
        q75, q25 = np.percentile(volume_series, [75, 25])
        iqr = q75 - q25
        upper_bound = q75 + 1.5 * iqr
        
        current_volume = volume_series[-1]
        return current_volume / upper_bound if upper_bound > 0 else 1.0
    
    def _large_order_analysis(self, data: pd.DataFrame) -> float:
        """大單分析（舊版，保留相容性）"""
        avg_trade_size = data['volume'].mean()
        current_size = data['volume'].iloc[-1]
        
        if 'trade_count' in data.columns:
            large_trades = data[data['volume'] > avg_trade_size * 5]
            return len(large_trades) / len(data) if len(data) > 0 else 0.0
        
        return current_size / (avg_trade_size * 3) if avg_trade_size > 0 else 0.0
    
    def _large_order_analysis_v2(self, data: pd.DataFrame) -> float:
        """改進版大單分析 - 使用標準差方法"""
        if len(data) < 5:
            return 0.0
        
        volumes = data['volume'].values
        mean_vol = np.mean(volumes)
        std_vol = np.std(volumes)
        
        if std_vol == 0:
            return 0.0
        
        # 使用 2.5 個標準差作為大單閾值 (99% 信賴區間)
        threshold = mean_vol + 2.5 * std_vol
        
        # 找出大單
        large_orders = volumes[volumes > threshold]
        
        if len(large_orders) == 0:
            return 0.0
        
        # 計算大單比例
        large_order_ratio = len(large_orders) / len(volumes)
        
        # 額外加分: 連續大單 (主力持續進場)
        consecutive_bonus = 0.0
        if len(large_orders) >= 3:
            # 檢查是否連續出現
            large_order_indices = np.where(volumes > threshold)[0]
            if len(large_order_indices) >= 3:
                consecutive_diffs = np.diff(large_order_indices)
                if np.any(consecutive_diffs <= 2):  # 間隔不超過2天
                    consecutive_bonus = 0.3
        
        return min(large_order_ratio + consecutive_bonus, 1.0)
    
    def _turnover_rate(self, data: pd.DataFrame) -> float:
        """換手率分析 - 新增特徵"""
        if len(data) < 5:
            return 0.0
        
        # 計算平均成交量
        avg_volume = data['volume'].mean()
        current_volume = data['volume'].iloc[-1]
        
        # 換手率估算 (假設流通股數約等於20日平均量的100倍)
        # 這是簡化估算，實際應該查詢股票基本面資料
        estimated_outstanding = avg_volume * 100
        
        if estimated_outstanding == 0:
            return 0.0
        
        turnover = current_volume / estimated_outstanding
        
        # 標準化: 5% 換手率為正常，10% 以上為高
        normalized_turnover = min(turnover / 0.10, 1.0)
        
        return normalized_turnover
    
    def _price_momentum(self, data: pd.DataFrame) -> float:
        """價格動能分析"""
        if len(data) < 2:
            return 0.0
            
        # 計算5日動能
        if len(data) >= 5:
            recent_prices = data['close'].tail(5)
            momentum = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
            return momentum
        else:
            return (data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0]
    
    def _bid_ask_analysis(self, data: pd.DataFrame) -> float:
        """委買委賣分析"""
        if 'bid_volume' in data.columns and 'ask_volume' in data.columns:
            total_bid = data['bid_volume'].sum()
            total_ask = data['ask_volume'].sum()
            
            if total_ask > 0:
                bid_ask_ratio = total_bid / total_ask
                return bid_ask_ratio
        
        return 1.0
    
    def _money_flow_index(self, data: pd.DataFrame, period: int = 14) -> float:
        """資金流向指標 (MFI)"""
        if len(data) < period:
            return 50.0  # 中性值
            
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        money_flow = typical_price * data['volume']
        
        # 計算正負資金流
        price_change = data['close'].diff()
        positive_flow = money_flow[price_change > 0].sum()
        negative_flow = money_flow[price_change < 0].sum()
        
        if negative_flow == 0:
            return 100.0
        
        money_ratio = positive_flow / negative_flow
        mfi = 100 - (100 / (1 + money_ratio))
        
        return mfi
    
    def _institutional_tracking(self, data: pd.DataFrame) -> float:
        """法人追蹤指標"""
        # 這裡需要實際的法人買賣數據
        # 暫時使用量價關係模擬
        if len(data) < 5:
            return 0.0
            
        # 簡單模擬：價漲量增 = 法人買進
        price_change = data['close'].pct_change()
        volume_change = data['volume'].pct_change()
        
        # 計算相關性
        correlation = price_change.tail(20).corr(volume_change.tail(20))
        return correlation if not np.isnan(correlation) else 0.0
    
    def _pattern_recognition(self, data: pd.DataFrame) -> float:
        """型態突破識別"""
        if len(data) < 20:
            return 0.0
            
        # 計算20日移動平均
        ma20 = data['close'].rolling(window=20).mean()
        
        # 判斷是否突破
        current_price = data['close'].iloc[-1]
        current_ma20 = ma20.iloc[-1]
        
        if pd.isna(current_ma20):
            return 0.0
            
        # 突破程度
        breakout_strength = (current_price - current_ma20) / current_ma20
        
        return breakout_strength
    
    def detect_main_force(self, features_df: pd.DataFrame, threshold: float = 0.8) -> Tuple[bool, float]:
        """
        AI主力判斷
        
        Args:
            features_df: 特徵DataFrame
            threshold: 信心閥值
            
        Returns:
            (是否為主力, 信心分數)
        """
        try:
            # 特徵標準化 (更新特徵列表)
            feature_columns = ['volume_ratio', 'large_order_ratio', 'turnover_rate',
                              'money_flow', 'institutional_flow', 'pattern_breakout']
            
            # 確保所有特徵都存在
            valid_features = [col for col in feature_columns if col in features_df.columns]
            
            if not valid_features:
                return False, 0.0
            
            # 權重設定 v2 (優化版，新增換手率)
            weights = {
                'large_order_ratio': 0.30,    # 最關鍵，不變
                'volume_ratio': 0.20,          # 調降 5%
                'turnover_rate': 0.15,         # 新增! ⭐
                'institutional_flow': 0.15,    # 調降 5%
                'money_flow': 0.10,            # 調降 5%
                'pattern_breakout': 0.05,      # 調降 5%
                'volatility_spike': 0.05       # 新增 (預留，暫時不實作)
            }
            
            # 計算主力信心分數
            confidence_score = 0.0
            total_weight = 0.0
            
            for feature in valid_features:
                if feature in weights:
                    feature_value = features_df[feature].values[0]
                    
                    # 標準化特徵值到 [0, 1]
                    normalized_value = self._normalize_feature(feature, feature_value)
                    
                    confidence_score += normalized_value * weights[feature]
                    total_weight += weights[feature]
            
            # 歸一化分數
            if total_weight > 0:
                confidence_score = confidence_score / total_weight
            
            return confidence_score > threshold, confidence_score
            
        except Exception as e:
            logger.error(f"主力判斷錯誤: {e}")
            return False, 0.0
    
    def _normalize_feature(self, feature_name: str, value: float) -> float:
        """標準化特徵值到 [0, 1]"""
        
        # 針對不同特徵使用不同的標準化方法
        if feature_name == 'volume_ratio':
            # volume_ratio > 1.5 為強
            return min(value / 2.0, 1.0)
            
        elif feature_name == 'large_order_ratio':
            # 大單比例 > 0.3 為強
            return min(value / 0.5, 1.0)
        
        elif feature_name == 'turnover_rate':
            # 換手率已在 _turnover_rate() 中標準化
            return min(value, 1.0)
            
        elif feature_name == 'money_flow':
            # MFI > 70 為強
            return value / 100.0
            
        elif feature_name == 'institutional_flow':
            # 相關性 > 0.5 為強
            return (value + 1) / 2.0  # 從 [-1, 1] 轉換到 [0, 1]
            
        elif feature_name == 'pattern_breakout':
            # 突破 > 5% 為強
            return min(abs(value) / 0.1, 1.0)
            
        else:
            return abs(value) if abs(value) <= 1 else 1.0
