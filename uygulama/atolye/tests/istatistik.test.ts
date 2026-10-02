import { describe, it, expect } from 'vitest';
import {
  eksikMi, sayiCoz, sayisalSutunlar, sutunDegerleri, tamKayitlar, stdSapma, kantil, medyan,
  enKucukBuyuk, pearson, spearman, kendallTauB, ols, r2Hesapla, tohumluUretec, karistir,
  standartlastir, kMeans, silhouette,
} from '../src/engine/istatistik';

/**
 * Saf istatistik çekirdeği. Altın değerler scipy 1.x / scikit-learn 1.5 ile
 * üretildi (mlservice ortamı, 24 Eyl 2026) — elle hesaplanmadı.
 */

describe('sayı çözücü ve eksik tanımı', () => {
  it('null/boş/boolean/Date sayı DEĞİL (Number(null)===0 tuzağı)', () => {
    for (const v of [null, undefined, '', '   ', true, false, new Date(), {}, [], NaN, Infinity]) {
      expect(sayiCoz(v)).toBeNull();
    }
    expect(sayiCoz(0)).toBe(0);
    expect(sayiCoz('0')).toBe(0);
    expect(sayiCoz(' 12.5 ')).toBe(12.5);
    expect(sayiCoz('37,58')).toBeCloseTo(37.58);
    expect(sayiCoz('1,234,567')).toBeNull();
  });

  it('eksikMi yalnız boşluktan ibaret metni de eksik sayar; 0 eksik değildir', () => {
    expect(eksikMi('  ')).toBe(true);
    expect(eksikMi(null)).toBe(true);
    expect(eksikMi(0)).toBe(false);
    expect(eksikMi('0')).toBe(false);
  });

  it('sayısal sütun tespiti ilk satıra değil TÜM dolu hücrelere bakar', () => {
    const satirlar = [
      { a: null, b: 'x', c: 1, d: true },
      { a: 2, b: 'y', c: '3,5', d: false },
      { a: 3, b: 'z', c: '', d: true },
    ];
    // a: ilk hücre boş ama sayısal (eski motor düşürüyordu); d: boolean sayısal değil
    expect(sayisalSutunlar(satirlar, ['a', 'b', 'c', 'd'])).toEqual(['a', 'c']);
    expect(sayisalSutunlar([{ e: null }, { e: '' }], ['e'])).toEqual([]);
  });

  it('sutunDegerleri eksik ve geçersiz hücreleri ayrı sayar', () => {
    const r = sutunDegerleri([{ x: 1 }, { x: null }, { x: 'abc' }, { x: '2' }], 'x');
    expect(r).toEqual({ degerler: [1, 2], eksik: 1, gecersiz: 1 });
  });

  it('tamKayitlar satır hizasını korur (değişkenler ayrı süzülmez)', () => {
    const r = tamKayitlar([{ x: 1, y: 2 }, { x: 2, y: null }, { x: null, y: 8 }, { x: 5, y: 10 }], ['x', 'y']);
    expect(r.matris).toEqual([[1, 2], [5, 10]]);
    expect(r.satirIdx).toEqual([0, 3]);
    expect(r.dislanan).toBe(2);
  });
});

