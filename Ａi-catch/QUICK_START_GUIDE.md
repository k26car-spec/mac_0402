# 全自動選股決策引擎 - 快速使用指南

## 🚀 快速開始（3步驟）

### 步驟1: 抓取券商數據

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 抓取富邦新店券商數據
python3 test_fubon_direct.py
```

這會生成：
- `fubon_test_YYYYMMDD_HHMMSS.html` - 原始HTML
- 顯示抓取結果

### 步驟2: 解析券商數據

```bash
# 解析HTML並提取券商買賣數據
python3 analyze_fubon_html.py
```

這會生成：
- `broker_data_extracted.csv` - 券商買賣數據（330+筆）

### 步驟3: 執行選股分析

```bash
# 整合券商數據並執行選股引擎
python3 test_integration_complete.py
```

這會生成：
- 完整分析報告
- `/backend-v3/reports/fubon_broker_analysis.csv` - 可用Excel開啟

---

## 📊 詳細使用方式

### 方法一：完整流程（推薦）

**一鍵執行完整流程**：

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 執行完整流程
python3 run_full_analysis.py
```

這個腳本會自動：
1. 抓取富邦券商數據
2. 解析並提取買賣資訊
3. 識別買超股票
4. 執行選股引擎分析
5. 生成完整報告

### 方法二：使用 API

**啟動後端服務**：

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_api_v3.sh
```

**訪問 API 文檔**：
```
http://localhost:8000/api/docs
```

**使用 API 端點**：

```bash
# 1. 分析單一股票
curl http://localhost:8000/api/stock-selector/analyze/2330

# 2. 批量分析
curl -X POST http://localhost:8000/api/stock-selector/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["2330", "2454", "0050"]}'

# 3. 獲取推薦股票
curl "http://localhost:8000/api/stock-selector/recommendations?stock_codes=2330&stock_codes=2454&top_n=5"
```

### 方法三：Python 程式碼

**創建自己的分析腳本**：

```python
import asyncio
import sys
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.services.integrated_stock_selector import analyze_multiple_stocks

async def my_analysis():
    # 定義要分析的股票
    my_stocks = ['2330', '2454', '2317', '0050', '0056']
    
    # 執行分析
    df = await analyze_multiple_stocks(my_stocks)
    
    # 顯示結果
    print(df[['股票代碼', '綜合評分', '評級', '建議動作', '目標價']])
    
    # 篩選買入建議
    buy_list = df[df['建議動作'].isin(['強力買入', '買入'])]
    print("\n買入建議:")
    print(buy_list)

# 執行
asyncio.run(my_analysis())
```

---

## 📋 常用腳本說明

### 1. `test_fubon_direct.py`
**功能**: 測試富邦網站連接並下載HTML  
**輸出**: `fubon_test_YYYYMMDD_HHMMSS.html`  
**用途**: 確認能否訪問富邦網站

### 2. `analyze_fubon_html.py`
**功能**: 解析HTML提取券商數據  
**輸入**: `fubon_test_*.html`  
**輸出**: `broker_data_extracted.csv`  
**用途**: 從HTML中提取買賣數據

### 3. `test_integration_complete.py`
**功能**: 完整整合測試  
**輸入**: `broker_data_extracted.csv`  
**輸出**: 分析報告 + CSV  
**用途**: 執行完整選股流程

### 4. `stock_selector_examples.py`
**功能**: 5個實用範例  
**用途**: 學習如何使用選股引擎

---

## 🎯 實際使用場景

### 場景1: 每日選股

```bash
#!/bin/bash
# daily_stock_selection.sh

cd /Users/Mac/Documents/ETF/AI/Ａi-catch

echo "📊 開始每日選股..."

# 1. 抓取券商數據
python3 test_fubon_direct.py

# 2. 解析數據
python3 analyze_fubon_html.py

# 3. 執行分析
python3 test_integration_complete.py

echo "✅ 每日選股完成！"
echo "報告位置: backend-v3/reports/"
```

### 場景2: 分析特定股票

```python
# my_stock_analysis.py
import asyncio
import sys
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.services.integrated_stock_selector import analyze_single_stock

async def analyze_my_stock(stock_code):
    print(f"分析 {stock_code}...")
    
    result = await analyze_single_stock(stock_code)
    
    if not result.get('metadata', {}).get('error'):
        scores = result['scores']
        recommendation = result['recommendation']
        
        print(f"\n股票: {stock_code}")
        print(f"評分: {scores['weighted_score']:.2f}")
        print(f"評級: {scores['final_grade']}")
        print(f"建議: {scores['recommendation']}")
        print(f"目標價: {scores.get('target_price', 'N/A')}")
        print(f"停損價: {scores.get('stop_loss', 'N/A')}")
        print(f"建議倉位: {result['position_sizing']['position_pct']:.2f}%")

