# LSTM 訓練系統數據格式詳解

## 📊 數據結構總覽

```
原始股票數據 (yfinance)
    ↓
特徵工程 (計算技術指標)
    ↓
數據標準化 (RobustScaler)
    ↓
創建時間序列 (60天回看窗口)
    ↓
LSTM 輸入格式 (3D 張量)
```

---

## 1️⃣ 原始數據格式

### 來源：yfinance API

```python
import yfinance as yf

# 獲取台積電 (2330) 過去365天數據
ticker = yf.Ticker("2330.TW")
df = ticker.history(period="365d")
```

### 原始 DataFrame 結構

| 日期 | Open | High | Low | Close | Volume |
|------|------|------|-----|-------|--------|
| 2025-02-08 | 645.0 | 650.0 | 642.0 | 648.0 | 25000000 |
| 2025-02-09 | 648.0 | 655.0 | 647.0 | 652.0 | 28000000 |
| ... | ... | ... | ... | ... | ... |

**欄位說明：**
- `Open`: 開盤價
- `High`: 最高價
- `Low`: 最低價
- `Close`: 收盤價
- `Volume`: 成交量

**形狀：** `(365, 5)` - 365天 × 5個欄位

---

## 2️⃣ 特徵工程後的數據

### 計算的技術指標

```python
def prepare_features(df):
    # 移動平均線
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # RSI (相對強弱指數)
    df['RSI'] = calculate_rsi(df['Close'], period=14)
    
    # MACD
    df['MACD'] = calculate_macd(df['Close'])
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
    
    # 成交量比率
    df['Volume_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    
    # 價格變化率
    df['Price_Change'] = df['Close'].pct_change()
    
    # 目標變量：未來5天收益率
    df['Future_Return'] = df['Close'].shift(-5) / df['Close'] - 1
    
    return df.dropna()
```

### 完整特徵 DataFrame

| 日期 | Close | MA5 | MA20 | MA60 | RSI | MACD | MACD_Signal | Volume_Ratio | Price_Change | Future_Return |
|------|-------|-----|------|------|-----|------|-------------|--------------|--------------|---------------|
| 2025-02-08 | 648.0 | 645.2 | 642.5 | 635.8 | 58.3 | 2.45 | 1.82 | 1.15 | 0.0062 | 0.0154 |
| 2025-02-09 | 652.0 | 646.8 | 643.2 | 636.1 | 61.2 | 2.87 | 2.15 | 1.28 | 0.0062 | 0.0123 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**特徵數量：** 10 個
- 9 個輸入特徵 (Close ~ Price_Change)
- 1 個目標變量 (Future_Return)

**形狀：** `(280, 10)` - 清理 NaN 後約 280 天

---

## 3️⃣ 數據標準化

### 使用 RobustScaler

```python
from sklearn.preprocessing import RobustScaler

scaler = RobustScaler()
data_scaled = scaler.fit_transform(data)
```

### 標準化前後對比

**標準化前：**
```
Close: 648.0, MA5: 645.2, RSI: 58.3, MACD: 2.45, ...
```

**標準化後：**
```
Close: 0.234, MA5: 0.189, RSI: 0.412, MACD: 0.678, ...
```

**為什麼用 RobustScaler？**
- 使用中位數和四分位距
- 對異常值不敏感
- 適合金融數據（常有極端值）

**形狀不變：** `(280, 10)`

---

## 4️⃣ 創建時間序列

### 滑動窗口法

```python
LOOKBACK_DAYS = 60  # 回看60天
PREDICTION_DAYS = 5  # 預測未來5天

def create_sequences(data, lookback=60):
    X, y = [], []
    
    for i in range(lookback, len(data)):
        # X: 過去60天的9個特徵
        X.append(data[i-lookback:i, :-1])  # 排除最後一列（目標變量）
        
        # y: 未來5天的收益率
        y.append(data[i-1, -1])  # 最後一列（Future_Return）
    
    return np.array(X), np.array(y)
```

### 時間序列示意圖

```
原始數據：280 天

╔════════════════════════════════════════════════╗
║ Day 1  Day 2  ...  Day 60 ║ Day 61 ║ ... Day 65 ║
║ ←─── 輸入特徵 (X) ───────→ ║  預測點 ║  預測目標   ║
╚════════════════════════════════════════════════╝

第1個樣本：
- X[0]: Day 1~60 的 9 個特徵 → 形狀 (60, 9)
- y[0]: Day 60 預測未來 5 天的收益率 → 形狀 ()

第2個樣本：
- X[1]: Day 2~61 的 9 個特徵 → 形狀 (60, 9)
- y[1]: Day 61 預測未來 5 天的收益率 → 形狀 ()

...

總共樣本數：280 - 60 = 220 個
```

---

## 5️⃣ LSTM 輸入格式

### 最終數據形狀

