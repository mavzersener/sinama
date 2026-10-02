/* eslint-disable @typescript-eslint/no-explicit-any -- test, motorun dinamik sonuç JSON'unu derinlemesine okur */
import { describe, it, expect } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import { executeNode, type ExecutionResult } from '../src/engine/executionEngine';
import type { NodeData } from '../src/store/useStore';

/**
 * Tarayıcı motorunun sayısal doğruluğu — denetimde (23 Eyl 2026) bulunan
 * SESSİZ YANLIŞ sonuç sınıfı. Her test, eski motorun uyarısız yanlış sayı
 * ürettiği bir durumu sabitler.
 */

const kaynak = (rows: Record<string, unknown>[]) => ({
  id: 'src', type: 'custom', position: { x: 0, y: 0 },
  data: { type: 'csv_source', label: 'src', config: { _uploadedData: { rows, columns: Object.keys(rows[0] ?? {}), filename: 't.csv' } } },
}) as unknown as Node<NodeData>;
const dugum = (type: string, config: Record<string, unknown>) => ({
  id: 'n', type: 'custom', position: { x: 0, y: 0 }, data: { type, label: type, config },
}) as unknown as Node<NodeData>;

async function kos(rows: Record<string, unknown>[], type: string, config: Record<string, unknown>) {
  const edges = [{ id: 'e', source: 'src', target: 'n', sourceHandle: 'output', targetHandle: 'input' }] as Edge[];
  const sonuclar = new Map<string, ExecutionResult>();
  sonuclar.set('src', await executeNode(kaynak(rows), edges, sonuclar));
  const r = await executeNode(dugum(type, config), edges, sonuclar);
  expect(r.status, r.error).toBe('success');
  return r.data as Record<string, any>;
}

// Gerçek ilişki y = 2x; iki satırda birer hücre boş. Tam çiftlerde r = 1.
const Y2X = [
  { x: 1, y: 2 }, { x: 2, y: null }, { x: 3, y: 6 }, { x: null, y: 8 }, { x: 5, y: 10 }, { x: 6, y: 12 },
];

