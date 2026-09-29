# GELİŞME PLANI — suç analizi MCP sunucusu (v6.4 sonrası)

**Tarih:** 2026-07-18 · **Temel:** v6.4.0 (60 araç, 137 birim test, 5.372 satır üretim kodu)
**Yöntem:** Bu plan varsayım değil, ölçüm üzerine kuruludur. Her madde denetimde bulunan
somut bir bulguya (dosya:satır) ve bir yazılım ilkesine bağlanır.

---

## 0. Yol gösterici ilkeler

1. **Kanıt bütünlüğü her şeyin üstündedir.** Analiz sonucu yanlış olabilir (insan denetiminde
   düzeltilir); kanıt zincirinin sessizce kopması kabul edilemez.
2. **Sessiz yanlış, gürültülü hatanın en tehlikelisidir.** Kollukta birim hatası, test edilmemiş
   zaman serisi, yutulmuş istisna — bunlar kaza değil, tasarım açığıdır.
3. **Tek kapı, tek otorite.** v6.0'dan beri kazanılan mimari disiplin geri alınmaz.
4. **Sıfır bağımlılık (stdlib).** Air-gap kolluk ortamı kısıtı pazarlık konusu değildir.
   Geliştirme araçları da stdlib'den seçilir (`trace`, `logging`, `unittest`).
