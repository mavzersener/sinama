// Senaryo 1 — Açılış: uygulama yükleniyor mu, temel yüzey yerinde mi.
import { test, expect } from '@playwright/test';
import { konsolHatalari, demoYukle, nodeSayisi } from './yardimcilar';

test.describe('Açılış', () => {
  test('uygulama konsol hatası olmadan yüklenir', async ({ page }) => {
    const hatalar = konsolHatalari(page);
    await page.goto('/');
    await expect(page.locator('.react-flow')).toBeVisible();
    // Ağ kaynaklı 401'ler beklenen (oturum yok); yalnız kod hatalarına bak.
    const kodHatalari = hatalar.filter(
      (h) => !/401|Unauthorized|Failed to fetch|net::/i.test(h),
    );
    expect(kodHatalari, `Konsol hataları:\n${kodHatalari.join('\n')}`).toEqual([]);
  });

  test('araç çubuğu ve düğüm paneli görünür', async ({ page }) => {
    await page.goto('/');
    for (const ad of ['Run', 'Demo', 'Rehberli Mod', 'Akademik Mod']) {
      await expect(
        page.getByRole('button', { name: ad, exact: true }),
        `"${ad}" düğmesi yok`,
      ).toBeVisible();
    }
  });

  test('Demo grafı düğümleri tuvale çizer', async ({ page }) => {
    await page.goto('/');
    await demoYukle(page);
    expect(await nodeSayisi(page)).toBeGreaterThan(1);
  });

  test('düğümler ÖLÇÜLÜR ve görünür olur', async ({ page }) => {
    // React Flow düğümü ölçene kadar visibility:hidden tutar. Ölçüm
    // tetiklenmezse hiçbir tıklama isabet etmez — bu testin varlık sebebi.
    await page.goto('/');
    await demoYukle(page);
    const gizli = await page.locator('.react-flow__node').evaluateAll(
      (els) => els.filter((e) => getComputedStyle(e).visibility === 'hidden').length,
    );
    expect(gizli, 'ölçülmemiş (görünmez) düğüm var').toBe(0);
  });
});
