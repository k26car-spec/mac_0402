# 🚀 v3.0 服務啟動指南

## 方法一：使用一鍵啟動腳本（推薦）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_api_v3.sh
```

**功能**：
- ✅ 自動檢查虛擬環境
- ✅ 自動安裝依賴
- ✅ 自動啟動服務
- ✅ 顯示訪問地址

---

## 方法二：手動步驟（逐步執行）

### Step 1: 進入目錄
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
```

### Step 2: 創建虛擬環境（首次使用）
```bash
python3 -m venv venv
```

### Step 3: 啟動虛擬環境
```bash
source venv/bin/activate
```

### Step 4: 安裝依賴（首次使用）
```bash
# 最小安裝（快速測試）
pip install fastapi uvicorn[standard] websockets

# 或完整安裝（所有功能）
pip install -r requirements-v3.txt
```

### Step 5: 啟動服務
```bash
python app/main.py
```

---

## 方法三：使用 uvicorn 直接啟動

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**參數說明**：
- `--reload`: 自動重載（代碼修改後自動重啟）
- `--host 0.0.0.0`: 允許外部訪問
- `--port 8000`: 指定端口

---

## 訪問服務

### 服務啟動後，訪問：

| 功能 | URL |
|------|-----|
| API 首頁 | http://127.0.0.1:8000 |
| **API 文檔** | **http://127.0.0.1:8000/api/docs** ⭐ |
| 健康檢查 | http://127.0.0.1:8000/health |
| WebSocket 測試 | ws://127.0.0.1:8000/ws/test |

---

## 測試 WebSocket

### 使用 wscat (需要安裝)
```bash
# 安裝 wscat
npm install -g wscat

# 連接 WebSocket
wscat -c ws://127.0.0.1:8000/ws/test

# 發送測試消息
> hello
```

### 使用 Python 測試
```python
import asyncio
import websockets

async def test_ws():
    uri = "ws://127.0.0.1:8000/ws/test"
    async with websockets.connect(uri) as ws:
        # 接收連接消息
        response = await ws.recv()
        print(f"收到: {response}")
        
        # 發送測試消息
        await ws.send("Hello Server")
        
        # 接收回應
        response = await ws.recv()
        print(f"收到: {response}")

asyncio.run(test_ws())
```

---

## 停止服務

### 方法 1: 終端中按
```
Ctrl + C
```

### 方法 2: 查找並終止進程
```bash
# 查找進程
ps aux | grep "uvicorn\|python app/main.py"

# 終止進程
kill <PID>
```

---

## 常見問題

### Q1: 提示 "No module named 'fastapi'"
```bash
# 確認虛擬環境已啟動（命令行前應有 (venv)）
source venv/bin/activate

# 安裝依賴
pip install fastapi uvicorn
```

### Q2: 端口 8000 已被占用
```bash
# 查看占用端口的進程
lsof -i :8000

# 終止該進程或使用其他端口
uvicorn app.main:app --port 8001
```

### Q3: 虛擬環境無法啟動
```bash
# 刪除舊環境
rm -rf venv

# 重新創建
python3 -m venv venv
source venv/bin/activate
```

---

## 同時運行 v2.0 和 v3.0

### Terminal 1: v2.0 Dashboard
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./restart_dashboard.sh
# v2.0 運行在 http://127.0.0.1:8082
```

### Terminal 2: v3.0 API
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_api_v3.sh
# v3.0 運行在 http://127.0.0.1:8000
```

**兩者可以同時運行，互不干擾！** ✅

---

## 下一步

啟動成功後：

1. **訪問 API 文檔**
   ```
   http://127.0.0.1:8000/api/docs
   ```

2. **測試健康檢查**
   ```bash
   curl http://127.0.0.1:8000/health
   ```

3. **查看日誌**
   - 終端會顯示請求日誌
   - 按 Ctrl+C 停止服務

4. **開始開發**
   - 修改 `app/main.py` 會自動重載
   - 添加新的 API 端點
   - 開發 v3.0 專家系統

---

**準備好啟動了嗎？執行：** `./start_api_v3.sh`
