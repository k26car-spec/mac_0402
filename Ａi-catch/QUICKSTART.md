# 🚀 快速入門指南

本指南將幫助您在 5 分鐘內啟動 AI 主力偵測系統。

## 📝 前置準備

確保您的系統已安裝：
- Python 3.9 或更高版本
- pip（Python 套件管理器）

## ⚡ 快速啟動（3 步驟）

### 1️⃣ 安裝依賴

```bash
# 進入專案目錄
cd Ａi-catch

# 安裝必要套件
pip install -r requirements.txt
```

### 2️⃣ 運行測試

```bash
# 測試系統是否正常
python3 test_system.py
```

如果看到「所有測試通過」，表示系統可以運行！

### 3️⃣ 啟動監控

```bash
# 給腳本執行權限
chmod +x start_monitor.sh

# 啟動系統
./start_monitor.sh

# 選擇選項 1 (前台運行)
```

🎉 完成！系統現在開始監控股票了。

---

## 🔧 進階設定（可選）

### 啟用通知功能

如果您想收到 LINE/Telegram/Email 通知，請依照以下步驟：

#### LINE Notify

```bash
# 1. 取得 Token
# 前往: https://notify-bot.line.me/my/
# 登入並發行新的權杖

# 2. 設定環境變數
export LINE_NOTIFY_TOKEN="your_token_here"

# 3. 在 config.yaml 中啟用
# notifications:
#   line:
#     enabled: true
```

#### Telegram Bot

```bash
# 1. 建立機器人
# 與 @BotFather 對話，輸入 /newbot

# 2. 取得 Chat ID
# 與 @userinfobot 對話

# 3. 設定環境變數
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# 4. 在 config.yaml 中啟用
# notifications:
#   telegram:
#     enabled: true
```

### 自訂監控清單

編輯 `config.yaml` 文件：

```yaml
watchlist:
  stocks:
    - "2330.TW"  # 台積電
    - "2454.TW"  # 聯發科
    - "你的股票代碼.TW"
```

### 調整靈敏度

如果覺得警報太多或太少，調整信心閥值：

```yaml
ai_model:
  confidence_threshold: 0.7  # 預設值
  # 降低 = 更多警報（0.5-0.6）
  # 提高 = 更少警報（0.8-0.9）
```

---

## 📱 使用範例

### 場景 1: 上班族盤中監控

```bash
# 早上 9 點前啟動
./start_monitor.sh
# 選擇選項 2 (背景運行)

# 系統會在交易時間自動監控
# 發現主力進場時發送通知到手機

# 下午 2 點後停止
./stop_monitor.sh
```

### 場景 2: 週末回測分析

```python
# 查看本週的主力警示
from stock_monitor import AdvancedStockMonitor

monitor = AdvancedStockMonitor()
alerts = monitor.get_historical_alerts(days=7)

for alert in alerts:
    print(f"{alert['stock_code']}: {alert['confidence']:.2%}")
```

### 場景 3: 訓練自己的模型

```python
# 使用您的歷史數據訓練模型
from ml_predictor import MainForcePredictor
import pandas as pd

# 載入您的數據
df = pd.read_csv('my_historical_data.csv')

# 訓練模型
predictor = MainForcePredictor()
X, y = predictor.prepare_training_data(df)
predictor.train(X, y)

# 在 config.yaml 啟用 ML 模型
# ai_model:
#   use_ml_model: true
```

---

## 🆘 常見問題

### Q: 系統沒有發送通知？

**A:** 檢查：
1. 環境變數是否正確設定
2. config.yaml 中對應通知管道是否啟用
3. Token 是否有效
4. 查看日誌: `tail -f logs/stock_monitor.log`

### Q: 如何只監控特定股票？

**A:** 編輯 `config.yaml`：

```yaml
watchlist:
  stocks:
    - "2330.TW"  # 只監控台積電
```

### Q: 可以調整檢查頻率嗎？

**A:** 可以，編輯 `config.yaml`：

```yaml
monitoring:
  check_interval: 60  # 改為 30 (每30秒檢查)
```

### Q: 如何停止系統？

**A:** 
```bash
# 如果是前台運行，按 Ctrl+C
# 如果是背景運行，執行:
./stop_monitor.sh
```

### Q: 數據儲存在哪裡？

**A:** 
- 資料庫: `data/stock_monitor.db`
- 日誌: `logs/stock_monitor.log`
- 模型: `models/main_force_model.pkl`

### Q: 系統會自動啟動嗎？

**A:** 不會。您需要手動啟動。如需開機自動啟動，可使用 systemd 或 launchd（macOS）。

---

## 📊 檢視結果

### 查看即時日誌

```bash
tail -f logs/stock_monitor.log
```

### 搜尋特定股票

```bash
grep "2330.TW" logs/stock_monitor.log
```

### 查詢資料庫

```bash
sqlite3 data/stock_monitor.db

# 查看所有警示
SELECT * FROM stock_alerts ORDER BY timestamp DESC LIMIT 10;

# 查看特定股票
SELECT * FROM stock_alerts WHERE stock_code = '2330.TW';

# 離開
.quit
```

---

## 🎯 下一步

現在您已經掌握基礎，可以：

1. **優化參數** - 根據實際效果調整閥值和權重
2. **訓練模型** - 使用真實數據訓練 ML 模型
3. **擴展功能** - 添加自己的分析邏輯
4. **整合其他工具** - 連結到您的交易系統

---

## 💡 專業提示

1. **分散監控** - 不要監控太多股票（建議 5-10 支）
2. **定期檢視** - 每週檢視警示準確度，調整參數
3. **結合技術分析** - 主力信號 + 技術面 = 更高勝率
4. **謹慎交易** - 主力進場不等於必漲，需綜合判斷
5. **保持更新** - 定期更新數據源和演算法

---

## 📚 延伸閱讀

- [完整文檔](README.md)
- [配置說明](config.yaml)
- [API 文檔](docs/API.md)（如有）

---

**祝您使用愉快！** 🚀

如有問題，歡迎開 Issue 討論。

---

**最後更新**: 2024-12-11
