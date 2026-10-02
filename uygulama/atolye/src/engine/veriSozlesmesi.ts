// Analizlerin VERİ gereksinimleri ve öngörülü ön-kontrol.
//
// NEDEN VAR: `getRequiredFields` yalnız CONFIG alanının dolu olup olmadığına
// bakar. Oysa arızaların çoğu veri şeklinden gelir: enlem sütunu seçilmiş ama
// içinde metin var, koordinatlar Türkiye dışında, zaman sütunu ayrıştırılamıyor,
// 5 satırla kümeleme isteniyor…
//
// Bu modül her analiz için "veriden ne bekliyorum" sözleşmesini yazar ve
// analiz KOŞMADAN ÖNCE veriyi bu sözleşmeye karşı sınar. Amaç kullanıcıyı
// tek tek denemeye zorlamamak: kırılacak analiz, kırılmadan önce söylenir.
//
// ÇIKTI SÖZLEŞMESİ: her bulgu bir ÇÖZÜM taşır. "Uygun değil" demek yetmez;
// hangi düğümü ekleyeceğini ya da hangi sütunu seçeceğini söylemek gerekir.

import { sayiCoz } from './istatistik';

export type BulguSeviyesi = 'engel' | 'uyari';

export interface OnKontrolBulgusu {
  /** 'engel': analiz çalıştırılmamalı. 'uyari': çalışır ama sonuç şüpheli. */
  seviye: BulguSeviyesi;
  /** Makine-okunur kod (test ve telemetri için). */
  kod: string;
  /** İlgili sütun (varsa). */
  sutun?: string;
  mesaj: string;
  /** NE YAPILACAĞI — bu alan boş bırakılamaz. */
  cozum: string;
}

/** Bir sütundan beklenen içerik rolü. */
export type SutunRolu =
  | 'enlem' | 'boylam' | 'zaman' | 'sayisal' | 'kategorik' | 'herhangi'
  /** İkili sınıflandırma hedefi: tam olarak 2 farklı değer. */
  | 'ikili'
  /** Liste taşıyan metin (ör. "ekmek;süt;yumurta") — birliktelik kuralları. */
  | 'liste';

/** Bir analizin veriden beklediği sütun rolü. */
export interface SutunGereksinimi {
  /** config içindeki alan adı (ör. 'latColumn'). */
  alan: string;
  /** Beklenen içerik türü. */
  bekleyen: SutunRolu;
  zorunlu: boolean;
  /** config değeri çoklu mu (dizi ya da virgülle ayrılmış metin). */
  cokluMu?: boolean;
  /**
   * Rol `task` yapılandırmasına bağlıysa doldurulur.
   *
   * random_forest / gradient_boosting / svm hem sınıflandırma hem regresyon
   * yapar: hedef sütunun beklentisi seçilen göreve göre değişir. Sabit bir
   * rol yazmak, iki durumdan birinde yanlış uyarı üretirdi.
   */
  gorevBagli?: { siniflandirma: SutunRolu; regresyon: SutunRolu };
}

export interface VeriSozlesmesi {
  /** Analizin anlamlı sonuç verebilmesi için asgari satır sayısı. */
  asgariSatir: number;
  sutunlar: SutunGereksinimi[];
  /** Sözleşmenin gerekçesi — hata mesajlarında kullanılır. */
  not?: string;
}

// Türkiye sınırları — koordinat karışıklığını (enlem/boylam ters) yakalar.
const TR_ENLEM: [number, number] = [35.5, 42.5];
const TR_BOYLAM: [number, number] = [25.5, 45.0];

