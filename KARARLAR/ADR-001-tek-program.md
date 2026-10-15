# ADR-001 — Tek bilimsel suç analizi programı

- **Durum:** Kabul edildi — 29.09.2026 (proje sahibinin onayı)
- **Kapsam:** tüm kolluk analitiği projeleri

## Bağlam

- Yedi proje (suc_analizi, DataFlow, harp_pol_x, science_gpt, AnlamCekirdegi,
  YerelAjan, CinKollukKatalog) aynı işleri iki ile beş kez uygulamış:
  4 hipotez modeli, 4 yöntem önerici, 2 uygunluk kapısı, 3 analiz oturumu,
  5 hash zinciri, 4 regresyon motoru, 4 Python ortamı.
- Fiilî kullanım çok düşük: DataFlow'da tek yürütme kaydı var, YerelAjan'da suç
  araçları hiç çağrılmamış, science_gpt 29.07'den beri durgun. Yeniden kurmanın
  mevcut kullanıcıyı kırma bedeli düşük.
- Her proje yalnız kendi klasörünü gören ayrı bir yapay zekâ oturumunda doğdu;
  ekosistem bağlamı olmadığı için her yeni plan bir sürüm daha önerdi. Codex'in
  hazırlık kopyası kanonik depoyla çatallandı; P06 mahremiyet düzeltmesi
  kanoniğe hiç aktarılmadı.
- Kod için uzak yedek yok.

## Karar

1. **Tek program, tek depo.** `sinama`, proje sahibinin kişisel GitHub hesabında
   **özel** depo; hesaptaki tek proje.
2. **Hasat.** Mevcut projelerin en iyi parçaları testleriyle taşınır, yeniden
   yazılmaz; her parçanın kaynağı ve commit'i `HASAT.md`'dedir.
3. **İki yüz, tek arka uç.** Rehberli (varsayılan: Soru → Plan → Hüküm) ve Atölye
   (DataFlow no-code editörü — DataFlow bu programın no-code aracıdır). Tek Python
   (FastAPI) arka ucu, tek süreç, tek port; SQLite ve JSONL. Arayüz DataFlow'un
   React bileşenlerinden hasat edilir.
4. **Hesap.** Kanıt üreten her hesap sunucuda, tek motorda koşar. Dil modeli
   opsiyoneldir (8080 kapalıyken çekirdek tam çalışır) ve sayı üretmez.
5. **Veri.** Özel veri, oturum ve kanıt kayıtları, Bilgi Notları, anahtarlar ve
   `.env` depoya — dolayısıyla GitHub'a — girmez; veri kökü depo dışındadır.
   `betikler/veri_bekcisi.py` bunu commit ve push'ta zorlar.
6. **Kaynak projeler** hasat edildikçe dondurulur (etiket ve README yönlendirmesi);
   paralel geliştirme yapılmaz. YerelAjan ve Anlam Çekirdeği ayrı yaşar, programa
   MCP ya da dışa aktarımla bağlanır.
7. **Ölçüm içeride.** Bilimsel Muhakeme Kıyası (BMK) depo içindedir ve CI'da koşar.

## MVP dışı

Tahminci kara kutu ML, kişi/fail tespiti, otomatik operasyonel görevlendirme, çok
kullanıcı, bulut barındırma, kendini değiştiren döngüler.

## Aşamalar

| Aşama | İçerik | Çıkış ölçütü |
|---|---|---|
| A0 | Yerel iskelet: ADR, AGENTS/CLAUDE, HASAT, veri bekçisi | bekçi testleri yeşil, ilk yerel commit |
| A1 | GitHub özel depo ve ilk push (onaylı) | uzakta tek dal; bekçi push'ta yeşil |
| A2 | Çekirdek: suc_analizi + P06 birleşimi + testleri; CI Windows ve Linux | CI yeşil |
| A3 | BMK v0: üç vaka ve başlangıç ölçümü | başlangıç tablosu |
| A4 | Bilim katmanı v1: çalışma, hipotez seti, rakip açıklama kataloğu, hüküm kuralları | BMK'da ölçülen kazanç |
| A5 | Tek arka uç ve Rehberli yüz | üç ekran uçtan uca |
| A6 | Atölye: editör ve 22 ucun FastAPI'ye taşınması | DataFlow testleriyle eşdeğerlik → DataFlow dondurulur |
| A7 | Kaynak depoların dondurulması | etiket ve yönlendirme |

Aynı anda tek aşama açıktır; her aşama testler yeşilken ve proje sahibinin onayıyla
kapanır.

## Sonuçlar

- (+) Tek bakım yüzeyi; kod için uzak yedek; Codex ve Claude aynı depoda, dallarla
  çalışır — hazırlık kopyası ve elle aktarım düzeni kapanır.
- (−) DataFlow Node arka ucunun 22 ucu Python'a taşınacak; geçiş boyunca DataFlow
  çalışır tutulur.
- Geri dönüş: kaynak projeler dondurulmuş hâlde durur; her aşamada eskiye dönülebilir.

## İlerleme

