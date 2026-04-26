#!/bin/bash

# PostgreSQL 安裝腳本
# 適用於 macOS 系統

echo "🚀 PostgreSQL 14 安裝指南"
echo "========================================"
echo ""

# 檢查是否已安裝 Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ 未檢測到 Homebrew"
    echo ""
    echo "📦 方案 A：安裝 Homebrew（推薦）"
    echo "========================================"
    echo ""
    echo "Homebrew 是 macOS 最好的套件管理器"
    echo "安裝後可以輕鬆管理 PostgreSQL、Redis 等軟件"
    echo ""
    echo "安裝命令（複製並執行）："
    echo ""
    echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo ""
    echo "安裝完成後，運行以下命令："
    echo "  brew install postgresql@14"
    echo ""
    echo "========================================"
    echo ""
    echo "📦 方案 B：使用 Postgres.app（圖形化）"
    echo "========================================"
    echo ""
    echo "1. 訪問 https://postgresapp.com/"
    echo "2. 下載並安裝 Postgres.app"
    echo "3. 啟動應用程式"
    echo "4. 點擊 'Initialize' 初始化數據庫"
    echo ""
    echo "========================================"
    echo ""
    echo "⏸️  請選擇一個方案並安裝，安裝完成後再運行此腳本"
    exit 1
fi

# Homebrew 已安裝，繼續安裝 PostgreSQL
echo "✅ 檢測到 Homebrew"
echo ""
echo "📥 開始安裝 PostgreSQL 14..."
echo ""

# 更新 Homebrew
echo "🔄 更新 Homebrew..."
brew update

# 安裝 PostgreSQL 14
echo ""
echo "📦 安裝 PostgreSQL 14..."
brew install postgresql@14

# 啟動 PostgreSQL 服務
echo ""
echo "🚀 啟動 PostgreSQL 服務..."
brew services start postgresql@14

# 等待服務啟動
echo ""
echo "⏳ 等待服務就緒..."
sleep 3

# 驗證安裝
echo ""
echo "✅ 驗證安裝..."
psql --version

# 顯示後續步驟
echo ""
echo "========================================"
echo "🎉 PostgreSQL 14 安裝完成！"
echo "========================================"
echo ""
echo "📊 服務狀態："
brew services list | grep postgresql

echo ""
echo "📋 下一步："
echo "1. 創建數據庫："
echo "   createdb ai_stock_db"
echo ""
echo "2. 連接數據庫："
echo "   psql ai_stock_db"
echo ""
echo "3. 創建用戶和授權："
echo "   參考 setup_database.sql"
echo ""
echo "========================================"
