# 6種改進模型使用指南

## 🎯 快速開始

### 立即測試
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 quick_test_improved_models.py
```

**預期時間**: 5-10 分鐘（測試所有6種方法）

---

## 📋 6種模型方案詳解

### 方案1️⃣: Baseline（基準模型）

#### 適用情況
- ✅ 訓練良好的股票
- ✅ 作為對照組
- ✅ 快速測試

#### 架構
```
LSTM(64) → Dropout(0.2) 
→ LSTM(32) → Dropout(0.2) 
→ Dense(1)
```

#### 配置
```python
config = BaselineConfig()
model = build_baseline_model(config)
```

#### 參數
| 參數 | 值 | 說明 |
|------|-----|------|
| LSTM層數 | 2 | 64 → 32 |
| Dropout | 0.2 | 標準值 |
| 學習率 | 0.001 | 標準值 |
| L2正則化 | 0.0 | 無 |

#### 預期效果
- 快速收斂
- 適合數據質量好的股票
- 訓練時間最短

---

### 方案2️⃣: Regularized（正則化模型）

#### 適用情況
- ⚠️ 驗證曲線出現鋸齒狀震盪
- ⚠️ 訓練後期不穩定
- ⚠️ 驗證損失波動大

####核心改進
- ✅ L2正則化 (0.015)
- ✅ 更高Dropout (0.35)
- ✅ Recurrent Dropout (0.2)
- ✅ 添加Dense層

#### 架構
```
LSTM(64, L2=0.015, RecDrop=0.2) → Dropout(0.35)
→ LSTM(32, L2=0.015, RecDrop=0.2) → Dropout(0.35)
→ Dense(16, L2=0.015) → Dropout(0.2)
→ Dense(1)
```

#### 配置
```python
config = RegularizedConfig()
model = build_regularized_model(config)
```

#### 參數對比
| 參數 | Baseline | Regularized | 改進 |
|------|----------|-------------|------|
| Dropout | 0.2 | 0.35 | +75% |
| L2正則化 | 0.0 | 0.015 | 新增 |
| Recurrent Dropout | 0.0 | 0.2 | 新增 |
| 學習率 | 0.001 | 0.0008 | -20% |
| Early Stop Patience | 20 | 25 | +25% |

#### 預期效果
- 📉 驗證曲線更平滑（減少鋸齒）
- 📉 震盪幅度降低 60-70%
- 📈 訓練穩定性提升
- ⏱️ 訓練時間略增 (+10-15%)

---

### 方案3️⃣: Larger（大容量模型）

#### 適用情況
- ⚠️ 驗證損失在前10-20個epoch就平台
- ⚠️ 模型容量不足
- ⚠️ 無法學習複雜模式

#### 核心改進
- ✅ 3層LSTM (128→64→32)
- ✅ 更多參數學習複雜模式
- ✅ 降低學習率 (0.0005)
- ✅ 輕度L2正則化

#### 架構
```
LSTM(128, L2=0.005) → Dropout(0.2)
→ LSTM(64, L2=0.005) → Dropout(0.2)
→ LSTM(32, L2=0.005) → Dropout(0.2)
→ Dense(32) → Dropout(0.1)
→ Dense(1)
```

#### 配置
```python
config = LargerConfig()
model = build_larger_model(config)
```

#### 容量對比
| 指標 | Baseline | Larger | 增加 |
|------|----------|--------|------|
| LSTM層數 | 2 | 3 | +50% |
| 總LSTM單元 | 96 | 224 | +133% |
| Dense單元 | 0 | 32 | 新增 |
| 參數數量 | ~50K | ~150K | +200% |

#### 預期效果
- 📈 突破早期平台
- 📈 延長有效訓練期 (20→40 epochs)
- 📈 更好地學習複雜模式
- ⏱️ 訓練時間增加 (+30-40%)

---

### 方案4️⃣: Optimized（優化平衡模型）⭐ 推薦

#### 適用情況
- ✅ 中等難度股票
- ✅ 需要平衡性能和穩定性
- ✅ 不確定選哪個時的默認選擇

#### 核心改進
- ✅ 中等容量 (96→48)
- ✅ 適度正則化 (L2=0.008)
- ✅ 平衡的Dropout (0.25)
- ✅ Recurrent Dropout

#### 架構
```
LSTM(96, L2=0.008, RecDrop=0.25) → Dropout(0.25)
→ LSTM(48, L2=0.008, RecDrop=0.25) → Dropout(0.25)
→ Dense(24, L2=0.008) → Dropout(0.15)
→ Dense(1)
```

#### 配置
```python
config = OptimizedConfig()
model = build_optimized_model(config)
```

#### 折中設計
| 維度 | 值 | 說明 |
|------|-----|------|
| 模型容量 | 144 units | 介於Baseline和Larger之間 |
| 正則化強度 | 0.008 | 介於無和強正則化之間 |
| Dropout | 0.25 | 介於0.2和0.35之間 |
| 學習率 | 0.0008 | 折中值 |

#### 預期效果
- ✅ 穩定的訓練過程
- ✅ 良好的泛化性能
- ✅ 適用範圍廣（60-70%股票）
- ⏱️ 訓練時間適中

---

### 方案5️⃣: Augmented（數據擴增模型）

#### 適用情況
- ⚠️ 訓練樣本不足（<800樣本）
- ⚠️ 嚴重過擬合（訓練MAE<0.03, 驗證MAE>0.12）
- ⚠️ 訓練-驗證差距大（>0.06）

#### 核心改進
- ✅ 添加微小噪聲 (0.3%)
- ✅ 樣本數翻倍
- ✅ 使用Optimized架構
- ✅ 增大batch size (64)

#### 數據擴增策略
```python
# 原始樣本
X_original: (1000, 60, 9)

