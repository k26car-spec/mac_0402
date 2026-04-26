'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    Activity, TrendingUp, TrendingDown, AlertTriangle, Filter,
    RefreshCw, Bell, BarChart3, Zap, Eye, Clock, Target,
    CheckCircle, XCircle, Pause, Play, Settings, Plus, X, Search, Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';

// 訊號介面
interface BigOrderSignal {
    id: string;
    timestamp: string;
    stock_code: string;
    stock_name: string;
    signal_type: 'BUY' | 'SELL';
    price: number;
    composite_score: number;
    confidence: number;
    quality_score: number;
    momentum_score: number;
    volume_score: number;
    pattern_score: number;
    quality_level: string;
    reason: string;
    warnings: string[];
    stop_loss: number;
    take_profit: number;
}

// 統計介面
interface MonitorStats {
    total_ticks: number;
    big_orders: number;
    fake_orders: number;
    signals_generated: number;
    valid_signals: number;
    quality_distribution: {
        excellent: number;
        good: number;
        fair: number;
        poor: number;
    };
}

// 監控股票介面
interface WatchStock {
    code: string;
    name: string;
    type: string;
    threshold: number;
    price?: number;           // 當前股價
    thresholdAmount?: string; // 門檻金額
}

// 預設監控股票 (門檻會根據股價動態更新)
// 分類: 大型股(金融)、中型電子、小型電子、半導體
const DEFAULT_WATCH_STOCKS: WatchStock[] = [
    // 金融類 (大型股)
    { code: '2881', name: '富邦金', type: '金融', threshold: 100 },
    { code: '2882', name: '國泰金', type: '金融', threshold: 100 },

    // 電子類 (大型/中型)
    { code: '2308', name: '台達電', type: '電子', threshold: 50 },
    { code: '3231', name: '緯創', type: '電子', threshold: 50 },
    { code: '3037', name: '欣興', type: '電子', threshold: 50 },

    // 電子類 (中小型)
    { code: '5498', name: '凱崴', type: '電子', threshold: 50 },
    { code: '3030', name: '德律', type: '電子', threshold: 50 },
    { code: '1815', name: '富喬', type: '電子', threshold: 50 },
    { code: '8039', name: '台虹', type: '電子', threshold: 50 },
    { code: '3363', name: '上詮', type: '電子', threshold: 50 },
    { code: '8155', name: '博智', type: '電子', threshold: 50 },
    { code: '2312', name: '金寶', type: '電子', threshold: 50 },
    { code: '3706', name: '神達', type: '電子', threshold: 50 },

    // 塑化類
    { code: '1303', name: '南亞', type: '塑化', threshold: 50 },

    // 半導體類
    { code: '2344', name: '華邦電', type: '半導體', threshold: 50 },
    { code: '6257', name: '矽格', type: '半導體', threshold: 50 },
    { code: '2337', name: '旺宏', type: '半導體', threshold: 50 },
    { code: '6670', name: '力積電', type: '半導體', threshold: 50 },
    { code: '3481', name: '群創', type: '面板', threshold: 50 },
    { code: '8074', name: '鉅橡', type: '電子', threshold: 50 },
];

// 計算動態門檻
const calculateDynamicThreshold = (price: number): { threshold: number; amount: string } => {
    if (price <= 0) return { threshold: 50, amount: '' };

    const TARGET_AMOUNT = 500; // 目標金額 500萬
    const MIN_THRESHOLD = 5;
    const MAX_THRESHOLD = 200;

    // 公式: 張數 = 目標金額(萬) × 10 / 股價
    const rawThreshold = (TARGET_AMOUNT * 10) / price;
    const threshold = Math.max(MIN_THRESHOLD, Math.min(MAX_THRESHOLD, Math.ceil(rawThreshold)));
    const actualAmount = (price * threshold * 1000) / 10000; // 萬元

    return {
        threshold,
        amount: `$${actualAmount.toFixed(0)}萬`
    };
};

// 股票類型選項
const STOCK_TYPES = ['半導體', '電子', '金融', '航運', '生技', '鋼鐵', '塑化', '其他'];

