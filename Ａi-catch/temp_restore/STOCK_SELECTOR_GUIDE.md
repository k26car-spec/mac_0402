# 全自動選股決策引擎 - 使用指南

## 📋 系統概述

全自動選股決策引擎整合了多維度分析，提供量化評分與投資建議：

### 核心功能
1. **券商分點進出分析** - 抓取富邦新店等關鍵券商的買賣資料
2. **多維度整合分析** - 基本面、技術面、籌碼面、法人買賣、市場情緒
3. **量化評分系統** - 0-100分綜合評分，A+到F評級
4. **智能投資建議** - 買入/賣出建議、目標價、停損價、倉位建議
5. **批量分析** - 同時分析多檔股票，自動排序推薦
6. **報告匯出** - CSV/Excel格式報告

## 🏗️ 系統架構

```
[數據輸入層] → [策略整合層] → [決策引擎層] → [執行輸出層]
     ↓              ↓              ↓              ↓
券商數據     基本面+技術面+籌碼面  量化評分      交易訊號
財務數據     多維度分析邏輯       風險評估      倉位管理
法人數據     AI輔助分析          目標價計算    報告匯出
```

## 📦 安裝與設定

### 1. 安裝依賴套件

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
pip install -r requirements-v3.txt
```

### 2. 確認必要套件

```bash
pip install pandas numpy yfinance beautifulsoup4 requests openpyxl
```

## 🚀 快速開始

### 方法一：使用測試腳本

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python test_stock_selector.py
```

這會執行完整測試流程：
1. 測試券商進出分析
2. 測試整合選股引擎
3. 測試完整工作流程

### 方法二：使用 API

#### 啟動後端服務

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_api_v3.sh
```

#### API 端點

1. **分析單一股票**
```bash
curl http://localhost:8000/api/stock-selector/analyze/2330
```

2. **批量分析股票**
```bash
curl -X POST http://localhost:8000/api/stock-selector/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["2330", "2303", "2317"]}'
```

3. **獲取富邦新店買超股票**
```bash
curl http://localhost:8000/api/stock-selector/broker-flow/fubon-xindan/top-stocks?top_n=20
```

4. **查詢特定股票券商進出**
```bash
curl http://localhost:8000/api/stock-selector/broker-flow/2330?days=5
```

5. **匯出分析報告**
```bash
curl "http://localhost:8000/api/stock-selector/export/report?stock_codes=2330&stock_codes=2303&format=csv"
```

### 方法三：Python 程式碼

```python
import asyncio
from app.services.integrated_stock_selector import (
    analyze_single_stock,
    analyze_multiple_stocks,
    get_top_recommendations
)
from app.services.broker_flow_analyzer import get_fubon_xindan_top_stocks

async def main():
    # 1. 獲取富邦新店買超股票
    fubon_stocks = get_fubon_xindan_top_stocks(top_n=20)
    stock_codes = [s['stock_code'] for s in fubon_stocks]
    
    # 2. 批量分析
    df = await analyze_multiple_stocks(stock_codes)
    
    # 3. 篩選買入建議
    buy_stocks = df[df['建議動作'].isin(['強力買入', '買入'])]
    
    print(buy_stocks)

asyncio.run(main())
```

## 📊 評分系統說明

### 綜合評分計算

```
綜合評分 = 基本面(30%) + 技術面(25%) + 籌碼面(25%) + 法人買賣(10%) + 市場環境(10%)
```

### 各維度評分標準

#### 1. 基本面評分 (0-100分)

| 指標 | 優秀 | 良好 | 普通 | 不佳 |
|------|------|------|------|------|
| ROE | >15% | 8-15% | 0-8% | <0% |
| 本益比 | 5-15 | 15-20 | 20-30 | >30 |
| 負債比 | <50% | 50-100% | 100-200% | >200% |
| 股息殖利率 | >4% | 2-4% | 1-2% | <1% |
| 營收成長 | >10% | 0-10% | -10-0% | <-10% |

#### 2. 技術面評分 (0-100分)

- **均線排列**: 多頭排列 +20分，空頭排列 -20分
- **成交量**: 放量 +10分，縮量 -5分
- **近期報酬**: 20日報酬 >10% +10分，<-10% -10分
- **波動率**: 低波動 +5分，高波動 -5分

#### 3. 籌碼面評分 (0-100分)

- **淨流入**: >1000張 +25分，<-1000張 -25分
- **趨勢**: 強力買入 +15分，強力賣出 -15分
- **異常活動**: 配合買入 +5分，配合賣出 -5分
- **法人比例**: >30% +10分

#### 4. 法人買賣評分 (0-100分)

- **外資**: 買超>1000張 +20分，賣超>1000張 -20分
- **投信**: 買超>500張 +15分，賣超>500張 -15分

### 評級標準

| 評級 | 分數範圍 | 建議動作 |
|------|----------|----------|
| A+ | 85-100 | 強力買入 |
| A | 75-84 | 買入 |
| B+ | 65-74 | 買入 |
| B | 55-64 | 持有 |
| C | 45-54 | 觀望 |
| D | 35-44 | 減碼 |
| F | 0-34 | 賣出 |

## 🎯 使用場景

### 場景1: 每日選股

```python
import asyncio
from app.services.broker_flow_analyzer import get_fubon_xindan_top_stocks
from app.services.integrated_stock_selector import analyze_multiple_stocks