# 添加0.3%噪聲
noise = np.random.normal(0, 0.003, X.shape)
X_noisy = X_original + noise

# 合併
X_augmented: (2000, 60, 9)
```

#### 配置
```python
config = AugmentedConfig()
X_aug, y_aug = augment_data(X, y, noise_level=0.003)
model = build_augmented_model(config)
```

#### 數據變化
| 指標 | 原始 | 擴增後 | 變化 |
|------|------|--------|------|
| 樣本數 | 1000 | 2000 | 2x |
| Batch Size | 32 | 64 | 2x |
| 數據多樣性 | 低 | 高 | ✅ |

#### 預期效果
- 📉 顯著減少過擬合
- 📉 訓練-驗證差距縮小 (0.06→0.03)
- 📈 提升泛化能力 20-30%
- ⏱️ 訓練時間增加 (+40-50%)

---

### 方案6️⃣: Attention（注意力模型）✨ 進階

#### 適用情況
- 🔬 9個特徵之間有複雜交互關係
- 🔬 需要模型關注重要時間點
- 🔬 標準LSTM效果不理想
- 🔬 複雜的市場模式

#### 核心改進
- ✅ 多頭注意力機制 (3 heads)
- ✅ 自動學習特徵重要性
- ✅ 殘差連接
- ✅ Layer Normalization

#### 架構
```
Input(60, 9)
→ LSTM(96, return_sequences=True)
→ MultiHeadAttention(heads=3, key_dim=32)
→ LayerNormalization + Residual Connection
→ LSTM(48)
→ Dense(32) → Dense(1)
```

#### 配置
```python
config = AttentionConfig()
model = build_attention_model(config)
```

#### 注意力機制
```
特徵交互矩陣 (9x9):
         Close  MA5  MA20  MA60  RSI  MACD  Signal  Vol  PChg
