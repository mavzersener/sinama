// Kusurlu veri fikstürleri — "gerçek veride ne bozuk olur" kataloğu.
//
// Her fikstür TAŞIDIĞI KUSURLARI beyan eder. Matris testi bu beyanı,
// ön-kontrolün gerçekten o kusuru bulduğunu doğrulamak için kullanır:
// böylece "kusur var ama kimse söylemedi" durumu test kırar.
//
// Şekiller gerçek kolluk verisinden alınmıştır: Türkçe başlıklar, noktalı
// virgül ayracı, gün.ay.yıl tarihleri, ondalık virgül, eksik koordinat.

export type Satirlar = Record<string, unknown>[];

export interface Fikstur {
  ad: string;
  aciklama: string;
  sutunlar: string[];
  satirlar: Satirlar;
  /**
   * Bu fikstürde ön-kontrolün bulması BEKLENEN kod'lar.
   * Boş dizi = temiz veri, hiçbir engel çıkmamalı.
   */
  beklenenKodlar: string[];
}

const ILLER = ['ADANA', 'ANKARA', 'IZMIR', 'BURSA', 'KONYA'];
const SUCLAR = ['OTODAN HIRSIZLIK', 'ISYERINDEN HIRSIZLIK', 'KAPKAC'];

/** Temiz temel: Türkçe başlıklı, geçerli koordinatlı, tarihli olay verisi. */
function temelSatirlar(n: number): Satirlar {
  return Array.from({ length: n }, (_, i) => ({
    'S.Nu.': i + 1,
    'Olay ili': ILLER[i % ILLER.length],
    'Olay ilce': `ILCE${i % 7}`,
    'Koordinat Enlem': 39.0 + (i % 50) * 0.01,
    'Koordinat Boylam': 32.0 + (i % 40) * 0.01,
    'Olay Tarihi': `${(i % 28) + 1}.${(i % 12) + 1}.2021`,
    'Olay Saati': `${String(i % 24).padStart(2, '0')}:00`,
    Suc: SUCLAR[i % SUCLAR.length],
    'Olay Sayisi': (i % 5) + 1,
    // ML sözleşmeleri için: ikili hedef, sepet (liste) ve tahmin sütunu.
    Yakalandi: i % 2 === 0 ? 'EVET' : 'HAYIR',
    Sepet: [SUCLAR[i % SUCLAR.length], SUCLAR[(i + 1) % SUCLAR.length]].join(';'),
    Tahmin: ((i % 5) + 1) * 0.9,
  }));
}

const SUTUNLAR = [
  'S.Nu.', 'Olay ili', 'Olay ilce', 'Koordinat Enlem', 'Koordinat Boylam',
  'Olay Tarihi', 'Olay Saati', 'Suc', 'Olay Sayisi',
  'Yakalandi', 'Sepet', 'Tahmin',
];

