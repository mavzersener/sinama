# BMK v10 — A5 Rehberli arka ucun seyri

Aynı ön-kayıtlı kıyas (v10, eşikler değişmedi), değişen kod. Her sütun bir değişiklikten
sonra yapılan tam ölçümdür; sayılar o commit'teki `v10.json`'dadır. Kalın: önceki sütuna
göre değişen.

| Ölçüt | Eşik | Başlangıç (A5 öncesi) | A5.1 arka uç | A5.2 ön yüz (TR/EN) |
|---|---|---|---|---|
| K17.1 HTTP hükmü = MCP hükmü | ≥ 1,00 | 0 | **1,00** | 1,00 |
| K17.2 veri kökü depo dışında | = 1 | 0 | **1** | 1 |
| K17.3 ekran sözleşmesi | ≥ 1,00 | 0 | **1,00** | 1,00 |
| K17.4 yasak anahtar yok | ≥ 1,00 | 0 | **1,00** | 1,00 |
| K17.5 tr/en sözlük tamlığı | = 1 | 0 | 0 | **1** |
| K17.6 dil modeli kapalıyken tam | = 1 | 0 | **1** | 1 |
| K17.7 127.0.0.1:8810 | = 1 | 0 | **1** | 1 |
| **Geçen** | | **0/7** | **6/7** | **7/7** |

## Notlar

- **Başlangıç:** `uygulama.sunucu` yok (ModuleNotFoundError) → 0/7; 7/7 öngörü
  doğrulandı (tanım gereği).
- **A5.1 — arka uç (`uygulama/sunucu.py`) + çalışma dizinine düşmenin kaldırılması.**
  0/7 → 6/7. 20 akışın 20'sinde HTTP hükmü MCP hükmüyle birebir (paket hash'i dahil); 84
  yanıtta yasak anahtar yok; depoda yeni dosya yok, 40 oturum dosyası veri kökünde, depo içi
  kök reddediliyor. K17.5 (tr/en sözlükleri) ön yüzle (A5.2) gelecek.
- **Ölçüm sırasında bulunan hata:** vaka dosyasındaki dil modeli adresi açıklama metni
  içeriyordu (`"http://127.0.0.1:9 (erişilemez …)"`); arka uç bu bozuk adreste
  `InvalidURL` fırlatıp sağlık ucunu ve TÜM akışları düşürüyordu (ilk koşu 1/7). Opsiyonel dil
  modeli yolu artık her hatayı "erişilemez" sayar (test: bozuk adres akışı düşürmez). Vaka
  dosyası kilitli olduğu için değişmedi; bozuk adres "dil modeli kapalı" anlamını korur.
- **Aynı sınıf (A3 bulgusu canlıydı):** çekirdek `SINAMA_LOG_DIR` yokken oturumu çalışma
  dizinine yazıyordu — A4.15 testlerimin yalıtılmış koşuları `cekirdek/oturumlar`'a 35 keşif
  oturumu bırakmıştı (sentetik; silindi). Artık veri köküne düşer
  (`guvenlik.varsayilan_veri_koku`), test dosyası kendi geçici dizinini kurar; tam kapı
  koşusundan sonra ne depoda ne kullanıcı veri dizininde oturum kalıyor.
- **A5.2 — ön yüz (`uygulama/web`, Vite + React + Tailwind; DataFlow'dan hasat edilen temeller).**
  6/7 → 7/7. tr/en sözlükleri 170 anahtar: çekirdekten türetilen aileler (kategori, rakip
  durumu, birincil durum, 10 RAK rakibi, 4 soru türü, 3 amaç, 10 hüküm kuralı) + ekranların
  her `t()` anahtarı + sınama/sonraki kanıt/birincil hipotez metinlerinin çevirisi.
  Çekirdeğin ürettiği gerekçe cümleleri ve araç uyarıları Türkçe kalır (ADR-003; İngilizce
  arayüzde not düşülür). Hata tipi → HTTP durumu eşlemesi (kapı 422, sistem 500) eklendi.
- **Tarayıcıdan uçtan uca (CI dışı, yerel; `sinama-a5` önizlemesi, sentetik veri, depo dışı
  veri kökü):** ARTIŞ/doğrulayıcı bildirim artefaktı → Plan (tavan DESTEKLENDİ, R-MEVSIM
  "veriye bağlı") → Hüküm BELİRSİZ, en güçlü rakip R-BILDIRIM (sürekli kanal payı 0,236,
  z −2,874) → İngilizceye geçiş → SONUÇ insan onayıyla kaydedildi; ETKİ/doğrulayıcı
  (müdahale/kontrol/tampon bölge değerleri seçimle) → Hüküm BELİRSİZ, en güçlü rakip
  R-ORTALAMAYA-DONUS (sentetik gerçek etki verisinde rakibin I. tip hatası — v7'de bilinen
  ~%6); SERİ/keşifsel Plan'ı tavan KIRILGAN. Konsol hatası yok. Ekran görüntüsü alınamadı
  (pencere arka planda; doğrulama metin ve erişilebilirlik ağacıyla yapıldı).
