# Backend v3.0 使用說明

## 🚀 快速開始

### 1. 創建虛擬環境
```bash
cd backend-v3
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows
```

### 2. 安裝依賴
```bash
pip install -r requirements-v3.txt
```

### 3. 設置環境變數
```bash
cp ../.env.example .env
# 編輯 .env 配置數據庫等資訊
```

### 4. 啟動開發服務器
```bash
cd app
python main.py

# 或使用 uvicorn 直接啟動
uvicorn app.main:app --reload --port 8000
```

### 5. 訪問 API 文檔
```
http://127.0.0.1:8000/api/docs
```

---

## 📁 目錄結構

```
backend-v3/
├── app/
│   ├── main.py              # FastAPI 主程式 ✅
│   ├── config.py            # 配置管理（待開發）
│   ├── database.py          # 數據庫連接（待開發）
│   │
│   ├── api/                 # API 路由
│   │   ├── analysis.py      # 分析端點（待開發）
│   │   ├── realtime.py      # WebSocket（待開發）
│   │   ├── stocks.py        # 股票查詢（待開發）
│   │   └── alerts.py        # 警報系統（待開發）
│   │
│   ├── detector/            # v3.0 偵測核心
│   │   ├── main_force_v3.py # 15位專家（待開發）
│   │   ├── chip_analyzer.py # 籌碼分析（待開發）
│   │   └── ...
│   │
│   ├── ml/                  # 機器學習
│   │   ├── lstm_model.py    # LSTM（待開發）
│   │   └── ...
│   │
│   └── models/              # 數據模型
│
├── venv/                    # 虛擬環境
├── requirements-v3.txt      # 依賴清單 ✅
└── README-v3.md             # 本文件 ✅
```

---

## 🔗 與 v2.0 的關係

### 共享資源
```python
# 可以導入 v2.0 的模組
import sys
sys.path.append('..')  # 添加父目錄到路徑

from fubon_client import FubonClient  # 復用富邦連接
from stock_names import get_stock_name  # 復用股票名稱
```

### 獨立運行
- v2.0: Flask @ Port 8082
- v3.0: FastAPI @ Port 8000
- 兩者可同時運行，互不干擾

---

## 📊 API 端點（規劃）

### 基礎
- `GET /` - 根端點 ✅
- `GET /health` - 健康檢查 ✅

### 分析
- `POST /api/analysis/{symbol}` - 主力分析
- `GET /api/analysis/history/{symbol}` - 歷史記錄

### 即時數據
- `WS /api/realtime/{symbol}` - WebSocket 價格推送
- `WS /api/alerts/{symbol}` - WebSocket 警報推送

### 股票
- `GET /api/stocks/search?q={query}` - 搜尋股票
- `GET /api/stocks/{symbol}/info` - 股票資訊

### 警報
- `GET /api/alerts` - 獲取警報清單
- `POST /api/alerts/config` - 配置警報規則

---

## 🧪 測試

```bash
# 單元測試
pytest

# 測試覆蓋率
pytest --cov=app

# 測試 WebSocket
wscat -c ws://127.0.0.1:8000/ws/test
```

---

## 📚 開發指南

### 添加新 API 端點
1. 在 `app/api/` 創建新文件
2. 定義路由和處理函數
3. 在 `main.py` 註冊路由

### 添加新專家
1. 在 `app/detector/` 創建專家模組
2. 實作分析邏輯
3. 整合到 `main_force_v3.py`

---

## 🔧 維護

### 更新依賴
```bash
pip install --upgrade -r requirements-v3.txt
pip freeze > requirements-v3.txt
```

### 數據庫遷移
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

**下一步**: 開始開發 v3.0 核心專家系統！
