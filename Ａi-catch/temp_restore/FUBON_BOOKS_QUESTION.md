# 富邦 API 五檔掛單訂閱問題 - 技術諮詢

## 📋 問題摘要

使用富邦 Python SDK 訂閱五檔掛單 (books channel) 時，WebSocket 連接成功並收到訂閱確認，但**無法接收到實際的五檔數據**。

---

## 🖥️ 環境資訊

| 項目 | 版本/資訊 |
|------|----------|
| Python | 3.11 |
| 作業系統 | macOS |
| 富邦 SDK | fubon-neo (最新版) |
| 測試時間 | 2025-12-19 盤中 (09:00-13:30) |
| 測試股票 | 2330 台積電 |

---

## ✅ 成功的部分

1. **SDK 登入成功** - 使用憑證檔案 (.pfx) 成功登入
2. **REST API 報價成功** - `sdk.marketdata.rest_client` 可正常取得即時報價
3. **WebSocket 連接成功** - 收到 `{"event":"authenticated","data":{"message":"Authenticated successfully"}}`
4. **訂閱請求成功** - 收到 `{"event":"subscribed","data":{"channel":"books","symbol":"2330"}}`
5. **心跳正常** - 收到 `{"event":"heartbeat",...}`

---

## ❌ 失敗的部分

訂閱五檔後，**只收到 heartbeat，沒有收到任何五檔數據**。

### 我的訂閱程式碼：

```python
from fubon_neo.sdk import FubonSDK

# 初始化並登入
sdk = FubonSDK()
accounts = sdk.login(
    identity='YOUR_ID',
    password='YOUR_PASSWORD',
    cert_path='/path/to/cert.pfx',
    cert_password='CERT_PASSWORD'
)

# 取得 WebSocket 客戶端
ws_client = sdk.marketdata.websocket_client.stock

# 設定事件處理器
def on_books(data):
    print(f"收到五檔數據: {data}")

# 註冊事件
ws_client.on("books", on_books)

# 連接並訂閱
ws_client.connect()
ws_client.subscribe({"channel": "books", "symbol": "2330"})

# 等待數據...
import time
time.sleep(15)

# 結果：on_books 從未被呼叫
```

### 我收到的 WebSocket 訊息：

```
2025-12-19 09:50:00 - WebSocket connected
2025-12-19 09:50:00 - 收到: {"event":"authenticated","data":{"message":"Authenticated successfully"}}
2025-12-19 09:50:00 - 收到: {"event":"pong","data":{"time":1765874982338823,"state":""}}
2025-12-19 09:50:01 - 訂閱請求已發出
2025-12-19 09:50:01 - 收到: {"event":"subscribed","data":{"id":"...","channel":"books","symbol":"2330"}}
2025-12-19 09:50:05 - 收到: {"event":"heartbeat","data":{"time":1765874991275356}}
2025-12-19 09:50:10 - 已等待 10 秒...
2025-12-19 09:50:15 - 已等待 15 秒...
# ⚠️ 從未收到 books 事件的數據
```

---

## ❓ 我的問題

1. **五檔訂閱的正確方式是什麼？**
   - 訂閱參數是否正確？ `{"channel": "books", "symbol": "2330"}`
   - 是否需要額外的參數或設定？

2. **五檔數據的回調格式是什麼？**
   - 事件名稱是 `"books"` 還是其他？
   - 數據結構長什麼樣子？

3. **是否需要特定權限？**
   - 我的帳戶是否有訂閱五檔數據的權限？
   - 是否需要在合約中啟用特定功能？

4. **有沒有完整的五檔訂閱範例程式碼？**

---

## 📝 補充說明

- 使用 REST API 的 `snapshot.quotes()` 可以取得**買一價/賣一價**，但無法取得完整五檔
- 參考您之前提供的測試截圖，似乎也是只收到 subscribed 和 heartbeat，沒有實際數據

---

## 🙏 期望獲得的協助

1. 確認五檔訂閱的正確程式碼
2. 提供五檔數據的回調事件名稱和數據格式
3. 確認帳戶權限是否足夠
4. 如有可能，提供一個可運行的範例程式碼

---

**聯絡資訊：**
- 日期：2025-12-19
- 帳號：[您的富邦帳號]

感謝您的協助！