export const VERI_SOZLESMELERI: Record<string, VeriSozlesmesi> = {
  geo_hotspot: {
    asgariSatir: 30,
    not: 'Sıcak nokta yoğunluğu az sayıda noktada rastlantıyla oluşur.',
    sutunlar: [
      { alan: 'latColumn', bekleyen: 'enlem', zorunlu: true },
      { alan: 'lngColumn', bekleyen: 'boylam', zorunlu: true },
      { alan: 'weightColumn', bekleyen: 'sayisal', zorunlu: false },
    ],
  },
  temporal_pattern: {
    asgariSatir: 30,
    not: 'Gün/saat örüntüsü için her hücreye düşen olay sayısı yeterli olmalı.',
    sutunlar: [
      { alan: 'timeColumn', bekleyen: 'zaman', zorunlu: true },
      { alan: 'categoryColumn', bekleyen: 'kategorik', zorunlu: false },
    ],
  },
  arima: {
    asgariSatir: 24,
    not: 'Zaman serisi modeli en az iki mevsim döngüsü ister.',
    sutunlar: [
      { alan: 'timeColumn', bekleyen: 'zaman', zorunlu: false },
      { alan: 'valueColumn', bekleyen: 'sayisal', zorunlu: false },
    ],
  },
  correlation: {
    asgariSatir: 10,
    sutunlar: [{ alan: 'columns', bekleyen: 'sayisal', zorunlu: true, cokluMu: true }],
  },
  clustering: {
    asgariSatir: 10,
    not: 'Küme sayısından az gözlemle kümeleme anlamsızdır.',
    sutunlar: [{ alan: 'features', bekleyen: 'sayisal', zorunlu: true, cokluMu: true }],
  },
  dbscan: {
    asgariSatir: 10,
    sutunlar: [{ alan: 'features', bekleyen: 'sayisal', zorunlu: true, cokluMu: true }],
  },
  anomaly_detection: {
    asgariSatir: 20,
    sutunlar: [{ alan: 'columns', bekleyen: 'sayisal', zorunlu: true, cokluMu: true }],
  },
  linear_regression: {
    asgariSatir: 20,
    sutunlar: [
      { alan: 'target', bekleyen: 'sayisal', zorunlu: true },
      { alan: 'features', bekleyen: 'sayisal', zorunlu: false, cokluMu: true },
    ],
  },
  statistics: {
    asgariSatir: 3,
    sutunlar: [{ alan: 'columns', bekleyen: 'sayisal', zorunlu: false, cokluMu: true }],
  },
  sna: {
    asgariSatir: 5,
    sutunlar: [
      { alan: 'personColumn', bekleyen: 'herhangi', zorunlu: true },
      { alan: 'linkColumn', bekleyen: 'herhangi', zorunlu: true },
    ],
  },
  cooccurrence: {
    asgariSatir: 5,
    sutunlar: [
      { alan: 'entityColumn', bekleyen: 'herhangi', zorunlu: true },
      { alan: 'contextColumn', bekleyen: 'herhangi', zorunlu: true },
    ],
  },
  aggregate: {
    asgariSatir: 1,
    sutunlar: [
      { alan: 'groupBy', bekleyen: 'herhangi', zorunlu: true },
      { alan: 'valueColumn', bekleyen: 'sayisal', zorunlu: false },
    ],
  },
  filter: {
    asgariSatir: 1,
    sutunlar: [{ alan: 'column', bekleyen: 'herhangi', zorunlu: true }],
  },

  // ---- Sunucu taraflı ML düğümleri (ml-service) ----
  //
  // Bunlar hesabı dışarıda yapar ama VERİ gereksinimi aynı ölçüde katıdır:
  // ikili lojistik regresyona üç sınıflı hedef vermek, sabit bir sütunla
  // PCA istemek ya da liste taşımayan bir sütundan birliktelik kuralı
  // çıkarmak sessizce anlamsız sonuç üretir.

  logistic_regression: {
    asgariSatir: 30,
    not: 'İkili lojistik regresyon hedefte tam olarak iki sınıf ister.',
    sutunlar: [
      { alan: 'target', bekleyen: 'ikili', zorunlu: true },
      { alan: 'features', bekleyen: 'sayisal', zorunlu: false, cokluMu: true },
    ],
  },
  svm: {
    asgariSatir: 30,
    sutunlar: [
      {
        alan: 'target', bekleyen: 'herhangi', zorunlu: true,
        gorevBagli: { siniflandirma: 'kategorik', regresyon: 'sayisal' },
      },
      { alan: 'features', bekleyen: 'sayisal', zorunlu: false, cokluMu: true },
    ],
  },
  random_forest: {
    asgariSatir: 30,
    sutunlar: [
      {
        alan: 'target', bekleyen: 'herhangi', zorunlu: true,
        gorevBagli: { siniflandirma: 'kategorik', regresyon: 'sayisal' },
      },
      { alan: 'features', bekleyen: 'sayisal', zorunlu: false, cokluMu: true },
    ],
  },
  gradient_boosting: {
    asgariSatir: 30,
    sutunlar: [
      {
        alan: 'target', bekleyen: 'herhangi', zorunlu: true,
        gorevBagli: { siniflandirma: 'kategorik', regresyon: 'sayisal' },
      },
      { alan: 'features', bekleyen: 'sayisal', zorunlu: false, cokluMu: true },
    ],
  },
  pca: {
    asgariSatir: 10,
    not: 'Temel bileşen analizi en az iki değişken ve değişkenlik ister.',
    sutunlar: [{ alan: 'features', bekleyen: 'sayisal', zorunlu: true, cokluMu: true }],
  },
  hierarchical: {
    asgariSatir: 10,
    sutunlar: [{ alan: 'features', bekleyen: 'sayisal', zorunlu: true, cokluMu: true }],
  },
  association_rules: {
    asgariSatir: 20,
    not: 'Birliktelik kuralları için sütun liste taşımalı (ör. "a;b;c").',
    sutunlar: [{ alan: 'itemsColumn', bekleyen: 'liste', zorunlu: true }],
  },
  model_validation: {
    asgariSatir: 10,
    // Sınıf etiketleri: metin ("hırsızlık") ya da kodlu (0/1). Eskiden
    // 'sayisal' isteniyordu — metin etiketli her doğrulama engelleniyordu.
    sutunlar: [
      { alan: 'actualColumn', bekleyen: 'kategorik', zorunlu: true },
      { alan: 'predictedColumn', bekleyen: 'kategorik', zorunlu: true },
    ],
  },
  cross_validation: {
    asgariSatir: 30,
    not: 'k-kat çapraz doğrulama her kata yeterli gözlem ister.',
    sutunlar: [
      // Bu düğüm regresyon (OLS) doğrular: hedef sayısal olmalı. 'herhangi'
      // iken metin hedef ön-kontrolden geçip hesapta NaN üretiyordu.
      { alan: 'target', bekleyen: 'sayisal', zorunlu: true },
      { alan: 'features', bekleyen: 'sayisal', zorunlu: false, cokluMu: true },
    ],
  },

  // ---- Dönüşüm düğümleri ----
  dedup: {
    asgariSatir: 1,
    sutunlar: [{ alan: 'keyColumns', bekleyen: 'herhangi', zorunlu: false, cokluMu: true }],
  },
  sort: {
    asgariSatir: 1,
    sutunlar: [{ alan: 'columns', bekleyen: 'herhangi', zorunlu: false, cokluMu: true }],
  },
  data_clean: {
    asgariSatir: 1,
    sutunlar: [{ alan: 'columns', bekleyen: 'herhangi', zorunlu: false, cokluMu: true }],
  },
};

