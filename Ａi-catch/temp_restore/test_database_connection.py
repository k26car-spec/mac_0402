#!/usr/bin/env python3
"""
PostgreSQL 連接測試腳本
測試資料庫連接和基本操作
"""

import sys

def test_psycopg2():
    """測試 psycopg2 連接（同步）"""
    print("=" * 60)
    print("🔌 測試 PostgreSQL 連接（psycopg2）")
    print("=" * 60)
    print()
    
    try:
        import psycopg2
        print("✅ psycopg2 模組已安裝")
    except ImportError:
        print("❌ psycopg2 未安裝")
        print("   安裝命令: pip install psycopg2-binary")
        return False
    
    try:
        # 連接參數
        conn_params = {
            'dbname': 'ai_stock_db',
            'user': 'ai_stock_user',
            'password': 'ai_股_2025_secure',
            'host': 'localhost',
            'port': 5432
        }
        
        print(f"📡 嘗試連接到數據庫...")
        print(f"   Host: {conn_params['host']}")
        print(f"   Database: {conn_params['dbname']}")
        print(f"   User: {conn_params['user']}")
        print()
        
        # 連接
        conn = psycopg2.connect(**conn_params)
        print("✅ 成功連接到 PostgreSQL！")
        print()
        
        # 創建游標
        cursor = conn.cursor()
        
        # 測試 1: 查詢版本
        print("📊 測試 1: 查詢數據庫版本")
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   版本: {version.split(',')[0]}")
        print()
        
        # 測試 2: 查詢所有表
        print("📊 測試 2: 查詢所有表")
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = cursor.fetchall()
        print(f"   找到 {len(tables)} 個表:")
        for table in tables:
            print(f"   - {table[0]}")
        print()
        
        # 測試 3: 查詢 stocks 表數據
        print("📊 測試 3: 查詢 stocks 表")
        cursor.execute("SELECT symbol, name, market FROM stocks LIMIT 5;")
        stocks = cursor.fetchall()
        print(f"   找到 {len(stocks)} 筆股票資料:")
        for stock in stocks:
            print(f"   - {stock[0]}: {stock[1]} ({stock[2]})")
        print()
        
        # 測試 4: 插入測試數據
        print("📊 測試 4: 插入測試數據")
        cursor.execute("""
            INSERT INTO stocks (symbol, name, market, industry)
            VALUES ('9999', '測試股票', 'TEST', '測試')
            ON CONFLICT (symbol) DO NOTHING
            RETURNING id, symbol, name;
        """)
        result = cursor.fetchone()
        if result:
            print(f"   ✅ 插入成功: {result[1]} - {result[2]}")
        else:
            print(f"   ℹ️  資料已存在，跳過插入")
        
        # 刪除測試數據
        cursor.execute("DELETE FROM stocks WHERE symbol = '9999';")
        conn.commit()
        print(f"   ✅ 測試數據已清理")
        print()
        
        # 關閉連接
        cursor.close()
        conn.close()
        
        print("=" * 60)
        print("🎉 所有測試通過！")
        print("=" * 60)
        print()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ 連接錯誤: {e}")
        print()
        print("可能的原因：")
        print("1. PostgreSQL 服務未啟動")
        print("   解決: brew services start postgresql@14")
        print()
        print("2. 數據庫不存在")
        print("   解決: createdb ai_stock_db")
        print()
        print("3. 用戶不存在或密碼錯誤")
        print("   解決: 執行 backend-v3/database/setup_database.sql")
        print()
        return False
        
    except Exception as e:
        print(f"❌ 錯誤: {type(e).__name__}: {e}")
        return False


