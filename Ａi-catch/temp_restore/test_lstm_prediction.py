#!/usr/bin/env python3
"""
LSTM模型预测示例
使用训练好的模型进行价格预测
"""

import numpy as np
import joblib
from tensorflow.keras.models import load_model
import os

def predict_next_price(symbol: str, model_dir: str = "models/lstm", data_dir: str = "data/lstm"):
    """
    预测下一天的价格
    
    Args:
        symbol: 股票代码
        model_dir: 模型目录
        data_dir: 数据目录
    
    Returns:
        float: 预测价格
    """
    print(f"\n{'='*70}")
    print(f"📊 使用LSTM模型预测 {symbol} 下一天价格")
    print(f"{'='*70}\n")
    
    # 1. 加载模型
    model_path = os.path.join(model_dir, f"{symbol}_model.h5")
    if not os.path.exists(model_path):
        print(f"❌ 模型不存在: {model_path}")
        return None
    
    print(f"📦 加载模型: {model_path}")
    model = load_model(model_path)
    print(f"✅ 模型加载成功")
    
    # 2. 加载scaler
    scaler_X_path = os.path.join(data_dir, symbol, f"{symbol}_scaler_X.pkl")
    scaler_y_path = os.path.join(data_dir, symbol, f"{symbol}_scaler_y.pkl")
    
    print(f"\n📦 加载归一化器...")
    scaler_X = joblib.load(scaler_X_path)
    scaler_y = joblib.load(scaler_y_path)
    print(f"✅ scaler_X 加载成功")
    print(f"✅ scaler_y 加载成功")
    
    # 3. 加载测试数据（使用最后一个序列作为示例）
    X_test_path = os.path.join(data_dir, symbol, f"{symbol}_X_test.npy")
    y_test_path = os.path.join(data_dir, symbol, f"{symbol}_y_test.npy")
    
    X_test = np.load(X_test_path)
    y_test = np.load(y_test_path)
    
    print(f"\n📊 加载测试数据...")
    print(f"   测试样本数: {len(X_test)}")
    print(f"   序列长度: {X_test.shape[1]}天")
    print(f"   特征数: {X_test.shape[2]}个")
    
    # 4. 使用最后一个序列进行预测
    print(f"\n🔮 进行预测...")
    
    # 取最后一个序列
    X_latest = X_test[-1:]  # shape: (1, 60, 15)
    y_actual_scaled = y_test[-1]
    
    # 预测（归一化空间）
    y_pred_scaled = model.predict(X_latest, verbose=0)[0][0]
    
    # 反归一化到实际价格
    y_actual = scaler_y.inverse_transform([[y_actual_scaled]])[0][0]
    y_pred = scaler_y.inverse_transform([[y_pred_scaled]])[0][0]
    
    # 5. 显示结果
    print(f"\n{'='*70}")
    print(f"📈 预测结果")
    print(f"{'='*70}")
    print(f"\n股票代码: {symbol}")
    print(f"实际价格: ${y_actual:.2f}")
    print(f"预测价格: ${y_pred:.2f}")
    print(f"误差:     ${abs(y_actual - y_pred):.2f}")
    print(f"误差率:   {abs(y_actual - y_pred) / y_actual * 100:.2f}%")
    
    if y_pred > y_actual:
        print(f"趋势:     📈 看涨 (+{(y_pred - y_actual) / y_actual * 100:.2f}%)")
    else:
        print(f"趋势:     📉 看跌 ({(y_pred - y_actual) / y_actual * 100:.2f}%)")
    
    print(f"\n{'='*70}\n")
    
    return {
        'symbol': symbol,
        'actual_price': float(y_actual),
        'predicted_price': float(y_pred),
        'error': float(abs(y_actual - y_pred)),
        'error_rate': float(abs(y_actual - y_pred) / y_actual * 100),
        'trend': 'up' if y_pred > y_actual else 'down'
    }


def predict_all_stocks():
    """预测所有训练过的股票"""
    stocks = ["2330", "2317", "2454"]
    
    print("\n" + "="*70)
    print("🚀 LSTM股票价格预测演示")
    print("="*70)
    
    results = {}
    
    for symbol in stocks:
        result = predict_next_price(symbol)
        if result:
            results[symbol] = result
    
    # 总结
    print("\n" + "="*70)
    print("📊 预测总结")
    print("="*70)
    
    for symbol, result in results.items():
        trend_icon = "📈" if result['trend'] == 'up' else "📉"
        print(f"\n{symbol}:")
        print(f"  实际: ${result['actual_price']:.2f}")
        print(f"  预测: ${result['predicted_price']:.2f}")
        print(f"  误差率: {result['error_rate']:.2f}%")
        print(f"  趋势: {trend_icon}")
    
    print("\n" + "="*70)
    print("\n💡 注意:")
    print("   - 以上预测仅供参考，不构成投资建议")
    print("   - 该模型使用最后一个测试样本进行演示")
    print("   - 实际应用需要最新的60天历史数据")
    print("\n" + "="*70)


if __name__ == "__main__":
    # 演示：预测所有股票
    predict_all_stocks()
    
    # 或者单独预测一只
    # predict_next_price("2330")
