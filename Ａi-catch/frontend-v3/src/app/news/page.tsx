'use client';

import React, { useState, useEffect, useCallback } from 'react';

// 類型定義
interface NewsItem {
    id: string;
    title: string;
    source: string;
    sourceType: 'iek' | 'ttv' | 'cmoney' | 'udn' | 'technews' | 'pocket' | 'perplexity' | 'manual' | 'external';
    url?: string;
    date: string;
    industry?: string;
    stocks: string[];
    sentiment: 'positive' | 'negative' | 'neutral';
    sentimentScore?: number;
    content?: string;
}

interface StockRecommendation {
    symbol: string;
    name: string;
    mentionCount: number;
    positiveCount: number;
    negativeCount: number;
    sentimentRatio: number;
    score: number;
    action: string;
    color: string;
    relatedNews: string[];
}

interface NewsSummary {
    totalNews: number;
    iekCount: number;
    ttvCount: number;
    cmoneyCount: number;
    udnCount: number;
    technewsCount: number;
    pocketCount: number;
    perplexityCount: number;
    manualCount: number;
    stocksMentioned: number;
}

interface IndustryNews {
    [key: string]: {
        count: number;
        news: NewsItem[];
    };
}

// 情緒顏色映射
const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
        case 'positive': return '#52c41a';
        case 'negative': return '#f5222d';
        default: return '#8c8c8c';
    }
};

const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
        case 'positive': return '📈';
        case 'negative': return '📉';
        default: return '➖';
    }
};

// API 基礎 URL
const API_BASE = 'http://127.0.0.1:8000';

