'use client';

import { useState, useEffect } from 'react';

interface Expert {
    name: string;
    score: number;
    weight: number;
    status: string;
    evidence: string[];
    confidence: number;
}

interface MainforceData {
    symbol: string;
    stockName: string;
    overallScore: number;
    action: string;
    confidence: number;
    timestamp: string;
    experts: Expert[];
    actionReason: string;
}

interface InvestmentSignal {
    ticker: string;
    name: string;
    signal: string;
    score: number;
    confidence: number;
    action: string;
    reasons: string[];
}

const WATCH_LIST = ['2330', '2454', '2382', '3231', '6669', '2317', '3008', '2308'];

export default function MainforcePage() {
    const [selectedStock, setSelectedStock] = useState('2330');
    const [mainforceData, setMainforceData] = useState<MainforceData | null>(null);
    const [signalData, setSignalData] = useState<InvestmentSignal | null>(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<'mainforce' | 'signal'>('mainforce');

    const fetchMainforce = async (symbol: string) => {
        setLoading(true);
        try {
            const res = await fetch(`http://localhost:8000/api/analysis/mainforce/${symbol}`);
            const data = await res.json();
            setMainforceData(data);
        } catch (error) {
            console.error('Error fetching mainforce:', error);
        }
        setLoading(false);
    };

    const fetchSignal = async (symbol: string) => {
        try {
            const res = await fetch(`http://localhost:8000/api/economic-cycle/signals/stock/${symbol}`);
            const data = await res.json();
            if (data.success) {
                setSignalData(data.signal);
            }
        } catch (error) {
            console.error('Error fetching signal:', error);
        }
    };

    useEffect(() => {
        fetchMainforce(selectedStock);
        fetchSignal(selectedStock);
    }, [selectedStock]);

    const getActionColor = (action: string) => {
        switch (action) {
            case 'entry': return 'text-green-400 bg-green-900/30';
            case 'exit': return 'text-red-400 bg-red-900/30';
            default: return 'text-yellow-400 bg-yellow-900/30';
        }
    };

    const getSignalColor = (signal: string) => {
        if (signal.includes('買進')) return 'text-green-400 bg-green-900/30';
        if (signal.includes('賣出')) return 'text-red-400 bg-red-900/30';
        return 'text-yellow-400 bg-yellow-900/30';
    };

    const getSignalEmoji = (signal: string) => {
        if (signal === '強力買進') return '🔥';
        if (signal === '買進') return '✅';
        if (signal === '持有') return '⏸️';
        if (signal === '賣出') return '⚠️';
        if (signal === '強力賣出') return '🔴';
        return '📊';
    };

    return (
        <div className="min-h-screen bg-gray-900 text-white p-6">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2">🎯 主力偵測 & 投資信號</h1>
                <p className="text-gray-400">15位專家分析 + AI投資信號產生器</p>
            </div>

            {/* Stock Selector */}
            <div className="mb-6">
                <div className="flex flex-wrap gap-2">
                    {WATCH_LIST.map((symbol) => (
                        <button
                            key={symbol}
                            onClick={() => setSelectedStock(symbol)}
                            className={`px-4 py-2 rounded-lg font-medium transition-all ${selectedStock === symbol
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                                }`}
                        >
                            {symbol}
                        </button>
                    ))}
                </div>
            </div>

            {/* Tab Selector */}
            <div className="mb-6">
                <div className="flex gap-2">
                    <button
                        onClick={() => setActiveTab('mainforce')}
                        className={`px-6 py-3 rounded-lg font-medium transition-all ${activeTab === 'mainforce'
                                ? 'bg-purple-600 text-white'
                                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                            }`}
                    >
                        🔍 主力偵測
                    </button>
                    <button
                        onClick={() => setActiveTab('signal')}
                        className={`px-6 py-3 rounded-lg font-medium transition-all ${activeTab === 'signal'
                                ? 'bg-purple-600 text-white'
                                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                            }`}
                    >
                        🎯 投資信號
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                </div>
            ) : (
                <>
                    {/* Mainforce Tab */}
                    {activeTab === 'mainforce' && mainforceData && (
                        <div className="space-y-6">
                            {/* Overview Card */}
                            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                                <div className="flex items-center justify-between mb-4">
                                    <div>
                                        <h2 className="text-2xl font-bold">{mainforceData.stockName}</h2>
                                        <p className="text-gray-400">{mainforceData.symbol}</p>
                                    </div>
                                    <div className={`px-6 py-3 rounded-lg font-bold text-xl ${getActionColor(mainforceData.action)}`}>
                                        {mainforceData.action === 'entry' ? '🟢 主力進場' :
                                            mainforceData.action === 'exit' ? '🔴 主力出場' : '🟡 觀望'}
                                    </div>
                                </div>

                                <div className="grid grid-cols-3 gap-4 mb-4">
                                    <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                                        <div className="text-3xl font-bold text-blue-400">
                                            {(mainforceData.overallScore * 100).toFixed(0)}
                                        </div>
                                        <div className="text-gray-400 text-sm">綜合評分</div>
                                    </div>
                                    <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                                        <div className="text-3xl font-bold text-green-400">
                                            {(mainforceData.confidence * 100).toFixed(0)}%
                                        </div>
                                        <div className="text-gray-400 text-sm">信心度</div>
                                    </div>
                                    <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                                        <div className="text-3xl font-bold text-purple-400">15</div>
                                        <div className="text-gray-400 text-sm">專家分析</div>
                                    </div>
                                </div>

                                <div className="bg-gray-700/30 rounded-lg p-4">
                                    <p className="text-gray-300">{mainforceData.actionReason}</p>
                                </div>
                            </div>

                            {/* Expert Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {mainforceData.experts.map((expert, index) => (
                                    <div key={index} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                                        <div className="flex items-center justify-between mb-3">
                                            <h3 className="font-semibold">{expert.name}</h3>
                                            <span className={`px-2 py-1 rounded text-xs ${expert.status === 'bullish' ? 'bg-green-900/50 text-green-400' :
                                                    expert.status === 'bearish' ? 'bg-red-900/50 text-red-400' :
                                                        'bg-yellow-900/50 text-yellow-400'
                                                }`}>
                                                {expert.status === 'bullish' ? '看多' :
                                                    expert.status === 'bearish' ? '看空' : '中性'}
                                            </span>
                                        </div>

                                        <div className="mb-3">
                                            <div className="flex justify-between text-sm mb-1">
                                                <span className="text-gray-400">評分</span>
                                                <span>{(expert.score * 100).toFixed(0)}</span>
                                            </div>
                                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full ${expert.score > 0.7 ? 'bg-green-500' :
                                                            expert.score > 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                                                        }`}
                                                    style={{ width: `${expert.score * 100}%` }}
                                                />
                                            </div>
                                        </div>

                                        <div className="text-sm text-gray-400">
                                            {expert.evidence.map((e, i) => (
                                                <div key={i} className="flex items-start gap-1 mb-1">
                                                    <span>•</span>
                                                    <span>{e}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Signal Tab */}
                    {activeTab === 'signal' && signalData && (
                        <div className="space-y-6">
                            {/* Signal Overview */}
                            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <h2 className="text-2xl font-bold">{signalData.name}</h2>
                                        <p className="text-gray-400">{signalData.ticker}</p>
                                    </div>
                                    <div className={`px-6 py-3 rounded-lg font-bold text-xl ${getSignalColor(signalData.signal)}`}>
                                        {getSignalEmoji(signalData.signal)} {signalData.signal}
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                    <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                                        <div className="text-3xl font-bold text-blue-400">
                                            {signalData.score.toFixed(0)}
                                        </div>
                                        <div className="text-gray-400 text-sm">綜合評分</div>
                                    </div>
                                    <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                                        <div className="text-3xl font-bold text-green-400">
                                            {(signalData.confidence * 100).toFixed(0)}%
                                        </div>
                                        <div className="text-gray-400 text-sm">信心度</div>
                                    </div>
                                    <div className="bg-gray-700/50 rounded-lg p-4 text-center col-span-2">
                                        <div className="text-xl font-bold text-purple-400">
                                            {signalData.action}
                                        </div>
                                        <div className="text-gray-400 text-sm">操作建議</div>
                                    </div>
                                </div>

                                {/* Reasons */}
                                <div className="bg-gray-700/30 rounded-lg p-4">
                                    <h3 className="font-semibold mb-3">📝 分析理由</h3>
                                    <div className="space-y-2">
                                        {signalData.reasons.map((reason, i) => (
                                            <div key={i} className="flex items-start gap-2 text-gray-300">
                                                <span className="text-blue-400">•</span>
                                                <span>{reason}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Quick Actions */}
                            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                                <h3 className="font-semibold mb-4">⚡ 快速操作</h3>
                                <div className="flex gap-4">
                                    <button className="flex-1 bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg font-medium transition-colors">
                                        加入觀察清單
                                    </button>
                                    <button className="flex-1 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-medium transition-colors">
                                        詳細分析報告
                                    </button>
                                    <button className="flex-1 bg-purple-600 hover:bg-purple-700 px-6 py-3 rounded-lg font-medium transition-colors">
                                        設定警報
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Timestamp */}
            {mainforceData && (
                <div className="mt-6 text-center text-gray-500 text-sm">
                    最後更新: {new Date(mainforceData.timestamp).toLocaleString('zh-TW')}
                </div>
            )}
        </div>
    );
}
