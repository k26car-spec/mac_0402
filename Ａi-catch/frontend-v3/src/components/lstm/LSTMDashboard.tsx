'use client';

import { useState, useEffect } from 'react';
import LSTMPrediction from './LSTMPrediction';
import { Activity, TrendingUp } from 'lucide-react';

interface ModelInfo {
    symbol: string;
    r2_score: number;
    direction_accuracy: number;
    mape: number;
    rmse: number;
    trained_at: string;
    status: string;
}

export default function LSTMDashboard() {
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [selectedSymbol, setSelectedSymbol] = useState('2330');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchModels();
    }, []);

    const fetchModels = async () => {
        try {
            setLoading(true);
            const response = await fetch('http://127.0.0.1:8000/api/lstm/models');
            const data = await response.json();
            const availableModels = data.models.filter((m: ModelInfo) => m.status === 'available');
            setModels(availableModels);

            if (availableModels.length > 0 && !selectedSymbol) {
                setSelectedSymbol(availableModels[0].symbol);
            }
        } catch (err) {
            console.error('Failed to fetch models:', err);
        } finally {
            setLoading(false);
        }
    };

    const selectedModel = models.find(m => m.symbol === selectedSymbol);

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <Activity className="w-8 h-8 animate-spin text-blue-500" />
                <span className="ml-3 text-lg text-gray-600">加载模型中...</span>
            </div>
        );
    }

    return (
        <div className="container mx-auto p-6 space-y-6">
            {/* Header */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center">
                            <Activity className="w-8 h-8 mr-3 text-blue-600" />
                            LSTM股价预测系统
                        </h1>
                        <p className="text-gray-600 dark:text-gray-400 mt-2">
                            基于深度学习的智能价格预测
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-sm text-gray-500">可用模型</p>
                        <p className="text-2xl font-bold text-blue-600">{models.length}</p>
                    </div>
                </div>
            </div>

            {/* Tab Navigation */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-2">
                <div className="flex space-x-2">
                    {models.map(model => (
                        <button
                            key={model.symbol}
                            onClick={() => setSelectedSymbol(model.symbol)}
                            className={`
                flex-1 py-3 px-4 rounded-lg font-semibold transition-all
                ${selectedSymbol === model.symbol
                                    ? 'bg-blue-600 text-white shadow-lg'
                                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                                }
              `}
                        >
                            {model.symbol}
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Content Grid */}
            {selectedModel && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Prediction Card */}
                    <LSTMPrediction symbol={selectedSymbol} />

                    {/* Model Performance Card */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center">
                            <TrendingUp className="w-6 h-6 mr-2 text-green-600" />
                            模型性能指标
                        </h2>

                        <div className="grid grid-cols-2 gap-4 mb-6">
                            {/* MAPE */}
                            <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900 dark:to-blue-800 rounded-lg p-5">
                                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">平均误差率 (MAPE)</p>
                                <p className="text-3xl font-bold text-blue-700 dark:text-blue-300">
                                    {selectedModel.mape.toFixed(2)}%
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                                    {selectedModel.mape < 5 ? '⭐⭐⭐⭐⭐ 优秀' : selectedModel.mape < 10 ? '⭐⭐⭐⭐ 良好' : '⭐⭐⭐ 可用'}
                                </p>
                            </div>

                            {/* Direction Accuracy */}
                            <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900 dark:to-green-800 rounded-lg p-5">
                                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">方向准确率</p>
                                <p className="text-3xl font-bold text-green-700 dark:text-green-300">
                                    {(selectedModel.direction_accuracy * 100).toFixed(1)}%
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                                    {selectedModel.direction_accuracy > 0.6 ? '🎯 精准' : selectedModel.direction_accuracy > 0.5 ? '✅ 可用' : '⚠️ 需优化'}
                                </p>
                            </div>

                            {/* R² Score */}
                            <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900 dark:to-purple-800 rounded-lg p-5">
                                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">R² 分数</p>
                                <p className="text-3xl font-bold text-purple-700 dark:text-purple-300">
                                    {selectedModel.r2_score.toFixed(2)}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                                    拟合优度指标
                                </p>
                            </div>

                            {/* RMSE */}
                            <div className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900 dark:to-orange-800 rounded-lg p-5">
                                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">RMSE</p>
                                <p className="text-3xl font-bold text-orange-700 dark:text-orange-300">
                                    {selectedModel.rmse.toFixed(2)}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                                    均方根误差
                                </p>
                            </div>
                        </div>

                        {/* Model Info */}
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-5">
                            <h3 className="font-semibold text-gray-900 dark:text-white mb-3">模型信息</h3>
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-gray-600 dark:text-gray-400">训练时间:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {new Date(selectedModel.trained_at).toLocaleString('zh-CN')}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-600 dark:text-gray-400">模型状态:</span>
                                    <span className="font-medium text-green-600">✅ {selectedModel.status}</span>
                                </div>
                            </div>
                        </div>

                        {/* Usage Guidelines */}
                        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                            <h4 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">使用建议</h4>
                            <ul className="text-sm space-y-1 text-blue-800 dark:text-blue-300">
                                <li>• MAPE &lt; 5%: 价格预测优秀</li>
                                <li>• 方向准确率 &gt; 50%: 比随机预测好</li>
                                <li>• 建议结合其他指标综合判断</li>
                                <li>• 预测仅供参考，不构成投资建议</li>
                            </ul>
                        </div>
                    </div>
                </div>
            )}

            {/* No Models Message */}
            {models.length === 0 && !loading && (
                <div className="text-center py-12">
                    <Activity className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                    <p className="text-xl text-gray-600">暂无可用模型</p>
                    <p className="text-gray-500 mt-2">请先训练LSTM模型</p>
                </div>
            )}
        </div>
    );
}
