# 📦 系統備份說明

## 🗂️ 備份資訊

**備份時間**: 2025-12-15 11:15:47  
**備份目錄**: `backups/backup_20251215_111547/`  
**備份原因**: 準備進行 AI 偵測演算法改進前的完整備份  

---

## 📋 備份內容清單

### ✅ 核心程式檔案 (16 個)
- main_force_detector.py - AI 主力偵測演算法
- stock_monitor.py - 主監控系統
- async_crawler.py - 異步數據爬蟲
- notifier.py - 多管道通知系統
- dashboard.py - Web 監控平台
- 及其他輔助工具

### ✅ 配置檔案 (3 個)
- config.yaml - 系統主配置
- requirements.txt - Python 依賴
- .env - 環境變數

### ✅ 腳本檔案 (8 個)
- start_monitor.sh, stop_monitor.sh
- start_dashboard.sh, stop_dashboard.sh
- restart_dashboard.sh, setup_dashboard.sh

### ✅ 資料目錄
- templates/ - HTML 模板
- static/ - 靜態資源
- data/ - 資料庫
- logs/ - 日誌檔案

---

## 🔄 如何還原

### 完整還原
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
cp -r backups/backup_20251215_111547/* .
```

### 還原特定檔案
```bash
cp backups/backup_20251215_111547/main_force_detector.py .
```

---

**備份狀態**: ✅ 成功
