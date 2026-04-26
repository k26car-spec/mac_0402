# 電子股趨勢與訂單監測模組

> 📱 分析電子股產業趨勢、產品週期、訂單能見度

## 📋 模組功能

- **技術趨勢分析**: AI加速、電動車、邊緣運算、AR/VR
- **產品週期追蹤**: 智慧手機、AI伺服器、電動車、IoT
- **訂單信號監測**: 訂單增減、庫存變化、產能擴張
- **供應鏈分析**: 供應商關係、風險評估、庫存監控
- **投資想法生成**: 趨勢驅動、動能驅動、週期驅動

## 🔬 技術趨勢

| 趨勢 | 採用率 | 成長預測 | 關鍵公司 |
|------|--------|----------|----------|
| AI加速運算 | 30% | 40% | 台積電, 廣達, 緯創, 緯穎 |
| 電動車轉型 | 15% | 25% | 台達電, 康普, 國巨 |
| 邊緣運算 | 20% | 30% | 聯發科, 瑞昱, 聯詠 |
| AR/VR發展 | 5% | 50% | 大立光, 玉晶光 |

## 📦 產品週期

| 產品 | 週期階段 | 成長率 | 市場規模 |
|------|----------|--------|----------|
| 智慧手機 | 成熟期 | 2% | $5000億 |
| AI伺服器 | 成長期 | 35% | $1500億 |
| 電動車 | 成長期 | 25% | $8000億 |
| IoT裝置 | 成長期 | 15% | $1200億 |
| AR/VR | 導入期 | 40% | $300億 |

## 📊 電子股分類

### 半導體
| 代碼 | 名稱 | 次產業 |
|------|------|--------|
| 2330 | 台積電 | 晶圓代工 |
| 2454 | 聯發科 | IC設計 |
| 3711 | 日月光投控 | 封裝測試 |

### 組裝代工
| 代碼 | 名稱 | 次產業 |
|------|------|--------|
| 2317 | 鴻海 | EMS |
| 2382 | 廣達 | 筆電/伺服器 |
| 6669 | 緯穎 | 伺服器 |

## 🚀 快速開始

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/economic_cycle_system/electronics_monitor
python electronics_monitor.py
```

## 📈 使用範例

```python
from electronics_monitor import ElectronicsMonitor

# 初始化
monitor = ElectronicsMonitor()

# 分析技術趨勢
trends = monitor.analyze_technology_trends()
for trend_id, info in trends.items():
    print(f"{info['trend']}: 影響分數 {info['impact_score']:.1f}")

# 分析產品週期
cycle = monitor.analyze_product_cycle("ai_server")
print(f"AI伺服器: {cycle.current_phase.value} 成長 {cycle.growth_rate*100:.0f}%")

# 生成訂單信號
signals = monitor.generate_order_signals()
for s in signals[:3]:
    print(f"{s.company}: {s.signal_type} 強度 {s.strength:.2f}")

# 監測供應鏈
supply_chain = monitor.monitor_supply_chain(["2330", "2382", "6669"])
for company, info in supply_chain.items():
    print(f"{company}: {info['supply_chain_risk']['risk_level']}風險")

# 生成投資想法
ideas = monitor.generate_investment_ideas(top_n=5)
for idea in ideas:
    print(f"{idea['ticker']}: {idea['theme']} 評分 {idea['score']:.0f}")

# 生成報告
report = monitor.generate_report()
print(report)
```

## 🔌 API 端點

| 端點 | 說明 |
|------|------|
| `GET /api/electronics/trends` | 技術趨勢分析 |
| `GET /api/electronics/product-cycles` | 產品週期分析 |
| `GET /api/electronics/order-signals` | 訂單信號 |
| `GET /api/electronics/supply-chain` | 供應鏈分析 |
| `GET /api/electronics/investment-ideas` | 投資想法 |
| `GET /api/electronics/company/{ticker}` | 公司資料 |
| `GET /api/electronics/sectors` | 產業分類 |
| `GET /api/electronics/report` | 監測報告 |

## 📊 輸出範例

```
📱 電子股趨勢與訂單監測報告
================================================================================

🔬 【技術趨勢分析】

AI加速運算:
  採用率: 30.0%
  成長預測: 40.0%
  影響分數: 8.5/10
  關鍵公司: 2330, 2382, 3231, 6669

📦 【產品週期分析】

ai_server:
  當前階段: 成長期
  成長率: 35.0%
  市場規模: $1500億美元
  下個催化劑: 新一代GPU發布 (2025-03)

📊 【訂單信號監測】

2330 (台積電):
  信號類型: order_increase
  信號強度: 0.85
  證據: 客戶追加訂單，產能利用率提升至95%

💡 【投資機會】

1. 2330 (台積電)
   主題: AI加速運算
   上行潛力: 32.0%
   評分: 85/100
```

## 🔧 訂單信號類型

| 信號類型 | 說明 | 影響 |
|----------|------|------|
| order_increase | 訂單增加 | 正面 |
| order_decrease | 訂單減少 | 負面 |
| inventory_build | 庫存上升 | 負面 |
| inventory_draw | 庫存下降 | 正面 |
| capacity_expansion | 產能擴張 | 正面 |
| price_increase | 價格上漲 | 正面 |
| price_decrease | 價格下跌 | 負面 |

---

📅 **版本**: v2.0 | 最後更新: 2025-12-27
