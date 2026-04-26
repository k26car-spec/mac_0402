# 投資信號產生器

> 🎯 整合所有分析模組，輸出買進/賣出/持有信號 + 配置建議

## 📋 模組功能

- **信號產生**: 買進/賣出/持有信號
- **資產配置**: 股票/債券/現金/另類配置建議
- **個股分析**: 綜合評分、停損停利、理由說明
- **ETF建議**: 核心+衛星配置
- **風險提示**: 關鍵風險警示

## 🎯 信號類型

| 信號 | 評分區間 | 操作建議 |
|------|----------|----------|
| 🔥 強力買進 | 80-100 | 積極買入，加大部位 |
| ✅ 買進 | 60-80 | 買入，建立基本部位 |
| ⏸️ 持有 | 40-60 | 觀望，維持現有部位 |
| ⚠️ 賣出 | 20-40 | 減碼，降低部位 |
| 🔴 強力賣出 | 0-20 | 清倉或避開 |

## 📊 評分權重

| 因子 | 權重 | 說明 |
|------|------|------|
| 技術分析 | 40% | 價格位置、指標信號 |
| 趨勢曝險 | 25% | AI/EV等產業趨勢 |
| 訂單動能 | 20% | 訂單能見度、產能 |
| 基本面 | 15% | 財務指標 |

## 🚀 快速開始

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/economic_cycle_system/signal_generator
python signal_generator.py
```

## 📈 使用範例

```python
from signal_generator import SignalGenerator

# 初始化 (穩健型，100萬)
generator = SignalGenerator(
    risk_profile="MODERATE",
    initial_capital=1000000
)

# 生成單一股票信號
signal = generator.generate_stock_signal("2330")
print(f"{signal.ticker}: {signal.signal.value}")
print(f"評分: {signal.score:.0f}")
print(f"建議: {signal.action}")
print(f"停損: {signal.stop_loss} | 停利: {signal.take_profit}")

# 生成投資組合建議
recommendation = generator.generate_portfolio_recommendation([
    "2330", "2454", "2382", "6669", "3008"
])

print(f"股票配置: {recommendation.equity_allocation*100:.0f}%")
print(f"債券配置: {recommendation.bond_allocation*100:.0f}%")

# 生成完整報告
report = generator.generate_report(recommendation)
print(report)
```

## 🔌 API 端點

| 端點 | 說明 |
|------|------|
| `POST /api/signals/generate` | 生成投資信號 |
| `GET /api/signals/stock/{ticker}` | 單一股票信號 |
| `GET /api/signals/report` | 完整投資報告 |
| `GET /api/signals/quick-summary` | 快速摘要 |

## 📊 輸出範例

```
🎯 投資信號與配置建議報告
================================================================================

📅 報告時間: 2025-12-27 22:30:00
👤 風險偏好: MODERATE
💰 投資資金: NT$1,000,000
📈 市場狀況: 偏多盤整

💼 【資產配置建議】
  📊 股票: 50% (NT$500,000)
  📈 債券: 35% (NT$350,000)
  💵 現金: 10% (NT$100,000)
  🏠 另類: 5% (NT$50,000)

📊 【個股投資信號】

🔥 2330 (台積電) - 強力買進
   綜合評分: 82/100
   信心度: 75%
   操作建議: 積極買入，可加大部位
   建議配置: 8.0%
   停損價: 950 | 停利價: 1150

✅ 2382 (廣達) - 買進
   綜合評分: 71/100
   信心度: 68%
   操作建議: 買入，建立基本部位
   建議配置: 5.0%

🟢 可考慮買進:
   • 2330 (台積電) @ 停損 950
   • 2382 (廣達) @ 停損 250
   • 6669 (緯穎) @ 停損 1800
```

## 🔧 風險偏好配置

| 風險偏好 | 股票 | 債券 | 現金 | 另類 |
|----------|------|------|------|------|
| 保守型 | 30% | 50% | 15% | 5% |
| 穩健型 | 50% | 35% | 10% | 5% |
| 積極型 | 70% | 20% | 5% | 5% |

---

📅 **版本**: v1.0 | 最後更新: 2025-12-27
