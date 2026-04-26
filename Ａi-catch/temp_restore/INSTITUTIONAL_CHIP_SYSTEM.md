# 法人籌碼系統 API 使用指南

> 建立日期: 2026-01-02
> 版本: 1.0.0

## 📊 系統架構

```
[外部數據源] --> [數據採集層] --> [數據處理與儲存層] --> [業務邏輯層] --> [API層]
       ↓              ↓                   ↓                  ↓             ↓
   ┌───────┐    ┌──────────┐       ┌──────────────┐    ┌─────────┐   ┌─────────┐
   │富邦API │    │TAIFEX爬蟲│       │ PostgreSQL   │    │籌碼計算 │   │ FastAPI │
   │證交所  │ -> │融資融券  │  ->   │ 6個資料表    │ -> │情緒分析 │-> │ 13端點  │
   │期交所  │    │TWSE爬蟲  │       │ SQL Views    │    │連續性   │   │ WebSocket│
   └───────┘    └──────────┘       └──────────────┘    └─────────┘   └─────────┘
```

## 🗄️ 資料庫結構

### 資料表清單

| 表名 | 說明 | 資料來源 | 更新頻率 |
|------|------|----------|----------|
| `institutional_trading` | 三大法人買賣超日報 | 證交所 T86 | 盤後 |
| `branch_trading` | 券商分點買賣超 | 富邦/Goodinfo | 盤後 |
| `margin_trading` | 融資融券餘額 | 證交所/櫃買 | 盤後 |
| `futures_open_interest` | 期貨未平倉部位 | 期交所 TAIFEX | 盤後 |
| `options_open_interest` | 選擇權未平倉部位 | 期交所 TAIFEX | 盤後 |
| `institutional_continuous` | 法人連續買賣超統計 | 計算結果 | 盤後 |

### 檢視表

| 檢視表 | 說明 |
|--------|------|
| `v_foreign_continuous_buy_top` | 外資連續買超前20名 |
| `v_investment_continuous_buy_top` | 投信連續買超前20名 |
| `v_futures_foreign_summary` | 外資期貨多空摘要 |
| `v_margin_abnormal` | 融資融券異常股票 |

---

## 🌐 API 端點

### 期貨選擇權類

#### 1. 取得期貨法人未平倉
```bash
GET /api/institutional/futures?date=2026-01-02
```
**回應範例:**
```json
{
  "success": true,
  "date": "2026-01-02",
  "data": [
    {
      "contract": "TX",
      "contract_name": "臺股期貨",
      "identity": "foreign",
      "long_position": 50000,
      "short_position": 45000,
      "net_position": 5000
    }
  ],
  "summary": {
    "foreign_net": 5000,
    "investment_net": -200,
    "dealer_net": 1000
  }
}
```

#### 2. 取得選擇權法人未平倉
```bash
GET /api/institutional/options?date=2026-01-02
```

#### 3. 取得大額交易人部位
```bash
GET /api/institutional/large-trader?date=2026-01-02
```

#### 4. 取得市場情緒指標 ⭐
```bash
GET /api/institutional/market-sentiment?date=2026-01-02
```
**回應範例:**
```json
{
  "success": true,
  "analysis": {
    "foreign_futures_net": 5000,
    "pc_ratio": 0.85,
    "foreign_stance": "偏多",
    "market_sentiment": "偏樂觀"
  }
}
```

---

### 融資融券類

#### 5. 取得全市場融資融券
```bash
GET /api/institutional/margin-trading?date=2026-01-02
```

#### 6. 取得個股融資融券歷史
```bash
GET /api/institutional/margin-trading/2330?days=30
```

#### 7. 取得融資融券異常股票
```bash
GET /api/institutional/margin-abnormal?margin_threshold=500&short_threshold=200
```

#### 8. 取得散戶情緒指標
```bash
GET /api/institutional/retail-sentiment?date=2026-01-02
```
**回應範例:**
```json
{
  "success": true,
  "retail_sentiment": "偏多",
  "margin_change_ratio": 0.5,
  "short_change_ratio": -0.2
}
```

---

### 綜合分析類

#### 9. 籌碼綜合摘要 ⭐⭐⭐ (最重要)
```bash
GET /api/institutional/chip-summary?date=2026-01-02
```
**回應範例:**
```json
{
  "success": true,
  "summary": {
    "overall_stance": "偏多",
    "total_score": 25.5,
    "foreign_futures_net": 5000,
    "pc_ratio": 0.85,
    "retail_sentiment": "偏多"
  },
  "recommendation": {
    "action": "買進",
    "confidence": 0.255,
    "reason": "外資期貨淨部位 +5,000 口，P/C Ratio 0.85，散戶偏多"
  }
}
```

#### 10. 取得個股法人買賣超
```bash
GET /api/institutional/net-values/2330?days=30
```

#### 11. 取得法人連續買賣超天數
```bash
GET /api/institutional/continuous/2330
```
**回應範例:**
```json
{
  "success": true,
  "symbol": "2330",
  "foreign": {"direction": "buy", "days": 5, "total": 125000},
  "investment": {"direction": "buy", "days": 3, "total": 50000},
  "dealer": {"direction": "sell", "days": 2, "total": -10000}
}
```

---

## 📈 籌碼分析邏輯

### 綜合分數計算 (-100 ~ +100)

```python
futures_score = min(max(外資期貨淨部位 / 100, -50), 50)  # 佔50分
options_score = (1 - PC_Ratio) * 30                       # 佔30分  
margin_score = 融資變化率 * 5                             # 佔20分

total_score = futures_score + options_score + margin_score
```

### 總體態度判斷

| 分數區間 | 態度 |
|----------|------|
| > 30 | 強烈看多 |
| 10 ~ 30 | 偏多 |
| -10 ~ 10 | 中性 |
| -30 ~ -10 | 偏空 |
| < -30 | 強烈看空 |

### P/C Ratio 解讀

| P/C Ratio | 市場情緒 |
|-----------|----------|
| > 1.2 | 極度恐慌 |
| 1.0 ~ 1.2 | 偏悲觀 |
| 0.8 ~ 1.0 | 中性 |
| 0.6 ~ 0.8 | 偏樂觀 |
| < 0.6 | 極度樂觀 |

---

## 🔧 快速測試

```bash
# 測試期貨法人
curl -s "http://localhost:8000/api/institutional/futures" | jq

# 測試融資融券
curl -s "http://localhost:8000/api/institutional/margin-trading" | jq

# 測試籌碼綜合摘要 (最有價值)
curl -s "http://localhost:8000/api/institutional/chip-summary" | jq

# 測試個股法人連續性
curl -s "http://localhost:8000/api/institutional/continuous/2330" | jq
```

---

## 📂 相關檔案

| 檔案路徑 | 說明 |
|----------|------|
| `backend-v3/app/models/institutional.py` | 資料庫模型 |
| `backend-v3/app/services/taifex_crawler.py` | 期交所爬蟲 |
| `backend-v3/app/services/margin_trading_crawler.py` | 融資融券爬蟲 |
| `backend-v3/migrations/001_create_institutional_tables.sql` | SQL Migration |

---

## 🚀 下一步建議

1. **定時任務**: 設定 cron 在盤後自動抓取數據
2. **前端整合**: 將籌碼儀表板加入 Next.js 前端
3. **Redis 快取**: 熱門查詢結果快取
4. **Alert 系統**: 當籌碼發生異常時發送通知
