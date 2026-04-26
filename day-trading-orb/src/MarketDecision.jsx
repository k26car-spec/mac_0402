import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, AlertTriangle, AlertCircle, Info, CheckCircle, ArrowRight, Shield, Zap } from 'lucide-react';

const MarketDecision = ({ symbol, API_BASE, variant = 'full' }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchData = async () => {
        try {
            const url = symbol
                ? `${API_BASE}/api/market-decision/status?symbol=${symbol}`
                : `${API_BASE}/api/market-decision/status`;
            const res = await fetch(url);
            const result = await res.json();
            setData(result);
            setLoading(false);
        } catch (err) {
            console.error("Fetch market decision failed:", err);
            setError(err.message);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 60000); // 1分鐘更新一次
        return () => clearInterval(interval);
    }, [symbol]);

    if (loading && !data) return (
        <div className="flex items-center justify-center p-8 text-blue-600">
            <span className="animate-spin mr-2"><Activity size={20} /></span>
            正在解析大盤決策矩陣...
        </div>
    );

    if (error) return (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 flex items-center shadow-sm">
            <AlertCircle size={20} className="mr-2" />
            無法獲取市場數據: {error}
        </div>
    );

    const { market_data, market_condition, stock_condition, decision, warnings, summary } = data;

    const getStatusIcon = (cond) => {
        if (cond === 'BULL' || cond === 'STRONG') return <TrendingUp className="text-emerald-600" />;
        if (cond === 'BEAR' || cond === 'WEAK') return <TrendingDown className="text-rose-600" />;
        return <Activity className="text-amber-600" />;
    };

    const getStatusText = (cond) => {
        if (cond === 'BULL' || cond === 'STRONG') return '強勢 🟢';
        if (cond === 'BEAR' || cond === 'WEAK') return '弱勢 🔴';
        return '中性 🟡';
    };

    const getLevelClass = (level) => {
        switch (level) {
            case 'success': return 'bg-emerald-50 border-2 border-emerald-400 text-emerald-800 shadow-emerald-100';
            case 'info': return 'bg-blue-50 border-2 border-blue-400 text-blue-800 shadow-blue-100';
            case 'warning': return 'bg-amber-50 border-2 border-amber-400 text-amber-800 shadow-amber-100';
            case 'error': return 'bg-rose-50 border-2 border-rose-400 text-rose-800 shadow-rose-100';
            default: return 'bg-slate-50 border-2 border-slate-300 text-slate-800 shadow-slate-100';
        }
    };

    if (variant === 'compact') {
        return (
            /* 🛡️ 核心決策區域 - 超緊湊水平狀態列 */
            <div className={`border-l-4 rounded-r-xl overflow-hidden shadow-sm transition-all duration-500 ${getLevelClass(decision.level)}`}>
                <div className="flex flex-wrap md:flex-nowrap items-center justify-between px-4 py-2 gap-4">
                    {/* 左側：核心標籤 */}
                    <div className="flex items-center gap-2 min-w-fit">
                        <Shield className="text-blue-600" size={14} />
                        <span className="text-[10px] font-black text-gray-800 whitespace-nowrap uppercase tracking-tighter">AI 聯合決策</span>
                    </div>

                    {/* 中間：狀態指標 */}
                    <div className="flex items-center gap-6 flex-1 justify-center">
                        <div className="flex items-center gap-2">
                            <div className="scale-75 origin-right">{getStatusIcon(market_condition)}</div>
                            <div>
                                <div className="text-[8px] text-gray-400 font-bold uppercase leading-none mb-0.5">大盤狀態</div>
                                <div className="text-[11px] font-black text-gray-900 leading-none">{getStatusText(market_condition)}</div>
                            </div>
                        </div>

                        <div className="w-px h-6 bg-gray-200/50"></div>

                        <div className="flex items-center gap-2">
                            <div className="scale-75 origin-right">{getStatusIcon(stock_condition)}</div>
                            <div>
                                <div className="text-[8px] text-gray-400 font-bold uppercase leading-none mb-0.5">多空力道</div>
                                <div className="text-[11px] font-black text-gray-900 leading-none">{getStatusText(stock_condition)}</div>
                            </div>
                        </div>
                    </div>

                    {/* 右側：最終決策 & 倉位 */}
                    <div className="flex items-center gap-3 bg-white/50 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/60 shadow-inner">
                        <div className="text-right">
                            <div className="text-[8px] font-bold text-gray-500 uppercase leading-none mb-0.5">聯合決策</div>
                            <div className="text-sm font-black tracking-tight leading-none">{decision.action}</div>
                        </div>
                        <div className="w-px h-6 bg-current opacity-10"></div>
                        <div className="text-center">
                            <div className="text-[8px] font-bold text-gray-500 uppercase leading-none mb-0.5">建議部位</div>
                            <div className="text-lg font-black tracking-tighter leading-none animate-number-pop">{decision.position}</div>
                        </div>
                    </div>

                    {/* 最右側：小時間戳 */}
                    <div className="hidden xl:block text-[8px] text-gray-400 font-bold uppercase tracking-widest pl-2 border-l border-gray-100">
                        版本 v3.1 • {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                </div>
                <style jsx>{`
                    @keyframes number-pop {
                        0% { transform: scale(0.95); opacity: 0; }
                        80% { transform: scale(1.05); }
                        100% { transform: scale(1); opacity: 1; }
                    }
                    .animate-number-pop {
                        animation: number-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
                    }
                `}</style>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 🚨 大盤預警系統 - 亮色卡片設計 */}
            {warnings && warnings.length > 0 && (
                <div className="grid grid-cols-1 gap-4">
                    {warnings.map((warn, idx) => (
                        <div key={idx} className="bg-white border border-gray-100 rounded-2xl overflow-hidden shadow-xl hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-1">
                            <div className="bg-gray-50/80 backdrop-blur-sm px-5 py-3 flex justify-between items-center border-b border-gray-100">
                                <h3 className="font-bold flex items-center text-gray-800 text-base">
                                    <span className="text-xl mr-2">{warn.type === 'opening' ? '🌅' : warn.type === 'abnormal' ? '🚨' : '🕐'}</span>
                                    {warn.title}
                                </h3>
                                <div className="flex items-center space-x-2">
                                    <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse"></span>
                                    <span className="text-xs text-gray-400 font-mono font-bold tracking-wider">{warn.timestamp}</span>
                                </div>
                            </div>
                            <div className="p-5">
                                <div className="space-y-2 mb-4">
                                    {warn.content.map((line, lidx) => (
                                        <div key={lidx} className="text-sm text-gray-600 flex items-start">
                                            <span className="text-gray-300 mr-2 mt-1">•</span>
                                            <span className="font-medium">{line}</span>
                                        </div>
                                    ))}
                                </div>
                                <div className={`p-4 rounded-xl font-black text-center text-base shadow-sm border ${(warn.prediction && warn.prediction.includes('🟢')) || (warn.recommendation && warn.recommendation.includes('🟢'))
                                    ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                                    : (warn.prediction && warn.prediction.includes('🔴')) || (warn.recommendation && warn.recommendation.includes('🔴'))
                                        ? 'bg-rose-50 border-rose-200 text-rose-700'
                                        : 'bg-amber-50 border-amber-200 text-amber-700'
                                    }`}>
                                    {warn.prediction || warn.recommendation}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* 📊 大盤數據面板 - 緊湊水平Ticker */}
            <div className="bg-white/40 backdrop-blur-md border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                <div className="grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">
                    {/* TAIEX Summary (XL-3) */}
                    <div className="lg:col-span-3 p-3 flex items-center justify-between">
                        <div className="flex flex-col">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">TAIEX 加權指數</span>
                            <div className="flex items-baseline gap-2 mt-0.5">
                                <span className="text-xl font-black text-slate-900 tracking-tighter">{market_data.index.toLocaleString()}</span>
                                <span className={`text-[11px] font-black ${market_data.change >= 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                                    {market_data.change >= 0 ? '+' : ''}{market_data.change.toFixed(2)} ({Math.abs(market_data.change_pct).toFixed(2)}%)
                                </span>
                            </div>
                        </div>
                        <div className="text-right flex flex-col items-end">
                            <div className="text-[10px] font-bold text-slate-400 uppercase">法人買賣超 (億)</div>
                            <div className="flex gap-2">
                                <span className={`text-[11px] font-black ${market_data.foreign_net > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>外:{market_data.foreign_net}E</span>
                                <span className={`text-[11px] font-black ${market_data.trust_net > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>投:{market_data.trust_net}E</span>
                            </div>
                        </div>
                    </div>

                    {/* Global Markets (XL-3) */}
                    <div className="lg:col-span-3 p-3 flex flex-col justify-center">
                        <div className="flex justify-between items-center text-[10px] mb-1">
                            <span className="font-black text-slate-400 uppercase tracking-widest leading-none">全球市場連動</span>
                            <span className="font-mono text-slate-400">台幣匯率: {market_data.usdtwd.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between items-center gap-4">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-bold text-slate-500 uppercase">美股 S&P500</span>
                                <span className={`text-[11px] font-black ${market_data.sp500_change > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>{market_data.sp500_change.toFixed(2)}%</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-bold text-slate-500 uppercase">日經 NIKKEI</span>
                                <span className={`text-[11px] font-black ${market_data.nikkei_change > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>{market_data.nikkei_change.toFixed(2)}%</span>
                            </div>
                        </div>
                    </div>

                    {/* AI Market Intel (XL-6) */}
                    <div className="lg:col-span-6 p-3 bg-blue-50/30 flex items-center">
                        <div className="flex-shrink-0 mr-3">
                            <div className="bg-blue-600 text-white p-1.5 rounded-lg shadow-blue-200 shadow-lg">
                                <Zap size={14} fill="currentColor" />
                            </div>
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <div className="flex items-center gap-2 mb-0.5">
                                <span className="text-[9px] font-black text-blue-600 uppercase tracking-widest">AI 市場情報解析</span>
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-600 text-white font-bold animate-pulse">核心運算中</span>
                            </div>
                            <p className="text-[11px] text-blue-900 font-bold italic line-clamp-1 leading-none tracking-tight">
                                "{summary}"
                            </p>
                        </div>
                    </div>
                </div>
            </div>


            <style jsx>{`
                @keyframes number-pop {
                    0% { transform: scale(0.95); opacity: 0; }
                    80% { transform: scale(1.05); }
                    100% { transform: scale(1); opacity: 1; }
                }
                .animate-number-pop {
                    animation: number-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
                }
                .animate-pulse-subtle {
                    animation: pulse-subtle 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
                }
                @keyframes pulse-subtle {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.01); }
                }
            `}</style>
        </div>
    );
};

export default MarketDecision;
