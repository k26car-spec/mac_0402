# 🎯 AI主力偵測系統 - 完整架構說明

## 📁 專案結構

```
Ａi-catch/
├── 📝 核心程式碼
│   ├── config.py                 # 配置模組（數據源、預設值）
│   ├── main_force_detector.py   # 主力偵測演算法（8大特徵）
│   ├── async_crawler.py         # 異步爬蟲系統（多數據源）
│   ├── ml_predictor.py          # 機器學習模型（GradientBoosting）
│   ├── notifier.py              # 多管道通知（LINE/Telegram/Email）
│   └── stock_monitor.py         # 主監控系統（整合所有模組）
│
├── ⚙️ 配置文件
│   ├── config.yaml              # 系統配置（監控清單、通知設定）
│   ├── .env.example             # 環境變數範例
│   └── requirements.txt         # Python 依賴套件
│
├── 🚀 部署腳本
│   ├── start_monitor.sh         # 啟動腳本（3種模式）
│   ├── stop_monitor.sh          # 停止腳本
│   ├── Dockerfile               # Docker 容器化
│   └── docker-compose.yml       # Docker Compose 配置
│
├── 🧪 測試與文檔
│   ├── test_system.py           # 完整系統測試
│   ├── README.md                # 完整文檔
│   ├── QUICKSTART.md            # 快速入門指南
│   └── .gitignore               # Git 忽略規則
│
└── 📂 資料目錄（運行時自動創建）
    ├── data/                    # 資料庫檔案
    │   └── stock_monitor.db    # SQLite 資料庫
    ├── logs/                    # 日誌檔案
    │   └── stock_monitor.log   # 系統日誌
    └── models/                  # AI 模型
        └── main_force_model.pkl # 訓練好的模型
```

---

## 🔧 核心模組詳解

### 1. **config.py** - 配置模組

**功能**: 定義所有系統常數和預設值

**主要內容**:
- `DATA_SOURCES`: 數據源配置（Yahoo、富邦、TDCC、Goodinfo）
- `SYSTEM_CONFIG`: 系統運行參數
- `DEFAULT_WATCHLIST`: 預設監控清單
- `NOTIFICATION_CONFIG`: 通知管道設定
- `AI_MODEL_CONFIG`: AI 模型參數

**使用時機**: 其他模組導入時自動載入

---

### 2. **main_force_detector.py** - 主力偵測演算法

**功能**: 多維度主力特徵分析與判斷

**核心類別**: `MainForceDetector`

**8大特徵提取**:
1. ✅ **量能異常** (`_volume_anomaly`)
   - IQR 方法偵測異常量能
   - 閥值: 1.5倍標準上界

2. ✅ **大單分析** (`_large_order_analysis`)
   - 計算大單佔比
   - 閥值: 30% 表示主力

3. ✅ **價格動能** (`_price_momentum`)
   - 5日價格變化率
   - 正值表示上漲動能

4. ✅ **委買委賣** (`_bid_ask_analysis`)
   - 委買/委賣比率
   - >1 表示買盤強勁

5. ✅ **資金流向** (`_money_flow_index`)
   - MFI 指標計算
   - >70 表示資金大量流入

6. ✅ **法人追蹤** (`_institutional_tracking`)
   - 價量相關性分析
   - 正相關表示法人買進

7. ✅ **統計特徵**
   - 量能偏度 (Skewness)
   - 價格峰度 (Kurtosis)

8. ✅ **型態突破** (`_pattern_recognition`)
   - MA20 突破分析
   - >5% 表示強勢突破

**判斷邏輯**:
```python
信心分數 = Σ(特徵值 × 權重)

權重分配:
- volume_ratio: 25%
- large_order_ratio: 30%
- money_flow: 15%
- institutional_flow: 20%
- pattern_breakout: 10%

主力判斷 = 信心分數 > 閥值 (預設 0.7)
```

---

### 3. **async_crawler.py** - 異步爬蟲系統

**功能**: 高效並發獲取多數據源

**核心類別**: `AsyncStockCrawler`

**支援數據源**:
- ✅ **Yahoo Finance**
  - 主力進出頁面解析
  - OHLCV 歷史數據
  - Chart API 調用

- 🔄 **富邦** (預留接口)
  - 5檔委買委賣
  - 即時大單追蹤
  - 需實際 API

**關鍵特性**:
- `aiohttp` 異步 HTTP 請求
- `BeautifulSoup` HTML 解析
- 批量並發處理 (`gather`)
- 自動重試與錯誤處理
- 交易時間判斷

