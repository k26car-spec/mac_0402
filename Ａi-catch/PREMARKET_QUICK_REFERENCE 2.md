# ⚡ 開盤前5分鐘精準選股系統 - 快速參考卡

## 🚀 一行啟動

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch && ./start_premarket.sh
```

---

## 🌐 快速訪問

| 功能 | URL |
|------|-----|
| 主控台 | http://127.0.0.1:8082 |
| **精準選股** | **http://127.0.0.1:8082/premarket** |
| API 文檔 | http://127.0.0.1:8000/api/docs |

---

## ⏰ 關鍵時間點

```
前一晚  21:00 → 開始隔夜分析
早  上  08:00 → 開始早盤掃描
        08:45 → 台指期開盤
🔥      08:55 → 最終5分鐘精選
🚀      09:00 → 開盤執行決策
```

---

## 📊 評分權重

```
美股影響:  40% ████████
法人動向:  30% ██████
技術面:    20% ████
即時新聞:  10% ██
```

**進場條件**: 至少符合 **3 個條件**

---

## 🎯 紀律鐵律

```
❌ 不追高    開高 > 2% 絕不追
⛔ 嚴守停損  跌破 -2% 立刻出場
💰 不貪心    達標 +5% 分批了結
📊 不all-in  單一標的 ≤ 40%
```

---

## 📈 技術訊號 (60分合格)

| 訊號 | 條件 | 分數 |
|------|------|------|
| 突破型態 | 突破均線 + 量增 | 30 |
| 多頭排列 | MA5>MA10>MA20>MA60 | 25 |
| 黃金交叉 | MA5 上穿 MA20 | 20 |
| RSI強勢 | 50 < RSI < 70 | 15 |
| MACD多頭 | MACD > Signal | 10 |

---

## 🔧 API 端點速查

```bash
# 隔夜分析
GET /api/premarket/overnight-analysis

# 早盤掃描
GET /api/premarket/morning-scan

# 技術篩選
GET /api/premarket/technical-screening

# 🔥 最終精選 (08:55)
GET /api/premarket/final-selection

# 開盤執行
POST /api/premarket/opening-execution

# 勝率統計
GET /api/premarket/statistics

# 檢查清單
GET /api/premarket/checklist
```

---

## 📁 核心檔案

```
後端 API:
  backend-v3/app/api/premarket.py       (763 行)
  backend-v3/app/models/premarket.py    (253 行)

前端介面:
  templates/premarket.html              (629 行)

文檔:
  PREMARKET_SELECTION_SYSTEM.md         (完整文檔)
  PREMARKET_IMPLEMENTATION_SUMMARY.md   (實作總結)

啟動:
  start_premarket.sh                    (快速啟動)
```

---

## 🎬 開盤前5分鐘流程

```
08:50 → 訪問系統，查看 Top 5 精選
      ↓
08:55 → 確認主力標的 (#1)
      ↓
      → 記下進場價、停損價、目標價
      ↓
09:00 → 觀察開盤價與量能
      ↓
      → 判斷開盤型態:
         • 平開 ±0.5% → 立即買進
         • 開高 >1% → 等回測
         • 開低 >1% → 放棄
      ↓
09:01 → 執行交易
      ↓
09:02 → 立即設定停損單 (-2%)
```

---

## 📊 實戰案例模板

```
🥇 主力標的: 台積電 (2330)
信心度: 95%
綜合分數: 95

選股原因:
✅ 美股輝達大漲 +4.8%
✅ 外資買超 15,000張
✅ 突破季線 + 量增
✅ 法說會預告利多

交易計畫:
進場價: 995
目標價: 1045 (+5%)
停損價: 975 (-2%)
部位: 40%資金
策略: 開盤價或回測支撐進場
```

---

## 🛠️ 故障排除

### 後端啟動失敗

```bash
# 檢查 port 8000
lsof -i :8000

# 重啟
cd backend-v3
python3 -m uvicorn app.main:app --reload --port 8000
```

### Dashboard 啟動失敗

```bash
# 檢查 port 8082
lsof -i :8082

# 重啟
python3 dashboard.py
```

### API 無回應

```bash
# 檢查健康狀態
curl http://127.0.0.1:8000/health

# 查看 API 文檔
open http://127.0.0.1:8000/api/docs
```

---

## 📞 快速命令

```bash
# 啟動
./start_premarket.sh          # 選項 1 (完整)

# 檢查狀態
./start_premarket.sh          # 選項 4

# 停止
./start_premarket.sh          # 選項 5

# 查看文檔
./start_premarket.sh          # 選項 6
```

---

## 🎯 勝率統計 (模擬)

```
總交易: 180次
勝率:   70% ✅
平均獲利: +4.2%
平均虧損: -1.8%
期望值: +2.0%
```

---

## 📚 完整文檔

```bash
# 查看完整系統文檔
cat PREMARKET_SELECTION_SYSTEM.md

# 查看實作總結
cat PREMARKET_IMPLEMENTATION_SUMMARY.md

# 在編輯器中打開
code PREMARKET_SELECTION_SYSTEM.md
```

---

## 💡 專業提示

1. **提前準備** - 前一晚就看美股，隔天才不慌
2. **專注主力** - Top 1 標的往往信心度最高
3. **分批進場** - 不要一次買滿，留子彈
4. **停損優先** - 立即設定停損單，不要拖延
5. **記錄覆盤** - 每次交易都記錄，找出改進點

---

**⚡ 系統已就緒，立即開始！**

```bash
./start_premarket.sh
```

---

*版本: v1.0.0 | 更新: 2025-12-16*
