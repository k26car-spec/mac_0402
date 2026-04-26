'use client';

import React, { useState, useEffect, useCallback } from 'react';
import DipAnalysisCard from '@/components/analysis/DipAnalysisCard';
import { entryCheckApi } from '@/lib/api-client';
import type { DipAnalysis } from '@/types/analysis';

// ==================== API 配置 ====================
const API_BASE = 'http://localhost:8000/api/stock-analysis';

// ==================== 類型定義 ====================
interface DimensionScore {
    name: string;
    score: number;
    weight: number;
    details: string[];
}

interface Signal {
    type: string;
    name: string;
    description: string;
    confidence: number;
    source: string;
}

interface RiskAlert {
    level: string;
    title: string;
    description: string;
    metric: string;
    value: number | string;
}

interface QuarterlyEPS {
    quarter: string;      // 例如 "2025Q3"
    eps: number;          // 該季度 EPS
}

interface FinancialHealth {
    roe: number;
    eps: number;
    quarterly_eps: QuarterlyEPS[];  // 季度 EPS 資料
    revenue_growth_3y: number;
    gross_margin: number;
    debt_ratio: number;
    current_ratio: number;
    quick_ratio: number;
    interest_coverage: number;
    free_cash_flow: number;
}

interface Valuation {
    pe_ratio: number;
    pb_ratio: number;
    dividend_yield: number;
    peg_ratio: number;
    ev_ebitda: number;
}

interface TechnicalIndicators {
    // 價格
    current_price: number;
    change_pct: number;
    // MA 均線
    ma5: number;
    ma10: number;
    ma20: number;
    ma60: number;
    // MA 均線分析
    ma_arrangement: string;
    ma_signal: string;
    ma_trend: string;
    // 壓力與支撐
    resistance_1: number;
    resistance_2: number;
    support_1: number;
    support_2: number;
    // 其他技術指標
    rsi_14: number;
    macd: number;
    macd_signal: string;
    kd_k: number;
    kd_d: number;
    bollinger_width: number;
    deviation_20d: number;
    deviation_60d: number;
    trend: string;
}

interface InstitutionalTrading {
    foreign_net: number;
    trust_net: number;
    dealer_net: number;
    total_net: number;
    consecutive_days: number;
}

interface NewsItem {
    title: string;
    summary: string;
    date: string;
    source: string;
    sentiment: string;
    impact: string;
}

// 量價分析介面 (新增)
interface VolumePriceAnalysis {
    trend_direction: string;           // bullish, bearish, sideways
    trend_confidence: number;          // 0-100 置信度
    volume_price_confirmation: string; // 價漲量增, 價漲量縮, 價跌量增, 價跌量縮
    confirmation_signal: string;       // bullish_confirmation, bearish_confirmation, caution, neutral
    confirmation_strength: number;     // 0-1 信號強度
    divergence_detected: boolean;      // 是否檢測到背離
    divergence_type: string;           // bullish_divergence, bearish_divergence, none
    divergence_description: string;    // 背離說明
    volume_ratio: number;              // 量比
    volume_trend: string;              // increasing, decreasing, stable
    volume_sma5: number;               // 5日成交量均值
    volume_sma20: number;              // 20日成交量均值
    obv: number;                       // OBV 能量潮
    obv_trend: string;                 // OBV趨勢: bullish, bearish, neutral
    vwap: number;                      // VWAP 成交量加權平均價
    vwap_deviation: number;            // VWAP偏離度
    key_signals: string[];             // 關鍵量價訊號
    predicted_direction: string;       // up, down, sideways
    prediction_probability: {
        up: number;
        down: number;
        sideways: number;
    };
}

interface AnalysisData {
    status: string;
    stock_code: string;
    stock_name: string;
    last_updated: string;
    overall_score: number;
    dimension_scores: DimensionScore[];
    buy_signals: Signal[];
    sell_signals: Signal[];
    risk_alerts: RiskAlert[];
    financial_health: FinancialHealth | null;
    valuation: Valuation | null;
    technical_indicators: TechnicalIndicators | null;
    institutional_trading: InstitutionalTrading | null;
    related_news: NewsItem[];
    ai_summary: string;
    recommendation: string;
    target_price: number | null;
    stop_loss: number | null;
    // 新增欄位
    abnormal_warning?: {
        is_abnormal: boolean;
        reasons: string[];
    };
    events?: {
        next_revenue_date?: string;
        last_revenue_month?: string;
        next_quarterly_report?: {
            quarter: string;
            deadline: string;
        };
        dividend?: {
            last_ex_date?: string;
            dividend_yield?: number;
            annual_dividend?: number;
        };
    };
    institutional_analysis?: {
        trend?: string;
        strength?: string;
        consecutive_days?: {
            foreign: number;
            trust: number;
            dealer: number;
        };
    };
    // 量價分析 (新增)
    volume_price_analysis?: VolumePriceAnalysis | null;
    dip_analysis?: DipAnalysis | null;
}

// ==================== 法人籌碼類型 ====================
interface ChipSummary {
    success: boolean;
    date: string;
    summary: {
        overall_stance: string;
        total_score: number;
        foreign_futures_net: number;
        pc_ratio: number;
        retail_sentiment: string;
    };
    futures: {
        foreign_futures_net: number;
        foreign_call_net: number;
        foreign_put_net: number;
        pc_ratio: number;
        foreign_stance: string;
        market_sentiment: string;
    };
    margin: {
        retail_sentiment: string;
        margin_change_ratio: number;
        short_change_ratio: number;
    };
    recommendation: {
        action: string;
        confidence: number;
        reason: string;
    };
}

interface InstitutionalContinuous {
    success: boolean;
    symbol: string;
    foreign: { direction: string; days: number; total: number };
    investment: { direction: string; days: number; total: number };
    dealer: { direction: string; days: number; total: number };
}

// ==================== 輔助函數 ====================
const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-red-600';
};

const getScoreBarColor = (score: number): string => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-blue-500';
    if (score >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
};

const getDimensionColor = (name: string): string => {
    const colors: { [key: string]: string } = {
        '成長性': 'bg-green-500',
        '估值': 'bg-blue-500',
        '財務品質': 'bg-purple-500',
        '技術面': 'bg-orange-500',
    };
    return colors[name] || 'bg-gray-500';
};

const getRiskLevelColor = (level: string): { bg: string; text: string; border: string } => {
    const colors: { [key: string]: { bg: string; text: string; border: string } } = {
        low: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
        medium: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200' },
        high: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
        critical: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' },
    };
    return colors[level] || colors.medium;
};

const getRecommendationStyle = (rec: string): { bg: string; text: string } => {
    // 台股習慣：買進=紅色，賣出=綠色
    if (rec === '強力買進') return { bg: 'bg-red-600', text: 'text-white' };
    if (rec === '買進') return { bg: 'bg-red-500', text: 'text-white' };
    if (rec === '觀望') return { bg: 'bg-yellow-500', text: 'text-white' };
    if (rec === '減碼') return { bg: 'bg-orange-500', text: 'text-white' };
    return { bg: 'bg-green-500', text: 'text-white' };  // 賣出為綠色
};
// ==================== 主頁面組件 ====================

// 我的最愛類型
interface FavoriteStock {
    code: string;
    name: string;
    score?: number;  // 評分
    loading?: boolean;  // 是否正在載入評分
}

