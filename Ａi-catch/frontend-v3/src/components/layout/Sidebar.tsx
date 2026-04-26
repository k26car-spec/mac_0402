'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    Home,
    Brain,
    TrendingUp,
    Search,
    Bell,
    BarChart3,
    Activity,
    Settings,
    ChevronLeft,
    ChevronRight,
    CandlestickChart,
    ShieldCheck,
    FileText,
    Layers,
    Monitor,
    Briefcase,
    PieChart,
    Newspaper,
    Target
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface NavItem {
    name: string;
    href: string;
    icon: React.ReactNode;
    badge?: number;
}

const navItems: NavItem[] = [
    {
        name: '首頁',
        href: '/',
        icon: <Home className="w-5 h-5" />,
    },
    {
        name: '主儀表板',
        href: '/dashboard',
        icon: <BarChart3 className="w-5 h-5" />,
    },
    {
        name: '🎯 選股決策引擎',
        href: '/dashboard/stock-selector',
        icon: <Target className="w-5 h-5" />,
    },
    {
        name: '🔫 當沖狙擊手 Pro',
        href: '/dashboard/sniper',
        icon: <Target className="w-5 h-5" />,
    },
    {
        name: '📊 綜合分析',
        href: '/dashboard/stock-analysis',
        icon: <PieChart className="w-5 h-5" />,
    },
    {
        name: '📰 產業新聞',
        href: '/news',
        icon: <Newspaper className="w-5 h-5" />,
    },
    {
        name: '🏦 凱基研究報告',
        href: '/dashboard/kgi-research',
        icon: <FileText className="w-5 h-5" />,
    },
    {
        name: 'K 線圖',
        href: '/dashboard/chart',
        icon: <CandlestickChart className="w-5 h-5" />,
    },
    {
        name: '五檔掛單',
        href: '/dashboard/orderbook',
        icon: <Layers className="w-5 h-5" />,
    },
    {
        name: 'LSTM 預測',
        href: '/dashboard/lstm',
        icon: <Brain className="w-5 h-5" />,
    },
    {
        name: '📈 訂單流分析',
        href: '/dashboard/order-flow',
        icon: <TrendingUp className="w-5 h-5" />,
    },

    {
        name: '🔍 大單監控',
        href: '/dashboard/big-order',
        icon: <Activity className="w-5 h-5" />,
    },
    {
        name: '📊 持有股票',
        href: '/dashboard/portfolio',
        icon: <Briefcase className="w-5 h-5" />,
    },
    {
        name: '🤖 AI績效追蹤',
        href: '/dashboard/ai-performance',
        icon: <Brain className="w-5 h-5" />,
    },
    {
        name: '⚔️ AI 實盤執行官',
        href: '/dashboard/trading-executor',
        icon: <Target className="w-5 h-5" />,
    },
    {
        name: '🔄 撐壓轉折',
        href: '/dashboard/trade-analyzer',
        icon: <TrendingUp className="w-5 h-5" />,
    },
    {
        name: '選股掃描',
        href: '/dashboard/scanner',
        icon: <Search className="w-5 h-5" />,
    },
    {
        name: 'AI 分析',
        href: '/dashboard/ai-report',
        icon: <FileText className="w-5 h-5" />,
    },
    {
        name: '即時數據',
        href: '/dashboard/realtime',
        icon: <Activity className="w-5 h-5" />,
    },
    {
        name: '警報中心',
        href: '/dashboard/alerts',
        icon: <Bell className="w-5 h-5" />,
        badge: 3,
    },
    {
        name: '通知設定',
        href: '/dashboard/notifications',
        icon: <Bell className="w-5 h-5" />,
    },
    {
        name: '系統監控',
        href: '/dashboard/monitor',
        icon: <Monitor className="w-5 h-5" />,
    },
    {
        name: '設定',
        href: '/dashboard/settings',
        icon: <Settings className="w-5 h-5" />,
    },
    {
        name: '管理者',
        href: '/dashboard/admin',
        icon: <ShieldCheck className="w-5 h-5" />,
    },
];

export function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    return (
        <aside
            className={cn(
                "fixed left-0 top-0 z-40 h-screen bg-gray-900 text-white transition-all duration-300",
                collapsed ? "w-16" : "w-64"
            )}
        >
            {/* Logo */}
            <div className="flex h-16 items-center justify-between px-4 border-b border-gray-800">
                {!collapsed && (
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                            <Brain className="w-5 h-5" />
                        </div>
                        <span className="font-bold text-lg">AI Stock</span>
                    </div>
                )}

                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="p-1.5 hover:bg-gray-800 rounded-lg transition-colors"
                >
                    {collapsed ? (
                        <ChevronRight className="w-5 h-5" />
                    ) : (
                        <ChevronLeft className="w-5 h-5" />
                    )}
                </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto py-4">
                <ul className="space-y-1 px-3">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;

                        return (
                            <li key={item.href}>
                                <Link
                                    href={item.href}
                                    className={cn(
                                        "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all",
                                        "hover:bg-gray-800",
                                        isActive && "bg-blue-600 hover:bg-blue-700",
                                        collapsed && "justify-center"
                                    )}
                                    title={collapsed ? item.name : undefined}
                                >
                                    <div className="flex-shrink-0">{item.icon}</div>

                                    {!collapsed && (
                                        <>
                                            <span className="flex-1 text-sm font-medium">
                                                {item.name}
                                            </span>

                                            {item.badge && (
                                                <span className="px-2 py-0.5 text-xs font-semibold bg-red-500 text-white rounded-full">
                                                    {item.badge}
                                                </span>
                                            )}
                                        </>
                                    )}

                                    {collapsed && item.badge && (
                                        <span className="absolute right-2 top-1 w-2 h-2 bg-red-500 rounded-full" />
                                    )}
                                </Link>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            {/* Footer */}
            {!collapsed && (
                <div className="border-t border-gray-800 p-4">
                    <div className="space-y-2 text-xs text-gray-400">
                        <div className="flex items-center justify-between">
                            <span>後端 API</span>
                            <span className="flex items-center gap-1">
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                運行中
                            </span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span>WebSocket</span>
                            <span className="flex items-center gap-1">
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                                已連線
                            </span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span>LSTM 模型</span>
                            <span className="text-white">6 個就緒</span>
                        </div>
                    </div>
                </div>
            )}
        </aside>
    );
}