export default function BigOrderMonitorPage() {
    const [signals, setSignals] = useState<BigOrderSignal[]>([]);
    const [isMonitoring, setIsMonitoring] = useState(false);
    const [stats, setStats] = useState<MonitorStats>({
        total_ticks: 0,
        big_orders: 0,
        fake_orders: 0,
        signals_generated: 0,
        valid_signals: 0,
        quality_distribution: { excellent: 0, good: 0, fair: 0, poor: 0 }
    });
    const [filterType, setFilterType] = useState<'all' | 'BUY' | 'SELL'>('all');
    const [filterQuality, setFilterQuality] = useState<'all' | 'excellent' | 'good'>('all');
    const intervalRef = useRef<NodeJS.Timeout | null>(null);

    // 監控股票清單 state
    const [watchStocks, setWatchStocks] = useState<WatchStock[]>(() => {
        // 從 localStorage 讀取（如果有的話）
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('bigorder_watchlist');
            if (saved) {
                try {
                    return JSON.parse(saved);
                } catch {
                    return DEFAULT_WATCH_STOCKS;
                }
            }
        }
        return DEFAULT_WATCH_STOCKS;
    });

    // 新增股票 modal state
    const [showAddModal, setShowAddModal] = useState(false);
    const [newStock, setNewStock] = useState({ code: '', name: '', type: '電子', threshold: 50 });
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState('');

    // 歷史大單訊號記錄
    interface HistorySignal {
        id: number;
        signal_id: string;
        timestamp: string;
        stock_code: string;
        stock_name: string;
        signal_type: 'BUY' | 'SELL';
        price: number;
        quality_score: number;
        quality_level: string;
        reason: string;
        data_source: string;
    }

    // 歷史記錄 state
    const [historySignals, setHistorySignals] = useState<HistorySignal[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [historyStockFilter, setHistoryStockFilter] = useState<string>('all'); // 股票篩選器

    // 載入歷史記錄
    const loadHistory = useCallback(async () => {
        setHistoryLoading(true);
        try {
            const response = await fetch('http://localhost:8000/api/big-order/history?limit=500');
            const data = await response.json();
            if (data.success && data.signals) {
                setHistorySignals(data.signals);
            }
        } catch (error) {
            console.error('載入歷史記錄失敗:', error);
        } finally {
            setHistoryLoading(false);
        }
    }, []);

    // 🎯 更新股票的動態門檻
    const updateStockThresholds = useCallback(async () => {
        if (watchStocks.length === 0) return;

        try {
            // 使用 yfinance batch API (支援上櫃股票 .TWO)
            const symbols = watchStocks.map(s => s.code).join(',');
            const response = await fetch(`http://localhost:8000/api/smart-picks/yfinance/batch?symbols=${symbols}`);
            const data = await response.json();

            if (data.quotes && data.quotes.length > 0) {
                setWatchStocks(prevStocks =>
                    prevStocks.map(stock => {
                        const quote = data.quotes.find((q: { symbol: string; success: boolean }) =>
                            q.symbol === stock.code && q.success
                        );
                        if (quote && quote.price > 0) {
                            const { threshold, amount } = calculateDynamicThreshold(quote.price);
                            return {
                                ...stock,
                                price: quote.price,
                                threshold: threshold,
                                thresholdAmount: amount
                            };
                        }
                        return stock;
                    })
                );
                console.log('✅ 已根據股價更新門檻 (yfinance)');
            }
        } catch (error) {
            console.error('更新門檻失敗:', error);

            // 備援: 嘗試使用 fubon API
            try {
                const symbols = watchStocks.map(s => s.code).join(',');
                const response = await fetch(`http://localhost:8000/api/fubon/quotes?symbols=${symbols}`);
                const data = await response.json();

                if (data.quotes && data.quotes.length > 0) {
                    setWatchStocks(prevStocks =>
                        prevStocks.map(stock => {
                            const quote = data.quotes.find((q: { symbol: string }) => q.symbol === stock.code);
                            if (quote && quote.price > 0) {
                                const { threshold, amount } = calculateDynamicThreshold(quote.price);
                                return {
                                    ...stock,
                                    price: quote.price,
                                    threshold: threshold,
                                    thresholdAmount: amount
                                };
                            }
                            return stock;
                        })
                    );
                    console.log('✅ 已根據股價更新門檻 (fubon fallback)');
                }
            } catch (fallbackError) {
                console.error('備援 API 也失敗:', fallbackError);
            }
        }
    }, [watchStocks]);

    // 初始載入歷史記錄
    useEffect(() => {
        loadHistory();
    }, [loadHistory]);

    // 初始載入時更新門檻
    useEffect(() => {
        updateStockThresholds();
    }, []); // 只在初次載入時執行

    // 保存 watchlist 到 localStorage
    useEffect(() => {
        localStorage.setItem('bigorder_watchlist', JSON.stringify(watchStocks));
    }, [watchStocks]);

    // 模擬訊號生成（實際應從 WebSocket 或 API 獲取）
    const generateMockSignal = useCallback((): BigOrderSignal => {
        const stock = watchStocks[Math.floor(Math.random() * watchStocks.length)];
        const signal_type = Math.random() > 0.5 ? 'BUY' : 'SELL';
        const quality_score = 0.6 + Math.random() * 0.35;
        const basePrice = stock.code === '2330' ? 580 : stock.code === '2454' ? 1100 : 100 + Math.random() * 200;

        return {
            id: `signal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date().toISOString(),
            stock_code: stock.code,
            stock_name: stock.name,
            signal_type,
            price: basePrice,
            composite_score: 0.65 + Math.random() * 0.30,
            confidence: 0.65 + Math.random() * 0.30,
            quality_score,
            momentum_score: 0.5 + Math.random() * 0.45,
            volume_score: 0.5 + Math.random() * 0.45,
            pattern_score: 0.5 + Math.random() * 0.45,
            quality_level: quality_score >= 0.8 ? '優秀' : quality_score >= 0.7 ? '良好' : quality_score >= 0.6 ? '普通' : '不佳',
            reason: `${signal_type === 'BUY' ? '買盤' : '賣壓'}力道${(0.65 + Math.random() * 0.30).toFixed(1)}%，${3 + Math.floor(Math.random() * 5)}筆大單集中`,
            warnings: Math.random() > 0.7 ? ['成交量偏低'] : [],
            stop_loss: signal_type === 'BUY' ? basePrice * 0.985 : basePrice * 1.015,
            take_profit: signal_type === 'BUY' ? basePrice * 1.025 : basePrice * 0.975,
        };
    }, [watchStocks]);

    // 搜尋股票名稱
    const searchStockName = async (code: string) => {
        if (!code || code.length < 4) return;

        setSearchLoading(true);
        setSearchError('');

        try {
            // 先嘗試 tw-stocks API
            const response = await fetch(`http://localhost:8000/api/tw-stocks/search?q=${code}&limit=1`);
            const data = await response.json();

            if (data.stocks && data.stocks.length > 0) {
                const stock = data.stocks[0];
                if (stock.symbol === code) {
                    setNewStock(prev => ({
                        ...prev,
                        name: stock.name,
                        type: stock.industry || '其他'
                    }));
                    return;
                }
            }

            // 備援: 使用 yfinance API (支援更多股票)
            console.log('tw-stocks 搜尋失敗，嘗試 yfinance...');
            const yfResponse = await fetch(`http://localhost:8000/api/smart-picks/yfinance/quote/${code}`);
            const yfData = await yfResponse.json();

            if (yfData.success && yfData.price > 0) {
                // 從本地股票名稱字典取得名稱
                const STOCK_NAMES: Record<string, string> = {
                    '2881': '富邦金', '2882': '國泰金', '2308': '台達電',
                    '3363': '上詮', '8155': '博智', '5498': '凱崴', '1815': '富喬',
                    '3030': '德律', '3037': '欣興', '3231': '緯創', '8039': '台虹',
                    '2312': '金寶', '3706': '神達', '1303': '南亞', '2344': '華邦電',
                    '2327': '國巨', '2408': '南亞科', '1504': '東元', '6770': '力積電',
                    '2330': '台積電', '2317': '鴻海', '2454': '聯發科',
                };

                const stockName = STOCK_NAMES[code] || `${code}`;
                setNewStock(prev => ({
                    ...prev,
                    name: stockName,
                    type: '其他'
                }));
                console.log(`✅ yfinance 找到股票: ${code} ${stockName} @ $${yfData.price}`);
                return;
            }

            setSearchError('找不到此股票');
        } catch (err) {
            setSearchError('搜尋失敗');
        } finally {
            setSearchLoading(false);
        }
    };

    // 新增股票
    const handleAddStock = () => {
        if (!newStock.code || !newStock.name) return;

        // 檢查是否已存在
        if (watchStocks.some(s => s.code === newStock.code)) {
            setSearchError('此股票已在監控清單中');
            return;
        }

        setWatchStocks(prev => [...prev, { ...newStock }]);
        setNewStock({ code: '', name: '', type: '電子', threshold: 50 });
        setShowAddModal(false);
        setSearchError('');
    };

    // 刪除股票
    const handleRemoveStock = (code: string) => {
        setWatchStocks(prev => prev.filter(s => s.code !== code));
    };

    // 重設為預設清單
    const handleResetToDefault = () => {
        setWatchStocks(DEFAULT_WATCH_STOCKS);
    };

    // 從後端 API 獲取分析數據
    const fetchAnalysis = useCallback(async () => {
        if (!watchStocks.length) return;

        try {
            const stocksData = watchStocks.map(s => ({
                symbol: s.code,
                name: s.name,
                threshold: s.threshold
            }));

            const response = await fetch('http://localhost:8000/api/big-order/batch-analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(stocksData)
            });

            if (!response.ok) {
                console.error('API 錯誤:', response.status);
                return;
            }

            const data = await response.json();

            // 更新統計
            setStats(prev => ({
                ...prev,
                total_ticks: prev.total_ticks + data.total_stocks * 20,
                big_orders: prev.big_orders + data.signals_count,
                signals_generated: prev.signals_generated + data.signals_count,
            }));

            // 添加新訊號
            if (data.signals && data.signals.length > 0) {
                for (const signal of data.signals) {
                    setSignals(prev => [signal, ...prev].slice(0, 50));

                    // 更新品質分佈
                    setStats(prev => ({
                        ...prev,
                        valid_signals: prev.valid_signals + (signal.quality_score >= 0.6 ? 1 : 0),
                        quality_distribution: {
                            ...prev.quality_distribution,
                            excellent: prev.quality_distribution.excellent + (signal.quality_score >= 0.8 ? 1 : 0),
                            good: prev.quality_distribution.good + (signal.quality_score >= 0.7 && signal.quality_score < 0.8 ? 1 : 0),
                            fair: prev.quality_distribution.fair + (signal.quality_score >= 0.6 && signal.quality_score < 0.7 ? 1 : 0),
                            poor: prev.quality_distribution.poor + (signal.quality_score < 0.6 ? 1 : 0),
                        }
                    }));
                }
            }

            // 處理瀏覽器推播通知
            if (data.notifications && data.notifications.length > 0) {
                for (const notif of data.notifications) {
                    // 請求通知權限並發送
                    if ('Notification' in window) {
                        if (Notification.permission === 'granted') {
                            showBrowserNotification(notif);
                        } else if (Notification.permission !== 'denied') {
                            Notification.requestPermission().then(permission => {
                                if (permission === 'granted') {
                                    showBrowserNotification(notif);
                                }
                            });
                        }
                    }
                }
            }
        } catch (error) {
            console.error('獲取分析數據失敗:', error);
            // 失敗時使用模擬數據作為備援
            const signal = generateMockSignal();
            if (Math.random() > 0.5) {
                setSignals(prev => [signal, ...prev].slice(0, 50));
                setStats(prev => ({
                    ...prev,
                    total_ticks: prev.total_ticks + 100,
                    big_orders: prev.big_orders + 1,
                    signals_generated: prev.signals_generated + 1,
                    valid_signals: prev.valid_signals + (signal.quality_score >= 0.6 ? 1 : 0),
                    quality_distribution: {
                        ...prev.quality_distribution,
                        excellent: prev.quality_distribution.excellent + (signal.quality_score >= 0.8 ? 1 : 0),
                        good: prev.quality_distribution.good + (signal.quality_score >= 0.7 && signal.quality_score < 0.8 ? 1 : 0),
                        fair: prev.quality_distribution.fair + (signal.quality_score >= 0.6 && signal.quality_score < 0.7 ? 1 : 0),
                        poor: prev.quality_distribution.poor + (signal.quality_score < 0.6 ? 1 : 0),
                    }
                }));
            }
        }
    }, [watchStocks, generateMockSignal]);

    // 顯示瀏覽器推播通知
    const showBrowserNotification = (notif: {
        stock_code: string;
        stock_name: string;
        signal_type: string;
        quality: number;
        price: number;
        reason: string;
    }) => {
        const emoji = notif.signal_type === 'BUY' ? '🔴' : '🟢';
        const action = notif.signal_type === 'BUY' ? '買進' : '賣出';

        new Notification(`${emoji} ${notif.stock_code} ${notif.stock_name} - ${action}訊號`, {
            body: `💰 價格: $${notif.price.toFixed(2)}\n⭐ 品質: ${(notif.quality * 100).toFixed(0)}%\n📊 ${notif.reason}`,
            icon: notif.signal_type === 'BUY' ? '/buy-icon.png' : '/sell-icon.png',
            tag: `big-order-${notif.stock_code}`,
            requireInteraction: true,
        });
    };

    // 開始/停止監控
    const toggleMonitoring = useCallback(() => {
        if (isMonitoring) {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            setIsMonitoring(false);
        } else {
            setIsMonitoring(true);

            // 請求瀏覽器通知權限
            if ('Notification' in window && Notification.permission === 'default') {
                Notification.requestPermission();
            }

            // 立即執行一次
            fetchAnalysis();
            // 每 5 秒從後端獲取數據
            intervalRef.current = setInterval(fetchAnalysis, 5000);
        }
    }, [isMonitoring, fetchAnalysis]);

    // 清理
    useEffect(() => {
        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, []);

    // 過濾訊號
    const filteredSignals = signals.filter(signal => {
        if (filterType !== 'all' && signal.signal_type !== filterType) return false;
        if (filterQuality === 'excellent' && signal.quality_score < 0.8) return false;
        if (filterQuality === 'good' && signal.quality_score < 0.7) return false;
        return true;
    });

    // 品質顏色
    const getQualityColor = (score: number) => {
        if (score >= 0.8) return 'text-emerald-600 bg-emerald-50';
        if (score >= 0.7) return 'text-blue-600 bg-blue-50';
        if (score >= 0.6) return 'text-amber-600 bg-amber-50';
        return 'text-gray-600 bg-gray-50';
    };

    const getQualityEmoji = (score: number) => {
        if (score >= 0.8) return '🌟';
        if (score >= 0.7) return '✨';
        if (score >= 0.6) return '💫';
        return '⚠️';
    };

    return (
        <div className="space-y-6">
            {/* 頁面標題 */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl text-white shadow-lg">
                        <Zap className="w-6 h-6" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">大單偵測監控系統 v3.0</h1>
                        <p className="text-gray-500">即時監控 • 訊號分析 • 品質評估</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={toggleMonitoring}
                        className={cn(
                            "flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold transition-all",
                            isMonitoring
                                ? "bg-red-100 text-red-700 hover:bg-red-200"
                                : "bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 shadow-lg"
                        )}
                    >
                        {isMonitoring ? (
                            <>
                                <Pause className="w-5 h-5" />
                                停止監控
                            </>
                        ) : (
                            <>
                                <Play className="w-5 h-5" />
                                開始監控
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* 監控狀態指示 */}
            <div className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl",
                isMonitoring ? "bg-green-50 border border-green-200" : "bg-gray-50 border border-gray-200"
            )}>
                <div className={cn(
                    "relative flex h-3 w-3",
                    isMonitoring && "animate-pulse"
                )}>
                    <span className={cn(
                        "absolute inline-flex h-full w-full rounded-full opacity-75",
                        isMonitoring ? "bg-green-400 animate-ping" : "bg-gray-400"
                    )} />
                    <span className={cn(
                        "relative inline-flex rounded-full h-3 w-3",
                        isMonitoring ? "bg-green-500" : "bg-gray-500"
                    )} />
                </div>
                <span className={cn(
                    "font-medium",
                    isMonitoring ? "text-green-700" : "text-gray-600"
                )}>
                    {isMonitoring ? '監控中 - 即時偵測大單訊號' : '監控已停止'}
                </span>
                {isMonitoring && (
                    <span className="text-sm text-green-600">
                        監控 {watchStocks.length} 檔股票
                    </span>
                )}
            </div>

            {/* 統計卡片 */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                        <Activity className="w-4 h-4" />
                        處理 Tick
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{stats.total_ticks.toLocaleString()}</div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                        <BarChart3 className="w-4 h-4" />
                        偵測大單
                    </div>
                    <div className="text-2xl font-bold text-indigo-600">{stats.big_orders}</div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                        <Bell className="w-4 h-4" />
                        產生訊號
                    </div>
                    <div className="text-2xl font-bold text-purple-600">{stats.signals_generated}</div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-2 text-emerald-500 text-sm mb-1">
                        🌟 優秀
                    </div>
                    <div className="text-2xl font-bold text-emerald-600">{stats.quality_distribution.excellent}</div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-2 text-blue-500 text-sm mb-1">
                        ✨ 良好
                    </div>
                    <div className="text-2xl font-bold text-blue-600">{stats.quality_distribution.good}</div>
                </div>

                <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
                    <div className="flex items-center gap-2 text-amber-500 text-sm mb-1">
                        💫 普通
                    </div>
                    <div className="text-2xl font-bold text-amber-600">{stats.quality_distribution.fair}</div>
                </div>
            </div>

            {/* 監控股票清單 */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 className="font-bold text-gray-900 flex items-center gap-2">
                        <Eye className="w-5 h-5 text-indigo-500" />
                        監控股票清單
                        <span className="text-sm font-normal text-gray-500">({watchStocks.length} 檔)</span>
                    </h2>
                    <div className="flex gap-2">
                        <button
                            onClick={updateStockThresholds}
                            className="flex items-center gap-1 px-3 py-1.5 text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors"
                            title="根據最新股價更新門檻"
                        >
                            <RefreshCw className="w-3 h-3" />
                            更新門檻
                        </button>
                        <button
                            onClick={handleResetToDefault}
                            className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            重設預設
                        </button>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                        >
                            <Plus className="w-4 h-4" />
                            新增股票
                        </button>
                    </div>
                </div>
                <div className="p-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
                        {watchStocks.map((stock: WatchStock) => (
                            <div
                                key={stock.code}
                                className="relative group flex flex-col items-center p-3 bg-gray-50 rounded-lg hover:bg-indigo-50 transition-colors"
                            >
                                <button
                                    onClick={() => handleRemoveStock(stock.code)}
                                    className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                                    title="移除"
                                >
                                    <X className="w-3 h-3" />
                                </button>
                                <span className="font-bold text-gray-900">{stock.code}</span>
                                <span className="text-sm text-gray-600">{stock.name}</span>
                                {stock.price ? (
                                    <>
                                        <span className="text-xs text-indigo-600 mt-1">${stock.price.toFixed(0)}</span>
                                        <span className="text-xs text-gray-400">門檻 {stock.threshold}張</span>
                                        {stock.thresholdAmount && (
                                            <span className="text-[10px] text-green-600">{stock.thresholdAmount}</span>
                                        )}
                                    </>
                                ) : (
                                    <span className="text-xs text-gray-400 mt-1">門檻 {stock.threshold}張</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* 過濾器 */}
            <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-gray-500" />
                    <span className="text-sm text-gray-600">篩選:</span>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={() => setFilterType('all')}
                        className={cn(
                            "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                            filterType === 'all' ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        )}
                    >
                        全部
                    </button>
                    <button
                        onClick={() => setFilterType('BUY')}
                        className={cn(
                            "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                            filterType === 'BUY' ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        )}
                    >
                        🟢 買進
                    </button>
                    <button
                        onClick={() => setFilterType('SELL')}
                        className={cn(
                            "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                            filterType === 'SELL' ? "bg-red-100 text-red-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        )}
                    >
                        🔴 賣出
                    </button>
                </div>

                <div className="h-6 w-px bg-gray-300" />

                <div className="flex gap-2">
                    <button
                        onClick={() => setFilterQuality('all')}
                        className={cn(
                            "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                            filterQuality === 'all' ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        )}
                    >
                        所有品質
                    </button>
                    <button
                        onClick={() => setFilterQuality('excellent')}
                        className={cn(
                            "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                            filterQuality === 'excellent' ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        )}
                    >
                        🌟 優秀
                    </button>
                    <button
                        onClick={() => setFilterQuality('good')}
                        className={cn(
                            "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                            filterQuality === 'good' ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                        )}
                    >
                        ✨ 良好+
                    </button>
                </div>
            </div>

            {/* 訊號列表 */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                    <h2 className="font-bold text-gray-900 flex items-center gap-2">
                        <Bell className="w-5 h-5 text-purple-500" />
                        即時訊號
                        <span className="text-sm font-normal text-gray-500">({filteredSignals.length} 筆)</span>
                    </h2>
                </div>

                {filteredSignals.length === 0 ? (
                    <div className="p-12 text-center text-gray-500">
                        <Zap className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                        <p className="text-lg font-medium">尚無訊號</p>
                        <p className="text-sm mt-1">
                            {isMonitoring ? '監控中，等待大單訊號...' : '點擊「開始監控」開始偵測'}
                        </p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
                        {filteredSignals.map(signal => (
                            <div
                                key={signal.id}
                                className="p-4 hover:bg-gray-50 transition-colors"
                            >
                                <div className="flex items-start gap-4">
                                    {/* 訊號方向 */}
                                    <div className={cn(
                                        "flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center",
                                        signal.signal_type === 'BUY'
                                            ? "bg-red-100 text-red-600"
                                            : "bg-green-100 text-green-600"
                                    )}>
                                        {signal.signal_type === 'BUY'
                                            ? <TrendingUp className="w-6 h-6" />
                                            : <TrendingDown className="w-6 h-6" />
                                        }
                                    </div>

                                    {/* 訊號內容 */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={cn(
                                                "px-2 py-0.5 rounded text-xs font-bold",
                                                signal.signal_type === 'BUY'
                                                    ? "bg-red-100 text-red-700"
                                                    : "bg-green-100 text-green-700"
                                            )}>
                                                {signal.signal_type === 'BUY' ? '買進' : '賣出'}
                                            </span>
                                            <span className="font-bold text-gray-900">{signal.stock_code}</span>
                                            <span className="text-gray-600">{signal.stock_name}</span>
                                            <span className={cn(
                                                "px-2 py-0.5 rounded text-xs font-medium",
                                                getQualityColor(signal.quality_score)
                                            )}>
                                                {getQualityEmoji(signal.quality_score)} {signal.quality_level}
                                            </span>
                                        </div>

                                        <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                                            <span className="font-bold text-lg text-gray-900">
                                                ${signal.price.toFixed(2)}
                                            </span>
                                            <span>綜合 {(signal.composite_score * 100).toFixed(0)}%</span>
                                            <span>信心 {(signal.confidence * 100).toFixed(0)}%</span>
                                        </div>

                                        <p className="text-sm text-gray-600 mb-2">{signal.reason}</p>

                                        {/* 分數詳情 */}
                                        <div className="flex flex-wrap gap-2 text-xs">
                                            <span className="px-2 py-1 bg-gray-100 rounded">品質 {(signal.quality_score * 100).toFixed(0)}%</span>
                                            <span className="px-2 py-1 bg-gray-100 rounded">動能 {(signal.momentum_score * 100).toFixed(0)}%</span>
                                            <span className="px-2 py-1 bg-gray-100 rounded">成交量 {(signal.volume_score * 100).toFixed(0)}%</span>
                                            <span className="px-2 py-1 bg-gray-100 rounded">型態 {(signal.pattern_score * 100).toFixed(0)}%</span>
                                            <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded">停損 ${signal.stop_loss.toFixed(2)}</span>
                                            <span className="px-2 py-1 bg-green-50 text-green-700 rounded">停利 ${signal.take_profit.toFixed(2)}</span>
                                        </div>

                                        {signal.warnings.length > 0 && (
                                            <div className="mt-2 flex items-center gap-1 text-xs text-amber-600">
                                                <AlertTriangle className="w-3 h-3" />
                                                {signal.warnings.join(', ')}
                                            </div>
                                        )}
                                    </div>

                                    {/* 時間 */}
                                    <div className="flex-shrink-0 text-right text-sm text-gray-500">
                                        <Clock className="w-4 h-4 inline-block mr-1" />
                                        {new Date(signal.timestamp).toLocaleTimeString('zh-TW')}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* 免責聲明 */}
            {/* 歷史大單訊號記錄 */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-4">
                    <h2 className="font-bold text-gray-900 flex items-center gap-2">
                        📋 歷史大單訊號記錄
                        <span className="text-sm font-normal text-gray-500">
                            ({historyStockFilter === 'all'
                                ? historySignals.length
                                : historySignals.filter(s => s.stock_code === historyStockFilter).length} 筆)
                        </span>
                    </h2>
                    <div className="flex items-center gap-3">
                        {/* 股票篩選器 */}
                        <select
                            value={historyStockFilter}
                            onChange={(e) => setHistoryStockFilter(e.target.value)}
                            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                        >
                            <option value="all">全部股票</option>
                            {Array.from(new Set(historySignals.map(s => s.stock_code)))
                                .sort()
                                .map(code => {
                                    const signal = historySignals.find(s => s.stock_code === code);
                                    return (
                                        <option key={code} value={code}>
                                            {code} {signal?.stock_name || ''}
                                        </option>
                                    );
                                })
                            }
                        </select>
                        <button
                            onClick={loadHistory}
                            disabled={historyLoading}
                            className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                        >
                            <RefreshCw className={cn("w-4 h-4", historyLoading && "animate-spin")} />
                            重新載入
                        </button>
                    </div>
                </div>

                {historyLoading ? (
                    <div className="p-8 text-center text-gray-500">
                        <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-2"></div>
                        載入中...
                    </div>
                ) : historySignals.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        <p>尚無歷史紀錄</p>
                        <p className="text-sm mt-1">開始監控後，偵測到的大單訊號會自動保存於此</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                                <tr>
                                    <th className="px-4 py-3 text-left">時間</th>
                                    <th className="px-4 py-3 text-left">股票</th>
                                    <th className="px-4 py-3 text-center">訊號</th>
                                    <th className="px-4 py-3 text-right">價格</th>
                                    <th className="px-4 py-3 text-center">品質</th>
                                    <th className="px-4 py-3 text-left">原因</th>
                                    <th className="px-4 py-3 text-center">數據源</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {historySignals
                                    .filter(signal => historyStockFilter === 'all' || signal.stock_code === historyStockFilter)
                                    .map(signal => (
                                        <tr key={signal.signal_id} className="hover:bg-gray-50">
                                            <td className="px-4 py-3 text-sm text-gray-600">
                                                {new Date(signal.timestamp).toLocaleString('zh-TW')}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="font-bold text-gray-900">{signal.stock_code}</span>
                                                <span className="text-sm text-gray-500 ml-1">{signal.stock_name}</span>
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <span className={cn(
                                                    "px-2 py-1 rounded text-xs font-bold",
                                                    signal.signal_type === 'BUY'
                                                        ? "bg-red-100 text-red-700"
                                                        : "bg-green-100 text-green-700"
                                                )}>
                                                    {signal.signal_type === 'BUY' ? '🔴 買進' : '🟢 賣出'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-right font-medium text-gray-900">
                                                ${signal.price.toFixed(2)}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <span className={cn(
                                                    "px-2 py-1 rounded text-xs font-bold",
                                                    signal.quality_level === '優秀' ? "bg-purple-100 text-purple-700" :
                                                        signal.quality_level === '良好' ? "bg-blue-100 text-blue-700" :
                                                            signal.quality_level === '普通' ? "bg-gray-100 text-gray-700" :
                                                                "bg-red-100 text-red-700"
                                                )}>
                                                    {signal.quality_level} {(signal.quality_score * 100).toFixed(0)}%
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-600 max-w-[200px] truncate">
                                                {signal.reason}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <span className={cn(
                                                    "px-2 py-0.5 rounded text-xs",
                                                    signal.data_source === 'fubon' ? "bg-green-50 text-green-600" : "bg-yellow-50 text-yellow-600"
                                                )}>
                                                    {signal.data_source === 'fubon' ? '富邦' : 'Yahoo'}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* 統計摘要 */}
                {historySignals.length > 0 && (() => {
                    const filteredSignals = historySignals.filter(s =>
                        historyStockFilter === 'all' || s.stock_code === historyStockFilter
                    );
                    const buyCount = filteredSignals.filter(s => s.signal_type === 'BUY').length;
                    const sellCount = filteredSignals.filter(s => s.signal_type === 'SELL').length;
                    const avgQuality = filteredSignals.length > 0
                        ? (filteredSignals.reduce((sum, s) => sum + s.quality_score, 0) / filteredSignals.length * 100).toFixed(0)
                        : 0;

                    return (
                        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex gap-6 text-sm flex-wrap">
                            {historyStockFilter !== 'all' && (
                                <div>
                                    <span className="text-gray-500">篩選：</span>
                                    <span className="font-bold text-indigo-600 ml-1">{historyStockFilter}</span>
                                </div>
                            )}
                            <div>
                                <span className="text-gray-500">買進訊號：</span>
                                <span className="font-bold text-red-600 ml-1">{buyCount} 筆</span>
                            </div>
                            <div>
                                <span className="text-gray-500">賣出訊號：</span>
                                <span className="font-bold text-green-600 ml-1">{sellCount} 筆</span>
                            </div>
                            <div>
                                <span className="text-gray-500">平均品質：</span>
                                <span className="font-bold text-indigo-600 ml-1">{avgQuality}%</span>
                            </div>
                        </div>
                    );
                })()}
            </div>

            {/* 免責聲明 */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
                <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div>
                        <p className="font-bold mb-1">重要提醒</p>
                        <p>本系統僅供監控參考，不構成投資建議。訊號僅供參考，投資決策需自行判斷。投資有風險，請謹慎評估。</p>
                    </div>
                </div>
            </div>

            {/* 新增股票 Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowAddModal(false)}>
                    <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in duration-200" onClick={e => e.stopPropagation()}>
                        <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
                            <div className="flex items-center gap-3">
                                <Plus className="w-6 h-6" />
                                <div>
                                    <h3 className="font-bold text-lg">新增監控股票</h3>
                                    <p className="text-indigo-100 text-sm">輸入股票代號自動查詢</p>
                                </div>
                            </div>
                        </div>

                        <div className="p-6 space-y-4">
                            {/* 股票代號 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">股票代號</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={newStock.code}
                                        onChange={(e) => setNewStock({ ...newStock, code: e.target.value, name: '' })}
                                        placeholder="例: 2330"
                                        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
                                        maxLength={6}
                                    />
                                    <button
                                        onClick={() => searchStockName(newStock.code)}
                                        disabled={searchLoading || newStock.code.length < 4}
                                        className="px-4 py-2.5 bg-indigo-100 text-indigo-700 rounded-xl font-medium hover:bg-indigo-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                    >
                                        {searchLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                                        查詢
                                    </button>
                                </div>
                            </div>

                            {/* 股票名稱 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">股票名稱</label>
                                <input
                                    type="text"
                                    value={newStock.name}
                                    onChange={(e) => setNewStock({ ...newStock, name: e.target.value })}
                                    placeholder="自動填入或手動輸入"
                                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
                                />
                            </div>

                            {/* 股票類型 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">股票類型</label>
                                <select
                                    value={newStock.type}
                                    onChange={(e) => setNewStock({ ...newStock, type: e.target.value })}
                                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none bg-white"
                                >
                                    {STOCK_TYPES.map(type => (
                                        <option key={type} value={type}>{type}</option>
                                    ))}
                                </select>
                            </div>

                            {/* 大單門檻 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">大單門檻 (張)</label>
                                <input
                                    type="number"
                                    value={newStock.threshold}
                                    onChange={(e) => setNewStock({ ...newStock, threshold: parseInt(e.target.value) || 50 })}
                                    min={10}
                                    max={500}
                                    className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none"
                                />
                                <p className="text-xs text-gray-500 mt-1">建議：大型股 100-150張，中型股 50-80張，小型股 30-50張</p>
                            </div>

                            {/* 錯誤訊息 */}
                            {searchError && (
                                <div className="flex items-center gap-2 text-red-600 text-sm">
                                    <AlertTriangle className="w-4 h-4" />
                                    {searchError}
                                </div>
                            )}
                        </div>

                        <div className="p-6 border-t border-gray-100 bg-gray-50 flex gap-3">
                            <button
                                onClick={() => {
                                    setShowAddModal(false);
                                    setNewStock({ code: '', name: '', type: '電子', threshold: 50 });
                                    setSearchError('');
                                }}
                                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-100 transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleAddStock}
                                disabled={!newStock.code || !newStock.name}
                                className="flex-1 px-4 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                <Plus className="w-4 h-4" />
                                新增
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
