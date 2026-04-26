#!/usr/bin/env python3
"""
LSTM模型训练脚本
Train LSTM Model with Prepared Data

使用昨天准备的数据训练LSTM模型
"""

import numpy as np
import os
import json
from datetime import datetime


def check_tensorflow():
    """检查TensorFlow安装"""
    try:
        import tensorflow as tf
        print(f"✅ TensorFlow版本: {tf.__version__}")
        
        # 检查GPU
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"✅ 检测到GPU: {len(gpus)}个")
        else:
            print(f"⚠️  未检测到GPU，将使用CPU训练（可能较慢）")
        
        return True
    except ImportError:
        print("❌ 未安装TensorFlow")
        print("   请运行: pip install tensorflow")
        return False


def load_prepared_data(symbol: str, data_dir: str = "data/lstm"):
    """
    加载准备好的数据
    
    Args:
        symbol: 股票代码
        data_dir: 数据目录
    
    Returns:
        dict: 包含训练/验证/测试数据
    """
    stock_dir = os.path.join(data_dir, symbol)
    
    if not os.path.exists(stock_dir):
        print(f"❌ 找不到数据目录: {stock_dir}")
        return None
    
    print(f"\n📂 加载 {symbol} 数据...")
    
    # 加载元数据
    meta_path = os.path.join(stock_dir, f"{symbol}_metadata.json")
    with open(meta_path, 'r') as f:
        metadata = json.load(f)
    
    print(f"✅ 元数据已加载")
    print(f"   期间: {metadata['date_range']}")
    print(f"   总天数: {metadata['total_days']}")
    print(f"   训练样本: {metadata['train_samples']}")
    print(f"   验证样本: {metadata['val_samples']}")
    print(f"   测试样本: {metadata['test_samples']}")
    
    # 加载NumPy数据
    data = {}
    for key in ['X_train', 'y_train', 'X_val', 'y_val', 'X_test', 'y_test']:
        path = os.path.join(stock_dir, f"{symbol}_{key}.npy")
        data[key] = np.load(path)
        print(f"✅ {key}: {data[key].shape}")
    
    data['metadata'] = metadata
    
    return data


def build_lstm_model(input_shape, layers=[64, 64, 32], dropout=0.2):
    """
    构建LSTM模型
    
    Args:
        input_shape: 输入形状 (sequence_length, features)
        layers: LSTM层的单元数列表
        dropout: Dropout比例
    
    Returns:
        model: 编译好的模型
    """
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    
    print(f"\n🔨 构建LSTM模型...")
    print(f"   输入形状: {input_shape}")
    print(f"   LSTM层: {layers}")
    print(f"   Dropout: {dropout}")
    
    model = Sequential()
    
    # 第一层LSTM
    model.add(LSTM(units=layers[0], return_sequences=True, input_shape=input_shape))
    model.add(Dropout(dropout))
    
    # 中间LSTM层
    for units in layers[1:-1]:
        model.add(LSTM(units=units, return_sequences=True))
        model.add(Dropout(dropout))
    
    # 最后一层LSTM
    model.add(LSTM(units=layers[-1]))
    model.add(Dropout(dropout))
    
    # 输出层
    model.add(Dense(units=1))
    
    # 编译模型
    model.compile(optimizer='adam', loss='mean_squared_error', metrics=['mae'])
    
    print(f"✅ 模型构建完成")
    print(f"   总参数: {model.count_params():,}")
    
    return model


def train_model(model, X_train, y_train, X_val, y_val, 
                epochs=50, batch_size=32, patience=10):
    """
    训练模型
    
    Args:
        model: LSTM模型
        X_train, y_train: 训练数据
        X_val, y_val: 验证数据
        epochs: 训练轮数
        batch_size: 批次大小
        patience: 早停耐心值
    
    Returns:
        history: 训练历史
    """
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    
    print(f"\n🚀 开始训练...")
    print(f"   训练样本: {len(X_train)}")
    print(f"   验证样本: {len(X_val)}")
    print(f"   训练轮数: {epochs}")
    print(f"   批次大小: {batch_size}")
    print(f"   早停耐心: {patience}")
    
    # 回调函数
    callbacks = [
        EarlyStopping(
            monitor='val_loss',
            patience=patience,
            restore_best_weights=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=0.00001,
            verbose=1
        )
    ]
    
    # 训练
    start_time = datetime.now()
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n✅ 训练完成！")
    print(f"   用时: {duration:.0f}秒 ({duration/60:.1f}分钟)")
    print(f"   最终训练损失: {history.history['loss'][-1]:.6f}")
    print(f"   最终验证损失: {history.history['val_loss'][-1]:.6f}")
    
    return history


