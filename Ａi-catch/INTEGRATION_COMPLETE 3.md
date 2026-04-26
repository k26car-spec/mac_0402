# ✅ 選股引擎已整合到啟動腳本

## 🎉 完成！

您的全自動選股決策引擎已成功整合到 `start_v3.sh` 啟動腳本中！

---

## 🚀 現在您可以這樣使用

### 最簡單的方式（推薦）⭐

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
```

**會發生什麼**:

1. 🔧 啟動後端 API (Port 8000)
2. 🎨 啟動前端服務 (Port 3000)
3. 🏦 啟動富邦 Bridge (Port 8003，如有)
4. 🎯 **詢問是否執行選股分析**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 全自動選股決策引擎
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

是否要執行選股分析？

  1) 是 - 立即執行完整選股流程 (2-3分鐘)
  2) 否 - 跳過，僅啟動服務

請選擇 [1/2]:
```

5. 選擇「1」→ 自動執行選股 → 生成報告
6. 選擇「2」→ 跳過選股 → 僅啟動服務

---

## 📊 選擇「1」後會自動完成

1. ✅ 抓取富邦券商數據（自動使用今天日期：2026-01-01）
2. ✅ 解析並提取330+筆買賣資訊
3. ✅ 識別買超股票
4. ✅ 執行多維度選股分析
5. ✅ 生成完整Excel報告

**執行時間**: 2-3 分鐘

**完成後顯示**:
```
✅ 選股分析完成！

📊 查看報告：
   open backend-v3/reports/fubon_broker_analysis.csv

📊 查看券商數據：
   open broker_data_extracted.csv
```

---

## 🎯 使用場景

### 場景1: 每日選股（最常用）

```bash
# 每天收盤後執行
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh

# 選擇「1」執行選股
# 等待2-3分鐘
# 查看報告
```

### 場景2: 僅啟動服務（開發用）

```bash
# 啟動服務
./start_v3.sh

# 選擇「2」跳過選股
# 使用前端或API
```

### 場景3: 稍後手動執行選股

```bash
# 先啟動服務（選擇「2」）
./start_v3.sh

# 稍後需要時手動執行
python3 run_full_analysis.py
```

---

## 📁 更新的文件

### 主要更新

| 文件 | 更新內容 |
|------|----------|
| `start_v3.sh` | ✅ 添加選股引擎互動選單 |
| `HOW_TO_USE.md` | ✅ 更新使用方式 |
| `START_SCRIPT_GUIDE.md` | ✅ 新增啟動腳本指南 |

### 新增的 API 端點

在 `start_v3.sh` 啟動後可用：

```
選股引擎 API (Port 8000)：
  • 分析單股:      http://localhost:8000/api/stock-selector/analyze/2330
  • 批量分析:      http://localhost:8000/api/stock-selector/analyze/batch
  • 推薦股票:      http://localhost:8000/api/stock-selector/recommendations
  • 富邦新店:      http://localhost:8000/api/stock-selector/broker-flow/fubon-xindan/top-stocks
```

---

## 🔧 技術細節

### 整合方式

在 `start_v3.sh` 中添加了：

1. **更新說明**（第7-13行）
   - 添加選股引擎功能說明

2. **API 端點顯示**（第191-197行）
   - 顯示選股引擎相關API

3. **互動式選單**（第211-250行）
   - 詢問用戶是否執行選股
   - 自動執行 `run_full_analysis.py`
   - 顯示結果和報告位置

### 執行流程

```
[啟動 start_v3.sh]
    ↓
[檢查依賴]
    ↓
[啟動後端 (8000)]
    ↓
[啟動前端 (3000)]
    ↓
[啟動富邦 Bridge (8003)]
    ↓
[等待服務就緒]
    ↓
[顯示服務資訊]
    ↓
[互動式選單] ← NEW!
    ├─ 選擇「1」→ [執行選股分析] → [顯示報告位置]
    └─ 選擇「2」→ [跳過]
    ↓
[監控日誌]
```

---

## 📖 相關文檔

| 文檔 | 說明 | 何時查看 |
|------|------|----------|
| **START_SCRIPT_GUIDE.md** | 啟動腳本詳細說明 | 了解啟動流程 |
| **HOW_TO_USE.md** | 使用總結 | 快速參考 |
| **QUICK_START_GUIDE.md** | 快速開始指南 | 第一次使用 |
| **README_STOCK_SELECTOR.md** | 系統入口 | 完整導航 |

---

## ✅ 測試清單

請確認以下功能正常：

- [ ] 執行 `./start_v3.sh`
- [ ] 看到選股引擎選單
- [ ] 選擇「1」執行選股
- [ ] 等待2-3分鐘
- [ ] 看到「選股分析完成」訊息
- [ ] 確認生成 `broker_data_extracted.csv`
- [ ] 確認生成 `backend-v3/reports/fubon_broker_analysis.csv`
- [ ] 用 Excel 開啟報告查看

---

## 🎉 立即試用

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
```

**選擇「1」體驗全自動選股！** 🚀

---

## 💡 使用建議

### 每日使用

```bash
# 設定每日自動執行（可選）
crontab -e

# 添加每日18:00執行
0 18 * * * cd /Users/Mac/Documents/ETF/AI/Ａi-catch && ./start_v3.sh
```

### 手動使用

```bash
# 每天收盤後手動執行
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
# 選擇「1」
```

---

**整合完成！現在您可以一鍵啟動所有服務並執行選股分析！** ✅

---

**更新日期**: 2026-01-01  
**版本**: v1.0.0  
**狀態**: ✅ 已整合並可用
