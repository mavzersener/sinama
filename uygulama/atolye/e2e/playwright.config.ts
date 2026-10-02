import { defineConfig, devices } from "@playwright/test"

/**
 * Atölye uçtan uca testi (A6 eşdeğerlik E3, ESDEGERLIK.md): gerçek tarayıcı, gerçek arka uç
 * (e2e/sunucu.py — A5/A6 tek süreç, geçici veri kökü). Önce `npm run build` (arka uç
 * dist/'i /atolye/ altında sunar).
 */
export default defineConfig({
  testDir: ".",
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8813",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [{ name: "masaustu", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: {
    command: `${process.env.SINAMA_PY ?? "python"} sunucu.py`, // yapılandırma dizinine (e2e/) göreli
    url: "http://127.0.0.1:8813/api/saglik",
    reuseExistingServer: false,
    timeout: 60_000,
    env: { PYTHONUTF8: "1" },
  },
})
