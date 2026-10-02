import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../store/useStore';
import { eskiVeriyiTasi } from './veriDeposu';

/**
 * İş akışının kalıcılaştırma sınırı: geri-alma geçmişi, localStorage, bulut
 * kaydı ve model kitaplığı hep buradan geçer.
 *
 * - YAZARKEN sonuç (`data.result`) ve çalışma durumu yazılmaz; CSV satırları
 *   düğümde taşınmaz (veriDeposu). Eskiden her geri-alma adımı tüm satırları
 *   ve tüm sonuçları JSON ile derin kopyalıyordu (50 adıma kadar);
 *   localStorage dolunca kayıt SESSİZCE yazılamıyordu.
 * - YÜKLERKEN yapı normalleştirilir: kimliği ya da türü olmayan düğüm atlanır,
 *   `config` nesne değilse `{}` olur (eskiden `config: null` taşıyan kayıt
 *   özellik panelini çökertiyordu), eski satır-içi veri depoya taşınır.
 */

type Dugum = Node<NodeData>;

const nesneMi = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);

/** Eski satır-içi veriyi (`_uploadedData`) depoya taşır; config'i yerinde değiştirir. */
function eskiVeriyiDonustur(nodeId: string, config: Record<string, unknown>): void {
  const eski = config._uploadedData;
  if (eski === undefined) return;
  delete config._uploadedData;
  const datasetId = typeof config._datasetId === 'number' ? config._datasetId : undefined;
  delete config._datasetId;
  if (!nesneMi(eski)) return;
  const kaynak = eskiVeriyiTasi(nodeId, eski, {
    hasHeader: config.hasHeader !== false,
    delimiter: typeof config.delimiter === 'string' ? config.delimiter : ',',
  }, datasetId);
  if (kaynak) config._veriKaynagi = kaynak;
}

/** Yazmadan önce: sonuç ve durum yok, satırlar düğümde yok. */
export function kaliciDugumler(nodes: Dugum[]): Dugum[] {
  return nodes.map((n) => {
    const { result: _sonuc, ...data } = n.data;
    void _sonuc;
    const config = { ...(nesneMi(data.config) ? data.config : {}) };
    eskiVeriyiDonustur(n.id, config);
    return { ...n, data: { ...data, config, status: 'idle' } } as Dugum;
  });
}

export interface YuklemeSonucu {
  nodes: Dugum[];
  edges: Edge[];
  /** Onarılamadığı için atlanan düğüm ve kenar sayısı. */
  atlanan: number;
}

/** Dışarıdan gelen (localStorage, bulut, katalog, model) akışı güvenli biçime getirir. */
export function yuklenenAkis(hamNodes: unknown, hamEdges: unknown): YuklemeSonucu {
  const nodes: Dugum[] = [];
  let atlanan = 0;
  for (const h of Array.isArray(hamNodes) ? hamNodes : []) {
    if (!nesneMi(h) || typeof h.id !== 'string' || !nesneMi(h.data) || typeof h.data.type !== 'string') {
      atlanan++;
      continue;
    }
    const d = h.data;
    const config = { ...(nesneMi(d.config) ? d.config : {}) };
    eskiVeriyiDonustur(h.id, config);
    const konum = nesneMi(h.position) && typeof h.position.x === 'number' && typeof h.position.y === 'number'
      ? h.position : { x: 0, y: 0 };
    const { result: _sonuc, ...kalan } = d as Record<string, unknown>;
    void _sonuc;
    nodes.push({
      ...h,
      type: typeof h.type === 'string' ? h.type : 'custom',
      position: konum,
      data: { ...kalan, label: typeof d.label === 'string' ? d.label : d.type, config, status: 'idle' },
    } as Dugum);
  }
  const kimlik = new Set(nodes.map((n) => n.id));
  const edges: Edge[] = [];
  for (const e of Array.isArray(hamEdges) ? hamEdges : []) {
    if (nesneMi(e) && typeof e.id === 'string' && typeof e.source === 'string' && typeof e.target === 'string'
        && kimlik.has(e.source) && kimlik.has(e.target)) {
      edges.push(e as unknown as Edge);
    } else {
      atlanan++;
    }
  }
  return { nodes, edges, atlanan };
}

/**
 * Geri al / yinele: geçmiş sonuç taşımaz; yapısı DEĞİŞMEMİŞ düğümlerin mevcut
 * sonuçları korunur. Bir düğüm; türü, config'i, gelen kenarları ve TÜM
 * ataları aynıysa değişmemiştir (atası değişen düğümün sonucu bayattır).
 */
export function sonuclariAktar(mevcutNodes: Dugum[], mevcutEdges: Edge[], yeniNodes: Dugum[], yeniEdges: Edge[]): Dugum[] {
  const imza = (n: Dugum) => JSON.stringify([n.data.type, n.data.config ?? {}]);
  const girdiler = (edges: Edge[], id: string) =>
    edges.filter((e) => e.target === id)
      .map((e) => `${e.source}|${e.sourceHandle ?? ''}|${e.targetHandle ?? ''}`).sort().join(',');
  // İmza iki tarafta da KALICI biçimden: canlı düğüm eski satır-içi biçimdeyse
  // (setNodes ile doğrudan konmuş) geçmişteki dönüştürülmüş haliyle eşleşsin.
  const mevcut = new Map(kaliciDugumler(mevcutNodes).map((n) => [n.id, n]));
  const canli = new Map(mevcutNodes.map((n) => [n.id, n]));
  const yeni = new Map(yeniNodes.map((n) => [n.id, n]));
  const not = new Map<string, boolean>();
  const ziyarette = new Set<string>();

  const degismedi = (id: string): boolean => {
    const kayitli = not.get(id);
    if (kayitli !== undefined) return kayitli;
    if (ziyarette.has(id)) return false; // çevrim: güvenli taraf
    ziyarette.add(id);
    const a = mevcut.get(id);
    const b = yeni.get(id);
    const sonuc = !!a && !!b && imza(a) === imza(b)
      && girdiler(mevcutEdges, id) === girdiler(yeniEdges, id)
      && yeniEdges.filter((e) => e.target === id).every((e) => degismedi(e.source));
    ziyarette.delete(id);
    not.set(id, sonuc);
    return sonuc;
  };

  return yeniNodes.map((n) => {
    const eski = canli.get(n.id);
    if (!eski?.data.result || !degismedi(n.id)) return n;
    return { ...n, data: { ...n.data, result: eski.data.result, status: eski.data.status } };
  });
}
