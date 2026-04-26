# LSTM 訓練系統 - 完成報告

## 📅 創建時間
2026-02-07 22:46

---

## ✅ 已完成的工作

### 1. **核心訓練腳本** 
文件：`train_lstm_smart_entry_v2.py`

#### 主要功能：
- ✅ 完整的 LSTM 訓練循環
- ✅ 使用 **MSE (均方誤差)** 作為損失函數
- ✅ 使用 **Adam 優化器**（自適應學習率，比 SGD 聰明）
- ✅ 訓練 **500 個 Epochs**
- ✅ 每 **50 輪** 打印當前損失值
- ✅ **Matplotlib 損失曲線圖**（展示機器如何減少痛苦）
- ✅ 自動訓練 **ORB 監控列表**中的所有股票（50支）

#### LSTM 架構：
```
輸入 (60天, 9特徵)
    ↓
LSTM-128 + BatchNorm + Dropout(0.3)
    ↓
LSTM-64 + BatchNorm + Dropout(0.3)
    ↓
LSTM-32 + BatchNorm + Dropout(0.3)
    ↓
Dense-1 輸出（預測未來5天收益率）
```

#### 激活函數：
- **Tanh** - LSTM 單元狀態
- **Sigmoid** - LSTM 門控機制（遺忘門、輸入門、輸出門）

---

### 2. **使用指南文檔**
文件：`LSTM_TRAINING_GUIDE.md`

#### 內容包括：
- ✅ 系統架構說明
- ✅ 技術指標特徵介紹
- ✅ 激活函數詳解
- ✅ 使用方法步驟
- ✅ **為什麼使用 Adam 而不是 SGD**（附詳細原因）
- ✅ MSE 損失函數解釋
- ✅ 損失曲線圖解讀方法
- ✅ 高級配置選項
- ✅ 常見問題解答
- ✅ 如何整合到 Smart Entry v2

---

### 3. **一鍵啟動腳本**
文件：`start_lstm_training.sh`

#### 功能：
- ✅ 自動檢查 Python 環境
- ✅ 自動安裝必要套件（TensorFlow, numpy, pandas等）
- ✅ 檢查 ORB 監控列表
- ✅ 創建輸出目錄
- ✅ 顯示訓練配置
- ✅ 確認提示
- ✅ 執行訓練
- ✅ 訓練完成後自動打開結果目錄

---

## 🎯 為什麼使用 Adam 優化器？

### Adam vs SGD 對比

| 特性 | SGD | Adam |
|------|-----|------|
| **學習率** | 固定，需手動調整 | 自適應，自動調整 |
| **收斂速度** | 較慢 | ⚡ **更快** |
| **穩定性** | 容易震盪 | ✅ **更平滑** |
| **超參數敏感度** | 高，需仔細調整 | ✅ **低，默認參數即可** |
| **適用場景** | 簡單模型 | ✅ **深度神經網絡** |
| **處理稀疏梯度** | 較差 | ✅ **優秀** |

### Adam 的五大優勢：

#### 1. 🎯 **自適應學習率**
- 每個參數都有獨立的學習率
- 自動調整每個權重的更新幅度
- 不需要手動調參

#### 2. 🚀 **動量累積**
```python
# Adam 內部機制
m_t = beta_1 * m_t-1 + (1-beta_1) * gradient  # 一階動量
v_t = beta_2 * v_t-1 + (1-beta_2) * gradient² # 二階動量
```
- 結合過去梯度信息
- 避免訓練震盪
- 更平滑的收斂

#### 3. ⚡ **收斂更快**
- 通常需要更少的 epochs
- 在複雜損失函數中表現更好
- 適合深度 LSTM 網絡

#### 4. 📊 **適合稀疏梯度**
- 金融時間序列數據常有稀疏特徵
- Adam 能更好處理這種情況
- SGD 可能陷入局部最優