| Aşama | Durum | Kanıt |
|---|---|---|
| A0 | Kapandı — 29.09.2026 | `dd7cca2`; bekçi 19 test, iki mutasyon yakalandı, gerçek depoda veri+token commit'i reddedildi |
| A1 | Kapandı — 29.09.2026 | `origin` = github.com/mavzersener/sinama (özel: oturumsuz web ve API 404); yerel ve uzak `main` aynı commit |
| A2 | Kapandı — 29.09.2026 | `cekirdek/` = suc_analizi `20d6e2c` birebir hasadı (93 dosyanın 92'si blob düzeyinde aynı); paket adı `sinama` (aynı adla import konuma göre kanoniği alıyordu — ölçüldü, testle kilitlendi); P06 mahremiyet + 07 zincir v2 üçlü birleşimi (birleşik testler, iki mutasyon yakalandı). CI koşusu `36516719251`: bekçi tüm geçmişte (8 commit), çekirdek tam kapı Linux py3.12 (505 test, kapsam %94,1) ve Windows py3.14 (505 test, %93,7) — hepsi yeşil |
| A3 | Kapandı — 29.09.2026 | BMK v0: ön-kayıt `db8bf95` (11:47:42, sonuç görülmeden kilit) → ölçüm `ef1b5a6`. 15 ölçütün 6'sı geçti; kod incelemesinden yazılan 6/6 öngörü doğrulandı; öngörülmeyen 3 başarısızlık keşifle açıklandı (biri ölçüt tasarım hatası, v1'de düzeltilecek). CI `36519746996`: Windows/py3.14'te üretilen sonuç Linux/py3.12'de birebir yeniden üretildi. Bulgular: `kiyas/sonuclar/v0_bulgular.md` |
| A4 | Kapandı — 02.10.2026 (proje sahibinin onayı) | Araç dürüstlüğü + bilim katmanı v1 ([ADR-002](ADR-002-bilim-katmani.md)): A4.1–A4.16; 10 ön-kayıtlı kıyasta (BMK v0–v9) 37/96 → 90/96; kalan 6 ölçüt ölçülmüş ve belgeli (yöntem/bilgi sınırı, bir ölçüt hatası). [Kapanış dosyası](A4-kapanis-dosyasi.md). CI `36977568707` (`253bfc3`): BMK v0–v9 Linux/py3.12'de birebir (v8, v9 Windows/py3.14'te üretildi), çekirdek tam kapı Linux ve Windows — hepsi yeşil |
| A5 | Kapandı — 02.10.2026 (proje sahibinin "tüm aşamaları tamamla" talimatıyla) | [ADR-003](ADR-003-a5-arka-uc-rehberli.md); BMK v10 0/7 → 7/7 (CI `36984030467` Linux'ta birebir); üç ekran Playwright ile uçtan uca 2/2 (TR + EN); internetsiz kurulum temiz ortamda doğrulandı. [Kapanış dosyası](A5-kapanis-dosyasi.md) |
| A6 | Kapandı — 02.10.2026 (proje sahibinin "tüm aşamaları tamamla" talimatıyla; DataFlow'un dondurulması hariç → A7) | [ADR-004](ADR-004-a6-atolye.md); ön-kayıtlı eşdeğerlik (`93fd618`): E1 914/914 taşınan ön yüz testi değiştirilmeden, E2 88/88 sunucu testi Python karşılığıyla, E3 Playwright 4/4, E4 kanıt defteri biçimi iki yönde, E5 tek süreç; ölçüm duyarlılığı 9/9 mutasyon. [Kapanış dosyası](A6-kapanis-dosyasi.md) |
| A7 | Uygulandı — 15.10.2026 (proje sahibinin açık onayıyla); **kapanış CI sonrası sahibin** | `suc_analizi` dondurma commit'i `01462e7`, DataFlow `3d3d9d0`; her ikisinde `sinama-dondurma` etiketi. Geri dönüş: `git revert` + `git tag -d`. [Kapanış dosyası](A7-kapanis-dosyasi.md). Dondurulmayanlar gerekçeli (betikte) |

## Kapanan konular

- Commit e-postası: kişisel e-posta kaldı; depo özel olduğu için noreply'e geçilmedi.
- Push kimlik doğrulamasını Git for Windows'un Credential Manager'ı
  (`credential.helper=manager`) yapar. `gh` CLI A2'de yalnız CI okumak için
  kuruldu (v2.101.0, resmi zip, SHA-256 doğrulandı, kullanıcı dizininde; git
  ayarlarına dokunulmadı).

## Açık konular

- Kanonik `C:\Projects\suc_analizi`'de P06 mahremiyet düzeltmesi yok; DataFlow
  ve HARP onu kullanıyor. (A6: DataFlow yolu kapandı — Atölye Sınama çekirdeğini kullanır;
  HARP yarısı açık.) Seçenekler: A6'ya (DataFlow'un Sınama'ya geçişi) kadar
  kabul etmek ya da birleşik düzeltmeyi oraya geri taşımak. Karar proje sahibinde.
