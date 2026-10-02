import { describe, it, expect } from 'vitest';
import { profileColumns, recommendAnalyses } from './recommendations';

/**
 * Yardımcı: koordinatli satırlar üretici.
 * Verilen adlarla geçerli enlem/boylam sayıları taşıyan satır dizisi oluşturur.
 */
function koordinatliSatirlar(
  latAd: string,
  lngAd: string,
  n = 60,
): Record<string, unknown>[] {
  const rows: Record<string, unknown>[] = [];
  for (let i = 0; i < n; i++) {
    rows.push({
      [latAd]: 41.0 + i * 0.001,
      [lngAd]: 29.0 + i * 0.001,
      Suc: `Olay ${i}`,
    });
  }
  return rows;
}

describe('profileColumns — koordinat tespiti', () => {
  it("'latitude' / 'longitude' tanınır", () => {
    const columns = ['latitude', 'longitude', 'Suc'];
    const rows = koordinatliSatirlar('latitude', 'longitude');

    const profil = profileColumns(columns, rows);
    const latProfil = profil.find((p) => p.name === 'latitude');
    const lngProfil = profil.find((p) => p.name === 'longitude');

    expect(latProfil?.isLatLng).toBe('lat');
    expect(lngProfil?.isLatLng).toBe('lng');
  });

  it("'lat' / 'lng' tanınır", () => {
    const columns = ['lat', 'lng', 'Suc'];
    const rows = koordinatliSatirlar('lat', 'lng');

    const profil = profileColumns(columns, rows);
    const latProfil = profil.find((p) => p.name === 'lat');
    const lngProfil = profil.find((p) => p.name === 'lng');

    expect(latProfil?.isLatLng).toBe('lat');
    expect(lngProfil?.isLatLng).toBe('lng');
  });

  it("'Enlem' / 'Boylam' tanınır", () => {
    const columns = ['Enlem', 'Boylam', 'Suc'];
    const rows = koordinatliSatirlar('Enlem', 'Boylam');

    const profil = profileColumns(columns, rows);
    const latProfil = profil.find((p) => p.name === 'Enlem');
    const lngProfil = profil.find((p) => p.name === 'Boylam');

    expect(latProfil?.isLatLng).toBe('lat');
    expect(lngProfil?.isLatLng).toBe('lng');
  });

  it("'Koordinat Enlem' / 'Koordinat Boylam' tanınır (regresyon koruması)", () => {
    // Gerçek kolluk verisinde bu başlıklar yaygın; eski sürüm KAÇIRIYORDU
    const columns = ['Koordinat Enlem', 'Koordinat Boylam', 'Suc'];
    const rows = koordinatliSatirlar('Koordinat Enlem', 'Koordinat Boylam');

    const profil = profileColumns(columns, rows);
    const latProfil = profil.find((p) => p.name === 'Koordinat Enlem');
    const lngProfil = profil.find((p) => p.name === 'Koordinat Boylam');

    expect(latProfil?.isLatLng).toBe('lat');
    expect(lngProfil?.isLatLng).toBe('lng');
  });

  it("'lat_deg' / 'lon_deg' tanınır", () => {
    const columns = ['lat_deg', 'lon_deg', 'Suc'];
    const rows = koordinatliSatirlar('lat_deg', 'lon_deg');

    const profil = profileColumns(columns, rows);
    const latProfil = profil.find((p) => p.name === 'lat_deg');
    const lngProfil = profil.find((p) => p.name === 'lon_deg');

    expect(latProfil?.isLatLng).toBe('lat');
    expect(lngProfil?.isLatLng).toBe('lng');
  });

  it("'X Boylam' / 'Y Enlem' tanınır", () => {
    const columns = ['X Boylam', 'Y Enlem', 'Suc'];
    const rows = koordinatliSatirlar('Y Enlem', 'X Boylam');

    const profil = profileColumns(columns, rows);
    const lngProfil = profil.find((p) => p.name === 'X Boylam');
    const latProfil = profil.find((p) => p.name === 'Y Enlem');

    expect(latProfil?.isLatLng).toBe('lat');
    expect(lngProfil?.isLatLng).toBe('lng');
  });

  it("'plate' adlı sayısal sütun lat olarak IŞARETLENMEZ (alt dize tuzağı)", () => {
    // 'plate' içinde 'lat' alt dizesi var ama sözcük değil; yanlış eşleşme olmamalı
    const columns = ['plate', 'Suc'];
    const rows = [
      { plate: 10.5, Suc: 'Olay 1' },
      { plate: 20.3, Suc: 'Olay 2' },
    ];

    const profil = profileColumns(columns, rows);
    const plateProfil = profil.find((p) => p.name === 'plate');

    expect(plateProfil?.type).toBe('numeric');
    expect(plateProfil?.isLatLng).toBeUndefined();
  });

  it("'Lastik' adlı sayısal sütun lat olarak IŞARETLENMEZ", () => {
    const columns = ['Lastik', 'Suc'];
    const rows = [
      { Lastik: 5.2, Suc: 'Olay 1' },
      { Lastik: 8.1, Suc: 'Olay 2' },
    ];

    const profil = profileColumns(columns, rows);
    const lastikProfil = profil.find((p) => p.name === 'Lastik');

    expect(lastikProfil?.type).toBe('numeric');
    expect(lastikProfil?.isLatLng).toBeUndefined();
  });

  it('metin sütunu koordinat sayılmaz', () => {
    // Enlem sütununa sayı yerine metin koy
    const columns = ['Enlem', 'Boylam', 'Suc'];
    const rows = [
      { Enlem: 'abc', Boylam: 29.5, Suc: 'Olay 1' },
      { Enlem: 'def', Boylam: 30.1, Suc: 'Olay 2' },
    ];

    const profil = profileColumns(columns, rows);
    const enlemProfil = profil.find((p) => p.name === 'Enlem');

    // Enlem metin olduğundan isLatLng atanmamalı
    expect(enlemProfil?.isLatLng).toBeUndefined();
  });
});

describe('recommendAnalyses — coğrafi hotspot önerisi', () => {
  it('koordinat tanınınca geo_hotspot önerisi DOLU config ile gelir', () => {
    const columns = ['Koordinat Enlem', 'Koordinat Boylam', 'Suc'];
    const rows = koordinatliSatirlar('Koordinat Enlem', 'Koordinat Boylam');

    const recs = recommendAnalyses(columns, rows);
    const geoRec = recs.find((r) => r.nodeType === 'geo_hotspot');

    expect(geoRec).toBeDefined();
    expect(geoRec?.config.latColumn).toBe('Koordinat Enlem');
    expect(geoRec?.config.lngColumn).toBe('Koordinat Boylam');
    expect(geoRec?.config.latColumn).not.toBe('');
    expect(geoRec?.config.lngColumn).not.toBe('');
  });

  it('koordinat yoksa geo_hotspot önerilmez', () => {
    // Hiç koordinat sütunu yok
    const columns = ['Suc', 'Olay ili', 'Tarih'];
    const rows = [
      { Suc: 'Olay 1', 'Olay ili': 'İstanbul', Tarih: '2024-01-01' },
      { Suc: 'Olay 2', 'Olay ili': 'Ankara', Tarih: '2024-01-02' },
    ];

    const recs = recommendAnalyses(columns, rows);
    const geoRec = recs.find((r) => r.nodeType === 'geo_hotspot');

    expect(geoRec).toBeUndefined();
  });
});