// ---------------------------------------------------------------- ölçümler

const bosMu = (v: unknown) => v === null || v === undefined || v === '';

// Tek kaynak: ön-kontrol ile yürütücüler AYNI çözücüyü kullanır. Ayrı
// kopyalar varken ön-kontrol "37,58"i sayı sayıp yürütücü Number() ile NaN
// diye atıyordu.
export { sayiCoz };

/** Metni tarihe çevirmeyi dener; Türk biçimlerini (g.a.yyyy) de tanır. */
export function tarihCoz(v: unknown): Date | null {
  if (v instanceof Date) return Number.isNaN(v.getTime()) ? null : v;
  if (typeof v === 'number') return null;
  if (typeof v !== 'string') return null;
  const t = v.trim();
  if (!t) return null;
  // 1.02.2018 / 01/02/2018 → gün.ay.yıl
  const tr = t.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{4})/);
  if (tr) {
    const d = new Date(Number(tr[3]), Number(tr[2]) - 1, Number(tr[1]));
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(t);
  return Number.isNaN(d.getTime()) ? null : d;
}

interface SutunOlcumu {
  doluOran: number;
  sayisalOran: number;
  tarihOran: number;
  farkli: number;
  enKucuk: number | null;
  enBuyuk: number | null;
  /** Ayraç (; , |) taşıyan değerlerin oranı — liste sütunu tespiti. */
  listeOran: number;
  /** En sık değerin payı — sınıf dengesizliği tespiti. */
  enSikPay: number;
}

