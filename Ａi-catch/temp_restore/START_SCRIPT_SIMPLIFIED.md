# ✅ 啟動腳本已簡化

## 🎉 更新完成！

啟動腳本已簡化，移除互動式選單，改為僅啟動服務。

---

## 🚀 現在的使用方式

### 一鍵啟動所有服務

```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh
```

**會自動啟動**:
1. ✅ 後端 API (Port 8000)
2. ✅ 前端服務 (Port 3000)
3. ✅ 富邦 Bridge (Port 8003，如有)
4. ✅ 顯示選股引擎使用提示

**不會再詢問是否執行選股分析**

---

## 📊 使用選股引擎

### 方法一：透過網頁（推薦）⭐

```bash
# 1. 啟動服務
./start_v3.sh

# 2. 訪問選股引擎頁面
open http://localhost:3000/dashboard/stock-selector

# 3. 點擊「執行選股分析」
```

### 方法二：手動執行

```bash
# 啟動服務後，在另一個終端執行
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 run_full_analysis.py
```

---

## 🎯 啟動後顯示的資訊

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 全自動選股決策引擎
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 透過網頁使用選股引擎：
   http://localhost:3000/dashboard/stock-selector

💡 或手動執行選股分析：
   cd /Users/Mac/Documents/ETF/AI/Ａi-catch
   python3 run_full_analysis.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 按 Ctrl+C 停止所有服務
```

---

## 📁 更新的文件

| 文件 | 更新內容 |
|------|----------|
| `start_v3.sh` | ✅ 移除互動式選單 |
| | ✅ 添加選股引擎網頁提示 |
| | ✅ 簡化啟動流程 |

---

## 🔄 變更對比

### 之前（有互動選單）

```bash
./start_v3.sh
# 會詢問：是否要執行選股分析？
# 1) 是
# 2) 否
# 需要用戶選擇
```

### 現在（僅啟動服務）

```bash
./start_v3.sh
# 直接啟動所有服務
# 顯示選股引擎網頁地址
# 用戶可自行決定何時使用
```

---

## 💡 使用建議

### 日常使用

```bash
# 每天啟動一次
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
./start_v3.sh

# 需要選股時，訪問網頁
open http://localhost:3000/dashboard/stock-selector
```

### 開發使用

```bash
# 啟動服務
./start_v3.sh

# 在另一個終端測試
python3 run_full_analysis.py
```

---

## 🌐 服務地址

| 服務 | 地址 |
|------|------|
| 前端首頁 | http://localhost:3000 |
| 選股引擎 | http://localhost:3000/dashboard/stock-selector |
| API 文件 | http://localhost:8000/api/docs |
| 健康檢查 | http://localhost:8000/health |

---

## ⚡ 快速參考

### 啟動服務
```bash
./start_v3.sh
```

### 使用選股引擎
```
http://localhost:3000/dashboard/stock-selector
```

### 手動執行選股
```bash
python3 run_full_analysis.py
```

### 停止服務
```
Ctrl+C
```

---

## ✅ 優點

1. **更簡單** - 不需要選擇，直接啟動
2. **更靈活** - 用戶可自行決定何時使用選股功能
3. **更直觀** - 透過網頁操作更方便
4. **更快速** - 啟動時間更短

---

**啟動腳本已簡化！現在更容易使用了！** 🚀

---

**更新日期**: 2026-01-01  
**版本**: v1.1.0  
**狀態**: ✅ 已簡化並可用
