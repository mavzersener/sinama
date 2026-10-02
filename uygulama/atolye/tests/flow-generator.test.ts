import { describe, it, expect } from 'vitest';
import { detectIntent, buildWorkflow, normalizeGoal } from '../src/lib/flowGenerator';
import { getNodeDefinition } from '../src/nodes/nodeDefinitions';

describe('flowGenerator — niyet tespiti', () => {
  const ornekler: Array<[string, string]> = [
    ['köylere göre olay yoğunluğunu haritala', 'cografi'],
    ['son 3 yılın asayiş trendini tahmin et', 'zaman_serisi'],
    ['suç türlerinin frekansını çıkar ve anomali bak', 'suc_analizi'],
    ['müşterileri benzer segmentlere kümele', 'kumeleme'],
    ['gelir ve yaş arasındaki korelasyonu bul', 'korelasyon'],
    ['riski sınıflandıran bir model kur', 'siniflandirma'],
    ['veriyi temizle ve mükerrer kayıtları at', 'temizlik'],
    ['bir şeyler yap işte', 'genel'],
  ];
  for (const [goal, beklenen] of ornekler) {
    it(`"${goal}" → ${beklenen}`, () => {
      expect(detectIntent(goal).key).toBe(beklenen);
    });
  }

  it('TR karakterleri sadeleştirir', () => {
    expect(normalizeGoal('Şüpheli Göç İğne')).toBe('supheli goc igne');
  });
});

describe('flowGenerator — iş akışı üretimi', () => {
  it('her üretilen node tipi katalogda vardır', () => {
    const hedefler = [
      'hotspot haritası', 'zaman serisi tahmini', 'suç frekansı',
      'kümeleme', 'korelasyon', 'sınıflandırma modeli', 'veri temizliği', 'genel analiz',
    ];
    for (const h of hedefler) {
      const { nodes } = buildWorkflow(h);
      expect(nodes.length).toBeGreaterThan(0);
      for (const n of nodes) {
        expect(getNodeDefinition(n.data.type), `bilinmeyen tip: ${n.data.type}`).toBeDefined();
      }
    }
  });

  it('edge\'ler var olan node id\'lerine bağlanır ve zinciri kurar', () => {
    const { nodes, edges } = buildWorkflow('asayiş trendini tahmin et');
    const idler = new Set(nodes.map((n) => n.id));
    expect(edges.length).toBe(nodes.length - 1);
    for (const e of edges) {
      expect(idler.has(e.source)).toBe(true);
      expect(idler.has(e.target)).toBe(true);
      // CustomNode handle'ları id'li olduğundan edge'ler handle belirtmeli
      expect(e.sourceHandle).toBe('output');
      expect(e.targetHandle).toBe('input');
    }
  });

  it('agent destekli: üretilen akış bir agent_insight düğümü içerir (uygun niyetlerde)', () => {
    const g = buildWorkflow('gelir ve skor korelasyonu');
    expect(g.nodes.some((n) => n.data.type === 'agent_insight')).toBe(true);
  });

  it('coğrafi niyet geo_hotspot + alert üretir', () => {
    const { nodes } = buildWorkflow('köy bazlı sıcak nokta haritası');
    const tipler = nodes.map((n) => n.data.type);
    expect(tipler).toContain('geo_hotspot');
    expect(tipler).toContain('alert');
  });

  it('suç niyeti kanonik suç node\'larını + kanıt çıktısını üretir', () => {
    const { nodes } = buildWorkflow('olay frekansı ve bölge anomalisi, kanıt üret');
    const tipler = nodes.map((n) => n.data.type);
    expect(tipler).toContain('suc_frekans');
    expect(tipler).toContain('suc_bolge_anomali');
    expect(tipler).toContain('evidence_export');
  });

  it('node\'lar geçerli konum ve custom tip taşır', () => {
    const { nodes } = buildWorkflow('genel analiz');
    for (const n of nodes) {
      expect(n.type).toBe('custom');
      expect(typeof n.position.x).toBe('number');
      expect(typeof n.position.y).toBe('number');
      expect(n.data.config).toBeDefined();
    }
  });

  it('id\'ler benzersizdir', () => {
    const { nodes } = buildWorkflow('zaman serisi tahmini ve anomali');
    const idler = nodes.map((n) => n.id);
    expect(new Set(idler).size).toBe(idler.length);
  });
});
