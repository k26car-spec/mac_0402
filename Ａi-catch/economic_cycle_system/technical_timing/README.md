# 技術面與線型時機模組

> 📈 運用五年區間高低點、技術指標、價格型態判斷進出場時機

## 📋 模組功能

- **五年區間分析**: 判斷價格在歷史區間的位置
- **支撐阻力位檢測**: 自動識別關鍵價位
- **多指標整合**: RSI、KD、MACD、布林通道
- **交易信號生成**: 綜合多維度信號
- **交易計劃生成**: 自動生成停損獲利建議

## 🎯 價格位置評分

| 區間 | 位置 | 評分 | 建議 |
|------|------|------|------|
| 底部10% | 0-10% | 90分 | 強力買入 |
| 低檔區 | 10-25% | 70分 | 買入 |
| 中間區 | 25-50% | 50分 | 持有 |
| 高檔區 | 50-75% | 30分 | 謹慎 |
| 頂部區 | 75-90% | 10分 | 賣出 |
| 歷史高 | 90-100% | 0分 | 強力賣出 |

## 📊 技術指標

| 指標 | 買入信號 | 賣出信號 |
|------|----------|----------|
| RSI | < 30 超賣 | > 70 超買 |
| KD | K<20 且黃金交叉 | K>80 且死亡交叉 |
| MACD | 黃金交叉 | 死亡交叉 |
| 布林 | 觸及下軌 | 觸及上軌 |
| 均線 | 多頭排列 | 空頭排列 |

## 🚀 快速開始

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/economic_cycle_system/technical_timing
python technical_analyzer.py
```

## 📈 使用範例

```python
from technical_analyzer import TechnicalAnalyzer

# 初始化
analyzer = TechnicalAnalyzer(market="TW")

# 分析單一股票
plan = analyzer.generate_trading_plan("2330")
print(f"信號: {plan['final_signal']}")
print(f"停損: {plan['risk_management']['stop_loss']}")
print(f"目標: {plan['risk_management']['take_profit']}")

# 批量分析
results = analyzer.batch_analyze(["2330", "2454", "2317"])

# 生成報告
report = analyzer.generate_report("2330")
print(report)
```

## 🔌 API 端點

| 端點 | 說明 |
|------|------|
| `/api/technical/analyze/{market}/{ticker}` | 完整分析 |
| `/api/technical/position/{market}/{ticker}` | 價格位置 |
| `/api/technical/indicators/{market}/{ticker}` | 技術指標 |
| `/api/technical/support-resistance/{market}/{ticker}` | 支撐阻力 |
| `/api/technical/signals/{market}/{ticker}` | 交易信號 |
| `/api/technical/plan/{market}/{ticker}` | 交易計劃 |
| `/api/technical/screener/{market}` | 信號篩選 |

## 📊 輸出範例

```
📈 技術面與線型時機分析報告
================================================================================

股票代號: 2330
當前價格: 550.00

🎯 【交易信號】
最終信號: BUY
信號強度: 68.5%
主要理由:
  • 五年區間位置: 35.2% (相對低檔)
  • RSI超賣(28.5)
  • 接近支撐位 520 (距離 5.5%)

💡 【交易建議】
建議動作: 買入
停損價位: 506.00 (-8.0%)
獲利目標: 632.50 (+15.0%)
風險報酬比: 1:1.9
```

## 🔧 風險管理

### 停損策略
1. **支撐停損**: 關鍵支撐下方 2%
2. **ATR停損**: 2倍ATR
3. **固定停損**: 8% (預設)

### 獲利策略
1. **阻力獲利**: 關鍵阻力位
2. **技術目標**: 15% 固定目標
3. **移動停利**: 回落 5% 出場

---

📅 **版本**: v2.0 | 最後更新: 2025-12-27
