import { describe, it, expect } from 'vitest';
import { grafikVerisi, GRAFIK_AZAMI_SATIR, type GrafikVerisi } from '../src/lib/grafikVerisi';

/**
 * Grafik düğümü eskiden GERÇEK veriden bağımsız çiziyordu: pasta her zaman
 * sabit A–E (35/25/20/15/5), dağılım her zaman Math.random(), veri yoksa
 * uydurma A–F çubukları; xColumn/yColumn yok sayılıyordu.
 */

const il = [
  { il: 'Antalya', olay: 433, zarar: 1.5 },
  { il: 'Adana', olay: 532, zarar: null },
  { il: 'İstanbul', olay: 727, zarar: 3.1 },
];

const ok = (g: ReturnType<typeof grafikVerisi>): GrafikVerisi => {
  if ('hata' in g) throw new Error(g.hata);
  return g;
};

describe('grafikVerisi — uydurma veri yok', () => {
  it('veri yoksa çizmez, sebebini söyler (eski: sahte A–F)', () => {
    expect(grafikVerisi([], { chartType: 'bar' })).toEqual({ hata: expect.stringMatching(/veri yok/) });
  });

  it('pasta GERÇEK değerlerden (eski: sabit 35/25/20/15/5)', () => {
    const g = ok(grafikVerisi(il, { chartType: 'pie', xColumn: 'il', yColumn: 'olay' }));
    expect(g.veri).toEqual([
      { ad: 'Antalya', olay: 433 }, { ad: 'Adana', olay: 532 }, { ad: 'İstanbul', olay: 727 },
    ]);
  });

  it('dağılım GERÇEK sütunlardan, boş hücre çizilmez ve söylenir (eski: Math.random)', () => {
    const g = ok(grafikVerisi(il, { chartType: 'scatter', xColumn: 'olay', yColumn: 'zarar' }));
    expect(g.veri).toEqual([{ olay: 433, zarar: 1.5 }, { olay: 727, zarar: 3.1 }]);
    expect(g.uyarilar.join(' ')).toMatch(/1 satır/);
  });

  it('dağılım iki sayısal sütun yoksa çizilmez', () => {
    expect(grafikVerisi([{ a: 'x', b: 1 }], { chartType: 'scatter' })).toEqual({ hata: expect.stringMatching(/iki sayısal/) });
  });

  it('xColumn/yColumn yapılandırması uygulanır; boşsa ilk metin + ilk sayısallar', () => {
    const secili = ok(grafikVerisi(il, { chartType: 'bar', xColumn: 'il', yColumn: 'zarar' }));
    expect(secili.xAnahtar).toBe('il');
    expect(secili.yAnahtarlar).toEqual(['zarar']);
    expect(secili.veri[1]).toEqual({ il: 'Adana', zarar: null });
    const oto = ok(grafikVerisi(il, { chartType: 'line' }));
    expect(oto.xAnahtar).toBe('il');
    expect(oto.yAnahtarlar).toEqual(['olay', 'zarar']);
  });

  it('geçersiz sütun seçimi hata verir', () => {
    expect(grafikVerisi(il, { yColumn: 'yok' })).toEqual({ hata: expect.stringMatching(/bulunamadı/) });
    expect(grafikVerisi(il, { yColumn: 'il' })).toEqual({ hata: expect.stringMatching(/sayısal değil/) });
  });

  it('heatmap desteklenmiyor: çubuğa düşer ve söyler', () => {
    const g = ok(grafikVerisi(il, { chartType: 'heatmap' }));
    expect(g.tip).toBe('bar');
    expect(g.uyarilar.join(' ')).toMatch(/Isı haritası/);
  });

  it('kesilme görünür', () => {
    const cok = Array.from({ length: GRAFIK_AZAMI_SATIR + 50 }, (_, i) => ({ k: `k${i}`, v: i }));
    const g = ok(grafikVerisi(cok, { chartType: 'bar' }, 1000));
    expect(g.veri).toHaveLength(GRAFIK_AZAMI_SATIR);
    expect(g.uyarilar.join(' ')).toMatch(new RegExp(`İlk ${GRAFIK_AZAMI_SATIR} / 1000`));
  });
});
