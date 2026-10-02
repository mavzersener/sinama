import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../store/useStore';
import type { ExecutionResult } from './executionEngine';
import { executeNode, getExecutionOrder, ML_DUGUMLERI } from './executionEngine';

/**
 * İş akışı yürütücüsü: bağımlılık sırasıyla, bağımsız dallar eşzamanlı.
 *
 * Eskiden Toolbar düğümleri tek tek, aralarına 0,6–1,4 sn "UX için" yapay
 * bekleme koyarak çalıştırıyordu; iptal ve zaman aşımı yoktu. Burada:
 *
 * - Bir düğüm, TÜM girdileri başarıyla bittiğinde başlar; en çok
 *   `eszamanlilik` düğüm aynı anda çalışır. Kazanç ağ düğümlerinde (ML,
 *   suç analizi, ajan): JS tek iş parçacıklı, yerel hesaplar yine sırayla
 *   işlenir ama bir ML isteği beklenirken diğer dallar ilerler.
 * - Güvenlik: yürütücüler `allResults`'tan yalnız girdilerini/atalarını
 *   okur (join, agent_insight, evidence_export) ve bunlar hep önce biter.
 * - İlk hatada yeni düğüm başlamaz; uçuştaki ağ istekleri kesilir (fail-fast,
 *   eski davranışla aynı sonuç). Kullanıcı iptali de aynı yoldan gider.
 * - Düğüm başına zaman aşımı: sinyal ağ isteğini keser; sinyali dinlemeyen
 *   düğüm için yarış kurulur (sonucu atılır). Zaman aşımı = hata; iptal =
 *   iptal (hata sayılmaz, durum 'idle'a döner).
 * - Kanıt kaydı (evidence_export) sinyal ALMAZ: yarıda kesilirse sunucuda
 *   paketsiz bir defter kaydı kalabilirdi; kısa sürer, tamamlanmasına izin
 *   verilir.
 */

export type YurutmeDurumu = 'tamamlandi' | 'hata' | 'iptal';

export interface YurutmeOlaylari {
  basladi?: (id: string) => void;
  bitti?: (id: string, sonuc: ExecutionResult) => void;
  hata?: (id: string, sonuc: ExecutionResult) => void;
  /** Başlamış ama iptal/başka düğümün hatası yüzünden kesilmiş düğüm. */
  kesildi?: (id: string) => void;
}

export interface YurutmeSecenekleri {
  nodes: Node<NodeData>[];
  edges: Edge[];
  sinyal?: AbortSignal;
  eszamanlilik?: number;
  zamanAsimiMs?: (tip: string) => number;
  olaylar?: YurutmeOlaylari;
  /** Test için: gerçek yürütücünün yerine. */
  calistir?: (node: Node<NodeData>, edges: Edge[], sonuclar: Map<string, ExecutionResult>, baglam: { sinyal: AbortSignal }) => Promise<ExecutionResult>;
}

export interface YurutmeSonucu {
  durum: YurutmeDurumu;
  sonuclar: Map<string, ExecutionResult>;
  hataDugumu: string | null;
  /** Hiç başlamamış düğümler (hata/iptal sonrası ya da girdisi başarısız). */
  baslamayanlar: string[];
  kesilenler: string[];
  sureMs: number;
}

/** Ağ düğümleri (ML servisi, suç analizi köprüsü, yerel LLM) 5 dk, kanıt 1 dk, yerel hesap 2 dk. */
export function varsayilanZamanAsimi(tip: string): number {
  // ML listesi tek kaynaktan (ML_DUGUMLERI): yeni ML düğümü ayrıca eklenmek zorunda değil.
  if (tip in ML_DUGUMLERI || tip.startsWith('suc_') || tip === 'agent_insight') return 300_000;
  if (tip === 'evidence_export') return 60_000;
  return 120_000;
}

class ZamanAsimi extends Error {}

const hataSonucu = (nodeId: string, nodeType: string, error: string): ExecutionResult =>
  ({ status: 'error', nodeId, nodeType, timestamp: new Date().toISOString(), data: {}, error, rowCount: 0 });

