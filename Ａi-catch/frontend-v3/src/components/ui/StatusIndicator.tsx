'use client';

import React, { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface StatusIndicatorProps {
    showDetails?: boolean;
}

export default function StatusIndicator({ showDetails = false }: StatusIndicatorProps) {
    const [status, setStatus] = useState<'loading' | 'healthy' | 'warning' | 'error'>('loading');
    const [version, setVersion] = useState<string>('');

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const response = await fetch(`${API_BASE}/api/health`, {
                    method: 'GET',
                    signal: AbortSignal.timeout(5000) // 5秒超時
                });

                if (response.ok) {
                    const data = await response.json();
                    setStatus(data.status === 'healthy' ? 'healthy' : 'warning');
                    setVersion(data.version || '3.0');
                } else {
                    setStatus('warning');
                }
            } catch {
                setStatus('error');
            }
        };

        checkHealth();
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, []);

    const statusConfig = {
        loading: {
            color: 'bg-gray-400',
            text: '檢查中...',
            pulse: true
        },
        healthy: {
            color: 'bg-green-500',
            text: '系統正常',
            pulse: false
        },
        warning: {
            color: 'bg-yellow-500',
            text: '部分服務異常',
            pulse: true
        },
        error: {
            color: 'bg-red-500',
            text: '無法連接',
            pulse: true
        }
    };

    const config = statusConfig[status];

    return (
        <div className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${config.color} ${config.pulse ? 'animate-pulse' : ''}`}></div>
            {showDetails && (
                <>
                    <span className="text-gray-300">{config.text}</span>
                    {version && <span className="text-gray-500">v{version}</span>}
                </>
            )}
        </div>
    );
}
