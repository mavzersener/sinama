import { describe, it, expect } from 'vitest';
import type { Edge } from '@xyflow/react';
import { executeNode, getPrebuiltModels, type ExecutionResult } from '../src/engine/executionEngine';

/**
 * "Birleştirilmiş hücre" ihracı üzerinde doğru analiz.
 *
 * Gerçek bir otodan-hırsızlık şüpheli/mağdur ihracında (1107 satır / 579 olay)
 * yakalanan üç hata:
 *
 * 1. `extend_field` metin sütunlarıyla SESSİZCE boş sütun üretiyordu
 *    (status=success, değer=""). Sayısal olmayan sütun ifadeye giremiyordu.
 * 2. `geo_hotspot` koordinatı BOŞ satırları eliyordu sanılıyordu; oysa yalnız
 *    `undefined` kontrol ediliyordu. Number(null)===0 olduğu için koordinatsız
 *    82 olay 0,0'a düşüp "1 numaralı sıcak nokta" olarak raporlanıyordu.
 * 3. Olay kimliği sütunlarda değil SATIR SIRASINDA saklı. Sütun birleştirerek
 *    (tarih+yer) kimlik üretmek gerçek veride 411 birliktelik verdi; doğrusu
 *    370'ti ve 2+ olayda birlikte olan 56 çiftin TAMAMI kaçırılmıştı.
 */

type ExecArgs = Parameters<typeof executeNode>;

function d(id: string, type: string, config: Record<string, unknown>): ExecArgs[0] {
  return { id, type: 'custom', position: { x: 0, y: 0 }, data: { label: id, type, category: 'T', icon: 'B', color: '#fff', config, status: 'idle' } } as unknown as ExecArgs[0];
}
const e = (s: string, t: string): Edge => ({ id: `${s}->${t}`, source: s, target: t });

/**
 * Gerçek ihracın şeklini taklit eden fixture (gerçek veri KVKK nedeniyle
 * depoya konmaz): 4 olay, 8 şüpheli kaydı. 3. olayın koordinatı YOK.
 */
function blokluVeri() {
  const columns = ['tarih', 'yer', 'suc', 'enlem', 'boylam', 'Skodu'];
  const rows: Record<string, unknown>[] = [
    // Olay 1 — iki şüpheli
    { tarih: '2023-01-05', yer: 'ALATAŞ', suc: 'OTODAN HIRSIZLIK', enlem: 36.1, boylam: 32.7, Skodu: 'S1' },
    { tarih: null, yer: null, suc: null, enlem: null, boylam: null, Skodu: 'S2' },
    // Olay 2 — iki şüpheli (S1 ve S2 TEKRAR birlikte)
    { tarih: '2023-02-11', yer: 'BOZDOĞAN', suc: 'OTODAN HIRSIZLIK', enlem: 36.2, boylam: 32.8, Skodu: 'S1' },
    { tarih: null, yer: null, suc: null, enlem: null, boylam: null, Skodu: 'S2' },
    // Olay 3 — KOORDİNATSIZ, tek şüpheli
    { tarih: '2023-03-02', yer: 'MIZRAKLI', suc: 'OTODAN HIRSIZLIK', enlem: null, boylam: null, Skodu: 'S3' },
    { tarih: null, yer: null, suc: null, enlem: null, boylam: null, Skodu: 'S4' },
    // Olay 4 — tek şüpheli
    { tarih: '2023-04-19', yer: 'TEKELİ', suc: 'OTODAN HIRSIZLIK', enlem: 36.3, boylam: 32.9, Skodu: 'S5' },
    { tarih: null, yer: null, suc: null, enlem: null, boylam: null, Skodu: 'S1' },
  ];
  return { columns, rows };
}

function kaynak(): ExecArgs[0] {
  const { columns, rows } = blokluVeri();
  return d('csv', 'csv_source', { filename: 'f.csv', _uploadedData: { rows, columns, filename: 'f.csv' } });
}

async function kos(nodes: ExecArgs[0][], edges: Edge[]) {
  const m = new Map<string, ExecutionResult>();
  for (const n of nodes) m.set(n.id, await executeNode(n, edges, m));
  return m;
}

describe('block_group — blok kimliği ve blok-içi doldurma', () => {
  it('kimliği satır sırasından üretir, sınırı aşmaz', async () => {
    const nodes = [kaynak(), d('blok', 'block_group', { markerColumn: 'suc', idColumn: 'olay_id', fillColumns: 'tarih, yer, enlem, boylam' })];
    const m = await kos(nodes, [e('csv', 'blok')]);
    const out = m.get('blok')!;
    const veri = out.data as Record<string, unknown>;

    expect(out.status).toBe('success');
    expect(veri.block_count).toBe(4);
    expect(veri.rows_total).toBe(8);
    expect(veri.rows_before_first_block).toBe(0);

    const rows = veri.rows as Record<string, unknown>[];
    expect(rows.map((r) => r.olay_id)).toEqual(
      ['B000001', 'B000001', 'B000002', 'B000002', 'B000003', 'B000003', 'B000004', 'B000004'],
    );
  });

  it('KOORDİNATSIZ olaya ÖNCEKİ olayın koordinatını taşımaz', async () => {
    const nodes = [kaynak(), d('blok', 'block_group', { markerColumn: 'suc', idColumn: 'olay_id', fillColumns: 'tarih, yer, enlem, boylam' })];
    const m = await kos(nodes, [e('csv', 'blok')]);
    const rows = (m.get('blok')!.data as Record<string, unknown>).rows as Record<string, unknown>[];

    // Olay 3 (satır 4-5) koordinatsız; data_clean'in ffill'i burada olay 2'nin
    // koordinatını taşırdı — blok sınırı bunu engeller.
    expect(rows[4].enlem).toBeNull();
    expect(rows[5].enlem).toBeNull();
    // Ama blok İÇİNDE doldurma çalışır:
    expect(rows[5].tarih).toBe('2023-03-02');
    expect(rows[1].enlem).toBe(36.1);
  });

  it('eksik/yanlış sütun sessizce geçmez', async () => {
    const m1 = await kos([kaynak(), d('b', 'block_group', { markerColumn: '', idColumn: 'x' })], [e('csv', 'b')]);
    expect(m1.get('b')!.status).toBe('error');
    const m2 = await kos([kaynak(), d('b', 'block_group', { markerColumn: 'olmayan', idColumn: 'x' })], [e('csv', 'b')]);
    expect(m2.get('b')!.status).toBe('error');
    expect(m2.get('b')!.error).toMatch(/olmayan/);
  });
});

