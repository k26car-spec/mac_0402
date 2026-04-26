# LSTM Smart Entry v2.0 訓練系統使用指南

## 📅 創建時間
2026-02-07 22:45

---

## 🎯 系統概述

這是一個整合深度學習 LSTM 到 Smart Entry v2.0 的訓練系統，專門為 ORB 監控股票列表設計。

### ✨ 主要特點

1. **深度學習架構**：3層 LSTM + BatchNormalization + Dropout
2. **智能優化器**：使用 Adam（比 SGD 更聰明的自適應學習率）
3. **完整訓練循環**：500 個 epochs，每 50 輪報告進度
4. **視覺化呈現**：Matplotlib 繪製損失曲線圖
5. **自動化流程**：批量訓練 ORB 監控列表中的所有股票

---

## 🏗️ 系統架構

### LSTM 模型結構

```
輸入層 (60, 9)  ← 60天回看，9個特徵
    ↓
LSTM Layer 1 (128 units) + BatchNorm + Dropout(0.3)
    ↓
LSTM Layer 2 (64 units) + BatchNorm + Dropout(0.3)
    ↓
LSTM Layer 3 (32 units) + BatchNorm + Dropout(0.3)
    ↓
Dense Output (1) ← 預測未來5天收益率
```

### 技術指標特徵

系統使用以下 9 個特徵：

1. **Close** - 收盤價
2. **MA5** - 5日移動平均
3. **MA20** - 20日移動平均
4. **MA60** - 60日移動平均
5. **RSI** - 相對強弱指數
6. **MACD** - MACD指標
7. **MACD_Signal** - MACD信號線
8. **Volume_Ratio** - 成交量比率
9. **Price_Change** - 價格變化率

### 激活函數

LSTM 層內部使用：
- **Tanh** (雙曲正切) - 單元狀態和隱藏狀態
- **Sigmoid** (σ) - 遺忘門、輸入門、輸出門

---

## 🚀 使用方法

### 1. 環境準備

首先安裝必要的套件：

```bash
# 安裝 TensorFlow
pip install tensorflow

# 安裝其他依賴
pip install numpy pandas matplotlib scikit-learn yfinance
```

### 2. 檢查 ORB 監控列表

確認監控列表存在：

```bash
cat /Users/Mac/Documents/ETF/AI/Ａi-catch/data/orb_watchlist.json
```

當前列表包含 50 支股票。

### 3. 開始訓練

執行訓練腳本：

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 train_lstm_smart_entry_v2.py
```

### 4. 訓練過程

系統會：
1. 載入 ORB 監控列表（50支股票）
2. 逐一獲取每支股票的歷史數據
3. 進行特徵工程（計算技術指標）
4. 創建時間序列數據
5. 訓練 LSTM 模型（500 epochs）
6. 每 50 個 epoch 打印當前損失
7. 保存訓練好的模型
8. 繪製損失曲線圖

---

## 📊 輸出說明

### 控制台輸出示例

```
========================================================================
🤖 LSTM Smart Entry v2.0 - 深度學習訓練系統
========================================================================

📋 訓練配置:
  • 回看天數: 60 天
  • 預測天數: 5 天
  • LSTM 架構: 128 -> 64 -> 32 units
  • Dropout率: 0.3
  • 批次大小: 32
  • 訓練輪數: 500 epochs
  • 學習率: 0.001
  • 優化器: Adam (自適應學習率)
  • 損失函數: MSE (均方誤差)

✅ 載入 50 支 ORB 監控股票
📊 將訓練 50 支股票

============================================================
🎯 開始訓練: 2330
============================================================
  📊 2330: 獲取 365 天數據
  訓練集: 192 樣本
  測試集: 48 樣本
  特徵維度: 9

🚀 開始訓練 500 個 Epochs...
📝 優化器: Adam (比 SGD 更聰明，自適應學習率)
📉 損失函數: MSE (均方誤差)

📊 Epoch 50/500 | Loss: 0.001234 | Val Loss: 0.001456 | MAE: 0.025678
📊 Epoch 100/500 | Loss: 0.000987 | Val Loss: 0.001234 | MAE: 0.022345
📊 Epoch 150/500 | Loss: 0.000756 | Val Loss: 0.001123 | MAE: 0.019876
...
📊 Epoch 500/500 | Loss: 0.000234 | Val Loss: 0.000567 | MAE: 0.012345

