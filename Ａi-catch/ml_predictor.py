# ml_predictor.py - 機器學習模型整合

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
import joblib
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class MainForcePredictor:
    """
    主力行為分類模型
    """
    
    def __init__(self, model_path: str = None):
        """
        初始化預測器
        
        Args:
            model_path: 模型檔案路徑，如果存在則載入，否則建立新模型
        """
        if model_path and os.path.exists(model_path):
            logger.info(f"載入已訓練模型: {model_path}")
            self.model = joblib.load(model_path)
        else:
            logger.info("建立新的 GradientBoosting 模型")
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
                verbose=0
            )
        
        # 歷史資料儲存
        self.history_db = []
        self.feature_names = None
    
    def prepare_training_data(self, historical_data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        準備訓練資料
        
        Args:
            historical_data: 包含特徵和標籤的歷史數據
            
        Returns:
            (X, y) 特徵矩陣和標籤向量
        """
        # 假設 historical_data 包含以下欄位：
        # - volume_ratio, large_order_ratio, money_flow, institutional_flow, pattern_breakout
        # - label: 1=主力進場，0=無主力
        
        feature_columns = [
            'volume_ratio', 
            'large_order_ratio', 
            'money_flow', 
            'institutional_flow', 
            'pattern_breakout',
            'price_momentum',
            'volume_skewness',
            'price_kurtosis'
        ]
        
        # 過濾存在的特徵欄位
        available_features = [col for col in feature_columns if col in historical_data.columns]
        
        if not available_features:
            raise ValueError("歷史數據中沒有可用的特徵欄位")
        
        self.feature_names = available_features
        
        X = historical_data[available_features].values
        y = historical_data['label'].values
        
        return X, y
    
    def train(self, X: np.ndarray, y: np.ndarray, save_path: str = 'models/main_force_model.pkl'):
        """
        訓練模型
        
        Args:
            X: 特徵矩陣
            y: 標籤向量
            save_path: 模型保存路徑
        """
        logger.info(f"開始訓練模型，數據量: {len(X)} 筆")
        
        # 分割訓練集和測試集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # 訓練模型
        self.model.fit(X_train, y_train)
        
        # 評估模型
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        # 交叉驗證
        cv_scores = cross_val_score(self.model, X, y, cv=5)
        
        logger.info(f"訓練準確率: {train_score:.2%}")
        logger.info(f"測試準確率: {test_score:.2%}")
        logger.info(f"交叉驗證準確率: {cv_scores.mean():.2%} (+/- {cv_scores.std() * 2:.2%})")
        
        # 預測測試集
        y_pred = self.model.predict(X_test)
        
        # 詳細分類報告
        report = classification_report(y_test, y_pred, target_names=['無主力', '主力進場'])
        logger.info(f"\n分類報告:\n{report}")
        
        # 特徵重要性
        if hasattr(self.model, 'feature_importances_') and self.feature_names:
            importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
            logger.info(f"特徵重要性: {importance_dict}")
        
        # 儲存模型
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(self.model, save_path)
        logger.info(f"模型已保存至: {save_path}")
        
        return {
            'train_score': train_score,
            'test_score': test_score,
            'cv_scores': cv_scores,
            'feature_importance': importance_dict if self.feature_names else {}
        }
    
    def predict(self, features: pd.Series or Dict) -> Dict:
        """
        預測主力行為
        
        Args:
            features: 特徵字典或Series
            
        Returns:
            預測結果字典
        """
        try:
            # 轉換為數組
            if isinstance(features, dict):
                features = pd.Series(features)
            
            # 確保特徵順序正確
            if self.feature_names:
                feature_vector = []
                for name in self.feature_names:
                    feature_vector.append(features.get(name, 0.0))
            else:
                feature_vector = features.values
            
            feature_array = np.array(feature_vector).reshape(1, -1)
            
            # 預測
            prediction = self.model.predict(feature_array)
            probability = self.model.predict_proba(feature_array)
            
            # 特徵重要性
            feature_importance = {}
            if hasattr(self.model, 'feature_importances_') and self.feature_names:
                feature_importance = dict(zip(
                    self.feature_names,
                    self.model.feature_importances_
                ))
            
            return {
                'is_main_force': bool(prediction[0]),
                'confidence': float(probability[0][1]),
                'probability_no_main_force': float(probability[0][0]),
                'probability_main_force': float(probability[0][1]),
                'features_importance': feature_importance
            }
            
        except Exception as e:
            logger.error(f"預測錯誤: {e}")
            return {
                'is_main_force': False,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def update_online(self, new_data: np.ndarray, label: int):
        """
        線上學習更新
        
        Args:
            new_data: 新的特徵數據
            label: 標籤 (0 或 1)
        """
        try:
            # 如果模型支援 partial_fit
            if hasattr(self.model, 'partial_fit'):
                self.model.partial_fit([new_data], [label])
                logger.info(f"模型已更新（線上學習）")
            else:
                # 累積到歷史數據，定期重新訓練
                self.history_db.append({
                    'features': new_data,
                    'label': label
                })
                logger.info(f"數據已累積，歷史數據量: {len(self.history_db)}")
                
        except Exception as e:
            logger.error(f"線上學習更新錯誤: {e}")
    
    def retrain_from_history(self, save_path: str = 'models/main_force_model.pkl'):
        """從累積的歷史數據重新訓練"""
        if len(self.history_db) < 100:
            logger.warning(f"歷史數據不足（{len(self.history_db)}），建議至少100筆")
            return
        
        # 轉換為訓練格式
        X = np.array([item['features'] for item in self.history_db])
        y = np.array([item['label'] for item in self.history_db])
        
        # 重新訓練
        self.train(X, y, save_path)
        
        # 清空歷史數據
        self.history_db = []


def generate_synthetic_training_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    生成合成訓練數據（用於演示）
    實際使用時應替換為真實的歷史標記數據
    """
    np.random.seed(42)
    
    data = []
    
    for i in range(n_samples):
        # 隨機決定是否為主力
        is_main_force = np.random.choice([0, 1], p=[0.7, 0.3])
        
        if is_main_force:
            # 主力特徵（較高的值）
            volume_ratio = np.random.uniform(1.5, 3.0)
            large_order_ratio = np.random.uniform(0.3, 0.7)
            money_flow = np.random.uniform(60, 90)
            institutional_flow = np.random.uniform(0.3, 0.8)
            pattern_breakout = np.random.uniform(0.03, 0.1)
            price_momentum = np.random.uniform(0.02, 0.08)
        else:
            # 無主力特徵（較低的值）
            volume_ratio = np.random.uniform(0.5, 1.2)
            large_order_ratio = np.random.uniform(0.05, 0.25)
            money_flow = np.random.uniform(30, 60)
            institutional_flow = np.random.uniform(-0.3, 0.2)
            pattern_breakout = np.random.uniform(-0.05, 0.02)
            price_momentum = np.random.uniform(-0.02, 0.02)
        
        data.append({
            'volume_ratio': volume_ratio,
            'large_order_ratio': large_order_ratio,
            'money_flow': money_flow,
            'institutional_flow': institutional_flow,
            'pattern_breakout': pattern_breakout,
            'price_momentum': price_momentum,
            'volume_skewness': np.random.uniform(-1, 1),
            'price_kurtosis': np.random.uniform(-1, 1),
            'label': is_main_force
        })
    
    return pd.DataFrame(data)


if __name__ == '__main__':
    # 配置日誌
    logging.basicConfig(level=logging.INFO)
    
    # 生成訓練數據
    logger.info("生成合成訓練數據...")
    df = generate_synthetic_training_data(1000)
    
    # 初始化預測器
    predictor = MainForcePredictor()
    
    # 準備訓練數據
    X, y = predictor.prepare_training_data(df)
    
    # 訓練模型
    results = predictor.train(X, y)
    
    # 測試預測
    test_features = {
        'volume_ratio': 2.5,
        'large_order_ratio': 0.5,
        'money_flow': 75,
        'institutional_flow': 0.6,
        'pattern_breakout': 0.08,
        'price_momentum': 0.05,
        'volume_skewness': 0.5,
        'price_kurtosis': 0.3
    }
    
    prediction = predictor.predict(test_features)
    logger.info(f"測試預測結果: {prediction}")
