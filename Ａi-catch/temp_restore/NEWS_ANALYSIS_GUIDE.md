# 產業新聞分析系統使用說明

## 📌 系統概述

本系統整合 IEK 產業情報網與手動更新的 Perplexity AI 新聞，自動分析哪些股票值得關注。

### 新聞來源

1. **IEK 產業情報網** (自動抓取)
   - 網址：https://ieknet.iek.org.tw/member/DailyNews.aspx
   - 涵蓋：半導體、資通訊、零組件及材料、車輛、綠能與環境、生技醫療、機械、產經政策等產業
   - 更新頻率：每 30 分鐘自動快取

2. **Perplexity AI** (手動更新)
   - 因 Perplexity API 需付費，系統支援手動輸入新聞
   - 可透過前端介面或 API 新增

3. **其他來源** (手動輸入)
   - 支援任意來源的新聞手動輸入

---

## 🚀 快速開始

### 1. 確認 API 服務運行

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_api_v3.sh
```

或直接運行：
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/app
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 存取前端頁面

前端地址：http://127.0.0.1:3002/news

### 3. 查看 API 文檔

API 文檔：http://127.0.0.1:8000/api/docs

---

## 📡 API 端點

### 取得完整新聞分析
```bash
GET http://127.0.0.1:8000/api/news/analysis
```

返回：
- IEK、Perplexity、手動新聞
- 股票提及次數統計
- 股票推薦清單

### 取得 IEK 產業新聞
```bash
GET http://127.0.0.1:8000/api/news/iek
```

### 取得今日關注股票
```bash
GET http://127.0.0.1:8000/api/news/stocks-to-watch
```

### 依產業分類取得新聞
```bash
GET http://127.0.0.1:8000/api/news/industries
```

### 取得特定股票相關新聞
```bash
GET http://127.0.0.1:8000/api/news/by-stock/{symbol}
# 例如：GET http://127.0.0.1:8000/api/news/by-stock/2330
```

### 取得 Perplexity 新聞
```bash
GET http://127.0.0.1:8000/api/news/perplexity
```

### 手動新增 Perplexity 新聞
```bash
POST http://127.0.0.1:8000/api/news/perplexity
Content-Type: application/json

{
    "title": "台積電法說會釋利多，外資目標價上調至1200元",
    "content": "台積電在法說會上宣布...",
    "stocks": ["2330"],
    "sentiment": "positive"
}
```

### 手動新增其他新聞
```bash
POST http://127.0.0.1:8000/api/news/manual
Content-Type: application/json

{
    "title": "AI 伺服器需求爆發",
    "content": "...",
    "stocks": ["2382", "3231", "6669"],
    "sentiment": "positive",
    "category": "科技"
}
```

---

## 📊 股票關注分析邏輯

系統根據以下因素計算股票關注分數：

1. **新聞提及次數** - 被新聞提及越多次，分數越高
2. **情緒分析** - 正面新聞加分，負面新聞減分
3. **產業關聯** - 根據產業關鍵詞自動關聯股票

### 關注等級

| 等級 | 分數範圍 | 說明 |
|------|---------|------|
| 🔴 強力關注 | ≥40 且情緒>0.3 | 多則正面新聞，值得密切關注 |
| 🟠 值得關注 | ≥25 且情緒≥0 | 較多新聞提及，可以關注 |
| 🟡 觀察 | ≥15 | 有新聞提及，可觀察 |
| ⚪ 低度關注 | <15 | 較少新聞提及 |

---

## 🔧 手動更新 Perplexity 新聞的步驟

因為 Perplexity API 需要付費，建議使用以下方式手動更新：

### 方法 1：使用前端介面

1. 前往 http://127.0.0.1:3002/news
2. 點擊「Perplexity」標籤
3. 點擊「手動新增」按鈕
4. 填入新聞標題、內容、相關股票、情緒判斷
5. 點擊「新增」

### 方法 2：使用 curl 命令

```bash
curl -X POST http://127.0.0.1:8000/api/news/perplexity \
  -H "Content-Type: application/json" \
  -d '{
    "title": "您的新聞標題",
    "content": "新聞內容摘要",
    "stocks": ["2330", "2454"],
    "sentiment": "positive"
  }'
```

### 方法 3：直接編輯 JSON 檔案

檔案位置：`/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/data/news/perplexity_news.json`

```json
{
  "updated_at": "2025-12-26T10:00:00",
  "source": "perplexity",
  "news": [
    {
      "id": "perplexity_1",
      "title": "新聞標題",
      "content": "內容摘要",
      "stocks": ["2330"],
      "sentiment": "positive",
      "source": "Perplexity AI",
      "created_at": "2025-12-26T10:00:00"
    }
  ]
}
```

---

## 📂 相關檔案

| 檔案 | 說明 |
|------|------|
| `backend-v3/app/services/news_analysis_service.py` | 新聞分析服務主程式 |
| `backend-v3/app/services/iek_news_crawler.py` | IEK 新聞爬蟲 |
| `backend-v3/data/news/perplexity_news.json` | Perplexity 新聞資料 |
| `backend-v3/data/news/manual_news.json` | 手動新聞資料 |
| `frontend-v3/src/app/news/page.tsx` | 前端新聞分析頁面 |

---

## 🎯 今日關注股票 (範例輸出)

```
Success: True
Date: 2025-12-26
Count: 20
  2382 廣達: 強力關注 (提及3次, 分數60.0)
  3231 緯創: 強力關注 (提及3次, 分數60.0)
  2356 英業達: 強力關注 (提及3次, 分數60.0)
  3324 雙鴻: 強力關注 (提及2次, 分數50.0)
  6239 力成: 強力關注 (提及1次, 分數40.0)
```

---

## 🔗 快速連結

- **新聞分析前端**：http://127.0.0.1:3002/news
- **API 文檔**：http://127.0.0.1:8000/api/docs
- **IEK 原始資料**：https://ieknet.iek.org.tw/member/DailyNews.aspx

---

*建立時間：2025-12-26*
