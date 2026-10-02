import { describe, it, expect } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import type { ExecutionResult } from '../src/engine/executionEngine';
import { calistirIsAkisi, varsayilanZamanAsimi } from '../src/engine/yurutucu';

const dugum = (id: string, type = 'filter', config: Record<string, unknown> = {}): Node<NodeData> =>
  ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { label: id.toUpperCase(), type, category: 'x', icon: 'x', color: '#000', config, status: 'idle' } }) as Node<NodeData>;
const kenar = (source: string, target: string): Edge => ({ id: `${source}-${target}`, source, target });
const basari = (id: string, extra: Record<string, unknown> = {}): ExecutionResult =>
  ({ status: 'success', nodeId: id, nodeType: 'x', timestamp: '', data: { id, ...extra }, rowCount: 0 });
const hata = (id: string, error = 'patladı'): ExecutionResult =>
  ({ status: 'error', nodeId: id, nodeType: 'x', timestamp: '', data: {}, error, rowCount: 0 });
const bekle = (ms: number, sinyal?: AbortSignal) => new Promise<void>((ok, red) => {
  const t = setTimeout(ok, ms);
  sinyal?.addEventListener('abort', () => { clearTimeout(t); red(sinyal.reason); }, { once: true });
});

/** Sahte yürütücü: süreleri ve davranışı düğüm başına ayarlanır; eşzamanlılığı ölçer. */
function sahte(ayar: Record<string, { ms?: number; hata?: boolean; sinyaliYoksay?: boolean; asiliKal?: boolean; abortIleti?: string; anlik?: boolean }>) {
  let aktif = 0;
  const olcum = { enCokAktif: 0, baslama: new Map<string, number>(), bitis: new Map<string, number>(), sinyaller: new Map<string, AbortSignal>() };
  const t0 = Date.now();
  const calistir = async (n: Node<NodeData>, _e: Edge[], sonuclar: Map<string, ExecutionResult>, b: { sinyal: AbortSignal }) => {
    const a = ayar[n.id] ?? {};
    olcum.baslama.set(n.id, Date.now() - t0);
    olcum.sinyaller.set(n.id, b.sinyal);
    aktif++; olcum.enCokAktif = Math.max(olcum.enCokAktif, aktif);
    try {
      if (a.asiliKal) await new Promise(() => {});
      // Anında biten yerel düğüm (dışa aktarma gibi): hiç beklemeden döner.
      if (a.anlik) return a.hata ? hata(n.id) : basari(n.id);
      try {
        await bekle(a.ms ?? 5, a.sinyaliYoksay ? undefined : b.sinyal);
      } catch (e) {
        // Gerçek yürütücüler AbortError'ı kendi iletisine çevirir.
        if (a.abortIleti) return hata(n.id, a.abortIleti);
        throw e;
      }
      if (a.hata) return hata(n.id);
      return basari(n.id, { gorulenGirdiler: [...sonuclar.keys()].sort() });
    } finally {
      aktif--; olcum.bitis.set(n.id, Date.now() - t0);
    }
  };
  return { calistir, olcum };
}

