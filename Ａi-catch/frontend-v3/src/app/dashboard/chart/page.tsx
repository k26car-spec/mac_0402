'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import {
    TrendingUp, TrendingDown, BarChart3, Activity, Clock,
    RefreshCw, Info, ChevronDown, Calendar, ZoomIn, ZoomOut,
    Maximize2, HelpCircle, WifiOff, Wifi, Users
} from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

// 計算技術指標
const calculateMA = (data: any[], period: number) => {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            result.push({ time: data[i].time, value: null });
        } else {
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += data[i - j].close;
            }
            result.push({ time: data[i].time, value: parseFloat((sum / period).toFixed(2)) });
        }
    }
    return result;
};

export default function ChartPage() {
    const searchParams = useSearchParams();
    const initialSymbol = searchParams.get('symbol') || '2330';

    const [symbol, setSymbol] = useState(initialSymbol);
    const [stockInfo, setStockInfo] = useState<{ name: string; industry: string; market?: string }>({ name: '', industry: '' });
    const [timeframe, setTimeframe] = useState<'1D' | '1W' | '1M' | '3M'>('1M');
    const [candleData, setCandleData] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showHelp, setShowHelp] = useState(false);
    const [dataSource, setDataSource] = useState<string>('loading');
    const [error, setError] = useState<string | null>(null);
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<any>(null);

    // 法人買賣超歷史
    const [institutionalData, setInstitutionalData] = useState<any[]>([]);
    const [institutionalLoading, setInstitutionalLoading] = useState(false);

    // 從後端 API 獲取股票名稱
    const fetchStockInfo = useCallback(async (sym: string) => {
        try {
            const response = await fetch(
                `http://localhost:8000/api/tw-stocks/search?q=${sym}&limit=1`,
                { signal: AbortSignal.timeout(5000) }
            );
            if (response.ok) {
                const data = await response.json();
                if (data.stocks && data.stocks.length > 0) {
                    const stock = data.stocks[0];
                    // 確保是完全匹配的代碼
                    if (stock.symbol === sym) {
                        setStockInfo({
                            name: stock.name || sym,
                            industry: stock.industry || stock.market || '',
                            market: stock.market
                        });
                        return;
                    }
                }
            }
            // 如果找不到，顯示代碼
            setStockInfo({ name: sym, industry: '' });
        } catch (error) {
            console.error('獲取股票資訊失敗:', error);
            setStockInfo({ name: sym, industry: '' });
        }
    }, []);

    // 獲取法人買賣超歷史
    const fetchInstitutionalData = useCallback(async (sym: string) => {
        setInstitutionalLoading(true);
        try {
            const response = await fetch(
                `http://localhost:8000/api/smart-picks/twse/stock/${sym}/institutional?days=10`,
                { signal: AbortSignal.timeout(10000) }
            );
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success' && data.data) {
                    setInstitutionalData(data.data);
                }
            }
        } catch (error) {
            console.error('獲取法人買賣超失敗:', error);
        } finally {
            setInstitutionalLoading(false);
        }
    }, []);

    // 當 symbol 變化時獲取股票資訊和法人買賣超
    useEffect(() => {
        fetchStockInfo(symbol);
        fetchInstitutionalData(symbol);
    }, [symbol, fetchStockInfo, fetchInstitutionalData]);

    // 載入圖表數據 - 從後端 API 獲取真實數據（不使用模擬數據）
    const loadChartData = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        const days = timeframe === '1D' ? 5 : timeframe === '1W' ? 14 : timeframe === '1M' ? 60 : 180;

        try {
            const response = await fetch(
                `http://localhost:8000/api/fubon/candles/${symbol}?days=${days}&timeframe=D`,
                { signal: AbortSignal.timeout(10000) }
            );

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.candles && data.candles.length > 0) {
                    setCandleData(data.candles);
                    setDataSource(data.source || 'api');
                } else {
                    setError('無法取得 K 線數據，API 回傳空資料');
                    setCandleData([]);
                    setDataSource('error');
                }
            } else {
                throw new Error(`API 請求失敗: ${response.status}`);
            }
        } catch (err) {
            console.error('載入 K 線數據失敗:', err);
            setError('無法連接到後端 API，請確認服務是否啟動');
            setCandleData([]);
            setDataSource('error');
        } finally {
            setIsLoading(false);
        }
    }, [symbol, timeframe]);

    useEffect(() => {
        loadChartData();
    }, [loadChartData]);

    // 初始化圖表
    useEffect(() => {
        // Don't initialize chart while loading or if ref is not available
        if (typeof window === 'undefined' || isLoading || candleData.length === 0) return;
        if (!chartContainerRef.current) return;

        const initChart = async () => {
            const LightweightCharts = await import('lightweight-charts');

            // 清除舊圖表
            if (chartRef.current) {
                chartRef.current.remove();
            }

            const chart = LightweightCharts.createChart(chartContainerRef.current!, {
                layout: {
                    background: { type: LightweightCharts.ColorType.Solid, color: '#ffffff' },
                    textColor: '#333',
                },
                grid: {
                    vertLines: { color: '#f0f0f0' },
                    horzLines: { color: '#f0f0f0' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                },
                rightPriceScale: {
                    borderColor: '#e0e0e0',
                },
                timeScale: {
                    borderColor: '#e0e0e0',
                    timeVisible: true,
                },
                width: chartContainerRef.current!.clientWidth,
                height: 400,
            });

            chartRef.current = chart;

            // 確保數據按時間升序排列
            const sortedData = [...candleData].sort((a, b) => {
                const timeA = new Date(a.time).getTime();
                const timeB = new Date(b.time).getTime();
                return timeA - timeB;
            });

            // K線圖 - 使用 v5 API
            const candlestickSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
                upColor: '#ef4444',
                downColor: '#22c55e',
                borderUpColor: '#ef4444',
                borderDownColor: '#22c55e',
                wickUpColor: '#ef4444',
                wickDownColor: '#22c55e',
            });
            candlestickSeries.setData(sortedData);

            // MA5 - 使用 v5 API (使用排序後的數據)
            const ma5Data = calculateMA(sortedData, 5).filter(d => d.value !== null);
            const ma5Series = chart.addSeries(LightweightCharts.LineSeries, {
                color: '#f59e0b',
                lineWidth: 1,
            });
            ma5Series.setData(ma5Data);

            // MA20 - 使用 v5 API (使用排序後的數據)
            const ma20Data = calculateMA(sortedData, 20).filter(d => d.value !== null);
            const ma20Series = chart.addSeries(LightweightCharts.LineSeries, {
                color: '#3b82f6',
                lineWidth: 1,
            });
            ma20Series.setData(ma20Data);

            // 自適應大小
            const handleResize = () => {
                if (chartContainerRef.current) {
                    chart.applyOptions({ width: chartContainerRef.current.clientWidth });
                }
            };
            window.addEventListener('resize', handleResize);

            chart.timeScale().fitContent();

            return () => {
                window.removeEventListener('resize', handleResize);
                chart.remove();
            };
        };

        initChart();
    }, [candleData, isLoading]);

    // stockInfo 已經在 state 中管理，這裡不需要重複宣告
    // 確保數據按時間排序後取得最新價格
    const sortedForPrice = [...candleData].sort((a, b) => {
        const timeA = new Date(a.time).getTime();
        const timeB = new Date(b.time).getTime();
        return timeA - timeB;
    });
    const latestData = sortedForPrice[sortedForPrice.length - 1];
    const previousData = sortedForPrice[sortedForPrice.length - 2];
    const priceChange = latestData && previousData ? latestData.close - previousData.close : 0;
    const priceChangePercent = previousData ? (priceChange / previousData.close) * 100 : 0;

    return (
        <div className="space-y-6">
            {/* 功能說明 Banner */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-4">
                <div className="flex items-start gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                        <Info className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1">
                        <h3 className="font-bold text-blue-900 mb-1">📈 專業 K 線圖分析</h3>
                        <p className="text-sm text-blue-700 leading-relaxed">
                            本頁面提供即時 K 線圖與技術指標分析。您可以：
                            <span className="font-medium"> 切換不同時間週期</span>（日/週/月）、
                            <span className="font-medium"> 查看均線走勢</span>（MA5/MA20）、
                            <span className="font-medium"> 滑鼠懸停查看詳細數據</span>。
                            紅色代表上漲，綠色代表下跌（符合台股慣例）。
                        </p>
                    </div>
                    <button
                        onClick={() => setShowHelp(!showHelp)}
                        className="p-2 text-blue-500 hover:bg-blue-100 rounded-lg transition-colors"
                    >
                        <HelpCircle className="w-5 h-5" />
                    </button>
                </div>

                {showHelp && (
                    <div className="mt-4 pt-4 border-t border-blue-200 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div className="flex items-start gap-2">
                            <div className="w-4 h-4 bg-red-500 rounded mt-0.5"></div>
                            <div>
                                <p className="font-bold text-gray-900">紅色 K 棒</p>
                                <p className="text-gray-600">收盤價 ＞ 開盤價（上漲）</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-2">
                            <div className="w-4 h-4 bg-green-500 rounded mt-0.5"></div>
                            <div>
                                <p className="font-bold text-gray-900">綠色 K 棒</p>
                                <p className="text-gray-600">收盤價 ＜ 開盤價（下跌）</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-2">
                            <div className="flex gap-1 mt-0.5">
                                <div className="w-2 h-4 bg-amber-500 rounded"></div>
                                <div className="w-2 h-4 bg-blue-500 rounded"></div>
                            </div>
                            <div>
                                <p className="font-bold text-gray-900">均線</p>
                                <p className="text-gray-600">橙色 MA5 / 藍色 MA20</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl text-white shadow-lg">
                        <BarChart3 className="w-6 h-6" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h1 className="text-2xl font-bold text-gray-900">{symbol}</h1>
                            <span className="text-lg text-gray-600">{stockInfo.name}</span>
                            <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded text-xs font-medium">
                                {stockInfo.industry}
                            </span>
                        </div>
                        {latestData && (
                            <div className="flex items-center gap-3 mt-1">
                                <span className={cn(
                                    "text-2xl font-black",
                                    priceChange >= 0 ? "text-red-600" : "text-green-600"
                                )}>
                                    {latestData.close.toFixed(2)}
                                </span>
                                <span className={cn(
                                    "flex items-center gap-1 text-sm font-bold px-2 py-0.5 rounded",
                                    priceChange >= 0 ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"
                                )}>
                                    {priceChange >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                    {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePercent.toFixed(2)}%)
                                </span>
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* 股票代碼輸入 */}
                    <div className="relative">
                        <input
                            type="text"
                            value={symbol}
                            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                            placeholder="輸入股票代碼"
                            className="w-32 px-4 py-2 border border-gray-200 rounded-lg bg-white text-sm font-medium focus:ring-2 focus:ring-blue-500 outline-none"
                        />
                    </div>

                    {/* 時間週期 */}
                    <div className="flex bg-gray-100 rounded-lg p-1">
                        {(['1D', '1W', '1M', '3M'] as const).map(tf => (
                            <button
                                key={tf}
                                onClick={() => setTimeframe(tf)}
                                className={cn(
                                    "px-3 py-1.5 text-xs font-bold rounded-md transition-all",
                                    timeframe === tf
                                        ? "bg-white text-blue-600 shadow-sm"
                                        : "text-gray-500 hover:text-gray-700"
                                )}
                            >
                                {tf}
                            </button>
                        ))}
                    </div>

                    <button
                        onClick={loadChartData}
                        disabled={isLoading}
                        className="p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={cn("w-5 h-5", isLoading && "animate-spin")} />
                    </button>
                </div>
            </div>

            {/* Chart Container */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 text-sm">
                            <span className="w-3 h-0.5 bg-amber-500 rounded"></span>
                            <span className="text-gray-600">MA5</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                            <span className="w-3 h-0.5 bg-blue-500 rounded"></span>
                            <span className="text-gray-600">MA20</span>
                        </div>
                        {/* 數據來源標籤 */}
                        <div className={cn(
                            "px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1",
                            (dataSource === 'fubon' || dataSource === 'api') && "bg-green-100 text-green-700",
                            dataSource === 'yahoo' && "bg-blue-100 text-blue-700",
                            dataSource === 'error' && "bg-red-100 text-red-700",
                            dataSource === 'loading' && "bg-gray-100 text-gray-500"
                        )}>
                            {(dataSource === 'fubon' || dataSource === 'api') && <><Wifi className="w-3 h-3" /> 真實數據</>}
                            {dataSource === 'yahoo' && '📊 Yahoo Finance'}
                            {dataSource === 'error' && <><WifiOff className="w-3 h-3" /> 連接失敗</>}
                            {dataSource === 'loading' && '載入中...'}
                        </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                        <Clock className="w-3.5 h-3.5" />
                        最後更新: {new Date().toLocaleTimeString('zh-TW')}
                    </div>
                </div>

                <div className="p-4">
                    {isLoading ? (
                        <div className="h-[400px] flex items-center justify-center">
                            <div className="text-center">
                                <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
                                <p className="text-gray-500">載入圖表中...</p>
                            </div>
                        </div>
                    ) : error ? (
                        <div className="h-[400px] flex items-center justify-center">
                            <div className="text-center">
                                <WifiOff className="w-12 h-12 text-red-400 mx-auto mb-3" />
                                <p className="text-gray-700 font-medium mb-2">{error}</p>
                                <p className="text-sm text-gray-500 mb-4">請確認後端 API 服務已正確啟動</p>
                                <button
                                    onClick={loadChartData}
                                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                                >
                                    重試
                                </button>
                            </div>
                        </div>
                    ) : candleData.length === 0 ? (
                        <div className="h-[400px] flex items-center justify-center">
                            <div className="text-center">
                                <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                                <p className="text-gray-500">暫無 K 線數據</p>
                            </div>
                        </div>
                    ) : (
                        <div ref={chartContainerRef} className="w-full" />
                    )}
                </div>
            </div>

            {/* Quick Stats */}
            {latestData && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">開盤</p>
                        <p className="text-lg font-bold text-gray-900">${latestData.open}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">最高</p>
                        <p className="text-lg font-bold text-red-600">${latestData.high}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">最低</p>
                        <p className="text-lg font-bold text-green-600">${latestData.low}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">收盤</p>
                        <p className={cn(
                            "text-lg font-bold",
                            priceChange >= 0 ? "text-red-600" : "text-green-600"
                        )}>${latestData.close}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">成交量</p>
                        <p className="text-lg font-bold text-gray-900">{(latestData.volume / 1000).toFixed(0)}K</p>
                    </div>
                </div>
            )}

            {/* 法人買賣超歷史 */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Users className="w-5 h-5 text-blue-600" />
                        <h3 className="font-bold text-gray-900">法人買賣超歷史</h3>
                        <span className="text-xs text-gray-400">近10日</span>
                    </div>
                    <span className="text-xs text-gray-400">資料來源: TWSE</span>
                </div>

                <div className="p-4">
                    {institutionalLoading ? (
                        <div className="text-center py-8">
                            <RefreshCw className="w-6 h-6 animate-spin text-blue-500 mx-auto mb-2" />
                            <span className="text-gray-500 text-sm">載入中...</span>
                        </div>
                    ) : institutionalData.length > 0 ? (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-4 py-3 text-left font-medium text-gray-600">日期</th>
                                        <th className="px-4 py-3 text-right font-medium text-gray-600">外資</th>
                                        <th className="px-4 py-3 text-right font-medium text-gray-600">投信</th>
                                        <th className="px-4 py-3 text-right font-medium text-gray-600">自營商</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                    {institutionalData.map((item, i) => {
                                        const parseValue = (val: string) => {
                                            const num = parseFloat(val?.replace(/[,]/g, '') || '0');
                                            return num;
                                        };
                                        const foreign = parseValue(item.foreign);
                                        const trust = parseValue(item.trust);
                                        const dealer = parseValue(item.dealer);

                                        return (
                                            <tr key={i} className="hover:bg-gray-50">
                                                <td className="px-4 py-3 text-gray-900">{item.date}</td>
                                                <td className={cn("px-4 py-3 text-right font-medium",
                                                    foreign > 0 ? "text-red-600" : foreign < 0 ? "text-green-600" : "text-gray-500"
                                                )}>
                                                    {foreign > 0 ? '+' : ''}{item.foreign || '-'}
                                                </td>
                                                <td className={cn("px-4 py-3 text-right font-medium",
                                                    trust > 0 ? "text-red-600" : trust < 0 ? "text-green-600" : "text-gray-500"
                                                )}>
                                                    {trust > 0 ? '+' : ''}{item.trust || '-'}
                                                </td>
                                                <td className={cn("px-4 py-3 text-right font-medium",
                                                    dealer > 0 ? "text-red-600" : dealer < 0 ? "text-green-600" : "text-gray-500"
                                                )}>
                                                    {dealer > 0 ? '+' : ''}{item.dealer || '-'}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-gray-500">
                            <Users className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                            <p>暫無法人買賣超資料</p>
                            <p className="text-xs mt-1">請確認後端 API 是否正常運行</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Quick Links */}
            <div className="flex flex-wrap gap-2">
                <Link
                    href="/dashboard/lstm"
                    className="px-4 py-2 bg-purple-50 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-100 transition-colors"
                >
                    查看 LSTM 預測 →
                </Link>
                <Link
                    href="/dashboard/mainforce"
                    className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors"
                >
                    查看主力動向 →
                </Link>
                <Link
                    href="/dashboard/ai-report"
                    className="px-4 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-medium hover:bg-green-100 transition-colors"
                >
                    查看 AI 分析 →
                </Link>
            </div>
        </div>
    );
}
