'use client';

import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/mops';

// ==================== 類型定義 ====================
interface KGIReport {
    code: string | null;
    stock_name: string;
    rating: string | null;
    target_price: number | null;
    eps_2026: number | null;
    pe_multiple: number | null;
    date: string;
    title: string;
    link: string;
    source: string;
    highlight?: boolean;
    note?: string;
    catalyst?: string;
}

interface KGIResearchData {
    success: boolean;
    summary: string;
    reports: KGIReport[];
    static_count: number;
    live_count: number;
    fetched_at: string;
}

interface SectorOutlook {
    name: string;
    icon: string;
    rating: string;
    rating_color: string;
    growth_2026: string;
    key_stocks: string[];
    catalyst: string;
    summary: string;
}

interface OutlookData {
    success: boolean;
    outlook: {
        report_date: string;
        macro: {
            title: string;
            taiex_high: number;
            taiex_low: number;
            pe_high: number;
            pe_low: number;
            earnings_growth_2026: number;
            summary: string;
            risks: string[];
        };
        sectors: SectorOutlook[];
        investment_strategy: {
            title: string;
            core_themes: string[];
            portfolio_approach: string;
            lead_breakdown: Record<string, string>;
        };
    };
}

// ==================== 輔助函數 ====================
const getRatingStyle = (rating: string | null) => {
    if (!rating) return { badge: 'bg-gray-800 text-gray-300 border border-gray-600', dot: 'bg-gray-400' };
    if (rating.includes('強力買進') || rating.includes('Strong Buy')) return { badge: 'bg-red-900/60 text-red-300 border border-red-700', dot: 'bg-red-400' };
    if (rating.includes('買進') || rating.includes('增加持股') || rating.includes('Outperform') || rating.includes('Buy')) return { badge: 'bg-rose-900/50 text-rose-300 border border-rose-700', dot: 'bg-rose-400' };
    if (rating.includes('中立') || rating.includes('Neutral') || rating.includes('Hold')) return { badge: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700', dot: 'bg-yellow-400' };
    return { badge: 'bg-green-900/50 text-green-300 border border-green-700', dot: 'bg-green-400' };
};

const getRatingIcon = (rating: string | null) => {
    if (!rating) return '➖';
    if (rating.includes('強力買進') || rating.includes('Strong Buy')) return '🔥';
    if (rating.includes('買進') || rating.includes('增加持股') || rating.includes('Outperform')) return '📈';
    if (rating.includes('中立') || rating.includes('Neutral') || rating.includes('Hold')) return '⚖️';
    return '📉';
};

const formatPrice = (price: number | null, suffix = '') => {
    if (price === null || price === undefined) return '—';
    if (price >= 1000) return `$${price.toLocaleString()}${suffix}`;
    return `$${price.toFixed(1)}${suffix}`;
};

// ==================== 主頁面 ====================
export default function KGIResearchPage() {
    const [data, setData] = useState<KGIResearchData | null>(null);
    const [outlookData, setOutlookData] = useState<OutlookData | null>(null);
    const [loading, setLoading] = useState(false);
    const [outlookLoading, setOutlookLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'table' | 'cards' | 'outlook'>('table');
    const [filterRating, setFilterRating] = useState<string>('all');
    const [searchCode, setSearchCode] = useState('');
    const [sortBy, setSortBy] = useState<'date' | 'target_price' | 'eps_2026' | 'pe_multiple'>('date');
    const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc');
    const [selectedReport, setSelectedReport] = useState<KGIReport | null>(null);

    const fetchData = useCallback(async (stockCode?: string) => {
        setLoading(true);
        setError(null);
        try {
            const url = stockCode
                ? `${API_BASE}/kgi-research?stock_code=${stockCode}`
                : `${API_BASE}/kgi-research`;
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            setData(json);
        } catch (e) {
            setError(e instanceof Error ? e.message : '資料取得失敗');
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchOutlook = useCallback(async () => {
        setOutlookLoading(true);
        try {
            const res = await fetch(`${API_BASE}/kgi-outlook`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            setOutlookData(json);
        } catch (e) {
            console.error('Outlook fetch failed:', e);
        } finally {
            setOutlookLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
        fetchOutlook();
    }, []);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        fetchData(searchCode.trim() || undefined);
    };

    // 過濾 + 排序
    const filteredReports = (data?.reports || [])
        .filter(r => {
            if (filterRating === 'all') return true;
            if (filterRating === 'buy') return r.rating && (r.rating.includes('買進') || r.rating.includes('增加持股') || r.rating.includes('Buy') || r.rating.includes('Outperform'));
            if (filterRating === 'neutral') return r.rating && (r.rating.includes('中立') || r.rating.includes('Neutral') || r.rating.includes('Hold'));
            if (filterRating === 'highlight') return r.highlight;
            return true;
        })
        .sort((a, b) => {
            const va = (a[sortBy] ?? 0) as number | string;
            const vb = (b[sortBy] ?? 0) as number | string;
            if (typeof va === 'string' && typeof vb === 'string') {
                return sortDir === 'desc' ? vb.localeCompare(va) : va.localeCompare(vb);
            }
            const na = Number(va) || 0;
            const nb = Number(vb) || 0;
            return sortDir === 'desc' ? nb - na : na - nb;
        });

    const toggleSort = (col: typeof sortBy) => {
        if (sortBy === col) {
            setSortDir(d => d === 'desc' ? 'asc' : 'desc');
        } else {
            setSortBy(col);
            setSortDir('desc');
        }
    };

    const SortIcon = ({ col }: { col: typeof sortBy }) => {
        if (sortBy !== col) return <span className="text-gray-600 ml-1">⇅</span>;
        return <span className="text-blue-400 ml-1">{sortDir === 'desc' ? '↓' : '↑'}</span>;
    };

    return (
        <div className="min-h-screen bg-gray-950 text-white">
            {/* ────────── 頂部橫幅 ────────── */}
            <div className="bg-gradient-to-r from-gray-900 via-blue-950 to-gray-900 border-b border-blue-900/30">
                <div className="max-w-7xl mx-auto px-6 py-6">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                        <div>
                            <div className="flex items-center gap-3 mb-1">
                                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center text-xl shadow-lg">
                                    🏦
                                </div>
                                <div>
                                    <h1 className="text-2xl font-bold text-white tracking-tight">
                                        凱基投顧研究報告中心
                                    </h1>
                                    <p className="text-sm text-blue-300/80">KGI Securities Research · 以當月最新訊息為準</p>
                                </div>
                            </div>
                            {data && (
                                <p className="text-xs text-gray-400 mt-2 ml-13">
                                    📡 {data.summary}
                                </p>
                            )}
                        </div>

                        {/* 搜尋 */}
                        <form onSubmit={handleSearch} className="flex items-center gap-2">
                            <input
                                type="text"
                                value={searchCode}
                                onChange={e => setSearchCode(e.target.value)}
                                placeholder="股票代碼（如 2337）"
                                className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none w-44"
                                id="kgi-search-input"
                            />
                            <button
                                type="submit"
                                disabled={loading}
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50"
                                id="kgi-search-btn"
                            >
                                {loading ? '⟳ 搜尋中' : '🔍 搜尋'}
                            </button>
                            {searchCode && (
                                <button
                                    type="button"
                                    onClick={() => { setSearchCode(''); fetchData(); }}
                                    className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
                                >
                                    全部
                                </button>
                            )}
                            <button
                                type="button"
                                onClick={() => fetchData(searchCode || undefined)}
                                disabled={loading}
                                className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm disabled:opacity-50"
                                title="重新整理"
                            >
                                🔄
                            </button>
                        </form>
                    </div>

                    {/* Tab 切換 */}
                    <div className="flex gap-1 mt-5">
                        {[
                            { key: 'table', label: '📊 個股評等表格', id: 'tab-table' },
                            { key: 'cards', label: '🃏 卡片視圖', id: 'tab-cards' },
                            { key: 'outlook', label: '🌐 產業展望', id: 'tab-outlook' },
                        ].map(tab => (
                            <button
                                key={tab.key}
                                id={tab.id}
                                onClick={() => setActiveTab(tab.key as typeof activeTab)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.key
                                    ? 'bg-blue-600 text-white shadow-lg'
                                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                                    }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* ────────── 主內容 ────────── */}
            <div className="max-w-7xl mx-auto px-6 py-6">
                {error && (
                    <div className="mb-4 p-4 bg-red-900/30 border border-red-800 rounded-lg text-red-300 text-sm">
                        ⚠️ {error} — 後端可能尚未啟動，請確認 <code className="bg-red-900/50 px-1 rounded">http://localhost:8000</code> 正常運行
                    </div>
                )}

                {/* ── 統計卡片 ── */}
                {data && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                        {[
                            { label: '總報告數', value: data.reports.length, icon: '📋', color: 'from-blue-900/40 to-blue-800/20 border-blue-800/40' },
                            { label: '買進/增持', value: data.reports.filter(r => r.rating && (r.rating.includes('買進') || r.rating.includes('增加持股'))).length, icon: '🔥', color: 'from-red-900/40 to-red-800/20 border-red-800/40' },
                            { label: '中立', value: data.reports.filter(r => r.rating && (r.rating.includes('中立') || r.rating.includes('Neutral'))).length, icon: '⚖️', color: 'from-yellow-900/40 to-yellow-800/20 border-yellow-800/40' },
                            { label: '含目標價', value: data.reports.filter(r => r.target_price).length, icon: '🎯', color: 'from-purple-900/40 to-purple-800/20 border-purple-800/40' },
                        ].map(stat => (
                            <div key={stat.label} className={`bg-gradient-to-br ${stat.color} border rounded-xl p-4`}>
                                <div className="text-2xl mb-1">{stat.icon}</div>
                                <div className="text-2xl font-bold text-white">{stat.value}</div>
                                <div className="text-xs text-gray-400 mt-1">{stat.label}</div>
                            </div>
                        ))}
                    </div>
                )}

                {/* ══════════ TAB: 表格 ══════════ */}
                {activeTab === 'table' && (
                    <div>
                        {/* 過濾器 */}
                        <div className="flex items-center gap-2 mb-4 flex-wrap">
                            <span className="text-sm text-gray-500">篩選：</span>
                            {[
                                { key: 'all', label: '全部' },
                                { key: 'highlight', label: '⭐ 重點關注' },
                                { key: 'buy', label: '📈 買進/增持' },
                                { key: 'neutral', label: '⚖️ 中立' },
                            ].map(f => (
                                <button
                                    key={f.key}
                                    id={`filter-${f.key}`}
                                    onClick={() => setFilterRating(f.key)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filterRating === f.key
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                                        }`}
                                >
                                    {f.label}
                                </button>
                            ))}
                            <span className="ml-auto text-xs text-gray-500">{filteredReports.length} 筆</span>
                        </div>

                        {loading ? (
                            <div className="flex items-center justify-center py-20">
                                <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mr-3" />
                                <span className="text-gray-400">正在從凱基官方管道彙整最新數據...</span>
                            </div>
                        ) : (
                            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden shadow-xl">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="bg-gray-800/60 text-gray-400 text-xs uppercase tracking-wider">
                                                <th className="px-4 py-3 text-left">日期</th>
                                                <th className="px-4 py-3 text-left">代號</th>
                                                <th className="px-4 py-3 text-left">名稱</th>
                                                <th className="px-4 py-3 text-left">投資評等</th>
                                                <th
                                                    className="px-4 py-3 text-right cursor-pointer hover:text-white select-none"
                                                    onClick={() => toggleSort('target_price')}
                                                >
                                                    目標價 <SortIcon col="target_price" />
                                                </th>
                                                <th
                                                    className="px-4 py-3 text-right cursor-pointer hover:text-white select-none"
                                                    onClick={() => toggleSort('eps_2026')}
                                                >
                                                    2026E EPS <SortIcon col="eps_2026" />
                                                </th>
                                                <th
                                                    className="px-4 py-3 text-right cursor-pointer hover:text-white select-none"
                                                    onClick={() => toggleSort('pe_multiple')}
                                                >
                                                    P/E （x） <SortIcon col="pe_multiple" />
                                                </th>
                                                <th className="px-4 py-3 text-left">催化劑 / 核心觀點</th>
                                                <th className="px-4 py-3 text-center">報告</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-800">
                                            {filteredReports.length === 0 && (
                                                <tr>
                                                    <td colSpan={9} className="px-4 py-12 text-center text-gray-500">
                                                        {loading ? '載入中...' : '暫無符合條件的資料'}
                                                    </td>
                                                </tr>
                                            )}
                                            {filteredReports.map((r, idx) => {
                                                const rStyle = getRatingStyle(r.rating);
                                                return (
                                                    <tr
                                                        key={`${r.code}-${r.date}-${idx}`}
                                                        className={`transition-all cursor-pointer ${r.highlight
                                                            ? 'bg-blue-950/30 hover:bg-blue-950/50'
                                                            : 'hover:bg-gray-800/50'
                                                            }`}
                                                        onClick={() => setSelectedReport(r === selectedReport ? null : r)}
                                                    >
                                                        <td className="px-4 py-3.5 text-gray-400 text-xs whitespace-nowrap">
                                                            {r.date || '—'}
                                                        </td>
                                                        <td className="px-4 py-3.5">
                                                            <div className="flex items-center gap-2">
                                                                {r.highlight && <span className="text-yellow-400 text-xs">⭐</span>}
                                                                <span className="font-mono font-bold text-blue-300">
                                                                    {r.code || '—'}
                                                                </span>
                                                            </div>
                                                        </td>
                                                        <td className="px-4 py-3.5 font-medium text-white whitespace-nowrap">
                                                            {r.stock_name}
                                                        </td>
                                                        <td className="px-4 py-3.5">
                                                            {r.rating ? (
                                                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${rStyle.badge}`}>
                                                                    <span className={`w-1.5 h-1.5 rounded-full ${rStyle.dot}`} />
                                                                    {getRatingIcon(r.rating)} {r.rating}
                                                                </span>
                                                            ) : (
                                                                <span className="text-gray-600 text-xs">未揭露</span>
                                                            )}
                                                        </td>
                                                        <td className="px-4 py-3.5 text-right">
                                                            {r.target_price ? (
                                                                <span className="font-bold text-red-400">
                                                                    {formatPrice(r.target_price)}
                                                                </span>
                                                            ) : <span className="text-gray-600">—</span>}
                                                        </td>
                                                        <td className="px-4 py-3.5 text-right">
                                                            {r.eps_2026 ? (
                                                                <span className="text-emerald-400 font-semibold">
                                                                    {r.eps_2026 >= 100
                                                                        ? `$${r.eps_2026.toFixed(0)}`
                                                                        : `$${r.eps_2026.toFixed(2)}`}
                                                                </span>
                                                            ) : <span className="text-gray-600">—</span>}
                                                        </td>
                                                        <td className="px-4 py-3.5 text-right">
                                                            {r.pe_multiple ? (
                                                                <span className="text-purple-300">
                                                                    {r.pe_multiple.toFixed(1)}x
                                                                </span>
                                                            ) : <span className="text-gray-600">—</span>}
                                                        </td>
                                                        <td className="px-4 py-3.5 text-xs text-gray-400 max-w-xs">
                                                            {r.catalyst ? (
                                                                <div>
                                                                    <span className="text-blue-400 font-medium">{r.catalyst}</span>
                                                                    {r.note && (
                                                                        <div className="text-gray-500 mt-0.5 line-clamp-1">{r.note}</div>
                                                                    )}
                                                                </div>
                                                            ) : (
                                                                <span className="line-clamp-2">{r.title}</span>
                                                            )}
                                                        </td>
                                                        <td className="px-4 py-3.5 text-center">
                                                            {r.link ? (
                                                                <a
                                                                    href={r.link}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    onClick={e => e.stopPropagation()}
                                                                    className="text-blue-400 hover:text-blue-300 text-xs underline"
                                                                >
                                                                    原文
                                                                </a>
                                                            ) : <span className="text-gray-700">—</span>}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* 展開詳情抽屜 */}
                        {selectedReport && (
                            <div className="mt-4 bg-gradient-to-br from-gray-900 to-blue-950/30 border border-blue-900/40 rounded-xl p-6 shadow-xl animate-fade-in">
                                <div className="flex items-start justify-between mb-4">
                                    <div>
                                        <div className="flex items-center gap-3">
                                            {selectedReport.highlight && <span>⭐</span>}
                                            <h3 className="text-xl font-bold text-white">
                                                {selectedReport.stock_name}
                                                <span className="text-gray-400 ml-2 font-mono text-base">({selectedReport.code})</span>
                                            </h3>
                                            {selectedReport.rating && (
                                                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getRatingStyle(selectedReport.rating).badge}`}>
                                                    {getRatingIcon(selectedReport.rating)} {selectedReport.rating}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-sm text-gray-500 mt-1">{selectedReport.date} · {selectedReport.source}</p>
                                    </div>
                                    <button
                                        onClick={() => setSelectedReport(null)}
                                        className="text-gray-500 hover:text-white transition-colors text-xl"
                                    >
                                        ✕
                                    </button>
                                </div>

                                <div className="grid grid-cols-3 gap-4 mb-5">
                                    <div className="bg-gray-800/60 rounded-xl p-4 text-center">
                                        <div className="text-xs text-gray-400 mb-1">🎯 凱基目標價</div>
                                        <div className="text-2xl font-bold text-red-400">{formatPrice(selectedReport.target_price)}</div>
                                    </div>
                                    <div className="bg-gray-800/60 rounded-xl p-4 text-center">
                                        <div className="text-xs text-gray-400 mb-1">💰 2026E EPS</div>
                                        <div className="text-2xl font-bold text-emerald-400">
                                            {selectedReport.eps_2026
                                                ? `$${selectedReport.eps_2026 >= 100 ? selectedReport.eps_2026.toFixed(0) : selectedReport.eps_2026.toFixed(2)}`
                                                : '—'}
                                        </div>
                                    </div>
                                    <div className="bg-gray-800/60 rounded-xl p-4 text-center">
                                        <div className="text-xs text-gray-400 mb-1">📐 目標 P/E</div>
                                        <div className="text-2xl font-bold text-purple-400">
                                            {selectedReport.pe_multiple ? `${selectedReport.pe_multiple.toFixed(1)}x` : '—'}
                                        </div>
                                    </div>
                                </div>

                                {selectedReport.catalyst && (
                                    <div className="mb-3">
                                        <span className="text-xs text-blue-400 font-semibold uppercase tracking-wider">催化劑</span>
                                        <p className="text-white mt-1 font-medium">{selectedReport.catalyst}</p>
                                    </div>
                                )}
                                {selectedReport.note && (
                                    <div>
                                        <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider">凱基核心觀點</span>
                                        <p className="text-gray-300 mt-1 text-sm leading-relaxed">{selectedReport.note}</p>
                                    </div>
                                )}
                                {selectedReport.title && (
                                    <div className="mt-3 pt-3 border-t border-gray-800">
                                        <span className="text-xs text-gray-500">報告摘要：</span>
                                        <p className="text-gray-400 text-xs mt-1">{selectedReport.title}</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* ══════════ TAB: 卡片視圖 ══════════ */}
                {activeTab === 'cards' && (
                    <div>
                        <div className="flex gap-2 mb-4 flex-wrap">
                            {[
                                { key: 'all', label: '全部' },
                                { key: 'highlight', label: '⭐ 重點' },
                                { key: 'buy', label: '📈 買進' },
                                { key: 'neutral', label: '⚖️ 中立' },
                            ].map(f => (
                                <button
                                    key={f.key}
                                    onClick={() => setFilterRating(f.key)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filterRating === f.key ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                                >
                                    {f.label}
                                </button>
                            ))}
                        </div>

                        {loading ? (
                            <div className="flex items-center justify-center py-20">
                                <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mr-3" />
                                <span className="text-gray-400">載入中...</span>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {filteredReports.map((r, idx) => {
                                    const rStyle = getRatingStyle(r.rating);
                                    return (
                                        <div
                                            key={`card-${r.code}-${idx}`}
                                            className={`rounded-xl border p-5 transition-all hover:shadow-2xl hover:-translate-y-0.5 cursor-pointer ${r.highlight
                                                ? 'bg-gradient-to-br from-blue-950/60 to-indigo-950/40 border-blue-800/50'
                                                : 'bg-gray-900 border-gray-800'
                                                }`}
                                        >
                                            {/* 卡片頂部 */}
                                            <div className="flex items-start justify-between mb-4">
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        {r.highlight && <span className="text-yellow-400">⭐</span>}
                                                        <span className="font-mono text-sm text-blue-400 font-bold">{r.code}</span>
                                                    </div>
                                                    <h3 className="text-lg font-bold text-white mt-0.5">{r.stock_name}</h3>
                                                    <p className="text-xs text-gray-500 mt-0.5">{r.date}</p>
                                                </div>
                                                {r.rating && (
                                                    <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${rStyle.badge}`}>
                                                        {getRatingIcon(r.rating)} {r.rating}
                                                    </span>
                                                )}
                                            </div>

                                            {/* 數據列 */}
                                            <div className="grid grid-cols-3 gap-2 mb-4">
                                                <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                                                    <div className="text-xs text-gray-500 mb-0.5">目標價</div>
                                                    <div className="text-sm font-bold text-red-400">{formatPrice(r.target_price)}</div>
                                                </div>
                                                <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                                                    <div className="text-xs text-gray-500 mb-0.5">2026E EPS</div>
                                                    <div className="text-sm font-bold text-emerald-400">
                                                        {r.eps_2026 ? `$${r.eps_2026 >= 100 ? r.eps_2026.toFixed(0) : r.eps_2026.toFixed(2)}` : '—'}
                                                    </div>
                                                </div>
                                                <div className="bg-gray-800/50 rounded-lg p-2.5 text-center">
                                                    <div className="text-xs text-gray-500 mb-0.5">目標P/E</div>
                                                    <div className="text-sm font-bold text-purple-400">
                                                        {r.pe_multiple ? `${r.pe_multiple.toFixed(1)}x` : '—'}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* 催化劑 */}
                                            {r.catalyst && (
                                                <div className="text-xs">
                                                    <span className="text-blue-400 font-semibold">⚡ {r.catalyst}</span>
                                                </div>
                                            )}
                                            {r.note && (
                                                <p className="text-xs text-gray-500 mt-2 line-clamp-2">{r.note}</p>
                                            )}

                                            {/* 底部 */}
                                            <div className="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between">
                                                <span className="text-xs text-gray-600">{r.source}</span>
                                                {r.link && (
                                                    <a href={r.link} target="_blank" rel="noopener noreferrer"
                                                        className="text-xs text-blue-500 hover:text-blue-400 underline"
                                                        onClick={e => e.stopPropagation()}>
                                                        查看原文 →
                                                    </a>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}

                {/* ══════════ TAB: 產業展望 ══════════ */}
                {activeTab === 'outlook' && (
                    <div>
                        {outlookLoading ? (
                            <div className="flex items-center justify-center py-20">
                                <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mr-3" />
                                <span className="text-gray-400">載入產業展望...</span>
                            </div>
                        ) : outlookData ? (
                            <div className="space-y-6">
                                {/* 大盤展望 */}
                                <div className="bg-gradient-to-br from-gray-900 to-blue-950/40 border border-blue-900/30 rounded-2xl p-6">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-xl">🌏</div>
                                        <div>
                                            <h2 className="text-xl font-bold text-white">{outlookData.outlook.macro.title}</h2>
                                            <p className="text-xs text-gray-400">最新更新：{outlookData.outlook.report_date}</p>
                                        </div>
                                    </div>

                                    <p className="text-gray-300 text-sm leading-relaxed mb-5">{outlookData.outlook.macro.summary}</p>

                                    {/* 大盤指標 */}
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                                        {[
                                            { label: '台股高點目標', value: `${outlookData.outlook.macro.taiex_high.toLocaleString()} 點`, sub: `約 ${outlookData.outlook.macro.pe_high}x P/E`, color: 'text-red-400' },
                                            { label: '台股低點支撐', value: `${outlookData.outlook.macro.taiex_low.toLocaleString()} 點`, sub: `約 ${outlookData.outlook.macro.pe_low}x P/E`, color: 'text-yellow-400' },
                                            { label: '2026 盈餘年增', value: `+${outlookData.outlook.macro.earnings_growth_2026}%`, sub: '大幅上調（原20%）', color: 'text-emerald-400' },
                                            { label: 'AI 類股盈利佔比', value: '>60%', sub: '台股整體獲利來源', color: 'text-blue-400' },
                                        ].map(item => (
                                            <div key={item.label} className="bg-gray-800/60 rounded-xl p-4 text-center">
                                                <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
                                                <div className="text-xs text-gray-300 mt-1">{item.label}</div>
                                                <div className="text-xs text-gray-500 mt-0.5">{item.sub}</div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* 風險因素 */}
                                    <div>
                                        <h4 className="text-sm font-semibold text-gray-400 mb-2">⚠️ 三大主要風險因素</h4>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                            {outlookData.outlook.macro.risks.map((r, i) => (
                                                <div key={i} className="flex items-start gap-2 bg-gray-800/40 rounded-lg p-3 text-sm text-gray-400">
                                                    <span className="text-yellow-500 flex-shrink-0">•</span>
                                                    <span>{r}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* 產業別展望 */}
                                <div>
                                    <h2 className="text-lg font-bold text-white mb-4">📊 凱基 2026 各產業展望</h2>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {outlookData.outlook.sectors.map((sector, i) => (
                                            <div
                                                key={i}
                                                className={`rounded-xl border p-5 ${sector.rating_color === 'red'
                                                    ? 'bg-gradient-to-br from-gray-900 to-red-950/20 border-red-900/30'
                                                    : 'bg-gradient-to-br from-gray-900 to-yellow-950/20 border-yellow-900/30'
                                                    }`}
                                            >
                                                <div className="flex items-center justify-between mb-3">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-2xl">{sector.icon}</span>
                                                        <div>
                                                            <h3 className="font-bold text-white">{sector.name}</h3>
                                                            <p className="text-xs text-gray-400">2026 預估成長：{sector.growth_2026}</p>
                                                        </div>
                                                    </div>
                                                    <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${sector.rating_color === 'red'
                                                        ? 'bg-red-900/60 text-red-300 border border-red-800'
                                                        : 'bg-yellow-900/60 text-yellow-300 border border-yellow-800'
                                                        }`}>
                                                        {sector.rating}
                                                    </span>
                                                </div>

                                                <p className="text-xs text-gray-400 mb-3 leading-relaxed">{sector.summary}</p>

                                                <div className="mb-2">
                                                    <div className="text-xs text-gray-500 mb-1">🔑 主要催化劑</div>
                                                    <p className="text-xs text-blue-400">{sector.catalyst}</p>
                                                </div>

                                                <div className="flex flex-wrap gap-1.5 mt-3">
                                                    {sector.key_stocks.map((s, j) => (
                                                        <span key={j} className="px-2 py-0.5 bg-gray-800 text-gray-300 rounded text-xs font-mono">
                                                            {s}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* 投資策略 LEAD */}
                                <div className="bg-gradient-to-br from-gray-900 to-indigo-950/30 border border-indigo-900/30 rounded-2xl p-6">
                                    <h2 className="text-lg font-bold text-white mb-4">
                                        🧭 {outlookData.outlook.investment_strategy.title}
                                    </h2>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        {/* 核心主題 */}
                                        <div>
                                            <h4 className="text-sm font-semibold text-gray-400 mb-3">2026 五大核心投資主題</h4>
                                            <div className="space-y-2">
                                                {outlookData.outlook.investment_strategy.core_themes.map((theme, i) => (
                                                    <div key={i} className="flex items-center gap-2 bg-gray-800/40 rounded-lg p-2.5 text-sm text-gray-300">
                                                        {theme}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* LEAD 策略 */}
                                        <div>
                                            <h4 className="text-sm font-semibold text-gray-400 mb-3">
                                                資產配置策略：{outlookData.outlook.investment_strategy.portfolio_approach}
                                            </h4>
                                            <div className="space-y-2">
                                                {Object.entries(outlookData.outlook.investment_strategy.lead_breakdown).map(([k, v]) => (
                                                    <div key={k} className="bg-gray-800/40 rounded-lg p-2.5">
                                                        <span className="text-indigo-400 font-bold text-lg mr-2">{k}</span>
                                                        <span className="text-xs text-gray-300">{v}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center py-20 text-gray-500">
                                無法載入產業展望數據，請確認後端服務正常
                            </div>
                        )}
                    </div>
                )}

                {/* 底部說明 */}
                <div className="mt-8 p-4 bg-gray-900/50 border border-gray-800 rounded-xl text-xs text-gray-500">
                    <div className="flex items-start gap-2">
                        <span>⚡</span>
                        <div>
                            <span className="text-gray-400 font-semibold">數據來源說明：</span>
                            本頁數據依據三大核心搜尋關鍵詞彙整：
                            ①「凱基投顧 台灣投資領航日報」（每日盤前核心報告）、
                            ②「KGI Research Company Update」（個股財報/事件更新）、
                            ③「凱基投顧 2026 展望」（整體產業獲利預估）。
                            靜態數據每月月底人工複核更新；即時數據透過 Google News RSS 抓取最新資訊。
                            <span className="text-yellow-500 ml-1">⚠️ 本資料僅供參考，不構成投資建議，投資前請審慎評估。</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