✅ 訓練完成！
  訓練集 Loss: 0.000234
  測試集 Loss: 0.000567
  💾 模型已保存: /Users/Mac/Documents/ETF/AI/Ａi-catch/models/lstm_smart_entry/2330_model.h5
```

### 保存的文件

訓練完成後會生成以下文件：

1. **模型文件** (每支股票)
   ```
   /models/lstm_smart_entry/{股票代碼}_model.h5
   ```

2. **訓練曲線圖**
   ```
   /training_results/training_curves_20260207_224500.png
   ```
   - 顯示每支股票的損失下降過程
   - 標註最小損失點
   - 展示「機器如何一步一步減少痛苦」

3. **統計圖表**
   ```
   /training_results/overall_statistics_20260207_224500.png
   ```
   - 各股票最終測試損失分佈
   - 訓練 vs 測試損失比較

4. **訓練報告**
   ```
   /models/lstm_smart_entry/training_report_20260207_224500.json
   ```
   - 完整的訓練配置
   - 每支股票的詳細結果
   - 成功/失敗統計

---

## 🔍 為什麼使用 Adam 而不是 SGD？

### Adam 優化器的優勢

```python
# Adam 優化器 (Adaptive Moment Estimation)
optimizer = Adam(
    learning_rate=0.001,
    beta_1=0.9,   # 一階動量衰減率
    beta_2=0.999  # 二階動量衰減率
)
```

#### 1. **自適應學習率** 🎯
- 每個參數都有獨立的學習率
- 自動調整每個權重的更新幅度
- SGD 對所有參數使用相同的學習率

#### 2. **動量累積** 🚀
- 結合過去梯度的信息
- 避免訓練過程中的震盪
- 更平滑的收斂過程

#### 3. **收斂更快** ⚡
- 通常需要更少的 epochs
- 在複雜的損失函數地形中表現更好
- 適合深度神經網絡

#### 4. **適合稀疏梯度** 📊
- 金融時間序列數據常常有稀疏特徵
- Adam 能更好地處理這種情況
- SGD 可能陷入局部最優

#### 5. **對超參數不敏感** 🎛️
- 默認參數通常就很好
- SGD 需要仔細調整學習率
- 減少超參數調優的工作量

### 對比表格

| 特性 | SGD | Adam |
|------|-----|------|
| 學習率 | 固定（需手動調整） | 自適應（自動調整） |
| 收斂速度 | 較慢 | 較快 |
| 穩定性 | 容易震盪 | 更平滑 |
| 超參數敏感度 | 高 | 低 |
| 適用場景 | 簡單模型 | 深度神經網絡 |
| 記憶體需求 | 低 | 稍高 |

---

## 📈 損失函數：MSE (均方誤差)

### 為什麼使用 MSE？

```python
model.compile(
    optimizer=optimizer,
    loss='mse',  # Mean Squared Error
    metrics=['mae', 'mse']
)
```

#### MSE 的定義

$$MSE = \frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2$$

其中：
- $y_i$ = 實際收益率
- $\hat{y}_i$ = 預測收益率
- $n$ = 樣本數量

#### 優點

1. **平方懲罰**：大誤差被平方放大，模型更關注減少大誤差
2. **可微分**：在任何點都可微，適合梯度下降
3. **統計意義**：與高斯分佈的最大似然估計一致
4. **廣泛認可**：回歸問題的標準損失函數

#### 解釋

- **MSE 越小** = 預測越準確 = "痛苦"越少
- **訓練目標** = 最小化 MSE = 讓機器"不再痛苦"

---

## 🎨 損失曲線圖解讀

### 理想的訓練曲線

```
Loss
 │
高│  ╲
 │   ╲
 │    ╲___
 │        ╲___          訓練損失（藍線）
 │            ╲___
 │                ╲___
 │                    ╲___
低│                        ━━━━━━━━━━━━
 └─────────────────────────────────> Epochs
                                    0 → 500
