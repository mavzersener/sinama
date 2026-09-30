# ADR-002 — Bilim katmanı v1: çalışma, hipotez seti, rakip açıklamalar, hüküm

- **Durum:** Kabul edildi — 30.09.2026 (proje sahibinin onayı; dört nokta aynen)
- **Kapsam:** A4'ün ikinci yarısı (ADR-001 aşama tablosu: "Bilim katmanı v1")
- **Uygulama:** A4.9 — BMK v3 0/12 → 12/12 (ön-kayıt `b65c8a9`); §7'nin ayrıntılı
  araçları (`calisma_baslat`, `hipotez_ekle`, `sinama_plani`, `kanit_bagla`,
  `hukum`) henüz yok — v1'de yalnız Rehberli giriş noktası (`rehberli_calisma`)
- **Değişiklik (A4.10, sınama v1.1):** bir rakip, ayırt edici sınamanın yalnız
  anlamlılığıyla değil **etki büyüklüğüyle** dışlanır (R-BILDIRIM: artışın çoğu
  sürekli kanallarda mı). Rakip kaydı ölçümü (`olcum`) hükme taşır. BMK v4 3/7 → 7/7
- **Değişiklik (A4.12, sınama v1.3):** ayrıştırmanın varyansı bileşene özgü yayılım
  çarpanıyla (her bileşen kendi Fisher testiyle kapılı). v1.2 (havuzlanmış tek φ)
  reddedildi (`d3ef040`). BMK v6 6/8 → 8/8

## Bağlam

- A4'ün ilk yarısı araçları dürüstleştirdi: çoklu test düzeltmesi (Gi*, LISA, anomali,
  yükselen sıcak nokta), anlamlılık sınaması (trend), belirsizlikli ITS, katmanlı seri
  adayı. BMK v0 12/15, v1 8/9, v2 10/10.
- Ama program hâlâ **araç çıktısı** üretir, **bilimsel hüküm** üretmez. Soru → hipotez
  seti → rakip açıklamalar → kanıt → kategorik hüküm zinciri yok. v0 V2'nin doğru
  hükmü ("kayıtlı artış bildirim değişikliğinden") ve `sistem_olcutleri`
  (zorunlu/yasak iddialar) bugün hiçbir kodla desteklenmiyor ve ölçülmüyor.
- Çekirdekte zemin hazır: PPDAC oturumu (durum makinesi), ön-kayıt kilidi
  (`surec/kilit.py`, doğrulayıcı çalışmada veriden önce zorunlu), yapılandırılmış
  gerekçe (hipotez + yorum + alternatifler), insan onayı, hash zinciri.
- Kaynak projelerde bu katmanın yarım denemeleri var; hiçbiri kategorik hüküm
  kuralı içermiyor:
  - science_gpt `domain.py` (190da89): araştırma amacı, `confirmatory`, H0/H1,
    kilit = onay + içerik hash'i, sapma politikası — **kavram olarak alınır**
    (pydantic; çekirdek yalnız standart kütüphane).
  - HARP `schemas.Hypothesis` (fbf3f31): `reasoning_trail` (kural, girdi, eşik,
    elenen) fikri alınır; `confidence` / `priority_score` ondalıkları **alınmaz**
    (AGENTS kural 6: sahte olasılık).

## Karar

### 1. Yer ve bütünlük

`cekirdek/sinama/bilim/` (yeni paket, yalnız standart kütüphane). Bilimsel nesneler
mevcut PPDAC oturumunun manifestosunda isteğe bağlı `bilimsel` alanında; her değişiklik
mevcut hash zincirine olay olarak yazılır. **İkinci bir kayıt defteri açılmaz.** Eski
oturumlar `bilimsel` alanı olmadan aynen yüklenir.

### 2. Çalışma (soru türü şablonları)

v1'de üç soru türü; her biri bir şablondur (birincil hipotez + makinece sınanabilir
öngörü + uygulanabilir rakipler):

| Tür | Örnek soru | Birincil öngörü (araç → koşul) |
|---|---|---|
| ARTIŞ | "X suçu arttı mı?" | `trend` → yorum = artan (eğim t-testi); `kesinti_analizi` varsa seviye GA'sı > 0 |
| YOĞUNLAŞMA | "A'da mekânsal yoğunlaşma var mı?" | `sicak_nokta_gi` → FDR'li sıcak hücre ≥ 1; `mekansal_kumelenme` anlamlı |
| SERİ | "Bu olaylarda seri var mı?" | `seri_eslestirme` → güçlü katmanda ≥ 1 aday |

ETKİ ("müdahale işe yaradı mı?", nedensel) v1.1'e bırakılır: kontrol grubu üreteci ve
yer değiştirme ölçütü ayrı BMK ister.

Çalışmanın **amacı** oturumun mevcut `amac` alanıdır (`operasyonel` / `dogrulayici` /
`kesifsel`). Doğrulayıcıda hipotez seti, veri bağlanmadan önce mevcut kilitle
hash'lenir (kilit zaten veriden önce zorunlu; kapsamı hipotez setine genişler).

