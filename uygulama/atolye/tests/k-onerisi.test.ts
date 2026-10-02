import { describe, it, expect } from 'vitest';
import { kOner, recommendAnalyses } from '../src/engine/recommendations';

/**
 * Kullanıcı geri bildirimi (feedback tablosu, 3 Tem 2026): "K degeri hep 3
 * oneriliyor, veriye gore degismeli". Öneri artık K'yı veriden seçer.
 */

/** Belirgin, belirlenimci kümeler: merkezler çember üzerinde, küçük sapma. */
function kumeler(k: number, n = 60): Record<string, unknown>[] {
  const satirlar: Record<string, unknown>[] = [];
  let t = 1;
  const r = () => { t = (t * 16807) % 2147483647; return (t / 2147483647) - 0.5; };
  for (let c = 0; c < k; c++) {
    // 45° kaydırma: iki boyut da bilgi taşır (k=2'de merkezler x ekseninde olsaydı
    // y salt gürültü olur, düğümün varsayılan standartlaştırması onu büyütürdü).
    const aci = (2 * Math.PI * c) / k + Math.PI / 4;
    const [mx, my] = [Math.cos(aci) * 20, Math.sin(aci) * 20];
    for (let i = 0; i < n; i++) satirlar.push({ x: mx + r() * 2, y: my + r() * 2, etiket: `c${c}` });
  }
  return satirlar;
}

describe('kOner', () => {
  it.each([2, 4, 5])('belirgin %i küme → K=%i', (k) => {
    const o = kOner(kumeler(k), ['x', 'y']);
    expect(o.k).toBe(k);
    expect(o.skor!).toBeGreaterThan(0.7);
  });

  it('belirlenimci: aynı veri her seferinde aynı öneri', () => {
    const v = kumeler(4, 200); // 800 satır → 400'lük örneklem
    expect(kOner(v, ['x', 'y'])).toEqual(kOner(v, ['x', 'y']));
  });

  it('az ya da eksik satır: varsayılan K=3, skor yok', () => {
    expect(kOner([{ x: 1, y: 2 }, { x: 2, y: 3 }], ['x', 'y'])).toEqual({ k: 3, skor: null, kMaks: 0 });
    expect(kOner(Array.from({ length: 20 }, () => ({ x: '', y: null })), ['x', 'y']).skor).toBeNull();
  });

  it('öneri kartı veriden seçilen K\'yı ve gerekçesini taşır', () => {
    const recs = recommendAnalyses(['x', 'y', 'etiket'], kumeler(5));
    const km = recs.find((r) => r.nodeType === 'clustering')!;
    expect(km.config.k).toBe(5);
    expect(km.reason).toMatch(/K=5 chosen from the data \(best silhouette 0\.\d\d among K=2–8\)/);
  });
});
