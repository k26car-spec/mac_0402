'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, Plus } from 'lucide-react';
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
        institutional?: {
            total_net: number;
        };
        [key: string]: any;
    };
}

// 股票分類定義 (與 ORB Watchlist 一致)
const STOCK_CATEGORIES = {
    'AI_SEMI': {
        title: '🤖 AI / 半導體',
        codes: ['2330', '2317', '3231', '2382', '2303', '3706', '2371', '2312', '6770',
            '2449', '6257', '6239', '3265', '8150', '2301', '3017',
            '3661', '3443', '6669', '2356', '2357', '6176', '3529', '3693', '3035', '3533', '5274']
    },
    'SATELLITE': {
        title: '📡 網通 / 衛星',
        codes: ['2313', '2314', '6285', '3163', '3363', '2412',
            '3491', '5388', '3062', '4979', '6442', '6426', '4909']
    },
    'MEMORY': {
        title: '💾 記憶體',
        codes: ['2337', '2344', '2408', '8299', '3260', '2451', '3006', '3257']
    },
    'IC_DESIGN': {
        title: '✨ IC 設計',
        codes: ['2454', '3034', '2379', '3008', '5269', '4966', '6643', '6531', '6533', '8081']
    },
    'PCB': {
        title: '🔌 PCB / 零組件',
        codes: ['3037', '8046', '3189', '2367', '6153', '8074', '8155', '5498', '1815',
            '3481', '2327', '6282', '1605', '2409', '6116']
    },
    'TRADITIONAL': {
        title: '🚢 傳產 / 金融',
        codes: ['2609', '2618', '2881', '1301', '1326', '1303', '5521', '8422', '1802',
            '2603', '2615', '2637', '2882', '2891', '2884', '2892', '2002', '1101', '2912', '9910']
    }
};

// 根據股票代碼判斷分類
const getStockCategory = (symbol: string): string => {
    const cleanSymbol = symbol.replace('.TW', '').replace('.TWO', '');
    for (const [key, category] of Object.entries(STOCK_CATEGORIES)) {
        if (category.codes.includes(cleanSymbol)) {
            return key;
        }
    }
    return 'OTHER';
};

