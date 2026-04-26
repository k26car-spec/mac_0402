'use client';

import { useState, useEffect } from 'react';

interface StockAnalysis {
    股票代碼: string;
    綜合評分: number;
    評級: string;
    建議動作: string;
    目標價: number;
    停損價: number;
    '建議倉位(%)': number;
    風險等級: string;
    基本面分數: number;
    技術面分數: number;
    籌碼面分數: number;
}

interface BrokerData {
    stock_code: string;
    stock_name: string;
    buy_count: number;
    sell_count: number;
    net_count: number;
}

export default function StockSelectorPage() {
    const [loading, setLoading] = useState(false);
    const [analysisData, setAnalysisData] = useState<StockAnalysis[]>([]);
    const [brokerData, setBrokerData] = useState<BrokerData[]>([]);
    const [brokerLoading, setBrokerLoading] = useState(true);
    const [brokerError, setBrokerError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState('overview');
    const [lastUpdate, setLastUpdate] = useState<string>('');
    const [analysisMode, setAnalysisMode] = useState<'fast' | 'full'>('fast');
    const [marketAnalysis, setMarketAnalysis] = useState<any>(null);


    // 執行完整分析
    const runFullAnalysis = async () => {
        setLoading(true);
        try {
            // 步驟1: 獲取富邦新店買超股票
            console.log('步驟1: 獲取券商買超數據...');
            const brokerResponse = await fetch('http://localhost:8000/api/stock-selector/broker-flow/fubon-xindan/top-stocks?top_n=10&min_net_count=50');

            if (!brokerResponse.ok) {
                throw new Error(`獲取券商數據失敗: HTTP ${brokerResponse.status}`);
            }

            const brokerResult = await brokerResponse.json();
            console.log('券商數據原始返回:', brokerResult);

            // 提取股票代碼
            let stockCodes: string[] = [];
            if (brokerResult.success && brokerResult.data && Array.isArray(brokerResult.data)) {
                stockCodes = brokerResult.data
                    .map((item: any) => item.stock_code)
                    .filter((code: string) => code && typeof code === 'string');
            } else if (Array.isArray(brokerResult)) {
                stockCodes = brokerResult
                    .map((item: any) => item.stock_code)
                    .filter((code: string) => code && typeof code === 'string');
            }

            console.log('提取的股票代碼:', stockCodes);

            if (stockCodes.length === 0) {
                alert('未找到買超股票。可能原因：\n1. 今天不是交易日\n2. 券商數據尚未更新\n3. 沒有符合條件的買超股票');
                return;
            }

            console.log(`步驟2: 準備分析 ${stockCodes.length} 檔股票...（模式: ${analysisMode}）`);
            console.log('發送的請求數據:', { stock_codes: stockCodes, include_ai: false });

            // 步驟2: 分析這些股票 (根據模式選擇API)
            const apiEndpoint = analysisMode === 'full'
                ? 'http://localhost:8000/api/stock-selector/analyze/batch/full'
                : 'http://localhost:8000/api/stock-selector/analyze/batch';

            const analysisResponse = await fetch(apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    stock_codes: stockCodes,
                    include_ai: false  // 暫時不使用 AI 分析以加快速度
                })
            });

            if (analysisResponse.ok) {
                const data = await analysisResponse.json();
                console.log('分析結果:', data);

                // 處理返回的數據
                if (data.success && Array.isArray(data.data)) {
                    setAnalysisData(data.data);
                    // 保存市場分析（完整模式才有）
                    if (data.market_analysis) {
                        setMarketAnalysis(data.market_analysis);
                    }
                    alert(`✅ 分析完成！共分析 ${data.data.length} 檔股票`);
                } else if (Array.isArray(data)) {
                    setAnalysisData(data);
                    alert(`✅ 分析完成！共分析 ${data.length} 檔股票`);
                } else {
                    console.warn('分析數據格式不正確:', data);
                    alert('分析完成，但數據格式不正確。請查看控制台了解詳情。');
                }

                setLastUpdate(new Date().toLocaleString('zh-TW'));
            } else {
                let errorMessage = `HTTP ${analysisResponse.status}`;
                try {
                    const errorData = await analysisResponse.json();
                    console.error('API 錯誤詳情:', errorData);

                    // 更好的錯誤訊息處理
                    if (typeof errorData === 'string') {
                        errorMessage = errorData;
                    } else if (errorData.detail) {
                        errorMessage = typeof errorData.detail === 'string'
                            ? errorData.detail
                            : JSON.stringify(errorData.detail, null, 2);
                    } else if (errorData.message) {
                        errorMessage = errorData.message;
                    } else {
                        errorMessage = JSON.stringify(errorData, null, 2);
                    }
                } catch (e) {
                    const errorText = await analysisResponse.text();
                    console.error('API 錯誤文本:', errorText);
                    errorMessage = errorText || analysisResponse.statusText;
                }

                console.error('完整錯誤訊息:', errorMessage);
                alert(`分析失敗:\n\n${errorMessage}\n\n請查看控制台了解更多詳情`);
            }
        } catch (error) {
            console.error('分析失敗:', error);
            const errorMessage = error instanceof Error ? error.message : '未知錯誤';
            alert(`執行失敗: ${errorMessage}\n\n請確認:\n1. 後端服務已啟動\n2. 端口 8000 可訪問`);
        } finally {
            setLoading(false);
        }
    };

    // 獲取富邦新店買超
    const fetchBrokerData = async () => {
        setBrokerLoading(true);
        setBrokerError(null);
        try {
            const response = await fetch('http://localhost:8000/api/stock-selector/broker-flow/fubon-xindan/top-stocks?top_n=20');
            if (response.ok) {
                const data = await response.json();
                // 確保數據是數組
                if (Array.isArray(data)) {
                    setBrokerData(data);
                } else if (data && Array.isArray(data.data)) {
                    setBrokerData(data.data);
                } else {
                    console.warn('券商數據格式不正確:', data);
                    setBrokerData([]);
                    setBrokerError('數據格式不正確');
                }
            } else {
                console.error('獲取券商數據失敗:', response.status);
                setBrokerData([]);
                setBrokerError(`API 錯誤: ${response.status}`);
            }
        } catch (error) {
            console.error('獲取券商數據失敗:', error);
            setBrokerData([]);
            setBrokerError('無法連接到後端服務');
        } finally {
            setBrokerLoading(false);
        }
    };

    useEffect(() => {
        fetchBrokerData();
    }, []);

    const getGradeColor = (grade: string) => {
        const colors: Record<string, string> = {
            'A+': 'bg-green-500 text-white',
            'A': 'bg-green-400 text-white',
            'B+': 'bg-blue-400 text-white',
            'B': 'bg-blue-300 text-white',
            'C': 'bg-yellow-400 text-white',
            'D': 'bg-orange-400 text-white',
            'F': 'bg-red-500 text-white'
        };
        return colors[grade] || 'bg-gray-400 text-white';
    };

    const getActionColor = (action: string) => {
        const colors: Record<string, string> = {
            '強力買入': 'text-green-700 bg-green-50 border-green-200',
            '買入': 'text-green-600 bg-green-50 border-green-200',
            '持有': 'text-blue-600 bg-blue-50 border-blue-200',
            '觀望': 'text-yellow-600 bg-yellow-50 border-yellow-200',
            '減碼': 'text-orange-600 bg-orange-50 border-orange-200',
            '賣出': 'text-red-600 bg-red-50 border-red-200'
        };
        return colors[action] || 'text-gray-600 bg-gray-50 border-gray-200';
    };

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            {/* 標題區 */}
            <div className="max-w-7xl mx-auto mb-6">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">🎯 全自動選股決策引擎</h1>
                        <p className="text-gray-500 mt-2">
                            整合券商進出、多維度分析、量化評分的智能選股系統
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={runFullAnalysis}
                            disabled={loading}
                            className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-lg font-medium disabled:opacity-50 flex items-center gap-2"
                        >
                            {loading ? '🔄 分析中...' : '▶️ 執行選股分析'}
                        </button>
                        <button className="px-4 py-2 border border-gray-300 hover:bg-gray-50 rounded-lg font-medium flex items-center gap-2">
                            📥 匯出報告
                        </button>
                    </div>
                </div>

                {/* 分析模式切換 */}
                <div className="mt-4 p-4 bg-white rounded-lg shadow-sm border border-gray-200">
                    <div className="flex items-center gap-4">
                        <span className="text-sm font-medium text-gray-700">分析模式：</span>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setAnalysisMode('fast')}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${analysisMode === 'fast'
                                    ? 'bg-green-500 text-white'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                    }`}
                            >
                                ⚡ 快速模式
                            </button>
                            <button
                                onClick={() => setAnalysisMode('full')}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${analysisMode === 'full'
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                    }`}
                            >
                                📊 完整模式
                            </button>
                        </div>
                        <span className="text-xs text-gray-500">
                            {analysisMode === 'fast'
                                ? '（約 3-5 秒，基於券商籌碼快速評分）'
                                : '（約 15-30 秒，基本面30%+技術面25%+籌碼面25%+法人10%+市場10%）'}
                        </span>
                    </div>
                </div>
            </div>

            {/* 統計卡片 */}
            <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-600">分析股票數</span>
                        <span className="text-gray-400">📊</span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{analysisData.length}</div>
                    <p className="text-xs text-gray-500 mt-1">
                        最後更新: {lastUpdate || '尚未執行'}
                    </p>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-600">買入建議</span>
                        <span className="text-green-600">📈</span>
                    </div>
                    <div className="text-2xl font-bold text-green-600">
                        {analysisData.filter(s => s.建議動作.includes('買入')).length}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">強力買入 + 買入</p>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-600">平均評分</span>
                        <span className="text-gray-400">💰</span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900">
                        {analysisData.length > 0
                            ? (analysisData.reduce((sum, s) => sum + s.綜合評分, 0) / analysisData.length).toFixed(1)
                            : '0.0'
                        }
                    </div>
                    <p className="text-xs text-gray-500 mt-1">綜合評分 (0-100)</p>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-600">券商買超</span>
                        <span className="text-blue-600">✅</span>
                    </div>
                    <div className="text-2xl font-bold text-blue-600">{brokerData.length}</div>
                    <p className="text-xs text-gray-500 mt-1">富邦新店買超股票</p>
                </div>
            </div>

            {/* 市場維度分析（只在完整模式且有數據時顯示） */}
            {analysisMode === 'full' && marketAnalysis && (
                <div className="max-w-7xl mx-auto mb-6">
                    <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow-sm border border-blue-200 p-6">
                        <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                            📊 市場維度分析
                            <span className={`px-2 py-1 rounded text-sm font-medium ${marketAnalysis['市場評分'] >= 6 ? 'bg-green-100 text-green-700' :
                                marketAnalysis['市場評分'] >= 4 ? 'bg-yellow-100 text-yellow-700' :
                                    'bg-red-100 text-red-700'
                                }`}>
                                {marketAnalysis['市場評分']?.toFixed(1) || 0}/10
                            </span>
                        </h3>

                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
                            <div className="text-center">
                                <div className="text-2xl font-bold text-blue-600">
                                    {marketAnalysis['大盤趨勢']?.toFixed(1) || 0}
                                </div>
                                <div className="text-xs text-gray-500">大盤趨勢 /4</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-green-600">
                                    {marketAnalysis['成交量']?.toFixed(1) || 0}
                                </div>
                                <div className="text-xs text-gray-500">成交量 /3</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-purple-600">
                                    {marketAnalysis['外資期貨']?.toFixed(1) || 0}
                                </div>
                                <div className="text-xs text-gray-500">外資期貨 /2</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-orange-600">
                                    {marketAnalysis['VIX指數']?.toFixed(1) || 0}
                                </div>
                                <div className="text-xs text-gray-500">VIX指數 /1</div>
                            </div>
                            <div className="text-center bg-white rounded-lg p-2">
                                <div className="text-sm font-medium text-gray-700">
                                    {marketAnalysis['市場狀態']}
                                </div>
                                <div className="text-xs text-gray-500 mt-1">
                                    {marketAnalysis['操作建議']}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 標籤頁 */}
            <div className="max-w-7xl mx-auto">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                    {/* 標籤頁導航 */}
                    <div className="border-b border-gray-200">
                        <div className="flex gap-4 px-6">
                            <button
                                onClick={() => setActiveTab('overview')}
                                className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${activeTab === 'overview'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                分析總覽
                            </button>
                            <button
                                onClick={() => setActiveTab('broker')}
                                className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${activeTab === 'broker'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                券商進出
                            </button>
                            <button
                                onClick={() => setActiveTab('recommendations')}
                                className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${activeTab === 'recommendations'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                            >
                                投資建議
                            </button>
                        </div>
                    </div>

                    {/* 標籤頁內容 */}
                    <div className="p-6">
                        {/* 分析總覽 */}
                        {activeTab === 'overview' && (
                            <div>
                                {analysisData.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-12">
                                        <div className="text-6xl mb-4">📊</div>
                                        <h3 className="text-lg font-semibold mb-2">尚未執行分析</h3>
                                        <p className="text-gray-500 mb-4">點擊「執行選股分析」開始分析</p>
                                        <button
                                            onClick={runFullAnalysis}
                                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center gap-2"
                                        >
                                            ▶️ 開始分析
                                        </button>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {analysisData.map((stock) => (
                                            <div key={stock.股票代碼} className="border border-gray-200 rounded-lg p-6">
                                                <div className="flex justify-between items-start mb-4">
                                                    <div>
                                                        <h3 className="text-xl font-bold text-gray-900">
                                                            {stock.股票代碼} {(stock as any).股票名稱 && <span className="text-gray-600">{(stock as any).股票名稱}</span>}
                                                        </h3>
                                                        <div className="flex gap-4 mt-1">
                                                            {(stock as any).現價 > 0 && (
                                                                <span className="text-sm text-blue-600 font-medium">現價: ${(stock as any).現價.toLocaleString()}</span>
                                                            )}
                                                            <span className="text-sm text-gray-500">綜合評分: {stock.綜合評分.toFixed(2)}</span>
                                                        </div>
                                                    </div>
                                                    <div className="flex gap-2">
                                                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getGradeColor(stock.評級)}`}>
                                                            {stock.評級}
                                                        </span>
                                                        <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getActionColor(stock.建議動作)}`}>
                                                            {stock.建議動作}
                                                        </span>
                                                    </div>
                                                </div>

                                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                                    <div>
                                                        <p className="text-sm text-gray-500">目標價</p>
                                                        <p className="text-lg font-semibold text-green-600">${stock.目標價}</p>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm text-gray-500">停損價</p>
                                                        <p className="text-lg font-semibold text-red-600">${stock.停損價}</p>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm text-gray-500">建議倉位</p>
                                                        <p className="text-lg font-semibold">{stock['建議倉位(%)']}%</p>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm text-gray-500">風險等級</p>
                                                        <span className={`inline-block px-2 py-1 rounded text-sm font-medium ${stock.風險等級 === 'high' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'
                                                            }`}>
                                                            {stock.風險等級}
                                                        </span>
                                                    </div>
                                                </div>

                                                {/* 評分細項 */}
                                                <div className="space-y-2">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-sm text-gray-600">基本面</span>
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-32 bg-gray-200 rounded-full h-2">
                                                                <div
                                                                    className="bg-blue-600 h-2 rounded-full"
                                                                    style={{ width: `${stock.基本面分數}%` }}
                                                                />
                                                            </div>
                                                            <span className="text-sm font-medium w-12 text-right">{stock.基本面分數}</span>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-sm text-gray-600">技術面</span>
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-32 bg-gray-200 rounded-full h-2">
                                                                <div
                                                                    className="bg-green-600 h-2 rounded-full"
                                                                    style={{ width: `${stock.技術面分數}%` }}
                                                                />
                                                            </div>
                                                            <span className="text-sm font-medium w-12 text-right">{stock.技術面分數}</span>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-sm text-gray-600">籌碼面</span>
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-32 bg-gray-200 rounded-full h-2">
                                                                <div
                                                                    className="bg-purple-600 h-2 rounded-full"
                                                                    style={{ width: `${stock.籌碼面分數}%` }}
                                                                />
                                                            </div>
                                                            <span className="text-sm font-medium w-12 text-right">{stock.籌碼面分數}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* 券商進出 */}
                        {activeTab === 'broker' && (
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-2">富邦新店買超前20名</h3>
                                <p className="text-sm text-gray-500 mb-4">最新券商進出數據（自動使用當天日期）</p>

                                {brokerLoading ? (
                                    <div className="text-center text-gray-500 py-8">
                                        <div className="text-4xl mb-2">🔄</div>
                                        <p>載入中...</p>
                                    </div>
                                ) : brokerError ? (
                                    <div className="text-center text-red-500 py-8">
                                        <div className="text-4xl mb-2">⚠️</div>
                                        <p>{brokerError}</p>
                                        <button
                                            onClick={fetchBrokerData}
                                            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                                        >
                                            重試
                                        </button>
                                    </div>
                                ) : brokerData.length === 0 ? (
                                    <p className="text-center text-gray-500 py-8">暫無數據</p>
                                ) : (
                                    <div className="space-y-2">
                                        {brokerData.map((stock, index) => (
                                            <div
                                                key={stock.stock_code}
                                                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <span className="text-lg font-bold text-gray-400 w-8">{index + 1}</span>
                                                    <div>
                                                        <p className="font-semibold text-gray-900">{stock.stock_code}</p>
                                                        <p className="text-sm text-gray-500">{stock.stock_name}</p>
                                                    </div>
                                                </div>
                                                <div className="flex gap-6 text-sm">
                                                    <div className="text-right">
                                                        <p className="text-gray-500">買進</p>
                                                        <p className="font-semibold text-green-600">{stock.buy_count}</p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-gray-500">賣出</p>
                                                        <p className="font-semibold text-red-600">{stock.sell_count}</p>
                                                    </div>
                                                    <div className="text-right">
                                                        <p className="text-gray-500">淨流入</p>
                                                        <p className={`font-semibold ${stock.net_count > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                            {stock.net_count > 0 ? '+' : ''}{stock.net_count}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* 投資建議 */}
                        {activeTab === 'recommendations' && (
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-2">買入建議清單</h3>
                                <p className="text-sm text-gray-500 mb-4">根據多維度分析篩選出的買入建議</p>

                                {analysisData.filter(s => s.建議動作.includes('買入')).length === 0 ? (
                                    <p className="text-center text-gray-500 py-8">尚無買入建議，請先執行分析</p>
                                ) : (
                                    <div className="space-y-4">
                                        {analysisData
                                            .filter(s => s.建議動作.includes('買入'))
                                            .map((stock) => (
                                                <div
                                                    key={stock.股票代碼}
                                                    className="p-4 border border-green-200 rounded-lg bg-gradient-to-r from-green-50 to-blue-50"
                                                >
                                                    <div className="flex justify-between items-start mb-3">
                                                        <div>
                                                            <h3 className="text-lg font-bold text-gray-900">{stock.股票代碼}</h3>
                                                            <span className={`inline-block mt-1 px-3 py-1 rounded-full text-sm font-medium border ${getActionColor(stock.建議動作)}`}>
                                                                {stock.建議動作}
                                                            </span>
                                                        </div>
                                                        <div className="text-right">
                                                            <p className="text-2xl font-bold text-green-600">{stock.綜合評分.toFixed(1)}</p>
                                                            <p className="text-sm text-gray-500">綜合評分</p>
                                                        </div>
                                                    </div>
                                                    <div className="grid grid-cols-3 gap-4 text-sm">
                                                        <div>
                                                            <p className="text-gray-500">目標價</p>
                                                            <p className="font-semibold text-green-600">${stock.目標價}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-gray-500">停損價</p>
                                                            <p className="font-semibold text-red-600">${stock.停損價}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-gray-500">建議倉位</p>
                                                            <p className="font-semibold text-gray-900">{stock['建議倉位(%)']}%</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* 使用說明 */}
                <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-blue-900 mb-3">💡 使用說明</h3>
                    <div className="text-sm text-blue-800 space-y-2">
                        <p>• 點擊「執行選股分析」開始完整分析流程（約2-3分鐘）</p>
                        <p>• 系統會自動抓取富邦券商數據並執行多維度分析</p>
                        <p>• 綜合評分 = 基本面(30%) + 技術面(25%) + 籌碼面(25%) + 法人(10%) + 市場(10%)</p>
                        <p>• 評級：A+ (85-100) → A (75-84) → B+ (65-74) → B (55-64) → C (45-54) → D (35-44) → F (0-34)</p>
                        <p>• 建議僅供參考，請結合個人判斷和風險承受度</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
