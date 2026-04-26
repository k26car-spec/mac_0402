'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, AlertCircle } from 'lucide-react';

interface PredictionData {
    symbol: string;
    predicted_price: number;
    confidence: number;
    model_version: string;
    timestamp: string;
    note: string;
}

interface ModelMetrics {
    r2_score: number;
    direction_accuracy: number;
    mape: number;
    rmse: number;
}

export default function LSTMPrediction({ symbol }: { symbol: string }) {
    const [prediction, setPrediction] = useState<PredictionData | null>(null);
    const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchPrediction();
        fetchMetrics();
    }, [symbol]);

    const fetchPrediction = async () => {
        try {
            setLoading(true);
            const response = await fetch(`http://127.0.0.1:8000/api/lstm/predict/${symbol}`);

            if (!response.ok) {
                throw new Error('Failed to fetch prediction');
            }

            const data = await response.json();
            setPrediction(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    };

    const fetchMetrics = async () => {
        try {
            const response = await fetch(`http://127.0.0.1:8000/api/lstm/model/${symbol}/info`);
            if (response.ok) {
                const data = await response.json();
                setMetrics(data.performance_metrics);
            }
        } catch (err) {
            console.error('Failed to fetch metrics:', err);
        }
    };

    if (loading) {
        return (
            <div className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-md">
                <div className="p-6">
                    <div className="flex items-center justify-center p-8">
                        <Activity className="w-6 h-6 animate-spin text-blue-500" />
                        <span className="ml-2 text-gray-600 dark:text-gray-300">加载AI预测中...</span>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-md border-2 border-red-200">
                <div className="p-6">
                    <div className="flex items-center text-red-600">
                        <AlertCircle className="w-5 h-5 mr-2" />
                        <span>{error}</span>
                    </div>
                </div>
            </div>
        );
    }

    if (!prediction) return null;

    const trend = prediction.predicted_price > 0 ? 'up' : 'down';
    const TrendIcon = trend === 'up' ? TrendingUp : TrendingDown;
    const trendColor = trend === 'up' ? 'text-green-600' : 'text-red-600';

    return (
        <div className="w-full bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 rounded-lg shadow-lg">
            <div className="p-6">
                {/* Header */}
                <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center">
                        <Activity className="w-5 h-5 mr-2 text-blue-600" />
                        <span className="text-xl font-semibold text-gray-800 dark:text-white">
                            AI价格预测 - {symbol}
                        </span>
                    </div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                        {prediction.model_version}
                    </span>
                </div>

                {/* Prediction Box */}
                <div className="bg-white dark:bg-gray-800 rounded-lg p-5 shadow-sm mb-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">预测价格</p>
                            <div className="flex items-baseline">
                                <span className="text-4xl font-bold text-gray-900 dark:text-white">
                                    ${prediction.predicted_price.toFixed(2)}
                                </span>
                                <TrendIcon className={`w-7 h-7 ml-2 ${trendColor}`} />
                            </div>
                        </div>

                        {/* Confidence */}
                        <div className="text-right">
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">置信度</p>
                            <div>
                                <span className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                                    {prediction.confidence.toFixed(1)}%
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Metrics Grid */}
                {metrics && (
                    <div className="grid grid-cols-2 gap-3 mb-4">
                        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
                            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">平均误差率</p>
                            <p className="text-xl font-bold text-gray-900 dark:text-white">
                                {metrics.mape.toFixed(2)}%
                            </p>
                        </div>

                        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
                            <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">方向准确率</p>
                            <p className="text-xl font-bold text-gray-900 dark:text-white">
                                {metrics.direction_accuracy.toFixed(1)}%
                            </p>
                        </div>
                    </div>
                )}

                {/* Note */}
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                    <p className="text-xs text-yellow-800 dark:text-yellow-200">
                        💡 {prediction.note}
                    </p>
                </div>

                {/* Timestamp */}
                <div className="text-center mt-4">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        更新时间: {new Date(prediction.timestamp).toLocaleString('zh-CN')}
                    </p>
                </div>
            </div>
        </div>
    );
}
