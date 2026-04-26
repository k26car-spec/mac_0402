'use client';

import { Activity, TrendingUp, TrendingDown, Clock, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';

interface Stock {
    symbol: string;
    name: string;
    price: number;
    change: number;
    volume: number;
    high?: number;
    low?: number;
}

interface MarketData {
    taiex: { value: number; change: number };
    tpex: { value: number; change: number };
    volume: number;
    status: string;
}

export default function RealtimePage() {
    const [stocks, setStocks] = useState<Stock[]>([]);
    const [market, setMarket] = useState<MarketData | null>(null);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [tickCount, setTickCount] = useState(0);
    const wsRef = useRef<WebSocket | null>(null);

    // 連接 WebSocket
    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        setIsConnecting(true);

        const ws = new WebSocket('ws://localhost:8000/ws/realtime');
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('✅ WebSocket 連接成功');
            setIsConnected(true);
            setIsConnecting(false);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'realtime_update') {
                    setStocks(data.data.stocks || []);
                    setMarket(data.data.market || null);
                    setLastUpdate(new Date());
                    setTickCount(prev => prev + 1);
                }
            } catch (err) {
                console.error('解析數據失敗:', err);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket 錯誤:', error);
            setIsConnected(false);
            setIsConnecting(false);
        };

        ws.onclose = () => {
            console.log('WebSocket 連接關閉');
            setIsConnected(false);
            setIsConnecting(false);

            // 5 秒後自動重連
            setTimeout(() => {
                if (document.visibilityState === 'visible') {
                    connectWebSocket();
                }
            }, 5000);
        };
    }, []);

    // 組件掛載時連接
    useEffect(() => {
        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [connectWebSocket]);

    // 手動重新連接
    const handleReconnect = () => {
        if (wsRef.current) {
            wsRef.current.close();
        }
        connectWebSocket();
    };

    const formatVolume = (volume: number) => {
        if (volume >= 100000000) {
            return `${(volume / 100000000).toFixed(2)} 億`;
        } else if (volume >= 10000) {
            return `${(volume / 10000).toFixed(0)} 萬`;
        }
        return volume.toLocaleString();
    };

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Activity className="w-8 h-8 text-blue-600" />
                        即時數據
                    </h1>
                    <p className="text-gray-600 mt-2">WebSocket 即時推送股票報價（每 3 秒更新）</p>
                </div>

                {/* Connection Status & Refresh */}
                <div className="flex items-center gap-4">
                    {lastUpdate && (
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                            <Clock className="w-4 h-4" />
                            更新: {lastUpdate.toLocaleTimeString('zh-TW')}
                            <span className="text-xs text-gray-400">(#{tickCount})</span>
                        </div>
                    )}

                    <button
                        onClick={handleReconnect}
                        disabled={isConnecting}
                        className={cn(
                            "flex items-center gap-2 px-4 py-2 rounded-lg transition-colors",
                            isConnected
                                ? "bg-green-100 text-green-700 hover:bg-green-200"
                                : "bg-red-100 text-red-700 hover:bg-red-200"
                        )}
                    >
                        {isConnecting ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : isConnected ? (
                            <Wifi className="w-4 h-4" />
                        ) : (
                            <WifiOff className="w-4 h-4" />
                        )}
                        {isConnecting ? '連接中...' : isConnected ? '已連線' : '重新連接'}
                    </button>
                </div>
            </div>

            {/* Market Status */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <MarketStatusCard
                    title="台股加權"
                    value={market?.taiex.value?.toLocaleString() || '---'}
                    change={market?.taiex.change || 0}
                />
                <MarketStatusCard
                    title="櫃買指數"
                    value={market?.tpex.value?.toLocaleString() || '---'}
                    change={market?.tpex.change || 0}
                />
                <MarketStatusCard
                    title="成交金額"
                    value={market?.volume ? `${market.volume.toLocaleString()} 億` : '---'}
                    change={0}
                />
                <MarketStatusCard
                    title="市場狀態"
                    value={market?.status === 'trading' ? '交易時間' : '休市'}
                    status={market?.status === 'trading' ? 'active' : 'closed'}
                />
            </div>

            {/* Stock Table */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <div className="p-6 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-bold text-gray-900">監控清單</h2>
                        <span className={cn(
                            "px-3 py-1 text-sm rounded-full flex items-center gap-2",
                            isConnected
                                ? "bg-green-100 text-green-600"
                                : "bg-red-100 text-red-600"
                        )}>
                            <span className={cn(
                                "w-2 h-2 rounded-full",
                                isConnected
                                    ? "bg-green-500 animate-pulse"
                                    : "bg-red-500"
                            )} />
                            {isConnected ? 'WebSocket 即時更新' : '連線中斷'}
                        </span>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    股票
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    現價
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    漲跌
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    最高
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    最低
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    成交量
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {stocks.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                                        {isConnecting ? (
                                            <div className="flex items-center justify-center gap-2">
                                                <RefreshCw className="w-5 h-5 animate-spin" />
                                                正在連接 WebSocket...
                                            </div>
                                        ) : (
                                            '等待數據...'
                                        )}
                                    </td>
                                </tr>
                            ) : (
                                stocks.map((stock) => (
                                    <tr key={stock.symbol} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="font-semibold text-gray-900">{stock.symbol}</div>
                                            <div className="text-sm text-gray-600">{stock.name}</div>
                                        </td>
                                        <td className={cn(
                                            "px-6 py-4 text-right font-semibold text-lg",
                                            stock.change >= 0 ? "text-rise" : "text-fall"
                                        )}>
                                            {stock.price.toFixed(2)}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className={cn(
                                                "inline-flex items-center gap-1 px-2 py-1 rounded text-sm font-medium",
                                                stock.change >= 0 ? "bg-red-50 text-rise" : "bg-green-50 text-fall"
                                            )}>
                                                {stock.change >= 0 ? (
                                                    <TrendingUp className="w-4 h-4" />
                                                ) : (
                                                    <TrendingDown className="w-4 h-4" />
                                                )}
                                                {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right text-rise">
                                            {stock.high?.toFixed(2) || '-'}
                                        </td>
                                        <td className="px-6 py-4 text-right text-fall">
                                            {stock.low?.toFixed(2) || '-'}
                                        </td>
                                        <td className="px-6 py-4 text-right text-gray-600">
                                            {formatVolume(stock.volume)}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* WebSocket Status */}
            <div className={cn(
                "rounded-lg border p-6",
                isConnected
                    ? "bg-gradient-to-r from-green-50 to-blue-50 border-green-200"
                    : "bg-gradient-to-r from-red-50 to-orange-50 border-red-200"
            )}>
                <div className="flex items-start gap-4">
                    {isConnected ? (
                        <Wifi className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                    ) : (
                        <WifiOff className="w-6 h-6 text-red-600 flex-shrink-0 mt-1" />
                    )}
                    <div className="flex-1">
                        <h3 className="text-lg font-bold text-gray-900 mb-2">
                            {isConnected ? 'WebSocket 即時連線中' : 'WebSocket 連線中斷'}
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                                <span className="text-gray-600">狀態:</span>
                                <span className={cn(
                                    "ml-2 font-medium",
                                    isConnected ? "text-green-600" : "text-red-600"
                                )}>
                                    {isConnected ? '已連線' : '斷線'}
                                </span>
                            </div>
                            <div>
                                <span className="text-gray-600">端點:</span>
                                <span className="ml-2 text-gray-900 font-medium">ws://localhost:8000</span>
                            </div>
                            <div>
                                <span className="text-gray-600">更新頻率:</span>
                                <span className="ml-2 text-gray-900 font-medium">每 3 秒</span>
                            </div>
                            <div>
                                <span className="text-gray-600">接收次數:</span>
                                <span className="ml-2 text-gray-900 font-medium">{tickCount} 筆</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Market Status Card Component
function MarketStatusCard({
    title,
    value,
    change,
    status,
}: {
    title: string;
    value: string;
    change?: number;
    status?: 'active' | 'closed';
}) {
    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="text-sm text-gray-600 mb-1">{title}</div>
            <div className="text-2xl font-bold text-gray-900">{value}</div>
            {change !== undefined && change !== 0 && (
                <div className={cn(
                    "text-sm font-medium mt-1",
                    change >= 0 ? "text-rise" : "text-fall"
                )}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                </div>
            )}
            {status && (
                <div className={cn(
                    "text-sm font-medium mt-1 flex items-center gap-1",
                    status === 'active' ? "text-green-600" : "text-gray-500"
                )}>
                    <span className={cn(
                        "w-2 h-2 rounded-full",
                        status === 'active' ? "bg-green-500 animate-pulse" : "bg-gray-400"
                    )} />
                    {status === 'active' ? '開盤中' : '休市'}
                </div>
            )}
        </div>
    );
}
