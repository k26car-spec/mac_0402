# 🎯 快速參考卡

## 🚀 一鍵啟動（最簡單）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch && ./start_v3.sh
```

然後訪問 → http://localhost:3000/dashboard/stock-selector

---

## 📊 主要功能

| 功能 | 命令 |
|------|------|
| **一鍵啟動** | `./start_v3.sh` |
| **僅執行選股** | `python3 run_full_analysis.py` |
| **查看報告** | `open backend-v3/reports/fubon_broker_analysis.csv` |
| **查看券商數據** | `open broker_data_extracted.csv` |

---

## 🌐 服務地址

| 服務 | 地址 |
|------|------|
| 前端首頁 | http://localhost:3000 |
| API 文件 | http://localhost:8000/api/docs |
| 健康檢查 | http://localhost:8000/health |
| 選股 API | http://localhost:8000/api/stock-selector/health |

---

## 📖 文檔導航

| 文檔 | 用途 |
|------|------|
| **START_SCRIPT_GUIDE.md** | 啟動腳本說明 |
| **HOW_TO_USE.md** | 使用總結 |
| **QUICK_START_GUIDE.md** | 快速指南 |
| **README_STOCK_SELECTOR.md** | 系統入口 |

---

## ⚡ 快速命令

```bash
# 啟動所有服務
./start_v3.sh

# 僅執行選股
python3 run_full_analysis.py

# 查看報告
open backend-v3/reports/fubon_broker_analysis.csv

# 停止服務
Ctrl+C
```

---

**立即開始**: `cd /Users/Mac/Documents/ETF/AI/Ａi-catch && ./start_v3.sh` 🚀