describe('eksik hücre: 0 sayılmaz, satırlar kaymaz', () => {
  it('istatistik: boş hücre count/mean/min\'e girmez (eski: count=6, min=0)', async () => {
    const d = await kos(Y2X, 'statistics', { columns: 'x,y', stats: ['count', 'mean', 'min', 'median'] });
    expect(d.stats.x).toMatchObject({ count: 5, mean: 3.4, min: 1, median: 3, eksik: 1 });
    expect(d.stats.y).toMatchObject({ count: 5, mean: 7.6, min: 2, median: 8 });
    expect(d.uyarilar.join(' ')).toMatch(/x: 1 boş/);
  });

  it('korelasyon: çift bazlı tam kayıt (eski: Pearson 0.64)', async () => {
    for (const method of ['pearson', 'spearman', 'kendall']) {
      const d = await kos(Y2X, 'correlation', { columns: 'x,y', method });
      expect(d.matrix.x.y, method).toBe(1);
      expect(d.n_matrix.x.y).toBe(4);
      expect(d.uyarilar.join(' ')).toMatch(/çift başına 4 satır kullanıldı \(toplam 6/);
    }
  });

  it('regresyon: eğim 2, R² 1 (eski: 1.28 / 0.41)', async () => {
    const d = await kos(Y2X, 'linear_regression', { target: 'y', features: 'x', testSize: 0 });
    expect(d.coefficients).toEqual([{ feature: 'x', coefficient: 2 }]);
    expect(d.intercept).toBe(0);
    expect(d.r_squared).toBe(1);
    expect(d.sample_size).toBe(4);
    expect(d.n_dislanan).toBe(2);
  });

  it('toplama: boş değer 0 değil; değer sütunu seçilebilir ve raporlanır', async () => {
    const rows = [
      { g: 'a', v: 10, w: 1 }, { g: 'a', v: null, w: 1 }, { g: 'b', v: 4, w: 1 }, { g: 'b', v: 6, w: 1 },
    ];
    const d = await kos(rows, 'aggregate', { groupBy: 'g', aggregations: ['COUNT', 'AVG', 'MIN'], valueColumn: 'v' });
    const a = d.rows.find((r: any) => r.g === 'a');
    expect(a).toMatchObject({ count: 2, avg: 10, min: 10 }); // eski: avg 5, min 0
    expect(d.deger_sutunu).toBe('v');
    const oto = await kos(rows, 'aggregate', { groupBy: 'g', aggregations: ['SUM'] });
    expect(oto.deger_sutunu).toBe('v');
    expect(oto.uyarilar.join(' ')).toMatch(/ilk sayısal sütun kullanıldı: v/);
  });
});

describe('aykırı değer: doğru satıra atanır', () => {
  // 3. satırda 'a' boş; aykırı değer 6. satırda (a=1000). Eski motor süzülmüş
  // diziyi values[i] ile satırlara geri eşlediği için aykırıyı BAŞKA satıra
  // yazıyor, boş hücreyi de 0 sayıp sahte aykırı üretiyordu.
  const rows = [
    { id: 'r1', a: 10 }, { id: 'r2', a: 11 }, { id: 'r3', a: null }, { id: 'r4', a: 12 },
    { id: 'r5', a: 10 }, { id: 'r6', a: 1000 }, { id: 'r7', a: 11 }, { id: 'r8', a: 12 },
  ];
  it('IQR: tek aykırı, r6', async () => {
    const d = await kos(rows, 'anomaly_detection', { columns: 'a', method: 'iqr', threshold: 1.5 });
    expect(d.anomalies_detected).toBe(1);
    expect(d.sample_anomalies.map((s: any) => s.row.id)).toEqual(['r6']);
  });
  it('satır bazında birleşim: oran %100\'ü aşamaz', async () => {
    const iki = rows.map((r) => ({ ...r, b: r.a }));
    const d = await kos(iki, 'anomaly_detection', { columns: 'a,b', method: 'iqr', threshold: 1.5 });
    expect(d.anomalies_detected).toBe(1);
    expect(d.isaretli_hucre).toBe(2);
    expect(d.kolon_bazinda).toEqual({ a: 1, b: 1 });
  });
  it('isolation_forest istenirse uygulanan yöntem dürüstçe yazılır', async () => {
    const d = await kos(rows, 'anomaly_detection', { columns: 'a', method: 'isolation_forest' });
    expect(d.uygulanan_yontem).toBe('zscore');
    expect(d.uyarilar.join(' ')).toMatch(/tarayıcı motorunda yok/);
  });
});

describe('model doğrulama', () => {
  it('iki değeri de boş satır DOĞRU tahmin sayılmaz (eski: accuracy şişiyordu)', async () => {
    const rows = [
      { a: 'x', p: 'x' }, { a: 'y', p: 'x' }, { a: null, p: null }, { a: '', p: '' }, { a: 'y', p: 'y' },
    ];
    const d = await kos(rows, 'model_validation', { actualColumn: 'a', predictedColumn: 'p' });
    expect(d.accuracy).toBeCloseTo(2 / 3, 4); // eski: 4/5
    expect(d.total_samples).toBe(3);
    expect(d.n_dislanan).toBe(2);
  });
});

describe('çok değişkenli ve tekrarlanabilir', () => {
  const rows = Array.from({ length: 60 }, (_, i) => {
    const x1 = (i * 7) % 13;
    const x2 = (i * 5) % 11;
    return { x1, x2, y: 3 + 2 * x1 - 1.5 * x2 + ((i % 3) - 1) * 0.1 };
  });

  it('regresyon TÜM özellikleri kullanır (eski: yalnız ilki)', async () => {
    const d = await kos(rows, 'linear_regression', { target: 'y', features: 'x1,x2', testSize: 20 });
    expect(d.features).toEqual(['x1', 'x2']);
    expect(d.coefficients[0].coefficient).toBeCloseTo(2, 1);
    expect(d.coefficients[1].coefficient).toBeCloseTo(-1.5, 1);
    expect(d.r_squared).toBeGreaterThan(0.999);
    expect(d.holdout.test_n).toBe(12);
    expect(d.holdout.test_r_squared).toBeGreaterThan(0.99);
  });

  it('çapraz doğrulama tohumla tekrarlanabilir ve tüm özellikleri kullanır', async () => {
    const a = await kos(rows, 'cross_validation', { target: 'y', features: 'x1,x2', k: 5 });
    const b = await kos(rows, 'cross_validation', { target: 'y', features: 'x1,x2', k: 5 });
    expect(a.folds).toEqual(b.folds);
    expect(a.features).toEqual(['x1', 'x2']);
    expect(a.avg_r2).toBeGreaterThan(0.99);
    expect(a.folds.map((f: any) => f.testSize)).toEqual([12, 12, 12, 12, 12]);
  });

  it('K-Means tüm sütunları kullanır, ölçekler, tekrarlanabilir; merkez özgün birimde', async () => {
    const pts = [
      ...Array.from({ length: 10 }, (_, i) => ({ gelir: 20000 + i * 100, skor: 10 + (i % 3), yas: 20 + (i % 4) })),
      ...Array.from({ length: 10 }, (_, i) => ({ gelir: 90000 + i * 100, skor: 80 + (i % 3), yas: 60 + (i % 4) })),
    ];
    const a = await kos(pts, 'clustering', { features: 'gelir,skor,yas', k: 2 });
    const b = await kos(pts, 'clustering', { features: 'gelir,skor,yas', k: 2 });
    expect(a).toEqual(b);
    expect(a.features).toEqual(['gelir', 'skor', 'yas']);
    expect(a.standardize).toBe(true);
    expect(a.clusters.map((c: any) => c.size)).toEqual([10, 10]);
    const gelirler = a.clusters.map((c: any) => c.centroid[0]).sort((x: number, y: number) => x - y);
    expect(gelirler[0]).toBeCloseTo(20450, 0);
    expect(gelirler[1]).toBeCloseTo(90450, 0);
    expect(a.silhouette_score).toBeGreaterThan(0.9);
  });

  it('K-Means boş hücreyi 0 noktası yapmaz (eski: Number(v) || 0)', async () => {
    const pts = [
      ...Array.from({ length: 6 }, (_, i) => ({ a: 100 + i, b: 100 + i })),
      ...Array.from({ length: 6 }, (_, i) => ({ a: 200 + i, b: 200 + i })),
      { a: null, b: 150 },
    ];
    const d = await kos(pts, 'clustering', { features: 'a,b', k: 2 });
    expect(d.sample_size).toBe(12);
    expect(d.n_dislanan).toBe(1);
    expect(d.clusters.map((c: any) => c.size)).toEqual([6, 6]);
  });
});
