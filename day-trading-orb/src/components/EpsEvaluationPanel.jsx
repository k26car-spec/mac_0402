import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, Activity, AlertTriangle, Briefcase, Zap, Target } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const MetricBox = ({ label, value, suffix = '', highlight = false, colorClass = 'text-slate-800' }) => (
  <div className={`p-3 rounded-xl border ${highlight ? 'bg-indigo-50 border-indigo-100' : 'bg-white border-slate-100 shadow-sm'}`}>
    <div className="text-[10px] text-slate-500 font-bold tracking-wider mb-1">{label}</div>
    <div className={`text-lg font-black font-mono ${colorClass} ${highlight ? 'text-indigo-700' : ''}`}>
      {value !== 0 ? value : '--'}{suffix}
    </div>
  </div>
);

const EpsEvaluationPanel = ({ symbol, stockName }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async (code) => {
    if (!code || code.length < 4) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/market/eps-evaluation/${code}`);
      const json = await res.json();
      if (json.success && json.data) {
        setData(json.data);
      } else {
        setError(json.error || '無法取得 EPS 評估資料');
      }
    } catch (e) {
      setError('連線失敗: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (symbol && symbol.length >= 4) {
      fetchData(symbol);
    } else {
      setData(null);
    }
  }, [symbol, fetchData]);

  if (!symbol || symbol.length < 4) return null;

  return (
    <div className="mt-4 border border-blue-100 rounded-2xl overflow-hidden shadow-sm bg-white">
      {/* Header */}
      <div className="px-5 py-3.5 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Briefcase size={18} className="text-blue-600" />
          <span className="text-sm font-black text-slate-800 tracking-tight">EPS 基本面評估報告</span>
          {stockName && (
            <span className="text-[10px] font-bold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full ml-1">
              {stockName} {symbol}
            </span>
          )}
        </div>
        {loading && <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />}
      </div>

      <div className="p-5">
        {error && (
          <div className="mb-4 bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
            <AlertTriangle size={16} /> {error}
          </div>
        )}

        {loading && !data && (
          <div className="py-8 text-center text-slate-400 text-sm animate-pulse font-bold">
            正在計算基本面與 EPS 評價模型...
          </div>
        )}

        {data && (
          <div className="space-y-5">
            {/* 總合評估 */}
            <div className={`p-4 rounded-xl border flex items-start gap-4 ${
              data.evaluation.color === 'green' ? 'bg-emerald-50 border-emerald-100' :
              data.evaluation.color === 'orange' ? 'bg-amber-50 border-amber-100' :
              'bg-blue-50 border-blue-100'
            }`}>
              <div className={`w-12 h-12 rounded-full flex flex-col items-center justify-center flex-shrink-0 text-white shadow-sm ${
                data.evaluation.color === 'green' ? 'bg-gradient-to-br from-emerald-400 to-green-600' :
                data.evaluation.color === 'orange' ? 'bg-gradient-to-br from-amber-400 to-orange-500' :
                'bg-gradient-to-br from-blue-400 to-indigo-600'
              }`}>
                <span className="text-[10px] font-bold opacity-80 uppercase">評級</span>
                <span className="text-sm font-black leading-none mt-0.5">
                  {(data.evaluation.level && data.evaluation.level.includes(' ')) 
                    ? data.evaluation.level.split(' ')[1].replace(/[()]/g, '') 
                    : (data.evaluation.level || '--')}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1.5">
                  <span className={`text-sm font-black ${
                    data.evaluation.color === 'green' ? 'text-emerald-700' :
                    data.evaluation.color === 'orange' ? 'text-amber-700' :
                    'text-blue-700'
                  }`}>
                    {data.evaluation.level} ({data.evaluation.score}分)
                  </span>
                  {data.evaluation.tags.map(tag => (
                    <span key={tag} className="text-[9px] font-bold px-1.5 py-0.5 rounded border bg-white text-slate-600 border-slate-200">
                      {tag}
                    </span>
                  ))}
                </div>
                <p className="text-xs font-medium text-slate-700 leading-relaxed">
                  {data.evaluation.verdict}
                </p>
              </div>
            </div>

            {/* 核心指標 Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <MetricBox 
                label="近四季 EPS" 
                value={data.metrics.eps_trailing} 
                suffix=" 元"
                colorClass="text-slate-700"
              />
              <MetricBox 
                label="未來預估 EPS" 
                value={data.metrics.eps_forward} 
                suffix=" 元"
                highlight={data.metrics.eps_forward > data.metrics.eps_trailing}
                colorClass={data.metrics.eps_forward > data.metrics.eps_trailing ? 'text-emerald-600' : 'text-slate-700'}
              />
              <MetricBox 
                label="目前本益比 P/E" 
                value={data.metrics.pe_trailing} 
                suffix="x"
                colorClass="text-blue-600"
              />
              <MetricBox 
                label="ROE (股東權益報酬)" 
                value={data.metrics.roe} 
                suffix="%"
                colorClass={data.metrics.roe > 15 ? 'text-emerald-600' : 'text-slate-700'}
              />
              <MetricBox 
                label="季盈餘 YOY" 
                value={data.metrics.earnings_growth} 
                suffix="%"
                colorClass={data.metrics.earnings_growth > 0 ? 'text-emerald-600' : (data.metrics.earnings_growth < 0 ? 'text-rose-600' : 'text-slate-700')}
              />
              <MetricBox 
                label="預估本益比" 
                value={data.metrics.pe_forward} 
                suffix="x"
              />
              <MetricBox 
                label="股價淨值比 P/B" 
                value={data.metrics.pb_ratio} 
                suffix="x"
              />
              <MetricBox 
                label="營收 YOY" 
                value={data.metrics.revenue_growth} 
                suffix="%"
              />
            </div>

            {/* 正負向因子分析 */}
            {(data.evaluation.positive_factors.length > 0 || data.evaluation.negative_factors.length > 0) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                {/* 優勢 */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <div className="text-[10px] text-emerald-600 font-bold uppercase tracking-wider mb-2 flex items-center gap-1">
                    <TrendingUp size={12} /> 基本面亮點
                  </div>
                  {data.evaluation.positive_factors.length > 0 ? (
                    <ul className="space-y-1.5">
                      {data.evaluation.positive_factors.map((factor, i) => (
                        <li key={i} className="text-xs text-slate-700 flex items-start gap-1.5">
                          <span className="text-emerald-500 mt-0.5 text-[10px]">●</span>
                          {factor}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-xs text-slate-400">目前無明顯亮點</div>
                  )}
                </div>
                
                {/* 劣勢 */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                  <div className="text-[10px] text-rose-600 font-bold uppercase tracking-wider mb-2 flex items-center gap-1">
                    <TrendingDown size={12} /> 潛在風險
                  </div>
                  {data.evaluation.negative_factors.length > 0 ? (
                    <ul className="space-y-1.5">
                      {data.evaluation.negative_factors.map((factor, i) => (
                        <li key={i} className="text-xs text-slate-700 flex items-start gap-1.5">
                          <span className="text-rose-500 mt-0.5 text-[10px]">●</span>
                          {factor}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-xs text-slate-400">目前無明顯風險</div>
                  )}
                </div>
              </div>
            )}
            <div className="text-center text-[9px] text-slate-400 pt-2 border-t border-slate-50">
              資料來源：Yahoo Finance API · 基本面數據隨財報公佈更新 · 評價自動生成僅供參考
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EpsEvaluationPanel;
