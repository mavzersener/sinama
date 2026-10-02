// Hedeften akış üretici — düz metin bir amaç girilir, kural tabanlı olarak
// geçerli bir DataFlow iş akışı (node + edge) üretilir.
//
// YerelAjan v3'teki "hedef → görsel iskelet" mekanizmasının DataFlow'a
// uyarlaması: amaç metnindeki anahtar kelimeler bir NİYET'e eşlenir, her
// niyet için node dizisi kurulur. Üretilen her akış, sonucu doğal dile çeviren
// bir "Agent Insight" düğümü içerir — sistemin "agent destekli" yanı budur.
//
// Node tipleri kanonik nodeDefinitions kataloğundan doğrulanır; katalogda
// olmayan tip sessizce atlanır, yani üretici asla geçersiz düğüm üretmez.
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../store/useStore';
import { getNodeDefinition } from '../nodes/nodeDefinitions';

export type IntentKey =
  | 'zaman_serisi'
  | 'cografi'
  | 'suc_analizi'
  | 'kumeleme'
  | 'korelasyon'
  | 'siniflandirma'
  | 'temizlik'
  | 'genel';

interface IntentTanim {
  key: IntentKey;
  // küçük harfe indirgenmiş, TR karakter sadeleştirilmiş metinde aranır
  desen: RegExp;
  // akıştaki node tipleri (nodeDefinitions'ta var olmalı)
  akis: string[];
  aciklama: string;
}

// Sıra önemlidir: ilk eşleşen niyet kazanır (özelden genele).
const NIYETLER: IntentTanim[] = [
  {
    key: 'cografi',
    desen: /(harita|hotspot|sicak nokta|konum|koordinat|mekansal|cografi|cografy)/,
    akis: ['csv_source', 'data_quality', 'geo_hotspot', 'agent_insight', 'alert'],
    aciklama: 'Coğrafi sıcak nokta tespiti + eşik uyarısı',
  },
  {
    key: 'suc_analizi',
    desen: /(suc|magdur|supheli|fail|knox|benford|zarar|hipotez|kanit|adli|frekans)/,
    akis: ['csv_source', 'data_quality', 'suc_frekans', 'suc_bolge_anomali', 'agent_insight', 'evidence_export'],
    aciklama: 'Kanonik suç analizi: frekans + bölge anomalisi + kanıt paketi',
  },
  {
    key: 'temizlik',
    desen: /(temizle|kalite|eksik|mukerrer|dedup|\bduzelt\b|normalize)/,
    akis: ['csv_source', 'data_quality', 'data_clean', 'dedup', 'export'],
    aciklama: 'Veri temizliği ve kalite raporu',
  },
  {
    key: 'zaman_serisi',
    desen: /(zaman|seri|trend|tahmin|forecast|gelecek|\bgun\b|\bay\b|hafta|arima|mevsim|donem)/,
    akis: ['csv_source', 'data_quality', 'statistics', 'anomaly_detection', 'arima', 'agent_insight', 'chart'],
    aciklama: 'Zaman serisi: istatistik + aykırı değer + ARIMA tahmini',
  },
  {
    key: 'siniflandirma',
    desen: /(siniflandir|tahmin et|model|ongor|risk skor|random forest|karar|etiket|sinif)/,
    akis: ['csv_source', 'data_quality', 'random_forest', 'model_validation', 'agent_insight', 'chart'],
    aciklama: 'Sınıflandırma modeli + doğrulama',
  },
  {
    key: 'kumeleme',
    desen: /(kume|grup|segment|benzer|cluster|profil|kategori)/,
    akis: ['csv_source', 'data_quality', 'clustering', 'agent_insight', 'chart'],
    aciklama: 'Kümeleme (K-Means) + görselleştirme',
  },
  {
    key: 'korelasyon',
    desen: /(korelasyon|iliski|baglanti|etki|ilinti|birlikte)/,
    akis: ['csv_source', 'correlation', 'agent_insight', 'chart'],
    aciklama: 'Değişkenler arası korelasyon',
  },
];

const GENEL: IntentTanim = {
  key: 'genel',
  desen: /.*/,
  akis: ['csv_source', 'data_quality', 'statistics', 'agent_insight', 'chart'],
  aciklama: 'Genel keşif: kalite + istatistik + doğal dil yorumu',
};

export function normalizeGoal(text: string): string {
  return String(text || '')
    .replace(/İ/g, 'i') // Türkçe noktalı büyük İ; toLowerCase birleşik nokta (U+0307) bırakır
    .toLowerCase()
    .replace(/̇/g, '') // varsa artık birleşik noktayı temizle
    .replaceAll('ı', 'i')
    .replaceAll('ğ', 'g')
    .replaceAll('ü', 'u')
    .replaceAll('ş', 's')
    .replaceAll('ö', 'o')
    .replaceAll('ç', 'c');
}

export function detectIntent(goal: string): IntentTanim {
  const g = normalizeGoal(goal);
  return NIYETLER.find((n) => n.desen.test(g)) ?? GENEL;
}

// Yerleşim: soldan sağa zincir; 5 node'da bir alt satıra sar.
const SUTUN_GEN = 300;
const SATIR_YUK = 200;
const SATIR_UZUNLUGU = 5;
const BASLANGIC = { x: 60, y: 80 };

function konum(i: number): { x: number; y: number } {
  const sutun = i % SATIR_UZUNLUGU;
  const satir = Math.floor(i / SATIR_UZUNLUGU);
  return { x: BASLANGIC.x + sutun * SUTUN_GEN, y: BASLANGIC.y + satir * SATIR_YUK };
}

/**
 * Amaç metninden geçerli bir DataFlow iş akışı üretir.
 * Bilinmeyen node tipleri (katalogda yoksa) atlanır; en az bir node üretilir.
 */
export function buildWorkflow(goal: string): { nodes: Node<NodeData>[]; edges: Edge[]; intent: IntentKey } {
  const niyet = detectIntent(goal);
  const damga = Date.now();
  const nodes: Node<NodeData>[] = [];

  niyet.akis.forEach((tip) => {
    const def = getNodeDefinition(tip);
    if (!def) return; // katalogda yoksa atla — asla geçersiz düğüm üretme
    const i = nodes.length;
    nodes.push({
      id: `gen-${tip}-${damga}-${i}`,
      type: 'custom',
      position: konum(i),
      data: {
        label: def.label,
        type: def.type,
        category: def.category,
        icon: def.icon,
        color: def.color,
        config: { ...def.defaultConfig },
        status: 'idle',
      } satisfies NodeData,
    });
  });

  // Ardışık node'ları doğrusal bağla. CustomNode handle'ları id'li
  // (source="output", target="input") olduğundan edge'lerin bu id'leri
  // belirtmesi ŞART — aksi halde React Flow bağlantıyı çizmez.
  const edges: Edge[] = [];
  for (let i = 0; i < nodes.length - 1; i += 1) {
    edges.push({
      id: `gen-e${damga}-${i}`,
      source: nodes[i].id,
      target: nodes[i + 1].id,
      sourceHandle: 'output',
      targetHandle: 'input',
    });
  }

  return { nodes, edges, intent: niyet.key };
}

export function intentAciklama(goal: string): string {
  return detectIntent(goal).aciklama;
}