Close    1.0   0.95  0.89  0.82  0.34  0.45   0.42  0.23  0.67
MA5      0.95  1.0   0.98  0.91  0.31  0.41   0.38  0.19  0.62
...
(注意力機制自動學習這些關係)
```

#### 特點對比
| 特性 | 標準LSTM | Attention |
|------|----------|-----------|
| 特徵交互 | 隱式 | 顯式學習 |
| 時間重要性 | 平等 | 自動加權 |
| 長期依賴 | 弱 | 強 |
| 可解釋性 | 低 | 中 |

#### 預期效果
- 📈 對複雜模式效果更好 (+15-25%)
- ⏱️ 需要更多訓練時間 (+50-60%)
- 📊 可視化注意力權重
- 🎯 泛化能力強

---

## 🔄 決策流程圖

```
開始
 │
 ├─ 訓練良好？(Val MAE<0.10, Gap<0.03)
 │   └─ YES → 保持Baseline ✅
 │   └─ NO → 繼續
 │
 ├─ 驗證曲線震盪？(Std>0.01)
 │   └─ YES → Regularized 📉
 │   └─ NO → 繼續
 │
 ├─ 驗證損失早期平台？(前20epoch改善<30%)
 │   └─ YES → Larger 📈
 │   └─ NO → 繼續
 │
 ├─ 嚴重過擬合？(Train<0.03, Val>0.12)
 │   └─ YES → Augmented 🔊
 │   └─ NO → 繼續
 │
 ├─ 標準方法都不理想？
 │   └─ YES → Attention ✨
 │   └─ NO → Optimized ⭐
```

---

## 💻 使用示例

### 示例1: 測試單個股票

```python
from improved_stock_training import comprehensive_test

# 載入數據
X = load_stock_features('2330')  # (1000, 60, 9)
y = load_stock_targets('2330')   # (1000,)

# 測試所有方法
results = comprehensive_test(
    stock_code='2330',
    X_data=X,
    y_data=y,
    test_all_methods=True,
    save_dir='./results_2330'
)

# 查看最佳方法
best = min(results.items(), key=lambda x: x[1]['val_mae'])
print(f"最佳方法: {best[0]}, MAE: {best[1]['val_mae']:.6f}")
```

### 示例2: 使用特定方法

```python
from improved_stock_training import build_optimized_model, OptimizedConfig

# 配置
config = OptimizedConfig()

# 構建模型
model = build_optimized_model(config)

# 訓練
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=config.max_epochs,
    batch_size=config.batch_size,
    callbacks=[early_stop, reduce_lr]
)
```

### 示例3: 自動選擇方法

```python
from improved_stock_training import ProblemClassifier

# 分析訓練曲線
problem_type = ProblemClassifier.classify(history.history)
recommended_method = ProblemClassifier.recommend_method(problem_type)

print(f"問題類型: {problem_type}")
print(f"推薦方法: {recommended_method}")
```

---

## 📊 預期改進效果

基於測試數據預期：

| 問題類型 | 當前 Val MAE | 改進後 MAE | 改善幅度 |
|---------|-------------|-----------|---------|
| 震盪問題 | 0.10-0.11 | 0.08-0.09 | 15-20% |
| 早期平台 | 0.11-0.13 | 0.09-0.10 | 15-25% |
| 嚴重過擬合 | 0.12-0.15 | 0.09-0.11 | 20-30% |
| 訓練不足 | 0.10-0.12 | 0.08-0.10 | 15-20% |

**訓練-驗證差距預期**:
- 當前: 0.03-0.05
- 目標: <0.03
- 最佳: <0.02

---

## 🎯 實際應用流程

### 階段1: 單股票驗證（1天）

```python
# 選擇3支代表性股票
test_stocks = ['3037', '2317', '2303']

for stock in test_stocks:
    X, y = load_stock_data(stock)
    results = comprehensive_test(
        stock_code=stock,
        X_data=X,
        y_data=y,
        test_all_methods=True
    )
```

### 階段2: 方法選擇（0.5天）

1. 分析測試結果
2. 為每種問題類型選擇最佳方法
3. 確定超參數

### 階段3: 批量應用（2-3天）

```python
# 自動分類和訓練
for stock in all_stocks:
    # 獲取歷史訓練曲線
    history = load_previous_training(stock)
    
    # 分類問題
    problem_type = ProblemClassifier.classify(history)
    
    # 選擇方法
    method = ProblemClassifier.recommend_method(problem_type)
    
    # 重新訓練
    train_with_method(stock, method)