def evaluate_model(model, X_test, y_test, symbol, data_dir="data/lstm"):
    """
    评估模型
    
    Args:
        model: 训练好的模型
        X_test, y_test: 测试数据
        symbol: 股票代码（用于加载scaler）
        data_dir: 数据目录
    
    Returns:
        dict: 评估指标
    """
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    import joblib
    
    print(f"\n📊 评估模型...")
    
    # 加载scaler_y用于反归一化
    scaler_y_path = os.path.join(data_dir, symbol, f"{symbol}_scaler_y.pkl")
    scaler_y = joblib.load(scaler_y_path)
    
    # 预测（归一化空间）
    y_pred_scaled = model.predict(X_test, verbose=0).flatten()
    
    # 反归一化到实际价格
    y_test_original = scaler_y.inverse_transform(y_test.reshape(-1, 1)).flatten()
    y_pred_original = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
    
    # 计算指标（基于实际价格）
    mse = mean_squared_error(y_test_original, y_pred_original)
    mae = mean_absolute_error(y_test_original, y_pred_original)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test_original, y_pred_original)
    
    # 方向准确率
    direction_correct = np.sum((y_pred_original[1:] - y_pred_original[:-1]) * (y_test_original[1:] - y_test_original[:-1]) > 0)
    direction_accuracy = direction_correct / (len(y_test_original) - 1)
    
    # 平均价格百分比误差
    mape = np.mean(np.abs((y_test_original - y_pred_original) / y_test_original)) * 100
    
    print(f"✅ 评估完成")
    print(f"\n📈 性能指标:")
    print(f"   MSE:  {mse:.6f}")
    print(f"   MAE:  {mae:.2f}")
    print(f"   RMSE: {rmse:.2f}")
    print(f"   R²:   {r2:.4f}")
    print(f"   MAPE: {mape:.2f}%")
    print(f"   方向准确率: {direction_accuracy:.2%}")
    
    return {
        'mse': float(mse),
        'mae': float(mae),
        'rmse': float(rmse),
        'r2': float(r2),
        'mape': float(mape),
        'direction_accuracy': float(direction_accuracy)
    }


def save_model_and_results(model, history, metrics, symbol, model_dir="models/lstm"):
    """
    保存模型和结果
    
    Args:
        model: 训练好的模型
        history: 训练历史
        metrics: 评估指标
        symbol: 股票代码
        model_dir: 模型目录
    """
    os.makedirs(model_dir, exist_ok=True)
    
    # 保存模型
    model_path = os.path.join(model_dir, f"{symbol}_model.h5")
    model.save(model_path)
    print(f"✅ 模型已保存: {model_path}")
    
    # 保存训练历史
    history_path = os.path.join(model_dir, f"{symbol}_history.json")
    history_data = {
        'loss': [float(x) for x in history.history['loss']],
        'val_loss': [float(x) for x in history.history['val_loss']],
        'mae': [float(x) for x in history.history['mae']],
        'val_mae': [float(x) for x in history.history['val_mae']]
    }
    with open(history_path, 'w') as f:
        json.dump(history_data, f, indent=2)
    print(f"✅ 训练历史已保存: {history_path}")
    
    # 保存评估指标
    metrics_path = os.path.join(model_dir, f"{symbol}_metrics.json")
    metrics['symbol'] = symbol
    metrics['trained_at'] = datetime.now().isoformat()
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✅ 评估指标已保存: {metrics_path}")


def train_stock_lstm(symbol: str, epochs: int = 50, batch_size: int = 32):
    """
    训练单个股票的LSTM模型
    
    Args:
        symbol: 股票代码
        epochs: 训练轮数
        batch_size: 批次大小
    """
    print("="*70)
    print(f"🧠 训练 {symbol} LSTM模型")
    print("="*70)
    
    # 1. 加载数据
    data = load_prepared_data(symbol)
    if data is None:
        return
    
    # 2. 构建模型
    input_shape = (data['X_train'].shape[1], data['X_train'].shape[2])
    model = build_lstm_model(input_shape, layers=[64, 64, 32], dropout=0.2)
    
    # 3. 训练模型
    history = train_model(
        model,
        data['X_train'], data['y_train'],
        data['X_val'], data['y_val'],
        epochs=epochs,
        batch_size=batch_size,
        patience=10
    )
    
    # 4. 评估模型（传递symbol用于加载scaler）
    metrics = evaluate_model(model, data['X_test'], data['y_test'], symbol)
    
    # 5. 保存模型
    save_model_and_results(model, history, metrics, symbol)
    
    print("\n" + "="*70)
    print(f"✅ {symbol} 模型训练完成！")
    print("="*70)
    
    return {
        'model': model,
        'history': history,
        'metrics': metrics
    }


def main():
    """主函数"""
    
    print("\n" + "="*70)
    print("🚀 LSTM股票预测模型训练系统")
    print("="*70)
    
    # 检查TensorFlow
    if not check_tensorflow():
        return
    
    # 训练股票列表（所有三只股票）
    stocks = ["2330", "2317", "2454"]
    
    print(f"\n📋 计划训练: {', '.join(stocks)}")
    print(f"⏰ 预计时间: {len(stocks) * 5}分钟（取决于硬件）")
    
    input("\n按Enter开始训练...")
    
    results = {}
    
    for symbol in stocks:
        result = train_stock_lstm(symbol, epochs=50, batch_size=16)
        if result:
            results[symbol] = result
        print("\n")
    
    # 总结
    print("="*70)
    print("📊 训练总结")
    print("="*70)
    
    for symbol, result in results.items():
        metrics = result['metrics']
        print(f"\n{symbol}:")
        print(f"  R²: {metrics['r2']:.4f}")
        print(f"  方向准确率: {metrics['direction_accuracy']:.2%}")
        print(f"  RMSE: {metrics['rmse']:.2f}")
        print(f"  MAPE: {metrics.get('mape', 0):.2f}%")
    
    print("\n" + "="*70)
    print("✅ 所有模型训练完成！")
    print("="*70)
    print(f"\n📁 模型位置: models/lstm/")
    print(f"\n下一步:")
    print(f"  1. 查看模型: ls models/lstm/")
    print(f"  2. 使用模型预测: python test_lstm_prediction.py")
    print(f"  3. 集成到API: 添加预测端点")


if __name__ == "__main__":
    main()
