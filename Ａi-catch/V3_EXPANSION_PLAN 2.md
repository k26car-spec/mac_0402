# 🚀 現有專案擴展計劃

## 📁 擴展架構設計

### 專案結構（v2.0 + v3.0 並存）

```
/Users/Mac/Documents/ETF/AI/Ａi-catch/
│
├── 【v2.0 現有系統 - 保持運行】
│   ├── dashboard.py              ✅ Flask Dashboard (Port 8082)
│   ├── stock_monitor.py          ✅ v2.0 監控系統
│   ├── main_force_detector.py    ✅ v2.0 偵測器（9位專家）
│   ├── async_crawler.py          ✅ 數據爬蟲
│   ├── fubon_client.py           ✅ 富邦連接
│   ├── templates/                ✅ HTML 模板
│   ├── static/                   ✅ 靜態資源
│   └── config.yaml               ✅ 配置文件
│
├── 【v3.0 新增系統 - 逐步開發】
│   │
│   ├── backend-v3/                    🆕 FastAPI 後端
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               🆕 FastAPI 主程式 (Port 8000)
│   │   │   ├── config.py             🆕 配置管理
│   │   │   ├── database.py           🆕 PostgreSQL 連接
│   │   │   │
│   │   │   ├── api/                  🆕 REST API
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analysis.py       # 分析端點
│   │   │   │   ├── realtime.py       # WebSocket
│   │   │   │   ├── stocks.py         # 股票查詢
│   │   │   │   └── alerts.py         # 警報系統
│   │   │   │
│   │   │   ├── detector/             🆕 v3.0 偵測核心
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main_force_v3.py  # 15位專家系統
│   │   │   │   ├── chip_analyzer.py  # 籌碼分析
│   │   │   │   ├── session_analyzer.py # 時段分析
│   │   │   │   ├── consecutive_tracker.py # 連續追蹤
│   │   │   │   └── timeframe_analyzer.py  # 多週期分析
│   │   │   │
│   │   │   ├── ml/                   🆕 機器學習
│   │   │   │   ├── __init__.py
│   │   │   │   ├── lstm_model.py     # LSTM 預測
│   │   │   │   ├── pattern_recognition.py
│   │   │   │   └── models/           # 訓練好的模型
│   │   │   │
│   │   │   ├── data/                 🆕 數據層（可復用現有）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── connectors.py     # 整合現有 fubon_client
│   │   │   │   └── cache_manager.py  # Redis 快取
│   │   │   │
│   │   │   └── models/               🆕 數據模型
│   │   │       ├── __init__.py
│   │   │       ├── stock.py
│   │   │       └── analysis.py
│   │   │
│   │   ├── requirements-v3.txt       🆕 v3.0 依賴
│   │   ├── Dockerfile                🆕 Docker 配置
│   │   └── README-v3.md              🆕 v3.0 說明
│   │
│   ├── frontend-v3/                  🆕 Next.js 前端
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── page.tsx
│   │   │   │   ├── dashboard/
│   │   │   │   └── api/
│   │   │   │
│   │   │   ├── components/
│   │   │   │   ├── charts/
│   │   │   │   ├── analysis/
│   │   │   │   └── realtime/
│   │   │   │
│   │   │   ├── hooks/
│   │   │   └── lib/
│   │   │
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── next.config.js
│   │
│   ├── config-v3/                    🆕 v3.0 配置
│   │   ├── settings.yaml             # 系統設定
│   │   ├── alerts.yaml               # 警報規則
│   │   └── database.yaml             # 數據庫配置
│   │
│   └── docs-v3/                      🆕 v3.0 文檔
│       ├── API.md
│       ├── ARCHITECTURE.md
│       └── DEPLOYMENT.md
│
├── 【共享資源】
│   ├── data/                         ✅ 共享數據
│   │   ├── stock_list.csv
│   │   └── historical/
│   │
│   ├── logs/                         ✅ 共享日誌
│   │   ├── v2_monitor.log
│   │   └── v3_api.log
│   │
│   └── backups/                      ✅ 備份目錄
│       ├── backup_v2.0_...
│       └── backup_before_v3_...
│
├── docker-compose.yml                🆕 服務編排
├── .env.v3                           🆕 v3.0 環境變數
├── .gitignore                        ✅ 更新忽略規則
└── README.md                         ✅ 更新說明

```

---

## 🔄 並行運行策略

### 端口分配
```
v2.0 系統:
- Flask Dashboard: http://127.0.0.1:8082

v3.0 系統:
- FastAPI Backend: http://127.0.0.1:8000
- Next.js Frontend: http://127.0.0.1:3000

數據庫:
- PostgreSQL: 127.0.0.1:5432
- Redis: 127.0.0.1:6379
```

### 數據共享
```python
# v2.0 和 v3.0 可以共享：
✅ 富邦 SDK 連接（fubon_client.py）
✅ Yahoo Finance 連接
✅ 股票清單數據
✅ 歷史分析結果

# v3.0 獨有：
🆕 PostgreSQL 數據庫
🆕 Redis 快取
🆕 LSTM 模型
🆕 WebSocket 服務
```

