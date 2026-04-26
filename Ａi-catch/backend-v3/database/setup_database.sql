-- ================================================
-- AI Stock Intelligence Database Setup
-- PostgreSQL 14+ 
-- ================================================

-- 清理舊數據（如果需要重新開始）
-- DROP DATABASE IF EXISTS ai_stock_db;
-- DROP USER IF EXISTS ai_stock_user;

-- ================================================
-- 1. 創建用戶和數據庫
-- ================================================

-- 創建用戶（如果直接用 createdb 已經創建了數據庫，可以跳過創建數據庫步驟）
-- 注意：請將密碼改為更安全的密碼
CREATE USER ai_stock_user WITH PASSWORD 'ai_stock_2025_secure';

-- 授予創建數據庫權限
ALTER USER ai_stock_user CREATEDB;

-- 連接到 ai_stock_db 數據庫後執行以下命令
-- 授予所有權限
GRANT ALL PRIVILEGES ON DATABASE ai_stock_db TO ai_stock_user;

-- PostgreSQL 15+ 需要額外授權 schema
GRANT ALL ON SCHEMA public TO ai_stock_user;

-- ================================================
-- 2. 創建擴展
-- ================================================

-- UUID 支持
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 全文搜索（中文支持）
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ================================================
-- 3. 創建主要數據表
-- ================================================

-- 3.1 股票基本資料表
CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,           -- 股票代碼（如：2330）
    name VARCHAR(100) NOT NULL,                   -- 股票名稱（如：台積電）
    market VARCHAR(20) DEFAULT 'TWSE',            -- 市場（TWSE/OTC）
    industry VARCHAR(50),                         -- 產業別
    sector VARCHAR(50),                           -- 類股
    listed_date DATE,                             -- 上市日期
    is_active BOOLEAN DEFAULT true,               -- 是否活躍
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_stocks_symbol ON stocks(symbol);
CREATE INDEX idx_stocks_market ON stocks(market);
CREATE INDEX idx_stocks_active ON stocks(is_active);

