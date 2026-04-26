'use client';

import { useState, useEffect, useCallback } from 'react';

interface PortfolioSummary {
    open_positions_count: number;
    closed_positions_count: number;
    total_unrealized_profit: number;
    total_realized_profit: number;
    total_profit: number;
    win_rate: number;
    wins: number;
    losses: number;
    source_breakdown: Record<string, { count: number; unrealized: number }>;
}

interface AccuracyData {
    analysis_source: string;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    net_profit: number;
    avg_profit_percent: number | null;
    avg_loss_percent: number | null;
}

interface Trade {
    id: number;
    portfolio_id: number | null;
    symbol: string;
    stock_name: string | null;
    trade_type: string;
    trade_date: string;
    price: number;
    quantity: number;
    total_amount: number;
    analysis_source: string;
    analysis_confidence: number | null;
    profit: number | null;
    profit_percent: number | null;
    is_simulated: boolean;
    notes: string | null;
    created_at: string;
}

interface Position {
    id: number;
    symbol: string;
    stock_name: string | null;
    entry_date: string;
    entry_price: number;
    entry_quantity: number;
    current_price: number | null;
    unrealized_profit: number | null;
    unrealized_profit_percent: number | null;
    analysis_source: string;
    target_price: number | null;
    stop_loss_price: number | null;
    status: string;
    is_simulated: boolean;
    realized_profit: number | null;
    realized_profit_percent: number | null;
    exit_price: number | null;
    exit_date: string | null;
}

const API_BASE = 'http://localhost:8000';

