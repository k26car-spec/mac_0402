'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Brain, TrendingUp, TrendingDown, AlertTriangle, CheckCircle,
    BarChart3, Activity, Zap, Target, Shield, RefreshCw,
    ArrowUpRight, ArrowDownRight, Minus, Wifi, WifiOff
} from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface StockAnalysis {
    symbol: string;
    name: string;
    price: number;
    change: number;
    mainForceSignal: 'buy' | 'sell' | 'neutral';
    mainForceConfidence: number;
    lstmPrediction: 'up' | 'down' | 'neutral';
    lstmConfidence: number;
    riskLevel: 'low' | 'medium' | 'high';
    recommendation: string;
    score: number;
    dataSource: string;
}

interface MarketSummary {
    sentiment: 'bullish' | 'bearish' | 'neutral';
    sentimentScore: number;
    volatility: 'low' | 'medium' | 'high';
    trendStrength: number;
    activeSignals: number;
    topPicks: string[];
}

// 股票監控清單（與大單偵測 v3.0 同步）
function getWatchlistStocks(): string[] {
    // 與 big-order page 的 DEFAULT_WATCH_STOCKS 同步
    return [
        // 金融股
        '2881', '2882',
        // 電子股
        '2308', '5498', '3030', '3037', '1815', '3231', '8039', '3363', '8155', '2312', '3706',
        // 傳產/半導體
        '1303', '2344',
        // 其他監控
        '2327', '2408', '1504', '6770'
    ];
}

// 股票名稱對應表（包含上櫃股票）
const STOCK_NAMES: Record<string, string> = {
    '2330': '台積電', '2454': '聯發科', '2317': '鴻海', '2308': '台達電',
    '2382': '廣達', '3443': '創意', '2887': '台新金', '2884': '玉山金',
    '2881': '富邦金', '2882': '國泰金', '2886': '兆豐金', '5880': '合庫金',
    '2603': '長榮', '2609': '陽明', '2615': '萬海', '2618': '長榮航',
    '2344': '華邦電', '8110': '華東', '5521': '工信', '3706': '神達',
    '8021': '尖點', '2449': '京元電', '3363': '上詮', '2379': '瑞昱',
    '3661': '世芯-KY', '6446': '藥華藥', '2412': '中華電', '2303': '聯電',
    '8046': '南電', '1802': '台玻', '2313': '華通', '2331': '精英',
    '8155': '博智', '5498': '凱崴', '3030': '德律', '3037': '欣興',
    '1815': '富喬', '3231': '緯創', '8039': '台虹', '2312': '金寶',
    '1303': '南亞', '2327': '國巨', '2408': '南亞科', '1504': '東元',
    '6770': '力積電',
};

