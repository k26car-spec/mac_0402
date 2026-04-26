"""
train_lstm_v7.py
第 7 代 LSTM 模型訓練腳本 — 全面對接 v4 滾動特徵建構器
注意：本腳本使用 TensorFlow/Keras，並且「不再產出 scaler.pkl」。
"""

import os
import sys
import numpy as np
import pandas as pd
import yfinance as yf
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from lstm_feature_builder_v4 import build_dataset

# 壓制 TF 日誌
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
tf.get_logger().setLevel('ERROR')

MODEL_DIR = "models/lstm_smart_entry"
os.makedirs(MODEL_DIR, exist_ok=True)

# 訓練參數
SEQ_LEN = 20
EPOCHS = 50
BATCH_SIZE = 64
HORIZON = 5


def build_keras_model(input_shape):
    """
    標準雙層 LSTM 架構 (Keras 版)
    """
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=input_shape),
        BatchNormalization(),
        Dropout(0.3),
        
        LSTM(32, return_sequences=False),
        BatchNormalization(),
        Dropout(0.3),
        
        Dense(16, activation='relu'),
        Dropout(0.2),
        Dense(1, activation='sigmoid')  # 輸出 0~1 的上漲機率
    ])
    
    # 使用 AdamW 概念或標準 Adam 配合良好 decay
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
    
    model.compile(
        optimizer=optimizer,
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
    )
    return model


def train_for_symbol(symbol: str):
    print(f"\n🚀 開始訓練 [{symbol}] TensorFlow LSTM 模型 (v7)...")
    
    # 1. 抓取五年歷史數據
    hist = yf.Ticker(f"{symbol}.TW").history(period="5y")
    if len(hist) < 300:
        print(f"❌ {symbol} 歷史數據不足，跳過訓練。")
        return
        
    hist.index = pd.to_datetime(hist.index).tz_localize(None)

    # 2. 調用 v4 特徵建構器 (此處自動切分成序列與標籤)
    try:
        X, y = build_dataset(hist, seq_len=SEQ_LEN, horizon=HORIZON, norm_window=60)
    except Exception as e:
        print(f"❌ {symbol} 特徵建構失敗: {e}")
        return
        
    if len(X) < 100:
        print(f"❌ {symbol} 有效序列過少 ({len(X)}筆)，無法訓練。")
        return

    # 時間序列切分：前 80% 訓練，後 20% 驗證
    split_idx = int(len(X) * 0.8)
    X_train, y_train = X[:split_idx], y[:split_idx]
    X_val, y_val     = X[split_idx:], y[split_idx:]
    
    print(f"📊 訓練集: {len(X_train)} 筆 | 驗證集: {len(X_val)} 筆")
    print(f"⚖️ 訓練集正樣本 (上漲機率): {y_train.mean():.1%} | 負樣本: {1-y_train.mean():.1%}")
    
    # 3. 建立並訓練神經網路
    model = build_keras_model((SEQ_LEN, X.shape[2]))
    
    model_path = os.path.join(MODEL_DIR, f"{symbol}_model.h5")
    
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True, verbose=1),
        # 由於我們沒有 scaler.pkl，所以這顆 h5 存下來就能獨立運作
        ModelCheckpoint(model_path, monitor='val_loss', save_best_only=True, verbose=0)
    ]
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1  # 設定 1 可看訓練進度條
    )
    
    # 取出最後最佳的 val_loss 跟 AUC 顯示
    best_val_loss = min(history.history['val_loss'])
    best_val_auc  = max(history.history['val_auc'])
    print(f"✅ [{symbol}] 訓練順利完成！最佳 Val Loss: {best_val_loss:.4f} | Val AUC: {best_val_auc:.4f}")
    print(f"   💾 模型已保存至: {model_path} (無須 Scaler .pkl)")


# ==========================================
# 執行區塊（您可以自行更換 ORB 的 46 檔清單）
# ==========================================
if __name__ == "__main__":
    tf.random.set_seed(42)
    np.random.seed(42)
    
    # 預設可以先拿勝率穩定的當做首波訓練對象
    # 您可以依需要改成包含 46 檔活躍股票的 list
    target_stocks = [
        "2337", "2454", "3163", "6285", "3037", "2330", "2317", "1303"
    ]
    
    for sym in target_stocks:
        train_for_symbol(sym)
