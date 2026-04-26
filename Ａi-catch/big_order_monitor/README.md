# 大單偵測監控系統 v3.0

## 🎯 系統特色

✅ **純訊號偵測** - 不執行任何交易  
✅ **多維度評分** - 綜合品質、動能、成交量、型態  
✅ **假單過濾** - 自動偵測並過濾假大單  
✅ **品質分級** - 優秀/良好/普通/不佳  
✅ **即時監控** - 支援多檔股票同時監控  
✅ **Email通知** - 高品質訊號自動發送通知  
✅ **整合富邦API** - 使用現有的富邦客戶端獲取即時數據

## 📦 專案結構

```
big_order_monitor/
├── config/
│   ├── __init__.py
│   └── trading_config.py      # 系統配置
├── core/
│   ├── __init__.py
│   └── detector/
│       ├── __init__.py
│       └── advanced_detector.py  # 進階大單偵測器
├── data/
│   ├── __init__.py
│   └── api/
│       ├── __init__.py
│       └── fubon_api.py       # 富邦API整合
├── utils/
│   ├── __init__.py
│   ├── logger.py              # 日誌模組
│   └── email_service.py       # Email通知服務
├── logs/                      # 日誌檔案
├── reports/                   # 報告檔案
├── main.py                    # 主程式
├── test_system.py             # 測試程式
├── requirements.txt           # 依賴套件
└── README.md                  # 說明文件
```

## 🚀 快速開始

### 1. 安裝依賴

```bash
cd big_order_monitor
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
# 複製範例檔案
cp env_example.txt .env

# 編輯 .env 填入設定
# Email 通知設定（Gmail 需使用應用程式密碼）
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECIPIENT_EMAILS=recipient@example.com
```

### 3. 建立 __init__.py 檔案

```bash
touch config/__init__.py
touch core/__init__.py
touch core/detector/__init__.py
touch data/__init__.py
touch data/api/__init__.py
touch utils/__init__.py
```

### 4. 測試系統

```bash
# 測試偵測器
python test_system.py --detector

# 測試 Email
python test_system.py --email
```

### 5. 啟動監控

```bash
python main.py
```

## ⚙️ 配置說明

### 偵測器參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `base_time_window` | 5 | 時間窗口（分鐘）|
| `base_min_big_orders` | 3 | 最少大單數 |
| `base_min_volume_ratio` | 0.40 | 大單佔比門檻 |
| `min_direction_ratio` | 0.70 | 方向一致性要求 |
| `min_signal_quality` | 0.60 | 最低品質分數 |
| `min_composite_score` | 0.65 | 最低綜合分數 |

### 大單門檻計算

大單門檻會根據以下因素動態調整：
- **股票類型**: 半導體 > 金融 > 電子 > 其他
- **市值**: 大型股門檻較高
- **日均量**: 量大的股票門檻較高
- **波動率**: 波動大的股票門檻較高

## 📊 訊號品質說明

| 等級 | 品質分數 | 說明 |
|------|----------|------|
| 🌟 優秀 | ≥80% | 方向明確、價量配合、大單集中 |
| ✨ 良好 | 70-80% | 訊號清晰、略有瑕疵 |
| 💫 普通 | 60-70% | 訊號可參考、需謹慎 |
| ⚠️ 不佳 | <60% | 自動過濾 |

## 📧 Email 通知

### 設定 Gmail 應用程式密碼

1. 登入 Google 帳戶
2. 前往「安全性」→「兩步驟驗證」
3. 在底部選擇「應用程式密碼」
4. 產生新的應用程式密碼
5. 將密碼填入 `SENDER_PASSWORD`

### 通知條件

- 訊號品質 ≥ 70% 才會發送 Email
- 可在配置中調整 `min_quality_for_email`

## 🔔 訊號範例

```
======================================================================
🌟 【買進訊號】 2330 台積電
======================================================================
   價格: $580.00
   ─────────────────────────────────────
   綜合評分: 85.3%
   信心度: 78.5%
   品質分數: 82.0% (優秀)
   動能分數: 90.0%
   成交量分數: 85.0%
   型態分數: 70.0%
   ─────────────────────────────────────
   觸發原因: 買盤力道78.5%，8筆大單集中，價格上漲1.5%
   ─────────────────────────────────────
   參考停損: $571.30
   參考停利: $594.50
   時間: 10:25:33
======================================================================
```

## ⚠️ 重要提醒

1. **本系統僅供監控參考，不執行交易**
2. 訊號僅供參考，投資決策需自行判斷
3. 過去績效不代表未來表現
4. 投資有風險，請謹慎評估

## 📝 更新日誌

### v3.0 (2025-12-20)
- ✨ 整合富邦API即時數據
- ✨ 新增 Email 通知服務
- ✨ 多維度訊號評分
- ✨ 假單偵測與過濾
- ✨ 每日報告自動發送

## 📄 授權

MIT License
