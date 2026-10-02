import { describe, it, expect, vi, afterEach } from 'vitest';
import { executeNode } from '../src/engine/executionEngine';
import { nodeDefinitions, getNodeDefinition } from '../src/nodes/nodeDefinitions';
import { sucAnaliziNodes, sucDiziAlanlari } from '../src/nodes/sucAnaliziNodes.generated';

type ExecArgs = Parameters<typeof executeNode>;

const node = {
  id: 'n1', type: 'custom', position: { x: 0, y: 0 },
  data: { label: 'frekans', type: 'suc_frekans', category: 'Suç Analizi', icon: 'Shield', color: '#dc2626',
    config: { alan: 'tur' }, status: 'idle' },
} as unknown as ExecArgs[0];

const edges = [{ id: 'e1', source: 'src', target: 'n1' }] as unknown as ExecArgs[1];

function upstream(): ExecArgs[2] {
  const m = new Map();
  m.set('src', { status: 'success', nodeId: 'src', nodeType: 'csv_source', timestamp: '',
    data: { columns: ['tur', 'grid_id'], rows: [{ tur: 'hirsizlik', grid_id: 'G1' }, { tur: 'gasp', grid_id: 'G2' }] } });
  return m as unknown as ExecArgs[2];
}

describe('suc_analizi üretilen node tanımları', () => {
  it('node\'lar kayıtlı, tipler benzersiz ve suc_ önekli', () => {
    // Sayı kanonik araç kataloğuyla büyür; kırılgan sabit yerine alt sınır.
    expect(sucAnaliziNodes.length).toBeGreaterThanOrEqual(42);
    const tipler = sucAnaliziNodes.map((n) => n.type);
    expect(new Set(tipler).size).toBe(tipler.length);
    expect(tipler.every((t) => t.startsWith('suc_'))).toBe(true);
    // yeni mekânsal istatistik node'ları geldi
    expect(tipler).toContain('suc_sicak_nokta_gi');
    expect(tipler).toContain('suc_mekansal_kumelenme');
  });

  it('nodeDefinitions içine yayılmış (getNodeDefinition bulur)', () => {
    const def = getNodeDefinition('suc_frekans');
    expect(def).toBeDefined();
    expect(def!.category).toBe('Suç Analizi');
    // csv_yolu/satirlar config alanı OLMAMALI — veri girişten gelir
    const alanAdlari = nodeDefinitions
      .filter((n) => n.type.startsWith('suc_'))
      .flatMap((n) => n.configFields.map((f) => f.name));
    expect(alanAdlari).not.toContain('csv_yolu');
    expect(alanAdlari).not.toContain('satirlar');
  });

  it('sucDiziAlanlari yalnız kayıtlı node tiplerini anahtar yapar', () => {
    const tipler = new Set(sucAnaliziNodes.map((n) => n.type));
    for (const anahtar of Object.keys(sucDiziAlanlari)) {
      expect(tipler.has(anahtar)).toBe(true);
    }
  });
});

describe('suc_ executor', () => {
  afterEach(() => vi.restoreAllMocks());

  it('/api/ml/suc/<arac> yoluna satirlar + config ile POST atar', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200,
      json: async () => ({ sonuc: { hirsizlik: 1, gasp: 1 }, meta: {} }) });
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(node, edges, upstream());
    expect(res.status).toBe('success');
    expect(fetchMock).toHaveBeenCalledWith('/api/ml/suc/frekans',
      expect.objectContaining({ method: 'POST', credentials: 'include' }));
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.alan).toBe('tur');
    expect(body.satirlar.length).toBe(2);
  });

  it('girdisiz koşuda fetch atmadan hata döner', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(node, edges, new Map() as unknown as ExecArgs[2]);
    expect(res.status).toBe('error');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('köprü hatasını (kapi reddi) mesajıyla iletir', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 422,
      json: async () => ({ tip: 'kapi', mesaj: 'fitness gate: n<30' }) });
    vi.stubGlobal('fetch', fetchMock);
    const res = await executeNode(node, edges, upstream());
    expect(res.status).toBe('error');
    expect(res.error).toContain('fitness gate');
  });
});
