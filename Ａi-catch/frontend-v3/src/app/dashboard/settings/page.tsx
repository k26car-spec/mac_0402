'use client';

import { Settings, Bell, User, Database, Palette, Shield, Save } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState('general');

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div>
                <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                    <Settings className="w-8 h-8 text-blue-600" />
                    設定
                </h1>
                <p className="text-gray-600 mt-2">自訂您的分析系統偏好設定</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Sidebar */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <nav className="space-y-1">
                        {[
                            { id: 'general', icon: <Settings className="w-5 h-5" />, label: '一般設定' },
                            { id: 'notifications', icon: <Bell className="w-5 h-5" />, label: '通知設定' },
                            { id: 'account', icon: <User className="w-5 h-5" />, label: '帳戶設定' },
                            { id: 'data', icon: <Database className="w-5 h-5" />, label: '數據設定' },
                            { id: 'appearance', icon: <Palette className="w-5 h-5" />, label: '外觀設定' },
                            { id: 'security', icon: <Shield className="w-5 h-5" />, label: '安全設定' },
                        ].map((item) => (
                            <button
                                key={item.id}
                                onClick={() => setActiveTab(item.id)}
                                className={cn(
                                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
                                    activeTab === item.id
                                        ? "bg-blue-50 text-blue-600"
                                        : "text-gray-700 hover:bg-gray-100"
                                )}
                            >
                                {item.icon}
                                <span className="font-medium">{item.label}</span>
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Content */}
                <div className="lg:col-span-3 space-y-6">
                    {activeTab === 'general' && (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-bold text-gray-900 mb-6">一般設定</h2>

                            <div className="space-y-6">
                                <SettingItem
                                    label="語言"
                                    description="選擇介面語言"
                                >
                                    <select className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                                        <option>繁體中文</option>
                                        <option>English</option>
                                    </select>
                                </SettingItem>

                                <SettingItem
                                    label="時區"
                                    description="設定您的時區"
                                >
                                    <select className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                                        <option>Asia/Taipei (GMT+8)</option>
                                    </select>
                                </SettingItem>

                                <SettingItem
                                    label="自動更新"
                                    description="啟用數據自動更新"
                                >
                                    <ToggleSwitch defaultChecked />
                                </SettingItem>

                                <SettingItem
                                    label="更新間隔"
                                    description="設定數據更新頻率"
                                >
                                    <select className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                                        <option>每 5 秒</option>
                                        <option>每 10 秒</option>
                                        <option>每 30 秒</option>
                                        <option>每 1 分鐘</option>
                                    </select>
                                </SettingItem>
                            </div>
                        </div>
                    )}

                    {activeTab === 'notifications' && (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-bold text-gray-900 mb-6">通知設定</h2>

                            <div className="space-y-6">
                                <SettingItem
                                    label="主力進場警報"
                                    description="當偵測到主力進場時通知"
                                >
                                    <ToggleSwitch defaultChecked />
                                </SettingItem>

                                <SettingItem
                                    label="主力出場警報"
                                    description="當偵測到主力出場時通知"
                                >
                                    <ToggleSwitch defaultChecked />
                                </SettingItem>

                                <SettingItem
                                    label="LSTM 預測更新"
                                    description="當 LSTM 模型更新預測時通知"
                                >
                                    <ToggleSwitch defaultChecked />
                                </SettingItem>

                                <SettingItem
                                    label="價格突破警報"
                                    description="當股價突破設定價位時通知"
                                >
                                    <ToggleSwitch />
                                </SettingItem>

                                <SettingItem
                                    label="Email 通知"
                                    description="透過 Email 接收重要警報"
                                >
                                    <ToggleSwitch />
                                </SettingItem>

                                <SettingItem
                                    label="信心度門檻"
                                    description="只有信心度超過此值才發送警報"
                                >
                                    <input
                                        type="number"
                                        defaultValue={75}
                                        min={0}
                                        max={100}
                                        className="w-24 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                    <span className="ml-2 text-gray-500">%</span>
                                </SettingItem>
                            </div>
                        </div>
                    )}

                    {activeTab === 'account' && (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-bold text-gray-900 mb-6">帳戶設定</h2>

                            <div className="space-y-6">
                                <SettingItem
                                    label="使用者名稱"
                                    description="您的顯示名稱"
                                >
                                    <input
                                        type="text"
                                        defaultValue="使用者"
                                        className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </SettingItem>

                                <SettingItem
                                    label="Email"
                                    description="用於接收通知的 Email"
                                >
                                    <input
                                        type="email"
                                        placeholder="your@email.com"
                                        className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </SettingItem>
                            </div>
                        </div>
                    )}

                    {(activeTab === 'data' || activeTab === 'appearance' || activeTab === 'security') && (
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-bold text-gray-900 mb-6">
                                {activeTab === 'data' && '數據設定'}
                                {activeTab === 'appearance' && '外觀設定'}
                                {activeTab === 'security' && '安全設定'}
                            </h2>

                            <div className="text-center py-12">
                                <Settings className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                                <p className="text-gray-600">此功能開發中...</p>
                            </div>
                        </div>
                    )}

                    {/* Save Button */}
                    <div className="flex justify-end">
                        <button className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
                            <Save className="w-5 h-5" />
                            儲存設定
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Setting Item Component
function SettingItem({
    label,
    description,
    children,
}: {
    label: string;
    description: string;
    children: React.ReactNode;
}) {
    return (
        <div className="flex items-center justify-between py-4 border-b border-gray-100 last:border-0">
            <div>
                <div className="font-medium text-gray-900">{label}</div>
                <div className="text-sm text-gray-600">{description}</div>
            </div>
            <div className="flex items-center">{children}</div>
        </div>
    );
}

// Toggle Switch Component
function ToggleSwitch({ defaultChecked = false }: { defaultChecked?: boolean }) {
    const [checked, setChecked] = useState(defaultChecked);

    return (
        <button
            onClick={() => setChecked(!checked)}
            className={cn(
                "relative w-12 h-6 rounded-full transition-colors",
                checked ? "bg-blue-600" : "bg-gray-300"
            )}
        >
            <span
                className={cn(
                    "absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform",
                    checked && "translate-x-6"
                )}
            />
        </button>
    );
}