export default function AIPerformancePage() {
    const [summary, setSummary] = useState<PortfolioSummary | null>(null);
    const [accuracy, setAccuracy] = useState<AccuracyData[]>([]);
    const [trades, setTrades] = useState<Trade[]>([]);
    const [openPositions, setOpenPositions] = useState<Position[]>([]);
    const [closedPositions, setClosedPositions] = useState<Position[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'overview' | 'trades' | 'analysis'>('overview');
    const [error, setError] = useState<string | null>(null);

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const [summaryRes, accuracyRes, tradesRes, openRes, closedRes] = await Promise.all([
                fetch(`${API_BASE}/api/portfolio/summary`),
                fetch(`${API_BASE}/api/portfolio/accuracy?days=90`),
                fetch(`${API_BASE}/api/portfolio/trades?limit=50`),
                fetch(`${API_BASE}/api/portfolio/positions?status=open`),
                fetch(`${API_BASE}/api/portfolio/positions?status=closed`)
            ]);

            if (summaryRes.ok) {
                const data = await summaryRes.json();
                setSummary(data);
            }

            if (accuracyRes.ok) {
                const data = await accuracyRes.json();
                setAccuracy(data);
            }

            if (tradesRes.ok) {
                const data = await tradesRes.json();
                setTrades(data);
            }

            if (openRes.ok) {
                const data = await openRes.json();
                setOpenPositions(data);
            }

            if (closedRes.ok) {
                const data = await closedRes.json();
                setClosedPositions(data);
            }

        } catch (err) {
            setError('無法連接 API 伺服器');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, [fetchData]);

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'target_hit': return '#10b981';
            case 'stopped': return '#ef4444';
            case 'closed': return '#6b7280';
            case 'open': return '#3b82f6';
            default: return '#6b7280';
        }
    };

    const getStatusText = (status: string) => {
        switch (status) {
            case 'target_hit': return '✅ 達標';
            case 'stopped': return '❌ 停損';
            case 'closed': return '📋 已結束';
            case 'open': return '🔵 持倉中';
            default: return status;
        }
    };

    if (loading && !summary) {
        return (
            <div style={styles.container}>
                <div style={styles.loadingContainer}>
                    <div style={styles.spinner}></div>
                    <p>載入中...</p>
                </div>
            </div>
        );
    }

    return (
        <div style={styles.container}>
            {/* Header */}
            <header style={styles.header}>
                <div style={styles.headerContent}>
                    <h1 style={styles.title}>🤖 AI 績效追蹤儀表板</h1>
                    <p style={styles.subtitle}>追蹤 AI 交易決策的準確性（整合 Portfolio 數據）</p>
                </div>
                <button onClick={fetchData} style={styles.refreshBtn}>
                    🔄 刷新
                </button>
            </header>

            {error && (
                <div style={styles.errorBanner}>
                    ⚠️ {error}
                </div>
            )}

            {/* Tabs */}
            <div style={styles.tabs}>
                <button
                    style={activeTab === 'overview' ? styles.tabActive : styles.tab}
                    onClick={() => setActiveTab('overview')}
                >
                    📊 總覽
                </button>
                <button
                    style={activeTab === 'trades' ? styles.tabActive : styles.tab}
                    onClick={() => setActiveTab('trades')}
                >
                    📋 交易記錄
                </button>
                <button
                    style={activeTab === 'analysis' ? styles.tabActive : styles.tab}
                    onClick={() => setActiveTab('analysis')}
                >
                    🔬 來源分析
                </button>
            </div>

            {/* Overview Tab */}
            {activeTab === 'overview' && (
                <div style={styles.content}>
                    {/* Stats Cards */}
                    <div style={styles.statsGrid}>
                        <div style={styles.statCard}>
                            <div style={styles.statLabel}>總交易</div>
                            <div style={styles.statValue}>
                                {(summary?.open_positions_count || 0) + (summary?.closed_positions_count || 0)}
                            </div>
                        </div>
                        <div style={styles.statCard}>
                            <div style={styles.statLabel}>勝率</div>
                            <div style={{
                                ...styles.statValue,
                                color: (summary?.win_rate || 0) >= 50 ? '#ef4444' : '#10b981'
                            }}>
                                {summary?.win_rate?.toFixed(1) || 0}%
                            </div>
                        </div>
                        <div style={styles.statCard}>
                            <div style={styles.statLabel}>獲勝 / 虧損</div>
                            <div style={styles.statValue}>
                                <span style={{ color: '#ef4444' }}>{summary?.wins || 0}</span>
                                {' / '}
                                <span style={{ color: '#10b981' }}>{summary?.losses || 0}</span>
                            </div>
                        </div>
                        <div style={styles.statCard}>
                            <div style={styles.statLabel}>總損益</div>
                            <div style={{
                                ...styles.statValue,
                                color: (summary?.total_profit || 0) >= 0 ? '#ef4444' : '#10b981'
                            }}>
                                {(summary?.total_profit || 0) >= 0 ? '+' : ''}
                                ${summary?.total_profit?.toLocaleString() || 0}
                            </div>
                        </div>
                    </div>

                    {/* Profit Breakdown */}
                    <div style={styles.section}>
                        <h2 style={styles.sectionTitle}>💰 損益分析</h2>
                        <div style={styles.profitGrid}>
                            <div style={styles.profitCard}>
                                <div style={styles.profitLabel}>未實現損益（持倉中）</div>
                                <div style={{
                                    ...styles.profitValue,
                                    color: (summary?.total_unrealized_profit || 0) >= 0 ? '#ef4444' : '#10b981'
                                }}>
                                    {(summary?.total_unrealized_profit || 0) >= 0 ? '+' : ''}
                                    ${summary?.total_unrealized_profit?.toLocaleString() || 0}
                                </div>
                                <div style={styles.profitSubtext}>{summary?.open_positions_count || 0} 個持倉</div>
                            </div>
                            <div style={styles.profitCard}>
                                <div style={styles.profitLabel}>已實現損益（已結束）</div>
                                <div style={{
                                    ...styles.profitValue,
                                    color: (summary?.total_realized_profit || 0) >= 0 ? '#ef4444' : '#10b981'
                                }}>
                                    {(summary?.total_realized_profit || 0) >= 0 ? '+' : ''}
                                    ${summary?.total_realized_profit?.toLocaleString() || 0}
                                </div>
                                <div style={styles.profitSubtext}>{summary?.closed_positions_count || 0} 筆交易</div>
                            </div>
                        </div>
                    </div>

                    {/* Source Breakdown */}
                    {summary?.source_breakdown && Object.keys(summary.source_breakdown).length > 0 && (
                        <div style={styles.section}>
                            <h2 style={styles.sectionTitle}>📈 按訊號來源分析（持倉中）</h2>
                            <div style={styles.sourceGrid}>
                                {Object.entries(summary.source_breakdown).map(([source, data]) => (
                                    <div key={source} style={styles.sourceCard}>
                                        <div style={styles.sourceName}>{source}</div>
                                        <div style={styles.sourceStats}>
                                            <span>{data.count} 筆</span>
                                            <span style={{
                                                color: data.unrealized >= 0 ? '#ef4444' : '#10b981',
                                                fontWeight: 'bold'
                                            }}>
                                                {data.unrealized >= 0 ? '+' : ''}${data.unrealized.toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Open Positions */}
                    {openPositions.length > 0 && (
                        <div style={styles.section}>
                            <h2 style={styles.sectionTitle}>🔵 目前持倉 ({openPositions.length})</h2>
                            <div style={styles.positionList}>
                                {openPositions.slice(0, 10).map(pos => (
                                    <div key={pos.id} style={styles.positionCard}>
                                        <div style={styles.positionHeader}>
                                            <span style={styles.stockCode}>{pos.symbol}</span>
                                            <span style={styles.stockName}>{pos.stock_name}</span>
                                            {pos.is_simulated && (
                                                <span style={styles.simulatedBadge}>模擬</span>
                                            )}
                                            <span style={styles.sourceBadge}>{pos.analysis_source}</span>
                                        </div>
                                        <div style={styles.positionDetails}>
                                            <div>進場: ${pos.entry_price}</div>
                                            <div>現價: ${pos.current_price || '-'}</div>
                                            <div>目標: ${pos.target_price || '-'}</div>
                                            <div>停損: ${pos.stop_loss_price || '-'}</div>
                                            <div style={{
                                                color: (pos.unrealized_profit_percent || 0) >= 0 ? '#ef4444' : '#10b981',
                                                fontWeight: 'bold'
                                            }}>
                                                {(pos.unrealized_profit_percent || 0) >= 0 ? '+' : ''}
                                                {pos.unrealized_profit_percent?.toFixed(2) || 0}%
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Closed Positions */}
                    {closedPositions.length > 0 && (
                        <div style={styles.section}>
                            <h2 style={styles.sectionTitle}>📋 最近結束的交易</h2>
                            <div style={styles.positionList}>
                                {closedPositions.slice(0, 5).map(pos => (
                                    <div key={pos.id} style={styles.positionCard}>
                                        <div style={styles.positionHeader}>
                                            <span style={styles.stockCode}>{pos.symbol}</span>
                                            <span style={styles.stockName}>{pos.stock_name}</span>
                                            <span style={{
                                                ...styles.statusBadge,
                                                backgroundColor: getStatusColor(pos.status)
                                            }}>
                                                {getStatusText(pos.status)}
                                            </span>
                                        </div>
                                        <div style={styles.positionDetails}>
                                            <div>進場: ${pos.entry_price}</div>
                                            <div>出場: ${pos.exit_price || '-'}</div>
                                            <div style={{
                                                color: (pos.realized_profit_percent || 0) >= 0 ? '#ef4444' : '#10b981',
                                                fontWeight: 'bold'
                                            }}>
                                                {(pos.realized_profit_percent || 0) >= 0 ? '+' : ''}
                                                {pos.realized_profit_percent?.toFixed(2) || 0}%
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Trades Tab */}
            {activeTab === 'trades' && (
                <div style={styles.content}>
                    <div style={styles.section}>
                        <h2 style={styles.sectionTitle}>📋 交易歷史記錄</h2>
                        {trades.length === 0 ? (
                            <div style={styles.emptyState}>尚無交易記錄</div>
                        ) : (
                            <div style={styles.tradeList}>
                                {trades.map(trade => (
                                    <div key={trade.id} style={styles.tradeCard}>
                                        <div style={styles.tradeHeader}>
                                            <span style={styles.stockCode}>{trade.symbol}</span>
                                            <span style={styles.stockName}>{trade.stock_name}</span>
                                            <span style={{
                                                ...styles.typeBadge,
                                                backgroundColor: trade.trade_type === 'buy' ? '#10b981' : '#ef4444'
                                            }}>
                                                {trade.trade_type === 'buy' ? '買入' : '賣出'}
                                            </span>
                                            {trade.is_simulated && (
                                                <span style={styles.simulatedBadge}>模擬</span>
                                            )}
                                        </div>
                                        <div style={styles.tradeInfo}>
                                            <div style={styles.tradeRow}>
                                                <span>價格: ${trade.price}</span>
                                                <span>數量: {trade.quantity}</span>
                                                <span>總額: ${trade.total_amount.toLocaleString()}</span>
                                            </div>
                                            {trade.profit !== null && (
                                                <div style={{
                                                    color: trade.profit >= 0 ? '#ef4444' : '#10b981',
                                                    fontWeight: 'bold'
                                                }}>
                                                    損益: {trade.profit >= 0 ? '+' : ''}${trade.profit.toLocaleString()}
                                                    ({trade.profit_percent?.toFixed(2)}%)
                                                </div>
                                            )}
                                            <div style={styles.tradeSource}>
                                                訊號來源: {trade.analysis_source}
                                            </div>
                                            <div style={styles.tradeTime}>
                                                {new Date(trade.trade_date).toLocaleString('zh-TW')}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Analysis Tab */}
            {activeTab === 'analysis' && (
                <div style={styles.content}>
                    <div style={styles.section}>
                        <h2 style={styles.sectionTitle}>🔬 各分析來源準確性統計（90天）</h2>
                        {accuracy.length === 0 ? (
                            <div style={styles.emptyState}>尚無足夠數據進行分析</div>
                        ) : (
                            <div style={styles.accuracyGrid}>
                                {accuracy.map(acc => (
                                    <div key={acc.analysis_source} style={{
                                        ...styles.accuracyCard,
                                        borderColor: acc.win_rate >= 50 ? '#ef4444' : '#10b981'
                                    }}>
                                        <div style={styles.accuracyName}>{acc.analysis_source}</div>
                                        <div style={styles.accuracyStats}>
                                            <div style={styles.winRateRow}>
                                                <span>勝率</span>
                                                <span style={{
                                                    fontSize: '28px',
                                                    fontWeight: 'bold',
                                                    color: acc.win_rate >= 50 ? '#ef4444' : '#10b981'
                                                }}>
                                                    {acc.win_rate.toFixed(1)}%
                                                </span>
                                            </div>
                                            <div style={styles.statsRow}>
                                                <span style={{ color: '#ef4444' }}>{acc.winning_trades} 勝</span>
                                                <span style={{ color: '#10b981' }}>{acc.losing_trades} 負</span>
                                                <span>共 {acc.total_trades} 筆</span>
                                            </div>
                                            <div style={styles.profitRow}>
                                                <span>淨收益: </span>
                                                <span style={{
                                                    color: acc.net_profit >= 0 ? '#ef4444' : '#10b981',
                                                    fontWeight: 'bold'
                                                }}>
                                                    {acc.net_profit >= 0 ? '+' : ''}${acc.net_profit.toLocaleString()}
                                                </span>
                                            </div>
                                            {acc.avg_profit_percent !== null && (
                                                <div style={styles.avgRow}>
                                                    平均獲利: <span style={{ color: '#ef4444' }}>+{acc.avg_profit_percent.toFixed(2)}%</span>
                                                </div>
                                            )}
                                            {acc.avg_loss_percent !== null && (
                                                <div style={styles.avgRow}>
                                                    平均虧損: <span style={{ color: '#10b981' }}>{acc.avg_loss_percent.toFixed(2)}%</span>
                                                </div>
                                            )}
                                        </div>
                                        <div style={{
                                            ...styles.accuracyStatus,
                                            color: acc.win_rate >= 50 ? '#ef4444' : '#10b981'
                                        }}>
                                            {acc.win_rate >= 60 ? '⭐ 優秀' : acc.win_rate >= 50 ? '✅ 合格' : '⚠️ 需改進'}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Insights */}
                    <div style={styles.section}>
                        <h2 style={styles.sectionTitle}>💡 AI 洞察</h2>
                        <div style={styles.insightList}>
                            {accuracy.length > 0 && (
                                <>
                                    <div style={styles.insightItem}>
                                        🏆 最佳訊號來源: <strong>{accuracy[0]?.analysis_source}</strong> (勝率 {accuracy[0]?.win_rate.toFixed(1)}%)
                                    </div>
                                    {summary && summary.win_rate >= 50 && (
                                        <div style={styles.insightItem}>
                                            ✅ 整體勝率 {summary.win_rate.toFixed(1)}%，表現良好
                                        </div>
                                    )}
                                    {summary && summary.win_rate < 50 && (
                                        <div style={styles.insightItem}>
                                            ⚠️ 整體勝率 {summary.win_rate.toFixed(1)}%，建議調整策略
                                        </div>
                                    )}
                                    {accuracy.some(a => a.win_rate < 40) && (
                                        <div style={styles.insightItem}>
                                            ❌ 部分訊號來源勝率過低，建議減少使用或優化
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Footer */}
            <footer style={styles.footer}>
                <p>數據來源: Portfolio API | 自動刷新間隔: 30秒</p>
            </footer>
        </div>
    );
}

const styles: Record<string, React.CSSProperties> = {
    container: {
        minHeight: '100vh',
        backgroundColor: '#f8fafc',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    },
    loadingContainer: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        gap: '16px',
    },
    spinner: {
        width: '40px',
        height: '40px',
        border: '4px solid #e2e8f0',
        borderTop: '4px solid #3b82f6',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
    },
    header: {
        background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
        color: 'white',
        padding: '24px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    headerContent: {},
    title: {
        margin: 0,
        fontSize: '28px',
        fontWeight: 700,
    },
    subtitle: {
        margin: '8px 0 0',
        opacity: 0.8,
    },
    refreshBtn: {
        padding: '10px 20px',
        backgroundColor: 'rgba(255,255,255,0.2)',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        cursor: 'pointer',
        fontSize: '14px',
    },
    errorBanner: {
        backgroundColor: '#fef2f2',
        color: '#dc2626',
        padding: '12px 24px',
        textAlign: 'center',
    },
    tabs: {
        display: 'flex',
        gap: '4px',
        padding: '16px 32px',
        backgroundColor: 'white',
        borderBottom: '1px solid #e2e8f0',
    },
    tab: {
        padding: '12px 24px',
        backgroundColor: 'transparent',
        border: 'none',
        borderRadius: '8px',
        cursor: 'pointer',
        fontSize: '15px',
        color: '#64748b',
    },
    tabActive: {
        padding: '12px 24px',
        backgroundColor: '#3b82f6',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        cursor: 'pointer',
        fontSize: '15px',
        fontWeight: 600,
    },
    content: {
        padding: '24px 32px',
        maxWidth: '1200px',
        margin: '0 auto',
    },
    statsGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        marginBottom: '24px',
    },
    statCard: {
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    },
    statLabel: {
        fontSize: '14px',
        color: '#64748b',
        marginBottom: '8px',
    },
    statValue: {
        fontSize: '28px',
        fontWeight: 700,
        color: '#1e293b',
    },
    section: {
        backgroundColor: 'white',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    },
    sectionTitle: {
        margin: '0 0 16px',
        fontSize: '18px',
        fontWeight: 600,
        color: '#1e293b',
    },
    profitGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '16px',
    },
    profitCard: {
        backgroundColor: '#f8fafc',
        borderRadius: '12px',
        padding: '20px',
        textAlign: 'center',
    },
    profitLabel: {
        fontSize: '14px',
        color: '#64748b',
        marginBottom: '8px',
    },
    profitValue: {
        fontSize: '32px',
        fontWeight: 700,
    },
    profitSubtext: {
        fontSize: '13px',
        color: '#94a3b8',
        marginTop: '8px',
    },
    sourceGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '12px',
    },
    sourceCard: {
        backgroundColor: '#f8fafc',
        borderRadius: '8px',
        padding: '16px',
    },
    sourceName: {
        fontSize: '14px',
        fontWeight: 600,
        color: '#1e293b',
        marginBottom: '8px',
    },
    sourceStats: {
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '14px',
        color: '#475569',
    },
    positionList: {
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
    },
    positionCard: {
        backgroundColor: '#f8fafc',
        borderRadius: '12px',
        padding: '16px',
        border: '1px solid #e2e8f0',
    },
    positionHeader: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '12px',
        flexWrap: 'wrap',
    },
    stockCode: {
        fontSize: '18px',
        fontWeight: 700,
        color: '#1e293b',
    },
    stockName: {
        fontSize: '14px',
        color: '#64748b',
    },
    simulatedBadge: {
        padding: '4px 10px',
        borderRadius: '12px',
        fontSize: '11px',
        fontWeight: 600,
        color: '#7c3aed',
        backgroundColor: '#ede9fe',
    },
    sourceBadge: {
        padding: '4px 10px',
        borderRadius: '12px',
        fontSize: '11px',
        fontWeight: 600,
        color: '#0369a1',
        backgroundColor: '#e0f2fe',
    },
    statusBadge: {
        padding: '4px 10px',
        borderRadius: '12px',
        fontSize: '12px',
        fontWeight: 600,
        color: 'white',
        marginLeft: 'auto',
    },
    positionDetails: {
        display: 'flex',
        gap: '24px',
        fontSize: '14px',
        color: '#475569',
        flexWrap: 'wrap',
    },
    tradeList: {
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
    },
    tradeCard: {
        backgroundColor: '#f8fafc',
        borderRadius: '12px',
        padding: '16px',
        border: '1px solid #e2e8f0',
    },
    tradeHeader: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '12px',
        flexWrap: 'wrap',
    },
    typeBadge: {
        padding: '4px 10px',
        borderRadius: '12px',
        fontSize: '11px',
        fontWeight: 600,
        color: 'white',
    },
    tradeInfo: {
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
    },
    tradeRow: {
        display: 'flex',
        gap: '16px',
        alignItems: 'center',
        fontSize: '14px',
        color: '#475569',
        flexWrap: 'wrap',
    },
    tradeSource: {
        fontSize: '13px',
        color: '#94a3b8',
    },
    tradeTime: {
        fontSize: '12px',
        color: '#94a3b8',
    },
    emptyState: {
        textAlign: 'center',
        padding: '40px',
        color: '#94a3b8',
    },
    accuracyGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '16px',
    },
    accuracyCard: {
        backgroundColor: '#f8fafc',
        borderRadius: '12px',
        padding: '20px',
        borderLeft: '4px solid',
    },
    accuracyName: {
        fontSize: '18px',
        fontWeight: 600,
        color: '#1e293b',
        marginBottom: '16px',
    },
    accuracyStats: {
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
    },
    winRateRow: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '14px',
        color: '#64748b',
    },
    statsRow: {
        display: 'flex',
        gap: '16px',
        fontSize: '14px',
    },
    profitRow: {
        fontSize: '14px',
        color: '#475569',
    },
    avgRow: {
        fontSize: '13px',
        color: '#64748b',
    },
    accuracyStatus: {
        marginTop: '16px',
        fontSize: '14px',
        fontWeight: 600,
        textAlign: 'center',
    },
    insightList: {
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
    },
    insightItem: {
        padding: '12px 16px',
        backgroundColor: '#f8fafc',
        borderRadius: '8px',
        fontSize: '15px',
    },
    footer: {
        textAlign: 'center',
        padding: '24px',
        color: '#94a3b8',
        fontSize: '13px',
    },
};
