# 🚀 富邦 Neo SDK 整合指南

## 📍 發現

在 `/Users/Mac/Documents/ETF/AI/` 發現了**完整的富邦 Neo SDK 實作**！

---

## ✅ 已找到的資源

### 1. 富邦 Neo SDK
- **檔案**: `fubon_neo-2.2.5-cp37-abi3-macosx_10_12_x86_64.whl`
- **大小**: 2.7 MB
- **版本**: 2.2.5
- **狀態**: ✅ 可用

### 2. 專業級客戶端
- **檔案**: `fubon_client.py`
- **功能**:
  - ✅ SDK 初始化
  - ✅ 帳號登入（加密）
  - ✅ 即時報價 `get_quote()`
  - ✅ 歷史K線 `get_candles()`
  - ✅ 自動重連

### 3. 配置系統
- **檔案**: `config.py`
- **功能**:
  - ✅ 加密憑證管理
  - ✅ AES-256-GCM 加密
  - ✅ 從 .env 讀取配置

### 4. 憑證檔案
- **檔案**: `N123715042.pfx`
- **用途**: 富邦 API 憑證

---

## 🔧 整合步驟

### 步驟 1: 安裝富邦 SDK

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 啟動虛擬環境
source venv/bin/activate

# 安裝富邦 Neo SDK
pip install /Users/Mac/Documents/ETF/AI/fubon_neo-2.2.5-cp37-abi3-macosx_10_12_x86_64.whl
```

### 步驟 2: 複製必要檔案

```bash
# 複製富邦客戶端
cp /Users/Mac/Documents/ETF/AI/fubon_client.py .

# 複製配置管理
cp /Users/Mac/Documents/ETF/AI/config.py ./fubon_config.py

# 複製憑證（如果需要）
cp /Users/Mac/Documents/ETF/AI/N123715042.pfx .
cp /Users/Mac/Documents/ETF/AI/.env ./fubon.env
```

### 步驟 3: 更新 requirements.txt

```txt
# 新增依賴
pydantic-settings>=2.0.0
cryptography>=41.0.0
```

### 步驟 4: 創建富邦數據源

創建 `fubon_data_source.py`:

```python
from fubon_client import fubon_client
import asyncio

async def get_stock_data(symbol: str):
    """使用富邦 API 獲取股票資料"""
    # 連接
    if not fubon_client.is_connected:
        await fubon_client.connect()
    
    # 獲取報價
    quote = await fubon_client.get_quote(symbol)
    
    if quote:
        return {
            'code': symbol,
            'name': quote['name'],
            'price': quote['closePrice'],
            'change': quote['change'],
            'changePercent': quote['changePercent'],
            'volume': quote['volume']
        }
    
    return None

async def search_stock_by_name(keyword: str):
    """搜尋股票（使用富邦 API）"""
    # 富邦 SDK 提供的搜尋功能
    # 實作搜尋邏輯
    pass
```

---

## 📊 實際功能

### 可用的 API 方法

#### 1. 即時報價
```python
quote = await fubon_client.get_quote('2330')
# 返回:
{
    "symbol": "2330",
    "name": "台積電",
    "openPrice": 580.0,
    "highPrice": 585.0,
    "lowPrice": 578.0,
    "closePrice": 582.0,
    "change": 2.0,
    "changePercent": 0.34,
    "volume": 28500
}
```

#### 2. 歷史K線
```python
candles = await fubon_client.get_candles(
    symbol='2330',
    from_date='2024-01-01',
    to_date='2024-12-15',
    timeframe='D'  # D=日線, W=週線, M=月線
)
```

---

## 🎯 整合到 AI-catch

### 更新 async_crawler.py

將數據源從 Yahoo Finance 切換到富邦 API:

```python
# 在 async_crawler.py 中
from fubon_data_source import get_stock_data

async def fetch_stock_data(stock_code: str):
    """使用富邦 API 獲取數據"""
    
    # 方法1: 富邦 API（優先）
    try:
        data = await get_stock_data(stock_code)
        if data:
            return data
    except Exception as e:
        logger.warning(f"富邦 API 失敗: {e}")
    
    # 方法2: Yahoo Finance（備用）
    return await fetch_from_yahoo(stock_code)
```

---

## 🔐 安全配置

### .env 檔案設定

```env
# 富邦 API 憑證（加密）
FUBON_USER_ID_ENCRYPTED=<加密後的帳號>
FUBON_PASSWORD_ENCRYPTED=<加密後的密碼>
FUBON_CERT_PATH=/path/to/N123715042.pfx
FUBON_CERT_PASSWORD_ENCRYPTED=<加密後的憑證密碼>
ENCRYPTION_SECRET_KEY=<加密金鑰>

# 是否使用富邦 API
USE_FUBON_API=true
```

---

## 💡 優勢

### 使用富邦 Neo SDK 的好處

1. ✅ **官方 SDK** - 穩定可靠
2. ✅ **即時數據** - 毫秒級更新
3. ✅ **完整資訊** - 五檔、成交明細、K線
4. ✅ **專業級** - 證券商等級的數據
5. ✅ **已實作** - 現成的客戶端代碼

### vs Yahoo Finance

| 功能 | 富邦 SDK | Yahoo Finance |
|------|---------|---------------|
| 資料即時性 | ✅ 毫秒級 | ❌ 延遲15分鐘 |
| 五檔明細 | ✅ 有 | ❌ 無 |
| 成交明細 | ✅ 有 | ❌ 無 |
| 股票名稱 | ✅ 正確 | ⚠️ 有時缺失 |
| 穩定性 | ✅ 高 | ⚠️ 中等 |
| 需要帳號 | ⚠️ 需要 | ✅ 不需要 |

---

## 🚀 下一步

### 立即可做

1. **安裝 SDK** - 5 分鐘
2. **測試連接** - 5 分鐘
3. **整合到爬蟲** - 30 分鐘

### 完整整合

1. **數據源切換** - 將所有數據源改為富邦
2. **搜尋功能** - 使用富邦搜尋 API
3. **即時更新** - WebSocket 即時推送

---

## 📝 注意事項

1. **帳號需求** - 需要富邦證券帳號
2. **憑證管理** - 需要妥善保管 .pfx 憑證
3. **加密安全** - 使用 AES-256 加密保護憑證
4. **連線管理** - SDK 會自動管理連線

---

## 🎉 總結

您已經擁有：
- ✅ 富邦 Neo SDK（2.7 MB）
- ✅ 專業級客戶端代碼
- ✅ 完整的加密系統
- ✅ 憑證檔案

**建議：** 優先整合富邦 SDK，可以大幅提升數據品質和即時性！

---

**檔案位置:**
- SDK: `/Users/Mac/Documents/ETF/AI/fubon_neo-2.2.5-cp37-abi3-macosx_10_12_x86_64.whl`
- 客戶端: `/Users/Mac/Documents/ETF/AI/fubon_client.py`
- 配置: `/Users/Mac/Documents/ETF/AI/config.py`
- 憑證: `/Users/Mac/Documents/ETF/AI/N123715042.pfx`