**監控流程**:
```
1. 判斷是否交易時間
2. 批量獲取所有股票數據
3. 整理並合併數據
4. 回調處理函數
5. 等待 N 秒後重複
```

---

### 4. **ml_predictor.py** - 機器學習模型

**功能**: AI 預測主力行為

**核心類別**: `MainForcePredictor`

**模型演算法**: 
- `GradientBoostingClassifier`
  - n_estimators=100
  - learning_rate=0.1
  - max_depth=5

**主要功能**:
1. **訓練** (`train`)
   - 80/20 訓練/測試分割
   - 5折交叉驗證
   - 特徵重要性分析
   - 自動保存模型

2. **預測** (`predict`)
   - 輸入: 特徵字典
   - 輸出: 是否主力、信心度

3. **線上學習** (`update_online`)
   - 累積新數據
   - 定期重新訓練

**訓練數據格式**:
```python
{
    'volume_ratio': float,
    'large_order_ratio': float,
    'money_flow': float,
    'institutional_flow': float,
    'pattern_breakout': float,
    'price_momentum': float,
    'volume_skewness': float,
    'price_kurtosis': float,
    'label': 0 or 1  # 0=無主力, 1=主力
}
```

---

### 5. **notifier.py** - 多管道通知系統

**功能**: 即時警報推送

**核心類別**: `MultiChannelNotifier`

**支援管道**:

