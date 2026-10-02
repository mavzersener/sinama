import { useState } from 'react';
import { useStore } from '../store/useStore';
import { isMlResult, extractMetricRows, extractImportance } from '../engine/mlResultFormat';
import type { NodeData } from '../store/useStore';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, AreaChart, Area
} from 'recharts';
import {
  X, ChevronDown, CheckCircle2, AlertTriangle
} from 'lucide-react';
import FeedbackButtons from './FeedbackButtons';
import { HataSiniri } from './HataSiniri';
import { grafikVerisi } from '../lib/grafikVerisi';

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];

interface ChartNodeData {
  config: Record<string, unknown>;
  label: string;
  color: string;
  type: string;
}

function ChartView({ node }: { node: { data: ChartNodeData; id: string } }) {
  // GERÇEK veriden çizilir; veri yoksa ya da tür uymuyorsa çizilmez, sebebi
  // yazılır (eski sürüm uydurma pasta/dağılım/yedek veri gösteriyordu).
  const nodeData = node.data as unknown as NodeData;
  const resultData = nodeData.result?.data as Record<string, unknown> | undefined;
  const satirlar = (resultData?.inputData as Record<string, unknown>[] | undefined) ?? [];
  const g = grafikVerisi(satirlar, node.data.config, resultData?.rowCount as number | undefined);
  const baslik = (
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs font-medium text-slate-300">{node.data.label}</span>
      <span className="text-[10px] text-slate-500 capitalize bg-slate-700 px-1.5 py-0.5 rounded">
        {String(node.data.config.chartType || 'bar')}
      </span>
    </div>
  );

  if ('hata' in g) {
    return (
      <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
        {baslik}
        <div className="h-[120px] flex items-center justify-center text-[11px] text-slate-400 text-center px-4">
          {g.hata}
        </div>
      </div>
    );
  }

  const ipucu = { background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '11px' };
  return (
    <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
      {baslik}
      <ResponsiveContainer width="100%" height={250}>
        {g.tip === 'line' ? (
          <LineChart data={g.veri}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={g.xAnahtar} stroke="#94a3b8" fontSize={10} tick={{ fill: '#94a3b8' }} />
            <YAxis stroke="#94a3b8" fontSize={10} tick={{ fill: '#94a3b8' }} />
            <Tooltip contentStyle={ipucu} />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
            {g.yAnahtarlar.map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={false} connectNulls={false} />
            ))}
          </LineChart>
        ) : g.tip === 'pie' ? (
          <PieChart>
            <Pie data={g.veri} dataKey={g.yAnahtarlar[0]} nameKey={g.xAnahtar} cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={4}>
              {g.veri.map((_, index) => (
                <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={ipucu} />
            <Legend wrapperStyle={{ fontSize: '10px' }} />
          </PieChart>
        ) : g.tip === 'scatter' ? (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={g.xAnahtar} name={g.xAnahtar} type="number" stroke="#94a3b8" fontSize={10} />
            <YAxis dataKey={g.yAnahtarlar[0]} name={g.yAnahtarlar[0]} type="number" stroke="#94a3b8" fontSize={10} />
            <Tooltip contentStyle={ipucu} />
            <Scatter data={g.veri} fill={CHART_COLORS[0]} />
          </ScatterChart>
        ) : g.tip === 'area' ? (
          <AreaChart data={g.veri}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={g.xAnahtar} stroke="#94a3b8" fontSize={10} />
            <YAxis stroke="#94a3b8" fontSize={10} />
            <Tooltip contentStyle={ipucu} />
            {g.yAnahtarlar.map((k, i) => (
              <Area key={k} type="monotone" dataKey={k} stackId="1" stroke={CHART_COLORS[i % CHART_COLORS.length]} fill={CHART_COLORS[i % CHART_COLORS.length]} fillOpacity={0.3} />
            ))}
          </AreaChart>
        ) : (
          <BarChart data={g.veri}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={g.xAnahtar} stroke="#94a3b8" fontSize={10} />
            <YAxis stroke="#94a3b8" fontSize={10} />
            <Tooltip contentStyle={ipucu} />
            {g.yAnahtarlar.map((k, i) => (
              <Bar key={k} dataKey={k} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
      <Uyarilar liste={g.uyarilar} />
    </div>
  );
}

interface ResultNodeData extends NodeData {
  color: string;
  label: string;
  type: string;
}

// Sınama A6 (ADR-004 md. 5, AGENTS kural 5): kanıt üreten hesap yalnız sunucuda, tek
// motorda yapılır. Tarayıcı motorunun sonuçları ÖNİZLEMEdir; suç analizi düğümleri (suc_*)
// ve kanıt paketi sunucuda üretilir; ajan yorumu dil modelidir (bağlayıcı değil).
type SonucKaynagi = 'sunucu' | 'dil_modeli' | 'onizleme';
export function sonucKaynagi(tip: string): SonucKaynagi {
  if (tip.startsWith('suc_') || tip === 'evidence_export') return 'sunucu';
  if (tip.startsWith('agent_')) return 'dil_modeli';
  return 'onizleme';
}
const KAYNAK_ETIKET: Record<SonucKaynagi, string> = { sunucu: 'SUNUCU', dil_modeli: 'DİL MODELİ', onizleme: 'ÖNİZLEME' };
const KAYNAK_RENK: Record<SonucKaynagi, string> = {
  sunucu: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  dil_modeli: 'bg-violet-500/15 text-violet-300 border-violet-500/30',
  onizleme: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
};
const KAYNAK_ACIKLAMA: Record<SonucKaynagi, string> = {
  sunucu: 'Sunucuda, Sınama çekirdeğiyle üretildi (kapı, kanıt oturumu ve hash zinciri sunucuda).',
  dil_modeli: 'Yerel dil modelinin yorumu — bağlayıcı değildir, kanıt değildir.',
  onizleme: 'Önizleme: tarayıcı motorunda hesaplandı — kanıt değildir. Kanıt yalnız sunucuda üretilir (Suç Analizi düğümleri, kanıt paketi).',
};

function ResultCard({ node }: { node: { data: ResultNodeData; id: string } }) {
  const [expanded, setExpanded] = useState(false);
  const result = node.data.result;

  if (!result) return null;

  const isError = result.status === 'error';
  const kaynak = sonucKaynagi(node.data.type);

  return (
    <div className={`bg-slate-800/50 rounded-lg border ${isError ? 'border-red-800/50' : 'border-slate-700'} overflow-hidden`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full px-3 py-2 hover:bg-slate-800/80 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded flex items-center justify-center"
            style={{ backgroundColor: node.data.color + '25' }}
          >
            {isError ? (
              <X size={14} className="text-red-400" />
            ) : (
              <CheckCircle2 size={14} style={{ color: node.data.color }} />
            )}
          </div>
          <span className={`text-xs font-medium ${isError ? 'text-red-400' : 'text-slate-300'}`}>
            {node.data.label}
          </span>
          {result.rowCount !== undefined && (
            <span className="text-[10px] text-slate-500">
              {result.rowCount.toLocaleString()} rows
            </span>
          )}
          {!isError && result.demo && (
            <span className="text-[9px] font-bold px-1 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30">DEMO</span>
          )}
          {!isError && (
            <span data-testid={`kaynak-${kaynak}`} title={KAYNAK_ACIKLAMA[kaynak]}
              className={`text-[9px] font-bold px-1 rounded border ${KAYNAK_RENK[kaynak]}`}>{KAYNAK_ETIKET[kaynak]}</span>
          )}
        </div>
        <ChevronDown size={14} className={`text-slate-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-slate-700/50">
          {!isError && kaynak === 'onizleme' && (
            <div className="mt-2 text-[10px] text-slate-400 bg-slate-900/40 border border-slate-700/60 rounded p-2">
              {KAYNAK_ACIKLAMA.onizleme}
            </div>
          )}
          {!isError && result.demo && (
            <div className="mt-2 text-[10px] text-amber-300 bg-amber-900/20 border border-amber-800/40 rounded p-2">
              Sentetik (demo) veriden üretildi — gerçek bulgu değildir. Gerçek veri için kaynağa dosya yükleyin.
            </div>
          )}
          {isError ? (
            <div className="mt-2 text-[10px] text-red-400 bg-red-900/10 p-2 rounded">
              {result.error || 'Unknown error'}
            </div>
          ) : (
            <>
              {/* Node-type specific metrics */}
              <NodeMetrics result={result.data as Record<string, unknown>} nodeType={node.data.type} />

              {/* Motor uyarıları: dışlanan satırlar, kesilen veri, yerine uygulanan
                  yöntem... Sonuç ancak bunlarla birlikte doğru okunur. */}
              <Uyarilar liste={(result.data as Record<string, unknown> | undefined)?.uyarilar} />

              {/* Raw JSON */}
              <div className="mt-2 pt-2 border-t border-slate-700/50">
                <details>
                  <summary className="text-[10px] text-slate-500 cursor-pointer hover:text-slate-400">View raw result</summary>
                  <pre className="mt-1 text-[9px] text-slate-400 bg-slate-900/50 p-2 rounded overflow-auto max-h-[120px]">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </details>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function Uyarilar({ liste }: { liste: unknown }) {
  if (!Array.isArray(liste) || liste.length === 0) return null;
  return (
    <div className="mt-2 space-y-1" data-testid="sonuc-uyarilari">
      {liste.map((u, i) => (
        <div key={i} className="flex gap-1.5 text-[10px] text-amber-300/90 bg-amber-950/30 border border-amber-800/40 rounded px-2 py-1 leading-snug">
          <AlertTriangle size={11} className="shrink-0 mt-0.5" />
          <span>{String(u)}</span>
        </div>
      ))}
    </div>
  );
}

function NodeMetrics({ result, nodeType }: { result: Record<string, unknown>; nodeType: string }) {
  if (!result) return null;

  switch (nodeType) {
    case 'filter':
      return (
        <div className="grid grid-cols-3 gap-2 mt-2">
          <Metric label="Before" value={String((result.rows_before as number) || 0)} />
          <Metric label="After" value={String((result.rows_after as number) || 0)} />
          <Metric label="Rate" value={`${String(((result.rows_after as number) / ((result.rows_before as number) || 1) * 100).toFixed(1))}%`} />
        </div>
      );
    case 'linear_regression': {
      const holdout = result.holdout as { test_r_squared?: number | null; test_n?: number } | null | undefined;
      return (
        <div className="grid grid-cols-3 gap-2 mt-2">
          <Metric label="R² (örneklem içi)" value={String(result.r_squared ?? '—')} color="text-emerald-400" />
          <Metric label="MSE" value={String(result.mse ?? '—')} />
          <Metric label="Features" value={String(((result.coefficients as unknown[]) || []).length)} />
          {holdout && (
            <Metric label={`Test R² (n=${holdout.test_n ?? '?'})`} value={String(holdout.test_r_squared ?? '—')} color="text-sky-400" />
          )}
          <Metric label="Kullanılan satır" value={String(result.sample_size ?? '—')} />
        </div>
      );
    }
    case 'anomaly_detection':
      return (
        <div className="grid grid-cols-3 gap-2 mt-2">
          <Metric label="Total" value={String((result.total_rows as number) || 0)} />
          <Metric label="Anomalies" value={String(result.anomalies_detected || 0)} color="text-red-400" />
          <Metric label="Rate" value={`${String(result.anomaly_rate || 0)}%`} color="text-orange-400" />
        </div>
      );
    case 'association_rules':
      return (
        <div className="mt-2">
          <div className="text-[10px] text-slate-500 mb-1">
            Rules: <span className="text-emerald-400 font-medium">{String(result.rules_found || 0)}</span>
          </div>
          {(result.rules as Array<{ antecedent: string[]; consequent: string[]; confidence: string }> || []).slice(0, 3).map((rule, i: number) => (
            <div key={i} className="flex justify-between text-[10px] bg-slate-900/50 rounded p-1.5 mb-0.5">
              <span className="text-slate-300">{rule.antecedent.join(', ')} {'->'} {rule.consequent.join(', ')}</span>
              <span className="text-emerald-400">{rule.confidence}</span>
            </div>
          ))}
        </div>
      );
    case 'model_validation':
      return <ModelValidationMetrics result={result} />;
    case 'data_clean': {
      const filled = (result.filled_per_column as Record<string, number>) || {};
      return (
        <div className="mt-2 space-y-1.5 text-[10px]">
          <div className="grid grid-cols-2 gap-1">
            <div className="flex justify-between bg-slate-900/50 rounded p-1.5"><span className="text-slate-400">Strategy</span><span className="text-slate-200">{String(result.strategy)}</span></div>
            <div className="flex justify-between bg-slate-900/50 rounded p-1.5"><span className="text-slate-400">Rows</span><span className="text-slate-200">{String(result.rows_before)} → {String(result.rows_after)}</span></div>
            <div className="flex justify-between bg-slate-900/50 rounded p-1.5"><span className="text-slate-400">Dropped</span><span className="text-amber-400">{String(result.rows_dropped)}</span></div>
            <div className="flex justify-between bg-slate-900/50 rounded p-1.5"><span className="text-slate-400">Cells filled</span><span className="text-emerald-400">{String(result.cells_filled)}</span></div>
          </div>
          {Object.keys(filled).length > 0 && (
            <div className="space-y-0.5 pt-1">
              <div className="text-slate-600">filled per column</div>
              {Object.entries(filled).map(([c, n]) => (
                <div key={c} className="flex justify-between"><span className="text-slate-400 truncate">{c}</span><span className="text-emerald-400">+{n}</span></div>
              ))}
            </div>
          )}
        </div>
      );
    }
    case 'data_quality':
      return <DataQualityMetrics result={result} />;
    case 'cross_validation':
      return <CrossValidationMetrics result={result} />;
    case 'pts_source':
    case 'anpr_source':
    case 'mobese_source':
    case 'ihbar_source':
    case 'adli_sicil_source':
      return <PoliceSourceMetrics result={result} />;
    case 'sna':
      return <SnaMetrics result={result} />;
    case 'geo_hotspot':
      return <GeoHotspotMetrics result={result} />;
    case 'temporal_pattern':
      return <TemporalPatternMetrics result={result} />;
    case 'cooccurrence':
      return <CooccurrenceMetrics result={result} />;
    case 'evidence_export':
      return <EvidenceExportMetrics result={result} />;
    case 'random_forest':
    case 'gradient_boosting':
    case 'svm':
    case 'logistic_regression': {
      if (!isMlResult(result as Record<string, unknown>)) {
        return <div className="mt-2 text-[10px] text-slate-500">No metrics returned.</div>;
      }
      const metricRows = extractMetricRows(result as Record<string, unknown>);
      const importance = extractImportance(result as Record<string, unknown>);
      return (
        <div className="mt-2 space-y-1.5">
          <div className="text-[9px] text-slate-600">{String((result as Record<string, unknown>).algorithm || '')}</div>
          <div className="grid grid-cols-2 gap-1">
            {metricRows.map((m) => (
              <div key={m.name} className="flex justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
                <span className="text-slate-400">{m.name}</span>
                <span className="text-emerald-400 font-medium">{m.value}</span>
              </div>
            ))}
          </div>
          {importance.length > 0 && (
            <div className="space-y-0.5">
              <div className="text-[9px] text-slate-600">feature importance</div>
              {importance.map((f) => (
                <div key={f.feature} className="flex items-center gap-1 text-[10px]">
                  <span className="text-slate-300 w-20 truncate">{f.feature}</span>
                  <div className="flex-1 bg-slate-800 rounded h-1.5">
                    <div className="bg-violet-500 h-1.5 rounded" style={{ width: `${Math.min(100, Math.round(f.value * 100))}%` }} />
                  </div>
                  <span className="text-slate-500">{f.value.toFixed(3)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }
    case 'agent_insight':
      return (
        <div className="mt-2 space-y-1.5">
          {result.model ? (
            <div className="text-[9px] text-slate-600">model: {String(result.model)}</div>
          ) : null}
          <div className="text-[11px] text-cyan-100 whitespace-pre-wrap leading-snug bg-cyan-950/30 border border-cyan-800/40 rounded p-2">
            {String(result.insight || '(no insight)')}
          </div>
          <FeedbackButtons kind="node_result" nodeType="agent_insight" />
        </div>
      );
    case 'clustering':
      return (
        <div className="mt-2 space-y-1">
          <div className="text-[10px] text-slate-500">
            Silhouette: <span className="text-emerald-400 font-medium">{String(result.silhouette_score || 0)}</span>
          </div>
          {((result.clusters as Array<{ cluster: number; size: number }>) || []).map((c) => (
            <div key={c.cluster} className="flex justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
              <span className="text-slate-300">Cluster {c.cluster}</span>
              <span className="text-blue-400">{c.size.toLocaleString()} pts</span>
            </div>
          ))}
        </div>
      );
    default:
      if (result.rowCount !== undefined) {
        return (
          <div className="mt-2">
            <Metric label="Output Rows" value={String(result.rowCount)} />
          </div>
        );
      }
      return null;
  }
}

// P2-1: Model Validation Visualization
function ModelValidationMetrics({ result }: { result: Record<string, unknown> }) {
  const perClass = (result.per_class as Array<{ class: string; precision: number; recall: number; f1: number; support: number }>) || [];
  const cm = result.confusion_matrix as Record<string, Record<string, number>> | undefined;
  const classes = (result.classes as string[]) || [];
  const accuracy = result.accuracy as number;

  // Find max value for heatmap scaling
  let maxCmVal = 1;
  if (cm) {
    classes.forEach((c1) => classes.forEach((c2) => { maxCmVal = Math.max(maxCmVal, cm[c1]?.[c2] || 0); }));
  }

  return (
    <div className="mt-2 space-y-2">
      {/* Accuracy */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-slate-500">Accuracy:</span>
        <span className="text-xs font-bold text-emerald-400">{(accuracy * 100).toFixed(1)}%</span>
        <span className="text-[10px] text-slate-600">({String(result.total_samples)} samples)</span>
      </div>

      {/* Confusion Matrix Heatmap */}
      {cm && classes.length > 0 && (
        <div className="bg-slate-900/50 rounded p-2">
          <div className="text-[10px] text-slate-500 mb-1">Confusion Matrix</div>
          <div className="grid" style={{ gridTemplateColumns: `auto repeat(${classes.length}, 1fr)` }}>
            <div />
            {classes.map((c) => <div key={c} className="text-[9px] text-slate-500 text-center px-1">Pred:{c}</div>)}
            {classes.map((actual) => (
              <div key={actual} className="contents">
                <div className="text-[9px] text-slate-500 pr-1 self-center">Act:{actual}</div>
                {classes.map((pred) => {
                  const val = cm[actual]?.[pred] || 0;
                  const isDiag = actual === pred;
                  const intensity = maxCmVal > 0 ? val / maxCmVal : 0;
                  const bgColor = isDiag
                    ? `rgba(16, 185, 129, ${0.1 + intensity * 0.7})`
                    : `rgba(239, 68, 68, ${0.05 + intensity * 0.4})`;
                  return (
                    <div key={pred} className="text-[10px] text-center py-0.5 px-1 rounded-sm m-px" style={{ backgroundColor: bgColor, color: intensity > 0.5 ? '#fff' : '#94a3b8' }}>
                      {val}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Per-class metrics table */}
      {perClass.length > 0 && (
        <div className="space-y-1">
          {perClass.map((c) => (
            <div key={c.class} className="flex items-center justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
              <span className="text-slate-300 font-medium">{c.class}</span>
              <div className="flex gap-3">
                <span className="text-blue-400">P:{c.precision.toFixed(2)}</span>
                <span className="text-emerald-400">R:{c.recall.toFixed(2)}</span>
                <span className="text-purple-400">F1:{c.f1.toFixed(2)}</span>
                <span className="text-slate-500">N={c.support}</span>
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between text-[10px] bg-slate-800/50 rounded p-1.5 border-t border-slate-700">
            <span className="text-slate-400 font-medium">Macro Avg</span>
            <div className="flex gap-3">
              <span className="text-blue-400">P:{Number(result.macro_precision).toFixed(3)}</span>
              <span className="text-emerald-400">R:{Number(result.macro_recall).toFixed(3)}</span>
              <span className="text-purple-400">F1:{Number(result.macro_f1).toFixed(3)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// P2-3: Data Quality Visualization
function DataQualityMetrics({ result }: { result: Record<string, unknown> }) {
  const overallScore = result.overall_score as number;
  const columnReport = (result.columns as Array<{
    column: string; type: string; nullCount: number; nullPct: number;
    unique: number; uniquePct: number; outlierCount: number; outlierPct: number; qualityScore: number;
  }>) || [];
  const totalRows = result.total_rows as number;
  const duplicateRows = result.duplicate_rows as number;

  const scoreColor = overallScore >= 80 ? 'text-emerald-400' : overallScore >= 60 ? 'text-amber-400' : 'text-red-400';
  const scoreBg = overallScore >= 80 ? 'bg-emerald-900/20' : overallScore >= 60 ? 'bg-amber-900/20' : 'bg-red-900/20';

  return (
    <div className="mt-2 space-y-2">
      {/* Overall Score */}
      <div className="flex items-center gap-3">
        <div className={`${scoreBg} rounded px-2 py-1`}>
          <span className={`text-sm font-bold ${scoreColor}`}>{overallScore}</span>
          <span className="text-[10px] text-slate-500">/100</span>
        </div>
        <div className="text-[10px] text-slate-500">
          {totalRows?.toLocaleString()} rows | {duplicateRows > 0 && <span className="text-amber-400">{duplicateRows} dupes</span>}
        </div>
      </div>

      {/* Per-column quality bars */}
      <div className="space-y-1">
        {columnReport.map((col) => (
          <div key={col.column} className="bg-slate-900/50 rounded p-1.5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-slate-300 font-medium">{col.column}</span>
              <div className="flex gap-2">
                <span className="text-[9px] text-slate-500">{col.type}</span>
                {col.nullCount > 0 && <span className="text-[9px] text-amber-400">{col.nullCount} nulls ({col.nullPct}%)</span>}
                {col.outlierCount > 0 && <span className="text-[9px] text-red-400">{col.outlierCount} outliers</span>}
              </div>
            </div>
            {/* Quality bar */}
            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${col.qualityScore >= 80 ? 'bg-emerald-500' : col.qualityScore >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
                style={{ width: `${col.qualityScore}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// P2-4: Cross-Validation Visualization
function CrossValidationMetrics({ result }: { result: Record<string, unknown> }) {
  const folds = (result.folds as Array<{ fold: number; r2: number; mse: number; mae: number; testSize: number }>) || [];
  const avgR2 = result.avg_r2 as number;
  const stdR2 = result.std_r2 as number;
  const avgMse = result.avg_mse as number;
  const avgMae = result.avg_mae as number;

  return (
    <div className="mt-2 space-y-2">
      {/* Summary */}
      <div className="grid grid-cols-4 gap-2">
        <Metric label="Avg R²" value={avgR2?.toFixed(4) || '-'} color="text-emerald-400" />
        <Metric label="Std R²" value={stdR2?.toFixed(4) || '-'} />
        <Metric label="Avg MSE" value={avgMse?.toFixed(4) || '-'} />
        <Metric label="Avg MAE" value={avgMae?.toFixed(4) || '-'} />
      </div>

      {/* Fold details */}
      {folds.length > 0 && (
        <div className="space-y-0.5">
          <div className="text-[10px] text-slate-500 mb-1">{folds.length}-Fold Results</div>
          {folds.map((f) => (
            <div key={f.fold} className="flex items-center justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
              <span className="text-slate-400">Fold {f.fold}</span>
              <div className="flex gap-3">
                <span className="text-emerald-400">R²:{f.r2.toFixed(3)}</span>
                <span className="text-blue-400">MSE:{f.mse.toFixed(2)}</span>
                <span className="text-purple-400">MAE:{f.mae.toFixed(2)}</span>
                <span className="text-slate-600">n={f.testSize}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-slate-900/50 rounded p-2">
      <div className="text-[10px] text-slate-500">{label}</div>
      <div className={`text-sm font-bold ${color || 'text-white'}`}>{value}</div>
    </div>
  );
}

// P3: Police Data Source Metrics
function PoliceSourceMetrics({ result }: { result: Record<string, unknown> }) {
  const system = result.system as string;
  const kvkkClass = result.kvkkClass as string;
  const legalBasis = result.legalBasis as string;
  const isDemo = result._demoMode === true;

  const classColor = kvkkClass === 'Cok Gizli' ? 'text-red-400' : kvkkClass === 'Gizli' ? 'text-orange-400' : 'text-amber-400';
  const classBg = kvkkClass === 'Cok Gizli' ? 'bg-red-900/20' : kvkkClass === 'Gizli' ? 'bg-orange-900/20' : 'bg-amber-900/20';

  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${classBg} ${classColor}`}>{kvkkClass}</span>
        <span className="text-[10px] bg-slate-800 text-slate-500 px-2 py-0.5 rounded">{legalBasis}</span>
        <span className="text-[10px] bg-red-900/20 text-red-400 px-2 py-0.5 rounded">{system}</span>
        {isDemo && <span className="text-[10px] bg-amber-900/20 text-amber-400 px-2 py-0.5 rounded">Demo Veri</span>}
      </div>
      {result.rowCount !== undefined && (
        <div className="text-[10px] text-slate-500">
          {Number(result.rowCount).toLocaleString()} kayit donduruldu
        </div>
      )}
    </div>
  );
}

// P3: Social Network Analysis Visualization
function SnaMetrics({ result }: { result: Record<string, unknown> }) {
  const nodeCount = result.node_count as number;
  const edgeCount = result.edge_count as number;
  const communityCount = result.community_count as number;
  const density = result.network_density as number;
  const topNodes = (result.top_nodes as Array<{ node: string; degree: number; betweenness: number; closeness: number }>) || [];
  const communities = (result.communities as Array<{ id: number; size: number; members: string[] }>) || [];

  return (
    <div className="mt-2 space-y-2">
      <div className="grid grid-cols-4 gap-2">
        <Metric label="Dugum" value={nodeCount?.toString() || '0'} />
        <Metric label="Baglanti" value={edgeCount?.toString() || '0'} />
        <Metric label="Topluluk" value={communityCount?.toString() || '0'} color="text-purple-400" />
        <Metric label="Yogunluk" value={density?.toFixed(3) || '0'} />
      </div>
      {topNodes.length > 0 && (
        <div className="space-y-0.5">
          <div className="text-[10px] text-slate-500">Merkezi Aktorel</div>
          {topNodes.slice(0, 5).map((n) => (
            <div key={n.node} className="flex items-center justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
              <span className="text-slate-300 font-medium">{n.node}</span>
              <div className="flex gap-3">
                <span className="text-blue-400">D:{n.degree}</span>
                <span className="text-emerald-400">B:{n.betweenness.toFixed(3)}</span>
                <span className="text-purple-400">C:{n.closeness.toFixed(3)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
      {communities.length > 0 && (
        <div className="space-y-0.5">
          <div className="text-[10px] text-slate-500">Topluluklar</div>
          {communities.map((c) => (
            <div key={c.id} className="flex items-center justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
              <span className="text-slate-300">Topluluk {c.id}</span>
              <div className="flex gap-2">
                <span className="text-blue-400">{c.size} uye</span>
                <span className="text-slate-500">{c.members.slice(0, 3).join(', ')}{c.members.length > 3 ? '...' : ''}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// P3: Geographic Hotspot Visualization
function GeoHotspotMetrics({ result }: { result: Record<string, unknown> }) {
  const totalPoints = result.total_points as number;
  const hotspotCells = result.hotspot_cells as number;
  const avgDensity = result.avg_density as number;
  const timeWeightedDensity = result.time_weighted_density as number;
  const topHotspots = (result.top_hotspots as Array<{ cell: string; lat: number; lng: number; count: number }>) || [];

  return (
    <div className="mt-2 space-y-2">
      <div className="grid grid-cols-4 gap-2">
        <Metric label="Nokta" value={totalPoints?.toString() || '0'} />
        <Metric label="Hotspot Hucre" value={hotspotCells?.toString() || '0'} color="text-red-400" />
        <Metric label="Ort. Yogunluk" value={avgDensity?.toFixed(1) || '0'} />
        <Metric label="Z-Agirlikli" value={timeWeightedDensity?.toFixed(1) || '0'} color="text-orange-400" />
      </div>
      {topHotspots.length > 0 && (
        <div className="space-y-0.5">
          <div className="text-[10px] text-slate-500">En Sicak Noktalar</div>
          {topHotspots.slice(0, 5).map((h, i) => (
            <div key={i} className="flex items-center justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
              <span className="text-slate-400">{h.lat.toFixed(4)}, {h.lng.toFixed(4)}</span>
              <div className="flex gap-2">
                <span className="text-red-400 font-medium">{h.count} olay</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// P3: Temporal Pattern Visualization
function TemporalPatternMetrics({ result }: { result: Record<string, unknown> }) {
  const bucket = result.bucket as string;
  const totalEvents = result.total_events as number;
  const entropy = result.entropy as number;
  const peakBuckets = (result.peak_buckets as Array<{ bucket: string; count: number }>) || [];
  const distribution = (result.distribution as Array<{ bucket: string; count: number; top_category: string }>) || [];

  // Find max for bar scaling
  const maxCount = Math.max(...distribution.map((d) => d.count), 1);

  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-[10px] text-slate-500">{bucket} bazli | {totalEvents} olay | Entropi: <span className="text-blue-400">{entropy?.toFixed(2)}</span></span>
      </div>
      {/* Distribution bars */}
      <div className="space-y-1">
        {distribution.slice(0, 12).map((d) => (
          <div key={d.bucket} className="flex items-center gap-2">
            <span className="text-[9px] text-slate-400 w-8 text-right">{d.bucket}</span>
            <div className="flex-1 h-3 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full" style={{ width: `${(d.count / maxCount) * 100}%` }} />
            </div>
            <span className="text-[9px] text-slate-500 w-8">{d.count}</span>
          </div>
        ))}
      </div>
      {peakBuckets.length > 0 && (
        <div className="flex flex-wrap gap-1">
          <span className="text-[10px] text-slate-500">Tepe dilimler:</span>
          {peakBuckets.map((p) => (
            <span key={p.bucket} className="text-[9px] bg-red-900/20 text-red-400 px-1.5 py-0.5 rounded">{p.bucket} ({p.count})</span>
          ))}
        </div>
      )}
    </div>
  );
}

// P3: Co-occurrence Visualization
function CooccurrenceMetrics({ result }: { result: Record<string, unknown> }) {
  const totalEntities = result.total_entities as number;
  const totalContexts = result.total_contexts as number;
  const pairCount = result.cooccurrence_pairs as number;
  const topPairs = (result.top_pairs as Array<{ entity_a: string; entity_b: string; cooccurrence_count: number; shared_contexts: string[] }>) || [];
  const topEntities = (result.top_entities as Array<{ entity: string; context_count: number }>) || [];

  return (
    <div className="mt-2 space-y-2">
      <div className="grid grid-cols-3 gap-2">
        <Metric label="Varlik" value={totalEntities?.toString() || '0'} />
        <Metric label="Baglam" value={totalContexts?.toString() || '0'} />
        <Metric label="Es-Olusum" value={pairCount?.toString() || '0'} color="text-purple-400" />
      </div>
      {topPairs.length > 0 && (
        <div className="space-y-0.5">
          <div className="text-[10px] text-slate-500">En Sik Es-Olusumlar</div>
          {topPairs.slice(0, 5).map((p, i) => (
            <div key={i} className="flex items-center justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
              <span className="text-slate-300">{p.entity_a} <span className="text-slate-600">-</span> {p.entity_b}</span>
              <span className="text-purple-400 font-medium">{p.cooccurrence_count} kez</span>
            </div>
          ))}
        </div>
      )}
      {topEntities.length > 0 && (
        <div className="space-y-0.5">
          <div className="text-[10px] text-slate-500">En Merkezi Varliklar</div>
          {topEntities.slice(0, 5).map((e) => (
            <div key={e.entity} className="flex items-center justify-between text-[10px] bg-slate-900/50 rounded p-1.5">
              <span className="text-slate-300">{e.entity}</span>
              <span className="text-blue-400">{e.context_count} baglam</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Kanıt paketi: teknik bütünlük kanıtı (hukuki uygunluk iddiası YOK).
const HARP_ETIKET: Record<string, string> = {
  iletildi: 'mühürlendi',
  iletilemedi: 'iletilemedi — eşitleme bekliyor',
  reddedildi: 'REDDEDİLDİ — defter çelişkisi',
  yapilandirilmamis: 'yapılandırılmamış',
};

function EvidenceExportMetrics({ result }: { result: Record<string, unknown> }) {
  const kayitli = result.durum === 'KAYITLI';
  const satir = (etiket: string, deger: unknown, mono = false) => (
    <div className="flex justify-between gap-2 text-[10px]">
      <span className="text-slate-500 shrink-0">{etiket}</span>
      <span className={`text-slate-300 text-right break-all ${mono ? 'font-mono' : ''}`}>{String(deger ?? '—')}</span>
    </div>
  );
  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-2">
        {kayitli
          ? <CheckCircle2 size={14} className="text-emerald-400" />
          : <AlertTriangle size={14} className="text-amber-400" />}
        <span className={`text-[10px] font-medium ${kayitli ? 'text-emerald-400' : 'text-amber-400'}`}>
          {kayitli ? `Kanıt defterine kaydedildi (#${String(result.defter_sira)})` : 'KAYITSIZ — defter makbuzu yok'}
        </span>
      </div>
      <div className="bg-slate-900/50 rounded p-2 space-y-1">
        {satir('Dosya No', result.dosya_no)}
        {satir('Kanıt ID', result.kanit_id, true)}
        {satir('Satır × sütun', `${String(result.satir)} × ${String(result.sutun)}`)}
        {kayitli && satir('Sunucu zamanı', new Date(String(result.sunucu_zamani)).toLocaleString('tr-TR'))}
        {kayitli && satir('Kaydeden (oturum)', (result.aktor as { ad?: string | null; id?: number } | null)?.ad ?? (result.aktor as { id?: number } | null)?.id)}
        {satir('Beyan eden', result.beyan_eden || '—')}
        {kayitli && satir('HARP dış çapası', HARP_ETIKET[String(result.harp_durumu)] ?? '—')}
        {kayitli && result.harp_kayit_id ? satir('HARP kayıt', result.harp_kayit_id, true) : null}
        <div className="pt-1 border-t border-slate-700 space-y-1">
          <div className="text-[9px] text-slate-500">Veri SHA-256 (tüm satırlar, RFC 8785):</div>
          <div className="text-[9px] font-mono text-emerald-400 break-all">{String(result.veri_sha256)}</div>
          <div className="text-[9px] text-slate-500">Paket SHA-256:</div>
          <div className="text-[9px] font-mono text-slate-300 break-all">{String(result.paket_sha256)}</div>
          {kayitli && (
            <>
              <div className="text-[9px] text-slate-500">İmza anahtarı (Ed25519) parmak izi:</div>
              <div className="text-[9px] font-mono text-slate-400 break-all">{String(result.anahtar_parmak_izi)}</div>
            </>
          )}
        </div>
      </div>
      <div className="text-[9px] text-slate-500 leading-snug">
        Teknik bütünlük kanıtıdır; hukuki geçerlilik ayrıca değerlendirilir. Doğrulama:
        <span className="font-mono"> scripts/kanit_dogrula.py</span>
      </div>
    </div>
  );
}

export default function ResultsPanel() {
  const showResults = useStore((s) => s.showResults);
  const nodes = useStore((s) => s.nodes);
  const setShowResults = useStore((s) => s.setShowResults);
  const [activeTab, setActiveTab] = useState<'summary' | 'charts' | 'logs'>('summary');

  if (!showResults) return null;

  const resultNodes = nodes.filter((n) => n.data.result);
  const completedNodes = resultNodes.filter((n) => n.data.result?.status === 'success');
  const chartNodes = completedNodes.filter((n) => n.data.type === 'chart');
  const errorNodes = resultNodes.filter((n) => n.data.result?.status === 'error');

  return (
    <div className="h-[280px] bg-slate-900 border-t border-slate-800 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Results</span>
          <div className="flex bg-slate-800 rounded-lg p-0.5">
            {(['summary', 'charts', 'logs'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1 text-[10px] font-medium rounded-md transition-all capitalize ${
                  activeTab === tab
                    ? 'bg-slate-700 text-white'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
          {errorNodes.length > 0 && (
            <span className="text-[10px] text-red-400 bg-red-400/10 px-1.5 py-0.5 rounded-full">
              {errorNodes.length} error{errorNodes.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <button onClick={() => setShowResults(false)} className="text-slate-500 hover:text-white transition-colors">
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === 'summary' && (
          <div className="space-y-2">
            {completedNodes.length === 0 && errorNodes.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">No results yet. Run the workflow first.</div>
            ) : (
              <>
                {/* Kart başına sınır: tek bir beklenmedik sonuç biçimi paneli düşürmez. */}
                {[...completedNodes, ...errorNodes].map((node) => (
                  <HataSiniri key={node.id} kompakt bolge={`"${node.data.label}" sonucu`} sifirlaAnahtari={node.data.result}>
                    <ResultCard node={node as unknown as { data: ResultNodeData; id: string }} />
                  </HataSiniri>
                ))}
              </>
            )}
          </div>
        )}

        {activeTab === 'charts' && (
          <div className="space-y-3">
            {chartNodes.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">No chart nodes in workflow</div>
            ) : (
              chartNodes.map((node) => (
                <HataSiniri key={node.id} kompakt bolge={`"${node.data.label}" grafiği`} sifirlaAnahtari={node.data.result}>
                  <ChartView node={node as unknown as { data: ChartNodeData; id: string }} />
                </HataSiniri>
              ))
            )}
          </div>
        )}

        {activeTab === 'logs' && <LogView />}
      </div>
    </div>
  );
}

function LogView() {
  const logs = useStore((s) => s.logs);

  return (
    <div className="h-full">
      {logs.length === 0 ? (
        <div className="text-center py-8 text-xs text-slate-500">No logs yet</div>
      ) : (
        <div className="space-y-0.5 font-mono text-[10px]">
          {logs.map((log, i) => {
            const lower = log.toLowerCase();
            const isError = lower.includes('error');
            const isSuccess = lower.includes('completed') && lower.includes('workflow');
            const isStart = lower.includes('starting');
            return (
              <div
                key={i}
                className={`px-2 py-0.5 rounded ${
                  isError ? 'bg-red-900/20 text-red-400' :
                  isSuccess ? 'bg-emerald-900/20 text-emerald-400' :
                  isStart ? 'bg-blue-900/20 text-blue-400' :
                  'text-slate-400'
                }`}
              >
                {log}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