#### 5. 🎛️ **對超參數不敏感**
```python
optimizer = Adam(
    learning_rate=0.001,  # 默認值通常就很好
    beta_1=0.9,           # 一階動量衰減
    beta_2=0.999          # 二階動量衰減
)
```

---

## 📉 MSE (均方誤差) 損失函數

### 定義

$$MSE = \frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2$$

### 為什麼用於股價預測？

1. **平方懲罰**：大誤差被放大，鼓勵模型減少極端錯誤
2. **可微分**：平滑的梯度，適合梯度下降
3. **統計意義**：與高斯分佈的最大似然估計一致
4. **標準選擇**：回歸問題的黃金標準

### 解釋「痛苦」

- **MSE = 0.001**：預測非常準確，機器很開心 😊
- **MSE = 0.1**：預測有誤差，機器有點痛苦 😐
- **MSE = 1.0**：預測很差，機器很痛苦 😫

**訓練目標 = 讓 MSE 從 1.0 降到 0.001 = 機器從痛苦到開心！**

---

## 📊 訓練過程展示

### 控制台輸出示例

```bash
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

📊 Epoch 50/500 | Loss: 0.012345 | Val Loss: 0.015678 | MAE: 0.098765
📊 Epoch 100/500 | Loss: 0.008765 | Val Loss: 0.011234 | MAE: 0.076543
📊 Epoch 150/500 | Loss: 0.005432 | Val Loss: 0.008765 | MAE: 0.054321
📊 Epoch 200/500 | Loss: 0.003210 | Val Loss: 0.006543 | MAE: 0.043210
📊 Epoch 250/500 | Loss: 0.001987 | Val Loss: 0.004321 | MAE: 0.032109
📊 Epoch 300/500 | Loss: 0.001234 | Val Loss: 0.003210 | MAE: 0.025678
📊 Epoch 350/500 | Loss: 0.000876 | Val Loss: 0.002543 | MAE: 0.019876
📊 Epoch 400/500 | Loss: 0.000543 | Val Loss: 0.001987 | MAE: 0.014321
📊 Epoch 450/500 | Loss: 0.000321 | Val Loss: 0.001543 | MAE: 0.010987
📊 Epoch 500/500 | Loss: 0.000234 | Val Loss: 0.001234 | MAE: 0.008765

✅ 訓練完成！
  訓練集 Loss: 0.000234
  測試集 Loss: 0.001234
  💾 模型已保存
```

### 損失曲線圖

```
Loss (痛苦值)
 │
0.015│  ●
     │   ●
0.012│    ●
     │     ●●
0.009│       ●●
     │         ●●
0.006│           ●●●
     │              ●●●
0.003│                 ●●●●
     │                     ●●●●●________
0.000│                               ●●●●●
     └──────────────────────────────────────> Epochs
     0   50  100  150  200  250  300  350  400  450  500
     
     機器從痛苦 → 開心的過程！
```

---

## 🚀 如何使用

### 方法 1：使用啟動腳本（推薦）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_lstm_training.sh
```

這個腳本會：
1. ✅ 檢查環境
2. ✅ 安裝依賴
3. ✅ 確認開始訓練
4. ✅ 執行訓練
5. ✅ 打開結果目錄

### 方法 2：直接執行 Python 腳本

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 train_lstm_smart_entry_v2.py
```

---

## 📁 輸出文件

訓練完成後會生成：

### 1. 模型文件（每支股票）
```
/models/lstm_smart_entry/2330_model.h5
/models/lstm_smart_entry/2317_model.h5
/models/lstm_smart_entry/2454_model.h5
...（共 50 個）
```

### 2. 訓練曲線圖
```
/training_results/training_curves_20260207_224500.png
```
- 每支股票的損失下降曲線
- 標註最小損失點
- 展示「機器如何一步一步減少痛苦」

### 3. 統計圖表
```
/training_results/overall_statistics_20260207_224500.png
```
- 各股票最終損失分佈
- 訓練 vs 測試損失對比

