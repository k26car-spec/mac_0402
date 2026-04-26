import React from 'react';
import { TrendingUp, AlertTriangle, CheckCircle, Info, Target, Shield } from 'lucide-react';
import type { DipAnalysis } from '@/types/analysis';
import { cn } from '@/lib/utils';

interface DipAnalysisCardProps {
    analysis: DipAnalysis;
}

const DipAnalysisCard: React.FC<DipAnalysisCardProps> = ({ analysis }) => {
    const { quality, score, confidence, reasons, warnings, passed } = analysis;

    // 定義顏色與圖標
    const getQualityStatus = () => {
        switch (quality) {
            case '強力反彈訊號':
                return { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: <TrendingUp className="w-5 h-5" /> };
            case '止跌確認':
                return { color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', icon: <CheckCircle className="w-5 h-5" /> };
            case '支撐測試中':
                return { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: <Info className="w-5 h-5" /> };
            case '接刀風險':
                return { color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200', icon: <AlertTriangle className="w-5 h-5 text-gray-400" /> };
            default:
                return { color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200', icon: <Info className="w-5 h-5" /> };
        }
    };

    const status = getQualityStatus();

    return (
        <div className={cn("rounded-xl border shadow-sm overflow-hidden bg-white", status.border)}>
            <div className={cn("px-4 py-3 border-b flex items-center justify-between", status.bg, status.border)}>
                <div className="flex items-center gap-2">
                    {status.icon}
                    <h3 className={cn("font-bold", status.color)}>
                        低點分析: {quality}
                    </h3>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <span className="text-[10px] uppercase tracking-wider text-gray-400 font-bold block">評分</span>
                        <span className={cn("text-lg font-black tabular-nums", status.color)}>{score}</span>
                    </div>
                    <div className="text-right">
                        <span className="text-[10px] uppercase tracking-wider text-gray-400 font-bold block">信心</span>
                        <span className="text-lg font-black tabular-nums text-gray-700">{confidence}%</span>
                    </div>
                </div>
            </div>

            <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 止跌理由 */}
                <div className="space-y-2">
                    <h4 className="text-xs font-bold text-gray-400 uppercase flex items-center gap-1">
                        <CheckCircle className="w-3 h-3 text-green-500" /> 止跌訊號
                    </h4>
                    {reasons.length > 0 ? (
                        <ul className="space-y-1">
                            {reasons.map((reason, idx) => (
                                <li key={idx} className="text-sm text-gray-700 flex items-start gap-1.5">
                                    <span className="text-green-500 mt-1">•</span>
                                    {reason}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-xs text-gray-400 italic">暫無明顯止跌訊號</p>
                    )}
                </div>

                {/* 風險警示 */}
                <div className="space-y-2 text-right md:text-left">
                    <h4 className="text-xs font-bold text-gray-400 uppercase flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3 text-red-400" /> 破底風險
                    </h4>
                    {warnings.length > 0 ? (
                        <ul className="space-y-1">
                            {warnings.map((warning, idx) => (
                                <li key={idx} className="text-sm text-red-600/80 flex items-start gap-1.5">
                                    <span className="text-red-400 mt-1">•</span>
                                    {warning}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-xs text-green-600/70 italic">未偵測到明顯破底風險</p>
                    )}
                </div>
            </div>

            {/* 建議區塊 */}
            <div className="px-4 py-3 bg-gray-50/50 border-t border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-4 text-xs">
                    <div className="flex items-center gap-1">
                        <Target className="w-3.5 h-3.5 text-blue-500" />
                        <span className="text-gray-500">建議動作:</span>
                        <span className={cn("font-bold", passed ? "text-red-600" : "text-gray-600")}>
                            {passed ? "分批布局" : "繼續觀望"}
                        </span>
                    </div>
                    <div className="flex items-center gap-1">
                        <Shield className="w-3.5 h-3.5 text-indigo-500" />
                        <span className="text-gray-500">風險控制:</span>
                        <span className="font-bold text-gray-700">嚴守支撐位</span>
                    </div>
                </div>
                <div className="text-[10px] text-gray-400 font-medium">
                    AI 增強型回檔分析模型 v3.0
                </div>
            </div>
        </div>
    );
};

export default DipAnalysisCard;
