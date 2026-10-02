// Sunucu taraflı ML düğümleri (ml-service, /api/ml vekili): tablo + tek yürütücü, satır sınırı ve sayısal süzme.
// (executionEngine.ts'den bölündü — Faz 4.)

import { sayiCoz } from '../istatistik';
import { csvAlan, dislamaUyarisi, makeResult, makeError, type ExecutionResult } from '../sonuc';

// ---- Sunucu taraflı ML düğümleri (ml-service, kimlik korumalı /api/ml vekili) ----
//
// Eskiden 8 ayrı, ~45 satırlık kopya fonksiyondu; yalnız uç nokta, zorunlu
// alan ve gövde alanları farklıydı (özellikli üçü `.split` kullandığı için
// dizi olarak gelen alanda çöküyordu). Tablo + tek yürütücü; davranış
// tests/ml-dugumleri.test.ts ile sabitlendi.

type MlAilesi =
  /** Hedef sütun zorunlu; satırlar olduğu gibi gider (sınıflama/regresyon/zaman serisi). */
  | 'hedef'
  /** Özellik sütunları zorunlu; bu sütunlarda sayısal olmayan satır dışlanır, değerler sayıya çevrilir. */
  | 'ozellik';

interface MlTanimi {
  ad: string;
  /** /api/ml/ml/<uc> */
  uc: string;
  aile: MlAilesi;
  /** Gövdeye eklenen düğüme özgü alanlar (dataset ve hedef/özellik dışında). */
  alanlar: (c: Record<string, unknown>) => Record<string, unknown>;
}

const bolunme = (c: Record<string, unknown>) => ({ split: { test_size: Number(c.testSize ?? 20) / 100 } });
const gorev = (c: Record<string, unknown>) => (c.task as string) || 'classification';

export const ML_DUGUMLERI: Record<string, MlTanimi> = {
  random_forest: {
    ad: 'Random Forest', uc: 'random-forest', aile: 'hedef',
    alanlar: (c) => ({ task: gorev(c), ...bolunme(c), n_estimators: Number(c.nEstimators ?? 100) }),
  },
  arima: {
    ad: 'ARIMA', uc: 'arima', aile: 'hedef',
    alanlar: (c) => ({
      date_column: (c.dateColumn as string) || null,
      order: [Number(c.p ?? 1), Number(c.d ?? 1), Number(c.q ?? 1)],
      forecast_steps: Number(c.forecastSteps ?? 10),
    }),
  },
  gradient_boosting: {
    ad: 'Gradient Boosting', uc: 'gradient-boosting', aile: 'hedef',
    alanlar: (c) => ({
      ...bolunme(c), task: gorev(c), n_estimators: Number(c.nEstimators ?? 100),
      max_depth: Number(c.maxDepth ?? 3), learning_rate: Number(c.learningRate ?? 0.1),
    }),
  },
  svm: {
    ad: 'SVM', uc: 'svm', aile: 'hedef',
    alanlar: (c) => ({ ...bolunme(c), task: gorev(c), kernel: (c.kernel as string) || 'rbf', C: Number(c.c ?? 1.0) }),
  },
  logistic_regression: {
    ad: 'Logistic Regression', uc: 'logistic-regression', aile: 'hedef',
    alanlar: (c) => ({ ...bolunme(c), C: Number(c.c ?? 1.0), max_iter: Number(c.maxIter ?? 100) }),
  },
  dbscan: {
    ad: 'DBSCAN', uc: 'dbscan', aile: 'ozellik',
    alanlar: (c) => ({ eps: Number(c.eps ?? 0.5), min_samples: Number(c.minSamples ?? 5) }),
  },
  pca: {
    ad: 'PCA', uc: 'pca', aile: 'ozellik',
    alanlar: (c) => ({ n_components: Number(c.nComponents ?? 2) }),
  },
  hierarchical: {
    ad: 'Hierarchical Clustering', uc: 'hierarchical', aile: 'ozellik',
    alanlar: (c) => ({ n_clusters: Number(c.nClusters ?? 3), linkage: (c.linkage as string) || 'ward' }),
  },
};

