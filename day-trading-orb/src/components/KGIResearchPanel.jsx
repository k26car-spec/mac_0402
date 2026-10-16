import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env?.VITE_API_BASE || 'http://localhost:8000';

const RATING_COLORS = {
    '強力買進': 'bg-red-600 text-white',
    '強烈買進': 'bg-red-600 text-white',
    '買進': 'bg-red-500 text-white',
    'Buy': 'bg-red-500 text-white',
    '優於市場': 'bg-orange-400 text-white',
    'Outperform': 'bg-orange-400 text-white',
    '中立': 'bg-gray-400 text-white',
    'Neutral': 'bg-gray-400 text-white',
    '劣於市場': 'bg-green-600 text-white',
    'Underperform': 'bg-green-600 text-white',
    'Strong Buy': 'bg-red-600 text-white',
};

const getRatingColor = (rating) => {
    if (!rating) return 'bg-gray-200 text-gray-500';
    for (const key of Object.keys(RATING_COLORS)) {
        if (rating.includes(key)) return RATING_COLORS[key];
    }
    return 'bg-gray-300 text-gray-600';
};

const KGIResearchPanel = ({ symbol }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [filterCode, setFilterCode] = useState('');
    const [viewMode, setViewMode] = useState('table');  // 'table' | 'cards'

    const fetchData = useCallback(async (stockCode = null) => {
        setLoading(true);
        setError(null);
        try {
            const url = stockCode
                ? `${API_BASE}/api/mops/kgi-research?stock_code=${stockCode}`
                : `${API_BASE}/api/mops/kgi-research`;
            const res = await fetch(url);
            const json = await res.json();
            if (json.success) {
                setData(json);
            } else {
                setError('無法載入凱基研究報告');
            }
        } catch (e) {
            setError(`連線失敗: ${e.message}`);
        } finally {
            setLoading(false);
        }
    }, []);

    // Auto-fetch on mount or symbol change
    useEffect(() => {
        fetchData(symbol || null);
    }, [symbol, fetchData]);

    const handleSearch = (e) => {
        e.preventDefault();
        fetchData(filterCode.trim() || null);
    };

    const reports = data?.reports || [];
    const hasTarget = reports.filter(r => r.target_price).length;
    const hasBuy = reports.filter(r => r.rating && r.rating.includes('買進')).length;

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                        <span className="text-base font-bold text-gray-800">📊 凱基投顧評價彙整</span>
                        <span className="text-[10px] bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold px-2 py-0.5 rounded-full">KGI Research</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <button
                            onClick={() => setViewMode('table')}
                            className={`text-[10px] px-2 py-0.5 rounded font-bold border transition-colors ${viewMode === 'table' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-500 border-gray-200'}`}
                        >
                            表格
                        </button>
                        <button
                            onClick={() => setViewMode('cards')}
                            className={`text-[10px] px-2 py-0.5 rounded font-bold border transition-colors ${viewMode === 'cards' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-500 border-gray-200'}`}
                        >
                            卡片
                        </button>
                    </div>
                </div>

                {/* Search bar */}
                <form onSubmit={handleSearch} className="flex gap-2">
                    <input
                        type="text"
                        value={filterCode}
                        onChange={e => setFilterCode(e.target.value)}
                        placeholder="輸入股票代碼過濾 (如 2337)"
                        className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
                    />
                    <button
                        type="submit"
                        className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg font-bold hover:bg-blue-700 transition-colors"
                    >
                        搜尋
                    </button>
                    <button
                        type="button"
                        onClick={() => { setFilterCode(''); fetchData(null); }}
                        className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-lg font-bold hover:bg-gray-200 transition-colors"
                    >
                        全部
                    </button>
                </form>
            </div>

            {/* Summary stats */}
            {data && (
                <div className="grid grid-cols-3 gap-2">
                    {[
                        { label: '報告則數', value: reports.length, color: 'text-blue-700' },
                        { label: '含目標價', value: hasTarget, color: 'text-red-600' },
                        { label: '買進評等', value: hasBuy, color: 'text-orange-600' },
                    ].map((s, i) => (
                        <div key={i} className="bg-white rounded-xl border border-gray-100 p-2 text-center shadow-sm">
                            <div className={`text-xl font-black ${s.color}`}>{s.value}</div>
                            <div className="text-[9px] text-gray-400 font-bold uppercase tracking-wide">{s.label}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div className="flex items-center justify-center py-8 gap-3">
                    <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm text-gray-500">搜尋凱基投顧報告中…</span>
                </div>
            )}

            {/* Error */}
            {error && !loading && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-600">{error}</div>
            )}

            {/* Summary text */}
            {data?.summary && !loading && (
                <div className="text-xs bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 text-blue-700">
                    {data.summary}
                </div>
            )}

            {/* Table View */}
            {!loading && reports.length > 0 && viewMode === 'table' && (
                <div className="overflow-x-auto rounded-xl border border-gray-100 shadow-sm">
                    <table className="w-full text-[11px]">
                        <thead>
                            <tr className="bg-gradient-to-r from-slate-700 to-slate-800 text-white">
                                {['日期', '代號', '名稱', '評等', '目標價', 'EPS', 'P/E', '來源新聞'].map(h => (
                                    <th key={h} className="px-2 py-2 text-left font-bold tracking-wide whitespace-nowrap">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {reports.map((r, idx) => (
                                <tr
                                    key={idx}
                                    className={`border-t border-gray-100 hover:bg-blue-50 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/60'}`}
                                >
                                    <td className="px-2 py-1.5 text-gray-500 whitespace-nowrap">{r.date}</td>
                                    <td className="px-2 py-1.5 font-bold text-blue-700 whitespace-nowrap">{r.code || '—'}</td>
                                    <td className="px-2 py-1.5 font-semibold whitespace-nowrap">{r.stock_name}</td>
                                    <td className="px-2 py-1.5">
                                        {r.rating ? (
                                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${getRatingColor(r.rating)}`}>
                                                {r.rating}
                                            </span>
                                        ) : <span className="text-gray-300">—</span>}
                                    </td>
                                    <td className="px-2 py-1.5 text-red-600 font-bold whitespace-nowrap">
                                        {r.target_price ? `$${r.target_price}` : '—'}
                                    </td>
                                    <td className="px-2 py-1.5 text-emerald-600 font-semibold whitespace-nowrap">
                                        {r.eps_2026 ? `$${r.eps_2026}` : '—'}
                                    </td>
                                    <td className="px-2 py-1.5 text-purple-600 whitespace-nowrap">
                                        {r.pe_multiple ? `${r.pe_multiple}x` : '—'}
                                    </td>
                                    <td className="px-2 py-1.5 max-w-[200px]">
                                        {r.link ? (
                                            <a href={r.link} target="_blank" rel="noopener noreferrer"
                                               className="text-blue-500 hover:underline truncate block" title={r.title}>
                                                {r.title}
                                            </a>
                                        ) : (
                                            <span className="text-gray-500 truncate block">{r.title}</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Card View */}
            {!loading && reports.length > 0 && viewMode === 'cards' && (
                <div className="space-y-2">
                    {reports.map((r, idx) => (
                        <div key={idx} className="bg-white border border-gray-100 rounded-xl p-3 shadow-sm hover:shadow-md transition-shadow">
                            <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {r.code && <span className="text-[11px] font-black text-blue-700 bg-blue-50 px-1.5 rounded">{r.code}</span>}
                                        <span className="text-[11px] font-bold text-gray-800">{r.stock_name}</span>
                                        {r.rating && (
                                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${getRatingColor(r.rating)}`}>
                                                {r.rating}
                                            </span>
                                        )}
                                        <span className="text-[10px] text-gray-400">{r.date}</span>
                                    </div>
                                    <div className="flex gap-4 mt-1.5 flex-wrap">
                                        {r.target_price && (
                                            <div className="flex items-center gap-1">
                                                <span className="text-[10px] text-gray-400">目標價</span>
                                                <span className="text-[12px] font-black text-red-600">${r.target_price}</span>
                                            </div>
                                        )}
                                        {r.eps_2026 && (
                                            <div className="flex items-center gap-1">
                                                <span className="text-[10px] text-gray-400">EPS</span>
                                                <span className="text-[12px] font-black text-emerald-600">${r.eps_2026}</span>
                                            </div>
                                        )}
                                        {r.pe_multiple && (
                                            <div className="flex items-center gap-1">
                                                <span className="text-[10px] text-gray-400">P/E</span>
                                                <span className="text-[12px] font-black text-purple-600">{r.pe_multiple}x</span>
                                            </div>
                                        )}
                                    </div>
                                    {r.link ? (
                                        <a href={r.link} target="_blank" rel="noopener noreferrer"
                                           className="block mt-1 text-[10px] text-blue-500 hover:underline truncate">
                                            📰 {r.title}
                                        </a>
                                    ) : (
                                        <p className="mt-1 text-[10px] text-gray-500 truncate">📰 {r.title}</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {!loading && !error && reports.length === 0 && (
                <div className="text-center py-6 text-gray-400 text-sm">
                    <div className="text-3xl mb-2">🔍</div>
                    暫無找到凱基研究報告，請嘗試其他搜尋條件
                </div>
            )}

            {/* Disclaimer */}
            <div className="text-[9px] text-gray-400 text-center pt-1 border-t border-gray-100">
                資料來源：Google News RSS 公開媒體整理 ｜ 非凱基官方直接授權 ｜ 僅供參考，投資人應自行判斷
            </div>
        </div>
    );
};

export default KGIResearchPanel;
