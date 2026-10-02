import { defineConfig, devices } from "@playwright/test"

/**
 * Rehberli üç ekranın uçtan uca testi (A5 çıkış ölçütü): gerçek tarayıcı, gerçek arka uç
 * (e2e/sunucu.py — geçici veri kökü, sentetik veri, dil modeli kapalı). Önce
 * `npm run build` (arka uç dist/'i sunar).
 */
export default defineConfig({
  testDir: ".",
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8812",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [{ name: "masaustu", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } }],
  webServer: {
    command: `${process.env.SINAMA_PY ?? "python"} sunucu.py`, // yapılandırma dizinine (e2e/) göreli
    url: "http://127.0.0.1:8812/api/saglik",
    reuseExistingServer: false,
    timeout: 60_000,
    env: { PYTHONUTF8: "1" },
  },
})
