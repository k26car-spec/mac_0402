'use client';

import { useState, useEffect } from 'react';
import { useLSTMPrediction, useLSTMModels } from '@/hooks/useLSTM';
import { LSTMPredictionChart } from '@/components/charts/LSTMPredictionChart';
import { Brain, TrendingUp, TrendingDown, Activity, AlertCircle, CheckCircle, Info } from 'lucide-react';
import { formatPrice, formatPercentage, getTrendIcon, cn } from '@/lib/utils';

const DEFAULT_STOCKS = [
    { symbol: '2330', name: '台積電' },
    { symbol: '2454', name: '聯發科' },
    { symbol: '2317', name: '鴻海' },
    { symbol: '2409', name: '友達' },
    { symbol: '6669', name: '緯穎' },
    { symbol: '3443', name: '創意' },
    { symbol: '2308', name: '台達電' },
    { symbol: '2382', name: '廣達' },
];

export default function LSTMPage() {
    const [selectedStock, setSelectedStock] = useState('2330');
    const [availableStocks, setAvailableStocks] = useState(DEFAULT_STOCKS);

    useEffect(() => {
        const fetchWatchlist = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/orb/watchlist');
                const data = await response.json();
                if (data.success && data.details) {
                    const stocks = data.details.map((item: any) => ({
                        symbol: item.code,
                        name: item.name || item.code
                    }));
                    setAvailableStocks(stocks);
                }
            } catch (error) {
                console.error('Failed to fetch watchlist:', error);
            }
        };
        fetchWatchlist();
    }, []);

    const { data: prediction, isLoading, error } = useLSTMPrediction(selectedStock);
    const { data: models } = useLSTMModels();

    if (error) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">載入失敗</h3>
                    <p className="text-gray-600">無法取得 LSTM 預測數據</p>
                    <p className="text-sm text-gray-500 mt-2">{error.message}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Brain className="w-8 h-8 text-blue-600" />
                        LSTM 智能預測
                    </h1>
                    <p className="text-gray-600 mt-2">基於深度學習的股價預測系統</p>
                </div>

                {/* Model Info Badge */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
                    <div className="text-sm text-blue-600 font-medium">
                        已訓練模型: {models?.length || 6} 個
                    </div>
                </div>
            </div>

            {/* Stock Selector */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">選擇股票</h2>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    {availableStocks.map((stock) => (
                        <button
                            key={stock.symbol}
                            onClick={() => setSelectedStock(stock.symbol)}
                            className={cn(
                                "p-4 rounded-lg border-2 transition-all",
                                "hover:border-blue-400 hover:shadow-md",
                                selectedStock === stock.symbol
                                    ? "border-blue-600 bg-blue-50"
                                    : "border-gray-200 bg-white"
                            )}
                        >
                            <div className="font-bold text-gray-900">{stock.symbol}</div>
                            <div className="text-sm text-gray-600">{stock.name}</div>
                        </button>
                    ))}
                </div>
            </div>

            {isLoading ? (
                <LoadingSkeleton />
            ) : prediction ? (
                <>
                    {/* Main Chart */}
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-gray-900">
                                    {selectedStock} - 價格預測走勢
                                </h2>
                                <p className="text-sm text-gray-600 mt-1">
                                    目前價格: {formatPrice(prediction.currentPrice)} 元
                                </p>
                            </div>

                            {/* Trend Badge */}
                            <div className={cn(
                                "px-4 py-2 rounded-lg font-semibold",
                                prediction.trend === 'up' && "bg-green-100 text-green-700",
                                prediction.trend === 'down' && "bg-red-100 text-red-700",
                                prediction.trend === 'neutral' && "bg-gray-100 text-gray-700"
                            )}>
                                {getTrendIcon(prediction.trend)} 趨勢: {
                                    prediction.trend === 'up' ? '看漲' :
                                        prediction.trend === 'down' ? '看跌' : '持平'
                                }
                            </div>
                        </div>

                        <LSTMPredictionChart data={prediction} />
                    </div>

                    {/* Predictions Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <PredictionCard
                            label="1 天預測"
                            currentPrice={prediction.currentPrice}
                            predictedPrice={prediction.predictions.day1}
                            icon={<TrendingUp className="w-6 h-6" />}
                        />
                        <PredictionCard
                            label="3 天預測"
                            currentPrice={prediction.currentPrice}
                            predictedPrice={prediction.predictions.day3}
                            icon={<Activity className="w-6 h-6" />}
                        />
                        <PredictionCard
                            label="5 天預測"
                            currentPrice={prediction.currentPrice}
                            predictedPrice={prediction.predictions.day5}
                            icon={<TrendingDown className="w-6 h-6" />}
                        />
                    </div>

                    {/* Scenarios Analysis */}
                    {prediction.scenarios && (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-4">情境分析 (Scenario Analysis)</h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="p-4 bg-green-50 rounded-lg border border-green-100">
                                    <div className="text-sm text-green-700 font-medium">樂觀情境</div>
                                    <div className="text-xl font-bold text-green-700 mt-1">
                                        {formatPrice(prediction.scenarios.optimistic)} 元
                                    </div>
                                </div>
                                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                                    <div className="text-sm text-gray-700 font-medium">中性情境</div>
                                    <div className="text-xl font-bold text-gray-900 mt-1">
                                        {formatPrice(prediction.scenarios.neutral)} 元
                                    </div>
                                </div>
                                <div className="p-4 bg-red-50 rounded-lg border border-red-100">
                                    <div className="text-sm text-red-700 font-medium">悲觀情境</div>
                                    <div className="text-xl font-bold text-red-700 mt-1">
                                        {formatPrice(prediction.scenarios.pessimistic)} 元
                                    </div>
                                </div>
                            </div>
                            <p className="text-sm text-gray-500 mt-4">
                                * 預測區間: {formatPrice(prediction.scenarios.pessimistic)} - {formatPrice(prediction.scenarios.optimistic)} 元 (信心區間 95%)
                            </p>
                        </div>
                    )}

                    {/* Details Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Technical Indicators */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-4">技術指標</h3>
                            <div className="space-y-3">
                                <IndicatorRow label="RSI" value={prediction.indicators.rsi.toFixed(2)} />
                                <IndicatorRow label="MACD" value={prediction.indicators.macd.toFixed(2)} />
                                <IndicatorRow label="MA5" value={formatPrice(prediction.indicators.ma5)} />
                                <IndicatorRow label="MA20" value={formatPrice(prediction.indicators.ma20)} />
                            </div>
                        </div>

                        {/* Model Performance */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-4">模型效能</h3>
                            <div className="space-y-3">
                                <ModelMetricRow
                                    label="準確率"
                                    value={`${((prediction.modelInfo.accuracy || 0) * 100).toFixed(2)}%`}
                                    status={(prediction.modelInfo.accuracy || 0) >= 0.7 ? 'good' : 'warning'}
                                />
                                <ModelMetricRow
                                    label="MSE"
                                    value={(prediction.modelInfo.mse || 0).toFixed(4)}
                                    status="neutral"
                                />
                                <ModelMetricRow
                                    label="MAE"
                                    value={(prediction.modelInfo.mae || 0).toFixed(2)}
                                    status="neutral"
                                />
                                <ModelMetricRow
                                    label="MAPE"
                                    value={`${(prediction.modelInfo.mape || 0).toFixed(2)}%`}
                                    status={(prediction.modelInfo.mape || 100) < 5 ? 'good' : 'warning'}
                                />
                            </div>

                            <div className="mt-4 pt-4 border-t border-gray-200">
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-gray-600">訓練時間</span>
                                    <span className="text-gray-900 font-medium">
                                        {new Date(prediction.modelInfo.trainedAt).toLocaleDateString('zh-TW')}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between text-sm mt-2">
                                    <span className="text-gray-600">資料範圍</span>
                                    <span className="text-gray-900 font-medium">{prediction.modelInfo.dataRange || 'N/A'}</span>
                                </div>
                                <div className="flex items-center justify-between text-sm mt-2">
                                    <span className="text-gray-600">模型版本</span>
                                    <span className="text-gray-900 font-medium">{prediction.modelInfo.version}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Confidence & Info */}
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200 p-6">
                        <div className="flex items-start gap-4">
                            <Info className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
                            <div className="flex-1">
                                <h3 className="text-lg font-bold text-gray-900 mb-2">
                                    預測信心度: {(prediction.confidence * 100).toFixed(1)}%
                                </h3>
                                <p className="text-gray-700 text-sm leading-relaxed">
                                    基於 LSTM 深度學習模型，使用 120 天歷史數據訓練。
                                    預測僅供參考，投資需謹慎。模型會持續學習和優化以提高準確度。
                                </p>
                            </div>
                        </div>
                    </div>
                </>
            ) : null}
        </div>
    );
}

