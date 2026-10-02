// MATRİS TESTİ — her veri kusuru × her analiz.
//
// AMACI: kullanıcıyı tek tek denemeye zorlamamak. Farklı veri şekilleriyle
// farklı analizler koşulduğunda ortaya çıkacak sorunlar burada, elle
// tıklamadan önce görünür.
//
// ÜÇ KURAL — her hücre bunlardan birini karşılamak zorunda:
//   1. Veri uygunsa ön-kontrol ENGEL çıkarmaz.
//   2. Veri uygun değilse ön-kontrol ENGEL çıkarır ve çözüm önerir.
//   3. Hiçbir durumda çökme ya da sessiz geçiş olmaz.
//
// "Uygun değil" demek yetmez: her bulgu NE YAPILACAĞINI söylemek zorundadır.
// Bu yüzden `cozum` alanı boş olamaz — test bunu ayrıca sınar.
import { describe, it, expect } from 'vitest';
import { fiksturler } from './veri/uretici';
import {
  analizOnKontrol, engelVar, sayiCoz, tarihCoz,
  VERI_SOZLESMELERI, sutunAdaylari,
  type OnKontrolBulgusu,
} from '../src/engine/veriSozlesmesi';

/** Fikstüre göre analiz yapılandırması (gerçek kullanıcı seçimini taklit eder). */
function config(nodeType: string): Record<string, unknown> {
  const enlem = 'Koordinat Enlem';
  const boylam = 'Koordinat Boylam';
  switch (nodeType) {
    case 'geo_hotspot':
      return { latColumn: enlem, lngColumn: boylam, gridSize: 0.01 };
    case 'temporal_pattern':
      return { timeColumn: 'Olay Tarihi', categoryColumn: 'Suc' };
    case 'arima':
      return { timeColumn: 'Olay Tarihi', valueColumn: 'Olay Sayisi' };
    case 'correlation':
      return { columns: ['Olay Sayisi', enlem] };
    case 'clustering':
    case 'dbscan':
      return { features: [enlem, boylam] };
    case 'anomaly_detection':
      return { columns: ['Olay Sayisi'] };
    case 'linear_regression':
      return { target: 'Olay Sayisi', features: [enlem] };
    case 'statistics':
      return { columns: ['Olay Sayisi'] };
    case 'sna':
      return { personColumn: 'Olay ili', linkColumn: 'Olay ilce' };
    case 'cooccurrence':
      return { entityColumn: 'Suc', contextColumn: 'Olay ilce' };
    case 'aggregate':
      return { groupBy: 'Olay ili' };
    case 'filter':
      return { column: 'Suc', condition: 'equals' };

    // ---- Sunucu taraflı ML düğümleri ----
    case 'logistic_regression':
      // Hedef İKİLİ olmalı: 'Yakalandi' iki değer taşır.
      return { target: 'Yakalandi', features: 'Olay Sayisi' };
    case 'svm':
    case 'random_forest':
    case 'gradient_boosting':
      return { target: 'Suc', task: 'classification', features: 'Olay Sayisi' };
    case 'pca':
    case 'hierarchical':
      // Virgülle ayrılmış metin — ML düğümlerinde alan tipi böyle.
      return { features: `${enlem},${boylam}` };
    case 'association_rules':
      return { itemsColumn: 'Sepet' };
    case 'model_validation':
      return { actualColumn: 'Olay Sayisi', predictedColumn: 'Tahmin' };
    case 'cross_validation':
      return { target: 'Olay Sayisi', features: 'Olay Sayisi', k: 5 };
    case 'dedup':
      return { keyColumns: 'S.Nu.' };
    case 'sort':
      return { columns: 'Olay Tarihi' };
    case 'data_clean':
      return { columns: 'Suc' };
    default:
      return {};
  }
}

const ANALIZLER = Object.keys(VERI_SOZLESMELERI);
const FIKSTURLER = fiksturler();

describe('Matris — her kusur × her analiz', () => {
  it('katalog boş değil (test kendini aldatmasın)', () => {
    expect(ANALIZLER.length).toBeGreaterThan(8);
    expect(FIKSTURLER.length).toBeGreaterThan(10);
  });

  for (const f of FIKSTURLER) {
    describe(`veri: ${f.ad}`, () => {
      for (const nodeType of ANALIZLER) {
        it(`${nodeType} — çökmeden, çözüm önererek sonuç verir`, () => {
          let bulgular: OnKontrolBulgusu[];
          expect(() => {
            bulgular = analizOnKontrol(nodeType, config(nodeType), f.sutunlar, f.satirlar);
          }, `${nodeType} × ${f.ad}: ön-kontrol ÇÖKTÜ`).not.toThrow();

          // Her bulgu kendini açıklamak ve çözüm önermek zorunda.
          for (const b of bulgular!) {
            expect(b.mesaj.length, `${nodeType} × ${f.ad}: boş mesaj`).toBeGreaterThan(10);
            expect(
              b.cozum.length,
              `${nodeType} × ${f.ad}: "${b.kod}" bulgusu çözüm önermiyor`,
            ).toBeGreaterThan(10);
            expect(['engel', 'uyari']).toContain(b.seviye);
          }
        });
      }
    });
  }
});

