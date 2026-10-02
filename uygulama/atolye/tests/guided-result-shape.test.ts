import { describe, it, expect } from 'vitest';
import { sonucGorseli } from '../src/lib/guidedResultShape';

describe('sonucGorseli — gerçek backend şekilleri', () => {
  it('grid_hotspot hucreler → harita', () => {
    const sonuc = { hucreler: [{ lat: 39.9, lon: 32.8, adet: 3 }, { lat: 40.1, lon: 32.9, adet: 1 }], kapsam: {} };
    const p = sonucGorseli('grid_hotspot', sonuc);
    expect(p.tip).toBe('harita');
    expect(p.harita).toHaveLength(2);
    expect(p.harita![0].adet).toBe(3);
  });

  it('geçersiz koordinatlı hücreler elenir, kalan yoksa haritaya düşmez', () => {
    const sonuc = { hucreler: [{ lat: 'x', lon: null, adet: 1 }] };
    const p = sonucGorseli('grid_hotspot', sonuc);
    expect(p.tip).not.toBe('harita');
  });

  it('getis_ord sonuclar (lat/lon + gi_z) → harita', () => {
    const sonuc = { sonuclar: [
      { lat: 39.9, lon: 32.8, adet: 20, gi_z: 5.04, guven: '%99', tur: 'sıcak' },
      { lat: 40.1, lon: 32.9, adet: 1, gi_z: -2.1, guven: '%95', tur: 'soğuk' },
    ], sicak: 1, soguk: 1 };
    const p = sonucGorseli('sicak_nokta_gi', sonuc);
    expect(p.tip).toBe('harita');
    expect(p.baslik).toContain('nokta');
    // boyut gi_z büyüklüğünden gelmeli (|5.04|)
    expect(p.harita![0].adet).toBeCloseTo(5.04, 2);
  });

  it('cografi_profil yuzey (lat/lon + skor) → harita', () => {
    const sonuc = { tepe: { lat: 39.9, lon: 32.8, skor: 1 }, yuzey: [
      { lat: 39.9, lon: 32.8, skor: 1.0 }, { lat: 39.91, lon: 32.81, skor: 0.7 },
    ], n_suc: 5 };
    const p = sonucGorseli('cografi_profil', sonuc);
    expect(p.tip).toBe('harita');
    expect(p.baslik).toContain('çapa');
    expect(p.harita![0].adet).toBeCloseTo(1.0, 2);
  });

  it('bolge_anomali anlamli → bar (gözlenen)', () => {
    const sonuc = { anlamli: [{ bolge: 'G1', gozlenen: 24, beklenen: 5, p: 0.001, q: 0.003 }], tum_sonuclar: [] };
    const p = sonucGorseli('bolge_anomali', sonuc);
    expect(p.tip).toBe('bar');
    expect(p.bar![0]).toEqual({ ad: 'G1', deger: 24 });
  });

  it('frekans düz sayım sözlüğü → bar', () => {
    const p = sonucGorseli('frekans', { hirsizlik: 27, gasp: 13 });
    expect(p.tip).toBe('bar');
    expect(p.bar).toHaveLength(2);
    expect(p.bar!.find((b) => b.ad === 'hirsizlik')!.deger).toBe(27);
  });

  it('iç içe tek sayım alanı ({dagilim:{...}}) → bar', () => {
    const p = sonucGorseli('saat_dagilimi', { dagilim: { '8': 5, '9': 12, '10': 7 } });
    expect(p.tip).toBe('bar');
    expect(p.bar).toHaveLength(3);
  });

  it('karışık/karmaşık sonuç → json fallback', () => {
    const p = sonucGorseli('muhakeme_izi', { urun: 'markdown', notlar: ['a', 'b'] });
    expect(p.tip).toBe('json');
  });

  it('null/primitive → json fallback', () => {
    expect(sonucGorseli('x', null).tip).toBe('json');
    expect(sonucGorseli('x', 42).tip).toBe('json');
  });

  it('sayım sözlüğünde sayı olmayan değer varsa bar değil', () => {
    const p = sonucGorseli('x', { a: 1, b: 'metin' });
    expect(p.tip).toBe('json');
  });
});