---

## 🎯 開發流程

### Phase 1: 基礎設施（不影響 v2.0）
1. 創建 `backend-v3/` 目錄
2. 創建 `frontend-v3/` 目錄
3. 設置 PostgreSQL + Redis
4. 配置 Docker Compose

### Phase 2: v3.0 偵測器（可獨立測試）
1. 開發 15 位專家系統
2. 整合多週期分析
3. 單元測試
4. 與 v2.0 對比驗證

### Phase 3: API 與前端（平行開發）
1. FastAPI 端點開發
2. Next.js 組件開發
3. WebSocket 整合
4. LSTM 模型訓練

### Phase 4: 整合上線（逐步切換）
1. 雙系統並行運行
2. 逐步將流量導向 v3.0
3. 驗證穩定後關閉 v2.0

---

## 📝 Git 分支策略

### 分支架構
```
main (v2.0 穩定版)
  └── develop-v3 (v3.0 開發分支)
       ├── feature/backend-v3
       ├── feature/frontend-v3
       ├── feature/lstm-model
       └── feature/websocket
```

### 保護機制
```bash
# main 分支只有 v2.0 代碼
# 不會被 v3.0 影響

# develop-v3 分支包含所有 v3.0 代碼
# 測試穩定後才合併到 main
```

---

## 🔧 資源復用

### 可直接復用
```python
# v2.0 現有資源
✅ fubon_client.py       # 富邦連接
✅ stock_names.py        # 股票名稱
✅ async_crawler.py      # 爬蟲邏輯
✅ config.yaml           # 監控清單

# v3.0 引用方式
from ...fubon_client import FubonClient  # 相對導入
```

### 需要重構
```python
# v2.0 → v3.0 升級
❌ main_force_detector.py (9專家)
✅ main_force_v3.py (15專家)

❌ Flask dashboard.py
✅ FastAPI main.py + Next.js
```

---

## 💾 數據遷移計劃

### v2.0 數據（SQLite）
```sql
-- 保留現有 alerts.db
-- v2.0 繼續使用
```

### v3.0 數據（PostgreSQL）
```sql
-- 創建新數據庫
CREATE DATABASE stock_ai_v3;

-- 可選：遷移歷史數據
INSERT INTO mainforce_analysis (...)
SELECT ... FROM v2_alerts.db;
```

---

## ⚠️ 風險控制

### 回退機制
```bash
# 任何時候都可以回退
git checkout main  # 回到 v2.0
docker-compose down  # 關閉 v3.0
./restart_monitor.sh  # 重啟 v2.0
```

### 備份策略
```bash
# 每次重大更新前備份
cp -r . ../backups/backup_$(date +%Y%m%d_%H%M%S)
```

### 監控指標
```
- v2.0 運行狀態（現有）
- v3.0 API 健康度（新增）
- 資源使用率（CPU/記憶體）
- 錯誤率（日誌監控）
```

---

## 🚀 立即執行步驟

### Step 1: 創建 Git 分支（保護 v2.0）
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
git checkout -b develop-v3
```

### Step 2: 創建 v3.0 目錄結構
```bash
mkdir -p backend-v3/app/{api,detector,ml,data,models}
mkdir -p frontend-v3/src/{app,components,hooks,lib}
mkdir -p config-v3 docs-v3
```

### Step 3: 初始化 Python 環境
```bash
cd backend-v3
python3 -m venv venv
source venv/bin/activate
```

### Step 4: 安裝 v3.0 依賴
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary redis
pip freeze > requirements-v3.txt
```

### Step 5: 創建基礎文件
```bash
touch app/__init__.py
touch app/main.py
touch app/config.py
```

---

## 📊 開發時間表

### Week 1: 基礎設施
- Day 1-2: 目錄結構、Git、環境
- Day 3-4: PostgreSQL、Redis、Docker
- Day 5-7: FastAPI 基礎、健康檢查

### Week 2: v3.0 偵測器
- 在 `backend-v3/app/detector/` 開發
- 不影響 v2.0 運行
- 獨立測試

### Week 3+: 其他模組
- 按照 FULL_SYSTEM_ROADMAP.md 執行

---

## ✅ 成功指標

### Phase 1 完成
- [ ] v3.0 目錄創建完成
- [ ] Git 分支保護設置
- [ ] PostgreSQL + Redis 運行
- [ ] FastAPI "Hello World" 成功

### Phase 2 完成
- [ ] v3.0 偵測器開發完成
- [ ] 準確率 > v2.0
- [ ] 單元測試通過

### Phase 3 完成
- [ ] API 端點全部實作
- [ ] Next.js 前端完成
- [ ] WebSocket 正常運行

---

**準備好開始了嗎？** 🚀

建議立即執行：
1. Git 分支創建
2. 目錄結構搭建
3. 基礎環境設置

這些操作**完全不會影響 v2.0**！
