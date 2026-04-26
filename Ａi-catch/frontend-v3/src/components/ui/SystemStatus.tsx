'use client';

import React, { useEffect, useState } from 'react';

interface ServiceStatus {
    api: string;
    yfinance: string;
    yfinance_patch: string;
    fubon_api: string;
    news_crawler: string;
    finmind_api: string;
}

interface HealthStatus {
    status: string;
    version: string;
    service: string;
    timestamp: string;
    services: ServiceStatus;
    features: Record<string, boolean | string>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function SystemStatus() {
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

    const fetchHealth = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/health`);
            if (response.ok) {
                const data = await response.json();
                setHealth(data);
                setError(null);
                setLastUpdate(new Date());
            } else {
                setError('API 回應異常');
            }
        } catch (err) {
            setError('無法連接到 API');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHealth();

        // 每 30 秒檢查一次
        const interval = setInterval(fetchHealth, 30000);

        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status: string): string => {
        switch (status) {
            case 'healthy':
            case 'working':
            case 'active':
            case 'connected':
            case 'available':
                return 'bg-green-500';
            case 'fallback_mode':
            case 'fallback_ready':
            case 'limited':
                return 'bg-yellow-500';
            case 'warning':
            case 'unavailable':
            case 'not_loaded':
                return 'bg-red-500';
            default:
                return 'bg-gray-500';
        }
    };

    const getStatusText = (status: string): string => {
        switch (status) {
            case 'healthy':
            case 'working':
                return '正常';
            case 'active':
                return '啟用';
            case 'connected':
                return '已連接';
            case 'available':
                return '可用';
            case 'fallback_mode':
            case 'fallback_ready':
                return '備援模式';
            case 'limited':
                return '受限';
            case 'warning':
                return '警告';
            case 'unavailable':
                return '不可用';
            case 'not_loaded':
                return '未載入';
            default:
                return status;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center gap-2 text-gray-400 text-xs">
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-pulse"></div>
                <span>檢查系統狀態...</span>
            </div>
        );
    }

    if (error || !health) {
        return (
            <div className="flex items-center gap-2 text-red-400 text-xs">
                <div className="w-2 h-2 rounded-full bg-red-500"></div>
                <span>{error || '系統異常'}</span>
            </div>
        );
    }

    return (
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            {/* 主狀態 */}
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(health.status)}`}></div>
                    <span className="text-sm font-medium text-gray-200">
                        系統狀態: {health.status === 'healthy' ? '正常運作' : '異常'}
                    </span>
                </div>
                <span className="text-xs text-gray-500">v{health.version}</span>
            </div>

            {/* 服務狀態網格 */}
            <div className="grid grid-cols-3 gap-2 mt-3">
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health.services.yfinance_patch)}`}></div>
                    <span className="text-xs text-gray-400">YF 修補</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health.services.yfinance)}`}></div>
                    <span className="text-xs text-gray-400">Yahoo</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health.services.fubon_api)}`}></div>
                    <span className="text-xs text-gray-400">富邦</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health.services.news_crawler)}`}></div>
                    <span className="text-xs text-gray-400">新聞</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health.services.finmind_api)}`}></div>
                    <span className="text-xs text-gray-400">FinMind</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${getStatusColor(health.services.api)}`}></div>
                    <span className="text-xs text-gray-400">API</span>
                </div>
            </div>

            {/* 最後更新時間 */}
            <div className="mt-2 pt-2 border-t border-gray-700">
                <span className="text-xs text-gray-500">
                    最後更新: {lastUpdate.toLocaleTimeString('zh-TW')}
                </span>
            </div>
        </div>
    );
}
