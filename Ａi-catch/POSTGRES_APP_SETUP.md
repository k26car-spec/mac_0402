# 📦 Postgres.app 安裝與配置指南

**安裝方式**: Postgres.app  
**預計時間**: 5-10 分鐘  
**狀態**: 🟡 進行中

---

## ✅ Step 1: 下載與安裝（您正在進行）

### 1.1 下載
- ✅ 已打開官網: https://postgresapp.com/
- ⏳ 點擊 "Download" 按鈕
- ⏳ 等待下載完成

### 1.2 安裝
```
1. 打開下載的 .dmg 文件
2. 拖動 Postgres 到 Applications
3. 等待複製完成
```

---

## 🚀 Step 2: 啟動 Postgres.app

### 2.1 首次啟動

```bash
# 方法 A: 從應用程式文件夾打開
open /Applications/Postgres.app

# 方法 B: 使用 Spotlight
# 按 Cmd+Space，輸入 "Postgres"，按 Enter
```

### 2.2 初始化資料庫

**在 Postgres.app 視窗中**：

1. 你會看到一個伺服器列表
2. 點擊 **"Initialize"** 按鈕（如果是首次啟動）
3. 等待初始化完成（約 10 秒）
4. 伺服器狀態應該顯示為 **"Running"** ✅

---

## 🔧 Step 3: 配置 PATH（重要！）

為了在終端中使用 `psql` 命令，需要配置 PATH。

### 3.1 添加到 PATH

在終端執行：

```bash
# 添加 Postgres.app 到 PATH
echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zshrc

# 重新載入配置
source ~/.zshrc
```

### 3.2 驗證安裝

```bash
# 檢查 psql 是否可用
which psql

# 應該顯示:
# /Applications/Postgres.app/Contents/Versions/latest/bin/psql

# 檢查版本
psql --version

# 應該顯示類似:
# psql (PostgreSQL) 14.x 或更高版本
```

---

## 🗄️ Step 4: 創建專案數據庫

### 4.1 創建數據庫

```bash
# 回到專案目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 創建數據庫
createdb ai_stock_db

# 驗證數據庫已創建
psql -l | grep ai_stock_db
```

### 4.2 連接測試

```bash
# 連接到數據庫
psql ai_stock_db

# 在 psql 提示符中執行:
SELECT version();

# 應該顯示 PostgreSQL 版本信息

# 退出
\q
```

---

## 📋 Step 5: 執行 Database Schema

### 5.1 執行 SQL 腳本

```bash
# 確保在專案根目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 執行 Schema 設置腳本
psql ai_stock_db < backend-v3/database/setup_database.sql
```

### 5.2 驗證表已創建

```bash
# 查看所有表
psql ai_stock_db -c "\dt"

# 應該看到 8 個表:
# - stocks
# - stock_quotes
# - order_books
# - expert_signals
# - analysis_results
# - alerts
# - lstm_predictions
# - users
```

### 5.3 查看初始數據

```bash
# 查看股票數據
psql ai_stock_db -c "SELECT symbol, name, market FROM stocks;"

# 應該看到 11 筆股票資料
```

---

## ✅ Step 6: 測試 Python 連接

### 6.1 安裝 Python 套件

```bash
# 進入 backend-v3
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3

# 啟動虛擬環境
source venv/bin/activate

# 安裝數據庫套件
pip install psycopg2-binary asyncpg sqlalchemy
```

### 6.2 運行測試腳本

```bash
# 回到專案根目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 運行連接測試
python3 test_database_connection.py
```

**預期結果**: 所有測試應該通過 ✅

---

## 🔧 Step 7: 配置環境變數

### 7.1 創建 .env 文件

```bash
# 進入 backend-v3
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3

# 創建 .env 文件
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost/ai_stock_db
DATABASE_POOL_SIZE=20

# Redis (Day 2 會用到)
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256

# Logging
LOG_LEVEL=INFO
EOF
```

**注意**: Postgres.app 預設使用當前系統用戶，不需要密碼

---

## 🎯 完成檢查清單

請確認以下項目：

