import { describe, it, expect } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import { executeNode, akisVerisi, type ExecutionResult } from '../src/engine/executionEngine';

/**
 * Veri akışı sözleşmesi: her düğümün ardındakilere akan tablo (akisVerisi)
 * satır taşır ve `columns` sütun ADLARIDIR.
 *
 * Bulgu (24 Eyl): 11 analiz düğümü yalnız özet üretiyor, satır geçirmiyordu —
 * ardındaki her düğüm boş veri görüyordu (demo: Veri Kalitesi → Anomali "No
 * numeric columns", K-Means → Export 0 satır; Hedeften Akış'ın csv →
 * data_quality → suc_… → agent → evidence zinciri ikinci adımda kuruyordu).
 * Veri Kalitesi ayrıca `data.columns`a profil nesneleri koyuyordu.
 */

const satirlar = Array.from({ length: 60 }, (_, i) => ({
  ilce: ['Merkez', 'Kuzey', 'Güney'][i % 3],
  yas: 18 + (i * 7) % 50,
  gelir: 1000 + ((i * 131) % 900),
  puan: (i * 13) % 11,
  tarih: `2026-0${1 + (i % 9)}-1${i % 9} 1${i % 9}:00:00`,
  kisi: `K${i % 8}`,
  arac: `A${i % 5}`,
  sinif: i % 2 ? 'A' : 'B',
}));
const kolonlar = Object.keys(satirlar[0]);

const d = (id: string, type: string, config: Record<string, unknown> = {}): Node<NodeData> =>
  ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { label: id, type, category: 'x', icon: 'x', color: '#000', config, status: 'idle' } }) as Node<NodeData>;
const k = (source: string, target: string): Edge => ({ id: `${source}>${target}`, source, target });

/** Düğümleri verilen sırayla koşturur (her biri girdileri bittikten sonra). */
async function kos(nodes: Node<NodeData>[], edges: Edge[]) {
  const sonuclar = new Map<string, ExecutionResult>();
  for (const n of nodes) {
    const r = await executeNode(n, edges, sonuclar);
    if (r.status !== 'success') throw new Error(`${n.id} (${n.data.type}): ${r.error}`);
    sonuclar.set(n.id, r);
  }
  return sonuclar;
}
const csv = () => d('csv', 'csv_source', { _uploadedData: { rows: satirlar, columns: kolonlar, filename: 't.csv' } });

// Özet üreten analiz düğümleri (satır üretmez → girdi tablosu aynen akar).
const OZET: Record<string, Record<string, unknown>> = {
  statistics: { columns: 'yas,gelir' },
  correlation: { columns: 'yas,gelir,puan', method: 'pearson' },
  clustering: { features: 'yas,gelir', k: 3 },
  anomaly_detection: { columns: 'gelir', method: 'iqr', threshold: 1.5 },
  data_quality: { columns: '' },
  linear_regression: { target: 'gelir', features: 'yas,puan' },
  cross_validation: { target: 'gelir', features: 'yas,puan', folds: 3 },
  model_validation: { actualColumn: 'sinif', predictedColumn: 'sinif' },
  temporal_pattern: { timeColumn: 'tarih', granularity: 'hour' },
  cooccurrence: { entityColumn: 'kisi', contextColumn: 'arac' },
  chart: { chartType: 'bar', title: 't' },
  alert: { condition: 'count_greater_than', threshold: 10, channel: 'email' },
};
// Kendi tablosunu üreten dönüştürücüler.
const DONUSTURUCU: Record<string, Record<string, unknown>> = {
  filter: { column: 'gelir', condition: 'greater_than', value: '1300' },
  aggregate: { groupBy: 'ilce', aggregations: ['COUNT', 'SUM'], valueColumn: 'gelir' },
  sort: { columns: 'gelir', order: 'desc' },
  dedup: { keyColumns: 'ilce' },
  data_clean: { strategy: 'drop' },
  extend_field: { newColumn: 'cift', expression: 'gelir * 2' },
};

