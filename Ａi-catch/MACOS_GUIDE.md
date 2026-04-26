# 🍎 macOS 使用注意事項

## ✅ 已修復的問題

### 問題：grep -P 不相容

**錯誤訊息**:
```
grep: invalid option -- P
```

**原因**: macOS 使用 BSD grep，不支援 GNU grep 的 `-P` (Perl regex) 選項。

**解決方案**: 
已修改 `start_monitor.sh` 使用 `sed` 代替 `grep -P`：

```bash
# 修改前（不相容）
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')

# 修改後（macOS 相容）  
python_version=$(python3 --version 2>&1 | sed -n 's/Python \([0-9]*\.[0-9]*\).*/\1/p')
```

---

## 🚀 macOS 上的使用方式

### 正常啟動流程

```bash
# 1. 進入專案目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 2. 確保腳本有執行權限
chmod +x start_monitor.sh stop_monitor.sh

# 3. 啟動系統
./start_monitor.sh

# 4. 選擇運行模式
# 1) 前台運行
# 2) 背景運行
# 3) 測試模式
```

---

## 💡 macOS 特定功能

### 使用 launchd 設定開機自動啟動

創建 `~/Library/LaunchAgents/com.ai-stock-monitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ai-stock-monitor</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/Mac/Documents/ETF/AI/Ａi-catch/start_monitor.sh</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/Mac/Documents/ETF/AI/Ａi-catch</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <false/>
    
    <key>StandardOutPath</key>
    <string>/Users/Mac/Documents/ETF/AI/Ａi-catch/logs/launchd.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/Mac/Documents/ETF/AI/Ａi-catch/logs/launchd.error.log</string>
</dict>
</plist>
```

載入服務：

```bash
launchctl load ~/Library/LaunchAgents/com.ai-stock-monitor.plist
```

---

## 🔧 macOS 特定設定

### Homebrew 安裝依賴（可選）

如果遇到編譯問題，可安裝額外依賴：

```bash
# 安裝 Homebrew (如果還沒安裝)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝可能需要的套件
brew install python@3.11
```

### 使用 GNU grep（可選）

如果需要 GNU grep：

```bash
brew install grep
# GNU grep 會安裝為 ggrep
```

---

## 🐛 macOS 常見問題

### Q: Python 版本檢查失敗？

**A**: 確認 Python 3 已安裝：

```bash
python3 --version
# 應該顯示 3.9 或更高版本
```

如果沒有，安裝 Python：

```bash
brew install python@3.11
```

### Q: pip 安裝失敗？

**A**: 更新 pip：

```bash
python3 -m pip install --upgrade pip
```

### Q: SSL 證書錯誤？

**A**: 安裝 certifi：

```bash
python3 -m pip install --upgrade certifi
```

或執行 Python 的憑證安裝腳本：

```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

### Q: 權限被拒絕？

**A**: 確保腳本有執行權限：

```bash
chmod +x start_monitor.sh
chmod +x stop_monitor.sh
```

### Q: 虛擬環境啟動失敗？

**A**: 手動建立虛擬環境：

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📊 效能建議

### macOS 上的記憶體管理

監控系統在 macOS 上的資源使用：

```bash
# 查看進程資源使用
ps aux | grep stock_monitor

# 監控系統資源
top -pid $(cat .monitor.pid)
```

### 設定資源限制

如需限制資源使用，編輯 `start_monitor.sh`：

```bash
# 在啟動命令前加入
ulimit -m 500000  # 限制記憶體為 500MB
ulimit -t 3600    # 限制 CPU 時間
```

---

## 🔐 macOS 安全性

### 系統完整性保護 (SIP)

如果遇到權限問題，可能需要：

1. 在「系統偏好設定」→「安全性與隱私權」中允許應用程式
2. 使用 `csrutil` 管理 SIP（不建議關閉）

### 防火牆設定

如果通知無法發送，檢查防火牆：

```bash
# 查看防火牆狀態
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 允許 Python 網路連線（如需要）
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/python3
```

---

## ✅ macOS 檢核清單

安裝前檢查：

- [ ] Python 3.9+ 已安裝
- [ ] pip 已更新
- [ ] 已設定環境變數 (.env)
- [ ] 已啟用所需通知管道
- [ ] 腳本有執行權限

運行中檢查：

- [ ] 虛擬環境已啟動
- [ ] 依賴套件已安裝
- [ ] 資料庫可寫入
- [ ] 日誌正常記錄
- [ ] 通知正常發送

---

## 🎯 macOS 最佳實踐

1. **使用虛擬環境**: 避免污染系統 Python
2. **定期更新**: `pip install --upgrade -r requirements.txt`
3. **監控日誌**: `tail -f logs/stock_monitor.log`
4. **備份數據**: 定期備份 `data/` 目錄
5. **使用launchd**: 而非 cron，更符合 macOS 慣例

---

## 📚 相關資源

- [macOS launchd 文檔](https://www.launchd.info/)
- [Homebrew 官網](https://brew.sh/)
- [Python macOS 安裝指南](https://www.python.org/downloads/macos/)

---

**最後更新**: 2024-12-11  
**macOS 版本支援**: macOS 10.15 (Catalina) 及以上

---

**現在您可以在 macOS 上順利運行 AI 主力偵測系統了！** 🍎✨
