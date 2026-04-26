'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    Target, RefreshCw, ChevronDown, ChevronUp, AlertTriangle,
    TrendingUp, TrendingDown, Wifi, WifiOff, Shield, Zap,
    DollarSign, Activity, Filter, Plus, Settings, Search, Trash2, Star,
    Flame, Thermometer, Orbit, BellRing
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SectorInfo {
    name: string;
    emoji: string;
    stocks: string[];
}

interface StockSignal {
    symbol: string;
    name: string;
    price: number;
    change: number;
    volume: number;
    sector: string;
    signalType: 'BUY' | 'WAIT' | 'AVOID' | 'LOADING' | 'ERROR';
    signalText: string;
    confidence: number;
    foreignNet: number;
    trustNet: number;
    chipAlert: boolean;
    chipAlertText?: string;
    supportLevel: number;
    resistanceLevel: number;
    vwap: number;
    vwapDeviation: number;
    riskScore: number;
    isStarred?: boolean;
    sniperSignals?: {
        vwap_control: 'LONG' | 'SHORT' | 'NEUTRAL';
        is_divergence: boolean;
        is_precision_strike: boolean;
        kd_k: number;
        kd_d?: number;
        status: 'RED_LIGHT' | 'GREEN_LIGHT' | 'PURPLE_LIGHT' | 'NEUTRAL' | 'WAIT_AND_SEE';
        vwap_deviation?: number;
        vwap?: number;
    };
    risk?: {
        volume_ratio: number;
    };
    checks?: {
        dip_analysis?: {
            quality: string;
            score: number;
            confidence: number;
            reasons: string[];
            warnings: string[];
            stop_loss_price: number;
            target_price: number;
        };
        [key: string]: any;
    };
}

