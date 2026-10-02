import { describe, it, expect, vi, beforeEach, afterAll } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import type { ExecutionResult } from '../src/engine/executionEngine';
import { kaliciDugumler, yuklenenAkis, sonuclariAktar } from '../src/lib/kalicilik';
import { veriAl, depoyuTemizle } from '../src/lib/veriDeposu';

// Durum deposu localStorage'ı modül yüklenirken okur: bellek içi sahte önce kurulur.
const bellek = vi.hoisted(() => {
  const m = new Map<string, string>();
  const ls = {
    dolu: false,
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => { if (ls.dolu) throw new DOMException('quota', 'QuotaExceededError'); m.set(k, v); },
    removeItem: (k: string) => { m.delete(k); },
    clear: () => m.clear(),
  };
  (globalThis as Record<string, unknown>).localStorage = ls;
  return ls;
});
import { useStore } from '../src/store/useStore';

afterAll(() => { delete (globalThis as Record<string, unknown>).localStorage; });

const sonuc = (id: string): ExecutionResult =>
  ({ status: 'success', nodeId: id, nodeType: 'x', timestamp: '', data: { rows: [{ gizli: 1 }] }, rowCount: 1 });
const dugum = (id: string, type = 'filter', config: Record<string, unknown> = {}, result?: ExecutionResult): Node<NodeData> =>
  ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { label: id, type, category: 'x', icon: 'x', color: '#000', config, status: result ? 'completed' : 'idle', ...(result ? { result } : {}) } }) as Node<NodeData>;
const k = (source: string, target: string): Edge => ({ id: `${source}>${target}`, source, target });
const eskiSatirlar = Array.from({ length: 300 }, (_, i) => ({ a: i }));

beforeEach(() => { depoyuTemizle(); bellek.clear(); bellek.dolu = false; });

describe('kaliciDugumler (yazma)', () => {
  it('sonuç ve durum yazılmaz; eski satır-içi veri depoya taşınır', () => {
    const n = dugum('csv', 'csv_source', { hasHeader: true, _uploadedData: { rows: eskiSatirlar, columns: ['a'], filename: 'e.csv' } }, sonuc('csv'));
    const [y] = kaliciDugumler([n]);
    expect(y.data.result).toBeUndefined();
    expect(y.data.status).toBe('idle');
    expect(y.data.config._uploadedData).toBeUndefined();
    expect(y.data.config._veriKaynagi).toMatchObject({ anahtar: 'yerel:csv', rowCount: 300, filename: 'e.csv' });
    expect(veriAl('yerel:csv')!.rows).toBe(eskiSatirlar);
    expect(JSON.stringify(y).length).toBeLessThan(2_000);
    // Canlı düğüm değişmedi (sonuç ekranda kalır).
    expect(n.data.result).toBeDefined();
  });
});

describe('yuklenenAkis (yükleme)', () => {
  it('bozuk kayıt onarılır: config null → {}, kimliksiz/türsüz düğüm ve sahipsiz kenar atlanır', () => {
    const { nodes, edges, atlanan } = yuklenenAkis(
      [
        { id: 'a', data: { type: 'csv_source', config: null } },
        { id: 'b', data: { type: 'filter', label: 'F', config: { column: 'x' }, result: sonuc('b'), status: 'completed' }, position: { x: 5, y: 6 } },
        { data: { type: 'sort' } },
        { id: 'c', data: 'bozuk' },
        null,
      ],
      [k('a', 'b'), k('a', 'yok'), { id: 'z' }],
    );
    expect(nodes.map((n) => n.id)).toEqual(['a', 'b']);
    expect(nodes[0].data.config).toEqual({});
    expect(nodes[0].data.label).toBe('csv_source');
    expect(nodes[0].position).toEqual({ x: 0, y: 0 });
    expect(nodes[1].data.result).toBeUndefined();
    expect(nodes[1].data.status).toBe('idle');
    expect(edges.map((e) => e.id)).toEqual(['a>b']);
    expect(atlanan).toBe(5);
  });

  it('eski kayıt sunucu kimliğiyle: ds: anahtarı, sonraki yüklemede sunucudan tamamı okunur', () => {
    const { nodes } = yuklenenAkis([{ id: 'n', data: { type: 'csv_source', config: { _datasetId: 42, _uploadedData: { rows: eskiSatirlar, columns: ['a'] } } } }], []);
    expect(nodes[0].data.config._veriKaynagi).toMatchObject({ anahtar: 'ds:42', datasetId: 42 });
    expect(nodes[0].data.config._datasetId).toBeUndefined();
  });
});

