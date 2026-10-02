# A4 kapanış dosyası — araç dürüstlüğü ve bilim katmanı v1

- **Hazırlayan:** otonom çalışma (30.09–01.10.2026), proje sahibinin talimatıyla.
- **Durum:** A4 **KAPANDI — 02.10.2026** (proje sahibinin onayı). Testler yeşilken: CI
  `36977568707` (`253bfc3`) — BMK v0–v9 Linux/py3.12'de birebir, çekirdek tam kapı Linux ve
  Windows. A5 açılmadı: ADR-003 taslağı sahibin kabulünü bekliyor.
- **Çıkış ölçütü (ADR-001):** "BMK'da ölçülen kazanç."

## 1. Ölçülen kazanç (BMK, ön-kayıtlı; her sürüm uygulamadan ÖNCE kilitlendi)

| Sürüm | Konu | Tohum | Başlangıç | Bugün |
|---|---|---|---|---|
| v0 | kümelenme, bildirim artefaktı, ortak MO | 1–30 | 6/15 | 12/15 |
| v1 | kanal sayımı, LISA, yükselen sıcak nokta, anomali, yayılmış seri | 101–130 | 4/9 | 8/9 |
| v2 | seri bağlantısında katman ve kanıt hatları | 201–230 | 6/10 | 10/10 |
| v3 | kategorik hüküm (Rehberli akış) | 301–330 | 0/12 | 12/12 |
| v4 | hüküm sağlamlığı (etki büyüklüğü) | 401–430 | 3/7 | 7/7 |
| v5 | aşırı yayılım (NB) | 501–700 | 6/7 | 7/7 |
| v6 | bileşene özgü yayılım | 701–880 | 6/8 | 8/8 |
| v7 | ETKİ soru türü | 10001–10100 | 0/9 | 9/9 |
| v8 | NNI ve CUSUM | 10101–10200 | 1/12 | 11/12* |
| v9 | CUSUM kalibrasyonu | 10201–10400 | 5/7 | 6/7 |
| **Toplam** | | | **37/96** | **90/96** |

\* v8'in son sütunu (A4.16) incelenmiş tohumlarda — kanıt değil kayıt; A4.16'nın kanıtı v9.

Tümü CI'da (`kapi.yml`, sürüm matrisi) Linux/py3.12'de birebir yeniden üretilir; ayrıntı
her sürümün `sonuclar/ilerleme.md` dosyasında (sütun = çekirdek değişikliği).

## 2. Adımlar

| Adım | Commit | Özet |
|---|---|---|
| A4.1 | `1721ced` | Gi* Benjamini–Hochberg FDR: sahte sıcak nokta %70 → %0 |
| A4.2 | `025e041` | seri ADAYI (taban oranlı MO + uzay-zaman), uyarı + insan onayı |
| A4.3–4 | `cc193d6`, `169e7e4` | BMK v1 ön-kayıt ve ölçüm |
| A4.5 | `e5042d5` | LISA ve bölge anomalisi FDR |
| A4.6 | `fec3764` | yükselen sıcak nokta yeniden tasarım |
| A4.7 | `00c1f57` | trend anlamlılığı, segmentli ITS aracı; 0/0'dan çıkarım denetimi |
| A4.8 | `e1f408c` | seri eşleştirme: ayırt edici paylaşım testi + katman |
| A4.9 | `96c5182` | bilim katmanı v1 (ADR-002): hipotez seti, RAK, kategorik hüküm |
| A4.10 | `1715910` | sınama v1.1: rakibi etki büyüklüğüyle dışlama |
| A4.11 | `dd140cf` | sınama v1.2 REDDEDİLDİ (v5 koruma ölçütü düştü) |
| A4.12 | `ba65c7a` | sınama v1.3: bileşene özgü yayılım çarpanı |
| A4.13 | `7d82250` | ETKİ soru türü (oran oranı DiD, üç yeni rakip) |
| A4.14 | `9fde6a6` | ayrıntılı bilim araçları; ön-kayıt geçerliliği hükme girer |
| A4.15 | `547c120` | NNI dürüst varsayılan; kalibre kalıcı artış alarmı |
| A4.16 | `3ec7a73` | CUSUM Anscombe dönüşümü |

## 3. Öngörü kaydı (bilim yalnız tutan öngörülerden oluşmaz)

Her ön-kayıt, başlangıç ve uygulama için zaman damgalı öngörü taşır. Yanlış çıkanlar
kayıtlıdır ve her biri bir ders üretti:

