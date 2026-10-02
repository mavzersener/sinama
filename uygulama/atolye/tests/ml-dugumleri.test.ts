import { describe, it, expect, vi, afterEach } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import { executeNode, type ExecutionResult } from '../src/engine/executionEngine';

/**
 * Sunucu taraflı 8 ML düğümünün sözleşmesi (karakterizasyon): hangi uca hangi
 * gövdeyle gidildiği, doğrulama ve hata iletileri, satır sınırı ve sayısal
 * süzme. Faz 4'te 8 kopya fonksiyon tek genel yürütücüye indirilirken
 * davranışın birebir korunduğunu bu testler kanıtlar.
 */

const satirlar = Array.from({ length: 40 }, (_, i) => ({
  x1: i, x2: (i * 3) % 17, y: 100 + i * 2, sinif: i % 2 ? 'A' : 'B', tarih: `2026-01-${String(1 + (i % 28)).padStart(2, '0')}`,
}));
const kolonlar = ['x1', 'x2', 'y', 'sinif', 'tarih'];

const d = (id: string, type: string, config: Record<string, unknown>): Node<NodeData> =>
  ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { label: id, type, category: 'x', icon: 'x', color: '#000', config, status: 'idle' } }) as Node<NodeData>;

async function kos(tip: string, config: Record<string, unknown>, rows: Record<string, unknown>[] = satirlar, sinyal?: AbortSignal) {
  const sonuclar = new Map<string, ExecutionResult>();
  const edges: Edge[] = [];
  if (rows.length) {
    const kaynak = d('csv', 'csv_source', { _uploadedData: { rows, columns: Object.keys(rows[0]), filename: 'm.csv' } });
    sonuclar.set('csv', await executeNode(kaynak, [], sonuclar));
    edges.push({ id: 'e', source: 'csv', target: 'ml' });
  }
  return executeNode(d('ml', tip, config), edges, sonuclar, { sinyal });
}

/** fetch'i yakalar; yanıtı belirlenebilir. */
function yakala(yanit: () => Response | Promise<Response> = () => new Response(JSON.stringify({ metrics: { accuracy: 0.9 } }), { status: 200 })) {
  const cagrilar: Array<{ url: string; govde: Record<string, unknown>; init: RequestInit }> = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit) => {
    cagrilar.push({ url, govde: JSON.parse(String(init.body)), init });
    return yanit();
  }));
  return cagrilar;
}
afterEach(() => vi.unstubAllGlobals());

const HEDEFLI: Array<[string, string, Record<string, unknown>, string, Record<string, unknown>]> = [
  ['random_forest', 'Random Forest', { target: 'sinif' }, '/api/ml/ml/random-forest',
    { target_column: 'sinif', task: 'classification', split: { test_size: 0.2 }, n_estimators: 100 }],
  ['arima', 'ARIMA', { target: 'y' }, '/api/ml/ml/arima',
    { target_column: 'y', date_column: null, order: [1, 1, 1], forecast_steps: 10 }],
  ['gradient_boosting', 'Gradient Boosting', { target: 'sinif' }, '/api/ml/ml/gradient-boosting',
    { target_column: 'sinif', split: { test_size: 0.2 }, task: 'classification', n_estimators: 100, max_depth: 3, learning_rate: 0.1 }],
  ['svm', 'SVM', { target: 'sinif' }, '/api/ml/ml/svm',
    { target_column: 'sinif', split: { test_size: 0.2 }, task: 'classification', kernel: 'rbf', C: 1 }],
  ['logistic_regression', 'Logistic Regression', { target: 'sinif' }, '/api/ml/ml/logistic-regression',
    { target_column: 'sinif', split: { test_size: 0.2 }, C: 1, max_iter: 100 }],
];
const OZELLIKLI: Array<[string, string, string, Record<string, unknown>]> = [
  ['dbscan', 'DBSCAN', '/api/ml/ml/dbscan', { eps: 0.5, min_samples: 5 }],
  ['pca', 'PCA', '/api/ml/ml/pca', { n_components: 2 }],
  ['hierarchical', 'Hierarchical Clustering', '/api/ml/ml/hierarchical', { n_clusters: 3, linkage: 'ward' }],
];

