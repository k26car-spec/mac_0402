# 訂單流模式識別系統 (Order Flow Pattern Recognition System)

## 概述

本系統是**替代傳統 LSTM 價格預測**的新一代市場分析工具。傳統的 LSTM 價格預測存在以下問題：

1. **市場非平穩性**：金融時間序列的統計特性隨時間變化
2. **高噪音信號比**：價格變動包含大量隨機噪音
3. **反身性問題**：預測本身可能影響市場行為
4. **特徵過於單一**：只輸入價格序列，未包含市場微觀結構信息

本系統改為識別**有意義的市場微觀模式**，這些模式對交易決策更有實際價值。

## 支援的市場模式

| 模式 | 說明 | 交易建議 |
|------|------|----------|
| 積極買盤攻擊 (AGGRESSIVE_BUYING) | 大量主動買入，價格上漲 | 跟進買入 |
| 積極賣盤攻擊 (AGGRESSIVE_SELLING) | 大量主動賣出，價格下跌 | 注意風險 |
| 測試支撐 (SUPPORT_TESTING) | 賣盤被吸收，價格守穩 | 觀察布局 |
| 測試阻力 (RESISTANCE_TESTING) | 買盤被吸收，價格受壓 | 突破可追 |
| 流動性枯竭 (LIQUIDITY_DRYING) | 掛單變薄，市場冷清 | 避免大單 |
| 假突破 (FAKE_OUT) | 大單撤單或快速反轉 | 反向操作 |

## 系統架構

```
backend-v3/app/
├── ml/
│   ├── __init__.py
│   └── order_flow/
│       ├── __init__.py          # 模組入口
│       ├── patterns.py          # 6種市場微觀模式定義
│       ├── features.py          # 特徵工程器
│       ├── labeler.py           # 模式標註器
│       └── dataset.py           # 訓練資料集構建
├── services/
│   └── order_flow_service.py    # 訂單流服務
└── api/
    └── order_flow.py            # REST API 端點
```

## API 端點

### 系統狀態
```
GET /api/order-flow/status
```

### 模式檢測
```
GET /api/order-flow/patterns/{symbol}?include_features=true
```

### 特徵提取
```
GET /api/order-flow/features/{symbol}
```

### 完整分析
```
POST /api/order-flow/analyze
Body: {
    "symbol": "2330",
    "quote": { "price": 1000, "volume": 100, ... },
    "orderbook": { "bids": [...], "asks": [...] }
}
```

### 歷史記錄
```
GET /api/order-flow/history/{symbol}?limit=50
```

### 統計資訊
```
GET /api/order-flow/statistics/{symbol}
```

### 所有模式類型
```
GET /api/order-flow/patterns/types
```

## 特徵向量

系統提取 14 維特徵向量：

**成交特徵 (5):**
- `buy_volume_ratio`: 買入量佔比
- `sell_volume_ratio`: 賣出量佔比
- `large_net_flow`: 大單淨流向
- `tick_frequency`: 成交頻率
- `trade_imbalance`: 交易不平衡度

**訂單簿特徵 (3):**
- `order_book_imbalance`: 訂單簿不平衡度
- `bid_ask_spread`: 買賣價差
- `depth_ratio`: 深度比例

**動量特徵 (3):**
- `price_return`: 價格收益率
- `price_volatility`: 價格波動率
- `price_momentum`: 價格動量

**時間特徵 (3):**
- `intraday_position`: 日內時段位置
- `is_open_period`: 是否開盤時段
- `is_close_period`: 是否收盤時段

## 使用範例

### Python 直接使用

```python
from app.ml.order_flow import (
    OrderFlowFeatureExtractor,
    PatternLabeler,
)
from app.ml.order_flow.features import TickData, OrderBookSnapshot

# 創建工具
extractor = OrderFlowFeatureExtractor(large_order_threshold=100)
labeler = PatternLabeler()

# 添加數據
tick = TickData(
    timestamp=datetime.now(),
    price=1000,
    volume=150,
    direction="BUY",
    order_type="LARGE"
)
extractor.add_tick(tick)

# 提取特徵
features = extractor.extract_features()

# 檢測模式
detections = labeler.detect_patterns(
    symbol="2330",
    ticks=extractor._tick_buffer,
    orderbooks=extractor._orderbook_buffer,
)

# 獲取主要模式
primary = labeler.get_primary_pattern(detections)
print(f"模式: {primary.pattern_name}, 信心度: {primary.confidence:.2%}")
```

### 使用服務

```python
from app.services.order_flow_service import order_flow_service

# 處理報價
await order_flow_service.process_realtime_quote("2330", {
    "price": 1000,
    "volume": 150,
    "timestamp": datetime.now().isoformat()
})

# 檢測模式
result = await order_flow_service.detect_patterns("2330")
print(result["primary_pattern"])
```

## 測試

```bash
cd backend-v3
python3 scripts/test_order_flow.py
```

## 配置閾值

可以通過 `PatternThresholds` 類調整模式識別的敏感度：

```python
from app.ml.order_flow import PatternThresholds

thresholds = PatternThresholds(
    aggressive_buy_volume_ratio=0.70,     # 積極買盤的量佔比門檻
    aggressive_buy_price_change=0.003,    # 價格上漲幅度門檻
    large_order_volume_threshold=100,     # 大單門檻（張）
    min_confidence=0.60,                  # 最低信心度
)
```

## 未來擴展

### 第二階段：機器學習模型 ✅

已完成：

