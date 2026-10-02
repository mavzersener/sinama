import { describe, it, expect } from 'vitest';
import type { DugumOzeti, KenarOzeti } from './ustSutunlar';
import { ustSutunlariBul, sutunlariSirala } from './ustSutunlar';

describe('ustSutunlariBul', () => {
  it('doğrudan üst düğümün sütunlarını bulur', () => {
    // A → B kenarı; A'da sonucSutunlari var
    const dugumler: DugumOzeti[] = [
      { id: 'A', sonucSutunlari: ['x', 'y'] },
      { id: 'B' },
    ];
    const kenarlar: KenarOzeti[] = [{ source: 'A', target: 'B' }];

    const sonuc = ustSutunlariBul('B', dugumler, kenarlar);
    expect(sonuc).toEqual(['x', 'y']);
  });

  it('iki adım yukarıdan bulur', () => {
    // A → B → C; A'da sütun, B'de yok
    const dugumler: DugumOzeti[] = [
      { id: 'A', sonucSutunlari: ['a', 'b'] },
      { id: 'B' },
      { id: 'C' },
    ];
    const kenarlar: KenarOzeti[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'C' },
    ];

    const sonuc = ustSutunlariBul('C', dugumler, kenarlar);
    expect(sonuc).toEqual(['a', 'b']);
  });

  it('EN YAKIN kaynak kazanır', () => {
    // A(['a']) → B(['b']) → C; B daha yakın
    const dugumler: DugumOzeti[] = [
      { id: 'A', sonucSutunlari: ['a'] },
      { id: 'B', sonucSutunlari: ['b'] },
      { id: 'C' },
    ];
    const kenarlar: KenarOzeti[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'C' },
    ];

    const sonuc = ustSutunlariBul('C', dugumler, kenarlar);
    expect(sonuc).toEqual(['b']);
  });

  it('sonucSutunlari yoksa yuklenenSutunlar kullanılır', () => {
    // A(yuklenenSutunlar) → B
    const dugumler: DugumOzeti[] = [
      { id: 'A', yuklenenSutunlar: ['p', 'q'] },
      { id: 'B' },
    ];
    const kenarlar: KenarOzeti[] = [{ source: 'A', target: 'B' }];

    const sonuc = ustSutunlariBul('B', dugumler, kenarlar);
    expect(sonuc).toEqual(['p', 'q']);
  });

  it('sonucSutunlari VARSA onu tercih eder', () => {
    // A(sonucSutunlari:['s'], yuklenenSutunlar:['y']) → B
    const dugumler: DugumOzeti[] = [
      { id: 'A', sonucSutunlari: ['s'], yuklenenSutunlar: ['y'] },
      { id: 'B' },
    ];
    const kenarlar: KenarOzeti[] = [{ source: 'A', target: 'B' }];

    const sonuc = ustSutunlariBul('B', dugumler, kenarlar);
    expect(sonuc).toEqual(['s']);
  });

  it('boş dizi sütun sayılmaz', () => {
    // A(sonucSutunlari:[], yuklenenSutunlar:['z']) → B
    const dugumler: DugumOzeti[] = [
      { id: 'A', sonucSutunlari: [], yuklenenSutunlar: ['z'] },
      { id: 'B' },
    ];
    const kenarlar: KenarOzeti[] = [{ source: 'A', target: 'B' }];

    const sonuc = ustSutunlariBul('B', dugumler, kenarlar);
    expect(sonuc).toEqual(['z']);
  });

  it('hiç sütun yoksa boş dizi döner', () => {
    // A (sütun yok) → B
    const dugumler: DugumOzeti[] = [{ id: 'A' }, { id: 'B' }];
    const kenarlar: KenarOzeti[] = [{ source: 'A', target: 'B' }];

    const sonuc = ustSutunlariBul('B', dugumler, kenarlar);
    expect(sonuc).toEqual([]);
  });

  it('döngülü grafta sonsuza gitmez', () => {
    // A → B, B → A kenarları; hiçbirinde sütun yok
    const dugumler: DugumOzeti[] = [{ id: 'A' }, { id: 'B' }];
    const kenarlar: KenarOzeti[] = [
      { source: 'A', target: 'B' },
      { source: 'B', target: 'A' },
    ];

    // Zaman aşımı riski yoksa test başarılı
    const sonuc = ustSutunlariBul('B', dugumler, kenarlar);
    expect(sonuc).toEqual([]);
  });

  it('hedefin KENDİ sütunları dikkate alınmaz', () => {
    // A(['ust']) → B; B'nin kendi sonucSutunlari:['kendi'] olsun
    const dugumler: DugumOzeti[] = [
      { id: 'A', sonucSutunlari: ['ust'] },
      { id: 'B', sonucSutunlari: ['kendi'] },
    ];
    const kenarlar: KenarOzeti[] = [{ source: 'A', target: 'B' }];

    const sonuc = ustSutunlariBul('B', dugumler, kenarlar);
    expect(sonuc).toEqual(['ust']);
  });

  it('birden çok girişli düğüm — bir kaynak kabul', () => {
    // A(['a']) → C, B(['b']) → C; sonuc a veya b
    const dugumler: DugumOzeti[] = [
      { id: 'A', sonucSutunlari: ['a'] },
      { id: 'B', sonucSutunlari: ['b'] },
      { id: 'C' },
    ];
    const kenarlar: KenarOzeti[] = [
      { source: 'A', target: 'C' },
      { source: 'B', target: 'C' },
    ];

    const sonuc = ustSutunlariBul('C', dugumler, kenarlar);
    expect(['a', 'b']).toContain(sonuc[0]);
    expect(sonuc.length).toBeGreaterThan(0);
  });
});

describe('sutunlariSirala', () => {
  it('ipucu null ise sıra değişmez', () => {
    const sutunlar = ['Suc', 'Olay ili', 'Tarih'];
    const sonuc = sutunlariSirala(sutunlar, null);
    expect(sonuc).toEqual(sutunlar);
  });

  it("ipucu 'lat' ise enlem/lat içeren sütunlar BAŞA gelir", () => {
    const sutunlar = ['Olay ili', 'Koordinat Enlem', 'Suc'];
    const sonuc = sutunlariSirala(sutunlar, 'lat');
    expect(sonuc[0]).toBe('Koordinat Enlem');
  });

  it("ipucu 'lng' ise boylam içeren başa gelir", () => {
    const sutunlar = ['Olay ili', 'Koordinat Boylam', 'Suc'];
    const sonuc = sutunlariSirala(sutunlar, 'lng');
    expect(sonuc[0]).toBe('Koordinat Boylam');
  });

  it('eşleşme yoksa dizi aynen döner', () => {
    const sutunlar = ['Suc', 'Olay ili', 'Tarih'];
    const sonuc = sutunlariSirala(sutunlar, 'lat');
    expect(sonuc).toEqual(sutunlar);
    expect(sonuc.length).toBe(sutunlar.length);
  });
});