describe('betimsel', () => {
  it('medyan çift n\'de iki ortanın ortalaması (numpy: 2.5)', () => {
    expect(medyan([4, 1, 3, 2])).toBe(2.5);
  });
  it('doğrusal kantil (numpy: q25=3.25)', () => {
    expect(kantil([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.25)).toBeCloseTo(3.25, 12);
  });
  it('örneklem std ddof=1 (numpy: 2.1380899353); n<=ddof → null', () => {
    expect(stdSapma([2, 4, 4, 4, 5, 5, 7, 9], 1)).toBeCloseTo(2.1380899353, 9);
    expect(stdSapma([5], 1)).toBeNull();
  });
  it('enKucukBuyuk büyük dizide yığın taşırmaz (Math.max(...x) taşırdı)', () => {
    const buyuk = Array.from({ length: 300_000 }, (_, i) => i);
    expect(enKucukBuyuk(buyuk)).toEqual({ min: 0, max: 299_999 });
  });
});

describe('korelasyon (scipy altın değerleri)', () => {
  const x = [1, 2, 3, 4, 5, 6, 7, 8];
  const y = [2, 1, 4, 3, 6, 5, 8, 7];
  it('bağsız veri', () => {
    expect(pearson(x, y)).toBeCloseTo(0.9047619048, 9);
    expect(spearman(x, y)).toBeCloseTo(0.9047619048, 9);
    expect(kendallTauB(x, y)).toBeCloseTo(0.7142857143, 9);
  });
  it('bağlı veri: Kendall tau-b (eski motor tau-a + çift bağı uyumlu sayıyordu)', () => {
    const tx = [1, 1, 2, 2, 3, 3];
    const ty = [1, 2, 1, 2, 3, 3];
    expect(kendallTauB(tx, ty)).toBeCloseTo(0.6666666667, 9);
    expect(spearman(tx, ty)).toBeCloseTo(0.75, 9);
    expect(pearson(tx, ty)).toBeCloseTo(0.75, 9);
  });
  it('tanımsız durum null döner, 0 değil', () => {
    expect(pearson([1], [2])).toBeNull();
    expect(pearson([3, 3, 3], [1, 2, 3])).toBeNull();
    expect(kendallTauB([1, 1], [1, 2])).toBeNull();
  });
});

describe('OLS (sklearn LinearRegression altın değerleri)', () => {
  const X = [[1, 2], [2, 1], [3, 4], [4, 3], [5, 6], [6, 5], [7, 9], [8, 7]];
  const y = [9.1, 7.8, 19.05, 18.3, 28.9, 28.2, 41.85, 38.05];
  it('çok değişkenli katsayılar, kesişim, R², MSE', () => {
    const m = ols(X, y);
    expect(m.katsayilar[0]).toBeCloseTo(2.0557343234, 8);
    expect(m.katsayilar[1]).toBeCloseTo(2.9415841584, 8);
    expect(m.kesisim).toBeCloseTo(1.0506188119, 8);
    expect(m.r2).toBeCloseTo(0.9998428225, 9);
    expect(m.mse).toBeCloseTo(0.0215931828, 9);
    expect(m.n).toBe(8);
  });
  it('sabit ya da doğrusal bağımlı özellik sessizce yanlış katsayı değil hata üretir', () => {
    expect(() => ols(X.map((r) => [r[0], 2 * r[0]]), y)).toThrow(/doğrusal bağımlı/);
    expect(() => ols(X.map((r) => [r[0], 5]), y)).toThrow(/doğrusal bağımlı/);
    expect(() => ols([[1, 2], [2, 3]], [1, 2])).toThrow(/en az 3/);
  });
  it('R² sabit hedefte sklearn force_finite gibi davranır', () => {
    expect(r2Hesapla(0, 0)).toBe(1);
    expect(r2Hesapla(5, 0)).toBe(0);
  });
});

describe('tohumlu rastgelelik', () => {
  it('aynı tohum → aynı dizi; farklı tohum → farklı', () => {
    const a = tohumluUretec(42);
    const b = tohumluUretec(42);
    const c = tohumluUretec(7);
    const da = [a(), a(), a()];
    expect([b(), b(), b()]).toEqual(da);
    expect([c(), c(), c()]).not.toEqual(da);
    expect(da.every((v) => v >= 0 && v < 1)).toBe(true);
  });
  it('karıştırma permütasyondur ve tekrarlanabilir', () => {
    const x = Array.from({ length: 20 }, (_, i) => i);
    const k1 = karistir(x, tohumluUretec(1));
    expect([...k1].sort((p, q) => p - q)).toEqual(x);
    expect(karistir(x, tohumluUretec(1))).toEqual(k1);
  });
});

describe('kümeleme', () => {
  it('silhouette sklearn ile aynı; tek elemanlı küme s=0 (sklearn: 0.8034927455)', () => {
    const P = [[0, 0], [0, 1], [1, 0], [1, 1], [10, 10], [10, 11], [11, 10], [30, 30]];
    const L = [0, 0, 0, 0, 1, 1, 1, 2];
    expect(silhouette(P, L).skor).toBeCloseTo(0.8034927455, 9);
  });
  it('silhouette: tek küme ya da n küme → null; özdeş noktalar NaN değil', () => {
    expect(silhouette([[0], [1], [2]], [0, 0, 0]).skor).toBeNull();
    expect(silhouette([[0], [1], [2]], [0, 1, 2]).skor).toBeNull();
    expect(Number.isNaN(silhouette([[0], [0], [5], [5]], [0, 0, 1, 1]).skor)).toBe(false);
  });
  it('K-Means ayrık kümeleri bulur, tekrarlanabilir, büyükten küçüğe numaralar', () => {
    const X = [
      ...Array.from({ length: 12 }, (_, i) => [i % 3, Math.floor(i / 3) % 2]),
      ...Array.from({ length: 7 }, (_, i) => [50 + (i % 2), 50 + (i % 3)]),
      ...Array.from({ length: 4 }, (_, i) => [100 + (i % 2), i % 2]),
    ];
    const a = kMeans(X, 3, { tohum: 3 });
    const b = kMeans(X, 3, { tohum: 3 });
    expect(a).toEqual(b);
    const boyut = [0, 0, 0];
    a.etiketler.forEach((e) => { boyut[e]++; });
    expect(boyut).toEqual([12, 7, 4]);
  });
  it('standartlaştırma sabit sütunda 0\'a bölmez', () => {
    const { Z, olcek } = standartlastir([[1, 5], [3, 5], [5, 5]]);
    expect(olcek[1]).toBe(1);
    expect(Z.map((r) => r[1])).toEqual([0, 0, 0]);
    expect(Z.map((r) => r[0])[1]).toBe(0);
  });
});