describe('hedefli ML düğümleri', () => {
  it.each(HEDEFLI)('%s: varsayılan gövde, uç ve sinyal', async (tip, _ad, config, uc, beklenen) => {
    const c = yakala();
    const sinyal = new AbortController().signal;
    const r = await kos(tip, config, satirlar, sinyal);
    expect(r.status).toBe('success');
    expect(c).toHaveLength(1);
    expect(c[0].url).toBe(uc);
    expect(c[0].init.signal).toBe(sinyal);
    expect(c[0].init.credentials).toBe('include');
    expect(c[0].govde).toEqual({ dataset: { columns: kolonlar, data: satirlar }, ...beklenen });
    expect(r.data).toEqual({ metrics: { accuracy: 0.9 } });
    expect(r.rowCount).toBe(40);
  });

  it.each(HEDEFLI)('%s: satır yoksa ve hedef yoksa hata iletisi', async (tip, ad) => {
    yakala();
    expect((await kos(tip, { target: 'sinif' }, [])).error).toBe(`Connect a data source with rows to ${ad}, then run.`);
    expect((await kos(tip, {})).error).toBe('Target column is required.');
  });

  it('yapılandırma değerleri gövdeye doğru eşlenir', async () => {
    const c = yakala();
    await kos('random_forest', { target: 'y', task: 'regression', nEstimators: 50, testSize: 30 });
    await kos('arima', { target: 'y', dateColumn: 'tarih', p: 2, d: 0, q: 1, forecastSteps: 5 });
    await kos('gradient_boosting', { target: 'y', task: 'regression', nEstimators: 20, maxDepth: 5, learningRate: 0.05, testSize: 25 });
    await kos('svm', { target: 'sinif', kernel: 'linear', c: 2.5, testSize: 10 });
    await kos('logistic_regression', { target: 'sinif', c: 0.5, maxIter: 300 });
    const govde = (i: number) => { const { dataset: _d, ...kalan } = c[i].govde; void _d; return kalan; };
    expect(govde(0)).toEqual({ target_column: 'y', task: 'regression', split: { test_size: 0.3 }, n_estimators: 50 });
    expect(govde(1)).toEqual({ target_column: 'y', date_column: 'tarih', order: [2, 0, 1], forecast_steps: 5 });
    expect(govde(2)).toEqual({ target_column: 'y', split: { test_size: 0.25 }, task: 'regression', n_estimators: 20, max_depth: 5, learning_rate: 0.05 });
    expect(govde(3)).toEqual({ target_column: 'sinif', split: { test_size: 0.1 }, task: 'classification', kernel: 'linear', C: 2.5 });
    expect(govde(4)).toEqual({ target_column: 'sinif', split: { test_size: 0.2 }, C: 0.5, max_iter: 300 });
  });

  it('ön-kontrol çelişkili görevi sunucuya GİTMEDEN durdurur (kategorik hedefte regresyon)', async () => {
    const c = yakala();
    const r = await kos('random_forest', { target: 'sinif', task: 'regression' });
    expect(r.status).toBe('error');
    expect(c).toHaveLength(0);
  });
});

