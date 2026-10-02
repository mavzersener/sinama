// Arayüz testleri için ortak yardımcılar ve TEŞHİS araçları.
//
// Buradaki asıl değer `handleTani`: bir bağlantı kurulamadığında "kurulamadı"
// demek yetmez, NEDEN kurulamadığını söylemek gerekir. Görünmez mi, kırpılmış
// mı, üstünü başka eleman mı kapatıyor — hepsi ayrı bir düzeltme demektir.

import { expect, type Locator, type Page } from '@playwright/test';

/** Bir handle'ın tıklanabilirliğini engelleyen olası nedenler. */
export interface HandleTanisi {
  bulundu: boolean;
  gorunurluk: string;
  goster: string;
  isaretciOlaylari: string;
  /** Elemanın kutusu (viewport koordinatı). */
  kutu: { x: number; y: number; w: number; h: number } | null;
  /** Ebeveynin overflow değeri — 'hidden' ise taşan kısım KIRPILIR. */
  ebeveynOverflow: string;
  /** Handle ebeveyn kutusunun dışına ne kadar taşıyor (px). */
  tasmaPx: number;
  /**
   * Fareyle gerçekten tutulabilen genişlik (px, ekran ölçeğinde).
   *
   * Taşma YALNIZCA ebeveyn kırpıyorsa alanı azaltır; kırpmıyorsa handle
   * kutusunun tamamı tutulabilir. Bu ayrım önemli: "dışarı taşıyor" tek
   * başına sorun değildir, "taşıyor VE kırpılıyor" sorundur.
   */
  tutulabilirPx: number;
  /** Merkezinde gerçekten handle mı var (elementFromPoint). */
  merkezIsabet: boolean;
  /** Merkeze isabet eden elemanın sınıfı — engeli teşhis eder. */
  merkezdeki: string | null;
  /** İnsan okuyabilir teşhis. */
  teshis: string;
}

/**
 * Handle'ın neden tıklanamadığını ölçer.
 *
 * Sırayla bakar: eleman var mı → görünür mü → isaretci olayları açık mı →
 * ebeveyn kırpıyor mu → merkezine gerçekten isabet ediliyor mu.
 */
export async function handleTani(handle: Locator): Promise<HandleTanisi> {
  const sayi = await handle.count();
  if (sayi === 0) {
    return {
      bulundu: false, gorunurluk: '-', goster: '-', isaretciOlaylari: '-',
      kutu: null, ebeveynOverflow: '-', tasmaPx: 0, tutulabilirPx: 0,
      merkezIsabet: false, merkezdeki: null,
      teshis: 'Handle DOM içinde yok — CustomNode bu düğüm türü için handle çizmiyor olabilir.',
    };
  }

  return handle.evaluate((el) => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const ebeveyn = el.parentElement;
    const ecs = ebeveyn ? getComputedStyle(ebeveyn) : null;
    const er = ebeveyn ? ebeveyn.getBoundingClientRect() : null;

    // Handle ebeveyn kutusunun dışına ne kadar taşıyor?
    let tasma = 0;
    if (er) {
      tasma = Math.max(
        0,
        er.left - r.left,
        r.right - er.right,
        er.top - r.top,
        r.bottom - er.bottom,
      );
    }

    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const isabet = document.elementFromPoint(cx, cy);
    const sinif = isabet
      ? (isabet.className?.baseVal ?? isabet.className ?? isabet.tagName).toString().slice(0, 60)
      : null;

    const ebeveynOverflow = ecs?.overflow ?? '-';
    const kirpiliyor = ebeveynOverflow === 'hidden' || ebeveynOverflow === 'clip';
    const tutulabilir = kirpiliyor ? Math.max(0, r.width - tasma) : r.width;
    const merkezIsabet = isabet === el || !!isabet?.classList?.contains('react-flow__handle');

    let teshis: string;
    if (cs.visibility === 'hidden') {
      teshis =
        'Handle GÖRÜNMEZ (visibility:hidden) — görünmez elemanlar tıklanamaz. ' +
        'React Flow düğümü ölçmediyse bunu kendisi uygular.';
    } else if (cs.display === 'none') {
      teshis = 'Handle çizilmiyor (display:none).';
    } else if (cs.pointerEvents === 'none') {
      teshis = 'Handle isaretci olaylarını almıyor (pointer-events:none).';
    } else if (r.width === 0 || r.height === 0) {
      teshis = 'Handle sıfır boyutlu — tutulabilir alan yok.';
    } else if (kirpiliyor && tasma > 0) {
      teshis =
        `Handle ebeveyn kutusundan ${tasma.toFixed(1)}px taşıyor ve ebeveynde ` +
        'overflow:hidden var → taşan kısım KIRPILIYOR, tutulabilir alan daralıyor.';
    } else if (!merkezIsabet) {
      teshis = `Handle merkezine başka eleman isabet ediyor: ${sinif}`;
    } else {
      teshis = 'Handle tıklanabilir görünüyor.';
    }

    return {
      bulundu: true,
      gorunurluk: cs.visibility,
      goster: cs.display,
      isaretciOlaylari: cs.pointerEvents,
      kutu: { x: +r.left.toFixed(1), y: +r.top.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1) },
      ebeveynOverflow,
      tasmaPx: +tasma.toFixed(1),
      tutulabilirPx: +tutulabilir.toFixed(1),
      merkezIsabet,
      merkezdeki: sinif,
      teshis,
    };
  });
}

