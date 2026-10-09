/**
 * MOPSPanel.jsx - 公開資訊觀測站即時監控儀表板 (明亮版)
 * 顯示：最新重大公告 + AI 對未來看法指標
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import KGIResearchPanel from './KGIResearchPanel';
import {
  FileText, TrendingUp, TrendingDown, AlertTriangle, Activity,
  ChevronDown, ChevronUp, RefreshCw, Loader2, Zap, Eye, Clock,
  BarChart2, Shield, Flame, ArrowUpRight, ArrowDownRight, Minus, Image
} from 'lucide-react';
import * as htmlToImage from 'html-to-image';

const API_BASE = 'http://localhost:8000';

// ─── 情緒標籤 ───────────────────────────────
const SentimentBadge = ({ sentiment, score }) => {
  const cfg = {
    positive: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-200', icon: '📈', label: '利多' },
    negative: { bg: 'bg-rose-100', text: 'text-rose-700', border: 'border-rose-200', icon: '📉', label: '利空' },
    neutral:  { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200', icon: '📋', label: '中性' },
  }[sentiment] || { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200', icon: '📋', label: '中性' };

  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
      {cfg.icon} {cfg.label}
    </span>
  );
};

// ─── 分類標籤 ───────────────────────────────
const CategoryBadge = ({ category }) => {
  const colorMap = {
    '財務': 'bg-purple-100 text-purple-700 border-purple-200',
    '業務': 'bg-blue-100 text-blue-700 border-blue-200',
    '股利': 'bg-amber-100 text-amber-700 border-amber-200',
    '公司治理': 'bg-teal-100 text-teal-700 border-teal-200',
    '投資擴產': 'bg-indigo-100 text-indigo-700 border-indigo-200',
    '其他': 'bg-slate-100 text-slate-600 border-slate-200',
  };
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium border ${colorMap[category] || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
      {category}
    </span>
  );
};

// ─── AI 信心條 ───────────────────────────────
const ConfidenceBar = ({ value, color }) => (
  <div className="relative w-full h-2.5 bg-slate-200 rounded-full overflow-hidden shadow-inner">
    <div
      className={`h-full rounded-full transition-all duration-700 ${
        color === 'green' ? 'bg-gradient-to-r from-emerald-400 to-emerald-500' :
        color === 'red'   ? 'bg-gradient-to-r from-rose-400 to-rose-500' :
                            'bg-gradient-to-r from-amber-400 to-amber-500'
      }`}
      style={{ width: `${value}%` }}
    />
    <div className="absolute inset-0 flex items-center justify-end pr-1.5">
      <span className="text-[10px] text-white font-bold drop-shadow-sm">{value}%</span>
    </div>
  </div>
);

// ─── AI 展望卡片 ───────────────────────────────
const AIOutlookCard = ({ outlook }) => {
  if (!outlook) return null;
  const { signal, signal_color, confidence, summary, key_points, risk_level,
          catalyst, tech_data, pos_count, neg_count } = outlook;

  const riskColor = { '低': 'text-emerald-600 bg-emerald-50', '中': 'text-amber-600 bg-amber-50', '高': 'text-rose-600 bg-rose-50' }[risk_level] || 'text-slate-600 bg-slate-50';
  
  const TrendIcon = tech_data?.trend?.includes('多頭') ? ArrowUpRight :
                    tech_data?.trend?.includes('空頭') ? ArrowDownRight : Minus;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-5 py-3 bg-gradient-to-r from-indigo-50 to-blue-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap size={18} className="text-indigo-600" />
          <span className="text-sm font-black text-slate-800 tracking-tight">AI 展望分析</span>
        </div>
        <div className={`text-xs font-bold px-2.5 py-1 rounded-full border shadow-sm ${
          signal_color === 'green' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
          signal_color === 'red'   ? 'bg-rose-50 text-rose-700 border-rose-200' :
                                     'bg-amber-50 text-amber-700 border-amber-200'
        }`}>
          {signal}
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* 信心指數 */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">AI 信心指數</span>
            <span className={`text-sm font-black ${
              signal_color === 'green' ? 'text-emerald-600' :
              signal_color === 'red'   ? 'text-rose-600' : 'text-amber-600'
            }`}>{confidence}%</span>
          </div>
          <ConfidenceBar value={confidence} color={signal_color} />
        </div>

        {/* 攤位統計 */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: '利多公告', value: pos_count ?? 0, color: 'text-emerald-600', bg: 'bg-emerald-50 border border-emerald-100' },
            { label: '利空公告', value: neg_count ?? 0, color: 'text-rose-600',   bg: 'bg-rose-50 border border-rose-100' },
            { label: '風險等級', value: risk_level,     color: riskColor.split(' ')[0], bg: `${riskColor.split(' ')[1]} border border-slate-100` },
          ].map(({ label, value, color, bg }) => (
            <div key={label} className={`rounded-xl p-3 text-center ${bg}`}>
              <div className={`text-xl font-black ${color}`}>{value}</div>
              <div className="text-[10px] text-slate-500 font-bold mt-1 uppercase tracking-wider">{label}</div>
            </div>
          ))}
        </div>

        {/* AI 摘要 */}
        <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">
          <p className="text-sm text-slate-700 font-medium leading-[1.7] whitespace-pre-wrap">{summary}</p>
        </div>

        {/* 關鍵要點 */}
        {key_points && key_points.length > 0 && (
          <div className="space-y-2">
            {key_points.map((pt, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-slate-600">
                <span className="text-indigo-500 mt-0.5 flex-shrink-0 font-bold">›</span>
                <span className="font-medium">{pt}</span>
              </div>
            ))}
          </div>
        )}

        {/* 技術面 */}
        {tech_data && (
          <div className="border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <BarChart2 size={14} /> 技術面指標
              </span>
              <div className={`flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-md ${
                tech_data.trend?.includes('多頭') ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
              }`}>
                <TrendIcon size={12} />
                {tech_data.trend}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'MA5',  value: tech_data.ma5 },
                { label: 'MA20', value: tech_data.ma20 },
                { label: '5日動能', value: `${tech_data.momentum_5d > 0 ? '+' : ''}${tech_data.momentum_5d}%` },
                { label: '10日波動', value: `${tech_data.volatility}%` },
              ].map(({ label, value }) => (
                <div key={label} className="bg-slate-50 border border-slate-100 rounded-lg p-2 flex justify-between items-center">
                  <span className="text-[10px] text-slate-500 font-bold tracking-wider">{label}</span>
                  <span className="text-xs font-mono font-bold text-slate-800">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 主要催化劑 */}
        {catalyst && catalyst !== '無' && (
          <div className="border-t border-slate-100 pt-4">
            <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2 flex items-center gap-1">
              <Flame size={12} className="text-amber-500" /> 主要催化劑
            </div>
            <p className="text-sm text-amber-700 font-medium bg-amber-50 p-3 rounded-lg border border-amber-100">
              {catalyst}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

// ─────────────────── 主組件 ───────────────────
const MOPSPanel = ({ symbol, stockName }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedNews, setExpandedNews] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const intervalRef = useRef(null);
  const panelRef = useRef(null);

  const handleDownloadImage = useCallback(async () => {
    if (!panelRef.current) return;
    try {
      setIsDownloading(true);
      const dataUrl = await htmlToImage.toPng(panelRef.current, {
        quality: 1.0,
        backgroundColor: '#ffffff',
        style: { transform: 'scale(1)', margin: 0, padding: '24px' }
      });
      const link = document.createElement('a');
      link.download = `AI展望分析-${stockName || symbol}-${new Date().getTime()}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('導出圖片失敗', err);
    } finally {
      setIsDownloading(false);
    }
  }, [symbol]);

  const fetchData = useCallback(async (code) => {
    if (!code || code.length < 4) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/mops/full/${code}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastFetch(new Date().toLocaleTimeString('zh-TW'));
    } catch (e) {
      setError('載入失敗，請稍後再試');
      console.error('MOPS fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  // 當 symbol 改變時重新抓取
  useEffect(() => {
    if (!symbol || symbol.length < 4) {
      setData(null);
      return;
    }
    fetchData(symbol);
    // 每 5 分鐘自動刷新
    intervalRef.current = setInterval(() => fetchData(symbol), 5 * 60 * 1000);
    return () => clearInterval(intervalRef.current);
  }, [symbol, fetchData]);

  // ── 空白或未輸入代碼 ──
  if (!symbol || symbol.length < 4) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center space-y-3">
        <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-2">
          <Eye size={24} className="text-slate-400" />
        </div>
        <p className="text-base font-bold text-slate-600">請輸入股票代碼</p>
        <p className="text-sm text-slate-500 font-medium">系統將自動獲取並分析最新公開資訊觀測站公告</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" ref={panelRef}>
      {/* 面板標題列 */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-sm flex items-center justify-center">
            <FileText size={16} className="text-white" />
          </div>
          <div>
            <h3 className="text-lg font-black text-slate-800 tracking-tight flex items-center gap-2">
              公開資訊觀測站
              {symbol && (
                <span className="text-sm px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-md whitespace-nowrap">
                  {stockName} {symbol}
                </span>
              )}
            </h3>
            {lastFetch && (
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">UPDATE: {lastFetch}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadImage}
            disabled={isDownloading || loading}
            className="p-2 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-600 transition-colors border border-blue-200"
            title="導出分享圖卡"
          >
            {isDownloading ? <Loader2 size={16} className="animate-spin" /> : <Image size={16} />}
          </button>
          <button
            onClick={() => fetchData(symbol)}
            disabled={loading}
            className="p-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-indigo-600 transition-colors border border-slate-200"
            title="手動刷新"
          >
            {loading ? <Loader2 size={16} className="animate-spin text-indigo-500" /> : <RefreshCw size={16} />}
          </button>
        </div>
      </div>

      {/* 載入中 */}
      {loading && !data && (
        <div className="flex flex-col items-center justify-center py-12 text-slate-500 gap-3">
          <Loader2 size={24} className="animate-spin text-indigo-500" />
          <span className="text-sm font-bold animate-pulse">正在同步 MOPS 公告資料...</span>
        </div>
      )}

      {/* 錯誤 */}
      {error && (
        <div className="rounded-xl bg-rose-50 border border-rose-200 p-4 flex items-center gap-3 shadow-sm">
          <AlertTriangle size={18} className="text-rose-500" />
          <span className="text-sm font-bold text-rose-700">{error}</span>
        </div>
      )}

      {/* 主內容 */}
      {data && (
        <>
          {/* AI 展望 */}
          <AIOutlookCard outlook={data.outlook} />

          {/* 重大公告列表 */}
          <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
            <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-blue-500" />
                <span className="text-sm font-black text-slate-800">最新重大訊息</span>
                {data.news?.length > 0 && (
                  <span className="text-[10px] font-bold bg-blue-100 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full ml-1">
                    {data.news.length} 則
                  </span>
                )}
              </div>
              <Clock size={14} className="text-slate-400" />
            </div>

            <div className="divide-y divide-slate-100 max-h-[400px] overflow-y-auto">
              {data.news && data.news.length > 0 ? (
                data.news.map((item, idx) => {
                  const isExpanded = expandedNews === idx;
                  return (
                    <div
                      key={idx}
                      className="px-5 py-3.5 hover:bg-slate-50 cursor-pointer transition-colors"
                      onClick={() => setExpandedNews(isExpanded ? null : idx)}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          {/* 標題 + 情緒 */}
                          <div className="flex items-start gap-2 mb-1.5 mt-0.5">
                            <SentimentBadge sentiment={item.sentiment} score={item.score} />
                            <span className="text-sm font-bold text-slate-800 leading-tight">
                              {item.title}
                            </span>
                          </div>
                          {/* 分類 + 日期 */}
                          <div className="flex items-center gap-2.5 mt-2">
                            <CategoryBadge category={item.category} />
                            <span className="text-xs font-medium text-slate-500">{item.date}</span>
                            <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 bg-slate-100 text-slate-400 rounded-md">
                              {item.source}
                            </span>
                          </div>
                        </div>
                        <div className="flex-shrink-0 mt-1 bg-slate-100 p-1 rounded-md text-slate-400">
                          {isExpanded
                            ? <ChevronUp size={16} />
                            : <ChevronDown size={16} />
                          }
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="mt-3 p-4 rounded-xl bg-slate-50 border border-slate-100 text-sm text-slate-600 space-y-2">
                          <p className="flex justify-between"><span className="text-slate-400 font-bold">公告日期</span> <span className="font-mono text-slate-700">{item.date}</span></p>
                          <p className="flex justify-between"><span className="text-slate-400 font-bold">資料來源</span> <span className="font-medium text-slate-700">{item.source}</span></p>
                          <p className="flex justify-between items-center">
                            <span className="text-slate-400 font-bold">AI 評分</span>
                            <span className={`font-black px-2 py-0.5 rounded-md ${
                              item.score > 0 ? 'bg-emerald-100 text-emerald-700' :
                              item.score < 0 ? 'bg-rose-100 text-rose-700' : 'bg-slate-200 text-slate-600'
                            }`}>
                              {item.score > 0 ? `+${item.score}` : item.score} 分
                            </span>
                          </p>
                          <div className="pt-2 mt-2 border-t border-slate-200">
                            <a
                              href={item.link || `https://mops.twse.com.tw/mops/web/t05st01?step=1&firstin=true&co_id=${symbol}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="flex items-center justify-center gap-1 w-full py-2 bg-white hover:bg-indigo-50 text-indigo-600 font-bold rounded-lg border border-indigo-100 transition-colors"
                            >
                              <span>{item.link ? '前往閱讀完整新聞/報告' : '前往公開資訊觀測站查看原文'}</span>
                              <ArrowUpRight size={14} />
                            </a>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="py-12 text-center">
                  <div className="w-16 h-16 bg-slate-50 rounded-full flex justify-center items-center mx-auto mb-3">
                    <FileText size={28} className="text-slate-400" />
                  </div>
                  <p className="text-base font-bold text-slate-600">目前無重大公告</p>
                  <a
                    href={`https://mops.twse.com.tw/mops/web/t05st01?step=1&firstin=true&co_id=${symbol}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-bold text-blue-500 hover:text-blue-600 hover:underline mt-2 inline-block"
                  >
                    → 前往 MOPS 查詢所有歷史資料
                  </a>
                </div>
              )}
            </div>

            {/* 底部連結 */}
            <div className="px-5 py-3 border-t border-slate-200 bg-slate-50">
              <a
                href={`https://mops.twse.com.tw/mops/web/t05st01?step=1&firstin=true&co_id=${symbol}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-1.5 text-xs font-bold text-slate-500 hover:text-blue-600 transition-colors w-full"
              >
                <span>在公開資訊觀測站查看 {symbol} 完整總覽</span>
                <ArrowUpRight size={14} />
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// ─── KGI 研究報告區塊包裝 (掛載在 MOPSPanel 外部) ───
export const KGISection = ({ symbol }) => {
  const [showKGI, setShowKGI] = useState(false);
  return (
    <div className="mt-4 border border-blue-100 rounded-2xl overflow-hidden shadow-sm">
      <button
        onClick={() => setShowKGI(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-blue-800">📊 凱基投顧研究報告彙整</span>
          <span className="text-[10px] bg-blue-600 text-white font-bold px-2 py-0.5 rounded-full">KGI Research</span>
        </div>
        <span className="text-blue-400 text-xs">{showKGI ? '▲ 收起' : '▼ 展開'}</span>
      </button>
      {showKGI && (
        <div className="p-4 bg-white">
          <KGIResearchPanel symbol={symbol} />
        </div>
      )}
    </div>
  );
};

export default MOPSPanel;

