'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
    TrendingUp,
    TrendingDown,
    Briefcase,
    Plus,
    X,
    History,
    BarChart3,
    Target,
    AlertTriangle,
    CheckCircle2,
    Bot,
    RefreshCw,
    Trash2,
    DollarSign,
    HelpCircle,
    ChevronDown,
    ChevronUp,
    Info,
    Crosshair,
    ExternalLink,
    Download
} from 'lucide-react';
import { cn } from '@/lib/utils';

// API Base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// 類型定義
interface Position {
    id: number;
    symbol: string;
    stock_name: string | null;
    entry_date: string;
    entry_price: number;
    entry_quantity: number;
    analysis_source: string;
    analysis_confidence: number | null;
    stop_loss_price: number | null;
    target_price: number | null;
    current_price: number | null;
    unrealized_profit: number | null;
    unrealized_profit_percent: number | null;
    exit_date: string | null;
    exit_price: number | null;
    exit_reason: string | null;
    realized_profit: number | null;
    realized_profit_percent: number | null;
    status: string;
    is_simulated: boolean;
    is_short: boolean;
    notes: string | null;
    created_at: string;
}

interface TradeRecord {
    id: number;
    portfolio_id: number | null;
    symbol: string;
    stock_name: string | null;
    trade_type: string;
    trade_date: string;
    price: number;
    quantity: number;
    total_amount: number;
    analysis_source: string;
    profit: number | null;
    profit_percent: number | null;
    is_simulated: boolean;
}

interface AccuracyData {
    analysis_source: string;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    net_profit: number;
    avg_profit_percent: number | null;
    avg_loss_percent: number | null;
}

interface PortfolioSummary {
    open_positions_count: number;
    closed_positions_count: number;
    total_unrealized_profit: number;
    total_realized_profit: number;
    total_profit: number;
    win_rate: number;
    wins: number;
    losses: number;
}

// 來源名稱對照
const SOURCE_NAMES: Record<string, string> = {
    main_force: '主力偵測',
    big_order: '大單分析',
    lstm_prediction: 'LSTM 預測',
    expert_signal: '專家信號',
    premarket: '盤前分析',
    manual: '手動操作',
    ai_simulation: 'AI 模擬',
    day_trading: '當沖戰情室',
};

