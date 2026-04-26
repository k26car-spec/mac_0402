import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

const MacroPanel = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdate, setLastUpdate] = useState(null);
    const [collapsed, setCollapsed] = useState(false);

    const fetchMacro = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const res = await fetch(`${API_BASE}/api/market-decision/macro`);
            const json = await res.json();
            setData(json);
            setLastUpdate(new Date().toLocaleTimeString('zh-TW'));
        } catch (err) {
            setError('無法連線取得國際新聞');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchMacro();
        const t = setInterval(fetchMacro, 10 * 60 * 1000); // 10 minutes
        return () => clearInterval(t);
    }, [fetchMacro]);

    const isOptimistic = data?.sentiment?.includes('樂觀');
    const isPessimistic = data?.sentiment?.includes('恐慌');
    const badgeColor = isOptimistic ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 
                       isPessimistic ? 'bg-red-50 text-red-700 border-red-200' : 
                       'bg-amber-50 text-amber-600 border-amber-200';

    return (
        <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden mt-6">
            {/* 標題列 */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                <div className="flex items-center gap-2">
                    <span className="text-base">🌍</span>
                    <span className="text-xs font-black text-slate-800 uppercase tracking-widest">國際政經總匯</span>
                    {loading && <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />}
                </div>
                <div className="flex items-center gap-2">
                    {lastUpdate && (
                        <span className="text-[10px] text-slate-400 font-mono">{lastUpdate}</span>
                    )}
                    <button
                        onClick={fetchMacro}
                        disabled={loading}
                        className="text-slate-400 hover:text-slate-700 transition-colors text-xs px-2 py-0.5 rounded-lg border border-slate-200 hover:border-slate-400 disabled:opacity-40"
                    >↻</button>
                    <button
                        onClick={() => setCollapsed(c => !c)}
                        className="text-slate-400 hover:text-slate-700 transition-colors text-xs"
                    >{collapsed ? '▼' : '▲'}</button>
                </div>
            </div>

            {!collapsed && (
                <div className="px-6 py-5 space-y-4">
                    {error ? (
                        <div className="text-center text-red-500 text-sm py-4">
                            ⚠️ {error}
                            <button onClick={fetchMacro} className="ml-2 text-blue-500 underline text-xs">重試</button>
                        </div>
                    ) : loading && !data ? (
                        <div className="text-center text-slate-400 text-sm py-6 animate-pulse">
                            正在掃描全球即時新聞與地緣政治現況...
                        </div>
                    ) : (
                        <>
                            {/* Summary & Sentiment */}
                            <div className="flex items-center justify-between">
                                <span className={`text-[12px] font-black px-3 py-1 rounded-full border ${badgeColor}`}>
                                    {data.sentiment || "分析中"}
                                </span>
                            </div>
                            
                            <p className="text-sm font-bold text-slate-700 leading-relaxed border-l-4 border-blue-400 pl-3">
                                {data.summary}
                            </p>

                            {/* Action Advice */}
                            <div className="bg-blue-50/50 rounded-xl p-3 border border-blue-100/50 mt-3">
                                <div className="text-[10px] text-blue-600 font-bold mb-1 flex items-center gap-1">
                                    <span>💡</span> 大盤資金聯動建議
                                </div>
                                <div className="text-[11px] text-slate-600 leading-relaxed font-medium">
                                    {data.action_advice}
                                </div>
                            </div>

                            {/* Top Geopolitical Events */}
                            {data.top_events && data.top_events.length > 0 && (
                                <div className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
                                    <div className="text-[9px] text-slate-400 font-black uppercase tracking-widest mb-2">🔥 即時觸發熱點</div>
                                    {data.top_events.map((event, i) => (
                                        <div key={i} className="flex items-start gap-1.5 text-[11px] font-medium text-slate-600 mb-3 last:mb-0">
                                            <span className="text-slate-400 mt-[1px] flex-shrink-0">
                                                {event.impact === 'positive' ? '🟢' : '🔴'}
                                            </span>
                                            <div className="flex-1">
                                                <a href={event.link} target="_blank" rel="noopener noreferrer" className="font-bold hover:text-blue-600 hover:underline block leading-tight">
                                                    {event.title}
                                                </a>
                                                <span className="text-[9px] text-slate-400 mt-1 block">
                                                    {event.source} {event.category && `· ${event.category}`}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Recent Headlines */}
                            {data.recent_headlines && data.recent_headlines.length > 0 && (
                                <div className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
                                    <div className="text-[9px] text-slate-400 font-black uppercase tracking-widest mb-2">📰 國際與國內頭條</div>
                                    {data.recent_headlines.map((item, i) => (
                                        <div key={i} className="flex items-start gap-1.5 text-[11px] text-slate-500 mb-2 last:mb-0">
                                            <span className="text-slate-300 mt-[1px] flex-shrink-0">•</span>
                                            <div className="flex-1 min-w-0">
                                                <a href={item.link} target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 hover:underline truncate block" title={item.original_title || item.title}>
                                                    {item.is_foreign && <span className="text-[9px] bg-blue-50 text-blue-500 px-1 rounded mr-1">譯</span>}
                                                    {item.title}
                                                </a>
                                                <div className="text-[8px] text-slate-300 mt-0.5">{item.source}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="text-center text-[9px] text-slate-400 mt-2">
                                來源：多元媒體 (Reuters, CNBC, Google News) · AI 自動翻譯與分類
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default MacroPanel;
