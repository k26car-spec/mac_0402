# 📊 當沖戰情室 Performance Optimization Plan
**目標**：大幅提升 http://localhost:5173/ 頁面更新速度

## 🎯 問題分析

### 現有性能瓶頸：
1. **ORB股票名稱查詢慢**
   - 每個股票要查詢4個API（Fubon, Analysis, Comprehensive, BigOrder）
   - 批次間有500ms延遲
   - 總共50+個股票 = 最長需要5-10秒

2. **API請求串聯慢**
   - 使用fallback架構：API1失敗→API2→API3→API4
   - 每個timeout 2-3秒 = 單個股票最長12秒

3. **前端輪詢問題**
   - 可能存在多個setInterval同時運行
   - 沒有使用WebSocket實時推送

## ⚡ 優化方案

### **方案一：後端批量名稱查詢API（最快）**

**實施步驟：**
1. 在 `backend-v3/app/api/` 新增批量查詢端點
2. 一次請求獲取所有股票名稱
3. 後端使用並發查詢（asyncio.gather）
4. 添加Redis緩存（TTL 24小時）

**預期效果：** 50個股票從10秒→0.5秒

```python
# 新增端點示例
@app.post("/api/stocks/batch-names")
async def get_batch_stock_names(codes: List[str]):
    # 從緩存獲取
    # 並發查詢缺失的名稱
    # 返回完整映射
```

### **方案二：前端優化（立即可用）**

1. **移除批次延遲**
   - 刪除第624行的500ms延遲
   - 使用Promise.all並發請求

2. **優化API fallback**
   - 減少timeout時間：3秒→1秒
   - 並行查詢而不是串聯

3. **添加本地緩存**
   - 使用localStorage緩存股票名稱
   - TTL 24小時

**預期效果：** 10秒→3秒

### **方案三：WebSocket實時推送（根本解決）**

1. **後端添加WebSocket服務**
   - 推送股價/法人數據更新
   - 減少前端輪詢

2. **前端訂閱機制**
   - 只訂閱當前監控的股票
   - 自動重連機制

**預期效果：** 延遲<100ms，無需輪詢

## 🚀 快速優化步驟（立即可用）

### **Step 1: 後端新增批量API（5分鐘）**
創建 `/api/stocks/batch-names` 端點

### **Step 2: 前端修改（10分鐘）**
修改 `orb_watchlist.html` 的 `fetchMissingNames` 函數

### **Step 3: 添加Redis緩存（可選）**
避免重複查詢相同的股票

## 💾 緩存策略

```javascript
// localStorage緩存示例
const CACHE_KEY = 'stock_names_cache';
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24小時

function getCachedNames() {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return {};
    const data = JSON.parse(cached);
    if (Date.now() - data.timestamp > CACHE_TTL) {
        localStorage.removeItem(CACHE_KEY);
        return {};
    }
    return data.names;
}

function setCachedNames(names) {
    localStorage.setItem(CACHE_KEY, JSON.stringify({
        names,
        timestamp: Date.now()
    }));
}
```

## 📈 效能提升預估

| 優化項目 | 當前耗時 | 優化後 | 提升幅度 |
|---------|---------|--------|---------|
| 股票名稱載入 | ~10秒 | ~0.5秒 | **95%↓** |
| 頁面初始化 | ~12秒 | ~2秒 | **83%↓** |
| 數據更新延遲 | 5-30秒 | <0.1秒 | **99%↓** (WebSocket) |

## 🎬 立即行動

**想現在優化嗎？我可以幫您：**
1. ✅ 創建批量查詢API（後端）
2. ✅ 優化前端查詢邏輯
3. ✅ 添加localStorage緩存
4. ❓ 實施WebSocket（較複雜，後續再做）

請告訴我要執行哪個方案！