function sutunuOlc(rows: Record<string, unknown>[], sutun: string): SutunOlcumu {
  const ornek = rows.slice(0, 1000);
  const degerler = ornek.map((r) => r[sutun]);
  const dolu = degerler.filter((v) => !bosMu(v));
  const sayilar = dolu.map(sayiCoz).filter((n): n is number => n !== null);
  const tarihler = dolu.filter((v) => tarihCoz(v) !== null);
  const listeli = dolu.filter((v) => typeof v === 'string' && /[;,|]/.test(v));
  const sayac = new Map<string, number>();
  dolu.forEach((v) => {
    const k = String(v);
    sayac.set(k, (sayac.get(k) ?? 0) + 1);
  });
  const enSik = sayac.size ? Math.max(...sayac.values()) : 0;
  return {
    doluOran: degerler.length ? dolu.length / degerler.length : 0,
    sayisalOran: dolu.length ? sayilar.length / dolu.length : 0,
    tarihOran: dolu.length ? tarihler.length / dolu.length : 0,
    farkli: sayac.size,
    enKucuk: sayilar.length ? Math.min(...sayilar) : null,
    enBuyuk: sayilar.length ? Math.max(...sayilar) : null,
    listeOran: dolu.length ? listeli.length / dolu.length : 0,
    enSikPay: dolu.length ? enSik / dolu.length : 0,
  };
}

// ---------------------------------------------------------------- ön-kontrol

/**
 * config alanından sütun adlarını çıkarır.
 *
 * Çoklu alanlar hem dizi hem VİRGÜLLE AYRILMIŞ METİN olabilir: ML
 * düğümlerinde `features` bir metin girdisidir ("age,income"). Metni tek
 * sütun adı saymak, var olan sütunları "yok" diye bildirirdi.
 */
function alanDegerleri(config: Record<string, unknown>, g: SutunGereksinimi): string[] {
  const v = config[g.alan];
  if (Array.isArray(v)) {
    return v.filter((x): x is string => typeof x === 'string' && x.trim() !== '')
      .map((x) => x.trim());
  }
  if (typeof v !== 'string' || !v.trim()) return [];
  if (g.cokluMu) {
    return v.split(',').map((x) => x.trim()).filter(Boolean);
  }
  return [v.trim()];
}

/** `task` yapılandırmasına bağlı rolü çözer. */
function rolCoz(g: SutunGereksinimi, config: Record<string, unknown>): SutunRolu {
  if (!g.gorevBagli) return g.bekleyen;
  const gorev = String(config.task ?? 'classification').toLowerCase();
  return gorev.startsWith('reg') ? g.gorevBagli.regresyon : g.gorevBagli.siniflandirma;
}

const ROL_ADI: Record<SutunRolu, string> = {
  enlem: 'enlem', boylam: 'boylam', zaman: 'zaman/tarih',
  sayisal: 'sayısal', kategorik: 'kategorik', herhangi: 'değer',
  ikili: 'iki sınıflı (ikili)', liste: 'liste taşıyan',
};

/**
 * Bir analizi ÇALIŞTIRMADAN ÖNCE verinin uygunluğunu sınar.
 *
 * @param nodeType analiz düğümü türü
 * @param config düğüm yapılandırması
 * @param columns veride bulunan sütun adları
 * @param rows veri satırları (örneklem yeterli; ilk 1000 kullanılır)
 * @returns bulgular; boş dizi = engel yok
 */