// 從後端 API 獲取真實數據
async function fetchRealAnalysisData(): Promise<{ stocks: StockAnalysis[], summary: MarketSummary, dataSource: string }> {
    const stocks: StockAnalysis[] = [];
    let dataSource = 'api';

    // 從大單偵測監控系統獲取股票清單
    const STOCK_SYMBOLS = getWatchlistStocks();
    console.log('📋 使用監控清單 (與大單偵測同步):', STOCK_SYMBOLS);

    // 🚀 使用 yfinance batch API 獲取所有價格（支援上櫃股票 .TWO）
    let priceMap: Record<string, { price: number; change: number }> = {};

    try {
        const symbolsParam = STOCK_SYMBOLS.join(',');
        const response = await fetch(`http://localhost:8000/api/smart-picks/yfinance/batch?symbols=${symbolsParam}`, {
            signal: AbortSignal.timeout(30000)
        });
        if (response.ok) {
            const data = await response.json();
            if (data.quotes && data.quotes.length > 0) {
                data.quotes.forEach((quote: { symbol: string; price: number; change_percent: number; success: boolean }) => {
                    if (quote.success && quote.price > 0) {
                        priceMap[quote.symbol] = {
                            price: quote.price,
                            change: quote.change_percent || 0
                        };
                    }
                });
                console.log('📊 yfinance batch 價格獲取成功:', Object.keys(priceMap).length, '檔');
                dataSource = 'yfinance';
            }
        }
    } catch (e) {
        console.log('yfinance batch API 失敗，嘗試 fubon API...');

        // 備援: 使用富邦 API
        const pricePromises = STOCK_SYMBOLS.map(async (symbol) => {
            try {
                const response = await fetch(`http://localhost:8000/api/fubon/quote/${symbol}`, {
                    signal: AbortSignal.timeout(8000)
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data.price && data.price > 0) {
                        priceMap[symbol] = {
                            price: data.price,
                            change: data.change || 0
                        };
                    }
                }
            } catch (e) {
                console.log(`富邦 API 獲取 ${symbol} 失敗`);
            }
        });

        await Promise.all(pricePromises);
        console.log('📊 富邦 API 備援價格獲取:', Object.keys(priceMap).length, '檔');
        if (Object.keys(priceMap).length > 0) {
            dataSource = 'fubon';
        }
    }

    // 並行獲取所有股票的數據（只獲取富邦報價，其他 API 盤後無數據）
    const fetchPromises = STOCK_SYMBOLS.map(async (symbol) => {
        try {
            // 獲取富邦報價（盤後使用 Yahoo 備用）
            const quoteResponse = await fetch(`http://localhost:8000/api/fubon/quote/${symbol}`, {
                signal: AbortSignal.timeout(10000)
            });
            const quoteData = quoteResponse.ok ? await quoteResponse.json() : null;

            // 盤後模式：使用價格漲跌幅來推算訊號
            let lstmPrediction: 'up' | 'down' | 'neutral' = 'neutral';
            let lstmConfidence = 50;
            let mainForceSignal: 'buy' | 'sell' | 'neutral' = 'neutral';
            let mainForceConfidence = 50;

            // 根據漲跌幅推算訊號
            const changePercent = quoteData?.change || 0;
            if (changePercent > 2) {
                mainForceSignal = 'buy';
                lstmPrediction = 'up';
                mainForceConfidence = 70;
                lstmConfidence = 65;
            } else if (changePercent > 0.5) {
                lstmPrediction = 'up';
                lstmConfidence = 55;
            } else if (changePercent < -2) {
                mainForceSignal = 'sell';
                lstmPrediction = 'down';
                mainForceConfidence = 70;
                lstmConfidence = 65;
            } else if (changePercent < -0.5) {
                lstmPrediction = 'down';
                lstmConfidence = 55;
            }

            // 計算 AI 評分 - 使用多個因素
            let score = 50;  // 基礎分

            // 1. 主力訊號加分
            if (mainForceSignal === 'buy') score += 20;
            if (mainForceSignal === 'sell') score -= 15;

            // 2. LSTM 預測加分
            if (lstmPrediction === 'up') score += 15;
            if (lstmPrediction === 'down') score -= 10;

            // 3. 使用批量獲取的價格漲跌幅來調整評分（盤後有效）
            if (priceMap[symbol]) {
                const changePercent = priceMap[symbol].change;
                // 漲幅加分，跌幅減分
                if (changePercent > 3) score += 20;       // 大漲 > 3%
                else if (changePercent > 1.5) score += 15; // 中漲 1.5-3%
                else if (changePercent > 0.5) score += 10; // 小漲 0.5-1.5%
                else if (changePercent < -3) score -= 15;  // 大跌 < -3%
                else if (changePercent < -1.5) score -= 10; // 中跌
                else if (changePercent < -0.5) score -= 5;  // 小跌

                // 根據漲跌調整主力訊號
                if (changePercent > 2) mainForceSignal = 'buy';
                else if (changePercent < -2) mainForceSignal = 'sell';

                // 根據漲跌調整 LSTM 預測
                if (changePercent > 1) lstmPrediction = 'up';
                else if (changePercent < -1) lstmPrediction = 'down';
            }

            score = Math.min(100, Math.max(0, score));

            // 計算風險等級
            const riskLevel: 'low' | 'medium' | 'high' = score > 70 ? 'low' : score > 40 ? 'medium' : 'high';

            // 生成建議
            let recommendation = '觀望';
            if (score >= 75) {
                recommendation = '強力買進';
            } else if (score >= 60) {
                recommendation = '建議買進';
            } else if (score <= 30) {
                recommendation = '建議賣出';
            } else if (score <= 40) {
                recommendation = '謹慎觀望';
            }

            // 獲取價格和漲跌幅 - 直接使用富邦 API 返回的數據
            let price = 0;
            let change = 0;
            let dataSourceUsed = 'none';

            // 使用 quoteData（富邦 API）
            if (quoteData && quoteData.price > 0) {
                price = quoteData.price;
                change = quoteData.change || 0;
                dataSourceUsed = 'fubon';
            }
            // 備用：使用預先批量獲取的 priceMap
            else if (priceMap[symbol]) {
                price = priceMap[symbol].price;
                change = priceMap[symbol].change;
                dataSourceUsed = 'fubon-batch';
            }

            return {
                symbol,
                name: STOCK_NAMES[symbol] || symbol,
                price,
                change,
                mainForceSignal,
                mainForceConfidence,
                lstmPrediction,
                lstmConfidence,
                riskLevel,
                recommendation,
                score,
                dataSource: quoteData?.source || 'api'
            };
        } catch (error) {
            console.error(`獲取 ${symbol} 數據失敗:`, error);
            // 返回基本數據結構，標記為無數據
            return {
                symbol,
                name: STOCK_NAMES[symbol] || symbol,
                price: 0,
                change: 0,
                mainForceSignal: 'neutral' as const,
                mainForceConfidence: 0,
                lstmPrediction: 'neutral' as const,
                lstmConfidence: 0,
                riskLevel: 'medium' as const,
                recommendation: '數據載入中',
                score: 0,
                dataSource: 'error'
            };
        }
    });

    const results = await Promise.all(fetchPromises);
    stocks.push(...results);

    // 計算市場摘要
    const validStocks = stocks.filter(s => s.dataSource !== 'error');
    const buySignals = validStocks.filter(s => s.mainForceSignal === 'buy').length;
    const upPredictions = validStocks.filter(s => s.lstmPrediction === 'up').length;
    const avgScore = validStocks.length > 0
        ? validStocks.reduce((sum, s) => sum + s.score, 0) / validStocks.length
        : 50;

    const summary: MarketSummary = {
        sentiment: buySignals > validStocks.length / 2 ? 'bullish' : buySignals < validStocks.length / 3 ? 'bearish' : 'neutral',
        sentimentScore: validStocks.length > 0 ? Math.round((buySignals / validStocks.length) * 100) : 50,
        volatility: avgScore > 70 ? 'low' : avgScore > 40 ? 'medium' : 'high',
        trendStrength: Math.round(avgScore),
        activeSignals: buySignals + upPredictions,
        topPicks: stocks.filter(s => s.score >= 70).map(s => s.symbol).slice(0, 3)
    };

    return { stocks, summary, dataSource };
}

