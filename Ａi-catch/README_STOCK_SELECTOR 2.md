# 🎯 全自動選股決策引擎

> 整合券商進出、多維度分析、量化評分的智能選股系統

[![Status](https://img.shields.io/badge/status-ready-brightgreen)]()
[![Version](https://img.shields.io/badge/version-1.0.0-blue)]()
[![Python](https://img.shields.io/badge/python-3.8+-blue)]()

---

## 🚀 快速開始

### 一鍵執行（推薦）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 run_full_analysis.py
```

**就這麼簡單！** 系統會自動：
1. ✅ 抓取富邦券商數據（自動使用今天日期）
2. ✅ 解析並提取買賣資訊
3. ✅ 執行多維度選股分析
4. ✅ 生成完整Excel報告

**執行時間**: 2-3 分鐘

---

## 📊 系統功能

### 核心功能

- 🏦 **券商進出分析** - 抓取富邦新店等8家關鍵券商數據
- 📈 **多維度評分** - 基本面(30%) + 技術面(25%) + 籌碼面(25%) + 法人(10%) + 市場(10%)
- 🎯 **量化決策** - 0-100分評分，A+到F評級
- 💡 **投資建議** - 強力買入/買入/持有/觀望/減碼/賣出
- 🎲 **風險管理** - 目標價、停損價、倉位建議
- 📊 **報告匯出** - CSV/Excel格式

### 技術特色

- 🕷️ **進階爬蟲** - 5層反爬蟲策略
- 🔄 **自動更新** - 日期自動使用當天
- ⚡ **批量處理** - 並行分析多檔股票
- 🛡️ **錯誤處理** - 自動重試與備用方案

---

## 📖 文檔導航

### ⭐ 必讀文檔

| 文檔 | 說明 | 適合對象 |
|------|------|----------|
| [**HOW_TO_USE.md**](HOW_TO_USE.md) | 使用總結 | 所有用戶 |
| [**QUICK_START_GUIDE.md**](QUICK_START_GUIDE.md) | 快速開始指南 | 新手 |
| [**SYSTEM_COMPLETE.md**](SYSTEM_COMPLETE.md) | 系統完成總結 | 所有用戶 |

### 📚 詳細文檔

| 文檔 | 說明 | 適合對象 |
|------|------|----------|
| [DATE_PARAMETER_GUIDE.md](DATE_PARAMETER_GUIDE.md) | 日期參數說明 | 所有用戶 |
| [STOCK_SELECTOR_GUIDE.md](STOCK_SELECTOR_GUIDE.md) | 完整使用手冊 | 進階用戶 |
| [STOCK_SELECTOR_IMPLEMENTATION.md](STOCK_SELECTOR_IMPLEMENTATION.md) | 技術實現報告 | 開發者 |
| [ADVANCED_CRAWLER_GUIDE.md](ADVANCED_CRAWLER_GUIDE.md) | 爬蟲技術指南 | 開發者 |

---

## 💻 使用方式

### 方法一：一鍵執行（最簡單）

```bash
python3 run_full_analysis.py
```

### 方法二：分步執行

```bash
# 步驟1: 抓取券商數據
python3 test_fubon_direct.py

# 步驟2: 解析數據
python3 analyze_fubon_html.py

# 步驟3: 執行分析
python3 test_integration_complete.py
```

### 方法三：Python 程式碼

```python
import asyncio
import sys
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.services.integrated_stock_selector import analyze_single_stock

async def main():
    result = await analyze_single_stock('2330')
    print(f"評分: {result['scores']['weighted_score']:.2f}")
    print(f"建議: {result['scores']['recommendation']}")

asyncio.run(main())
```

---

## 📊 輸出報告

執行完成後會生成：

### 1. 券商數據
```
broker_data_extracted.csv
```
包含330+筆券商買賣資訊

### 2. 分析報告（重點！）
```
backend-v3/reports/fubon_broker_analysis.csv
```

報告欄位：
- 股票代碼、綜合評分、評級
- 建議動作、目標價、停損價
- 建議倉位(%)、風險等級
- 基本面/技術面/籌碼面分數

**用 Excel 開啟查看**：
```bash
open backend-v3/reports/fubon_broker_analysis.csv
```

---

## 🎯 評分系統

### 綜合評分公式

```
綜合評分 = 基本面(30%) + 技術面(25%) + 籌碼面(25%) + 法人(10%) + 市場(10%)
```

### 評級標準

| 評級 | 分數 | 建議動作 |
|------|------|----------|
| A+ | 85-100 | 強力買入 |
| A | 75-84 | 買入 |
| B+ | 65-74 | 買入 |
| B | 55-64 | 持有 |
| C | 45-54 | 觀望 |
| D | 35-44 | 減碼 |
| F | 0-34 | 賣出 |

---

## 🔧 系統架構

```
[富邦證券網站]
    ↓ (反爬蟲策略)
[HTML數據]
    ↓ (解析提取)
[券商買賣數據]
    ↓ (識別買超)
[股票清單]
    ↓ (多維度分析)
[基本面 + 技術面 + 籌碼面 + 法人 + 市場]
    ↓ (量化評分)
[綜合評分 + 評級]
    ↓ (決策引擎)
[投資建議 + 目標價 + 停損價 + 倉位]
    ↓ (報告匯出)
[Excel 分析報告]
```

---

## 📁 文件結構

```
/Users/Mac/Documents/ETF/AI/Ａi-catch/
│
├── run_full_analysis.py              ⭐ 一鍵執行
├── README_STOCK_SELECTOR.md          📖 本文件
│
├── test_fubon_direct.py              🔧 抓取券商數據
├── analyze_fubon_html.py             🔧 解析HTML
├── test_integration_complete.py      🔧 完整分析
│
├── HOW_TO_USE.md                     📖 使用總結
├── QUICK_START_GUIDE.md              📖 快速指南
├── SYSTEM_COMPLETE.md                📖 完成總結
├── DATE_PARAMETER_GUIDE.md           📖 日期說明
│
├── broker_data_extracted.csv         📊 券商數據（輸出）
└── backend-v3/
    ├── app/services/
    │   ├── broker_flow_analyzer.py   💼 券商分析器
    │   ├── advanced_broker_crawler.py 🕷️ 進階爬蟲
    │   └── integrated_stock_selector.py 🎯 選股引擎
    └── reports/
        └── fubon_broker_analysis.csv 📊 分析報告（輸出）
```

---

## ⚙️ 安裝與配置

### 依賴套件

```bash
pip install pandas numpy yfinance beautifulsoup4 requests openpyxl
```

或使用 requirements：

```bash
pip install -r backend-v3/requirements-v3.txt
```

### 系統需求

- Python 3.8+
- 網路連線
- 磁碟空間 100MB+

---

## 💡 使用場景

### 場景1: 每日選股

```bash
# 每天收盤後執行
python3 run_full_analysis.py
```

### 場景2: 分析特定股票

```python
# 分析台積電
asyncio.run(analyze_single_stock('2330'))
```

### 場景3: 批量篩選

```python
# 篩選高分股票
stocks = ['2330', '2454', '0050', '0056']
df = await analyze_multiple_stocks(stocks)
good = df[df['綜合評分'] >= 70]
```

---

## 🔄 自動化執行

### 設定 cron 每日執行

```bash
# 編輯 crontab
crontab -e

# 添加每日18:00執行
0 18 * * * cd /Users/Mac/Documents/ETF/AI/Ａi-catch && python3 run_full_analysis.py
```

---

## ⚠️ 重要提醒

### 日期自動更新

✅ **所有腳本已自動使用當天日期**

系統會自動使用今天的日期（例如：2026-01-01），您不需要手動修改！

詳見：[DATE_PARAMETER_GUIDE.md](DATE_PARAMETER_GUIDE.md)

### 投資建議

1. **系統建議僅供參考** - 需結合個人判斷
2. **嚴格執行停損停利** - 風險管理最重要
3. **分散投資** - 不要單押一檔股票
4. **定期回測** - 檢視系統準確度

---

## 📞 需要幫助？

### 快速查詢

| 問題 | 查看 |
|------|------|
| 如何使用？ | [HOW_TO_USE.md](HOW_TO_USE.md) |
| 快速開始？ | [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) |
| 日期問題？ | [DATE_PARAMETER_GUIDE.md](DATE_PARAMETER_GUIDE.md) |
| 完整手冊？ | [STOCK_SELECTOR_GUIDE.md](STOCK_SELECTOR_GUIDE.md) |

### 常見問題

**Q: 如何開始使用？**  
A: 執行 `python3 run_full_analysis.py`

**Q: 報告在哪裡？**  
A: `backend-v3/reports/fubon_broker_analysis.csv`

**Q: 如何查看買入建議？**  
A: 用 Excel 開啟報告，篩選「建議動作」欄位

---

## 📈 系統狀態

- ✅ 券商數據抓取 - 已完成
- ✅ 數據解析 - 已完成
- ✅ 多維度分析 - 已完成
- ✅ 量化評分 - 已完成
- ✅ 投資建議 - 已完成
- ✅ 報告匯出 - 已完成
- ✅ 日期自動更新 - 已完成
- ✅ API 端點 - 已完成
- ✅ 反爬蟲策略 - 已完成

**系統狀態**: 🟢 完全就緒

---

## 🎉 立即開始

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 run_full_analysis.py
```

**預期結果**:
- ✅ 抓取今天的券商數據
- ✅ 提取330+筆買賣資訊
- ✅ 分析買超股票
- ✅ 生成完整報告

**下一步**:
```bash
open backend-v3/reports/fubon_broker_analysis.csv
```

---

**祝您投資順利！** 📈🚀

---

**版本**: v1.0.0  
**建立日期**: 2026-01-01  
**狀態**: ✅ 完成並可用  
**最後更新**: 日期自動更新功能已啟用