| 管道 | 特性 | 取得方式 |
|------|------|----------|
| LINE Notify | 免費、即時 | [notify-bot.line.me](https://notify-bot.line.me/my/) |
| Telegram | 免費、功能強 | @BotFather |
| Email | 通用、詳細 | Gmail 應用程式密碼 |
| Webhook | 可整合任何系統 | 自訂 |

**通知範例**:
```
🚨 主力大單警報 🚨

📈 股票代碼: 2330.TW
⭐ 信心指數: 85.30%
🕒 時間: 2024-12-11 10:30:15

📊 關鍵特徵:
• 量能比率: 2.35
• 大單比例: 42.50%
• 資金流向: 78.20
```

**並發發送**: 使用 `asyncio.gather` 同時發送所有管道

---

### 6. **stock_monitor.py** - 主監控系統

**功能**: 整合所有模組，協調運作

**核心類別**: `AdvancedStockMonitor`

**系統流程**:

```
┌─────────────────┐
│  初始化系統      │
│  - 配置載入      │
│  - 資料庫初始化   │
│  - 模組啟動      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  開始監控循環    │
│  - 檢查交易時間   │
│  - 批量爬取數據   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  數據處理        │
│  - 特徵提取      │
│  - AI 判斷       │
└────────┬────────┘
         │
         ▼
    主力信號？
    /        \
  是          否
   │          │
   ▼          ▼
發送通知    記錄日誌
儲存警示    
   │          │
   └────┬─────┘
        │
        ▼
   等待間隔
        │
        └──► 返回監控循環
```

**資料庫設計**:

**stock_alerts** (警示記錄):
```sql
- id: 主鍵
- stock_code: 股票代碼
- alert_type: 警示類型
- confidence: 信心分數
- features: 特徵 JSON
- timestamp: 時間戳
- notified: 是否已通知
```

**stock_data** (數據記錄):
```sql
- id: 主鍵
- stock_code: 股票代碼
- data_type: 數據類型
- data_json: 數據 JSON
- timestamp: 時間戳
```

---

## 🎛️ 配置文件說明

### config.yaml

**結構**:
```yaml
system:           # 系統資訊
monitoring:       # 監控參數
watchlist:        # 監控清單
notifications:    # 通知設定
database:         # 資料庫配置
logging:          # 日誌配置
ai_model:         # AI 模型設定
features:         # 特徵權重
security:         # 安全設定
performance:      # 效能優化
report:           # 報告設定
```

**關鍵參數**:
- `check_interval`: 60 秒（建議 30-300）
- `confidence_threshold`: 0.7（建議 0.6-0.9）
- `trading_hours_only`: true（僅交易時間）

---

## 🚀 部署方案

### 方案 1: 本地運行

**適合**: 開發、測試、小規模使用

**步驟**:
```bash
1. pip install -r requirements.txt
2. cp .env.example .env
3. ./start_monitor.sh
```

**優點**: 簡單、靈活
**缺點**: 需要保持電腦開機

---

### 方案 2: Docker 容器

**適合**: 生產環境、雲端部署

**步驟**:
```bash
docker-compose up -d
```

**優點**: 
- 環境隔離
- 易於部署
- 自動重啟

**缺點**: 需要 Docker 知識

---

### 方案 3: 雲端服務

**適合**: 24/7 監控

**平台選擇**:
- AWS EC2 / Lightsail
- Google Cloud Compute
- DigitalOcean Droplet
- Heroku (需調整)

**最小規格**: 1 vCPU, 512MB RAM

---

## 📊 效能指標

**系統容量**:
- 監控股票數: 建議 5-20 支
- 檢查間隔: 30-60 秒
- 記憶體使用: ~100-200 MB
- CPU 使用: ~5-10%
- 網路流量: ~1-5 MB/小時

**資料庫成長**:
- 每日警示: ~10-50 筆
- 每月數據: ~1-5 MB
- 建議定期清理30天前數據

---

## 🔒 安全建議

### 敏感資訊保護

1. ✅ **絕不提交** `.env` 到 Git
2. ✅ **使用應用程式密碼** 而非主密碼
3. ✅ **定期輪換** API Token
4. ✅ **限制權限** 資料庫檔案 (chmod 600)

### API 速率限制

```yaml
security:
  api_rate_limit: 10  # 每秒最多10次請求
  timeout: 10         # 請求超時10秒
  max_retries: 3      # 最多重試3次
```

---

## 📈 最佳實踐

### 1. 監控策略

**DO ✅**:
- 專注熟悉的股票（5-10支）
- 結合技術分析
- 設定合理閥值（0.7-0.8）
- 定期檢視準確率

**DON'T ❌**:
- 監控過多股票（>20支）
- 完全依賴系統信號
- 設定過低閥值（<0.5）
- 忽略市場大環境

### 2. 參數調優

**初期設定** (保守):
```yaml
confidence_threshold: 0.8
check_interval: 120  # 2分鐘
```

**穩定後** (積極):
```yaml
confidence_threshold: 0.6
check_interval: 60   # 1分鐘
```

### 3. 數據管理

**每週**:
- 檢視警示準確度
- 備份資料庫
- 檢查日誌檔案大小

**每月**:
- 重新訓練 ML 模型
- 清理舊數據
- 更新監控清單

---

## 🎓 進階功能開發

### 擴展新數據源

```python
# async_crawler.py
async def fetch_new_source(self, stock_code):
    url = f'https://newsource.com/api/{stock_code}'
    async with self.session.get(url) as response:
        data = await response.json()
        return data
```

### 添加新特徵

```python
# main_force_detector.py
def _new_feature(self, data):
    # 計算新特徵
    return feature_value

# 在 extract_features 中添加
features['new_feature'] = self._new_feature(ticker_data)
```

### 自訂通知格式

```python
# stock_monitor.py
async def send_notification(self, stock_code, confidence, features):
    # 自訂訊息格式
    message = f"您的自訂格式: {stock_code}"
    await self.notifier.send_all(...)
```

---

## 🐛 除錯技巧

### 啟用 DEBUG 日誌

```yaml
# config.yaml
logging:
  level: "DEBUG"
```

### 查看特定模組日誌

```python
import logging
logging.getLogger('async_crawler').setLevel(logging.DEBUG)
```

### SQL 查詢技巧

```sql
-- 最近的警示
SELECT * FROM stock_alerts 
ORDER BY timestamp DESC 
LIMIT 10;

-- 統計每支股票警示次數
SELECT stock_code, COUNT(*) as count 
FROM stock_alerts 
GROUP BY stock_code 
ORDER BY count DESC;

-- 高信心度警示
SELECT * FROM stock_alerts 
WHERE confidence > 0.85 
ORDER BY timestamp DESC;
```

---

## 📚 學習資源

### 技術文檔
- [aiohttp 文檔](https://docs.aiohttp.org/)
- [scikit-learn 文檔](https://scikit-learn.org/)
- [pandas 文檔](https://pandas.pydata.org/)

### 金融知識
- 主力進出分析
- 量價關係
- 技術指標

---

## 🎯 總結

這是一個**完整、可擴展的 AI 主力偵測系統**，具備：

✅ **8大主力特徵分析**
✅ **即時異步監控**
✅ **AI 智能判斷**
✅ **多管道通知**
✅ **完整數據管理**
✅ **靈活配置**
✅ **易於部署**

**適用對象**: 進階交易者、量化開發者、AI 愛好者

**核心價值**: 自動化偵測主力動向，提高交易決策效率

---

**版本**: 1.0.0  
**最後更新**: 2024-12-11  
**作者**: 進階交易者  

🚀 **開始使用吧！**