### 3. Hipotez seti

- **BİRİNCİL** (tam bir tane), **RAKİP** (katalogdan otomatik + analist ekler),
  **BİLİNMEYEN** (`H_bilinmeyen`, zorunlu).
- `H_bilinmeyen` silinemez, birincil yapılamaz, hüküm almaz: "listelenen
  açıklamaların dışında kalan pay"ın yer tutucusudur. Her hüküm "listelenen rakiplere
  göre"dir ve bunu metninde söyler.
- Her hipotezin makinece değerlendirilebilir en az bir öngörüsü vardır:
  `{arac, argumanlar, olcut (sonuç içindeki yol), kosul}` ve bir yanlışlama koşulu.
  v1'de öngörüler şablondan gelir; serbest öngörü dili v1.1.
- Düzeltme eski kaydı silmez, `yerine_gecer` ile yenisini ekler.

### 4. Rakip Açıklama Kataloğu (RAK) v1

Her kayıt: kod, ad, uygulandığı soru türleri, mekanizma (deseni nasıl taklit eder),
**ayırt edici öngörü** (araç + koşul), veri gereksinimi (alan), etki (yüksek/orta),
kaynak. Veri ya da araç yoksa rakip **düşürülmez**, "çözülmedi" olarak kalır.

| Kod | Rakip | Türler | Ayırt edici sınama |
|---|---|---|---|
| R-RASTLANTI | Rastgele dalgalanma / küçük sayı / CSR / çoklu karşılaştırma | hepsi | Birincil öngörünün anlamlılık + FDR'si (araçlarda var) |
| R-BİLDİRİM | Kayıt/bildirim değişikliği (yeni kanal, sistem, tanım) | ARTIŞ | Kanal/kaynak alanı: artış kanallardan birinde mi, hepsinde mi |
| R-MEVSİM | Mevsimsellik | ARTIŞ | ≥ 24 ay: aynı ayların yıllar arası karşılaştırması |
| R-PAYDA | Risk altındaki nüfus/hedef değişimi | ARTIŞ (oran sorusu), YOĞUNLAŞMA | Nüfus/hedef alanı ile oran |
| R-VERİ | Veri kalitesi: yinelenen kayıt, varsayılan koordinat yığılması, eksiklik | hepsi | `veri_kalitesi` (mevcut kapı) |
| R-ORTAK-MO | Yaygın yöntem (taban oranı) | SERİ | A4.8 ayırt edicilik testi |
| R-TESADÜF-YAKINLIK | Farklı faillerin uzay-zaman yakınlığı | SERİ | MO kanıt hattı (A4.8) |

### 5. Kanıt bağlama

Araç koşusu (zincirdeki olay) → öngörü değerlendirmesi, **deterministik**: `tutuldu`
/ `karşıt` (anlamlı ters yön ya da yanlışlama koşulu) / `belirsiz` (anlamsız, düşük
güç) / `sınanamadı` (kapı reddi, eksik alan, araç hatası). Rakipler için aynı:
`dışlandı` / `destekleniyor` / `çözülmedi` / `uygulanamaz`. Dil modeli bu adımda yoktur.

### 6. Hüküm kuralları (sürümlü, sıralı, deterministik)

Kategoriler (AGENTS kural 6): **DESTEKLENDİ / KIRILGAN / BELİRSİZ / ÇELİŞKİLİ /
ÇEKİMSER**. Olasılık, yüzde, "güven puanı" yoktur.

1. **ÇEKİMSER** — kanıt zinciri bozuk; birincil öngörünün sınaması koşmadı ya da kapı
   reddetti; veri analize uygun değil.
2. **ÇELİŞKİLİ** — birincil öngörü `karşıt`.
3. **BELİRSİZ** — birincil öngörü `belirsiz` ("doğrulanmadı ≠ yanlış"); ya da
   yüksek etkili bir rakip `destekleniyor` (desen başka bir açıklamayla da
   uyumlu ve o açıklama sınandı).
4. **KIRILGAN** — birincil `tutuldu`, ama en az bir uygulanabilir rakip `çözülmedi`
   ya da sağlamlık uyarısı var (Durbin–Watson, kısa seri, kapsam kaybı, kararsız
   ağırlık).
5. **DESTEKLENDİ** — birincil `tutuldu`, uygulanabilir her rakip `dışlandı`,
   sağlamlık temiz **ve** çalışma doğrulayıcı (kilitli).

**Tavanlar** (kuraldan sonra uygulanır):
- Keşifsel ve operasyonel çalışma en çok KIRILGAN'dır (ön-kayıtsız: hipotez üretir,
  sınamaz).
- SERİ en çok KIRILGAN'dır ve insan onayı ister: desen ≠ fail; "aynı fail" iddiası
  hiçbir kategoride üretilmez.

