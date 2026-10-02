// Senaryo 3 — Rehberli Mod ve Akademik Mod: açılış, kapanış, ön-kayıt kapısı.
//
// Bu testler backend/oturum GEREKTİRMEZ: yalnız arayüzün kendi mantığını
// (kapı sırası, devir, motor-kapalı davranışı) sınar. Motorla konuşan yollar
// science_gpt tarafındaki uçtan uca betiklerle ayrıca kanıtlanır.
import { test, expect } from '@playwright/test';

test.describe('Rehberli Mod', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Rehberli Mod' }).click();
  });

  test('açılır ve kapanır', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Rehberli Mod' });
    await expect(kapak).toBeVisible();
    await kapak.getByRole('button', { name: 'Kapat' }).click();
    await expect(kapak).toBeHidden();
  });

  test('ön-kayıt kapısı işaretlenmeden devir düğmesi ÇIKMAZ', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Rehberli Mod' });
    await expect(kapak.getByRole('button', { name: /Akademik Mod'a geç/ })).toHaveCount(0);
  });

  test('işaretlenince devir düğmesi ve sıra uyarısı çıkar', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Rehberli Mod' });
    await kapak.locator('input[type=checkbox]').check();
    await expect(kapak.getByRole('button', { name: /Akademik Mod'a geç/ })).toBeVisible();
    // Veri yüklenmemişken sıranın korunduğu söylenmeli (HARKing uyarısı).
    await expect(kapak.getByText(/veri yüklenmeden önce/)).toBeVisible();
  });

  test('devir Akademik Mod-u açar ve Rehberli Mod-u kapatır', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Rehberli Mod' });
    await kapak.getByRole('textbox').first().fill('Köy düzeyinde olay yoğunluğu nerede toplanıyor');
    await kapak.locator('input[type=checkbox]').check();
    await kapak.getByRole('button', { name: /Akademik Mod'a geç/ }).click();

    await expect(page.getByRole('dialog', { name: 'Rehberli Mod' })).toBeHidden();
    await expect(page.getByRole('dialog', { name: 'Akademik Mod' })).toBeVisible();
  });
});

test.describe('Akademik Mod', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Akademik Mod' }).click();
  });

  test('sekiz adımlı şerit çizilir', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Akademik Mod' });
    for (const ad of ['Protokol', 'Ön-kayıt kilidi', 'Veri', 'Şema onayı',
      'Yöntem önerisi', 'Yürütme', 'Doğrulama', 'Kanıt + makale']) {
      await expect(kapak.getByText(ad, { exact: false }).first(),
        `"${ad}" adımı şeritte yok`).toBeVisible();
    }
  });

  test('motor kapalıyken durum AÇIKÇA bildirilir (sessiz düşme yok)', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Akademik Mod' });
    // Oturum yoksa proxy 401 verir; arayüz bunu "motor kapalı" olarak
    // göstermeli, sessizce başarılı gibi davranmamalı.
    await expect(kapak.getByText(/motor kapalı/)).toBeVisible();
  });

  test('protokol metni kısayken üretim düğmesi kapalıdır', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Akademik Mod' });
    const dugme = kapak.getByRole('button', { name: /Protokol taslağı üret/ });
    await expect(dugme).toBeDisabled();
    await kapak.getByRole('textbox').first().fill('kısa');
    await expect(dugme).toBeDisabled();
  });

  test('yeterli metin girilince üretim düğmesi açılır', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Akademik Mod' });
    await kapak.getByRole('textbox').first().fill(
      'Köy düzeyinde olay yoğunluğu ile nüfus arasındaki ilişkiyi inceliyorum.',
    );
    await expect(kapak.getByRole('button', { name: /Protokol taslağı üret/ })).toBeEnabled();
  });

  test('kapanır', async ({ page }) => {
    const kapak = page.getByRole('dialog', { name: 'Akademik Mod' });
    await kapak.getByRole('button', { name: 'Kapat' }).click();
    await expect(kapak).toBeHidden();
  });
});
