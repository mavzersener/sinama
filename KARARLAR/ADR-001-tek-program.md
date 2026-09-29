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

## Açık konular

- Commit e-postası: GitHub noreply adresine geçiş — ilk push'tan önce karar
  (geçmiş tek commit; düzeltmesi ucuz).
- `gh` CLI kurulumu (A1; indirme gerektirir, onaylı).
