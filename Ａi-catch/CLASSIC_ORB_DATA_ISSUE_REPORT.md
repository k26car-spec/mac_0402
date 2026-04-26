# 經典版 ORB 系統數據讀取問題 - 診斷報告

**時間**: 2026-02-12 18:15  
**問題**: `http://localhost:5173/` 經典版無法讀到資料

---

## 🔍 問題診斷

### 系統狀態檢查
- ✅ **ORB 前端** (port 5173): 正常運行 (PID: 21777)
- ✅ **Backend API** (port 8000): 正常運行 (PID: 26870)
- ❌ **API 調用**: 超時 (10+ 秒無響應)

### 問題重現
```bash
curl "http://localhost:8000/api/smart-entry/score/2330"
# 結果: 超時，無響應
```

### 根本原因
**收盤後數據抓取超時問題**

1. **時間因素**: 當前時間 18:15（台股收盤後）
2. **數據源問題**: yfinance 在收盤後抓取即時數據（1分鐘K線）會超時
3. **API 阻塞**: `/api/smart-entry/score` 需要抓取 intraday 數據：
   ```python
   intraday = ticker.history(period="1d", interval="1m")
   ```

### 影響範圍
經典版 ORB 系統調用的所有 API 都可能受影響：
- `/api/smart-entry/score/{stock_code}` - **主要問題**
- `/api/smart-entry/bollinger/{stock_code}`
- `/api/big-order/quote/{stock_code}`
- `/api/smart-entry/support-resistance/{stock_code}`

---

## 💡 解決方案

### 方案 A：重啟後端（臨時）⭐ 推薦

後端可能有殘留的超時連接，重啟可以清理：

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./restart_backend_quick.sh
```

**優點**: 立即見效  
**缺點**: 治標不治本

---

### 方案 B：修改 API 增加超時處理（根治）

修改 `backend-v3/app/api/smart_entry.py` 的 `get_entry_score` 函數：

```python
# 在獲取 intraday 數據時添加超時處理
try:
    intraday = ticker.history(period="1d", interval="1m")
except Exception as e:
    logger.warning(f"無法獲取 {stock_code} 即時數據: {e}")
    intraday = pd.DataFrame()  # 空 DataFrame
```

**同時修改 ORB 評分邏輯**：
```python
# 1. ORB 開盤區間突破 (20%)
if not intraday.empty and len(intraday) >= 15:
    # ... 原邏輯 ...
else:
    orb_score = 50
    factors["orb"] = {
        "score": 50,
        "weight": 0.20,
        "status": "收盤後無法判斷",
        "note": "請在交易時段使用"
    }
```

---

### 方案 C：前端增加 Loading 和錯誤處理

修改 `day-trading-orb/src/App.jsx`：

```javascript
const fetchStockData = useCallback(async (stockCode) => {
  setLoading(true);
  setError(null);
  
  try {
    // 設定 5 秒超時
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    
    const promises = [
      fetch(`${API_BASE}/api/smart-entry/score/${stockCode}`, { 
        signal: controller.signal 
      }),
      // ...
    ];
    
    const results = await Promise.allSettled(promises);
    clearTimeout(timeout);
    
    // 處理結果...
  } catch (error) {
    if (error.name === 'AbortError') {
      setError('資料載入超時，請稍後再試（建議在交易時段使用）');
    } else {
      setError(`載入失敗: ${error.message}`);
    }
  } finally {
    setLoading(false);
  }
}, []);
```

---

## 🚀 立即行動方案

### Step 1: 重啟後端（現在就做）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./restart_backend_quick.sh
```

等待 10 秒後測試：
```bash
curl -m 5 "http://localhost:8000/api/smart-entry/watchlist"
```

### Step 2: 刷新經典版頁面

```
http://localhost:5173/
```

### Step 3: 測試輸入股票代碼

輸入 `2330` 或任何監控股票

---

## 📊 預期結果

### 重啟後的行為

**交易時段 (09:00-13:30)**:
- ✅ 正常讀取數據
- ✅ 即時分析有效

**收盤後 (13:30 之後)**:
- ⚠️ 可能仍會超時（除非做方案 B）
- 💡 建議顯示：「請在交易時段使用」

---

## 🔧 長期優化建議

1. **數據緩存**: 使用 Redis 緩存收盤數據
2. **超時處理**: 所有 yfinance 調用都加上 timeout
3. **優雅降級**: 收盤後使用昨日收盤數據代替即時數據
4. **前端提示**: 顯示「交易時段」vs「收盤後」模式

---

## 📝 相關文件

- API 文件: `/backend-v3/app/api/smart_entry.py`
- 前端文件: `/day-trading-orb/src/App.jsx`
- 啟動腳本: `/start_backend.sh`

---

**建議優先級**: 
1. 🔴 **立即**: 重啟後端（方案 A）
2. 🟡 **短期**: 添加前端超時處理（方案 C）
3. 🟢 **長期**: 修改 API 邏輯（方案 B）

---

**文檔版本**: v1.0  
**最後更新**: 2026-02-12 18:15  
**狀態**: 🔍 已診斷，待修復
