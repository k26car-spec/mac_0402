# 🎯 全自動選股決策引擎 - 使用總結

## 📌 最簡單的使用方式

### 方法一：透過網頁（最推薦！）⭐

```bash
# 1. 啟動所有服務
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh

# 2. 訪問選股引擎頁面
open http://localhost:3000/dashboard/stock-selector

# 3. 點擊「執行選股分析」
```

**優點**:
- 🚀 一鍵啟動所有服務
- 🎯 透過網頁操作，直觀易用
- 📊 即時查看分析結果
- 💡 無需等待，隨時執行

詳見：[START_SCRIPT_SIMPLIFIED.md](START_SCRIPT_SIMPLIFIED.md)

---

### 方法二：僅執行選股（不啟動服務）

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 run_full_analysis.py
```

**這個命令會自動完成**:
1. ✅ 抓取富邦券商數據
2. ✅ 解析並提取買賣資訊
3. ✅ 執行選股引擎分析
4. ✅ 生成完整報告

**執行時間**: 約 2-3 分鐘

**輸出文件**:
- `broker_data_extracted.csv` - 券商買賣數據
- `backend-v3/reports/fubon_broker_analysis.csv` - 完整分析報告

---

## 📊 查看結果

### 方法1: Excel/Numbers 開啟

```bash
# 開啟分析報告
open backend-v3/reports/fubon_broker_analysis.csv
```

### 方法2: 命令行查看

```bash
# 查看買入建議
python3 -c "
import pandas as pd
df = pd.read_csv('backend-v3/reports/fubon_broker_analysis.csv', encoding='utf-8-sig')
buy = df[df['建議動作'].isin(['強力買入', '買入'])]
print(buy[['股票代碼', '綜合評分', '評級', '建議動作', '目標價']])
"
```

---

## 🎓 進階使用

### 分析特定股票

```python
# my_analysis.py
import asyncio
import sys
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.services.integrated_stock_selector import analyze_single_stock

async def main():
    # 分析台積電
    result = await analyze_single_stock('2330')
    
    scores = result['scores']
    print(f"評分: {scores['weighted_score']:.2f}")
    print(f"建議: {scores['recommendation']}")
    print(f"目標價: {scores.get('target_price')}")

asyncio.run(main())
```

執行:
```bash
python3 my_analysis.py
```

### 批量篩選股票

```python
# batch_screen.py
import asyncio
import sys
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.services.integrated_stock_selector import analyze_multiple_stocks

async def main():
    # 定義股票池
    stocks = ['2330', '2454', '2317', '0050', '0056', '00878']
    
    # 分析
    df = await analyze_multiple_stocks(stocks)
    
    # 篩選高分股票
    good = df[df['綜合評分'] >= 70]
    print(good[['股票代碼', '綜合評分', '建議動作']])

asyncio.run(main())
```

---

## 🔧 常見問題

### Q1: 如何每天自動執行？

**A**: 使用 cron 或 launchd

```bash
# 編輯 crontab
crontab -e

# 添加每日18:00執行
0 18 * * * cd /Users/Mac/Documents/ETF/AI/Ａi-catch && python3 run_full_analysis.py
```

### Q2: 如何調整評分權重？

**A**: 修改配置

```python
from app.services.integrated_stock_selector import IntegratedStockSelector

config = {
    'scoring_weights': {
        'fundamentals': 0.40,    # 基本面 40%
        'technicals': 0.20,      # 技術面 20%
        'broker_flow': 0.30,     # 籌碼面 30%
        'market_sentiment': 0.10 # 市場 10%
    }
}

selector = IntegratedStockSelector(config=config)
```

### Q3: 如何只看買入建議？

**A**: 過濾結果

```python
import pandas as pd

df = pd.read_csv('backend-v3/reports/fubon_broker_analysis.csv', encoding='utf-8-sig')
buy_only = df[df['建議動作'].isin(['強力買入', '買入'])]
print(buy_only)
```

---

## 📁 重要文件位置

```
/Users/Mac/Documents/ETF/AI/Ａi-catch/
│
├── run_full_analysis.py              ⭐ 一鍵執行腳本
├── QUICK_START_GUIDE.md              📖 快速使用指南
│
├── test_fubon_direct.py              🔧 抓取券商數據
├── analyze_fubon_html.py             🔧 解析HTML
├── test_integration_complete.py      🔧 完整分析
│
├── broker_data_extracted.csv         📊 券商數據（輸出）
└── backend-v3/
    └── reports/
        └── fubon_broker_analysis.csv 📊 分析報告（輸出）
```

---

## 🚀 快速參考

### 完整流程（3步驟）

```bash
# 步驟1: 抓取
python3 test_fubon_direct.py

# 步驟2: 解析
python3 analyze_fubon_html.py

# 步驟3: 分析
python3 test_integration_complete.py
```

### 或者一鍵執行

```bash
python3 run_full_analysis.py
```

### 查看結果

```bash
open backend-v3/reports/fubon_broker_analysis.csv
```

---

## 📈 報告欄位說明

| 欄位 | 說明 |
|------|------|
| 股票代碼 | 股票/ETF代碼 |
| 綜合評分 | 0-100分，越高越好 |
| 評級 | A+, A, B+, B, C, D, F |
| 建議動作 | 強力買入/買入/持有/觀望/減碼/賣出 |
| 目標價 | 建議目標價位 |
| 停損價 | 建議停損價位 |
| 建議倉位(%) | 建議配置比例 |
| 風險等級 | low/medium/high |
| 基本面分數 | 基本面評分 (0-100) |
| 技術面分數 | 技術面評分 (0-100) |
| 籌碼面分數 | 籌碼面評分 (0-100) |

---

## 💡 使用建議

1. **每日執行**: 建議每天收盤後執行一次
2. **結合判斷**: 系統建議僅供參考，需結合個人判斷
3. **風險管理**: 嚴格執行停損停利
4. **分散投資**: 不要單押一檔股票
5. **定期回測**: 檢視系統準確度並調整參數

---

## 📞 需要幫助？

1. **快速指南**: `QUICK_START_GUIDE.md`
2. **完整文檔**: `STOCK_SELECTOR_GUIDE.md`
3. **實現報告**: `STOCK_SELECTOR_IMPLEMENTATION.md`
4. **範例腳本**: `stock_selector_examples.py`

---

## ✅ 檢查清單

使用前確認：
- [ ] Python 3.x 已安裝
- [ ] 依賴套件已安裝 (`pip install -r backend-v3/requirements-v3.txt`)
- [ ] 網路連線正常
- [ ] 有足夠磁碟空間（至少100MB）

第一次使用：
- [ ] 執行 `python3 run_full_analysis.py`
- [ ] 確認生成 `broker_data_extracted.csv`
- [ ] 確認生成分析報告
- [ ] 用 Excel 開啟報告查看

---

**準備好了嗎？立即開始！** 🚀

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 run_full_analysis.py
```

**預計執行時間**: 2-3 分鐘  
**輸出**: 完整分析報告 + 券商數據  
**下一步**: 開啟報告查看買入建議！
