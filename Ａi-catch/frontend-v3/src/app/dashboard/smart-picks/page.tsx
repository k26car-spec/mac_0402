'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, RefreshCw, Newspaper, Star, Target, AlertTriangle, Clock, Flame, BarChart3, Brain, Filter } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface ExpertDetail {
    狀態: string;
    說明: string;
}

interface ExpertResult {
    avg_score: number;
    scores: Record<string, number>;
    details: Record<string, ExpertDetail>;
    summary: string;
}

interface SmartPick {
    stock_code: string;
    stock_name: string;
    price: number;
    volume: number;
    news_heat: number;
    news_sentiment: string;
    expert_score: number;
    expert_details: ExpertResult;
    recommendation: string;
    timeframe: string;
    entry_price: number;
    target_price: number;
    stop_loss: number;
    reasons: string[];
}

interface NewsTheme {
    theme: string;
    news_count: number;
    sample_news: string[];
}

interface SmartPicksResponse {
    status: string;
    timestamp: string;
    from_cache?: boolean;
    market_summary: {
        total_candidates: number;
        news_sentiment: string;
        recommendation: string;
    };
    short_term: SmartPick[];
    mid_term: SmartPick[];
    long_term: SmartPick[];
    filters_applied: {
        max_price: number;
        min_price: number;
        min_volume: number;
        min_news_mentions: number;
    };
    news_report: {
        total_news: number;
        key_themes: NewsTheme[];
    };
    institutional?: {
        date: string;
        data: { name: string; buy: string; sell: string; diff: string; }[];
        source: string;
    };
}