describe('sonuclariAktar (geri al / yinele)', () => {
  const mevcut = [dugum('a', 'csv_source', {}, sonuc('a')), dugum('b', 'filter', { v: 1 }, sonuc('b')), dugum('c', 'sort', {}, sonuc('c')), dugum('d', 'sort', {}, sonuc('d'))];
  const kenarlar = [k('a', 'b'), k('b', 'c'), k('a', 'd')];

  it('yapısı değişmeyen düğümler sonucunu korur; config\'i değişen ve TÜM torunları düşer', () => {
    const yeni = kaliciDugumler([mevcut[0], dugum('b', 'filter', { v: 2 }), mevcut[2], mevcut[3]]);
    const r = sonuclariAktar(mevcut, kenarlar, yeni, kenarlar);
    const var_ = (id: string) => !!r.find((n) => n.id === id)!.data.result;
    expect([var_('a'), var_('b'), var_('c'), var_('d')]).toEqual([true, false, false, true]);
  });

  it('yeni gelen kenar sonucu bayatlatır; çevrim sonsuz döngüye girmez', () => {
    const yeni = kaliciDugumler(mevcut);
    const r = sonuclariAktar(mevcut, kenarlar, yeni, [...kenarlar, k('d', 'c')]);
    expect(r.find((n) => n.id === 'c')!.data.result).toBeUndefined();
    const cevrim = [k('b', 'c'), k('c', 'b')];
    expect(() => sonuclariAktar(mevcut, cevrim, yeni, cevrim)).not.toThrow();
  });
});

describe('durum deposu entegrasyonu', () => {
  it('geçmiş anlık görüntüsü sonuç ve satır taşımaz; koşu sonrası geri al sonuçları korur', () => {
    const s = useStore.getState();
    s.setNodes([dugum('a', 'csv_source', { _uploadedData: { rows: eskiSatirlar, columns: ['a'] } }), dugum('b', 'sort')]);
    s.setEdges([k('a', 'b')]);
    s.pushHistory();
    s.setNodeResult('a', sonuc('a'));
    s.setNodeResult('b', sonuc('b'));
    s.pushHistory(); // Toolbar koşu sonrası
    const anlik = JSON.stringify(useStore.getState().history.at(-1));
    expect(anlik).not.toContain('gizli');
    expect(anlik).not.toContain('"rows"');
    useStore.getState().undo();
    const n = useStore.getState().nodes;
    expect(n.find((x) => x.id === 'b')!.data.result).toBeDefined(); // yapı aynı → sonuç kaldı
  });

  it('localStorage: sonuç/satır yazılmaz; kullanıcı modelleri kaydedilir ve GERİ YÜKLENİR (eskiden hiç okunmuyordu)', () => {
    const s = useStore.getState();
    s.setNodes([dugum('a', 'csv_source', {}, sonuc('a'))]);
    s.setEdges([]);
    s.addSavedModel({ name: 'Benim akışım', description: '', category: 'Custom', nodes: [dugum('m', 'sort', {}, sonuc('m'))], edges: [], tags: [] });
    expect(s.saveToLocalStorage()).toBe(true);
    const yazilan = bellek.getItem('dataflow_workflows')!;
    expect(yazilan).not.toContain('gizli');
    const onceki = useStore.getState().savedModels.length;
    useStore.setState({ savedModels: useStore.getState().savedModels.filter((m) => m.name !== 'Benim akışım') });
    expect(useStore.getState().loadFromLocalStorage()).toBe(true);
    expect(useStore.getState().savedModels.length).toBe(onceki);
    expect(useStore.getState().savedModels.some((m) => m.name === 'Benim akışım')).toBe(true);
    // Hazır modeller localStorage'a yazılmaz (kodla gelir).
    expect(JSON.parse(yazilan).savedModels.map((m: { name: string }) => m.name)).toEqual(['Benim akışım']);
  });

  it('kota dolu: false döner ve günlüğe yazar (eskiden sessiz, arayüz "kaydedildi" diyordu)', () => {
    bellek.dolu = true;
    useStore.getState().clearLogs();
    expect(useStore.getState().saveToLocalStorage()).toBe(false);
    expect(useStore.getState().logs.some((l) => l.includes('KAYDEDİLMEDİ'))).toBe(true);
  });
});