5. **YAGNI ölçüm kapısı.** Performans ve soyutlama işleri ancak ölçülmüş acıyla açılır
   (Faz G'deki grid indeksi örneği).
6. **Doktrin = icra eden test.** Bu plandan çıkan her yapısal kural, kanıt testiyle birlikte
   gelir; `DOKTRIN_KAPSAM` haritası güncellenmeden faz kapanmaz.
7. **Her faz bağımsız teslim edilir.** Her fazın sonunda tüm testler yeşil, zip doğrulanmış,
   CHANGELOG yazılmış olur. Açık iş bırakılmaz.

---

## 1. Denetim bulguları özeti

| # | Bulgu | Yer | İlke ihlali | Şiddet |
|---|-------|-----|-------------|--------|
| A1 | Manifesto yazımı atomik değil — çökme ortasında bozuk JSON, bir sonraki `yukle` çöker | `surec/dongu.py:248` (`open(yol,"w")` doğrudan) | Fail-safe | **Kritik** |
| A2 | Olay akışında fsync yok; yazım sırası (olay→manifesto) çökmede mükerrer olay üretebilir (`olay_sayaci` manifestoda tutuluyor) | `surec/kanit.py:77`, `surec/dongu.py` `kaydet` | Dayanıklılık | **Kritik** |
| A3 | Keşif oturumu yazılamazsa analiz yine de döner; kanıt sessizce kaybolur (sadece stderr log) | `arayuz/sunucu.py:55` | Sessiz yanlış | **Kritik** |
| A4 | Açılışta manifesto ↔ olay akışı uzlaştırması (reconciliation) yok | `surec/dongu.py` `yukle` | Doğrulama | Yüksek |
| B1 | Hata taksonomisi yok: 18× `ValueError` hem böcek hem "yetersiz veri" için; agent düzeltici eylem seçemiyor | tüm `cekirdek/` + `arayuz/sunucu.py:113` | Anlamlı hata | Yüksek |
| B2 | `isle()` 75 satır: şema→gate→oturum→araç→kapat→meta→hata iç içe | `arayuz/sunucu.py:68` | SRP | Orta |
| C1 | `araclar.py` 829 satır / 60 araç, altı analitik alan karışık | `arayuz/araclar.py` | Kohezyon | Orta |
| C2 | `ortak.py` 433 satır: sabitler + PII + audit + registry + gate kancaları + paylaşılan şemalar | `arayuz/ortak.py` | Kohezyon ("ortak" çöplüğü) | Orta |
| C3 | `kapi()` 87 satır; kural eklemek fonksiyon içinde gezinmeyi gerektiriyor | `kalite/kapi.py:40` | Veri-odaklı tasarım | Orta |
| D1 | **Doğrudan birim testi olmayan çekirdek modüller: `zaman`, `orneklem`, `skor`, `degerlendirme`** — `kontrol_grafigi`, `cusum`, `trend`, `gun_saat_analizi` hep `zaman.gunluk_seri`'ye dayanıyor; golden test yok | `tests/` eşleşmesi | Test piramidi | **Kritik** |
| D2 | 60 aracın yalnızca ~15'i uçtan uca (MCP) testli; `{sonuc, meta}` sözleşmesi çoğu araçta denetlenmiyor | `test_mcp.py` çağrı sayımı | Sözleşme testi | Yüksek |
| D3 | Kapsam ölçümü yok; regresyon takibi "OK" ibaresine indirgenmiş | `test.sh` | Ölç-göster | Düşük |
| E1 | `log()` = seviyesiz `print(stderr)`; audit ile uygulama logu aynı boruda | `arayuz/ortak.py:36` | Gözlemlenebilirlik | Düşük |
| E2 | Docstring %60, tip notu %0; public fonksiyonlarda **birim** (km/gün/oran) dokümante değil | 280 fonksiyon ölçümü | Dokümantasyon | Orta |
| F1 | Yayın süreci elle: bu oturumda `/mnt` üzerinde boş zip (0 bayt) üretildi, taze-açılım doğrulaması sonradan yakaladı | oturum kaydı | Tekrarlanabilirlik | Yüksek |
| F2 | `PROTOKOL = "2024-11-05"` sabit; initialize'da sürüm anlaşması yok — agent uyumluluğu şansa bağlı | `arayuz/ortak.py:23`, `sunucu.py:73` | Savunmacı protokol | Orta |

---

## 2. Fazlar

### FAZ H1 — Kanıt dayanıklılığı (A1–A4) · Öncelik: P0 · Emek: orta ✅ v6.5

**Gerekçe:** Sistemin varoluş nedeni kanıt zinciri; üç kritik bulgu da aynı tema etrafında.

| İş | Ayrıntı | Kabul kriteri (test) |
|----|---------|----------------------|
| H1.1 Atomik manifesto | temp dosyaya yaz + `os.replace`; `dongu.kaydet` ve kanıt akışı için ortak `_atomik_yaz` yardımcısı | Yazım ortasında enjekte edilen hatada eski manifesto bozulmadan kalır |
| H1.2 fsync + idempotent kaydet | olay append'inden sonra `f.flush(); os.fsync`; `olay_sayaci` manifestodan değil **akıştan** türetilir (`_akis_uzunlugu`) → çökme sonrası mükerrer yazım yapısal olarak imkânsız | Çökme simülasyonunda (yazımlar arası öldürme) yeniden açılışta zincir sağlam, mükerrer olay yok |
| H1.3 Kanıt kaybı gürültülü | keşif oturumu yazılamazsa sonuç `meta.kanit_durumu: "YAZILAMADI"` + `meta.uyarilar` başa eklenir; resmi modda `sonucla` bunu reddeder | Yazım hatası enjekte edilir → cevapta bayrak görünür; stderr dışında kullanıcı da görür |
| H1.4 Açılış uzlaştırması | `yukle` sırasında manifesto `gecmis` sayısı vs akış satır sayısı; uyuşmazlık → uyarı + `kanit_dogrula` önerisi | Bozdurulmuş çiftte `yukle` uyarı verir, sessizce devam etmez |

**Doktrin adayı:** "Kanıt yazımı atomiktir ve kaybı asla sessiz değildir" → `DOKTRIN_KAPSAM`'a işlenir.

### FAZ H2 — Hata taksonomisi + dispatch boru hattı (B1–B2) · Öncelik: P0/P1 · Emek: orta ✅ v6.5

| İş | Ayrıntı | Kabul kriteri |
|----|---------|---------------|
| H2.1 Hata sınıfları | `cekirdek/hatalar.py`: `VeriHatasi` (yetersiz/kirli — kullanıcı düzeltebilir), `KapiRed` (politika), `DonguHatasi` (süreç), `SistemHatasi`. 18 `ValueError` sınıflandırılır; "yetersiz veri" türü mesajlar `VeriHatasi(min_n=...)` taşır | Her hata cevabı yapısal alan taşır: `{hata_tipi, duzeltme_onerisi}` — llama.cpp agent'ı düzeltici eylem seçebilir |
| H2.2 `isle()` boru hattı | 75 satırlık fonksiyon adımlara ayrılır: `_sema_adimi → _gate_adimi → _oturum_adimi → _yurut → _meta_adimi`; davranış bit-bit aynı | Mevcut 137 test + test_mcp değişmeden yeşil (refactor kanıtı) |
| H2.3 Hata→test haritası | her hata sınıfı için en az bir MCP seviyesi test | test_mcp'ye 4 senaryo |

**Not:** H2.1, kullanıcının yerel agent'ının kendi kendine düzeltme (self-healing) kalitesini
doğrudan artırır — no-code hedefinin omurgası.

### FAZ H3 — Test tabanını kapatma (D1–D3) · Öncelik: P1 · Emek: orta ✅ v6.6 (cırcır borcu ✅ v6.8: çekirdeğin tamamı ≥%82, genel %93.1)

| İş | Ayrıntı | Kabul kriteri |
|----|---------|---------------|
| H3.1 `zaman` golden testleri | `gunluk_seri`, `saat/gun/ay_dagilimi`, `holt_winters` giriş serisi için elle hesaplanmış değerler; hafta sonu/kayıp gün kenarları | `tests/test_zaman.py` — en az 10 golden |
| H3.2 `orneklem`, `skor`, `degerlendirme` | tabakalı örneklemin tabaka oranları; `toplu_skorla` ağırlık toplamı; DiD elle hesap | 3 yeni test dosyası veya mevcutlara bölüm |
| H3.3 Araç sözleşme testi jeneratörü | registry üzerinden 60 aracın her birine minimal geçerli çağrı üreten meta-test: şema var, `-32602` dönmez, `{sonuc, meta}` döner, `meta.uyarilar` liste | 60 araç × 1 sözleşme testi; yeni araç eklendiğinde otomatik kapsanır |
| H3.4 Kapsam ölçümü (stdlib) | `python -m trace --count` dev-time raporu; `test.sh` sonuna özet satırı | çekirdek modüllerin satır kapsamı raporda görünür; eşik: yeni kod %80 altına düşemez |

**İlke:** Test piramidinin tabanı (birim) sağlam olmadan üst kat (doktrin icrası) göstermeliktir.

### FAZ H4 — Modül olgunlaştırma (C1–C3) · Öncelik: P2 · Emek: orta-büyük · **Davranış değişmez** · katman testleri ✅ v6.7 (tetikleyiciler bekliyor: 60<70 araç, ortak.py 445<500)

Sıkıştırma değil, olgunlaştırma: v6.1 god-module'dan çıkardı, bu faz büyümenin
doğal sınırlarını çizer.

| İş | Ayrıntı | Tetikleyici (YAGNI kapısı) |
|----|---------|----------------------------|
| H4.1 `araclar/` paketi | `araclar.py` → `araclar/{tanimlayici,hipotez,mekansal,zamansal,iliski,surec}.py`; registry ve araç adları aynı kalır | 829 satır → 70+ araca ulaşınca **veya** yeni alan eklenince |
| H4.2 `ortak.py` sınır çizme | bölümler ayrı modüllere: `sablonlar` (şemalar), `pii`, `kayit_defteri` (registry); `ortak.py` ince re-export | `ortak.py` 500 satırı aşınca |
| H4.3 `kapi()` kural tablosu | 87 satırlık fonksiyon → `KURALLAR = [(kosul, karar, sebep), ...]` veri yapısı + küçük değerlendirici; kural eklemek = satır eklemek | bir sonraki kapı kuralı eklenirken |

**Disiplin:** Bu faz tek başına yapılmaz; tetikleyici iş geldiğinde o işle birlikte yapılır
(boy scout kuralı kurumsallaşmış hâli). Katman ihlali testleri (çekirdek arayüzü import etmez)
varsa genişletilir, yoksa bu fazda eklenir.

### FAZ H5 — Gözlemlenebilirlik + dokümantasyon standardı (E1–E2) · Öncelik: P2 · Emek: küçük ✅ v6.7

- `log()` → stdlib `logging` (seviye + modül etiketi); **audit akışı ayrı kalır** (kanıt niteliğinde).
- Public çekirdek fonksiyonlarda docstring standardı: `Args/Returns` + **birim** zorunlu
  (`mesafe_km`, `pencere_gun`, `oran`). Kollukta birim belirsizliği = yanlış rapor.
- Doğrulama: docstring kapsamı %60 → %85 hedefi; birim içermeyen public imza kalmaz
  (basit AST denetimi teste dönüştürülür — mevcut meta-test geleneğine uyar).

### FAZ H6 — Yayın mühendisliği (F1–F2) · Öncelik: P1 · Emek: küçük

| İş | Ayrıntı |
|----|---------|
| H6.1 `release.sh` ✅ v6.5 | tek komut: test paketi → wheel → **/tmp'de** zip kur → taze açılımda tam test → ancak hepsi yeşilse `/mnt/agents/output`'a kopyala. Bu oturumdaki boş-zip vakası (0 bayt) yapısal olarak tekrarlanamaz |
| H6.2 Protokol anlaşması ✅ v6.6 | `initialize` cevabında desteklenen protokol listesi; bilinmeyen sürümde reddetmek yerine en yakın uyumlu davranış + `meta.uyarilar`. Agent ekosistemi (2025 protokolleri) kırılmadan taşınır |
| H6.3 Sürüm doğrulaması ✅ v6.5 | `pyproject.toml` ↔ `ortak.SURUM` ↔ `__init__.__version__` ↔ CHANGELOG başlığı tutarlılık testi (dört kaynak tek gerçek) |

---

## 3. Sıralama ve bağımlılıklar

```
H1 (kanıt dayanıklılığı) ──┐
                            ├──► v6.5 "dayanıklılık"  (P0 demeti)
H2 (hata taksonomisi)    ──┘
H6.1 (release.sh) ──────────────► hemen, bağımsız, küçük (P1, acısı taze)
H3 (test tabanı) ───────────────► v6.6 "güven tabanı" (P1)
H6.2+H6.3 ──────────────────────► v6.6 ile birlikte
H4, H5 ─────────────────────────► v6.7 "olgunlaştırma" (P2, tetikleyici-kapılı)
```

**Neden bu sıra:** (1) Kanıt bütünlüğü ve hata kalitesi kullanıcıya dokunan güven meselesidir;
(2) `release.sh` ucuz ve acısı bu oturumda yaşanmıştır; (3) test tabanı kapatılmadan yapılacak
her refactor (H4) kör uçuştur — bu yüzden H4, H3'ten sonradır.

## 4. Açıkça yapılmayacaklar (YAGNI listesi)

- GUI / web arayüzü — kapsam dışı; MCP + no-code agent yeterli.
- Üçüncü taraf bağımlılık (numpy/pandas dahil) — air-gap kısıtı.
- Async / çok kullanıcılı eşzamanlılık — tek yerel agent, tek süreç; ihtiyaç ölçülmeden açılmaz.
- Yeni analitik yöntemler — bu plan mühendislik planıdır; metodoloji genişlemesi ayrı bir
  belgeyle ve ölçüm/gereksinim kapısıyla gelir.

## 5. Kapanış disiplini (her faz için)

1. Tüm testler yeşil + yeni yapısal kural varsa `DOKTRIN_KAPSAM` güncel.
2. `test.sh` tam tur + `release.sh` (H6.1'den sonra) ile zip doğrulaması.
3. CHANGELOG girdisi + sürüm tutarlılığı.
4. Zip: `/tmp`'den kur, taze açılımda doğrula, sonra teslim.