/** Tuvale örnek graf yükler (Demo düğmesi) ve düğümlerin çizilmesini bekler. */
export async function demoYukle(page: Page) {
  await page.getByRole('button', { name: 'Demo' }).click();
  await expect(page.locator('.react-flow__node').first()).toBeVisible();
}

/** Tuvaldeki düğüm sayısı. */
export const nodeSayisi = (page: Page) => page.locator('.react-flow__node').count();

/** Tuvaldeki kenar (bağlantı) sayısı. */
export const kenarSayisi = (page: Page) => page.locator('.react-flow__edge').count();

/**
 * İki düğüm arasında GERÇEK fare sürüklemesiyle bağlantı kurmayı dener.
 *
 * React Flow bağlantıyı isaretci olaylarıyla kurar: handle üzerinde basılı
 * tut → birkaç adımda hareket ettir → hedef handle üzerinde bırak. Tek adımlı
 * `dragTo` React Flow'da güvenilir değildir; bu yüzden elle adımlanır.
 */
export async function baglantiKur(page: Page, kaynakIdx: number, hedefIdx: number) {
  const kaynak = page.locator('.react-flow__node').nth(kaynakIdx)
    .locator('.react-flow__handle-right');
  const hedef = page.locator('.react-flow__node').nth(hedefIdx)
    .locator('.react-flow__handle-left');

  const kk = await kaynak.boundingBox();
  const hk = await hedef.boundingBox();
  if (!kk || !hk) return { basarili: false, sebep: 'handle kutusu ölçülemedi' };

  const x1 = kk.x + kk.width / 2;
  const y1 = kk.y + kk.height / 2;
  const x2 = hk.x + hk.width / 2;
  const y2 = hk.y + hk.height / 2;

  const oncekiKenar = await kenarSayisi(page);

  await page.mouse.move(x1, y1);
  await page.mouse.down();
  // Ara adımlar: React Flow bağlantı çizgisini hareket olaylarıyla sürdürür.
  for (let i = 1; i <= 8; i++) {
    await page.mouse.move(x1 + ((x2 - x1) * i) / 8, y1 + ((y2 - y1) * i) / 8);
  }
  await page.mouse.up();
  await page.waitForTimeout(300);

  const sonrakiKenar = await kenarSayisi(page);
  return {
    basarili: sonrakiKenar > oncekiKenar,
    oncekiKenar,
    sonrakiKenar,
    sebep: sonrakiKenar > oncekiKenar ? '' : 'kenar sayısı artmadı',
  };
}

/** Sayfadaki konsol hatalarını toplar (test boyunca biriktirir). */
export function konsolHatalari(page: Page): string[] {
  const hatalar: string[] = [];
  page.on('console', (m) => {
    if (m.type() === 'error') hatalar.push(m.text());
  });
  page.on('pageerror', (e) => hatalar.push(`pageerror: ${e.message}`));
  return hatalar;
}
