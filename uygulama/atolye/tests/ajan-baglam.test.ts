import { describe, it, expect, vi, afterEach } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import { executeNode, type ExecutionResult } from '../src/engine/executionEngine';
import { pyJsonUzunlugu, baglamiSigdir, AJAN_BAGLAM_BUTCESI } from '../src/engine/dugumler/ajan';

/**
 * YerelAjan bağlamı json.dumps(inputs, ensure_ascii=False)[:6000] ile JSON'un
 * ORTASINDAN keser (gui/server.py). DataFlow bağlamı bu bütçeye sığdırır ve
 * uyarılar/demo notunu her girdinin başına koyar.
 */

describe('pyJsonUzunlugu', () => {
  it('gerçek Python json.dumps(ensure_ascii=False) uzunluğuyla aynı (değerler Python ile ölçüldü)', () => {
    expect(pyJsonUzunlugu({ a: [1, 2], b: 'ç' })).toBe(23);
    expect(pyJsonUzunlugu({ x: null, y: true, z: [], w: {} })).toBe(40);
    expect(pyJsonUzunlugu([{ nodeType: 'statistics', rowCount: 3, data: { uyarilar: ['İ ğ ş " \\ \n'], rows: [{ a: 1.5, b: 'Ş' }, { a: -2, b: '' }] } }])).toBe(137);
    expect(pyJsonUzunlugu('düz metin')).toBe(11);
    expect(pyJsonUzunlugu(12345)).toBe(5);
    expect(pyJsonUzunlugu([[], [[]], { k: [1, { m: 'n' }] }])).toBe(34);
  });
});

describe('baglamiSigdir', () => {
  const genis = (n: number) => Array.from({ length: n }, (_, i) => Object.fromEntries(Array.from({ length: 12 }, (_, j) => [`sutun_${j}`, `değer ${i}-${j}`])));

  it('büyük bağlam bütçeye sığar; öncelikli alanlar başta ve eksiksiz', () => {
    const uyarilar = ['3 / 60 satır dışlandı.', 'Sunucuya yalnız İLK 5000 satır gönderildi.'];
    const inputs = [0, 1, 2].map((i) => ({
      nodeType: 'statistics', rowCount: 60,
      data: { stats: { ortalama: i }, rows: genis(60), uyarilar, veri_notu: 'SENTETİK DEMO VERİSİ' },
    }));
    expect(pyJsonUzunlugu(inputs)).toBeGreaterThan(AJAN_BAGLAM_BUTCESI);
    const { inputs: sigan, kirpildi } = baglamiSigdir(inputs);
    expect(kirpildi).toBe(true);
    expect(pyJsonUzunlugu(sigan)).toBeLessThanOrEqual(AJAN_BAGLAM_BUTCESI);
    for (const g of sigan) {
      expect(Object.keys(g.data!).slice(0, 2)).toEqual(['veri_notu', 'uyarilar']);
      expect(g.data!.uyarilar).toEqual(uyarilar);
      expect(g.data!.stats).toEqual(inputs[sigan.indexOf(g)].data.stats);
    }
  });

  it('küçük bağlama dokunulmaz (satırlar ve sıra korunur)', () => {
    const inputs = [{ nodeType: 'filter', rowCount: 2, data: { rows: genis(2), columns: ['a'] } }];
    const { inputs: sigan, kirpildi } = baglamiSigdir(inputs);
    expect(kirpildi).toBe(false);
    expect(sigan[0].data).toEqual(inputs[0].data);
  });
});

describe('ajan düğümü', () => {
  afterEach(() => vi.unstubAllGlobals());
  const d = (id: string, type: string, config: Record<string, unknown>): Node<NodeData> =>
    ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { label: id, type, category: 'x', icon: 'x', color: '#000', config, status: 'idle' } }) as Node<NodeData>;

  it('gönderilen bağlam Python ölçüsüyle ≤ 6000; kısaltıldıysa sonuç bunu söyler', async () => {
    const govdeler: Array<{ context: { inputs: unknown[] } }> = [];
    vi.stubGlobal('fetch', vi.fn(async (_u: string, init: RequestInit) => {
      govdeler.push(JSON.parse(String(init.body)));
      return new Response(JSON.stringify({ insight: 'yorum' }), { status: 200 });
    }));
    const satirlar = Array.from({ length: 300 }, (_, i) => Object.fromEntries(Array.from({ length: 15 }, (_, j) => [`s${j}`, `uzunca bir metin değeri ${i}-${j}`])));
    const s = new Map<string, ExecutionResult>();
    s.set('csv', await executeNode(d('csv', 'csv_source', { _uploadedData: { rows: satirlar, columns: Object.keys(satirlar[0]), filename: 'b.csv' } }), [], s));
    const r = await executeNode(d('aj', 'agent_insight', { question: 'Yorumla' }), [{ id: 'e', source: 'csv', target: 'aj' } as Edge], s);
    expect(r.status).toBe('success');
    expect(pyJsonUzunlugu(govdeler[0].context.inputs)).toBeLessThanOrEqual(AJAN_BAGLAM_BUTCESI);
    expect(String((r.data.uyarilar as string[])[0])).toContain('kısaltıldı');
  });
});
