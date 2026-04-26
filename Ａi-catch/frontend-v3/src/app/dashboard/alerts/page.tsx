'use client';

import { useState, useEffect, useCallback } from 'react';
import { Bell, AlertTriangle, CheckCircle, Info, Trash2, Settings, Filter, RefreshCw, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { alertsApi } from '@/lib/api-client';

type AlertType = 'mainforce' | 'lstm' | 'price' | 'system';
type Severity = 'critical' | 'high' | 'medium' | 'low';

interface Alert {
    id: string;
    symbol: string;
    stockName: string;
    type: AlertType;
    severity: Severity;
    title: string;
    message: string;
    status: string;
    read: boolean;
    createdAt: string;
}

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<'all' | AlertType>('all');
    const [showUnreadOnly, setShowUnreadOnly] = useState(false);
    const [refreshing, setRefreshing] = useState(false);

    // 獲取警報數據
    const fetchAlerts = useCallback(async () => {
        try {
            setRefreshing(true);
            const response = await alertsApi.getActive();
            setAlerts(response.alerts || []);
            setError(null);
        } catch (err) {
            console.error('獲取警報失敗:', err);
            setError('無法獲取警報數據');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        fetchAlerts();
    }, [fetchAlerts]);

    const filteredAlerts = alerts.filter(alert => {
        if (showUnreadOnly && alert.read) return false;
        if (filter !== 'all' && alert.type !== filter) return false;
        return true;
    });

    const unreadCount = alerts.filter(a => !a.read).length;

    const markAsRead = async (id: string) => {
        try {
            await alertsApi.markAsRead(id);
            setAlerts(alerts.map(a => a.id === id ? { ...a, read: true } : a));
        } catch (err) {
            console.error('標記失敗:', err);
        }
    };

    const markAllAsRead = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/alerts/read-all', { method: 'POST' });
            if (response.ok) {
                setAlerts(alerts.map(a => ({ ...a, read: true })));
            }
        } catch (err) {
            console.error('標記失敗:', err);
        }
    };

    const deleteAlert = async (id: string) => {
        try {
            await alertsApi.delete(id);
            setAlerts(alerts.filter(a => a.id !== id));
        } catch (err) {
            console.error('刪除失敗:', err);
        }
    };

    const getTypeIcon = (type: AlertType) => {
        switch (type) {
            case 'mainforce': return <AlertTriangle className="w-5 h-5" />;
            case 'lstm': return <Info className="w-5 h-5" />;
            case 'price': return <Bell className="w-5 h-5" />;
            case 'system': return <Settings className="w-5 h-5" />;
        }
    };

    const getTypeColor = (type: AlertType) => {
        switch (type) {
            case 'mainforce': return 'bg-orange-100 text-orange-600';
            case 'lstm': return 'bg-blue-100 text-blue-600';
            case 'price': return 'bg-purple-100 text-purple-600';
            case 'system': return 'bg-gray-100 text-gray-600';
        }
    };

    const getSeverityColor = (severity: Severity) => {
        switch (severity) {
            case 'critical': return 'bg-red-200 text-red-700';
            case 'high': return 'bg-red-100 text-red-600';
            case 'medium': return 'bg-yellow-100 text-yellow-600';
            case 'low': return 'bg-green-100 text-green-600';
        }
    };

    const getSeverityLabel = (severity: Severity) => {
        switch (severity) {
            case 'critical': return '緊急';
            case 'high': return '高';
            case 'medium': return '中';
            case 'low': return '低';
        }
    };

    const formatTime = (isoString: string) => {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

        if (diffMins < 60) return `${diffMins} 分鐘前`;
        if (diffHours < 24) return `${diffHours} 小時前`;
        return date.toLocaleDateString('zh-TW');
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                <span className="ml-2 text-gray-600">載入中...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <Bell className="w-16 h-16 text-red-500 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">載入失敗</h3>
                    <p className="text-gray-600">{error}</p>
                    <button
                        onClick={fetchAlerts}
                        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                        重試
                    </button>
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
                        <Bell className="w-8 h-8 text-blue-600" />
                        警報中心
                    </h1>
                    <p className="text-gray-600 mt-2">管理您的交易警報和系統通知（即時數據）</p>
                </div>

                {/* Unread Badge */}
                {unreadCount > 0 && (
                    <div className="bg-red-100 border border-red-200 rounded-lg px-4 py-2">
                        <div className="text-sm text-red-600 font-medium">
                            {unreadCount} 條未讀通知
                        </div>
                    </div>
                )}
            </div>

            {/* Actions Bar */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    {/* Filters */}
                    <div className="flex items-center gap-3">
                        <Filter className="w-5 h-5 text-gray-400" />
                        <div className="flex gap-2">
                            {(['all', 'mainforce', 'lstm', 'price', 'system'] as const).map((type) => (
                                <button
                                    key={type}
                                    onClick={() => setFilter(type)}
                                    className={cn(
                                        "px-3 py-1.5 text-sm rounded-lg transition-colors",
                                        filter === type
                                            ? "bg-blue-600 text-white"
                                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                    )}
                                >
                                    {type === 'all' && '全部'}
                                    {type === 'mainforce' && '主力'}
                                    {type === 'lstm' && 'LSTM'}
                                    {type === 'price' && '價格'}
                                    {type === 'system' && '系統'}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 text-sm text-gray-600">
                            <input
                                type="checkbox"
                                checked={showUnreadOnly}
                                onChange={(e) => setShowUnreadOnly(e.target.checked)}
                                className="w-4 h-4 rounded border-gray-300"
                            />
                            只顯示未讀
                        </label>

                        <button
                            onClick={markAllAsRead}
                            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            <CheckCircle className="w-4 h-4" />
                            全部標為已讀
                        </button>

                        <button
                            onClick={fetchAlerts}
                            disabled={refreshing}
                            className="flex items-center gap-2 px-3 py-1.5 text-sm text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50"
                        >
                            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
                            {refreshing ? '更新中...' : '重新整理'}
                        </button>
                    </div>
                </div>
            </div>

            {/* Status Bar */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-sm text-green-700">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    即時連接中 - 數據來自後端 API
                </div>
            </div>

            {/* Alerts List */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                {filteredAlerts.length === 0 ? (
                    <div className="p-12 text-center">
                        <Bell className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">沒有警報</h3>
                        <p className="text-gray-600">目前沒有符合條件的警報</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {filteredAlerts.map((alert) => (
                            <div
                                key={alert.id}
                                className={cn(
                                    "p-4 hover:bg-gray-50 transition-colors",
                                    !alert.read && "bg-blue-50"
                                )}
                            >
                                <div className="flex items-start gap-4">
                                    {/* Icon */}
                                    <div className={cn(
                                        "p-2 rounded-lg flex-shrink-0",
                                        getTypeColor(alert.type)
                                    )}>
                                        {getTypeIcon(alert.type)}
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h4 className="font-semibold text-gray-900">{alert.title}</h4>
                                            {!alert.read && (
                                                <span className="w-2 h-2 bg-blue-600 rounded-full" />
                                            )}
                                            <span className={cn(
                                                "text-xs px-2 py-0.5 rounded-full",
                                                getSeverityColor(alert.severity)
                                            )}>
                                                {getSeverityLabel(alert.severity)}
                                            </span>
                                        </div>
                                        <p className="text-sm text-gray-600 mb-2">{alert.message}</p>
                                        <div className="flex items-center gap-4 text-xs text-gray-400">
                                            <span>{formatTime(alert.createdAt)}</span>
                                            {alert.stockName && (
                                                <span className="text-blue-600 font-medium">
                                                    {alert.symbol} {alert.stockName}
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    {/* Actions */}
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        {!alert.read && (
                                            <button
                                                onClick={() => markAsRead(alert.id)}
                                                className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                                title="標為已讀"
                                            >
                                                <CheckCircle className="w-4 h-4" />
                                            </button>
                                        )}
                                        <button
                                            onClick={() => deleteAlert(alert.id)}
                                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                            title="刪除"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Settings Panel */}
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200 p-6">
                <div className="flex items-start gap-4">
                    <Settings className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
                    <div className="flex-1">
                        <h3 className="text-lg font-bold text-gray-900 mb-2">警報設定</h3>
                        <p className="text-gray-700 text-sm leading-relaxed mb-4">
                            您可以在設定頁面自訂警報條件，包括主力進出場閾值、LSTM 預測變動幅度、價格突破條件等。
                        </p>
                        <div className="flex gap-3">
                            <button className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors">
                                前往設定
                            </button>
                            <button className="px-4 py-2 bg-white text-gray-700 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors">
                                了解更多
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