describe('extend_field — metin ifadeleri', () => {
  it('metin sütunlarını birleştirir (eskiden sessizce boş dönerdi)', async () => {
    const nodes = [kaynak(), d('ext', 'extend_field', { newColumn: 'anahtar', expression: 'tarih + "_" + yer' })];
    const m = await kos(nodes, [e('csv', 'ext')]);
    const rows = (m.get('ext')!.data as Record<string, unknown>).rows as Record<string, unknown>[];
    expect(rows[0].anahtar).toBe('2023-01-05_ALATAŞ');
    expect(rows[0].anahtar).not.toBe('');
  });

  it('sayısal ifadeler bozulmadı', async () => {
    const nodes = [kaynak(), d('ext', 'extend_field', { newColumn: 'iki', expression: 'enlem * 2' })];
    const m = await kos(nodes, [e('csv', 'ext')]);
    const rows = (m.get('ext')!.data as Record<string, unknown>).rows as Record<string, unknown>[];
    expect(rows[0].iki).toBeCloseTo(72.2, 4);
  });

  it('geçersiz ifade SESSİZ boş sütun değil, HATA döner', async () => {
    const nodes = [kaynak(), d('ext', 'extend_field', { newColumn: 'x', expression: 'boyleBirSutunYok + 1' })];
    const m = await kos(nodes, [e('csv', 'ext')]);
    expect(m.get('ext')!.status).toBe('error');
    expect(m.get('ext')!.error).toMatch(/boyleBirSutunYok|not defined/);
  });
});

describe('geo_hotspot — boş koordinat', () => {
  it('boş koordinatı 0,0 sıcak noktası yapmaz', async () => {
    const nodes = [
      kaynak(),
      d('blok', 'block_group', { markerColumn: 'suc', idColumn: 'olay_id', fillColumns: 'tarih, yer, enlem, boylam' }),
      d('olay', 'dedup', { keyColumns: 'olay_id', keep: 'first' }),
      d('geo', 'geo_hotspot', { latColumn: 'enlem', lngColumn: 'boylam', weightColumn: '', gridSize: 0.05 }),
    ];
    const m = await kos(nodes, [e('csv', 'blok'), e('blok', 'olay'), e('olay', 'geo')]);
    const veri = m.get('geo')!.data as Record<string, unknown>;

    // 4 olayın 3'ünde koordinat var.
    expect(veri.total_points).toBe(3);
    expect(veri.dropped_invalid_coords).toBe(1);
    const hucreler = (veri.top_hotspots as { cell: string }[]).map((h) => h.cell);
    expect(hucreler).not.toContain('0.0000,0.0000');
  });

  it('ağırlığı 0 olan satırı 1 saymaz', async () => {
    // Aynı grid hücresine düşen FARKLI koordinatlar: ön-kontrol "tüm olaylar
    // aynı noktada" uyarısını haklı olarak verir, o yüzden değerler ayrışık.
    const columns = ['lat', 'lng', 'w'];
    const rows = [
      { lat: 10.1, lng: 10.1, w: 0 },
      { lat: 10.2, lng: 10.2, w: 5 },
      { lat: 20.5, lng: 20.5, w: 1 },
    ];
    const nodes = [
      d('csv', 'csv_source', { filename: 'f.csv', _uploadedData: { rows, columns, filename: 'f.csv' } }),
      d('geo', 'geo_hotspot', { latColumn: 'lat', lngColumn: 'lng', weightColumn: 'w', gridSize: 1 }),
    ];
    const m = await kos(nodes, [e('csv', 'geo')]);
    const geo = m.get('geo')!;
    expect(geo.status, geo.error).toBe('success');
    const hucreler = (geo.data as Record<string, unknown>).top_hotspots as { cell: string; count: number; weight: number }[];
    const ortak = hucreler.find((h) => h.count === 2)!;
    expect(ortak.weight).toBe(5); // 0+5, eskiden 1+5=6 olurdu
  });
});

describe('hazır akış', () => {
  it('Otodan Hırsızlık modeli katalogda ve blok onarımıyla başlıyor', () => {
    const model = getPrebuiltModels().find((x) => x.id === 'model-otodan-hirsizlik');
    expect(model).toBeDefined();
    const tipler = model!.nodes.map((n) => n.data.type);
    expect(tipler).toContain('block_group');
    // Olay düzeyi analizleri tekilleştirmeden SONRA gelmeli.
    const blok = model!.nodes.find((n) => n.data.type === 'block_group')!;
    const olay = model!.nodes.find((n) => n.data.type === 'dedup')!;
    const geo = model!.nodes.find((n) => n.data.type === 'geo_hotspot')!;
    expect(model!.edges).toContainEqual(expect.objectContaining({ source: blok.id, target: olay.id }));
    expect(model!.edges).toContainEqual(expect.objectContaining({ source: olay.id, target: geo.id }));
  });
});
