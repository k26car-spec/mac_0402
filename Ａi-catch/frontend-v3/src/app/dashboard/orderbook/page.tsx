'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import {
    BarChart3, RefreshCw, Info, TrendingUp, TrendingDown,
    ArrowUp, ArrowDown, Zap, Target, HelpCircle, Eye, Wifi, WifiOff
} from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

const STOCK_INFO: Record<string, { name: string }> = {
    "2330": { name: "台積電" },
    "2454": { name: "聯發科" },
    "2317": { name: "鴻海" },
    "2308": { name: "台達電" },
    "2382": { name: "廣達" },
    "3443": { name: "創意" },
};

interface OrderBookLevel {
    price: number;
    volume: number;
}

interface OrderBookData {
    symbol: string;
    lastPrice: number;
    change: number;
    bids: OrderBookLevel[];
    asks: OrderBookLevel[];
    totalBidVolume: number;
    totalAskVolume: number;
    source: string;
    timestamp: string;
}

export default function OrderBookPage() {
    const searchParams = useSearchParams();
    const initialSymbol = searchParams.get('symbol') || '2330';

    const [symbol, setSymbol] = useState(initialSymbol);
    const [orderBook, setOrderBook] = useState<OrderBookData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [showHelp, setShowHelp] = useState(false);
    const [useWebSocket, setUseWebSocket] = useState(true);
    const [isConnected, setIsConnected] = useState(false);
    const [tickCount, setTickCount] = useState(0);

    const wsRef = useRef<WebSocket | null>(null);

    // WebSocket 連接
    useEffect(() => {
        if (!useWebSocket) {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
            setIsConnected(false);
            return;
        }

        const wsUrl = 'ws://localhost:8000/ws/stock/' + symbol;
        console.log('[WS] Connecting to', wsUrl);

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = function () {
                console.log('[WS] Connected');
                setIsConnected(true);
            };

            ws.onmessage = function (event) {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'tick' && msg.data) {
                        const d = msg.data;
                        if (d.orderBook) {
                            setOrderBook({
                                symbol: symbol,
                                lastPrice: d.price,
                                change: d.change,
                                bids: d.orderBook.bids,
                                asks: d.orderBook.asks,
                                totalBidVolume: d.orderBook.bids.reduce(function (s: number, b: any) { return s + b.volume; }, 0),
                                totalAskVolume: d.orderBook.asks.reduce(function (s: number, a: any) { return s + a.volume; }, 0),
                                source: 'websocket',
                                timestamp: new Date().toISOString()
                            });
                            setIsLoading(false);
                        }
                        setTickCount(msg.tickCount || 0);
                    }
                } catch (e) {
                    console.error('[WS] Parse error', e);
                }
            };

            ws.onerror = function () {
                console.error('[WS] Error');
            };

            ws.onclose = function () {
                console.log('[WS] Closed');
                setIsConnected(false);
                wsRef.current = null;
            };

        } catch (e) {
            console.error('[WS] Failed to connect', e);
        }

        return function () {
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [symbol, useWebSocket]);

    // API 載入（當 WebSocket 未連線時）
    const loadOrderBook = useCallback(async function () {
        if (useWebSocket && isConnected) return;

        try {
            const response = await fetch(
                'http://localhost:8000/api/fubon/orderbook/' + symbol
            );

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.bids && data.asks) {
                    setOrderBook({
                        symbol: symbol,
                        lastPrice: data.lastPrice || 0,
                        change: data.change || (Math.random() - 0.5) * 3,
                        bids: data.bids,
                        asks: data.asks,
                        totalBidVolume: data.totalBidVolume || 0,
                        totalAskVolume: data.totalAskVolume || 0,
                        source: data.source || 'api',
                        timestamp: data.timestamp || new Date().toISOString()
                    });
                }
            }
        } catch (error) {
            console.error('Load failed:', error);
        } finally {
            setIsLoading(false);
        }
    }, [symbol, useWebSocket, isConnected]);

    useEffect(function () {
        if (!useWebSocket || !isConnected) {
            loadOrderBook();
        }
    }, [loadOrderBook, useWebSocket, isConnected]);

    useEffect(function () {
        setIsLoading(true);
    }, [symbol]);

    const stockInfo = STOCK_INFO[symbol] || { name: symbol };
    const buyPressure = orderBook
        ? (orderBook.totalBidVolume / (orderBook.totalBidVolume + orderBook.totalAskVolume)) * 100
        : 50;
    const sellPressure = 100 - buyPressure;
    const maxVolume = orderBook
        ? Math.max(...orderBook.bids.map(function (b) { return b.volume; }), ...orderBook.asks.map(function (a) { return a.volume; }))
        : 100;

    return (
        <div className="space-y-6">
            {/* 功能說明 Banner */}
            <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-100 rounded-xl p-4">
                <div className="flex items-start gap-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                        <Info className="w-5 h-5 text-purple-600" />
                    </div>
                    <div className="flex-1">
                        <h3 className="font-bold text-purple-900 mb-1">📊 五檔掛單熱力圖</h3>
                        <p className="text-sm text-purple-700 leading-relaxed">
                            本頁面即時顯示五檔買賣掛單深度。
                            <span className="font-medium text-red-600"> 紅色買盤</span>代表支撐力道，
                            <span className="font-medium text-green-600"> 綠色賣盤</span>代表壓力位置。
                        </p>
                    </div>
                    <button onClick={function () { setShowHelp(!showHelp); }} className="p-2 text-purple-500 hover:bg-purple-100 rounded-lg">
                        <HelpCircle className="w-5 h-5" />
                    </button>
                </div>

                {showHelp && (
                    <div className="mt-4 pt-4 border-t border-purple-200 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div className="flex items-start gap-2">
                            <div className="w-4 h-4 bg-red-500 rounded mt-0.5"></div>
                            <div>
                                <p className="font-bold text-gray-900">買盤（Bid）</p>
                                <p className="text-gray-600">買方願意購買的價格與數量</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-2">
                            <div className="w-4 h-4 bg-green-500 rounded mt-0.5"></div>
                            <div>
                                <p className="font-bold text-gray-900">賣盤（Ask）</p>
                                <p className="text-gray-600">賣方願意出售的價格與數量</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-2">
                            <Target className="w-4 h-4 text-blue-500 mt-0.5" />
                            <div>
                                <p className="font-bold text-gray-900">買賣力道</p>
                                <p className="text-gray-600">買盤 &gt; 賣盤 偏多，反之偏空</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl text-white shadow-lg">
                        <BarChart3 className="w-6 h-6" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h1 className="text-2xl font-bold text-gray-900">{symbol}</h1>
                            <span className="text-lg text-gray-600">{stockInfo.name}</span>
                        </div>
                        {orderBook && (
                            <div className="flex items-center gap-3 mt-1">
                                <span className={cn("text-2xl font-black", orderBook.change >= 0 ? "text-red-600" : "text-green-600")}>
                                    ${orderBook.lastPrice.toFixed(2)}
                                </span>
                                <span className={cn("flex items-center gap-1 text-sm font-bold px-2 py-0.5 rounded", orderBook.change >= 0 ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700")}>
                                    {orderBook.change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                    {orderBook.change >= 0 ? '+' : ''}{orderBook.change.toFixed(2)}%
                                </span>
                                <span className={cn("px-2 py-0.5 rounded-full text-xs font-bold",
                                    orderBook.source === 'websocket' ? "bg-purple-100 text-purple-700" :
                                        orderBook.source === 'fubon' ? "bg-green-100 text-green-700" :
                                            "bg-gray-100 text-gray-500"
                                )}>
                                    {orderBook.source === 'websocket' ? '🔌 WebSocket' :
                                        orderBook.source === 'fubon' ? '🔴 富邦' : '⚠️ 模擬'}
                                </span>
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <select value={symbol} onChange={function (e) { setSymbol(e.target.value); setIsLoading(true); }} className="px-4 py-2 border border-gray-200 rounded-lg bg-white text-sm font-medium">
                        {Object.entries(STOCK_INFO).map(function ([code, info]) {
                            return <option key={code} value={code}>{code} {info.name}</option>;
                        })}
                    </select>

                    {/* 連線狀態 */}
                    <div className="flex items-center gap-2 text-xs">
                        <span className={cn("w-2 h-2 rounded-full", isConnected ? "bg-green-500 animate-pulse" : "bg-red-500")} />
                        <span className={isConnected ? "text-green-600" : "text-red-500"}>
                            {isConnected ? '即時連線' : '離線'}
                        </span>
                        {isConnected && tickCount > 0 && <span className="text-gray-400">#{tickCount}</span>}
                    </div>

                    <button onClick={function () { setUseWebSocket(!useWebSocket); }} className={cn("px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-2", useWebSocket ? (isConnected ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700") : "bg-gray-100 text-gray-500")}>
                        {useWebSocket ? <Wifi className={cn("w-4 h-4", isConnected && "animate-pulse")} /> : <WifiOff className="w-4 h-4" />}
                        {useWebSocket ? (isConnected ? '即時' : '連接中') : 'WS關閉'}
                    </button>

                    <button onClick={loadOrderBook} disabled={isLoading || (useWebSocket && isConnected)} className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 disabled:opacity-50">
                        <RefreshCw className={cn("w-5 h-5", isLoading && "animate-spin")} />
                    </button>
                </div>
            </div>

            {/* 買賣力道 */}
            {orderBook && (
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Zap className="w-5 h-5 text-yellow-500" />
                            <h3 className="font-bold text-gray-900">買賣力道分析</h3>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                            <span className="text-red-600 font-bold">買盤: {orderBook.totalBidVolume.toLocaleString()} 張</span>
                            <span className="text-green-600 font-bold">賣盤: {orderBook.totalAskVolume.toLocaleString()} 張</span>
                        </div>
                    </div>

                    <div className="relative h-8 bg-gray-100 rounded-full overflow-hidden">
                        <div className="absolute left-0 top-0 h-full bg-gradient-to-r from-red-500 to-red-400 transition-all duration-500" style={{ width: buyPressure + '%' }} />
                        <div className="absolute right-0 top-0 h-full bg-gradient-to-l from-green-500 to-green-400 transition-all duration-500" style={{ width: sellPressure + '%' }} />
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="bg-white px-3 py-1 rounded-full text-sm font-bold shadow">
                                {buyPressure > sellPressure ? (
                                    <span className="text-red-600 flex items-center gap-1"><ArrowUp className="w-4 h-4" /> 偏多 {buyPressure.toFixed(1)}%</span>
                                ) : (
                                    <span className="text-green-600 flex items-center gap-1"><ArrowDown className="w-4 h-4" /> 偏空 {sellPressure.toFixed(1)}%</span>
                                )}
                            </span>
                        </div>
                    </div>
                </div>
            )}

            {/* 五檔明細 */}
            {isLoading ? (
                <div className="bg-white rounded-xl border border-gray-200 p-10 flex items-center justify-center">
                    <div className="text-center">
                        <RefreshCw className="w-8 h-8 animate-spin text-purple-500 mx-auto mb-2" />
                        <p className="text-gray-500">載入五檔數據中...</p>
                    </div>
                </div>
            ) : orderBook && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Eye className="w-5 h-5 text-gray-600" />
                            <h3 className="font-bold text-gray-900">五檔掛單明細</h3>
                        </div>
                        <div className="text-xs text-gray-400">
                            更新: {new Date(orderBook.timestamp).toLocaleTimeString('zh-TW')}
                        </div>
                    </div>

                    <div className="p-4">
                        {/* 賣盤 */}
                        <div className="mb-2">
                            <div className="text-xs text-gray-400 uppercase tracking-wider mb-2 flex justify-between px-2">
                                <span>賣盤</span><span>價格</span><span>數量</span>
                            </div>
                            {[...orderBook.asks].reverse().map(function (ask, idx) {
                                return (
                                    <div key={'ask-' + idx} className="relative flex items-center h-10 mb-1">
                                        <div className="absolute right-0 top-0 h-full bg-green-100 rounded-r-lg" style={{ width: (ask.volume / maxVolume * 60) + '%' }} />
                                        <div className="relative z-10 flex items-center justify-between w-full px-3">
                                            <span className="text-xs text-gray-400 w-16">賣{5 - idx}</span>
                                            <span className="font-bold text-green-600 w-24 text-center">${ask.price.toFixed(2)}</span>
                                            <span className="font-medium text-gray-700 w-24 text-right">{ask.volume.toLocaleString()}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* 成交價 */}
                        <div className="flex items-center gap-2 my-4">
                            <div className="flex-1 h-px bg-gray-200" />
                            <div className={cn("px-4 py-2 rounded-full font-black text-lg", orderBook.change >= 0 ? "bg-red-100 text-red-600" : "bg-green-100 text-green-600")}>
                                ${orderBook.lastPrice.toFixed(2)}
                            </div>
                            <div className="flex-1 h-px bg-gray-200" />
                        </div>

                        {/* 買盤 */}
                        <div>
                            <div className="text-xs text-gray-400 uppercase tracking-wider mb-2 flex justify-between px-2">
                                <span>買盤</span><span>價格</span><span>數量</span>
                            </div>
                            {orderBook.bids.map(function (bid, idx) {
                                return (
                                    <div key={'bid-' + idx} className="relative flex items-center h-10 mb-1">
                                        <div className="absolute left-0 top-0 h-full bg-red-100 rounded-l-lg" style={{ width: (bid.volume / maxVolume * 60) + '%' }} />
                                        <div className="relative z-10 flex items-center justify-between w-full px-3">
                                            <span className="text-xs text-gray-400 w-16">買{idx + 1}</span>
                                            <span className="font-bold text-red-600 w-24 text-center">${bid.price.toFixed(2)}</span>
                                            <span className="font-medium text-gray-700 w-24 text-right">{bid.volume.toLocaleString()}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {/* 快速連結 */}
            <div className="flex flex-wrap gap-2">
                <Link href={'/dashboard/chart?symbol=' + symbol} className="px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-medium hover:bg-indigo-100">查看 K 線圖 →</Link>
                <Link href="/dashboard/mainforce" className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100">查看主力動向 →</Link>
                <Link href="/dashboard/ai-report" className="px-4 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-medium hover:bg-green-100">查看 AI 分析 →</Link>
            </div>
        </div>
    );
}