export function analizOnKontrol(
  nodeType: string,
  config: Record<string, unknown>,
  columns: string[],
  rows: Record<string, unknown>[],
): OnKontrolBulgusu[] {
  const sozlesme = VERI_SOZLESMELERI[nodeType];
  if (!sozlesme) return [];
  const bulgular: OnKontrolBulgusu[] = [];

  if (rows.length === 0) {
    return [{
      seviye: 'engel', kod: 'veri_yok',
      mesaj: 'Analize gelen veri boş.',
      cozum: 'Yukarı akıştaki veri kaynağını ve filtreleri kontrol edin; ' +
             'filtre tüm satırları elemiş olabilir.',
    }];
  }

  // Satır sayısı: İKİ AYRI eşik.
  //
  // Az satır bir DOĞRULUK hatası değil, istatistiksel güven sorunudur —
  // 5 satırla keşif yapmak meşrudur. Bu yüzden 'uyari'dır: analiz koşar,
  // sonucun güvenilmezliği bildirilir.
  //
  // Ancak 3 satırın altında hiçbir dağılım/komşuluk hesaplanamaz; orada
  // engel gerçekten vardır.
  if (rows.length < 3) {
    bulgular.push({
      seviye: 'uyari', kod: 'satir_cok_az',
      mesaj: `Yalnız ${rows.length} satır var; hiçbir dağılım ya da komşuluk ` +
             'anlamlı hesaplanamaz.',
      cozum: 'Veri kaynağını ve filtreleri kontrol edin.',
    });
  } else if (rows.length < sozlesme.asgariSatir) {
    bulgular.push({
      seviye: 'uyari', kod: 'satir_yetersiz',
      mesaj: `Bu analiz için ${sozlesme.asgariSatir} satır önerilir; ` +
             `${rows.length} satır var — sonuç istatistiksel olarak zayıftır.` +
             (sozlesme.not ? ` ${sozlesme.not}` : ''),
      cozum: 'Daha geniş bir dönem/kapsam seçin ya da filtreyi gevşetin; ' +
             'bu sonucu yayına ya da karara esas almayın.',
    });
  }

  for (const g of sozlesme.sutunlar) {
    const secilenler = alanDegerleri(config, g);

    if (secilenler.length === 0) {
      if (g.zorunlu) {
        // Seviye 'uyari': "config alanı boş" denetimi ZATEN doğrulama
        // katmanında var (getRequiredFields) ve yürütücülerin kendi
        // mesajları daha özeldir. Burada tekrar engellemek, daha genel bir
        // mesajın daha özel olanı bastırmasına yol açardı. Katkımız aday
        // sütunları göstermek; engelleme değil.
        const adaylar = sutunAdaylari(columns, rows, rolCoz(g, config));
        bulgular.push({
          seviye: 'uyari', kod: 'sutun_secilmedi', sutun: g.alan,
          mesaj: `"${g.alan}" seçilmemiş (${ROL_ADI[rolCoz(g, config)]} sütunu gerekli).`,
          cozum: adaylar.length
            ? `Uygun görünen sütunlar: ${adaylar.join(', ')}.`
            : `Veride ${ROL_ADI[rolCoz(g, config)]} niteliğinde sütun bulunamadı; ` +
              'Veri Temizleme düğümüyle sütunu dönüştürmeniz gerekebilir.',
        });
      }
      continue;
    }

    for (const sutun of secilenler) {
      if (!columns.includes(sutun)) {
        bulgular.push({
          seviye: 'engel', kod: 'sutun_yok', sutun,
          mesaj: `Seçilen sütun veride yok: "${sutun}".`,
          cozum: `Mevcut sütunlar: ${columns.slice(0, 12).join(', ')}` +
                 `${columns.length > 12 ? '…' : ''}.`,
        });
        continue;
      }
      bulgular.push(...sutunuSina(sutun, rolCoz(g, config), rows));
    }
  }

  return bulgular;
}

