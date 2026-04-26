# ⚡ Day 1 快速行動清單

> 複製命令直接執行，節省時間！

**當前時間**: 2025-12-15 22:35  
**目標**: 完成 PostgreSQL 安裝與 Schema 設置

---

## 📦 Phase 1: PostgreSQL 安裝

### Option A: 使用 Homebrew（推薦）⭐

```bash
# Step 1: 安裝 Homebrew（如果沒有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安裝後配置 PATH（按照終端提示操作）

# Step 2: 驗證 Homebrew
brew --version

# Step 3: 安裝 PostgreSQL 14
brew install postgresql@14

# Step 4: 啟動服務
brew services start postgresql@14

# Step 5: 驗證安裝
psql --version
```

### Option B: 下載 Postgres.app

```bash
# 1. 在瀏覽器打開
open https://postgresapp.com/

# 2. 下載並安裝（拖到 Applications）

# 3. 啟動 Postgres.app 並點擊 Initialize

# 4. 配置 PATH
echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 5. 驗證
psql --version
```

---

## 🗄️ Phase 2: 創建數據庫

```bash
# 進入專案目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 創建數據庫
createdb ai_stock_db

# 測試連接
psql ai_stock_db

# 在 psql 中執行
SELECT version();
\q
```

---

## 📋 Phase 3: 執行 Schema

```bash
# 確保在專案根目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 執行 SQL 腳本
psql ai_stock_db < backend-v3/database/setup_database.sql

# 驗證表已創建
psql ai_stock_db -c "\dt"

# 查看初始數據
psql ai_stock_db -c "SELECT symbol, name FROM stocks;"
```

---

## ✅ Phase 4: 測試連接

```bash
# 測試數據庫連接
python3 test_database_connection.py
```

**預期輸出**: 所有測試通過 ✅

---

## 🔧 Phase 5: 安裝 Python 依賴

```bash
# 進入 backend-v3
cd backend-v3

# 確認虛擬環境已啟動
source venv/bin/activate

# 安裝數據庫相關依賴
pip install sqlalchemy asyncpg psycopg2-binary alembic redis aioredis

# 或安裝完整依賴
pip install -r requirements-v3.txt
```

---

## 📝 Phase 6: 配置環境變數

```bash
# 創建 .env 文件（如果不存在）
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3

# 創建 .env
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://ai_stock_user:ai_stock_2025_secure@localhost/ai_stock_db
DATABASE_POOL_SIZE=20

# Redis（Day 2 會用到）
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256

# Logging
LOG_LEVEL=INFO
EOF

echo "✅ .env 文件已創建"
```

---

## 🧪 Phase 7: 快速驗證

```bash
# 回到專案根目錄
cd /Users/Mac/Documents/ETF/AI/Ａi-catch

# 1. 檢查 PostgreSQL 服務
brew services list | grep postgresql
# 應該顯示 "started"

# 2. 檢查數據庫
psql -l | grep ai_stock_db
# 應該顯示數據庫

# 3. 檢查表
psql ai_stock_db -c "\dt"
# 應該顯示 8 個表

# 4. 檢查數據
psql ai_stock_db -c "SELECT COUNT(*) FROM stocks;"
# 應該返回 11

# 5. 測試 Python 連接
python3 test_database_connection.py
# 所有測試應通過
```

---

## 🎯 完成檢查清單

完成後請確認：

- [ ] `psql --version` 顯示 PostgreSQL 14.x
- [ ] `brew services list` 顯示 postgresql@14 正在運行
- [ ] `psql ai_stock_db` 可以成功連接
- [ ] `psql ai_stock_db -c "\dt"` 顯示 8 個表
- [ ] `python3 test_database_connection.py` 全部通過
- [ ] `backend-v3/.env` 文件已創建
- [ ] Python 依賴已安裝

---

## 🚨 如果遇到問題

### 問題 1: `brew: command not found`
```bash
# 安裝 Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 按照安裝後的提示配置 PATH
```

### 問題 2: `psql: command not found`
```bash
# Homebrew 用戶：配置 PATH
echo 'export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Postgres.app 用戶：配置 PATH
echo 'export PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 問題 3: `psql: connection refused`
```bash
# 啟動 PostgreSQL 服務
brew services start postgresql@14

# 或重啟
brew services restart postgresql@14

# 檢查狀態
brew services list
```

### 問題 4: 權限錯誤
```bash
# 重新授權
psql ai_stock_db << EOF
GRANT ALL PRIVILEGES ON DATABASE ai_stock_db TO ai_stock_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_stock_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_stock_user;
EOF
```

### 問題 5: Python 模組找不到
```bash
# 確認虛擬環境已啟動
cd /Users/Mac/Documents/ETF/AI/Ａi-catch/backend-v3
source venv/bin/activate

# 重新安裝
pip install psycopg2-binary asyncpg sqlalchemy
```

---

## 📊 預計時間

| 階段 | 時間 | 說明 |
|------|------|------|
| Phase 1: 安裝 PostgreSQL | 15-30分鐘 | 首次安裝 Homebrew 會較久 |
| Phase 2: 創建數據庫 | 2分鐘 | 快速 |
| Phase 3: 執行 Schema | 1分鐘 | 快速 |
| Phase 4: 測試連接 | 2分鐘 | 需安裝 Python 套件 |
| Phase 5: Python 依賴 | 5分鐘 | 下載安裝時間 |
| Phase 6: 配置 .env | 1分鐘 | 快速 |
| Phase 7: 驗證 | 3分鐘 | 檢查各項配置 |
| **總計** | **30-45分鐘** | 視網速和機器性能 |

---

## 🎉 完成後

### 你將擁有：

✅ **PostgreSQL 14** - 生產級數據庫運行中  
✅ **ai_stock_db** - 完整的 Schema  
✅ **8 個數據表** - stocks, quotes, analysis 等  
✅ **Python 連接** - psycopg2, asyncpg, SQLAlchemy  
✅ **環境配置** - .env 文件完成  

### 下一步：

1. **Day 1 下半天**: Alembic 遷移設置
2. **Day 2**: Redis 安裝與配置
3. **Day 3-4**: FastAPI API 開發

### 文檔參考：

- 📖 `POSTGRESQL_INSTALL_GUIDE.md` - 詳細指南
- 📊 `DAY1_PROGRESS.md` - 進度追蹤
- 📋 `WEEK1_PLAN.md` - 完整計劃

---

## 💬 獲取幫助

遇到問題時：

1. 查看 `POSTGRESQL_INSTALL_GUIDE.md`
2. 查看上面的「如果遇到問題」部分
3. 檢查 `DAY1_PROGRESS.md` 的筆記
4. Google 搜索錯誤訊息

---

**開始時間**: ___:___  
**完成時間**: ___:___  
**實際用時**: _____ 分鐘

**準備好了嗎？從 Phase 1 開始！** 🚀
