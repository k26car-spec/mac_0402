'use client';

import { useState, useEffect } from 'react';

interface StockSignal {
    ticker: string;
    name: string;
    signal: string;
    score: number;
    confidence: number;
    action: string;
    target_weight: number;
    stop_loss: number;
    take_profit: number;
    time_horizon: string;
    reasons: string[];
    risks: string[];
    // 6 維度評分
    technical_score: number;
    economic_cycle_score: number;
    industry_power_score: number;
    financial_score: number;
    trend_exposure: number;
    order_momentum: number;
}

interface Recommendation {
    risk_profile: string;
    total_capital: number;
    market_condition: string;
    equity_allocation: number;
    bond_allocation: number;
    cash_allocation: number;
    alternative_allocation: number;
    stock_recommendations: StockSignal[];
    overall_action: string;
    key_themes: string[];
    risk_warnings: string[];
}

interface TrendInfo {
    trend: string;
    adoption_rate: number;
    growth_forecast: number;
    impact_score: number;
}

// 主題股票清單
const THEME_STOCKS: Record<string, string[]> = {
    "AI伺服器": ["2382", "3231", "6669", "2356", "3017", "2376", "3443", "6515", "3661", "2330", "2317", "2308", "2345"],
    "矽光子": ["3324", "6285", "3037", "2327", "3533", "6409", "3105", "8299", "2449"],
    "半導體": ["2330", "2454", "2303", "3034", "2379", "3711", "2408", "3529", "3443", "3661"],
    "電動車": ["2317", "2308", "2327", "3037"],
    "5G網通": ["2454", "2379", "6285", "2345", "8086"],
    "國防軍工": ["2634", "2208", "2231", "1476", "2023"],
    "機器人": ["2317", "2049", "4523", "3515", "6121"],
    "低軌衛星": ["3704", "2455", "3682", "6285", "2345"],
    "精選8檔": ["2330", "2454", "2382", "3231", "6669", "2317", "3008", "2308"],
    "📋 我的監控清單": [],  // 動態載入
};