-- 3.2 即時報價表
CREATE TABLE IF NOT EXISTS stock_quotes (
    id BIGSERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,                  -- 冗余欄位，便於查詢
    timestamp TIMESTAMP NOT NULL,                  -- 報價時間
    open DECIMAL(10, 2),                          -- 開盤價
    high DECIMAL(10, 2),                          -- 最高價
    low DECIMAL(10, 2),                           -- 最低價
    close DECIMAL(10, 2) NOT NULL,                -- 收盤價/即時價
    volume BIGINT,                                -- 成交量
    amount DECIMAL(20, 2),                        -- 成交金額
    change_price DECIMAL(10, 2),                  -- 漲跌價
    change_percent DECIMAL(5, 2),                 -- 漲跌幅%
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_quotes_stock_id ON stock_quotes(stock_id);
CREATE INDEX idx_quotes_symbol ON stock_quotes(symbol);
CREATE INDEX idx_quotes_timestamp ON stock_quotes(timestamp DESC);
CREATE INDEX idx_quotes_stock_time ON stock_quotes(stock_id, timestamp DESC);

-- 3.3 五檔掛單表
CREATE TABLE IF NOT EXISTS order_books (
    id BIGSERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    
    -- 買盤（5檔）
    bid_price_1 DECIMAL(10, 2),
    bid_volume_1 BIGINT,
    bid_price_2 DECIMAL(10, 2),
    bid_volume_2 BIGINT,
    bid_price_3 DECIMAL(10, 2),
    bid_volume_3 BIGINT,
    bid_price_4 DECIMAL(10, 2),
    bid_volume_4 BIGINT,
    bid_price_5 DECIMAL(10, 2),
    bid_volume_5 BIGINT,
    
    -- 賣盤（5檔）
    ask_price_1 DECIMAL(10, 2),
    ask_volume_1 BIGINT,
    ask_price_2 DECIMAL(10, 2),
    ask_volume_2 BIGINT,
    ask_price_3 DECIMAL(10, 2),
    ask_volume_3 BIGINT,
    ask_price_4 DECIMAL(10, 2),
    ask_volume_4 BIGINT,
    ask_price_5 DECIMAL(10, 2),
    ask_volume_5 BIGINT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_orderbook_stock_id ON order_books(stock_id);
CREATE INDEX idx_orderbook_timestamp ON order_books(timestamp DESC);

-- 3.4 專家信號表
CREATE TABLE IF NOT EXISTS expert_signals (
    id BIGSERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    expert_name VARCHAR(50) NOT NULL,             -- 專家名稱
    signal_type VARCHAR(20) NOT NULL,             -- 信號類型（buy/sell/hold）
    strength DECIMAL(3, 2) NOT NULL,              -- 信號強度（0-1）
    confidence DECIMAL(3, 2) NOT NULL,            -- 信心度（0-1）
    timeframe VARCHAR(10),                        -- 時間框架（1m/5m/15m/1h/1d）
    reasoning TEXT,                               -- 判斷理由
    metadata JSONB,                               -- 額外數據（JSON格式）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_signals_stock_id ON expert_signals(stock_id);
CREATE INDEX idx_signals_symbol ON expert_signals(symbol);
CREATE INDEX idx_signals_expert ON expert_signals(expert_name);
CREATE INDEX idx_signals_created ON expert_signals(created_at DESC);
CREATE INDEX idx_signals_metadata ON expert_signals USING gin(metadata);

-- 3.5 分析結果表
CREATE TABLE IF NOT EXISTS analysis_results (
    id BIGSERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    analysis_type VARCHAR(50) NOT NULL,           -- 分析類型
    timeframe VARCHAR(10),                        -- 時間框架
    
    -- 主力偵測結果
    mainforce_action VARCHAR(20),                 -- entry/exit/consolidation
    mainforce_confidence DECIMAL(3, 2),
    
    -- 綜合評分
    overall_score DECIMAL(3, 2),                  -- 0-1
    recommendation VARCHAR(20),                   -- strong_buy/buy/hold/sell/strong_sell
    
    -- 風險評估
    risk_level VARCHAR(20),                       -- low/medium/high
    risk_score DECIMAL(3, 2),
    
    -- 詳細數據
    details JSONB,                                -- 詳細分析數據
    expert_summary JSONB,                         -- 專家意見摘要
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_analysis_stock_id ON analysis_results(stock_id);
CREATE INDEX idx_analysis_symbol ON analysis_results(symbol);
CREATE INDEX idx_analysis_type ON analysis_results(analysis_type);
CREATE INDEX idx_analysis_created ON analysis_results(created_at DESC);
CREATE INDEX idx_analysis_details ON analysis_results USING gin(details);

-- 3.6 警報表
CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,              -- 警報類型
    severity VARCHAR(20) NOT NULL,                -- low/medium/high/critical
    title VARCHAR(200) NOT NULL,                  -- 警報標題
    message TEXT NOT NULL,                        -- 警報內容
    triggered_by VARCHAR(50),                     -- 觸發者（專家名稱）
    
    -- 狀態
    status VARCHAR(20) DEFAULT 'active',          -- active/acknowledged/resolved
    is_sent BOOLEAN DEFAULT false,                -- 是否已發送通知
    sent_at TIMESTAMP,                            -- 發送時間
    
    -- 額外數據
    metadata JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_alerts_stock_id ON alerts(stock_id);
CREATE INDEX idx_alerts_symbol ON alerts(symbol);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_created ON alerts(created_at DESC);

-- 3.7 LSTM 預測結果表
CREATE TABLE IF NOT EXISTS lstm_predictions (
    id BIGSERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    prediction_date DATE NOT NULL,                -- 預測日期
    
    -- 預測價格
    predicted_close DECIMAL(10, 2),               -- 預測收盤價
    predicted_high DECIMAL(10, 2),                -- 預測最高價
    predicted_low DECIMAL(10, 2),                 -- 預測最低價
    
    -- 預測信心度
    confidence DECIMAL(3, 2),                     -- 0-1
    
    -- 模型信息
    model_version VARCHAR(50),                    -- 模型版本
    training_accuracy DECIMAL(5, 4),              -- 訓練準確度
    
    -- 實際結果（用於驗證）
    actual_close DECIMAL(10, 2),                  -- 實際收盤價
    accuracy DECIMAL(5, 4),                       -- 預測準確度
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_lstm_stock_id ON lstm_predictions(stock_id);
CREATE INDEX idx_lstm_symbol ON lstm_predictions(symbol);
CREATE INDEX idx_lstm_date ON lstm_predictions(prediction_date DESC);

-- 3.8 用戶表（可選）
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),                   -- 加密後的密碼
    role VARCHAR(20) DEFAULT 'user',              -- admin/user
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- ================================================
-- 4. 創建視圖（便於查詢）
-- ================================================

-- 4.1 最新報價視圖
CREATE OR REPLACE VIEW latest_quotes AS
SELECT DISTINCT ON (symbol)
    sq.*,
    s.name,
    s.industry
FROM stock_quotes sq
JOIN stocks s ON sq.stock_id = s.id
ORDER BY symbol, timestamp DESC;

-- 4.2 活躍警報視圖
CREATE OR REPLACE VIEW active_alerts AS
SELECT 
    a.*,
    s.name as stock_name
FROM alerts a
JOIN stocks s ON a.stock_id = s.id
WHERE a.status = 'active'
ORDER BY a.created_at DESC;

-- 4.3 專家信號摘要視圖
CREATE OR REPLACE VIEW expert_signals_summary AS
SELECT 
    symbol,
    expert_name,
    signal_type,
    AVG(strength) as avg_strength,
    AVG(confidence) as avg_confidence,
    COUNT(*) as signal_count,
    MAX(created_at) as latest_signal
FROM expert_signals
WHERE created_at > NOW() - INTERVAL '1 day'
GROUP BY symbol, expert_name, signal_type;

-- ================================================
-- 5. 創建函數
-- ================================================

-- 5.1 自動更新 updated_at 的觸發函數
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 5.2 應用觸發器
CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- 6. 插入初始數據
-- ================================================

-- 插入一些常見台股
INSERT INTO stocks (symbol, name, market, industry) VALUES
    ('2330', '台積電', 'TWSE', '半導體'),
    ('2317', '鴻海', 'TWSE', '電子'),
    ('2454', '聯發科', 'TWSE', '半導體'),
    ('2308', '台達電', 'TWSE', '電子'),
    ('2882', '國泰金', 'TWSE', '金融'),
    ('2891', '中信金', 'TWSE', '金融'),
    ('2344', '華邦電', 'TWSE', '半導體'),
    ('8110', '華東', 'OTC', '電子'),
    ('8021', '尖點', 'OTC', '電子'),
    ('3706', '神達', 'TWSE', '電子'),
    ('5521', '工信', 'OTC', '電子')
ON CONFLICT (symbol) DO NOTHING;

-- ================================================
-- 7. 授權
-- ================================================

-- 授予表權限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ai_stock_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ai_stock_user;

-- ================================================
-- 完成
-- ================================================

-- 顯示創建的表
SELECT 
    tablename,
    schemaname
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 顯示表大小
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
