"""
機器學習模型模組
ML Models Module

包含：
- pattern_classifier: LSTM 模式分類器
- market_state_classifier: XGBoost 市場狀態分類器
"""

import logging

logger = logging.getLogger(__name__)

# Pattern Classifier
PATTERN_CLASSIFIER_AVAILABLE = False
OrderFlowPatternClassifier = None
SimplePatternClassifier = None
ModelConfig = None
FocalLoss = None

try:
    from .pattern_classifier import (
        OrderFlowPatternClassifier,
        SimplePatternClassifier,
        ModelConfig,
        FocalLoss,
    )
    PATTERN_CLASSIFIER_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Pattern Classifier 不可用: {e}")
except Exception as e:
    logger.debug(f"Pattern Classifier 載入錯誤: {e}")


# Market State Classifier
MARKET_STATE_CLASSIFIER_AVAILABLE = False
MarketStateClassifier = None
MarketState = None
MARKET_STATE_NAMES = {}
XGBConfig = None
AdvancedFeatureEngineer = None

try:
    # 嘗試導入 XGBoost
    import xgboost
    import sklearn
    
    from .market_state_classifier import (
        MarketStateClassifier,
        MarketState,
        MARKET_STATE_NAMES,
        XGBConfig,
        AdvancedFeatureEngineer,
    )
    MARKET_STATE_CLASSIFIER_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Market State Classifier 不可用: {e}")
except Exception as e:
    logger.debug(f"Market State Classifier 載入錯誤: {e}")


__all__ = [
    # Pattern Classifier
    'OrderFlowPatternClassifier',
    'SimplePatternClassifier',
    'ModelConfig',
    'FocalLoss',
    'PATTERN_CLASSIFIER_AVAILABLE',
    # Market State Classifier
    'MarketStateClassifier',
    'MarketState',
    'MARKET_STATE_NAMES',
    'XGBConfig',
    'AdvancedFeatureEngineer',
    'MARKET_STATE_CLASSIFIER_AVAILABLE',
    # Utility
    'get_available_models',
]


def get_available_models():
    """獲取可用的模型"""
    models = {}
    
    if PATTERN_CLASSIFIER_AVAILABLE:
        models['pattern_classifier'] = {
            'name': 'LSTM 模式分類器',
            'class': 'OrderFlowPatternClassifier',
            'description': '混合架構 LSTM 用於市場微觀模式識別',
        }
        models['simple_pattern_classifier'] = {
            'name': '簡化 LSTM 分類器',
            'class': 'SimplePatternClassifier',
            'description': '快速原型開發用的簡化 LSTM',
        }
    
    if MARKET_STATE_CLASSIFIER_AVAILABLE:
        models['market_state_classifier'] = {
            'name': 'XGBoost 市場狀態分類器',
            'class': 'MarketStateClassifier',
            'description': '使用高階特徵工程的 XGBoost 分類器',
        }
    
    return models