/** Katalog: her biri tek bir kusuru izole eder (teşhis netliği için). */
export function fiksturler(): Fikstur[] {
  return [
    {
      ad: 'temiz',
      aciklama: 'Türkçe başlıklı, geçerli koordinatlı, 120 satır — kusursuz.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120),
      beklenenKodlar: [],
    },
    {
      ad: 'az-satir',
      aciklama: 'Yalnız 8 satır — mekânsal/zamansal analiz için yetersiz.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(8),
      beklenenKodlar: ['satir_yetersiz'],  // uyarı: analiz koşar, güven zayıf
    },
    {
      ad: 'bos',
      aciklama: 'Hiç satır yok (filtre her şeyi elemiş gibi).',
      sutunlar: SUTUNLAR,
      satirlar: [],
      beklenenKodlar: ['veri_yok'],
    },
    {
      ad: 'koordinat-metin',
      aciklama: 'Enlem sütununda metin ("BILINMIYOR") — sayıya çevrilemez.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r) => ({ ...r, 'Koordinat Enlem': 'BILINMIYOR' })),
      beklenenKodlar: ['sayisal_degil'],
    },
    {
      ad: 'koordinat-virgullu',
      aciklama: 'Ondalık ayracı virgül ("39,05") — Türkçe Excel çıktısı.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r, i) => ({
        ...r,
        'Koordinat Enlem': `39,${String(i % 90).padStart(2, '0')}`,
        'Koordinat Boylam': `32,${String(i % 90).padStart(2, '0')}`,
      })),
      // Virgüllü ondalık ÇÖZÜLMELİ; kusur sayılmaz.
      beklenenKodlar: [],
    },
    {
      ad: 'koordinat-ters',
      aciklama: 'Enlem ve boylam yer değişmiş (enleme boylam konmuş).',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r) => ({
        ...r,
        'Koordinat Enlem': r['Koordinat Boylam'],
        'Koordinat Boylam': r['Koordinat Enlem'],
      })),
      // Enlem 32 (geçerli), boylam 39 (geçerli) → aralık ihlali YOK,
      // ama ikisi de Türkiye aralığının dışında kalır.
      beklenenKodlar: ['koordinat_turkiye_disi'],
    },
    {
      ad: 'koordinat-aralik-disi',
      aciklama: 'Enlem 1000 — projeksiyonlu (UTM) koordinat şüphesi.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r, i) => ({
        ...r, 'Koordinat Enlem': 400000 + i,
      })),
      beklenenKodlar: ['koordinat_aralik_disi'],
    },
    {
      ad: 'koordinat-tek-nokta',
      aciklama: 'Tüm olaylar aynı koordinatta — geokodlama hatası.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r) => ({
        ...r, 'Koordinat Enlem': 39.9, 'Koordinat Boylam': 32.85,
      })),
      beklenenKodlar: ['koordinat_tek_nokta'],
    },
    {
      ad: 'koordinat-cogu-eksik',
      aciklama: 'Koordinatların %70i boş.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r, i) =>
        i % 10 < 7 ? { ...r, 'Koordinat Enlem': '', 'Koordinat Boylam': '' } : r,
      ),
      beklenenKodlar: ['sutun_cok_eksik'],
    },
    {
      ad: 'koordinat-tamamen-bos',
      aciklama: 'Koordinat sütunu var ama tamamı boş.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r) => ({ ...r, 'Koordinat Enlem': '' })),
      beklenenKodlar: ['sutun_bos'],
    },
    {
      ad: 'tarih-bozuk',
      aciklama: 'Tarih sütununda serbest metin ("gecen hafta").',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r) => ({ ...r, 'Olay Tarihi': 'gecen hafta' })),
      beklenenKodlar: ['tarih_cozulemiyor'],
    },
    {
      ad: 'tarih-iso',
      aciklama: 'ISO 8601 tarihler — çözülmeli, kusur değil.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r, i) => ({
        ...r, 'Olay Tarihi': `2021-${String((i % 12) + 1).padStart(2, '0')}-15T10:00:00`,
      })),
      beklenenKodlar: [],
    },
    {
      ad: 'kategori-cok-fazla',
      aciklama: 'Suç sütunu her satırda farklı — kategorik analiz için fazla.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r, i) => ({ ...r, Suc: `SUC_${i}` })),
      beklenenKodlar: ['kategori_cok_fazla'],
    },
    {
      ad: 'hedef-cok-sinifli',
      aciklama: 'İkili hedef beklenirken 5 sınıf var — lojistik regresyon kırılır.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r, i) => ({ ...r, Yakalandi: `DURUM_${i % 5}` })),
      beklenenKodlar: ['hedef_ikili_degil'],
    },
    {
      ad: 'sepet-liste-degil',
      aciklama: 'Birliktelik kuralı sütunu tek değer taşıyor, liste değil.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r) => ({ ...r, Sepet: 'HIRSIZLIK' })),
      beklenenKodlar: ['liste_degil'],
    },
    {
      ad: 'sabit-sutun',
      aciklama: 'Sayısal sütunun tamamı aynı değer — varyans yok.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(120).map((r) => ({ ...r, 'Olay Sayisi': 3 })),
      beklenenKodlar: ['sabit_sutun'],
    },
    {
      ad: 'sinif-dengesizligi',
      aciklama: 'Sınıfların %99u tek değer — doğruluk yanıltıcı olur.',
      sutunlar: SUTUNLAR,
      satirlar: temelSatirlar(200).map((r, i) => ({
        ...r, Suc: i < 2 ? 'KAPKAC' : 'OTODAN HIRSIZLIK',
      })),
      beklenenKodlar: ['sinif_dengesizligi'],
    },
    {
      ad: 'koordinat-sutunu-yok',
      aciklama: 'Koordinat sütunu hiç yok — yalnız bölge adı var.',
      // YALNIZ koordinatlar çıkarılır; diğer sütunlar yerinde kalmalı,
      // yoksa fikstür ölçmek istemediği kusurları da üretir.
      sutunlar: SUTUNLAR.filter((s) => !s.startsWith('Koordinat')),
      satirlar: temelSatirlar(120).map((r) =>
        Object.fromEntries(
          Object.entries(r).filter(([k]) => !k.startsWith('Koordinat')),
        ),
      ),
      beklenenKodlar: ['sutun_yok'],
    },
  ];
}

/** Fikstürü ada göre getirir (testlerde tek senaryo koşturmak için). */
export function fikstur(ad: string): Fikstur {
  const f = fiksturler().find((x) => x.ad === ad);
  if (!f) throw new Error(`Fikstür yok: ${ad}`);
  return f;
}