describe('akış sözleşmesi', () => {
  it.each(Object.entries(OZET))('özet düğümü %s: ardına girdi tablosunu AYNEN geçirir, özeti kendinde kalır', async (tip, config) => {
    const s = await kos([csv(), d('x', tip, config)], [k('csv', 'x')]);
    const akan = akisVerisi(s.get('x'))!;
    expect(akan.rows).toBe(satirlar); // başvuru: kopya yok
    expect(akan.columns).toEqual(kolonlar);
    expect(Object.keys(s.get('x')!.data).length).toBeGreaterThan(0);
  });

  it.each(Object.entries(DONUSTURUCU))('dönüştürücü %s: kendi tablosunu üretir, columns sütun ADLARI', async (tip, config) => {
    const s = await kos([csv(), d('x', tip, config)], [k('csv', 'x')]);
    const akan = akisVerisi(s.get('x'))!;
    expect(Array.isArray(akan.rows)).toBe(true);
    expect((akan.columns as unknown[]).every((c) => typeof c === 'string')).toBe(true);
    expect(s.get('x')!.akis).toBeUndefined(); // kendi satırı varken akış kanalı gerekmez
  });

  it('Veri Kalitesi: panel için profil nesneleri data.columns\'ta kalır, akan tablo ise sütun ADLARI taşır', async () => {
    const s = await kos([csv(), d('dq', 'data_quality', { columns: '' })], [k('csv', 'dq')]);
    expect(typeof (s.get('dq')!.data.columns as unknown[])[0]).toBe('object');
    expect(akisVerisi(s.get('dq'))!.columns).toEqual(kolonlar);
  });

  it('demo zinciri: Veri Kalitesi → Anomali → Sıralama; Kümeleme → Sıralama (eskiden "No numeric columns" / 0 satır)', async () => {
    const s = await kos(
      [csv(), d('dq', 'data_quality'), d('an', 'anomaly_detection', { columns: 'gelir', method: 'iqr', threshold: 1.5 }),
        d('sr', 'sort', { columns: 'gelir', order: 'asc' }), d('km', 'clustering', { features: 'yas,gelir', k: 3 }),
        d('sr2', 'sort', { columns: 'yas', order: 'asc' })],
      [k('csv', 'dq'), k('dq', 'an'), k('an', 'sr'), k('csv', 'km'), k('km', 'sr2')],
    );
    expect(s.get('an')!.data.total_rows).toBe(60);
    expect((akisVerisi(s.get('sr'))!.rows as unknown[]).length).toBe(60);
    expect((akisVerisi(s.get('sr2'))!.rows as unknown[]).length).toBe(60);
  });

  it('join: özet düğümünün ardındaki tabloyu da birleştirir', async () => {
    const sag = d('sag', 'csv_source', { _uploadedData: { rows: [{ ilce: 'Merkez', nufus: 10 }], columns: ['ilce', 'nufus'], filename: 's.csv' } });
    const s = await kos(
      [csv(), d('ist', 'statistics', { columns: 'yas' }), sag, d('j', 'join', { leftKey: 'ilce', rightKey: 'ilce', joinType: 'inner' })],
      [k('csv', 'ist'), k('ist', 'j'), k('sag', 'j')],
    );
    const rows = akisVerisi(s.get('j'))!.rows as Record<string, unknown>[];
    expect(rows.length).toBe(20); // 60 satırın Merkez olanları
    expect(rows[0].nufus).toBe(10);
  });

  it('kanıt paketi analiz zincirinin sonunda veriyi görür (Hedeften Akış: … → istatistik → kanıt)', async () => {
    const s = await kos(
      [csv(), d('ist', 'statistics', { columns: 'yas' }), d('kn', 'evidence_export', { caseNumber: '2026/1', officerId: 'PN-1' })],
      [k('csv', 'ist'), k('ist', 'kn')],
    );
    // Sunucu yok (node): KAYITSIZ ama paket TÜM satırlardan üretilir — eskiden "satır yok" hatası.
    expect(s.get('kn')!.data.satir).toBe(60);
    expect(s.get('kn')!.data.durum).toBe('KAYITSIZ');
  });
});

