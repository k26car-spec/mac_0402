# 自動平倉系統使用指南

## 📋 功能概述

自動平倉系統會監控所有模擬交易持倉，當達到以下條件時自動執行平倉：

1. **達到目標價**（嚴格達標）→ 狀態標記為 `target_hit`
2. **觸及停損價** → 狀態標記為 `stopped`

## 🚀 使用方式

### 方式一：前端手動觸發

1. 進入 **持有股票與交易紀錄** 頁面（`/dashboard/portfolio`）
2. 點擊右上角的 **「自動平倉」** 按鈕（紫色）
3. 確認執行
4. 查看平倉結果

### 方式二：API 調用

```bash
# 執行自動平倉（只監控模擬交易）
curl -X POST "http://localhost:8000/api/portfolio/auto-close?simulated_only=true"

# 查看需要監控的持倉狀態
curl "http://localhost:8000/api/portfolio/auto-close/status?simulated_only=true"
```

### 方式三：定時任務（推薦）

#### 使用 Python 腳本

```bash
# 單次執行
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
python auto_close_scheduler.py

# 查看日誌
tail -f logs/auto_close.log
```

#### 使用 crontab（每分鐘執行）

```bash
# 編輯 crontab
crontab -e

# 添加以下行（每分鐘執行一次）
* * * * * cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3 && python auto_close_scheduler.py >> logs/auto_close.log 2>&1
```

#### 使用 systemd timer（Linux）

創建 `/etc/systemd/system/auto-close.service`：

```ini
[Unit]
Description=Auto Close Monitor Service
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
ExecStart=/usr/bin/python3 auto_close_scheduler.py
StandardOutput=append:/var/log/auto_close.log
StandardError=append:/var/log/auto_close.log

[Install]
WantedBy=multi-user.target
```

創建 `/etc/systemd/system/auto-close.timer`：

```ini
[Unit]
Description=Auto Close Monitor Timer
Requires=auto-close.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
AccuracySec=1s

[Install]
WantedBy=timers.target
```

啟用定時器：

```bash
sudo systemctl daemon-reload
sudo systemctl enable auto-close.timer
sudo systemctl start auto-close.timer

# 查看狀態
sudo systemctl status auto-close.timer
```

## 📊 平倉邏輯

### 目標價平倉

```python
if current_price >= target_price:
    # 自動平倉
    status = "target_hit"
    reason = f"達到目標價 ${target_price}"
```

### 停損價平倉

```python
if current_price <= stop_loss_price:
    # 自動平倉
    status = "stopped"
    reason = f"觸及停損價 ${stop_loss_price}"
```

## 📝 平倉記錄

每次自動平倉都會：

1. **更新持倉狀態**
   - `status`: `target_hit` 或 `stopped`
   - `exit_date`: 平倉時間
   - `exit_price`: 平倉價格
   - `exit_reason`: 平倉原因
   - `realized_profit`: 實現損益
   - `realized_profit_percent`: 實現損益百分比

2. **創建交易記錄**
   - `trade_type`: `sell`
   - `profit`: 損益金額
   - `profit_percent`: 損益百分比
   - `notes`: 自動平倉原因

## 🔍 監控範圍

預設只監控 **模擬交易**（`is_simulated = True`）：

- ✅ 主力偵測模擬交易
- ✅ LSTM 預測模擬交易
- ✅ AI 模擬交易
- ❌ 真實交易（需手動平倉）

如需監控真實交易，設置 `simulated_only=false`：

```bash
curl -X POST "http://localhost:8000/api/portfolio/auto-close?simulated_only=false"
```

## 📈 查看平倉統計

### API 查詢

```bash
# 查看持倉摘要
curl "http://localhost:8000/api/portfolio/summary"

# 查看準確性分析
curl "http://localhost:8000/api/portfolio/accuracy?days=30"

# 查看交易記錄
curl "http://localhost:8000/api/portfolio/trades?limit=50"
```

### 前端查看

1. 進入 **持有股票與交易紀錄** 頁面
2. 切換到 **「交易紀錄」** 標籤 → 查看所有平倉記錄
3. 切換到 **「準確性分析」** 標籤 → 查看各來源的勝率

## ⚙️ 配置選項

### 環境變數

在 `.env` 文件中配置：

```bash
# 資料庫連線
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_stock_v3

# 自動平倉設定（可選）
AUTO_CLOSE_ENABLED=true
AUTO_CLOSE_INTERVAL_SECONDS=60
AUTO_CLOSE_SIMULATED_ONLY=true
```

### 程式碼配置

在 `auto_close_monitor.py` 中修改：

```python
# 修改平倉條件
if current_price >= position.target_price * 1.02:  # 超過目標價 2% 才平倉
    should_close = True
```

## 🐛 故障排除

### 問題 1：無法獲取即時價格

**原因**：yfinance API 限制或股票代碼錯誤

**解決**：
- 檢查網路連線
- 確認股票代碼正確（上市用 `.TW`，上櫃用 `.TWO`）
- 等待幾分鐘後重試

### 問題 2：平倉未執行

**原因**：
- 持倉狀態不是 `open`
- 未設定目標價或停損價
- 價格尚未達到條件

**解決**：
```bash
# 查看持倉狀態
curl "http://localhost:8000/api/portfolio/auto-close/status"

# 檢查是否有需要平倉的持倉
```

### 問題 3：定時任務未執行

**原因**：crontab 配置錯誤或權限問題

**解決**：
```bash
# 檢查 crontab 是否正確
crontab -l

# 查看 cron 日誌
tail -f /var/log/syslog | grep CRON

# 手動執行測試
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
python auto_close_scheduler.py
```

## 📞 技術支援

如有問題，請查看：
- 系統日誌：`logs/auto_close.log`
- API 文檔：`http://localhost:8000/docs`
- 資料庫記錄：`SELECT * FROM portfolio WHERE status IN ('target_hit', 'stopped')`

## 🔄 更新日誌

### v1.0.0 (2026-01-01)
- ✅ 初始版本
- ✅ 支援目標價/停損價自動平倉
- ✅ 支援模擬交易監控
- ✅ 前端手動觸發功能
- ✅ 定時任務腳本
