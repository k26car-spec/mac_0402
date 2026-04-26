"""
機器學習決策引擎
使用多模型集成進行交易決策
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
import os
import json
import joblib

logger = logging.getLogger(__name__)


class MLDecisionEngine:
    """機器學習決策引擎"""
    
    def __init__(self):
        self.models = {}
        self.ensemble_model = None
        self.best_threshold = 0.5
        self.feature_names = []
        self.is_trained = False
        self.model_path = "/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/models"
        
        os.makedirs(self.model_path, exist_ok=True)
        
        # 嘗試載入已訓練的模型
        self._try_load_models()
    
    def _try_load_models(self):
        """嘗試載入已保存的模型"""
        config_path = f"{self.model_path}/config.json"
        if os.path.exists(config_path):
            try:
                self.load_models()
                logger.info("✅ 已載入訓練好的 ML 模型")
            except Exception as e:
                logger.warning(f"載入模型失敗: {e}")
    
    def train_models(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """訓練多個模型"""
        
        if len(X) < 50:
            logger.warning("數據不足，無法訓練")
            return {'error': '數據不足'}
        
        try:
            from sklearn.ensemble import (
                RandomForestClassifier, 
                GradientBoostingClassifier,
                VotingClassifier
            )
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score, 
                f1_score, roc_auc_score, confusion_matrix
            )
        except ImportError:
            logger.error("請安裝 sklearn: pip install scikit-learn")
            return {'error': '缺少 sklearn'}
        
        # 記錄特徵名稱
        self.feature_names = list(X.columns)
        
        # 分割訓練集和測試集（時間序列分割）
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        logger.info(f"訓練集: {len(X_train)} 筆, 測試集: {len(X_test)} 筆")
        
        results = {}
        
        # === 1. Random Forest ===
        logger.info("訓練 Random Forest...")
        rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train, y_train)
        self.models['random_forest'] = rf_model
        results['random_forest'] = self._evaluate_model(rf_model, X_test, y_test)
        
        # === 2. Gradient Boosting ===
        logger.info("訓練 Gradient Boosting...")
        gb_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42
        )
        gb_model.fit(X_train, y_train)
        self.models['gradient_boosting'] = gb_model
        results['gradient_boosting'] = self._evaluate_model(gb_model, X_test, y_test)
        
        # === 3. Logistic Regression ===
        logger.info("訓練 Logistic Regression...")
        lr_model = LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            random_state=42
        )
        lr_model.fit(X_train, y_train)
        self.models['logistic_regression'] = lr_model
        results['logistic_regression'] = self._evaluate_model(lr_model, X_test, y_test)
        
        # === 4. 集成模型 ===
        logger.info("訓練集成模型...")
        self.ensemble_model = VotingClassifier(
            estimators=[
                ('rf', rf_model),
                ('gb', gb_model),
                ('lr', lr_model)
            ],
            voting='soft',
            weights=[2, 2, 1]
        )
        self.ensemble_model.fit(X_train, y_train)
        results['ensemble'] = self._evaluate_model(self.ensemble_model, X_test, y_test)
        
        # === 5. 優化閾值 ===
        self.best_threshold = self._optimize_threshold(self.ensemble_model, X_test, y_test)
        
        # === 6. 特徵重要性 ===
        feature_importance = self._analyze_feature_importance()
        
        # 保存模型
        self.save_models()
        
        self.is_trained = True
        
        logger.info(f"✅ 訓練完成！最佳閾值: {self.best_threshold:.3f}")
        
        return {
            'model_results': results,
            'best_model': max(results.items(), key=lambda x: x[1].get('roc_auc', 0))[0],
            'best_threshold': self.best_threshold,
            'feature_importance': feature_importance
        }
    
    def _evaluate_model(self, model, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """評估模型性能"""
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, 
            f1_score, roc_auc_score, confusion_matrix
        )
        
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_test, y_pred, zero_division=0)),
            'roc_auc': float(roc_auc_score(y_test, y_pred_proba)) if len(np.unique(y_test)) > 1 else 0.5,
        }
        
        cm = confusion_matrix(y_test, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
        
        return metrics
    
    def _optimize_threshold(self, model, X_test: pd.DataFrame, y_test: pd.Series) -> float:
        """優化決策閾值"""
        
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # 假設平均獲利 2%，平均虧損 3%
        avg_profit = 2.0
        avg_loss = -3.0
        
        best_threshold = 0.5
        best_ev = float('-inf')
        
        for threshold in np.arange(0.3, 0.8, 0.05):
            y_pred = (y_pred_proba >= threshold).astype(int)
            
            tp = np.sum((y_pred == 1) & (y_test == 1))
            fp = np.sum((y_pred == 1) & (y_test == 0))
            
            ev = (tp * avg_profit + fp * avg_loss) / len(y_test)
            
            if ev > best_ev:
                best_ev = ev
                best_threshold = threshold
        
        logger.info(f"最佳閾值: {best_threshold:.3f}, 期望值: {best_ev:.2f}%")
        return float(best_threshold)
    
    def _analyze_feature_importance(self) -> Dict:
        """分析特徵重要性"""
        
        if 'random_forest' not in self.models:
            return {}
        
        importance = self.models['random_forest'].feature_importances_
        importance_dict = dict(zip(self.feature_names, importance))
        
        sorted_importance = dict(sorted(
            importance_dict.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        return sorted_importance
    
    def predict(self, features: np.ndarray) -> Dict:
        """對新訊號進行預測"""
        
        if not self.is_trained or self.ensemble_model is None:
            return {
                'should_enter': False,
                'confidence': 0,
                'error': '模型尚未訓練'
            }
        
        X = pd.DataFrame([features], columns=self.feature_names)
        
        # 使用集成模型預測
        proba = self.ensemble_model.predict_proba(X)[0, 1]
        decision = 1 if proba >= self.best_threshold else 0
        
        # 獲取各模型預測
        individual_predictions = {}
        for model_name, model in self.models.items():
            try:
                pred_proba = model.predict_proba(X)[0, 1]
                individual_predictions[model_name] = {
                    'probability': float(pred_proba),
                    'decision': int(pred_proba >= 0.5)
                }
            except Exception:
                pass
        
        return {
            'should_enter': bool(decision),
            'confidence': float(proba),
            'threshold': self.best_threshold,
            'individual_models': individual_predictions,
            'recommendation': self._generate_recommendation(proba, decision)
        }
    
    def _generate_recommendation(self, proba: float, decision: int) -> str:
        """生成建議"""
        
        if decision == 1:
            if proba > 0.8:
                return "✅ 強烈建議進場（高信心）"
            elif proba > 0.7:
                return "✅ 建議進場（中高信心）"
            else:
                return "⚠️ 可以進場（謹慎）"
        else:
            if proba < 0.3:
                return "❌ 強烈建議觀望（高風險）"
            elif proba < 0.4:
                return "❌ 建議觀望（中高風險）"
            else:
                return "⚠️ 建議觀望（信心不足）"
    
    def save_models(self):
        """保存模型"""
        
        for model_name, model in self.models.items():
            joblib.dump(model, f"{self.model_path}/{model_name}.pkl")
        
        if self.ensemble_model:
            joblib.dump(self.ensemble_model, f"{self.model_path}/ensemble.pkl")
        
        config = {
            'best_threshold': self.best_threshold,
            'feature_names': self.feature_names,
            'trained_at': datetime.now().isoformat()
        }
        with open(f"{self.model_path}/config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"模型已保存至 {self.model_path}")
    
    def load_models(self):
        """載入模型"""
        
        with open(f"{self.model_path}/config.json", 'r') as f:
            config = json.load(f)
        
        self.best_threshold = config['best_threshold']
        self.feature_names = config['feature_names']
        
        for model_name in ['random_forest', 'gradient_boosting', 'logistic_regression']:
            model_path = f"{self.model_path}/{model_name}.pkl"
            if os.path.exists(model_path):
                self.models[model_name] = joblib.load(model_path)
        
        ensemble_path = f"{self.model_path}/ensemble.pkl"
        if os.path.exists(ensemble_path):
            self.ensemble_model = joblib.load(ensemble_path)
        
        self.is_trained = True
        logger.info(f"模型已從 {self.model_path} 載入")


# 全局實例
ml_decision_engine = MLDecisionEngine()
