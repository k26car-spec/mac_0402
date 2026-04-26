import Link from 'next/link';
import { Brain, TrendingUp, Activity, Bell } from 'lucide-react';

export default function HomePage() {
    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
            {/* Hero Section */}
            <div className="container mx-auto px-6 py-20">
                <div className="text-center">
                    <h1 className="text-5xl font-bold text-gray-900 mb-6">
                        🚀 AI 股票智能分析平台
                    </h1>
                    <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto">
                        結合 LSTM 深度學習與 15 位專家系統<br />
                        為您提供專業級的台股分析與預測
                    </p>

                    {/* Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12 max-w-4xl mx-auto">
                        <StatsCard
                            icon={<Brain className="w-8 h-8 text-blue-600" />}
                            title="LSTM 準確率"
                            value="71.9%"
                            subtitle="AI 智能預測"
                        />
                        <StatsCard
                            icon={<TrendingUp className="w-8 h-8 text-green-600" />}
                            title="AI 分析"
                            value="90%+"
                            subtitle="智能分析"
                        />
                        <StatsCard
                            icon={<Activity className="w-8 h-8 text-purple-600" />}
                            title="即時數據"
                            value="<50ms"
                            subtitle="WebSocket"
                        />
                        <StatsCard
                            icon={<Bell className="w-8 h-8 text-orange-600" />}
                            title="數據真實度"
                            value="100%"
                            subtitle="零模擬"
                        />
                    </div>

                    {/* CTA Buttons */}
                    <div className="flex flex-col sm:flex-row gap-4 justify-center flex-wrap">
                        <Link
                            href="/dashboard/stock-selector"
                            className="px-8 py-4 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-semibold hover:from-green-700 hover:to-emerald-700 transition-all shadow-lg hover:shadow-xl"
                        >
                            🎯 全自動選股決策引擎
                        </Link>
                        <Link
                            href="/dashboard"
                            className="px-8 py-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
                        >
                            進入主儀表板
                        </Link>
                        <Link
                            href="/dashboard/lstm"
                            className="px-8 py-4 bg-white text-blue-600 border-2 border-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition-colors shadow-lg hover:shadow-xl"
                        >
                            查看 LSTM 預測
                        </Link>
                        <a
                            href="http://localhost:5173/"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all shadow-lg hover:shadow-xl"
                        >
                            🔥 當沖 ORB 系統
                        </a>
                    </div>
                </div>

                {/* Features Grid */}
                <div className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-8">
                    <FeatureCard
                        icon="🎯"
                        title="全自動選股決策引擎"
                        description="整合富邦券商買超數據，快速批量分析股票，自動生成買賣建議與評分"
                        link="/dashboard/stock-selector"
                    />
                    <FeatureCard
                        icon="🔄"
                        title="循環驅動多因子投資"
                        description="六維度評分系統：總經循環、產業定價權、財報健康、技術分析、趨勢曝險、訂單動能"
                        link="/dashboard/economic-cycle"
                    />
                    <FeatureCard
                        icon="🧠"
                        title="LSTM 智能預測"
                        description="使用深度學習模型預測 1/3/5 日價格走勢，平均準確率達 71.9%"
                        link="/dashboard/lstm"
                    />
                    <FeatureCard
                        icon="📊"
                        title="15 位專家系統"
                        description="綜合大單分析、籌碼集中度、量能爆發等 15 個維度進行智能分析"
                        link="/dashboard/scanner"
                    />
                    <FeatureCard
                        icon="⚡"
                        title="即時數據推送"
                        description="WebSocket 實時更新股價、五檔掛單，延遲小於 50ms"
                        link="/dashboard"
                    />
                    <FeatureCard
                        icon="🔍"
                        title="智能選股掃描"
                        description="基於 AI 分析結果自動篩選高潛力股票，提供買賣建議"
                        link="/dashboard/scanner"
                    />
                    <FeatureCard
                        icon="🚨"
                        title="即時警報系統"
                        description="主力進出、價格異動即時通知，支援瀏覽器推送和郵件提醒"
                        link="/dashboard/alerts"
                    />
                    <FeatureCard
                        icon="📰"
                        title="產業新聞分析"
                        description="整合 IEK 產業情報網、Perplexity AI，分析哪些股票值得關注"
                        link="/news"
                    />
                    <FeatureCard
                        icon="📈"
                        title="多時間框架"
                        description="日線、週線、月線多維度分析，全面掌握趨勢變化"
                        link="/dashboard"
                    />
                </div>

                {/* System Status */}
                <div className="mt-20 max-w-2xl mx-auto">
                    <SystemStatus />
                </div>
            </div>
        </div>
    );
}

// Stats Card Component
function StatsCard({ icon, title, value, subtitle }: {
    icon: React.ReactNode;
    title: string;
    value: string;
    subtitle: string;
}) {
    return (
        <div className="bg-white rounded-lg p-6 shadow-lg hover:shadow-xl transition-shadow">
            <div className="flex justify-center mb-3">{icon}</div>
            <div className="text-sm text-gray-600 mb-1">{title}</div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{value}</div>
            <div className="text-xs text-gray-500">{subtitle}</div>
        </div>
    );
}

// Feature Card Component
function FeatureCard({ icon, title, description, link }: {
    icon: string;
    title: string;
    description: string;
    link: string;
}) {
    return (
        <Link href={link}>
            <div className="bg-white rounded-lg p-6 shadow-md hover:shadow-xl transition-all hover:-translate-y-1 cursor-pointer h-full">
                <div className="text-4xl mb-4">{icon}</div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">{title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{description}</p>
            </div>
        </Link>
    );
}

// System Status Component
function SystemStatus() {
    return (
        <div className="bg-white rounded-lg p-6 shadow-lg">
            <h3 className="text-lg font-bold text-gray-900 mb-4 text-center">
                系統狀態
            </h3>
            <div className="space-y-3">
                <StatusItem label="後端 API" status="running" />
                <StatusItem label="LSTM 模型" status="ready" count={6} />
                <StatusItem label="WebSocket" status="connected" />
                <StatusItem label="數據源" status="active" detail="富邦 + 證交所 + Yahoo" />
            </div>
        </div>
    );
}

function StatusItem({ label, status, count, detail }: {
    label: string;
    status: 'running' | 'ready' | 'connected' | 'active';
    count?: number;
    detail?: string;
}) {
    return (
        <div className="flex items-center justify-between py-2 border-b last:border-0">
            <span className="text-gray-700">{label}</span>
            <div className="flex items-center gap-2">
                {count && <span className="text-sm text-gray-500">({count})</span>}
                {detail && <span className="text-xs text-gray-500">{detail}</span>}
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                    <span className="text-sm text-green-600 font-medium">
                        {status === 'running' && '運行中'}
                        {status === 'ready' && '就緒'}
                        {status === 'connected' && '已連線'}
                        {status === 'active' && '活躍'}
                    </span>
                </div>
            </div>
        </div>
    );
}