export default function NewsAnalysisPage() {
    const [activeTab, setActiveTab] = useState<'overview' | 'iek' | 'ttv' | 'cmoney' | 'udn' | 'technews' | 'pocket' | 'perplexity' | 'industries' | 'watchlist'>('overview');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // 數據狀態
    const [summary, setSummary] = useState<NewsSummary | null>(null);
    const [allNews, setAllNews] = useState<NewsItem[]>([]);
    const [iekNews, setIekNews] = useState<NewsItem[]>([]);
    const [ttvNews, setTtvNews] = useState<NewsItem[]>([]);
    const [cmoneyNews, setCmoneyNews] = useState<NewsItem[]>([]);
    const [udnNews, setUdnNews] = useState<NewsItem[]>([]);
    const [technewsNews, setTechnewsNews] = useState<NewsItem[]>([]);
    const [pocketNews, setPocketNews] = useState<NewsItem[]>([]);
    const [perplexityNews, setPerplexityNews] = useState<NewsItem[]>([]);
    const [recommendations, setRecommendations] = useState<StockRecommendation[]>([]);
    const [industries, setIndustries] = useState<IndustryNews>({});

    // 新增：增強分析數據
    const [sentimentAnalysis, setSentimentAnalysis] = useState<{
        positive: { count: number; ratio: number };
        neutral: { count: number; ratio: number };
        negative: { count: number; ratio: number };
        overall: string;
        confidence: number;
    } | null>(null);
    const [hotKeywords, setHotKeywords] = useState<{ name: string; count: number }[]>([]);
    const [smartSummary, setSmartSummary] = useState<{
        mood: string;
        moodEmoji: string;
        moodColor: string;
        hotTopics: string[];
        summaryText: string;
        actionAdvice: string;
    } | null>(null);

    // 新增：可行動洞察
    const [actionableInsights, setActionableInsights] = useState<{
        corePoints: Array<{
            type: string;
            icon: string;
            title: string;
            summary: string;
            action: string;
            priority: number;
        }>;
        opportunities: Array<{
            industry: string;
            signal: string;
            newsCount: number;
            description: string;
        }>;
        risks: Array<{
            industry: string;
            signal: string;
            negativeRatio: number;
            description: string;
        }>;
        industryActions: Array<{
            industry: string;
            newsCount: number;
            action: string;
            color: string;
        }>;
        industryDetails: Array<{
            industry: string;
            newsCount: number;
            description: string;
            stocks: Array<{
                code: string;
                name: string;
                role: string;
                tier: number;
                sentiment: string;
            }>;
            relatedConcepts: string[];
        }>;
        trendingThemes: Array<{
            theme: string;
            newsCount: number;
            sentiment: string;
            sentimentLabel: string;
            relatedStocks: string[];
            sampleNews: Array<{
                title: string;
                source: string;
                sentiment: string;
            }>;
            heatLevel: string;
        }>;
        updateTime: string;
    } | null>(null);

    // 展開的產業（用於顯示詳細股票）
    const [expandedIndustry, setExpandedIndustry] = useState<string | null>(null);

    // 股票詳情模態框
    const [selectedStock, setSelectedStock] = useState<string | null>(null);
    const [stockDetail, setStockDetail] = useState<{
        stockCode: string;
        stockName: string;
        totalNews: number;
        sentimentAnalysis: {
            positive: { count: number; ratio: number };
            neutral: { count: number; ratio: number };
            negative: { count: number; ratio: number };
            overall: string;
            score: number;
        };
        industries: Array<{
            industry: string;
            role: string;
            tier: number;
            relatedConcepts: string[];
        }>;
        peerStocks: Array<{
            code: string;
            name: string;
            role: string;
            tier: number;
            mentionCount: number;
        }>;
        relatedNews: Array<{
            title: string;
            source: string;
            sourceType: string;
            date: string;
            sentiment: string;
            industry: string;
            url: string;
        }>;
    } | null>(null);
    const [loadingStockDetail, setLoadingStockDetail] = useState(false);

    // 漲停股分析
    const [limitUpData, setLimitUpData] = useState<{
        success: boolean;
        date: string;
        limitUp: Array<{
            code: string;
            name: string;
            close: number;
            changePct: number;
            market: string;
        }>;
        limitDown: Array<{
            code: string;
            name: string;
            close: number;
            changePct: number;
            market: string;
        }>;
        summary: {
            limitUpCount: number;
            limitDownCount: number;
        };
        industryAnalysis: Record<string, {
            count: number;
            stocks: Array<{ code: string; role: string }>;
        }>;
        chainReaction: Array<{
            industry: string;
            limitUpCount: number;
            description: string;
        }>;
        opportunities: Array<{
            code: string;
            name: string;
            industry: string;
            role: string;
            reason: string;
        }>;
        relatedNews: Array<{
            title: string;
            url: string;
            source: string;
            timestamp: string;
            relatedStocks?: Array<{ code: string; name: string; }>;
        }>;
    } | null>(null);
    const [loadingLimitUp, setLoadingLimitUp] = useState(false);

    // 新增新聞表單
    const [showAddForm, setShowAddForm] = useState(false);
    const [newNewsTitle, setNewNewsTitle] = useState('');
    const [newNewsContent, setNewNewsContent] = useState('');
    const [newNewsStocks, setNewNewsStocks] = useState('');
    const [newNewsSentiment, setNewNewsSentiment] = useState<'positive' | 'negative' | 'neutral'>('neutral');
    const [addingNews, setAddingNews] = useState(false);

    // 載入數據
    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            // 取得完整分析
            const analysisRes = await fetch(`${API_BASE}/api/news/analysis`);
            if (analysisRes.ok) {
                const data = await analysisRes.json();
                if (data.success) {
                    setSummary(data.summary);
                    setAllNews(data.news?.all || []);
                    setIekNews(data.news?.iek || []);
                    setTtvNews(data.news?.ttv || []);
                    setCmoneyNews(data.news?.cmoney || []);
                    setUdnNews(data.news?.udn || []);
                    setTechnewsNews(data.news?.technews || []);
                    setPocketNews(data.news?.pocket || []);
                    setPerplexityNews(data.news?.perplexity || []);
                    setRecommendations(data.recommendations || []);

                    // 新增：載入增強分析數據
                    setSentimentAnalysis(data.sentimentAnalysis || null);
                    setHotKeywords(data.hotKeywords || []);
                    setSmartSummary(data.smartSummary || null);
                    setActionableInsights(data.actionableInsights || null);
                }
            }

            // 取得產業新聞
            const industryRes = await fetch(`${API_BASE}/api/news/industries`);
            if (industryRes.ok) {
                const data = await industryRes.json();
                if (data.success) {
                    setIndustries(data.industries || {});
                }
            }
        } catch (err) {
            setError('載入數據失敗，請確認後端服務是否運行');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
        // 每 5 分鐘刷新一次
        const interval = setInterval(loadData, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, [loadData]);

    // 載入股票詳情
    const loadStockDetail = async (stockCode: string) => {
        setSelectedStock(stockCode);
        setLoadingStockDetail(true);
        try {
            const res = await fetch(`${API_BASE}/api/news/stock/${stockCode}`);
            if (res.ok) {
                const data = await res.json();
                if (data.success) {
                    setStockDetail(data);
                }
            }
        } catch (err) {
            console.error('載入股票詳情失敗', err);
        } finally {
            setLoadingStockDetail(false);
        }
    };

    // 關閉股票詳情
    const closeStockDetail = () => {
        setSelectedStock(null);
        setStockDetail(null);
    };

    // 載入漲停股數據
    const loadLimitUpData = async () => {
        setLoadingLimitUp(true);
        try {
            const res = await fetch(`${API_BASE}/api/momentum/daily-report`);
            if (res.ok) {
                const data = await res.json();
                if (data.success) {
                    setLimitUpData(data);
                }
            }
        } catch (err) {
            console.error('載入漲停股失敗', err);
        } finally {
            setLoadingLimitUp(false);
        }
    };

    // 連續漲停股狀態
    const [consecutiveStocks, setConsecutiveStocks] = useState<Array<{
        code: string;
        name: string;
        market: string;
        dates: string[];
        consecutiveDays: number;
        totalDays: number;
        latestPrice: number;
        latestChangePct: number;
    }>>([]);

    // 產業趨勢狀態
    const [industryTrends, setIndustryTrends] = useState<Array<{
        industry: string;
        totalLimitUp: number;
        daysActive: number;
        stockCount: number;
        trendScore: number;
    }>>([]);

    // 載入連續漲停和產業趨勢
    const loadAdvancedMomentumData = async () => {
        try {
            // 連續漲停
            const consecutiveRes = await fetch(`${API_BASE}/api/momentum/consecutive?days=5`);
            if (consecutiveRes.ok) {
                const data = await consecutiveRes.json();
                if (data.success) {
                    setConsecutiveStocks(data.stocks || []);
                }
            }

            // 產業趨勢
            const trendsRes = await fetch(`${API_BASE}/api/momentum/industry-trends`);
            if (trendsRes.ok) {
                const data = await trendsRes.json();
                if (data.success) {
                    setIndustryTrends(data.trends || []);
                }
            }
        } catch (err) {
            console.error('載入進階動能數據失敗', err);
        }
    };

    // 頁面載入時也載入漲停股
    useEffect(() => {
        loadLimitUpData();
        loadAdvancedMomentumData();
    }, []);

    // 新增 Perplexity 新聞
    const handleAddPerplexityNews = async () => {
        if (!newNewsTitle.trim()) return;

        setAddingNews(true);
        try {
            const stocks = newNewsStocks.split(',').map(s => s.trim()).filter(s => s);

            const res = await fetch(`${API_BASE}/api/news/perplexity`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: newNewsTitle,
                    content: newNewsContent,
                    stocks,
                    sentiment: newNewsSentiment,
                }),
            });

            if (res.ok) {
                setNewNewsTitle('');
                setNewNewsContent('');
                setNewNewsStocks('');
                setNewNewsSentiment('neutral');
                setShowAddForm(false);
                await loadData();
            }
        } catch (err) {
            console.error('新增新聞失敗:', err);
        } finally {
            setAddingNews(false);
        }
    };

    // 渲染新聞卡片
    const renderNewsCard = (news: NewsItem) => (
        <div
            key={news.id}
            style={{
                background: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '12px',
                padding: '16px',
                marginBottom: '12px',
                transition: 'all 0.2s',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div style={{ flex: 1 }}>
                    {news.url ? (
                        <a
                            href={news.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: '#1f2937', textDecoration: 'none', fontSize: '15px', fontWeight: 500 }}
                        >
                            {news.title}
                        </a>
                    ) : (
                        <span style={{ color: '#1f2937', fontSize: '15px', fontWeight: 500 }}>{news.title}</span>
                    )}
                </div>
                <span style={{
                    color: getSentimentColor(news.sentiment),
                    fontSize: '20px',
                    marginLeft: '8px'
                }}>
                    {getSentimentIcon(news.sentiment)}
                </span>
            </div>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', fontSize: '13px', color: '#6b7280' }}>
                {/* 來源標籤 */}
                <span style={{
                    background: news.sourceType === 'iek' ? 'rgba(24, 144, 255, 0.2)' :
                        news.sourceType === 'ttv' ? 'rgba(255, 87, 51, 0.2)' :
                            news.sourceType === 'cmoney' ? 'rgba(255, 193, 7, 0.2)' :
                                news.sourceType === 'udn' ? 'rgba(0, 150, 136, 0.2)' :
                                    news.sourceType === 'technews' ? 'rgba(233, 30, 99, 0.2)' :
                                        news.sourceType === 'pocket' ? 'rgba(255, 107, 0, 0.2)' :
                                            news.sourceType === 'perplexity' ? 'rgba(114, 46, 209, 0.2)' : 'rgba(255,255,255,0.1)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    color: news.sourceType === 'iek' ? '#1890ff' :
                        news.sourceType === 'ttv' ? '#ff5733' :
                            news.sourceType === 'cmoney' ? '#ffc107' :
                                news.sourceType === 'udn' ? '#009688' :
                                    news.sourceType === 'technews' ? '#e91e63' :
                                        news.sourceType === 'pocket' ? '#ff6b00' :
                                            news.sourceType === 'perplexity' ? '#722ed1' : '#fff',
                }}>
                    {news.source}
                </span>

                {/* 產業標籤 */}
                {news.industry && (
                    <span style={{ background: 'rgba(82, 196, 26, 0.2)', padding: '2px 8px', borderRadius: '4px', color: '#52c41a' }}>
                        {news.industry}
                    </span>
                )}

                {/* 日期 - 明確標示 */}
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    📅 {news.date}
                </span>
            </div>

            {news.stocks.length > 0 && (
                <div style={{ marginTop: '10px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {news.stocks.map(stock => (
                        <span
                            key={stock}
                            style={{
                                background: 'rgba(250, 173, 20, 0.2)',
                                color: '#faad14',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                fontSize: '12px',
                            }}
                        >
                            {stock}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );

    // 渲染股票推薦卡片 - 改進版：顯示風險警示
    const renderStockCard = (stock: StockRecommendation & { riskLevel?: string; riskWarning?: string; neutralCount?: number }) => (
        <div
            key={stock.symbol}
            style={{
                background: stock.riskLevel === 'high' ? '#fef2f2' :
                    stock.riskLevel === 'medium' ? '#fffbeb' : '#ffffff',
                border: `1px solid ${stock.riskLevel === 'high' ? '#fecaca' :
                    stock.riskLevel === 'medium' ? '#fde68a' :
                        stock.color === 'red' ? '#fecaca' :
                            stock.color === 'orange' ? '#fde68a' : '#e5e7eb'}`,
                borderRadius: '12px',
                padding: '16px',
                marginBottom: '12px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            }}
        >
            {/* 風險警示橫幅 */}
            {stock.riskWarning && (
                <div style={{
                    background: stock.riskLevel === 'high' ? '#fee2e2' : '#fef3c7',
                    color: stock.riskLevel === 'high' ? '#dc2626' : '#d97706',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '12px',
                    marginBottom: 12,
                    fontWeight: 500,
                }}>
                    {stock.riskWarning}
                </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                    <span style={{ fontSize: '18px', fontWeight: 600, color: '#1f2937', marginRight: '12px' }}>
                        {stock.symbol}
                    </span>
                    <span style={{ color: '#6b7280' }}>{stock.name}</span>
                </div>
                <span style={{
                    background: stock.action.includes('謹慎') ? 'rgba(245, 34, 45, 0.2)' :
                        stock.color === 'red' ? 'rgba(245, 34, 45, 0.2)' :
                            stock.color === 'orange' ? 'rgba(250, 173, 20, 0.2)' :
                                stock.color === 'yellow' ? 'rgba(255, 214, 0, 0.2)' : 'rgba(255,255,255,0.1)',
                    color: stock.action.includes('謹慎') ? '#ff4d4f' :
                        stock.color === 'red' ? '#ff4d4f' :
                            stock.color === 'orange' ? '#faad14' :
                                stock.color === 'yellow' ? '#ffd600' : '#8c8c8c',
                    padding: '4px 12px',
                    borderRadius: '16px',
                    fontSize: '13px',
                    fontWeight: 500,
                }}>
                    {stock.action}
                </span>
            </div>

            <div style={{ display: 'flex', gap: '16px', marginBottom: 12, flexWrap: 'wrap' }}>
                <div>
                    <span style={{ color: '#6b7280', fontSize: '12px' }}>新聞提及</span>
                    <div style={{ fontSize: '18px', fontWeight: 600, color: '#1f2937' }}>{stock.mentionCount}</div>
                </div>
                <div>
                    <span style={{ color: '#6b7280', fontSize: '12px' }}>正面 📈</span>
                    <div style={{ fontSize: '18px', fontWeight: 600, color: '#16a34a' }}>{stock.positiveCount}</div>
                </div>
                <div>
                    <span style={{ color: '#6b7280', fontSize: '12px' }}>負面 📉</span>
                    <div style={{ fontSize: '18px', fontWeight: 600, color: '#dc2626' }}>{stock.negativeCount}</div>
                </div>
                <div>
                    <span style={{ color: '#6b7280', fontSize: '12px' }}>情緒比</span>
                    <div style={{
                        fontSize: '18px',
                        fontWeight: 600,
                        color: stock.sentimentRatio > 0.3 ? '#16a34a' :
                            stock.sentimentRatio < 0 ? '#dc2626' : '#d97706'
                    }}>
                        {stock.sentimentRatio > 0 ? '+' : ''}{stock.sentimentRatio}
                    </div>
                </div>
                <div>
                    <span style={{ color: '#6b7280', fontSize: '12px' }}>分數</span>
                    <div style={{
                        fontSize: '18px',
                        fontWeight: 600,
                        color: stock.score >= 50 ? '#16a34a' : stock.score >= 30 ? '#2563eb' : '#6b7280'
                    }}>
                        {stock.score}
                    </div>
                </div>
            </div>

            {stock.relatedNews.length > 0 && (
                <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: 10 }}>
                    <div style={{ color: '#6b7280', fontSize: '12px', marginBottom: 6 }}>相關新聞：</div>
                    {stock.relatedNews.slice(0, 2).map((news, idx) => (
                        <div key={idx} style={{ color: '#4b5563', fontSize: '13px', marginBottom: 4 }}>
                            • {news}...
                        </div>
                    ))}
                </div>
            )}
        </div>
    );

    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(135deg, #f0f5ff 0%, #ffffff 50%, #f5fff0 100%)',
            color: '#1f2937',
            padding: '24px',
        }}>
            {/* 頁面標題 */}
            <div style={{ marginBottom: 24 }}>
                <h1 style={{
                    fontSize: '28px',
                    fontWeight: 700,
                    background: 'linear-gradient(90deg, #2563eb, #059669)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    marginBottom: 8
                }}>
                    📰 產業新聞分析中心
                </h1>
                <p style={{ color: '#6b7280' }}>
                    整合 IEK 產業情報網、台視財經、CMoney、經濟日報、Perplexity AI 等多元來源，智慧分析哪些股票值得關注
                </p>
            </div>

            {/* 統計摘要 */}
            {summary && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                    gap: '12px',
                    marginBottom: 24
                }}>
                    <div style={{ background: 'rgba(24, 144, 255, 0.1)', border: '1px solid rgba(24, 144, 255, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#1890ff' }}>{summary.totalNews}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>總新聞</div>
                    </div>
                    <div style={{ background: 'rgba(82, 196, 26, 0.1)', border: '1px solid rgba(82, 196, 26, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#52c41a' }}>{summary.iekCount}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>IEK</div>
                    </div>
                    <div style={{ background: 'rgba(255, 87, 51, 0.1)', border: '1px solid rgba(255, 87, 51, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#ff5733' }}>{summary.ttvCount}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>台視財經</div>
                    </div>
                    <div style={{ background: 'rgba(255, 193, 7, 0.1)', border: '1px solid rgba(255, 193, 7, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#ffc107' }}>{summary.cmoneyCount || 0}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>CMoney</div>
                    </div>
                    <div style={{ background: 'rgba(0, 150, 136, 0.1)', border: '1px solid rgba(0, 150, 136, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#009688' }}>{summary.udnCount || 0}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>經濟日報</div>
                    </div>
                    <div style={{ background: 'rgba(233, 30, 99, 0.1)', border: '1px solid rgba(233, 30, 99, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#e91e63' }}>{summary.technewsCount || 0}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>科技新報</div>
                    </div>
                    <div style={{ background: 'rgba(255, 107, 0, 0.1)', border: '1px solid rgba(255, 107, 0, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#ff6b00' }}>{summary.pocketCount || 0}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>口袋研報</div>
                    </div>
                    <div style={{ background: 'rgba(114, 46, 209, 0.1)', border: '1px solid rgba(114, 46, 209, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#722ed1' }}>{summary.perplexityCount}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>Perplexity</div>
                    </div>
                    <div style={{ background: 'rgba(250, 173, 20, 0.1)', border: '1px solid rgba(250, 173, 20, 0.3)', borderRadius: '12px', padding: '14px', textAlign: 'center' }}>
                        <div style={{ fontSize: '24px', fontWeight: 700, color: '#faad14' }}>{summary.stocksMentioned}</div>
                        <div style={{ color: '#6b7280', fontSize: '12px' }}>提及股票</div>
                    </div>
                </div>
            )}

            {/* Tab 切換 */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
                {[
                    { key: 'overview', label: '📊 總覽', icon: '' },
                    { key: 'watchlist', label: '🎯 關注股票', icon: '' },
                    { key: 'iek', label: '🏢 IEK', icon: '' },
                    { key: 'ttv', label: '📺 台視財經', icon: '' },
                    { key: 'cmoney', label: '💰 CMoney', icon: '' },
                    { key: 'udn', label: '📊 經濟日報', icon: '' },
                    { key: 'technews', label: '🔬 科技新報', icon: '' },
                    { key: 'pocket', label: '📋 口袋研報', icon: '' },
                    { key: 'perplexity', label: '🤖 Perplexity', icon: '' },
                    { key: 'industries', label: '🏭 產業分類', icon: '' },
                ].map(tab => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key as typeof activeTab)}
                        style={{
                            padding: '10px 20px',
                            borderRadius: '8px',
                            border: activeTab === tab.key ? 'none' : '1px solid #e5e7eb',
                            cursor: 'pointer',
                            fontSize: '14px',
                            fontWeight: 500,
                            background: activeTab === tab.key ? 'linear-gradient(90deg, #2563eb, #059669)' : '#ffffff',
                            color: activeTab === tab.key ? '#fff' : '#6b7280',
                            transition: 'all 0.2s',
                            boxShadow: activeTab === tab.key ? '0 2px 8px rgba(37, 99, 235, 0.3)' : '0 1px 2px rgba(0,0,0,0.05)',
                        }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* 內容區 */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
                    <div style={{ fontSize: 40, marginBottom: 16 }}>⏳</div>
                    載入中...
                </div>
            ) : error ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#f5222d' }}>
                    <div style={{ fontSize: 40, marginBottom: 16 }}>❌</div>
                    {error}
                    <button onClick={loadData} style={{ marginTop: 16, padding: '8px 16px', background: '#1890ff', border: 'none', borderRadius: 8, color: '#1f2937', cursor: 'pointer' }}>
                        重試
                    </button>
                </div>
            ) : (
                <>
                    {/* 總覽 - AI 投資晨報 */}
                    {activeTab === 'overview' && (
                        <div>
                            {/* ========== 頁面標題 - 決策導向 ========== */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginBottom: '20px'
                            }}>
                                <div>
                                    <h2 style={{ margin: 0, fontSize: '22px', color: '#1f2937', fontWeight: 700 }}>
                                        {smartSummary?.moodEmoji || '📊'} AI 投資晨報
                                    </h2>
                                    <p style={{ margin: '4px 0 0 0', color: '#6b7280', fontSize: '13px' }}>
                                        更新時間：{actionableInsights?.updateTime || '--:--'} | 分析 {summary?.totalNews || 0} 則新聞
                                    </p>
                                </div>
                                <div style={{
                                    padding: '8px 16px',
                                    background: smartSummary?.moodColor === 'green' ? '#dcfce7' :
                                        smartSummary?.moodColor === 'red' ? '#fef2f2' : '#f3f4f6',
                                    borderRadius: '20px',
                                    color: smartSummary?.moodColor === 'green' ? '#166534' :
                                        smartSummary?.moodColor === 'red' ? '#991b1b' : '#4b5563',
                                    fontSize: '14px',
                                    fontWeight: 600
                                }}>
                                    市場情緒：{smartSummary?.mood || '分析中'}
                                </div>
                            </div>

                            {/* ========== 核心觀點（給忙碌投資人的3點建議）========== */}
                            {actionableInsights?.corePoints && actionableInsights.corePoints.length > 0 && (
                                <div style={{
                                    background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
                                    border: '1px solid #93c5fd',
                                    borderRadius: '16px',
                                    padding: '24px',
                                    marginBottom: '24px',
                                }}>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px',
                                        marginBottom: '20px',
                                        paddingBottom: '12px',
                                        borderBottom: '1px solid #93c5fd'
                                    }}>
                                        <span style={{ fontSize: '20px' }}>💡</span>
                                        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#1e40af' }}>
                                            給忙碌投資人的 {actionableInsights.corePoints.length} 點建議
                                        </h3>
                                    </div>

                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                        {actionableInsights.corePoints.map((point, idx) => (
                                            <div key={idx} style={{
                                                display: 'flex',
                                                gap: '16px',
                                                padding: '16px',
                                                background: '#ffffff',
                                                borderRadius: '12px',
                                                border: '1px solid #e5e7eb',
                                                borderLeft: `4px solid ${point.type === 'opportunity' ? '#22c55e' :
                                                    point.type === 'warning' ? '#f59e0b' :
                                                        point.type === 'action' ? '#3b82f6' : '#9ca3af'
                                                    }`
                                            }}>
                                                <div style={{
                                                    fontSize: '28px',
                                                    width: '40px',
                                                    textAlign: 'center',
                                                    flexShrink: 0
                                                }}>
                                                    {point.icon}
                                                </div>
                                                <div style={{ flex: 1 }}>
                                                    <div style={{
                                                        fontSize: '15px',
                                                        fontWeight: 600,
                                                        marginBottom: '6px',
                                                        color: '#1f2937'
                                                    }}>
                                                        {point.title}
                                                    </div>
                                                    <div style={{
                                                        fontSize: '13px',
                                                        color: '#6b7280',
                                                        marginBottom: '8px'
                                                    }}>
                                                        {point.summary}
                                                    </div>
                                                    <div style={{
                                                        fontSize: '12px',
                                                        padding: '6px 12px',
                                                        background: '#f0fdf4',
                                                        border: '1px solid #bbf7d0',
                                                        borderRadius: '6px',
                                                        display: 'inline-block',
                                                        color: '#166534'
                                                    }}>
                                                        → {point.action}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}


                            {/* ========== 機會與風險提示 ========== */}
                            {((actionableInsights?.opportunities?.length ?? 0) > 0 || (actionableInsights?.risks?.length ?? 0) > 0) && (
                                <div style={{
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                                    gap: '16px',
                                    marginBottom: '24px'
                                }}>
                                    {/* 機會標記 */}
                                    {(actionableInsights?.opportunities?.length ?? 0) > 0 && (
                                        <div style={{
                                            background: '#f0fdf4',
                                            border: '1px solid #bbf7d0',
                                            borderRadius: '12px',
                                            padding: '16px',
                                        }}>
                                            <div style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px',
                                                marginBottom: '12px',
                                                color: '#166534',
                                                fontWeight: 600
                                            }}>
                                                <span>🟢</span> 機會標記
                                            </div>
                                            {actionableInsights?.opportunities?.slice(0, 3).map((opp, idx) => (
                                                <div key={idx} style={{
                                                    fontSize: '13px',
                                                    color: '#166534',
                                                    marginBottom: '8px',
                                                    paddingLeft: '8px',
                                                    borderLeft: '2px solid #22c55e'
                                                }}>
                                                    <strong>{opp.industry}</strong>：{opp.description}
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* 風險警示 */}
                                    {(actionableInsights?.risks?.length ?? 0) > 0 && (
                                        <div style={{
                                            background: '#fef2f2',
                                            border: '1px solid #fecaca',
                                            borderRadius: '12px',
                                            padding: '16px',
                                        }}>
                                            <div style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px',
                                                marginBottom: '12px',
                                                color: '#991b1b',
                                                fontWeight: 600
                                            }}>
                                                <span>🔴</span> 風險警示
                                            </div>
                                            {actionableInsights?.risks?.slice(0, 3).map((risk, idx) => (
                                                <div key={idx} style={{
                                                    fontSize: '13px',
                                                    color: '#991b1b',
                                                    marginBottom: '8px',
                                                    paddingLeft: '8px',
                                                    borderLeft: '2px solid #ef4444'
                                                }}>
                                                    <strong>{risk.industry}</strong>：{risk.description}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ========== 第一層：核心洞察 ========== */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '20px', marginBottom: '24px' }}>

                                {/* 市場情緒儀表板 */}
                                <div style={{
                                    background: '#ffffff',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '16px',
                                    padding: '24px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                }}>
                                    <h3 style={{ margin: '0 0 16px 0', color: '#1f2937', fontSize: '16px', fontWeight: 600 }}>
                                        📊 市場情緒儀表板
                                    </h3>

                                    {/* 情緒指標 */}
                                    <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                                        <div style={{
                                            fontSize: '48px',
                                            marginBottom: '8px'
                                        }}>
                                            {smartSummary?.moodEmoji || '📊'}
                                        </div>
                                        <div style={{
                                            fontSize: '24px',
                                            fontWeight: 700,
                                            color: smartSummary?.moodColor === 'green' ? '#16a34a' :
                                                smartSummary?.moodColor === 'red' ? '#dc2626' : '#6b7280'
                                        }}>
                                            {smartSummary?.mood || '分析中...'}
                                        </div>
                                        <div style={{ color: '#6b7280', fontSize: '13px', marginTop: '4px' }}>
                                            根據 {summary?.totalNews || 0} 則新聞分析
                                        </div>
                                    </div>

                                    {/* 情緒比例條 */}
                                    {sentimentAnalysis && (
                                        <div style={{ marginBottom: '16px' }}>
                                            <div style={{
                                                display: 'flex',
                                                height: '12px',
                                                borderRadius: '6px',
                                                overflow: 'hidden',
                                                marginBottom: '8px'
                                            }}>
                                                <div style={{
                                                    width: `${sentimentAnalysis.positive.ratio}%`,
                                                    background: 'linear-gradient(90deg, #22c55e, #16a34a)',
                                                    transition: 'width 0.5s'
                                                }} />
                                                <div style={{
                                                    width: `${sentimentAnalysis.neutral.ratio}%`,
                                                    background: '#9ca3af',
                                                    transition: 'width 0.5s'
                                                }} />
                                                <div style={{
                                                    width: `${sentimentAnalysis.negative.ratio}%`,
                                                    background: 'linear-gradient(90deg, #ef4444, #dc2626)',
                                                    transition: 'width 0.5s'
                                                }} />
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                                <span style={{ color: '#16a34a' }}>
                                                    📈 正面 {sentimentAnalysis.positive.ratio}%
                                                </span>
                                                <span style={{ color: '#6b7280' }}>
                                                    ➖ 中性 {sentimentAnalysis.neutral.ratio}%
                                                </span>
                                                <span style={{ color: '#dc2626' }}>
                                                    📉 負面 {sentimentAnalysis.negative.ratio}%
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {/* 行動建議 */}
                                    {smartSummary?.actionAdvice && (
                                        <div style={{
                                            background: '#f0fdf4',
                                            border: '1px solid #bbf7d0',
                                            borderRadius: '8px',
                                            padding: '12px',
                                            fontSize: '13px',
                                            color: '#166534'
                                        }}>
                                            💡 {smartSummary.actionAdvice}
                                        </div>
                                    )}
                                </div>

                                {/* 熱門產業關鍵字 */}
                                <div style={{
                                    background: '#ffffff',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '16px',
                                    padding: '24px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                }}>
                                    <h3 style={{ margin: '0 0 16px 0', color: '#1f2937', fontSize: '16px', fontWeight: 600 }}>
                                        🔥 今日熱門產業 <span style={{ fontSize: '12px', color: '#9ca3af', fontWeight: 400 }}>(點擊查看相關股票)</span>
                                    </h3>

                                    {hotKeywords.length > 0 ? (
                                        <div>
                                            {/* 產業標籤列表 */}
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: expandedIndustry ? '16px' : 0 }}>
                                                {hotKeywords.map((kw, idx) => (
                                                    <button
                                                        key={kw.name}
                                                        onClick={() => setExpandedIndustry(expandedIndustry === kw.name ? null : kw.name)}
                                                        style={{
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            gap: '6px',
                                                            padding: '8px 16px',
                                                            borderRadius: '20px',
                                                            fontSize: idx < 3 ? '15px' : '13px',
                                                            fontWeight: idx < 3 ? 600 : 400,
                                                            background: expandedIndustry === kw.name ? '#1e40af' :
                                                                idx === 0 ? 'linear-gradient(135deg, #fef3c7, #fde68a)' :
                                                                    idx === 1 ? 'linear-gradient(135deg, #e0e7ff, #c7d2fe)' :
                                                                        idx === 2 ? 'linear-gradient(135deg, #ffe4e6, #fecdd3)' :
                                                                            '#f3f4f6',
                                                            color: expandedIndustry === kw.name ? '#ffffff' :
                                                                idx === 0 ? '#92400e' :
                                                                    idx === 1 ? '#3730a3' :
                                                                        idx === 2 ? '#be123c' :
                                                                            '#4b5563',
                                                            border: 'none',
                                                            cursor: 'pointer',
                                                            transition: 'all 0.2s ease',
                                                        }}
                                                    >
                                                        {idx === 0 && '🥇'}
                                                        {idx === 1 && '🥈'}
                                                        {idx === 2 && '🥉'}
                                                        {kw.name}
                                                        <span style={{
                                                            fontSize: '11px',
                                                            background: expandedIndustry === kw.name ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)',
                                                            padding: '2px 6px',
                                                            borderRadius: '10px'
                                                        }}>
                                                            {kw.count}則
                                                        </span>
                                                    </button>
                                                ))}
                                            </div>

                                            {/* 展開的產業詳情 */}
                                            {expandedIndustry && actionableInsights?.industryDetails && (
                                                <div style={{
                                                    background: '#f8fafc',
                                                    border: '1px solid #e2e8f0',
                                                    borderRadius: '12px',
                                                    padding: '16px',
                                                    marginTop: '12px',
                                                }}>
                                                    {(() => {
                                                        const detail = actionableInsights.industryDetails.find(d => d.industry === expandedIndustry);
                                                        if (!detail) {
                                                            return <div style={{ color: '#6b7280', fontSize: '13px' }}>暫無此產業詳細資料</div>;
                                                        }
                                                        return (
                                                            <div>
                                                                <div style={{
                                                                    display: 'flex',
                                                                    justifyContent: 'space-between',
                                                                    alignItems: 'center',
                                                                    marginBottom: '12px'
                                                                }}>
                                                                    <div style={{ fontWeight: 600, color: '#1e40af', fontSize: '15px' }}>
                                                                        【{detail.industry}】相關股票
                                                                    </div>
                                                                    {detail.relatedConcepts && detail.relatedConcepts.length > 0 && (
                                                                        <div style={{ display: 'flex', gap: '6px' }}>
                                                                            {detail.relatedConcepts.map((concept, i) => (
                                                                                <span key={i} style={{
                                                                                    fontSize: '11px',
                                                                                    padding: '2px 8px',
                                                                                    background: '#e0e7ff',
                                                                                    color: '#3730a3',
                                                                                    borderRadius: '12px'
                                                                                }}>
                                                                                    {concept}
                                                                                </span>
                                                                            ))}
                                                                        </div>
                                                                    )}
                                                                </div>

                                                                {/* 股票列表 */}
                                                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px' }}>
                                                                    {detail.stocks.map(stock => (
                                                                        <button
                                                                            key={stock.code}
                                                                            onClick={() => loadStockDetail(stock.code)}
                                                                            style={{
                                                                                display: 'flex',
                                                                                alignItems: 'center',
                                                                                gap: '8px',
                                                                                padding: '10px 12px',
                                                                                background: '#ffffff',
                                                                                border: '1px solid #e5e7eb',
                                                                                borderRadius: '8px',
                                                                                borderLeft: `3px solid ${stock.sentiment === 'positive' ? '#22c55e' :
                                                                                    stock.sentiment === 'negative' ? '#ef4444' : '#9ca3af'
                                                                                    }`,
                                                                                cursor: 'pointer',
                                                                                textAlign: 'left',
                                                                                transition: 'all 0.2s ease',
                                                                            }}
                                                                            onMouseOver={(e) => e.currentTarget.style.background = '#f8fafc'}
                                                                            onMouseOut={(e) => e.currentTarget.style.background = '#ffffff'}
                                                                        >
                                                                            <div>
                                                                                <div style={{ fontWeight: 600, color: '#1f2937', fontSize: '14px' }}>
                                                                                    {stock.code} {stock.name}
                                                                                </div>
                                                                                <div style={{ fontSize: '11px', color: '#6b7280' }}>
                                                                                    {stock.role}
                                                                                    {stock.tier === 1 && <span style={{ marginLeft: '6px', color: '#f59e0b' }}>⭐核心</span>}
                                                                                </div>
                                                                            </div>
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        );
                                                    })()}
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div style={{ color: '#9ca3af', textAlign: 'center', padding: '20px' }}>
                                            正在分析產業趨勢...
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* 智能摘要 */}
                            {smartSummary?.summaryText && (
                                <div style={{
                                    background: 'linear-gradient(135deg, #eff6ff, #dbeafe)',
                                    border: '1px solid #93c5fd',
                                    borderRadius: '12px',
                                    padding: '20px',
                                    marginBottom: '24px',
                                }}>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'flex-start',
                                        gap: '12px'
                                    }}>
                                        <span style={{ fontSize: '24px' }}>🤖</span>
                                        <div>
                                            <div style={{
                                                fontSize: '14px',
                                                fontWeight: 600,
                                                color: '#1e40af',
                                                marginBottom: '8px'
                                            }}>
                                                AI 智能摘要
                                            </div>
                                            <p style={{
                                                margin: 0,
                                                color: '#1e3a8a',
                                                fontSize: '14px',
                                                lineHeight: 1.6
                                            }}>
                                                {smartSummary.summaryText}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* ========== 今日漲停股分析 ========== */}
                            {limitUpData && limitUpData.summary?.limitUpCount > 0 && (
                                <div style={{
                                    background: '#ffffff',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '16px',
                                    padding: '24px',
                                    marginBottom: '24px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                }}>
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        marginBottom: '16px'
                                    }}>
                                        <h3 style={{
                                            margin: 0,
                                            color: '#1f2937',
                                            fontSize: '16px',
                                            fontWeight: 600,
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '8px'
                                        }}>
                                            🚀 今日漲停股
                                            <span style={{
                                                background: '#dc2626',
                                                color: '#fff',
                                                padding: '2px 10px',
                                                borderRadius: '12px',
                                                fontSize: '12px',
                                                fontWeight: 600
                                            }}>
                                                {limitUpData.summary.limitUpCount} 檔
                                            </span>
                                        </h3>
                                        <button
                                            onClick={loadLimitUpData}
                                            style={{
                                                background: '#f3f4f6',
                                                border: 'none',
                                                borderRadius: '6px',
                                                padding: '6px 12px',
                                                cursor: 'pointer',
                                                fontSize: '12px',
                                                color: '#6b7280'
                                            }}
                                        >
                                            🔄 刷新
                                        </button>
                                    </div>

                                    {/* 產業連動警示 */}
                                    {limitUpData.chainReaction && limitUpData.chainReaction.length > 0 && (
                                        <div style={{
                                            background: 'linear-gradient(135deg, #fef3c7, #fde68a)',
                                            border: '1px solid #f59e0b',
                                            borderRadius: '10px',
                                            padding: '12px 16px',
                                            marginBottom: '16px',
                                        }}>
                                            <div style={{ fontWeight: 600, color: '#92400e', fontSize: '13px', marginBottom: '6px' }}>
                                                🔥 產業連動效應
                                            </div>
                                            {limitUpData.chainReaction.map((chain, idx) => (
                                                <div key={idx} style={{ fontSize: '12px', color: '#78350f' }}>
                                                    • {chain.description}
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* 漲停股列表 - 分上市/上櫃 */}
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                                        {/* 上市 */}
                                        <div>
                                            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px', fontWeight: 500 }}>
                                                📈 上市 ({limitUpData.limitUp.filter(s => s.market === 'TWSE').length} 檔)
                                            </div>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                                {limitUpData.limitUp
                                                    .filter(s => s.market === 'TWSE')
                                                    .slice(0, 12)
                                                    .map(stock => (
                                                        <button
                                                            key={stock.code}
                                                            onClick={() => loadStockDetail(stock.code)}
                                                            style={{
                                                                padding: '6px 10px',
                                                                background: '#fef2f2',
                                                                border: '1px solid #fecaca',
                                                                borderRadius: '8px',
                                                                cursor: 'pointer',
                                                                fontSize: '12px',
                                                                color: '#dc2626',
                                                                fontWeight: 500,
                                                            }}
                                                        >
                                                            {stock.code} {stock.name}
                                                            <span style={{ marginLeft: '4px', fontSize: '10px' }}>
                                                                +{stock.changePct}%
                                                            </span>
                                                        </button>
                                                    ))}
                                            </div>
                                        </div>

                                        {/* 上櫃 */}
                                        <div>
                                            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '8px', fontWeight: 500 }}>
                                                📊 上櫃 ({limitUpData.limitUp.filter(s => s.market === 'OTC').length} 檔)
                                            </div>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                                {limitUpData.limitUp
                                                    .filter(s => s.market === 'OTC')
                                                    .slice(0, 12)
                                                    .map(stock => (
                                                        <button
                                                            key={stock.code}
                                                            onClick={() => loadStockDetail(stock.code)}
                                                            style={{
                                                                padding: '6px 10px',
                                                                background: '#fff7ed',
                                                                border: '1px solid #fed7aa',
                                                                borderRadius: '8px',
                                                                cursor: 'pointer',
                                                                fontSize: '12px',
                                                                color: '#ea580c',
                                                                fontWeight: 500,
                                                            }}
                                                        >
                                                            {stock.code} {stock.name}
                                                            <span style={{ marginLeft: '4px', fontSize: '10px' }}>
                                                                +{stock.changePct}%
                                                            </span>
                                                        </button>
                                                    ))}
                                            </div>
                                        </div>
                                    </div>

                                    {/* 漲停股相關新聞 */}
                                    {limitUpData.relatedNews && limitUpData.relatedNews.length > 0 && (
                                        <div style={{
                                            background: '#fffbeb',
                                            border: '1px solid #fcd34d',
                                            borderRadius: '10px',
                                            padding: '12px 16px',
                                            marginTop: '12px',
                                        }}>
                                            <div style={{ fontWeight: 600, color: '#b45309', fontSize: '13px', marginBottom: '10px' }}>
                                                📰 漲停股相關新聞 ({limitUpData.relatedNews.length} 則)
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                                {limitUpData.relatedNews.slice(0, 8).map((news, idx) => (
                                                    <a
                                                        key={idx}
                                                        href={news.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        style={{
                                                            display: 'block',
                                                            padding: '8px 12px',
                                                            background: 'white',
                                                            border: '1px solid #fde68a',
                                                            borderRadius: '6px',
                                                            textDecoration: 'none',
                                                            color: '#1f2937',
                                                            fontSize: '13px',
                                                            transition: 'all 0.2s',
                                                        }}
                                                        onMouseOver={(e) => e.currentTarget.style.borderColor = '#f59e0b'}
                                                        onMouseOut={(e) => e.currentTarget.style.borderColor = '#fde68a'}
                                                    >
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                            <span style={{ flex: 1 }}>{news.title}</span>
                                                            <span style={{
                                                                background: '#fef3c7',
                                                                color: '#92400e',
                                                                padding: '2px 6px',
                                                                borderRadius: '4px',
                                                                fontSize: '10px',
                                                                marginLeft: '8px',
                                                                flexShrink: 0
                                                            }}>
                                                                {news.source}
                                                            </span>
                                                        </div>
                                                    </a>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* 潛在機會股 */}
                                    {limitUpData.opportunities && limitUpData.opportunities.length > 0 && (
                                        <div style={{
                                            background: '#f0fdf4',
                                            border: '1px solid #86efac',
                                            borderRadius: '10px',
                                            padding: '12px 16px',
                                            marginTop: '12px',
                                        }}>
                                            <div style={{ fontWeight: 600, color: '#166534', fontSize: '13px', marginBottom: '8px' }}>
                                                💡 潛在機會股（同產業未漲停）
                                            </div>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                                {limitUpData.opportunities.slice(0, 8).map(stock => (
                                                    <button
                                                        key={stock.code}
                                                        onClick={() => loadStockDetail(stock.code)}
                                                        style={{
                                                            padding: '6px 10px',
                                                            background: '#dcfce7',
                                                            border: '1px solid #86efac',
                                                            borderRadius: '8px',
                                                            cursor: 'pointer',
                                                            fontSize: '12px',
                                                            color: '#166534',
                                                        }}
                                                    >
                                                        {stock.code} {stock.name}
                                                        <span style={{ marginLeft: '4px', fontSize: '10px', color: '#22c55e' }}>
                                                            {stock.industry}
                                                        </span>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ========== 連續漲停追蹤 ========== */}
                            {consecutiveStocks.length > 0 && (
                                <div style={{
                                    background: '#ffffff',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '16px',
                                    padding: '24px',
                                    marginBottom: '24px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                }}>
                                    <h3 style={{
                                        margin: '0 0 16px 0',
                                        color: '#1f2937',
                                        fontSize: '16px',
                                        fontWeight: 600,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}>
                                        🔥 連續漲停追蹤
                                        <span style={{
                                            background: '#fef3c7',
                                            color: '#b45309',
                                            padding: '4px 10px',
                                            borderRadius: '12px',
                                            fontSize: '12px',
                                            fontWeight: 600
                                        }}>
                                            近5日
                                        </span>
                                    </h3>

                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                        {consecutiveStocks.slice(0, 8).map(stock => (
                                            <div
                                                key={stock.code}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'space-between',
                                                    background: stock.consecutiveDays >= 2 ? '#fef3c7' : '#f3f4f6',
                                                    borderRadius: '10px',
                                                    padding: '12px 16px',
                                                    borderLeft: `4px solid ${stock.consecutiveDays >= 3 ? '#dc2626' : stock.consecutiveDays >= 2 ? '#f59e0b' : '#9ca3af'}`
                                                }}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                    <button
                                                        onClick={() => loadStockDetail(stock.code)}
                                                        style={{
                                                            fontWeight: 600,
                                                            color: '#1f2937',
                                                            background: 'none',
                                                            border: 'none',
                                                            cursor: 'pointer',
                                                            fontSize: '14px'
                                                        }}
                                                    >
                                                        {stock.code} {stock.name}
                                                    </button>
                                                    <span style={{
                                                        background: stock.market === 'TWSE' ? '#dbeafe' : '#fce7f3',
                                                        color: stock.market === 'TWSE' ? '#1d4ed8' : '#be185d',
                                                        padding: '2px 8px',
                                                        borderRadius: '4px',
                                                        fontSize: '11px'
                                                    }}>
                                                        {stock.market === 'TWSE' ? '上市' : '上櫃'}
                                                    </span>
                                                </div>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                                    <span style={{
                                                        background: stock.consecutiveDays >= 2 ? '#dc2626' : '#6b7280',
                                                        color: 'white',
                                                        padding: '4px 10px',
                                                        borderRadius: '6px',
                                                        fontSize: '12px',
                                                        fontWeight: 600
                                                    }}>
                                                        連續 {stock.consecutiveDays} 天
                                                    </span>
                                                    <span style={{ color: '#dc2626', fontWeight: 600, fontSize: '13px' }}>
                                                        +{stock.latestChangePct}%
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {consecutiveStocks.length === 0 && (
                                        <div style={{ textAlign: 'center', color: '#9ca3af', padding: '20px' }}>
                                            目前沒有連續漲停的股票
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ========== 產業趨勢分析 ========== */}
                            {industryTrends.length > 0 && (
                                <div style={{
                                    background: '#ffffff',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '16px',
                                    padding: '24px',
                                    marginBottom: '24px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                }}>
                                    <h3 style={{
                                        margin: '0 0 16px 0',
                                        color: '#1f2937',
                                        fontSize: '16px',
                                        fontWeight: 600,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}>
                                        📈 產業趨勢分析
                                        <span style={{ fontSize: '12px', color: '#9ca3af', fontWeight: 400 }}>
                                            近5日產業漲停股統計
                                        </span>
                                    </h3>

                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                                        {industryTrends.slice(0, 6).map((trend, idx) => (
                                            <div key={idx} style={{
                                                background: trend.trendScore >= 50 ? '#eff6ff' : '#f9fafb',
                                                border: `1px solid ${trend.trendScore >= 50 ? '#bfdbfe' : '#e5e7eb'}`,
                                                borderRadius: '12px',
                                                padding: '16px',
                                                position: 'relative',
                                                overflow: 'hidden'
                                            }}>
                                                {/* 趨勢強度條 */}
                                                <div style={{
                                                    position: 'absolute',
                                                    bottom: 0,
                                                    left: 0,
                                                    width: `${trend.trendScore}%`,
                                                    height: '3px',
                                                    background: trend.trendScore >= 70 ? '#22c55e' : trend.trendScore >= 50 ? '#3b82f6' : '#9ca3af',
                                                    borderRadius: '0 3px 0 0'
                                                }} />

                                                <div style={{ fontWeight: 600, color: '#1f2937', marginBottom: '8px', fontSize: '14px' }}>
                                                    {trend.industry}
                                                </div>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#6b7280' }}>
                                                    <span>漲停: <strong style={{ color: '#dc2626' }}>{trend.totalLimitUp}</strong> 檔</span>
                                                    <span>活躍: <strong>{trend.daysActive}</strong> 天</span>
                                                </div>
                                                <div style={{ marginTop: '8px', fontSize: '11px', color: '#9ca3af' }}>
                                                    趨勢強度: {trend.trendScore}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* ========== 發酵中主題 - 跨新聞主題聚合 ========== */}
                            {actionableInsights?.trendingThemes && actionableInsights.trendingThemes.length > 0 && (
                                <div style={{
                                    background: '#ffffff',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '16px',
                                    padding: '24px',
                                    marginBottom: '24px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                                }}>
                                    <h3 style={{
                                        margin: '0 0 16px 0',
                                        color: '#1f2937',
                                        fontSize: '16px',
                                        fontWeight: 600,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}>
                                        🎯 發酵中主題
                                        <span style={{ fontSize: '12px', color: '#9ca3af', fontWeight: 400 }}>
                                            AI 偵測到的熱門投資主題
                                        </span>
                                    </h3>

                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                        {actionableInsights.trendingThemes.map((theme, idx) => (
                                            <div key={idx} style={{
                                                background: '#f8fafc',
                                                border: '1px solid #e2e8f0',
                                                borderRadius: '12px',
                                                padding: '16px',
                                                borderLeft: `4px solid ${theme.sentiment === 'positive' ? '#22c55e' :
                                                    theme.sentiment === 'negative' ? '#ef4444' : '#3b82f6'
                                                    }`
                                            }}>
                                                <div style={{
                                                    display: 'flex',
                                                    justifyContent: 'space-between',
                                                    alignItems: 'flex-start',
                                                    marginBottom: '10px'
                                                }}>
                                                    <div>
                                                        <div style={{
                                                            fontWeight: 600,
                                                            color: '#1f2937',
                                                            fontSize: '15px',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '8px'
                                                        }}>
                                                            {theme.heatLevel} {theme.theme}
                                                        </div>
                                                        <div style={{
                                                            fontSize: '12px',
                                                            color: theme.sentiment === 'positive' ? '#16a34a' :
                                                                theme.sentiment === 'negative' ? '#dc2626' : '#6b7280',
                                                            marginTop: '4px'
                                                        }}>
                                                            {theme.sentimentLabel} | {theme.newsCount} 則相關新聞
                                                        </div>
                                                    </div>
                                                    <div style={{
                                                        padding: '4px 10px',
                                                        background: theme.sentiment === 'positive' ? '#dcfce7' :
                                                            theme.sentiment === 'negative' ? '#fef2f2' : '#eff6ff',
                                                        borderRadius: '12px',
                                                        fontSize: '11px',
                                                        fontWeight: 500,
                                                        color: theme.sentiment === 'positive' ? '#166534' :
                                                            theme.sentiment === 'negative' ? '#991b1b' : '#1e40af',
                                                    }}>
                                                        {theme.sentiment === 'positive' ? '📈 機會' :
                                                            theme.sentiment === 'negative' ? '⚠️ 注意' : 'ℹ️ 追蹤'}
                                                    </div>
                                                </div>

                                                {/* 相關股票 */}
                                                {theme.relatedStocks.length > 0 && (
                                                    <div style={{
                                                        display: 'flex',
                                                        flexWrap: 'wrap',
                                                        gap: '6px',
                                                        marginBottom: '10px'
                                                    }}>
                                                        {theme.relatedStocks.map((stock, i) => (
                                                            <span key={i} style={{
                                                                padding: '4px 10px',
                                                                background: '#e0e7ff',
                                                                color: '#3730a3',
                                                                borderRadius: '10px',
                                                                fontSize: '12px',
                                                                cursor: 'pointer',
                                                            }}
                                                                onClick={() => {
                                                                    const code = stock.split(' ')[0];
                                                                    if (code) loadStockDetail(code);
                                                                }}
                                                            >
                                                                {stock}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* 樣本新聞 */}
                                                {theme.sampleNews.length > 0 && (
                                                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                                                        {theme.sampleNews.map((news, i) => (
                                                            <div key={i} style={{ marginBottom: '4px' }}>
                                                                • {news.title}... <span style={{ color: '#9ca3af' }}>({news.source})</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* ========== 第二層：行動建議 ========== */}
                            <div style={{ marginBottom: '24px' }}>
                                <h2 style={{ fontSize: '18px', marginBottom: '16px', color: '#1f2937', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    🎯 今日關注清單
                                    {recommendations.length > 0 && (
                                        <span style={{ fontSize: '12px', color: '#6b7280', fontWeight: 400 }}>
                                            ({recommendations.length} 檔)
                                        </span>
                                    )}
                                </h2>

                                {recommendations.length > 0 ? (
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '12px' }}>
                                        {recommendations.slice(0, 6).map(stock => (
                                            <div key={stock.symbol} style={{
                                                background: '#ffffff',
                                                border: '1px solid #e5e7eb',
                                                borderRadius: '12px',
                                                padding: '16px',
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                                            }}>
                                                <div>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                                        <span style={{ color: '#1f2937', fontWeight: 600, fontSize: '16px' }}>{stock.symbol}</span>
                                                        <span style={{ color: '#6b7280', fontSize: '14px' }}>{stock.name}</span>
                                                    </div>
                                                    {stock.relatedNews[0] && (
                                                        <div style={{ color: '#9ca3af', fontSize: '12px' }}>
                                                            💡 {stock.relatedNews[0].length > 30 ? stock.relatedNews[0].substring(0, 30) + '...' : stock.relatedNews[0]}
                                                        </div>
                                                    )}
                                                </div>
                                                <span style={{
                                                    background: stock.action === '強力關注' ? '#fef2f2' :
                                                        stock.action === '值得關注' ? '#fffbeb' : '#f3f4f6',
                                                    color: stock.action === '強力關注' ? '#dc2626' :
                                                        stock.action === '值得關注' ? '#d97706' : '#6b7280',
                                                    padding: '6px 14px',
                                                    borderRadius: '20px',
                                                    fontSize: '12px',
                                                    fontWeight: 600,
                                                    border: `1px solid ${stock.action === '強力關注' ? '#fecaca' :
                                                        stock.action === '值得關注' ? '#fde68a' : '#e5e7eb'}`
                                                }}>
                                                    {stock.action}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div style={{
                                        background: '#f9fafb',
                                        border: '1px dashed #d1d5db',
                                        borderRadius: '12px',
                                        padding: '24px',
                                        textAlign: 'center',
                                        color: '#6b7280'
                                    }}>
                                        <div style={{ fontSize: '32px', marginBottom: '8px' }}>📋</div>
                                        <div>今日系統推薦更新中，您可先查看市場情緒與最新新聞</div>
                                    </div>
                                )}
                            </div>

                            {/* ========== 第三層：新聞摘要 ========== */}
                            <div style={{ marginBottom: '24px' }}>
                                <h2 style={{ fontSize: '18px', marginBottom: '16px', color: '#1f2937' }}>
                                    📰 各來源最新新聞
                                </h2>

                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '16px' }}>
                                    {/* IEK 新聞 */}
                                    <div style={{ background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '16px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: '#16a34a', fontSize: '14px', fontWeight: 600 }}>
                                            🏢 IEK 產業情報網
                                            <span style={{ background: '#dcfce7', padding: '2px 8px', borderRadius: '12px', fontSize: '12px' }}>
                                                {iekNews.length} 則
                                            </span>
                                        </div>
                                        {iekNews.length > 0 ? (
                                            iekNews.slice(0, 4).map((news, idx) => (
                                                <div key={idx} style={{ color: '#4b5563', fontSize: '13px', marginBottom: 6, paddingLeft: 8, borderLeft: '2px solid #dcfce7' }}>
                                                    {news.title.length > 40 ? news.title.substring(0, 40) + '...' : news.title}
                                                </div>
                                            ))
                                        ) : (
                                            <div style={{ color: '#9ca3af', fontSize: '13px', fontStyle: 'italic' }}>
                                                今日暫無 IEK 新聞
                                            </div>
                                        )}
                                    </div>

                                    {/* 台視財經 */}
                                    <div style={{ background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '16px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: '#ea580c', fontSize: '14px', fontWeight: 600 }}>
                                            📺 台視財經
                                            <span style={{ background: '#ffedd5', padding: '2px 8px', borderRadius: '12px', fontSize: '12px' }}>
                                                {ttvNews.length} 則
                                            </span>
                                        </div>
                                        {ttvNews.length > 0 ? (
                                            ttvNews.slice(0, 4).map((news, idx) => (
                                                <div key={idx} style={{ color: '#4b5563', fontSize: '13px', marginBottom: 6, paddingLeft: 8, borderLeft: '2px solid #ffedd5' }}>
                                                    {news.title.length > 40 ? news.title.substring(0, 40) + '...' : news.title}
                                                </div>
                                            ))
                                        ) : (
                                            <div style={{ color: '#9ca3af', fontSize: '13px', fontStyle: 'italic' }}>
                                                今日暫無台視財經新聞
                                            </div>
                                        )}
                                    </div>

                                    {/* CMoney */}
                                    <div style={{ background: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '16px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: '#ca8a04', fontSize: '14px', fontWeight: 600 }}>
                                            💰 CMoney
                                            <span style={{ background: '#fef9c3', padding: '2px 8px', borderRadius: '12px', fontSize: '12px' }}>
                                                {cmoneyNews.length} 則
                                            </span>
                                        </div>
                                        {cmoneyNews.length > 0 ? (
                                            cmoneyNews.slice(0, 4).map((news, idx) => (
                                                <div key={idx} style={{ color: '#4b5563', fontSize: '13px', marginBottom: 6, paddingLeft: 8, borderLeft: '2px solid #fef9c3' }}>
                                                    {news.title.length > 40 ? news.title.substring(0, 40) + '...' : news.title}
                                                </div>
                                            ))
                                        ) : (
                                            <div style={{ color: '#9ca3af', fontSize: '13px', fontStyle: 'italic' }}>
                                                今日暫無 CMoney 新聞
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* ========== 第四層：全域導覽 ========== */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'center',
                                gap: '16px',
                                flexWrap: 'wrap',
                                padding: '20px',
                                background: '#f9fafb',
                                borderRadius: '12px'
                            }}>
                                <button
                                    onClick={() => setActiveTab('watchlist')}
                                    style={{
                                        padding: '12px 24px',
                                        background: '#ffffff',
                                        border: '1px solid #e5e7eb',
                                        borderRadius: '8px',
                                        color: '#374151',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: 500,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    📋 查看完整關注清單
                                </button>
                                <button
                                    onClick={async () => {
                                        const res = await fetch(`${API_BASE}/api/news/send-report`, { method: 'POST' });
                                        const data = await res.json();
                                        if (data.success) {
                                            alert(`✅ 報告已發送至: ${data.recipients?.join(', ') || '設定的收件人'}`);
                                        } else {
                                            alert(`❌ 發送失敗: ${data.error || '未知錯誤'}`);
                                        }
                                    }}
                                    style={{
                                        padding: '12px 24px',
                                        background: 'linear-gradient(90deg, #2563eb, #059669)',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: '#ffffff',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: 500,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    📧 發送今日報告到 Email
                                </button>
                            </div>
                        </div>
                    )}

                    {/* 關注股票 */}
                    {activeTab === 'watchlist' && (
                        <div>
                            <h2 style={{ fontSize: '18px', marginBottom: '16px', color: '#1f2937' }}>🎯 今日應關注的股票</h2>
                            <p style={{ color: '#6b7280', marginBottom: 20 }}>根據新聞分析，以下股票近期被頻繁提及且情緒正面，值得關注</p>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '16px' }}>
                                {recommendations.map(renderStockCard)}
                            </div>
                        </div>
                    )}

                    {/* IEK 新聞 */}
                    {activeTab === 'iek' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h2 style={{ fontSize: '18px', color: '#1f2937' }}>🏢 IEK 產業情報網新聞</h2>
                                <a
                                    href="https://ieknet.iek.org.tw/member/DailyNews.aspx"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: '#1890ff', fontSize: '13px' }}
                                >
                                    前往 IEK 網站 ↗
                                </a>
                            </div>
                            <p style={{ color: '#6b7280', marginBottom: 16, fontSize: '13px' }}>
                                共 {iekNews.length} 則新聞
                            </p>
                            {iekNews.map(renderNewsCard)}
                        </div>
                    )}

                    {/* 台視財經 */}
                    {activeTab === 'ttv' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h2 style={{ fontSize: '18px', color: '#1f2937' }}>📺 台視財經新聞</h2>
                                <a
                                    href="https://www.ttv.com.tw/finance/"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: '#1890ff', fontSize: '13px' }}
                                >
                                    前往台視財經 ↗
                                </a>
                            </div>
                            <p style={{ color: '#6b7280', marginBottom: 16, fontSize: '13px' }}>
                                共 {ttvNews.length} 則新聞
                            </p>
                            {ttvNews.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
                                    <div style={{ fontSize: 40, marginBottom: 16 }}>📭</div>
                                    暫無台視財經新聞
                                </div>
                            ) : (
                                ttvNews.map(renderNewsCard)
                            )}
                        </div>
                    )}

                    {/* CMoney 新聞 */}
                    {activeTab === 'cmoney' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h2 style={{ fontSize: '18px', color: '#1f2937' }}>💰 CMoney 投資網誌新聞</h2>
                                <a
                                    href="https://cmnews.com.tw/twstock/twstock_news"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: '#1890ff', fontSize: '13px' }}
                                >
                                    前往 CMoney ↗
                                </a>
                            </div>
                            <p style={{ color: '#6b7280', marginBottom: 16, fontSize: '13px' }}>
                                共 {cmoneyNews.length} 則新聞 - 來源：CMoney 投資網誌台股新聞快訊
                            </p>
                            {cmoneyNews.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
                                    <div style={{ fontSize: 40, marginBottom: 16 }}>📭</div>
                                    暫無 CMoney 新聞
                                </div>
                            ) : (
                                cmoneyNews.map(renderNewsCard)
                            )}
                        </div>
                    )}

                    {/* 經濟日報 UDN */}
                    {activeTab === 'udn' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h2 style={{ fontSize: '18px', color: '#1f2937' }}>📊 經濟日報熱門新聞</h2>
                                <a
                                    href="https://money.udn.com/rank/pv/1001/0"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: '#1890ff', fontSize: '13px' }}
                                >
                                    前往經濟日報 ↗
                                </a>
                            </div>
                            <p style={{ color: '#6b7280', marginBottom: 16, fontSize: '13px' }}>
                                共 {udnNews.length} 則新聞 - 來源：經濟日報即時熱門排行榜
                            </p>
                            {udnNews.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
                                    <div style={{ fontSize: 40, marginBottom: 16 }}>📭</div>
                                    暫無經濟日報新聞
                                </div>
                            ) : (
                                udnNews.map(renderNewsCard)
                            )}
                        </div>
                    )}

                    {/* 科技新報 TechNews */}
                    {activeTab === 'technews' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h2 style={{ fontSize: '18px', color: '#1f2937' }}>🔬 科技新報 TechNews</h2>
                                <a
                                    href="https://technews.tw/category/cutting-edge/"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: '#e91e63', fontSize: '13px' }}
                                >
                                    前往科技新報 ↗
                                </a>
                            </div>
                            <p style={{ color: '#6b7280', marginBottom: 16, fontSize: '13px' }}>
                                共 {technewsNews.length} 則新聞 - 來源：TechNews 尖端科技
                            </p>
                            {technewsNews.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
                                    <div style={{ fontSize: 40, marginBottom: 16 }}>📭</div>
                                    暫無科技新報新聞
                                </div>
                            ) : (
                                technewsNews.map(renderNewsCard)
                            )}
                        </div>
                    )}

                    {/* 口袋證券研報 */}
                    {activeTab === 'pocket' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h2 style={{ fontSize: '18px', color: '#1f2937' }}>📋 口袋證券研究報告</h2>
                                <a
                                    href="https://www.pocket.tw/school/report/?main=SCHOOL"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: '#ff6b00', fontSize: '13px' }}
                                >
                                    前往口袋學堂 ↗
                                </a>
                            </div>
                            <p style={{ color: '#6b7280', marginBottom: 16, fontSize: '13px' }}>
                                共 {pocketNews.length} 則研報 - 來源：口袋證券研究報告
                            </p>
                            {pocketNews.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
                                    <div style={{ fontSize: 40, marginBottom: 16 }}>📭</div>
                                    暫無口袋證券研報（需要 Playwright 爬蟲）
                                </div>
                            ) : (
                                pocketNews.map(renderNewsCard)
                            )}
                        </div>
                    )}

                    {/* Perplexity 新聞 */}
                    {activeTab === 'perplexity' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                                <h2 style={{ fontSize: '18px', color: '#1f2937' }}>🤖 Perplexity AI 新聞</h2>
                                <button
                                    onClick={() => setShowAddForm(!showAddForm)}
                                    style={{
                                        padding: '8px 16px',
                                        background: 'linear-gradient(90deg, #722ed1, #1890ff)',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: '#1f2937',
                                        cursor: 'pointer',
                                        fontSize: '13px',
                                    }}
                                >
                                    ➕ 手動新增
                                </button>
                            </div>

                            <p style={{ color: '#6b7280', marginBottom: 16, fontSize: '13px' }}>
                                ⚠️ 因 Perplexity API 需付費，此區新聞需手動更新
                            </p>

                            {/* 新增表單 */}
                            {showAddForm && (
                                <div style={{
                                    background: 'rgba(114, 46, 209, 0.1)',
                                    border: '1px solid rgba(114, 46, 209, 0.3)',
                                    borderRadius: '12px',
                                    padding: '20px',
                                    marginBottom: '20px'
                                }}>
                                    <h3 style={{ marginBottom: 16, fontSize: '16px' }}>新增 Perplexity 新聞</h3>

                                    <div style={{ marginBottom: 12 }}>
                                        <label style={{ display: 'block', marginBottom: 6, color: '#6b7280', fontSize: '13px' }}>新聞標題 *</label>
                                        <input
                                            type="text"
                                            value={newNewsTitle}
                                            onChange={e => setNewNewsTitle(e.target.value)}
                                            placeholder="輸入新聞標題..."
                                            style={{
                                                width: '100%',
                                                padding: '10px 12px',
                                                background: 'rgba(0,0,0,0.3)',
                                                border: '1px solid #e5e7eb',
                                                borderRadius: '8px',
                                                color: '#1f2937',
                                                fontSize: '14px',
                                            }}
                                        />
                                    </div>

                                    <div style={{ marginBottom: 12 }}>
                                        <label style={{ display: 'block', marginBottom: 6, color: '#6b7280', fontSize: '13px' }}>內容摘要</label>
                                        <textarea
                                            value={newNewsContent}
                                            onChange={e => setNewNewsContent(e.target.value)}
                                            placeholder="輸入新聞內容摘要..."
                                            rows={3}
                                            style={{
                                                width: '100%',
                                                padding: '10px 12px',
                                                background: 'rgba(0,0,0,0.3)',
                                                border: '1px solid #e5e7eb',
                                                borderRadius: '8px',
                                                color: '#1f2937',
                                                fontSize: '14px',
                                                resize: 'vertical',
                                            }}
                                        />
                                    </div>

                                    <div style={{ marginBottom: 12 }}>
                                        <label style={{ display: 'block', marginBottom: 6, color: '#6b7280', fontSize: '13px' }}>相關股票代碼（逗號分隔）</label>
                                        <input
                                            type="text"
                                            value={newNewsStocks}
                                            onChange={e => setNewNewsStocks(e.target.value)}
                                            placeholder="例如: 2330, 2454, 2382"
                                            style={{
                                                width: '100%',
                                                padding: '10px 12px',
                                                background: 'rgba(0,0,0,0.3)',
                                                border: '1px solid #e5e7eb',
                                                borderRadius: '8px',
                                                color: '#1f2937',
                                                fontSize: '14px',
                                            }}
                                        />
                                    </div>

                                    <div style={{ marginBottom: 16 }}>
                                        <label style={{ display: 'block', marginBottom: 6, color: '#6b7280', fontSize: '13px' }}>情緒判斷</label>
                                        <div style={{ display: 'flex', gap: 12 }}>
                                            {(['positive', 'neutral', 'negative'] as const).map(s => (
                                                <button
                                                    key={s}
                                                    onClick={() => setNewNewsSentiment(s)}
                                                    style={{
                                                        padding: '8px 16px',
                                                        background: newNewsSentiment === s ?
                                                            (s === 'positive' ? 'rgba(82, 196, 26, 0.3)' :
                                                                s === 'negative' ? 'rgba(245, 34, 45, 0.3)' : 'rgba(255,255,255,0.1)') :
                                                            'rgba(0,0,0,0.3)',
                                                        border: `1px solid ${newNewsSentiment === s ?
                                                            (s === 'positive' ? '#52c41a' : s === 'negative' ? '#f5222d' : '#8c8c8c') :
                                                            'rgba(255,255,255,0.1)'}`,
                                                        borderRadius: '8px',
                                                        color: newNewsSentiment === s ?
                                                            (s === 'positive' ? '#52c41a' : s === 'negative' ? '#f5222d' : '#fff') : '#8c8c8c',
                                                        cursor: 'pointer',
                                                        fontSize: '13px',
                                                    }}
                                                >
                                                    {s === 'positive' ? '📈 正面' : s === 'negative' ? '📉 負面' : '➖ 中性'}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div style={{ display: 'flex', gap: 12 }}>
                                        <button
                                            onClick={handleAddPerplexityNews}
                                            disabled={!newNewsTitle.trim() || addingNews}
                                            style={{
                                                padding: '10px 24px',
                                                background: 'linear-gradient(90deg, #722ed1, #1890ff)',
                                                border: 'none',
                                                borderRadius: '8px',
                                                color: '#1f2937',
                                                cursor: newNewsTitle.trim() && !addingNews ? 'pointer' : 'not-allowed',
                                                opacity: newNewsTitle.trim() && !addingNews ? 1 : 0.5,
                                                fontSize: '14px',
                                            }}
                                        >
                                            {addingNews ? '新增中...' : '✅ 新增'}
                                        </button>
                                        <button
                                            onClick={() => setShowAddForm(false)}
                                            style={{
                                                padding: '10px 24px',
                                                background: 'rgba(255,255,255,0.1)',
                                                border: 'none',
                                                borderRadius: '8px',
                                                color: '#6b7280',
                                                cursor: 'pointer',
                                                fontSize: '14px',
                                            }}
                                        >
                                            取消
                                        </button>
                                    </div>
                                </div>
                            )}

                            {perplexityNews.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
                                    <div style={{ fontSize: 40, marginBottom: 16 }}>📭</div>
                                    尚無 Perplexity 新聞，點擊「手動新增」開始
                                </div>
                            ) : (
                                perplexityNews.map(renderNewsCard)
                            )}
                        </div>
                    )}

                    {/* 產業分類 */}
                    {activeTab === 'industries' && (
                        <div>
                            <h2 style={{ fontSize: '18px', marginBottom: '16px', color: '#1f2937' }}>🏭 依產業分類</h2>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '20px' }}>
                                {Object.entries(industries).map(([industry, data]) => (
                                    <div key={industry} style={{
                                        background: '#ffffff',
                                        border: '1px solid #e5e7eb',
                                        borderRadius: '12px',
                                        padding: '16px',
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                                            <h3 style={{ fontSize: '16px', color: '#1890ff', margin: 0 }}>{industry}</h3>
                                            <span style={{
                                                background: 'rgba(24, 144, 255, 0.2)',
                                                color: '#1890ff',
                                                padding: '2px 8px',
                                                borderRadius: '12px',
                                                fontSize: '12px'
                                            }}>
                                                {data.count} 則
                                            </span>
                                        </div>
                                        {data.news.map((news, idx) => (
                                            <div key={idx} style={{
                                                padding: '8px 0',
                                                borderBottom: idx < data.news.length - 1 ? '1px solid rgba(255,255,255,0.05)' : 'none'
                                            }}>
                                                <div style={{ fontSize: '13px', color: '#e6f7ff', marginBottom: 4 }}>{news.title}</div>
                                                <div style={{ fontSize: '11px', color: '#6b7280' }}>{news.source} • {news.date}</div>
                                            </div>
                                        ))}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* 底部刷新按鈕 */}
            <div style={{
                position: 'fixed',
                bottom: 24,
                right: 24,
                display: 'flex',
                gap: 12
            }}>
                <button
                    onClick={loadData}
                    style={{
                        padding: '12px 24px',
                        background: 'linear-gradient(90deg, #1890ff, #52c41a)',
                        border: 'none',
                        borderRadius: '12px',
                        color: '#1f2937',
                        cursor: 'pointer',
                        fontSize: '14px',
                        fontWeight: 500,
                        boxShadow: '0 4px 12px rgba(24, 144, 255, 0.3)',
                    }}
                >
                    🔄 刷新數據
                </button>
            </div>

            {/* ========== 股票詳情模態框 ========== */}
            {selectedStock && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000,
                }} onClick={closeStockDetail}>
                    <div style={{
                        background: '#ffffff',
                        borderRadius: '16px',
                        width: '90%',
                        maxWidth: '800px',
                        maxHeight: '85vh',
                        overflow: 'auto',
                        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                    }} onClick={(e) => e.stopPropagation()}>
                        {loadingStockDetail ? (
                            <div style={{ padding: '60px', textAlign: 'center', color: '#6b7280' }}>
                                <div style={{ fontSize: '32px', marginBottom: '16px' }}>📊</div>
                                載入中...
                            </div>
                        ) : stockDetail ? (
                            <div>
                                {/* 標題區 */}
                                <div style={{
                                    background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
                                    color: '#ffffff',
                                    padding: '24px',
                                    borderRadius: '16px 16px 0 0',
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                        <div>
                                            <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>
                                                {stockDetail.stockCode} {stockDetail.stockName}
                                            </h2>
                                            <div style={{ marginTop: '8px', opacity: 0.8, fontSize: '14px' }}>
                                                {stockDetail.industries?.[0]?.industry && (
                                                    <span>📂 {stockDetail.industries[0].industry} - {stockDetail.industries[0].role}</span>
                                                )}
                                            </div>
                                        </div>
                                        <button onClick={closeStockDetail} style={{
                                            background: 'rgba(255,255,255,0.2)',
                                            border: 'none',
                                            borderRadius: '50%',
                                            width: '36px',
                                            height: '36px',
                                            color: '#ffffff',
                                            cursor: 'pointer',
                                            fontSize: '18px',
                                        }}>✕</button>
                                    </div>

                                    {/* 情緒指標 */}
                                    <div style={{ marginTop: '20px', display: 'flex', gap: '24px' }}>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{ fontSize: '32px', fontWeight: 700 }}>
                                                {stockDetail.totalNews}
                                            </div>
                                            <div style={{ fontSize: '12px', opacity: 0.8 }}>相關新聞</div>
                                        </div>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{
                                                fontSize: '32px',
                                                fontWeight: 700,
                                                color: stockDetail.sentimentAnalysis.overall === 'positive' ? '#86efac' :
                                                    stockDetail.sentimentAnalysis.overall === 'negative' ? '#fca5a5' : '#e5e7eb'
                                            }}>
                                                {stockDetail.sentimentAnalysis.overall === 'positive' ? '📈' :
                                                    stockDetail.sentimentAnalysis.overall === 'negative' ? '📉' : '➖'}
                                            </div>
                                            <div style={{ fontSize: '12px', opacity: 0.8 }}>情緒傾向</div>
                                        </div>
                                        <div style={{ textAlign: 'center' }}>
                                            <div style={{ fontSize: '32px', fontWeight: 700 }}>
                                                {stockDetail.sentimentAnalysis.positive.ratio}%
                                            </div>
                                            <div style={{ fontSize: '12px', opacity: 0.8 }}>正面比例</div>
                                        </div>
                                    </div>
                                </div>

                                {/* 內容區 */}
                                <div style={{ padding: '24px' }}>
                                    {/* 情緒比例條 */}
                                    <div style={{ marginBottom: '24px' }}>
                                        <div style={{ fontSize: '14px', fontWeight: 600, color: '#1f2937', marginBottom: '8px' }}>
                                            今日新聞情緒分佈
                                        </div>
                                        <div style={{
                                            display: 'flex',
                                            height: '12px',
                                            borderRadius: '6px',
                                            overflow: 'hidden',
                                            marginBottom: '8px'
                                        }}>
                                            <div style={{
                                                width: `${stockDetail.sentimentAnalysis.positive.ratio}%`,
                                                background: 'linear-gradient(90deg, #22c55e, #16a34a)',
                                            }} />
                                            <div style={{
                                                width: `${stockDetail.sentimentAnalysis.neutral.ratio}%`,
                                                background: '#9ca3af',
                                            }} />
                                            <div style={{
                                                width: `${stockDetail.sentimentAnalysis.negative.ratio}%`,
                                                background: 'linear-gradient(90deg, #ef4444, #dc2626)',
                                            }} />
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                                            <span style={{ color: '#16a34a' }}>
                                                📈 正面 {stockDetail.sentimentAnalysis.positive.count} 則 ({stockDetail.sentimentAnalysis.positive.ratio}%)
                                            </span>
                                            <span style={{ color: '#6b7280' }}>
                                                ➖ 中性 {stockDetail.sentimentAnalysis.neutral.count} 則
                                            </span>
                                            <span style={{ color: '#dc2626' }}>
                                                📉 負面 {stockDetail.sentimentAnalysis.negative.count} 則 ({stockDetail.sentimentAnalysis.negative.ratio}%)
                                            </span>
                                        </div>
                                    </div>

                                    {/* 相關概念 */}
                                    {stockDetail.industries?.[0]?.relatedConcepts && stockDetail.industries[0].relatedConcepts.length > 0 && (
                                        <div style={{ marginBottom: '24px' }}>
                                            <div style={{ fontSize: '14px', fontWeight: 600, color: '#1f2937', marginBottom: '8px' }}>
                                                相關概念
                                            </div>
                                            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                                {stockDetail.industries[0].relatedConcepts.map((concept, i) => (
                                                    <span key={i} style={{
                                                        padding: '6px 14px',
                                                        background: '#e0e7ff',
                                                        color: '#3730a3',
                                                        borderRadius: '16px',
                                                        fontSize: '13px',
                                                    }}>{concept}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* 同業比較 */}
                                    {stockDetail.peerStocks && stockDetail.peerStocks.length > 0 && (
                                        <div style={{ marginBottom: '24px' }}>
                                            <div style={{ fontSize: '14px', fontWeight: 600, color: '#1f2937', marginBottom: '8px' }}>
                                                同產業股票
                                            </div>
                                            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                                {stockDetail.peerStocks.map(peer => (
                                                    <button
                                                        key={peer.code}
                                                        onClick={() => loadStockDetail(peer.code)}
                                                        style={{
                                                            padding: '8px 16px',
                                                            background: '#f8fafc',
                                                            border: '1px solid #e2e8f0',
                                                            borderRadius: '8px',
                                                            cursor: 'pointer',
                                                            fontSize: '13px',
                                                            color: '#374151',
                                                        }}
                                                    >
                                                        {peer.code} {peer.name}
                                                        {peer.mentionCount > 0 && (
                                                            <span style={{ marginLeft: '6px', color: '#6b7280' }}>({peer.mentionCount}則)</span>
                                                        )}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* 相關新聞列表 */}
                                    <div>
                                        <div style={{ fontSize: '14px', fontWeight: 600, color: '#1f2937', marginBottom: '12px' }}>
                                            📰 相關新聞 ({stockDetail.relatedNews?.length || 0} 則)
                                        </div>
                                        {stockDetail.relatedNews && stockDetail.relatedNews.length > 0 ? (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                                {stockDetail.relatedNews.slice(0, 10).map((news, idx) => (
                                                    <div key={idx} style={{
                                                        padding: '12px 16px',
                                                        background: '#f8fafc',
                                                        borderRadius: '8px',
                                                        borderLeft: `3px solid ${news.sentiment === 'positive' ? '#22c55e' :
                                                            news.sentiment === 'negative' ? '#ef4444' : '#9ca3af'
                                                            }`
                                                    }}>
                                                        <div style={{ fontSize: '14px', color: '#1f2937', marginBottom: '4px' }}>
                                                            {news.title}
                                                        </div>
                                                        <div style={{ fontSize: '12px', color: '#6b7280' }}>
                                                            📅 {news.date} | 🏢 {news.source}
                                                            {news.industry && <span> | 📂 {news.industry}</span>}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div style={{ color: '#9ca3af', textAlign: 'center', padding: '20px' }}>
                                                今日暫無此股票的相關新聞
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div style={{ padding: '60px', textAlign: 'center', color: '#6b7280' }}>
                                無法載入股票資訊
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
