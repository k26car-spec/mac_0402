# 資產配置與風險控制模組

> ⚖️ 動態資產配置、風險控制、投資組合優化

## 📋 模組功能

- **動態資產配置**: 根據風險承受度自動配置股債比例
- **市場狀況調整**: 多頭/空頭/盤整自動調整配置
- **ETF投資組合**: 台股/美股/債券/現金/另類投資
- **風險控制**: VaR、最大回撤、波動率監控
- **績效模擬**: 歷史回測投資組合表現
- **再平衡建議**: 自動檢測偏離並建議調整
- **定期定額計劃**: 自動生成月度投資計劃

## 🎯 風險偏好設定

| 類型 | 股票上限 | 債券下限 | 現金下限 | 最大回撤 | 目標報酬 |
|------|----------|----------|----------|----------|----------|
| 保守型 | 40% | 40% | 10% | 10% | 5% |
| 穩健型 | 60% | 30% | 5% | 15% | 7% |
| 積極型 | 80% | 10% | 2% | 25% | 10% |

## 📊 ETF 投資標的

### 台股 ETF
| 代碼 | 名稱 | 類型 |
|------|------|------|
| 0050.TW | 元大台灣50 | 指數 |
| 0056.TW | 元大高股息 | 高股息 |
| 00878.TW | 國泰永續高股息 | ESG高股息 |

### 美股 ETF
| 代碼 | 名稱 | 類型 |
|------|------|------|
| SPY | S&P 500 ETF | 大盤指數 |
| QQQ | Nasdaq 100 ETF | 科技成長 |
| VTI | 全市場 ETF | 全市場 |

### 債券 ETF
| 代碼 | 名稱 | 類型 |
|------|------|------|
| TLT | 20年期公債 | 長期債券 |
| IEF | 7-10年公債 | 中期債券 |
| AGG | 綜合債券 | 多元債券 |

### 另類投資
| 代碼 | 名稱 | 類型 |
|------|------|------|
| GLD | 黃金 ETF | 貴金屬 |
| VNQ | 房地產 ETF | REITs |

## 🚀 快速開始

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/economic_cycle_system/asset_allocation
python asset_allocator.py
```

## 📈 使用範例

```python
from asset_allocator import AssetAllocator

# 初始化 (穩健型，100萬)
allocator = AssetAllocator(
    risk_profile="MODERATE", 
    initial_capital=1000000
)

# 生成配置
allocations = allocator.generate_portfolio_allocation()
for a in allocations:
    print(f"{a.ticker}: {a.allocation*100:.1f}%")

# 模擬績效
perf = allocator.simulate_portfolio_performance(allocations, period="3y")
print(f"總報酬: {allocator.performance_metrics['total_return']*100:.1f}%")

# 定期定額計劃
dca = allocator.create_dca_plan(allocations, monthly_investment=30000)
print(f"每月投資: NT${dca['monthly_investment']:,.0f}")

# 生成報告
report = allocator.generate_report()
print(report)
```

## 🔌 API 端點

| 端點 | 說明 |
|------|------|
| `POST /api/allocation/calculate` | 計算資產配置 |
| `GET /api/allocation/profiles` | 獲取風險偏好設定 |
| `GET /api/allocation/etf-universe` | ETF投資標的清單 |
| `POST /api/allocation/simulate/{profile}` | 模擬績效 |
| `POST /api/allocation/dca-plan/{profile}` | 定期定額計劃 |
| `GET /api/allocation/report/{profile}` | 配置報告 |
| `GET /api/allocation/compare-profiles` | 比較不同風險偏好 |

## 📊 輸出範例

```
⚖️ 資產配置與風險控制報告
================================================================================

【基本資訊】
風險承受度: 穩健型
初始資金: NT$1,000,000
市場狀況: 盤整市場

【投資組合配置】
  • 0050.TW: 9.0% (NT$90,000) - 核心: 台灣50指數ETF
  • 0056.TW: 6.0% (NT$60,000) - 衛星: 高股息ETF
  • SPY: 15.0% (NT$150,000) - 核心: S&P 500指數
  • QQQ: 10.0% (NT$100,000) - 衛星: 科技成長
  • TLT: 16.0% (NT$160,000) - 債券: 長期公債
  • IEF: 12.0% (NT$120,000) - 債券: 中期公債
  • AGG: 12.0% (NT$120,000) - 債券: 綜合債券
  • SHY: 10.0% (NT$100,000) - 現金: 短期公債
  • GLD: 10.0% (NT$100,000) - 另類: 黃金

【預期績效】
預期年化報酬率: 6.50%
預期年化波動率: 9.20%
預期夏普比率: 0.49
```

## 🔧 風險管理

### 風險指標
- **VaR (95%)**: 95%信賴區間的最大損失
- **CVaR**: 條件風險值，極端損失預估
- **最大回撤**: 歷史最大虧損幅度
- **夏普比率**: 風險調整後報酬
- **索提諾比率**: 只考慮下行風險

### 再平衡策略
- **偏離容忍度**: 5% (預設)
- **再平衡頻率**: 每季
- **觸發條件**: 任一資產偏離目標超過容忍度

---

📅 **版本**: v2.0 | 最後更新: 2025-12-27
