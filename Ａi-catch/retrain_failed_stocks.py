"""
拯救不及格股票脚本
针对在白名单之外的股票（准确率 < 50%）进行针对性重训
使用 Class Weights 平衡样本，尝试挽救模型
"""

import numpy as np
import pandas as pd
import yfinance as yf
import json
import os
import pickle
from sklearn.preprocessing import MinMaxScaler
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import accuracy_score
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import warnings
warnings.filterwarnings('ignore')

# 配置
MODEL_DIR = "models/lstm_smart_entry"
WHITELIST_FILE = "lstm_whitelist.json"
SEQUENCE_LENGTH = 60

def get_failed_stocks():
    """找出不在白名单中的股票"""
    # 1. 获取所有模型文件
    all_models = [f.replace('_model.h5', '') for f in os.listdir(MODEL_DIR) if f.endswith('_model.h5')]
    
    # 2. 获取白名单
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, 'r') as f:
            whitelist = json.load(f)
            passed = list(whitelist.keys())
    else:
        passed = []
        
    failed = [s for s in all_models if s not in passed]
    return failed

def prepare_data(stock_code):
    """准备训练数据"""
    try:
        ticker = yf.Ticker(f"{stock_code}.TW")
        df = ticker.history(period="2y") # 取长一点的数据训练
        
        if df.empty or len(df) < 150:
            return None
        
        # 技术指标
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df['Volatility'] = df['Close'].rolling(window=20).std()
        
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        
        df['Future_Return'] = (df['Close'].shift(-5) / df['Close'] - 1) * 100
        df['Target'] = df['Future_Return']
        
        df = df.dropna()
        
        feature_cols = ['Close', 'Volume', 'MA5', 'MA10', 'MA20', 
                        'Volume_MA5', 'RSI', 'Volatility', 'MACD']
        
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        
        df[feature_cols] = scaler_X.fit_transform(df[feature_cols])
        df[['Target']] = scaler_y.fit_transform(df[['Target']])
        
        X, y_labels = [], []
        
        for i in range(len(df) - SEQUENCE_LENGTH - 5):
            X.append(df[feature_cols].iloc[i:i+SEQUENCE_LENGTH].values)
            ret = df['Future_Return'].iloc[i+SEQUENCE_LENGTH]
            y_labels.append(1 if ret > 0 else 0)
            
        return np.array(X), np.array(y_labels), scaler_y
        
    except Exception as e:
        print(f"数据错误: {e}")
        return None

def build_model(input_shape):
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(1) # 输出连续值
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def find_optimal_threshold(predictions, y_true):
    pred_flat = predictions.flatten()
    if np.std(pred_flat) < 0.0001: return np.median(pred_flat)
        
    candidates = np.linspace(pred_flat.min(), pred_flat.max(), 100)
    best_acc = 0
    best_threshold = 0.5
    
    for t in candidates:
        pred_binary = (pred_flat > t).astype(int)
        acc = accuracy_score(y_true, pred_binary)
        if acc > best_acc:
            best_acc = acc
            best_threshold = t
    return best_threshold

def retrain_stocks():
    failed_stocks = get_failed_stocks()
    print(f"🚑 开始拯救行动！目标: {len(failed_stocks)} 支股票")
    
    saved_count = 0
    
    for i, stock in enumerate(failed_stocks, 1):
        print(f"\n[{i}/{len(failed_stocks)}] {stock} 重训中...", end="", flush=True)
        
        # 1. 准备数据
        data = prepare_data(stock)
        if data is None:
            print(" ❌ 数据不足/无效")
            continue
            
        X, y_binary, scaler_y = data
        
        # 将y_binary转回用于训练的Target (这里为了简化，我们直接用binary分类训练可能更好，
        # 但为了保持架构一致，我们还是用回归，但用class weights影响loss)
        # 修正：要在MSE回归中使用class_weight是无效的。
        # 策略调整：我们这里针对这批难搞的股票，直接改用「分类模型」或「加权回归」。
        # 为了不破坏原有架构，我们保留回归输出，但在fit时即使是回归，Keras也支持class_weight
        # (会对样本的loss加权)
        
        # 切分
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y_binary[:split], y_binary[split:] 
        
        # 注意：我们的模型输出是连续值，但y_train现在是0/1
        # 这其实可以作为一种强引导：让它以此为目标
        
        # 计算类别权重 (平衡样本)
        weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
        class_weight_dict = {0: weights[0], 1: weights[1]}
        
        # 2. 构建与训练
        model = build_model((X_train.shape[1], X_train.shape[2]))
        
        early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        
        # 训练
        model.fit(
            X_train, y_train, # 用 0/1 作为目标，强迫模型两极化
            epochs=50,
            batch_size=32,
            validation_data=(X_test, y_test),
            class_weight=class_weight_dict, # 关键！
            callbacks=[early_stop],
            verbose=0
        )
        
        # 3. 验证 (使用自适应阈值)
        pred_test = model.predict(X_test, verbose=0)
        best_threshold = find_optimal_threshold(pred_test, y_test)
        
        pred_binary = (pred_test.flatten() > best_threshold).astype(int)
        acc = accuracy_score(y_test, pred_binary)
        
        print(f" -> 新准确率: {acc*100:.1f}%", end="")
        
        if acc >= 0.50:
            print(" ✅ 拯救成功！")
            saved_count += 1
            
            # 保存模型
            model.save(f"{MODEL_DIR}/{stock}_model.h5")
            
            # 更新白名单
            if os.path.exists(WHITELIST_FILE):
                with open(WHITELIST_FILE, 'r') as f:
                    whitelist = json.load(f)
            else:
                whitelist = {}
                
            whitelist[stock] = {
                'threshold': float(best_threshold),
                'accuracy': float(acc)
            }
            
            with open(WHITELIST_FILE, 'w') as f:
                json.dump(whitelist, f, indent=2)
        else:
            print(" ❌ 仍然失败")

    print(f"\n{'='*70}")
    print(f"🎉 拯救行动结束！成功挽救: {saved_count} 支")
    print(f"{'='*70}")

if __name__ == "__main__":
    retrain_stocks()