```

### 三種典型情況

#### 1. **理想收斂** ✅
- 訓練損失和驗證損失都下降
- 兩條曲線接近
- 最終趨於平穩

#### 2. **過擬合** ⚠️
- 訓練損失持續下降
- 驗證損失開始上升
- 解決方法：增加 Dropout、減少 epochs

#### 3. **欠擬合** ⚠️
- 兩條曲線都很高
- 下降緩慢或停滯
- 解決方法：增加模型複雜度、增加特徵

---

## 🔧 高級配置

### 修改訓練參數

在 `train_lstm_smart_entry_v2.py` 中找到 `TrainingConfig` 類：

```python
class TrainingConfig:
    # 數據參數
    LOOKBACK_DAYS = 60          # 回看天數（可改為 30, 90）
    PREDICTION_DAYS = 5         # 預測天數（可改為 1, 3, 10）
    
    # 模型參數
    LSTM_UNITS = [128, 64, 32]  # LSTM 層（可改為 [256, 128, 64]）
    DROPOUT_RATE = 0.3          # Dropout（可改為 0.2, 0.4）
    EPOCHS = 500                # 訓練輪數（可改為 300, 1000）
    LEARNING_RATE = 0.001       # 學習率（可改為 0.0001, 0.01）
```

### 添加更多股票

編輯監控列表：

```bash
nano /Users/Mac/Documents/ETF/AI/Ａi-catch/data/orb_watchlist.json
```

添加股票代碼到 `watchlist` 數組中。

---

## 🚨 常見問題

### Q1: TensorFlow 安裝失敗

```bash
# macOS (Apple Silicon)
pip install tensorflow-macos tensorflow-metal

# macOS (Intel) / Linux / Windows
pip install tensorflow
```

### Q2: 記憶體不足

減少批次大小：
```python
BATCH_SIZE = 16  # 改為 16 (原本 32)
```

### Q3: 訓練時間太長

減少 epochs 或股票數量：
```python
EPOCHS = 200  # 改為 200 (原本 500)
```

或只訓練前 10 支股票進行測試。

### Q4: 部分股票無數據

正常現象。系統會自動跳過數據不足的股票，繼續訓練其他股票。

---

## 📚 下一步：整合到 Smart Entry v2

訓練完成後，您可以：

### 方案 1：預測輔助評分

在 `smart_entry_system.py` 中添加 LSTM 預測：

```python
async def evaluate_stock(self, symbol: str) -> Dict:
    # 原有規則評分
    confidence = self._calculate_rule_based_score(data)
    
    # 🆕 添加 LSTM 預測
    try:
        import tensorflow as tf
        model = tf.keras.models.load_model(
            f'/Users/Mac/Documents/ETF/AI/Ａi-catch/models/lstm_smart_entry/{symbol}_model.h5'
        )
        
        # 準備輸入數據
        X = prepare_lstm_input(symbol)
        
        # 預測未來收益
        prediction = model.predict(X)[0][0]
        
        # 調整信心度
        if prediction > 0.03:  # 預測上漲 > 3%
            confidence += 15
            logger.info(f"🤖 LSTM 預測 {symbol} 上漲 {prediction*100:.1f}%，信心度 +15")
        elif prediction < -0.02:  # 預測下跌 > 2%
            confidence -= 20
            logger.warning(f"🤖 LSTM 預測 {symbol} 下跌 {prediction*100:.1f}%，信心度 -20")
    
    except Exception as e:
        logger.debug(f"LSTM 預測失敗: {e}")
    
    return {'confidence': confidence, ...}
```

### 方案 2：獨立 LSTM 信號系統

創建新的 LSTM 信號生成器，與 smart_entry_v2 並行運行。

---

## ✅ 總結

這個訓練系統提供了：

1. ✅ **完整的深度學習流程**：數據準備 → 訓練 → 評估 → 可視化
2. ✅ **智能優化器**：Adam 自適應學習率
3. ✅ **MSE 損失函數**：適合回歸問題
4. ✅ **500 Epochs 訓練**：充分學習數據模式
5. ✅ **視覺化報告**：損失曲線圖展示訓練過程
6. ✅ **批量處理**：自動訓練 ORB 監控列表所有股票

**現在您可以看到機器如何一步一步減少痛苦（降低損失）！** 📉🤖

---

## 📞 技術支持

如有問題，請查看：
- 訓練日誌: 控制台輸出
- 訓練報告: `/models/lstm_smart_entry/training_report_*.json`
- 損失曲線: `/training_results/training_curves_*.png`

**祝您訓練順利！** 🚀