async def test_asyncpg():
    """測試 asyncpg 連接（異步）"""
    print()
    print("=" * 60)
    print("🔌 測試 PostgreSQL 連接（asyncpg - 異步）")
    print("=" * 60)
    print()
    
    try:
        import asyncpg
        print("✅ asyncpg 模組已安裝")
    except ImportError:
        print("❌ asyncpg 未安裝")
        print("   安裝命令: pip install asyncpg")
        return False
    
    try:
        # 連接字符串
        dsn = "postgresql://ai_stock_user:ai_stock_2025_secure@localhost/ai_stock_db"
        
        print(f"📡 嘗試異步連接...")
        print()
        
        # 連接
        conn = await asyncpg.connect(dsn)
        print("✅ 成功建立異步連接！")
        print()
        
        # 測試查詢
        print("📊 測試異步查詢")
        version = await conn.fetchval("SELECT version();")
        print(f"   版本: {version.split(',')[0]}")
        print()
        
        # 查詢多行
        stocks = await conn.fetch("""
            SELECT symbol, name 
            FROM stocks 
            LIMIT 3
        """)
        print(f"   查詢結果: {len(stocks)} 筆")
        for stock in stocks:
            print(f"   - {stock['symbol']}: {stock['name']}")
        print()
        
        # 關閉連接
        await conn.close()
        
        print("=" * 60)
        print("🎉 異步連接測試通過！")
        print("=" * 60)
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 錯誤: {type(e).__name__}: {e}")
        return False


def test_sqlalchemy():
    """測試 SQLAlchemy 連接（ORM）"""
    print()
    print("=" * 60)
    print("🔌 測試 SQLAlchemy 連接（ORM）")
    print("=" * 60)
    print()
    
    try:
        from sqlalchemy import create_engine, text
        print("✅ SQLAlchemy 模組已安裝")
    except ImportError:
        print("❌ SQLAlchemy 未安裝")
        print("   安裝命令: pip install sqlalchemy")
        return False
    
    try:
        # 創建引擎
        engine = create_engine(
            "postgresql://ai_stock_user:ai_stock_2025_secure@localhost/ai_stock_db"
        )
        
        print("📡 嘗試連接...")
        print()
        
        # 測試連接
        with engine.connect() as conn:
            print("✅ SQLAlchemy 連接成功！")
            print()
            
            # 查詢
            print("📊 測試 ORM 查詢")
            result = conn.execute(text("SELECT COUNT(*) FROM stocks"))
            count = result.scalar()
            print(f"   stocks 表記錄數: {count}")
            print()
        
        print("=" * 60)
        print("🎉 SQLAlchemy 測試通過！")
        print("=" * 60)
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 錯誤: {type(e).__name__}: {e}")
        return False


def main():
    """主測試函數"""
    print()
    print("🚀 PostgreSQL 連接測試")
    print()
    print("此腳本將測試三種連接方式：")
    print("1. psycopg2（同步，基礎）")
    print("2. asyncpg（異步，高性能）")
    print("3. SQLAlchemy（ORM，便捷）")
    print()
    
    results = []
    
    # 測試 1: psycopg2
    results.append(("psycopg2", test_psycopg2()))
    
    # 測試 2: asyncpg（異步）
    try:
        import asyncio
        results.append(("asyncpg", asyncio.run(test_asyncpg())))
    except Exception as e:
        print(f"⚠️  asyncpg 測試跳過: {e}")
        results.append(("asyncpg", None))
    
    # 測試 3: SQLAlchemy
    results.append(("SQLAlchemy", test_sqlalchemy()))
    
    # 總結
    print()
    print("=" * 60)
    print("📊 測試總結")
    print("=" * 60)
    print()
    
    for name, result in results:
        if result is True:
            status = "✅ 通過"
        elif result is False:
            status = "❌ 失敗"
        else:
            status = "⏭️  跳過"
        print(f"{name:15} {status}")
    
    print()
    
    # 判斷是否全部通過
    passed = sum(1 for _, r in results if r is True)
    total = len([r for _, r in results if r is not None])
    
    if passed == total and total > 0:
        print("🎉 所有測試通過！數據庫連接正常！")
        print()
        print("✅ 下一步:")
        print("   1. 安裝 Python 依賴: pip install -r backend-v3/requirements-v3.txt")
        print("   2. 配置 .env 文件")
        print("   3. 繼續 Day 1 下半天: Alembic 遷移")
        print()
        sys.exit(0)
    else:
        print(f"⚠️  部分測試失敗 ({passed}/{total})")
        print()
        print("請檢查：")
        print("1. PostgreSQL 是否已啟動")
        print("2. 數據庫是否已創建")
        print("3. SQL Schema 是否已執行")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
