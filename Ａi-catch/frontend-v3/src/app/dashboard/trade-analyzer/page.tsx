'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
    Target, TrendingUp, AlertTriangle, CheckCircle, Calculator, RotateCcw,
    BookOpen, DollarSign, Layers, ArrowUpCircle, ArrowDownCircle, Maximize2,
    HelpCircle, Activity, BarChart2, ClipboardList, PieChart, Search, RefreshCw,
    TrendingDown, Shield, Zap, Star, Heart, X, Mail, Send
} from 'lucide-react';

// API Response Types
interface SupportResistanceLevel {
    price: number;
    type: string;
    strength: number;
    source: string;
    description: string;
    distance_pct: number;
}

interface TrendStatus {
    short_term: string;
    mid_term: string;
    long_term: string;
    overall: string;
    strength: number;
    ma_arrangement: string;
    ma_trend: string;
}

interface ReversalSignal {
    type: string;
    strength: number;
    confidence: number;
    signals: string[];
    description: string;
    action: string;
}

interface RiskRewardAnalysis {
    risk_reward_ratio: number;
    potential_upside_pct: number;
    potential_downside_pct: number;
    target_price: number;
    stop_loss_price: number;
    assessment: string;
}

interface SRData {
    stock_code: string;
    stock_name: string;
    current_price: number;
    resistance_levels: SupportResistanceLevel[];
    support_levels: SupportResistanceLevel[];
    trend_status: TrendStatus;
    reversal_signal: ReversalSignal;
    risk_reward_analysis: RiskRewardAnalysis;
    recommendation: string;
    overall_score: number;
}

