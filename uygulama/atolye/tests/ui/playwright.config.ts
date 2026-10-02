import { defineConfig, devices } from '@playwright/test';

/**
 * Arayüz test koşucusu — GERÇEK fare olaylarıyla.
 *
 * NEDEN AYRI KOŞUCU: vitest bu projede saf mantık testleri için kullanılıyor
 * (environment: node, DOM yok). Arayüz sorunları — kırpılan tıklama alanı,
 * ölçülmeyen düğüm, sürüklenemeyen bağlantı — yalnız gerçek bir tarayıcıda
 * gerçek fare olaylarıyla ortaya çıkar.
 *
 * Uygulama içi önizleme paneli bu iş için YETERSİZDİR: orada ResizeObserver
 * tetiklenmediği için React Flow düğümleri `visibility: hidden` kalır ve
 * hiçbir tıklama isabet etmez. Playwright'ın Chromium'u gerçek ölçüm yapar.
 */
export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  // Arayüz testleri sıralı koşar: tek dev sunucu, paylaşılan durum.
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [
    ['list'],
    ['html', { outputFolder: 'rapor', open: 'never' }],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    // Başarısızlıkta teşhis: ekran görüntüsü + iz + video.
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
  },
  projects: [
    { name: 'masaustu', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    cwd: '../..',
    // Zaten açık bir sunucu varsa onu kullan (geliştirme sırasında pratik).
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