describe('özellikli ML düğümleri', () => {
  const kirli = satirlar.map((r, i) => (i % 10 === 0 ? { ...r, x2: '' } : i === 5 ? { ...r, x1: '37,5' } : r));

  it.each(OZELLIKLI)('%s: yalnız seçili özellikleri tam olan satırlar, SAYIYA çevrilmiş gider; dışlama uyarısı', async (tip, _ad, uc, beklenen) => {
    const c = yakala();
    const r = await kos(tip, { features: 'x1, x2' }, kirli);
    expect(r.status).toBe('success');
    expect(c[0].url).toBe(uc);
    const gonderilen = c[0].govde.dataset as { columns: string[]; data: Record<string, unknown>[] };
    expect(gonderilen.columns).toEqual(kolonlar);
    expect(gonderilen.data).toHaveLength(36); // 4 satırda x2 boş
    expect(gonderilen.data.find((x) => x.y === 110)!.x1).toBe(37.5); // "37,5" → 37.5
    const { dataset: _d, ...kalan } = c[0].govde;
    void _d;
    expect(kalan).toEqual({ feature_columns: ['x1', 'x2'], ...beklenen });
    expect(r.data.uyarilar).toEqual(['4 / 40 satır (%10.0) seçili özelliklerde boş/sayısal olmayan hücre için dışlandı.']);
  });

  it.each(OZELLIKLI)('%s: satır yoksa ve özellik yoksa hata iletisi', async (tip, ad) => {
    yakala();
    expect((await kos(tip, { features: 'x1' }, [])).error).toBe(`Connect a data source with rows to ${ad}, then run.`);
    expect((await kos(tip, { features: ' , ' })).error).toBe('Feature columns are required.');
  });

  it.each(OZELLIKLI)('%s: özellik alanı DİZİ olarak gelse de çalışır (eskiden .split → çöküyordu)', async (tip) => {
    const c = yakala();
    const r = await kos(tip, { features: ['x1', 'x2'] });
    expect(r.status).toBe('success');
    expect(c[0].govde.feature_columns).toEqual(['x1', 'x2']);
  });

  it('yapılandırma değerleri gövdeye doğru eşlenir', async () => {
    const c = yakala();
    await kos('dbscan', { features: 'x1', eps: 1.5, minSamples: 3 });
    await kos('pca', { features: 'x1,x2', nComponents: 1 });
    await kos('hierarchical', { features: 'x1', nClusters: 4, linkage: 'average' });
    expect(c.map((x) => { const { dataset: _d, ...k } = x.govde; void _d; return k; })).toEqual([
      { feature_columns: ['x1'], eps: 1.5, min_samples: 3 },
      { feature_columns: ['x1', 'x2'], n_components: 1 },
      { feature_columns: ['x1'], n_clusters: 4, linkage: 'average' },
    ]);
  });
});

describe('ortak davranış (tüm ML düğümleri)', () => {
  const HEPSI: Array<[string, Record<string, unknown>]> = [
    ...HEDEFLI.map(([t, , c]) => [t, c] as [string, Record<string, unknown>]),
    ...OZELLIKLI.map(([t]) => [t, { features: 'x1,x2' }] as [string, Record<string, unknown>]),
  ];

  it.each(HEPSI)('%s: 401 → oturum iletisi; hata gövdesi → detay; ağ hatası → ileti', async (tip, config) => {
    yakala(() => new Response('', { status: 401 }));
    expect((await kos(tip, config)).error).toBe('Sign in to use server-side ML (cloud feature).');
    yakala(() => new Response(JSON.stringify({ detail: 'hedef sabit' }), { status: 422 }));
    expect((await kos(tip, config)).error).toBe('hedef sabit');
    yakala(() => new Response(JSON.stringify({ error: 'e' }), { status: 500 }));
    expect((await kos(tip, config)).error).toBe('e');
    yakala(() => new Response('bozuk', { status: 503 }));
    expect((await kos(tip, config)).error).toBe('ML service error (503)');
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('ağ koptu'); }));
    expect((await kos(tip, config)).error).toBe('ağ koptu');
  });

  it.each(HEPSI)('%s: 5000 satır sınırı uyarısı, sunucunun kendi uyarıları korunur', async (tip, config) => {
    const cok = Array.from({ length: 5003 }, (_, i) => ({ ...satirlar[i % 40] }));
    const c = yakala(() => new Response(JSON.stringify({ uyarilar: ['sunucu notu'] }), { status: 200 }));
    const r = await kos(tip, config, cok);
    expect((c[0].govde.dataset as { data: unknown[] }).data).toHaveLength(5000);
    expect(r.data.uyarilar).toEqual(['sunucu notu', 'Sunucuya yalnız İLK 5000 satır gönderildi (toplam 5003); kalan 3 satır analize girmedi.']);
    expect(r.rowCount).toBe(5000);
  });
});