const TradeAnalyzer = () => {
    const [stockId, setStockId] = useState('');
    const [stockName, setStockName] = useState('');
    const [activeTab, setActiveTab] = useState('sr-analysis');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [srData, setSrData] = useState<SRData | null>(null);

    // Checklist - 10 items with real data checking
    const [checklist, setChecklist] = useState([
        { id: 1, category: '趨勢', text: '股價站上 20日均線且月線翻揚?', checked: false, weight: 10, reason: '' },
        { id: 2, category: '趨勢', text: '均線呈現多頭排列 (5>10>20>60)?', checked: false, weight: 10, reason: '' },
        { id: 3, category: '趨勢', text: '布林通道壓縮後開口向上?', checked: false, weight: 10, reason: '' },
        { id: 4, category: '動能', text: '成交量大於5日均量或溫和遞增?', checked: false, weight: 10, reason: '' },
        { id: 5, category: '動能', text: '出現突破缺口或逃逸缺口未回補?', checked: false, weight: 10, reason: '' },
        { id: 6, category: '籌碼', text: '法人近期由賣轉買或連續買超?', checked: false, weight: 10, reason: '' },
        { id: 7, category: '型態', text: '突破前高/頸線/完成底部型態?', checked: false, weight: 15, reason: '' },
        { id: 8, category: '指標', text: 'MACD紅柱增加或KD低檔黃金交叉?', checked: false, weight: 10, reason: '' },
        { id: 9, category: '支撐', text: '股價回測斐波那契支撐有守?', checked: false, weight: 10, reason: '' },
        { id: 10, category: '支撐', text: '位於大量成交籌碼區之上?', checked: false, weight: 5, reason: '' },
    ]);

    // Risk calculator
    const [entryPrice, setEntryPrice] = useState<number | ''>('');
    const [stopLoss, setStopLoss] = useState<number | ''>('');
    const [targetPrice, setTargetPrice] = useState<number | ''>('');
    const [capital, setCapital] = useState<number | ''>(100000);
    const [riskPercent, setRiskPercent] = useState<number | ''>(2);

    // Fibonacci
    const [fibHigh, setFibHigh] = useState<number | ''>('');
    const [fibLow, setFibLow] = useState<number | ''>('');
    const [fibTrend, setFibTrend] = useState<'uptrend' | 'downtrend'>('uptrend');

    // Calculated
    const [score, setScore] = useState(0);
    const [recommendation, setRecommendation] = useState('');
    const [positionSize, setPositionSize] = useState(0);
    const [riskRewardRatio, setRiskRewardRatio] = useState(0);

    // Volume Profile 籌碼分析
    const [volumeProfile, setVolumeProfile] = useState<any>(null);

    // 當沖判讀
    const [intradayHigh, setIntradayHigh] = useState<number | ''>('');
    const [intradayLow, setIntradayLow] = useState<number | ''>('');
    const [intradayCurrent, setIntradayCurrent] = useState<number | ''>('');

    // 我的最愛 (從 localStorage 讀取)
    const [favorites, setFavorites] = useState<{ code: string, name: string }[]>([]);

    // 初始化時從 localStorage 讀取我的最愛
    useEffect(() => {
        const saved = localStorage.getItem('tradeAnalyzerFavorites');
        if (saved) {
            try {
                setFavorites(JSON.parse(saved));
            } catch (e) {
                console.error('Failed to parse favorites', e);
            }
        }
    }, []);

    // 儲存我的最愛到 localStorage
    const saveFavorites = (newFavorites: { code: string, name: string }[]) => {
        setFavorites(newFavorites);
        localStorage.setItem('tradeAnalyzerFavorites', JSON.stringify(newFavorites));
    };

    // 新增/移除我的最愛
    const toggleFavorite = () => {
        if (!stockId) return;
        const exists = favorites.find(f => f.code === stockId);
        if (exists) {
            // 移除
            saveFavorites(favorites.filter(f => f.code !== stockId));
        } else {
            // 新增
            saveFavorites([...favorites, { code: stockId, name: stockName || stockId }]);
        }
    };

    // 檢查是否為我的最愛
    const isFavorite = favorites.some(f => f.code === stockId);

    // 發送報告
    const [sendingReport, setSendingReport] = useState(false);
    const [reportStatus, setReportStatus] = useState<{ success: boolean; message: string } | null>(null);

    const sendReport = async () => {
        if (!stockId || !srData) return;
        setSendingReport(true);
        setReportStatus(null);
        try {
            const res = await fetch(`http://localhost:8000/api/support-resistance/send-report/${stockId}?send_email=true`, {
                method: 'POST'
            });
            const result = await res.json();
            if (result.success && result.email_sent?.success) {
                setReportStatus({ success: true, message: `報告已發送至 ${result.email_sent.recipients} 位收件人` });
            } else {
                setReportStatus({ success: false, message: result.email_sent?.message || '發送失敗' });
            }
        } catch (err) {
            setReportStatus({ success: false, message: '發送失敗，請檢查後端服務' });
        } finally {
            setSendingReport(false);
        }
    };

    // Fetch API data
    const fetchSRData = useCallback(async (code: string) => {
        if (!code) return;
        setLoading(true);
        setError('');
        try {
            // 同時呼叫四個 API
            const [srRes, compRes, vpRes, intradayRes] = await Promise.all([
                fetch(`http://localhost:8000/api/support-resistance/analyze/${code}`),
                fetch(`http://localhost:8000/api/stock-analysis/comprehensive/${code}`),
                fetch(`http://localhost:8000/api/volume-profile/summary/${code}`).catch(() => null),
                fetch(`http://localhost:8000/api/support-resistance/intraday-data/${code}`).catch(() => null)
            ]);

            const srResult = await srRes.json();
            const compResult = await compRes.json();
            const vpResult = vpRes ? await vpRes.json().catch(() => null) : null;
            const intradayResult = intradayRes ? await intradayRes.json().catch(() => null) : null;

            if (srResult.success && srResult.data) {
                const data = srResult.data;
                setSrData(data);
                setStockName(data.stock_name);

                // 設置 Volume Profile 數據
                if (vpResult?.success) {
                    setVolumeProfile(vpResult);
                }

                // 設置當沖數據 (自動帶入，四捨五入到小數點兩位)
                if (intradayResult?.success) {
                    setIntradayHigh(Number(Number(intradayResult.range_high).toFixed(2)));
                    setIntradayLow(Number(Number(intradayResult.range_low).toFixed(2)));
                    setIntradayCurrent(Number(Number(intradayResult.current).toFixed(2)));
                }

                // 自動填入風控資料
                if (data.current_price) setEntryPrice(data.current_price);
                if (data.risk_reward_analysis?.stop_loss_price) setStopLoss(data.risk_reward_analysis.stop_loss_price);
                if (data.risk_reward_analysis?.target_price) setTargetPrice(data.risk_reward_analysis.target_price);

                // 自動填入斐波那契高低點
                if (data.resistance_levels?.length > 0 && data.support_levels?.length > 0) {
                    const highestResistance = Math.max(...data.resistance_levels.map((r: SupportResistanceLevel) => r.price));
                    const lowestSupport = Math.min(...data.support_levels.map((s: SupportResistanceLevel) => s.price));
                    setFibHigh(highestResistance);
                    setFibLow(lowestSupport);
                } else if (data.current_price) {
                    setFibHigh(Math.round(data.current_price * 1.1 * 100) / 100);
                    setFibLow(Math.round(data.current_price * 0.9 * 100) / 100);
                }

                // 使用 comprehensive API 的完整數據更新清單
                autoUpdateChecklist(data, compResult, vpResult);
            } else {
                setError(srResult.detail || '無法取得資料');
            }
        } catch (err) {
            console.error('API Error:', err);
            setError('API 連線失敗，請確認後端服務是否啟動');
        } finally {
            setLoading(false);
        }
    }, []);

    // 使用真實 API 數據自動判斷所有檢查項目
    const autoUpdateChecklist = (srData: SRData, compData: any, vpData?: any) => {
        const tech = compData?.technical_indicators || {};
        const vol = compData?.volume_price_analysis || {};
        const inst = compData?.institutional_trading || {};
        const vp = vpData || {};  // Volume Profile 數據
        const currentPrice = srData.current_price || tech.current_price || 0;
        const ma20 = tech.ma20 || 0;
        const ma60 = tech.ma60 || 0;

        setChecklist(prev => prev.map(item => {
            let checked = false;
            let reason = '';

            switch (item.id) {
                case 1: // 股價站上20日均線且月線翻揚
                    checked = currentPrice > ma20 && srData.trend_status?.mid_term === 'bullish';
                    reason = checked ? `價格${currentPrice} > MA20(${ma20?.toFixed(1)})` : '';
                    break;

                case 2: // 均線呈現多頭排列
                    const maArr = tech.ma_arrangement || srData.trend_status?.ma_arrangement || '';
                    checked = maArr.includes('多頭');
                    reason = checked ? maArr : '';
                    break;

                case 3: // 布林通道 (使用布林寬度判斷)
                    const bbWidth = tech.bollinger_width || 0;
                    const trend = tech.trend || srData.trend_status?.overall || '';
                    // 布林收窄後突破或趨勢向上
                    checked = (bbWidth > 0 && bbWidth < 15 && trend === '多頭') ||
                        (currentPrice > ma20 && tech.deviation_20d > 0);
                    reason = checked ? `布林寬度: ${bbWidth?.toFixed(1)}%` : '';
                    break;

                case 4: // 成交量大於5日均量
                    const volRatio = vol.volume_ratio || 0;
                    checked = volRatio >= 1.0;
                    reason = checked ? `量比: ${volRatio?.toFixed(2)}` : '';
                    break;

                case 5: // 突破缺口 (使用價量確認)
                    const confirmation = vol.confirmation_signal || '';
                    checked = confirmation === 'bullish_confirmation' ||
                        (vol.key_signals || []).some((s: string) => s.includes('突破'));
                    reason = checked ? vol.volume_price_confirmation : '';
                    break;

                case 6: // 法人近期買超
                    const totalNet = inst.total_net || 0;
                    const foreignNet = inst.foreign_net || 0;
                    const trustNet = inst.trust_net || 0;
                    checked = totalNet > 0 || (foreignNet > 0 && trustNet > 0);
                    reason = checked ? `法人淨買: ${totalNet.toLocaleString()}` : '';
                    break;

                case 7: // 突破前高/型態
                    checked = srData.reversal_signal?.type === 'bullish_reversal' ||
                        (srData.reversal_signal?.signals || []).some(s => s.includes('突破'));
                    reason = checked ? srData.reversal_signal?.description : '';
                    break;

                case 8: // MACD/KD黃金交叉
                    const macdSignal = tech.macd_signal || '';
                    const kd_k = tech.kd_k || 50;
                    const kd_d = tech.kd_d || 50;
                    const macd = tech.macd || 0;
                    checked = macdSignal.includes('多頭') || (kd_k > kd_d && kd_k < 80) || macd > 0;
                    reason = checked ? `MACD: ${macdSignal}, K:${kd_k?.toFixed(0)} D:${kd_d?.toFixed(0)}` : '';
                    break;

                case 9: // 斐波那契支撐有守
                    // 判斷價格是否在支撐位之上
                    const nearestSupport = srData.support_levels?.[0]?.price || 0;
                    checked = currentPrice > nearestSupport && srData.trend_status?.short_term === 'bullish';
                    reason = checked ? `支撐: ${nearestSupport}` : '';
                    break;

                case 10: // 位於大量成交籌碼區之上
                    // 優先使用 Volume Profile，否則使用 VWAP
                    if (vp?.position_analysis) {
                        const pos = vp.position_analysis;
                        checked = pos.position === 'above_value_area' || pos.position === 'upper_value_area';
                        reason = checked ? `${pos.status} (支撐: ${vp.major_support?.price?.toFixed(1)})` : '';
                    } else {
                        const vwap = vol.vwap || 0;
                        const vwapDev = vol.vwap_deviation || 0;
                        checked = vwapDev >= 0;
                        reason = checked ? `VWAP: ${vwap?.toFixed(1)}, 偏離: ${vwapDev?.toFixed(1)}%` : '';
                    }
                    break;
            }

            return { ...item, checked, reason };
        }));
    };

    useEffect(() => {
        const total = checklist.reduce((acc, item) => item.checked ? acc + item.weight : acc, 0);
        setScore(total);
        if (total >= 85) setRecommendation('S級 強力買進 - 各項指標共振');
        else if (total >= 70) setRecommendation('A級 觀察買進 - 趨勢正確');
        else if (total >= 50) setRecommendation('B級 中性觀望 - 多空不明');
        else setRecommendation('C級 弱勢 - 條件不符');
    }, [checklist]);

    useEffect(() => {
        if (entryPrice && stopLoss && capital && riskPercent) {
            const entry = Number(entryPrice), stop = Number(stopLoss);
            if (entry > stop) {
                const riskPerShare = entry - stop;
                const maxRisk = Number(capital) * (Number(riskPercent) / 100);
                setPositionSize(Math.floor(maxRisk / riskPerShare));
                if (targetPrice) {
                    setRiskRewardRatio(Number(((Number(targetPrice) - entry) / riskPerShare).toFixed(2)));
                }
            }
        }
    }, [entryPrice, stopLoss, targetPrice, capital, riskPercent]);

    const toggleCheck = (id: number) => setChecklist(prev => prev.map(item => item.id === id ? { ...item, checked: !item.checked } : item));
    const resetAll = () => {
        setChecklist(prev => prev.map(item => ({ ...item, checked: false })));
        setEntryPrice(''); setStopLoss(''); setTargetPrice(''); setFibHigh(''); setFibLow('');
        setScore(0); setSrData(null); setStockId(''); setStockName('');
    };
    const handleSearch = () => stockId.trim() && fetchSRData(stockId.trim());

    // 台灣慣例: 紅色=漲, 綠色=跌
    const TrendBadge = ({ trend, label }: { trend: string; label: string }) => {
        const colors: Record<string, string> = {
            bullish: 'bg-red-100 text-red-700',   // 多頭=紅色
            bearish: 'bg-green-100 text-green-700', // 空頭=綠色
            sideways: 'bg-gray-100 text-gray-600'
        };
        return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[trend] || colors.sideways}`}>{label}</span>;
    };

    // SR Analysis Panel
    const SRAnalysisPanel = () => (
        <div className="bg-white p-6 rounded-xl shadow-lg border border-slate-200">
            <div className="flex justify-between items-center mb-6 border-b pb-4">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                        <BarChart2 className="text-blue-600" /> 撐壓趨勢轉折分析
                    </h2>
                    <p className="text-slate-500 text-sm mt-1">{srData ? `${srData.stock_name} (${srData.stock_code})` : '請輸入股票代碼'}</p>
                </div>
                {srData && <div className="text-right"><div className="text-sm text-slate-500">當前價格</div><div className="text-3xl font-bold">${srData.current_price}</div></div>}
            </div>
            {loading && <div className="flex items-center justify-center py-12"><RefreshCw className="w-8 h-8 animate-spin text-blue-500" /></div>}
            {error && <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center gap-2"><AlertTriangle className="w-5 h-5" />{error}</div>}
            {srData && !loading && (
                <div className="space-y-6">
                    <div className="bg-slate-50 rounded-xl p-4">
                        <h3 className="font-semibold mb-3 flex items-center gap-2"><Activity className="w-4 h-4 text-blue-500" />趨勢狀態</h3>
                        <div className="flex flex-wrap gap-3">
                            <TrendBadge trend={srData.trend_status.short_term} label={`短期 ${srData.trend_status.short_term === 'bullish' ? '偏多' : srData.trend_status.short_term === 'bearish' ? '偏空' : '盤整'}`} />
                            <TrendBadge trend={srData.trend_status.mid_term} label={`中期 ${srData.trend_status.mid_term === 'bullish' ? '偏多' : '偏空'}`} />
                            <TrendBadge trend={srData.trend_status.long_term} label={`長期 ${srData.trend_status.long_term === 'bullish' ? '偏多' : '偏空'}`} />
                        </div>
                        <div className="mt-3 text-sm text-slate-600">均線: {srData.trend_status.ma_arrangement} | 強度: {srData.trend_status.strength}%</div>
                    </div>
                    <div className={`rounded-xl p-4 ${srData.reversal_signal.type === 'bullish_reversal' ? 'bg-red-50 border-red-200' : srData.reversal_signal.type === 'bearish_reversal' ? 'bg-green-50 border-green-200' : 'bg-slate-50'} border`}>
                        <h3 className="font-semibold mb-3 flex items-center gap-2"><Zap className="w-4 h-4" />轉折訊號 - {srData.reversal_signal.description}</h3>
                        {srData.reversal_signal.signals.map((s, i) => <div key={i} className="flex items-center gap-2 text-sm"><CheckCircle className={`w-4 h-4 ${srData.reversal_signal.type === 'bullish_reversal' ? 'text-red-500' : 'text-green-500'}`} />{s}</div>)}
                        <div className="mt-3 text-sm">強度: {srData.reversal_signal.strength}% | 信心: {(srData.reversal_signal.confidence * 100).toFixed(0)}%</div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                            <h3 className="font-semibold text-red-700 mb-3 flex items-center gap-2"><ArrowUpCircle className="w-4 h-4" />壓力位</h3>
                            {srData.resistance_levels.slice(0, 3).map((l, i) => (
                                <div key={i} className="flex justify-between items-center bg-white rounded-lg p-2 mb-2 border border-red-100">
                                    <div><div className="font-medium text-red-700">${l.price}</div><div className="text-xs text-slate-500">{l.description}</div></div>
                                    <div className="text-sm text-red-600">+{l.distance_pct}%</div>
                                </div>
                            ))}
                        </div>
                        <div className="bg-green-50 rounded-xl p-4 border border-green-100">
                            <h3 className="font-semibold text-green-700 mb-3 flex items-center gap-2"><ArrowDownCircle className="w-4 h-4" />支撐位</h3>
                            {srData.support_levels.slice(0, 3).map((l, i) => (
                                <div key={i} className="flex justify-between items-center bg-white rounded-lg p-2 mb-2 border border-green-100">
                                    <div><div className="font-medium text-green-700">${l.price}</div><div className="text-xs text-slate-500">{l.description}</div></div>
                                    <div className="text-sm text-green-600">-{l.distance_pct}%</div>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                        <h3 className="font-semibold text-blue-700 mb-3 flex items-center gap-2"><Shield className="w-4 h-4" />風險回報</h3>
                        <div className="grid grid-cols-4 gap-4 text-center">
                            <div><div className="text-xs text-slate-500">風報比</div><div className={`text-xl font-bold ${srData.risk_reward_analysis.risk_reward_ratio >= 2 ? 'text-green-600' : 'text-orange-500'}`}>1:{srData.risk_reward_analysis.risk_reward_ratio}</div></div>
                            <div><div className="text-xs text-slate-500">潛在漲幅</div><div className="text-xl font-bold text-red-600">+{srData.risk_reward_analysis.potential_upside_pct}%</div></div>
                            <div><div className="text-xs text-slate-500">潛在跌幅</div><div className="text-xl font-bold text-green-600">-{srData.risk_reward_analysis.potential_downside_pct}%</div></div>
                            <div><div className="text-xs text-slate-500">評分</div><div className={`text-xl font-bold ${srData.overall_score >= 70 ? 'text-green-600' : 'text-yellow-600'}`}>{srData.overall_score}</div></div>
                        </div>
                    </div>

                    {/* 籌碼支撐壓力 */}
                    {volumeProfile && (
                        <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                            <h3 className="font-semibold text-purple-700 mb-3 flex items-center gap-2">
                                <PieChart className="w-4 h-4" />籌碼支撐壓力 (Volume Profile)
                            </h3>
                            <div className="grid grid-cols-3 gap-4">
                                <div className="bg-white rounded-lg p-3 border border-red-200">
                                    <div className="text-xs text-slate-500">上方大量壓力</div>
                                    <div className="text-xl font-bold text-red-600">
                                        ${volumeProfile.major_resistance?.price?.toFixed(1) || '-'}
                                    </div>
                                    <div className="text-xs text-red-500">
                                        +{volumeProfile.major_resistance?.distance_pct?.toFixed(1) || 0}%
                                    </div>
                                </div>
                                <div className="bg-white rounded-lg p-3 border border-purple-200">
                                    <div className="text-xs text-slate-500">主控價位 (POC)</div>
                                    <div className="text-xl font-bold text-purple-600">
                                        ${volumeProfile.poc?.price?.toFixed(1) || '-'}
                                    </div>
                                    <div className="text-xs text-purple-500">
                                        成交量最大
                                    </div>
                                </div>
                                <div className="bg-white rounded-lg p-3 border border-green-200">
                                    <div className="text-xs text-slate-500">下方大量支撐</div>
                                    <div className="text-xl font-bold text-green-600">
                                        ${volumeProfile.major_support?.price?.toFixed(1) || '-'}
                                    </div>
                                    <div className="text-xs text-green-500">
                                        -{volumeProfile.major_support?.distance_pct?.toFixed(1) || 0}%
                                    </div>
                                </div>
                            </div>
                            {volumeProfile.position_analysis && (
                                <div className={`mt-3 p-2 rounded-lg text-sm ${volumeProfile.position_analysis.signal === 'bullish' ? 'bg-red-100 text-red-700' :
                                    volumeProfile.position_analysis.signal === 'bearish' ? 'bg-green-100 text-green-700' :
                                        'bg-slate-100 text-slate-600'
                                    }`}>
                                    📊 {volumeProfile.position_analysis.status}: {volumeProfile.position_analysis.description}
                                </div>
                            )}
                        </div>
                    )}

                    <div className={`p-4 rounded-xl ${srData.reversal_signal.action === 'buy' ? 'bg-red-100 text-red-800' : srData.reversal_signal.action === 'sell' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-700'}`}>
                        <h4 className="font-bold mb-1">AI 建議：</h4><p>{srData.recommendation}</p>
                    </div>
                </div>
            )}
            {!srData && !loading && !error && <div className="text-center py-12 text-slate-400"><BarChart2 className="w-12 h-12 mx-auto mb-3 opacity-30" /><p>輸入股票代碼並按搜尋開始分析</p></div>}
        </div>
    );

    // Checklist Panel
    const ChecklistPanel = () => (
        <div className="bg-white p-6 rounded-xl shadow-lg border border-slate-200">
            <div className="flex justify-between items-center mb-6 border-b pb-4">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                        <ClipboardList className="text-blue-600" />綜合分析戰報
                    </h2>
                    <p className="text-xs text-slate-500 mt-1">✨ 基於真實 API 數據自動判斷</p>
                </div>
                <div className="text-right">
                    <div className="text-sm text-slate-500">評分</div>
                    <div className={`text-5xl font-extrabold ${score >= 80 ? 'text-green-600' : score >= 60 ? 'text-blue-600' : 'text-red-500'}`}>
                        {score}<span className="text-lg text-slate-400">/100</span>
                    </div>
                </div>
            </div>
            <div className="space-y-3 mb-8">
                {checklist.map(item => (
                    <div key={item.id} onClick={() => toggleCheck(item.id)}
                        className={`p-4 rounded-lg cursor-pointer border-l-4 shadow-sm hover:shadow-md transition-all ${item.checked ? 'border-l-green-500 bg-green-50' : 'border-l-slate-300 bg-white'}`}>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className={`w-6 h-6 rounded-full flex items-center justify-center border-2 shrink-0 ${item.checked ? 'bg-green-500 border-green-500' : 'border-slate-300'}`}>
                                    {item.checked && <CheckCircle className="w-4 h-4 text-white" />}
                                </div>
                                <div>
                                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full mr-2 ${item.category === '趨勢' ? 'bg-purple-100 text-purple-700' :
                                        item.category === '動能' ? 'bg-orange-100 text-orange-700' :
                                            item.category === '籌碼' ? 'bg-blue-100 text-blue-700' :
                                                item.category === '型態' ? 'bg-pink-100 text-pink-700' :
                                                    item.category === '指標' ? 'bg-cyan-100 text-cyan-700' :
                                                        'bg-green-100 text-green-700'
                                        }`}>{item.category}</span>
                                    <span className={`font-medium ${item.checked ? 'text-slate-900' : 'text-slate-500'}`}>{item.text}</span>
                                </div>
                            </div>
                            <div className="text-right shrink-0">
                                <div className={`text-sm font-bold ${item.checked ? 'text-green-600' : 'text-slate-400'}`}>+{item.weight}分</div>
                            </div>
                        </div>
                        {item.checked && item.reason && (
                            <div className="mt-2 ml-10 text-xs text-green-600 bg-green-100 px-2 py-1 rounded inline-block">
                                📊 {item.reason}
                            </div>
                        )}
                    </div>
                ))}
            </div>
            <div className={`p-5 rounded-xl ${score >= 70 ? 'bg-gradient-to-r from-green-50 to-emerald-50 text-green-900 border border-green-200' : 'bg-slate-100 text-slate-600'}`}>
                <h4 className="font-bold text-lg mb-1">🤖 AI 決策建議：</h4>
                <p className="text-lg font-medium">{recommendation}</p>
                {srData && (
                    <p className="text-xs mt-2 opacity-70">
                        數據來源: 技術指標 API + 法人籌碼 API + 量價分析 API
                    </p>
                )}
            </div>
        </div>
    );

    // Risk Calculator
    const RiskCalcPanel = () => (
        <div className="bg-white p-6 rounded-xl shadow-lg border border-slate-200">
            <div className="flex items-center gap-2 mb-6 border-b pb-4"><Calculator className="text-blue-600" /><h2 className="text-2xl font-bold text-slate-800">部位風控計算</h2></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-5">
                    <div><label className="block text-sm font-medium mb-1">總資金</label><input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))} className="w-full px-4 py-2 border rounded-lg" /></div>
                    <div><label className="block text-sm font-medium mb-1">單筆風險 %</label><input type="number" value={riskPercent} onChange={e => setRiskPercent(Number(e.target.value))} className="w-full px-4 py-2 border rounded-lg" /></div>
                    <div><label className="block text-sm font-medium mb-1">進場價</label><input type="number" value={entryPrice} onChange={e => setEntryPrice(Number(e.target.value))} className="w-full px-4 py-2 border rounded-lg" /></div>
                    <div><label className="block text-sm font-medium mb-1 text-red-600">停損價</label><input type="number" value={stopLoss} onChange={e => setStopLoss(Number(e.target.value))} className="w-full px-4 py-2 border border-red-200 bg-red-50 rounded-lg" /></div>
                    <div><label className="block text-sm font-medium mb-1 text-green-600">目標價</label><input type="number" value={targetPrice} onChange={e => setTargetPrice(Number(e.target.value))} className="w-full px-4 py-2 border border-green-200 bg-green-50 rounded-lg" /></div>
                </div>
                <div className="bg-slate-50 rounded-xl p-6 flex flex-col justify-center space-y-6">
                    <div className="text-center"><div className="text-sm text-slate-500">建議股數</div><div className="text-3xl font-bold text-blue-600">{positionSize.toLocaleString()} <span className="text-sm">股</span></div><div className="text-sm text-slate-400">(約 {(positionSize / 1000).toFixed(1)} 張)</div></div>
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                        <div><div className="text-xs text-slate-500">投入成本</div><div className="font-semibold">${entryPrice && positionSize ? (Number(entryPrice) * positionSize).toLocaleString() : 0}</div></div>
                        <div><div className="text-xs text-slate-500">最大虧損</div><div className="font-semibold text-red-600">-${capital && riskPercent ? (Number(capital) * Number(riskPercent) / 100).toLocaleString() : 0}</div></div>
                    </div>
                    {riskRewardRatio > 0 && <div className="text-center bg-white p-3 rounded-lg border shadow-sm"><div className="text-xs text-slate-500">損益比</div><div className={`text-xl font-bold ${riskRewardRatio >= 3 ? 'text-green-600' : 'text-orange-500'}`}>1 : {riskRewardRatio}</div></div>}
                </div>
            </div>
        </div>
    );

    // Fibonacci Tool
    const FibPanel = () => {
        const h = Number(fibHigh), l = Number(fibLow), valid = h > l && h > 0;
        const calc = (r: number) => valid ? (fibTrend === 'uptrend' ? h - (h - l) * r : l + (h - l) * r).toFixed(2) : '-';
        return (
            <div className="bg-white p-6 rounded-xl shadow-lg border border-slate-200">
                <div className="flex items-center gap-2 mb-6 border-b pb-4"><Layers className="text-blue-600" /><h2 className="text-2xl font-bold">斐波那契回撤</h2></div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-6">
                        <div className="flex gap-2 bg-slate-100 p-1 rounded-lg">
                            <button onClick={() => setFibTrend('uptrend')} className={`flex-1 py-2 rounded-md text-sm font-bold ${fibTrend === 'uptrend' ? 'bg-white text-green-600 shadow' : 'text-slate-500'}`}><ArrowUpCircle className="w-4 h-4 inline mr-1" />上升趨勢</button>
                            <button onClick={() => setFibTrend('downtrend')} className={`flex-1 py-2 rounded-md text-sm font-bold ${fibTrend === 'downtrend' ? 'bg-white text-red-600 shadow' : 'text-slate-500'}`}><ArrowDownCircle className="w-4 h-4 inline mr-1" />下降趨勢</button>
                        </div>
                        <div><label className="block text-sm font-medium mb-1">波段高點</label><input type="number" value={fibHigh} onChange={e => setFibHigh(Number(e.target.value))} className="w-full px-4 py-2 border rounded-lg" /></div>
                        <div><label className="block text-sm font-medium mb-1">波段低點</label><input type="number" value={fibLow} onChange={e => setFibLow(Number(e.target.value))} className="w-full px-4 py-2 border rounded-lg" /></div>
                    </div>
                    <div className="space-y-3">
                        <div className="text-center text-slate-500 text-sm mb-2">{fibTrend === 'uptrend' ? '回檔支撐' : '反彈壓力'}</div>
                        {[{ r: 0.382, label: '0.382 強勢', color: 'green' }, { r: 0.5, label: '0.500 中關', color: 'yellow' }, { r: 0.618, label: '0.618 黃金', color: 'red' }].map(({ r, label, color }) => (
                            <div key={r} className={`flex items-center p-4 bg-white border rounded-lg shadow-sm border-l-4 border-l-${color}-500`}>
                                <div className="flex-1"><span className="text-xs font-bold text-slate-400">{label}</span><div className="text-2xl font-bold">{calc(r)}</div></div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    };

    // 當沖判讀 Panel
    const IntradayPanel = () => {
        const high = Number(intradayHigh);
        const low = Number(intradayLow);
        const current = Number(intradayCurrent);
        const valid = high > low && high > 0 && low > 0 && current > 0;

        // 格式化為小數點兩位
        const highFmt = high.toFixed(2);
        const lowFmt = low.toFixed(2);
        const currentFmt = current.toFixed(2);

        // 計算關鍵位置
        const range = high - low;
        const midPoint = (high + low) / 2;
        const upperThird = low + range * 0.667;
        const lowerThird = low + range * 0.333;

        // 判斷狀態
        let signal = '';
        let signalColor = '';
        let signalBg = '';
        let description = '';
        let action = '';

        if (valid) {
            if (current > high) {
                signal = '🔴 突破高點 - 強勢多頭';
                signalColor = 'text-red-700';
                signalBg = 'bg-red-100';
                description = '價格突破開盤15分鐘高點，視為當日強勢，可順勢做多';
                action = '做多';
            } else if (current < low) {
                signal = '🟢 跌破低點 - 弱勢空頭';
                signalColor = 'text-green-700';
                signalBg = 'bg-green-100';
                description = '價格跌破開盤15分鐘低點，視為當日弱勢，可順勢做空';
                action = '做空';
            } else if (current > upperThird) {
                signal = '⬆️ 高檔偏多';
                signalColor = 'text-orange-700';
                signalBg = 'bg-orange-50';
                description = '價格位於區間上方 1/3，偏多但尚未突破，觀察突破訊號';
                action = '觀望偏多';
            } else if (current < lowerThird) {
                signal = '⬇️ 低檔偏空';
                signalColor = 'text-blue-700';
                signalBg = 'bg-blue-50';
                description = '價格位於區間下方 1/3，偏空但尚未跌破，觀察破位訊號';
                action = '觀望偏空';
            } else {
                signal = '⚖️ 中性盤整';
                signalColor = 'text-slate-600';
                signalBg = 'bg-slate-100';
                description = '價格位於區間中段，多空不明，建議等待方向確認';
                action = '觀望';
            }
        }

        // 計算目標價 (根據突破狀態動態計算)
        let longTarget1 = '-', longTarget2 = '-', longStop = '-';
        let shortTarget1 = '-', shortTarget2 = '-', shortStop = '-';
        let longMode = '', shortMode = '';

        if (valid) {
            if (current > high) {
                // 已突破：從現價往上計算目標
                longTarget1 = (current + range * 0.5).toFixed(2);
                longTarget2 = (current + range * 1.0).toFixed(2);

                // 動態停損：現價離高點太遠時，停損也要跟上來
                if (current > high + range) {
                    // 追高模式：停損設在 現價 - 0.5倍區間 (短線防守)
                    longStop = (current - range * 0.5).toFixed(2);
                    longMode = '追高';
                } else {
                    // 剛突破模式：停損守在 突破點下方
                    longStop = (high - range * 0.2).toFixed(2);
                    longMode = '突破';
                }
            } else {
                // 未突破：從高點往上計算目標
                longTarget1 = (high + range * 0.5).toFixed(2);
                longTarget2 = (high + range * 1.0).toFixed(2);
                longStop = (low - range * 0.2).toFixed(2);
                longMode = '待機';
            }

            if (current < low) {
                // 已跌破：從現價往下計算目標
                shortTarget1 = (current - range * 0.5).toFixed(2);
                shortTarget2 = (current - range * 1.0).toFixed(2);

                // 動態停損：現價離低點太遠時，停損也要跟上來
                if (current < low - range) {
                    // 追空模式：停損設在 現價 + 0.5倍區間 (短線防守)
                    shortStop = (current + range * 0.5).toFixed(2);
                    shortMode = '追空';
                } else {
                    // 剛跌破模式：停損守在 跌破點上方
                    shortStop = (low + range * 0.2).toFixed(2);
                    shortMode = '跌破';
                }
            } else {
                // 未跌破：從低點往下計算目標
                shortTarget1 = (low - range * 0.5).toFixed(2);
                shortTarget2 = (low - range * 1.0).toFixed(2);
                shortStop = (high + range * 0.2).toFixed(2);
                shortMode = '待機';
            }
        }

        return (
            <div className="bg-white p-6 rounded-xl shadow-lg border border-slate-200">
                <div className="flex items-center gap-2 mb-6 border-b pb-4">
                    <Activity className="text-blue-600" />
                    <h2 className="text-2xl font-bold">當沖判讀 (Intraday Analysis)</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* 輸入區 */}
                    <div className="space-y-4">
                        <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
                            <div className="flex items-center gap-2 mb-2">
                                <HelpCircle className="w-4 h-4 text-blue-500" />
                                <span className="font-medium text-slate-700">輸入開盤15分鐘內的關鍵價位：</span>
                            </div>
                            <p className="text-xs text-slate-500">
                                💡 策略邏輯：觀察開盤後15分鐘的高低點區間。突破高點視為當日強勢；跌破低點視為當日弱勢。
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1 text-red-600">前15分鐘最高價 (RANGE HIGH)</label>
                            <input
                                type="number"
                                placeholder="例如: 102"
                                value={intradayHigh}
                                onChange={e => setIntradayHigh(Number(e.target.value) || '')}
                                className="w-full px-4 py-3 border border-red-200 bg-red-50 rounded-lg text-lg"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1 text-green-600">前15分鐘最低價 (RANGE LOW)</label>
                            <input
                                type="number"
                                placeholder="例如: 98"
                                value={intradayLow}
                                onChange={e => setIntradayLow(Number(e.target.value) || '')}
                                className="w-full px-4 py-3 border border-green-200 bg-green-50 rounded-lg text-lg"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1 text-slate-600">目前最新成交價 (CURRENT)</label>
                            <input
                                type="number"
                                placeholder="例如: 103"
                                value={intradayCurrent}
                                onChange={e => setIntradayCurrent(Number(e.target.value) || '')}
                                className="w-full px-4 py-3 border rounded-lg text-lg"
                            />
                        </div>
                    </div>

                    {/* 判讀結果 */}
                    <div className="space-y-4">
                        {valid ? (
                            <>
                                {/* 主要訊號 */}
                                <div className={`${signalBg} p-6 rounded-xl border`}>
                                    <div className={`text-2xl font-bold mb-2 ${signalColor}`}>{signal}</div>
                                    <p className="text-slate-600">{description}</p>
                                    <div className="mt-4 flex items-center gap-2">
                                        <span className="text-sm text-slate-500">建議操作:</span>
                                        <span className={`px-3 py-1 rounded-full text-sm font-bold ${action === '做多' ? 'bg-red-200 text-red-800' :
                                            action === '做空' ? 'bg-green-200 text-green-800' :
                                                'bg-slate-200 text-slate-700'
                                            }`}>{action}</span>
                                    </div>
                                </div>

                                {/* 價位圖示 */}
                                <div className="bg-slate-50 rounded-xl p-4">
                                    <div className="relative h-32">
                                        <div className="absolute inset-0 flex flex-col justify-between text-xs">
                                            <div className="flex justify-between items-center">
                                                <span className="text-red-600 font-bold">高: ${highFmt}</span>
                                                {current > high && <span className="text-red-600 font-bold">← 突破!</span>}
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-slate-400">中: ${midPoint.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between items-center">
                                                <span className="text-green-600 font-bold">低: ${lowFmt}</span>
                                                {current < low && <span className="text-green-600 font-bold">← 跌破!</span>}
                                            </div>
                                        </div>
                                        <div className="absolute left-1/2 top-0 bottom-0 w-2 bg-gradient-to-b from-red-400 via-slate-300 to-green-400 rounded-full" />
                                        {/* 目前價位指示 */}
                                        <div
                                            className="absolute left-1/2 transform -translate-x-1/2 w-6 h-6 bg-blue-600 rounded-full border-4 border-white shadow-lg flex items-center justify-center"
                                            style={{
                                                top: `${Math.min(100, Math.max(0, ((high - current) / range) * 100))}%`,
                                                marginTop: '-12px'
                                            }}
                                        >
                                            <span className="text-white text-xs font-bold">●</span>
                                        </div>
                                    </div>
                                    <div className="text-center mt-2 text-sm text-blue-600 font-medium">
                                        現價: ${currentFmt} (區間 {((current - low) / range * 100).toFixed(0)}%)
                                    </div>
                                </div>

                                {/* 目標價表格 */}
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div className="bg-red-50 rounded-lg p-3 border border-red-100">
                                        <div className="font-bold text-red-700 mb-2 flex items-center gap-2">
                                            做多參考
                                            {longMode && <span className={`text-xs px-2 py-0.5 rounded-full ${longMode === '追高' ? 'bg-orange-200 text-orange-700' :
                                                longMode === '突破' ? 'bg-red-200 text-red-700' :
                                                    'bg-slate-200 text-slate-600'
                                                }`}>{longMode}</span>}
                                        </div>
                                        <div>目標1: <span className="font-bold">${longTarget1}</span></div>
                                        <div>目標2: <span className="font-bold">${longTarget2}</span></div>
                                        <div className="text-red-500">停損: ${longStop}</div>
                                    </div>
                                    <div className="bg-green-50 rounded-lg p-3 border border-green-100">
                                        <div className="font-bold text-green-700 mb-2 flex items-center gap-2">
                                            做空參考
                                            {shortMode && <span className={`text-xs px-2 py-0.5 rounded-full ${shortMode === '追空' ? 'bg-blue-200 text-blue-700' :
                                                shortMode === '跌破' ? 'bg-green-200 text-green-700' :
                                                    'bg-slate-200 text-slate-600'
                                                }`}>{shortMode}</span>}
                                        </div>
                                        <div>目標1: <span className="font-bold">${shortTarget1}</span></div>
                                        <div>目標2: <span className="font-bold">${shortTarget2}</span></div>
                                        <div className="text-green-500">停損: ${shortStop}</div>
                                    </div>
                                </div>
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-slate-400 py-12">
                                <Zap className="w-12 h-12 mb-4 opacity-30" />
                                <p>請輸入 15分鐘高低點 與 現價</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="min-h-screen bg-slate-100 p-4 md:p-8">
            <div className="max-w-4xl mx-auto">
                <header className="mb-8 text-center">
                    <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-2 flex items-center justify-center gap-3"><TrendingUp className="w-8 h-8 text-blue-600" />股市大師策略分析儀</h1>
                    <p className="text-slate-500">整合撐壓趨勢、斐波那契與風控計算</p>
                </header>
                <div className="mb-6 flex gap-4 bg-white p-4 rounded-xl shadow-sm">
                    <input type="text" placeholder="股票代號 (如: 2330)" value={stockId} onChange={e => setStockId(e.target.value.toUpperCase())} onKeyPress={e => e.key === 'Enter' && handleSearch()} className="flex-1 px-4 py-2 border rounded-lg" />
                    <button onClick={handleSearch} disabled={loading || !stockId} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"><Search className="w-4 h-4" />分析</button>
                    {stockId && (
                        <button
                            onClick={toggleFavorite}
                            className={`px-3 py-2 rounded-lg flex items-center gap-1 transition-colors ${isFavorite
                                ? 'bg-yellow-100 text-yellow-600 hover:bg-yellow-200'
                                : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                                }`}
                            title={isFavorite ? '移除最愛' : '加入最愛'}
                        >
                            <Star className={`w-4 h-4 ${isFavorite ? 'fill-yellow-500' : ''}`} />
                        </button>
                    )}
                    {stockName && <div className="flex items-center px-4 py-2 bg-slate-100 rounded-lg font-medium">{stockName}</div>}
                </div>

                {/* 我的最愛快捷選單 */}
                {favorites.length > 0 && (
                    <div className="mb-4 bg-yellow-50 p-3 rounded-lg border border-yellow-200">
                        <div className="flex items-center gap-2 mb-2 text-sm font-medium text-yellow-700">
                            <Star className="w-4 h-4 fill-yellow-500" />我的最愛
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {favorites.map(fav => (
                                <div key={fav.code} className="flex items-center gap-1">
                                    <button
                                        onClick={() => { setStockId(fav.code); fetchSRData(fav.code); }}
                                        className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${stockId === fav.code
                                            ? 'bg-yellow-500 text-white'
                                            : 'bg-white text-slate-700 hover:bg-yellow-100'
                                            }`}
                                    >
                                        {fav.code} {fav.name && fav.name !== fav.code && `(${fav.name})`}
                                    </button>
                                    <button
                                        onClick={() => saveFavorites(favorites.filter(f => f.code !== fav.code))}
                                        className="text-slate-400 hover:text-red-500 transition-colors"
                                        title="移除"
                                    >
                                        <X className="w-3 h-3" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                    {[
                        { id: 'sr-analysis', icon: BarChart2, label: '撐壓趨勢' },
                        { id: 'checklist', icon: ClipboardList, label: '分析戰報' },
                        { id: 'calculator', icon: Calculator, label: '倉位風控' },
                        { id: 'fibonacci', icon: Layers, label: '斐波那契' },
                        { id: 'intraday', icon: Activity, label: '當沖判讀' }
                    ].map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-6 py-3 rounded-lg font-bold whitespace-nowrap ${activeTab === tab.id ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-slate-600 hover:bg-slate-50'}`}><tab.icon className="w-4 h-4" />{tab.label}</button>
                    ))}
                    {srData && (
                        <button
                            onClick={sendReport}
                            disabled={sendingReport}
                            className="flex items-center gap-2 px-4 py-3 rounded-lg font-bold text-purple-600 bg-purple-50 hover:bg-purple-100 disabled:opacity-50"
                        >
                            <Mail className="w-4 h-4" />
                            {sendingReport ? '發送中...' : '發送報告'}
                        </button>
                    )}
                    {favorites.length > 0 && (
                        <button
                            onClick={async () => {
                                setSendingReport(true);
                                setReportStatus(null);
                                try {
                                    const codes = favorites.map(f => f.code).join(',');
                                    const res = await fetch(`http://localhost:8000/api/support-resistance/schedule-report?stock_codes=${codes}&send_time=09:05`, {
                                        method: 'POST'
                                    });
                                    const result = await res.json();
                                    if (result.success) {
                                        setReportStatus({ success: true, message: `已排程 ${favorites.length} 檔股票於 09:05 發送` });
                                    } else {
                                        setReportStatus({ success: false, message: '排程失敗' });
                                    }
                                } catch {
                                    setReportStatus({ success: false, message: '排程失敗' });
                                } finally {
                                    setSendingReport(false);
                                }
                            }}
                            disabled={sendingReport}
                            className="flex items-center gap-2 px-4 py-3 rounded-lg font-bold text-orange-600 bg-orange-50 hover:bg-orange-100 disabled:opacity-50"
                            title="開盤5分鐘後發送所有最愛股票報告"
                        >
                            <Send className="w-4 h-4" />
                            09:05 發送最愛
                        </button>
                    )}
                    <button onClick={resetAll} className="ml-auto flex items-center gap-2 px-4 py-3 rounded-lg font-bold text-slate-500 hover:bg-red-50 hover:text-red-500"><RotateCcw className="w-4 h-4" />重置</button>
                </div>
                {reportStatus && (
                    <div className={`mb-4 p-3 rounded-lg ${reportStatus.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {reportStatus.success ? '✅' : '❌'} {reportStatus.message}
                    </div>
                )}
                <div className="transition-all duration-300">
                    {activeTab === 'sr-analysis' && <SRAnalysisPanel />}
                    {activeTab === 'checklist' && <ChecklistPanel />}
                    {activeTab === 'calculator' && <RiskCalcPanel />}
                    {activeTab === 'fibonacci' && <FibPanel />}
                    {activeTab === 'intraday' && <IntradayPanel />}
                </div>
                <footer className="mt-12 text-center text-slate-400 text-sm"><p className="flex items-center justify-center gap-2"><AlertTriangle className="w-4 h-4" />投資一定有風險，本工具僅供策略輔助。</p></footer>
            </div>
        </div>
    );
};

export default TradeAnalyzer;
