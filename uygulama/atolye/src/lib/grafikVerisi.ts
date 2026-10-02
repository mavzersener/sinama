// Grafik düğümü için veri şekillendirme (saf; ResultsPanel.ChartView kullanır).
//
// Eski ChartView GERÇEK veriden bağımsız çizim yapıyordu: pasta grafiği her
// zaman sabit A–E (35/25/20/15/5), dağılım grafiği her zaman Math.random()
// noktaları, veri yoksa uydurma "A–F" çubukları gösteriyordu; xColumn/yColumn
// yapılandırması yok sayılıyordu. Buradaki kural: veri yoksa ya da grafik
// türü veriye uymuyorsa ÇİZİLMEZ, sebebi söylenir. Uydurma veri yok.

import { eksikMi, sayiCoz, sayisalSutunlar } from '../engine/istatistik';

export type GrafikTipi = 'bar' | 'line' | 'area' | 'pie' | 'scatter';

export interface GrafikVerisi {
  tip: GrafikTipi;
  veri: Array<Record<string, string | number | null>>;
  /** Kategori ekseni (bar/line/area/pie) ya da x (scatter). */
  xAnahtar: string;
  yAnahtarlar: string[];
  uyarilar: string[];
}

export const GRAFIK_AZAMI_SATIR = 200;
const PASTA_AZAMI_DILIM = 12;

export function grafikVerisi(
  satirlar: Record<string, unknown>[],
  config: Record<string, unknown>,
  toplamSatir?: number,
): GrafikVerisi | { hata: string } {
  if (!satirlar.length) return { hata: 'Grafik için veri yok — düğümü bir veri kaynağına bağlayıp çalıştırın.' };
  const uyarilar: string[] = [];
  let tip = String(config.chartType || 'bar') as GrafikTipi | 'heatmap';
  if (tip === 'heatmap') {
    uyarilar.push('Isı haritası henüz desteklenmiyor; çubuk grafik gösteriliyor.');
    tip = 'bar';
  }
  const toplam = toplamSatir ?? satirlar.length;
  const kullan = satirlar.slice(0, GRAFIK_AZAMI_SATIR);
  if (toplam > kullan.length) uyarilar.push(`İlk ${kullan.length} / ${toplam} satır çizildi.`);

  const sutunlar = Object.keys(satirlar[0]);
  const sayisal = sayisalSutunlar(kullan, sutunlar);
  const secX = String(config.xColumn || '').trim();
  const secY = String(config.yColumn || '').trim();
  if (secX && !sutunlar.includes(secX)) return { hata: `X sütunu bulunamadı: ${secX}` };
  if (secY && !sutunlar.includes(secY)) return { hata: `Y sütunu bulunamadı: ${secY}` };
  if (secY && !sayisal.includes(secY)) return { hata: `Y sütunu sayısal değil: ${secY}` };

  if (tip === 'scatter') {
    const x = secX || sayisal[0];
    const y = secY || sayisal.find((s) => s !== x);
    if (!x || !y || !sayisal.includes(x)) return { hata: 'Dağılım grafiği iki sayısal sütun ister (X ve Y).' };
    const veri = kullan
      .map((r) => ({ [x]: sayiCoz(r[x]), [y]: sayiCoz(r[y]) }))
      .filter((p) => p[x] !== null && p[y] !== null);
    if (veri.length < kullan.length) uyarilar.push(`${kullan.length - veri.length} satır boş/sayısal olmayan değer yüzünden çizilmedi.`);
    return { tip, veri, xAnahtar: x, yAnahtarlar: [y], uyarilar };
  }

  const x = secX || sutunlar.find((s) => !sayisal.includes(s)) || '';
  const yler = secY ? [secY] : sayisal.filter((s) => s !== x).slice(0, 3);
  if (!yler.length) return { hata: 'Çizilecek sayısal sütun yok (Y sütunu seçin).' };
  const etiket = (r: Record<string, unknown>, i: number) => (x && !eksikMi(r[x]) ? String(r[x]) : `Satır ${i + 1}`);

  if (tip === 'pie') {
    const y = yler[0];
    const dilimler = kullan
      .map((r, i) => ({ ad: etiket(r, i), deger: sayiCoz(r[y]) }))
      .filter((d): d is { ad: string; deger: number } => d.deger !== null && d.deger > 0);
    if (!dilimler.length) return { hata: `Pasta grafiği pozitif değer ister ("${y}" sütununda yok).` };
    if (dilimler.length > PASTA_AZAMI_DILIM) uyarilar.push(`Pasta grafiği ilk ${PASTA_AZAMI_DILIM} dilimi gösteriyor (${dilimler.length} değer var).`);
    return {
      tip,
      veri: dilimler.slice(0, PASTA_AZAMI_DILIM).map((d) => ({ ad: d.ad, [y]: d.deger })),
      xAnahtar: 'ad',
      yAnahtarlar: [y],
      uyarilar,
    };
  }

  return {
    tip,
    veri: kullan.map((r, i) => ({
      [x || 'satir']: etiket(r, i),
      ...Object.fromEntries(yler.map((y) => [y, sayiCoz(r[y])])),
    })),
    xAnahtar: x || 'satir',
    yAnahtarlar: yler,
    uyarilar,
  };
}
