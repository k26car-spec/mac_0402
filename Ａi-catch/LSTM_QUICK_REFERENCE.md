# LSTM 訓練快速參考卡

## 🚀 一行命令啟動

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch && ./start_lstm_training.sh
```

---

## 📊 訓練配置

| 參數 | 值 | 說明 |
|------|-----|------|
| **Epochs** | 500 | 訓練輪數 |
| **優化器** | Adam | 自適應學習率 |
| **損失函數** | MSE | 均方誤差 |
| **批次大小** | 32 | Batch Size |
| **學習率** | 0.001 | Learning Rate |
| **LSTM架構** | 128→64→32 | 三層LSTM |
| **Dropout** | 0.3 | 防止過擬合 |
| **回看天數** | 60 | 使用過去60天 |
| **預測天數** | 5 | 預測未來5天 |
| **股票數量** | 50 | ORB監控列表 |

---

## ⏱️ 時間估算

- **每支股票**：3-5 分鐘
- **50 支股票**：2.5-4 小時
- **建議時間**：晚上執行，第二天查看結果

---

## 🎯 為什麼用 Adam？

Adam > SGD 的 5 大原因：

1. ⚡ **收斂更快**（需要更少 epochs）
2. 🎯 **自適應學習率**（每個參數獨立調整）
3. 🚀 **動量累積**（避免震盪）
4. 📊 **適合稀疏梯度**（金融數據特性）
5. 🎛️ **超參數不敏感**（默認值即可）

---

## 📉 MSE 損失函數

**公式**：$MSE = \frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2$

**解釋**：
- MSE 越小 = 預測越準 = 機器越開心 😊
- MSE 越大 = 預測越差 = 機器越痛苦 😫

**目標**：讓機器從痛苦（MSE=1.0）到開心（MSE=0.001）！

---

## 🧠 激活函數

LSTM 內部使用：
- **Tanh** (雙曲正切) - 單元狀態和隱藏狀態
- **Sigmoid** (σ) - 遺忘門、輸入門、輸出門

---

## 📁 輸出文件位置

```
/models/lstm_smart_entry/
├── 2330_model.h5         ← 台積電模型
├── 2317_model.h5         ← 鴻海模型
├── 2454_model.h5         ← 聯發科模型
└── ...                   ← 其他 47 支

/training_results/
├── training_curves_*.png      ← 損失曲線圖
├── overall_statistics_*.png   ← 統計圖表
└── ...
```

---

## 📊 如何解讀損失曲線

### 理想狀態 ✅
```
Loss
 │  ╲
 │   ╲___
 │       ╲___
 │           ━━━━━  ← 平穩收斂
 └────────────────> Epochs
```

### 過擬合 ⚠️
```
Loss
 │  ╲     訓練 ↘
 │   ╲___
 │       ━━━━
 │    驗證 ↗
 └────────────────> Epochs
```

### 欠擬合 ⚠️
```
Loss
 │  ━━━━━━━━━━  ← 停滯不動
 │
 │
 └────────────────> Epochs
```

---

## 🔧 常見問題

### Q: TensorFlow 安裝失敗？
```bash
# macOS (Apple Silicon)
pip install tensorflow-macos tensorflow-metal

# 其他平台
pip install tensorflow
```

### Q: 記憶體不足？
修改 `TrainingConfig.BATCH_SIZE = 16`（改小批次）

### Q: 訓練太慢？
減少 epochs 或股票數量測試

---

## 📚 詳細文檔

- **完整指南**：`LSTM_TRAINING_GUIDE.md`
- **完成報告**：`LSTM_TRAINING_COMPLETE.md`
- **訓練腳本**：`train_lstm_smart_entry_v2.py`

---

## ✅ 檢查清單

訓練前：
- [ ] Python 3.x 已安裝
- [ ] TensorFlow 已安裝
- [ ] ORB 監控列表存在
- [ ] 有足夠的磁碟空間（至少 1GB）
- [ ] 網路連線正常（下載數據）

訓練完成後：
- [ ] 檢查模型數量（應有 50 個 .h5 文件）
- [ ] 查看損失曲線圖
- [ ] 閱讀訓練報告 JSON
- [ ] 準備整合到 smart_entry_v2

---

**🎊 開始訓練，看機器如何一步步減少痛苦！** 📉🤖
