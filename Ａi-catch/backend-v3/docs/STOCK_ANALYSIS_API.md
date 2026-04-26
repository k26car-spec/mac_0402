# 股票綜合分析 API 使用說明

## 🚀 功能概述

新增完整的股票綜合分析系統，提供類似您圖片中的完整分析功能。

### 核心功能

1. **綜合評分系統** - 四維度評分
   - 成長性 (20%)
   - 估值 (25%)
   - 財務品質 (25%)
   - 技術面 (30%)

2. **買入訊號分析**
   - 多頭排列
   - MACD 黃金交叉
   - RSI 超賣
   - KD 低檔黃金交叉
   - 法人連續買超
   - 本益比低估
   - 高殖利率

3. **賣出訊號分析**
   - 空頭排列
   - MACD 死亡交叉
   - RSI 極度超買
   - KD 高檔死亡交叉
   - 乖離率過高
   - 法人連續賣超
   - 本益比過高

4. **風險警示**
   - ROE 偏低
   - 營收衰退
   - RSI 過熱
   - 負債比過高
   - 流動比率過低
   - 短期漲幅過大

5. **三大法人籌碼**
   - 外資買賣超
   - 投信買賣超
   - 自營商買賣超
   - 連續買/賣超天數
   - 籌碼趨勢判斷

6. **財務健康指標**
   - ROE (股東權益報酬率)
   - EPS (每股盈餘)
   - 營收成長率 (3年)
   - 毛利率
   - 負債比
   - 流動比率
   - 速動比率
   - 自由現金流

7. **估值分析**
   - 本益比 (PE)
   - 股價淨值比 (PB)
   - 殖利率
   - PEG
   - EV/EBITDA

8. **技術指標**
   - RSI (14)
   - MACD
   - KD (9)
   - 布林通道寬度
   - 乖離率 (20日/60日)
   - 趨勢判斷

9. **股票相關新聞** (透過 Perplexity API 或爬蟲)

---

## 📡 API 端點

### 基本路徑
```
/api/stock-analysis
```

### 1. 綜合分析
取得完整的股票綜合分析報告

```
GET /api/stock-analysis/comprehensive/{stock_code}
```

**範例:**
```bash
curl http://127.0.0.1:8000/api/stock-analysis/comprehensive/2330
```

**回傳:**
```json
{
  "status": "success",
  "stock_code": "2330",
  "stock_name": "台積電",
  "overall_score": 79.8,
  "dimension_scores": [...],
  "buy_signals": [...],
  "sell_signals": [...],
  "risk_alerts": [...],
  "financial_health": {...},
  "valuation": {...},
  "technical_indicators": {...},
  "institutional_trading": {...},
  "related_news": [...],
  "ai_summary": "...",
  "recommendation": "買進",
  "target_price": 1193.10,
  "stop_loss": 984.60
}
```

### 2. 買入/賣出訊號
取得股票的交易訊號

```
GET /api/stock-analysis/signals/{stock_code}
GET /api/stock-analysis/signals/{stock_code}?signal_type=buy
GET /api/stock-analysis/signals/{stock_code}?signal_type=sell
```

### 3. 風險警示
取得股票的風險警示

```
GET /api/stock-analysis/risks/{stock_code}
GET /api/stock-analysis/risks/{stock_code}?min_level=high
```

### 4. 財務健康
取得股票的財務健康指標

```
GET /api/stock-analysis/financial-health/{stock_code}
```

### 5. 三大法人籌碼
取得股票的法人買賣超資料

```
GET /api/stock-analysis/institutional/{stock_code}
GET /api/stock-analysis/institutional/{stock_code}?days=10
```

### 6. 技術指標
取得股票的技術分析指標

```
GET /api/stock-analysis/technical/{stock_code}
```

### 7. 股票新聞
取得股票相關新聞

```
GET /api/stock-analysis/news/{stock_code}
GET /api/stock-analysis/news/{stock_code}?limit=10
```

### 8. 批量分析
批量分析多檔股票

```
GET /api/stock-analysis/batch?symbols=2330,2454,2317
```

### 9. 市場概覽
取得今日市場整體狀況

```
GET /api/stock-analysis/market-overview
```

---

## ⚙️ 設定

### Perplexity API (可選)
若要啟用 AI 新聞搜尋功能，請設定環境變數：

```bash
export PERPLEXITY_API_KEY="your-api-key"
```

若未設定，系統會使用內建的新聞爬蟲。

---

## 📂 新增檔案

1. **`app/services/stock_comprehensive_analyzer.py`**
   - 股票綜合分析服務核心
   - 包含所有分析邏輯

2. **`app/api/stock_analysis.py`**
   - API 端點定義
   - 提供完整的 REST API

---

## 🔗 與前端整合

### 取得綜合分析

```javascript
// React/Next.js 範例
const [analysis, setAnalysis] = useState(null);

useEffect(() => {
  fetch(`/api/stock-analysis/comprehensive/${stockCode}`)
    .then(res => res.json())
    .then(data => setAnalysis(data));
}, [stockCode]);

// 顯示綜合評分
<div className="score-card">
  <h2>綜合評分</h2>
  <div className="score">{analysis.overall_score}/100</div>
  {analysis.dimension_scores.map(d => (
    <div key={d.name}>
      <span>{d.name}</span>
      <span>{d.score}分</span>
    </div>
  ))}
</div>
```

### 顯示買入訊號

```javascript
// 買入訊號列表
<div className="signals">
  <h3>買入訊號 ({analysis.buy_signals.length})</h3>
  {analysis.buy_signals.map(s => (
    <div key={s.name} className="signal">
      <span className="icon">✅</span>
      <span className="name">{s.name}</span>
      <span className="confidence">信心度: {s.confidence}%</span>
      <p>{s.description}</p>
    </div>
  ))}
</div>
```

### 顯示風險警示

```javascript
// 風險警示列表
<div className="risk-alerts">
  <h3>風險警示 ({analysis.risk_alerts.length})</h3>
  {analysis.risk_alerts.map(r => (
    <div key={r.title} className={`alert alert-${r.level}`}>
      <span className="icon">⚠️</span>
      <span className="title">{r.title}</span>
      <p>{r.description}</p>
    </div>
  ))}
</div>
```

---

## 📊 回傳資料結構

### DimensionScore (維度評分)
```typescript
{
  name: string;       // 維度名稱
  score: number;      // 分數 (0-100)
  weight: number;     // 權重
  details: string[];  // 詳細說明
}
```

### Signal (訊號)
```typescript
{
  type: "buy" | "sell";  // 訊號類型
  name: string;          // 訊號名稱
  description: string;   // 描述
  confidence: number;    // 信心度 (0-100)
  source: string;        // 來源
}
```

### RiskAlert (風險警示)
```typescript
{
  level: "low" | "medium" | "high" | "critical";  // 風險等級
  title: string;      // 警示標題
  description: string; // 描述
  metric: string;     // 指標名稱
  value: any;         // 指標數值
}
```

---

## 🚀 啟動服務

```bash
cd backend-v3
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

API 文件: http://127.0.0.1:8000/api/docs

---

## 📈 更新日誌

- **2025-12-25**: 新增股票綜合分析 API
  - 四維度評分系統
  - 買入/賣出訊號分析
  - 風險警示系統
  - 三大法人籌碼分析
  - 財務健康指標
  - 技術指標分析
  - Perplexity AI 新聞整合