export default function SniperPage() {
    const [signals, setSignals] = useState<StockSignal[]>([]);
    const [sectorWatchlists, setSectorWatchlists] = useState<Record<string, SectorInfo>>({});
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [starredStocks, setStarredStocks] = useState<Set<string>>(new Set());
    const [isConnected, setIsConnected] = useState(false);
    const [connStatus, setConnStatus] = useState({ connected: false, source: 'loading' });
    const [lastPriceUpdate, setLastPriceUpdate] = useState<Date | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const prevGreenHighRef = useRef<Set<string>>(new Set());

    // UI 狀態
    const [activeSector, setActiveSector] = useState<string>('AI_SEMI');
    const [showAddStock, setShowAddStock] = useState(false);
    const [isTabVisible, setIsTabVisible] = useState(true);

    // 監聽頁面可見性變化
    useEffect(() => {
        const handleVisibilityChange = () => {
            setIsTabVisible(!document.hidden);
        };
        document.addEventListener('visibilitychange', handleVisibilityChange);
        return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
    }, []);

    // 同態獲取 API 路徑
    const getApiUrl = (path: string) => {
        return `http://127.0.0.1:8000${path}`;
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

    // 核心：從 ORB Watchlist 獲取標的並分類
    const loadConfig = useCallback(async () => {
        try {
            setError(null);
            const res = await fetch(`http://127.0.0.1:8000/api/orb/watchlist`);
            if (res.ok) {
                const data = await res.json();
                if (data.watchlist && Array.isArray(data.watchlist)) {
                    setIsConnected(true);

                    // 按分類組織股票
                    const sectors: Record<string, SectorInfo> = {};

                    Object.entries(STOCK_CATEGORIES).forEach(([key, category]) => {
                        const stocksInCategory = data.watchlist.filter((symbol: string) =>
                            category.codes.includes(symbol.replace('.TW', '').replace('.TWO', ''))
                        );
                        if (stocksInCategory.length > 0) {
                            sectors[key] = {
                                name: category.title,
                                emoji: category.title.split(' ')[0],
                                stocks: stocksInCategory
                            };
                        }
                    });

                    // 其他未分類的股票
                    const categorizedSymbols = new Set(
                        Object.values(STOCK_CATEGORIES).flatMap(c => c.codes)
                    );
                    const otherStocks = data.watchlist.filter((symbol: string) =>
                        !categorizedSymbols.has(symbol.replace('.TW', '').replace('.TWO', ''))
                    );
                    if (otherStocks.length > 0) {
                        sectors['OTHER'] = {
                            name: '📁 其他',
                            emoji: '📁',
                            stocks: otherStocks
                        };
                    }

                    setSectorWatchlists(sectors);

                    // 🆕 預載所有數據（一次性載入，後續切換無需等待）
                    loadAllSignals(sectors);
                    return sectors;
                }
            }
            return null;
        } catch (err) {
            console.error("Config load error:", err);
            return null;
        }
    }, [activeSector]);

    // 只載入特定分類的訊號 (減輕流量)
    const loadSignalsForSector = useCallback(async (sector: string, sectorsInput?: Record<string, SectorInfo>) => {
        const sectors = sectorsInput || sectorWatchlists;
        const sectorInfo = sectors[sector];

        if (!sectorInfo || sectorInfo.stocks.length === 0) {
            setIsLoading(false);
            return;
        }

        if (abortControllerRef.current) abortControllerRef.current.abort();
        abortControllerRef.current = new AbortController();

        try {
            setIsLoading(true);
            const res = await fetch(getApiUrl('/api/entry-check/batch-details'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbols: sectorInfo.stocks }),
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
                        sector: sector,
                        signalType: r.should_enter ? 'BUY' : 'WAIT',
                        signalText: r.recommended_action,
                        confidence: r.confidence,
                        foreignNet: r.checks?.institutional?.total_net || 0,
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

    // 完整載入所有訊號 (用於初始化或手動刷新)
    const loadAllSignals = useCallback(async (sectorsInput?: Record<string, SectorInfo>) => {
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
                        sector: getStockCategory(r.symbol),
                        signalType: r.should_enter ? 'BUY' : 'WAIT',
                        signalText: r.recommended_action,
                        confidence: r.confidence,
                        foreignNet: r.checks?.institutional?.total_net || 0,
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

    // 🆕 快速股價更新（每 3 秒直接從富邦 API 拉最新價，不做複雜分析）
    const fetchLivePrices = useCallback(async () => {
        if (!isTabVisible) return;
        // 取當前頁所有股票代碼
        const allSymbols = Object.values(sectorWatchlists).flatMap(s => s.stocks);
        if (allSymbols.length === 0) return;

        try {
            const symbolsParam = allSymbols.map(s => s.replace('.TW', '').replace('.TWO', '')).join(',');
            const res = await fetch(`http://127.0.0.1:8000/api/fubon/quotes?symbols=${symbolsParam}`);
            if (!res.ok) return;
            const data = await res.json();
            const quotesMap: Record<string, { price: number, change: number, source?: string }> = {};
            (data.quotes || []).forEach((q: any) => {
                const code = q.symbol?.replace('.TW', '').replace('.TWO', '') || q.symbol;
                quotesMap[code] = {
                    price: q.price || 0,
                    change: q.change || 0,
                    source: q.source
                };
            });

            // 僅更新股價欄位，不觸動 AI 訊號
            setSignals(prev => prev.map(sig => {
                const code = sig.symbol.replace('.TW', '').replace('.TWO', '');
                const live = quotesMap[code];
                if (live && live.price > 0) {
                    return { ...sig, price: live.price, change: live.change };
                }
                return sig;
            }));
            setLastPriceUpdate(new Date());
            setIsConnected(true);
        } catch (e) {
            // 靜默失敗，不影響畫面
        }
    }, [isTabVisible, sectorWatchlists]);

    useEffect(() => {
        fetchConnStatus();
        loadConfig(); // Initial load

        // 🔴 快速股價輪詢：每 3 秒更新一次（富邦 REST API）
        const priceInterval = setInterval(() => {
            fetchLivePrices();
        }, 3000);

        // 🟡 AI 訊號分析：每 60 秒完整運算一次（含 KD/VWAP/籌碼）
        const signalInterval = setInterval(() => {
            if (isTabVisible && Object.keys(sectorWatchlists).length > 0) {
                loadAllSignals(); // 背景更新全部數據
            }
        }, 60000);

        const statusInterval = setInterval(() => fetchConnStatus(), 30000);
        const configInterval = setInterval(() => loadConfig(), 300000); // Sync config every 5 mins

        return () => {
            clearInterval(priceInterval);
            clearInterval(signalInterval);
            clearInterval(statusInterval);
            clearInterval(configInterval);
        };
    }, [loadConfig, fetchConnStatus, fetchLivePrices, activeSector, isTabVisible]);

    // 🆕 切換分頁時無需重新載入，直接從快取篩選（即時切換）

    // 生成分頁標籤
    const tabs = Object.entries(sectorWatchlists).map(([key, info]) => ({
        id: key,
        label: info.name,
        count: info.stocks.length
    }));

    // 當前分頁的訊號
    const currentSignals = signals.filter(s => s.sector === activeSector);

    return (
        <div className="min-h-screen p-6 font-sans bg-[#0E1117] text-[#FAFAFA]">
            <style jsx global>{`
                /* --- 關鍵動畫：紅色危險閃爍 (KD背離) --- */
                @keyframes blink-red {
                    0% { background-color: rgba(60, 20, 20, 1); box-shadow: 0 0 0px red; border-color: #500; }
                    50% { background-color: rgba(120, 30, 30, 1); box-shadow: 0 0 15px red; border-color: red; }
                    100% { background-color: rgba(60, 20, 20, 1); box-shadow: 0 0 0px red; border-color: #500; }
                }

                /* --- 關鍵動畫：綠色買進訊號 (回測支撐) --- */
                @keyframes pulse-green {
                    0% { box-shadow: 0 0 0 0 rgba(0, 255, 100, 0.4); border-color: #43A047;}
                    70% { box-shadow: 0 0 0 10px rgba(0, 255, 100, 0); border-color: #00E676;}
                    100% { box-shadow: 0 0 0 0 rgba(0, 255, 100, 0); border-color: #43A047;}
                }

                .status-danger {
                    color: #FFCDD2;
                    animation: blink-red 1.5s infinite;
                    border: 1px solid red;
                    background-color: rgba(120, 30, 30, 0.5);
                }

                .status-buy {
                    background-color: #1B5E20;
                    color: #C8E6C9;
                    border: 1px solid #43A047;
                    animation: pulse-green 2s infinite;
                }

                .status-wait {
                    background-color: #262626;
                    color: #777;
                    border: 1px dashed #444;
                }
                
                .text-up { color: #FF4B4B; }
                .text-down { color: #00FF00; }
                .text-neutral { color: #888; }
            `}</style>

            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-3xl font-bold">🛡️ 戰術操盤中控台 <span className="text-xs bg-green-600 px-2 py-1 rounded">V2.0 分類版</span></h1>
                    <p className="text-gray-400 text-sm mt-1">
                        5分K 雙重背離濾網 + VWAP 趨勢監控
                        <span className="ml-3 text-xs">
                            {lastPriceUpdate ? (
                                <span className="text-green-400">● 股價已即時更新 {lastPriceUpdate.toLocaleTimeString('zh-TW')}</span>
                            ) : (
                                <span className="text-yellow-400">◌ 等待股價...</span>
                            )}
                        </span>
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setShowAddStock(true)}
                        className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded shadow transition flex items-center border border-gray-700"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        新增標的
                    </button>
                    <button
                        onClick={() => loadConfig().then(s => s && loadAllSignals(s))}
                        className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded shadow transition flex items-center"
                    >
                        <RefreshCw className={cn("w-4 h-4 mr-2", isLoading && "animate-spin")} />
                        {isLoading ? '更新中...' : '刷新報價'}
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-700 mb-6 overflow-x-auto">
                {tabs.map(tab => (
                    <div
                        key={tab.id}
                        className={cn(
                            "px-5 py-2.5 cursor-pointer border-b-2 transition-all text-sm font-medium whitespace-nowrap",
                            activeSector === tab.id
                                ? "text-white border-[#FF4B4B] font-bold"
                                : "text-gray-500 border-transparent hover:text-gray-300"
                        )}
                        onClick={() => setActiveSector(tab.id)}
                    >
                        {tab.label} <span className="text-xs opacity-60">({tab.count})</span>
                    </div>
                ))}
            </div>

            {/* Grid Container */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {currentSignals.map((stock) => (
                    <TacticalCard
                        key={stock.symbol}
                        stock={stock}
                    />
                ))}
            </div>

            {currentSignals.length === 0 && !isLoading && (
                <div className="text-center py-20 text-gray-500 border-2 border-dashed border-gray-800 rounded-xl">
                    <p className="text-xl font-bold">此分類尚無監控標的</p>
                    <p className="mt-2 text-sm">請切換其他分類或點擊「新增標的」</p>
                </div>
            )}

            {/* Legend & Strategy Details */}
            <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="p-6 bg-[#0E1117] rounded-lg border border-gray-800">
                    <h3 className="text-lg font-bold mb-4 text-white flex items-center">
                        <span className="bg-yellow-500 w-2 h-6 mr-3 rounded-sm"></span>
                        訊號偵測與定義
                    </h3>
                    <div className="space-y-4 text-sm text-gray-400">
                        <div className="bg-[#18181b] p-3 rounded border border-gray-800 flex items-start">
                            <div className="w-3 h-3 rounded-full bg-red-500 mt-1 mr-3 shrink-0 shadow-[0_0_10px_red]"></div>
                            <div>
                                <span className="text-white font-bold text-base">⚠️ 紅燈警示 (Danger)</span>
                                <div className="mt-1 text-gray-400">頂部背離偵測：價創高但 KD 指標未創高</div>
                                <ul className="mt-2 text-xs text-gray-500 list-disc ml-4 space-y-1">
                                    <li>條件一：收盤價 &gt;= 20日布林上軌</li>
                                    <li>條件二：KD指標高檔鈍化或背離 (K &lt; 80 但 價創新高)</li>
                                    <li><span className="text-red-400 font-bold">動作：</span>禁止追價，跌破 5MA 或爆大量收黑即刻停利。</li>
                                </ul>
                            </div>
                        </div>

                        <div className="bg-[#18181b] p-3 rounded border border-gray-800 flex items-start">
                            <div className="w-3 h-3 rounded-full bg-green-500 mt-1 mr-3 shrink-0 shadow-[0_0_10px_#00E676]"></div>
                            <div>
                                <span className="text-white font-bold text-base">✅ 綠燈買訊 (Buy)</span>
                                <div className="mt-1 text-gray-400">趨勢回測支撐：多頭排列回測 VWAP 或 MA</div>
                                <ul className="mt-2 text-xs text-gray-500 list-disc ml-4 space-y-1">
                                    <li>條件一：股價位於 VWAP 之上 (多方趨勢)</li>
                                    <li>條件二：KD 指標低檔黃金交叉 (K &lt; 30 且 K &gt; D)</li>
                                    <li><span className="text-green-400 font-bold">動作：</span>分批佈局，停損設前低或跌破 VWAP 2%。</li>
                                </ul>
                            </div>
                        </div>

                        <div className="bg-[#18181b] p-3 rounded border border-gray-800 flex items-start">
                            <div className="w-3 h-3 rounded-full bg-purple-500 mt-1 mr-3 shrink-0 shadow-[0_0_10px_#D500F9]"></div>
                            <div>
                                <span className="text-white font-bold text-base">⚡ 爆量攻擊 (Momentum)</span>
                                <div className="mt-1 text-gray-400">極強勢動能：開盤爆量或盤中突破</div>
                                <ul className="mt-2 text-xs text-gray-500 list-disc ml-4 space-y-1">
                                    <li>條件一：預估成交量 &gt; 5日均量 2倍</li>
                                    <li>條件二：漲幅 &gt; 3% 且 大戶籌碼集中</li>
                                    <li><span className="text-purple-400 font-bold">動作：</span>積極追價，設移動停利 (守爆量低點)。</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="p-6 bg-[#0E1117] rounded-lg border border-gray-800">
                    <h3 className="text-lg font-bold mb-4 text-white flex items-center">
                        <span className="bg-blue-500 w-2 h-6 mr-3 rounded-sm"></span>
                        AI 戰術濾網說明
                    </h3>
                    <div className="space-y-4">
                        <div className="border-l-2 border-gray-700 pl-4 py-1">
                            <h4 className="text-white font-bold text-sm">籌碼濾網 (Chip Filter)</h4>
                            <p className="text-xs text-gray-400 mt-1">
                                即時計算外資與投信的主動買盤。若<span className="text-yellow-400">大戶吸</span>且股價在 VWAP 之上，表主力護盤，下跌為買點；若<span className="text-green-400">大戶拋</span>，則反彈皆為逃命波。
                            </p>
                        </div>
                        <div className="border-l-2 border-gray-700 pl-4 py-1">
                            <h4 className="text-white font-bold text-sm">VWAP 均價防線</h4>
                            <p className="text-xs text-gray-400 mt-1">
                                成交量加權平均價 (VWAP) 是當日法人的成本線。
                                <br />• <span className="text-red-400">股價 &gt; VWAP</span>：多方控盤，只做多或空手。
                                <br />• <span className="text-green-400">股價 &lt; VWAP</span>：空方控盤，只做空或搶反彈。
                            </p>
                        </div>
                        <div className="border-l-2 border-gray-700 pl-4 py-1">
                            <h4 className="text-white font-bold text-sm">5分K KD 背離</h4>
                            <p className="text-xs text-gray-400 mt-1">
                                專門過濾「假突破」。當股價創新高，但 5分K 的 KD 指標卻沒有創新高 (例如前波 K值 85，這波只有 78)，通常預示著動能衰竭，為<span className="text-red-400">即將反轉</span>的強烈訊號。
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {showAddStock && (
                <AddStockModal
                    onClose={() => setShowAddStock(false)}
                    onSuccess={() => { setShowAddStock(false); loadConfig().then(s => s && loadAllSignals(s)); }}
                    currentWatchlist={signals.map(s => s.symbol)}
                />
            )}
        </div>
    );
}

function TacticalCard({ stock }: { stock: StockSignal }) {
    // 🔒 數據有效性檢查 - 防止誤判
    const isDataValid = (s: StockSignal): boolean => {
        // 檢查核心價格數據是否有效
        if (!s.price || s.price === 0) return false;
        // 檢查是否有基本的 VWAP 或 sniper 信號數據
        if (!s.vwap && !s.sniperSignals) return false;
        return true;
    };

    // Strategy Logic Mapping
    const analyzeStrategy = (s: StockSignal) => {
        // ⚠️ 數據驗證 - 如果數據無效，返回等待狀態
        if (!isDataValid(s)) {
            return {
                trend: "⏳ 等待",
                chip: "-- 查詢中",
                signalType: "loading",
                signalMsg: "⏳ 等待市場數據..."
            };
        }

        const vwap = s.vwap || s.price; // Fallback if 0
        const trend = s.price > vwap ? "🟢 多方" : "🔴 空方";
        const totalNet = s.foreignNet; // mapped from backend
        const chip = totalNet > 0 ? "🔥 大戶吸" : (totalNet < 0 ? "💸 大戶拋" : "⚖️ 觀望");

        // Signal Mapping
        let signalType = "wait";
        let signalMsg = "盤整觀望";

        // Map backend sniper signals to UI states
        if (s.sniperSignals?.is_divergence || s.sniperSignals?.status === 'RED_LIGHT') {
            signalType = "danger";
            signalMsg = "⚠️ 頂部背離 (價漲標跌)";
        } else if (s.sniperSignals?.status === 'GREEN_LIGHT' || (s.confidence > 80 && s.price > vwap)) {
            signalType = "buy";
            signalMsg = "✅ 趨勢低買 (KD翻揚)";
        } else if (s.sniperSignals?.status === 'PURPLE_LIGHT') {
            signalType = "buy"; // Purple acts as strong buy too
            signalMsg = "⚡ 爆量攻擊 (極強勢)";
        }

        return { trend, chip, signalType, signalMsg };
    };

    const analysis = analyzeStrategy(stock);
    const hasValidPrice = stock.price && stock.price !== 0;
    const colorClass = stock.change > 0 ? 'text-up' : (stock.change < 0 ? 'text-down' : 'text-neutral');
    const sign = stock.change > 0 ? '+' : '';

    // Dynamic Badge Class
    let badgeClass = 'status-wait';
    if (analysis.signalType === 'loading') badgeClass = 'bg-gray-700 text-gray-400 border-gray-600';
    else if (analysis.signalType === 'danger') badgeClass = 'status-danger';
    else if (analysis.signalType === 'buy') badgeClass = 'status-buy';

    return (
        <div className="bg-[#1E1E1E] border border-[#333] rounded-[10px] p-[15px] transition-transform duration-200 hover:-translate-y-[3px] hover:border-[#555] relative overflow-hidden group">
            <div className="flex justify-between items-end mb-2">
                <div>
                    <span className="text-xl font-bold text-gray-200 block">{stock.name || '查詢中...'}</span>
                    <span className="text-xs text-gray-500 font-mono">{stock.symbol}</span>
                </div>
                <div className={cn("text-2xl font-black font-mono", hasValidPrice ? colorClass : 'text-gray-600')}>
                    {hasValidPrice ? stock.price : '--'} {hasValidPrice && <span className="text-xs">{sign}{stock.change}%</span>}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-[5px] text-[0.85em] text-[#CCC] mt-[8px] pt-[8px] border-t border-[#333]">
                <div>濾網: {analysis.trend}</div>
                <div>籌碼: <span className="text-yellow-400">{analysis.chip}</span></div>
                <div>VWAP: <span className="font-mono">{hasValidPrice && stock.vwap ? stock.vwap.toFixed(1) : '--'}</span></div>
                <div>5分K值: <span className="font-mono">{stock.sniperSignals?.kd_k?.toFixed(0) || '--'}</span> <span className="text-gray-500 text-xs">({stock.sniperSignals?.kd_d?.toFixed(0) || '--'})</span></div>
            </div>

            <div className={cn("block text-center p-[8px] rounded-[6px] font-bold mt-[10px] text-[0.9em]", badgeClass)}>
                {analysis.signalMsg}
            </div>
        </div>
    );
}

function AddStockModal({ onClose, onSuccess, currentWatchlist }: any) {
    const [symbol, setSymbol] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Force 127.0.0.1
    const getApiUrl = (path: string) => `http://127.0.0.1:8000${path}`;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault(); if (!symbol || isSubmitting) return;
        setIsSubmitting(true);
        try {
            const newList = [...currentWatchlist, symbol];
            const res = await fetch(getApiUrl('/api/orb/watchlist'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ watchlist: newList })
            });
            if (res.ok) { onSuccess(); setSymbol(''); }
        } catch (e) { } finally { setIsSubmitting(false); }
    };
    return (
        <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-[#1E1E1E] border border-[#333] rounded-xl p-8 max-w-md w-full shadow-2xl">
                <h2 className="text-2xl font-black mb-6 text-white">新增監控標的</h2>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">股票代碼</label>
                        <input autoFocus type="text" value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="例如: 2330" className="w-full px-4 py-3 bg-[#0E1117] border border-[#333] text-white rounded-lg focus:outline-none focus:border-[#FF4B4B] font-bold" />
                    </div>
                    <div className="flex gap-3 pt-4">
                        <button type="button" onClick={onClose} className="flex-1 py-3 bg-[#333] text-gray-300 font-bold rounded-lg hover:bg-[#444]">取消</button>
                        <button type="submit" disabled={isSubmitting} className="flex-1 py-3 bg-[#FF4B4B] text-white font-bold rounded-lg hover:bg-red-600 disabled:opacity-50">確認新增</button>
                    </div>
                </form>
            </div>
        </div>
    );
}
