/** Pure helpers to shape server-side ML results for display. */

export interface MetricRow { name: string; value: string }
export interface ImportanceRow { feature: string; value: number }

export function isMlResult(data: Record<string, unknown> | null | undefined): boolean {
  return !!data && typeof data.algorithm === 'string' && 'metrics' in data;
}

export function extractMetricRows(data: Record<string, unknown>): MetricRow[] {
  const metrics = (data.metrics as Record<string, unknown>) || {};
  return Object.entries(metrics)
    .filter(([, v]) => typeof v === 'number' && Number.isFinite(v))
    .map(([k, v]) => ({ name: k, value: (v as number).toFixed(4) }));
}

export function extractImportance(data: Record<string, unknown>, topN = 8): ImportanceRow[] {
  const imp = (data.feature_importance as Record<string, unknown>) || {};
  return Object.entries(imp)
    .filter(([, v]) => typeof v === 'number' && Number.isFinite(v))
    .map(([feature, value]) => ({ feature, value: value as number }))
    .sort((a, b) => b.value - a.value)
    .slice(0, topN);
}