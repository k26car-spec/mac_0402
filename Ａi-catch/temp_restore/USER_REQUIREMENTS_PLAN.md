# 🎯 用戶需求改進計畫
## AI 智慧選股系統優化方案

**建立日期**: 2025-12-20  
**更新日期**: 2025-12-20  
**目標**: 解決操作不便問題，提供實用的 AI 選股功能

---

## ✅ 實作進度

| # | 需求 | 狀態 | 說明 |
|---|------|------|------|
| 1 | AI 新聞爬蟲分析 | ✅ 完成 | `news_crawler_service.py` |
| 2 | 股價篩選優化 | ✅ 完成 | 預設 ≤$200, ≥500張 |
| 3 | 大單監控動態閾值 | ✅ 完成 | `big_order_config.py` |
| 4 | 熱門股AI推薦 | ✅ 完成 | `smart_picks.py` API |
| 5 | 前端頁面 | ✅ 完成 | `/dashboard/smart-picks` |

---

## 📁 新增檔案列表

```
backend-v3/app/
├── api/
│   └── smart_picks.py           # 智慧選股 API ✨新增
├── services/
│   └── news_crawler_service.py  # 新聞爬蟲服務 ✨新增
└── config/
    └── big_order_config.py      # 大單動態閾值 ✨新增

frontend-v3/src/app/dashboard/
└── smart-picks/
    └── page.tsx                 # 智慧選股頁面 ✨新增
```

---

## 🚀 如何使用

### 1. 啟動後端服務
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

### 2. 啟動前端
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/frontend-v3
npm run dev
```

### 3. 訪問智慧選股頁面
```
http://localhost:3000/dashboard/smart-picks
```

### 4. 直接呼叫 API
```bash
# 快速選股 (股價 ≤200元, 成交量 ≥500張)
curl "http://localhost:8000/api/smart-picks/quick-picks?max_price=200&min_volume=500"

# 完整分析 (可自訂篩選條件)
curl -X POST "http://localhost:8000/api/smart-picks/smart-picks" \
  -H "Content-Type: application/json" \
  -d '{"max_price": 200, "min_volume": 500}'

# 取得今日新聞摘要
curl "http://localhost:8000/api/smart-picks/news-summary"
```

### 方案 2: 股價篩選優化

```python
# 篩選邏輯
filters = {
    "max_price": 200,           # 股價上限
    "min_volume": 500,          # 最低成交量(張)
    "min_turnover_rate": 0.5,   # 最低週轉率%
    "market_cap_rank": "top50%", # 市值排名
    "news_mentions": True       # 近期有新聞
}
```

### 方案 3: 大單監控公式

```python
# 動態大單閾值 (依股價調整)
def calculate_big_order_threshold(price):
    """
    股價    | 大單閾值
    --------|----------
    < 50    | 100 張
    50-100  | 50 張  
    100-200 | 30 張
    200-500 | 20 張
    > 500   | 10 張
    """
    if price < 50:
        return 100
    elif price < 100:
        return 50
    elif price < 200:
        return 30
    elif price < 500:
        return 20
    else:
        return 10

# 1分鐘累積閾值
def calculate_minute_threshold(price, base_threshold):
    return base_threshold * 2  # 1分鐘內2倍視為異常
```

### 方案 4: 整合式 AI 推薦

```python
# 推薦系統流程
1. 爬取新聞 -> 提取熱門股票代碼
2. 價格篩選 -> 過濾 > 200 元
3. 成交量篩選 -> 過濾冷門股
4. 9 專家分析 -> 綜合評分
5. 分類輸出:
   - 短期 (1-5天): 技術面強勢
   - 中期 (1-4週): 籌碼轉強
   - 長期 (1-3個月): 基本面佳
```

---

## 📅 實作時程

### 第一階段: 新聞爬蟲 (Day 1-2)
- [ ] 建立 `news_crawler.py`
- [ ] 整合多個新聞來源
- [ ] NLP 情緒分析
- [ ] 股票代碼提取

### 第二階段: 股價篩選 (Day 2-3)
- [ ] 修改 `/api/premarket.py`
- [ ] 新增價格/成交量篩選
- [ ] 整合新聞熱度

### 第三階段: 大單監控 (Day 3-4)
- [ ] 修改 `/api/big_order.py`
- [ ] 動態閾值計算
- [ ] 1分鐘累積監控
- [ ] Email 即時推送

### 第四階段: 整合推薦 (Day 4-5)
- [ ] 建立 `smart_picks.py` API
- [ ] 前端頁面整合
- [ ] 每日自動報告

---

## 📱 前端介面規劃

### 新增頁面: `/dashboard/smart-picks`

```
┌────────────────────────────────────────────┐
│  🤖 AI 智慧選股                            │
├────────────────────────────────────────────┤
│  📰 今日新聞重點                           │
│  ├── 🔥 熱門話題: AI 概念股、航運反彈     │
│  └── 📊 相關個股: 2330, 2454, 2603...      │
├────────────────────────────────────────────┤
│  🎯 價格篩選: ≤ 200元  成交量: ≥ 500張    │
├────────────────────────────────────────────┤
│  ⭐ AI 推薦清單                            │
│                                            │
│  【短期】(1-5天)                           │
│  | 股票 | 價格 | 新聞熱度 | AI評分 | 推薦 |
│  |------|------|----------|--------|------|
│  | 2603 | 98.5 | 🔥🔥🔥   | 85%   | ⭐⭐⭐ |
│  | 3443 | 145  | 🔥🔥     | 78%   | ⭐⭐   |
│                                            │
│  【中期】(1-4週)                           │
│  | 股票 | 價格 | 籌碼轉變 | AI評分 | 推薦 |
│  |------|------|----------|--------|------|
│  | 2618 | 32.5 | 外資買   | 82%   | ⭐⭐⭐ |
│                                            │
│  【長期】(1-3月)                           │
│  | 股票 | 價格 | 基本面   | AI評分 | 推薦 |
│  |------|------|----------|--------|------|
│  | 2887 | 28.8 | ROE 15%  | 88%   | ⭐⭐⭐ |
└────────────────────────────────────────────┘
```

---

## ✅ 確認事項

請確認以下設定：

1. **股價上限**: 200 元 (可調整?)
2. **最低成交量**: 500 張/日 (可調整?)
3. **大單張數閾值**: 使用上述動態計算?
4. **Email 通知頻率**: 即時 or 批次(每5分鐘)?
5. **新聞來源優先順序**: 鉅亨網 > 經濟日報 > Yahoo?

---

## 🚀 立即執行

一旦確認，我將開始：
1. 創建新聞爬蟲模組
2. 修改股價篩選邏輯
3. 強化大單監控通知
4. 建立整合推薦 API
5. 開發前端頁面

**預計完成時間**: 3-5 個工作日
