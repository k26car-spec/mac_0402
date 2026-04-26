"""
股票預測模型改進方案 - 6種模型實現
針對9特徵數據的LSTM訓練系統

方案：
1. Baseline - 基準模型
2. Regularized - 針對震盪問題
3. Larger - 針對早期平台
4. Optimized - 綜合平衡
5. Augmented - 數據擴增
6. Attention - 注意力機制

作者: AI Trading System
日期: 2026-02-08
版本: v3.0
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json
import os

# TensorFlow/Keras
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import (
    LSTM, Dense, Dropout, Input, Layer,
    LayerNormalization, MultiHeadAttention, Add
)
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.regularizers import l2

# Sklearn
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split

print(f"✅ TensorFlow {tf.__version__} loaded")

# 設置隨機種子
np.random.seed(42)
tf.random.set_seed(42)


# ==================== 配置類 ====================

class ModelConfig:
    """模型配置基類"""
    def __init__(self):
        # 通用參數
        self.input_shape = (60, 9)  # 60天 × 9特徵
        self.batch_size = 32
        self.max_epochs = 150
        self.validation_split = 0.15
        
        # Early Stopping
        self.early_stop_patience = 20
        self.early_stop_min_delta = 0.0001
        
        # Learning Rate
        self.reduce_lr_patience = 8
        self.reduce_lr_factor = 0.5
        self.min_lr = 1e-7


# ==================== 方案1: Baseline模型 ====================

class BaselineConfig(ModelConfig):
    """基準模型配置"""
    def __init__(self):
        super().__init__()
        self.name = "Baseline"
        self.lstm_units = [64, 32]
        self.dropout_rate = 0.2
        self.learning_rate = 0.001
        self.l2_reg = 0.0  # 無正則化


def build_baseline_model(config: BaselineConfig) -> keras.Model:
    """
    方案1: Baseline模型
    
    適用: 訓練良好的股票，作為對照組
    特點: 簡單、快速收斂
    """
    model = Sequential(name='Baseline_Model')
    
    # 第一層LSTM
    model.add(LSTM(
        config.lstm_units[0],
        return_sequences=True,
        input_shape=config.input_shape,
        name='LSTM_1'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_1'))
    
    # 第二層LSTM
    model.add(LSTM(
        config.lstm_units[1],
        return_sequences=False,
        name='LSTM_2'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_2'))
    
    # 輸出層
    model.add(Dense(1, name='Output'))
    
    # 編譯
    model.compile(
        optimizer=Adam(learning_rate=config.learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


# ==================== 方案2: Regularized模型 ====================

class RegularizedConfig(ModelConfig):
    """正則化模型配置"""
    def __init__(self):
        super().__init__()
        self.name = "Regularized"
        self.lstm_units = [64, 32]
        self.dense_units = 16
        self.dropout_rate = 0.35  # 更高
        self.recurrent_dropout = 0.2
        self.learning_rate = 0.0008  # 降低
        self.l2_reg = 0.015  # L2正則化
        self.early_stop_patience = 25  # 更有耐心


def build_regularized_model(config: RegularizedConfig) -> keras.Model:
    """
    方案2: Regularized模型
    
    適用: 驗證曲線震盪
    特點: 強正則化、高Dropout、Recurrent Dropout
    """
    model = Sequential(name='Regularized_Model')
    
    # 第一層LSTM (加L2和Recurrent Dropout)
    model.add(LSTM(
        config.lstm_units[0],
        return_sequences=True,
        input_shape=config.input_shape,
        kernel_regularizer=l2(config.l2_reg),
        recurrent_dropout=config.recurrent_dropout,
        name='LSTM_1'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_1'))
    
    # 第二層LSTM
    model.add(LSTM(
        config.lstm_units[1],
        return_sequences=False,
        kernel_regularizer=l2(config.l2_reg),
        recurrent_dropout=config.recurrent_dropout,
        name='LSTM_2'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_2'))
    
    # 中間Dense層
    model.add(Dense(
        config.dense_units,
        activation='relu',
        kernel_regularizer=l2(config.l2_reg),
        name='Dense_Middle'
    ))
    model.add(Dropout(0.2, name='Dropout_3'))
    
    # 輸出層
    model.add(Dense(1, name='Output'))
    
    # 編譯
    model.compile(
        optimizer=Adam(learning_rate=config.learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


# ==================== 方案3: Larger模型 ====================

class LargerConfig(ModelConfig):
    """大容量模型配置"""
    def __init__(self):
        super().__init__()
        self.name = "Larger"
        self.lstm_units = [128, 64, 32]  # 3層
        self.dense_units = 32
        self.dropout_rate = 0.2
        self.learning_rate = 0.0005  # 降低
        self.l2_reg = 0.005  # 輕度正則化
        self.early_stop_patience = 30  # 延長訓練


def build_larger_model(config: LargerConfig) -> keras.Model:
    """
    方案3: Larger模型
    
    適用: 驗證損失早期平台
    特點: 3層LSTM、更多參數、更低學習率
    """
    model = Sequential(name='Larger_Model')
    
    # 第一層LSTM
    model.add(LSTM(
        config.lstm_units[0],
        return_sequences=True,
        input_shape=config.input_shape,
        kernel_regularizer=l2(config.l2_reg),
        name='LSTM_1'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_1'))
    
    # 第二層LSTM
    model.add(LSTM(
        config.lstm_units[1],
        return_sequences=True,
        kernel_regularizer=l2(config.l2_reg),
        name='LSTM_2'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_2'))
    
    # 第三層LSTM
    model.add(LSTM(
        config.lstm_units[2],
        return_sequences=False,
        kernel_regularizer=l2(config.l2_reg),
        name='LSTM_3'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_3'))
    
    # Dense層
    model.add(Dense(
        config.dense_units,
        activation='relu',
        name='Dense_Middle'
    ))
    model.add(Dropout(0.1, name='Dropout_4'))
    
    # 輸出層
    model.add(Dense(1, name='Output'))
    
    # 編譯
    model.compile(
        optimizer=Adam(learning_rate=config.learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


# ==================== 方案4: Optimized模型 ====================

class OptimizedConfig(ModelConfig):
    """優化平衡模型配置"""
    def __init__(self):
        super().__init__()
        self.name = "Optimized"
        self.lstm_units = [96, 48]  # 中等容量
        self.dense_units = 24
        self.dropout_rate = 0.25
        self.recurrent_dropout = 0.25
        self.learning_rate = 0.0008  # 折中
        self.l2_reg = 0.008  # 適度正則化


def build_optimized_model(config: OptimizedConfig) -> keras.Model:
    """
    方案4: Optimized模型
    
    適用: 中等難度股票、通用方案
    特點: 平衡容量、穩定訓練、適用範圍廣
    """
    model = Sequential(name='Optimized_Model')
    
    # 第一層LSTM
    model.add(LSTM(
        config.lstm_units[0],
        return_sequences=True,
        input_shape=config.input_shape,
        kernel_regularizer=l2(config.l2_reg),
        recurrent_dropout=config.recurrent_dropout,
        name='LSTM_1'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_1'))
    
    # 第二層LSTM
    model.add(LSTM(
        config.lstm_units[1],
        return_sequences=False,
        kernel_regularizer=l2(config.l2_reg),
        recurrent_dropout=config.recurrent_dropout,
        name='LSTM_2'
    ))
    model.add(Dropout(config.dropout_rate, name='Dropout_2'))
    
    # Dense層
    model.add(Dense(
        config.dense_units,
        activation='relu',
        kernel_regularizer=l2(config.l2_reg),
        name='Dense_Middle'
    ))
    model.add(Dropout(0.15, name='Dropout_3'))
    
    # 輸出層
    model.add(Dense(1, name='Output'))
    
    # 編譯
    model.compile(
        optimizer=Adam(learning_rate=config.learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


# ==================== 方案5: Augmented模型 ====================

class AugmentedConfig(OptimizedConfig):
    """數據擴增模型配置"""
    def __init__(self):
        super().__init__()
        self.name = "Augmented"
        self.use_augmentation = True
        self.noise_level = 0.003  # 0.3% 噪聲
        self.batch_size = 64  # 增大batch size


def augment_data(X: np.ndarray, y: np.ndarray, noise_level: float = 0.003) -> Tuple[np.ndarray, np.ndarray]:
    """
    數據擴增
    
    策略: 添加微小噪聲，樣本數翻倍
    """
    # 原始數據
    X_orig = X.copy()
    y_orig = y.copy()
    
    # 添加噪聲
    noise = np.random.normal(0, noise_level, X.shape)
    X_noisy = X + noise
    
    # 合併
    X_augmented = np.concatenate([X_orig, X_noisy], axis=0)
    y_augmented = np.concatenate([y_orig, y_orig], axis=0)
    
    # 打亂
    indices = np.random.permutation(len(X_augmented))
    X_augmented = X_augmented[indices]
    y_augmented = y_augmented[indices]
    
    return X_augmented, y_augmented


def build_augmented_model(config: AugmentedConfig) -> keras.Model:
    """
    方案5: Augmented模型
    
    適用: 嚴重過擬合、訓練樣本不足
    特點: 使用Optimized架構 + 數據擴增
    """
    return build_optimized_model(config)


# ==================== 方案6: Attention模型 ====================

class AttentionConfig(ModelConfig):
    """注意力模型配置"""
    def __init__(self):
        super().__init__()
        self.name = "Attention"
        self.lstm_units = [96, 48]
        self.attention_heads = 3
        self.attention_key_dim = 32
        self.dense_units = 32
        self.dropout_rate = 0.25
        self.learning_rate = 0.0005  # 降低
        self.l2_reg = 0.005
        self.early_stop_patience = 30  # 需要更多訓練時間


def build_attention_model(config: AttentionConfig) -> keras.Model:
    """
    方案6: Attention模型
    
    適用: 複雜特徵交互、標準方法效果不理想
    特點: 多頭注意力、殘差連接、Layer Normalization
    """
    # 輸入層
    inputs = Input(shape=config.input_shape, name='Input')
    
    # 第一層LSTM
    x = LSTM(
        config.lstm_units[0],
        return_sequences=True,
        kernel_regularizer=l2(config.l2_reg),
        name='LSTM_1'
    )(inputs)
    x = Dropout(config.dropout_rate, name='Dropout_1')(x)
    
    # 多頭注意力
    attn_residual = x  # 殘差連接
    attn_out = MultiHeadAttention(
        num_heads=config.attention_heads,
        key_dim=config.attention_key_dim,
        dropout=0.1,
        name='MultiHeadAttention'
    )(x, x)
    
    # 殘差連接 + Layer Normalization
    x = Add(name='Residual_Add')([attn_residual, attn_out])
    x = LayerNormalization(name='LayerNorm')(x)
    x = Dropout(0.2, name='Dropout_2')(x)
    
    # 第二層LSTM
    x = LSTM(
        config.lstm_units[1],
        return_sequences=False,
        kernel_regularizer=l2(config.l2_reg),
        name='LSTM_2'
    )(x)
    x = Dropout(config.dropout_rate, name='Dropout_3')(x)
    
    # Dense層
    x = Dense(
        config.dense_units,
        activation='relu',
        kernel_regularizer=l2(config.l2_reg),
        name='Dense_Middle'
    )(x)
    x = Dropout(0.15, name='Dropout_4')(x)
    
    # 輸出層
    outputs = Dense(1, name='Output')(x)
    
    # 創建模型
    model = Model(inputs=inputs, outputs=outputs, name='Attention_Model')
    
    # 編譯
    model.compile(
        optimizer=Adam(learning_rate=config.learning_rate),
        loss='mse',
        metrics=['mae']
    )
    
    return model


# ==================== 問題分類器 ====================

class ProblemClassifier:
    """自動分類訓練曲線問題"""
    
    @staticmethod
    def classify(history: Dict) -> str:
        """
        分類問題類型
        
        返回:
            - 'good': 訓練良好
            - 'oscillation': 驗證曲線震盪
            - 'early_plateau': 驗證損失早期平台
            - 'overfitting': 嚴重過擬合
            - 'undertrained': 訓練不足
        """
        train_mae = history['mae']
        val_mae = history['val_mae']
        
        # 計算指標
        final_train_mae = train_mae[-1]
        final_val_mae = val_mae[-1]
        gap = final_val_mae - final_train_mae
        
        # 震盪檢測（計算驗證損失的標準差）
        val_std = np.std(val_mae[-20:]) if len(val_mae) >= 20 else np.std(val_mae)
        
        # 早期平台檢測（前20個epoch驗證損失變化小）
        if len(val_mae) >= 20:
            early_improvement = val_mae[0] - val_mae[19]
            total_improvement = val_mae[0] - val_mae[-1]
            early_plateau_ratio = early_improvement / (total_improvement + 1e-8)
        else:
            early_plateau_ratio = 0
        
        # 分類邏輯
        if final_val_mae < 0.10 and gap < 0.03:
            return 'good'  # 訓練良好
        
        elif val_std > 0.01:
            return 'oscillation'  # 震盪
        
        elif early_plateau_ratio < 0.3:
            return 'early_plateau'  # 早期平台
        
        elif final_train_mae < 0.03 and final_val_mae > 0.12:
            return 'overfitting'  # 嚴重過擬合
        
        elif len(train_mae) < 30 and train_mae[-1] < train_mae[-10]:
            return 'undertrained'  # 訓練不足
        
        else:
            return 'other'  # 其他情況
    
    @staticmethod
    def recommend_method(problem_type: str) -> str:
        """推薦最佳方法"""
        mapping = {
            'good': 'Baseline',
            'oscillation': 'Regularized',
            'early_plateau': 'Larger',
            'overfitting': 'Augmented',
            'undertrained': 'Optimized',
            'other': 'Optimized'
        }
        return mapping.get(problem_type, 'Optimized')


# ==================== 綜合測試框架 ====================

def comprehensive_test(
    stock_code: str,
    X_data: np.ndarray,
    y_data: np.ndarray,
    test_all_methods: bool = True,
    save_dir: str = './improved_results'
) -> Dict:
    """
    綜合測試框架
    
    參數:
        stock_code: 股票代碼
        X_data: 輸入數據 (samples, 60, 9)
        y_data: 目標數據 (samples,)
        test_all_methods: 是否測試所有6種方法
        save_dir: 結果保存目錄
    
    返回:
        測試結果字典
    """
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"🎯 綜合測試: {stock_code}")
    print(f"{'='*70}\n")
    
    # 分割數據
    X_train, X_test, y_train, y_test = train_test_split(
        X_data, y_data, test_size=0.15, shuffle=False
    )
    
    print(f"數據集:")
    print(f"  訓練集: {X_train.shape}")
    print(f"  測試集: {X_test.shape}\n")
    
    # 測試所有方法
    if test_all_methods:
        methods = ['Baseline', 'Regularized', 'Larger', 'Optimized', 'Augmented', 'Attention']
    else:
        methods = ['Optimized']  # 只測試通用方案
    
    results = {}
    
    for method_name in methods:
        print(f"\n{'─'*70}")
        print(f"📊 測試方法: {method_name}")
        print(f"{'─'*70}")
        
        result = train_single_method(
            method_name,
            X_train, y_train,
            X_test, y_test,
            stock_code,
            save_dir
        )
        
        results[method_name] = result
        
        # 打印結果
        print(f"\n✅ {method_name} 完成:")
        print(f"  訓練 MAE: {result['train_mae']:.6f}")
        print(f"  驗證 MAE: {result['val_mae']:.6f}")
        print(f"  測試 MAE: {result['test_mae']:.6f}")
        print(f"  訓練-驗證差距: {result['gap']:.6f}")
        print(f"  實際Epochs: {result['epochs_trained']}")
    
    # 生成對比報告
    generate_comparison_report(stock_code, results, save_dir)
    
    # 推薦最佳方法
    best_method = min(results.items(), key=lambda x: x[1]['val_mae'])
    print(f"\n🏆 最佳方法: {best_method[0]} (驗證MAE: {best_method[1]['val_mae']:.6f})")
    
    return results


def train_single_method(
    method_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    stock_code: str,
    save_dir: str
) -> Dict:
    """訓練單個方法"""
    
    # 選擇配置和模型
    configs = {
        'Baseline': BaselineConfig(),
        'Regularized': RegularizedConfig(),
        'Larger': LargerConfig(),
        'Optimized': OptimizedConfig(),
        'Augmented': AugmentedConfig(),
        'Attention': AttentionConfig()
    }
    
    builders = {
        'Baseline': build_baseline_model,
        'Regularized': build_regularized_model,
        'Larger': build_larger_model,
        'Optimized': build_optimized_model,
        'Augmented': build_augmented_model,
        'Attention': build_attention_model
    }
    
    config = configs[method_name]
    builder = builders[method_name]
    
    # 數據擴增（僅Augmented方法）
    if isinstance(config, AugmentedConfig) and config.use_augmentation:
        X_train_use, y_train_use = augment_data(X_train, y_train, config.noise_level)
        print(f"  🔊 數據擴增: {X_train.shape[0]} → {X_train_use.shape[0]} 樣本")
    else:
        X_train_use, y_train_use = X_train, y_train
    
    # 構建模型
    model = builder(config)
    
    # Callbacks
    early_stop = EarlyStopping(
        monitor='val_mae',
        patience=config.early_stop_patience,
        min_delta=config.early_stop_min_delta,
        restore_best_weights=True,
        verbose=0
    )
    
    reduce_lr = ReduceLROnPlateau(
        monitor='val_mae',
        factor=config.reduce_lr_factor,
        patience=config.reduce_lr_patience,
        min_lr=config.min_lr,
        verbose=0
    )
    
    model_path = f"{save_dir}/{stock_code}_{method_name}_best.h5"
    checkpoint = ModelCheckpoint(
        model_path,
        monitor='val_mae',
        save_best_only=True,
        verbose=0
    )
    
    # 訓練
    history = model.fit(
        X_train_use, y_train_use,
        validation_data=(X_test, y_test),
        epochs=config.max_epochs,
        batch_size=config.batch_size,
        callbacks=[early_stop, reduce_lr, checkpoint],
        verbose=0
    )
    
    # 評估
    train_loss, train_mae = model.evaluate(X_train, y_train, verbose=0)
    test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
    
    val_mae = history.history['val_mae']
    gap = test_mae - train_mae
    
    return {
        'method': method_name,
        'train_mae': float(train_mae),
        'val_mae': float(min(val_mae)),
        'test_mae': float(test_mae),
        'gap': float(gap),
        'epochs_trained': len(history.history['loss']),
        'history': {
            'mae': [float(x) for x in history.history['mae']],
            'val_mae': [float(x) for x in history.history['val_mae']]
        }
    }


def generate_comparison_report(stock_code: str, results: Dict, save_dir: str):
    """生成對比報告"""
    
    # 創建對比表
    comparison = []
    for method, result in results.items():
        comparison.append({
            '方法': method,
            '訓練MAE': f"{result['train_mae']:.6f}",
            '驗證MAE': f"{result['val_mae']:.6f}",
            '測試MAE': f"{result['test_mae']:.6f}",
            '訓練-驗證差距': f"{result['gap']:.6f}",
            '實際Epochs': result['epochs_trained']
        })
    
    df = pd.DataFrame(comparison)
    
    # 保存CSV
    csv_path = f"{save_dir}/{stock_code}_comparison.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # 打印表格
    print(f"\n{'='*70}")
    print(f"📊 對比報告: {stock_code}")
    print(f"{'='*70}\n")
    print(df.to_string(index=False))
    
    # 保存JSON
    json_path = f"{save_dir}/{stock_code}_results.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 報告已保存:")
    print(f"  CSV: {csv_path}")
    print(f"  JSON: {json_path}")


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 股票預測模型改進方案 v3.0")
    print("="*70)
    
    print("\n📋 可用方法:")
    print("  1. Baseline    - 基準模型")
    print("  2. Regularized - 針對震盪問題")
    print("  3. Larger      - 針對早期平台")
    print("  4. Optimized   - 綜合平衡")
    print("  5. Augmented   - 數據擴增")
    print("  6. Attention   - 注意力機制")
    
    print("\n💡 使用示例:")
    print("""
    # 1. 準備數據
    X = np.random.randn(1000, 60, 9)  # 示例數據
    y = np.random.randn(1000)
    
    # 2. 綜合測試
    results = comprehensive_test(
        stock_code='2330',
        X_data=X,
        y_data=y,
        test_all_methods=True
    )
    
    # 3. 查看結果
    print(results)
    """)
    
    print("\n✅ 模型已準備就緒！")
