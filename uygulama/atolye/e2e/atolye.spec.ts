// Atölye uçtan uca (A6 eşdeğerlik E3, ESDEGERLIK.md) — gerçek tarayıcı + gerçek arka uç
// (A5/A6 tek süreç). Ölçüt: editör açılır; demo akışı koşar ve tarayıcı sonuçları "önizleme"
// işaretlidir; akış sunucuya kaydedilir, listelenir, yeniden açılır; bir suc_* düğümü
// SUNUCUDA koşar (çekirdek oturum kimliği görünür); kanıt paketi defterde kaydedilir ve
// verify geçerli döner.
import { test, expect, type APIRequestContext, type Page } from "@playwright/test"

async function rpc(request: APIRequestContext, yol: string, girdi?: unknown) {
  const r = await request.post(`/api/atolye/rpc/${yol}`, { data: { girdi: girdi ?? null } })
  expect(r.status(), `${yol}: ${await r.text()}`).toBe(200)
  return r.json()
}

function konsolHatalari(page: Page): string[] {
  const hatalar: string[] = []
  page.on("console", (m) => { if (m.type() === "error") hatalar.push(m.text()) })
  page.on("pageerror", (e) => hatalar.push(`pageerror: ${e.message}`))
  return hatalar
}
// Beklenen ağ hataları: ajan servisi ve kapsam dışı uçlar (503) — kod hatası değil.
const kodHatasi = (h: string) => !/503|Service Unavailable|Failed to fetch|net::/i.test(h)

/** 24 aylık sentetik olay dizisi: 13. aydan itibaren aylık sayı artar (belirlenimci). */
function aylikCsv(): string {
  const satirlar = ["id,tarih,kanal"]
  let i = 0
  for (let ay = 0; ay < 24; ay++) {
    const y = 2024 + Math.floor(ay / 12)
    const m = String((ay % 12) + 1).padStart(2, "0")
    for (let k = 0; k < (ay >= 12 ? 46 : 30); k++) {
      const gun = String(((k * 7) % 28) + 1).padStart(2, "0")
      satirlar.push(`o${i++},${y}-${m}-${gun},karakol`)
    }
  }
  return satirlar.join("\n") + "\n"
}

const dugum = (id: string, type: string, label: string, config: Record<string, unknown>, x: number, y: number) => ({
  id, type: "custom", position: { x, y },
  data: { label, type, category: "", icon: "", color: "#64748b", config, status: "idle" },
})

test("editör açılır, demo akışı koşar ve tarayıcı sonuçları ÖNİZLEME işaretlidir", async ({ page }) => {
  const hatalar = konsolHatalari(page)
  await page.goto("/atolye/")
  await expect(page.locator(".react-flow")).toBeVisible()
  await page.getByRole("button", { name: "Demo", exact: true }).click()   // yükler ve koşar
  await expect(page.locator(".react-flow__node").first()).toBeVisible()
  await expect(page.getByTestId("kaynak-onizleme").first()).toBeVisible()
  // Demo akışında sunucu düğümü yok: hiçbir sonuç "SUNUCU" görünmemeli.
  expect(await page.getByTestId("kaynak-sunucu").count()).toBe(0)
  await page.getByRole("button").filter({ has: page.getByTestId("kaynak-onizleme") }).first().click()
  await expect(page.getByText(/Önizleme: tarayıcı motorunda hesaplandı — kanıt değildir/).first()).toBeVisible()
  expect(hatalar.filter(kodHatasi), hatalar.join("\n")).toEqual([])
})

test("akış sunucuya kaydedilir, listelenir ve yeniden açılır", async ({ page, browser, request }) => {
  await page.goto("/atolye/")
  await page.getByRole("button", { name: "Demo", exact: true }).click()
  await expect(page.locator(".react-flow__node").first()).toBeVisible()
  const n = await page.locator(".react-flow__node").count()
  await page.getByRole("button", { name: "Save Cloud" }).click()
  await page.getByPlaceholder("Workflow name…").fill("E3 demo akışı")
  await page.getByPlaceholder("Workflow name…").press("Enter")
  await expect(page.getByText("Saved to cloud")).toBeVisible()

  const liste = await rpc(request, "workflow.list")
  const kayitli = liste.items.find((w: { name: string }) => w.name === "E3 demo akışı")
  expect(kayitli, JSON.stringify(liste)).toBeTruthy()
  expect(kayitli.nodes).toHaveLength(n)
  // Sonuçlar ve satırlar buluta yazılmaz (lib/kalicilik): kayıtlı düğümde result yok.
  expect(JSON.stringify(kayitli.nodes)).not.toContain('"result"')

  // Temiz tarayıcı bağlamı (yerel depolama yok) → listeden aç.
  const yeni = await (await browser.newContext({ baseURL: "http://127.0.0.1:8813" })).newPage()
  await yeni.goto("/atolye/")
  await expect(yeni.locator(".react-flow")).toBeVisible()
  await yeni.getByRole("button", { name: "Open", exact: true }).click()
  await yeni.getByText("E3 demo akışı").click()
  await expect(yeni.getByText('Opened "E3 demo akışı"')).toBeVisible()
  await expect(yeni.locator(".react-flow__node")).toHaveCount(n)
  await yeni.context().close()
})

