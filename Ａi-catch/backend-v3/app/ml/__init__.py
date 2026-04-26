"""
機器學習模組
Machine Learning Module

包含：
- order_flow: 訂單流模式識別系統
- models: ML 模型（LSTM, XGBoost）
- training_pipeline: 訓練管道
"""

# Order Flow
from .order_flow import (
    MarketPattern,
    MARKET_MICRO_PATTERNS,
    PatternThresholds,
    OrderFlowFeatureExtractor,
    PatternLabeler,
    OrderFlowDataset,
)

# Models
from .models import (
    OrderFlowPatternClassifier,
    SimplePatternClassifier,
    ModelConfig,
    MarketStateClassifier,
    MarketState,
    MARKET_STATE_NAMES,
    XGBConfig,
    AdvancedFeatureEngineer,
    PATTERN_CLASSIFIER_AVAILABLE,
    MARKET_STATE_CLASSIFIER_AVAILABLE,
    get_available_models,
)

# Training Pipeline
from .training_pipeline import (
    TrainingPipeline,
    TrainingConfig,
    create_sample_training_data,
)

__all__ = [
    # Order Flow
    'MarketPattern',
    'MARKET_MICRO_PATTERNS',
    'PatternThresholds',
    'OrderFlowFeatureExtractor',
    'PatternLabeler',
    'OrderFlowDataset',
    # Models
    'OrderFlowPatternClassifier',
    'SimplePatternClassifier',
    'ModelConfig',
    'MarketStateClassifier',
    'MarketState',
    'MARKET_STATE_NAMES',
    'XGBConfig',
    'AdvancedFeatureEngineer',
    'PATTERN_CLASSIFIER_AVAILABLE',
    'MARKET_STATE_CLASSIFIER_AVAILABLE',
    'get_available_models',
    # Training
    'TrainingPipeline',
    'TrainingConfig',
    'create_sample_training_data',
]


def check_dependencies():
    """檢查依賴狀態"""
    status = {
        "tensorflow": PATTERN_CLASSIFIER_AVAILABLE,
        "xgboost": MARKET_STATE_CLASSIFIER_AVAILABLE,
    }
    
    print("📦 ML 模組依賴檢查:")
    for dep, available in status.items():
        status_icon = "✅" if available else "❌"
        print(f"   {status_icon} {dep}")
    
    return status
