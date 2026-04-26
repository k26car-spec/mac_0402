# 📦 PostgreSQL 14 安裝指南

**目標**: 安裝並配置 PostgreSQL 14，為 AI Stock Intelligence 系統建立數據庫

**預計時間**: 15-30 分鐘

---

## 🎯 安裝選項

您有兩個安裝選項，請選擇一個：

### ⭐ **方案 A: Homebrew（強烈推薦）**
- ✅ 命令行安裝，簡單快速
- ✅ 易於管理和更新
- ✅ 後續安裝 Redis 也會用到
- ⚠️ 需要先安裝 Homebrew

### 方案 B: Postgres.app（圖形化）
- ✅ 圖形界面，易於理解
- ✅ 無需命令行
- ⚠️ 手動管理更新

---

## 📦 方案 A: 使用 Homebrew（推薦）

### Step 1: 安裝 Homebrew

**開啟終端**，複製並執行以下命令：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**過程說明**:
- 會要求您輸入密碼（Mac 系統密碼）
- 安裝時間約 5-10 分鐘
- 安裝完成後，按照提示配置 PATH

**驗證安裝**:
```bash
brew --version
```

應該顯示類似：`Homebrew 4.x.x`

---

### Step 2: 安裝 PostgreSQL 14

```bash
# 安裝 PostgreSQL 14
brew install postgresql@14

# 啟動 PostgreSQL 服務
brew services start postgresql@14

# 驗證安裝
psql --version
```

**預期輸出**:
```
psql (PostgreSQL) 14.x
```

---

### Step 3: 創建數據庫

```bash
# 創建數據庫
createdb ai_stock_db

# 連接到數據庫（測試）
psql ai_stock_db
```

**在 psql 中執行**:
```sql
-- 應該看到提示符: ai_stock_db=#

-- 測試查詢
SELECT version();

-- 退出
\q
```

---

### Step 4: 執行 Schema 設置

```bash
# 回到專案目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 執行 SQL 腳本
psql ai_stock_db < backend-v3/database/setup_database.sql
```

**預期結果**:
- 創建用戶 `ai_stock_user`
- 創建所有必要的表
- 創建索引和視圖
- 插入初始數據

---

### Step 5: 驗證安裝

```bash
# 連接到數據庫
psql -U ai_stock_user -d ai_stock_db

# 或使用預設用戶
psql ai_stock_db
```

**在 psql 中執行**:
```sql
-- 查看所有表
\dt

-- 應該看到以下表：
-- stocks, stock_quotes, order_books, expert_signals,
-- analysis_results, alerts, lstm_predictions, users

-- 查看stocks表的數據
SELECT symbol, name, market FROM stocks;

-- 退出
\q
```

---

## 📦 方案 B: 使用 Postgres.app

### Step 1: 下載並安裝

1. **訪問**: https://postgresapp.com/
2. **下載**: 點擊 "Download" 按鈕
3. **安裝**: 
   - 打開下載的 `.dmg` 文件
   - 拖動 Postgres.app 到 Applications 文件夾
   - 啟動 Postgres.app

### Step 2: 初始化數據庫

1. 在 Postgres.app 中，點擊 **"Initialize"**
2. 會自動創建預設數據庫

### Step 3: 配置 PATH（重要）

在終端執行：
```bash
# 添加到 PATH
echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zshrc

# 重新載入配置
source ~/.zshrc

# 驗證
psql --version
```

### Step 4: 創建數據庫並執行 Schema

```bash
# 創建數據庫
createdb ai_stock_db

# 執行 Schema
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
psql ai_stock_db < backend-v3/database/setup_database.sql
```

---

## ✅ 安裝驗證清單

完成安裝後，請確認以下項目：

- [ ] `psql --version` 顯示 PostgreSQL 14.x
- [ ] `psql ai_stock_db` 可以成功連接
- [ ] `\dt` 顯示 8 個表
- [ ] `SELECT COUNT(*) FROM stocks;` 返回 11（初始股票數據）

---

## 🔧 常見問題

### Q1: 找不到 psql 命令

**原因**: PATH 未正確配置

**解決方案**:
```bash
# Homebrew 用戶
echo 'export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Postgres.app 用戶
echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

### Q2: 連接被拒絕（Connection refused）

**原因**: PostgreSQL 服務未啟動

**解決方案**:
```bash
# Homebrew 用戶
brew services start postgresql@14

# Postgres.app 用戶
# 打開 Postgres.app 確保服務正在運行
```

---

### Q3: 權限錯誤

**原因**: 用戶權限不足

**解決方案**:
```sql
-- 以超級用戶連接
psql ai_stock_db

-- 重新授權
GRANT ALL PRIVILEGES ON DATABASE ai_stock_db TO ai_stock_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_stock_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_stock_user;
```

---

### Q4: 創建用戶失敗

**原因**: 用戶可能已存在

**解決方案**:
```sql
-- 刪除舊用戶（如果需要）
DROP USER IF EXISTS ai_stock_user;

-- 重新創建
CREATE USER ai_stock_user WITH PASSWORD 'ai_stock_2025_secure';
```

---

## 🎯 安裝完成後

### 1. 測試連接

創建測試腳本：
```bash
cd /Users/Mac/Documents/ETF/AI/Ａi-catch
python3 test_database_connection.py
```

### 2. 更新 .env 配置

編輯 `backend-v3/.env`:
```bash
DATABASE_URL=postgresql+asyncpg://ai_stock_user:ai_stock_2025_secure@localhost/ai_stock_db
```

### 3. 安裝 Python 依賴

```bash
cd backend-v3
source venv/bin/activate
pip install sqlalchemy asyncpg psycopg2-binary
```

---

## 📊 數據庫 Schema 說明

安裝完成後，您將擁有以下表：

| 表名 | 用途 |
|------|------|
| `stocks` | 股票基本資料 |
| `stock_quotes` | 即時報價歷史 |
| `order_books` | 五檔掛單數據 |
| `expert_signals` | 15位專家的信號 |
| `analysis_results` | 分析結果 |
| `alerts` | 警報記錄 |
| `lstm_predictions` | LSTM 預測結果 |
| `users` | 用戶管理 |

**視圖**:
- `latest_quotes` - 最新報價
- `active_alerts` - 活躍警報
- `expert_signals_summary` - 專家信號摘要

---

## 🚀 下一步

安裝完成後：

1. ✅ **繼續 Day 1 下半天**: Alembic 遷移設置
2. ✅ **Day 2**: Redis 安裝
3. ✅ **Day 3-4**: FastAPI API 開發

---

## 💡 小提示

### 管理 PostgreSQL 服務

```bash
# 啟動服務
brew services start postgresql@14

# 停止服務
brew services stop postgresql@14

# 重啟服務
brew services restart postgresql@14

# 查看服務狀態
brew services list
```

### 常用 psql 命令

```sql
\l          -- 列出所有數據庫
\dt         -- 列出所有表
\d 表名     -- 查看表結構
\du         -- 列出所有用戶
\q          -- 退出
```

---

**準備好開始安裝了嗎？**

**推薦流程**:
1. 先安裝 Homebrew（如果沒有）
2. 使用 Homebrew 安裝 PostgreSQL 14
3. 執行 setup_database.sql
4. 驗證安裝
5. 繼續 Day 1 下半天的工作

**安裝完成後，請運行**:
```bash
python3 test_database_connection.py
```

---

**建立時間**: 2025-12-15 22:35  
**最後更新**: 2025-12-15 22:35  
**狀態**: 📋 等待安裝