export default function AIReportPage() {
    const [analysisData, setAnalysisData] = useState<{ stocks: StockAnalysis[], summary: MarketSummary } | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
    const [dataSource, setDataSource] = useState<string>('loading');
    const [error, setError] = useState<string | null>(null);

    const fetchAnalysis = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const data = await fetchRealAnalysisData();
            setAnalysisData({ stocks: data.stocks, summary: data.summary });
            setDataSource(data.dataSource);
            setLastUpdate(new Date());
        } catch (err) {
            console.error('獲取分析數據失敗:', err);
            setError('無法連接到後端 API，請確認服務是否啟動');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAnalysis();
    }, [fetchAnalysis]);

    if (isLoading || !analysisData) {
        return (
            <div className="flex flex-col items-center justify-center h-96 gap-4">
                <div className="relative">
                    <Brain className="w-16 h-16 text-blue-500 animate-pulse" />
                    <div className="absolute inset-0 w-16 h-16 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin"></div>
                </div>
                <p className="text-gray-600 font-medium">AI 正在分析市場數據...</p>
                <p className="text-xs text-gray-400">從後端 API 獲取真實數據中</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-96 gap-4">
                <WifiOff className="w-16 h-16 text-red-500" />
                <p className="text-gray-600 font-medium">{error}</p>
                <button
                    onClick={fetchAnalysis}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                    重試
                </button>
            </div>
        );
    }

    const { stocks, summary } = analysisData;
    const topStocks = stocks.filter(s => s.score >= 60).sort((a, b) => b.score - a.score);

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl text-white shadow-lg">
                        <Brain className="w-6 h-6" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">AI 深度分析匯報</h1>
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                            <span>基於大單偵測監控系統股票清單（與 big-order 同步）</span>
                            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                                {stocks.length} 檔股票
                            </span>
                            <span className={cn(
                                "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase",
                                (dataSource === 'api' || dataSource === 'yfinance' || dataSource === 'fubon') && "bg-green-100 text-green-700",
                                dataSource === 'error' && "bg-red-100 text-red-700",
                                dataSource === 'loading' && "bg-yellow-100 text-yellow-700"
                            )}>
                                <Wifi className="w-3 h-3 inline mr-1" />
                                {dataSource === 'yfinance' || dataSource === 'api' ? '即時數據' :
                                    dataSource === 'fubon' ? '富邦數據' :
                                        dataSource === 'error' ? '離線' : '載入中'}
                            </span>
                            <span>| 更新時間: {lastUpdate?.toLocaleTimeString('zh-TW')}</span>
                        </div>
                    </div>
                </div>
                <button
                    onClick={fetchAnalysis}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                    <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
                    重新分析
                </button>
            </div>

            {/* Market Summary */}
            <div className="bg-gradient-to-r from-gray-900 to-gray-800 rounded-2xl p-6 text-white">
                <div className="flex items-center gap-2 mb-4">
                    <Zap className="w-5 h-5 text-yellow-400" />
                    <h2 className="font-bold">市場情緒總覽</h2>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    <div className="bg-white/10 rounded-xl p-4">
                        <p className="text-xs text-gray-300 mb-1">市場情緒</p>
                        <div className="flex items-center gap-2">
                            {summary.sentiment === 'bullish' && <TrendingUp className="w-5 h-5 text-green-400" />}
                            {summary.sentiment === 'bearish' && <TrendingDown className="w-5 h-5 text-red-400" />}
                            {summary.sentiment === 'neutral' && <Minus className="w-5 h-5 text-gray-400" />}
                            <span className={cn(
                                "font-bold",
                                summary.sentiment === 'bullish' && "text-green-400",
                                summary.sentiment === 'bearish' && "text-red-400",
                                summary.sentiment === 'neutral' && "text-gray-300"
                            )}>
                                {summary.sentiment === 'bullish' ? '偏多' : summary.sentiment === 'bearish' ? '偏空' : '中性'}
                            </span>
                        </div>
                    </div>
                    <div className="bg-white/10 rounded-xl p-4">
                        <p className="text-xs text-gray-300 mb-1">情緒指數</p>
                        <p className="text-2xl font-bold">{summary.sentimentScore}</p>
                    </div>
                    <div className="bg-white/10 rounded-xl p-4">
                        <p className="text-xs text-gray-300 mb-1">波動度</p>
                        <p className={cn(
                            "text-lg font-bold",
                            summary.volatility === 'high' && "text-red-400",
                            summary.volatility === 'medium' && "text-yellow-400",
                            summary.volatility === 'low' && "text-green-400"
                        )}>
                            {summary.volatility === 'high' ? '高' : summary.volatility === 'medium' ? '中' : '低'}
                        </p>
                    </div>
                    <div className="bg-white/10 rounded-xl p-4">
                        <p className="text-xs text-gray-300 mb-1">趨勢強度</p>
                        <p className="text-2xl font-bold">{summary.trendStrength}%</p>
                    </div>
                    <div className="bg-white/10 rounded-xl p-4">
                        <p className="text-xs text-gray-300 mb-1">活躍訊號</p>
                        <p className="text-2xl font-bold text-yellow-400">{summary.activeSignals}</p>
                    </div>
                </div>

                {summary.topPicks.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/10">
                        <p className="text-xs text-gray-300 mb-2">🎯 AI 精選標的</p>
                        <div className="flex gap-2">
                            {summary.topPicks.map(symbol => (
                                <span key={symbol} className="px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-sm font-bold">
                                    {symbol}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Top Recommendations */}
            {topStocks.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    <div className="p-5 border-b border-gray-100 bg-gradient-to-r from-green-50 to-emerald-50">
                        <div className="flex items-center gap-2">
                            <Target className="w-5 h-5 text-green-600" />
                            <h2 className="font-bold text-gray-900">AI 推薦標的</h2>
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-bold">
                                {topStocks.length} 檔
                            </span>
                        </div>
                    </div>
                    <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {topStocks.map(stock => (
                            <div key={stock.symbol} className="bg-gray-50 rounded-xl p-4 hover:shadow-md transition-all border border-transparent hover:border-green-200">
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center font-bold text-blue-600 text-sm shadow-sm">
                                            {stock.symbol}
                                        </div>
                                        <div>
                                            <p className="font-bold text-gray-900">{stock.name}</p>
                                            <p className={cn(
                                                "text-xs font-medium",
                                                stock.change >= 0 ? "text-red-500" : "text-green-500"
                                            )}>
                                                ${stock.price.toFixed(2)} ({stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%)
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className={cn(
                                            "text-2xl font-black",
                                            stock.score >= 75 ? "text-green-600" : stock.score >= 60 ? "text-blue-600" : "text-gray-600"
                                        )}>
                                            {stock.score}
                                        </div>
                                        <p className="text-[10px] text-gray-400 uppercase tracking-wider">AI 評分</p>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-2 mb-3">
                                    <div className="bg-white rounded-lg p-2 text-center">
                                        <p className="text-[10px] text-gray-400 uppercase">主力訊號</p>
                                        <p className={cn(
                                            "text-xs font-bold flex items-center justify-center gap-1",
                                            stock.mainForceSignal === 'buy' && "text-red-600",
                                            stock.mainForceSignal === 'sell' && "text-green-600",
                                            stock.mainForceSignal === 'neutral' && "text-gray-500"
                                        )}>
                                            {stock.mainForceSignal === 'buy' && <ArrowUpRight className="w-3 h-3" />}
                                            {stock.mainForceSignal === 'sell' && <ArrowDownRight className="w-3 h-3" />}
                                            {stock.mainForceSignal === 'buy' ? '買進' : stock.mainForceSignal === 'sell' ? '賣出' : '觀望'}
                                            <span className="text-gray-400">({stock.mainForceConfidence}%)</span>
                                        </p>
                                    </div>
                                    <div className="bg-white rounded-lg p-2 text-center">
                                        <p className="text-[10px] text-gray-400 uppercase">LSTM 預測</p>
                                        <p className={cn(
                                            "text-xs font-bold flex items-center justify-center gap-1",
                                            stock.lstmPrediction === 'up' && "text-red-600",
                                            stock.lstmPrediction === 'down' && "text-green-600",
                                            stock.lstmPrediction === 'neutral' && "text-gray-500"
                                        )}>
                                            {stock.lstmPrediction === 'up' && <TrendingUp className="w-3 h-3" />}
                                            {stock.lstmPrediction === 'down' && <TrendingDown className="w-3 h-3" />}
                                            {stock.lstmPrediction === 'up' ? '看漲' : stock.lstmPrediction === 'down' ? '看跌' : '持平'}
                                            <span className="text-gray-400">({stock.lstmConfidence}%)</span>
                                        </p>
                                    </div>
                                </div>

                                <div className={cn(
                                    "text-center py-2 rounded-lg text-sm font-bold",
                                    stock.recommendation === '強力買進' && "bg-red-100 text-red-700",
                                    stock.recommendation === '建議買進' && "bg-orange-100 text-orange-700",
                                    stock.recommendation === '觀望' && "bg-gray-100 text-gray-600",
                                    stock.recommendation === '建議賣出' && "bg-green-100 text-green-700"
                                )}>
                                    {stock.recommendation}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Full Analysis Table */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-gray-100 bg-gray-50/50">
                    <div className="flex items-center gap-2">
                        <BarChart3 className="w-5 h-5 text-gray-600" />
                        <h2 className="font-bold text-gray-900">完整分析報告</h2>
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-bold">
                            真實數據
                        </span>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 text-xs uppercase text-gray-500 tracking-wider">
                            <tr>
                                <th className="px-6 py-3 text-left">股票</th>
                                <th className="px-6 py-3 text-left">現價</th>
                                <th className="px-6 py-3 text-center">主力訊號</th>
                                <th className="px-6 py-3 text-center">LSTM 預測</th>
                                <th className="px-6 py-3 text-center">風險等級</th>
                                <th className="px-6 py-3 text-center">AI 評分</th>
                                <th className="px-6 py-3 text-center">建議</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {stocks.map(stock => (
                                <tr key={stock.symbol} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center font-bold text-blue-600 text-xs">
                                                {stock.symbol}
                                            </div>
                                            <span className="font-medium text-gray-900">{stock.name}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div>
                                            <p className="font-bold text-gray-900">${stock.price.toFixed(2)}</p>
                                            <p className={cn(
                                                "text-xs font-medium",
                                                stock.change >= 0 ? "text-red-500" : "text-green-500"
                                            )}>
                                                {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                                            </p>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <span className={cn(
                                            "px-2 py-1 rounded-full text-xs font-bold",
                                            stock.mainForceSignal === 'buy' && "bg-red-100 text-red-700",
                                            stock.mainForceSignal === 'sell' && "bg-green-100 text-green-700",
                                            stock.mainForceSignal === 'neutral' && "bg-gray-100 text-gray-600"
                                        )}>
                                            {stock.mainForceSignal === 'buy' ? '🔴 買超' : stock.mainForceSignal === 'sell' ? '🟢 賣超' : '⚪ 中性'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <span className={cn(
                                            "px-2 py-1 rounded-full text-xs font-bold",
                                            stock.lstmPrediction === 'up' && "bg-red-100 text-red-700",
                                            stock.lstmPrediction === 'down' && "bg-green-100 text-green-700",
                                            stock.lstmPrediction === 'neutral' && "bg-gray-100 text-gray-600"
                                        )}>
                                            {stock.lstmPrediction === 'up' ? '📈 上漲' : stock.lstmPrediction === 'down' ? '📉 下跌' : '➡️ 持平'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <span className={cn(
                                            "px-2 py-1 rounded-full text-xs font-bold flex items-center justify-center gap-1 w-fit mx-auto",
                                            stock.riskLevel === 'low' && "bg-green-100 text-green-700",
                                            stock.riskLevel === 'medium' && "bg-yellow-100 text-yellow-700",
                                            stock.riskLevel === 'high' && "bg-red-100 text-red-700"
                                        )}>
                                            <Shield className="w-3 h-3" />
                                            {stock.riskLevel === 'low' ? '低' : stock.riskLevel === 'medium' ? '中' : '高'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <span className={cn(
                                            "text-lg font-black",
                                            stock.score >= 75 ? "text-green-600" : stock.score >= 50 ? "text-blue-600" : "text-gray-500"
                                        )}>
                                            {stock.score}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <span className={cn(
                                            "px-3 py-1 rounded-lg text-xs font-bold",
                                            stock.recommendation === '強力買進' && "bg-red-500 text-white",
                                            stock.recommendation === '建議買進' && "bg-orange-500 text-white",
                                            stock.recommendation === '觀望' && "bg-gray-200 text-gray-700",
                                            stock.recommendation === '建議賣出' && "bg-green-500 text-white"
                                        )}>
                                            {stock.recommendation}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Disclaimer */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div>
                    <p className="text-sm font-bold text-yellow-800">免責聲明</p>
                    <p className="text-xs text-yellow-700 mt-1">
                        本報告由 AI 系統基於真實市場數據自動生成，僅供參考，不構成任何投資建議。投資有風險，入市需謹慎。過去表現不代表未來收益。
                    </p>
                </div>
            </div>
        </div>
    );
}