# 使用
asyncio.run(analyze_my_stock('2330'))
```

### 場景3: 批量篩選

```python
# batch_screening.py
import asyncio
import sys
sys.path.append('/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3')

from app.services.integrated_stock_selector import analyze_multiple_stocks

async def screen_stocks():
    # 大範圍股票池
    stock_pool = [
        '2330', '2303', '2317', '2454', '2882', '2881',
        '0050', '0056', '00878', '00929', '00919'
    ]
    
    print(f"篩選 {len(stock_pool)} 檔股票...")
    
    df = await analyze_multiple_stocks(stock_pool)
    
    # 篩選條件: 評分>=70 且 建議買入
    good_stocks = df[
        (df['綜合評分'] >= 70) & 
        (df['建議動作'].isin(['強力買入', '買入']))
    ]
    
    print(f"\n符合條件: {len(good_stocks)} 檔")
    print(good_stocks[['股票代碼', '綜合評分', '評級', '建議動作', '目標價']])

asyncio.run(screen_stocks())
```

---

## 📁 輸出文件說明

### 1. 券商數據文件

**`broker_data_extracted.csv`**
```
券商名稱,買進張數,賣出張數,差額
00878...,95,5136,5041
00953...,10,3849,3839
...
```

### 2. 分析報告文件

**`backend-v3/reports/fubon_broker_analysis.csv`**
```
股票代碼,綜合評分,評級,建議動作,目標價,停損價,建議倉位(%),...
2330,85.5,A+,強力買入,1150,950,12.0,...
```

可用 Excel 或 Numbers 開啟查看。

---

## ⚙️ 自訂配置

### 調整評分權重

```python
from app.services.integrated_stock_selector import IntegratedStockSelector

# 自訂配置
custom_config = {
    'scoring_weights': {
        'fundamentals': 0.40,      # 提高基本面權重
        'technicals': 0.20,        # 降低技術面
        'broker_flow': 0.30,       # 提高籌碼面
        'market_sentiment': 0.05,
        'ai_analysis': 0.05
    }
}

# 使用自訂配置
selector = IntegratedStockSelector(config=custom_config)
```

### 調整風險參數

```python
custom_config = {
    'risk_parameters': {
        'max_position_pct': 0.10,  # 降低單一倉位上限
        'stop_loss_pct': 0.05,     # 更嚴格的停損
        'take_profit_pct': 0.30,   # 更高的停利
    }
}
```

---

## 🔧 故障排除

### 問題1: 券商數據抓取失敗

**解決方案**:
```bash
# 檢查網路連接
curl -I https://fubon-ebrokerdj.fbs.com.tw

# 查看保存的HTML
open fubon_test_*.html

# 手動調整日期參數
# 編輯 test_fubon_direct.py，修改日期
```

### 問題2: 分析結果為空

**解決方案**:
```bash
# 確認數據文件存在
ls -lh broker_data_extracted.csv

# 檢查數據內容
head broker_data_extracted.csv

# 使用預設股票測試
# 編輯腳本，使用 ['2330', '0050'] 等已知股票
```

### 問題3: 導入錯誤

**解決方案**:
```bash
# 確認路徑正確
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 檢查 Python 路徑
python3 -c "import sys; print(sys.path)"

# 重新安裝依賴
pip3 install -r backend-v3/requirements-v3.txt
```

---

## 📞 快速參考

### 一鍵命令

```bash
# 完整流程
cd /Users/Mac/Documents/ETF/AI/Ａi-catch && \
python3 test_fubon_direct.py && \
python3 analyze_fubon_html.py && \
python3 test_integration_complete.py

# 查看結果
open backend-v3/reports/fubon_broker_analysis.csv
```

### 重要文件位置

```
/Users/Mac/Documents/ETF/AI/Ａi-catch/
├── test_fubon_direct.py          # 抓取券商數據
├── analyze_fubon_html.py         # 解析HTML
├── test_integration_complete.py  # 完整分析
├── stock_selector_examples.py    # 使用範例
├── broker_data_extracted.csv     # 券商數據
└── backend-v3/
    └── reports/
        └── fubon_broker_analysis.csv  # 分析報告
```

### API 端點

```
http://localhost:8000/api/stock-selector/analyze/{code}
http://localhost:8000/api/stock-selector/analyze/batch
http://localhost:8000/api/stock-selector/recommendations
http://localhost:8000/api/stock-selector/broker-flow/{code}
```

---

## 🎓 學習資源

1. **完整文檔**: `STOCK_SELECTOR_GUIDE.md`
2. **實現報告**: `STOCK_SELECTOR_IMPLEMENTATION.md`
3. **爬蟲指南**: `ADVANCED_CRAWLER_GUIDE.md`
4. **範例腳本**: `stock_selector_examples.py`

---

**準備好了嗎？開始您的第一次選股分析！** 🚀

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 test_integration_complete.py
```
