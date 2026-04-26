# LSTM v2.1 改進版訓練系統使用指南

## 🆕 改進項目總覽

### 版本對比

| 改進項目 | v2.0 原版 | v2.1 改進版 | 改進效果 |
|---------|----------|------------|---------|
| **LSTM 層數** | 3層 (128→64→32) | 2層 (64→32) | ✅ 簡化架構，減少過擬合風險 |
| **L2 正則化** | ❌ 無 | ✅ 0.01 | ✅ 權重懲罰，防止過擬合 |
| **Recurrent Dropout** | ❌ 無 | ✅ 0.2 | ✅ LSTM 內部 Dropout |
| **數據預處理** | StandardScaler | RobustScaler | ✅ 對異常值更穩健 |
| **數據增強** | ❌ 無 | ✅ 噪聲增強 | ✅ 增加數據多樣性 |
| **Early Stopping** | 20 patience | 15 patience | ✅ 更早停止，節省時間 |
| **Learning Rate 調整** | 10 patience | 5 patience | ✅ 更積極降低學習率 |
| **訓練 Epochs** | 500 (固定) | 100 (最大) | ✅ Early Stop 提前停止 |
| **中間 Dense 層** | ❌ 無 | ✅ 16 units | ✅ 額外特徵提取 |

---

## 🎯 7 大改進詳解

### 1. 簡化模型架構

#### 原版（3層 LSTM）
```python
LSTM(128) → LSTM(64) → LSTM(32) → Dense(1)
```
**問題**：過深容易過擬合，訓練慢

#### 改進版（2層 LSTM + Dense）
```python
LSTM(64) → LSTM(32) → Dense(16) → Dense(1)
```
**優勢**：
- ✅ 減少參數數量
- ✅ 降低過擬合風險
- ✅ 訓練速度更快
- ✅ 泛化能力更好

---

### 2. L2 正則化

#### 程式碼
```python
LSTM(64, kernel_regularizer=l2(0.01))
```

#### 原理
L2 正則化在損失函數中添加權重的平方和：

$$Loss_{total} = Loss_{MSE} + \lambda \sum w_i^2$$

其中 $\lambda = 0.01$

#### 效果
- ✅ 懲罰過大的權重
- ✅ 鼓勵權重分佈更均勻
- ✅ 防止模型過度擬合訓練數據

---

### 3. Recurrent Dropout

#### 程式碼
```python
LSTM(64, recurrent_dropout=0.2)
```

#### 與普通 Dropout 的區別

| 類型 | 作用位置 | 效果 |
|------|---------|------|
| **Dropout** | LSTM 層之間 | 防止層間過擬合 |
| **Recurrent Dropout** | LSTM 內部循環連接 | 防止時間步之間過擬合 |

#### 原理
在 LSTM 的循環連接中隨機 "關閉" 20% 的神經元：

```
t-1 → [×] → t → [×] → t+1
      80%       80%
```

---

### 4. RobustScaler vs StandardScaler

#### StandardScaler（原版）
```python
# 對均值和標準差敏感
X_scaled = (X - mean) / std
```
**問題**：極端值會影響 mean 和 std

#### RobustScaler（改進版）
```python
# 使用中位數和四分位距
X_scaled = (X - median) / IQR
```
**優勢**：
- ✅ 對異常值不敏感
- ✅ 適合金融數據（常有極端值）
- ✅ 更穩健的標準化

**範例**：
```
數據: [1, 2, 3, 4, 100]

StandardScaler:
  mean = 22, std = 43.5
  → 前4個值被壓得很小

RobustScaler:
  median = 3, IQR = 2.5
  → 前4個值正常分佈，100被正確識別為異常
```

---

### 5. Early Stopping

#### 程式碼
```python
EarlyStopping(
    monitor='val_loss',
    patience=15,           # 15 epoch 沒改善就停止
    restore_best_weights=True  # 恢復最佳權重
)
```

