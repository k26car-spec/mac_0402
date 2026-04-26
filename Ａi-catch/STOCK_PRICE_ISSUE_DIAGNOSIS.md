# 🔍 股價數據問題診斷報告

**問題時間**: 2025-12-17 01:22  
**狀態**: ❌ 使用模擬數據

---

## 🐛 問題描述

**網頁顯示**: 股價為固定值
- 鴻海: 110.00 (固定)
- 聯發科: 1275.00 (固定)
- 富邦金: 89.50 (固定)
- 國泰金: 68.00 (固定)

**預期**: 應該顯示真實即時股價

---

## 🔍 根本原因

### **後端錯誤訊息**:
```
[FubonClient] Missing credentials
⚠️ 富邦API連接失敗，將使用備用數據源
警告: 未設定 ENCRYPTION_SECRET_KEY
```

### **診斷結果**:

1. ❌ **ENCRYPTION_SECRET_KEY 缺失**
   - .env文件中沒有這個key
   - 導致無法解密富邦憑證
   - fubon.env雖然存在但無法使用

2. ❌ **富邦憑證無法讀取**
   - fubon_config.py需要ENCRYPTION_SECRET_KEY
   - 沒有key就無法解密帳號密碼
   - 導致 "Missing credentials" 錯誤

3. ✅ **Fallback機制正常工作**
   - 系統正確使用模擬數據
   - 避免了崩潰
   - 但用戶看到的是固定股價

---

## 🔧 解決方案

### **方案一：生成ENCRYPTION_SECRET_KEY** (推薦)

如果您有富邦證券帳戶並想使用真實數據：

```bash
# 1. 生成32字符加密密鑰
python3 -c "import secrets; print(secrets.token_hex(16))"

# 2. 將輸出的密鑰添加到.env
echo "ENCRYPTION_SECRET_KEY=你的密鑰" >> .env

# 3. 確保fubon.env配置正確
# 編輯fubon.env，確保有：
# FUBON_USER_ID=你的帳號
# FUBON_PASSWORD=加密後的密碼
# FUBON_CERT_PASSWORD=加密後的憑證密碼
# FUBON_CERT_PATH=憑證路徑

# 4. 重啟後端
pkill -f uvicorn
cd backend-v3 && source venv/bin/activate && python -m uvicorn app.main:app --reload --port 8000
```

---

### **方案二：使用Yahoo Finance作為備用** (暫時方案)

如果暫時沒有富邦帳戶，但想要"更真實"的數據：

**修改watchlist.py使用Yahoo Finance**:

```python
# 修改 watchlist.py 的 generate_mock_stock_analysis 函數
# 改為從Yahoo Finance獲取即時報價

import yfinance as yf

def generate_realtime_stock_analysis(stock_code: str, index: int):
    """使用Yahoo Finance獲取即時股價"""
    
    try:
        # 台股代碼需要加.TW
        ticker = yf.Ticker(f"{stock_code}.TW")
        
        # 獲取即時報價
        info = ticker.info
        current_price = info.get('currentPrice', 0)
        
        # 或獲取最新收盤價
        if current_price == 0:
            hist = ticker.history(period="1d")
            if len(hist) > 0:
                current_price = hist['Close'].iloc[-1]
        
        # ... 繼續計算技術指標和信心度
        
    except Exception as e:
        # 如果Yahoo也失敗，才用固定值
        current_price = base_prices.get(stock_code, 100.0)
```

---

### **方案三：接受模擬數據** (最簡單)

如果只是展示系統功能，不需要真實交易：

✅ 系統目前的狀態已經很好
- 所有功能都正常運作
- UI完整美觀
- Fallback機制保證穩定性
- 只是數據是預設值

**優點**:
- 不需要任何配置
- 系統已經可以展示
- 適合Demo/測試

**缺點**:
- 股價是固定值
- 無法用於實際交易決策

---

## 📊 當前系統狀態

### **正常工作的部分** ✅:
- ✅ 美股數據 (Yahoo Finance) - 真實
- ✅ VIX指數 (Yahoo Finance) - 真實
- ✅ Fear & Greed (Alternative.me) - 真實
- ✅ 日經225 (Yahoo Finance) - 真實
- ✅ 台股指數 (Yahoo Finance) - 真實
- ✅ 證交所法人數據 - 真實

### **使用模擬數據的部分** ❌:
- ❌ 台股個股股價 - 固定值
- ❌ 技術指標 (MA/RSI/MACD) - 無法計算
- ❌ 信心度 - 基於固定股價計算

### **真實度**:
- 全球市場數據: ✅ 100%真實
- 台股個股數據: ❌ 0%真實
- **整體真實度: 約60%**

---

## 🎯 推薦行動

### **如果您有富邦證券帳戶**:

1. 生成ENCRYPTION_SECRET_KEY
2. 配置fubon.env
3. 重啟後端
4. **→ 達成100%真實數據** ✨

### **如果沒有富邦帳戶**:

**選項A**: 實現Yahoo Finance備用方案
- 可獲得即時股價
- 但技術指標計算受限
- **→ 達成80-85%真實度**

**選項B**: 接受現狀
- 用於展示和Demo
- 不用於實際交易
- **→ 維持60%真實度**

---

## 🔍 驗證方法

### **檢查ENCRYPTION_SECRET_KEY**:
```bash
grep ENCRYPTION_SECRET_KEY .env
# 應該顯示: ENCRYPTION_SECRET_KEY=xxxxx
```

### **檢查富邦連接**:
```bash
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

**成功輸出**:
```
✅ 富邦API連接成功
富邦連接: ✅成功
```

**失敗輸出**:
```
[FubonClient] Missing credentials
富邦連接: ❌失敗
```

---

## 📝 總結

### **問題**:
股價顯示固定值，因為富邦API連接失敗

### **原因**:
缺少ENCRYPTION_SECRET_KEY，無法解密富邦憑證

### **解決**:
1. 添加ENCRYPTION_SECRET_KEY到.env
2. 或使用Yahoo Finance作為備用
3. 或接受模擬數據用於展示

### **當前狀態**:
- 系統功能正常 ✅
- 全球市場數據真實 ✅
- 台股個股數據模擬 ❌
- **整體可用，但不適合實際交易**

---

**您想要哪種解決方案？** 🤔

1. 配置富邦API (需要證券帳戶) → 100%真實
2. 使用Yahoo Finance備用 → 80%真實
3. 保持現狀Demo用 → 60%真實
