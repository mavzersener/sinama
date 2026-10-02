# ADR-003 — A5: tek arka uç ve Rehberli yüz

- **Durum:** Kabul edildi — 02.10.2026 (proje sahibinin onayı: varsayılan tercihlerle;
  arayüzde İngilizce seçeneği de bulunur — DataFlow'da olduğu gibi). Taslak 01.10.2026'da
  otonom çalışma sırasında yazılmıştı.
- **Kapsam:** ADR-001 aşama tablosu A5 ("Tek arka uç ve Rehberli yüz — üç ekran uçtan
  uca"). A4 kapanmadan A5 açılmaz (ADR-001: aynı anda tek aşama; kapanış sahibindedir).

## Bağlam

- A4 sonunda çekirdek, bilim katmanı ve ölçüm hazır: 80+ MCP aracı, Rehberli akışın arka
  ucu (`rehberli_calisma`) ve ayrıntılı bilim araçları (`calisma_baslat`, `hipotez_ekle`,
  `sinama_plani`, `kanit_bagla`, `hukum` — A4.14, Rehberli ile eşdeğerliği testle kanıtlı),
  BMK v0–v9 CI'da.
- Kullanıcı yüzü yok: bugün program yalnız MCP üzerinden (dil modeli ya da el ile JSON)
  kullanılabiliyor.
- Veri kökü sorunu (A3'te bulundu): `SINAMA_LOG_DIR` verilmezse oturumlar ve kanıt
  zinciri **çalışma dizinine** yazılır (`arayuz/ortak.py::_log_dir`). Depo içinden
  çalıştırılırsa özel türev veri depoya düşebilir (bekçi commit'te yakalar ama yazımı
  önlemez).
- DataFlow'un React bileşenleri (C:\Projects\DataFlow) hasat kaynağıdır; Node arka ucu A6'da
  taşınır.

## Karar

1. **Tek süreç, tek port.** FastAPI arka ucu çekirdeği süreç içinde çağırır — ayrı
   hesap motoru yok; HTTP uçları araç kayıt defterinin (`ARACLAR`, `arac_calistir`) ince
   sarmalayıcısıdır: kapı, gerekçe, kanıt zinciri ve uyarılar MCP ile aynı yoldan geçer.
   Bağlanma yalnız 127.0.0.1. *Varsayılan tercih:* port 8810 (8080 Gemma, 8765/8790
   YerelAjan, 8002 HARP dolu).
2. **Rehberli yüz = üç ekran**, ayrıntılı bilim araçlarının sırasıyla:
   - **Soru:** soru türü (ARTIS / YOĞUNLAŞMA / SERİ / ETKİ), veri (veri kökünden dosya),
     amaç (doğrulayıcı / keşifsel / operasyonel) ve türün parametreleri (kanal alanı,
     MO alanı, bölge, müdahale/kontrol/tampon, kesinti tarihi). → `calisma_baslat`
   - **Plan:** hipotez seti (birincil + RAK rakipleri + H_bilinmeyen), sınama planı:
     hangi rakip bu parametrelerle önceden çözülemez, **ulaşılabilir en üst kategori**;
     serbest rakip ekleme; doğrulayıcıda "protokolü kilitle" onayı (onaylayan adıyla).
     → `hipotez_ekle`, `sinama_plani`, `kanit_bagla`
   - **Hüküm:** kategori, tetiklenen kurallar (iz), rakiplerin durumu ve ölçümleri,
     sonraki en iyi kanıt, H_bilinmeyen notu; "taslak" damgası; insan onayıyla SONUÇ.
     → `hukum`, `dongu_sonuc`
   Olasılık, yüzde ya da güven puanı gösterilmez (AGENTS kural 6).
   **Dil:** Türkçe varsayılan, İngilizce seçenek (DataFlow `src/i18n.ts` düzeni: tr/en
   sözlükleri, seçim tarayıcıda kalıcı). Çevrilen: arayüz metinleri, kategoriler, rakip
   durumları, soru türleri, amaçlar, RAK rakip adları ve hüküm kuralları (kod anahtarlı).
   Çekirdeğin ürettiği gerekçe cümleleri v1'de Türkçe kalır ve İngilizce arayüzde de
   öyle gösterilir (sayılar kanıt kaydına bağlıdır; makine çevirisi araya girmez).
3. **Veri kökü zorunlu ve depo dışı.** `SINAMA_VERI_KOKU` (oturumlar, kanıt zinciri,
   yüklenen veri); verilmezse `%LOCALAPPDATA%\sinama` (Linux: `~/.local/share/sinama`);
   düzen: `veri/` (girdi ve yüklemeler), `oturumlar/` (oturum + kanıt zinciri). Çalışma dizinine düşme
   kaldırılır; veri kökü depo içindeyse arka uç başlamayı reddeder (bekçinin yazım
   zamanı karşılığı). A3 bulgusu böylece kapanır.
4. **Dil modeli opsiyonel.** Yalnız (a) serbest soru metninden soru türü ve parametre
   **önerisi** (kullanıcı onaylar), (b) hüküm ifadesinin sade dile çevrilmesi. Sayı
   üretmez, hüküm kategorisini değiştiremez; 8080 kapalıyken üç ekran tam çalışır.
5. **Ölçüm önce (BMK v10, A5 uygulamasından ÖNCE ön-kayıt).** (a) Eşdeğerlik: HTTP
   Rehberli akışı MCP `rehberli_calisma` ile aynı paket hash'ini ve hükmü verir (v3–v9
   vakalarından örneklem); (b) veri kökü: hiçbir oturum dosyası depo içine yazılmaz;
   (c) üç ekran uçtan uca (tarayıcıdan) — ekran başına zorunlu öğeler (tavan, çözülemez
   rakipler, H_bilinmeyen, taslak damgası) ve yasak öğeler (olasılık/yüzde) denetlenir.
   Dil modelli sistem ölçütleri (`sistem_olcutleri`) ayrı ve opsiyonel ölçülür.
6. **Arayüz hasadı.** DataFlow React bileşenleri `git archive` ile (HASAT.md kaydıyla);
   Node uçları taşınmaz (A6).

## Kapsam dışı (A5)

Atölye / no-code editör (A6), çok kullanıcı ve kimlik doğrulama (tek kullanıcı, yerel),
uzak barındırma, dil modeliyle hüküm üretimi.

## Açık soruların yanıtları (02.10.2026)

1. Port 8810, veri kökü yukarıdaki gibi — **kabul** (varsayılan).
2. Dil modeli yardımı (öneri + sadeleştirme) A5'e **girer**, md. 4'teki sınırlarla;
   kapalıyken akış tam çalışır (BMK v10'da ölçülür).
3. Arayüz **Türkçe + İngilizce** (yukarıda "Dil").
4. P06 geri taşıma **A6'da** (varsayılan): DataFlow'un Sınama'ya geçişiyle birlikte.

## Uygulama düzeni

- `uygulama/` (depo kökünde): FastAPI arka ucu (`uygulama/sunucu.py`) ve ön yüz kaynağı
  (`uygulama/web/`, Vite + React + Tailwind, DataFlow'dan hasat). `cekirdek/` saf standart
  kitaplık kalır; FastAPI bağımlılığı yalnız `uygulama/`'dadır. Derlenmiş ön yüz
  (`uygulama/web/dist/`) depoya girmez; arka uç varsa onu sunar.

## Sonuçlar

- (+) Program ilk kez kullanıcı yüzü kazanır; hesap tek motorda kalır.
- (+) Veri kökü sorunu yapısal olarak kapanır.
- (−) FastAPI ve ön uç derleme zinciri yeni bağımlılıklar getirir (air-gap kurulum
  paketi A5 işine dahil edilmeli).
