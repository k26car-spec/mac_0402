# 股票綜合評分系統 - 專家優化版 v2.0

## 更新日期：2026-01-10

## 修改依據
根據專家審查建議進行的五大修正：

---

## 一、架構邏輯修正：解決權重重疊與雙重計分問題

### 問題
原架構中「籌碼面 (25%)」與「法人 (10%)」合計佔 35%，且主力買賣超通常已包含外資與投信數據，導致雙重計分。

### 解決方案
| 修改前 | 修改後 |
|--------|--------|
| 籌碼面 25% + 法人 10% = 35% | 合併為「資金動能」30% |
| 無風險維度 | 新增「風險控管」5% |

### 新的五維度權重
```
基本面 (30%) + 技術面 (25%) + 資金動能 (30%) + 市場 (10%) + 風險 (5%)
```

---

## 二、估值判斷優化：避免估值陷阱

### 問題
- 成長股誤殺：AI/IP股 PE 常在 40-60 倍，被誤判為「偏高」
- 景氣循環股陷阱：航運、面板在景氣高點 PE 極低，被誤判為「低估」

### 解決方案

#### 2.1 引入 PEG (本益成長比)
```python
if peg < 0.8:
    score += 12  # PEG低估，具成長價值
elif peg < 1.0:
    score += 8   # PEG合理
elif peg > 2.0:
    score -= 5   # PEG偏高，估值過高
```

#### 2.2 PE Band 歷史區間比較
```python
if pe_band_position < 20:
    score += 10  # PE處歷史低檔區
elif pe_band_position > 80:
    score -= 5   # PE處歷史高檔區
```

#### 2.3 景氣循環股特殊處理
```python
if is_cyclical and 0 < pe < 5:
    score -= 5  # ⚠️ 景氣循環股PE極低，小心高點陷阱
```

#### 2.4 營收 MoM 動能判斷
```python
if revenue_growth_yoy > 20 and revenue_growth_mom < 0:
    # YoY增但MoM衰退，成長趨緩
    score += 6  # 原本會給12分，現在打折
```

---

## 三、技術面優化：RSI 鈍化與量價異常處理

### 問題
- RSI > 70 直接扣分，導致提早賣出最強勢股票
- RSI < 30 直接加分，在空頭市場接刀危險

### 解決方案

#### 3.1 RSI 高檔鈍化判定
```python
if rsi > 80 and macd_histogram > 0 and macd > 0:
    # 超強勢狀態，不扣分反而加分
    score += 8
    details.append("RSI高檔鈍化，超強勢延續 🔥")
else:
    # MACD 動能衰退，開始扣分
    score -= 8
```

#### 3.2 RSI 底背離才給分
```python
if rsi < 30:
    if rsi_divergence == 'bullish':
        score += 12  # RSI超賣 + 底背離 = 反彈訊號
    else:
        score += 3   # 只是超賣，不急著給分
```

#### 3.3 乖離率濾網
```python
if deviation_20d > 20:
    score -= 10  # 乖離率過高，漲多風險
```

#### 3.4 爆量異常訊號
```python
if volume_ratio > 2 and price_change < -3:
    score -= 15  # ⚠️ 爆量長黑，強烈賣出訊號
elif volume_ratio > 2 and abs(price_change) < 1 and rsi > 60:
    score -= 10  # ⚠️ 高檔爆量不漲，警戒出貨
```

---

## 四、新增模組：風險指標與產業分析

### 4.1 RiskMetrics (風險指標)
```python
@dataclass
class RiskMetrics:
    beta: float                    # 波動率係數 (相對大盤)
    volatility: float              # 歷史波動率 (年化)
    margin_usage: float            # 融資使用率 (%)
    retail_concentration: float    # 散戶持股比例 (%)
    short_selling_balance: float   # 借券賣出餘額
    margin_increase_ratio: float   # 融資增減比例 (%)
```

### 4.2 SectorAnalysis (產業分析)
```python
@dataclass
class SectorAnalysis:
    sector_name: str               # 產業名稱
    sector_trend: str              # 產業趨勢
    relative_strength: float       # 相對強度 RS (>1 強勢)
    pe_rank_in_sector: float       # 同產業PE排名 (0-100)
    sector_avg_pe: float           # 產業平均PE
    pe_band_position: float        # PE Band 位置
```

---

## 五、資金動能優化：避免雙重計分

### 5.1 分流計算
- **三大法人**：外資、投信、自營商 (避免重複)
- **主力大戶**：非法人的內資大戶

### 5.2 借券餘額判斷假買真空
```python
if foreign_net > 1000 and foreign_short_balance > foreign_net * 0.5:
    score -= 8  # ⚠️ 外資買超但借券餘額高，疑似避險操作
```

### 5.3 主力買均價判斷
```python
if main_force_avg_cost > 0 and current_price > main_force_avg_cost * 1.3:
    score += 8  # 打折給分，價格已高於主力成本30%
```

### 5.4 散戶反向指標
```python
if margin_increase_ratio > 10:
    score -= 5  # 融資大增，散戶追漲 (反向指標)
```

---

## 新增的評分維度總覽

### 風險控管評分 (5%)
| 指標 | 條件 | 加減分 |
|------|------|--------|
| Beta | < 0.8 | +10 (防禦性佳) |
| Beta | > 1.5 | -15 (風險高) |
| 波動率 | > 50% | -12 (極高) |
| 波動率 | < 15% | +8 (穩定) |
| 融資使用率 | > 50% | -15 |
| 融資使用率 | < 10% | +5 |
| 散戶持股 | > 70% | -10 (籌碼凌亂) |
| 散戶持股 | < 30% | +8 (法人為主) |

---

## 程式碼變更摘要

### 新增 Dataclass
- `RiskMetrics` (風險指標)
- `SectorAnalysis` (產業分析)

### 新增/修改函數
- `_calculate_fundamental_score_v2()` - 專家優化版基本面評分
- `_calculate_technical_score_v2()` - 專家優化版技術面評分
- `_calculate_capital_momentum_score()` - 資金動能評分 (合併籌碼+法人)
- `_calculate_risk_score()` - 風險控管評分
- `_build_risk_metrics()` - 建構風險指標
- `_build_sector_analysis()` - 建構產業分析
- `_generate_investment_thesis()` - AI 投資邏輯
- `_generate_risk_warning()` - AI 風險預警

### 更新 ComprehensiveAnalysis
新增欄位：
- `risk_metrics: Optional[RiskMetrics]`
- `sector_analysis: Optional[SectorAnalysis]`
- `ai_investment_thesis: str`
- `ai_risk_warning: str`

---

## 後續待優化項目

1. **相對強度 (RS) 真實計算**：需接入大盤/產業指數數據
2. **PE Band 歷史數據**：需建立股票歷史PE資料庫
3. **同業比較自動化**：建立完整產業分類和即時PE對照
4. **借券餘額即時數據**：接入證券商API
5. **融資使用率即時數據**：接入資融公司API
