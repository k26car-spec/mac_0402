# 📊 持有股票與交易紀錄系統

## 功能概述

這個系統讓您可以追蹤持有股票、交易紀錄，並透過 AI 模擬來驗證各分析來源的準確性。

### 主要功能

1. **持有股票管理**
   - 新增/編輯/刪除持倉
   - 追蹤進場價、停損價、目標價
   - 即時計算未實現損益
   - 記錄分析來源與信心度

2. **交易紀錄**
   - 自動記錄買入/賣出操作
   - 完整的交易歷史追蹤
   - 損益統計

3. **AI 模擬交易**
   - 從分析信號自動模擬進出場
   - 使用歷史數據驗證分析準確性
   - 產生模擬交易報告

4. **準確性分析**
   - 各分析來源的勝率統計
   - 平均獲利/虧損計算
   - 分析來源評級與建議

---

## 資料結構

### Portfolio (持有股票)

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | BigInt | 主鍵 |
| symbol | String(20) | 股票代碼 |
| stock_name | String(100) | 股票名稱 |
| entry_date | DateTime | 進場日期時間 |
| entry_price | Decimal(10,2) | 進場價格 |
| entry_quantity | Integer | 進場數量（股） |
| analysis_source | String(50) | 分析來源 |
| analysis_confidence | Decimal(3,2) | 分析信心度 (0-1) |
| analysis_details | JSON | 詳細分析數據 |
| stop_loss_price | Decimal(10,2) | 停損價 |
| stop_loss_amount | Decimal(10,2) | 停損金額 |
| target_price | Decimal(10,2) | 目標價 |
| current_price | Decimal(10,2) | 當前價格 |
| unrealized_profit | Decimal(12,2) | 未實現損益 |
| unrealized_profit_percent | Decimal(6,2) | 未實現損益比例 |
| exit_date | DateTime | 出場日期 |
| exit_price | Decimal(10,2) | 出場價格 |
| exit_reason | String(100) | 出場原因 |
| realized_profit | Decimal(12,2) | 已實現損益 |
| realized_profit_percent | Decimal(6,2) | 已實現損益比例 |
| status | String(20) | 狀態 (open/closed/stopped/target_hit) |
| is_simulated | Boolean | 是否為模擬交易 |
| notes | Text | 備註 |

### TradeRecord (交易紀錄)

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | BigInt | 主鍵 |
| portfolio_id | BigInt | 關聯持有紀錄 |
| symbol | String(20) | 股票代碼 |
| stock_name | String(100) | 股票名稱 |
| trade_type | String(10) | 交易類型 (buy/sell) |
| trade_date | DateTime | 交易日期時間 |
| price | Decimal(10,2) | 成交價格 |
| quantity | Integer | 成交數量 |
| total_amount | Decimal(12,2) | 總金額 |
| analysis_source | String(50) | 分析來源 |
| profit | Decimal(12,2) | 損益（賣出時） |
| profit_percent | Decimal(6,2) | 損益比例 |
| is_simulated | Boolean | 是否為模擬 |

### AnalysisAccuracy (分析準確性)

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | BigInt | 主鍵 |
| analysis_source | String(50) | 分析來源 |
| period_start | DateTime | 統計起始日期 |
| period_end | DateTime | 統計結束日期 |
| total_trades | Integer | 總交易次數 |
| winning_trades | Integer | 獲利次數 |
| losing_trades | Integer | 虧損次數 |
| win_rate | Decimal(5,2) | 勝率 |
| avg_profit_percent | Decimal(6,2) | 平均獲利比例 |
| avg_loss_percent | Decimal(6,2) | 平均虧損比例 |
| profit_factor | Decimal(6,2) | 獲利因子 |

---

## API 端點

### 持倉管理

```
GET  /api/portfolio/positions          # 取得所有持倉
GET  /api/portfolio/positions/open     # 取得持有中的持倉
GET  /api/portfolio/positions/{id}     # 取得單一持倉
POST /api/portfolio/positions          # 新增持倉
PATCH /api/portfolio/positions/{id}    # 更新持倉
POST /api/portfolio/positions/{id}/close  # 結束持倉（賣出）
DELETE /api/portfolio/positions/{id}   # 刪除持倉
```