#### 工作原理
```
Epoch  Val_Loss  改善?  Patience計數
1      0.0123    -      0
2      0.0115    ✅     0 (重置)
3      0.0118    ❌     1
4      0.0120    ❌     2
...
18     0.0119    ❌     15
→ 停止訓練，恢復到 Epoch 2 的權重
```

#### 優勢
- ✅ 自動找到最佳停止點
- ✅ 節省訓練時間（不必跑完 100 epochs）
- ✅ 防止過擬合（不會訓練過頭）

---

### 6. Learning Rate 調整

#### 程式碼
```python
ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.5,      # 學習率減半
    patience=5,      # 5 epoch 沒改善就降低
    min_lr=1e-6      # 最小學習率
)
```

#### 學習率調整策略
```
Epoch  Val_Loss  LR        動作
1-5    下降      0.001     正常訓練
6-10   停滯      0.001     觀察中
11     停滯      0.0005    ✅ 降低學習率
12-16  下降      0.0005    繼續訓練
17-21  停滯      0.0005    再次觀察
22     停滯      0.00025   ✅ 再次降低
```

#### 為什麼有效？

**大學習率 (0.001)**：
- 優點：快速收斂
- 缺點：可能跳過最優點

**小學習率 (0.0001)**：
- 優點：精細調整
- 缺點：收斂慢

**動態調整**：
- ✅ 初期快速接近最優
- ✅ 後期精細優化
- ✅ 兩全其美

---

### 7. 數據增強

#### 程式碼
```python
def add_noise(data, noise_level=0.01):
    noise = np.random.normal(0, noise_level, data.shape)
    return data + noise
```

#### 為什麼添加噪聲？

**原始數據**：
```
[1.00, 2.00, 3.00, 4.00, 5.00]
```

**添加噪聲後**：
```
[1.01, 1.98, 3.02, 3.99, 5.01]
```

#### 效果
- ✅ 增加數據多樣性
- ✅ 防止記憶訓練數據
- ✅ 提升模型泛化能力
- ✅ 類似於正則化效果

#### 注意
- 只對訓練集添加噪聲
- 測試集保持原樣
- 噪聲水平要適中（0.01 = 1%）

---

## 🚀 使用方法

### 快速開始

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 train_lstm_improved_v2.1.py
```

### 預期輸出

```
======================================================================
🤖 LSTM Smart Entry v2.1 - 改進版訓練系統
======================================================================

🆕 改進項目:
  1. ✅ 簡化架構: 2層 LSTM (64→32)
  2. ✅ L2 正則化: 防止過擬合
  3. ✅ Recurrent Dropout: LSTM 內部 Dropout
  4. ✅ Early Stopping: 15 epoch patience
  5. ✅ Learning Rate 調整: 自動降低學習率
  6. ✅ RobustScaler: 對異常值更穩健
  7. ✅ 數據增強: 添加微小噪聲

============================================================
🎯 開始訓練: 2330
============================================================
  📊 2330: 獲取 365 天數據
  🔊 數據增強: 添加 0.01 水平噪聲
  訓練集: 192 樣本
  測試集: 48 樣本
  特徵維度: 9

🏗️ 模型架構:
  • LSTM 層: 64 → 32
  • Dense 層: 16
  • Dropout: 0.3
  • Recurrent Dropout: 0.2
  • L2 正則化: 0.01

⚙️ 訓練策略:
  • Early Stopping: patience=15
  • Learning Rate 調整: patience=5, factor=0.5
  • 最大 Epochs: 100

🚀 開始訓練...
📝 優化器: Adam (自適應學習率)
📉 損失函數: MSE (均方誤差)

📊 Epoch  10/100 | Loss: 0.002345 | Val_Loss: 0.003456 | MAE: 0.034567 | Val_MAE: 0.045678
📊 Epoch  20/100 | Loss: 0.001234 | Val_Loss: 0.002345 | MAE: 0.023456 | Val_MAE: 0.034567
...
Epoch 35: early stopping

