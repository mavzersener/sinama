# A6 kapanış dosyası — Atölye (DataFlow no-code editörü Sınama'da)

- **Durum:** A6 **KAPANDI — 02.10.2026**, proje sahibinin "tüm aşamaları tamamla ve testleri
  yap" talimatıyla (sahip bilgisayar başında değilken; itiraz ederse yeniden açılır).
  **İstisna:** çıkış ölçütünün ikinci yarısı — "→ DataFlow dondurulur" — kaynak depoya yazmak
  gerektirir (AGENTS kural 3). ADR-004 md. 7 gereği hazırlandı ve kuru çalıştırıldı; uygulanması
  A7 ile birlikte proje sahibinin açık onayını bekler.
- **Çıkış ölçütü (ADR-001):** "DataFlow testleriyle eşdeğerlik → DataFlow dondurulur".
  **Karar belgesi:** [ADR-004](ADR-004-a6-atolye.md). **Ön-kayıt:**
  [`uygulama/atolye_esdegerlik/ESDEGERLIK.md`](../uygulama/atolye_esdegerlik/ESDEGERLIK.md)
  (`93fd618`, hasattan ve arka uçtan ÖNCE).

## 1. Kanıt

Ölçüm: `betikler/a6_esdegerlik.py` → [`sonuc.json`](../uygulama/atolye_esdegerlik/sonuc.json).
Başlangıç (Sınama, hasattan önce): E1–E5 hepsi 0.

