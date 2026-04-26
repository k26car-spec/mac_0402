# 產業鏈與定價權分析模組

> 🏭 分析產業鏈結構，識別具有定價權的關鍵企業

## 📋 模組功能

- **產業鏈結構分析**: 分析上中下游產業鏈結構
- **定價權評分**: 計算每家公司的定價權分數 (0-100)
- **瓶頸識別**: 自動識別產業鏈中的關鍵瓶頸環節
- **投資建議**: 根據定價權分數生成投資建議
- **數據導出**: 支援 Excel 和文字報告導出

## 🏭 支援產業

| 產業代碼 | 名稱 | 環節數 | 公司數 |
|----------|------|--------|--------|
| semiconductor | 半導體產業鏈 | 3 | 18 |
| electric_vehicle | 電動車產業鏈 | 3 | 13 |
| ai_server | AI伺服器產業鏈 | 3 | 15 |
| smartphone | 智慧手機產業鏈 | 3 | 14 |

## 🚀 快速開始

### 執行分析

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/economic_cycle_system/industry_chain
python industry_chain_analyzer.py
```

### 程式碼使用

```python
from industry_chain_analyzer import IndustryChainAnalyzer

# 初始化（選擇產業）
analyzer = IndustryChainAnalyzer(industry="semiconductor")

# 執行分析
result = analyzer.analyze_industry_chain(fetch_real_data=True)

# 獲取定價權 Top 10
top_stocks = analyzer.get_top_stocks(10)

# 生成報告
report = analyzer.generate_report()
print(report)

# 導出 Excel
analyzer.export_to_excel()
```

## 📊 定價權評分系統

總分 = 各項加權分數之和 (0-100分)

| 指標 | 權重 | 說明 |
|------|------|------|
| 市占率 | 25% | 市占率越高，定價權越強 |
| 毛利率 | 25% | 毛利率反映定價能力 |
| ROE | 15% | 股東權益報酬率 |
| 研發強度 | 15% | 技術壁壘指標 |
| 客戶集中度 | 10% | 越低越好（分散風險） |
| 專利數量 | 10% | 技術護城河 |

## 🔍 分析結果範例

```
定價權 Top 5:
  1. 台積電 (2330): 90.5 分
  2. 聯發科 (2454): 86.5 分
  3. 信驊 (5274): 86.3 分
  4. 瑞昱 (2379): 72.0 分
  5. 聯詠 (3034): 70.3 分

各環節平均定價權:
  上游: 71.4
  中游: 51.3
  下游: 26.7

瓶頸環節:
  - 上游: 高風險（前三大市占率達 80%+）
  - 中游: 高風險（台積電市占 55%）
```

## 🔌 API 端點

整合到主系統後可用的 API：

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/industry-chain/industries` | GET | 列出支援的產業 |
| `/api/industry-chain/analyze/{industry}` | GET | 分析指定產業 |
| `/api/industry-chain/top-stocks/{industry}` | GET | 獲取定價權最高股票 |
| `/api/industry-chain/bottlenecks/{industry}` | GET | 獲取瓶頸分析 |
| `/api/industry-chain/company/{ticker}` | GET | 查詢單一公司 |

## 💡 投資策略建議

### 分數範圍對應策略

| 分數 | 等級 | 策略 |
|------|------|------|
| ≥ 70 | 頂級 | 積極布局，長期持有 |
| 55-70 | 優質 | 選擇性投資，關注成長性 |
| 40-55 | 一般 | 等待更好進場點位 |
| < 40 | 弱勢 | 避開或謹慎觀望 |

### 瓶頸策略

投資產業鏈瓶頸環節的龍頭公司：
- 供應集中度高
- 技術門檻高
- 擴產困難
- 定價權強

## 📁 專案結構

```
industry_chain/
├── industry_chain_analyzer.py  # 核心分析程式
├── api.py                      # FastAPI 整合
├── requirements.txt            # 依賴套件
├── data/
│   └── industry_definitions.json  # 產業定義
├── reports/                    # 報告輸出
├── charts/                     # 圖表輸出
└── exports/                    # Excel 導出
```

## 🔗 與其他模組整合

```python
# 結合總經循環模組
from economic_cycle import EconomicCycleDetector
from industry_chain.industry_chain_analyzer import IndustryChainAnalyzer

# 1. 判斷經濟週期
cycle = EconomicCycleDetector()
cycle.fetch_all_indicators()
stage, _, _ = cycle.analyze_cycle()

# 2. 根據週期選擇產業
if stage in ['recovery', 'expansion']:
    industry = 'semiconductor'  # 復甦/擴張期看科技
elif stage == 'overheat':
    industry = 'electric_vehicle'  # 過熱期看新能源
else:
    industry = 'smartphone'  # 其他週期看消費電子

# 3. 分析產業鏈
analyzer = IndustryChainAnalyzer(industry=industry)
result = analyzer.analyze_industry_chain()

# 4. 獲取投資建議
top_stocks = analyzer.get_top_stocks(10)
```

---

📅 **版本**: v2.0 | 最後更新: 2025-12-27
