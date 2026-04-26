#!/usr/bin/env python3
"""
LSTM 模型優化訓練腳本
Optimize LSTM Models with Better Hyperparameters

目標：
- 增加訓練數據（3年）
- 優化模型架構
- 使用更好的特徵工程
- 調整超參數
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# 股票列表
STOCKS_TO_TRAIN = ['2330', '2454', '2317']  # 先訓練這三支重要股票

class OptimizedLSTMTrainer:
    """優化的 LSTM 訓練器"""
    
    def __init__(self, symbol: str, years: int = 3):
        self.symbol = symbol
        self.years = years
        self.model_dir = "models/lstm_optimized"
        self.data_dir = "data/lstm_optimized"
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
    def download_data(self) -> pd.DataFrame:
        """下載歷史數據"""
        print(f"\n📊 下載 {self.symbol} 過去{self.years}年數據...")
        
        ticker = yf.Ticker(f"{self.symbol}.TW")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.years * 365)
        
        hist = ticker.history(start=start_date.strftime('%Y-%m-%d'),
                             end=end_date.strftime('%Y-%m-%d'))
        
        if hist.empty:
            print(f"❌ 無法獲取 {self.symbol} 數據")
            return None
            
        print(f"✅ 成功下載 {len(hist)} 天數據")
        return hist
    
    def add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加技術指標作為特徵"""
        print("🔧 計算技術指標...")
        
        # 價格特徵
        df['Returns'] = df['Close'].pct_change()
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # 移動平均
        for period in [5, 10, 20, 60]:
            df[f'MA{period}'] = df['Close'].rolling(window=period).mean()
            df[f'MA{period}_Ratio'] = df['Close'] / df[f'MA{period}']
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # 波動率
        df['Volatility'] = df['Returns'].rolling(window=20).std()
        df['ATR'] = self._calculate_atr(df)
        
        # 成交量特徵
        df['Volume_Change'] = df['Volume'].pct_change()
        df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA5']
        
        # 價格位置
        df['BB_Upper'] = df['MA20'] + 2 * df['Close'].rolling(20).std()
        df['BB_Lower'] = df['MA20'] - 2 * df['Close'].rolling(20).std()
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # 動量
        df['Momentum_5'] = df['Close'].pct_change(5)
        df['Momentum_10'] = df['Close'].pct_change(10)
        df['Momentum_20'] = df['Close'].pct_change(20)
        
        # 高低價特徵
        df['HL_Ratio'] = (df['High'] - df['Low']) / df['Close']
        df['CO_Ratio'] = (df['Close'] - df['Open']) / df['Open']
        
        print(f"✅ 添加了 {len(df.columns) - 6} 個技術指標")
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算 ATR"""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=period).mean()
    
    def prepare_sequences(self, df: pd.DataFrame, seq_length: int = 30):
        """準備 LSTM 序列"""
        print(f"📦 創建序列（長度={seq_length}）...")
        
        # 清理數據
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        
        # 選擇特徵（不包含原始 OHLC）
        feature_cols = [
            'Returns', 'RSI', 'MACD', 'MACD_Hist', 'Volatility',
            'MA5_Ratio', 'MA20_Ratio', 'Volume_Ratio', 'BB_Position',
            'Momentum_5', 'Momentum_10', 'HL_Ratio', 'CO_Ratio'
        ]
        
        available_cols = [c for c in feature_cols if c in df.columns]
        
        # 歸一化
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        
        X_data = scaler_X.fit_transform(df[available_cols])
        y_data = scaler_y.fit_transform(df[['Close']])
        
        # 創建序列
        X, y = [], []
        for i in range(seq_length, len(X_data)):
            X.append(X_data[i-seq_length:i])
            y.append(y_data[i, 0])
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"✅ 序列形狀: X={X.shape}, y={y.shape}")
        
        return X, y, scaler_X, scaler_y, available_cols
    
    def split_data(self, X, y, train_ratio=0.8, val_ratio=0.1):
        """分割數據"""
        n = len(X)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        return {
            'X_train': X[:train_end],
            'y_train': y[:train_end],
            'X_val': X[train_end:val_end],
            'y_val': y[train_end:val_end],
            'X_test': X[val_end:],
            'y_test': y[val_end:]
        }
    
    def build_model(self, input_shape):
        """建構優化的 LSTM 模型"""
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
        from tensorflow.keras.optimizers import Adam
        from tensorflow.keras.regularizers import l2
        
        print("🔨 建構優化 LSTM 模型...")
        
        model = Sequential([
            # 第一層 LSTM
            LSTM(128, return_sequences=True, input_shape=input_shape,
                 kernel_regularizer=l2(0.001)),
            BatchNormalization(),
            Dropout(0.3),
            
            # 第二層 LSTM
            LSTM(64, return_sequences=True, kernel_regularizer=l2(0.001)),
            BatchNormalization(),
            Dropout(0.3),
            
            # 第三層 LSTM
            LSTM(32, kernel_regularizer=l2(0.001)),
            BatchNormalization(),
            Dropout(0.2),
            
            # 全連接層
            Dense(16, activation='relu'),
            Dense(1)
        ])
        
        optimizer = Adam(learning_rate=0.001)
        model.compile(optimizer=optimizer, loss='huber', metrics=['mae'])
        
        print(f"✅ 模型參數: {model.count_params():,}")
        return model
    
    def train(self, model, data, epochs=100, batch_size=32):
        """訓練模型"""
        from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
        
        print(f"\n🚀 開始訓練 {self.symbol}...")
        print(f"   訓練樣本: {len(data['X_train'])}")
        print(f"   驗證樣本: {len(data['X_val'])}")
        print(f"   測試樣本: {len(data['X_test'])}")
        
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=7, min_lr=1e-6, verbose=1),
            ModelCheckpoint(
                filepath=os.path.join(self.model_dir, f"{self.symbol}_best.keras"),
                monitor='val_loss', save_best_only=True, verbose=0
            )
        ]
        
        history = model.fit(
            data['X_train'], data['y_train'],
            validation_data=(data['X_val'], data['y_val']),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def evaluate(self, model, data, scaler_y):
        """評估模型"""
        print("\n📊 評估模型...")
        
        # 預測
        y_pred_scaled = model.predict(data['X_test'], verbose=0).flatten()
        
        # 反歸一化
        y_test_original = scaler_y.inverse_transform(data['y_test'].reshape(-1, 1)).flatten()
        y_pred_original = scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
        
        # 計算指標
        mse = mean_squared_error(y_test_original, y_pred_original)
        mae = mean_absolute_error(y_test_original, y_pred_original)
        r2 = r2_score(y_test_original, y_pred_original)
        mape = np.mean(np.abs((y_test_original - y_pred_original) / y_test_original)) * 100
        
        # 方向準確率
        actual_direction = np.sign(np.diff(y_test_original))
        pred_direction = np.sign(np.diff(y_pred_original))
        direction_accuracy = np.mean(actual_direction == pred_direction)
        
        metrics = {
            'symbol': self.symbol,
            'mse': float(mse),
            'mae': float(mae),
            'rmse': float(np.sqrt(mse)),
            'r2': float(r2),
            'mape': float(mape),
            'direction_accuracy': float(direction_accuracy),
            'trained_at': datetime.now().isoformat()
        }
        
        print(f"\n📈 效能指標:")
        print(f"   R²: {r2:.4f}")
        print(f"   MAPE: {mape:.2f}%")
        print(f"   方向準確率: {direction_accuracy:.2%}")
        print(f"   MAE: {mae:.2f}")
        
        return metrics
    
    def run(self):
        """執行完整訓練流程"""
        print("=" * 70)
        print(f"🧠 優化訓練 {self.symbol} LSTM 模型")
        print("=" * 70)
        
        # 1. 下載數據
        df = self.download_data()
        if df is None:
            return None
        
        # 2. 添加特徵
        df = self.add_features(df)
        
        # 3. 準備序列
        X, y, scaler_X, scaler_y, feature_cols = self.prepare_sequences(df, seq_length=30)
        
        # 4. 分割數據
        data = self.split_data(X, y)
        
        # 5. 建構模型
        model = self.build_model(input_shape=(X.shape[1], X.shape[2]))
        
        # 6. 訓練
        history = self.train(model, data, epochs=100, batch_size=32)
        
        # 7. 評估
        metrics = self.evaluate(model, data, scaler_y)
        
        # 8. 保存
        model_path = os.path.join(self.model_dir, f"{self.symbol}_model.keras")
        model.save(model_path)
        print(f"✅ 模型已保存: {model_path}")
        
        metrics_path = os.path.join(self.model_dir, f"{self.symbol}_metrics.json")
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"✅ 指標已保存: {metrics_path}")
        
        # 保存 scaler
        import joblib
        joblib.dump(scaler_X, os.path.join(self.model_dir, f"{self.symbol}_scaler_X.pkl"))
        joblib.dump(scaler_y, os.path.join(self.model_dir, f"{self.symbol}_scaler_y.pkl"))
        
        print("\n" + "=" * 70)
        print(f"✅ {self.symbol} 優化訓練完成！")
        print("=" * 70)
        
        return metrics


def main():
    """主函數"""
    print("\n" + "=" * 70)
    print("🚀 LSTM 模型優化訓練系統")
    print("=" * 70)
    
    # 檢查 TensorFlow
    try:
        import tensorflow as tf
        print(f"✅ TensorFlow 版本: {tf.__version__}")
    except ImportError:
        print("❌ 需要安裝 TensorFlow")
        return
    
    results = {}
    
    for symbol in STOCKS_TO_TRAIN:
        trainer = OptimizedLSTMTrainer(symbol, years=3)
        metrics = trainer.run()
        if metrics:
            results[symbol] = metrics
        print("\n")
    
    # 總結
    print("\n" + "=" * 70)
    print("📊 優化訓練總結")
    print("=" * 70)
    
    for symbol, metrics in results.items():
        print(f"\n{symbol}:")
        print(f"  R²: {metrics['r2']:.4f}")
        print(f"  方向準確率: {metrics['direction_accuracy']:.2%}")
        print(f"  MAPE: {metrics['mape']:.2f}%")
    
    print("\n" + "=" * 70)
    print(f"✅ 完成 {len(results)}/{len(STOCKS_TO_TRAIN)} 支股票優化訓練")
    print("=" * 70)
    print(f"\n📁 優化模型位置: models/lstm_optimized/")


if __name__ == "__main__":
    main()