```python
X.shape = (220, 60, 9)
y.shape = (220,)
```

**維度解釋：**
- **220**: 樣本數量（samples）
- **60**: 時間步長（timesteps / lookback days）
- **9**: 特徵數量（features）

### 3D 張量結構

```
X[0] =  # 第1個樣本
[
    # Day 1
    [Close_scaled, MA5_scaled, MA20_scaled, ..., Price_Change_scaled],
    
    # Day 2
    [Close_scaled, MA5_scaled, MA20_scaled, ..., Price_Change_scaled],
    
    # ...
    
    # Day 60
    [Close_scaled, MA5_scaled, MA20_scaled, ..., Price_Change_scaled]
]
形狀: (60, 9)

y[0] = 0.0154  # 對應的未來收益率
```

### 訓練集 / 測試集分割

```python
# 80/20 分割
split_idx = int(220 * 0.8)  # 176

X_train = X[:176]    # 形狀: (176, 60, 9)
X_test = X[176:]     # 形狀: (44, 60, 9)

y_train = y[:176]    # 形狀: (176,)
y_test = y[176:]     # 形狀: (44,)
```

---

## 6️⃣ 實際數據示例

### 示例：2330 台積電

```python
# 1. 原始數據（部分）
原始 DataFrame (前5行):
         Date    Close  Volume
0  2025-02-08  648.00  25000000
1  2025-02-09  652.00  28000000
2  2025-02-10  650.00  26500000
3  2025-02-11  655.00  30000000
4  2025-02-12  658.00  32000000

# 2. 特徵工程後（部分）
特徵 DataFrame (前3行):
         Date    Close    MA5   MA20   MA60    RSI   MACD  MACD_Sig  Vol_Ratio  Price_Chg  Future_Ret
0  2025-03-15  648.00  645.2  642.5  635.8   58.3   2.45     1.82       1.15      0.0062      0.0154
1  2025-03-16  652.00  646.8  643.2  636.1   61.2   2.87     2.15       1.28      0.0062      0.0123
2  2025-03-17  650.00  647.5  643.8  636.4   59.8   2.65     2.28       1.21     -0.0031      0.0108

# 3. 標準化後（部分）
標準化數據 (前3行):
[[0.234, 0.189, 0.156, -0.012, 0.412, 0.678, 0.534, 0.089, 0.145, 0.523],
 [0.289, 0.212, 0.178, -0.001, 0.498, 0.789, 0.612, 0.156, 0.145, 0.412],
 [0.267, 0.223, 0.189,  0.005, 0.456, 0.712, 0.645, 0.123, -0.089, 0.378]]

# 4. 時間序列格式
X[0].shape = (60, 9)  # 60天 × 9個特徵
y[0] = 0.523          # 標準化後的未來收益率

# 5. 批次數據
一個訓練批次 (batch_size=32):
X_batch.shape = (32, 60, 9)  # 32個樣本 × 60天 × 9特徵
y_batch.shape = (32,)         # 32個目標值
```

---

## 7️⃣ 數據流程完整示例

### Python 代碼示例

```python
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import RobustScaler

# ========== 步驟 1: 獲取原始數據 ==========
ticker = yf.Ticker("2330.TW")
df = ticker.history(period="365d")
print(f"原始數據: {df.shape}")  # (365, 5)

# ========== 步驟 2: 特徵工程 ==========
# 計算技術指標
df['MA5'] = df['Close'].rolling(5).mean()
df['MA20'] = df['Close'].rolling(20).mean()
df['MA60'] = df['Close'].rolling(60).mean()
# ... 其他指標

# 目標變量
df['Future_Return'] = df['Close'].shift(-5) / df['Close'] - 1

# 移除 NaN
df = df.dropna()
print(f"特徵工程後: {df.shape}")  # (280, 10)

# ========== 步驟 3: 提取特徵和目標 ==========
feature_cols = ['Close', 'MA5', 'MA20', 'MA60', 'RSI', 
                'MACD', 'MACD_Signal', 'Volume_Ratio', 
                'Price_Change', 'Future_Return']
data = df[feature_cols].values
print(f"數據矩陣: {data.shape}")  # (280, 10)

# ========== 步驟 4: 標準化 ==========
scaler = RobustScaler()
data_scaled = scaler.fit_transform(data)
print(f"標準化後: {data_scaled.shape}")  # (280, 10)

# ========== 步驟 5: 創建時間序列 ==========
lookback = 60

X, y = [], []
for i in range(lookback, len(data_scaled)):
    X.append(data_scaled[i-lookback:i, :-1])  # 9 個特徵
    y.append(data_scaled[i-1, -1])             # 目標變量

X = np.array(X)
y = np.array(y)
print(f"X 形狀: {X.shape}")  # (220, 60, 9)
print(f"y 形狀: {y.shape}")  # (220,)

# ========== 步驟 6: 分割訓練/測試集 ==========
split_idx = int(len(X) * 0.8)

X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

print(f"訓練集 X: {X_train.shape}")  # (176, 60, 9)
print(f"訓練集 y: {y_train.shape}")  # (176,)
print(f"測試集 X: {X_test.shape}")   # (44, 60, 9)
print(f"測試集 y: {y_test.shape}")   # (44,)

# ========== 步驟 7: 輸入 LSTM ==========
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(60, 9)),
    LSTM(32),
    Dense(16, activation='relu'),
    Dense(1)
])

model.compile(optimizer='adam', loss='mse')

# 訓練
model.fit(X_train, y_train, 
          validation_data=(X_test, y_test),
          epochs=100, 
          batch_size=32)
```

