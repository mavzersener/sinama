// Senaryo 2 — Düğüm bağlama: kullanıcının bildirdiği sorunun testi.
//
// Bu dosya "bağlanmıyor" demekle yetinmez; bağlanmıyorsa NEDENİNİ ölçer.
// Handle görünmez mi, kırpılmış mı, üstü kapalı mı — her biri ayrı düzeltme.
import { test, expect } from '@playwright/test';
import { demoYukle, handleTani, baglantiKur, kenarSayisi } from './yardimcilar';

test.describe('Düğüm bağlama', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await demoYukle(page);
  });

  test('her düğümde çıkış ve giriş handle-ı bulunur', async ({ page }) => {
    const cikis = await page.locator('.react-flow__handle-right').count();
    const giris = await page.locator('.react-flow__handle-left').count();
    expect(cikis, 'çıkış handle-ı yok').toBeGreaterThan(0);
    expect(giris, 'giriş handle-ı yok').toBeGreaterThan(0);
  });

  test('çıkış handle-ı tıklanabilir (kırpılmamış, görünür)', async ({ page }) => {
    const handle = page.locator('.react-flow__node').first()
      .locator('.react-flow__handle-right');
    const tani = await handleTani(handle);
    expect(
      tani.teshis,
      `ÇIKIŞ HANDLE TEŞHİSİ\n${JSON.stringify(tani, null, 2)}`,
    ).toBe('Handle tıklanabilir görünüyor.');
  });

  test('giriş handle-ı tıklanabilir (kırpılmamış, görünür)', async ({ page }) => {
    const handle = page.locator('.react-flow__node').nth(1)
      .locator('.react-flow__handle-left');
    const tani = await handleTani(handle);
    expect(
      tani.teshis,
      `GİRİŞ HANDLE TEŞHİSİ\n${JSON.stringify(tani, null, 2)}`,
    ).toBe('Handle tıklanabilir görünüyor.');
  });

  test('handle tutulabilir alanı en az 8px olmalı', async ({ page }) => {
    // Kırpılma tutulabilir alanı yarıya indirir; 8px altı pratikte
    // "bağlayamıyorum" demektir.
    const handle = page.locator('.react-flow__node').first()
      .locator('.react-flow__handle-right');
    const tani = await handleTani(handle);
    expect(
      tani.tutulabilirPx,
      `Tutulabilir genişlik ${tani.tutulabilirPx}px (kutu ${tani.kutu?.w}px, ` +
        `taşma ${tani.tasmaPx}px, ebeveyn overflow=${tani.ebeveynOverflow})`,
    ).toBeGreaterThanOrEqual(8);
  });

  test('iki düğüm fare sürüklemesiyle BAĞLANIR', async ({ page }) => {
    const once = await kenarSayisi(page);
    const sonuc = await baglantiKur(page, 0, 1);
    expect(
      sonuc.basarili,
      `Bağlantı kurulamadı (${sonuc.sebep}). Kenar: ${once} → ${sonuc.sonrakiKenar}`,
    ).toBe(true);
  });

  test('bağlantı kurulduktan sonra kenar tuvalde çizilir', async ({ page }) => {
    await baglantiKur(page, 0, 1);
    const yollar = await page.locator('.react-flow__edge-path').count();
    expect(yollar, 'kenar yolu (path) çizilmemiş').toBeGreaterThan(0);
  });
});