1. **LSTM 模式分類器** (`app/ml/models/pattern_classifier.py`)
   - 混合架構：Bidirectional LSTM + Conv1D + Attention
   - 支援 Focal Loss 處理類別不平衡
   - 完整的訓練和評估流程

2. **XGBoost 市場狀態分類器** (`app/ml/models/market_state_classifier.py`)
   - 高階特徵工程器
   - 時間序列交叉驗證
   - 特徵重要性分析

3. **模型訓練管道** (`app/ml/training_pipeline.py`)
   - 端到端訓練流程
   - 支援 LSTM、XGBoost 和集成模型
   - 自動模型評估和保存

### 第三階段：實時推理引擎 ✅

已完成：

1. **決策融合** - 整合多模型輸出
2. **風險過濾** - 多維度風險檢查
3. **警報系統** - 回調式警報觸發
4. **決策歷史** - 追蹤和統計

## 模型架構

### LSTM 模式分類器

```
Input (序列特徵) ─┬─ Bidirectional LSTM ─ Attention ─ LSTM ─┐
                 │                                         │
                 └─ Conv1D ─ Conv1D ─ Pooling ─────────────┼─ Concat ─ Dense ─ Output
                                                           │
Input (輔助特徵) ──────────────────────────────────────────┘
```

### XGBoost 市場狀態分類器

支援 6 種市場狀態：
- 上漲趨勢 (TRENDING_UP)
- 下跌趨勢 (TRENDING_DOWN)
- 區間震盪 (RANGING)
- 高波動 (VOLATILE)
- 低波動 (QUIET)
- 突破狀態 (BREAKOUT)

## 推理引擎

### 交易動作

| 動作 | 說明 |
|------|------|
| STRONG_BUY | 強烈建議買入 |
| BUY | 建議買入 |
| WEAK_BUY | 可考慮小量買入 |
| HOLD | 建議持有觀望 |
| WEAK_SELL | 可考慮減碼 |
| SELL | 建議賣出 |
| STRONG_SELL | 強烈建議賣出 |

### 風險過濾

引擎會自動過濾以下情況：
- 接近收盤（最後5分鐘）
- 波動率過高（>3%）
- 流動性不足
- 極端價格變動（>5%）
- 信心度過低（<40%）

### 第四階段：前端整合 ✅

已完成：

1. **訂單流分析頁面** (`frontend-v3/src/app/dashboard/order-flow/page.tsx`)
   - 模式檢測結果視覺化
   - 特徵向量展示
   - 模擬數據輸入
   - 自動刷新功能

2. **側邊欄導航** - 已添加「訂單流分析」入口

3. **頁面功能**
   - 輸入股票代碼搜索
   - 一鍵模擬數據
   - 實時模式檢測
   - 信心度/強度進度條
   - 證據詳細展示
   - 所有模式類型說明

**訪問方式**：http://localhost:3000/dashboard/order-flow

## 第五階段：準確率評估系統 ✅

### 準確率衡量方法

系統採用**後續價格追蹤法**來評估預測準確率：

1. **記錄預測**：每次識別出模式時，記錄當下價格
2. **追蹤價格**：追蹤 5秒/30秒/60秒/5分鐘後的價格
3. **判斷正確性**：
   - 預測「積極買盤」→ 價格上漲 = 正確
   - 預測「積極賣盤」→ 價格下跌 = 正確
   - 預測「中性」→ 價格變動小於 0.1% = 正確

### 準確率指標

| 指標 | 說明 |
|------|------|
| `accuracy_5s` | 5秒後價格方向準確率 |
| `accuracy_30s` | 30秒後價格方向準確率 |
| `accuracy_60s` | 60秒後價格方向準確率 |
| `accuracy_5m` | 5分鐘後價格方向準確率（主要指標） |
| `avg_return` | 平均收益率 |
| `by_confidence` | 按信心度分層的準確率 |
| `by_pattern` | 按模式類型的準確率 |

### API 端點

```bash
# 獲取準確率報告
GET /api/order-flow/accuracy/report

# 獲取最近預測記錄
GET /api/order-flow/accuracy/recent?limit=20

# 導出數據
POST /api/order-flow/accuracy/export
```

### 準確率報告範例

```json
{
  "accuracy": {
    "5s": 55.2,
    "30s": 52.8,
    "60s": 54.1,
    "5m": 51.5
  },
  "by_confidence": {
    "high (>=80%)": 58.3,
    "medium (60-80%)": 52.1,
    "low (<60%)": 48.2
  },
  "interpretation": {
    "overall": "⚠️ 系統表現一般，準確率略高於隨機",
    "confidence": "✅ 高信心度信號表現優於低信心度"
  }
}
```

### 解讀標準

| 準確率 | 評價 |
|--------|------|
| >= 60% | ✅ 良好，有參考價值 |
| 50-60% | ⚠️ 一般，僅供參考 |
| < 50% | ❌ 需要優化 |

### 重要說明

⚠️ **準確率限制**：
- 當前使用的是**基於規則**的模式識別，非訓練好的 ML 模型
- 準確率會受市場狀況影響（牛市/熊市/震盪市）
- 建議累積至少 100 筆預測後再評估準確率
- 開盤時段的準確率通常高於收盤時段

## 安裝依賴

```bash
# 完整安裝
pip install tensorflow xgboost scikit-learn

# 僅 LSTM
pip install tensorflow

# 僅 XGBoost
pip install xgboost scikit-learn
```

---

**版本**: 2.1.0  
**更新日期**: 2025-12-30