export async function execMl(
  nodeId: string,
  tip: string,
  config: Record<string, unknown>,
  inputData: Record<string, unknown> | null,
  sinyal?: AbortSignal,
): Promise<ExecutionResult> {
  const t = ML_DUGUMLERI[tip];
  const allRows = (inputData?.rows as Record<string, unknown>[] | undefined) ?? [];
  if (allRows.length === 0) {
    return makeError(nodeId, tip, `Connect a data source with rows to ${t.ad}, then run.`);
  }
  let secim: Record<string, unknown>;
  let ozellikler: string[] = [];
  if (t.aile === 'hedef') {
    const target = (config.target as string) || '';
    if (!target) return makeError(nodeId, tip, 'Target column is required.');
    secim = { target_column: target };
  } else {
    // csvAlan: alan metin ("a, b") ya da dizi olabilir (eski kayıtlar, defaultConfig).
    ozellikler = csvAlan(config.features);
    if (ozellikler.length === 0) return makeError(nodeId, tip, 'Feature columns are required.');
    secim = { feature_columns: ozellikler };
  }
  const rows = allRows.slice(0, SUNUCU_SATIR_SINIRI);
  const gonderilen = t.aile === 'ozellik' ? numericRows(rows, ozellikler) : rows;
  const columns = (inputData?.columns as string[] | undefined) ?? Object.keys(rows[0] ?? {});

  try {
    const resp = await fetch(`/api/ml/ml/${t.uc}`, {
      method: 'POST',
      signal: sinyal,
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ dataset: { columns, data: gonderilen }, ...secim, ...t.alanlar(config) }),
    });

    if (resp.status === 401) {
      return makeError(nodeId, tip, 'Sign in to use server-side ML (cloud feature).');
    }
    if (!resp.ok) {
      const detail = (await resp.json().catch(() => ({}))) as { error?: string; detail?: string };
      return makeError(nodeId, tip, detail.error || detail.detail || `ML service error (${resp.status})`);
    }

    const out = (await resp.json()) as Record<string, unknown>;
    return makeResult(nodeId, tip, mlSonuc(out, sunucuUyarilari(allRows.length, rows.length, rows.length - gonderilen.length)), rows.length);
  } catch (err) {
    return makeError(nodeId, tip, err instanceof Error ? err.message : 'ML request failed');
  }
}

/**
 * Sunucuya gönderilen satır sınırı (istek gövdesi). ÖRNEK değil, İLK N satır
 * gider — aşıldığında sonuç bunu SÖYLER (eskiden sessizce kesiliyordu).
 */
export const SUNUCU_SATIR_SINIRI = 5000;

export function sunucuUyarilari(toplam: number, gonderilen: number, dislanan = 0): string[] {
  const u: string[] = [];
  if (toplam > gonderilen) {
    u.push(`Sunucuya yalnız İLK ${gonderilen} satır gönderildi (toplam ${toplam}); kalan ${toplam - gonderilen} satır analize girmedi.`);
  }
  const d = dislamaUyarisi(dislanan, gonderilen, 'seçili özelliklerde boş/sayısal olmayan hücre');
  if (d) u.push(d);
  return u;
}

/** ML yanıtına motor uyarılarını ekler (sunucunun kendi uyarıları korunur). */
function mlSonuc(out: Record<string, unknown>, uyarilar: string[]): Record<string, unknown> {
  if (!uyarilar.length) return out;
  const onceki = Array.isArray(out.uyarilar) ? (out.uyarilar as string[]) : [];
  return { ...out, uyarilar: [...onceki, ...uyarilar] };
}

/**
 * Keep only rows where EVERY listed column is a real, finite number.
 * Guards server-side ML (DBSCAN/PCA/Hierarchical) against garbage-in: rows with
 * empty/blank coordinate cells otherwise collapse a column to object dtype in
 * pandas, so the model silently drops a feature (observed on real police data:
 * empty lat cells -> n_features 1, one meaningless cluster).
 */
export function numericRows(rows: Record<string, unknown>[], cols: string[]): Record<string, unknown>[] {
  // sayiCoz: Number(true)===1 kabul ediliyor, "37,58" reddediliyordu (ön-kontrol
  // ise kabul ediyordu). Seçili sütunlar SAYIYA çevrilerek gönderilir —
  // sunucu metin "37,58"i ayrıştıramaz.
  const out: Record<string, unknown>[] = [];
  for (const r of rows) {
    const o: Record<string, unknown> = { ...r };
    let tam = true;
    for (const c of cols) {
      const n = sayiCoz(r[c]);
      if (n === null) { tam = false; break; }
      o[c] = n;
    }
    if (tam) out.push(o);
  }
  return out;
}