- [ ] Postgres.app 已下載並安裝
- [ ] Postgres.app 正在運行（狀態顯示 "Running"）
- [ ] PATH 已配置（`which psql` 有輸出）
- [ ] `psql --version` 顯示版本號
- [ ] `ai_stock_db` 數據庫已創建
- [ ] Schema 已執行（8 個表已創建）
- [ ] 初始數據已插入（11 筆股票）
- [ ] Python 連接測試通過
- [ ] .env 文件已創建

---

## 🚨 常見問題

### Q1: Postgres.app 無法打開

**錯誤**: "無法打開，因為它來自未識別的開發者"

**解決方案**:
```bash
# 方法 1: 在 Finder 中右鍵點擊，選擇 "打開"

# 方法 2: 終端命令
sudo xattr -d com.apple.quarantine /Applications/Postgres.app
```

---

### Q2: 找不到 psql 命令

**錯誤**: `zsh: command not found: psql`

**解決方案**:
```bash
# 重新配置 PATH
echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 驗證
which psql
```

---

### Q3: 連接被拒絕

**錯誤**: `Connection refused`

**解決方案**:
```bash
# 確認 Postgres.app 正在運行
# 打開 Postgres.app，查看伺服器狀態應該是 "Running"

# 如果沒有運行，點擊伺服器旁的啟動按鈕
```

---

### Q4: Schema 執行錯誤

**錯誤**: 權限或語法錯誤

**解決方案**:
```bash
# Postgres.app 使用當前用戶，修改 SQL 中的用戶創建部分

# 連接數據庫
psql ai_stock_db

# 手動創建用戶（如果需要）
CREATE USER ai_stock_user WITH PASSWORD 'ai_stock_2025_secure';
GRANT ALL PRIVILEGES ON DATABASE ai_stock_db TO ai_stock_user;
```

---

## 🎓 Postgres.app 管理

### 啟動/停止服務

**圖形界面**:
- 打開 Postgres.app
- 點擊伺服器旁的停止/啟動按鈕

**自動啟動**:
- 在 Preferences 中勾選 "Automatically start at login"

### 查看日誌

在 Postgres.app 中:
- 點擊伺服器
- 選擇 "Server Settings"
- 查看 "Log" 標籤

---

## 📊 效能建議

### 基本配置

Postgres.app 預設配置已經很好，但如果需要調整：

1. 打開 Postgres.app
2. 點擊伺服器旁的設置按鈕
3. 修改配置檔（postgresql.conf）

### 推薦設置（可選）

```bash
# 進入 psql
psql ai_stock_db

# 調整連接數（如果需要）
ALTER SYSTEM SET max_connections = 100;

# 優化記憶體（根據您的 RAM）
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';

# 重啟服務使設置生效
# 在 Postgres.app 中停止再啟動伺服器
```

---

## ✨ 優勢

使用 Postgres.app 的好處：

- ✅ **圖形化界面** - 易於管理
- ✅ **快速安裝** - 5 分鐘內完成
- ✅ **包含多版本** - PostgreSQL 14, 15, 16
- ✅ **開箱即用** - 無需複雜配置
- ✅ **內建工具** - pgAdmin 等管理工具

---

## 🔄 與 Homebrew PostgreSQL 的差異

| 特性 | Postgres.app | Homebrew |
|------|-------------|----------|
| 安裝方式 | 圖形化 | 命令行 |
| 啟動方式 | 雙擊應用 | brew services |
| 管理界面 | 圖形化 | 命令行 |
| 更新方式 | 下載新版 | brew upgrade |
| 適合對象 | 圖形化愛好者 | 命令行愛好者 |

**兩者功能完全相同**，選擇您喜歡的即可！

---

## 📚 相關資源

- 官方網站: https://postgresapp.com/
- 文檔: https://postgresapp.com/documentation/
- PostgreSQL 官方文檔: https://www.postgresql.org/docs/

---

## ⏭️ 完成後的下一步

1. ✅ 更新 `DAY1_PROGRESS.md` 標記完成
2. ✅ 繼續 Day 1 下半天: Alembic 設置
3. ✅ 或直接進入 Day 2: Redis 安裝

---

**安裝開始時間**: _____:_____  
**安裝完成時間**: _____:_____  
**實際用時**: _____ 分鐘

**狀態**: 🟡 進行中 → ✅ 完成
