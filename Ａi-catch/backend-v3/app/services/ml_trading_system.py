"""
完整的 ML 交易系統
整合特徵工程、模型訓練、預測和持續學習
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio

from app.services.feature_engineering import feature_engineer, FeatureEngineer
from app.services.ml_decision_engine import ml_decision_engine, MLDecisionEngine
from app.services.signal_tracking_db import signal_tracking_db

logger = logging.getLogger(__name__)


class MLTradingSystem:
    """完整的 ML 交易系統"""
    
    def __init__(self):
        self.feature_engineer = feature_engineer
        self.ml_engine = ml_decision_engine
        self.db = signal_tracking_db
        
        logger.info("🤖 ML 交易系統已初始化")
    
    async def initial_training(self, days: int = 90) -> Dict:
        """初始訓練（使用歷史數據）"""
        
        logger.info(f"開始初始訓練（使用過去 {days} 天數據）...")
        
        # 1. 獲取歷史數據
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        signals = self.db.get_signals_for_period(start_date, end_date)
        
        if len(signals) < 50:
            logger.warning(f"數據不足: {len(signals)} 筆，需要至少 50 筆")
            return {
                'success': False,
                'message': f'數據不足，目前只有 {len(signals)} 筆',
                'required': 50
            }
        
        logger.info(f"獲取 {len(signals)} 筆歷史數據")
        
        # 2. 創建訓練數據集
        X, y = self.feature_engineer.create_training_dataset(signals)
        
        if len(X) == 0:
            return {
                'success': False,
                'message': '無法創建訓練數據集'
            }
        
        logger.info(f"訓練數據: {len(X)} 筆，正樣本: {y.sum()}，負樣本: {len(y)-y.sum()}")
        
        # 3. 訓練模型
        training_results = self.ml_engine.train_models(X, y)
        
        if 'error' in training_results:
            return {
                'success': False,
                'message': training_results['error']
            }
        
        logger.info(f"✅ 訓練完成！最佳模型: {training_results.get('best_model')}")
        
        return {
            'success': True,
            'training_samples': len(X),
            'positive_samples': int(y.sum()),
            'negative_samples': int(len(y) - y.sum()),
            'best_model': training_results.get('best_model'),
            'best_threshold': training_results.get('best_threshold'),
            'model_results': training_results.get('model_results', {}),
            'feature_importance': dict(list(training_results.get('feature_importance', {}).items())[:10])
        }
    
    def process_signal(self, signal_data: Dict) -> Dict:
        """處理實時訊號（ML 版本）"""
        
        if not self.ml_engine.is_trained:
            logger.warning("模型尚未訓練，使用規則系統")
            return self._fallback_to_rules(signal_data)
        
        # 提取特徵
        features = self.feature_engineer.extract_features(signal_data)
        
        # ML 預測
        prediction = self.ml_engine.predict(features)
        
        logger.info(
            f"ML 預測: {signal_data.get('stock_code')} - "
            f"{'進場' if prediction['should_enter'] else '觀望'}, "
            f"信心: {prediction['confidence']*100:.1f}%"
        )
        
        return {
            'decision': 'ALLOW' if prediction['should_enter'] else 'REJECT',
            'method': 'ML',
            'confidence': prediction['confidence'],
            'threshold': prediction['threshold'],
            'recommendation': prediction['recommendation'],
            'individual_models': prediction.get('individual_models', {})
        }
    
    def _fallback_to_rules(self, signal_data: Dict) -> Dict:
        """回退到規則系統"""
        
        rejection_reasons = []
        
        vwap_dev = signal_data.get('vwap_deviation', 0)
        kd_k = signal_data.get('kd_k', 50)
        ofi = signal_data.get('ofi', 0)
        
        if vwap_dev >= 30:
            rejection_reasons.append(f"VWAP 乖離過大 (+{vwap_dev:.1f}%)")
        
        if kd_k > 90:
            rejection_reasons.append(f"KD 極度超買 (K:{kd_k:.0f})")
        
        if ofi < -50:
            rejection_reasons.append(f"大戶大量拋售 (OFI:{ofi:.1f})")
        
        if rejection_reasons:
            return {
                'decision': 'REJECT',
                'method': 'RULES',
                'reasons': rejection_reasons
            }
        else:
            return {
                'decision': 'ALLOW',
                'method': 'RULES'
            }
    
    async def retrain_weekly(self):
        """每週重新訓練"""
        
        logger.info("開始每週重新訓練...")
        
        result = await self.initial_training(days=90)
        
        if result.get('success'):
            logger.info(f"✅ 重新訓練完成！最佳模型: {result.get('best_model')}")
        else:
            logger.warning(f"重新訓練失敗: {result.get('message')}")
        
        return result
    
    def get_model_status(self) -> Dict:
        """獲取模型狀態"""
        
        return {
            'is_trained': self.ml_engine.is_trained,
            'models_loaded': list(self.ml_engine.models.keys()),
            'best_threshold': self.ml_engine.best_threshold,
            'feature_count': len(self.ml_engine.feature_names),
            'feature_names': self.ml_engine.feature_names[:10]  # 只返回前 10 個
        }


# 全局實例
ml_trading_system = MLTradingSystem()