describe('calistirIsAkisi', () => {
  it('elmas: B ve C eşzamanlı, D ikisi bitmeden BAŞLAMAZ; tüm sonuçlar toplanır', async () => {
    const nodes = ['a', 'b', 'c', 'd'].map((i) => dugum(i));
    const edges = [kenar('a', 'b'), kenar('a', 'c'), kenar('b', 'd'), kenar('c', 'd')];
    const { calistir, olcum } = sahte({ b: { ms: 40 }, c: { ms: 40 } });
    const r = await calistirIsAkisi({ nodes, edges, calistir });
    expect(r.durum).toBe('tamamlandi');
    expect([...r.sonuclar.keys()].sort()).toEqual(['a', 'b', 'c', 'd']);
    expect(olcum.enCokAktif).toBeGreaterThanOrEqual(2);
    expect(olcum.baslama.get('d')!).toBeGreaterThanOrEqual(Math.max(olcum.bitis.get('b')!, olcum.bitis.get('c')!));
    // D çalışırken girdileri (B, C) zaten sonuçlardaydı.
    expect(r.sonuclar.get('d')!.data.gorulenGirdiler).toEqual(expect.arrayContaining(['b', 'c']));
    expect(r.baslamayanlar).toEqual([]);
  });

  it('eşzamanlılık sınırı aşılmaz', async () => {
    const nodes = ['a', 'b', 'c', 'd', 'e', 'f'].map((i) => dugum(i));
    const { calistir, olcum } = sahte(Object.fromEntries(nodes.map((n) => [n.id, { ms: 20 }])));
    const r = await calistirIsAkisi({ nodes, edges: [], calistir, eszamanlilik: 2 });
    expect(r.durum).toBe('tamamlandi');
    expect(olcum.enCokAktif).toBe(2);
  });

  it('ilk hata: uçuştaki ağ düğümü KESİLİR, bağımlılar başlamaz, durum "hata"', async () => {
    const nodes = ['a', 'b', 'c', 'd'].map((i) => dugum(i));
    const edges = [kenar('a', 'b'), kenar('a', 'c'), kenar('b', 'd')];
    const { calistir, olcum } = sahte({ b: { ms: 10, hata: true }, c: { ms: 5_000 } });
    const kesilen: string[] = [];
    const r = await calistirIsAkisi({ nodes, edges, calistir, olaylar: { kesildi: (id) => kesilen.push(id) } });
    expect(r.durum).toBe('hata');
    expect(r.hataDugumu).toBe('b');
    expect(r.kesilenler).toEqual(['c']);
    expect(kesilen).toEqual(['c']);
    expect(r.baslamayanlar).toEqual(['d']);
    expect(olcum.sinyaller.get('c')!.aborted).toBe(true);
    expect(r.sureMs).toBeLessThan(2_000); // C'nin 5 sn'sini beklemedi
  });

  it('aynı turda biri hata verse de ANINDA başarıyla biten düğüm başarılı sayılır (kesildi DEĞİL)', async () => {
    // Tarayıcıda yakalandı: demo'da Export CSV dosyayı indirmişken "Kesildi" raporlanıyordu.
    const nodes = [dugum('x'), dugum('y')];
    const { calistir } = sahte({ x: { anlik: true, hata: true }, y: { anlik: true } });
    const r = await calistirIsAkisi({ nodes, edges: [], calistir });
    expect(r.durum).toBe('hata');
    expect(r.hataDugumu).toBe('x');
    expect(r.sonuclar.has('y')).toBe(true);
    expect(r.kesilenler).toEqual([]);
  });

  it('kullanıcı iptali: uçuştaki kesilir, kalanlar başlamaz, durum "iptal" (hata değil)', async () => {
    const nodes = ['a', 'b', 'c'].map((i) => dugum(i));
    const edges = [kenar('a', 'b'), kenar('b', 'c')];
    const { calistir } = sahte({ b: { ms: 5_000 } });
    const k = new AbortController();
    const hatalar: string[] = [];
    const p = calistirIsAkisi({ nodes, edges, calistir, sinyal: k.signal, olaylar: { hata: (id) => hatalar.push(id) } });
    await bekle(30);
    k.abort();
    const r = await p;
    expect(r.durum).toBe('iptal');
    expect(r.sonuclar.has('a')).toBe(true);
    expect(r.kesilenler).toEqual(['b']);
    expect(r.baslamayanlar).toEqual(['c']);
    expect(hatalar).toEqual([]);
  });

  it('önceden iptal edilmiş sinyal: hiçbir düğüm başlamaz', async () => {
    const k = new AbortController();
    k.abort();
    const { calistir, olcum } = sahte({});
    const r = await calistirIsAkisi({ nodes: [dugum('a')], edges: [], calistir, sinyal: k.signal });
    expect(r.durum).toBe('iptal');
    expect(olcum.baslama.size).toBe(0);
  });

  it('iş bittikten SONRA basılan iptal koşuyu iptal saymaz', async () => {
    const k = new AbortController();
    const { calistir } = sahte({});
    const r = await calistirIsAkisi({ nodes: [dugum('a')], edges: [], calistir, sinyal: k.signal, olaylar: { bitti: () => k.abort() } });
    expect(r.durum).toBe('tamamlandi');
  });

  it('zaman aşımı: sinyali dinlemeyen ve hiç bitmeyen düğüm yarışla düşer → hata', async () => {
    const { calistir } = sahte({ a: { asiliKal: true } });
    const r = await calistirIsAkisi({ nodes: [dugum('a')], edges: [], calistir, zamanAsimiMs: () => 50 });
    expect(r.durum).toBe('hata');
    expect(r.hataDugumu).toBe('a');
  });

  it('zaman aşımı, yürütücünün kendi iletisine rağmen "zaman aşımı" diye raporlanır', async () => {
    const { calistir } = sahte({ a: { ms: 5_000, abortIleti: 'ML servisine ulaşılamadı' } });
    const hatalar: ExecutionResult[] = [];
    const r = await calistirIsAkisi({ nodes: [dugum('a', 'random_forest')], edges: [], calistir, zamanAsimiMs: () => 50, olaylar: { hata: (_, s) => hatalar.push(s) } });
    expect(r.durum).toBe('hata');
    expect(hatalar[0].error).toBe('A: zaman aşımı (0 sn)');
  });

  it('kanıt kaydı fail-fast ile KESİLMEZ: sinyali hiç düşmez, sonucu korunur', async () => {
    const nodes = [dugum('a'), dugum('k', 'evidence_export'), dugum('x')];
    const edges = [kenar('a', 'k'), kenar('a', 'x')];
    const { calistir, olcum } = sahte({ k: { ms: 80 }, x: { ms: 5, hata: true } });
    const r = await calistirIsAkisi({ nodes, edges, calistir });
    expect(r.durum).toBe('hata');
    expect(r.hataDugumu).toBe('x');
    expect(r.sonuclar.has('k')).toBe(true);
    expect(r.kesilenler).not.toContain('k');
    expect(olcum.sinyaller.get('k')!.aborted).toBe(false);
  });

  it('kanıt kaydı zaman aşımında sunucuda kayıt oluşmuş olabileceğini söyler', async () => {
    const { calistir } = sahte({ k: { asiliKal: true } });
    const hatalar: ExecutionResult[] = [];
    await calistirIsAkisi({ nodes: [dugum('k', 'evidence_export')], edges: [], calistir, zamanAsimiMs: () => 30, olaylar: { hata: (_, s) => hatalar.push(s) } });
    expect(hatalar[0].error).toContain('kayıt sunucuda yine de oluşmuş olabilir');
  });

  it('varsayılan zaman aşımları: ağ 5 dk, kanıt 1 dk, yerel 2 dk', () => {
    expect(varsayilanZamanAsimi('random_forest')).toBe(300_000);
    expect(varsayilanZamanAsimi('suc_frekans')).toBe(300_000);
    expect(varsayilanZamanAsimi('agent_insight')).toBe(300_000);
    expect(varsayilanZamanAsimi('evidence_export')).toBe(60_000);
    expect(varsayilanZamanAsimi('filter')).toBe(120_000);
  });

  it('GERÇEK motor: sıralı (1) ve paralel (4) koşu aynı sonuçları üretir', async () => {
    const satirlar = Array.from({ length: 40 }, (_, i) => ({ ilce: ['A', 'B', 'C'][i % 3], adet: i % 7, puan: (i * 13) % 11 }));
    const csv = dugum('csv', 'csv_source', { _uploadedData: { rows: satirlar, columns: ['ilce', 'adet', 'puan'], filename: 't.csv' } });
    const nodes = [
      csv,
      dugum('filtre', 'filter', { column: 'adet', condition: 'greater_than', value: '2' }),
      dugum('topla', 'aggregate', { groupBy: 'ilce', aggregations: ['COUNT', 'SUM'], valueColumn: 'adet' }),
      dugum('sirala', 'sort', { columns: 'puan', order: 'desc' }),
      dugum('ist', 'statistics', { columns: 'adet,puan' }),
    ];
    const edges = [kenar('csv', 'filtre'), kenar('filtre', 'topla'), kenar('csv', 'sirala'), kenar('csv', 'ist')];
    const temizle = (m: Map<string, ExecutionResult>) =>
      Object.fromEntries([...m].map(([k, v]) => [k, { ...v, timestamp: '' }]).sort(([a], [b]) => String(a).localeCompare(String(b))));
    const sirali = await calistirIsAkisi({ nodes, edges, eszamanlilik: 1 });
    const paralel = await calistirIsAkisi({ nodes, edges, eszamanlilik: 4 });
    expect(sirali.durum).toBe('tamamlandi');
    expect(paralel.durum).toBe('tamamlandi');
    expect(Object.keys(temizle(paralel.sonuclar))).toHaveLength(5);
    expect(temizle(paralel.sonuclar)).toEqual(temizle(sirali.sonuclar));
  });
});
