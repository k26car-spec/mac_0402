# 🚀 AI 股票智能分析系統 - 快速啟動指南

## 📋 服務清單

系統現已整合 **6 個核心服務**，一鍵啟動所有功能：

| # | 服務名稱 | Port | 說明 | 訪問URL |
|---|---------|------|------|---------|
| 1 | 後端 API v3 | 8000 | 核心 API 服務 + 富邦 SDK | http://localhost:8000/api/docs |
| 2 | 前端 UI v3 | 3000 | Next.js 主控台 | http://localhost:3000 |
| 3 | Sniper 戰情室 | 3000 | 當沖狙擊系統 | http://localhost:3000/dashboard/sniper |
| 4 | ORB 監控 | 5173 | 當沖 ORB 系統 | http://localhost:5173 |
| 5 | 清單管理工具 | 8888 | 監控清單管理 | http://localhost:8888/orb_watchlist.html |
| 6 | **潛力股監控** | **8501** | **Streamlit 儀表板** | **http://localhost:8501** |

## 🎯 一鍵啟動

### 方法一：完整啟動（推薦）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./stop_all.sh      # 先停止所有服務
./start_backend.sh # 啟動所有服務（包含 Streamlit）
```

### 方法二：僅啟動 Streamlit 監控

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_stock_monitor.sh
```

## 🛑 停止所有服務

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./stop_all.sh
```

停止服務包括：
- ✅ 後端 API (Port 8000)
- ✅ 前端 UI (Port 3000)
- ✅ ORB 系統 (Port 5173)
- ✅ **Streamlit 儀表板 (Port 8501)**
- ✅ 管理頁面 (Port 8888)

## 📊 Streamlit 潛力股監控儀表板

### 核心功能
- **📈 即時行情**: 整合富邦 API 獲取即時報價
- **📊 成長率分析**: 週/月/雙月成長率自動計算
- **🎯 型態識別**: 多頭/突破/弱勢自動判斷
- **⭐ 優先度評分**: 智能評分系統（99分/10分）
- **📉 視覺化圖表**: 多維度數據分析

### 快速訪問
啟動後，直接訪問：
```
http://localhost:8501
```

### 主要特色
1. **雙模式顯示**: 簡潔 / 完整模式隨時切換
2. **智能篩選**: 按成長率、優先度快速篩選
3. **自訂清單**: 隨時新增/移除監控股票
4. **自動更新**: 每 60 秒自動刷新數據
5. **批次查詢**: 一次獲取多支股票數據

## 📝 預設監控清單

Streamlit 預設監控 7 支潛力股：
- 3380 明泰
- 3413 京鼎
- 3450 聯鈞
- 3466 德晉
- 3518 柏騰
- 3563 牧德
- 3581 博磊

可隨時透過側邊欄新增更多股票！

## 🔧 服務管理

### 查看服務狀態
```bash
# 查看後端日誌
tail -f /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/backend.log

# 查看前端日誌
tail -f /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/frontend.log

# 查看 Streamlit 日誌
tail -f /Users/Mac/Documents/ETF/AI/Ａi-catch/logs/streamlit.log
```

### 檢查端口占用
```bash
# 查看所有服務端口
lsof -ti :8000,3000,5173,8888,8501
```

### 重啟單一服務

**重啟 Streamlit 儀表板：**
```bash
# 停止
lsof -ti :8501 | xargs kill -9

# 啟動
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
streamlit run streamlit_stock_monitor.py --server.port 8501
```

## 📖 完整文檔

- **Streamlit 使用指南**: `STREAMLIT_MONITOR_GUIDE.md`
- **系統啟動腳本**: `start_backend.sh`
- **停止所有服務**: `stop_all.sh`
- **Streamlit 主程式**: `streamlit_stock_monitor.py`

## ⚡ 快速操作流程

### 每日操作流程

```bash
# 1. 啟動系統
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_backend.sh

# 2. 訪問服務
# - Streamlit 監控: http://localhost:8501
# - Sniper 戰情室: http://localhost:3000/dashboard/sniper
# - 系統首頁: http://localhost:3000

# 3. 收盤後停止
./stop_all.sh
```

### Streamlit 操作流程

1. **訪問儀表板**: http://localhost:8501
2. **查看統計卡片**: 監控股票數、高優先度數量、多頭型態數量
3. **篩選股票**: 側邊欄調整成長率、優先度條件
4. **新增股票**: 側邊欄輸入股票代號
5. **查看圖表**: 切換 Tab 查看不同維度分析
6. **調整顯示**: 切換簡潔/完整模式

## 🎨 自訂配置

### 修改預設監控清單
編輯 `streamlit_stock_monitor.py` 第 139 行：
```python
default_symbols = ["3380", "3413", "3450", "3466", "3518", "3563", "3581"]
```

### 修改啟動端口
編輯 `start_backend.sh` 第 82 行：
```bash
nohup streamlit run streamlit_stock_monitor.py --server.port 8501 ...
```

## ⚠️ 常見問題

### Q: Streamlit 無法啟動？
**A**: 檢查：
1. Streamlit 是否已安裝：`pip3 install streamlit`
2. Port 8501 是否被占用：`lsof -ti :8501`
3. 查看日誌：`tail -f logs/streamlit.log`

### Q: 數據無法載入？
**A**: 確認：
1. 後端 API 是否運行：`curl http://localhost:8000/health`
2. 富邦 API 憑證是否正確
3. 網路連線是否正常

### Q: 如何單獨啟動 Streamlit？
**A**: 
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
streamlit run streamlit_stock_monitor.py --server.port 8501
```

## 🔐 安全提示

- 富邦 API 憑證存放在 `.env` 文件
- 請勿將 `.env` 提交到版本控制
- 建議定期更換憑證密碼
- 所有數據處理在本地進行

## 📊 效能建議

- **監控股票**: 建議不超過 30 支
- **自動更新**: 建議 60 秒以上間隔
- **快取時間**: 保持預設值（60秒/5分鐘）

---

**版本**: v3.0 + Streamlit Integration  
**最後更新**: 2026-02-13  
**下次更新**: 根據使用反饋持續優化

🎉 **享受您的智能交易體驗！**