export default function SniperPage() {
    const [signals, setSignals] = useState<StockSignal[]>([]);
    const [sectorWatchlists, setSectorWatchlists] = useState<Record<string, SectorInfo>>({});
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [starredStocks, setStarredStocks] = useState<Set<string>>(new Set());
    const [isConnected, setIsConnected] = useState(false);
    const [connStatus, setConnStatus] = useState({ connected: false, source: 'loading' });
    const abortControllerRef = useRef<AbortController | null>(null);
    const prevGreenHighRef = useRef<Set<string>>(new Set());

    // UI 狀態
    const [activeSector, setActiveSector] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [showAddStock, setShowAddStock] = useState(false);
    const [quotes, setQuotes] = useState<any[]>([]);

    useEffect(() => {
        const fetchQuotes = async () => {
            try {
                const res = await fetch(`http://${window.location.hostname}:8000/api/market/quotes`);
                if (res.ok) { const data = await res.json(); setQuotes(data.quotes || []); }
            } catch (e) { }
        };
        fetchQuotes();
        const timer = setInterval(fetchQuotes, 60000);
        return () => clearInterval(timer);
    }, []);

    // 同態獲取 API 路徑
    const getApiUrl = (path: string) => {
        const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
        return `http://${hostname}:8000${path}`;
    };

    const fetchConnStatus = useCallback(async () => {
        try {
            const res = await fetch(getApiUrl('/api/market/status'));
            if (res.ok) {
                const data = await res.json();
                setConnStatus({ connected: data.connected, source: data.source });
            }
        } catch (e) {
            console.error('Fetch status error:', e);
            setConnStatus(prev => ({ ...prev, connected: false }));
        }
    }, []);

    // 載入 localStorage 中的關注列表
    useEffect(() => {
        const saved = localStorage.getItem('sniper_starred_stocks');
        if (saved) {
            try { setStarredStocks(new Set(JSON.parse(saved))); } catch (e) { }
        }
    }, []);

    // 儲存關注列表
    useEffect(() => {
        localStorage.setItem('sniper_starred_stocks', JSON.stringify(Array.from(starredStocks)));
    }, [starredStocks]);

    const toggleStar = useCallback((symbol: string) => {
        setStarredStocks(prev => {
            const next = new Set(prev);
            if (next.has(symbol)) next.delete(symbol);
            else next.add(symbol);
            return next;
        });
    }, []);

    const playAlert = useCallback(() => {
        if (typeof window !== 'undefined') {
            const audio = new Audio('/sounds/sniper-shot.mp3');
            audio.play().catch(() => { });
        }
    }, []);

    // 核心：從 ORB Watchlist 獲取標的
    const loadConfig = useCallback(async () => {
        try {
            setError(null);
            const res = await fetch(getApiUrl('/api/orb/watchlist'));
            if (res.ok) {
                const data = await res.json();
                if (data.watchlist) {
                    setIsConnected(true);
                    const sectors: Record<string, SectorInfo> = { 'ORB_MONITOR': { name: '主力監控', emoji: '🎯', stocks: data.watchlist } };
                    setSectorWatchlists(sectors);
                    if (!activeSector) setActiveSector('ORB_MONITOR');
                    return sectors;
                }
            }
            return null;
        } catch (err) {
            setIsConnected(false);
            setError('無法連接後端伺服器');
            return null;
        }
    }, [activeSector]);

    const loadSignals = useCallback(async (sectorsInput?: Record<string, SectorInfo>) => {
        const sectors = sectorsInput || sectorWatchlists;
        const allSymbols = Object.values(sectors).flatMap(s => s.stocks);
        if (allSymbols.length === 0) { setIsLoading(false); return; }

        if (abortControllerRef.current) abortControllerRef.current.abort();
        abortControllerRef.current = new AbortController();

        try {
            setIsLoading(true);
            const res = await fetch(getApiUrl('/api/entry-check/batch-details'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbols: allSymbols }),
                signal: abortControllerRef.current.signal
            });

            if (res.ok) {
                const data = await res.json();
                if (data.results) {
                    const mapped: StockSignal[] = data.results.map((r: any) => ({
                        symbol: r.symbol,
                        name: r.name,
                        price: r.entry_price || 0,
                        change: r.checks?.risk?.change_pct || 0,
                        volume: 0,
                        sector: 'ORB_MONITOR',
                        signalType: r.should_enter ? 'BUY' : 'WAIT',
                        signalText: r.recommended_action,
                        confidence: r.confidence,
                        foreignNet: r.checks?.institutional?.total_net > 0 ? 100 : 0,
                        trustNet: 0,
                        chipAlert: false,
                        supportLevel: 0,
                        resistanceLevel: 0,
                        vwap: r.sniper_signals?.vwap || 0,
                        vwapDeviation: r.sniper_signals?.vwap_deviation || 0,
                        riskScore: 0,
                        sniperSignals: r.sniper_signals,
                        risk: r.checks?.risk,
                        checks: r.checks
                    }));

                    // 偵測精準打擊訊號並播放音效
                    mapped.forEach(s => {
                        if (s.sniperSignals?.status === 'GREEN_LIGHT' && s.confidence >= 85) {
                            if (!prevGreenHighRef.current.has(s.symbol)) {
                                playAlert();
                            }
                        }
                    });
                    prevGreenHighRef.current = new Set(mapped.filter(s => s.sniperSignals?.status === 'GREEN_LIGHT' && s.confidence >= 85).map(s => s.symbol));

                    setSignals(mapped);
                }
            }
        } catch (err: any) {
            if (err.name !== 'AbortError') setIsConnected(false);
        } finally {
            setIsLoading(false);
        }
    }, [sectorWatchlists, playAlert]);

    useEffect(() => {
        fetchConnStatus();
        loadConfig(); // loadConfig sets sectorWatchlists which triggers loadSignals

        const signalInterval = setInterval(() => loadSignals(), 60000);
        const statusInterval = setInterval(() => fetchConnStatus(), 30000);
        const configInterval = setInterval(() => loadConfig(), 300000); // Sync config every 5 mins

        return () => {
            clearInterval(signalInterval);
            clearInterval(statusInterval);
            clearInterval(configInterval);
        };
    }, [loadConfig, loadSignals, fetchConnStatus]);

    // Automatically load signals when config is loaded
    useEffect(() => {
        if (Object.keys(sectorWatchlists).length > 0) {
            loadSignals(sectorWatchlists);
        }
    }, [sectorWatchlists, loadSignals]);

    const sortedSignals = signals.filter(s => {
        if (activeSector && s.sector !== activeSector) return false;
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            return s.symbol.toLowerCase().includes(query) || (s.name && s.name.toLowerCase().includes(query));
        }
        return true;
    }).sort((a, b) => {
        const aStarred = starredStocks.has(a.symbol);
        const bStarred = starredStocks.has(b.symbol);
        if (aStarred && !bStarred) return -1;
        if (!aStarred && bStarred) return 1;

        const priority = { 'PURPLE_LIGHT': 6, 'RED_LIGHT': 5, 'GREEN_LIGHT': 4, 'NEUTRAL': 3, 'WAIT_AND_SEE': 2, 'ERROR': 1 };
        const pA = priority[a.sniperSignals?.status as keyof typeof priority] || 0;
        const pB = priority[b.sniperSignals?.status as keyof typeof priority] || 0;
        if (pA !== pB) return pB - pA;

        return b.confidence - a.confidence;
    });

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-20">
            <style jsx global>{`
                @keyframes blink-red {
                    0% { background-color: #fff1f2; box-shadow: 0 0 0px #ef4444; border-color: #fec1c1; }
                    50% { background-color: #fee2e2; box-shadow: 0 0 10px #ef4444; border-color: #ef4444; }
                    100% { background-color: #fff1f2; box-shadow: 0 0 0px #ef4444; border-color: #fec1c1; }
                }
                @keyframes pulse-green {
                    0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4); border-color: #22c55e;}
                    70% { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); border-color: #22c55e;}
                    100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); border-color: #22c55e;}
                }
                @keyframes purple-burst {
                    0% { background-color: #f5f3ff; box-shadow: 0 0 0px #8b5cf6; border-color: #ddd6fe; }
                    50% { background-color: #ede9fe; box-shadow: 0 0 15px #8b5cf6; border-color: #8b5cf6; }
                    100% { background-color: #f5f3ff; box-shadow: 0 0 0px #8b5cf6; border-color: #ddd6fe; }
                }
                .status-danger { color: #b91c1c; animation: blink-red 1.5s infinite; border: 1px solid #ef4444; font-weight: 800; background-color: #fff1f2 !important; }
                .status-buy { background-color: #f0fdf4 !important; color: #15803d; border: 1px solid #22c55e; animation: pulse-green 2s infinite; font-weight: 800; }
                .status-burst { background-color: #f5f3ff !important; color: #6d28d9; border: 1px solid #8b5cf6; animation: purple-burst 1s infinite; font-weight: 900; }
                .status-wait { background-color: #f8fafc !important; color: #64748b; border: 1px dashed #cbd5e1; font-weight: 800; }
                .stock-card-lite { background-color: #fff; border: 1px solid #e2e8f0; transition: all 0.2s; border-radius: 16px; padding: 20px; }
                .stock-card-lite:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-color: #cbd5e1; }
                .slim-top-bar { backdrop-filter: blur(8px); background-color: rgba(255, 255, 255, 0.82); }
            `}</style>

            {/* 🔥 Elegant Integrated Top Bar */}
            <div className="bg-white border-b border-slate-200/60 h-14 flex items-center px-8 sticky top-0 z-40 backdrop-blur-md bg-white/80">
                <div className="flex items-center gap-10 overflow-x-auto no-scrollbar scroll-smooth">
                    {quotes.slice(0, 6).map((q, i) => (
                        <div key={i} className="flex items-center gap-3 whitespace-nowrap">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider">{q.label}</span>
                            <span className="text-sm font-black text-slate-800 font-mono tracking-tighter">{q.value === "---" ? "即時" : q.value}</span>
                            <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded-md", q.change >= 0 ? "text-rose-600 bg-rose-50" : "text-emerald-600 bg-emerald-50")}>
                                {q.change >= 0 ? '▲' : '▼'}{Math.abs(q.change).toFixed(2)}%
                            </span>
                        </div>
                    ))}
                </div>

                <div className="ml-auto pl-8 border-l border-slate-100 hidden md:flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                        <span className="text-[11px] font-black text-slate-600 uppercase tracking-widest">System Live</span>
                    </div>
                </div>
            </div>

            <div className="max-w-[1600px] mx-auto p-8 space-y-12">
                {/* 🎯 Main Header Area */}
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 pb-4">
                    <div className="space-y-4">
                        <div className="flex items-center gap-4">
                            <h1 className="text-6xl font-black tracking-tighter text-slate-900 leading-none">
                                ORB 監控戰情室
                            </h1>
                            <div className="flex flex-col">
                                <span className="bg-indigo-600 text-white text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest shadow-lg shadow-indigo-100">
                                    {connStatus.connected ? 'Premium API' : 'Fallback'}
                                </span>
                            </div>
                        </div>
                        <p className="text-slate-400 font-bold text-xl flex items-center gap-3">
                            <Orbit className="w-5 h-5 text-indigo-400" />
                            同步自戰情名單 | 目前監控 <span className="text-slate-900">{signals.length}</span> 支主力標的
                        </p>
                    </div>

                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => { loadConfig().then(s => s && loadSignals(s)); }}
                            disabled={isLoading}
                            className="bg-slate-900 hover:bg-black text-white px-10 py-5 rounded-[2rem] shadow-2xl flex items-center gap-4 font-black text-xl transition-all active:scale-95 disabled:opacity-50"
                        >
                            <RefreshCw className={cn("w-6 h-6", isLoading && "animate-spin")} />
                            {isLoading ? '解析中...' : '刷新報價'}
                        </button>
                        <button
                            onClick={() => setShowAddStock(true)}
                            className="p-5 bg-white border-2 border-slate-100 text-slate-400 rounded-[2rem] hover:border-indigo-500 hover:text-indigo-500 transition-all shadow-sm"
                        >
                            <Plus className="w-8 h-8" />
                        </button>
                    </div>
                </div>

                {/* 📊 Market Pulse & Legend Grid */}
                <div className="grid grid-cols-1 xl:grid-cols-4 gap-8 items-start">
                    <div className="xl:col-span-3">
                        <MarketPulse quotes={quotes} />
                    </div>
                    <div className="bg-white border border-slate-100 rounded-[2.5rem] p-8 shadow-sm space-y-6">
                        <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] px-2 mb-4">訊號圖例</h3>
                        <div className="space-y-5">
                            <div className="flex items-start gap-4">
                                <div className="w-3 h-3 rounded-full bg-purple-500 mt-1.5 shadow-[0_0_10px_rgba(168,85,247,0.4)]" />
                                <div><div className="font-bold text-sm">⚡ 爆量攻擊</div><p className="text-[10px] text-slate-400 font-bold">15分量比 {">"} 2.0</p></div>
                            </div>
                            <div className="flex items-start gap-4">
                                <div className="w-3 h-3 rounded-full bg-emerald-500 mt-1.5 shadow-[0_0_10px_rgba(16,185,129,0.4)]" />
                                <div><div className="font-bold text-sm">🎯 精準打擊</div><p className="text-[10px] text-slate-400 font-bold">帶量回測支撐</p></div>
                            </div>
                            <div className="flex items-start gap-4">
                                <div className="w-3 h-3 rounded-full bg-rose-500 mt-1.5 shadow-[0_0_10px_rgba(244,63,94,0.4)]" />
                                <div><div className="font-bold text-sm">🛑 理性避險</div><p className="text-[10px] text-slate-400 font-bold">價量背離/高位過熱</p></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="pt-4 pb-12">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-black text-slate-800 flex items-center gap-3">
                            <Activity className="w-6 h-6 text-indigo-500" />
                            實時監控清單
                        </h2>
                        {isLoading && (
                            <div className="flex items-center gap-2 text-indigo-500 font-bold animate-pulse">
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                正在解析全盤大數據...
                            </div>
                        )}
                    </div>

                    {signals.length === 0 && !isLoading ? (
                        <div className="bg-white rounded-[2rem] p-20 text-center border-2 border-dashed border-slate-200">
                            <div className="text-slate-300 mb-4 flex justify-center"><Search className="w-16 h-16" /></div>
                            <h3 className="text-xl font-bold text-slate-400">尚未加入監控標的</h3>
                            <p className="text-slate-400 mt-2">點擊右上角 "+" 按鈕從 ORB Watchlist 同步或手動新增</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {isLoading && signals.length === 0 ? (
                                Array(8).fill(0).map((_, i) => (
                                    <div key={i} className="animate-pulse bg-white border border-slate-100 h-64 rounded-3xl" />
                                ))
                            ) : (
                                sortedSignals.map((stock) => (
                                    <StockCard
                                        key={`${stock.sector}-${stock.symbol}`}
                                        stock={stock}
                                        isStarred={starredStocks.has(stock.symbol)}
                                        onStar={() => toggleStar(stock.symbol)}
                                        onDelete={async () => {
                                            if (confirm(`確定移除 ${stock.name}?`)) {
                                                const currentList = signals.map(s => s.symbol).filter(s => s !== stock.symbol);
                                                const res = await fetch(getApiUrl('/api/orb/watchlist'), {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({ watchlist: currentList })
                                                });
                                                if (res.ok) { loadConfig().then(s => s && loadSignals(s)); }
                                            }
                                        }}
                                    />
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>

            {showAddStock && (
                <AddStockModal
                    onClose={() => setShowAddStock(false)}
                    onSuccess={() => { setShowAddStock(false); loadConfig().then(s => s && loadSignals(s)); }}
                    currentWatchlist={signals.map(s => s.symbol)}
                />
            )}
        </div>
    );
}

function MarketPulse({ quotes }: { quotes: any[] }) {
    return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {quotes.map((q, i) => (
                <div key={i} className="bg-white p-6 rounded-3xl border border-slate-100 flex flex-col gap-2 shadow-sm transition-all hover:shadow-md hover:-translate-y-1">
                    <span className="text-[11px] font-black text-slate-400 uppercase tracking-[0.1em]">{q.label}</span>
                    <span className="text-3xl font-black text-slate-900 font-mono tracking-tighter">
                        {q.value}
                    </span>
                    <span className={cn("text-sm font-bold flex items-center gap-1", q.change >= 0 ? "text-rose-500" : "text-emerald-500")}>
                        {q.change >= 0 ? '▲' : '▼'}{Math.abs(q.change).toFixed(2)}%
                    </span>
                </div>
            ))}
        </div>
    );
}

function StockCard({ stock, onDelete, onStar, isStarred }: { stock: StockSignal, onDelete: () => void, onStar: () => void, isStarred: boolean }) {
    const sniper = stock.sniperSignals;
    const vwapControl = sniper?.vwap_control || 'NEUTRAL';
    const vwapDev = sniper?.vwap_deviation || 0;

    // 格式化功能
    const getFilterStatus = () => {
        if (vwapControl === 'LONG') return { icon: '🟢', text: '多方' };
        if (vwapControl === 'SHORT') return { icon: '🔴', text: '空方' };
        return { icon: '⚪', text: '盤整' };
    };

    const getChipStatus = () => {
        const net = stock.checks?.institutional?.total_net || 0;
        if (net > 0) return { icon: '🔥', text: '大戶吸' };
        if (net < 0) return { icon: '💧', text: '散戶進' };
        return { icon: '⚖️', text: '力道平' };
    };

    const filter = getFilterStatus();
    const chips = getChipStatus();
    const colorClass = stock.change >= 0 ? "text-red-600" : "text-green-600";

    return (
        <div className={cn("relative group p-6 border rounded-2xl bg-white transition-all shadow-sm hover:shadow-md border-slate-200", isStarred && "ring-2 ring-indigo-500/20 border-indigo-200")}>
            {/* Actions */}
            <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all z-10">
                <button onClick={(e) => { e.stopPropagation(); onStar(); }} className={cn("p-1.5 border rounded-lg transition-all", isStarred ? "bg-amber-50 border-amber-200 text-amber-500" : "bg-white border-slate-100 text-slate-300 hover:text-amber-400")}>
                    <Star className={cn("w-3.5 h-3.5", isStarred && "fill-amber-400")} />
                </button>
                <button onClick={(e) => { e.stopPropagation(); onDelete(); }} className="p-1.5 bg-white border border-slate-100 text-slate-300 hover:text-red-500 rounded-lg transition-all">
                    <Trash2 className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* Title: Name Code */}
            <div className="text-xl font-black text-slate-800 flex items-baseline gap-2 mb-1">
                {stock.name} <span className="text-sm font-mono text-slate-400">{stock.symbol}</span>
            </div>

            {/* Price Change */}
            <div className={cn("text-lg font-black font-mono mb-4", colorClass)}>
                {Number.isInteger(stock.price) ? stock.price : stock.price.toFixed(1)} {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(1)}%
            </div>

            {/* Content List as requested */}
            <div className="space-y-2 text-sm font-bold text-slate-700">
                <div className="flex items-center gap-2">
                    <span className="text-slate-400 min-w-[50px]">濾網:</span>
                    <span>{filter.icon} {filter.text}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-slate-400 min-w-[50px]">籌碼:</span>
                    <span>{chips.icon} {chips.text}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-slate-400 min-w-[50px]">VWAP:</span>
                    <span className="font-mono text-indigo-600">{stock.vwap.toFixed(1)}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-slate-400 min-w-[50px]">5分K值:</span>
                    <span className="font-mono">{sniper?.kd_k?.toFixed(0) || '--'} ({sniper?.kd_d?.toFixed(0) || '--'})</span>
                </div>
            </div>

            {/* Warnings / Special Status */}
            <div className="mt-4 pt-3 border-t border-slate-50 min-h-[40px]">
                {sniper?.is_divergence && (
                    <div className="text-xs font-black text-rose-600 flex items-center gap-1.5 animate-pulse">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        ⚠️ 頂部背離 (價漲標跌)
                    </div>
                )}
                {sniper?.status === 'PURPLE_LIGHT' && (
                    <div className="text-xs font-black text-purple-600 flex items-center gap-1.5">
                        <Zap className="w-3.5 h-3.5" />
                        ⚡ 爆量攻擊 (極強勢)
                    </div>
                )}
                {sniper?.status === 'GREEN_LIGHT' && (
                    <div className="text-xs font-black text-emerald-600 flex items-center gap-1.5">
                        <Target className="w-3.5 h-3.5" />
                        🎯 精準打擊 (支撐確認)
                    </div>
                )}
                {(!sniper?.is_divergence && sniper?.status === 'NEUTRAL') && (
                    <div className="text-[10px] font-bold text-slate-300 italic">穩健觀察中...</div>
                )}
            </div>
        </div>
    );
}

function AddStockModal({ onClose, onSuccess, currentWatchlist }: any) {
    const [symbol, setSymbol] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault(); if (!symbol || isSubmitting) return;
        setIsSubmitting(true);
        try {
            const newList = [...currentWatchlist, symbol];
            const res = await fetch(`http://${window.location.hostname}:8000/api/orb/watchlist`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ watchlist: newList })
            });
            if (res.ok) { onSuccess(); setSymbol(''); }
        } catch (e) { } finally { setIsSubmitting(false); }
    };
    return (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl animate-in zoom-in duration-200">
                <h2 className="text-2xl font-black mb-6 text-slate-800">新增監控標的</h2>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div><label className="block text-xs font-black text-slate-400 uppercase tracking-widest mb-2">股票代碼</label><input autoFocus type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="例如: 2330" className="w-full px-4 py-3 bg-slate-50 border border-slate-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 font-bold" /></div>
                    <div className="flex gap-3 pt-4"><button type="button" onClick={onClose} className="flex-1 py-3 bg-slate-100 text-slate-600 font-bold rounded-xl hover:bg-slate-200">取消</button><button type="submit" disabled={isSubmitting} className="flex-1 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 disabled:opacity-50">確認新增</button></div>
                </form>
            </div>
        </div>
    );
}