export default function SmartPicksPage() {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<SmartPicksResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    // 篩選條件
    const [maxPrice, setMaxPrice] = useState(2000);
    const [minVolume, setMinVolume] = useState(100);
    const [showFilters, setShowFilters] = useState(false);

    const fetchSmartPicks = async () => {
        setLoading(true);
        setError(null);

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 分鐘超時

            const response = await fetch('http://localhost:8000/api/smart-picks/smart-picks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    max_price: maxPrice,
                    min_price: 10,
                    min_volume: minVolume,
                    min_news_mentions: 1,
                    include_categories: []
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`伺服器錯誤: ${response.status}`);
            }

            const result = await response.json();
            setData(result);
        } catch (err) {
            if (err instanceof Error && err.name === 'AbortError') {
                setError('請求超時（2分鐘），請稍後再試。如果問題持續，請重啟後端服務。');
            } else {
                setError(err instanceof Error ? err.message : '獲取數據失敗');
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSmartPicks();
    }, []);

    const getRecommendationStyle = (rec: string) => {
        switch (rec) {
            case '強烈推薦': return 'bg-red-100 text-red-700 border-red-200';
            case '一般推薦': return 'bg-orange-100 text-orange-700 border-orange-200';
            case '觀察': return 'bg-yellow-100 text-yellow-700 border-yellow-200';
            default: return 'bg-gray-100 text-gray-700 border-gray-200';
        }
    };

    const getHeatLevel = (heat: number) => {
        if (heat >= 5) return { text: '🔥🔥🔥 極高', color: 'text-red-600' };
        if (heat >= 3) return { text: '🔥🔥 高', color: 'text-orange-600' };
        if (heat >= 1) return { text: '🔥 一般', color: 'text-yellow-600' };
        return { text: '○ 低', color: 'text-gray-400' };
    };

    const StockCard = ({ stock, rank }: { stock: SmartPick; rank: number }) => {
        const heat = getHeatLevel(stock.news_heat);

        return (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
                {/* Header */}
                <div className="p-4 border-b border-gray-100 bg-gray-50/50">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center font-bold text-lg">
                                {rank}
                            </div>
                            <div>
                                <Link href={`/dashboard/chart?symbol=${stock.stock_code}`} className="font-bold text-gray-900 hover:text-blue-600 transition-colors">
                                    {stock.stock_code} {stock.stock_name}
                                </Link>
                                <div className={cn("text-xs font-medium", heat.color)}>新聞熱度: {heat.text}</div>
                            </div>
                        </div>
                        <div className={cn("px-3 py-1 rounded-full text-xs font-bold border", getRecommendationStyle(stock.recommendation))}>
                            {stock.recommendation}
                        </div>
                    </div>
                </div>

                {/* Body */}
                <div className="p-4">
                    {/* 關鍵指標 */}
                    <div className="grid grid-cols-3 gap-4 mb-4">
                        <div className="text-center p-3 bg-gray-50 rounded-lg">
                            <div className="text-2xl font-black text-gray-900">${stock.price.toFixed(1)}</div>
                            <div className="text-xs text-gray-500 mt-1">現價</div>
                        </div>
                        <div className="text-center p-3 bg-blue-50 rounded-lg">
                            <div className="text-2xl font-black text-blue-600">{stock.expert_score.toFixed(0)}<span className="text-sm">%</span></div>
                            <div className="text-xs text-gray-500 mt-1">AI評分</div>
                        </div>
                        <div className="text-center p-3 bg-gray-50 rounded-lg">
                            <div className="text-2xl font-black text-gray-700">{stock.volume}</div>
                            <div className="text-xs text-gray-500 mt-1">成交量</div>
                        </div>
                    </div>

                    {/* 進場/目標/停損 */}
                    <div className="flex items-center justify-between text-sm bg-gray-50 rounded-lg p-3 mb-4">
                        <div className="text-center">
                            <div className="text-xs text-gray-500">進場</div>
                            <div className="font-bold text-green-600">${stock.entry_price.toFixed(1)}</div>
                        </div>
                        <div className="text-gray-300">→</div>
                        <div className="text-center">
                            <div className="text-xs text-gray-500">目標</div>
                            <div className="font-bold text-blue-600">${stock.target_price.toFixed(1)}</div>
                        </div>
                        <div className="text-gray-300">|</div>
                        <div className="text-center">
                            <div className="text-xs text-gray-500">停損</div>
                            <div className="font-bold text-red-600">${stock.stop_loss.toFixed(1)}</div>
                        </div>
                    </div>

                    {/* 推薦理由 */}
                    <div className="space-y-1 mb-3">
                        {stock.reasons.slice(0, 2).map((reason, i) => (
                            <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
                                <span className="text-green-500 mt-0.5">✓</span>
                                <span>{reason}</span>
                            </div>
                        ))}
                    </div>

                    {/* AI 評分摘要 */}
                    {stock.expert_details && (
                        <div className="border-t border-gray-100 pt-3">
                            <div className="text-xs text-gray-500 mb-2">
                                {stock.expert_details.summary}
                            </div>

                            {/* 9 專家評分詳情 */}
                            <div className="grid grid-cols-3 gap-1">
                                {stock.expert_details.scores && Object.entries(stock.expert_details.scores).map(([expert, score]) => {
                                    const numScore = typeof score === 'number' ? score : 50;
                                    const detail = stock.expert_details.details?.[expert];

                                    return (
                                        <div
                                            key={expert}
                                            className="text-center p-1.5 rounded hover:bg-gray-50 cursor-default"
                                            title={detail?.說明 || ''}
                                        >
                                            <div className={cn(
                                                "text-xs font-bold",
                                                numScore >= 70 ? "text-green-600" :
                                                    numScore >= 50 ? "text-yellow-600" :
                                                        "text-red-500"
                                            )}>
                                                {numScore}
                                            </div>
                                            <div className="text-[10px] text-gray-400">{expert}</div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Brain className="w-8 h-8 text-purple-600" />
                        AI 智慧選股
                        {data?.from_cache && (
                            <span className="text-xs font-normal bg-yellow-100 text-yellow-700 px-2 py-1 rounded">
                                📦 快取資料
                            </span>
                        )}
                    </h1>
                    <p className="text-gray-600 mt-2">
                        新聞熱度分析 × 價格篩選 × 9專家綜合評分
                        {data?.timestamp && (
                            <span className="ml-2 text-xs text-gray-400">
                                更新時間: {new Date(data.timestamp).toLocaleTimeString('zh-TW')}
                            </span>
                        )}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setShowFilters(!showFilters)}
                        className={cn(
                            "px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors border",
                            showFilters ? "bg-blue-50 text-blue-600 border-blue-200" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                        )}
                    >
                        <Filter className="w-4 h-4" />
                        篩選條件
                    </button>
                    <button
                        onClick={fetchSmartPicks}
                        disabled={loading}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                    >
                        {loading ? (
                            <>
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                分析中...
                            </>
                        ) : (
                            <>
                                <RefreshCw className="w-4 h-4" />
                                重新分析
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Filters Panel */}
            {showFilters && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                    <div className="flex flex-wrap items-center gap-6">
                        <div className="flex items-center gap-2">
                            <label className="text-sm text-gray-600">股價上限:</label>
                            <input
                                type="number"
                                value={maxPrice}
                                onChange={(e) => setMaxPrice(Number(e.target.value))}
                                className="w-24 px-3 py-2 border border-gray-200 rounded-lg text-center text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                            <span className="text-gray-400 text-sm">元</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <label className="text-sm text-gray-600">最低成交量:</label>
                            <input
                                type="number"
                                value={minVolume}
                                onChange={(e) => setMinVolume(Number(e.target.value))}
                                className="w-24 px-3 py-2 border border-gray-200 rounded-lg text-center text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                            />
                            <span className="text-gray-400 text-sm">張/日</span>
                        </div>
                        <button
                            onClick={fetchSmartPicks}
                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium"
                        >
                            套用篩選
                        </button>
                        {data && (
                            <div className="text-sm text-gray-500 ml-auto flex items-center gap-4">
                                <span>市場情緒: <span className="font-medium text-yellow-600">{data.market_summary.news_sentiment}</span></span>
                                <span>候選股: <span className="font-medium text-blue-600">{data.market_summary.total_candidates}</span></span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* 📊 AI 評分操作建議 */}
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-200 shadow-sm p-5">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold text-gray-900 flex items-center gap-2">
                        <Brain className="w-5 h-5 text-purple-600" />
                        📋 AI 評分操作建議
                    </h3>
                    <span className="text-xs text-gray-400">評分範圍 0-100</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-green-100 border border-green-300 rounded-lg p-3 text-center">
                        <div className="text-green-600 font-bold text-lg">🔥 ≥70分</div>
                        <div className="text-green-700 font-semibold">強烈買進</div>
                        <div className="text-green-600 text-xs mt-1">分批進場・減低成本</div>
                    </div>
                    <div className="bg-blue-100 border border-blue-300 rounded-lg p-3 text-center">
                        <div className="text-blue-600 font-bold text-lg">💚 60-69分</div>
                        <div className="text-blue-700 font-semibold">建議買進</div>
                        <div className="text-blue-600 text-xs mt-1">逢低布局・耐心持有</div>
                    </div>
                    <div className="bg-yellow-100 border border-yellow-300 rounded-lg p-3 text-center">
                        <div className="text-yellow-600 font-bold text-lg">🟡 45-59分</div>
                        <div className="text-yellow-700 font-semibold">觀望</div>
                        <div className="text-yellow-600 text-xs mt-1">等待訊號・暫不進場</div>
                    </div>
                    <div className="bg-red-100 border border-red-300 rounded-lg p-3 text-center">
                        <div className="text-red-600 font-bold text-lg">🔴 &lt;45分</div>
                        <div className="text-red-700 font-semibold">避開</div>
                        <div className="text-red-600 text-xs mt-1">風險較高・不建議進場</div>
                    </div>
                </div>
                <div className="mt-4 flex items-center justify-between text-xs">
                    <p className="text-gray-600 bg-white/50 px-3 py-2 rounded-lg">
                        💡 <strong>穩健投資人建議</strong>：≥65分 再考慮添購，搭配主力進場+成交量放大訊號更佳
                    </p>
                    <p className="text-gray-400">
                        評分來源：9大專家系統綜合分析
                    </p>
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <div>
                        <div className="font-medium text-red-700">獲取資料失敗</div>
                        <div className="text-red-600 text-sm mt-1">{error}</div>
                        <div className="text-gray-500 text-xs mt-2">請確認後端服務 (port 8000) 是否正常運行</div>
                    </div>
                </div>
            )}

            {/* News Summary */}
            {data?.news_report?.key_themes && data.news_report.key_themes.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                    <h3 className="font-bold text-gray-900 flex items-center gap-2 mb-4">
                        <Newspaper className="w-5 h-5 text-blue-600" />
                        今日新聞重點
                        <span className="text-sm font-normal text-gray-400 ml-2">
                            共 {data.news_report.total_news || 0} 則新聞
                        </span>
                    </h3>

                    <div className="space-y-4">
                        {data.news_report.key_themes.map((theme, i) => (
                            <div key={i} className="border border-gray-100 rounded-lg overflow-hidden">
                                {/* 分類標題 */}
                                <div className="bg-gray-50 px-4 py-3 flex items-center gap-2 border-b border-gray-100">
                                    <Flame className="w-4 h-4 text-orange-500" />
                                    <span className="font-bold text-gray-800">{theme.theme}</span>
                                    <span className="text-sm text-gray-500">({theme.news_count}則)</span>
                                </div>

                                {/* 新聞內容列表 */}
                                <div className="p-3 space-y-2">
                                    {theme.sample_news && theme.sample_news.length > 0 ? (
                                        theme.sample_news.map((news, j) => (
                                            <div key={j} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg hover:bg-blue-50 transition-colors">
                                                <span className="text-blue-500 mt-0.5 flex-shrink-0">📰</span>
                                                <span className="text-sm text-gray-700 leading-relaxed">{news}</span>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-sm text-gray-400 text-center py-2">
                                            暫無新聞內容
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* 市場情緒總結 */}
                    <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="text-gray-600 text-sm">市場情緒:</span>
                            <span className={cn(
                                "px-3 py-1 rounded-full text-sm font-medium",
                                data.market_summary.news_sentiment === "偏多" ? "bg-red-100 text-red-700" :
                                    data.market_summary.news_sentiment === "偏空" ? "bg-green-100 text-green-700" :
                                        "bg-gray-100 text-gray-700"
                            )}>
                                {data.market_summary.news_sentiment}
                            </span>
                        </div>
                        <span className="text-xs text-gray-400">
                            資料來源: 鉅亨網 / Yahoo / 經濟日報 / PTT / GoodInfo / TWSE
                        </span>
                    </div>
                </div>
            )}

            {/* 三大法人買賣超 */}
            {data?.institutional?.data && data.institutional.data.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                    <h3 className="font-bold text-gray-900 flex items-center gap-2 mb-4">
                        <BarChart3 className="w-5 h-5 text-green-600" />
                        三大法人買賣超
                        <span className="text-sm font-normal text-gray-400 ml-2">
                            資料來源: {data.institutional.source}
                        </span>
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {data.institutional.data.map((item, i) => {
                            const diffValue = parseFloat(item.diff?.replace(/[,]/g, '') || '0');
                            const isPositive = diffValue > 0;

                            return (
                                <div key={i} className="bg-gray-50 rounded-lg p-4">
                                    <div className="text-sm text-gray-600 mb-2">{item.name}</div>
                                    <div className="flex items-center justify-between">
                                        <div className="text-xs text-gray-500">
                                            <div>買: {item.buy}</div>
                                            <div>賣: {item.sell}</div>
                                        </div>
                                        <div className={cn(
                                            "text-lg font-bold",
                                            isPositive ? "text-red-600" : "text-green-600"
                                        )}>
                                            {isPositive ? '+' : ''}{item.diff}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Loading State */}
            {loading && (
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12">
                    <div className="flex flex-col items-center justify-center">
                        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                            <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
                        </div>
                        <div className="text-xl font-bold text-gray-900 mb-2">正在分析市場熱門股票...</div>
                        <div className="text-gray-500 text-sm mb-4">爬取新聞 → 價格篩選 → 專家評分</div>
                        <div className="text-yellow-600 text-xs bg-yellow-50 px-3 py-1 rounded-full">
                            ⏳ 首次載入需要 1-2 分鐘，請耐心等候
                        </div>
                    </div>
                </div>
            )}

            {/* Results */}
            {!loading && data && (
                <div className="space-y-8">
                    {/* Short Term */}
                    <section>
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                            <h2 className="text-xl font-bold text-gray-900">短期推薦</h2>
                            <span className="text-sm text-gray-500">(1-5天)</span>
                            <span className="text-xs text-gray-400 ml-auto">共 {data.short_term.length} 檔</span>
                        </div>
                        {data.short_term.length > 0 ? (
                            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {data.short_term.map((stock, i) => (
                                    <StockCard key={stock.stock_code} stock={stock} rank={i + 1} />
                                ))}
                            </div>
                        ) : (
                            <div className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl p-8 text-center text-gray-500">
                                <Target className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                                <div>目前沒有符合條件的短期推薦</div>
                            </div>
                        )}
                    </section>

                    {/* Mid Term */}
                    <section>
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                            <h2 className="text-xl font-bold text-gray-900">中期推薦</h2>
                            <span className="text-sm text-gray-500">(1-4週)</span>
                            <span className="text-xs text-gray-400 ml-auto">共 {data.mid_term.length} 檔</span>
                        </div>
                        {data.mid_term.length > 0 ? (
                            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {data.mid_term.map((stock, i) => (
                                    <StockCard key={stock.stock_code} stock={stock} rank={i + 1} />
                                ))}
                            </div>
                        ) : (
                            <div className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl p-8 text-center text-gray-500">
                                <Target className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                                <div>目前沒有符合條件的中期推薦</div>
                            </div>
                        )}
                    </section>

                    {/* Long Term */}
                    <section>
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                            <h2 className="text-xl font-bold text-gray-900">長期推薦</h2>
                            <span className="text-sm text-gray-500">(1-3個月)</span>
                            <span className="text-xs text-gray-400 ml-auto">共 {data.long_term.length} 檔</span>
                        </div>
                        {data.long_term.length > 0 ? (
                            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {data.long_term.map((stock, i) => (
                                    <StockCard key={stock.stock_code} stock={stock} rank={i + 1} />
                                ))}
                            </div>
                        ) : (
                            <div className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-xl p-8 text-center text-gray-500">
                                <Target className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                                <div>目前沒有符合條件的長期推薦</div>
                            </div>
                        )}
                    </section>
                </div>
            )}

            {/* Footer Note */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-800">
                    <div className="font-medium">投資警語</div>
                    <div className="text-yellow-700 mt-1">
                        本系統僅供參考，不構成投資建議。投資有風險，請謹慎評估自身風險承受能力後再做決策。
                    </div>
                    {data && (
                        <div className="text-yellow-600 mt-2 flex items-center gap-2">
                            <Clock className="w-4 h-4" />
                            更新時間: {new Date(data.timestamp).toLocaleString('zh-TW')}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