/** Tek sütunu beklenen role karşı sınar. */
function sutunuSina(
  sutun: string,
  bekleyen: SutunRolu,
  rows: Record<string, unknown>[],
): OnKontrolBulgusu[] {
  const b: OnKontrolBulgusu[] = [];
  const o = sutunuOlc(rows, sutun);

  if (o.doluOran === 0) {
    return [{
      seviye: 'engel', kod: 'sutun_bos', sutun,
      mesaj: `"${sutun}" sütununun tamamı boş.`,
      cozum: 'Başka bir sütun seçin ya da veri kaynağını kontrol edin.',
    }];
  }
  if (o.doluOran < 0.5) {
    b.push({
      seviye: 'uyari', kod: 'sutun_cok_eksik', sutun,
      mesaj: `"${sutun}" sütununda doluluk %${Math.round(o.doluOran * 100)}.`,
      cozum: 'Veri Temizleme düğümüyle eksik satırları eleyin; aksi hâlde ' +
             'sonuç veri kaybını yansıtır.',
    });
  }

  if (bekleyen === 'sayisal' || bekleyen === 'enlem' || bekleyen === 'boylam') {
    if (o.sayisalOran < 0.9) {
      b.push({
        seviye: 'engel', kod: 'sayisal_degil', sutun,
        mesaj: `"${sutun}" sayısal değil (dolu değerlerin yalnız ` +
               `%${Math.round(o.sayisalOran * 100)}'i sayıya çevrilebiliyor).`,
        cozum: 'Veri Temizleme düğümünde bu sütunu sayıya dönüştürün; ' +
               'ondalık ayracı virgülse nokta yapın.',
      });
      return b;
    }
  }

  if (bekleyen === 'enlem' || bekleyen === 'boylam') {
    const [alt, ust] = bekleyen === 'enlem' ? [-90, 90] : [-180, 180];
    if (o.enKucuk !== null && (o.enKucuk < alt || (o.enBuyuk ?? 0) > ust)) {
      b.push({
        seviye: 'engel', kod: 'koordinat_aralik_disi', sutun,
        mesaj: `"${sutun}" ${bekleyen} aralığının dışında ` +
               `(${o.enKucuk} … ${o.enBuyuk}; beklenen ${alt} … ${ust}).`,
        cozum: 'Enlem ve boylam sütunları ters seçilmiş olabilir; ' +
               'ya da koordinatlar projeksiyonlu (UTM) olabilir.',
      });
      return b;
    }
    // Türkiye dışı: engel değil ama sessiz geçilmemeli.
    const [trAlt, trUst] = bekleyen === 'enlem' ? TR_ENLEM : TR_BOYLAM;
    if (o.enKucuk !== null && (o.enBuyuk! < trAlt || o.enKucuk > trUst)) {
      b.push({
        seviye: 'uyari', kod: 'koordinat_turkiye_disi', sutun,
        mesaj: `"${sutun}" değerleri Türkiye aralığı dışında ` +
               `(${o.enKucuk} … ${o.enBuyuk}).`,
        cozum: 'Enlem/boylam sütunlarının yer değişmiş olup olmadığını ' +
               'kontrol edin.',
      });
    }
    if (o.farkli === 1) {
      b.push({
        seviye: 'engel', kod: 'koordinat_tek_nokta', sutun,
        mesaj: `"${sutun}" tek bir değerden oluşuyor; tüm olaylar aynı noktada.`,
        cozum: 'Geokodlama hatası şüphesi — kaynak veriyi kontrol edin.',
      });
    }
  }

  if (bekleyen === 'zaman' && o.tarihOran < 0.8) {
    b.push({
      seviye: 'engel', kod: 'tarih_cozulemiyor', sutun,
      mesaj: `"${sutun}" tarih olarak çözülemiyor (dolu değerlerin ` +
             `%${Math.round(o.tarihOran * 100)}'i çözülebiliyor).`,
      cozum: 'Veri Temizleme düğümünde tarih biçimini standartlaştırın ' +
             '(gün.ay.yıl ve ISO desteklenir).',
    });
  }

  if (bekleyen === 'kategorik' && o.farkli > 50) {
    b.push({
      seviye: 'uyari', kod: 'kategori_cok_fazla', sutun,
      mesaj: `"${sutun}" ${o.farkli} farklı değer taşıyor; kategorik ` +
             'analiz için fazla.',
      cozum: 'Değerleri gruplayın ya da başka bir sütun seçin.',
    });
  }

  // İkili sınıflandırma hedefi: TAM OLARAK iki sınıf.
  if (bekleyen === 'ikili' && o.farkli !== 2) {
    b.push({
      seviye: 'engel', kod: 'hedef_ikili_degil', sutun,
      mesaj: `"${sutun}" ${o.farkli} farklı değer taşıyor; ikili lojistik ` +
             'regresyon tam olarak iki sınıf ister.',
      cozum: o.farkli > 2
        ? 'Sınıfları ikiye indirin (ör. "var/yok") ya da çok sınıflı bir ' +
          'yöntem seçin (Random Forest sınıflandırma).'
        : 'Hedef sütunda tek değer var; sınıflandırma yapılamaz.',
    });
    return b;
  }

  // Birliktelik kuralları liste taşıyan sütun ister.
  if (bekleyen === 'liste' && o.listeOran < 0.5) {
    b.push({
      seviye: 'engel', kod: 'liste_degil', sutun,
      mesaj: `"${sutun}" liste taşımıyor (değerlerin yalnız ` +
             `%${Math.round(o.listeOran * 100)}'i ayraç içeriyor).`,
      cozum: 'Birliktelik kuralları için her satırda birlikte görülen ' +
             'öğeler tek hücrede olmalı (ör. "hırsızlık;darp"). Sepet ' +
             'biçimine getirmek için Birleştir düğümünü kullanın.',
    });
    return b;
  }

  // Sabit sütun: varyans yok. Regresyon/kümeleme/PCA için anlamsız.
  if (o.farkli === 1 &&
      (bekleyen === 'sayisal' || bekleyen === 'kategorik')) {
    b.push({
      seviye: 'engel', kod: 'sabit_sutun', sutun,
      mesaj: `"${sutun}" tek bir değerden oluşuyor; değişkenlik yok.`,
      cozum: 'Bu sütun modele bilgi katmaz; çıkarın ya da başka sütun seçin.',
    });
    return b;
  }

  // Sınıf dengesizliği: baskın sınıf %95'i aşarsa doğruluk yanıltıcıdır.
  if ((bekleyen === 'kategorik' || bekleyen === 'ikili') && o.enSikPay > 0.95) {
    b.push({
      seviye: 'uyari', kod: 'sinif_dengesizligi', sutun,
      mesaj: `"${sutun}" içinde baskın sınıfın payı ` +
             `%${Math.round(o.enSikPay * 100)}.`,
      cozum: 'Doğruluk (accuracy) bu veride yanıltıcıdır; kesinlik/duyarlılık ' +
             've karışıklık matrisine bakın, gerekiyorsa örneklemi dengeleyin.',
    });
  }

  return b;
}

