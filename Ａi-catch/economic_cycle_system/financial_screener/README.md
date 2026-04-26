# 財報與營收量化篩選模組

> 📊 使用三大關鍵數字快速篩選優質公司

## 📋 模組功能

- **三大關鍵數字評分**: 毛利率、營收成長率、自由現金流
- **輔助指標分析**: ROE、流動比率、負債比、營益率等
- **智能評級系統**: A+ 到 F 七級評分
- **多市場支援**: 台灣、美國股市
- **多股票池**: 大型股、中型股、高股息、AI概念股

## 🎯 三大關鍵數字

| 指標 | 權重 | 理想範圍 | 說明 |
|------|------|----------|------|
| 毛利率 | 35% | 30%-60% | 反映定價能力和成本控制 |
| 營收成長率 | 35% | 10%-50% | 反映成長動能 |
| 自由現金流 | 30% | 5%-30% | 反映財務安全性 |

## 🏆 評級標準

| 評級 | 分數 | 說明 | 策略 |
|------|------|------|------|
| A+ | 90-100 | 極優質 | 強烈推薦，核心持股 |
| A | 80-90 | 優質 | 推薦買入 |
| B+ | 70-80 | 良好 | 值得關注 |
| B | 60-70 | 中等 | 可考慮 |
| C | 50-60 | 普通 | 需謹慎 |
| D | 40-50 | 偏弱 | 不建議 |
| F | 0-40 | 不佳 | 避開 |

## 🚀 快速開始

### 執行篩選

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/economic_cycle_system/financial_screener
python financial_screener.py
```

### 程式碼使用

```python
from financial_screener import FinancialScreener

# 初始化篩選器
screener = FinancialScreener(market="TW")

# 執行篩選（大型股，最低分數 70）
results = screener.screen_companies(
    universe_type="large_cap",
    min_score=70
)

# 獲取 Top 10
top_companies = screener.get_top_companies(10)

# 生成報告
report = screener.generate_report()
print(report)

# 導出 Excel
screener.export_to_excel()
```

## 📊 股票池類型

### 台灣市場 (TW)

| 股票池 | 說明 | 公司數 |
|--------|------|--------|
| large_cap | 大型股（台灣50成分股） | 25 |
| mid_cap | 中型股（中型100） | 20 |
| dividend | 高股息股 | 15 |
| ai_server | AI伺服器概念股 | 10 |

### 美國市場 (US)

| 股票池 | 說明 | 公司數 |
|--------|------|--------|
| tech | 科技股 | 10 |
| finance | 金融股 | 5 |
| healthcare | 醫療股 | 5 |

## 🔌 API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/financial-screener/markets` | GET | 列出支援市場 |
| `/api/financial-screener/universes/{market}` | GET | 列出股票池 |
| `/api/financial-screener/screen/{market}/{universe}` | GET | 執行篩選 |
| `/api/financial-screener/top/{market}/{universe}` | GET | 獲取 Top N |
| `/api/financial-screener/company/{market}/{ticker}` | GET | 查詢單一公司 |
| `/api/financial-screener/rating-scale` | GET | 獲取評級標準 |

## 📈 使用範例

### 篩選結果預覽

```
📊 財務評分 Top 10:
   1. 2330   台積電        | A+  92.5分 | 毛利55.8% | 成長+25.0%
   2. 5274   信驊          | A   88.2分 | 毛利52.0% | 成長+22.0%
   3. 6415   矽力-KY       | A   87.5分 | 毛利55.0% | 成長+20.0%
   4. 2454   聯發科        | A   85.3分 | 毛利48.5% | 成長+18.0%
   5. 3008   大立光        | A   84.1分 | 毛利60.0% | 成長 +5.0%
```

## 🔗 與其他模組整合

```python
# 整合總經循環模組
from economic_cycle import EconomicCycleDetector

# 判斷經濟週期
cycle = EconomicCycleDetector()
stage, _, _ = cycle.analyze_cycle()

# 根據週期調整篩選權重
screener = FinancialScreener(market="TW")

if stage == "recession":
    # 衰退期重視現金流
    screener.key_metrics_weights["free_cash_flow"]["weight"] = 0.40
    screener.key_metrics_weights["revenue_growth"]["weight"] = 0.25
elif stage == "recovery":
    # 復甦期重視成長性
    screener.key_metrics_weights["revenue_growth"]["weight"] = 0.40
    screener.key_metrics_weights["gross_margin"]["weight"] = 0.30

results = screener.screen_companies()
```

## 📁 專案結構

```
financial_screener/
├── financial_screener.py   # 核心程式
├── api.py                  # FastAPI 整合
├── requirements.txt        # 依賴套件
├── README.md              # 說明文件
├── data/                  # 數據目錄
├── reports/               # 報告輸出
├── exports/               # Excel 導出
└── charts/                # 圖表輸出
```

---

📅 **版本**: v2.0 | 最後更新: 2025-12-27