describe('Kusurlar GERÇEKTEN yakalanıyor', () => {
  // Her fikstürün beyan ettiği kusur, en az bir analizde bulunmalı.
  // Aksi hâlde "kusur var ama kimse söylemedi" durumu oluşur.
  for (const f of FIKSTURLER.filter((x) => x.beklenenKodlar.length > 0)) {
    it(`${f.ad}: ${f.beklenenKodlar.join(', ')} bulunur`, () => {
      const tumKodlar = new Set<string>();
      for (const nodeType of ANALIZLER) {
        for (const b of analizOnKontrol(nodeType, config(nodeType), f.sutunlar, f.satirlar)) {
          tumKodlar.add(b.kod);
        }
      }
      for (const beklenen of f.beklenenKodlar) {
        expect(
          tumKodlar.has(beklenen),
          `"${f.ad}" fikstürü ${beklenen} taşıyor ama ön-kontrol bulamadı. ` +
            `Bulunanlar: ${[...tumKodlar].join(', ') || '(yok)'}`,
        ).toBe(true);
      }
    });
  }

  it('temiz veri hiçbir analizde ENGEL üretmez', () => {
    const f = FIKSTURLER.find((x) => x.ad === 'temiz')!;
    const engeller: string[] = [];
    for (const nodeType of ANALIZLER) {
      const b = analizOnKontrol(nodeType, config(nodeType), f.sutunlar, f.satirlar);
      if (engelVar(b)) {
        engeller.push(`${nodeType}: ${b.filter((x) => x.seviye === 'engel').map((x) => x.kod).join(',')}`);
      }
    }
    expect(engeller, `temiz veride engel çıktı — yanlış pozitif:\n${engeller.join('\n')}`).toEqual([]);
  });

  it('ondalık virgüllü koordinat kusur SAYILMAZ (Türkçe Excel çıktısı)', () => {
    const f = FIKSTURLER.find((x) => x.ad === 'koordinat-virgullu')!;
    const b = analizOnKontrol('geo_hotspot', config('geo_hotspot', f), f.sutunlar, f.satirlar);
    expect(b.filter((x) => x.seviye === 'engel')).toEqual([]);
  });

  it('ISO tarih kusur SAYILMAZ', () => {
    const f = FIKSTURLER.find((x) => x.ad === 'tarih-iso')!;
    const b = analizOnKontrol('temporal_pattern', config('temporal_pattern', f), f.sutunlar, f.satirlar);
    expect(b.filter((x) => x.seviye === 'engel')).toEqual([]);
  });
});

describe('Değer çözücüler', () => {
  it('sayiCoz noktalı ve virgüllü ondalığı çözer', () => {
    expect(sayiCoz('37.58')).toBeCloseTo(37.58);
    expect(sayiCoz('37,58')).toBeCloseTo(37.58);
    expect(sayiCoz(41)).toBe(41);
  });

  it('sayiCoz metni ve boşu reddeder', () => {
    expect(sayiCoz('BILINMIYOR')).toBeNull();
    expect(sayiCoz('')).toBeNull();
    expect(sayiCoz(null)).toBeNull();
  });

  it('sayiCoz binlik ayracını ondalık sanmaz', () => {
    // "1.234,56" gibi biçimlerde tek virgül kuralı korunur; "1,234,567"
    // birden çok virgül taşıdığı için ondalığa çevrilmez.
    expect(sayiCoz('1,234,567')).toBeNull();
  });

  it('tarihCoz gün.ay.yıl ve ISO biçimlerini çözer', () => {
    expect(tarihCoz('1.02.2018')?.getFullYear()).toBe(2018);
    expect(tarihCoz('2021-03-15T10:00:00')?.getFullYear()).toBe(2021);
  });

  it('tarihCoz serbest metni reddeder', () => {
    expect(tarihCoz('gecen hafta')).toBeNull();
    expect(tarihCoz('')).toBeNull();
  });
});

describe('Sütun adayları içeriğe bakar', () => {
  it('adı Enlem olan ama metin dolu sütun enlem adayı SAYILMAZ', () => {
    const f = FIKSTURLER.find((x) => x.ad === 'koordinat-metin')!;
    const adaylar = sutunAdaylari(f.sutunlar, f.satirlar, 'enlem');
    expect(adaylar).not.toContain('Koordinat Enlem');
  });

  it('geçerli koordinat sütunu enlem adayı olur', () => {
    const f = FIKSTURLER.find((x) => x.ad === 'temiz')!;
    expect(sutunAdaylari(f.sutunlar, f.satirlar, 'enlem')).toContain('Koordinat Enlem');
  });

  it('tarih adayı içerik üzerinden bulunur', () => {
    const f = FIKSTURLER.find((x) => x.ad === 'temiz')!;
    expect(sutunAdaylari(f.sutunlar, f.satirlar, 'zaman')).toContain('Olay Tarihi');
  });
});
