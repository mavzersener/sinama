import { describe, it, expect, vi, afterEach } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import { executeNode, demoKaynagiMi, demoMu, type ExecutionResult } from '../src/engine/executionEngine';
import { csvHucresi } from '../src/engine/dugumler/cikti';

/**
 * Demo işareti: sentetik veriden türeyen HER sonuç işaretlenir. Eskiden
 * işaret yalnız kaynağın kendi sonucundaydı — demo verinin istatistiği,
 * kümelemesi, dışa aktarılan dosyası ve ajan yorumu gerçek bulgu gibi
 * görünüyordu; araç çubuğundaki "Demo Mode" ise hep true bir bayraktı.
 */

const d = (id: string, type: string, config: Record<string, unknown> = {}): Node<NodeData> =>
  ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { label: id, type, category: 'x', icon: 'x', color: '#000', config, status: 'idle' } }) as Node<NodeData>;
const k = (s: string, t: string): Edge => ({ id: `${s}>${t}`, source: s, target: t });
const gercek = (id = 'csv') => d(id, 'csv_source', { _uploadedData: { rows: [{ a: 1, b: 'x' }, { a: 2, b: 'y' }, { a: 3, b: 'x' }], columns: ['a', 'b'], filename: 'g.csv' } });

async function kos(nodes: Node<NodeData>[], edges: Edge[]) {
  const s = new Map<string, ExecutionResult>();
  for (const n of nodes) {
    const r = await executeNode(n, edges, s);
    if (r.status !== 'success') throw new Error(`${n.id}: ${r.error}`);
    s.set(n.id, r);
  }
  return s;
}
afterEach(() => vi.unstubAllGlobals());

describe('demo işareti yayılımı', () => {
  it('demo kaynaktan türeyen her sonuç demo; özet düğümünden (akış kanalı) de geçer', async () => {
    const s = await kos(
      [d('csv', 'csv_source', { filename: 'yok.csv' }), d('dq', 'data_quality'), d('ist', 'statistics', { columns: 'income' }), d('sr', 'sort', { columns: 'age' })],
      [k('csv', 'dq'), k('dq', 'ist'), k('ist', 'sr')],
    );
    expect(['csv', 'dq', 'ist', 'sr'].map((id) => demoMu(s.get(id)))).toEqual([true, true, true, true]);
  });

  it('gerçek veride hiçbir sonuç demo değil', async () => {
    const s = await kos([gercek(), d('ist', 'statistics', { columns: 'a' }), d('sr', 'sort', { columns: 'a' })], [k('csv', 'ist'), k('ist', 'sr')]);
    expect([...s.values()].some(demoMu)).toBe(false);
    expect([...s.values()].some((r) => 'demo' in r)).toBe(false);
  });

  it('join: girdilerden biri demo ise sonuç demo', async () => {
    const s = await kos(
      [gercek('sol'), d('sag', 'db_source', {}), d('j', 'join', { leftKey: 'a', rightKey: 'id', joinType: 'left' })],
      [k('sol', 'j'), k('sag', 'j')],
    );
    expect(demoMu(s.get('sol'))).toBe(false);
    expect(demoMu(s.get('j'))).toBe(true);
  });

  it('demoKaynagiMi: DB/API/kolluk her zaman, CSV yalnız dosyasızken', () => {
    for (const t of ['db_source', 'api_source', 'pts_source', 'anpr_source', 'mobese_source', 'ihbar_source', 'adli_sicil_source']) {
      expect(demoKaynagiMi(t, {})).toBe(true);
    }
    expect(demoKaynagiMi('csv_source', {})).toBe(true);
    expect(demoKaynagiMi('csv_source', { _veriKaynagi: { anahtar: 'x' } })).toBe(false);
    expect(demoKaynagiMi('csv_source', { _uploadedData: { rows: [] } })).toBe(false);
    expect(demoKaynagiMi('filter', {})).toBe(false);
  });
});

describe('çıktılar', () => {
  it('dışa aktarma: demo dosya adı _DEMO ile biter, gerçekte bitmez', async () => {
    const demo = await kos([d('csv', 'csv_source'), d('ex', 'export', { format: 'csv', filename: 'rapor' })], [k('csv', 'ex')]);
    expect(demo.get('ex')!.data.filename).toBe('rapor_DEMO');
    const gercekS = await kos([gercek(), d('ex', 'export', { format: 'csv', filename: 'rapor' })], [k('csv', 'ex')]);
    expect(gercekS.get('ex')!.data.filename).toBe('rapor');
    expect(gercekS.get('ex')!.data.icerik).toBe('a,b\n1,x\n2,y\n3,x');
  });

  it('grafik başlığı demo veride işaretlenir', async () => {
    const s = await kos([d('csv', 'csv_source'), d('g', 'chart', { chartType: 'bar', title: 'Gelir' })], [k('csv', 'g')]);
    expect(s.get('g')!.data.title).toBe('Gelir (DEMO VERİ)');
  });

  it('CSV hücresi: tırnak içeren değer kaçışlanır (eskiden sütun kayıyordu)', () => {
    expect(csvHucresi('Ali "Deli" Veli')).toBe('"Ali ""Deli"" Veli"');
    expect(csvHucresi('a,b')).toBe('"a,b"');
    expect(csvHucresi('satır\nsonu')).toBe('"satır\nsonu"');
    expect(csvHucresi(null)).toBe('');
    expect(csvHucresi(3.5)).toBe('3.5');
  });

  it('CSV hücresi: formül olarak çalışabilecek METİN nötrlenir, sayılar değişmez', () => {
    expect(csvHucresi('=HYPERLINK("http://x","tıkla")')).toBe('"\'=HYPERLINK(""http://x"",""tıkla"")"');
    expect(csvHucresi('@SUM(A1)')).toBe("'@SUM(A1)");
    expect(csvHucresi('+90 555 111 22 33')).toBe("'+90 555 111 22 33");  // bekci:izin — sentetik telefon biçimi (CSV formül nötrleme testi)
    expect(csvHucresi('-5')).toBe('-5');
    expect(csvHucresi('-3,5')).toBe('"-3,5"');
    expect(csvHucresi(-5)).toBe('-5');
    expect(csvHucresi('normal metin')).toBe('normal metin');
  });

  it('ajan: demo girdide not hem soruda hem veride; gerçek girdide istek değişmez', async () => {
    const govdeler: Record<string, unknown>[] = [];
    vi.stubGlobal('fetch', vi.fn(async (_u: string, init: RequestInit) => {
      govdeler.push(JSON.parse(String(init.body)));
      return new Response(JSON.stringify({ insight: 'ok' }), { status: 200 });
    }));
    await kos([d('csv', 'csv_source'), d('ist', 'statistics', { columns: 'income' }), d('aj', 'agent_insight', { question: 'Yorumla' })], [k('csv', 'ist'), k('ist', 'aj')]);
    await kos([gercek(), d('ist', 'statistics', { columns: 'a' }), d('aj', 'agent_insight', { question: 'Yorumla' })], [k('csv', 'ist'), k('ist', 'aj')]);
    const [demo, gercekG] = govdeler as Array<{ question: string; context: { inputs: Array<{ data: Record<string, unknown> }> } }>;
    expect(demo.question).toMatch(/^\[SENTETİK DEMO VERİSİ: .*\] Yorumla$/);
    expect(demo.context.inputs[0].data.veri_notu).toMatch(/^SENTETİK DEMO VERİSİ/);
    expect(gercekG.question).toBe('Yorumla');
    expect(gercekG.context.inputs[0].data).not.toHaveProperty('veri_notu');
  });
});