async def daily_stock_selection():
    # 1. 獲取富邦新店買超前30名
    fubon_stocks = get_fubon_xindan_top_stocks(top_n=30)
    stock_codes = [s['stock_code'] for s in fubon_stocks]
    
    # 2. 完整分析
    df = await analyze_multiple_stocks(stock_codes)
    
    # 3. 篩選高分股票 (評分>=70)
    high_score = df[df['綜合評分'] >= 70]
    
    # 4. 進一步篩選買入建議
    buy_list = high_score[high_score['建議動作'].isin(['強力買入', '買入'])]
    
    # 5. 按評分排序
    buy_list = buy_list.sort_values('綜合評分', ascending=False)
    
    return buy_list

# 執行
result = asyncio.run(daily_stock_selection())
print(result)
```

### 場景2: 特定股票深度分析

```python
import asyncio
from app.services.integrated_stock_selector import analyze_single_stock

async def deep_analysis(stock_code):
    result = await analyze_single_stock(stock_code)
    
    print(f"股票代碼: {stock_code}")
    print(f"綜合評分: {result['scores']['weighted_score']}")
    print(f"評級: {result['scores']['final_grade']}")
    print(f"建議: {result['scores']['recommendation']}")
    print(f"目標價: {result['scores'].get('target_price')}")
    print(f"停損價: {result['scores'].get('stop_loss')}")
    print(f"風險等級: {result['risk_assessment']['level']}")
    print(f"建議倉位: {result['position_sizing']['position_pct']}%")
    
    return result

# 執行
asyncio.run(deep_analysis('2330'))
```

### 場景3: 產業輪動分析

```python
import asyncio
from app.services.integrated_stock_selector import analyze_multiple_stocks

async def sector_rotation_analysis():
    # 定義產業股票池
    sectors = {
        '半導體': ['2330', '2303', '2454', '5347'],
        'AI伺服器': ['2382', '2345', '2317', '6669'],
        '金融': ['2882', '2881', '2891', '2886']
    }
    
    sector_results = {}
    
    for sector_name, stocks in sectors.items():
        df = await analyze_multiple_stocks(stocks)
        avg_score = df['綜合評分'].mean()
        
        sector_results[sector_name] = {
            'avg_score': avg_score,
            'top_stock': df.iloc[0]['股票代碼'],
            'top_score': df.iloc[0]['綜合評分']
        }
    
    # 找出最強產業
    best_sector = max(sector_results.items(), key=lambda x: x[1]['avg_score'])
    
    print(f"最強產業: {best_sector[0]}")
    print(f"平均評分: {best_sector[1]['avg_score']:.2f}")
    print(f"推薦標的: {best_sector[1]['top_stock']}")
    
    return sector_results

# 執行
asyncio.run(sector_rotation_analysis())
```

## 📈 券商進出分析

### 支援的券商

- **富邦-新店** (9600) - 主要監控
- **富邦-台北** (9601)
- **元大-台北** (1160)
- **凱基-台北** (8880)
- **美林** (9A9A) - 外資
- **瑞銀** (9A9C) - 外資
- **摩根士丹利** (9A9B) - 外資
- **高盛** (9A9D) - 外資

### 使用範例

```python
from app.services.broker_flow_analyzer import broker_flow_analyzer

# 1. 獲取富邦新店買超股票
top_stocks = broker_flow_analyzer.get_top_stocks_by_broker(
    broker_name='富邦-新店',
    top_n=20,
    min_net_count=100
)

