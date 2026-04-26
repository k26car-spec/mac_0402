'use client';

import { useState, useEffect } from 'react';
import {
    Bell, Mail, MessageSquare, Settings, Send, TestTube, History,
    Check, X, AlertCircle, Loader2, Save
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NotificationSettings {
    email: {
        enabled: boolean;
        smtp_server: string;
        smtp_port: number;
        username: string;
        has_password: boolean;
        recipients: string[];
    };
    line: {
        enabled: boolean;
        has_token: boolean;
    };
    alerts: {
        mainforce_entry: boolean;
        mainforce_exit: boolean;
        price_alert: boolean;
        lstm_signal: boolean;
    };
}

interface NotificationHistory {
    id: string;
    type: string;
    title: string;
    message: string;
    status: string;
    timestamp: string;
}

export default function NotificationsPage() {
    const [settings, setSettings] = useState<NotificationSettings | null>(null);
    const [history, setHistory] = useState<NotificationHistory[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [isTesting, setIsTesting] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    // 表單狀態
    const [emailPassword, setEmailPassword] = useState('');
    const [lineToken, setLineToken] = useState('');
    const [newRecipient, setNewRecipient] = useState('');

    // 載入設定
    useEffect(function () {
        loadSettings();
        loadHistory();
    }, []);

    async function loadSettings() {
        try {
            var response = await fetch('http://localhost:8000/api/notifications/settings');
            var data = await response.json();
            if (data.success) {
                setSettings(data.settings);
            }
        } catch (err) {
            console.error('載入設定失敗:', err);
        } finally {
            setIsLoading(false);
        }
    }

    async function loadHistory() {
        try {
            var response = await fetch('http://localhost:8000/api/notifications/history');
            var data = await response.json();
            if (data.success) {
                setHistory(data.history);
            }
        } catch (err) {
            console.error('載入歷史失敗:', err);
        }
    }

    async function saveSettings() {
        if (!settings) return;
        setIsSaving(true);
        setMessage(null);

        try {
            var payload: any = {
                email: {
                    enabled: settings.email.enabled,
                    smtp_server: settings.email.smtp_server,
                    smtp_port: settings.email.smtp_port,
                    username: settings.email.username,
                    recipients: settings.email.recipients
                },
                line: {
                    enabled: settings.line.enabled
                },
                alerts: settings.alerts
            };

            if (emailPassword) {
                payload.email.password = emailPassword;
            }
            if (lineToken) {
                payload.line.token = lineToken;
            }

            var response = await fetch('http://localhost:8000/api/notifications/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            var data = await response.json();
            if (data.success) {
                setMessage({ type: 'success', text: '設定已儲存' });
                loadSettings();
            } else {
                setMessage({ type: 'error', text: '儲存失敗' });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '儲存失敗' });
        } finally {
            setIsSaving(false);
        }
    }

    async function testNotification(type: string) {
        setIsTesting(true);
        setMessage(null);

        try {
            var response = await fetch('http://localhost:8000/api/notifications/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: type })
            });

            var data = await response.json();
            if (data.success) {
                setMessage({ type: 'success', text: '測試通知已發送' });
            } else {
                setMessage({ type: 'error', text: '發送失敗' });
            }
        } catch (err) {
            setMessage({ type: 'error', text: '發送失敗' });
        } finally {
            setIsTesting(false);
        }
    }

    function addRecipient() {
        if (!settings || !newRecipient || !newRecipient.includes('@')) return;
        setSettings({
            ...settings,
            email: {
                ...settings.email,
                recipients: [...settings.email.recipients, newRecipient]
            }
        });
        setNewRecipient('');
    }

    function removeRecipient(email: string) {
        if (!settings) return;
        setSettings({
            ...settings,
            email: {
                ...settings.email,
                recipients: settings.email.recipients.filter(function (r) { return r !== email; })
            }
        });
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* 頁面標題 */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Bell className="w-8 h-8 text-indigo-600" />
                        通知設定
                    </h1>
                    <p className="text-gray-600 mt-2">設定 Email 和 LINE 通知，即時接收交易訊號</p>
                </div>

                <button
                    onClick={saveSettings}
                    disabled={isSaving}
                    className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-2 disabled:opacity-50"
                >
                    {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    儲存設定
                </button>
            </div>

            {/* 訊息提示 */}
            {message && (
                <div className={cn(
                    "p-4 rounded-lg flex items-center gap-2",
                    message.type === 'success' ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                )}>
                    {message.type === 'success' ? <Check className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                    {message.text}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Email 設定 */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                    <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Mail className="w-5 h-5 text-blue-600" />
                            <h3 className="font-bold text-gray-900">Email 通知</h3>
                        </div>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={settings?.email.enabled || false}
                                onChange={function (e) {
                                    if (settings) {
                                        setSettings({ ...settings, email: { ...settings.email, enabled: e.target.checked } });
                                    }
                                }}
                                className="w-4 h-4 text-indigo-600 rounded"
                            />
                            <span className="text-sm text-gray-600">啟用</span>
                        </label>
                    </div>

                    <div className="p-4 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">SMTP 伺服器</label>
                                <input
                                    type="text"
                                    value={settings?.email.smtp_server || ''}
                                    onChange={function (e) {
                                        if (settings) {
                                            setSettings({ ...settings, email: { ...settings.email, smtp_server: e.target.value } });
                                        }
                                    }}
                                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
                                <input
                                    type="number"
                                    value={settings?.email.smtp_port || 587}
                                    onChange={function (e) {
                                        if (settings) {
                                            setSettings({ ...settings, email: { ...settings.email, smtp_port: parseInt(e.target.value) } });
                                        }
                                    }}
                                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">帳號</label>
                            <input
                                type="email"
                                value={settings?.email.username || ''}
                                onChange={function (e) {
                                    if (settings) {
                                        setSettings({ ...settings, email: { ...settings.email, username: e.target.value } });
                                    }
                                }}
                                placeholder="your@gmail.com"
                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                密碼 {settings?.email.has_password && <span className="text-green-600">(已設定)</span>}
                            </label>
                            <input
                                type="password"
                                value={emailPassword}
                                onChange={function (e) { setEmailPassword(e.target.value); }}
                                placeholder="輸入新密碼以更新"
                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">收件人</label>
                            <div className="flex gap-2 mb-2">
                                <input
                                    type="email"
                                    value={newRecipient}
                                    onChange={function (e) { setNewRecipient(e.target.value); }}
                                    placeholder="新增收件人 Email"
                                    className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                />
                                <button onClick={addRecipient} className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100">
                                    新增
                                </button>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {settings?.email.recipients.map(function (email) {
                                    return (
                                        <span key={email} className="px-2 py-1 bg-gray-100 rounded-full text-sm flex items-center gap-1">
                                            {email}
                                            <button onClick={function () { removeRecipient(email); }} className="text-gray-400 hover:text-red-500">
                                                <X className="w-3 h-3" />
                                            </button>
                                        </span>
                                    );
                                })}
                            </div>
                        </div>

                        <button
                            onClick={function () { testNotification('email'); }}
                            disabled={isTesting || !settings?.email.enabled}
                            className="w-full py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            <TestTube className="w-4 h-4" />
                            發送測試郵件
                        </button>
                    </div>
                </div>

                {/* LINE 設定 */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                    <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <MessageSquare className="w-5 h-5 text-green-600" />
                            <h3 className="font-bold text-gray-900">LINE Notify</h3>
                        </div>
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={settings?.line.enabled || false}
                                onChange={function (e) {
                                    if (settings) {
                                        setSettings({ ...settings, line: { ...settings.line, enabled: e.target.checked } });
                                    }
                                }}
                                className="w-4 h-4 text-indigo-600 rounded"
                            />
                            <span className="text-sm text-gray-600">啟用</span>
                        </label>
                    </div>

                    <div className="p-4 space-y-4">
                        <div className="p-3 bg-green-50 rounded-lg text-sm text-green-700">
                            <p className="font-medium mb-1">如何取得 LINE Notify Token？</p>
                            <ol className="list-decimal list-inside space-y-1 text-xs">
                                <li>前往 <a href="https://notify-bot.line.me/" target="_blank" className="underline">LINE Notify</a></li>
                                <li>登入後點擊「發行權杖」</li>
                                <li>選擇要通知的聊天室</li>
                                <li>複製產生的 Token</li>
                            </ol>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                LINE Token {settings?.line.has_token && <span className="text-green-600">(已設定)</span>}
                            </label>
                            <input
                                type="password"
                                value={lineToken}
                                onChange={function (e) { setLineToken(e.target.value); }}
                                placeholder="輸入 LINE Notify Token"
                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                            />
                        </div>

                        <button
                            onClick={function () { testNotification('line'); }}
                            disabled={isTesting || !settings?.line.enabled}
                            className="w-full py-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100 flex items-center justify-center gap-2 disabled:opacity-50"
                        >
                            <TestTube className="w-4 h-4" />
                            發送測試訊息
                        </button>
                    </div>
                </div>
            </div>

            {/* 警報設定 */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="p-4 border-b border-gray-100">
                    <div className="flex items-center gap-2">
                        <Settings className="w-5 h-5 text-gray-600" />
                        <h3 className="font-bold text-gray-900">警報類型</h3>
                    </div>
                </div>

                <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { key: 'mainforce_entry', label: '主力進場', icon: '📈' },
                        { key: 'mainforce_exit', label: '主力出場', icon: '📉' },
                        { key: 'price_alert', label: '價格警報', icon: '💰' },
                        { key: 'lstm_signal', label: 'LSTM 信號', icon: '🤖' },
                    ].map(function (item) {
                        return (
                            <label key={item.key} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                                <input
                                    type="checkbox"
                                    checked={settings?.alerts[item.key as keyof typeof settings.alerts] || false}
                                    onChange={function (e) {
                                        if (settings) {
                                            setSettings({
                                                ...settings,
                                                alerts: { ...settings.alerts, [item.key]: e.target.checked }
                                            });
                                        }
                                    }}
                                    className="w-4 h-4 text-indigo-600 rounded"
                                />
                                <span className="text-lg">{item.icon}</span>
                                <span className="text-sm font-medium text-gray-700">{item.label}</span>
                            </label>
                        );
                    })}
                </div>
            </div>

            {/* 通知歷史 */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
                <div className="p-4 border-b border-gray-100">
                    <div className="flex items-center gap-2">
                        <History className="w-5 h-5 text-gray-600" />
                        <h3 className="font-bold text-gray-900">通知歷史</h3>
                    </div>
                </div>

                <div className="divide-y divide-gray-100">
                    {history.map(function (item) {
                        return (
                            <div key={item.id} className="p-4 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    {item.type === 'email' ? (
                                        <Mail className="w-5 h-5 text-blue-500" />
                                    ) : (
                                        <MessageSquare className="w-5 h-5 text-green-500" />
                                    )}
                                    <div>
                                        <p className="font-medium text-gray-900">{item.title}</p>
                                        <p className="text-sm text-gray-500">{item.message}</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                                        已發送
                                    </span>
                                    <p className="text-xs text-gray-400 mt-1">
                                        {new Date(item.timestamp).toLocaleString('zh-TW')}
                                    </p>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