| Ölçüt | Eşik | Sonuç | Not |
|---|---|---|---|
| E1 taşınan ön yüz testleri, değiştirilmeden | 914/914 | **914/914** | 39 dosya; `oracle` yerelde koştu (pandas'lı Python) |
| E2 DataFlow sunucu testlerinin Python karşılıkları | 88/88 | **88/88** | `tests/test_atolye_{depo,kanit,kanit_uctan_uca}.py`, her biri `# DataFlow: <dosya> › <ad>` işaretli; `kanit-uctan-uca`'nın 8'i değiştirilmemiş JS yürütücüsünü GERÇEK Python sunucusuna karşı koşar |
| E3 Atölye uçtan uca (Playwright) | hepsi | **4/4** | editör + demo + ÖNİZLEME işareti; kaydet → listele → temiz bağlamda aç; `suc_rehberli_calisma` sunucuda (çekirdek oturumu Rehberli'nin manifest ucundan okunur, oturum kimliği kartta görünür); kanıt paketi defterde, `verify` geçerli; kapsam dışı 503 + iki yüz arası bağlantı |
| E4 kanıt defteri biçim uyumu | iki yön | **geçti** | DataFlow'un kendi koduyla üretilmiş 3 kayıtlık defter Python'da geçerli (mutasyonu yakalıyor); Sınama'nın defteri DataFlow'un bağımsız `kanit_dogrula.py`'siyle GEÇERLİ; satır sonu LF |
| E5 tek süreç | 1 | **1** | Rehberli `/` ve Atölye `/atolye/` aynı FastAPI sürecinden; MySQL, S3, ml-service, Kimi yok |

Ölçümün kendisinin duyarlılığı (`kiyas/kesif/a6_mutasyon.py`, keşif): dokuz bilinçli hata —
depo sırası, imza baytları, yalnız-yerel kapısı, CSV boş satırı, kanonik olmayan kayıt hash'i,
önizleme işareti, köprü yolu, kayıp suç düğümü, Atölye'nin bağlanmaması — **9/9 yakalandı**.

Ek kanıt:

| Kanıt | Sonuç |
|---|---|
| Atölye arka uç testleri (`tests/test_atolye_sunucu.py`) | 23 test: 23 prosedürün DataFlow davranışı (sahiplik, sürüm artışı, denetim metinleri, zod sınırları, katalog, geri bildirim özeti), veri seti uçları, köprü = `arac_calistir` çıktısı, 503'ler, yalnız-yerel kapısı, statik sunum ve SPA geri dönüşü |
| İnternetsiz kurulum (`betikler/a5_paketle.py`, iki ön yüz) | temiz venv'de `pip --no-index`; paketten başlayan sunucuda `/atolye/`, kanıt kaydı + `verify`, çok parçalı yükleme; `SHA256SUMS` 453/453 |
| Rehberli (A5) gerilemesi | Playwright 2/2, `tests/test_uygulama.py` yeşil; BMK v10 `--dogrula` (bkz. §5) |

## 2. Adımlar

| Adım | Commit | Özet |
|---|---|---|
| ADR-004 + ön-kayıt | `93fd618` | varsayılanlarla; DataFlow başlangıcı 1047 test (1040 geçti), A/B/C sınıflaması |
| Hasat | `0ffd5d8`, `443bcf4` | ön yüz 128 + 7 dosya birebir (`git archive`) |
| Uyarlama 1 | `41ca3c7` | tRPC bağdaştırıcısı, Vite `/atolye/`, sunucu bağımlılıkları çıktı — E1 914/914 |
| A6.1 | `92ee676`, `50632ff` | Python arka uç (SQLite, kanıt defteri, köprü, vekil, 503'ler), uyarlama 2, E2–E5, CI |
| Eşdeğerlik kaydı | `bd04993` | `sonuc.json`, mutasyon 9/9 |
| Paket | `802e92e` | internetsiz pakete Atölye derlemesi |
| A7 hazırlığı | `24281c0` | `betikler/a7_dondur.py` (kuru çalıştırma), README |

## 3. A6'da bulunanlar

- **DataFlow'un B sınıfı sunucu testleri sunucuyu sınamıyordu.** workflow/dataset/audit/
  integration testleri (49) bir bellek içi test ikizini (`tests/helpers.ts` `InMemoryDb`)
  sınıyordu; router kodu bu testlerde hiç çalışmıyordu. Sınama karşılıkları gerçek depoyu,
  ayrıca `test_atolye_sunucu.py` gerçek prosedürleri sınar. Tek anlamsal fark belgelendi:
  ikiz aynı milisaniyedeki kayıtları ekleme sırasında bırakıyordu (`audit-router` kanıt
  zinciri testi `[2]`'ye bakar); gerçek depo kesin artan zamanla sıralar (`[0]`).
- **Eşdeğerlik ölçümünün ilk sürümü iki hataya kördü.** Mutasyon denemesi, ölçütlerin aynı
  Python sürecinde koştuğunu ve modül önbelleğinin mutasyonu (ya da bir öncekinin kalıntısını)
  gizlediğini gösterdi; her ölçüm artık taze süreçte.
- **SQLite bağlantı sızıntısı:** her uygulama örneği açık bir bağlantı bırakıyordu
  (ResourceWarning); dosya deposu artık sorgu başına bağlanır.
- **`suc_dongu_veri` tuvalde kullanılamaz bir düğümdü** (`oturum_id` ister, tuval üretemez);
  üretecin kendi kapsam kuralına uyularak çıkarıldı. Sınama kaydından gelen üç yeni düğüm:
  `suc_bolge_oran`, `suc_kesinti_analizi`, `suc_rehberli_calisma`.
- **Sertleştirmeler (DataFlow'da yoktu):** Atölye uçları geri döngü dışını reddeder (aktör hep
  yerel kullanıcı; kanıt defterine başkası onun adına yazamaz); depolama anahtarı kökten
  çıkamaz (DataFlow yalnız `../` ayıklıyordu); Türkçe dosya adı indirme başlığını bozmaz
  (RFC 5987).
- **ADR-001 açık konusu (P06):** DataFlow yolu için kapandı — Atölye'nin suç düğümleri artık
  Sınama çekirdeğini (P06 mahremiyet + zincir v2) kullanır. HARP hâlâ kanonik `suc_analizi`'yi
  kullanıyor; o yarısı açık.

## 4. Açık kalanlar (devir)

| Konu | Neden / not |
|---|---|
| DataFlow'un dondurulması | kaynak depoya yazma — proje sahibinin onayı (A7); `python betikler/a7_dondur.py` kuru çalıştırma: HAZIR |
| CI'da A6 | yerelde yeşil; yeni CI adımları (Atölye derleme, vitest, eşdeğerlik) push'tan sonra koşar |
| DataFlow'un kendi Playwright arayüz testleri (`atolye/tests/ui`, hasat edildi) | `localhost:3000` kökünü hedefliyor; Sınama'da koşturulmadı (ön-kayıtta yok; E3 açılış/demo yüzeyini kapsıyor) |
| Atölye arayüz dili | DataFlow metinleri çoğunlukla İngilizce; Atölye'de tr/en seçimi yok (Rehberli'de var) |
| Ad çakışması | Atölye içindeki DataFlow "Rehberli Mod"u ile Sınama Rehberli yüzü aynı adı taşıyor |
| A5 uçlarında yalnız-yerel kapısı | A5 yalnız 127.0.0.1'e bağlanmakla korunuyor; istek düzeyi kapı yalnız Atölye uçlarında |
| YerelAjan vekili | sahte ajan sunucusuyla sınandı; gerçek YerelAjan (8800) ile denenmedi |

## 5. Tam test geçişi (kapanış anı, `24281c0` üzerinde, Windows / Python 3.14)

| Kapı | Sonuç |
|---|---|
| Çekirdek tam kapı (`cekirdek/test.sh`) | 623 test (1 atlama), kapsam cırcırı gerilemesiz, MCP, demolar — TÜM TESTLER GEÇTİ |
| Kök testler (`python -m unittest discover -s tests`) | 267 test — OK (A5 + A6 + dondurma betiği + bekçi + BMK birim) |
| BMK v0–v10 `--dogrula` | 11/11 yeniden ölçüm kayıtlı sonuçla birebir (v5 574 sn, v6 864 sn, v7 709 sn) |
| Bekçi, tüm geçmiş (`veri_bekcisi.py --gecmis`) | temiz |
| A6 eşdeğerliği (`a6_esdegerlik.py`) | E1 914/914, E2 88/88, E3 4/4, E4, E5 — hepsi eşikte |
| Rehberli Playwright (`uygulama/web`) | 2/2 |
| Mutasyon (`kiyas/kesif/a6_mutasyon.py`) | 9/9 |

CI (Linux py3.12 + Windows py3.14) A6 commit'lerini henüz görmedi: push proje sahibinin
onayını bekliyor (AGENTS kural 8).