# 2. 分析特定股票的券商進出
flow_summary = broker_flow_analyzer.get_broker_flow_summary(
    stock_code='2330',
    days=5
)

print(f"淨流入: {flow_summary['net_flow_count']} 張")
print(f"趨勢: {flow_summary['flow_trend']}")
print(f"關鍵觀察: {flow_summary['key_observations']}")
```

## 🔧 進階設定

### 自訂評分權重

```python
from app.services.integrated_stock_selector import IntegratedStockSelector

# 自訂配置
custom_config = {
    'scoring_weights': {
        'fundamentals': 0.40,      # 提高基本面權重
        'technicals': 0.20,        # 降低技術面權重
        'broker_flow': 0.30,       # 提高籌碼面權重
        'market_sentiment': 0.05,
        'ai_analysis': 0.05
    }
}

# 建立自訂選股器
selector = IntegratedStockSelector(config=custom_config)
```

### 自訂風險參數

```python
custom_config = {
    'risk_parameters': {
        'max_position_pct': 0.10,  # 降低單一倉位上限
        'stop_loss_pct': 0.05,     # 更嚴格的停損
        'take_profit_pct': 0.30,   # 更高的停利目標
        'max_drawdown': 0.10       # 降低回撤容忍
    }
}
```

## 📊 報告匯出

### CSV 格式

```python
from app.services.integrated_stock_selector import integrated_selector
import asyncio

async def export_csv():
    stock_codes = ['2330', '2303', '2317', '2454']
    df = await analyze_multiple_stocks(stock_codes)
    
    filepath = integrated_selector.export_report(
        df, 
        format='csv',
        filename='daily_analysis_20250101'
    )
    
    print(f"報告已匯出: {filepath}")

asyncio.run(export_csv())
```

### Excel 格式

```python
filepath = integrated_selector.export_report(
    df, 
    format='excel',
    filename='weekly_analysis'
)
```

## 🔄 自動化排程

### 每日自動選股

```python
import schedule
import time
import asyncio

async def daily_job():
    # 1. 獲取富邦新店買超股票
    fubon_stocks = get_fubon_xindan_top_stocks(top_n=30)
    stock_codes = [s['stock_code'] for s in fubon_stocks]
    
    # 2. 完整分析
    df = await analyze_multiple_stocks(stock_codes)
    
    # 3. 匯出報告
    integrated_selector.export_report(df, format='csv')
    
    print(f"每日選股完成: {datetime.now()}")

def run_daily_job():
    asyncio.run(daily_job())

# 設定每日18:30執行
schedule.every().day.at("18:30").do(run_daily_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## ⚠️ 注意事項

1. **數據來源限制**
   - 券商資料抓取可能受網站限制
   - 建議加入適當的延遲避免被封鎖
   - 使用快取機制減少重複請求

2. **評分僅供參考**
   - 系統評分基於量化指標
   - 需結合個人判斷和風險承受度
   - 建議搭配其他分析工具

3. **市場風險**
   - 過去表現不代表未來
   - 注意市場系統性風險
   - 嚴格執行停損停利

4. **技術限制**
   - 部分數據可能延遲
   - API 可能有請求限制
   - 建議定期更新系統

## 🆘 常見問題

### Q1: 券商資料抓取失敗？

**A**: 檢查網路連線，確認富邦證券網站可訪問。可能需要調整請求頻率。

### Q2: 分析結果為空？

**A**: 確認股票代碼正確，檢查數據源是否正常。可查看日誌了解詳細錯誤。

### Q3: 如何提高分析準確度？

**A**: 
- 增加分析天數
- 調整評分權重
- 結合多個數據源
- 加入 AI 分析

### Q4: 可以分析美股嗎？

**A**: 目前主要針對台股，美股需要調整數據源和券商邏輯。

## 📞 技術支援

如有問題，請查看：
- 系統日誌: `/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/log/`
- API 文件: `http://localhost:8000/docs`
- 測試腳本: `/Users/Mac/Documents/ETF/AI/Ａi-catch/test_stock_selector.py`

## 🔄 更新日誌

### v1.0.0 (2025-01-01)
- ✅ 券商分點進出分析
- ✅ 多維度整合選股
- ✅ 量化評分系統
- ✅ 批量分析功能
- ✅ 報告匯出
- ✅ API 端點

---

**祝您投資順利！** 📈