describe('filtre sağlamlığı', () => {
  const tek = async (config: Record<string, unknown>, rows: Record<string, unknown>[]) => {
    const kaynak = d('csv', 'csv_source', { _uploadedData: { rows, columns: Object.keys(rows[0]), filename: 'f.csv' } });
    const sonuclar = new Map<string, ExecutionResult>();
    sonuclar.set('csv', await executeNode(kaynak, [], sonuclar));
    return executeNode(d('f', 'filter', config), [k('csv', 'f')], sonuclar);
  };

  it('bilinmeyen koşul HATA verir (eskiden tüm satırları sessizce geçiriyordu)', async () => {
    const r = await tek({ column: 'a', condition: 'buyuktur', value: '1' }, [{ a: 1 }, { a: 2 }]);
    expect(r.status).toBe('error');
    expect(r.error).toContain('Bilinmeyen filtre koşulu');
  });

  it('ondalık virgül motorun tek sayı çözücüsüyle okunur (eskiden Number("37,58") = NaN → satır sessizce düşüyordu)', async () => {
    // sayiCoz kuralı (Faz 1): yalnız ondalık virgül; "1.234,5" gibi binlik
    // ayraçlı biçimler belirsiz sayılır ve çözülmez — filtre de aynı kuralı izler.
    const r = await tek({ column: 'oran', condition: 'greater_than', value: '30,5' },
      [{ oran: '37,58' }, { oran: '12,5' }, { oran: '30,6' }, { oran: 'yok' }]);
    expect(r.status).toBe('success');
    expect((r.data.rows as Record<string, unknown>[]).map((x) => x.oran)).toEqual(['37,58', '30,6']);
  });
});

describe('uyarı düğümü (Python dışa aktarımıyla aynı kural)', () => {
  const uyar = async (config: Record<string, unknown>) => {
    const sonuclar = new Map<string, ExecutionResult>();
    sonuclar.set('csv', await executeNode(csv(), [], sonuclar));
    return executeNode(d('u', 'alert', config), [k('csv', 'u')], sonuclar);
  };

  it('value_greater_than DEĞERİ karşılaştırır (eskiden satır sayısını karşılaştırıyordu)', async () => {
    // En büyük sayısal değer (gelir sütunundan gelir); satır sayısı 60.
    const enBuyuk = Math.max(...satirlar.map((r) => Math.max(r.yas, r.gelir, r.puan)));
    const altinda = await uyar({ condition: 'value_greater_than', threshold: enBuyuk });
    const ustunde = await uyar({ condition: 'value_greater_than', threshold: enBuyuk - 1 });
    expect(altinda.data).toMatchObject({ triggered: false, olculen: enBuyuk });
    expect(ustunde.data).toMatchObject({ triggered: true, olculen: enBuyuk });
    // Eski davranış: 60 satır > 100 → false olurdu; değer koşulu 1899 > 100 → true.
    expect((await uyar({ condition: 'value_greater_than', threshold: 100 })).data.triggered).toBe(true);
  });

  it('value_less_than en küçük değere bakar; count_* satır sayısına', async () => {
    expect((await uyar({ condition: 'value_less_than', threshold: 1 })).data).toMatchObject({ triggered: true, olculen: 0 });
    expect((await uyar({ condition: 'count_less_than', threshold: 61 })).data).toMatchObject({ triggered: true, olculen: 60 });
  });

  it('koşul yoksa ya da bilinmiyorsa açık hata (eskiden TypeError / sessiz sayım)', async () => {
    expect((await uyar({})).error).toContain('Bilinmeyen uyarı koşulu');
    expect((await uyar({ condition: 'mean_above' })).error).toContain('Bilinmeyen uyarı koşulu: "mean_above"');
  });
});