```

### 階段4: 結果驗證（0.5天）

- 對比改進前後
- 生成詳細報告
- 微調參數

**總預估時間: 4-5 天**

---

## 📈 進階技巧

### 1. 集成學習

```python
# 訓練多個模型
models = [
    build_optimized_model(OptimizedConfig()),
    build_regularized_model(RegularizedConfig()),
    build_attention_model(AttentionConfig())
]

# 集成預測
predictions = [model.predict(X_test) for model in models]
final_pred = np.mean(predictions, axis=0)
```

### 2. 超參數搜索

```python
# 定義搜索空間
param_grid = {
    'lstm_units_1': [64, 96, 128],
    'lstm_units_2': [32, 48, 64],
    'dropout': [0.2, 0.25, 0.3],
    'learning_rate': [0.0005, 0.0008, 0.001]
}

# Grid Search（簡化版）
best_params = grid_search(X, y, param_grid)
```

---

## ❓ FAQ

**Q1: 為什麼有些股票就是訓練不好？**

A: 可能原因：
1. 股票本身波動性太高（難以預測）
2. 數據質量問題（異常值、缺失值）
3. 特徵不足以捕捉模式
4. 市場環境變化（訓練集和測試集分佈不同）

建議：先檢查數據質量，再嘗試更複雜的模型

**Q2: 訓練-驗證差距多少算正常？**

- <0.02: 優秀 ⭐⭐⭐
- 0.02-0.03: 良好 ⭐⭐
- 0.03-0.05: 可接受 ⭐
- >0.05: 需要改進 ⚠️

**Q3: 應該訓練多少個epoch？**

- 設置 `max_epochs=100-150`
- 使用 `Early Stopping` 自動停止
- `patience=20-30`
- 通常實際訓練 30-60 個epoch

**Q4: Attention模型一定更好嗎？**

不一定！
- ✅ 對於複雜模式可能更好
- ❌ 對於簡單模式可能過度複雜
- ⏱️ 需要更多數據和訓練時間
- 💡 建議先嘗試標準方法

**Q5: 如何判斷模型已經最優？**

指標：
1. 驗證損失不再下降
2. 訓練-驗證差距穩定且小
3. 多次運行結果一致
4. 測試集表現接近驗證集

---

## ✅ 檢查清單

### 訓練前
- [ ] 數據形狀正確 (samples, 60, 9)
- [ ] 已經標準化（RobustScaler）
- [ ] 無缺失值或異常值
- [ ] 訓練/驗證/測試分割合理
- [ ] 設置了Early Stopping
- [ ] 設置了學習率衰減
- [ ] 保存最佳模型權重

### 訓練後
- [ ] 學習曲線是否正常
- [ ] 訓練-驗證差距是否合理
- [ ] 驗證集表現是否穩定
- [ ] 測試集表現是否接近驗證集
- [ ] 預測結果是否合理

---

## 📁 輸出文件

```
./improved_results/
├── {stock_code}_comparison.csv    # 對比表格
├── {stock_code}_results.json      # 詳細結果
├── {stock_code}_Baseline_best.h5  # Baseline模型
├── {stock_code}_Regularized_best.h5
├── {stock_code}_Larger_best.h5
├── {stock_code}_Optimized_best.h5
├── {stock_code}_Augmented_best.h5
└── {stock_code}_Attention_best.h5
```

---

## 🚀 立即開始

```bash
# 快速測試
python3 quick_test_improved_models.py

# 實際應用
python3 -c "
from improved_stock_training import comprehensive_test
import numpy as np

# 載入數據
X = np.load('your_X_data.npy')
y = np.load('your_y_data.npy')

# 測試
results = comprehensive_test('YOUR_STOCK', X, y, test_all_methods=True)
"
```

**預祝訓練成功！** 🎉📈