### 交易紀錄

```
GET /api/portfolio/trades              # 取得交易紀錄
    ?symbol=2330                       # 依股票篩選
    ?source=main_force                 # 依來源篩選
    ?trade_type=buy                    # 依類型篩選
    ?start_date=2024-01-01             # 起始日期
    ?end_date=2024-12-31               # 結束日期
```

### 準確性分析

```
GET /api/portfolio/accuracy            # 取得各來源準確性
    ?days=30                           # 統計天數
GET /api/portfolio/summary             # 取得投資組合總結
```

### AI 模擬

```
POST /api/portfolio/simulate           # 手動模擬單筆交易
POST /api/portfolio/auto-simulate      # 自動從分析信號模擬
    ?source=main_force                 # 分析來源
    ?days=7                            # 查詢最近幾天
```

---

## 分析來源代碼

| 代碼 | 說明 |
|------|------|
| main_force | 主力偵測 |
| big_order | 大單分析 |
| lstm_prediction | LSTM 預測 |
| expert_signal | 專家信號 |
| premarket | 盤前分析 |
| manual | 手動操作 |
| ai_simulation | AI 模擬 |

---

## 使用流程

### 1. 初始化資料庫

```bash
cd backend-v3

# 執行資料庫遷移
alembic upgrade head
```

### 2. 啟動後端服務

```bash
# 啟動 FastAPI 服務
uvicorn app.main:app --reload --port 8000
```

### 3. 使用前端頁面

訪問 `http://localhost:3000/dashboard/portfolio`

### 4. AI 模擬驗證

在前端頁面點擊「模擬主力」或「模擬 LSTM」按鈕，系統會：
1. 查詢最近的分析信號
2. 使用歷史股價數據模擬交易
3. 記錄模擬結果
4. 計算準確性統計

---

## 準確性評級說明

系統會根據勝率、獲利因子和期望值對各分析來源進行評級：

| 評級 | 分數 | 說明 |
|------|------|------|
| A+ | 90+ | 極佳，建議加大配置 |
| A | 80-89 | 優秀，可信賴的分析來源 |
| B+ | 70-79 | 良好，可適度參考 |
| B | 60-69 | 一般，需搭配其他指標 |
| C | 50-59 | 及格，僅供參考 |
| D | < 50 | 不理想，建議調整或停用 |

---

## 注意事項

1. **模擬交易**會標記為 `is_simulated=True`，與真實交易分開統計
2. **停損/目標價**會自動判斷出場原因
3. **準確性分析**只計算已結束的交易
4. 建議定期執行 AI 模擬來驗證分析系統的表現

---

## 🤖 自動化功能

### 即時信號自動建倉

當系統偵測到高品質信號時（品質分數 ≥75%），會自動建立模擬持倉：

- **來源**：大單監控、主力偵測等
- **條件**：買入信號 + 品質分數 ≥0.75
- **設定**：
  - 預設停損：5%
  - 預設目標：8%
  - 模擬數量：1000 股

### 每日排程任務

安裝排程後，系統會自動在指定時間執行任務：

#### 開市任務 (09:00)
- 模擬前3天的分析信號
- 驗證各來源分析準確性

#### 收盤任務 (13:35)
- 更新所有持倉的當前價格
- 自動執行停損/達標
- 計算準確性統計與評級

### 安裝排程

```bash
# 安裝每日自動排程
./portfolio_scheduler.sh install

# 查看排程狀態
./portfolio_scheduler.sh status

# 手動執行開市任務
./portfolio_scheduler.sh morning

# 手動更新持倉價格
./portfolio_scheduler.sh update

# 移除排程
./portfolio_scheduler.sh uninstall
```

---

## 🔗 快速啟動

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
```

這會啟動所有服務，包括：
- 後端 API (port 8000)
- 前端介面 (port 3000)
- 大單偵測監控 (port 8082)
- 資料庫表自動初始化
- 即時信號自動建倉功能
