import { expect, test } from "@playwright/test"

/**
 * A5 çıkış ölçütü: "üç ekran uçtan uca". Gerçek tarayıcı + gerçek arka uç; veri
 * sentetiktir (BMK üreteçleri, e2e/sunucu.py). Ekran sözleşmesi BMK v10'da HTTP düzeyinde
 * ölçülür; burada aynı sözleşmenin EKRANDA göründüğü sınanır.
 */

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("e2e_dil_kuruldu")) {
      localStorage.removeItem("sinama_dil")
      sessionStorage.setItem("e2e_dil_kuruldu", "1")
    }
  })
})

test("TR · doğrulayıcı ARTIŞ: bildirim artefaktı BELİRSİZ, insan onayıyla SONUÇ", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "Soru", exact: true })).toBeVisible()

  await page.getByPlaceholder("Ör. Son 12 ayda hırsızlık arttı mı?").fill("Son 12 ayda hırsızlık arttı mı?")
  await page.getByRole("button", { name: "Soru türünü öner" }).click()
  await expect(page.getByText("Öneri (kurallardan): ARTIŞ")).toBeVisible()

  const baslat = page.locator('[data-eylem="baslat"]')
  await expect(baslat).toBeDisabled() // veri ve onaylayan yok
  await page.getByLabel("Protokolü kilitleyecek kişi").fill("Analist A")
  await page.locator("select").first().selectOption("bildirim.csv")
  await expect(page.getByText(/satır · sütunlar: id, tarih, kanal/)).toBeVisible()
  await page.getByLabel("Bildirim kanalı alanı (isteğe bağlı)").selectOption("kanal")
  await baslat.click()

  await expect(page).toHaveURL(/#\/plan\/[a-z0-9]+$/)
  await expect(page.locator('[data-ekran="plan"]')).toBeVisible()
  await expect(page.locator('[data-tavan="DESTEKLENDİ"]')).toBeVisible()
  for (const kod of ["R-RASTLANTI", "R-BILDIRIM", "R-MEVSIM", "R-VERI"]) {
    await expect(page.locator(`[data-rakip="${kod}"]`)).toBeVisible()
  }
  await expect(page.locator("[data-bilinmeyen]")).toContainText("H_bilinmeyen")
  await expect(page.getByText("protokol Analist A adıyla, veriye bakılmadan kilitlenecek")).toBeVisible()

  await page.locator('[data-eylem="sina"]').click()
  await expect(page).toHaveURL(/#\/hukum\/[a-z0-9]+$/)
  await expect(page.locator("[data-kategori]").first()).toHaveAttribute("data-kategori", "BELİRSİZ")
  await expect(page.locator("[data-taslak]")).toBeVisible()
  await expect(page.getByText("En güçlü rakip: Kayıt/bildirim değişikliği")).toBeVisible()
  await expect(page.locator('[data-rakip="R-BILDIRIM"]')).toHaveAttribute("data-durum", "destekleniyor")
  await expect(page.locator('[data-kural="K3-rakip"]')).toBeVisible()
  const metin = await page.locator("main").innerText()
  expect(metin).not.toMatch(/güven puanı|probability|confidence/i)

  const onayla = page.locator('[data-eylem="onayla"]')
  await expect(onayla).toBeDisabled() // onaylayansız SONUÇ yok
  await page.getByLabel("Onaylayan").fill("Analist A")
  await onayla.click()
  await expect(page.locator("[data-onay]")).toContainText("SONUÇ kaydedildi: Analist A")

  await page.reload() // durum arka uçta: yeniden yüklemede korunur
  await expect(page.locator("[data-onay]")).toContainText("Analist A")
})

test("EN · keşifsel ETKİ: tavan FRAGILE, kategori İngilizce, dil seçimi kalıcı", async ({ page }) => {
  await page.goto("/")
  await page.getByRole("button", { name: "EN" }).click()
  await expect(page.getByRole("heading", { name: "Question", exact: true })).toBeVisible()

  await page.getByText("IMPACT — did an intervention reduce incidents?").click()
  await page.getByText("Exploratory (at most FRAGILE)").click()
  await page.locator("select").first().selectOption("etki.csv")
  await expect(page.getByText(/rows · columns: id, tarih, bolge/)).toBeVisible()
  await page.getByLabel("Area field (required)").selectOption("bolge")
  await page.getByLabel("Intervention area (required)").selectOption("M")
  await page.getByLabel("Control area (optional)").selectOption("K")
  await page.getByLabel("Buffer area (optional)").selectOption("T")
  await page.getByLabel("Intervention start date (required)").fill("2025-01-01")
  await page.locator('[data-eylem="baslat"]').click()

  await expect(page).toHaveURL(/#\/plan\//)
  await expect(page.locator('[data-tavan="KIRILGAN"]')).toContainText("FRAGILE")
  await expect(page.getByText("the intervention reduced incidents in the intervention area")).toBeVisible()
  for (const kod of ["R-ESZAMANLI", "R-ORTALAMAYA-DONUS", "R-YER-DEGISTIRME"]) {
    await expect(page.locator(`[data-rakip="${kod}"]`)).toBeVisible()
  }

  await page.locator('[data-eylem="sina"]').click()
  await expect(page).toHaveURL(/#\/hukum\//)
  const kategori = await page.locator("[data-kategori]").first().getAttribute("data-kategori")
  expect(kategori).not.toBe("DESTEKLENDİ") // keşifsel çalışma en çok KIRILGAN
  await expect(page.locator("[data-kategori]").first()).toHaveText(/SUPPORTED|FRAGILE|INCONCLUSIVE|CONTRADICTED|ABSTAIN/)
  await expect(page.getByText("Reasoning sentences are produced by the core in Turkish.")).toBeVisible()

  await page.reload()
  await expect(page.getByRole("heading", { name: "Verdict", exact: true })).toBeVisible()
})
