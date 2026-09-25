import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

// 恐慌等級 → accent 色（白底用）
const LEVEL_ACCENT = {
  euphoria:      { text: 'text-orange-500', bar: 'bg-gradient-to-r from-orange-400 to-red-400',    ring: '#f97316', badge: 'bg-orange-50 text-orange-600 border-orange-200' },
  calm:          { text: 'text-emerald-600', bar: 'bg-gradient-to-r from-emerald-400 to-green-400', ring: '#10b981', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  cautious:      { text: 'text-amber-500',   bar: 'bg-gradient-to-r from-amber-400 to-yellow-400',  ring: '#f59e0b', badge: 'bg-amber-50 text-amber-600 border-amber-200' },
  fearful:       { text: 'text-orange-600',  bar: 'bg-gradient-to-r from-orange-500 to-red-500',    ring: '#ea580c', badge: 'bg-orange-50 text-orange-700 border-orange-200' },
  panic:         { text: 'text-red-600',     bar: 'bg-gradient-to-r from-red-500 to-rose-500',      ring: '#ef4444', badge: 'bg-red-50 text-red-700 border-red-200' },
  extreme_panic: { text: 'text-purple-600',  bar: 'bg-gradient-to-r from-purple-500 to-red-500',    ring: '#a855f7', badge: 'bg-purple-50 text-purple-700 border-purple-200' },
  unknown:       { text: 'text-slate-500',   bar: 'bg-gradient-to-r from-slate-300 to-slate-400',   ring: '#94a3b8', badge: 'bg-slate-50 text-slate-500 border-slate-200' },
};

const STRATEGY_BADGE = {
  cash:         { label: '全部現金', color: 'bg-red-50 text-red-600 border-red-200' },
  defensive:    { label: '防守縮倉', color: 'bg-orange-50 text-orange-700 border-orange-200' },
  bear:         { label: '空方避險', color: 'bg-rose-50 text-rose-600 border-rose-200' },
  neutral:      { label: '個股自選', color: 'bg-slate-100 text-slate-600 border-slate-200' },
  bull_caution: { label: '謹慎做多', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  bull:         { label: '積極做多', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  follow_us:    { label: '順勢美股', color: 'bg-blue-50 text-blue-700 border-blue-200' },
};

const MiniChange = ({ val }) => {
  if (val == null) return <span className="text-slate-400 text-xs">--</span>;
  const up = val >= 0;
  return (
    <span className={`text-xs font-mono font-bold ${up ? 'text-red-500' : 'text-emerald-600'}`}>
      {up ? '▲' : '▼'}{Math.abs(val).toFixed(2)}%
    </span>
  );
};

// 迷你波段折線圖
const MiniSparkline = ({ history, accent, min, max }) => {
  if (!history || history.length < 2) return null;
  const w = 150;
  const h = 40;
  const padY = 4;
  
  // 為了避免 min = max 導致除 0
  const range = (max - min) || 1;
  const stepX = w / (history.length - 1);
  
  const getPtY = (val) => h - padY - ((val - min) / range) * (h - padY * 2);
  
  const points = history.map((pt, i) => `${i * stepX},${getPtY(pt.close)}`).join(' ');
  const lastY = getPtY(history[history.length - 1].close);

  return (
    <div className="mt-3 relative h-10 w-full group">
      {/* 標示極值 */}
      <span className="absolute -left-1 -top-1 text-[8px] text-slate-300 font-mono scale-90 origin-left">{max}</span>
      <span className="absolute -left-1 -bottom-1 text-[8px] text-slate-300 font-mono scale-90 origin-left">{min}</span>
      
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-full overflow-visible" preserveAspectRatio="none">
         {/* 畫水平輔助線（平均值或中位數） */}
         <line x1="0" y1={h/2} x2={w} y2={h/2} stroke="#f1f5f9" strokeWidth="1" strokeDasharray="2,2" />
         
         <polyline
            points={points}
            fill="none"
            stroke={accent.ring || '#94a3b8'}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="transition-all duration-1000"
         />
         {/* 最新高亮度點 */}
         <circle cx={w} cy={lastY} r="2.5" fill={accent.ring || '#94a3b8'} className="animate-pulse shadow-sm" />
      </svg>
      {/* Hover 提示（簡單版） */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-white/80 flex items-center justify-center text-[10px] text-slate-600 font-bold pointer-events-none rounded">
        近三個月波段走勢
      </div>
    </div>
  );
};

const VixFearPanel = ({ vixData: externalData }) => {
  const [data, setData]             = useState(null);
  const [loading, setLoading]       = useState(!externalData);
  const [error, setError]           = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [collapsed, setCollapsed]   = useState(false);

  // 若父層有傳入就直接用
  useEffect(() => {
    if (externalData) {
      setData(externalData);
      setLoading(false);
      setLastUpdate(new Date().toLocaleTimeString('zh-TW'));
    }
  }, [externalData]);

  const fetchVix = useCallback(async () => {
    if (externalData) return; // 有外部資料時不自行 fetch
    try {
      setLoading(true);
      setError(null);
      const res  = await fetch(`${API_BASE}/api/market/vix`);
      const json = await res.json();
      if (json.success) {
        setData(json);
        setLastUpdate(new Date().toLocaleTimeString('zh-TW'));
      } else {
        setError(json.error || '資料取得失敗');
      }
    } catch {
      setError('無法連線後端');
    } finally {
      setLoading(false);
    }
  }, [externalData]);

  useEffect(() => {
    if (!externalData) {
      fetchVix();
      const t = setInterval(fetchVix, 5 * 60 * 1000);
      return () => clearInterval(t);
    }
  }, [fetchVix, externalData]);

  const fear     = data?.fear_analysis ?? {};
  const twAdvice = data?.taiwan_advice ?? {};
  const vix      = data?.vix ?? {};
  const spx      = data?.spx ?? {};
  const ndx      = data?.ndx ?? {};
  const accent   = LEVEL_ACCENT[fear.level] ?? LEVEL_ACCENT.unknown;
  const badge    = STRATEGY_BADGE[twAdvice.strategy] ?? STRATEGY_BADGE.neutral;
  const fearPct  = Math.min(fear.score ?? 0, 99);

  return (
    <div className="bg-white rounded-[2rem] border border-slate-200 shadow-sm overflow-hidden">

      {/* ── 標題列 ── */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-base">{fear.emoji || '📊'}</span>
          <span className="text-xs font-black text-slate-800 uppercase tracking-widest">S&P500 VIX 恐慌儀</span>
          {loading && <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />}
        </div>
        <div className="flex items-center gap-2">
          {lastUpdate && (
            <span className="text-[10px] text-slate-400 font-mono">{lastUpdate}</span>
          )}
          <button
            onClick={fetchVix}
            disabled={loading}
            className="text-slate-400 hover:text-slate-700 transition-colors text-xs px-2 py-0.5 rounded-lg border border-slate-200 hover:border-slate-400 disabled:opacity-40"
          >↻</button>
          <button
            onClick={() => setCollapsed(c => !c)}
            className="text-slate-400 hover:text-slate-700 transition-colors text-xs"
          >{collapsed ? '▼' : '▲'}</button>
        </div>
      </div>

      {!collapsed && (
        <div className="px-6 py-5 space-y-4">

          {/* 錯誤 */}
          {error ? (
            <div className="text-center text-red-500 text-sm py-4">
              ⚠️ {error}
              <button onClick={fetchVix} className="ml-2 text-blue-500 underline text-xs">重試</button>
            </div>

          /* 載入中 */
          ) : loading && !data ? (
            <div className="text-center text-slate-400 text-sm py-6 animate-pulse">
              正在從 Yahoo Finance 抓取 VIX 資料...
            </div>

          ) : (
            <>
              {/* ── VIX 主數字 + 圓形儀表 ── */}
              <div className="flex items-center justify-between">
                <div className="flex-1 pr-4 min-w-0">
                  <div className="text-[9px] text-slate-400 uppercase tracking-widest font-bold mb-1">CBOE VIX</div>
                  <div className={`text-4xl sm:text-5xl font-black font-mono tabular-nums leading-none truncate ${accent.text}`}>
                    {vix.price?.toFixed(2) ?? '--'}
                  </div>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <MiniChange val={vix.change_pct} />
                    <span className="text-[10px] text-slate-400 truncate">前收 {vix.prev?.toFixed(2) ?? '--'}</span>
                  </div>
                  
                  {/* ✨ 迷你波段折線圖 ✨ */}
                  {vix.history && (
                    <MiniSparkline history={vix.history} min={vix.hist_min} max={vix.hist_max} accent={accent} />
                  )}
                </div>

                {/* 環形儀表 */}
                <div className="relative w-20 h-20 flex-shrink-0">
                  <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    <circle cx="18" cy="18" r="15.9" fill="none" stroke="#f1f5f9" strokeWidth="3.5" />
                    <circle
                      cx="18" cy="18" r="15.9" fill="none"
                      stroke={accent.ring}
                      strokeWidth="3.5"
                      strokeDasharray={`${fearPct} ${100 - fearPct}`}
                      strokeLinecap="round"
                      className="transition-all duration-1000"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={`text-lg font-black leading-none ${accent.text}`}>{fearPct}</span>
                    <span className="text-[8px] text-slate-400 font-bold">恐慌分</span>
                  </div>
                </div>
              </div>

              {/* ── 恐慌等級 + 進度條 ── */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <span className={`text-xs font-black ${accent.text}`}>{fear.label ?? '讀取中...'}</span>
                  <span className="text-[9px] text-slate-400">貪婪 ←——→ 恐慌</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${accent.bar} transition-all duration-1000`}
                    style={{ width: `${fearPct}%` }}
                  />
                </div>
                <div className="flex justify-between text-[9px] text-slate-400 mt-1 px-0.5">
                  <span>0 過熱</span><span>20 平靜</span><span>50 謹慎</span><span>80 恐慌</span><span>99</span>
                </div>
              </div>

              {/* ── S&P500 / NASDAQ ── */}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'S&P 500', d: spx, icon: '🇺🇸' },
                  { label: 'NASDAQ',  d: ndx, icon: '💻' },
                ].map(({ label, d, icon }) => (
                  <div key={label} className="bg-slate-50 rounded-2xl px-3 py-3 border border-slate-100">
                    <div className="flex items-center gap-1 mb-1">
                      <span className="text-xs">{icon}</span>
                      <span className="text-[10px] text-slate-500 font-bold">{label}</span>
                    </div>
                    <div className="text-base font-black font-mono text-slate-800 tabular-nums">
                      {d?.price ? d.price.toLocaleString() : '--'}
                    </div>
                    <MiniChange val={d?.change_pct} />
                  </div>
                ))}
              </div>

              {/* ── 歷史脈絡 ── */}
              {fear.context?.length > 0 && (
                <div className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
                  <div className="text-[9px] text-slate-400 font-black uppercase tracking-widest mb-2">📚 歷史脈絡</div>
                  {fear.context.map((c, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-[11px] text-slate-600 mb-1">
                      <span className="text-slate-300 mt-px flex-shrink-0">•</span>
                      <span>{c}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* ── AI 台股建議 ── */}
              <div className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] text-slate-500 font-black uppercase tracking-widest">🤖 AI 台股操作建議</span>
                  <span className={`text-[10px] font-black px-2 py-0.5 rounded-full border ${badge.color}`}>
                    {badge.label}
                  </span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed">{twAdvice.advice ?? '分析中...'}</p>
              </div>

              {/* 資料來源 */}
              <div className="text-center text-[9px] text-slate-400">
                資料來源：Yahoo Finance (^VIX) · 每5分鐘更新 · 僅供參考
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default VixFearPanel;
