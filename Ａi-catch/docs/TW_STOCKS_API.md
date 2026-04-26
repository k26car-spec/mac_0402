# 台股清單 API 使用說明

## 概述

此 API 提供完整的台股清單管理功能，支援：
- 所有上市（TWSE）和上櫃（TPEX）股票
- 繁體中文股票名稱
- 從證交所和櫃買中心自動同步更新
- 快速搜尋功能

## API 端點

### 1. 獲取所有台股清單

```
GET /api/tw-stocks/
```

**參數：**
- `skip` (int): 跳過的記錄數，預設 0
- `limit` (int): 返回的最大記錄數，預設 100，最大 2000
- `market` (string): 市場篩選 `TWSE`（上市）或 `TPEX`（上櫃）
- `active_only` (bool): 只顯示有效股票，預設 true

**範例：**
```bash
# 獲取前 100 支上市股票
curl "http://localhost:8000/api/tw-stocks/?market=TWSE&limit=100"

# 獲取所有上櫃股票
curl "http://localhost:8000/api/tw-stocks/?market=TPEX&limit=2000"
```

### 2. 搜尋股票

```
GET /api/tw-stocks/search?q={關鍵字}
```

**參數：**
- `q` (string): 搜尋關鍵字（代碼或名稱），**必填**
- `limit` (int): 返回的最大記錄數，預設 10

**範例：**
```bash
# 搜尋台積電
curl "http://localhost:8000/api/tw-stocks/search?q=台積"

# 搜尋代碼 2330
curl "http://localhost:8000/api/tw-stocks/search?q=2330"

# 搜尋所有包含 "電" 的股票
curl "http://localhost:8000/api/tw-stocks/search?q=電&limit=20"
```

### 3. 獲取單一股票資訊

```
GET /api/tw-stocks/{symbol}
```

**範例：**
```bash
curl "http://localhost:8000/api/tw-stocks/2330"
```

### 4. 從證交所同步台股清單

```
POST /api/tw-stocks/sync
```

**說明：**
- 從證交所和櫃買中心獲取最新的股票清單
- 自動新增新股票
- 自動更新股票名稱
- 自動標記已下市股票
- 此操作可能需要 10-30 秒

**範例：**
```bash
curl -X POST "http://localhost:8000/api/tw-stocks/sync"
```

**回應：**
```json
{
    "success": true,
    "message": "台股清單同步完成",
    "statistics": {
        "total_from_api": 1850,
        "added": 5,
        "updated": 10,
        "delisted": 2
    },
    "last_sync": "2025-12-20T00:45:00"
}
```

### 5. 取得統計摘要

```
GET /api/tw-stocks/stats/summary
```

**範例：**
```bash
curl "http://localhost:8000/api/tw-stocks/stats/summary"
```

**回應：**
```json
{
    "success": true,
    "statistics": {
        "total": 1850,
        "active": 1845,
        "inactive": 5,
        "twse": 980,
        "tpex": 870
    }
}
```

### 6. 初始化台股清單（首次使用）

```
POST /api/tw-stocks/init
```

**說明：**
- 首次使用時呼叫，會從證交所獲取所有股票
- 如果資料庫已有資料，會提示使用 `/sync` 端點

---

## 前端整合

前端搜尋框已自動使用此 API：

```typescript
// 搜尋 API
const response = await fetch(
    `http://localhost:8000/api/tw-stocks/search?q=${keyword}&limit=8`
);
const data = await response.json();
// data.stocks = [{ symbol, name, market, industry }, ...]
```

---

## 首次設置步驟

1. **確保資料庫已初始化**
   ```bash
   cd backend-v3
   python -m alembic upgrade head
   ```

2. **同步台股清單**
   ```bash
   curl -X POST "http://localhost:8000/api/tw-stocks/sync"
   ```

3. **驗證同步結果**
   ```bash
   curl "http://localhost:8000/api/tw-stocks/stats/summary"
   ```

---

## 定期更新

建議設置每日定時任務（如 cron）來同步台股清單：

```bash
# 每天早上 8:00 同步
0 8 * * * curl -X POST "http://localhost:8000/api/tw-stocks/sync"
```

---

## 資料來源

- **上市股票**：台灣證券交易所（TWSE）
- **上櫃股票**：證券櫃檯買賣中心（TPEX / OTC）
