"""add portfolio tables

Revision ID: 001_add_portfolio
Revises: 
Create Date: 2025-12-22

添加持有股票和交易紀錄資料表
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_portfolio'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 創建持有股票表
    op.create_table(
        'portfolio',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('stock_name', sa.String(100), nullable=True),
        
        # 進場資訊
        sa.Column('entry_date', sa.DateTime(), nullable=False, index=True),
        sa.Column('entry_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('entry_quantity', sa.Integer(), nullable=False, default=1000),
        
        # 分析來源
        sa.Column('analysis_source', sa.String(50), nullable=False, index=True),
        sa.Column('analysis_confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('analysis_details', postgresql.JSON(), nullable=True),
        
        # 價格設定
        sa.Column('stop_loss_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('stop_loss_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('target_price', sa.Numeric(10, 2), nullable=True),
        
        # 當前狀態
        sa.Column('current_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('unrealized_profit', sa.Numeric(12, 2), nullable=True),
        sa.Column('unrealized_profit_percent', sa.Numeric(6, 2), nullable=True),
        
        # 出場資訊
        sa.Column('exit_date', sa.DateTime(), nullable=True),
        sa.Column('exit_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('exit_reason', sa.String(100), nullable=True),
        
        # 實現損益
        sa.Column('realized_profit', sa.Numeric(12, 2), nullable=True),
        sa.Column('realized_profit_percent', sa.Numeric(6, 2), nullable=True),
        
        # 狀態
        sa.Column('status', sa.String(20), default='open', index=True),
        sa.Column('is_simulated', sa.Boolean(), default=False),
        
        # 備註
        sa.Column('notes', sa.Text(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 創建交易紀錄表
    op.create_table(
        'trade_records',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('portfolio_id', sa.BigInteger(), nullable=True, index=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('stock_name', sa.String(100), nullable=True),
        
        # 交易類型
        sa.Column('trade_type', sa.String(10), nullable=False),  # buy/sell
        sa.Column('trade_date', sa.DateTime(), nullable=False, index=True),
        
        # 價格資訊
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1000),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False),
        
        # 分析來源
        sa.Column('analysis_source', sa.String(50), nullable=False, index=True),
        sa.Column('analysis_confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('analysis_details', postgresql.JSON(), nullable=True),
        
        # 損益（賣出時記錄）
        sa.Column('profit', sa.Numeric(12, 2), nullable=True),
        sa.Column('profit_percent', sa.Numeric(6, 2), nullable=True),
        
        # 是否為模擬
        sa.Column('is_simulated', sa.Boolean(), default=False),
        
        # 備註
        sa.Column('notes', sa.Text(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), index=True),
    )
    
    # 創建分析準確性表
    op.create_table(
        'analysis_accuracy',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('analysis_source', sa.String(50), nullable=False, index=True),
        
        # 統計期間
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        
        # 交易統計
        sa.Column('total_trades', sa.Integer(), default=0),
        sa.Column('winning_trades', sa.Integer(), default=0),
        sa.Column('losing_trades', sa.Integer(), default=0),
        
        # 損益統計
        sa.Column('total_profit', sa.Numeric(12, 2), default=0),
        sa.Column('total_loss', sa.Numeric(12, 2), default=0),
        sa.Column('net_profit', sa.Numeric(12, 2), default=0),
        
        # 準確率指標
        sa.Column('win_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('avg_profit_percent', sa.Numeric(6, 2), nullable=True),
        sa.Column('avg_loss_percent', sa.Numeric(6, 2), nullable=True),
        sa.Column('profit_factor', sa.Numeric(6, 2), nullable=True),
        sa.Column('risk_reward_ratio', sa.Numeric(6, 2), nullable=True),
        
        # 詳細數據
        sa.Column('details', postgresql.JSON(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # 創建索引
    op.create_index('ix_portfolio_symbol_status', 'portfolio', ['symbol', 'status'])
    op.create_index('ix_trade_records_symbol_date', 'trade_records', ['symbol', 'trade_date'])


def downgrade() -> None:
    op.drop_index('ix_trade_records_symbol_date', table_name='trade_records')
    op.drop_index('ix_portfolio_symbol_status', table_name='portfolio')
    op.drop_table('analysis_accuracy')
    op.drop_table('trade_records')
    op.drop_table('portfolio')