test("suç analizi düğümü SUNUCUDA koşar; kanıt paketi defterde kaydedilir ve doğrulanır", async ({ page, request }) => {
  const hatalar = konsolHatalari(page)
  // 1) Veri seti gerçek yükleme ucundan (çok parçalı).
  const csv = aylikCsv()
  const yr = await request.post("/api/datasets/upload", {
    multipart: { file: { name: "olaylar.csv", mimeType: "text/csv", buffer: Buffer.from(csv) }, name: "olaylar" },
  })
  expect(yr.status(), await yr.text()).toBe(200)
  const ds = await yr.json()
  expect(ds.columns).toEqual(["id", "tarih", "kanal"])

  // 2) Akış: CSV → Rehberli çalışma (sunucu) ve CSV → kanıt paketi (sunucu defteri).
  const kaynak = { anahtar: `ds:${ds.id}`, datasetId: ds.id, filename: ds.filename, columns: ds.columns,
    rowCount: ds.rowCount, onizleme: [], hasHeader: true, delimiter: "," }
  const akis = await rpc(request, "workflow.create", {
    name: "E3 sunucu akışı",
    nodes: [
      dugum("csv", "csv_source", "Olaylar", { filename: ds.filename, _veriKaynagi: kaynak }, 0, 0),
      dugum("rc", "suc_rehberli_calisma", "rehberli calisma", { soru_turu: "ARTIS", amac: "kesifsel" }, 320, -80),
      dugum("kn", "evidence_export", "Kanıt paketi", { caseNumber: "2026/E3", officerId: "PN-1" }, 320, 120),
    ],
    edges: [{ id: "e1", source: "csv", target: "rc" }, { id: "e2", source: "csv", target: "kn" }],
  })

  // 3) Arayüzde aç ve koş.
  await page.goto("/atolye/")
  await page.getByRole("button", { name: "Open", exact: true }).click()
  await page.getByText("E3 sunucu akışı").click()
  await expect(page.locator(".react-flow__node")).toHaveCount(3)
  const sucYaniti = page.waitForResponse((r) => r.url().endsWith("/api/ml/suc/rehberli_calisma"))
  const kanitYaniti = page.waitForResponse((r) => r.url().endsWith("/api/evidence/record"))
  await page.getByRole("button", { name: "Run", exact: true }).click()

  const suc = await sucYaniti
  expect(suc.status(), await suc.text()).toBe(200)
  const paket = await suc.json()
  const oturum: string = paket.sonuc.oturum_id
  expect(oturum).toMatch(/^[0-9a-f]{6,}$/)
  expect(paket.meta.arac).toBe("rehberli_calisma")
  // Oturum çekirdekte gerçekten var: Rehberli'nin manifest ucu aynı oturumu okur.
  const manifest = await request.get(`/api/calisma/${oturum}`)
  expect(manifest.status(), await manifest.text()).toBe(200)

  await expect(page.getByTestId("kaynak-sunucu")).toHaveCount(2)
  const kart = page.getByRole("button").filter({ has: page.getByTestId("kaynak-sunucu") }).filter({ hasText: "rehberli calisma" })
  await kart.click()
  // suc_* sonuçlarının ham çıktısı kartın "View raw result" bölümünde (DataFlow arayüzü).
  await kart.locator("xpath=..").getByText("View raw result").click()
  await expect(page.getByText(oturum).first()).toBeVisible()

  // 4) Kanıt: imzalı makbuz, aktör yerel kullanıcı, zincir geçerli.
  const kanit = await kanitYaniti
  expect(kanit.status(), await kanit.text()).toBe(200)
  const makbuz = await kanit.json()
  expect(makbuz.kayit.aktor).toEqual({ id: 1, ad: "Yerel analist" })
  expect(makbuz.kayit.dosya_no).toBe("2026/E3")
  expect(makbuz.kayit.satir).toBe(ds.rowCount)
  const dogrulama = await (await request.get("/api/evidence/verify")).json()
  expect(dogrulama.gecerli, JSON.stringify(dogrulama)).toBe(true)
  expect(dogrulama.kayit_sayisi).toBeGreaterThanOrEqual(1)

  // 5) Koşu sunucuda kayıtlı (workflow.execute + completeExecution).
  await expect.poll(async () => (await rpc(request, "workflow.executions", { workflowId: akis.id })).items[0]?.status)
    .toMatch(/completed|failed/)
  expect(hatalar.filter(kodHatasi), hatalar.join("\n")).toEqual([])
})

test("kapsam dışı uçlar nedenini söyler; Rehberli ile Atölye aynı süreçte", async ({ page, request }) => {
  const ml = await request.post("/api/ml/ml/random_forest", { data: {} })
  expect(ml.status()).toBe(503)
  expect((await ml.json()).error).toMatch(/MVP dışı/)
  await page.goto("/")
  await page.getByRole("link", { name: "Atölye" }).click()
  await expect(page).toHaveURL(/\/atolye\/$/)
  await expect(page.locator(".react-flow")).toBeVisible()
  await page.getByRole("link", { name: "Sınama Rehberli" }).click()
  await expect(page).toHaveURL(/127\.0\.0\.1:8813\/$/)
})