### 4. 訓練報告
```
/models/lstm_smart_entry/training_report_20260207_224500.json
```
- 完整訓練配置
- 每支股票詳細結果
- 成功/失敗統計

---

## 🎨 損失曲線圖解讀

### 圖表元素

1. **藍色實線**：訓練損失（Training Loss）
2. **紅色虛線**：驗證損失（Validation Loss）
3. **綠色星號**：最小驗證損失點
4. **黃色標註**：最佳 Epoch 和最小損失值

### 理想狀態

- ✅ 訓練損失持續下降
- ✅ 驗證損失也下降
- ✅ 兩條線接近（沒有過擬合）
- ✅ 最終趨於平穩

### 需要注意

- ⚠️ 驗證損失上升：可能過擬合
- ⚠️ 損失停滯：可能需要更多數據或調整模型
- ⚠️ 損失震盪：可能需要降低學習率

---

## 📚 下一步：整合到 Smart Entry v2

訓練完成後，可以整合 LSTM 預測到 smart_entry_v2：

### 在 `smart_entry_system.py` 中添加：

```python
async def evaluate_stock(self, symbol: str) -> Dict:
    # 原有規則評分（60分）
    confidence = self._calculate_rule_based_score(data)
    
    # 🆕 添加 LSTM 預測（最多 ±20分）
    try:
        import tensorflow as tf
        import numpy as np
        
        # 載入模型
        model_path = f'/Users/Mac/Documents/ETF/AI/Ａi-catch/models/lstm_smart_entry/{symbol}_model.h5'
        model = tf.keras.models.load_model(model_path)
        
        # 準備輸入數據（60天，9特徵）
        X = await self._prepare_lstm_input(symbol)
        
        # 預測未來5天收益率
        predicted_return = model.predict(X, verbose=0)[0][0]
        
        # 調整信心度
        if predicted_return > 0.03:  # 預測上漲 > 3%
            confidence += 20
            logger.info(f"🤖 LSTM: {symbol} 預測上漲 {predicted_return*100:.1f}%，信心度 +20")
        elif predicted_return > 0.01:  # 預測上漲 1-3%
            confidence += 10
            logger.info(f"🤖 LSTM: {symbol} 預測上漲 {predicted_return*100:.1f}%，信心度 +10")
        elif predicted_return < -0.02:  # 預測下跌 > 2%
            confidence -= 15
            logger.warning(f"🤖 LSTM: {symbol} 預測下跌 {predicted_return*100:.1f}%，信心度 -15")
        
    except Exception as e:
        logger.debug(f"LSTM 預測失敗: {e}")
    
    return {'confidence': min(max(confidence, 0), 100), ...}
```

---

## 🎊 總結

### ✅ 完成的功能

1. ✅ **訓練迴圈**：500 Epochs，每 50 輪報告
2. ✅ **MSE 損失函數**：均方誤差作為痛苦指標
3. ✅ **Adam 優化器**：自適應學習率，比 SGD 聰明
4. ✅ **ORB 監控列表**：自動訓練 50 支股票
5. ✅ **Matplotlib 曲線圖**：視覺化展示痛苦減少過程
6. ✅ **激活函數**：Tanh + Sigmoid (LSTM 內部)
7. ✅ **完整文檔**：使用指南和技術說明
8. ✅ **一鍵啟動**：自動化腳本

### 🤖 技術亮點

- **深度學習**：3層 LSTM + BatchNormalization + Dropout
- **智能優化**：Adam 自適應學習率
- **完整流水線**：數據準備 → 訓練 → 評估 → 可視化
- **批量處理**：自動訓練所有 ORB 股票
- **視覺化**：損失曲線展示「機器的進化過程」

---

## 📞 開始訓練

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_lstm_training.sh
```

**現在您可以看到機器如何一步一步減少痛苦！** 📉🤖

預計訓練時間：**2.5 - 4 小時** (50 支股票)

**祝您訓練順利！** 🚀