---

## 8️⃣ 數據格式總結表

| 階段 | 數據類型 | 形狀 | 說明 |
|------|---------|------|------|
| 1. 原始數據 | DataFrame | (365, 5) | OHLCV |
| 2. 特徵工程 | DataFrame | (280, 10) | +技術指標 |
| 3. 標準化 | ndarray | (280, 10) | RobustScaler |
| 4. 時間序列 X | ndarray | (220, 60, 9) | 3D 張量 |
| 4. 時間序列 y | ndarray | (220,) | 1D 向量 |
| 5. 訓練集 X | ndarray | (176, 60, 9) | 80% |
| 5. 測試集 X | ndarray | (44, 60, 9) | 20% |

---

## 9️⃣ 特徵詳細說明

### 9 個輸入特徵

| # | 特徵名稱 | 類型 | 範圍 | 說明 |
|---|---------|------|------|------|
| 1 | Close | 價格 | 標準化後 -2~2 | 收盤價 |
| 2 | MA5 | 均線 | 標準化後 -2~2 | 5日移動平均 |
| 3 | MA20 | 均線 | 標準化後 -2~2 | 20日移動平均 |
| 4 | MA60 | 均線 | 標準化後 -2~2 | 60日移動平均 |
| 5 | RSI | 指標 | 標準化後 -2~2 | 相對強弱指數 |
| 6 | MACD | 指標 | 標準化後 -2~2 | MACD值 |
| 7 | MACD_Signal | 指標 | 標準化後 -2~2 | MACD信號線 |
| 8 | Volume_Ratio | 比率 | 標準化後 -2~2 | 成交量比率 |
| 9 | Price_Change | 變化率 | 標準化後 -2~2 | 價格變化率 |

### 1 個目標變量

| 特徵名稱 | 類型 | 範圍 | 說明 |
|---------|------|------|------|
| Future_Return | 收益率 | 標準化後 -2~2 | 未來5天收益率 |

---

## 🔟 實際訓練時的數據批次

### Batch 示例

```python
# 訓練時的一個批次
batch_size = 32

# 從訓練集中取一個批次
X_batch = X_train[0:32]    # 形狀: (32, 60, 9)
y_batch = y_train[0:32]    # 形狀: (32,)

# 輸入 LSTM
predictions = model.predict(X_batch)  # 形狀: (32, 1)
```

### 批次數據視覺化

```
Batch (32 個樣本):
┌─────────────────────────────────────────────┐
│ 樣本 1: (60天 × 9特徵) → 預測值 1          │
│ 樣本 2: (60天 × 9特徵) → 預測值 2          │
│ 樣本 3: (60天 × 9特徵) → 預測值 3          │
│ ...                                          │
│ 樣本 32: (60天 × 9特徵) → 預測值 32        │
└─────────────────────────────────────────────┘

每個樣本的詳細結構:
┌─ Day 1 ──┬─ Day 2 ──┬─ ... ─┬─ Day 60 ─┐
│ Feature 1│ Feature 1│        │ Feature 1│
│ Feature 2│ Feature 2│        │ Feature 2│
│ ...      │ ...      │        │ ...      │
│ Feature 9│ Feature 9│        │ Feature 9│
└──────────┴──────────┴────────┴──────────┘
     ↓
  預測未來5天收益率
```

---

## ✅ 總結

### 數據流程
```
yfinance API (365天)
    ↓ 特徵工程
DataFrame (280天, 10特徵)
    ↓ RobustScaler
標準化數據 (280, 10)
    ↓ 滑動窗口
時間序列 X(220, 60, 9) + y(220,)
    ↓ 80/20分割
訓練集(176, 60, 9) + 測試集(44, 60, 9)
    ↓ Batch=32
模型輸入(32, 60, 9)
```

### 關鍵參數
- **回看天數**: 60天
- **預測天數**: 5天
- **特徵數量**: 9個
- **樣本數**: ~220個
- **訓練/測試比**: 80/20
- **批次大小**: 32

**現在您完全了解LSTM訓練系統的數據格式了！** 📊✨
