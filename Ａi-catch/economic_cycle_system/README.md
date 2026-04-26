# 循環驅動多因子投資系統

> 🌐 自動化檢測當前經濟週期階段，提供資產配置建議

## 📋 系統架構

```
1. 總經循環定位模組 ✅ 已完成
   ↓
2. 產業鏈與定價權分析模組 ✅ 已完成
   ↓
3. 財報與營收量化篩選模組 ✅ 已完成
   ↓
4. 技術面與線型時機模組 ✅ 已完成 (v2.0)
   ↓
5. 資產配置與風險控制模組 ✅ 已完成 (v2.0)
   ↓
6. 電子股趨勢與訂單監測模組 ✅ 已完成 (v2.0)
   ↓
7. 🎯 投資信號產生器 ✅ 已完成 (v1.0) ← NEW!
   輸出：買進/賣出/持有信號 + 配置建議
```

## 🏭 模組概覽

| 模組 | 狀態 | 說明 |
|------|------|------|
| [總經循環定位](./economic_cycle.py) | ✅ 完成 | 判斷經濟週期，資產配置建議 |
| [產業鏈與定價權](./industry_chain/) | ✅ 完成 | 分析產業鏈結構，定價權評分 |
| [財報量化篩選](./financial_screener/) | ✅ 完成 | 三大關鍵數字，財務評級 |
| [技術面時機](./technical_timing/) | ✅ v2.0 | 五年區間分析，交易計劃 |
| [資產配置風控](./asset_allocation/) | ✅ v2.0 | 動態配置，風險控制 |
| [電子股訂單](./electronics_monitor/) | ✅ v2.0 | 趨勢分析，訂單監測 |
| [🎯 信號產生器](./signal_generator/) | ✅ v1.0 | **買賣信號 + 配置建議** |

## 🚀 快速開始

### 1. 安裝依賴

```bash
cd economic_cycle_system
pip install -r requirements.txt
```

### 2. 取得 FRED API 金鑰（可選，免費）

1. 前往 https://fred.stlouisfed.org/docs/api/api_key.html
2. 註冊帳號（免費）
3. 取得 API 金鑰
4. 在 `config.py` 中填入金鑰

### 3. 執行分析

```bash
# 直接執行
python economic_cycle.py

# 或使用 Python
python -c "from economic_cycle import main; main()"
```

## 📊 輸出範例

```
🌐 總經循環定位分析報告
📅 生成時間: 2025-12-27 18:00:00
======================================================================

📊 【當前經濟階段】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
階段: 復甦期 (recovery)
信心度: 72.5%
描述: 經濟開始復甦，企業獲利改善

💰 【資產配置建議】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
台股: 50%
美股: 25%
債券: 15%
現金: 10%

投資重點: 成長股, AI概念, 半導體
```

## 📁 專案結構

```
economic_cycle_system/
├── economic_cycle.py    # 核心分析程式
├── api.py              # FastAPI 整合
├── config.py           # 配置文件
├── requirements.txt    # 依賴套件
├── README.md           # 說明文件
├── data/               # 數據目錄
│   ├── historical/     # 歷史數據
│   └── cache/          # 緩存數據
├── reports/            # 報告輸出
└── charts/             # 圖表輸出
```

## 🔌 API 整合

### 整合到 backend-v3

在 `backend-v3/app/main.py` 中加入：

```python
import sys
sys.path.insert(0, '/Users/Mac/Documents/ETF/AI/Ａi-catch/economic_cycle_system')
from api import router as economic_cycle_router
app.include_router(economic_cycle_router)
```

### API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/economic-cycle/status` | GET | 獲取當前經濟階段 |
| `/api/economic-cycle/indicators` | GET | 獲取經濟指標 |
| `/api/economic-cycle/allocation` | GET | 獲取資產配置建議 |
| `/api/economic-cycle/sectors` | GET | 獲取產業配置建議 |
| `/api/economic-cycle/stock-picks` | GET | 獲取推薦股票 |
| `/api/economic-cycle/warnings` | GET | 獲取風險警告 |
| `/api/economic-cycle/report` | GET | 獲取完整報告 |

## 🎯 經濟週期階段

| 階段 | 名稱 | 特徵 | 建議配置 |
|------|------|------|----------|
| recovery | 復甦期 | PMI回升、失業率下降 | 科技、金融、成長股 |
| expansion | 擴張期 | 經濟穩定成長 | 工業、材料、價值股 |
| overheat | 過熱期 | 通膨上升、央行緊縮 | 能源、必需消費 |
| slowdown | 放緩期 | 成長動能減弱 | 公用事業、高股息 |
| recession | 衰退期 | 經濟收縮 | 債券、現金、防禦股 |

## ⚠️ 風險警告觸發條件

- **PMI < 48**: 製造業可能收縮
- **殖利率曲線倒掛 > 0.5%**: 衰退風險大增
- **CPI > 5%**: 通膨壓力嚴重
- **失業率 > 5.5%**: 就業市場惡化

## 📅 建議更新頻率

每月更新一次，特別注意：
- PMI數據（每月第1個工作日）
- 非農就業（每月第1個星期五）
- CPI數據（每月中旬）
- Fed利率決議（每6週）

## 🔧 參數調整

在 `config.py` 中可調整：

```python
# 權重參數
WEIGHTS = {
    'pmi': 0.30,
    'yield_curve': 0.25,
    'unemployment': 0.15,
    'inflation': 0.15,
    'gdp_growth': 0.15
}
```

## 📝 注意事項

1. **數據延遲**: 部分經濟數據有 1-2 個月延遲
2. **API 限制**: FRED 免費 API 有請求次數限制
3. **模型限制**: 無法完全預測黑天鵝事件
4. **歷史表現不代表未來**: 需持續監控和調整

## 📜 版本歷史

- v2.0 (2025-12-27): 完整實現，整合 FastAPI
- v1.0 (2025-12-20): 初始版本

---

💡 **提示**: 搭配其他模組使用效果更佳！
