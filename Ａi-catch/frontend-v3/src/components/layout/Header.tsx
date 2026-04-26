'use client';

import { Bell, LogOut, Search, User, Settings, Moon, Sun, ChevronDown, TrendingUp, Loader2 } from 'lucide-react';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

// 股票類型定義
interface StockItem {
    symbol: string;
    name: string;
    market?: string;
    industry?: string;
}

// 即時行情類型
interface MarketQuote {
    label: string;
    value: string;
    change: number;
}

export const Header = () => {
    const router = useRouter();
    const [user, setUser] = useState<{ username: string } | null>(null);
    const [showNotifications, setShowNotifications] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [filteredStocks, setFilteredStocks] = useState<StockItem[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const searchRef = useRef<HTMLDivElement>(null);
    const debounceRef = useRef<NodeJS.Timeout | null>(null);

    // 即時行情狀態
    const [marketQuotes, setMarketQuotes] = useState<MarketQuote[]>([
        { label: '台股加權', value: '---', change: 0 },
        { label: 'NASDAQ', value: '---', change: 0 },
        { label: '台積電 2330', value: '---', change: 0 },
        { label: '聯發科 2454', value: '---', change: 0 },
    ]);

    // 獲取即時行情
    const fetchMarketQuotes = useCallback(async () => {
        try {
            // 嘗試從後端獲取行情
            const response = await fetch('http://localhost:8000/api/market/quotes', {
                signal: AbortSignal.timeout(5000)
            });

            if (response.ok) {
                const data = await response.json();
                if (data.quotes) {
                    setMarketQuotes(data.quotes);
                    return;
                }
            }
        } catch (error) {
            // 後端不可用，嘗試直接從 Yahoo Finance 獲取
            console.log('使用備援行情源...');
        }

        // 備援：使用 Fubon API
        try {
            const symbols = ['2330', '2454'];
            const quotes: MarketQuote[] = [
                { label: '台股加權', value: '即時', change: 0 },
                { label: 'NASDAQ', value: '即時', change: 0 },
            ];

            for (const sym of symbols) {
                try {
                    const res = await fetch(`http://localhost:8000/api/fubon/quote/${sym}`, {
                        signal: AbortSignal.timeout(3000)
                    });
                    if (res.ok) {
                        const data = await res.json();
                        const price = data.price || data.current_price || 0;
                        const change = data.change || 0;
                        quotes.push({
                            label: sym === '2330' ? '台積電 2330' : '聯發科 2454',
                            value: price > 0 ? price.toLocaleString() : '---',
                            change: change
                        });
                    }
                } catch {
                    quotes.push({
                        label: sym === '2330' ? '台積電 2330' : '聯發科 2454',
                        value: '---',
                        change: 0
                    });
                }
            }

            setMarketQuotes(quotes);
        } catch (error) {
            console.error('獲取行情失敗:', error);
        }
    }, []);

    // 初始化時獲取行情，每 60 秒更新一次
    useEffect(() => {
        fetchMarketQuotes();
        const interval = setInterval(fetchMarketQuotes, 60000);
        return () => clearInterval(interval);
    }, [fetchMarketQuotes]);

    useEffect(() => {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
            try {
                setUser(JSON.parse(storedUser));
            } catch (e) {
                console.error('解析用戶資訊失敗', e);
            }
        }
    }, []);

    // 從後端 API 搜尋股票（支援 2000+ 台股）
    const searchStocksFromAPI = useCallback(async (keyword: string) => {
        if (!keyword.trim()) {
            setFilteredStocks([]);
            setShowSuggestions(false);
            return;
        }

        setIsSearching(true);
        try {
            // 使用台股清單 API 搜尋（支援 2000+ 台股）
            const response = await fetch(
                `http://localhost:8000/api/tw-stocks/search?q=${encodeURIComponent(keyword)}&limit=8`,
                { signal: AbortSignal.timeout(3000) }
            );

            if (response.ok) {
                const data = await response.json();
                const stocks = (data.stocks || []).slice(0, 8); // 最多顯示 8 個結果
                setFilteredStocks(stocks);
                setShowSuggestions(stocks.length > 0);
            } else {
                // 如果後端 API 失敗，嘗試直接搜尋（允許任意代碼）
                setFilteredStocks([{
                    symbol: keyword.toUpperCase(),
                    name: `搜尋 ${keyword}`,
                    industry: '直接搜尋'
                }]);
                setShowSuggestions(true);
            }
        } catch (error) {
            console.error('搜尋股票失敗:', error);
            // 失敗時允許直接搜尋任意代碼
            setFilteredStocks([{
                symbol: keyword.toUpperCase(),
                name: `搜尋 ${keyword}`,
                industry: '直接搜尋'
            }]);
            setShowSuggestions(true);
        } finally {
            setIsSearching(false);
        }
    }, []);

    // 搜尋過濾邏輯（帶 debounce，300ms 後才發送請求）
    useEffect(() => {
        // 清除之前的 debounce
        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }

        if (searchQuery.trim()) {
            setIsSearching(true);
            // 設置新的 debounce
            debounceRef.current = setTimeout(() => {
                searchStocksFromAPI(searchQuery.trim());
            }, 300);
        } else {
            setFilteredStocks([]);
            setShowSuggestions(false);
            setIsSearching(false);
        }

        return () => {
            if (debounceRef.current) {
                clearTimeout(debounceRef.current);
            }
        };
    }, [searchQuery, searchStocksFromAPI]);

    // 點擊外部關閉建議
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
                setShowSuggestions(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        setUser(null);
        router.push('/login');
    };

    // 處理搜尋 - 導向 K 線圖頁面
    const handleSearch = (symbol?: string) => {
        const targetSymbol = symbol || searchQuery.trim();
        if (targetSymbol) {
            // 清除搜尋框並關閉建議
            setSearchQuery('');
            setShowSuggestions(false);
            // 導向 K 線圖頁面
            router.push(`/dashboard/chart?symbol=${targetSymbol}`);
        }
    };

    // 處理 Enter 鍵
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            handleSearch();
        } else if (e.key === 'Escape') {
            setShowSuggestions(false);
        }
    };

    return (
        <header className="sticky top-0 z-30 transition-all duration-300">
            {/* Main Header */}
            <div className="h-16 border-b border-gray-200 bg-white/80 backdrop-blur-md flex items-center justify-between px-6 shadow-sm">
                {/* Left: Brand & Search */}
                <div className="flex items-center gap-6 flex-1">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">
                            AI
                        </div>
                        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent hidden sm:block">
                            AI 主力監控平台
                        </h1>
                    </div>

                    <div className="hidden lg:flex items-center gap-2 text-[10px] font-bold px-2 py-0.5 bg-green-50 text-green-600 rounded-full border border-green-100 uppercase tracking-wider">
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                        </span>
                        Live v3.0
                    </div>

                    {/* 搜尋框 */}
                    <div className="relative max-w-xs w-full hidden md:block ml-4" ref={searchRef}>
                        {isSearching ? (
                            <Loader2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-blue-500 animate-spin" />
                        ) : (
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        )}
                        <input
                            type="text"
                            placeholder="搜尋代碼或名稱 (支援 2000+ 台股)..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            onFocus={() => searchQuery.trim() && filteredStocks.length > 0 && setShowSuggestions(true)}
                            className="w-full pl-9 pr-4 py-1.5 bg-gray-100/50 border-transparent rounded-full text-sm focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                        />

                        {/* 搜尋建議下拉 */}
                        {showSuggestions && (
                            <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden z-50">
                                {isSearching ? (
                                    <div className="px-4 py-6 flex items-center justify-center gap-2 text-gray-500">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span className="text-sm">搜尋中...</span>
                                    </div>
                                ) : filteredStocks.length > 0 ? (
                                    <>
                                        {filteredStocks.map((stock) => (
                                            <button
                                                key={stock.symbol}
                                                onClick={() => handleSearch(stock.symbol)}
                                                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-blue-50 transition-colors text-left"
                                            >
                                                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 font-bold text-xs">
                                                    {stock.symbol.slice(-2)}
                                                </div>
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-bold text-gray-900">{stock.symbol}</span>
                                                        <span className="text-gray-600">{stock.name}</span>
                                                    </div>
                                                    <span className="text-xs text-gray-400">{stock.industry || stock.market || ''}</span>
                                                </div>
                                                <TrendingUp className="w-4 h-4 text-gray-400" />
                                            </button>
                                        ))}
                                        <div className="px-4 py-2 bg-gray-50 text-xs text-gray-500 border-t border-gray-100 flex items-center justify-between">
                                            <span>按 Enter 搜尋或點擊選擇</span>
                                            <span className="text-blue-500 font-medium">支援 2000+ 台股</span>
                                        </div>
                                    </>
                                ) : (
                                    <div className="px-4 py-4 text-center text-gray-500 text-sm">
                                        找不到符合的股票
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2">
                    {/* Notifications */}
                    <div className="relative">
                        <button
                            onClick={() => setShowNotifications(!showNotifications)}
                            className="p-2 text-gray-500 hover:bg-gray-100 rounded-full transition-colors relative"
                        >
                            <Bell size={20} />
                            <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
                        </button>

                        {showNotifications && (
                            <div className="absolute right-0 mt-3 w-80 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden animate-in fade-in zoom-in duration-200 origin-top-right">
                                <div className="p-4 border-b border-gray-50 flex items-center justify-between">
                                    <h3 className="font-semibold text-gray-900">最新通知</h3>
                                    <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-full font-bold">3 NEW</span>
                                </div>
                                <div className="max-h-96 overflow-y-auto">
                                    <NotificationItem
                                        title="主力進場訊號"
                                        message="2330 台積電檢測到主力進場，信心度 85%"
                                        time="5 分鐘前"
                                        type="success"
                                    />
                                    <NotificationItem
                                        title="LSTM 預測更新"
                                        message="2454 聯發科 3日預測價格上漲 3.2%"
                                        time="15 分鐘前"
                                        type="info"
                                    />
                                    <NotificationItem
                                        title="警報觸發"
                                        message="2317 鴻海突破關鍵壓力位"
                                        time="1 小時前"
                                        type="warning"
                                    />
                                </div>
                                <div className="p-3 border-t border-gray-50 text-center bg-gray-50/50">
                                    <button className="text-xs text-blue-600 hover:text-blue-700 font-bold uppercase tracking-tight">
                                        查看所有歷史通知
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="h-6 w-[1px] bg-gray-200 mx-1"></div>

                    {/* User Profile */}
                    {user ? (
                        <div className="flex items-center gap-1">
                            <button className="flex items-center gap-2.5 px-2 py-1.5 hover:bg-gray-100 rounded-full transition-all group">
                                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold shadow-sm ring-2 ring-white group-hover:ring-blue-100 transition-all uppercase">
                                    {user.username.charAt(0)}
                                </div>
                                <div className="text-left hidden lg:block">
                                    <p className="text-xs font-bold text-gray-900">{user.username}</p>
                                    <p className="text-[10px] text-gray-500 font-medium">Pro Member</p>
                                </div>
                                <ChevronDown size={14} className="text-gray-400 group-hover:text-gray-600 transition-colors" />
                            </button>

                            <button
                                onClick={handleLogout}
                                className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-all"
                                title="登出系統"
                            >
                                <LogOut size={18} />
                            </button>
                        </div>
                    ) : (
                        <button
                            onClick={() => router.push('/login')}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-full text-sm font-bold transition-all shadow-md shadow-blue-500/20 active:scale-95"
                        >
                            LOGIN
                        </button>
                    )}
                </div>
            </div>

            {/* Quick Stats Bar - 即時行情 */}
            <div className="border-b border-gray-100 bg-white/50 backdrop-blur-sm px-6 py-1.5 overflow-x-auto no-scrollbar hidden md:block">
                <div className="flex items-center gap-8 whitespace-nowrap">
                    {marketQuotes.map((quote, index) => (
                        <QuickStat key={index} label={quote.label} value={quote.value} change={quote.change} />
                    ))}
                    <div className="flex items-center gap-2 border-l border-gray-200 pl-8">
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Market Status:</span>
                        <span className="flex items-center gap-1.5 text-[10px] font-bold text-green-600 bg-green-50 px-2 py-0.5 rounded-full border border-green-100">
                            <span className="h-1 w-1 bg-green-500 rounded-full animate-pulse"></span>
                            LIVE
                        </span>
                    </div>
                </div>
            </div>
        </header>
    );
};

// Notification Item Component
function NotificationItem({
    title,
    message,
    time,
    type,
}: {
    title: string;
    message: string;
    time: string;
    type: 'success' | 'info' | 'warning';
}) {
    const iconColors = {
        success: 'bg-green-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500',
    };

    return (
        <div className="p-4 hover:bg-gray-50 border-b border-gray-50 cursor-pointer transition-colors group">
            <div className="flex items-start gap-4">
                <div className={cn('w-2 h-2 rounded-full mt-1.5 flex-shrink-0', iconColors[type])} />
                <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                        <h4 className="text-xs font-bold text-gray-900 truncate">{title}</h4>
                        <span className="text-[10px] text-gray-400 font-medium">{time}</span>
                    </div>
                    <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">{message}</p>
                </div>
            </div>
        </div>
    );
}

// Quick Stat Component
function QuickStat({
    label,
    value,
    change,
}: {
    label: string;
    value: string;
    change: number;
}) {
    const isUp = change >= 0;
    return (
        <div className="flex items-center gap-2.5 group cursor-default">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter group-hover:text-gray-600 transition-colors">{label}</span>
            <span className="text-xs font-bold text-gray-900 tabular-nums">{value}</span>
            <span
                className={cn(
                    'text-[10px] font-extrabold px-1.5 py-0.5 rounded flex items-center gap-0.5',
                    isUp ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'
                )}
            >
                {isUp ? '▲' : '▼'}
                {Math.abs(change).toFixed(2)}%
            </span>
        </div>
    );
}
