"use client";

import { TrendingUp, TrendingDown, Activity, Brain, AlertCircle, BarChart3, RefreshCw, Wifi, Search, Trash2, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { entryCheckApi } from '@/lib/api-client';
import type { DipAnalysis } from '@/types/analysis';

interface StockQuote {
    symbol: string;
    price: number;
    open?: number;
    high?: number;
    low?: number;
    volume?: number;
    bid?: number;
    ask?: number;
    change?: number;
    source?: string;
    time?: string;
}

// 股票名稱對照
const STOCK_NAMES: Record<string, string> = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2409": "友達",
    "6669": "緯穎", "3443": "創意", "2308": "台達電", "2382": "廣達"
};

export default function DashboardPage() {
    const [quotes, setQuotes] = useState<StockQuote[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isConnected, setIsConnected] = useState(false);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
    const [dataSource, setDataSource] = useState<string>('');
    const [watchlist, setWatchlist] = useState<string[]>([]);
    const [newSymbol, setNewSymbol] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // 低點分析數據
    const [dipResults, setDipResults] = useState<Record<string, DipAnalysis>>({});
    const [isScanningDip, setIsScanningDip] = useState(false);

    // 獲取用戶資料與監控清單
    const fetchUserPreferences = useCallback(async () => {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        try {
            const response = await fetch('http://localhost:8000/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            if (data.success && data.user.settings) {
                const userWatchlist = data.user.settings.watchlist || [];
                // 如果用戶清單為空，使用預設清單
                if (userWatchlist.length === 0) {
                    const defaultList = ["2330", "2454", "2317", "2308"];
                    setWatchlist(defaultList);
                    saveWatchlist(defaultList);
                } else {
                    setWatchlist(userWatchlist);
                }
            }
        } catch (error) {
            console.error('獲取用戶設定失敗:', error);
        }
    }, []);

    // 保存監控清單至後端
    const saveWatchlist = async (newList: string[]) => {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        setIsSaving(true);
        try {
            await fetch('http://localhost:8000/api/auth/settings', {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ watchlist: newList })
            });
        } catch (error) {
            console.error('同步清單失敗:', error);
        } finally {
            setIsSaving(false);
        }
    };

    // 獲取報價數據
    const fetchQuotes = useCallback(async () => {
        if (watchlist.length === 0) return;

        try {
            const symbolsParam = watchlist.join(',');
            const response = await fetch(`http://localhost:8000/api/fubon/quotes?symbols=${symbolsParam}`);
            const data = await response.json();

            if (data.quotes) {
                setQuotes(data.quotes);
                setLastUpdate(new Date());
                const source = data.quotes[0]?.source || 'unknown';
                setDataSource(source);
                setIsConnected(source === 'fubon');
            }
        } catch (error) {
            console.error('獲取報價失敗:', error);
            setIsConnected(false);
        } finally {
            setIsLoading(false);
        }
    }, [watchlist]);

    // 添加股票至清單
    const handleAddStock = (e: React.FormEvent) => {
        e.preventDefault();
        if (!newSymbol) return;

        const symbol = newSymbol.trim();
        if (watchlist.includes(symbol)) {
            setNewSymbol('');
            return;
        }

        const newList = [...watchlist, symbol];
        setWatchlist(newList);
        setNewSymbol('');
        saveWatchlist(newList);
    };

    // 從清單移除股票
    const handleRemoveStock = (symbol: string) => {
        const newList = watchlist.filter(s => s !== symbol);
        setWatchlist(newList);
        saveWatchlist(newList);
    };

    // 初始加載
    useEffect(() => {
        fetchUserPreferences();
    }, [fetchUserPreferences]);

    // 掃描低點機會
    const scanDipOpportunities = useCallback(async () => {
        if (watchlist.length === 0) return;

        setIsScanningDip(true);
        const results: Record<string, DipAnalysis> = {};

        try {
            // 對每支監控清單中的股票執行快速檢查
            await Promise.all(watchlist.map(async (symbol) => {
                try {
                    const res = await entryCheckApi.quickCheck(symbol);
                    if (res?.checks?.dip_analysis) {
                        results[symbol] = res.checks.dip_analysis;
                    }
                } catch (e) {
                    console.error(`掃描 ${symbol} 低點失敗:`, e);
                }
            }));
            setDipResults(results);
        } finally {
            setIsScanningDip(false);
        }
    }, [watchlist]);

    // 自動刷新報價與低點分析
    useEffect(() => {
        if (watchlist.length > 0) {
            fetchQuotes();
            scanDipOpportunities(); // 啟動時掃描一次

            const quoteInterval = setInterval(fetchQuotes, 15000);
            const dipInterval = setInterval(scanDipOpportunities, 60000); // 每分鐘掃描一次止跌品質

            return () => {
                clearInterval(quoteInterval);
                clearInterval(dipInterval);
            };
        }
    }, [fetchQuotes, scanDipOpportunities, watchlist]);

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">主儀表板</h1>
                    <p className="text-gray-600 mt-2">
                        歡迎回來，已加載您的個人監控清單
                        {isSaving && <span className="ml-2 text-xs text-blue-500 animate-pulse">(同步中...)</span>}
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <form onSubmit={handleAddStock} className="flex items-center gap-2">
                        <input
                            type="text"
                            placeholder="輸入代碼 (如 2330)"
                            value={newSymbol}
                            onChange={(e) => setNewSymbol(e.target.value)}
                            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none w-32"
                        />
                        <button
                            type="submit"
                            className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-700"
                        >
                            加入清單
                        </button>
                    </form>
                    <div className="h-6 w-px bg-gray-200 mx-1"></div>
                    <div className={cn(
                        "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium",
                        isConnected ? "bg-green-50 text-green-700 border border-green-100" : "bg-yellow-50 text-yellow-700 border border-yellow-100"
                    )}>
                        <Activity className="w-4 h-4" />
                        {isConnected ? '即時' : '延遲'}
                    </div>
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    title="監控中"
                    value={String(watchlist.length)}
                    change={0}
                    icon={<Activity className="w-6 h-6" />}
                    color="blue"
                />
                <MetricCard
                    title="本日上漲"
                    value={String(quotes.filter(q => (q.change || 0) > 0).length)}
                    change={0}
                    icon={<TrendingUp className="w-6 h-6" />}
                    color="green"
                />
                <MetricCard
                    title="本日下跌"
                    value={String(quotes.filter(q => (q.change || 0) < 0).length)}
                    change={0}
                    icon={<TrendingDown className="w-6 h-6" />}
                    color="red"
                />
                <MetricCard
                    title="系統狀態"
                    value={isConnected ? "優良" : "正常"}
                    change={0}
                    icon={<Wifi className="w-6 h-6" />}
                    color="purple"
                />
            </div>

            {/* 🔥 低點買進偵測 (Buy on Dip) */}
            {Object.keys(dipResults).some(s => dipResults[s].score >= 65) && (
                <div className="bg-gradient-to-r from-red-600 to-orange-500 rounded-xl p-0.5 shadow-lg animate-pulse-slow">
                    <div className="bg-white rounded-[10px] p-4">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <div className="p-2 bg-red-100 rounded-lg">
                                    <TrendingUp className="w-5 h-5 text-red-600" />
                                </div>
                                <div>
                                    <h2 className="text-lg font-bold text-gray-900">低點買進機會偵測</h2>
                                    <p className="text-xs text-gray-500">基於量縮、均線支撐與指標反轉的 7 維度評估</p>
                                </div>
                            </div>
                            <button onClick={scanDipOpportunities} className="text-xs text-blue-600 font-bold hover:underline flex items-center gap-1">
                                <RefreshCw className={cn("w-3 h-3", isScanningDip && "animate-spin")} />
                                立即重新掃描
                            </button>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {Object.entries(dipResults)
                                .filter(([_, res]) => res.score >= 65)
                                .sort((a, b) => b[1].score - a[1].score)
                                .map(([symbol, res]) => (
                                    <Link key={symbol} href={`/dashboard/stock-analysis?symbol=${symbol}`}>
                                        <div className="flex items-center justify-between p-3 bg-red-50 hover:bg-red-100 rounded-xl border border-red-100 transition-all cursor-pointer group">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center font-bold text-red-600 shadow-sm">
                                                    {symbol}
                                                </div>
                                                <div>
                                                    <div className="font-bold text-gray-900 text-sm">{STOCK_NAMES[symbol] || symbol}</div>
                                                    <div className="text-[10px] text-red-600 font-bold flex items-center gap-1">
                                                        {res.quality} ({res.score}分)
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-xs font-bold text-gray-400">信心度</div>
                                                <div className="text-sm font-black text-red-700">{res.confidence}%</div>
                                            </div>
                                        </div>
                                    </Link>
                                ))
                            }
                        </div>
                    </div>
                </div>
            )}

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                        <div className="p-5 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
                            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                <BarChart3 className="w-5 h-5 text-blue-600" />
                                我的監控清單
                            </h2>
                            <span className="text-xs text-gray-400 font-medium">最後更新: {lastUpdate?.toLocaleTimeString('zh-TW') || '--:--'}</span>
                        </div>
                        <div className="p-4">
                            {isLoading && watchlist.length > 0 ? (
                                <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                                    <RefreshCw className="w-8 h-8 animate-spin mb-3 text-blue-200" />
                                    <p className="text-sm font-medium">正在取得即時報價...</p>
                                </div>
                            ) : watchlist.length === 0 ? (
                                <div className="text-center py-12 text-gray-400 border-2 border-dashed border-gray-100 rounded-xl">
                                    <div className="bg-gray-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
                                        <Search className="w-6 h-6" />
                                    </div>
                                    <p className="text-sm font-medium">尚未添加股票</p>
                                    <p className="text-xs mt-1">在上方輸入代碼開始監控</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 gap-3">
                                    {quotes.map((quote) => (
                                        <StockListItem
                                            key={quote.symbol}
                                            symbol={quote.symbol}
                                            name={STOCK_NAMES[quote.symbol] || `股票 ${quote.symbol}`}
                                            price={quote.price}
                                            change={quote.change || 0}
                                            bid={quote.bid}
                                            ask={quote.ask}
                                            dipQuality={dipResults[quote.symbol]?.quality}
                                            dipScore={dipResults[quote.symbol]?.score}
                                            source={quote.source}
                                            time={quote.time}
                                            onRemove={() => handleRemoveStock(quote.symbol)}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-red-500" />
                            市場大盤
                        </h2>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <MarketIndexCard name="加權指數" value="23,456" change={-0.8} />
                            <MarketIndexCard name="台指期" value="23,480" change={-1.1} />
                            <MarketIndexCard name="NASDAQ" value="15,234" change={0.4} />
                            <MarketIndexCard name="費城半導體" value="4,820" change={1.2} />
                        </div>
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                        <h2 className="text-lg font-bold text-gray-900 mb-4">快速捷徑</h2>
                        <div className="grid grid-cols-1 gap-2">
                            <QuickLink href="/dashboard/smart-picks" icon={<Brain />} label="🤖 AI 智慧選股" />
                            <QuickLink href="/dashboard/lstm" icon={<Brain />} label="AI 預測" />
                            <QuickLink href="/dashboard/scanner" icon={<Search />} label="選股掃描" />
                            <QuickLink href="/dashboard/mainforce" icon={<TrendingUp />} label="主力追蹤" />
                            <QuickLink href="/dashboard/alerts" icon={<AlertCircle />} label="警報設定" />
                        </div>
                    </div>

                    <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl p-6 text-white shadow-lg shadow-blue-200">
                        <div className="flex items-center gap-2 mb-4">
                            <Brain className="w-6 h-6" />
                            <h3 className="font-bold">AI 智慧小幫手</h3>
                        </div>
                        <p className="text-sm text-blue-100 leading-relaxed mb-4">
                            目前的市場呈現震盪格局，建議關注「主力持續買超」且「LSTM 預測向上」的標的。
                        </p>
                        <Link
                            href="/dashboard/ai-report"
                            className="block w-full py-2.5 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-bold transition-all border border-white/20 text-center"
                        >
                            查看 AI 深度分析匯報
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}

// 快速鏈接組件
function QuickLink({ href, icon, label }: { href: string, icon: React.ReactNode, label: string }) {
    return (
        <Link href={href} className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-all border border-transparent hover:border-gray-100">
            <div className="text-blue-600">{icon}</div>
            <span className="text-sm font-bold text-gray-700">{label}</span>
        </Link>
    );
}

// 股票列表項目組件
function StockListItem({
    symbol,
    name,
    price,
    change,
    bid,
    ask,
    dipQuality,
    dipScore,
    source,
    time,
    onRemove
}: {
    symbol: string;
    name: string;
    price: number;
    change: number;
    bid?: number;
    ask?: number;
    dipQuality?: string;
    dipScore?: number;
    source?: string;
    time?: string;
    onRemove: () => void;
}) {
    const isUp = change >= 0;

    // 定義止跌標籤樣式
    const getDipBadge = (quality: string | undefined, score: number | undefined) => {
        if (!quality || !score) return null;
        if (score < 45) return null; // 體現不強就不顯示

        let colors = "bg-gray-100 text-gray-600";
        if (quality === '強力反彈訊號') colors = "bg-red-100 text-red-600 border border-red-200 animate-pulse-slow";
        if (quality === '止跌確認') colors = "bg-orange-100 text-orange-600 border border-orange-200";
        if (quality === '支撐測試中') colors = "bg-blue-100 text-blue-600 border border-blue-200";

        return (
            <div className={cn("px-2 py-0.5 rounded text-[10px] font-black uppercase flex items-center gap-1", colors)}>
                <CheckCircle2 className="w-3 h-3" />
                {quality}
            </div>
        );
    };

    return (
        <div className="group flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-white hover:shadow-md transition-all border border-transparent hover:border-gray-100">
            <Link
                href={`/dashboard/chart?symbol=${symbol}`}
                className="flex items-center gap-4 flex-1 cursor-pointer"
            >
                <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center shadow-sm border border-gray-100 font-bold text-blue-600 text-sm hover:bg-blue-50 hover:border-blue-200 transition-colors">
                    {symbol}
                </div>
                <div>
                    <div className="flex items-center gap-2">
                        <div className="font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                            {name}
                        </div>
                        {getDipBadge(dipQuality, dipScore)}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider font-bold text-gray-400 mt-0.5">
                        {source === 'fubon' ? (
                            <span className="text-green-600 flex items-center gap-1">
                                <span className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
                                REALTIME {time}
                            </span>
                        ) : (
                            <span>Yahoo Finance Data</span>
                        )}
                    </div>
                </div>
            </Link>

            <div className="flex items-center gap-4">
                <div className="text-right">
                    <div className={cn(
                        "text-lg font-black tabular-nums",
                        isUp ? "text-red-600" : "text-green-600"
                    )}>
                        ${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                    <div className={cn(
                        "text-[11px] font-bold flex items-center justify-end gap-0.5",
                        isUp ? "text-red-500" : "text-green-500"
                    )}>
                        {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {isUp ? '+' : ''}{change.toFixed(2)}%
                    </div>
                </div>

                <Link
                    href={`/dashboard/chart?symbol=${symbol}`}
                    className="p-2 text-gray-300 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                    title="查看 K 線圖"
                >
                    <BarChart3 className="w-4 h-4" />
                </Link>

                <button
                    onClick={(e) => {
                        e.preventDefault();
                        onRemove();
                    }}
                    className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                    title="移除此股票"
                >
                    <Trash2 className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}

// Metric Card Component
function MetricCard({
    title,
    value,
    change,
    icon,
    color,
}: {
    title: string;
    value: string;
    change: number;
    icon: React.ReactNode;
    color: 'green' | 'blue' | 'purple' | 'orange' | 'red';
}) {
    const colorClasses = {
        green: 'bg-green-100 text-green-600',
        blue: 'bg-blue-100 text-blue-600',
        purple: 'bg-purple-100 text-purple-600',
        orange: 'bg-orange-100 text-orange-600',
        red: 'bg-red-100 text-red-600',
    };

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
                <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
                    {icon}
                </div>
                {change !== 0 && (
                    <span className={`text-sm font-medium ${change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {change > 0 ? '+' : ''}{change}
                    </span>
                )}
            </div>
            <div className="mt-4">
                <h3 className="text-gray-600 text-sm">{title}</h3>
                <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
            </div>
        </div>
    );
}

// Market Index Card Component
function MarketIndexCard({ name, value, change }: { name: string; value: string; change: number }) {
    return (
        <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600">{name}</div>
            <div className="text-xl font-bold text-gray-900">{value}</div>
            <div className={`text-sm ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {change >= 0 ? '+' : ''}{change}%
            </div>
        </div>
    );
}

// Quick Action Button Component
function QuickActionButton({
    href,
    icon,
    label,
    description,
}: {
    href: string;
    icon: React.ReactNode;
    label: string;
    description: string;
}) {
    return (
        <Link
            href={href}
            className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg hover:bg-blue-50 transition-colors group"
        >
            <div className="p-2 bg-blue-100 rounded-lg text-blue-600 group-hover:bg-blue-200">
                {icon}
            </div>
            <div>
                <div className="font-medium text-gray-900">{label}</div>
                <div className="text-sm text-gray-500">{description}</div>
            </div>
        </Link>
    );
}
