'use client';

import { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

// 模式顏色映射
const PATTERN_COLORS: { [key: string]: { bg: string; text: string; border: string } } = {
    'AGGRESSIVE_BUYING': { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-300' },
    'AGGRESSIVE_SELLING': { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-300' },
    'SUPPORT_TESTING': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-300' },
    'RESISTANCE_TESTING': { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-300' },
    'LIQUIDITY_DRYING': { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-300' },
    'FAKE_OUT': { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-300' },
    'NEUTRAL': { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-300' },
};

// 模式中文名稱
const PATTERN_NAMES: { [key: string]: string } = {
    'AGGRESSIVE_BUYING': '積極買盤攻擊',
    'AGGRESSIVE_SELLING': '積極賣盤攻擊',
    'SUPPORT_TESTING': '測試支撐',
    'RESISTANCE_TESTING': '測試阻力',
    'LIQUIDITY_DRYING': '流動性枯竭',
    'FAKE_OUT': '假突破',
    'NEUTRAL': '中性',
};

// 交易動作徽章
const ACTION_BADGES: { [key: string]: { bg: string; text: string } } = {
    'BUY': { bg: 'bg-green-600', text: '買入' },
    'STRONG_BUY': { bg: 'bg-green-700', text: '強烈買入' },
    'WEAK_BUY': { bg: 'bg-green-500', text: '小量買入' },
    'SELL': { bg: 'bg-red-600', text: '賣出' },
    'STRONG_SELL': { bg: 'bg-red-700', text: '強烈賣出' },
    'WEAK_SELL': { bg: 'bg-red-500', text: '減碼' },
    'HOLD': { bg: 'bg-gray-600', text: '持有觀望' },
    'NO_ACTION': { bg: 'bg-gray-500', text: '無動作' },
};

interface PatternDetection {
    pattern: number;
    pattern_name: string;
    confidence: number;
    strength: number;
    timestamp: string;
    trading_hint?: {
        action: string;
        description: string;
    };
    evidence?: Record<string, any>;
}

interface FeatureData {
    [key: string]: number;
}

interface SystemStatus {
    monitored_symbols: number;
    symbols: string[];
    timestamp: string;
}

export default function OrderFlowPage() {
    const [symbol, setSymbol] = useState('2330');
    const [inputSymbol, setInputSymbol] = useState('2330');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // 數據狀態
    const [patternResult, setPatternResult] = useState<any>(null);
    const [features, setFeatures] = useState<FeatureData | null>(null);
    const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
    const [patternTypes, setPatternTypes] = useState<any[]>([]);

    // 自動刷新
    const [autoRefresh, setAutoRefresh] = useState(false);

    // 獲取系統狀態
    const fetchSystemStatus = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/order-flow/status`);
            if (res.ok) {
                const data = await res.json();
                setSystemStatus(data);
            }
        } catch (e) {
            console.error('獲取系統狀態失敗:', e);
        }
    }, []);

    // 獲取模式類型
    const fetchPatternTypes = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/order-flow/patterns/types`);
            if (res.ok) {
                const data = await res.json();
                setPatternTypes(data.patterns || []);
            }
        } catch (e) {
            console.error('獲取模式類型失敗:', e);
        }
    }, []);

    // 獲取模式檢測結果
    const fetchPatterns = useCallback(async () => {
        if (!symbol) return;

        setLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/api/order-flow/patterns/${symbol}?include_features=true`);
            if (!res.ok) {
                throw new Error(`API 錯誤: ${res.status}`);
            }
            const data = await res.json();

            if (data.success) {
                setPatternResult(data);
                if (data.features) {
                    setFeatures(data.features);
                }
            } else {
                setError(data.error || '檢測失敗');
            }
        } catch (e: any) {
            setError(e.message || '請求失敗');
        } finally {
            setLoading(false);
        }
    }, [symbol]);

    // 模擬數據輸入（用於演示）
    const simulateData = async () => {
        setLoading(true);
        try {
            // 發送模擬報價
            for (let i = 0; i < 20; i++) {
                await fetch(`${API_BASE}/api/order-flow/quote`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        symbol,
                        price: 1000 + Math.random() * 10 - 5,
                        volume: Math.floor(Math.random() * 150) + 50,
                        timestamp: new Date().toISOString(),
                    }),
                });
            }

            // 發送模擬五檔
            await fetch(`${API_BASE}/api/order-flow/orderbook`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol,
                    bids: [
                        { price: 999, volume: Math.floor(Math.random() * 100) + 50 },
                        { price: 998, volume: Math.floor(Math.random() * 100) + 50 },
                        { price: 997, volume: Math.floor(Math.random() * 100) + 50 },
                        { price: 996, volume: Math.floor(Math.random() * 100) + 50 },
                        { price: 995, volume: Math.floor(Math.random() * 100) + 50 },
                    ],
                    asks: [
                        { price: 1001, volume: Math.floor(Math.random() * 100) + 50 },
                        { price: 1002, volume: Math.floor(Math.random() * 100) + 50 },
                        { price: 1003, volume: Math.floor(Math.random() * 100) + 50 },
                        { price: 1004, volume: Math.floor(Math.random() * 100) + 50 },
                        { price: 1005, volume: Math.floor(Math.random() * 100) + 50 },
                    ],
                    lastPrice: 1000,
                    timestamp: new Date().toISOString(),
                }),
            });

            // 獲取模式檢測
            await fetchPatterns();
        } catch (e) {
            console.error('模擬數據失敗:', e);
        } finally {
            setLoading(false);
        }
    };

    // 使用實時數據分析（一站式 API）
    const fetchRealtimeAnalysis = async () => {
        if (!symbol) return;

        setLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/api/order-flow/realtime/${symbol}`);
            if (!res.ok) {
                throw new Error(`API 錯誤: ${res.status}`);
            }
            const data = await res.json();

            if (data.success || data.primary_pattern) {
                setPatternResult(data);
                if (data.features) {
                    setFeatures(data.features);
                }
            } else {
                setError(data.error || '分析失敗');
            }
        } catch (e: any) {
            setError(e.message || '請求失敗');
        } finally {
            setLoading(false);
        }
    };

    // 初始化
    useEffect(() => {
        fetchSystemStatus();
        fetchPatternTypes();
    }, [fetchSystemStatus, fetchPatternTypes]);

    // 自動刷新
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(() => {
            fetchPatterns();
        }, 5000);

        return () => clearInterval(interval);
    }, [autoRefresh, fetchPatterns]);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        setSymbol(inputSymbol);
    };

    const getPatternKey = (pattern: number | string): string => {
        if (typeof pattern === 'number') {
            const keys = ['AGGRESSIVE_BUYING', 'AGGRESSIVE_SELLING', 'SUPPORT_TESTING',
                'RESISTANCE_TESTING', 'LIQUIDITY_DRYING', 'FAKE_OUT', 'NEUTRAL'];
            return keys[pattern] || 'NEUTRAL';
        }
        return pattern;
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-6">
            {/* 頁面標題 */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    📊 訂單流模式識別系統
                </h1>
                <p className="text-gray-600 mt-2">
                    替代傳統 LSTM 價格預測 · 6種市場微觀模式識別 · 實時決策支援
                </p>
            </div>

            {/* 系統狀態 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
                    <div className="text-gray-500 text-sm">系統狀態</div>
                    <div className="text-2xl font-bold text-green-600 mt-1">✅ 運行中</div>
                </div>
                <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
                    <div className="text-gray-500 text-sm">監控股票數</div>
                    <div className="text-2xl font-bold text-blue-600 mt-1">
                        {systemStatus?.monitored_symbols || 0}
                    </div>
                </div>
                <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
                    <div className="text-gray-500 text-sm">支援模式數</div>
                    <div className="text-2xl font-bold text-purple-600 mt-1">
                        {patternTypes.length || 7}
                    </div>
                </div>
                <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
                    <div className="text-gray-500 text-sm">當前時間</div>
                    <div className="text-lg font-mono text-gray-700 mt-1">
                        {new Date().toLocaleTimeString()}
                    </div>
                </div>
            </div>

            {/* 搜索欄 */}
            <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm mb-6">
                <form onSubmit={handleSearch} className="flex gap-4 items-center flex-wrap">
                    <div className="flex-1 min-w-[200px]">
                        <input
                            type="text"
                            value={inputSymbol}
                            onChange={(e) => setInputSymbol(e.target.value)}
                            placeholder="輸入股票代碼 (例: 2330)"
                            className="w-full bg-gray-100 border border-gray-300 rounded-lg px-4 py-2 text-gray-900 placeholder-gray-400 focus:outline-none focus:border-blue-500"
                        />
                    </div>
                    <button
                        type="submit"
                        className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                    >
                        搜索
                    </button>
                    <button
                        type="button"
                        onClick={simulateData}
                        disabled={loading}
                        className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                    >
                        {loading ? '處理中...' : '📥 模擬數據'}
                    </button>
                    <button
                        type="button"
                        onClick={fetchPatterns}
                        disabled={loading}
                        className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                    >
                        🔍 檢測模式
                    </button>
                    <button
                        type="button"
                        onClick={fetchRealtimeAnalysis}
                        disabled={loading}
                        className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors disabled:opacity-50"
                    >
                        🔴 實時分析
                    </button>
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={(e) => setAutoRefresh(e.target.checked)}
                            className="w-4 h-4 rounded"
                        />
                        <span className="text-gray-700">自動刷新</span>
                    </label>
                </form>
            </div>

            {/* 錯誤提示 */}
            {error && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 mb-6">
                    <p className="text-red-400">❌ {error}</p>
                </div>
            )}

            {/* 主要內容 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 左側：模式檢測結果 */}
                <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
                    <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                        🎯 模式檢測結果
                        <span className="text-sm text-gray-500 font-normal">({symbol})</span>
                    </h2>

                    {patternResult?.primary_pattern ? (
                        <div className="space-y-4">
                            {/* 主要模式 */}
                            <div className={`p-4 rounded-xl border ${PATTERN_COLORS[getPatternKey(patternResult.primary_pattern.pattern)]?.bg || 'bg-gray-500/20'
                                } ${PATTERN_COLORS[getPatternKey(patternResult.primary_pattern.pattern)]?.border || 'border-gray-500/50'}`}>
                                <div className="flex justify-between items-start mb-3">
                                    <div>
                                        <div className={`text-xl font-bold ${PATTERN_COLORS[getPatternKey(patternResult.primary_pattern.pattern)]?.text || 'text-gray-600'
                                            }`}>
                                            {patternResult.primary_pattern.pattern_name}
                                        </div>
                                        <div className="text-gray-500 text-sm mt-1">
                                            {patternResult.primary_pattern.trading_hint?.description}
                                        </div>
                                    </div>
                                    {patternResult.primary_pattern.trading_hint?.action && (
                                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${ACTION_BADGES[patternResult.primary_pattern.trading_hint.action]?.bg || 'bg-gray-600'
                                            }`}>
                                            {ACTION_BADGES[patternResult.primary_pattern.trading_hint.action]?.text || ''}
                                        </span>
                                    )}
                                </div>

                                {/* 信心度和強度 */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <div className="text-gray-500 text-sm mb-1">信心度</div>
                                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all"
                                                style={{ width: `${(patternResult.primary_pattern.confidence || 0) * 100}%` }}
                                            />
                                        </div>
                                        <div className="text-right text-sm text-gray-600 mt-1">
                                            {((patternResult.primary_pattern.confidence || 0) * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-gray-500 text-sm mb-1">強度</div>
                                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all"
                                                style={{ width: `${(patternResult.primary_pattern.strength || 0) * 100}%` }}
                                            />
                                        </div>
                                        <div className="text-right text-sm text-gray-600 mt-1">
                                            {((patternResult.primary_pattern.strength || 0) * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                </div>

                                {/* 證據 */}
                                {patternResult.primary_pattern.evidence && Object.keys(patternResult.primary_pattern.evidence).length > 0 && (
                                    <div className="mt-4 pt-4 border-t border-gray-300/50">
                                        <div className="text-gray-500 text-sm mb-2">證據</div>
                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            {Object.entries(patternResult.primary_pattern.evidence).map(([key, value]) => (
                                                <div key={key} className="flex justify-between">
                                                    <span className="text-gray-600">{key}:</span>
                                                    <span className="text-white font-mono">
                                                        {typeof value === 'number' ? value.toFixed(4) : String(value)}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* 統計資訊 */}
                            {patternResult.statistics && (
                                <div className="bg-slate-700/30 rounded-xl p-4">
                                    <div className="text-gray-500 text-sm mb-2">統計資訊</div>
                                    <div className="grid grid-cols-2 gap-2 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">總檢測次數:</span>
                                            <span className="text-white">{patternResult.statistics.total_detections || 0}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-gray-600">平均信心度:</span>
                                            <span className="text-white">
                                                {((patternResult.statistics.avg_confidence || 0) * 100).toFixed(1)}%
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="text-center py-12 text-gray-500">
                            <div className="text-4xl mb-3">📈</div>
                            <p>點擊「模擬數據」或「檢測模式」開始分析</p>
                        </div>
                    )}
                </div>

                {/* 右側：特徵向量 */}
                <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
                    <h2 className="text-xl font-bold mb-4">📊 特徵向量 (14維)</h2>

                    {features && Object.keys(features).length > 0 ? (
                        <div className="space-y-3">
                            {Object.entries(features).map(([key, value]) => (
                                <div key={key} className="flex items-center gap-3">
                                    <div className="w-40 text-sm text-gray-400 truncate" title={key}>
                                        {key}
                                    </div>
                                    <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full transition-all ${value > 0 ? 'bg-gradient-to-r from-green-500 to-emerald-400' :
                                                value < 0 ? 'bg-gradient-to-r from-red-500 to-rose-400' :
                                                    'bg-gray-500'
                                                }`}
                                            style={{
                                                width: `${Math.min(Math.abs(value) * 100, 100)}%`,
                                                marginLeft: value < 0 ? 'auto' : 0,
                                            }}
                                        />
                                    </div>
                                    <div className="w-20 text-right font-mono text-sm text-gray-700">
                                        {value.toFixed(4)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12 text-gray-500">
                            <div className="text-4xl mb-3">📉</div>
                            <p>無特徵數據</p>
                        </div>
                    )}
                </div>
            </div>

            {/* 模式說明 */}
            <div className="mt-6 bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
                <h2 className="text-xl font-bold mb-4">📖 支援的市場模式</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {patternTypes.map((pattern) => (
                        <div
                            key={pattern.id}
                            className={`p-4 rounded-xl border ${PATTERN_COLORS[getPatternKey(pattern.id)]?.bg || 'bg-gray-500/20'
                                } ${PATTERN_COLORS[getPatternKey(pattern.id)]?.border || 'border-gray-500/50'}`}
                        >
                            <div className={`font-bold ${PATTERN_COLORS[getPatternKey(pattern.id)]?.text || 'text-gray-600'
                                }`}>
                                {pattern.name}
                            </div>
                            <div className="text-gray-500 text-sm mt-1">
                                {pattern.trading_hint?.description || ''}
                            </div>
                            {pattern.trading_hint?.action && (
                                <span className={`inline-block mt-2 px-2 py-0.5 rounded text-xs ${ACTION_BADGES[pattern.trading_hint.action]?.bg || 'bg-gray-600'
                                    }`}>
                                    {ACTION_BADGES[pattern.trading_hint.action]?.text || pattern.trading_hint.action}
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
