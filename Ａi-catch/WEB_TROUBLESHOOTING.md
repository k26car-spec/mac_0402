# 🔧 Web 平台啟動指南（最終版）

## ⚠️ 如果看到 {"detail":"Not Found"}

這表示有其他程式占用了 8080 端口！

---

## ✅ 解決方案：使用重啟腳本

### 方法 1: 使用重啟腳本（最簡單）

```bash
./restart_dashboard.sh
```

這個腳本會：
1. ✅ 停止所有相關進程
2. ✅ 釋放 8080 端口
3. ✅ 確認端口可用
4. ✅ 啟動 Web 平台

### 方法 2: 手動操作

```bash
# 1. 停止所有進程
pkill -f dashboard.py

# 2. 檢查並釋放端口
lsof -ti:8080 | xargs kill -9

# 3. 等待 2 秒
sleep 2

# 4. 啟動平台
./start_dashboard.sh
```

---

## 🎯 正確的啟動流程

### 步驟 1: 清理環境

```bash
./restart_dashboard.sh
```

### 步驟 2: 訪問網頁

打開瀏覽器，訪問：

## **http://127.0.0.1:8080**

### 步驟 3: 確認成功

您應該看到：
```
┌──────────────────────────────┐
│  🤖 AI主力監控平台            │
│  ⏰ 時間顯示                  │
│  🟢/🔴 系統狀態               │
└──────────────────────────────┘

[統計卡片區域]
[控制按鈕]
[監控清單]
[警示記錄]
```

---

## 🐛 仍然有問題？

### 檢查1: 確認是否真的啟動

```bash
ps aux | grep dashboard.py
```

應該看到類似：
```
Mac  12345  ... python3 dashboard.py
```

### 檢查2: 確認端口

```bash
lsof -i :8080
```

應該看到：
```
COMMAND   PID USER   FD   TYPE ...
Python  12345  Mac    3u  IPv4 ...
```

### 檢查3: 測試連接

```bash
curl http://127.0.0.1:8080/test
```

如果看到 `{"detail":"Not Found"}`，表示有其他程式佔用端口。

---

## 💡 替代端口方案

如果 8080 持續被占用，改用其他端口：

### 編輯 dashboard.py

最後一行改為：

```python
app.run(host='0.0.0.0', port=9000, debug=True)
```

然後訪問：`http://127.0.0.1:9000`

---

## 📱 完整命令參考

```bash
# 完全重啟（推薦）
./restart_dashboard.sh

# 一般啟動
./start_dashboard.sh

# 背景啟動
./start_dashboard_daemon.sh

# 停止
./stop_dashboard.sh
# 或 Ctrl+C

# 查看進程
ps | grep dashboard

# 查看端口
lsof -i :8080

# 強制停止
pkill -9 -f dashboard.py

# 測試
curl http://127.0.0.1:8080
```

---

## ✅ 快速測試

使用簡化版測試：

```bash
# 1. 停止所有
pkill -f dashboard.py

# 2. 運行測試
python3 test_flask.py

# 3. 訪問測試頁面
# http://127.0.0.1:8080/test
# 應該看到: "Flask is working!"

# 4. Ctrl+C 停止
# 5. 運行實際平台
./restart_dashboard.sh
```

---

## 🎉 成功標誌

當您訪問 http://127.0.0.1:8080 時，應該看到：

✅ **正確**：漂亮的儀表板頁面
❌ **錯誤**：`{"detail":"Not Found"}`
❌ **錯誤**：「無法連接」
❌ **錯誤**：空白頁面

---

## 📞 最後的建議

如果所有方法都試過還是不行：

1. **重新安裝 Flask**
   ```bash
   pip3 uninstall flask
   pip3 install flask
   ```

2. **使用不同端口**
   - 編輯 dashboard.py 使用 9000 或 3000

3. **檢查防火牆**
   - 確認沒有阻擋本機連接

4. **重啟電腦**
   - 釋放所有端口和資源

---

**使用 `./restart_dashboard.sh` 啟動，確保成功！** ✅