// 狀態配置
const STATUS_CONFIG: Record<string, { bg: string; text: string; border: string; label: string }> = {
    open: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', label: '持有中' },
    closed: { bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200', label: '已賣出' },
    stopped: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', label: '停損' },
    target_hit: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', label: '達標' },
    trailing_stopped: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', label: '移動停利' },
    forced_close: { bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-300', label: '強制平倉' },
};

export default function PortfolioPage() {
    // 狀態
    const [activeTab, setActiveTab] = useState<'positions' | 'trades' | 'accuracy'>('positions');
    const [positions, setPositions] = useState<Position[]>([]);
    const [trades, setTrades] = useState<TradeRecord[]>([]);
    const [accuracy, setAccuracy] = useState<AccuracyData[]>([]);
    const [summary, setSummary] = useState<PortfolioSummary | null>(null);
    const [capitalStatus, setCapitalStatus] = useState<any>(null); // ⭐ 新增資金狀態
    const [loading, setLoading] = useState(true);

    // 篩選狀態
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [sourceFilter, setSourceFilter] = useState<string>('all');
    const [showSimulated, setShowSimulated] = useState(true);

    // 說明面板
    const [showHelp, setShowHelp] = useState(false);

    // 背景更新狀態（不會導致整個畫面消失）
    const [isRefreshing, setIsRefreshing] = useState(false);

    // 新增持倉對話框
    const [showAddForm, setShowAddForm] = useState(false);
    const [showDepositForm, setShowDepositForm] = useState(false);
    const [showWithdrawForm, setShowWithdrawForm] = useState(false);
    const [depositAmount, setDepositAmount] = useState('');
    const [withdrawAmount, setWithdrawAmount] = useState('');
    const [newPosition, setNewPosition] = useState({
        symbol: '',
        stock_name: '',
        entry_price: '',
        entry_quantity: '1000',
        analysis_source: 'manual',
        stop_loss_price: '',
        target_price: '',
        notes: '',
    });

    // 更新即時價格
    const updatePrices = useCallback(async () => {
        try {
            console.log('🔄 更新即時價格...');
            const response = await fetch(`${API_BASE}/api/portfolio/positions/update-prices`, {
                method: 'POST'
            });
            if (response.ok) {
                const result = await response.json();
                console.log(`✅ 已更新 ${result.updated} 檔股票價格`);
                return true;
            }
        } catch (err) {
            console.error('更新價格失敗:', err);
        }
        return false;
    }, []);

    // 載入數據（背景更新，不會導致整個畫面消失）
    const fetchData = useCallback(async (isInitialLoad = false) => {
        // 只有首次載入時才顯示全屏 loading
        if (isInitialLoad) {
            setLoading(true);
        } else {
            setIsRefreshing(true);
        }

        try {
            // ✅ 先載入持倉資料
            const [positionsRes, tradesRes, accuracyRes, summaryRes, capitalRes] = await Promise.all([
                fetch(`${API_BASE}/api/portfolio/positions`),
                fetch(`${API_BASE}/api/portfolio/trades?limit=50`),
                fetch(`${API_BASE}/api/portfolio/accuracy?days=30`),
                fetch(`${API_BASE}/api/portfolio/summary`),
                fetch(`${API_BASE}/api/portfolio/capital-status`), // ⭐ 取回資金狀態
            ]);

            if (positionsRes.ok) setPositions(await positionsRes.json());
            if (tradesRes.ok) setTrades(await tradesRes.json());
            if (accuracyRes.ok) setAccuracy(await accuracyRes.json());
            if (summaryRes.ok) setSummary(await summaryRes.json());
            if (capitalRes.ok) setCapitalStatus(await capitalRes.json());

            // ✅ 更新即時價格在背景執行，不阻塞頁面顯示
            updatePrices().then(() => {
                // 價格更新完後再刷新一次位置數據
                fetch(`${API_BASE}/api/portfolio/positions`)
                    .then(r => r.ok ? r.json() : null)
                    .then(data => { if (data) setPositions(data); })
                    .catch(() => { });
            }).catch(() => { });

        } catch (err) {
            console.error('載入數據失敗:', err);
        } finally {
            setLoading(false);
            setIsRefreshing(false);
        }
    }, [updatePrices]);


    useEffect(() => {
        // 首次載入
        fetchData(true);
        // 每 30 秒背景更新一次
        const interval = setInterval(() => fetchData(false), 30000);
        return () => clearInterval(interval);
    }, [fetchData]);

    // 新增持倉
    const handleAddPosition = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/portfolio/positions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol: newPosition.symbol,
                    stock_name: newPosition.stock_name || null,
                    entry_date: new Date().toISOString(),
                    entry_price: parseFloat(newPosition.entry_price),
                    entry_quantity: parseInt(newPosition.entry_quantity),
                    analysis_source: newPosition.analysis_source,
                    stop_loss_price: newPosition.stop_loss_price ? parseFloat(newPosition.stop_loss_price) : null,
                    target_price: newPosition.target_price ? parseFloat(newPosition.target_price) : null,
                    notes: newPosition.notes || null,
                    is_simulated: false,
                }),
            });

            if (response.ok) {
                setShowAddForm(false);
                setNewPosition({
                    symbol: '',
                    stock_name: '',
                    entry_price: '',
                    entry_quantity: '1000',
                    analysis_source: 'manual',
                    stop_loss_price: '',
                    target_price: '',
                    notes: '',
                });
                fetchData();
            }
        } catch (err) {
            console.error('新增持倉失敗:', err);
        }
    };

    // 📊 匯出對帳單
    const handleExportCSV = () => {
        if (!capitalStatus) {
            alert('❌ 數據尚未載入');
            return;
        }

        const totalCap = capitalStatus.configured_capital || 0;
        const availableCap = capitalStatus.available_capital || 0;
        const netPnL = availableCap - totalCap; // 這裡即為可用本金餘額扣掉本金

        let csvContent = 'data:text/csv;charset=utf-8,\uFEFF';
        csvContent += '模擬投資帳戶對帳單 (Export Report)\n';
        csvContent += `匯出日期,${new Date().toLocaleString()}\n\n`;

        csvContent += '【資金總覽】\n';
        csvContent += `原始總投資本金,$${totalCap.toLocaleString()}\n`;
        csvContent += `可用本金餘額,$${availableCap.toLocaleString()}\n`;
        csvContent += `模擬損益淨額 (可用-本金),$${netPnL.toLocaleString()}\n`;
        csvContent += `總權益數 (淨值),$${capitalStatus.current_equity.toLocaleString()}\n\n`;

        csvContent += '【目前持倉詳情】\n';
        csvContent += '股票代號,股票名稱,進場日期,進場價格,數量,目前價格,未實現損益,分析來源\n';
        
        positions.filter(p => p.status === 'open').forEach(p => {
            const pnl = (p.current_price - p.entry_price) * p.entry_quantity;
            csvContent += `${p.symbol},${p.stock_name || '-'},${p.entry_date},${p.entry_price},${p.entry_quantity},${p.current_price || '-'},${pnl.toFixed(0)},${p.analysis_source}\n`;
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `Portfolio_Report_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // 💰 儲值功能
    const handleDeposit = async () => {
        const amount = parseFloat(depositAmount);
        if (isNaN(amount) || amount <= 0) {
            alert('❌ 金額無效');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/portfolio/capital/deposit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount }),
            });

            if (response.ok) {
                alert(`✅ 成功儲值 $${amount.toLocaleString('zh-TW')}！可用本金已更新。`);
                setShowDepositForm(false);
                setDepositAmount('');
                fetchData(false);
            } else {
                alert('❌ 儲值失敗，請稍後再試');
            }
        } catch (err) {
            console.error('儲值失敗:', err);
            alert('❌ 儲值發生錯誤');
        }
    };

    // 💸 提款功能 (匯出本金)
    const handleWithdraw = async () => {
        const amount = parseFloat(withdrawAmount);
        if (isNaN(amount) || amount <= 0) {
            alert('❌ 金額無效');
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/api/portfolio/capital/withdraw`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount }),
            });

            if (response.ok) {
                alert(`✅ 成功匯出 (減少) 本金 $${amount.toLocaleString('zh-TW')}！總本金已扣除。`);
                setShowWithdrawForm(false);
                setWithdrawAmount('');
                fetchData(false);
            } else {
                alert('❌ 提款失敗，請稍後再試');
            }
        } catch (err) {
            console.error('提款失敗:', err);
            alert('❌ 提款發生錯誤');
        }
    };

    // 結束持倉
    const handleClosePosition = async (position: Position) => {
        const exitPrice = prompt(`請輸入賣出價格 (進場價: ${position.entry_price})`);
        if (!exitPrice) return;

        try {
            const response = await fetch(`${API_BASE}/api/portfolio/positions/${position.id}/close`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    exit_date: new Date().toISOString(),
                    exit_price: parseFloat(exitPrice),
                    exit_reason: '手動賣出',
                }),
            });

            if (response.ok) fetchData();
        } catch (err) {
            console.error('賣出失敗:', err);
        }
    };

    // 刪除持倉
    const handleDeletePosition = async (position: Position) => {
        if (!confirm(`確定要刪除 ${position.symbol} 的持倉紀錄嗎？`)) return;

        try {
            await fetch(`${API_BASE}/api/portfolio/positions/${position.id}`, { method: 'DELETE' });
            fetchData();
        } catch (err) {
            console.error('刪除失敗:', err);
        }
    };

    // AI 模擬
    const handleAutoSimulate = async (source: string) => {
        try {
            const response = await fetch(`${API_BASE}/api/portfolio/auto-simulate?source=${source}&days=7`, {
                method: 'POST',
            });

            if (response.ok) {
                const result = await response.json();
                alert(`模擬完成：${result.message}`);
                fetchData();
            }
        } catch (err) {
            console.error('模擬失敗:', err);
        }
    };

    // 篩選持倉
    const filteredPositions = positions.filter(p => {
        if (statusFilter !== 'all' && p.status !== statusFilter) return false;
        if (sourceFilter !== 'all' && p.analysis_source !== sourceFilter) return false;
        if (!showSimulated && p.is_simulated) return false;
        return true;
    });

    // 格式化數字（預設不顯示小數點）
    const formatNumber = (num: number | null | undefined, decimals = 0): string => {
        if (num === null || num === undefined) return '-';
        return num.toLocaleString('zh-TW', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    };

    // 格式化百分比（保留 1 位小數）
    const formatPercent = (num: number | null | undefined): string => {
        if (num === null || num === undefined) return '-';
        return num.toFixed(1) + '%';
    };

    // 格式化日期
    const formatDate = (dateStr: string): string => {
        return new Date(dateStr).toLocaleString('zh-TW', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="space-y-6">
            {/* 頁面標題 */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Briefcase className="w-8 h-8 text-blue-600" />
                        持有股票與交易紀錄
                    </h1>
                    <p className="text-gray-600 mt-2">追蹤您的持倉、交易歷史和分析準確性</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={async () => {
                            setIsRefreshing(true);
                            await updatePrices();
                            await fetchData(false);
                        }}
                        className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
                        title="即時更新所有持倉的現價"
                    >
                        <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
                        更新價格
                    </button>
                    <button
                        onClick={async () => {
                            if (!confirm('確定要執行自動平倉檢查嗎？\n\n將檢查所有模擬交易持倉，達到目標價或停損價時自動平倉。')) return;

                            setIsRefreshing(true);
                            try {
                                const response = await fetch(`${API_BASE}/api/portfolio/auto-close?simulated_only=true`, {
                                    method: 'POST'
                                });

                                if (response.ok) {
                                    const result = await response.json();

                                    if (result.closed_count > 0) {
                                        const details = result.closed_details.map((d: any) =>
                                            `${d.symbol} ${d.stock_name}: ${d.profit >= 0 ? '+' : ''}${d.profit.toFixed(0)} (${d.reason})`
                                        ).join('\n');

                                        alert(`✅ ${result.message}\n\n平倉詳情：\n${details}`);
                                    } else {
                                        alert(`ℹ️ ${result.message}\n\n目前沒有需要平倉的持倉。`);
                                    }

                                    await fetchData(false);
                                } else {
                                    alert('❌ 自動平倉失敗');
                                }
                            } catch (err) {
                                console.error('自動平倉失敗:', err);
                                alert('❌ 自動平倉失敗');
                            } finally {
                                setIsRefreshing(false);
                            }
                        }}
                        className="flex items-center gap-2 px-3 py-2 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition-colors"
                        title="檢查並自動平倉達標的模擬交易"
                    >
                        <Target className="w-4 h-4" />
                        自動平倉
                    </button>
                    <button
                        onClick={() => setShowHelp(!showHelp)}
                        className={cn(
                            "flex items-center gap-2 px-3 py-2 rounded-lg font-medium transition-colors border",
                            showHelp
                                ? "bg-blue-50 text-blue-700 border-blue-200"
                                : "bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100"
                        )}
                    >
                        <HelpCircle className="w-5 h-5" />
                        使用說明
                        {showHelp ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                    <a
                        href="http://localhost:5173"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-amber-600 transition-colors shadow-sm"
                    >
                        <Crosshair className="w-5 h-5" />
                        當沖分析
                        <ExternalLink className="w-4 h-4" />
                    </a>
                    <button
                        onClick={handleExportCSV}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg font-medium transition-colors"
                        title="匯出資金與持倉對帳單 (CSV格式)"
                    >
                        <Download className="w-5 h-5" />
                        匯出對帳單
                    </button>
                    <button
                        onClick={() => setShowWithdrawForm(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-400 to-red-500 text-white rounded-lg font-medium hover:from-orange-500 hover:to-red-600 transition-colors shadow-sm"
                        title="將投入的模擬本金匯出 (減資)"
                    >
                        <DollarSign className="w-5 h-5" />
                        資金提款
                    </button>
                    <button
                        onClick={() => setShowDepositForm(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-lg font-medium hover:from-emerald-600 hover:to-green-700 transition-colors shadow-sm"
                        title="注入模擬交易可用本金"
                    >
                        <DollarSign className="w-5 h-5" />
                        資金儲值
                    </button>
                    <button
                        onClick={() => setShowAddForm(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                    >
                        <Plus className="w-5 h-5" />
                        新增持倉
                    </button>
                </div>
            </div>


            {/* 使用說明面板 */}
            {showHelp && (
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-200 p-6">
                    <div className="flex items-start gap-4">
                        <div className="p-2 bg-blue-100 rounded-lg">
                            <Info className="w-6 h-6 text-blue-600" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-bold text-gray-900 text-lg mb-4">📊 持有股票與交易紀錄系統說明</h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {/* 持倉管理 */}
                                <div className="space-y-2">
                                    <h4 className="font-semibold text-gray-800 flex items-center gap-2">
                                        <Briefcase className="w-4 h-4 text-blue-600" />
                                        持倉管理
                                    </h4>
                                    <ul className="text-sm text-gray-600 space-y-1">
                                        <li>• <b>新增持倉</b>：點擊右上角藍色按鈕</li>
                                        <li>• <b>賣出</b>：點擊「$」圖示輸入賣出價格</li>
                                        <li>• <b>刪除</b>：點擊垃圾桶圖示</li>
                                        <li>• <b>篩選</b>：使用上方下拉選單</li>
                                    </ul>
                                </div>

                                {/* 狀態說明 */}
                                <div className="space-y-2">
                                    <h4 className="font-semibold text-gray-800 flex items-center gap-2">
                                        <Target className="w-4 h-4 text-purple-600" />
                                        狀態說明
                                    </h4>
                                    <ul className="text-sm text-gray-600 space-y-1">
                                        <li>• <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">持有中</span> 尚未賣出</li>
                                        <li>• <span className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">已賣出</span> 手動結束</li>
                                        <li>• <span className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs">停損</span> 觸及停損價</li>
                                        <li>• <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs">達標</span> 達到目標價</li>
                                    </ul>
                                </div>

                                {/* AI 功能 */}
                                <div className="space-y-2">
                                    <h4 className="font-semibold text-gray-800 flex items-center gap-2">
                                        <Bot className="w-4 h-4 text-cyan-600" />
                                        AI 自動化功能
                                    </h4>
                                    <ul className="text-sm text-gray-600 space-y-1">
                                        <li>• <b>模擬主力</b>：模擬主力偵測的信號</li>
                                        <li>• <b>模擬 LSTM</b>：模擬 AI 預測的信號</li>
                                        <li>• <b>自動平倉</b>：達到目標價或停損價自動平倉</li>
                                        <li>• <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs">模擬</span> 標籤表示非真實交易</li>
                                        <li>• 高品質信號 (≥75%) 會自動建倉</li>
                                    </ul>
                                </div>
                            </div>

                            {/* 顏色說明 */}
                            <div className="mt-4 pt-4 border-t border-blue-200">
                                <div className="flex flex-wrap items-center gap-4 text-sm">
                                    <span className="text-gray-600">顏色說明：</span>
                                    <span className="text-red-600 font-medium">紅色 = 獲利/上漲</span>
                                    <span className="text-green-600 font-medium">綠色 = 虧損/下跌</span>
                                    <span className="text-gray-400">|</span>
                                    <span className="text-gray-600">數據每 60 秒自動更新</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 總結卡片 */}
            {summary && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    <SummaryCard
                        title="總投資本金"
                        value={formatNumber(capitalStatus?.configured_capital || 0)}
                        prefix="$"
                        icon={<DollarSign className="w-5 h-5" />}
                        color="purple"
                    />
                    <SummaryCard
                        title="可用本金餘額"
                        value={formatNumber(capitalStatus?.available_capital || 0)}
                        prefix="$"
                        icon={<DollarSign className="w-5 h-5" />}
                        color={capitalStatus?.available_capital >= 0 ? "emerald" : "red"}
                    />
                    <SummaryCard
                        title="總權益數 (淨值)"
                        value={formatNumber(capitalStatus?.current_equity || 0)}
                        prefix="$"
                        icon={<TrendingUp className="w-5 h-5" />}
                        color={capitalStatus?.current_equity >= (capitalStatus?.configured_capital || 0) ? "red" : "green"}
                    />
                    <SummaryCard
                        title="總勝率"
                        value={formatPercent(summary.win_rate)}
                        icon={<Target className="w-5 h-5" />}
                        color="purple"
                    />
                    <SummaryCard
                        title="目前持股成本"
                        value={formatNumber(capitalStatus?.open_cost || 0)}
                        prefix="$"
                        icon={<Briefcase className="w-5 h-5" />}
                        color="orange"
                    />
                    <SummaryCard
                        title="持倉數量"
                        value={summary.open_positions_count}
                        icon={<Briefcase className="w-5 h-5" />}
                        color="blue"
                    />
                    <SummaryCard
                        title="未實現損益"
                        value={formatNumber(summary.total_unrealized_profit)}
                        prefix={summary.total_unrealized_profit >= 0 ? '+' : ''}
                        icon={<DollarSign className="w-5 h-5" />}
                        color={summary.total_unrealized_profit >= 0 ? 'red' : 'green'}
                    />
                    <SummaryCard
                        title="已實現損益"
                        value={formatNumber(summary.total_realized_profit)}
                        prefix={summary.total_realized_profit >= 0 ? '+' : ''}
                        icon={<CheckCircle2 className="w-5 h-5" />}
                        color={summary.total_realized_profit >= 0 ? 'red' : 'green'}
                    />
                </div>
            )}

            {/* 分頁標籤 */}
            <div className="flex items-center gap-2 bg-white rounded-lg shadow-sm border border-gray-200 p-1.5">
                {[
                    { key: 'positions', label: '持倉管理', icon: <Briefcase className="w-4 h-4" /> },
                    { key: 'trades', label: '交易紀錄', icon: <History className="w-4 h-4" /> },
                    { key: 'accuracy', label: '準確性分析', icon: <BarChart3 className="w-4 h-4" /> },
                ].map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key as any)}
                        className={cn(
                            "flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all",
                            activeTab === tab.key
                                ? 'bg-blue-600 text-white'
                                : 'text-gray-600 hover:bg-gray-100'
                        )}
                    >
                        {tab.icon}
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* 持倉管理 */}
            {activeTab === 'positions' && (
                <div className="space-y-4">
                    {/* 工具列 */}
                    <div className="flex flex-wrap items-center gap-3 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        >
                            <option value="all">所有狀態</option>
                            <option value="open">持有中</option>
                            <option value="closed">已賣出</option>
                            <option value="stopped">停損</option>
                            <option value="target_hit">達標</option>
                            <option value="trailing_stopped">移動停利</option>
                            <option value="forced_close">強制平倉</option>
                        </select>

                        <select
                            value={sourceFilter}
                            onChange={(e) => setSourceFilter(e.target.value)}
                            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        >
                            <option value="all">所有來源</option>
                            {Object.entries(SOURCE_NAMES).map(([key, name]) => (
                                <option key={key} value={key}>{name}</option>
                            ))}
                        </select>

                        <label className="flex items-center gap-2 text-sm text-gray-600">
                            <input
                                type="checkbox"
                                checked={showSimulated}
                                onChange={(e) => setShowSimulated(e.target.checked)}
                                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            顯示模擬交易
                        </label>

                        <div className="ml-auto flex items-center gap-2">
                            <button
                                onClick={() => handleAutoSimulate('main_force')}
                                className="flex items-center gap-1.5 px-3 py-2 text-sm text-purple-700 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors"
                            >
                                <Bot className="w-4 h-4" />
                                模擬主力
                            </button>
                            <button
                                onClick={() => handleAutoSimulate('lstm_prediction')}
                                className="flex items-center gap-1.5 px-3 py-2 text-sm text-cyan-700 bg-cyan-50 border border-cyan-200 rounded-lg hover:bg-cyan-100 transition-colors"
                            >
                                <Bot className="w-4 h-4" />
                                模擬 LSTM
                            </button>
                            <button
                                onClick={() => fetchData(false)}
                                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            >
                                <RefreshCw className={cn("w-5 h-5", isRefreshing && "animate-spin")} />
                            </button>
                        </div>
                    </div>

                    {/* 持股倉 - 持有中 */}
                    <PositionSection
                        title="💼 持股倉"
                        subtitle="目前持有中的股票"
                        positions={filteredPositions.filter(p => p.status === 'open')}
                        headerBg="bg-blue-50"
                        headerBorder="border-blue-200"
                        isRefreshing={isRefreshing}
                        loading={loading}
                        onClose={handleClosePosition}
                        onDelete={handleDeletePosition}
                    />

                    {/* 達標倉 - 獲利出場 */}
                    <PositionSection
                        title="🎯 達標倉"
                        subtitle="達到目標價獲利出場"
                        positions={filteredPositions.filter(p => p.status === 'target_hit')}
                        headerBg="bg-red-50"
                        headerBorder="border-red-200"
                        isRefreshing={false}
                        loading={false}
                        onClose={handleClosePosition}
                        onDelete={handleDeletePosition}
                    />

                    {/* 停損倉 - 停損出場 */}
                    <PositionSection
                        title="🛑 停損倉"
                        subtitle="觸及停損價出場"
                        positions={filteredPositions.filter(p => p.status === 'stopped')}
                        headerBg="bg-green-50"
                        headerBorder="border-green-200"
                        isRefreshing={false}
                        loading={false}
                        onClose={handleClosePosition}
                        onDelete={handleDeletePosition}
                    />

                    {/* 移動停利倉 */}
                    <PositionSection
                        title="📉 移動停利倉"
                        subtitle="移動停利觸發出場"
                        positions={filteredPositions.filter(p => p.status === 'trailing_stopped')}
                        headerBg="bg-orange-50"
                        headerBorder="border-orange-200"
                        isRefreshing={false}
                        loading={false}
                        onClose={handleClosePosition}
                        onDelete={handleDeletePosition}
                        defaultCollapsed={true}
                    />

                    {/* 強制平倉 */}
                    <PositionSection
                        title="⚡ 強制平倉"
                        subtitle="系統強制平倉"
                        positions={filteredPositions.filter(p => p.status === 'forced_close')}
                        headerBg="bg-gray-50"
                        headerBorder="border-gray-300"
                        isRefreshing={false}
                        loading={false}
                        onClose={handleClosePosition}
                        onDelete={handleDeletePosition}
                        defaultCollapsed={true}
                    />

                    {/* 已平倉 - 手動賣出 */}
                    {filteredPositions.filter(p => p.status === 'closed').length > 0 && (
                        <PositionSection
                            title="📋 已平倉"
                            subtitle="手動賣出的股票"
                            positions={filteredPositions.filter(p => p.status === 'closed')}
                            headerBg="bg-gray-50"
                            headerBorder="border-gray-200"
                            isRefreshing={false}
                            loading={false}
                            onClose={handleClosePosition}
                            onDelete={handleDeletePosition}
                        />
                    )}
                </div>
            )}

            {/* 交易紀錄 */}
            {activeTab === 'trades' && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    {trades.length === 0 ? (
                        <div className="p-12 text-center">
                            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <History className="w-8 h-8 text-gray-400" />
                            </div>
                            <p className="text-gray-500 font-medium">尚無交易紀錄</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gray-50 border-b border-gray-200">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">時間</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">股票</th>
                                        <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">類型</th>
                                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">價格</th>
                                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">數量</th>
                                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">總額</th>
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">來源</th>
                                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">損益</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                    {trades.map((trade) => (
                                        <tr key={trade.id} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-4 py-3 text-sm text-gray-500">
                                                {formatDate(trade.trade_date)}
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="font-semibold text-gray-900">{trade.symbol}</span>
                                                {trade.stock_name && <span className="text-gray-500 text-sm ml-2">{trade.stock_name}</span>}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <span className={cn(
                                                    "px-2 py-1 rounded-full text-xs font-medium border",
                                                    trade.trade_type === 'buy'
                                                        ? 'bg-red-50 text-red-700 border-red-200'
                                                        : 'bg-green-50 text-green-700 border-green-200'
                                                )}>
                                                    {trade.trade_type === 'buy' ? '買入' : '賣出'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3 text-right font-mono text-gray-900">
                                                ${formatNumber(trade.price)}
                                            </td>
                                            <td className="px-4 py-3 text-right font-mono text-gray-700">
                                                {trade.quantity.toLocaleString()}
                                            </td>
                                            <td className="px-4 py-3 text-right font-mono text-yellow-700 font-medium">
                                                ${formatNumber(trade.total_amount)}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-gray-600">
                                                {SOURCE_NAMES[trade.analysis_source] || trade.analysis_source}
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                {trade.profit !== null && (
                                                    <span className={cn(
                                                        "font-mono font-bold",
                                                        trade.profit >= 0 ? 'text-red-600' : 'text-green-600'
                                                    )}>
                                                        {trade.profit >= 0 ? '+' : ''}{formatNumber(trade.profit)}
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )
            }

            {/* 準確性分析 */}
            {
                activeTab === 'accuracy' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {accuracy.length === 0 ? (
                            <div className="col-span-full bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
                                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <BarChart3 className="w-8 h-8 text-gray-400" />
                                </div>
                                <p className="text-gray-500 font-medium">尚無準確性數據</p>
                                <p className="text-gray-400 text-sm mt-1">需要有已結束的交易紀錄才能計算準確性</p>
                            </div>
                        ) : (
                            accuracy.map((acc) => (
                                <div key={acc.analysis_source} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="font-bold text-gray-900">
                                            {SOURCE_NAMES[acc.analysis_source] || acc.analysis_source}
                                        </h3>
                                        <span className={cn(
                                            "px-3 py-1 rounded-full text-sm font-bold",
                                            acc.win_rate >= 60 ? 'bg-green-100 text-green-700' :
                                                acc.win_rate >= 40 ? 'bg-yellow-100 text-yellow-700' :
                                                    'bg-red-100 text-red-700'
                                        )}>
                                            {acc.win_rate.toFixed(1)}%
                                        </span>
                                    </div>

                                    <div className="space-y-3">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-500">總交易次數</span>
                                            <span className="font-mono font-medium text-gray-900">{acc.total_trades}</span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-500">獲利 / 虧損</span>
                                            <span>
                                                <span className="text-red-600 font-mono font-medium">{acc.winning_trades}</span>
                                                <span className="text-gray-400"> / </span>
                                                <span className="text-green-600 font-mono font-medium">{acc.losing_trades}</span>
                                            </span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-500">淨損益</span>
                                            <span className={cn(
                                                "font-mono font-bold",
                                                acc.net_profit >= 0 ? 'text-red-600' : 'text-green-600'
                                            )}>
                                                {acc.net_profit >= 0 ? '+' : ''}{formatNumber(acc.net_profit)}
                                            </span>
                                        </div>
                                    </div>

                                    {/* 勝率進度條 */}
                                    <div className="mt-4">
                                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                                            <div
                                                className={cn(
                                                    "h-full transition-all duration-500",
                                                    acc.win_rate >= 60 ? 'bg-green-500' :
                                                        acc.win_rate >= 40 ? 'bg-yellow-500' :
                                                            'bg-red-500'
                                                )}
                                                style={{ width: `${acc.win_rate}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )
            }

            {/* 新增持倉對話框 */}
            {
                showAddForm && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
                            <div className="flex items-center justify-between p-5 border-b border-gray-200">
                                <h2 className="text-lg font-bold text-gray-900">新增持倉</h2>
                                <button
                                    onClick={() => setShowAddForm(false)}
                                    className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <div className="p-5 space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">股票代碼 *</label>
                                    <input
                                        type="text"
                                        value={newPosition.symbol}
                                        onChange={(e) => setNewPosition({ ...newPosition, symbol: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                        placeholder="例如: 2330"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">股票名稱</label>
                                    <input
                                        type="text"
                                        value={newPosition.stock_name}
                                        onChange={(e) => setNewPosition({ ...newPosition, stock_name: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                        placeholder="例如: 台積電"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">進場價格 *</label>
                                        <input
                                            type="number"
                                            value={newPosition.entry_price}
                                            onChange={(e) => setNewPosition({ ...newPosition, entry_price: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                            placeholder="進場價"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">數量</label>
                                        <input
                                            type="number"
                                            value={newPosition.entry_quantity}
                                            onChange={(e) => setNewPosition({ ...newPosition, entry_quantity: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">停損價</label>
                                        <input
                                            type="number"
                                            value={newPosition.stop_loss_price}
                                            onChange={(e) => setNewPosition({ ...newPosition, stop_loss_price: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                            placeholder="停損價"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">目標價</label>
                                        <input
                                            type="number"
                                            value={newPosition.target_price}
                                            onChange={(e) => setNewPosition({ ...newPosition, target_price: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                            placeholder="目標價"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">分析來源</label>
                                    <select
                                        value={newPosition.analysis_source}
                                        onChange={(e) => setNewPosition({ ...newPosition, analysis_source: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                    >
                                        {Object.entries(SOURCE_NAMES).map(([key, name]) => (
                                            <option key={key} value={key}>{name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">備註</label>
                                    <textarea
                                        value={newPosition.notes}
                                        onChange={(e) => setNewPosition({ ...newPosition, notes: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none h-20"
                                        placeholder="交易備註..."
                                    />
                                </div>
                            </div>

                            <div className="flex gap-3 p-5 border-t border-gray-200">
                                <button
                                    onClick={() => setShowAddForm(false)}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleAddPosition}
                                    disabled={!newPosition.symbol || !newPosition.entry_price}
                                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    新增
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* 儲值視窗 */}
            {
                showDepositForm && (
                    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                        <div className="bg-white rounded-2xl w-full max-w-sm overflow-hidden shadow-xl">
                            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                                <h3 className="font-bold text-gray-900 text-lg flex items-center gap-2">
                                    <DollarSign className="w-5 h-5 text-emerald-600" />
                                    模擬資金儲值
                                </h3>
                                <button
                                    onClick={() => setShowDepositForm(false)}
                                    className="p-1 hover:bg-gray-200 rounded-lg transition-colors"
                                >
                                    <X className="w-5 h-5 text-gray-500" />
                                </button>
                            </div>
                            
                            <div className="p-6 space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">儲值金額</label>
                                    <input
                                        type="number"
                                        value={depositAmount}
                                        onChange={(e) => setDepositAmount(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                                        placeholder="如: 1000000"
                                    />
                                    <p className="text-sm text-gray-500 mt-2">
                                        請輸入您希望為 AI 模擬操作準備的初始本金。
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-3 p-5 border-t border-gray-200">
                                <button
                                    onClick={() => setShowDepositForm(false)}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleDeposit}
                                    disabled={!depositAmount || parseFloat(depositAmount) <= 0}
                                    className="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    儲值
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* 提款視窗 (減少本金) */}
            {
                showWithdrawForm && (
                    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                        <div className="bg-white rounded-2xl w-full max-w-sm overflow-hidden shadow-xl">
                            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                                <h3 className="font-bold text-gray-900 text-lg flex items-center gap-2">
                                    <DollarSign className="w-5 h-5 text-red-600" />
                                    模擬資金提款 (匯出)
                                </h3>
                                <button
                                    onClick={() => setShowWithdrawForm(false)}
                                    className="p-1 hover:bg-gray-200 rounded-lg transition-colors"
                                >
                                    <X className="w-5 h-5 text-gray-500" />
                                </button>
                            </div>
                            
                            <div className="p-6 space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">提款金額 (減少本金)</label>
                                    <input
                                        type="number"
                                        value={withdrawAmount}
                                        onChange={(e) => setWithdrawAmount(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none"
                                        placeholder="如: 500000"
                                    />
                                    <p className="text-sm text-gray-500 mt-2">
                                        請輸入要從帳戶中「移除」或「退回」的本金額度。
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-3 p-5 border-t border-gray-200">
                                <button
                                    onClick={() => setShowWithdrawForm(false)}
                                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleWithdraw}
                                    disabled={!withdrawAmount || parseFloat(withdrawAmount) <= 0}
                                    className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    提款 / 減資
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
        </div>
    );
}

// 總結卡片組件
function SummaryCard({
    title,
    value,
    prefix = '',
    icon,
    color
}: {
    title: string;
    value: string | number;
    prefix?: string;
    icon: React.ReactNode;
    color: 'blue' | 'green' | 'red' | 'purple' | 'orange' | 'emerald';
}) {
    const colorClasses = {
        blue: 'bg-blue-50 text-blue-600 border-blue-100',
        green: 'bg-green-50 text-green-600 border-green-100',
        red: 'bg-red-50 text-red-600 border-red-100',
        purple: 'bg-purple-50 text-purple-600 border-purple-100',
        orange: 'bg-orange-50 text-orange-600 border-orange-100',
        emerald: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    };

    const iconClasses = {
        blue: 'bg-blue-100',
        green: 'bg-green-100',
        red: 'bg-red-100',
        purple: 'bg-purple-100',
        orange: 'bg-orange-100',
        emerald: 'bg-emerald-100',
    };

    return (
        <div className={cn(
            "relative overflow-hidden bg-white rounded-2xl p-5 border shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-1 group",
            colorClasses[color]
        )}>
            {/* 背景裝飾 */}
            <div className="absolute top-0 right-0 -mr-4 -mt-4 w-24 h-24 rounded-full opacity-5 bg-current" />
            
            <div className="flex items-center justify-between mb-3 relative z-10">
                <span className="text-sm font-medium text-gray-500 group-hover:text-gray-700 transition-colors uppercase tracking-wider">{title}</span>
                <div className={cn("p-2.5 rounded-xl transition-transform group-hover:scale-110 duration-300", iconClasses[color])}>
                    {icon}
                </div>
            </div>
            
            <div className="flex items-baseline gap-1 relative z-10">
                {prefix && <span className="text-lg font-semibold text-gray-400">{prefix}</span>}
                <div className="text-2xl font-black text-gray-900 tracking-tight">
                    {value}
                </div>
            </div>

            {/* 底部裝飾線 */}
            <div className="absolute bottom-0 left-0 h-1 w-full bg-current opacity-20" />
        </div>
    );
}

// 來源名稱（用於 PositionSection）
const SOURCE_NAMES_MAP: Record<string, string> = {
    main_force: '主力偵測',
    big_order: '大單分析',
    lstm_prediction: 'LSTM 預測',
    expert_signal: '專家信號',
    premarket: '盤前分析',
    manual: '手動操作',
    day_trading: '當沖戰情室',
};


// 狀態配置（用於 PositionSection）
const STATUS_CONFIG_MAP: Record<string, { label: string; bg: string; text: string; border: string }> = {
    open: { label: '持有中', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
    closed: { label: '已賣出', bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' },
    stopped: { label: '停損', bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
    target_hit: { label: '達標', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' },
};

// 持倉區塊組件
function PositionSection({
    title,
    subtitle,
    positions,
    headerBg,
    headerBorder,
    isRefreshing,
    loading,
    onClose,
    onDelete,
    defaultCollapsed = false,
}: {
    title: string;
    subtitle: string;
    positions: any[];
    headerBg: string;
    headerBorder: string;
    isRefreshing: boolean;
    loading: boolean;
    onClose: (pos: any) => void;
    onDelete: (pos: any) => void;
    defaultCollapsed?: boolean;
}) {
    const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);

    const formatNumber = (num: number | null | undefined) => {
        if (num === null || num === undefined) return '-';
        return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const formatDate = (dateStr: string) => {
        const d = new Date(dateStr);
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const hh = String(d.getHours()).padStart(2, '0');
        const min = String(d.getMinutes()).padStart(2, '0');
        return `${mm}/${dd} ${hh}:${min}`;
    };

    const formatPercent = (num: number | null | undefined) => {
        if (num === null || num === undefined) return '-';
        return `${num.toFixed(2)}%`;
    };

    if (positions.length === 0) {
        return null;
    }

    return (
        <div className={cn("bg-white rounded-xl shadow-sm border overflow-hidden", headerBorder)}>
            {/* 區塊標題 */}
            <div
                className={cn("px-4 py-3 flex items-center justify-between cursor-pointer", headerBg)}
                onClick={() => setIsCollapsed(!isCollapsed)}
            >
                <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-gray-900">{title}</span>
                    <span className="text-sm text-gray-500">{subtitle}</span>
                    <span className="px-2 py-0.5 bg-white rounded-full text-xs font-medium text-gray-700 border border-gray-200">
                        {positions.length} 筆
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    {isRefreshing && (
                        <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs">
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            更新中
                        </div>
                    )}
                    {isCollapsed ? (
                        <ChevronDown className="w-5 h-5 text-gray-500" />
                    ) : (
                        <ChevronUp className="w-5 h-5 text-gray-500" />
                    )}
                </div>
            </div>

            {/* 表格內容 */}
            {!isCollapsed && (
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">股票</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">來源</th>
                                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">進場價</th>
                                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">投資成本</th>
                                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">現價/出場價</th>
                                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">停損/目標</th>
                                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">損益</th>
                                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">操作</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {positions.map((pos) => {
                                const profit = pos.status === 'open' ? pos.unrealized_profit : pos.realized_profit;
                                const profitPercent = pos.status === 'open' ? pos.unrealized_profit_percent : pos.realized_profit_percent;
                                const isProfit = (profit || 0) >= 0;

                                return (
                                    <tr key={pos.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-center font-bold text-blue-600 text-sm">
                                                    {pos.symbol}
                                                </div>
                                                <div>
                                                    <div className="font-semibold text-gray-900 flex items-center gap-2">
                                                        {pos.stock_name || pos.symbol}
                                                        {pos.is_short && (
                                                            <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-xs font-bold rounded border border-red-200">
                                                                做空
                                                            </span>
                                                        )}
                                                        {pos.is_simulated && (
                                                            <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 text-xs font-medium rounded border border-yellow-200">
                                                                模擬
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="text-xs text-gray-400">
                                                        {pos.is_short ? '空單進場' : '做多進場'} {formatDate(pos.entry_date)}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="text-sm text-gray-700">
                                                {SOURCE_NAMES_MAP[pos.analysis_source] || pos.analysis_source}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-gray-900">
                                            ${formatNumber(pos.entry_price)}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <div className="font-mono text-gray-900 font-medium">
                                                ${formatNumber(pos.entry_price * pos.entry_quantity)}
                                            </div>
                                            <div className="text-xs text-gray-500">
                                                {formatNumber(pos.entry_quantity)} 股
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-gray-900">
                                            ${formatNumber(pos.status === 'open' ? pos.current_price : pos.exit_price)}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <div className="text-xs">
                                                <div className="text-red-600">{pos.stop_loss_price ? `停 $${formatNumber(pos.stop_loss_price)}` : '-'}</div>
                                                <div className="text-green-600">{pos.target_price ? `目 $${formatNumber(pos.target_price)}` : '-'}</div>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            {profit !== null && (
                                                <div className={isProfit ? 'text-red-600' : 'text-green-600'}>
                                                    <div className="font-mono font-bold">
                                                        {isProfit ? '+' : ''}{formatNumber(profit)}
                                                    </div>
                                                    {profitPercent !== null && (
                                                        <div className="text-xs">
                                                            ({isProfit ? '+' : ''}{formatPercent(profitPercent)})
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center justify-center gap-1">
                                                {pos.status === 'open' && (
                                                    <button
                                                        onClick={() => onClose(pos)}
                                                        className="p-1.5 text-orange-600 hover:bg-orange-50 rounded-lg transition-colors"
                                                        title="賣出"
                                                    >
                                                        <DollarSign className="w-4 h-4" />
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => onDelete(pos)}
                                                    className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                                    title="刪除"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