**Çıktı:** kategori; tetiklenen kurallar (HARP'ın izi gibi: kural, girdi, eşik); en
güçlü rakip; çözülmemiş rakipler; **sonraki en iyi kanıt** (çözülmemiş rakibin veri ya
da sınama gereksinimi; sıralama şeffaf kuraldır, sayısal "bilgi kazancı" yoktur);
insan onayı gerekip gerekmediği; kural sürümü.

**Bağımsızlık:** hüküm işlevi yalnız dondurulmuş kanıt paketinden (hash'iyle) okur;
hipotez ya da kanıt yazamaz. Aynı paket + aynı kural sürümü = aynı hüküm.

### 7. Araçlar (eklemeli; mevcut 79 aracın adı ve sözleşmesi değişmez)

`calisma_baslat` (döngüyü + soru türü şablonunu + RAK rakiplerini + H_bilinmeyen'i
kurar), `hipotez_ekle` (rakip ekler; H_bilinmeyen korunur), `sinama_plani` (hangi
araç hangi öngörüyü sınar; veri eksikse neyin çözülmeyeceğini önceden söyler),
`kanit_bagla` (döngü analiz adımını öngörülere bağlar), `hukum` (kategorik özet).
İnsan onayı olmadan hüküm "taslak"tır; döngünün SONUÇ fazına insan onayıyla geçer.

**Rehberli giriş noktası:** `rehberli_calisma` — ADR-001'in Rehberli yüzünün (Soru →
Plan → Hüküm) arka ucu: yukarıdaki adımları tek deterministik akışta, aynı zincire
yazarak koşar. Ayrıntılı araçlar dil modeli ve Atölye içindir; BMK v3 Rehberli akışı
ölçer (ürünün varsayılan yolu). Sözleşmesi BMK v3 ön-kaydında kilitlenir.

## Ölçüm — BMK v3 (uygulamadan ÖNCE ön-kayıt)

Gerçeği bilinen vakalarda **doğru kategorik hüküm**. Taslak ölçütler:

- V2 bildirim artefaktı (mevcut üreteç, yeni tohumlar): "suç arttı" DESTEKLENDİ
  oranı ≤ 0,10; en güçlü rakip R-BİLDİRİM ≥ 0,90.
- Gerçek artış (her kanalda, ≥ 24 ay, doğrulayıcı): DESTEKLENDİ ≥ 0,80 — sistemin
  her şeye "kırılgan" diyerek geçmesini engeller. Aynı vaka keşifsel: DESTEKLENDİ = 0.
- V1 odaklı / rastgele: odaklıda DESTEKLENDİ|KIRILGAN ≥ 0,90; rastgelede ≤ 0,10.
- V8 seri / seri yok: seride DESTEKLENDİ = 0 (tavan), KIRILGAN ≥ 0,80; seri yokta
  KIRILGAN ≤ 0,10.
- Değişmezler: H_bilinmeyen %100; hüküm çıktısında sayısal olasılık 0; aynı paket
  aynı hüküm %100.

Başlangıç ölçümü (bugünkü çekirdek hüküm üretmiyor) tanım gereği başarısızdır; v3'ün
değeri ön-kayıtlı spesifikasyon ve gerileme bekçisi olmasıdır. Öngörüler ve eşikler
kodlamadan önce kilitlenir.

## Kapsam dışı (v1)

Dil modeli değerlendiricisi, ETKİ soru türü, serbest öngörü dili, sayısal bilgi
kazancı, sonuç (outcome) kaydı ve kalibrasyon, OOD, genel bootstrap, arayüz (A5).

## Sonuçlar

- (+) "Sayı" ile "hüküm" arasındaki boşluk kapanır; sistem ölçütleri (zorunlu/yasak
  iddialar) çekirdek düzeyinde ölçülebilir olur.
- (+) Gerçek verinin çoğunda nüfus/devriye alanı olmadığından hükümlerin çoğu KIRILGAN
  çıkacaktır. Bu bir kusur değil, dürüst sonuçtur; "sonraki en iyi kanıt" hangi verinin
  eksik olduğunu söyler.
- (−) Şablonlar üç soru türüyle sınırlı; serbest soru v1.1'e kadar yalnız keşifsel.
- Geri dönüş: katman eklemelidir; kaldırılırsa mevcut araç ve döngü aynen çalışır.

## Onaylanan noktalar (30.09.2026)

1. v1 soru türleri: ARTIŞ, YOĞUNLAŞMA, SERİ (ETKİ v1.1'e).
2. Tavanlar: keşifsel/operasyonel → en çok KIRILGAN; SERİ → en çok KIRILGAN.
3. "Rakip destekleniyor" → BELİRSİZ (ÇELİŞKİLİ değil): gözlem gerçekti, açıklaması
   tartışmalı.
4. Sıra: ADR onayı → BMK v3 ön-kayıt (kilit) → uygulama → ölçüm.
