'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Monitor, Cpu, HardDrive, Database, Server, Activity,
    CheckCircle, XCircle, AlertTriangle, RefreshCw, Clock,
    Zap, MemoryStick, FileText, Brain
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SystemStatus {
    system: {
        os: string;
        os_version: string;
        python_version: string;
        hostname: string;
    };
    cpu: { percent: number; cores: number; frequency: number };
    memory: { total: number; used: number; percent: number };
    disk: { total: number; used: number; percent: number };
    services: Array<{ name: string; status: string; port: number; uptime: string }>;
    timestamp: string;
}

interface ModelInfo {
    symbol: string;
    name: string;
    type: string;
    file: string;
    size: number;
    modified: string;
}

interface LogEntry {
    id: string;
    level: string;
    message: string;
    timestamp: string;
}

export default function MonitorPage() {
    const [status, setStatus] = useState<SystemStatus | null>(null);
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [autoRefresh, setAutoRefresh] = useState(true);

    const loadData = useCallback(async function () {
        try {
            var [statusRes, modelsRes, logsRes] = await Promise.all([
                fetch('http://localhost:8000/api/monitor/status'),
                fetch('http://localhost:8000/api/monitor/models'),
                fetch('http://localhost:8000/api/monitor/logs')
            ]);

            var statusData = await statusRes.json();
            var modelsData = await modelsRes.json();
            var logsData = await logsRes.json();

            if (statusData.success) setStatus(statusData);
            if (modelsData.success) setModels(modelsData.models);
            if (logsData.success) setLogs(logsData.logs);
        } catch (err) {
            console.error('載入監控數據失敗:', err);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(function () {
        loadData();

        if (autoRefresh) {
            var interval = setInterval(loadData, 5000);
            return function () { clearInterval(interval); };
        }
    }, [loadData, autoRefresh]);

    function getStatusColor(percent: number) {
        if (percent < 50) return 'text-green-600 bg-green-100';
        if (percent < 80) return 'text-yellow-600 bg-yellow-100';
        return 'text-red-600 bg-red-100';
    }

    function getLogLevelColor(level: string) {
        switch (level) {
            case 'ERROR': return 'bg-red-100 text-red-700';
            case 'WARNING': return 'bg-yellow-100 text-yellow-700';
            case 'INFO': return 'bg-blue-100 text-blue-700';
            default: return 'bg-gray-100 text-gray-700';
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <RefreshCw className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 頁面標題 */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Monitor className="w-8 h-8 text-indigo-600" />
                        系統監控
                    </h1>
                    <p className="text-gray-600 mt-2">即時監控系統狀態和服務健康</p>
                </div>

                <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={function (e) { setAutoRefresh(e.target.checked); }}
                            className="w-4 h-4 text-indigo-600 rounded"
                        />
                        <span className="text-sm text-gray-600">自動刷新</span>
                    </label>

                    <button
                        onClick={loadData}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2"
                    >
                        <RefreshCw className="w-4 h-4" />
                        刷新
                    </button>
                </div>
            </div>

            {/* 系統資源卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* CPU */}
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Cpu className="w-5 h-5 text-blue-600" />
                            <h3 className="font-bold text-gray-900">CPU</h3>
                        </div>
                        <span className={cn("px-2 py-1 rounded-full text-sm font-medium", getStatusColor(status?.cpu.percent || 0))}>
                            {status?.cpu.percent || 0}%
                        </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                        <div
                            className="bg-blue-600 h-3 rounded-full transition-all"
                            style={{ width: (status?.cpu.percent || 0) + '%' }}
                        />
                    </div>
                    <div className="text-sm text-gray-500">
                        {status?.cpu.cores} 核心 · {Math.round(status?.cpu.frequency || 0)} MHz
                    </div>
                </div>

                {/* 記憶體 */}
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <MemoryStick className="w-5 h-5 text-purple-600" />
                            <h3 className="font-bold text-gray-900">記憶體</h3>
                        </div>
                        <span className={cn("px-2 py-1 rounded-full text-sm font-medium", getStatusColor(status?.memory.percent || 0))}>
                            {status?.memory.percent || 0}%
                        </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                        <div
                            className="bg-purple-600 h-3 rounded-full transition-all"
                            style={{ width: (status?.memory.percent || 0) + '%' }}
                        />
                    </div>
                    <div className="text-sm text-gray-500">
                        {status?.memory.used} / {status?.memory.total} GB
                    </div>
                </div>

                {/* 磁碟 */}
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <HardDrive className="w-5 h-5 text-green-600" />
                            <h3 className="font-bold text-gray-900">磁碟</h3>
                        </div>
                        <span className={cn("px-2 py-1 rounded-full text-sm font-medium", getStatusColor(status?.disk.percent || 0))}>
                            {status?.disk.percent || 0}%
                        </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
                        <div
                            className="bg-green-600 h-3 rounded-full transition-all"
                            style={{ width: (status?.disk.percent || 0) + '%' }}
                        />
                    </div>
                    <div className="text-sm text-gray-500">
                        {status?.disk.used} / {status?.disk.total} GB
                    </div>
                </div>
            </div>

            {/* 服務狀態 */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="p-4 border-b border-gray-100">
                    <div className="flex items-center gap-2">
                        <Server className="w-5 h-5 text-gray-600" />
                        <h3 className="font-bold text-gray-900">服務狀態</h3>
                    </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4">
                    {status?.services.map(function (service) {
                        var isRunning = service.status === 'running';
                        return (
                            <div key={service.name} className={cn(
                                "p-4 rounded-lg border-2 transition-colors",
                                isRunning ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"
                            )}>
                                <div className="flex items-center justify-between mb-2">
                                    <span className="font-medium text-gray-900">{service.name}</span>
                                    {isRunning ? (
                                        <CheckCircle className="w-5 h-5 text-green-600" />
                                    ) : (
                                        <XCircle className="w-5 h-5 text-red-600" />
                                    )}
                                </div>
                                <div className="text-sm text-gray-500">
                                    <div>Port: {service.port}</div>
                                    {isRunning && service.uptime !== '-' && (
                                        <div className="flex items-center gap-1 mt-1">
                                            <Clock className="w-3 h-3" />
                                            {service.uptime}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* LSTM 模型 */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                    <div className="p-4 border-b border-gray-100">
                        <div className="flex items-center gap-2">
                            <Brain className="w-5 h-5 text-indigo-600" />
                            <h3 className="font-bold text-gray-900">LSTM 模型</h3>
                            <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded-full">
                                {models.length} 個
                            </span>
                        </div>
                    </div>

                    <div className="divide-y divide-gray-100 max-h-[300px] overflow-y-auto">
                        {models.map(function (model) {
                            return (
                                <div key={model.symbol + model.type} className="p-3 flex items-center justify-between hover:bg-gray-50">
                                    <div>
                                        <div className="font-medium text-gray-900">
                                            {model.symbol} {model.name}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {model.type} · {model.size} KB
                                        </div>
                                    </div>
                                    <div className="text-xs text-gray-400">
                                        {new Date(model.modified).toLocaleDateString('zh-TW')}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* 系統日誌 */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                    <div className="p-4 border-b border-gray-100">
                        <div className="flex items-center gap-2">
                            <FileText className="w-5 h-5 text-gray-600" />
                            <h3 className="font-bold text-gray-900">系統日誌</h3>
                        </div>
                    </div>

                    <div className="divide-y divide-gray-100 max-h-[300px] overflow-y-auto">
                        {logs.map(function (log) {
                            return (
                                <div key={log.id} className="p-3 flex items-start gap-3 hover:bg-gray-50">
                                    <span className={cn("px-2 py-0.5 rounded text-xs font-medium", getLogLevelColor(log.level))}>
                                        {log.level}
                                    </span>
                                    <div className="flex-1">
                                        <div className="text-sm text-gray-900">{log.message}</div>
                                        <div className="text-xs text-gray-400">
                                            {new Date(log.timestamp).toLocaleString('zh-TW')}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* 系統資訊 */}
            <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                        <span className="text-gray-500">作業系統:</span>
                        <span className="ml-2 font-medium">{status?.system.os} {status?.system.os_version?.substring(0, 20)}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Python:</span>
                        <span className="ml-2 font-medium">{status?.system.python_version}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">主機名稱:</span>
                        <span className="ml-2 font-medium">{status?.system.hostname}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">更新時間:</span>
                        <span className="ml-2 font-medium">
                            {status?.timestamp ? new Date(status.timestamp).toLocaleTimeString('zh-TW') : '-'}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