- A4.5: LISA gücü korunur dedim, 1,00 → 0,47 (yöntem sınırı; kabul edildi).
- A4.7: K2.2 değişmez dedim, 0,967 (gücü hesaplamadan öngörü yazmışım).
- A4.9–10: v3 K9.1 1,00 dedim, 0,967 (tek sınamanın I. tip hatası hükme taşınıyordu → v1.1).
- v5: K11.3 öngörüsü yanlış (60 tohumluk keşif farkı gürültüydü).
- A4.11: v1.2 keşif varyantı uygulamayla özdeş değildi → red; ders: keşif kodu = uygulama.
- A4.15: K15.1 0,00–0,07 dedim, 0,14 (100 tohumluk keşif şanslıydı) → teşhis → v9.
- A4.17 (keşif): "v1.3'ün aşırı iddiası φ kestirim belirsizliğinden" ve "ayrım noktası
  yanından" hipotezlerinin ikisi de çürüdü; aday ön-kayda gitmedi.
- v9: K16.3 başlangıçta "sınırda kalır" dedim, geçti; K16.7 aralığın hemen altında;
  v0 K2.1 etkisini hiç yazmamıştım (eksik öngörü).

## 4. Aynı sınıf denetimleriyle bulunan hatalar (BMK dışı)

- 0/0'dan çıkarım: `coklu_ols` tam uyumda t = β/1e-9, `lojistik` ayrışmada p = 0,94,
  t-testleri/ANOVA sıfır varyansta uydurma p → artık tanımsız (None + not).
- Oturum kapısı araç adıyla değerlendiriliyordu (11 araçta yanlış kural) → ARAC_GATE.
- Ön-kayıt: `hipotez_seti` analiz sayılıyordu → her Rehberli doğrulayıcı oturumda
  provenans "keşifsel" derken hüküm DESTEKLENDİ; hüküm ve makale kilidin varlığına
  bakıyordu → geçerliliğine (A4.14).
- Ham CUSUM (tüm seri ortalaması, h = 5σ) değişimsiz seride %89 alarm → kaldırıldı.

## 5. Açık kalanlar (kapanışı engellemediğini öneriyorum; hepsi ölçülmüş ve belgeli)

| Konu | Durum | Neden / öneri |
|---|---|---|
| v0 K1.1 NNI yerel odak gücü 0,567 | KALIR | NNI küresel ölçü; araç bunu söyler, yerel soru → Gi* (güç 0,90) |
| v0 K2.1 CUSUM [−15, +60] 0,300 | KALIR | %5 yanlış alarmda bilgi sınırı; ölçüt gürültülü erken alarmı ödüllendirir |
| v0 K2.4 | KALIR | ölçüt tasarım hatası (v1 K2b.1 ile değiştirildi) |
| v1 K4.1 LISA gücü 0,467 | KALIR | FDR ile yöntem sınırı; sıcak nokta için Gi* |
| v8 K15.4 / v9 K16.4 %30 artış [−15, +180] | KALIR | 24 aylık seride bilgi sınırı |
| sınama v1.3: karma senaryolarda aşırı iddia %6–7,5 | eşik içinde | nominal %5 üstü; v1.4 adayı (t kritik değer) ve ayrım noktası yanı hipotezi keşifte ÇÜRÜDÜ ([a417](../kiyas/kesif/a417_bulgular.md)) — ölçülmüş sınır |
| ETKİ kontrolsüz ITS gücü 0,74 | belgeli | kontrolsüz hüküm zaten en çok KIRILGAN |
| `bulanik_eslesme`, `ag_analizi` | ÖLÇÜLMEDİ | insan onayı + uyarı var; BMK vakası yok |
| Oturumlar `SINAMA_LOG_DIR` yoksa çalışma dizinine | açık | A5 (ADR-003 taslağı md. 3) |
| P06 mahremiyet düzeltmesinin kanoniğe geri taşınması | açık | sahibin kararı; A6'ya kadar varsayılan |

## 6. Öneri ve karar

A4'ün çıkış ölçütü karşılandı: 10 ön-kayıtlı kıyasta 37/96 → 90/96, kalan 6 ölçütün her
biri ölçülmüş ve nedeni belgeli (yöntem ya da bilgi sınırı, biri ölçüt hatası).
**Önerim A4'ün kapatılmasıdır**; A5 taslağı [ADR-003](ADR-003-a5-arka-uc-rehberli.md).
Kapanış ve A5'in açılması proje sahibinin kararıdır. **Karar (02.10.2026):** A4 kapatıldı;
açık kalanlar (§5) kayıtlı sınırlar olarak sonraki aşamalara devredildi.

## 7. Push

02.10.2026'da proje sahibinin onayıyla itildi: `1715910..253bfc3` (19 commit), ardından
kapanış commit'i. `deneme/v1.2-havuz-phi` (`d3ef040`, reddedilen v1.2) itilmedi; yalnız D:
yedeğinde.