✅ 訓練完成！
  實際訓練 Epochs: 35  # 提前停止！
  訓練集 Loss: 0.000987 | MAE: 0.019876
  測試集 Loss: 0.001234 | MAE: 0.023456
  💾 最終模型: /models/lstm_smart_entry_v2.1/2330_final.h5
  💾 最佳模型: /models/lstm_smart_entry_v2.1/best_2330.h5
```

---

## 📊 改進效果對比

### 訓練時間

| 版本 | 平均 Epochs | 單股訓練時間 | 50 支總時間 |
|------|-----------|------------|-----------|
| v2.0 | 500 (固定) | 5-7 分鐘 | 4-6 小時 |
| v2.1 | 30-40 (動態) | 1-2 分鐘 | **0.8-1.7 小時** ⚡ |

**時間節省：70-75%** 

### 模型性能

預期改進：
- ✅ 測試集損失降低 15-25%
- ✅ 過擬合現象減少
- ✅ 模型更穩定
-✅ 泛化能力更強

---

## 📁 輸出文件

### 模型文件（每支股票 2 個）

```
/models/lstm_smart_entry_v2.1/
├── 2330_final.h5      # 最終模型
├── best_2330.h5       # 訓練過程中的最佳模型
├── 2317_final.h5
├── best_2317.h5
└── ...
```

**使用建議**：
- `best_*.h5` - 用於生產環境（性能最優）
- `*_final.h5` - 用於分析（看最終狀態）

### 訓練報告

```json
{
  "version": "v2.1",
  "improvements": [
    "簡化架構(2層LSTM)",
    "L2正則化",
    "Recurrent Dropout",
    "Early Stopping",
    "Learning Rate 調整",
    "RobustScaler",
    "數據增強"
  ],
  "config": {
    "lstm_units": [64, 32],
    "l2_reg": 0.01,
    "early_stop_patience": 15,
    ...
  }
}
```

---

## 🎨 可視化輸出

### 1. 訓練曲線圖
- 藍線：訓練損失
- 紅虛線：驗證損失
- 綠星：最佳點（Early Stopping 停止的位置）

### 2. MAE 曲線圖
- 綠線：訓練 MAE
- 紫虛線：驗證 MAE
- 展示平均絕對誤差變化

---

## 🔧 進階調整

### 如果模型仍然過擬合

增加正則化：
```python
L2_REG = 0.02  # 從 0.01 增加到 0.02
DROPOUT_RATE = 0.4  # 從 0.3 增加到 0.4
```

### 如果模型欠擬合

增加模型容量：
```python
LSTM_UNITS = [128, 64]  # 從 [64, 32] 增加
DENSE_UNITS = 32  # 從 16 增加
```

### 如果訓練太慢

減少數據或 epochs：
```python
MAX_EPOCHS = 50  # 從 100 減少
```

---

## ✅ 檢查清單

改進版特有檢查：
- [ ] TensorFlow 已安裝（包含 regularizers）
- [ ] sklearn 已安裝（RobustScaler）
- [ ] 磁碟空間充足（每支股票 2 個模型文件）
- [ ] 了解 Early Stopping 機制
- [ ] 知道如何選擇 best 或 final 模型

---

## 📚 技術參考

### L2 正則化公式
$$L = L_{MSE} + \lambda \sum_{i=1}^{n} w_i^2$$

### Learning Rate 調整公式
$$lr_{new} = lr_{old} \times factor$$

### RobustScaler 公式
$$X_{scaled} = \frac{X - median(X)}{IQR(X)}$$

其中 $IQR = Q_3 - Q_1$ (四分位距)

---

## 🎊 總結

**v2.1 改進版的 3 大優勢：**

1. **更快** ⚡
   - Early Stopping 提前停止
   - 訓練時間減少 70%

2. **更穩** 🛡️
   - L2 正則化 + Recurrent Dropout
   - RobustScaler 對異常值穩健
   - 過擬合風險大幅降低

3. **更優** 🎯
   - 簡化架構提升泛化能力
   - Learning Rate 調整優化收斂
   - 數據增強增加多樣性

**現在就開始使用改進版！** 🚀