export default function StockAnalysisPage() {
    const [stockCode, setStockCode] = useState('2330');
    const [searchInput, setSearchInput] = useState('2330');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<AnalysisData | null>(null);
    const [favorites, setFavorites] = useState<FavoriteStock[]>([]);
    const [priceData, setPriceData] = useState<{ price: number; change: number; changePercent: number } | null>(null);

    // 新聞相關狀態
    const [newsData, setNewsData] = useState<NewsItem[]>([]);
    const [newsLoading, setNewsLoading] = useState(false);
    const [newsError, setNewsError] = useState<string | null>(null);

    // 法人籌碼相關狀態
    const [chipData, setChipData] = useState<ChipSummary | null>(null);
    const [chipLoading, setChipLoading] = useState(false);
    const [continuousData, setContinuousData] = useState<InstitutionalContinuous | null>(null);
    const [chipTab, setChipTab] = useState<'summary' | 'futures' | 'margin'>('summary');

    // 熱門股票 (含名稱)
    const popularStocks = [
        { code: '2330', name: '台積電' },
        { code: '2454', name: '聯發科' },
        { code: '2317', name: '鴻海' },
        { code: '2308', name: '台達電' },
        { code: '2382', name: '廣達' },
        { code: '2303', name: '聯電' },
        { code: '2881', name: '富邦金' },
        { code: '2891', name: '中信金' },
    ];

    // 最愛評分載入狀態
    const [favoritesLoading, setFavoritesLoading] = useState(false);

    // 獲取單一股票評分
    const fetchStockScore = async (code: string): Promise<number | undefined> => {
        try {
            const response = await fetch(`${API_BASE}/comprehensive/${code}`);
            if (response.ok) {
                const result = await response.json();
                return result.overall_score;
            }
        } catch { }
        return undefined;
    };

    // 批次獲取所有最愛股票的評分
    const fetchAllFavoriteScores = useCallback(async (favList: FavoriteStock[]) => {
        if (favList.length === 0) return;

        setFavoritesLoading(true);

        // 批次獲取評分
        const updatedFavorites = await Promise.all(
            favList.map(async (fav) => {
                const score = await fetchStockScore(fav.code);
                return { ...fav, score, loading: false };
            })
        );

        setFavorites(updatedFavorites);
        setFavoritesLoading(false);
    }, []);

    // 載入我的最愛
    useEffect(() => {
        const loadFavorites = async () => {
            const saved = localStorage.getItem('stock_favorites_v2');
            if (saved) {
                try {
                    const parsedFavorites = JSON.parse(saved);
                    setFavorites(parsedFavorites);
                    // 自動獲取評分
                    fetchAllFavoriteScores(parsedFavorites);
                } catch { }
            } else {
                // 嘗試轉換舊格式
                const oldSaved = localStorage.getItem('stock_favorites');
                if (oldSaved) {
                    try {
                        const oldFavorites = JSON.parse(oldSaved);
                        // 批次取得股票名稱
                        const response = await fetch(`${API_BASE}/stock-names`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(oldFavorites)
                        });
                        let nameMap: Record<string, string> = {};
                        if (response.ok) {
                            const result = await response.json();
                            if (result.success) {
                                nameMap = result.data;
                            }
                        }
                        const converted = oldFavorites.map((code: string) => ({
                            code,
                            name: nameMap[code] || code
                        }));
                        setFavorites(converted);
                        localStorage.setItem('stock_favorites_v2', JSON.stringify(converted));
                        // 自動獲取評分
                        fetchAllFavoriteScores(converted);
                    } catch { }
                }
            }
        };
        loadFavorites();
    }, [fetchAllFavoriteScores]);

    // 取得股票名稱 (從 API)
    const fetchStockName = useCallback(async (code: string): Promise<string> => {
        try {
            const response = await fetch(`${API_BASE}/stock-name/${code}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.name && result.name !== code) {
                    return result.name;
                }
            }
        } catch { }
        return code; // 如果失敗，返回代碼作為名稱
    }, []);

    // 儲存我的最愛 (加入時透過 API 取得股票名稱)
    const toggleFavorite = async (code: string, name?: string) => {
        // 如果沒有提供名稱，嘗試從 API 取得
        let stockName = name || data?.stock_name || code;

        if (!name && !data?.stock_name) {
            stockName = await fetchStockName(code);
        }

        setFavorites(prev => {
            const exists = prev.find(f => f.code === code);
            let newFavorites: FavoriteStock[];

            if (exists) {
                newFavorites = prev.filter(f => f.code !== code);
            } else {
                newFavorites = [...prev, { code, name: stockName }];
            }

            localStorage.setItem('stock_favorites_v2', JSON.stringify(newFavorites));
            return newFavorites;
        });
    };

    const isFavorite = (code: string) => favorites.some(f => f.code === code);

    // 取得即時價格
    const fetchPrice = useCallback(async (code: string) => {
        try {
            const response = await fetch(`http://localhost:8000/api/realtime/quote/${code}`);
            if (response.ok) {
                const result = await response.json();
                setPriceData({
                    price: result.price || 0,
                    change: result.change || 0,
                    changePercent: result.changePercent || result.change || 0
                });
            }
        } catch { }
    }, []);

    const fetchAnalysis = useCallback(async (code: string, force: boolean = false) => {
        setLoading(true);
        setError(null);
        setPriceData(null);

        try {
            // 同時取得分析、價格與增強型低點分析
            const [analysisRes, entryCheckRes] = await Promise.all([
                fetch(`${API_BASE}/comprehensive/${code}${force ? '?force=true' : ''}`),
                entryCheckApi.quickCheck(code).catch(() => null),
                fetchPrice(code)
            ]);

            if (!analysisRes.ok) {
                throw new Error(`分析失敗: ${analysisRes.statusText}`);
            }
            const result = await analysisRes.json();

            // 整合 Dip Analysis 到數據中
            if (entryCheckRes && entryCheckRes.checks?.dip_analysis) {
                result.dip_analysis = entryCheckRes.checks.dip_analysis;
            }

            setData(result);
            setStockCode(code);

            // 清空新聞（需要點擊按鈕才會重新取得）
            setNewsData([]);
            setNewsError(null);

            // 從技術指標取得價格
            if (result.technical_indicators?.current_price) {
                setPriceData({
                    price: result.technical_indicators.current_price,
                    change: result.technical_indicators.change_pct || 0,
                    changePercent: result.technical_indicators.change_pct || 0
                });
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '取得分析資料失敗');
        } finally {
            setLoading(false);
        }
    }, [fetchPrice]);

    // 取得即時新聞 (透過後端 Playwright 爬蟲)
    const fetchNews = useCallback(async () => {
        if (!stockCode) return;

        setNewsLoading(true);
        setNewsError(null);

        try {
            // 使用後端 API 取得個股新聞 (後端使用 Playwright 繞過反爬蟲)
            const response = await fetch(`${API_BASE}/news/wantgoo/${stockCode}?limit=10`);

            if (response.ok) {
                const result = await response.json();
                setNewsData(result.news || []);
            } else {
                throw new Error('取得新聞失敗');
            }
        } catch (err) {
            console.error('後端 API 錯誤:', err);
            setNewsError(err instanceof Error ? err.message : '取得新聞失敗');
        } finally {
            setNewsLoading(false);
        }
    }, [stockCode]);

    useEffect(() => {
        fetchAnalysis(stockCode);
    }, []);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (searchInput.trim()) {
            fetchAnalysis(searchInput.trim());
        }
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* 頂部導航 */}
            <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            <h1 className="text-2xl font-bold text-gray-900">📊 股票綜合分析</h1>
                            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                                AI 驅動
                            </span>
                        </div>

                        {/* 搜尋框 */}
                        <form onSubmit={handleSearch} className="flex items-center space-x-2">
                            <input
                                type="text"
                                value={searchInput}
                                onChange={(e) => setSearchInput(e.target.value)}
                                placeholder="輸入股票代碼..."
                                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent w-48"
                            />
                            <button
                                type="submit"
                                disabled={loading}
                                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                            >
                                {loading ? '分析中...' : '分析'}
                            </button>
                        </form>
                    </div>

                    {/* 我的最愛 - 簡化版，無分類 */}
                    {favorites.length > 0 && (
                        <div className="mt-4 p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-xl border border-yellow-200">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-sm text-yellow-700 font-bold flex items-center gap-2">
                                    ⭐ 我的最愛 ({favorites.length})
                                    {favoritesLoading && (
                                        <span className="inline-block w-4 h-4 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></span>
                                    )}
                                </span>
                                <button
                                    onClick={() => fetchAllFavoriteScores(favorites)}
                                    disabled={favoritesLoading}
                                    className="text-xs text-yellow-600 hover:text-yellow-800 flex items-center gap-1"
                                >
                                    🔄 重新評分
                                </button>
                            </div>

                            {/* 簡單列表顯示 */}
                            <div className="flex flex-wrap gap-2">
                                {favorites.map((fav) => (
                                    <button
                                        key={fav.code}
                                        onClick={() => { setSearchInput(fav.code); fetchAnalysis(fav.code); }}
                                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${stockCode === fav.code
                                            ? 'bg-yellow-500 text-white shadow-md'
                                            : 'bg-white text-yellow-700 border border-yellow-300 hover:bg-yellow-100 hover:border-yellow-400'
                                            }`}
                                    >
                                        <span>{fav.name || fav.code}</span>
                                        {fav.score !== undefined && (
                                            <span className={`text-xs px-1.5 py-0.5 rounded ${fav.score >= 70 ? 'bg-green-100 text-green-700' :
                                                fav.score >= 60 ? 'bg-blue-100 text-blue-700' :
                                                    fav.score >= 45 ? 'bg-yellow-100 text-yellow-700' :
                                                        'bg-red-100 text-red-700'
                                                }`}>
                                                {fav.score.toFixed(0)}
                                            </span>
                                        )}
                                        {fav.score === undefined && (
                                            <span className="inline-block w-3 h-3 border border-yellow-400 border-t-transparent rounded-full animate-spin"></span>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 熱門股票快捷按鈕 */}
                    <div className="flex items-center flex-wrap gap-2 mt-3">
                        <span className="text-sm text-gray-500">熱門股票:</span>
                        {popularStocks.map((stock) => (
                            <button
                                key={stock.code}
                                onClick={() => {
                                    setSearchInput(stock.code);
                                    fetchAnalysis(stock.code);
                                }}
                                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${stockCode === stock.code
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                    }`}
                            >
                                {stock.name}
                            </button>
                        ))}
                    </div>
                </div>
            </header>

            {/* 主要內容 */}
            <main className="max-w-7xl mx-auto px-4 py-6">
                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                        ⚠️ {error}
                    </div>
                )}

                {loading && (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
                        <span className="ml-4 text-gray-600">正在進行 AI 分析...</span>
                    </div>
                )}

                {data && !loading && (
                    <div className="space-y-6">
                        {/* 股票標題區 */}
                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-4">
                                    {/* 加入最愛按鈕 */}
                                    <button
                                        onClick={() => toggleFavorite(data.stock_code)}
                                        className={`text-3xl transition-transform hover:scale-110 ${isFavorite(data.stock_code) ? 'text-yellow-500' : 'text-gray-300'
                                            }`}
                                        title={isFavorite(data.stock_code) ? '移除最愛' : '加入最愛'}
                                    >
                                        {isFavorite(data.stock_code) ? '⭐' : '☆'}
                                    </button>
                                    <div>
                                        <h2 className="text-3xl font-bold text-gray-900">
                                            {data.stock_name} <span className="text-gray-500">({data.stock_code})</span>
                                        </h2>
                                        <div className="flex items-center gap-2 mt-1">
                                            <p className="text-sm text-gray-500">
                                                最後更新: {new Date(data.last_updated).toLocaleString('zh-TW')}
                                            </p>
                                            <button
                                                onClick={() => fetchAnalysis(data.stock_code, true)}
                                                className="p-1 hover:bg-gray-100 rounded-full transition-colors text-blue-500"
                                                title="重新整理基本面與技術分析數據"
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"></path><path d="M21 3v5h-5"></path></svg>
                                            </button>
                                        </div>
                                        {/* 異常股票警示 */}
                                        {data.abnormal_warning?.is_abnormal && (
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                {data.abnormal_warning.reasons.map((reason, idx) => (
                                                    <span key={idx} className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full border border-red-300">
                                                        ⚠️ {reason}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* 股價和推薦 */}
                                <div className="flex items-center space-x-6">
                                    {/* 目前股價 */}
                                    {priceData && (
                                        <div className="text-right">
                                            <div className="text-sm text-gray-500">目前股價</div>
                                            <div className="flex items-center space-x-2">
                                                <span className="text-3xl font-bold text-gray-900">
                                                    ${priceData.price.toFixed(2)}
                                                </span>
                                                <span className={`px-2 py-1 rounded text-sm font-medium ${priceData.changePercent > 0
                                                    ? 'bg-red-100 text-red-700'
                                                    : priceData.changePercent < 0
                                                        ? 'bg-green-100 text-green-700'
                                                        : 'bg-gray-100 text-gray-700'
                                                    }`}>
                                                    {priceData.changePercent > 0 ? '▲' : priceData.changePercent < 0 ? '▼' : ''}
                                                    {Math.abs(priceData.changePercent).toFixed(2)}%
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {/* 推薦等級 */}
                                    <div className={`px-4 py-2 rounded-lg ${getRecommendationStyle(data.recommendation).bg} ${getRecommendationStyle(data.recommendation).text}`}>
                                        {data.recommendation}
                                    </div>

                                    {/* 目標價 */}
                                    {data.target_price && (
                                        <div className="text-right">
                                            <div className="text-sm text-gray-500">目標價</div>
                                            <div className="text-xl font-bold text-red-600">${data.target_price}</div>
                                        </div>
                                    )}

                                    {/* 停損價 */}
                                    {data.stop_loss && (
                                        <div className="text-right">
                                            <div className="text-sm text-gray-500">停損價</div>
                                            <div className="text-xl font-bold text-green-600">${data.stop_loss}</div>
                                        </div>
                                    )}

                                    {/* 匯出 PDF 按鈕 */}
                                    <button
                                        onClick={() => {
                                            const link = document.createElement('a');
                                            link.href = `http://localhost:8000/api/stock-analysis/report/pdf/${data.stock_code}`;
                                            link.download = `${data.stock_code}_${data.stock_name}_分析報告.pdf`;
                                            document.body.appendChild(link);
                                            link.click();
                                            document.body.removeChild(link);
                                        }}
                                        className="flex items-center px-4 py-2 bg-gradient-to-r from-red-500 to-pink-500 text-white rounded-lg hover:from-red-600 hover:to-pink-600 shadow-md transition-all hover:shadow-lg"
                                        title="下載 PDF 報告，可分享到 LINE"
                                    >
                                        <span className="mr-2">📄</span>
                                        匯出 PDF
                                    </button>

                                    {/* 下載懶人包按鈕 */}
                                    <button
                                        onClick={() => {
                                            const link = document.createElement('a');
                                            link.href = `http://localhost:8000/api/stock-analysis/report/genz/${data.stock_code}`;
                                            link.download = `${data.stock_code}_${data.stock_name}_懶人包.pdf`;
                                            document.body.appendChild(link);
                                            link.click();
                                            document.body.removeChild(link);
                                        }}
                                        className="flex items-center px-4 py-2 bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-lg hover:from-purple-600 hover:to-indigo-600 shadow-md transition-all hover:shadow-lg"
                                        title="下載 GenZ 風格懶人包，新手必備！"
                                    >
                                        <span className="mr-2">🔥</span>
                                        懶人包
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* 綜合評分區 */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            {/* 左側：綜合評分圓餅圖 */}
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">綜合評分</h3>
                                <p className="text-sm text-gray-500 mb-6">基於四大面向的 AI 評分模型</p>

                                {/* 大型評分圓圈 */}
                                <div className="flex justify-center mb-6">
                                    <div className="relative w-48 h-48">
                                        <svg className="w-full h-full transform -rotate-90">
                                            <circle
                                                cx="96"
                                                cy="96"
                                                r="88"
                                                fill="none"
                                                stroke="#e5e7eb"
                                                strokeWidth="12"
                                            />
                                            <circle
                                                cx="96"
                                                cy="96"
                                                r="88"
                                                fill="none"
                                                stroke={data.overall_score >= 70 ? '#22c55e' : data.overall_score >= 50 ? '#3b82f6' : '#ef4444'}
                                                strokeWidth="12"
                                                strokeLinecap="round"
                                                strokeDasharray={`${data.overall_score * 5.5} 1000`}
                                            />
                                        </svg>
                                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                                            <span className="text-sm text-gray-500">綜分</span>
                                            <span className={`text-4xl font-bold ${getScoreColor(data.overall_score)}`}>
                                                {Math.round(data.overall_score)}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* 維度評分列表 */}
                                <div className="space-y-4">
                                    {data.dimension_scores.map((dim) => (
                                        <div key={dim.name} className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3">
                                                <div className={`w-3 h-3 rounded-full ${getDimensionColor(dim.name)}`}></div>
                                                <span className="text-gray-700">{dim.name}</span>
                                            </div>
                                            <div className="flex items-center space-x-2">
                                                <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full ${getScoreBarColor(dim.score)} transition-all duration-500`}
                                                        style={{ width: `${dim.score}%` }}
                                                    ></div>
                                                </div>
                                                <span className="text-sm font-medium text-gray-900 w-12 text-right">
                                                    {Math.round(dim.score)}分
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* 📊 評分說明區塊 */}
                                <div className="mt-6 pt-4 border-t border-gray-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="text-sm font-semibold text-gray-700">📋 評分操作建議</h4>
                                        <span className="text-xs text-gray-400">點擊查看詳情</span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                        <div className={`p-2 rounded-lg border ${data.overall_score >= 70 ? 'bg-green-100 border-green-300 ring-2 ring-green-400' : 'bg-green-50 border-green-200'}`}>
                                            <div className="flex items-center space-x-1">
                                                <span className="text-green-600 font-bold">🔥 ≥70分</span>
                                            </div>
                                            <div className="text-green-700 font-medium">強烈買進</div>
                                            <div className="text-green-600 opacity-75">分批進場</div>
                                        </div>
                                        <div className={`p-2 rounded-lg border ${data.overall_score >= 60 && data.overall_score < 70 ? 'bg-blue-100 border-blue-300 ring-2 ring-blue-400' : 'bg-blue-50 border-blue-200'}`}>
                                            <div className="flex items-center space-x-1">
                                                <span className="text-blue-600 font-bold">💚 60-69分</span>
                                            </div>
                                            <div className="text-blue-700 font-medium">建議買進</div>
                                            <div className="text-blue-600 opacity-75">逢低布局</div>
                                        </div>
                                        <div className={`p-2 rounded-lg border ${data.overall_score >= 45 && data.overall_score < 60 ? 'bg-yellow-100 border-yellow-300 ring-2 ring-yellow-400' : 'bg-yellow-50 border-yellow-200'}`}>
                                            <div className="flex items-center space-x-1">
                                                <span className="text-yellow-600 font-bold">🟡 45-59分</span>
                                            </div>
                                            <div className="text-yellow-700 font-medium">觀望</div>
                                            <div className="text-yellow-600 opacity-75">等待訊號</div>
                                        </div>
                                        <div className={`p-2 rounded-lg border ${data.overall_score < 45 ? 'bg-red-100 border-red-300 ring-2 ring-red-400' : 'bg-red-50 border-red-200'}`}>
                                            <div className="flex items-center space-x-1">
                                                <span className="text-red-600 font-bold">🔴 &lt;45分</span>
                                            </div>
                                            <div className="text-red-700 font-medium">避開</div>
                                            <div className="text-red-600 opacity-75">不建議進場</div>
                                        </div>
                                    </div>
                                    <p className="mt-3 text-xs text-gray-500 bg-gray-50 p-2 rounded">
                                        💡 <strong>建議</strong>：穩健投資人建議 ≥65分 再考慮添購，搭配主力進場+成交量放大訊號更佳
                                    </p>
                                </div>
                            </div>

                            {/* 🆕 增強版低點分析 (Buy on Dip) */}
                            {data.dip_analysis && (
                                <div className="lg:col-span-1">
                                    <DipAnalysisCard analysis={data.dip_analysis} />
                                </div>
                            )}

                            {/* 中間：買入訊號 */}
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <div className="flex items-center space-x-2 mb-4">
                                    <span className="text-2xl">📈</span>
                                    <h3 className="text-lg font-semibold text-gray-900">
                                        買入訊號 ({data.buy_signals.length})
                                    </h3>
                                </div>

                                <div className="space-y-3">
                                    {data.buy_signals.length === 0 ? (
                                        <p className="text-gray-500 text-center py-4">目前無買入訊號</p>
                                    ) : (
                                        data.buy_signals.map((signal, idx) => (
                                            <div key={idx} className="p-3 bg-red-50 rounded-lg border border-red-100">
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="font-medium text-red-800">🔺 {signal.name}</span>
                                                    <span className="text-sm text-red-600">信心度: {signal.confidence}%</span>
                                                </div>
                                                <p className="text-sm text-red-700">{signal.description}</p>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* 右側：風險警示 */}
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <div className="flex items-center space-x-2 mb-4">
                                    <span className="text-2xl">⚠️</span>
                                    <h3 className="text-lg font-semibold text-gray-900">
                                        風險警示 ({data.risk_alerts.length})
                                    </h3>
                                </div>

                                <div className="space-y-3">
                                    {data.risk_alerts.length === 0 ? (
                                        <p className="text-gray-500 text-center py-4">目前無風險警示</p>
                                    ) : (
                                        data.risk_alerts.map((risk, idx) => {
                                            const colors = getRiskLevelColor(risk.level);
                                            return (
                                                <div key={idx} className={`p-3 ${colors.bg} rounded-lg border ${colors.border}`}>
                                                    <div className="flex items-center justify-between mb-1">
                                                        <span className={`font-medium ${colors.text}`}>• {risk.title}</span>
                                                    </div>
                                                    <p className={`text-sm ${colors.text}`}>{risk.description}</p>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>

                                {/* 賣出訊號 */}
                                {data.sell_signals.length > 0 && (
                                    <div className="mt-6 pt-4 border-t border-gray-200">
                                        <h4 className="font-medium text-green-600 mb-3">📉 賣出訊號 ({data.sell_signals.length})</h4>
                                        <div className="space-y-2">
                                            {data.sell_signals.map((signal, idx) => (
                                                <div key={idx} className="p-2 bg-green-50 rounded text-sm text-green-700">
                                                    🔻 {signal.name}: {signal.description}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* 財務健康度 */}
                        {data.financial_health && (
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
                                    <span className="text-2xl mr-2">💰</span> 財務健康度
                                </h3>

                                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                    <FinancialCard
                                        label="ROE"
                                        value={`${data.financial_health.roe}%`}
                                        status={data.financial_health.roe > 15 ? 'good' : data.financial_health.roe > 0 ? 'normal' : 'bad'}
                                        benchmark="基準: 15%"
                                    />
                                    <FinancialCard
                                        label="EPS (TTM)"
                                        value={`$${data.financial_health.eps}`}
                                        status={data.financial_health.eps > 3 ? 'good' : data.financial_health.eps > 0 ? 'normal' : 'bad'}
                                    />
                                    <FinancialCard
                                        label="營收成長(3年)"
                                        value={`${data.financial_health.revenue_growth_3y}%`}
                                        status={data.financial_health.revenue_growth_3y > 10 ? 'good' : data.financial_health.revenue_growth_3y > 0 ? 'normal' : 'bad'}
                                    />
                                    <FinancialCard
                                        label="毛利率"
                                        value={`${data.financial_health.gross_margin}%`}
                                        status={data.financial_health.gross_margin > 30 ? 'good' : 'normal'}
                                    />
                                    <FinancialCard
                                        label="負債比"
                                        value={`${data.financial_health.debt_ratio}%`}
                                        status={data.financial_health.debt_ratio < 50 ? 'good' : data.financial_health.debt_ratio < 70 ? 'normal' : 'bad'}
                                        benchmark="基準: 50%"
                                    />
                                    <FinancialCard
                                        label="流動比率"
                                        value={data.financial_health.current_ratio.toFixed(2)}
                                        status={data.financial_health.current_ratio > 2 ? 'good' : data.financial_health.current_ratio > 1 ? 'normal' : 'bad'}
                                        benchmark="基準: 2"
                                    />
                                    <FinancialCard
                                        label="速動比率"
                                        value={data.financial_health.quick_ratio.toFixed(2)}
                                        status={data.financial_health.quick_ratio > 1 ? 'good' : 'bad'}
                                        benchmark="基準: 1"
                                    />
                                    <FinancialCard
                                        label="自由現金流"
                                        value={`${data.financial_health.free_cash_flow}億`}
                                        status={data.financial_health.free_cash_flow > 0 ? 'good' : 'bad'}
                                    />
                                </div>

                                {/* 季度 EPS */}
                                {data.financial_health.quarterly_eps && data.financial_health.quarterly_eps.length > 0 && (
                                    <div className="mt-6 p-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-200">
                                        <h4 className="font-semibold text-indigo-800 mb-4 flex items-center">
                                            📈 季度 EPS
                                        </h4>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                            {data.financial_health.quarterly_eps.map((q, idx) => (
                                                <div
                                                    key={idx}
                                                    className="bg-white rounded-lg p-3 shadow-sm border border-indigo-100 hover:shadow-md transition-shadow text-center"
                                                >
                                                    <div className="text-xs text-indigo-600 font-medium mb-1">
                                                        {q.quarter}
                                                    </div>
                                                    <div className={`text-xl font-bold ${q.eps >= 0 ? 'text-gray-800' : 'text-red-600'}`}>
                                                        ${q.eps.toFixed(2)}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* 法人買賣超 */}
                        {data.institutional_trading && (
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
                                    <span className="text-2xl mr-2">🏦</span> 法人買賣超 (近2日)
                                </h3>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {/* 外資 */}
                                    <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl border border-blue-200">
                                        <div className="text-sm text-blue-600 font-medium mb-1">外資</div>
                                        <div className={`text-xl font-bold ${data.institutional_trading.foreign_net > 0 ? 'text-red-600' : data.institutional_trading.foreign_net < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                                            {data.institutional_trading.foreign_net > 0 ? '+' : ''}{data.institutional_trading.foreign_net.toLocaleString()}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {data.institutional_trading.foreign_net > 0 ? '買超' : data.institutional_trading.foreign_net < 0 ? '賣超' : '無交易'}
                                        </div>
                                    </div>
                                    {/* 投信 */}
                                    <div className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl border border-purple-200">
                                        <div className="text-sm text-purple-600 font-medium mb-1">投信</div>
                                        <div className={`text-xl font-bold ${data.institutional_trading.trust_net > 0 ? 'text-red-600' : data.institutional_trading.trust_net < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                                            {data.institutional_trading.trust_net > 0 ? '+' : ''}{data.institutional_trading.trust_net.toLocaleString()}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {data.institutional_trading.trust_net > 0 ? '買超' : data.institutional_trading.trust_net < 0 ? '賣超' : '無交易'}
                                        </div>
                                    </div>
                                    {/* 自營商 */}
                                    <div className="p-4 bg-gradient-to-br from-orange-50 to-orange-100 rounded-xl border border-orange-200">
                                        <div className="text-sm text-orange-600 font-medium mb-1">自營商</div>
                                        <div className={`text-xl font-bold ${data.institutional_trading.dealer_net > 0 ? 'text-red-600' : data.institutional_trading.dealer_net < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                                            {data.institutional_trading.dealer_net > 0 ? '+' : ''}{data.institutional_trading.dealer_net.toLocaleString()}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {data.institutional_trading.dealer_net > 0 ? '買超' : data.institutional_trading.dealer_net < 0 ? '賣超' : '無交易'}
                                        </div>
                                    </div>
                                    {/* 合計 */}
                                    <div className={`p-4 rounded-xl border ${data.institutional_trading.total_net > 0 ? 'bg-gradient-to-br from-red-50 to-red-100 border-red-200' : data.institutional_trading.total_net < 0 ? 'bg-gradient-to-br from-green-50 to-green-100 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                                        <div className="text-sm text-gray-600 font-medium mb-1">三大法人合計</div>
                                        <div className={`text-xl font-bold ${data.institutional_trading.total_net > 0 ? 'text-red-600' : data.institutional_trading.total_net < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                                            {data.institutional_trading.total_net > 0 ? '+' : ''}{data.institutional_trading.total_net.toLocaleString()}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            連續 {data.institutional_trading.consecutive_days} 天
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-3 text-xs text-gray-500">
                                    ※ 單位：張，紅色表示買超，綠色表示賣超
                                </div>
                            </div>
                        )}

                        {/* 估值分析 */}
                        {data.valuation && (
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
                                    <span className="text-2xl mr-2">📊</span> 估值分析
                                </h3>

                                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                    <ValuationCard
                                        label="本益比 (PE)"
                                        value={data.valuation.pe_ratio}
                                        status={data.valuation.pe_ratio > 0 && data.valuation.pe_ratio < 15 ? 'good' : data.valuation.pe_ratio < 25 ? 'normal' : 'bad'}
                                        benchmark="基準: 15"
                                    />
                                    <ValuationCard
                                        label="股價淨值比 (PB)"
                                        value={data.valuation.pb_ratio}
                                        status={data.valuation.pb_ratio < 1.5 ? 'good' : data.valuation.pb_ratio < 3 ? 'normal' : 'bad'}
                                        benchmark="基準: 1.5"
                                    />
                                    <ValuationCard
                                        label="殖利率"
                                        value={`${data.valuation.dividend_yield}%`}
                                        status={data.valuation.dividend_yield > 4 ? 'good' : 'normal'}
                                        benchmark="基準: 4%"
                                    />
                                    <ValuationCard
                                        label="PEG"
                                        value={data.valuation.peg_ratio}
                                        status={data.valuation.peg_ratio > 0 && data.valuation.peg_ratio < 1 ? 'good' : 'normal'}
                                        benchmark="基準: 1"
                                    />
                                    <ValuationCard
                                        label="EV/EBITDA"
                                        value={data.valuation.ev_ebitda}
                                        status="normal"
                                    />
                                </div>
                            </div>
                        )}

                        {/* 技術指標 */}
                        {data.technical_indicators && (
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
                                    <span className="text-2xl mr-2">📈</span> 技術指標
                                </h3>

                                {/* MA 均線分析區塊 */}
                                <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border border-blue-200">
                                    <h4 className="font-semibold text-blue-800 mb-4 flex items-center">
                                        📊 MA 均線分析
                                    </h4>

                                    {/* 均線數值 */}
                                    <div className="grid grid-cols-4 gap-3 mb-4">
                                        <div className="text-center p-2 bg-white rounded-lg shadow-sm">
                                            <div className="text-xs text-gray-500">MA5</div>
                                            <div className={`font-bold ${data.technical_indicators.current_price > (data.technical_indicators.ma5 || 0) ? 'text-red-600' : 'text-green-600'}`}>
                                                ${(data.technical_indicators.ma5 || 0).toFixed(2)}
                                            </div>
                                        </div>
                                        <div className="text-center p-2 bg-white rounded-lg shadow-sm">
                                            <div className="text-xs text-gray-500">MA10</div>
                                            <div className={`font-bold ${data.technical_indicators.current_price > (data.technical_indicators.ma10 || 0) ? 'text-red-600' : 'text-green-600'}`}>
                                                ${(data.technical_indicators.ma10 || 0).toFixed(2)}
                                            </div>
                                        </div>
                                        <div className="text-center p-2 bg-white rounded-lg shadow-sm">
                                            <div className="text-xs text-gray-500">MA20</div>
                                            <div className={`font-bold ${data.technical_indicators.current_price > (data.technical_indicators.ma20 || 0) ? 'text-red-600' : 'text-green-600'}`}>
                                                ${(data.technical_indicators.ma20 || 0).toFixed(2)}
                                            </div>
                                        </div>
                                        <div className="text-center p-2 bg-white rounded-lg shadow-sm">
                                            <div className="text-xs text-gray-500">MA60</div>
                                            <div className={`font-bold ${data.technical_indicators.current_price > (data.technical_indicators.ma60 || 0) ? 'text-red-600' : 'text-green-600'}`}>
                                                ${(data.technical_indicators.ma60 || 0).toFixed(2)}
                                            </div>
                                        </div>
                                    </div>

                                    {/* 均線狀態 */}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                        {/* 均線排列 */}
                                        <div className="p-3 bg-white rounded-lg shadow-sm">
                                            <div className="text-xs text-gray-500 mb-1">均線排列</div>
                                            <div className={`font-bold text-lg ${data.technical_indicators.ma_arrangement?.includes('多頭') ? 'text-red-600' :
                                                data.technical_indicators.ma_arrangement?.includes('空頭') ? 'text-green-600' : 'text-yellow-600'
                                                }`}>
                                                {data.technical_indicators.ma_arrangement?.includes('多頭') ? '🔺 ' :
                                                    data.technical_indicators.ma_arrangement?.includes('空頭') ? '🔻 ' : '➖ '}
                                                {data.technical_indicators.ma_arrangement || '計算中...'}
                                            </div>
                                        </div>

                                        {/* 突破/跌破訊號 */}
                                        <div className="p-3 bg-white rounded-lg shadow-sm">
                                            <div className="text-xs text-gray-500 mb-1">MA 訊號</div>
                                            <div className={`font-medium text-sm ${data.technical_indicators.ma_signal?.includes('突破') ? 'text-red-600' :
                                                data.technical_indicators.ma_signal?.includes('跌破') ? 'text-green-600' : 'text-gray-700'
                                                }`}>
                                                {data.technical_indicators.ma_signal || '無訊號'}
                                            </div>
                                        </div>

                                        {/* 趨勢描述 */}
                                        <div className="p-3 bg-white rounded-lg shadow-sm">
                                            <div className="text-xs text-gray-500 mb-1">趨勢判斷</div>
                                            <div className="font-medium text-sm text-gray-700">
                                                {data.technical_indicators.ma_trend || '計算中...'}
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* 壓力與支撐位區塊 */}
                                <div className="mb-6 p-4 bg-gradient-to-r from-orange-50 to-red-50 rounded-xl border border-orange-200">
                                    <h4 className="font-semibold text-orange-800 mb-4 flex items-center">
                                        🎯 壓力與支撐位
                                    </h4>

                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                        {/* 壓力位2 */}
                                        <div className="text-center p-3 bg-red-100 rounded-lg border border-red-200">
                                            <div className="text-xs text-red-700 mb-1">壓力位2 (遠)</div>
                                            <div className="text-xl font-bold text-red-700">
                                                ${(data.technical_indicators.resistance_2 || 0).toFixed(2)}
                                            </div>
                                            <div className="text-xs text-red-500 mt-1">
                                                +{(((data.technical_indicators.resistance_2 || 0) / data.technical_indicators.current_price - 1) * 100).toFixed(1)}%
                                            </div>
                                        </div>

                                        {/* 壓力位1 */}
                                        <div className="text-center p-3 bg-red-50 rounded-lg border border-red-200">
                                            <div className="text-xs text-red-600 mb-1">壓力位1 (近)</div>
                                            <div className="text-xl font-bold text-red-600">
                                                ${(data.technical_indicators.resistance_1 || 0).toFixed(2)}
                                            </div>
                                            <div className="text-xs text-red-400 mt-1">
                                                +{(((data.technical_indicators.resistance_1 || 0) / data.technical_indicators.current_price - 1) * 100).toFixed(1)}%
                                            </div>
                                        </div>

                                        {/* 支撐位1 */}
                                        <div className="text-center p-3 bg-green-50 rounded-lg border border-green-200">
                                            <div className="text-xs text-green-600 mb-1">支撐位1 (近)</div>
                                            <div className="text-xl font-bold text-green-600">
                                                ${(data.technical_indicators.support_1 || 0).toFixed(2)}
                                            </div>
                                            <div className="text-xs text-green-400 mt-1">
                                                {(((data.technical_indicators.support_1 || 0) / data.technical_indicators.current_price - 1) * 100).toFixed(1)}%
                                            </div>
                                        </div>

                                        {/* 支撐位2 */}
                                        <div className="text-center p-3 bg-green-100 rounded-lg border border-green-200">
                                            <div className="text-xs text-green-700 mb-1">支撐位2 (遠)</div>
                                            <div className="text-xl font-bold text-green-700">
                                                ${(data.technical_indicators.support_2 || 0).toFixed(2)}
                                            </div>
                                            <div className="text-xs text-green-500 mt-1">
                                                {(((data.technical_indicators.support_2 || 0) / data.technical_indicators.current_price - 1) * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                    </div>

                                    {/* 當前價格指示 */}
                                    <div className="mt-4 p-3 bg-white rounded-lg text-center">
                                        <span className="text-gray-500">目前股價: </span>
                                        <span className="text-2xl font-bold text-gray-900">
                                            ${data.technical_indicators.current_price?.toFixed(2)}
                                        </span>
                                        <span className={`ml-2 px-2 py-1 rounded text-sm font-medium ${data.technical_indicators.change_pct > 0 ? 'bg-red-100 text-red-700' :
                                            data.technical_indicators.change_pct < 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                                            }`}>
                                            {data.technical_indicators.change_pct > 0 ? '▲' : data.technical_indicators.change_pct < 0 ? '▼' : ''}
                                            {Math.abs(data.technical_indicators.change_pct || 0).toFixed(2)}%
                                        </span>
                                    </div>

                                    {/* 計算說明 */}
                                    <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                                        <div className="text-xs text-gray-500 flex items-center mb-2">
                                            <span className="mr-1">ℹ️</span>
                                            <span className="font-medium">計算說明</span>
                                        </div>
                                        <div className="text-xs text-gray-600 leading-relaxed">
                                            <p><span className="text-red-600 font-medium">壓力位</span>：綜合 MA5/MA10/MA20/MA60 均線、近期高點(20/60日)、整數關卡，取最近的價位</p>
                                            <p className="mt-1"><span className="text-green-600 font-medium">支撐位</span>：綜合 MA5/MA10/MA20/MA60 均線、近期低點(20/60日)、整數關卡，取最近的價位</p>
                                        </div>
                                    </div>
                                </div>

                                {/* 其他技術指標 */}
                                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                    <TechnicalCard
                                        label="RSI (14)"
                                        value={data.technical_indicators.rsi_14.toFixed(2)}
                                        status={data.technical_indicators.rsi_14 > 70 ? 'overbought' : data.technical_indicators.rsi_14 < 30 ? 'oversold' : 'neutral'}
                                    />
                                    <TechnicalCard
                                        label="MACD"
                                        value={data.technical_indicators.macd.toFixed(4)}
                                        extra={data.technical_indicators.macd_signal}
                                        status={data.technical_indicators.macd > 0 ? 'bullish' : 'bearish'}
                                    />
                                    <TechnicalCard
                                        label="KD (9)"
                                        value={`${data.technical_indicators.kd_k.toFixed(1)} / ${data.technical_indicators.kd_d.toFixed(1)}`}
                                    />
                                    <TechnicalCard
                                        label="布林帶寬"
                                        value={data.technical_indicators.bollinger_width.toFixed(2)}
                                    />
                                    <TechnicalCard
                                        label="乖離率 (20日)"
                                        value={`${data.technical_indicators.deviation_20d.toFixed(2)}%`}
                                        status={Math.abs(data.technical_indicators.deviation_20d) > 10 ? 'warning' : 'normal'}
                                    />
                                    <TechnicalCard
                                        label="乖離率 (60日)"
                                        value={`${data.technical_indicators.deviation_60d.toFixed(2)}%`}
                                    />
                                    <div className="border border-gray-200 rounded-lg p-4 col-span-2">
                                        <div className="text-sm text-gray-500 mb-1">趨勢</div>
                                        <div className={`text-2xl font-bold ${data.technical_indicators.trend === '多頭' ? 'text-red-600' :
                                            data.technical_indicators.trend === '空頭' ? 'text-green-600' : 'text-gray-600'
                                            }`}>
                                            {data.technical_indicators.trend === '多頭' ? '🐂 ' :
                                                data.technical_indicators.trend === '空頭' ? '🐻 ' : ''}
                                            {data.technical_indicators.trend}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* 量價分析 (新增) */}
                        {data.volume_price_analysis && (
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                                    <span className="text-2xl mr-2">📊</span> 量價分析
                                    <span className={`ml-3 px-3 py-1 rounded-full text-sm font-medium ${data.volume_price_analysis.trend_direction === 'bullish'
                                        ? 'bg-red-100 text-red-700'
                                        : data.volume_price_analysis.trend_direction === 'bearish'
                                            ? 'bg-green-100 text-green-700'
                                            : 'bg-gray-100 text-gray-700'
                                        }`}>
                                        {data.volume_price_analysis.trend_direction === 'bullish' ? '🔴 看漲'
                                            : data.volume_price_analysis.trend_direction === 'bearish' ? '🟢 看跌'
                                                : '⚪ 盤整'}
                                    </span>
                                </h3>

                                {/* 量價確認 + 趨勢預測 */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                                    {/* 量價確認 */}
                                    <div className={`p-4 rounded-lg border-2 ${data.volume_price_analysis.confirmation_signal === 'bullish_confirmation'
                                        ? 'bg-red-50 border-red-300'
                                        : data.volume_price_analysis.confirmation_signal === 'bearish_confirmation'
                                            ? 'bg-green-50 border-green-300'
                                            : data.volume_price_analysis.confirmation_signal === 'caution'
                                                ? 'bg-yellow-50 border-yellow-300'
                                                : 'bg-gray-50 border-gray-300'
                                        }`}>
                                        <div className="text-sm text-gray-600 mb-1">量價確認</div>
                                        <div className={`text-2xl font-bold ${data.volume_price_analysis.confirmation_signal === 'bullish_confirmation'
                                            ? 'text-red-700'
                                            : data.volume_price_analysis.confirmation_signal === 'bearish_confirmation'
                                                ? 'text-green-700'
                                                : data.volume_price_analysis.confirmation_signal === 'caution'
                                                    ? 'text-yellow-700'
                                                    : 'text-gray-700'
                                            }`}>
                                            {data.volume_price_analysis.volume_price_confirmation}
                                        </div>
                                        <div className="text-xs text-gray-500 mt-1">
                                            信號強度: {(data.volume_price_analysis.confirmation_strength * 100).toFixed(0)}%
                                        </div>
                                    </div>

                                    {/* 趨勢預測 */}
                                    <div className="p-4 rounded-lg border-2 bg-blue-50 border-blue-300">
                                        <div className="text-sm text-gray-600 mb-1">趨勢預測</div>
                                        <div className="text-2xl font-bold text-blue-700">
                                            {data.volume_price_analysis.predicted_direction === 'up' ? '📈 上漲'
                                                : data.volume_price_analysis.predicted_direction === 'down' ? '📉 下跌'
                                                    : '➡️ 盤整'}
                                        </div>
                                        <div className="flex gap-2 mt-2 text-xs">
                                            <span className="px-2 py-1 bg-red-100 text-red-700 rounded">
                                                漲 {(data.volume_price_analysis.prediction_probability.up * 100).toFixed(0)}%
                                            </span>
                                            <span className="px-2 py-1 bg-green-100 text-green-700 rounded">
                                                跌 {(data.volume_price_analysis.prediction_probability.down * 100).toFixed(0)}%
                                            </span>
                                            <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded">
                                                整 {(data.volume_price_analysis.prediction_probability.sideways * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* 量價指標 */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                    <div className="border border-gray-200 rounded-lg p-4">
                                        <div className="text-sm text-gray-500 mb-1">量比</div>
                                        <div className={`text-xl font-bold ${data.volume_price_analysis.volume_ratio > 1.5
                                            ? 'text-red-600'
                                            : data.volume_price_analysis.volume_ratio < 0.5
                                                ? 'text-green-600'
                                                : 'text-gray-700'
                                            }`}>
                                            {data.volume_price_analysis.volume_ratio.toFixed(2)}x
                                        </div>
                                        <div className="text-xs text-gray-400">
                                            {data.volume_price_analysis.volume_ratio > 2 ? '爆量'
                                                : data.volume_price_analysis.volume_ratio > 1.5 ? '放量'
                                                    : data.volume_price_analysis.volume_ratio < 0.5 ? '萎縮'
                                                        : '正常'}
                                        </div>
                                    </div>

                                    <div className="border border-gray-200 rounded-lg p-4">
                                        <div className="text-sm text-gray-500 mb-1">OBV 能量潮</div>
                                        <div className={`text-xl font-bold ${data.volume_price_analysis.obv_trend === 'bullish'
                                            ? 'text-red-600'
                                            : data.volume_price_analysis.obv_trend === 'bearish'
                                                ? 'text-green-600'
                                                : 'text-gray-700'
                                            }`}>
                                            {data.volume_price_analysis.obv_trend === 'bullish' ? '↑ 多頭'
                                                : data.volume_price_analysis.obv_trend === 'bearish' ? '↓ 空頭'
                                                    : '→ 中性'}
                                        </div>
                                        <div className="text-xs text-gray-400">資金流向</div>
                                    </div>

                                    <div className="border border-gray-200 rounded-lg p-4">
                                        <div className="text-sm text-gray-500 mb-1">VWAP</div>
                                        <div className="text-xl font-bold text-gray-700">
                                            ${data.volume_price_analysis.vwap.toFixed(2)}
                                        </div>
                                        <div className={`text-xs ${data.volume_price_analysis.vwap_deviation > 0
                                            ? 'text-red-500'
                                            : 'text-green-500'
                                            }`}>
                                            偏離 {data.volume_price_analysis.vwap_deviation > 0 ? '+' : ''}
                                            {data.volume_price_analysis.vwap_deviation.toFixed(2)}%
                                        </div>
                                    </div>

                                    <div className="border border-gray-200 rounded-lg p-4">
                                        <div className="text-sm text-gray-500 mb-1">量能趨勢</div>
                                        <div className={`text-xl font-bold ${data.volume_price_analysis.volume_trend === 'increasing'
                                            ? 'text-red-600'
                                            : data.volume_price_analysis.volume_trend === 'decreasing'
                                                ? 'text-green-600'
                                                : 'text-gray-700'
                                            }`}>
                                            {data.volume_price_analysis.volume_trend === 'increasing' ? '📈 放大'
                                                : data.volume_price_analysis.volume_trend === 'decreasing' ? '📉 縮小'
                                                    : '➡️ 穩定'}
                                        </div>
                                        <div className="text-xs text-gray-400">5日均量 vs 20日均量</div>
                                    </div>
                                </div>

                                {/* 背離警示 */}
                                {data.volume_price_analysis.divergence_detected && (
                                    <div className={`p-4 rounded-lg border-2 mb-4 ${data.volume_price_analysis.divergence_type === 'bullish_divergence'
                                        ? 'bg-green-50 border-green-300'
                                        : 'bg-red-50 border-red-300'
                                        }`}>
                                        <div className="flex items-center gap-2">
                                            <span className="text-2xl">⚠️</span>
                                            <div>
                                                <div className={`font-bold ${data.volume_price_analysis.divergence_type === 'bullish_divergence'
                                                    ? 'text-green-700'
                                                    : 'text-red-700'
                                                    }`}>
                                                    {data.volume_price_analysis.divergence_type === 'bullish_divergence'
                                                        ? '🟢 看漲背離 (底部訊號)'
                                                        : '🔴 看跌背離 (頭部警告)'}
                                                </div>
                                                <div className="text-sm text-gray-600">
                                                    {data.volume_price_analysis.divergence_description}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* 混合訊號說明 */}
                                {data.volume_price_analysis.confirmation_signal === 'bullish_confirmation' &&
                                    data.volume_price_analysis.divergence_type === 'bearish_divergence' && (
                                        <div className="p-4 rounded-lg border-2 bg-amber-50 border-amber-300 mb-4">
                                            <div className="flex items-center gap-2">
                                                <span className="text-2xl">💡</span>
                                                <div>
                                                    <div className="font-bold text-amber-700">
                                                        混合訊號提醒
                                                    </div>
                                                    <div className="text-sm text-gray-600">
                                                        今日量價確認多方（價漲量增），但中期出現背離警告。
                                                        這可能代表<strong>短線強勢但需注意反轉風險</strong>。
                                                        建議：密切關注後續量能是否持續。
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                {/* 關鍵量價訊號 */}
                                {data.volume_price_analysis.key_signals && data.volume_price_analysis.key_signals.length > 0 && (
                                    <div className="pt-4 border-t border-gray-200">
                                        <div className="text-sm text-gray-600 mb-2">🎯 關鍵量價訊號</div>
                                        <div className="flex flex-wrap gap-2">
                                            {data.volume_price_analysis.key_signals.map((signal, idx) => (
                                                <span
                                                    key={idx}
                                                    className={`px-3 py-1 rounded-full text-sm font-medium ${signal.includes('背離') || signal.includes('確認空頭')
                                                        ? 'bg-red-100 text-red-700'
                                                        : signal.includes('突破') || signal.includes('確認多頭')
                                                            ? 'bg-green-100 text-green-700'
                                                            : 'bg-blue-100 text-blue-700'
                                                        }`}
                                                >
                                                    {signal}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* 置信度 */}
                                <div className="mt-4 pt-4 border-t border-gray-200">
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-gray-600">分析置信度</span>
                                        <span className="font-bold text-blue-700">
                                            {data.volume_price_analysis.trend_confidence.toFixed(1)}%
                                        </span>
                                    </div>
                                    <div className="w-full h-2 bg-gray-200 rounded-full mt-2 overflow-hidden">
                                        <div
                                            className="h-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-500"
                                            style={{ width: `${data.volume_price_analysis.trend_confidence}%` }}
                                        ></div>
                                    </div>
                                </div>
                            </div>
                        )}


                        {/* 法人籌碼分析區塊 */}
                        <InstitutionalChipSection
                            stockCode={stockCode}
                            chipData={chipData}
                            setChipData={setChipData}
                            chipLoading={chipLoading}
                            setChipLoading={setChipLoading}
                            continuousData={continuousData}
                            setContinuousData={setContinuousData}
                            chipTab={chipTab}
                            setChipTab={setChipTab}
                        />

                        {/* 重要日期事件 */}
                        {data.events && (
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                                    <span className="text-2xl mr-2">📅</span> 重要日期
                                </h3>
                                <div className="space-y-3">
                                    {/* 月營收 */}
                                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                        <span className="text-gray-600">📊 月營收</span>
                                        <div className="text-right">
                                            <div className="text-sm text-gray-500">{data.events.last_revenue_month} 已公告</div>
                                            <div className="text-sm font-medium">下次: {data.events.next_revenue_date}</div>
                                        </div>
                                    </div>

                                    {/* 季財報 */}
                                    {data.events.next_quarterly_report && (
                                        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                            <span className="text-gray-600">📋 季財報</span>
                                            <div className="text-right">
                                                <div className="text-sm font-medium">{data.events.next_quarterly_report.quarter} 財報</div>
                                                <div className="text-sm text-gray-500">截止: {data.events.next_quarterly_report.deadline}</div>
                                            </div>
                                        </div>
                                    )}

                                    {/* 殖利率 */}
                                    {data.events.dividend && data.events.dividend.dividend_yield && data.events.dividend.dividend_yield > 0 && (
                                        <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                                            <span className="text-gray-600">💰 殖利率</span>
                                            <div className="text-right">
                                                <div className="text-lg font-bold text-green-600">{data.events.dividend.dividend_yield.toFixed(2)}%</div>
                                                <div className="text-sm text-gray-500">年度股利: ${data.events.dividend.annual_dividend?.toFixed(2)}</div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* 相關新聞 */}
                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                                    <span className="text-2xl mr-2">📰</span> 最新消息
                                    <span className="ml-2 text-xs text-gray-400 font-normal">(Wantgoo)</span>
                                </h3>
                                <button
                                    onClick={fetchNews}
                                    disabled={newsLoading}
                                    className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center ${newsLoading
                                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                        : 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white hover:from-purple-600 hover:to-indigo-700 shadow-md hover:shadow-lg'
                                        }`}
                                >
                                    {newsLoading ? (
                                        <>
                                            <span className="animate-spin mr-2">⏳</span>
                                            搜尋中...
                                        </>
                                    ) : (
                                        <>
                                            <span className="mr-2">🔍</span>
                                            {newsData.length > 0 ? '重新取得消息' : '取得最新消息'}
                                        </>
                                    )}
                                </button>
                            </div>

                            {/* 錯誤訊息 */}
                            {newsError && (
                                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                    ⚠️ {newsError}
                                </div>
                            )}

                            {/* 新聞列表 */}
                            {newsData.length > 0 ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {newsData.map((news, idx) => (
                                        <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                                            <div className="flex items-start justify-between">
                                                <h4 className="font-medium text-gray-900 flex-1">{news.title}</h4>
                                                <span className={`ml-2 px-2 py-1 rounded text-xs ${news.sentiment === 'positive' ? 'bg-red-100 text-red-700' :
                                                    news.sentiment === 'negative' ? 'bg-green-100 text-green-700' :
                                                        'bg-gray-100 text-gray-700'
                                                    }`}>
                                                    {news.sentiment === 'positive' ? '🔴 正面' :
                                                        news.sentiment === 'negative' ? '🟢 負面' : '⚪ 中性'}
                                                </span>
                                            </div>
                                            {news.summary && <p className="text-sm text-gray-600 mt-2">{news.summary}</p>}
                                            <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
                                                <span>{news.source}</span>
                                                <span>{news.date}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-gray-500">
                                    <div className="text-4xl mb-3">📡</div>
                                    <p>點擊上方按鈕取得 {data?.stock_name || stockCode} 的最新消息</p>
                                    <p className="text-xs text-gray-400 mt-2">資料來源: wantgoo.com</p>
                                </div>
                            )}
                        </div>

                        {/* AI 摘要 */}
                        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl shadow-sm p-6 text-white">
                            <h3 className="text-lg font-semibold mb-4 flex items-center">
                                <span className="text-2xl mr-2">🤖</span> AI 分析摘要
                            </h3>
                            <p className="text-lg leading-relaxed">{data.ai_summary}</p>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}

// ==================== 子組件 ====================

function FinancialCard({ label, value, status, benchmark }: {
    label: string;
    value: string;
    status: 'good' | 'normal' | 'bad';
    benchmark?: string;
}) {
    // 台股習慣：好的=紅色，不好的=綠色
    const statusColors = {
        good: 'text-red-600',     // 好 = 紅色
        normal: 'text-gray-900',
        bad: 'text-green-600',    // 不好 = 綠色
    };

    return (
        <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">{label}</div>
            <div className={`text-2xl font-bold ${statusColors[status]}`}>{value}</div>
            {benchmark && (
                <div className={`text-xs mt-1 ${status === 'good' ? 'text-red-500' : status === 'bad' ? 'text-green-500' : 'text-gray-400'}`}>
                    {benchmark} {status === 'good' ? '✔' : status === 'bad' ? '✘' : ''}
                </div>
            )}
        </div>
    );
}

function ValuationCard({ label, value, status, benchmark }: {
    label: string;
    value: number | string;
    status: 'good' | 'normal' | 'bad';
    benchmark?: string;
}) {
    // 台股習慣：好的=紅色，不好的=綠色
    const statusColors = {
        good: 'text-red-600',     // 好 = 紅色
        normal: 'text-gray-900',
        bad: 'text-green-600',    // 不好 = 綠色
    };

    return (
        <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">{label}</div>
            <div className={`text-2xl font-bold ${statusColors[status]}`}>
                {typeof value === 'number' ? value.toFixed(2) : value}
            </div>
            {benchmark && (
                <div className={`text-xs mt-1 ${status === 'good' ? 'text-red-500' : status === 'bad' ? 'text-green-500' : 'text-gray-400'}`}>
                    {benchmark}
                </div>
            )}
        </div>
    );
}

function TechnicalCard({ label, value, extra, status }: {
    label: string;
    value: string;
    extra?: string;
    status?: string;
}) {
    // 台股習慣：多頭=紅色，空頭=綠色
    const getStatusColor = () => {
        switch (status) {
            case 'bullish': return 'text-red-600';     // 多頭=紅色
            case 'bearish': return 'text-green-600';   // 空頭=綠色
            case 'overbought': return 'text-orange-500'; // 超買=橘色警示
            case 'oversold': return 'text-blue-500';   // 超賣=藍色
            case 'warning': return 'text-yellow-600';
            default: return 'text-gray-900';
        }
    };

    // 台股習慣：多頭=紅色，空頭=綠色
    const getStatusBadge = () => {
        switch (status) {
            case 'bullish': return <span className="ml-2 px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded">多頭強勢</span>;
            case 'bearish': return <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">空頭弱勢</span>;
            case 'overbought': return <span className="ml-2 px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded">超買</span>;
            case 'oversold': return <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">超賣</span>;
            default: return null;
        }
    };

    return (
        <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">{label}</div>
            <div className={`text-xl font-bold ${getStatusColor()}`}>
                {value}
                {getStatusBadge()}
            </div>
            {extra && <div className="text-xs text-gray-500 mt-1">{extra}</div>}
        </div>
    );
}

function InstitutionalCard({ label, value, isTotal }: {
    label: string;
    value: number;
    isTotal?: boolean;
}) {
    const formattedValue = Math.abs(value) >= 1000
        ? `${(value / 1000).toFixed(0)}K`
        : value.toLocaleString();

    // 台股習慣：買超=紅色，賣超=綠色
    return (
        <div className={`border rounded-lg p-4 ${isTotal ? 'border-blue-300 bg-blue-50' : 'border-gray-200'}`}>
            <div className="text-sm text-gray-500 mb-1">{label}</div>
            <div className={`text-2xl font-bold ${value > 0 ? 'text-red-600' : value < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                {value > 0 ? '+' : ''}{formattedValue}
                <span className="text-sm ml-1">張</span>
            </div>
            <div className={`text-xs mt-1 ${value > 0 ? 'text-red-500' : value < 0 ? 'text-green-500' : 'text-gray-400'}`}>
                {value > 0 ? '買超 🔺' : value < 0 ? '賣超 🔻' : '持平'}
            </div>
        </div>
    );
}

// ==================== 法人籌碼分析區塊 ====================
// ==================== 2日智能股價預測面板 ====================
function InstitutionalChipSection({
    stockCode,
}: {
    stockCode: string;
    chipData?: any;
    setChipData?: any;
    chipLoading?: boolean;
    setChipLoading?: any;
    continuousData?: any;
    setContinuousData?: any;
    chipTab?: any;
    setChipTab?: any;
}) {
    const [pred, setPred] = React.useState<any>(null);
    const [pred5, setPred5] = React.useState<any>(null);
    const [loading, setLoading] = React.useState(false);
    const [history, setHistory] = React.useState<any[]>([]);
    const [training, setTraining] = React.useState(false);
    const [trainMsg, setTrainMsg] = React.useState('');
    const API = 'http://localhost:8000/api/prediction';

    const fetchPrediction = async () => {
        if (!stockCode || stockCode === 'NONE') return;
        setLoading(true);
        try {
            const [r2, r5] = await Promise.all([
                fetch(`${API}/${stockCode}?horizon=2&save=true`),
                fetch(`${API}/${stockCode}?horizon=5&save=false`),
            ]);
            if (r2.ok) setPred(await r2.json());
            if (r5.ok) setPred5(await r5.json());

            // 取歷史準確率
            const rh = await fetch(`${API}/history/${stockCode}?limit=10`);
            if (rh.ok) {
                const d = await rh.json();
                setHistory(d.history || []);
            }
        } catch (e) {
            console.error('預測失敗:', e);
        } finally {
            setLoading(false);
        }
    };

    const triggerTraining = async () => {
        setTraining(true);
        setTrainMsg('訓練中（約需1-2分鐘）...');
        try {
            const r = await fetch(`${API}/train/${stockCode}?horizon=2`, { method: 'POST' });
            const d = await r.json();
            setTrainMsg(d.message || '訓練已啟動');
            setTimeout(() => { setTrainMsg(''); fetchPrediction(); }, 90000);
        } catch {
            setTrainMsg('訓練失敗');
        } finally {
            setTraining(false);
        }
    };

    React.useEffect(() => {
        if (stockCode && stockCode !== 'NONE') fetchPrediction();
    }, [stockCode]);

    const dirColor = (dir: string) =>
        dir === 'up' ? 'text-red-600' : dir === 'down' ? 'text-green-600' : 'text-gray-500';
    const dirBg = (dir: string) =>
        dir === 'up' ? 'from-red-500 to-rose-600' : dir === 'down' ? 'from-green-500 to-emerald-600' : 'from-gray-400 to-gray-500';
    const dirEmoji = (dir: string) =>
        dir === 'up' ? '📈' : dir === 'down' ? '📉' : '➡️';
    const dirLabel = (dir: string) =>
        dir === 'up' ? '上漲' : dir === 'down' ? '下跌' : '盤整';

    const accuracy = pred?.accuracy_stats?.direction_accuracy_pct ?? 0;
    const totalVerified = pred?.accuracy_stats?.total ?? 0;
    const correctCount = pred?.accuracy_stats?.correct ?? 0;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            {/* 標題列 */}
            <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <span className="text-2xl">🤖</span>
                    AI 股價預測
                    <span className="ml-1 px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded-full font-medium">LSTM v2 自學</span>
                </h3>
                <div className="flex gap-2">
                    <button
                        onClick={triggerTraining}
                        disabled={training}
                        title="重新訓練 LSTM 模型（需 1-2 分鐘）"
                        className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-all disabled:opacity-50"
                    >
                        {training ? '⏳ 訓練中' : '🎓 訓練模型'}
                    </button>
                    <button
                        onClick={fetchPrediction}
                        disabled={loading}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-all flex items-center gap-1 ${loading
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:from-indigo-600 hover:to-purple-700 shadow-md'
                        }`}
                    >
                        {loading ? <><span className="animate-spin">⏳</span> 計算中</> : <><span>🔄</span> {pred ? '重新預測' : '開始預測'}</>}
                    </button>
                </div>
            </div>

            {trainMsg && (
                <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">
                    ⚙️ {trainMsg}
                </div>
            )}

            {!pred ? (
                <div className="text-center py-10 text-gray-400">
                    <div className="text-5xl mb-3">🤖</div>
                    <p className="text-base text-gray-500">點擊「開始預測」取得 2日/5日 AI 預測</p>
                    <p className="text-xs mt-2">使用 LSTM 神經網路 + 18個技術指標特徵</p>
                    <p className="text-xs text-indigo-500 mt-1">每次預測自動存入 PostgreSQL，收盤後自動驗證準確率</p>
                </div>
            ) : (
                <div className="space-y-5">

                    {/* 主預測卡片（2日）*/}
                    <div className={`p-5 rounded-xl bg-gradient-to-r ${dirBg(pred.prediction.predicted_direction)} text-white`}>
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="text-sm opacity-80">2 日後預測方向</div>
                                <div className="text-4xl font-bold mt-1">
                                    {dirEmoji(pred.prediction.predicted_direction)} {dirLabel(pred.prediction.predicted_direction)}
                                </div>
                                <div className="text-sm opacity-80 mt-1">
                                    目標日期：{pred.prediction.target_date}
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-sm opacity-80">預測價格</div>
                                <div className="text-3xl font-bold">${pred.prediction.predicted_price?.toLocaleString()}</div>
                                <div className={`text-lg font-semibold mt-1`}>
                                    {pred.prediction.predicted_change_pct > 0 ? '+' : ''}{pred.prediction.predicted_change_pct?.toFixed(2)}%
                                </div>
                            </div>
                        </div>

                        {/* 信心度條 */}
                        <div className="mt-4 pt-4 border-t border-white/30">
                            <div className="flex justify-between text-sm mb-1">
                                <span className="opacity-80">模型信心度</span>
                                <span className="font-bold">{pred.prediction.confidence?.toFixed(1)}%</span>
                            </div>
                            <div className="w-full bg-white/30 rounded-full h-2">
                                <div
                                    className="bg-white rounded-full h-2 transition-all"
                                    style={{ width: `${Math.min(100, pred.prediction.confidence || 0)}%` }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* 預測區間 + 5日對比 */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                            <div className="text-xs text-gray-500 mb-2 font-medium">2日預測區間</div>
                            <div className="space-y-1.5">
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-gray-500">樂觀上界</span>
                                    <span className="text-sm font-bold text-red-600">${pred.prediction.predicted_high?.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-gray-500">目標中值</span>
                                    <span className="text-sm font-bold text-gray-800">${pred.prediction.predicted_price?.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-xs text-gray-500">悲觀下界</span>
                                    <span className="text-sm font-bold text-green-600">${pred.prediction.predicted_low?.toLocaleString()}</span>
                                </div>
                            </div>
                        </div>

                        {pred5 && (
                            <div className={`p-4 rounded-xl border ${pred5.prediction.predicted_direction === 'up' ? 'bg-red-50 border-red-200' : pred5.prediction.predicted_direction === 'down' ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                                <div className="text-xs text-gray-500 mb-2 font-medium">5日預測（週線）</div>
                                <div className={`text-2xl font-bold ${dirColor(pred5.prediction.predicted_direction)}`}>
                                    {dirEmoji(pred5.prediction.predicted_direction)} {dirLabel(pred5.prediction.predicted_direction)}
                                </div>
                                <div className={`text-sm font-semibold mt-1 ${dirColor(pred5.prediction.predicted_direction)}`}>
                                    ${pred5.prediction.predicted_price?.toLocaleString()}
                                    （{pred5.prediction.predicted_change_pct > 0 ? '+' : ''}{pred5.prediction.predicted_change_pct?.toFixed(2)}%）
                                </div>
                                <div className="text-xs text-gray-400 mt-1">信心 {pred5.prediction.confidence?.toFixed(1)}%</div>
                            </div>
                        )}
                    </div>

                    {/* 關鍵指標快照 */}
                    {pred.key_indicators && (
                        <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                            <div className="text-xs text-indigo-700 font-semibold mb-3">🔬 預測依據（18特徵快照）</div>
                            <div className="grid grid-cols-4 gap-3">
                                {[
                                    { label: 'RSI(14)', val: pred.key_indicators.rsi?.toFixed(1), warn: pred.key_indicators.rsi < 30 ? '超賣' : pred.key_indicators.rsi > 70 ? '超買' : '' },
                                    { label: 'MACD', val: pred.key_indicators.macd?.toFixed(3), warn: '' },
                                    { label: 'VIX', val: pred.key_indicators.vix?.toFixed(1), warn: pred.key_indicators.vix > 30 ? '高恐慌' : '' },
                                    { label: '法人籌碼', val: (pred.key_indicators.inst_net > 0 ? '+' : '') + (pred.key_indicators.inst_net || 0).toLocaleString(), warn: '' },
                                ].map((ind) => (
                                    <div key={ind.label} className="text-center p-2 bg-white rounded-lg">
                                        <div className="text-xs text-gray-500">{ind.label}</div>
                                        <div className="text-sm font-bold text-indigo-700">{ind.val ?? '-'}</div>
                                        {ind.warn && <div className="text-xs text-orange-500">{ind.warn}</div>}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 自學準確率追蹤 */}
                    <div className="p-4 bg-gradient-to-r from-gray-50 to-slate-50 rounded-xl border border-gray-200">
                        <div className="flex items-center justify-between mb-3">
                            <div className="text-xs text-gray-600 font-semibold">📊 模型準確率追蹤（14日）</div>
                            <div className={`text-xs font-bold px-2 py-0.5 rounded-full ${accuracy >= 80 ? 'bg-green-100 text-green-700' : accuracy >= 60 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                                {totalVerified > 0 ? `${accuracy}%（${correctCount}/${totalVerified}）` : '尚無驗證資料'}
                            </div>
                        </div>

                        {/* 進度條朝 80% 目標 */}
                        <div className="mb-2">
                            <div className="flex justify-between text-xs text-gray-400 mb-1">
                                <span>當前準確率</span><span>目標 80%</span>
                            </div>
                            <div className="relative w-full bg-gray-200 rounded-full h-3">
                                <div
                                    className={`h-3 rounded-full transition-all ${accuracy >= 80 ? 'bg-green-500' : accuracy >= 60 ? 'bg-yellow-500' : 'bg-red-400'}`}
                                    style={{ width: `${Math.min(100, accuracy)}%` }}
                                />
                                {/* 80% 標記線 */}
                                <div className="absolute top-0 bottom-0 border-l-2 border-dashed border-indigo-400" style={{ left: '80%' }} />
                            </div>
                        </div>

                        {/* 模型來源 */}
                        <div className="text-xs text-gray-400 mt-2">
                            模型：{pred.model.source === 'lstm_v2' ? '✅ LSTM v2（已訓練）' : '⚠️ 技術指標備援（尚未訓練 LSTM）'}
                            {pred.model.source !== 'lstm_v2' && (
                                <span className="ml-1 text-indigo-500">→ 點「訓練模型」以啟動 LSTM</span>
                            )}
                        </div>

                        {/* 近期預測歷史 */}
                        {history.length > 0 && (
                            <div className="mt-3 space-y-1">
                                <div className="text-xs text-gray-500 font-medium mb-1">近期預測記錄</div>
                                {history.slice(0, 5).map((h, i) => (
                                    <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-gray-100 last:border-0">
                                        <span className="text-gray-500">{h.prediction_date} → {h.target_date}</span>
                                        <span className={dirColor(h.predicted_direction)}>{dirEmoji(h.predicted_direction)} {dirLabel(h.predicted_direction)}</span>
                                        {h.is_verified ? (
                                            <span className={`font-bold ${h.direction_correct ? 'text-green-600' : 'text-red-500'}`}>
                                                {h.direction_correct ? '✅ 正確' : '❌ 錯誤'}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400">⏳ 待驗證</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* 聲明 */}
                    <div className="text-xs text-gray-400 text-center">
                        💡 預測僅供參考，不構成投資建議。每日 14:00 自動更新，16:00 驗證準確率並回饋學習。
                    </div>
                </div>
            )}
        </div>
    );
}

