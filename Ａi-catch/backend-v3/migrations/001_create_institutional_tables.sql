-- ============================================================
-- Migration 001: 法人籌碼系統資料表
-- 版本: 1.0.0
-- 日期: 2026-01-02
-- 描述: 創建三大法人買賣超、券商分點、融資融券、期貨/選擇權相關表
-- ============================================================

-- 設定時區
SET timezone = 'Asia/Taipei';

-- ============================================================
-- 1. 三大法人買賣超日報表 (institutional_trading)
-- 資料來源: 台灣證交所 T86 表
-- ============================================================
CREATE TABLE IF NOT EXISTS institutional_trading (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    
    -- 外資 (Foreign Investors)
    foreign_buy BIGINT DEFAULT 0,          -- 外資買進(張)
    foreign_sell BIGINT DEFAULT 0,         -- 外資賣出(張)
    foreign_net BIGINT DEFAULT 0,          -- 外資買賣超(張)
    foreign_buy_amount NUMERIC(20, 2),     -- 外資買進金額(元)
    foreign_sell_amount NUMERIC(20, 2),    -- 外資賣出金額(元)
    
    -- 投信 (Investment Trust)
    investment_buy BIGINT DEFAULT 0,       -- 投信買進(張)
    investment_sell BIGINT DEFAULT 0,      -- 投信賣出(張)
    investment_net BIGINT DEFAULT 0,       -- 投信買賣超(張)
    investment_buy_amount NUMERIC(20, 2),  -- 投信買進金額(元)
    investment_sell_amount NUMERIC(20, 2), -- 投信賣出金額(元)
    
    -- 自營商 (Dealers)
    dealer_buy BIGINT DEFAULT 0,           -- 自營商買進(張)
    dealer_sell BIGINT DEFAULT 0,          -- 自營商賣出(張)
    dealer_net BIGINT DEFAULT 0,           -- 自營商買賣超(張)
    dealer_buy_amount NUMERIC(20, 2),      -- 自營商買進金額(元)
    dealer_sell_amount NUMERIC(20, 2),     -- 自營商賣出金額(元)
    
    -- 合計
    total_net BIGINT DEFAULT 0,            -- 三大法人合計買賣超(張)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_institutional_date_symbol UNIQUE (trade_date, symbol)
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_institutional_date ON institutional_trading(trade_date);
CREATE INDEX IF NOT EXISTS ix_institutional_symbol ON institutional_trading(symbol);
CREATE INDEX IF NOT EXISTS ix_institutional_foreign_net ON institutional_trading(foreign_net);
CREATE INDEX IF NOT EXISTS ix_institutional_investment_net ON institutional_trading(investment_net);

-- 註解
COMMENT ON TABLE institutional_trading IS '三大法人買賣超日報表';
COMMENT ON COLUMN institutional_trading.foreign_net IS '外資買賣超張數，正數為買超，負數為賣超';

-- ============================================================
-- 2. 券商分點買賣超表 (branch_trading)
-- 資料來源: 富邦網站、Goodinfo 等
-- ============================================================
CREATE TABLE IF NOT EXISTS branch_trading (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    
    -- 券商分點資訊
    broker_code VARCHAR(20) NOT NULL,      -- 券商代碼 (如: 9600)
    broker_name VARCHAR(100) NOT NULL,     -- 券商名稱 (如: 富邦)
    branch_code VARCHAR(20) NOT NULL,      -- 分點代碼 (如: 9661)
    branch_name VARCHAR(100) NOT NULL,     -- 分點名稱 (如: 新店)
    
    -- 買賣數據
    buy_shares BIGINT DEFAULT 0,           -- 買進張數
    sell_shares BIGINT DEFAULT 0,          -- 賣出張數
    net_shares BIGINT DEFAULT 0,           -- 買賣超張數
    buy_amount NUMERIC(20, 2),             -- 買進金額
    sell_amount NUMERIC(20, 2),            -- 賣出金額
    net_amount NUMERIC(20, 2),             -- 買賣超金額
    
    -- 均價
    avg_buy_price NUMERIC(10, 2),          -- 買進均價
    avg_sell_price NUMERIC(10, 2),         -- 賣出均價
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_branch_date_symbol_branch UNIQUE (trade_date, symbol, branch_code)
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_branch_date ON branch_trading(trade_date);
CREATE INDEX IF NOT EXISTS ix_branch_symbol ON branch_trading(symbol);
CREATE INDEX IF NOT EXISTS ix_branch_code ON branch_trading(branch_code);
CREATE INDEX IF NOT EXISTS ix_branch_net_shares ON branch_trading(net_shares);

-- 註解
COMMENT ON TABLE branch_trading IS '券商分點買賣超表';

-- ============================================================
-- 3. 融資融券餘額表 (margin_trading)
-- 資料來源: 證交所公開資料
-- ============================================================
CREATE TABLE IF NOT EXISTS margin_trading (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    
    -- 融資 (Margin Purchase)
    margin_buy BIGINT DEFAULT 0,           -- 融資買進(張)
    margin_sell BIGINT DEFAULT 0,          -- 融資賣出(張)
    margin_cash_repay BIGINT DEFAULT 0,    -- 現金償還(張)
    margin_balance BIGINT DEFAULT 0,       -- 融資餘額(張)
    margin_balance_prev BIGINT DEFAULT 0,  -- 前日融資餘額(張)
    margin_change BIGINT DEFAULT 0,        -- 融資增減(張)
    margin_limit BIGINT,                   -- 融資限額(張)
    margin_utilization NUMERIC(5, 2),      -- 融資使用率(%)
    
    -- 融券 (Short Selling)
    short_sell BIGINT DEFAULT 0,           -- 融券賣出(張)
    short_buy BIGINT DEFAULT 0,            -- 融券買進(張)
    short_stock_repay BIGINT DEFAULT 0,    -- 現券償還(張)
    short_balance BIGINT DEFAULT 0,        -- 融券餘額(張)
    short_balance_prev BIGINT DEFAULT 0,   -- 前日融券餘額(張)
    short_change BIGINT DEFAULT 0,         -- 融券增減(張)
    short_limit BIGINT,                    -- 融券限額(張)
    short_utilization NUMERIC(5, 2),       -- 融券使用率(%)
    
    -- 資券比 (Margin/Short Ratio)
    margin_short_ratio NUMERIC(10, 2),     -- 資券比(%)
    
    -- 當沖相關
    day_trade_volume BIGINT,               -- 當沖張數
    day_trade_ratio NUMERIC(5, 2),         -- 當沖比率(%)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_margin_date_symbol UNIQUE (trade_date, symbol)
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_margin_date ON margin_trading(trade_date);
CREATE INDEX IF NOT EXISTS ix_margin_symbol ON margin_trading(symbol);
CREATE INDEX IF NOT EXISTS ix_margin_balance ON margin_trading(margin_balance);
CREATE INDEX IF NOT EXISTS ix_short_balance ON margin_trading(short_balance);

-- 註解
COMMENT ON TABLE margin_trading IS '融資融券餘額表';

-- ============================================================
-- 4. 期貨未平倉部位表 (futures_open_interest)
-- 資料來源: 台灣期貨交易所 (TAIFEX)
-- ============================================================
CREATE TABLE IF NOT EXISTS futures_open_interest (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    
    -- 契約資訊
    contract_code VARCHAR(20) NOT NULL,    -- 契約代碼 (TX=台指期, MTX=小台)
    contract_name VARCHAR(100) NOT NULL,   -- 契約名稱
    contract_month VARCHAR(10),            -- 到期月份
    
    -- 身份別 (foreign=外資, investment=投信, dealer=自營商)
    identity_type VARCHAR(20) NOT NULL,
    
    -- 多單部位
    long_position BIGINT DEFAULT 0,        -- 多單口數
    long_amount NUMERIC(20, 2),            -- 多單金額
    
    -- 空單部位
    short_position BIGINT DEFAULT 0,       -- 空單口數
    short_amount NUMERIC(20, 2),           -- 空單金額
    
    -- 淨部位
    net_position BIGINT DEFAULT 0,         -- 淨多單口數(多-空)
    net_position_change BIGINT DEFAULT 0,  -- 淨部位增減
    
    -- 未平倉合計
    total_oi BIGINT DEFAULT 0,             -- 未平倉總口數
    total_oi_change BIGINT DEFAULT 0,      -- 未平倉增減
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_futures_date_contract_identity UNIQUE (trade_date, contract_code, identity_type)
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_futures_date ON futures_open_interest(trade_date);
CREATE INDEX IF NOT EXISTS ix_futures_contract ON futures_open_interest(contract_code);
CREATE INDEX IF NOT EXISTS ix_futures_identity ON futures_open_interest(identity_type);
CREATE INDEX IF NOT EXISTS ix_futures_net_position ON futures_open_interest(net_position);

-- 註解
COMMENT ON TABLE futures_open_interest IS '期貨未平倉部位表';
COMMENT ON COLUMN futures_open_interest.net_position IS '淨多單口數，正數為淨多單，負數為淨空單';

-- ============================================================
-- 5. 選擇權未平倉部位表 (options_open_interest)
-- 資料來源: 台灣期貨交易所 (TAIFEX)
-- ============================================================
CREATE TABLE IF NOT EXISTS options_open_interest (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    
    -- 契約資訊
    contract_code VARCHAR(20) NOT NULL,    -- 契約代碼 (TXO=台指選)
    contract_name VARCHAR(100) NOT NULL,   -- 契約名稱
    contract_month VARCHAR(10),            -- 到期月份
    
    -- 選擇權類型 (call=買權, put=賣權)
    option_type VARCHAR(10) NOT NULL,
    
    -- 身份別
    identity_type VARCHAR(20) NOT NULL,
    
    -- 買方部位
    buy_position BIGINT DEFAULT 0,         -- 買方口數
    buy_amount NUMERIC(20, 2),             -- 買方金額
    
    -- 賣方部位
    sell_position BIGINT DEFAULT 0,        -- 賣方口數
    sell_amount NUMERIC(20, 2),            -- 賣方金額
    
    -- 淨部位
    net_position BIGINT DEFAULT 0,         -- 淨口數(買-賣)
    net_position_change BIGINT DEFAULT 0,  -- 淨部位增減
    
    -- 未平倉合計
    total_oi BIGINT DEFAULT 0,             -- 未平倉總口數
    total_oi_change BIGINT DEFAULT 0,      -- 未平倉增減
    
    -- P/C Ratio 相關
    put_call_ratio NUMERIC(10, 4),         -- 賣權/買權比
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_options_date_contract_type_identity UNIQUE (trade_date, contract_code, option_type, identity_type)
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_options_date ON options_open_interest(trade_date);
CREATE INDEX IF NOT EXISTS ix_options_contract ON options_open_interest(contract_code);
CREATE INDEX IF NOT EXISTS ix_options_type ON options_open_interest(option_type);
CREATE INDEX IF NOT EXISTS ix_options_identity ON options_open_interest(identity_type);

-- 註解
COMMENT ON TABLE options_open_interest IS '選擇權未平倉部位表';

-- ============================================================
-- 6. 法人連續買賣超統計表 (institutional_continuous)
-- 計算結果表，用於加速 API 響應
-- ============================================================
CREATE TABLE IF NOT EXISTS institutional_continuous (
    id BIGSERIAL PRIMARY KEY,
    calc_date DATE NOT NULL,               -- 計算日期
    symbol VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    
    -- 外資連續性
    foreign_direction VARCHAR(10),         -- 外資方向(buy/sell)
    foreign_continuous_days INTEGER DEFAULT 0,      -- 外資連續天數
    foreign_continuous_shares BIGINT DEFAULT 0,     -- 外資連續累計張數
    
    -- 投信連續性
    investment_direction VARCHAR(10),      -- 投信方向(buy/sell)
    investment_continuous_days INTEGER DEFAULT 0,   -- 投信連續天數
    investment_continuous_shares BIGINT DEFAULT 0,  -- 投信連續累計張數
    
    -- 自營商連續性
    dealer_direction VARCHAR(10),          -- 自營商方向(buy/sell)
    dealer_continuous_days INTEGER DEFAULT 0,       -- 自營商連續天數
    dealer_continuous_shares BIGINT DEFAULT 0,      -- 自營商連續累計張數
    
    -- 籌碼集中度分數
    chip_concentration_score NUMERIC(5, 2), -- 籌碼集中度分數(0-100)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_continuous_date_symbol UNIQUE (calc_date, symbol)
);

-- 索引
CREATE INDEX IF NOT EXISTS ix_continuous_date ON institutional_continuous(calc_date);
CREATE INDEX IF NOT EXISTS ix_continuous_symbol ON institutional_continuous(symbol);
CREATE INDEX IF NOT EXISTS ix_continuous_foreign_days ON institutional_continuous(foreign_continuous_days);
CREATE INDEX IF NOT EXISTS ix_continuous_investment_days ON institutional_continuous(investment_continuous_days);

-- 註解
COMMENT ON TABLE institutional_continuous IS '法人連續買賣超統計表';

-- ============================================================
-- 7. 建立檢視表 (Views) 方便查詢
-- ============================================================

-- 外資連續買超前20名
CREATE OR REPLACE VIEW v_foreign_continuous_buy_top AS
SELECT 
    symbol,
    stock_name,
    foreign_continuous_days,
    foreign_continuous_shares,
    calc_date
FROM institutional_continuous
WHERE foreign_direction = 'buy' 
  AND calc_date = (SELECT MAX(calc_date) FROM institutional_continuous)
ORDER BY foreign_continuous_days DESC, foreign_continuous_shares DESC
LIMIT 20;

-- 投信連續買超前20名
CREATE OR REPLACE VIEW v_investment_continuous_buy_top AS
SELECT 
    symbol,
    stock_name,
    investment_continuous_days,
    investment_continuous_shares,
    calc_date
FROM institutional_continuous
WHERE investment_direction = 'buy' 
  AND calc_date = (SELECT MAX(calc_date) FROM institutional_continuous)
ORDER BY investment_continuous_days DESC, investment_continuous_shares DESC
LIMIT 20;

-- 外資期貨多空部位摘要
CREATE OR REPLACE VIEW v_futures_foreign_summary AS
SELECT 
    trade_date,
    SUM(long_position) as total_long,
    SUM(short_position) as total_short,
    SUM(net_position) as total_net
FROM futures_open_interest
WHERE identity_type = 'foreign' 
  AND contract_code IN ('TX', 'MTX')
GROUP BY trade_date
ORDER BY trade_date DESC;

-- 融資融券異常股票 (融資大增或融券大增)
CREATE OR REPLACE VIEW v_margin_abnormal AS
SELECT 
    symbol,
    stock_name,
    trade_date,
    margin_change,
    short_change,
    margin_short_ratio,
    CASE 
        WHEN margin_change > 500 THEN '融資大增'
        WHEN margin_change < -500 THEN '融資大減'
        WHEN short_change > 200 THEN '融券大增'
        WHEN short_change < -200 THEN '融券大減'
        ELSE '正常'
    END as abnormal_type
FROM margin_trading
WHERE trade_date = (SELECT MAX(trade_date) FROM margin_trading)
  AND (ABS(margin_change) > 500 OR ABS(short_change) > 200)
ORDER BY ABS(margin_change) + ABS(short_change) DESC;

-- ============================================================
-- 8. 記錄 Migration 版本
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version, description) 
VALUES ('001', '創建法人籌碼系統資料表')
ON CONFLICT (version) DO NOTHING;

-- ============================================================
-- 完成
-- ============================================================
SELECT '✅ Migration 001 執行完成' as status;
