# 🚀 v3.0 快速啟動指令卡

> 將此文件保存為書籤，隨時可用！

---

## ⚡ 一鍵啟動

```bash
# 啟動後端 API
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3 && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 啟動前端 (另開終端)
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/frontend-v3 && npm run dev
```

**訪問服務**:
- 📚 API 文檔: http://localhost:8000/docs
- 🖥️ 前端介面: http://localhost:3001
- 💚 健康檢查: http://localhost:8000/health

---

## 🤖 AI 交易輔助功能

### 每日掃描強勢股
```bash
# 掃描漲幅 5-10%、量比 >1.5 的股票
curl -X POST "http://localhost:8000/api/watchlist/scan-strong-stocks?min_gain_pct=5&max_gain_pct=10&min_volume_ratio=1.5&limit=10"

# 取得今日觀察名單
curl http://localhost:8000/api/watchlist/today
```

### 進場前多因子檢查
```bash
# 快速檢查某股票是否可進場
curl http://localhost:8000/api/entry-check/quick/2330

# 完整檢查（指定進場價）
curl "http://localhost:8000/api/entry-check/comprehensive/8039?entry_price=85&signal_source=manual"

# 批量檢查多檔股票
curl "http://localhost:8000/api/entry-check/batch?symbols=2330,2454,3006"
```

### 交易檢討與學習
```bash
# 檢討所有停損交易
curl -X POST http://localhost:8000/api/trade-review/review-all-stopped

# 查看學到的教訓
curl http://localhost:8000/api/trade-review/lessons

# 查看問題統計
curl http://localhost:8000/api/trade-review/problem-statistics
```

### AI 績效追蹤
```bash
# 績效統計
curl http://localhost:8000/api/portfolio/summary

# 各訊號來源準確性
curl http://localhost:8000/api/portfolio/accuracy?days=30
```

---

## 📊 常用 API 端點

### 智慧選股
| 端點 | 描述 |
|------|------|
| `/api/smart-entry/score/{symbol}` | 計算智慧進場評分 |
| `/api/stock-analysis/comprehensive/{symbol}` | 完整股票分析 |
| `/api/support-resistance/analyze/{symbol}` | 支撐阻力分析 |

### 觀察名單
| 端點 | 方法 | 描述 |
|------|------|------|
| `/api/watchlist/scan-strong-stocks` | POST | 掃描強勢股 |
| `/api/watchlist/today` | GET | 今日觀察名單 |
| `/api/watchlist/candidates` | GET | 可進場候選股 |
| `/api/watchlist/add-manual` | POST | 手動加入觀察 |

### 進場檢查
| 端點 | 方法 | 描述 |
|------|------|------|
| `/api/entry-check/quick/{symbol}` | GET | 快速多因子檢查 |
| `/api/entry-check/comprehensive/{symbol}` | GET | 完整多因子檢查 |
| `/api/entry-check/batch` | GET | 批量檢查 |

### 交易檢討
| 端點 | 方法 | 描述 |
|------|------|------|
| `/api/trade-review/review-all-stopped` | POST | 檢討所有停損交易 |
| `/api/trade-review/lessons` | GET | 查看學習到的教訓 |
| `/api/trade-review/problem-statistics` | GET | 問題統計 |
| `/api/trade-review/should-trade/{symbol}` | GET | 根據教訓判斷是否交易 |

---

## 🔧 手動啟動（分步）

```bash
# 1. 進入 backend-v3
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3

# 2. 啟動虛擬環境
source venv/bin/activate

# 3. 啟動服務
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 測試命令

### API 測試
```bash
# 健康檢查
curl http://localhost:8000/health | python3 -m json.tool

# 根端點
curl http://localhost:8000 | python3 -m json.tool
```

### 瀏覽器測試
```bash
# 打開 API 文檔
open http://localhost:8000/docs

# 打開前端
open http://localhost:3001
```

---

## 🛑 停止服務

### 方法 1: 終端中
```
按 Ctrl + C
```

### 方法 2: 終止進程
```bash
# 查找進程
ps aux | grep uvicorn

# 終止進程
kill <PID>
```

---

## 🔍 狀態檢查

```bash
# 檢查服務是否運行
ps aux | grep uvicorn

# 檢查端口占用
lsof -i :8000

# 檢查前端
lsof -i :3001
```

---

## 📦 依賴安裝

### 完整安裝
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
source venv/bin/activate
pip install -r requirements-v3.txt
```

---

## 🐛 問題排查

### 問題 1: 端口被占用
```bash
# 查看占用端口的進程
lsof -i :8000

# 終止進程
kill -9 <PID>
```

### 問題 2: 找不到模塊
```bash
# 確認虛擬環境已啟動
source backend-v3/venv/bin/activate

# 重新安裝依賴
pip install -r requirements-v3.txt
```

---

## 📚 相關文檔

- `HOW_TO_START_V3.md` - 詳細啟動指南
- `V3_TEST_REPORT.md` - 測試報告
- `FULL_SYSTEM_ROADMAP.md` - 完整路線圖

---

## 🎯 每日工作流程

### 開盤前 (08:30)
1. 啟動後端和前端
2. 執行 `/api/watchlist/scan-strong-stocks` 掃描強勢股

### 盤中
1. 查看 `/api/watchlist/candidates` 取得可進場候選
2. 對有興趣的股票執行 `/api/entry-check/quick/{symbol}`
3. 只有通過 5/6 檢查才考慮進場

### 收盤後
1. 執行 `/api/trade-review/review-all-stopped` 檢討停損交易
2. 查看 `/api/trade-review/problem-statistics` 分析問題

---

**最後更新**: 2026-01-05  
**狀態**: ✅ AI 功能就緒  
**版本**: v3.1.0

