'use client';

import { useState, useEffect, useCallback } from 'react';
import { Search, Filter, TrendingUp, Brain, Target, BarChart3, Download, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { cn, formatPrice, formatPercentage } from '@/lib/utils';

interface StockData {
    symbol: string;
    name: string;
    price: number;
    change: number;
    volume: number;
    source?: string;
}

interface AIScores {
    lstm: number;
    mainforce: number;
    combined: number;
    dataSource: string;
}

// 股票名稱對照
const STOCK_NAMES: Record<string, string> = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2409": "友達",
    "6669": "緯穎", "3443": "創意", "2308": "台達電", "2382": "廣達",
    "2881": "富邦金", "2412": "中華電"
};

type SortBy = 'combined' | 'lstm' | 'mainforce' | 'change' | 'volume';

export default function ScannerPage() {
    const [stockPool, setStockPool] = useState<StockData[]>([]);
    const [aiScores, setAiScores] = useState<Record<string, AIScores>>({});
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingScores, setIsLoadingScores] = useState(false);
    const [dataSource, setDataSource] = useState<string>('');

    const [filters, setFilters] = useState({
        minPrice: '',
        maxPrice: '',
        minChange: '',
        minVolume: '',
        minLSTM: '0.5',
        minMainForce: '0.5',
        minCombined: '0.5',
    });

    const [sortBy, setSortBy] = useState<SortBy>('combined');
    const [isScanning, setIsScanning] = useState(false);

    // 獲取單支股票的 AI 評分
    const fetchAIScoresForStock = async (symbol: string): Promise<AIScores> => {
        try {
            // 獲取 LSTM 預測
            const lstmResponse = await fetch(`http://localhost:8000/api/lstm/predict/${symbol}`, {
                signal: AbortSignal.timeout(5000)
            });
            let lstmScore = 0.5;
            if (lstmResponse.ok) {
                const lstmData = await lstmResponse.json();
                if (lstmData.success && lstmData.prediction) {
                    // 根據信心度和趨勢方向計算分數
                    const confidence = lstmData.prediction.confidence || 0.5;
                    const trend = lstmData.prediction.trend_direction;
                    if (trend === 'up' || trend === 'bullish') {
                        lstmScore = 0.5 + (confidence * 0.5);
                    } else if (trend === 'down' || trend === 'bearish') {
                        lstmScore = 0.5 - (confidence * 0.3);
                    } else {
                        lstmScore = 0.5;
                    }
                }
            }

            // 獲取主力分析
            const analysisResponse = await fetch(`http://localhost:8000/api/analysis/summary/${symbol}`, {
                signal: AbortSignal.timeout(5000)
            });
            let mainforceScore = 0.5;
            if (analysisResponse.ok) {
                const analysisData = await analysisResponse.json();
                if (analysisData.mainforce) {
                    const action = analysisData.mainforce.action;
                    const confidence = analysisData.mainforce.confidence || 0.5;
                    if (action === 'buy' || action === 'accumulating' || action === 'entry') {
                        mainforceScore = 0.5 + (confidence * 0.5);
                    } else if (action === 'sell' || action === 'distributing' || action === 'exit') {
                        mainforceScore = 0.5 - (confidence * 0.3);
                    }
                }
            }

            // 綜合評分 = LSTM 權重 0.4 + 主力權重 0.6
            const combinedScore = (lstmScore * 0.4) + (mainforceScore * 0.6);

            return {
                lstm: lstmScore,
                mainforce: mainforceScore,
                combined: combinedScore,
                dataSource: 'api'
            };
        } catch (error) {
            console.error(`獲取 ${symbol} AI 評分失敗:`, error);
            return {
                lstm: 0.5,
                mainforce: 0.5,
                combined: 0.5,
                dataSource: 'error'
            };
        }
    };

    // 獲取所有股票的 AI 評分
    const fetchAllAIScores = async (stocks: StockData[]) => {
        setIsLoadingScores(true);
        const scores: Record<string, AIScores> = {};

        // 並行獲取所有股票的評分
        const results = await Promise.all(
            stocks.map(async (stock) => {
                const score = await fetchAIScoresForStock(stock.symbol);
                return { symbol: stock.symbol, score };
            })
        );

        results.forEach(({ symbol, score }) => {
            scores[symbol] = score;
        });

        setAiScores(scores);
        setIsLoadingScores(false);
    };

    // 獲取即時數據
    const fetchStockData = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await fetch('http://localhost:8000/api/fubon/quotes');
            const data = await response.json();

            if (data.quotes) {
                const stocks = data.quotes.map((q: any) => ({
                    symbol: q.symbol,
                    name: STOCK_NAMES[q.symbol] || q.symbol,
                    price: q.price || 0,
                    change: q.change || 0,
                    volume: q.volume || 0,
                    source: q.source
                }));
                setStockPool(stocks);
                setDataSource(data.quotes[0]?.source || 'unknown');

                // 獲取 AI 評分
                await fetchAllAIScores(stocks);
            }
        } catch (error) {
            console.error('獲取股票數據失敗:', error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchStockData();
    }, [fetchStockData]);

    // 獲取股票的評分（使用真實 API 數據）
    const getScores = (symbol: string): AIScores => {
        return aiScores[symbol] || { lstm: 0.5, mainforce: 0.5, combined: 0.5, dataSource: 'loading' };
    };

    // 篩選股票
    const filteredStocks = stockPool.filter(stock => {
        const scores = getScores(stock.symbol);

        if (filters.minPrice && stock.price < parseFloat(filters.minPrice)) return false;
        if (filters.maxPrice && stock.price > parseFloat(filters.maxPrice)) return false;
        if (filters.minChange && stock.change < parseFloat(filters.minChange)) return false;
        if (filters.minVolume && stock.volume < parseFloat(filters.minVolume)) return false;
        if (filters.minLSTM && scores.lstm < parseFloat(filters.minLSTM)) return false;
        if (filters.minMainForce && scores.mainforce < parseFloat(filters.minMainForce)) return false;
        if (filters.minCombined && scores.combined < parseFloat(filters.minCombined)) return false;

        return true;
    });

    // 排序股票
    const sortedStocks = [...filteredStocks].sort((a, b) => {
        const scoresA = getScores(a.symbol);
        const scoresB = getScores(b.symbol);

        switch (sortBy) {
            case 'combined':
                return scoresB.combined - scoresA.combined;
            case 'lstm':
                return scoresB.lstm - scoresA.lstm;
            case 'mainforce':
                return scoresB.mainforce - scoresA.mainforce;
            case 'change':
                return b.change - a.change;
            case 'volume':
                return b.volume - a.volume;
            default:
                return 0;
        }
    });

    const handleScan = () => {
        setIsScanning(true);
        fetchStockData().finally(() => setIsScanning(false));
    };

    const handleReset = () => {
        setFilters({
            minPrice: '',
            maxPrice: '',
            minChange: '',
            minVolume: '',
            minLSTM: '0.5',
            minMainForce: '0.5',
            minCombined: '0.5',
        });
    };

    return (
        <div className="space-y-6">
            {/* 頁面標題 */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Search className="w-8 h-8 text-blue-600" />
                        智能選股掃描器
                    </h1>
                    <div className="flex items-center gap-2 mt-2">
                        <p className="text-gray-600">結合 LSTM 預測與主力偵測，AI 智能篩選優質股票</p>
                        <span className={cn(
                            "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase flex items-center gap-1",
                            Object.values(aiScores).some(s => s.dataSource === 'api')
                                ? "bg-green-100 text-green-700"
                                : "bg-gray-100 text-gray-500"
                        )}>
                            {isLoadingScores ? (
                                <>
                                    <RefreshCw className="w-3 h-3 animate-spin" />
                                    載入評分中
                                </>
                            ) : Object.values(aiScores).some(s => s.dataSource === 'api') ? (
                                <>
                                    <Wifi className="w-3 h-3" />
                                    真實 API 數據
                                </>
                            ) : (
                                <>
                                    <WifiOff className="w-3 h-3" />
                                    離線
                                </>
                            )}
                        </span>
                    </div>
                </div>

                {/* 統計徽章 */}
                <div className="flex items-center gap-3">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
                        <div className="text-sm text-blue-600">股票池</div>
                        <div className="text-2xl font-bold text-blue-600">{stockPool.length}</div>
                    </div>
                    <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2">
                        <div className="text-sm text-green-600">符合條件</div>
                        <div className="text-2xl font-bold text-green-600">{filteredStocks.length}</div>
                    </div>
                </div>
            </div>

            {/* 篩選條件 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                        <Filter className="w-5 h-5 text-blue-600" />
                        篩選條件
                    </h2>
                    <div className="flex gap-2">
                        <button
                            onClick={handleReset}
                            className="px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            重置
                        </button>
                        <button
                            onClick={handleScan}
                            disabled={isScanning}
                            className={cn(
                                "px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold transition-all",
                                "hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed",
                                "flex items-center gap-2"
                            )}
                        >
                            {isScanning ? (
                                <>
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    掃描中...
                                </>
                            ) : (
                                <>
                                    <Search className="w-4 h-4" />
                                    開始掃描
                                </>
                            )}
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* 價格範圍 */}
                    <FilterInput
                        label="最低價格"
                        value={filters.minPrice}
                        onChange={(value) => setFilters({ ...filters, minPrice: value })}
                        placeholder="不限"
                        type="number"
                    />
                    <FilterInput
                        label="最高價格"
                        value={filters.maxPrice}
                        onChange={(value) => setFilters({ ...filters, maxPrice: value })}
                        placeholder="不限"
                        type="number"
                    />

                    {/* 漲跌幅 */}
                    <FilterInput
                        label="最低漲跌幅 (%)"
                        value={filters.minChange}
                        onChange={(value) => setFilters({ ...filters, minChange: value })}
                        placeholder="不限"
                        type="number"
                    />

                    {/* 成交量 */}
                    <FilterInput
                        label="最低成交量 (張)"
                        value={filters.minVolume}
                        onChange={(value) => setFilters({ ...filters, minVolume: value })}
                        placeholder="不限"
                        type="number"
                    />

                    {/* AI 評分 */}
                    <FilterInput
                        label="LSTM 最低分數"
                        value={filters.minLSTM}
                        onChange={(value) => setFilters({ ...filters, minLSTM: value })}
                        placeholder="0.0 - 1.0"
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                    />

                    <FilterInput
                        label="主力最低分數"
                        value={filters.minMainForce}
                        onChange={(value) => setFilters({ ...filters, minMainForce: value })}
                        placeholder="0.0 - 1.0"
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                    />

                    <FilterInput
                        label="綜合最低分數"
                        value={filters.minCombined}
                        onChange={(value) => setFilters({ ...filters, minCombined: value })}
                        placeholder="0.0 - 1.0"
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                    />
                </div>
            </div>

            {/* 排序選項 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-gray-900">排序方式：</h3>
                    <div className="flex gap-2">
                        <SortButton
                            active={sortBy === 'combined'}
                            onClick={() => setSortBy('combined')}
                            icon={<BarChart3 className="w-4 h-4" />}
                            label="綜合評分"
                        />
                        <SortButton
                            active={sortBy === 'lstm'}
                            onClick={() => setSortBy('lstm')}
                            icon={<Brain className="w-4 h-4" />}
                            label="LSTM"
                        />
                        <SortButton
                            active={sortBy === 'mainforce'}
                            onClick={() => setSortBy('mainforce')}
                            icon={<Target className="w-4 h-4" />}
                            label="主力"
                        />
                        <SortButton
                            active={sortBy === 'change'}
                            onClick={() => setSortBy('change')}
                            icon={<TrendingUp className="w-4 h-4" />}
                            label="漲跌幅"
                        />
                        <SortButton
                            active={sortBy === 'volume'}
                            onClick={() => setSortBy('volume')}
                            label="成交量"
                        />
                    </div>
                </div>
            </div>

            {/* 結果列表 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="p-6 border-b border-gray-200 flex items-center justify-between">
                    <h2 className="text-xl font-bold text-gray-900">
                        掃描結果 ({sortedStocks.length} 支股票)
                    </h2>
                    <button className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                        <Download className="w-4 h-4" />
                        匯出結果
                    </button>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    排名
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    股票
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    價格
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    漲跌幅
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    成交量
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    LSTM
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    主力
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    綜合評分
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    操作
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {sortedStocks.map((stock, index) => {
                                const scores = getScores(stock.symbol);
                                return (
                                    <StockRow
                                        key={stock.symbol}
                                        rank={index + 1}
                                        stock={stock}
                                        scores={scores}
                                    />
                                );
                            })}
                            {sortedStocks.length === 0 && (
                                <tr>
                                    <td colSpan={9} className="px-6 py-12 text-center text-gray-500">
                                        {isLoading ? '載入中...' : '沒有符合條件的股票，請調整篩選條件'}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

// 篩選輸入組件
function FilterInput({
    label,
    value,
    onChange,
    placeholder,
    type = 'text',
    step,
    min,
    max,
}: {
    label: string;
    value: string;
    onChange: (value: string) => void;
    placeholder: string;
    type?: string;
    step?: string;
    min?: string;
    max?: string;
}) {
    return (
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
                {label}
            </label>
            <input
                type={type}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder={placeholder}
                step={step}
                min={min}
                max={max}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
        </div>
    );
}

// 排序按鈕組件
function SortButton({
    active,
    onClick,
    icon,
    label,
}: {
    active: boolean;
    onClick: () => void;
    icon?: React.ReactNode;
    label: string;
}) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2",
                active
                    ? "bg-blue-600 text-white shadow-md"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
        >
            {icon}
            {label}
        </button>
    );
}

// 股票列組件
function StockRow({
    rank,
    stock,
    scores,
}: {
    rank: number;
    stock: StockData;
    scores: AIScores;
}) {
    const getRankColor = (rank: number) => {
        if (rank === 1) return 'bg-yellow-100 text-yellow-700';
        if (rank === 2) return 'bg-gray-100 text-gray-700';
        if (rank === 3) return 'bg-orange-100 text-orange-700';
        return 'bg-blue-50 text-blue-600';
    };

    const getScoreColor = (score: number) => {
        if (score >= 0.8) return 'text-green-600 bg-green-50';
        if (score >= 0.7) return 'text-blue-600 bg-blue-50';
        if (score >= 0.6) return 'text-yellow-600 bg-yellow-50';
        return 'text-gray-600 bg-gray-50';
    };

    return (
        <tr className="hover:bg-gray-50 transition-colors">
            <td className="px-6 py-4">
                <div className={cn('w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm', getRankColor(rank))}>
                    {rank}
                </div>
            </td>
            <td className="px-6 py-4">
                <div className="font-semibold text-gray-900">{stock.symbol}</div>
                <div className="text-sm text-gray-600">{stock.name}</div>
            </td>
            <td className="px-6 py-4 text-right">
                <div className="font-semibold text-gray-900">{formatPrice(stock.price)}</div>
            </td>
            <td className="px-6 py-4 text-right">
                <div className={cn('font-semibold', stock.change >= 0 ? 'text-rise' : 'text-fall')}>
                    {formatPercentage(stock.change)}
                </div>
            </td>
            <td className="px-6 py-4 text-right">
                <div className="text-gray-900">{stock.volume.toLocaleString()}</div>
            </td>
            <td className="px-6 py-4 text-center">
                <span className={cn('px-3 py-1 rounded-full text-sm font-semibold', getScoreColor(scores.lstm))}>
                    {(scores.lstm * 100).toFixed(0)}
                </span>
            </td>
            <td className="px-6 py-4 text-center">
                <span className={cn('px-3 py-1 rounded-full text-sm font-semibold', getScoreColor(scores.mainforce))}>
                    {(scores.mainforce * 100).toFixed(0)}
                </span>
            </td>
            <td className="px-6 py-4 text-center">
                <span className={cn('px-3 py-1 rounded-full text-sm font-semibold', getScoreColor(scores.combined))}>
                    {(scores.combined * 100).toFixed(0)}
                </span>
            </td>
            <td className="px-6 py-4 text-center">
                <button className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors text-sm font-medium">
                    詳細分析
                </button>
            </td>
        </tr>
    );
}
