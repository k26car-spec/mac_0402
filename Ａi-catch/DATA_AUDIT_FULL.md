# 系統數據來源完整檢查 - 2025-12-17 00:18

## 🔍 富邦SDK安裝狀態

✅ **已安裝並可用**
- venv已重建 with --system-site-packages
- fubon-neo模塊可導入
- FubonSDK類可用

---

## ⚠️ 但是...仍有大量模擬數據！

### 原因：**代碼沒有實際調用富邦API**

---

## 📊 數據來源詳細檢查

### 1. **監控清單精選分析** ❌ 100%模擬

**文件**: `backend-v3/app/api/watchlist.py`

**問題**:
- ❌ **完全沒有調用富邦API**
- ❌ 使用固定價格字典 (line 80-100)
- ❌ 信心度用公式計算 (line 93)
- ❌ 技術分析是模板文字 (line 100-115)

**證據**:
```python
# watchlist.py line 79-90
base_prices = {
    "2330": 1035.0,   # 固定值！！！
    "2317": 110.0,    # 固定值！！！
    ...
}

# line 93
confidence = 0.85 - (index * 0.05)  # 簡單公式！！！
```

**應該要**:
```python
# 應該調用富邦API
from app.services import fubon_service
indicators = await fubon_service.get_technical_indicators(stock_code)
current_price = indicators['current_price']  # 真實報價
```

---

### 2. **美股影響分析** ✅ 70%真實

**文件**: `backend-v3/app/api/premarket.py` line 147-204

**狀態**:
- ✅ NASDAQ, 道瓊, S&P500 - Yahoo Finance **真實**
- ✅ 輝達, 蘋果, AMD - Yahoo Finance **真實**
- ✅ VIX恐慌指數 - Yahoo Finance **真實**
- ❌ Fear & Greed Index - TODO待整合 (line 217)
- ❌ 台指期夜盤 - TODO待整合 (line 218)
- ❌ 日經期貨 - TODO待整合 (line 219)

**代碼**:
```python
# line 151-154
from app.services import yahoo_service
us_data = await yahoo_service.get_us_market_data()  # ✅ 真實
```

---

### 3. **法人同步買超** ❌ 100%模擬

**文件**: `backend-v3/app/api/premarket.py` line 234-267

**問題**:
- ❌ **完全是固定值**
- ❌ 沒有調用證交所API
- ❌ 外資買超固定15000張 (line 241)

**證據**:
```python
# line 237-245
institutional_data = [
    {
        "stock_id": "2330",
        "foreign_net_buy": 15000,  # 固定！！！
        "trust_net_buy": 2000,     # 固定！！！
        ...
    }
]
```

**但是已經有API可用**:
```python
# real_data_service.py line 244-307
# ✅ TWStockExchangeService 已實現！
class TWStockExchangeService:
    async def get_institutional_trades(self, date=None):
        # 連接證交所API獲取真實數據
        url = f"https://www.twse.com.tw/fund/T86?..."
```

---

### 4. **技術面篩選** ⚠️ 部分真實

**文件**: `backend-v3/app/api/premarket.py` line 441-516

**狀態**:
- ⚠️ 有調用富邦API的代碼 (line 467)
- ⚠️ 但有fallback機制
- ⚠️ 如果富邦連接失敗會用模擬數據

**代碼**:
```python
# line 467-469
from app.services import fubon_service
technical_data = await fubon_service.batch_get_technical_indicators(...)
# ✅ 這個有在用！但可能失敗
```

---

## 🔧 缺少的配置

### 1. **富邦憑證配置** ⚠️ 需檢查

**文件**: `fubon.env`

需要包含：
```env
FUBON_USER_ID=您的富邦帳號
FUBON_PASSWORD=加密後的密碼
FUBON_CERT_PASSWORD=加密後的憑證密碼
FUBON_CERT_PATH=/path/to/cert.pfx
```

### 2. **加密密鑰** ⚠️ 需檢查

**文件**: `.env`

需要包含：
```env
ENCRYPTION_SECRET_KEY=your-32-character-encryption-key
```

---

## 📝 需要修正的代碼

### **優先級1: 監控清單精選** (最重要)

**文件**: `backend-v3/app/api/watchlist.py`

**需要修改**: 
- line 40-41: 改為調用富邦API
- line 80-100: 移除固定價格字典
- line 93-94: 改為真實技術分析計算信心度

### **優先級2: 法人買賣超**

**文件**: `backend-v3/app/api/premarket.py`

**需要修改**:
- line 234-267: 改為調用證交所API
- 使用 `twse_service.get_institutional_trades()`

### **優先級3: 其他指標**

- Fear & Greed Index (需找API)
- 台指期夜盤 (需整合)
- 日經期貨 (需整合)

---

## 🎯 總結

### **目前真實的數據** (約30%):

1. ✅ 美股主要指數 (Yahoo Finance)
2. ✅ 美股科技個股 (Yahoo Finance)
3. ✅ VIX恐慌指數 (Yahoo Finance)
4. ✅ 時間計算功能
5. ⚠️ 技術面篩選 (有代碼，需測試是否啟用)

### **仍然模擬的數據** (約70%):

1. ❌ **監控清單股價** - 完全固定
2. ❌ **監控清單信心度** - 公式計算
3. ❌ **技術分析原因** - 模板文字
4. ❌ **法人買賣超** - 固定數據
5. ❌ **進場/停損/目標價** - 基於假股價

### **SDK已安裝但未啟用** :

- ✅ fubon-neo: 已安裝，可導入
- ❌ 但 watchlist.py 沒有調用
- ❌ 需要修改代碼才能使用

---

## 💡 立即行動項

### **快速測試** (1分鐘):

```bash
# 測試富邦連接
cd backend-v3
source venv/bin/activate
python -c "
import asyncio
from app.services.real_data_service import fubon_service

async def test():
    success = await fubon_service.initialize()
    print(f'富邦連接: {\"✅成功\" if success else \"❌失敗\"}')
    
asyncio.run(test())
"
```

### **修正代碼** (10分鐘):

需要修改 `watchlist.py` 的 `generate_stock_analysis` 函數，改為：

1. 調用富邦API獲取真實股價
2. 調用富邦API獲取技術指標
3. 基於真實指標計算信心度

---

**結論**: 
- ✅ SDK已安裝
- ❌ 但代碼還沒改為使用它
- ❌ 大約70%仍是模擬數據
- 🔧 需要修改代碼才能啟用真實數據

*下一步: 修改watchlist.py和premarket.py使用真實API*
