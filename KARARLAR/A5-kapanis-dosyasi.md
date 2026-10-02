# A5 kapanış dosyası — tek arka uç ve Rehberli yüz

- **Durum:** A5 **KAPANDI — 02.10.2026**, proje sahibinin "tüm aşamaları tamamla ve testleri
  yap" talimatıyla (sahip bilgisayar başında değilken; itiraz ederse yeniden açılır).
- **Çıkış ölçütü (ADR-001):** "üç ekran uçtan uca". **Karar belgesi:** [ADR-003](ADR-003-a5-arka-uc-rehberli.md).

## 1. Kanıt

| Kanıt | Sonuç |
|---|---|
| BMK v10 (ön-kayıt `4ae96d3`, uygulamadan önce kilit) | 0/7 → 6/7 (A5.1 arka uç) → **7/7** (A5.2 ön yüz). CI `36984030467`'de Linux/py3.12'de birebir |
| Üç ekran uçtan uca (Playwright, gerçek tarayıcı + gerçek arka uç, `uygulama/web/e2e`) | 2/2: TR doğrulayıcı ARTIŞ (öneri → plan → hüküm → insan onayıyla SONUÇ → yeniden yükleme) ve EN keşifsel ETKİ (bölge seçimi, tavan, İngilizce kategori, dil kalıcılığı); 3/3 mutasyon |
| Arka uç birim testleri (`tests/test_uygulama.py`) | 13 test; dil modeli yolları sahte sunucuyla; 12/12 + 2/2 mutasyon |
| İnternetsiz kurulum (`betikler/a5_paketle.py`) | temiz venv'de `pip --no-index` kurulum, paketten çalışan sunucu (sağlık, ön yüz, öneri), `SHA256SUMS` 278/278 |
| Dil modeli yolları (yerel Qwen3.8-27B, `kiyas/kesif/a5_dil_modeli_bulgular.md`) | soru türü önerisi 10/10 (8 TR + 2 EN), sade özet iki dilde sözleşmeye uygun |
| Çekirdek tam kapı, kök testler, BMK v0–v9 | değişmedi (A5.1'de veri kökü değişikliğinden sonra tam kapı ve v1–v9 yeniden doğrulandı) |

## 2. Adımlar

| Adım | Commit | Özet |
|---|---|---|
| ADR-003 kabul | `9a74511` | varsayılanlar + İngilizce seçenek |
| BMK v10 | `4ae96d3`, `8655167` | ön-kayıt ve başlangıç 0/7 |
| A5.1 | `ebd45b9` | FastAPI arka uç; çalışma dizinine düşme kaldırıldı |
| Hasat | `ca25fc6` | DataFlow arayüz temelleri birebir |
| A5.2 | `fdc1fdc` | Soru/Plan/Hüküm ön yüzü, tr/en |
| A5.3 | `a9af555`, `db4743a` | dil modeli düşünme kipi düzeltmesi, internetsiz paket |
| A5.4 | `e0f5eee` | Playwright uçtan uca test, CI'da |

## 3. A5'te bulunan hatalar

- Bozuk dil modeli adresi (`InvalidURL`) sağlık ucunu ve tüm akışları düşürüyordu.
- Çekirdek, `SINAMA_LOG_DIR` yokken oturumu çalışma dizinine yazıyordu (A3 bulgusu canlıydı;
  `cekirdek/oturumlar`'da 35 test oturumu).
- Dil modelinin düşünme kipi içeriği boş bırakıyordu → öneri hep kurala düşüyor, sade özet
  hep 422 veriyordu (yetenek ölüydü).
- Kurulum paketinin `SHA256SUMS.txt`'i kendini (boş dosya özetiyle) içeriyordu.

## 4. Açık kalanlar (sonraki aşamalara devir)

| Konu | Neden / not |
|---|---|
| Dil modelli sistem ölçütleri BMK'da değil | belirlenimci değil; keşif kaydı var, CI dışı (ADR-003 md. 5) |
| Çekirdek gerekçe cümleleri ve araç uyarıları İngilizce arayüzde Türkçe | ADR-003 kararı (makine çevirisi araya girmez) |
| Çok kullanıcı, kimlik doğrulama | A5 kapsam dışı (ADR-003); Atölye'de (A6) yerel tek kullanıcı |
| Ekran görüntüsüyle kanıt | uygulama penceresi arkadayken alınamadı; Playwright testleri ekranı CI'da sınar |