export async function calistirIsAkisi(s: YurutmeSecenekleri): Promise<YurutmeSonucu> {
  const bas = Date.now();
  const eszamanlilik = Math.max(1, s.eszamanlilik ?? 4);
  const zamanAsimi = s.zamanAsimiMs ?? varsayilanZamanAsimi;
  const calistir = s.calistir ?? ((n, e, r, b) => executeNode(n, e, r, b));
  const olay = s.olaylar ?? {};

  const sira = getExecutionOrder(s.nodes, s.edges);
  const kume = new Set(sira);
  const dugum = new Map(s.nodes.map((n) => [n.id, n]));
  const girdiler = new Map<string, string[]>(sira.map((id) => [id, []]));
  for (const e of s.edges) {
    if (kume.has(e.source) && kume.has(e.target)) girdiler.get(e.target)!.push(e.source);
  }

  // Koşu sinyali: kullanıcı iptali + ilk hata (fail-fast) aynı denetleyiciden.
  const kosu = new AbortController();
  const kullaniciIptali = () => kosu.abort(new DOMException('Kullanıcı iptal etti', 'AbortError'));
  if (s.sinyal?.aborted) kullaniciIptali();
  else s.sinyal?.addEventListener('abort', kullaniciIptali, { once: true });

  const sonuclar = new Map<string, ExecutionResult>();
  const bekleyen = new Set(sira);
  const calisan = new Map<string, Promise<void>>();
  const kesilenler: string[] = [];
  let durum: YurutmeDurumu = 'tamamlandi';
  let hataDugumu: string | null = null;

  const hazir = (id: string) => girdiler.get(id)!.every((g) => sonuclar.has(g));

  const baslat = (id: string) => {
    const node = dugum.get(id)!;
    bekleyen.delete(id);
    olay.basladi?.(id);
    const tip = node.data.type;
    const sure = zamanAsimi(tip);
    const zaman = new AbortController();
    const zamanlayici = setTimeout(() => zaman.abort(new ZamanAsimi(`zaman aşımı (${Math.round(sure / 1000)} sn)`)), sure);
    const kanit = tip === 'evidence_export';
    const dugumSinyali = AbortSignal.any([kosu.signal, zaman.signal]);
    // Kanıt kaydı iptal/fail-fast ile KESİLMEZ ve sonucu atılmaz (bkz. modül
    // notu): ne isteğe sinyal verilir ne de yarış koşu sinyaline bağlanır;
    // yalnız kendi zaman aşımıyla sınırlanır.
    const verilen = kanit ? new AbortController().signal : dugumSinyali;
    const yarisSinyali = kanit ? zaman.signal : dugumSinyali;

    const yaris = new Promise<never>((_, red) => {
      const dur = () => red(yarisSinyali.reason);
      if (yarisSinyali.aborted) dur();
      else yarisSinyali.addEventListener('abort', dur, { once: true });
    });

    const is = (async () => {
      let sonuc: ExecutionResult;
      try {
        sonuc = await Promise.race([calistir(node, s.edges, sonuclar, { sinyal: verilen }), yaris]);
      } catch (e) {
        sonuc = hataSonucu(id, tip, e instanceof Error ? e.message : String(e));
      } finally {
        clearTimeout(zamanlayici);
      }
      // Kendi başına BAŞARIYLA biten düğüm, sinyal sonradan düşse de başarılıdır:
      // aynı turda başka bir düğüm hata verince iptal sinyali düşer, ama bu
      // düğümün işi (ör. dışa aktarma dosyası indirildi) zaten yapılmıştır.
      // Tarayıcıda yakalandı: senkron biten Export "Kesildi" raporlanıyordu.
      if (sonuc.status === 'success') {
        sonuclar.set(id, sonuc);
        olay.bitti?.(id, sonuc);
        return;
      }
      // Hata sonucu + düşmüş sinyal: SEBEBİNE göre sınıfla — yürütücü
      // AbortError'ı kendi iletisine çevirmiş olabilir ("servise ulaşılamadı").
      if (zaman.signal.aborted && (kanit || !kosu.signal.aborted)) {
        const ek = kanit ? ' — kayıt sunucuda yine de oluşmuş olabilir; /api/evidence/verify ile denetleyin' : '';
        sonuc = hataSonucu(id, tip, `${node.data.label}: ${(zaman.signal.reason as Error).message}${ek}`);
      } else if (kosu.signal.aborted && !kanit) {
        kesilenler.push(id);
        olay.kesildi?.(id);
        return;
      }
      if (durum === 'tamamlandi') {
        durum = 'hata';
        hataDugumu = id;
        kosu.abort(new DOMException('Başka bir düğüm hata verdi', 'AbortError'));
      }
      olay.hata?.(id, sonuc);
    })();
    calisan.set(id, is.finally(() => calisan.delete(id)));
  };

  try {
    while (true) {
      if (!kosu.signal.aborted) {
        for (const id of sira) {
          if (calisan.size >= eszamanlilik) break;
          if (bekleyen.has(id) && hazir(id)) baslat(id);
        }
      }
      if (calisan.size === 0) break;
      await Promise.race(calisan.values());
    }
  } finally {
    s.sinyal?.removeEventListener('abort', kullaniciIptali);
  }
  if (durum === 'tamamlandi' && s.sinyal?.aborted && (bekleyen.size > 0 || kesilenler.length > 0)) durum = 'iptal';

  return {
    durum,
    sonuclar,
    hataDugumu,
    baslamayanlar: sira.filter((id) => bekleyen.has(id)),
    kesilenler,
    sureMs: Date.now() - bas,
  };
}
