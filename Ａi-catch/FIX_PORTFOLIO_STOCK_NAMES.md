# 修復持倉股票名稱為繁體中文 (2026-02-09)

## 問題描述
持股倉（Portfolio）中的股票名稱顯示為英文（如 FOCI、CAREER），而監控中的股票都是正確的繁體中文名稱。

## 根本原因
在創建持倉記錄時，`portfolio.py` 的 `create_position` 函數直接使用了傳入的 `stock_name` 參數，該參數可能來自 yfinance 或其他 API 返回的英文名稱。

## 解決方案

### 1. 修改 `create_position` API (✅ 已完成)
**文件**: `/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/app/api/portfolio.py`

**修改內容**:
- 在創建持倉前，使用富邦 API 的 `get_stock_name()` 獲取繁體中文股票名稱
- 替換所有使用 `data.stock_name` 的地方為 `stock_name_zh`
- 添加錯誤處理，如果富邦 API 失敗則回退到傳入的名稱

**關鍵代碼**:
```python
# 使用富邦 API 獲取繁體中文股票名稱（禁用股票名稱表）
try:
    from fubon_client import fubon_client
    stock_name_zh = await fubon_client.get_stock_name(data.symbol)
    # 如果富邦 API 返回代碼（未取得名稱），使用後備方案
    if stock_name_zh == data.symbol:
        stock_name_zh = data.stock_name or data.symbol
except Exception as e:
    stock_name_zh = data.stock_name or data.symbol

position = Portfolio(
    symbol=data.symbol,
    stock_name=stock_name_zh,  # 使用富邦 API 獲取的繁體名稱
    ...
)
```

### 2. 修復現有數據 (✅ 已完成)
**文件**: `/Users/Mac/Documents/ETF/AI/Ａi-catch/fix_portfolio_stock_names.py`

**功能**:
- 掃描所有 Portfolio 和 TradeRecord 記錄
- 識別英文名稱或缺失的股票名稱
- 使用富邦 API 批量更新為繁體中文

**執行結果**:
```
✅ 持倉更新: 43 筆
✅ 交易更新: 26 筆
```

**修復範例**:
- `6153: CAREER → 嘉聯益`
- `4958: ZHEN DING TECHNOLOGY HOLDING LT → 臻鼎-KY`
- `3363: FOCI → 上詮`
- `8150: CHIPMOS → 南茂`

### 3. 重啟後端服務 (✅ 已完成)
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
kill -9 $(lsof -ti:8000)
cd backend-v3
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
```

## 影響範圍

### 修改的文件
1. `/backend-v3/app/api/portfolio.py` - 修改 `create_position` 函數
2. `/fix_portfolio_stock_names.py` - 新增修復腳本

### 數據庫變更
- 更新 `portfolio` 表的 `stock_name` 欄位（43 筆）
- 更新 `trade_record` 表的 `stock_name` 欄位（26 筆）

## 驗證步驟

1. **檢查前端顯示**:
   - 訪問持倉頁面
   - 確認所有股票名稱都顯示為繁體中文

2. **測試新建倉位**:
   ```bash
   curl -X POST http://localhost:8000/api/portfolio/positions \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "2330",
       "entry_date": "2026-02-09T20:00:00",
       "entry_price": 1000,
       "analysis_source": "test"
     }'
   ```
   應返回 `stock_name: "台積電"` 而非英文名稱

## 注意事項

1. **API 速率限制**: 
   - 修復腳本在批量更新時可能觸發富邦 API 速率限制
   - 已實現錯誤處理，失敗的記錄會保留原名稱

2. **後續維護**:
   - 所有新建倉位將自動使用富邦 API 獲取繁體名稱
   - 不再依賴 `stock_mappings.py` 或其他股票名稱表

3. **性能影響**:
   - 每次創建倉位需額外調用一次富邦 API
   - 已實現快取機制減少重複請求

## 完成狀態

- [x] 修改 `create_position` API
- [x] 創建並執行修復腳本
- [x] 更新現有數據庫記錄
- [x] 重啟後端服務
- [x] 文檔更新

## 技術債務

**已解決**:
- ✅ 使用富邦 API 替代股票名稱表
- ✅ 自動獲取繁體中文名稱
- ✅ 修復歷史數據

**建議改進**:
- 可考慮在 fubon_client 中實現更智能的緩存策略
- 對於遇到速率限制的股票，可以實現延遲重試機制

---
**修復完成時間**: 2026-02-09 19:45
**修復人員**: AI Assistant
**影響版本**: V3.0+
