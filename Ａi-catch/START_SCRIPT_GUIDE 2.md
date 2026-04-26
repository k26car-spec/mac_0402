# 🚀 啟動腳本使用說明

## 📌 一鍵啟動所有服務

### 基本使用

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
```

這個命令會：
1. ✅ 啟動後端 API (Port 8000)
2. ✅ 啟動前端服務 (Port 3000)
3. ✅ 啟動富邦 Bridge (Port 8003，如有設定)
4. ✅ **詢問是否執行選股分析**（NEW!）

---

## 🎯 選股引擎整合

### 互動式選單

啟動服務後，會出現選股引擎選單：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 全自動選股決策引擎
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

是否要執行選股分析？

  1) 是 - 立即執行完整選股流程 (2-3分鐘)
  2) 否 - 跳過，僅啟動服務

請選擇 [1/2]:
```

### 選項說明

#### 選項 1: 是 - 立即執行

選擇「1」會自動執行：
1. 抓取富邦券商數據（自動使用今天日期）
2. 解析並提取買賣資訊
3. 執行多維度選股分析
4. 生成完整Excel報告

**執行時間**: 2-3 分鐘

**完成後會顯示**:
```
✅ 選股分析完成！

📊 查看報告：
   open backend-v3/reports/fubon_broker_analysis.csv

📊 查看券商數據：
   open broker_data_extracted.csv
```

#### 選項 2: 否 - 跳過

選擇「2」會：
- 跳過選股分析
- 僅啟動服務
- 顯示手動執行指令

**稍後可手動執行**:
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 run_full_analysis.py
```

---

## 📊 啟動後的服務

### 前端服務 (Port 3000)

- 首頁: http://localhost:3000
- Dashboard: http://localhost:3000/dashboard
- 股票分析: http://localhost:3000/dashboard/stock-analysis
- 訂單流分析: http://localhost:3000/dashboard/order-flow
- 經濟循環: http://localhost:3000/dashboard/economic-cycle
- 盤前選股: http://localhost:3000/dashboard/premarket
- 新聞分析: http://localhost:3000/dashboard/news

### 後端服務 (Port 8000)

- API 文件: http://localhost:8000/api/docs
- 健康檢查: http://localhost:8000/health
- 選股引擎: http://localhost:8000/api/stock-selector/health

### 選股引擎 API

- 分析單股: http://localhost:8000/api/stock-selector/analyze/2330
- 批量分析: http://localhost:8000/api/stock-selector/analyze/batch
- 推薦股票: http://localhost:8000/api/stock-selector/recommendations
- 富邦新店: http://localhost:8000/api/stock-selector/broker-flow/fubon-xindan/top-stocks

---

## 🔧 使用流程

### 標準流程（推薦）

```bash
# 步驟1: 啟動所有服務
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh

# 步驟2: 選擇「1」執行選股分析
# （等待2-3分鐘）

# 步驟3: 查看報告
open backend-v3/reports/fubon_broker_analysis.csv
```

### 僅啟動服務（不執行選股）

```bash
# 步驟1: 啟動服務
./start_v3.sh

# 步驟2: 選擇「2」跳過選股

# 步驟3: 使用前端或API
open http://localhost:3000
```

### 稍後手動執行選股

```bash
# 在任何時候執行
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 run_full_analysis.py
```

---

## 🛑 停止服務

### 方法1: Ctrl+C

在啟動腳本的終端視窗按 `Ctrl+C`

### 方法2: 手動停止

```bash
# 停止所有服務
lsof -ti:8000 | xargs kill -9  # 停止後端
lsof -ti:3000 | xargs kill -9  # 停止前端
lsof -ti:8003 | xargs kill -9  # 停止富邦Bridge
```

---

## 📁 輸出文件

執行選股分析後會生成：

### 1. 券商數據
```
/Users/Mac/Documents/ETF/AI/Ａi-catch/broker_data_extracted.csv
```

### 2. 分析報告
```
/Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3/reports/fubon_broker_analysis.csv
```

### 3. 日誌文件
```
/Users/Mac/Documents/ETF/AI/Ａi-catch/logs/backend.log
/Users/Mac/Documents/ETF/AI/Ａi-catch/logs/frontend.log
```

---

## 💡 使用建議

### 每日使用

```bash
# 每天收盤後執行
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
# 選擇「1」執行選股分析
```

### 開發使用

```bash
# 開發時僅啟動服務
./start_v3.sh
# 選擇「2」跳過選股

# 需要時手動執行
python3 run_full_analysis.py
```

---

## 🔍 故障排除

### 問題1: 端口被佔用

**症狀**: 啟動失敗，提示端口被佔用

**解決方案**:
```bash
# 手動釋放端口
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### 問題2: 選股分析失敗

**症狀**: 選擇「1」後分析失敗

**解決方案**:
```bash
# 檢查網路連接
curl -I https://fubon-ebrokerdj.fbs.com.tw

# 手動執行查看詳細錯誤
python3 run_full_analysis.py
```

### 問題3: 服務無法訪問

**症狀**: 無法訪問 http://localhost:3000

**解決方案**:
```bash
# 檢查服務狀態
lsof -i:3000
lsof -i:8000

# 查看日誌
tail -f logs/frontend.log
tail -f logs/backend.log
```

---

## 📞 快速參考

### 一鍵啟動
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch && ./start_v3.sh
```

### 手動執行選股
```bash
python3 run_full_analysis.py
```

### 查看報告
```bash
open backend-v3/reports/fubon_broker_analysis.csv
```

### 停止服務
```
Ctrl+C
```

---

## ✅ 檢查清單

啟動前確認：
- [ ] 已進入正確目錄
- [ ] 腳本有執行權限 (`chmod +x start_v3.sh`)
- [ ] 網路連線正常
- [ ] 端口 3000, 8000 未被佔用

第一次使用：
- [ ] 執行 `./start_v3.sh`
- [ ] 選擇「1」執行選股
- [ ] 等待2-3分鐘
- [ ] 查看生成的報告

---

**現在就試試看！**

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
```

選擇「1」立即體驗全自動選股決策引擎！🚀
