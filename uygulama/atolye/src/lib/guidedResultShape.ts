// Rehberli Mod sonuç şekli algılama — suç analizi araç çıktısını uygun
// görselleştirme tipine eşler. Saf ve test edilebilir; render'dan ayrı.
//
// Gerçek backend çıktı şekilleri (canlı köprüden doğrulandı):
//   grid_hotspot / kde_yogunluk : { hucreler: [{lat, lon, adet}], kapsam }
//   bolge_anomali               : { anlamli: [{bolge, gozlenen, beklenen, p, q}], ... }
//   frekans                     : { <deger>: <sayi>, ... } (düz sayım sözlüğü)
//   saat_dagilimi/gun_dagilimi  : { <dilim>: <sayi>, ... }

export type GorselTip = 'harita' | 'bar' | 'tablo' | 'json';

export interface HaritaNoktasi { lat: number; lon: number; adet: number }
export interface BarNoktasi { ad: string; deger: number }

export interface GorselPlan {
  tip: GorselTip;
  baslik: string;
  harita?: HaritaNoktasi[];
  bar?: BarNoktasi[];
  // tablo/json ham sonucu taşır
  ham?: unknown;
}

function sayiMi(v: unknown): v is number {
  return typeof v === 'number' && Number.isFinite(v);
}

// Düz {string: number} sözlüğü mü? (frekans/dağılım çıktısı)
function sayimSozlugu(o: Record<string, unknown>): BarNoktasi[] | null {
  const anahtarlar = Object.keys(o);
  if (anahtarlar.length === 0) return null;
  const hepsi = anahtarlar.every((k) => sayiMi(o[k]));
  if (!hepsi) return null;
  return anahtarlar.map((k) => ({ ad: k, deger: o[k] as number }));
}

/**
 * Araç adı + sonuç objesinden görselleştirme planı üretir.
 * Bilinmeyen/karmaşık şekiller tabloya, düz olmayanlar JSON'a düşer.
 */
export function sonucGorseli(arac: string, sonuc: unknown): GorselPlan {
  if (sonuc == null || typeof sonuc !== 'object') {
    return { tip: 'json', baslik: arac, ham: sonuc };
  }
  const s = sonuc as Record<string, unknown>;

  // 1) Mekânsal: koordinatlı hücre/sonuç listesi → harita (scatter).
  //    grid_hotspot → hucreler; Getis-Ord Gi* → sonuclar (lat/lon + gi_z).
  const mekansalDizi = Array.isArray(s.hucreler)
    ? { dizi: s.hucreler as Record<string, unknown>[], baslik: 'Yoğunluk haritası' }
    : Array.isArray(s.sonuclar) && (s.sonuclar as Record<string, unknown>[]).some((x) => sayiMi(x?.lat))
      ? { dizi: s.sonuclar as Record<string, unknown>[], baslik: 'Sıcak/soğuk nokta haritası' }
      : Array.isArray(s.yuzey) && (s.yuzey as Record<string, unknown>[]).some((x) => sayiMi(x?.lat))
        ? { dizi: s.yuzey as Record<string, unknown>[], baslik: 'Coğrafi profil (olası çapa bölgesi)' }
        : null;
  if (mekansalDizi) {
    const noktalar = mekansalDizi.dizi
      .filter((h) => sayiMi(h.lat) && sayiMi(h.lon))
      // boyut: gi_z (anlamlılık) > skor (profil) > risk (RTM) > adet
      .map((h) => ({
        lat: h.lat as number,
        lon: h.lon as number,
        adet: sayiMi(h.gi_z) ? Math.abs(h.gi_z as number)
          : sayiMi(h.skor) ? (h.skor as number)
            : sayiMi(h.risk) ? (h.risk as number)
              : sayiMi(h.adet) ? (h.adet as number) : 1,
      }));
    if (noktalar.length > 0) return { tip: 'harita', baslik: mekansalDizi.baslik, harita: noktalar };
  }

  // 2) Bölge anomalisi: anlamlı bölgeler → gözlenen sayı barı
  if (Array.isArray(s.anlamli) || Array.isArray(s.tum_sonuclar)) {
    const dizi = (s.anlamli as Record<string, unknown>[]) ?? [];
    const kaynak = dizi.length > 0 ? dizi : (s.tum_sonuclar as Record<string, unknown>[]) ?? [];
    const bar = kaynak
      .filter((x) => x && sayiMi(x.gozlenen))
      .slice(0, 20)
      .map((x) => ({ ad: String(x.bolge ?? '?'), deger: x.gozlenen as number }));
    if (bar.length > 0) return { tip: 'bar', baslik: 'Anlamlı bölgeler (gözlenen olay)', bar };
  }

  // 3) Düz sayım sözlüğü → bar (frekans, saat/gün dağılımı)
  const sayim = sayimSozlugu(s);
  if (sayim) return { tip: 'bar', baslik: 'Dağılım', bar: sayim };

  // 4) İçinde tek bir düz sayım alanı varsa (ör. {dagilim:{...}}) onu kullan
  for (const k of Object.keys(s)) {
    if (s[k] && typeof s[k] === 'object' && !Array.isArray(s[k])) {
      const ic = sayimSozlugu(s[k] as Record<string, unknown>);
      if (ic && ic.length > 1) return { tip: 'bar', baslik: k, bar: ic };
    }
  }

  // 5) Fallback: JSON
  return { tip: 'json', baslik: arac, ham: sonuc };
}