export default function EconomicCyclePage() {
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<'signals' | 'allocation' | 'electronics' | 'technical'>('signals');
    const [riskProfile, setRiskProfile] = useState('MODERATE');
    const [capital, setCapital] = useState(1000000);
    const [selectedTheme, setSelectedTheme] = useState('精選8檔');
    const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
    const [trends, setTrends] = useState<Record<string, TrendInfo>>({});
    const [selectedStock, setSelectedStock] = useState('2330');
    const [technicalData, setTechnicalData] = useState<any>(null);
    const [themeStocks, setThemeStocks] = useState<Record<string, string[]>>(THEME_STOCKS);
    const [watchlistLoaded, setWatchlistLoaded] = useState(false);

    // 載入監控清單 (優先從 big-order 的 localStorage 讀取)
    const fetchWatchlist = async () => {
        // 1. 先嘗試從 localStorage 讀取 (與 big-order 頁面共用)
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('bigorder_watchlist');
            if (saved) {
                try {
                    const watchlist = JSON.parse(saved);
                    if (watchlist && watchlist.length > 0) {
                        const stockCodes = watchlist.map((s: any) => s.code);
                        setThemeStocks(prev => ({
                            ...prev,
                            "📋 我的監控清單": stockCodes
                        }));
                        setWatchlistLoaded(true);
                        console.log('已從 big-order 載入監控清單:', stockCodes);
                        return; // 成功就返回
                    }
                } catch (e) {
                    console.log('localStorage 解析失敗');
                }
            }
        }

        // 2. 備援：嘗試從主控台 API 讀取
        try {
            const res = await fetch('http://127.0.0.1:8082/api/stocks');
            const data = await res.json();
            if (data.stocks && data.stocks.length > 0) {
                const stockCodes = data.stocks.map((s: any) => s.code.replace('.TW', ''));
                setThemeStocks(prev => ({
                    ...prev,
                    "📋 我的監控清單": stockCodes
                }));
                setWatchlistLoaded(true);
                console.log('已從主控台載入監控清單:', stockCodes);
            }
        } catch (error) {
            console.log('無法載入監控清單，等待 big-order 頁面設定');
        }
    };

    // 初始載入監控清單
    useEffect(() => {
        fetchWatchlist();

        // 監聽 localStorage 變化 (當 big-order 頁面修改時)
        const handleStorageChange = (e: StorageEvent) => {
            if (e.key === 'bigorder_watchlist') {
                fetchWatchlist();
            }
        };
        window.addEventListener('storage', handleStorageChange);
        return () => window.removeEventListener('storage', handleStorageChange);
    }, []);

    const generateSignals = async () => {
        setLoading(true);
        try {
            let focusStocks = themeStocks[selectedTheme];

            // 如果選擇監控清單且還沒載入，先嘗試載入
            if (selectedTheme === '📋 我的監控清單' && (!focusStocks || focusStocks.length === 0)) {
                await fetchWatchlist();
                focusStocks = themeStocks['📋 我的監控清單'] || themeStocks['精選8檔'];
            }

            if (!focusStocks || focusStocks.length === 0) {
                focusStocks = themeStocks['精選8檔'];
            }

            const res = await fetch('http://localhost:8000/api/economic-cycle/signals/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    risk_profile: riskProfile,
                    initial_capital: capital,
                    focus_stocks: focusStocks
                })
            });
            const data = await res.json();
            if (data.success) {
                setRecommendation(data.recommendation);
            }
        } catch (error) {
            console.error('Error generating signals:', error);
        }
        setLoading(false);
    };

    const fetchTrends = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/economic-cycle/electronics/trends');
            const data = await res.json();
            if (data.success) {
                setTrends(data.trends);
            }
        } catch (error) {
            console.error('Error fetching trends:', error);
        }
    };

    const fetchTechnical = async (ticker: string) => {
        try {
            const res = await fetch(`http://localhost:8000/api/economic-cycle/technical/analyze/${ticker}`);
            const data = await res.json();
            if (data.success) {
                setTechnicalData(data.analysis);
            }
        } catch (error) {
            console.error('Error fetching technical:', error);
        }
    };

    useEffect(() => {
        if (activeTab === 'electronics') {
            fetchTrends();
        }
        if (activeTab === 'technical') {
            fetchTechnical(selectedStock);
        }
    }, [activeTab, selectedStock]);

    const getSignalColor = (signal: string) => {
        if (signal.includes('買進')) return 'text-green-700 bg-green-50 border-green-200';
        if (signal.includes('賣出')) return 'text-red-700 bg-red-50 border-red-200';
        return 'text-yellow-700 bg-yellow-50 border-yellow-200';
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
        <div className="space-y-6">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900">
                    🌐 循環驅動多因子投資系統
                </h1>
                <p className="text-gray-600 mt-2">整合技術分析、資產配置、電子股監測，產生最終投資信號</p>
            </div>

            {/* Tab Navigation */}
            <div className="mb-6 flex flex-wrap gap-2">
                {[
                    { id: 'signals', label: '🎯 投資信號', desc: '買進/賣出/持有' },
                    { id: 'allocation', label: '⚖️ 資產配置', desc: '股債現金比例' },
                    { id: 'electronics', label: '📱 電子股監測', desc: 'AI/EV趨勢' },
                    { id: 'technical', label: '📈 技術分析', desc: '五年區間+指標' },
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        className={`px-6 py-3 rounded-xl font-medium transition-all border ${activeTab === tab.id
                            ? 'bg-blue-600 border-blue-500 text-white shadow-lg'
                            : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300'
                            }`}
                    >
                        <div>{tab.label}</div>
                        <div className="text-xs opacity-70">{tab.desc}</div>
                    </button>
                ))}
            </div>

            {/* Signals Tab */}
            {activeTab === 'signals' && (
                <div className="space-y-6">
                    {/* Controls */}
                    <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
                        {/* Theme Selection */}
                        <div className="mb-4">
                            <label className="block text-sm text-gray-600 font-medium mb-2">📌 選擇主題概念股</label>
                            <div className="flex flex-wrap gap-2">
                                {Object.keys(themeStocks).map((theme) => (
                                    <button
                                        key={theme}
                                        onClick={() => setSelectedTheme(theme)}
                                        className={`px-4 py-2 rounded-lg font-medium transition-all ${selectedTheme === theme
                                            ? 'bg-blue-600 text-white'
                                            : theme === '📋 我的監控清單'
                                                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        {theme} ({themeStocks[theme]?.length || 0})
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                            <div>
                                <label className="block text-sm text-gray-600 font-medium mb-2">風險偏好</label>
                                <select
                                    value={riskProfile}
                                    onChange={(e) => setRiskProfile(e.target.value)}
                                    className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="CONSERVATIVE">保守型</option>
                                    <option value="MODERATE">穩健型</option>
                                    <option value="AGGRESSIVE">積極型</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm text-gray-600 font-medium mb-2">投資資金 (NT$)</label>
                                <input
                                    type="number"
                                    value={capital}
                                    onChange={(e) => setCapital(Number(e.target.value))}
                                    className="w-full bg-white border border-gray-300 rounded-lg px-4 py-2 text-gray-900 focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                            <div className="flex items-end">
                                <button
                                    onClick={generateSignals}
                                    disabled={loading}
                                    className="w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-all disabled:opacity-50"
                                >
                                    {loading ? '分析中...' : `🚀 分析 ${selectedTheme}`}
                                </button>
                            </div>
                        </div>

                        {/* Selected stocks preview */}
                        <div className="text-sm text-gray-500">
                            將掃描: {themeStocks[selectedTheme]?.join(', ') || '載入中...'}
                        </div>
                    </div>

                    {/* Results */}
                    {recommendation && (
                        <>
                            {/* Overview */}
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
                                    <div className="text-gray-500 text-sm mb-1">市場狀況</div>
                                    <div className="text-xl font-bold text-gray-900">{recommendation.market_condition}</div>
                                </div>
                                <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
                                    <div className="text-gray-500 text-sm mb-1">分析主題</div>
                                    <div className="text-xl font-bold text-blue-600">{selectedTheme}</div>
                                </div>
                                <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
                                    <div className="text-gray-500 text-sm mb-1">分析標的數</div>
                                    <div className="text-xl font-bold text-gray-900">{recommendation.stock_recommendations.length} 檔</div>
                                </div>
                                <div className="bg-blue-50 rounded-xl p-4 border border-blue-200 shadow-sm">
                                    <div className="text-gray-500 text-sm mb-1">整體建議</div>
                                    <div className="text-lg font-bold text-blue-600">{recommendation.overall_action}</div>
                                </div>
                            </div>

                            {/* Asset Allocation Summary */}
                            <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
                                <h3 className="text-xl font-bold text-gray-900 mb-4">💼 資產配置建議</h3>
                                <div className="grid grid-cols-4 gap-4">
                                    <div className="text-center">
                                        <div className="text-3xl font-bold text-blue-600">{(recommendation.equity_allocation * 100).toFixed(0)}%</div>
                                        <div className="text-gray-500">股票</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-3xl font-bold text-green-600">{(recommendation.bond_allocation * 100).toFixed(0)}%</div>
                                        <div className="text-gray-500">債券</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-3xl font-bold text-yellow-600">{(recommendation.cash_allocation * 100).toFixed(0)}%</div>
                                        <div className="text-gray-500">現金</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-3xl font-bold text-purple-600">{(recommendation.alternative_allocation * 100).toFixed(0)}%</div>
                                        <div className="text-gray-500">另類</div>
                                    </div>
                                </div>
                            </div>

                            {/* Key Themes */}
                            <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
                                <h3 className="text-xl font-bold text-gray-900 mb-4">📌 關鍵主題</h3>
                                <div className="flex flex-wrap gap-2">
                                    {recommendation.key_themes.map((theme, i) => (
                                        <span key={i} className="px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-700">
                                            {theme}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* Stock Signals */}
                            <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
                                <h3 className="text-xl font-bold text-gray-900 mb-4">📊 個股投資信號 (6維度分析)</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {recommendation.stock_recommendations.map((stock, i) => (
                                        <div key={i} className={`rounded-xl p-4 border ${getSignalColor(stock.signal)}`}>
                                            <div className="flex items-center justify-between mb-3">
                                                <div>
                                                    <div className="font-bold text-lg text-gray-900">{stock.ticker} {stock.name}</div>
                                                    <div className="text-2xl font-bold">
                                                        {getSignalEmoji(stock.signal)} {stock.signal}
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <div className="text-3xl font-bold text-gray-900">{stock.score.toFixed(0)}</div>
                                                    <div className="text-sm text-gray-500">評分</div>
                                                </div>
                                            </div>

                                            {/* 6 維度評分 */}
                                            <div className="grid grid-cols-3 gap-1 mb-3 text-xs">
                                                <div className="bg-blue-100 rounded p-1.5 text-center">
                                                    <div className="font-bold text-blue-700">{stock.technical_score?.toFixed(0) || 50}</div>
                                                    <div className="text-gray-600">技術面</div>
                                                </div>
                                                <div className="bg-purple-100 rounded p-1.5 text-center">
                                                    <div className="font-bold text-purple-700">{stock.economic_cycle_score?.toFixed(0) || 50}</div>
                                                    <div className="text-gray-600">總經</div>
                                                </div>
                                                <div className="bg-indigo-100 rounded p-1.5 text-center">
                                                    <div className="font-bold text-indigo-700">{stock.industry_power_score?.toFixed(0) || 50}</div>
                                                    <div className="text-gray-600">定價權</div>
                                                </div>
                                                <div className="bg-green-100 rounded p-1.5 text-center">
                                                    <div className="font-bold text-green-700">{stock.financial_score?.toFixed(0) || 50}</div>
                                                    <div className="text-gray-600">財報</div>
                                                </div>
                                                <div className="bg-yellow-100 rounded p-1.5 text-center">
                                                    <div className="font-bold text-yellow-700">{stock.trend_exposure?.toFixed(0) || 50}</div>
                                                    <div className="text-gray-600">趨勢</div>
                                                </div>
                                                <div className="bg-orange-100 rounded p-1.5 text-center">
                                                    <div className="font-bold text-orange-700">{stock.order_momentum?.toFixed(0) || 50}</div>
                                                    <div className="text-gray-600">訂單</div>
                                                </div>
                                            </div>

                                            <div className="text-sm text-gray-600 mb-2">{stock.action}</div>

                                            <div className="flex gap-4 text-sm text-gray-600">
                                                <span>停損: {stock.stop_loss}</span>
                                                <span>停利: {stock.take_profit}</span>
                                            </div>

                                            {/* 分析理由 */}
                                            {stock.reasons && stock.reasons.length > 0 && (
                                                <div className="mt-3 pt-3 border-t border-gray-200">
                                                    <div className="text-xs text-gray-500 mb-1">分析理由:</div>
                                                    <div className="text-xs space-y-0.5">
                                                        {stock.reasons.slice(0, 3).map((r: string, j: number) => (
                                                            <div key={j} className="text-gray-600">{r}</div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Risk Warnings */}
                            <div className="bg-red-50 rounded-2xl p-6 border border-red-200">
                                <h3 className="text-xl font-bold mb-4 text-red-600">⚠️ 風險提示</h3>
                                <ul className="space-y-2">
                                    {recommendation.risk_warnings.map((warning, i) => (
                                        <li key={i} className="text-red-700">{warning}</li>
                                    ))}
                                </ul>
                            </div>
                        </>
                    )}

                    {!recommendation && !loading && (
                        <div className="text-center py-20 text-gray-500">
                            選擇主題後，點擊「分析」開始掃描
                        </div>
                    )}
                </div>
            )}

            {/* Allocation Tab */}
            {activeTab === 'allocation' && (
                <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-sm">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">⚖️ 資產配置策略</h2>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        {[
                            { profile: 'CONSERVATIVE', name: '保守型', equity: 30, bond: 50, cash: 15, alt: 5, desc: '低風險，穩定收益' },
                            { profile: 'MODERATE', name: '穩健型', equity: 50, bond: 35, cash: 10, alt: 5, desc: '平衡風險與報酬' },
                            { profile: 'AGGRESSIVE', name: '積極型', equity: 70, bond: 20, cash: 5, alt: 5, desc: '追求高報酬' },
                        ].map((p) => (
                            <div
                                key={p.profile}
                                className={`rounded-xl p-6 border cursor-pointer transition-all ${riskProfile === p.profile
                                    ? 'bg-blue-50 border-blue-500'
                                    : 'bg-gray-50 border-gray-200 hover:border-gray-300'
                                    }`}
                                onClick={() => setRiskProfile(p.profile)}
                            >
                                <h3 className="text-xl font-bold text-gray-900 mb-2">{p.name}</h3>
                                <p className="text-gray-500 text-sm mb-4">{p.desc}</p>
                                <div className="space-y-2 text-gray-700">
                                    <div className="flex justify-between"><span>股票</span><span className="font-bold text-blue-600">{p.equity}%</span></div>
                                    <div className="flex justify-between"><span>債券</span><span className="font-bold text-green-600">{p.bond}%</span></div>
                                    <div className="flex justify-between"><span>現金</span><span className="font-bold text-yellow-600">{p.cash}%</span></div>
                                    <div className="flex justify-between"><span>另類</span><span className="font-bold text-purple-600">{p.alt}%</span></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Electronics Tab */}
            {activeTab === 'electronics' && (
                <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
                    <h2 className="text-2xl font-bold text-gray-900 mb-6">📱 電子股技術趨勢</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {Object.entries(trends).map(([id, trend]) => (
                            <div key={id} className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                                <h3 className="text-xl font-bold text-gray-900 mb-3">{trend.trend}</h3>
                                <div className="grid grid-cols-3 gap-4 text-center">
                                    <div>
                                        <div className="text-2xl font-bold text-blue-600">{(trend.adoption_rate * 100).toFixed(0)}%</div>
                                        <div className="text-sm text-gray-500">採用率</div>
                                    </div>
                                    <div>
                                        <div className="text-2xl font-bold text-green-600">{(trend.growth_forecast * 100).toFixed(0)}%</div>
                                        <div className="text-sm text-gray-500">成長預測</div>
                                    </div>
                                    <div>
                                        <div className="text-2xl font-bold text-purple-600">{trend.impact_score.toFixed(1)}</div>
                                        <div className="text-sm text-gray-500">影響分數</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Technical Tab */}
            {activeTab === 'technical' && (
                <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
                    <div className="flex flex-wrap gap-2 mb-6">
                        {['2330', '2454', '2382', '6669', '3008', '3324', '3037'].map((ticker) => (
                            <button
                                key={ticker}
                                onClick={() => { setSelectedStock(ticker); fetchTechnical(ticker); }}
                                className={`px-4 py-2 rounded-lg ${selectedStock === ticker ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                    }`}
                            >
                                {ticker}
                            </button>
                        ))}
                    </div>
                    {technicalData && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-gray-50 rounded-lg p-4 text-center border border-gray-200">
                                <div className="text-2xl font-bold text-gray-900">{technicalData.current_price}</div>
                                <div className="text-gray-500 text-sm">現價</div>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-4 text-center border border-gray-200">
                                <div className="text-2xl font-bold text-gray-900">{technicalData.final_signal}</div>
                                <div className="text-gray-500 text-sm">信號</div>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-4 text-center border border-gray-200">
                                <div className="text-2xl font-bold text-gray-900">{technicalData.position_analysis?.zone || '-'}</div>
                                <div className="text-gray-500 text-sm">價格區間</div>
                            </div>
                            <div className="bg-gray-50 rounded-lg p-4 text-center border border-gray-200">
                                <div className="text-2xl font-bold text-gray-900">{technicalData.position_analysis?.score || '-'}</div>
                                <div className="text-gray-500 text-sm">位置評分</div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
