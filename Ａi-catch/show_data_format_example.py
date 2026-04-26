"""
LSTM 數據格式實例展示
生成真實的數據示例，幫助理解數據結構

執行: python3 show_data_format_example.py
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

print("=" * 70)
print("📊 LSTM 訓練系統 - 數據格式實例展示")
print("=" * 70)
print()

# ==================== 1. 原始數據示例 ====================

print("1️⃣  原始股票數據 (來自 yfinance)")
print("-" * 70)

# 模擬原始股票數據
dates = pd.date_range(start='2025-02-01', periods=10, freq='D')
raw_data = pd.DataFrame({
    'Date': dates,
    'Open': [645, 648, 650, 652, 655, 658, 660, 662, 665, 668],
    'High': [650, 655, 658, 660, 663, 665, 668, 670, 672, 675],
    'Low': [642, 645, 647, 649, 652, 655, 657, 659, 662, 665],
    'Close': [648, 652, 655, 658, 660, 662, 665, 668, 670, 672],
    'Volume': [25000000, 28000000, 26500000, 30000000, 32000000,
               29000000, 31000000, 33000000, 35000000, 34000000]
})

print(raw_data.to_string(index=False))
print(f"\n形狀: {raw_data.shape}")
print(f"列名: {list(raw_data.columns)}")

# ==================== 2. 特徵工程後 ====================

print("\n\n2️⃣  特徵工程後的數據")
print("-" * 70)

# 計算技術指標（簡化版）
feature_data = raw_data.copy()
feature_data['MA5'] = feature_data['Close'].rolling(window=5).mean()
feature_data['MA20'] = feature_data['Close'].rolling(window=20).mean().fillna(feature_data['Close'].mean())
feature_data['RSI'] = 60 + np.random.randn(len(feature_data)) * 5  # 模擬 RSI
feature_data['MACD'] = np.random.randn(len(feature_data)) * 2  # 模擬 MACD
feature_data['Volume_Ratio'] = feature_data['Volume'] / feature_data['Volume'].mean()
feature_data['Price_Change'] = feature_data['Close'].pct_change().fillna(0)

# 目標變量
feature_data['Future_Return'] = (feature_data['Close'].shift(-3) / feature_data['Close'] - 1).fillna(0)

# 移除初期的 NaN
feature_data = feature_data.iloc[4:].copy()

print(feature_data[['Date', 'Close', 'MA5', 'RSI', 'MACD', 'Volume_Ratio', 'Price_Change', 'Future_Return']].to_string(index=False))
print(f"\n形狀: {feature_data.shape}")
print(f"特徵數量: {len(feature_data.columns) - 5} (排除 OHLCV)")

# ==================== 3. 標準化後的數據 ====================

print("\n\n3️⃣  標準化後的數據")
print("-" * 70)

# 提取數值特徵
numeric_features = ['Close', 'MA5', 'RSI', 'MACD', 'Volume_Ratio', 'Price_Change', 'Future_Return']
numeric_data = feature_data[numeric_features].values

# 簡單標準化（模擬 RobustScaler）
from sklearn.preprocessing import RobustScaler
scaler = RobustScaler()
scaled_data = scaler.fit_transform(numeric_data)

scaled_df = pd.DataFrame(scaled_data, columns=numeric_features)
print(scaled_df.round(4).to_string(index=False))
print(f"\n形狀: {scaled_df.shape}")
print(f"\n標準化方法: RobustScaler (使用中位數和四分位距)")
print(f"  - 對異常值穩健")
print(f"  - 適合金融數據")

# ==================== 4. 時間序列格式 ====================

print("\n\n4️⃣  LSTM 輸入格式 (3D 張量)")
print("-" * 70)

# 創建一個時間序列樣本
lookback = 3  # 簡化為3天（實際是60天）
n_features = 6  # 簡化為6個特徵（實際是9個）

# 模擬一個樣本
sample_X = scaled_data[:lookback, :n_features]
sample_y = scaled_data[lookback-1, -1]

print(f"樣本 X (過去 {lookback} 天的 {n_features} 個特徵):")
print(f"形狀: {sample_X.shape}")
print()

for day in range(lookback):
    print(f"Day {day+1}:")
    print(f"  Close: {sample_X[day, 0]:.4f}")
    print(f"  MA5:   {sample_X[day, 1]:.4f}")
    print(f"  RSI:   {sample_X[day, 2]:.4f}")
    print(f"  MACD:  {sample_X[day, 3]:.4f}")
    print(f"  Vol_R: {sample_X[day, 4]:.4f}")
    print(f"  Pchg:  {sample_X[day, 5]:.4f}")
    print()

print(f"樣本 y (預測目標):")
print(f"形狀: ()")
print(f"值: {sample_y:.4f} (未來收益率)")

# ==================== 5. 完整數據集結構 ====================

print("\n\n5️⃣  完整數據集結構")
print("-" * 70)

# 模擬完整數據集
n_samples = 220  # 實際樣本數
lookback_real = 60
n_features_real = 9

print(f"輸入數據 X:")
print(f"  形狀: ({n_samples}, {lookback_real}, {n_features_real})")
print(f"  維度解釋:")
print(f"    - {n_samples}: 樣本數量")
print(f"    - {lookback_real}: 時間步長（回看 60 天）")
print(f"    - {n_features_real}: 特徵數量")
print()

print(f"目標數據 y:")
print(f"  形狀: ({n_samples},)")
print(f"  每個值代表未來 5 天的預測收益率")
print()

print(f"訓練集 / 測試集分割 (80/20):")
n_train = int(n_samples * 0.8)
n_test = n_samples - n_train
print(f"  訓練集 X: ({n_train}, {lookback_real}, {n_features_real})")
print(f"  訓練集 y: ({n_train},)")
print(f"  測試集 X: ({n_test}, {lookback_real}, {n_features_real})")
print(f"  測試集 y: ({n_test},)")

# ==================== 6. 批次數據 ====================

print("\n\n6️⃣  訓練批次數據")
print("-" * 70)

batch_size = 32
print(f"批次大小: {batch_size}")
print()

print(f"一個訓練批次:")
print(f"  X_batch: ({batch_size}, {lookback_real}, {n_features_real})")
print(f"  y_batch: ({batch_size},)")
print()

print(f"批次內容:")
print(f"  - {batch_size} 個樣本")
print(f"  - 每個樣本有 {lookback_real} 個時間步")
print(f"  - 每個時間步有 {n_features_real} 個特徵")
print(f"  - 對應 {batch_size} 個預測目標")

# ==================== 7. 特徵清單 ====================

print("\n\n7️⃣  9 個輸入特徵詳細說明")
print("-" * 70)

features_info = [
    ("1", "Close", "收盤價", "當日收盤價格"),
    ("2", "MA5", "5日均線", "過去5天收盤價平均"),
    ("3", "MA20", "20日均線", "過去20天收盤價平均"),
    ("4", "MA60", "60日均線", "過去60天收盤價平均"),
    ("5", "RSI", "相對強弱指數", "衡量超買超賣程度 (0-100)"),
    ("6", "MACD", "MACD指標", "短期與長期EMA差值"),
    ("7", "MACD_Signal", "MACD信號線", "MACD的9日EMA"),
    ("8", "Volume_Ratio", "成交量比率", "當日量/20日平均量"),
    ("9", "Price_Change", "價格變化率", "(今日收盤-昨日收盤)/昨日收盤")
]

for num, name, cn_name, desc in features_info:
    print(f"{num}. {name:15} ({cn_name:10}): {desc}")

print()
print("目標變量:")
print(f"   Future_Return (未來收益率): (5日後收盤-今日收盤)/今日收盤")

# ==================== 8. 數據示例矩陣 ====================

print("\n\n8️⃣  數據矩陣視覺化示例")
print("-" * 70)

print("\n單個樣本的 3D 張量結構:")
print()
print("X[0] =  # 第1個樣本 (60天 × 9特徵)")
print("┌─────────────────────────────────────────────────┐")
print("│ Day 1:  [0.234, 0.189, 0.156, ..., 0.145]      │")
print("│ Day 2:  [0.289, 0.212, 0.178, ..., 0.145]      │")
print("│ Day 3:  [0.267, 0.223, 0.189, ..., -0.089]     │")
print("│  ...                     ...                    │")
print("│ Day 60: [0.456, 0.412, 0.389, ..., 0.023]      │")
print("└─────────────────────────────────────────────────┘")
print("         ↓ LSTM 處理 ↓")
print("y[0] = 0.0154  # 預測的未來5天收益率")

# ==================== 9. 總結 ====================

print("\n\n" + "=" * 70)
print("📊 數據格式總結")
print("=" * 70)

summary = """
數據流程:
  原始數據 (365, 5) 
      ↓ 特徵工程
  特徵數據 (280, 10)
      ↓ 標準化
  標準化數據 (280, 10)
      ↓ 滑動窗口
  時間序列 X(220, 60, 9) + y(220,)
      ↓ 80/20分割
  訓練集(176, 60, 9) + 測試集(44, 60, 9)
      ↓ 批次訓練
  批次數據(32, 60, 9) → 模型訓練

關鍵參數:
  • 回看天數: 60天
  • 預測天數: 5天  
  • 輸入特徵: 9個
  • 批次大小: 32
  • 訓練/測試: 80/20
"""

print(summary)

print("\n✅ 數據格式展示完成！")
print("\n詳細文檔請查看: LSTM_DATA_FORMAT_GUIDE.md")
print("=" * 70)