// Prediction Card Component
function PredictionCard({
    label,
    currentPrice,
    predictedPrice,
    icon,
}: {
    label: string;
    currentPrice: number;
    predictedPrice: number;
    icon: React.ReactNode;
}) {
    const change = ((predictedPrice - currentPrice) / currentPrice) * 100;
    const isPositive = change >= 0;

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
                <div className={cn(
                    "p-3 rounded-lg",
                    isPositive ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600"
                )}>
                    {icon}
                </div>
                <div className={cn(
                    "text-sm font-semibold px-3 py-1 rounded-full",
                    isPositive ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                )}>
                    {formatPercentage(change)}
                </div>
            </div>

            <div className="text-sm text-gray-600 mb-1">{label}</div>
            <div className="text-2xl font-bold text-gray-900">
                {formatPrice(predictedPrice)} 元
            </div>
            <div className="text-sm text-gray-600 mt-2">
                從 {formatPrice(currentPrice)} 元
            </div>
        </div>
    );
}

// Indicator Row Component
function IndicatorRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
            <span className="text-gray-600">{label}</span>
            <span className="font-semibold text-gray-900">{value}</span>
        </div>
    );
}

// Model Metric Row Component
function ModelMetricRow({
    label,
    value,
    status,
}: {
    label: string;
    value: string;
    status: 'good' | 'warning' | 'neutral';
}) {
    const statusIcon = {
        good: <CheckCircle className="w-4 h-4 text-green-600" />,
        warning: <AlertCircle className="w-4 h-4 text-yellow-600" />,
        neutral: <Info className="w-4 h-4 text-gray-400" />,
    };

    return (
        <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
            <div className="flex items-center gap-2">
                {statusIcon[status]}
                <span className="text-gray-600">{label}</span>
            </div>
            <span className="font-semibold text-gray-900">{value}</span>
        </div>
    );
}

// Loading Skeleton
function LoadingSkeleton() {
    return (
        <div className="space-y-6 animate-pulse">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
                <div className="h-[400px] bg-gray-100 rounded"></div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                        <div className="h-20 bg-gray-200 rounded"></div>
                    </div>
                ))}
            </div>
        </div>
    );
}