/**
 * Veride bir role uygun sütun adaylarını bulur (hata mesajına ipucu).
 *
 * Yalnız ada değil İÇERİĞE de bakar: "Enlem" adlı ama metin dolu bir sütun
 * aday gösterilmez.
 */
export function sutunAdaylari(
  columns: string[],
  rows: Record<string, unknown>[],
  bekleyen: SutunRolu,
): string[] {
  const adaylar: string[] = [];
  for (const c of columns) {
    const o = sutunuOlc(rows, c);
    if (o.doluOran === 0) continue;
    if (bekleyen === 'zaman' && o.tarihOran >= 0.8) adaylar.push(c);
    else if (bekleyen === 'sayisal' && o.sayisalOran >= 0.9) adaylar.push(c);
    else if (bekleyen === 'enlem' && o.sayisalOran >= 0.9 &&
             (o.enKucuk ?? -999) >= -90 && (o.enBuyuk ?? 999) <= 90) adaylar.push(c);
    else if (bekleyen === 'boylam' && o.sayisalOran >= 0.9 &&
             (o.enKucuk ?? -999) >= -180 && (o.enBuyuk ?? 999) <= 180) adaylar.push(c);
    else if (bekleyen === 'kategorik' && o.farkli > 1 && o.farkli <= 50) adaylar.push(c);
    else if (bekleyen === 'ikili' && o.farkli === 2) adaylar.push(c);
    else if (bekleyen === 'liste' && o.listeOran >= 0.5) adaylar.push(c);
    else if (bekleyen === 'herhangi') adaylar.push(c);
  }
  return adaylar.slice(0, 8);
}

/** Bulgular arasında engel var mı (analiz çalıştırılmamalı mı). */
export const engelVar = (b: OnKontrolBulgusu[]) => b.some((x) => x.seviye === 'engel');
