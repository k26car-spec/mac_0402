-- 訊號追蹤資料庫 Schema
-- 用於持久化被拒絕訊號的追蹤數據

-- 1. 拒絕訊號主表
CREATE TABLE IF NOT EXISTS rejected_signals (
    signal_id VARCHAR(100) PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    reject_time TIMESTAMP NOT NULL,
    
    -- 拒絕時的市場狀況
    price_at_reject DECIMAL(10, 2) NOT NULL,
    vwap DECIMAL(10, 2) NOT NULL,
    vwap_deviation DECIMAL(5, 2) NOT NULL,
    kd_k DECIMAL(5, 2),
    kd_d DECIMAL(5, 2),
    ofi DECIMAL(10, 2),
    volume_trend VARCHAR(20),
    price_trend VARCHAR(20),
    
    -- 風險評估
    risk_score INT,
    
    -- 虛擬交易參數
    virtual_entry_price DECIMAL(10, 2),
    virtual_stop_loss DECIMAL(10, 2),
    virtual_take_profit DECIMAL(10, 2),
    
    -- 追蹤結果
    price_after_30min DECIMAL(10, 2),
    price_after_1hour DECIMAL(10, 2),
    price_after_2hour DECIMAL(10, 2),
    highest_price DECIMAL(10, 2),
    lowest_price DECIMAL(10, 2),
    
    -- 分析結果
    would_profit BOOLEAN,
    would_hit_stop_loss BOOLEAN,
    would_hit_take_profit BOOLEAN,
    virtual_pnl_percent DECIMAL(5, 2),
    decision_quality VARCHAR(50),
    
    -- 元數據
    tracking_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 拒絕原因表
CREATE TABLE IF NOT EXISTS rejection_reasons (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(100) REFERENCES rejected_signals(signal_id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    reason_category VARCHAR(50),
    severity INT
);

-- 3. 追蹤快照表
CREATE TABLE IF NOT EXISTS tracking_snapshots (
    id SERIAL PRIMARY KEY,
    signal_id VARCHAR(100) REFERENCES rejected_signals(signal_id) ON DELETE CASCADE,
    snapshot_time TIMESTAMP NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    volume INT,
    ofi DECIMAL(10, 2)
);

-- 4. 週報統計表
CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id VARCHAR(50) PRIMARY KEY,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- 整體統計
    total_signals INT,
    total_rejected INT,
    rejection_rate DECIMAL(5, 2),
    
    -- 決策品質
    correct_rejections INT,
    incorrect_rejections INT,
    ambiguous_decisions INT,
    decision_accuracy DECIMAL(5, 2),
    
    -- 損益分析
    avg_missed_profit DECIMAL(5, 2),
    avg_avoided_loss DECIMAL(5, 2),
    expected_value_if_entered DECIMAL(5, 2),
    net_benefit DECIMAL(5, 2),
    
    -- 元數據
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. 拒絕原因統計表
CREATE TABLE IF NOT EXISTS reason_statistics (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(50) REFERENCES weekly_reports(report_id) ON DELETE CASCADE,
    reason VARCHAR(100) NOT NULL,
    
    total_count INT,
    profitable_count INT,
    unprofitable_count INT,
    win_rate DECIMAL(5, 2),
    avg_pnl DECIMAL(5, 2),
    decision_accuracy DECIMAL(5, 2),
    expected_value DECIMAL(5, 2)
);

-- 6. 系統建議表
CREATE TABLE IF NOT EXISTS system_recommendations (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(50) REFERENCES weekly_reports(report_id) ON DELETE CASCADE,
    recommendation_text TEXT NOT NULL,
    priority VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_rejected_signals_stock_code ON rejected_signals(stock_code);
CREATE INDEX IF NOT EXISTS idx_rejected_signals_reject_time ON rejected_signals(reject_time);
CREATE INDEX IF NOT EXISTS idx_rejected_signals_decision_quality ON rejected_signals(decision_quality);
CREATE INDEX IF NOT EXISTS idx_rejection_reasons_signal_id ON rejection_reasons(signal_id);
CREATE INDEX IF NOT EXISTS idx_tracking_snapshots_signal_id ON tracking_snapshots(signal_id);
CREATE INDEX IF NOT EXISTS idx_weekly_reports_date_range ON weekly_reports(start_date, end_date);
