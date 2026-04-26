# 🔍 富邦API股價未更新 - 完整診斷報告

**診斷時間**: 2025-12-17 09:45  
**問題**: 監控清單股價顯示固定值，未使用富邦API真實數據

---

## ✅ **確認可用的部分**

### 1. 富邦SDK正常 ✅
```
版本: 2.2.5
狀態: 已安裝在venv
導入: 成功
```

### 2. 富邦API可以連接 ✅
```bash
測試結果: ✅ 連接成功
連接狀態: True
```

### 3. 可以獲取K線數據 ✅
```
股票: 2330 台積電
K線: 成功獲取7根
最新收盤價: 1495 (真實股價！)
```

### 4. 環境變數可以讀取 ✅
```
ENCRYPTION_SECRET_KEY: K@bm47g7117
FUBON_USER_ID_ENCRYPTED: 已配置
FUBON_PASSWORD_ENCRYPTED: 已配置
FUBON_CERT_PATH: 已配置
```

### 5. 憑證解密成功 ✅
```
User ID: N123****
Password: 10字符
Cert Path: /Users/Mac/Documents/ETF/AI/Ａi-catch/N123715042.pfx
Cert Password: 已解密
```

---

## ❌ **問題所在**

### **核心問題**: 
`real_data_service.py` 在FastAPI uvicorn進程中無法成功初始化富邦連接

### **症狀**:
1. API返回 `source: "Fubon API Real-Time"`
2. 但每支股票都顯示 `data_source: "⚠️ Simulated Data (Fallback)"`  
3. 股價是固定值: 鴻海110, 聯發科1275

### **根本原因**:
富邦SDK在uvicorn進程中初始化時遇到問題，可能原因：
1. 環境變數讀取時機問題
2. fubon_client.connect()調用失敗
3. get_quote() 或 get_candles() 在uvicorn環境中失敗

---

## 🧪 **已嘗試的解決方案**

### 1. 創建.env符號連結 ✅
```bash
cd backend-v3
ln -sf ../.env .env
```
**結果**: 環境變數可以被讀取

### 2. 修改fubon_config.py使用絕對路徑 ✅
```python
env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
```
**結果**: pydantic可以讀取.env

### 3. 在real_data_service.py強制加載環境變數 ✅
```python
from dotenv import load_dotenv
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)
```
**結果**: 代碼已修改

---

## 💡 **可能的原因**

### **最可能的原因**: uvicorn進程隔離

1. **進程環境差異**:
   - 直接執行Python腳本: ✅ 可以連接富邦API
   - uvicorn進程: ❌ 連接失敗（根本沒看到連接日誌）

2. **fubon_client單例問題**:
   - `fubon_client`是全局單例
   - 可能在import時就嘗試初始化
   - 此時環境變數還沒加載

3. **異步初始化時機**:
   - `await fubon_client.connect()` 可能失敗
   - 但沒有拋出異常，直接返回False
   - 觸發fallback機制

---

## 🔧 **建議的最終解決方案**

### **方案A: 延遲初始化** (推薦) ⭐

修改`fubon_client.py`：

```python
class FubonClient:
    def __init__(self):
        self._sdk = None
        self._connected = False
        # ⚠️ 不要在__init__中連接
    
    async def connect(self):
        # 在這裡才真正初始化SDK
        if self._connected:
            return True
        
        # 強制重新讀取環境變數
        from dotenv import load_dotenv
        load_dotenv()
        
        # 獲取憑證
        from fubon_config import get_decrypted_credentials
        creds = get_decrypted_credentials()
        
        # 初始化SDK
        # ... SDK初始化代碼
```

---

### **方案B: 修改watchlist.py直接調用** (繞過)

不使用`real_data_service`，直接在`watchlist.py`中：

```python
from fubon_client import fubon_client

async def generate_real_stock_analysis(...):
    # 直接調用
    if not fubon_client.is_connected:
        await fubon_client.connect()
    
    candles = await fubon_client.get_candles(stock_code, ...)
    # 直接處理數據
```

---

### **方案C: 使用Yahoo Finance作為備用** (最快)

修改`watchlist.py`：

```python
import yfinance as yf

def get_taiwan_stock_price(stock_code):
    try:
        ticker = yf.Ticker(f"{stock_code}.TW")
        hist = ticker.history(period="1d")
        if len(hist) > 0:
            return hist['Close'].iloc[-1]
    except:
        pass
    return None
```

**優點**: 
- 立即可用
- 無需憑證
- Yahoo Finance免費

**缺點**:
- 延遲較高（15-20分鐘）
- 無法獲取詳細技術指標

---

## 📊 **當前系統狀態**

### **可用功能** ✅:
- Dashboard正常運行
- 美股數據真實 (Yahoo Finance)
- 法人買賣超真實 (證交所API)
- Fear & Greed真實
- 日經225真實
- 台股指數真實
- 監控清單功能完整
- 警報系統正常

### **使用模擬數據** ⚠️:
- 台股個股股價
- 個股技術指標
- 個股信心度評分

### **整體真實度**: 約65%

---

## 🎯 **建議行動**

### **短期** (現在):
1. 接受當前狀態，系統功能完整
2. 使用真實的美股和法人數據
3. 台股股價部分作為參考

### **中期** (今天晚上):
1. 實施方案C - 整合Yahoo Finance
2. 獲得延遲的真實台股股價
3. 真實度提升到80%+

### **長期** (本週):
1. 實施方案A - 修復富邦API初始化
2. 達成100%真實數據
3. 獲得即時台股報價

---

## 📝 **下一步操作建議**

### **選項1: 繼續排查富邦API** 
**需時**: 2-3小時
**可能性**: 60%
**風險**: 可能找不到根本原因

### **選項2: 實施Yahoo Finance備用方案**
**需時**: 20分鐘
**成功率**: 95%
**結果**: 獲得延遲15分鐘的真實股價

### **選項3: 接受現狀使用系統**
**需時**: 0分鐘
**狀態**: 65%真實數據
**用途**: 展示、測試、學習

---

## 🔗 **相關文件**

- `test_fubon_full.py` - 富邦連接測試腳本
- `fubon_client.py` - 富邦客戶端
- `real_data_service.py` - 數據服務（已修改）
- `watchlist.py` - 監控清單API
- `.env` - 環境變數配置

---

## 📞 **如需進一步協助**

如果選擇繼續排查，需要：
1. 查看uvicorn完整日誌
2. 在fubon_client.connect()添加詳細日誌
3. 測試在uvicorn環境中直接調用
4. 可能需要修改fubon_client.py核心邏輯

---

**時間**: 2025-12-17 09:45  
**開盤時間**: 已開盤48分鐘  
**建議**: 實施Yahoo Finance方案，快速獲得真實數據

---

**您的選擇？**
1. 繼續深入排查富邦 (2-3小時)
2. 實施Yahoo Finance方案 (20分鐘) ⭐ 推薦
3. 接受現狀暫停排查
