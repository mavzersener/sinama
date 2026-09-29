# Saf Python Suç Analizi Kütüphanesi (No-Code Analiz Programı Çekirdeği) — v6.8

Kolluk personeli için no-code analiz uygulamasının analitik motoru.
**Hiçbir dış paket veya repo bağımlılığı yoktur** — yalnızca Python 3.8+
standart kütüphanesi kullanır. Kapalı ağda / internetsiz ortamda çalışır.

v2'de Maxfield & Babbie, *Research Methods for Criminal Justice and
Criminology* (8. baskı) temel alınarak örnekleme (Bölüm 8), ölçüm ve bileşik
endeks (Bölüm 5), değerlendirme araştırması (Bölüm 13) ve veri yorumlama /
ilişki ölçüleri (Bölüm 14) kapsamındaki yöntemler eklendi; ayrıca ileri suç
analizi teknikleri (CUSUM, Poisson, Rossmo, RTM, Benford vb.) genişletildi.

## Analiz Listesi (toplam 60+)

### veri.py — Veri Yükleme ve Kalite
1. CSV/TSV yükleme (otomatik ayıraç algılama)
2. Otomatik tiplendirme
3. Çok formatlı tarih çözümleme
4. Eksik veri raporu
5. Koordinat doğrulama

### istatistik.py — Temel İstatistik
6. Frekans dağılımı
7. Özet istatistik (ortalama, medyan, std. sapma, min, maks)
8. Çapraz tablo
9. Yüzdelik
10. Z-skor anomali
11. Dönemsel değişim oranı
12. Kayan ortalama
13. Doğrusal trend

### zaman.py — Zamansal Analiz
14. Saat dağılımı
15. Haftanın günü dağılımı
16. Ay serisi
17. Günlük seri (eksik gün doldurma)
18. Aoristik dağılım

### mekan.py — Mekânsal Analiz
19. Haversine mesafe
20. Grid hotspot
21. KDE ısı yoğunluğu (saf Python Gauss çekirdeği)
22. Hotspot hücre çıkarımı (üst yüzdelik)
23. NNI kümelenme testi
24. Tampon alan sorgusu

### tekrar.py — Tekrar ve Seri Analiz
25. Mükerrer mağduriyet
26. Yakın-tekrar çiftleri
27. Knox tablosu
28. Seri suç eşleştirme (MO Jaccard)

### ag.py — Ağ Analizi
29. Birlikte-olay ağı (co-offending)
30. Derece merkeziyeti
31. Aracılık merkeziyeti (Brandes)
32. Bağlı bileşenler
33. Topluluk tespiti (label propagation) — YENİ
34. PageRank — YENİ
35. Ego ağı çıkarımı — YENİ
36. En kısa yol (bağlantı zinciri) — YENİ

### kume.py — Küme İşlemleri ve Bulanık Eşleşme
37. Kesişim / birleşim / fark
38. N-liste çoklu çakıştırma
39. Levenshtein mesafesi
40. Benzerlik oranı
41. Bulanık kayıt eşleştirme

### skor.py — Risk Skorlama ve Uyarı
42. Ağırlıklı kural motoru (kod yazmadan kural tanımı)
43. Toplu risk skorlama
44. Eşik uyarıları

### orneklem.py — Örnekleme (Kitap Bölüm 8) — YENİ
45. Basit tesadüfi örneklem
46. Sistematik örneklem
47. Tabakalı örneklem (orantılı/orantısız)
48. Örnekleme hatası
49. Güven aralığı (oran ve ortalama)
50. Gerekli örneklem büyüklüğü

### iliski.py — Suç Oranları ve İlişki Ölçüleri (Bölüm 6/14) — YENİ
51. Suç oranı (100.000 kişi başına, UCR standardı)
52. Bölge oran tablosu
53. Ki-kare bağımsızlık testi (p-değeri dahil, saf Python gamma fonksiyonu)
54. Cramér's V
55. Lambda (nominal PRE ölçüsü)
56. Gamma (ordinal ilişki)
57. Pearson r ve r²

### olcek.py — Bileşik Ölçüm (Bölüm 5) — YENİ
58. Min-max normalizasyon (ters gösterge destekli)
59. Ağırlıklı bileşik endeks kurma (Index of Disorder mantığı)
60. Cronbach alfa güvenilirliği
61. Ölçüm düzeyi önerisi (uygun istatistiği belirler)

### degerlendirme.py — Değerlendirme Araştırması (Bölüm 13) — YENİ
62. Öncesi-sonrası karşılaştırma
63. Farkların farkı (DiD, kontrol gruplu yarı-deneysel)
64. Kesintili zaman serisi (seviye + eğim değişimi)
65. SARA döngüsü kontrol listesi

### ileri.py — İleri Suç Analizi — YENİ
66. Kontrol grafiği (±3σ aşım günleri)
67. CUSUM (kalıcı artış tespiti)
68. Poisson anomali (bölge bazında p-değerli)
69. Gün×saat ısı matrisi + en riskli dilimler
70. Dönemsel hotspot karşılaştırma (yeni/yükselen/kalıcı/zayıflayan/sönen)
71. Coğrafi profil — Rossmo journey-to-crime
72. Risk arazi modeli (RTM, ağırlıklı katman bindirme)
73. Olaylar arası süre (seri ritmi)
74. Benford yasası testi (uydurma sayı tespiti)
75. k-means olay gruplama
76. Holt-Winters kısa vadeli tahmin (mekanik projeksiyon)

### dongu.py — PPDAC Analiz Döngüsü (Crime Analyst's Companion) — YENİ v5.3
77. Döngü başlatma: talep kaydı + ürün türüne göre araç planı (taktik/
    stratejik/sorun çözme şablonları, Stratified Analysis Model)
78. VERİ fazı: profil + fitness gate otomatik bağlanır
79. VERİ→ANALİZ kapısı: gate "uygun değil" derse geçiş reddedilir
80. Döngü içi analiz: her araç çağrısı manifestoya işlenir; faz atlama
    ve iç içe döngü engellenir
81. SONUÇ fazı: insan onayı zorunlu (onaylayan adı + notu kayıtlı)
82. İzleme planı (3T-Tracking): metrik + eşik + kontrol tarihi ile
    döngü kapanır, yeni döngüye beslenir
83. Oturum manifestosu: JSON kalıcılığı, tüm geçmiş adımlar denetlenebilir

### zarar.py — Crime Harm Index (CHI) — YENİ v5.3
84. Zarar tablosu: olay sayımı yerine ağırlıklı zarar (gün-ceza esaslı);
    kurum ağırlık tablosu JSON ile jürisdiksiyona özel
85. Power Few: zararın %50'sini üreten en küçük birim kümesi (Pareto)
86. Hacim–zarar ayrışması: "seyrek ama ağır" / "yoğun ama hafif" birimler
87. Ağırlıklı KDE: zarar-ağırlıklı harm-spot haritası (mekan.py)

### rapor.py — Analiz Ürünleri — YENİ v5.3
88. Taktik brifing (saha personeli; hotspot + gün/saat + yakın tekrar +
    power few)
89. Stratejik değerlendirme (komuta; trend + oranlar + anomali + güç notu)
90. Belirsizlik ve sınırlar bölümü zorunlu — beyansız ürün üretilmez

### kanit.py + muhakeme izi — Birleşik Kanıt Mimarisi — YENİ v6.2
91. Katman 1: oturum bazlı değişmez olay akışı (JSONL; delta yazımı;
    PII değeri asla yazılmaz; hash-zinciri P2'ye hazır)
92. Katman 2: manifesto = akışın anlamsal projeksiyonu (tek kaynak;
    kanit.projeksiyon ile doğrulanabilir)
93. Katman 3: muhakeme izi — her analiz adımında OLGU (K1/K2) ve
    GEREKÇE (K3) görsel ayrımlı Markdown; brifinge otomatik eklenir
94. Yapılandırılmış gerekçe zorunluluğu: dongu_analiz'de
    {hipotez, yorum} şart; yorumsuz adımla sonuca geçilemez (yapısal)

### Faz E — Metodolojik derinlik — YENİ v6.3
95. Negatif binom anomali testi: aşırı yayılımda p-değerleri NB'den;
    model seçimi formal Fisher dispersiyon testiyle; yayılım parametresi
    üst %10 kırpılmış (maskeleme önlemi — uç bölge kendini boğduramaz)
96. oran_karsilastir aracı: iki Poisson oranının koşullu exact testi +
    RR Clopper-Pearson GA (öncesi/sonrası, müdahale/kontrol)
97. NNI Donnelly kenar düzeltmesi (kenar_duzeltme=true; çevre terimli
    beklenen + varyans)
98. Knox analitik beklenti: MC p yanında bağımsızlık altında kapalı-form
    beklenti (yakınsama doğrulamalı)

### Faz F/G + P2 — Yapısal pekiştirme — YENİ v6.4
99. Mekânsal grid indeksi (ölçümlü optimizasyon): NNI 22.3s→0.25s,
    Knox çift sayımı 5.9s→0.03s; sonuçlar kaba kuvvetle birebir aynı
100. Hash-zincirli kanıt akışı (P2): her olay öncekinin SHA-256'sına
    zincirli; kanit_dogrula aracı bütünlüğü sınar (kurcalama saptanır)
101. Doktrin-enforcement kapsam haritası: her yapısal kuralın kanıt
    testi var; meta-test haritanın canlılığını denetler
102. Nominal alanda sayısal özet yapısal red (dagilim_olculeri kapıda);
    kurum ağırlık tablosu .json erişimi düzeltildi

### kalite.py — Tek Gate Otoritesi — YENİ v6.0
91. `kapi(profil, analiz, **baglam)`: bütün fitness-gate kuralları tek
    fonksiyonda; `veri.analiz_uygun_mu` buraya delege eder
92. Dispatch-path gate: gate'li her analiz aracı (standalone VEYA döngü
    içi) çalışmadan önce aynı kapıdan geçer; araç-içi gate kodu yoktur
93. `KapiRed`: gate reddi = yapısal istisna ("HATA: fitness gate: ..."),
    yumuşak sözlük yok — tutarlı istemci sözleşmesi
94. Kapı kararı meta'ya işlenir: `meta.gate` + danışma sebepleri
    `meta.uyarilar`'da (sessiz geçiş yok)
95. Bağlam kancaları: payda (suc_oranlari), beklenen hücre (ki_kare),
    mertebe (benford), dispersiyon+bölge sayısı (bolge_anomali),
    tür kardinalite+dominans (zarar), örneklem büyüklüğü (t/anova/regresyon)

## Hızlı Başlangıç

```bash
python demo.py     # çekirdek 9 analiz grubu
python demo2.py    # kitap temelli + ileri analizler
```

## Metodolojik Notlar (kitap referanslı)
- Suç oranları ham sayı yerine 100.000 nüfus başına standartlaştırılır
  (Bölüm 14, "Computing Rates").
- Ki-kare sıfır hipotezini test eder: iki değişken arasında ilişki YOK;
  p < 0.05 ise ilişki örnekleme hatasıyla açıklanamaz (Bölüm 14).
- Lambda/gamma/Pearson seçimi ölçüm düzeyine bağlıdır; nominal veride
  ortalama hesaplamak geçersizdir (Bölüm 5).
- Değerlendirmede tek grup öncesi-sonrası zayıf tasarımdır; mümkünse
  kontrol gruplu DiD kullanın (Bölüm 13).
- Analiz süreci döngüseldir (PPDAC): Problem → Plan → Veri → Analiz →
  Sonuç → izleme üzerinden yeni problem. Tek seferlik "harita üret" değil,
  karar için kayıtlı süreç (Crime Analyst's Companion).
- Olay sayımı hacim yanılgısı yaratır: 100 hırsızlık ≠ 1 cinayet.
  Zarar ağırlığı (CHI) önceliklendirmeyi değiştirir; ağırlık tablosu
  kurum tarafından onaylanmış olmalıdır.
- "Her algoritmanın bir analiste ihtiyacı vardır": hiçbir çıktı insan
  onayı olmadan karara dönüşmez; belirsizlik beyanı zorunludur.
- Doğruluk ajanın itaatine değil sistemin inşasına dayanır (v6.0):
  fitness gate tek otoritedir (`kalite.kapi`) ve her analiz çağrısı
  — standalone ya da döngü içi — aynı kapıdan geçer. Gate'siz analiz
  yolu yoktur; doktrin küçülür, inşa büyür.

## Mimari (v6.1 — katmanlı yapı)
```
sinama/
  cekirdek/   16 saf modül (istatistik + veri erişimi; dışa bağımlılık yok)
  kalite/     profil.py + kapi.py (TEK gate otoritesi) + guvenlik.py
  surec/      dongu.py (PPDAC durum makinesi) + rapor.py (ürünler)
  arayuz/     ortak.py + araclar.py (57 ince adaptör) + sema.py +
              sunucu.py (yalnız JSON-RPC transportu)
```
Kurallar: gate mantığı yalnız `kalite/kapi.py`'de yazılır; uygulama tek
noktada (`dispatch_gate`); araç katmanında gate kodu yoktur. Gate'li her
analiz çağrısı — standalone bile — arka planda minimal keşif oturumu
açar (G3): profil, kapı kararı ve adım izi manifestoya düşer. Eski düz
import yolları (`from sinama import mekan` vb.) korunur.

## Güvenlik Notu
Modüller ağ erişimi açmaz, dış servis çağırmaz. KVKK kapsamındaki
verilerde yayın öncesi koordinat maskeleme (jitter) önerilir.


## MCP Sunucusu (v3) — Lokal Agent Entegrasyonu

`mcp_sunucu.py`, kütüphanenin 28 analizini MCP (Model Context Protocol)
aracı olarak sunar. **Resmi MCP SDK'sı dahil hiçbir dış bağımlılık yoktur** —
stdio transport üzerinde satır bazlı JSON-RPC 2.0 konuşur (protokol
2024-11-05). llama.cpp tabanlı lokal agent'lar, Claude Desktop ve herhangi
bir MCP uyumlu istemciyle çalışır.

### Kurulum
1. Tüm .py dosyalarını aynı klasöre koyun (örn. /opt/sinama/).
2. İstemci yapılandırmasına ekleyin (mcp_istemci_ornegi.json):

```json
{
  "mcpServers": {
    "sinama": {
      "command": "python",
      "args": ["/opt/sinama/mcp_sunucu.py"]
    }
  }
}
```

3. İstemciyi yeniden başlatın; agent artık şu tür istekleri araç çağrısına
   dönüştürebilir: "bu CSV'deki mahallelere göre Poisson anomalisi bul",
   "kapkaç için risk skorla", "A'dan G'ye bağlantı zincirini göster".

### Araç listesi (28)
veri_ozeti, frekans, capraz_tablo, saat_dagilimi, gun_dagilimi, ay_serisi,
trend, grid_hotspot, kde_yogunluk, nni, mukerrer_magduriyet, yakin_tekrar,
knox_tablosu, seri_eslestirme, gun_saat_analizi, kontrol_grafigi, cusum,
bolge_anomali, suc_oranlari, ki_kare_testi, pearson, endeks_hesapla,
degerlendirme_did, benford, ag_analizi, risk_skorla, bulanik_eslesme,
orneklem_cek

### Veri geçişi
Araçların çoğu iki girişi kabul eder:
- `csv_yolu`: sunucunun erişebildiği CSV dosyası (büyük veri için önerilir)
- `satirlar`: satır listesi (küçük veri, inline JSON)

Tarih alanı otomatik çözümlenir; lat/lon alan adları varsayılanı
"lat"/"lon"dur. Sonuçlar JSON metin olarak döner.

### Test
`python test_mcp.py` — gerçek stdio üzerinden initialize, tools/list ve
12 temsili tools/call çağrısını doğrular.

### Sınırlar
- Tek işlem, satır bazlı stdio: aynı anda tek istemci.
- SSE/HTTP transportu yok (lokal kullanım hedeflendi).
- Büyük CSV'lerde KDE/yakın-tekrar O(n²) maliyetli olabilir; önce
  filtreleme/frekans ile alt küme alınması önerilir.


## v4 — Güvenlik Sertleştirme ve Paketleme (bağımsız denetim sonrası)

### Kapatılan bulgular
1. **KRİTİK — Keyfi dosya okuma (kapatıldı):** `csv_yolu` artık
   `veri.guvenli_yol` ile izinli köke kilitli (realpath + commonpath,
   ".." ve sembolik bağ kaçışları reddedilir). Kök:
   `SINAMA_VERI_KOKU` ortam değişkeni (yoksa çalışma dizini).
   Yalnızca .csv/.tsv/.txt; dosya boyutu ≤ 50 MB.
2. **YÜKSEK — Traceback sızıntısı (kapatıldı):** beklenmedik hatalarda
   istemciye yalnızca "HATA: <Tip> — işlem başarısız" gider; traceback
   (yollar, içerik) yalnızca stderr logunda kalır.
3. **ORTA — DoS / kaynak sınırı:** satır tavanı (varsayılan 200.000);
   aşılırsa kesilir ve `veri_ozeti` çıktısında `"kesildi": true` görünür.
4. **ORTA — KVKK/PII:** ham kayıt döndüren araçlarda (orneklem_cek,
   bulanik_eslesme) PII benzeri alanlar (ad, telefon, adres, kimlik…)
   varsayılan olarak düşülür; `alanlar` parametresiyle beyaz liste
   verilebilir.
5. **YAPISAL — Gerçek paket:** modüller artık `sinama` paketi
   (`__init__.py`, relative import). Dışarıdan
   `from sinama.mekan import haversine_km` çalışır; jenerik
   üst-düzey ad çakışması riski kalktı. `mcp_sunucu.py`, `demo*.py` ve
   `test_mcp.py` paketin DIŞINDA ince başlatıcıdır.
6. **SAYISAL:** Poisson üst kuyruğu log-uzayında (λ>745 underflow
   giderildi); `tip_tahmin` yalnızca `\d+,\d{1,2}` biçimini Türkçe
   ondalık sayar ("1,234" artık sessizce 1.234 OLMAZ); kontrol grafiği
   örneklem std sapması (stdev) kullanır; label propagation ve k-means
   için kararlılık uyarıları eklendi.

### Dizin yapısı
```
suc_paket/
├── sinama/          # paket (13 modül + __init__.py)
├── mcp_sunucu.py         # MCP stdio sunucusu (paketi kullanır)
├── demo.py, demo2.py     # uçtan uca örnekler
├── test_mcp.py           # işlev + GÜVENLİK testleri
├── mcp_istemci_ornegi.json
└── README.md
```

### Güvenli çalıştırma
```bash
SINAMA_VERI_KOKU=/opt/suc_veri python mcp_sunucu.py
```
İstemci bu kökün dışındaki hiçbir dosyayı okutamaz (test_mcp.py'de
kök dışı mutlak yol, ".." kaçışı ve uzantı ihlali testleri dahildir).

### Bilinen sınırlar (bilinçli tercihler)
- Tek istemci / tek süreç stdio; iptal mekanizması yok — pahalı
  çağrılar (KDE, near-repeat) satır tavanıyla sınırlı tutulur.
- O(n²) analizlerde önce filtreleme önerisi geçerli.


## v5 — Bağımsız Denetim Planının Tam İcrası (Faz 0–3)

v4 sonrası ikinci bağımsız denetimdeki tüm bulgular (K1–K7) kapatıldı.
Ayrıntılar CHANGELOG.md'de; özet:

| Bulgu | Çözüm | Kalıcı test |
|---|---|---|
| K1 PII denylist eksikleri | default-deny + token eşleşme + domain terimleri | test_mcp (magdur/supheli sızıntısı) |
| K2 env yoksa kök=cwd | başlangıç guard'ı: env zorunlu, / ve $HOME reddedilir | test_mcp kök guard bloğu |
| K3 inline satirlar tavansız | MAKS_SATIR'a bağlandı | birim + entegrasyon |
| K4 compute-DoS | MAKS_QUADRATIC_N=5000, net ret mesajı | test_mcp 6k kayıt testi |
| K5 şema enforce değil | stdlib doğrulayıcı → -32602 | test_mcp zorunlu/tip testi |
| K6 audit yok | rotasyonlu log, yalnız argüman anahtarları | test_mcp audit bloğu |
| K7 anlamlılık yok | Knox/near-repeat Monte Carlo p-değeri; NNI z-testi; oranlara Garwood exact GA; ki-kare Yates+Cochran | birim golden-value |

### Çıktı sözleşmesi (v5)
Her tools/call yanıtı `{sonuc, meta}` paketidir:
- `meta.insan_onayi_gerekir`: tahmin/risk araçlarında true — çıktı insan
  onayı olmadan eyleme dönüştürülemez (yönetişim ilkesi).
- `meta.uyarilar`: araç bazlı metodoloji/önyargı notları (geri-besleme
  döngüsü, projeksiyon zarfı, GA'sız karşılaştırma uyarısı vb.).
- `meta.satir` / `meta.kesildi`: provenance (provenance manifestinin
  çekirdeği; girdi dosyası+parametreler audit logunda izlenir).

### Projeksiyon zarfı (Faz 3.4 belgelendirmesi)
Mekânsal modüller equirectangular km yaklaşımı kullanır (110.574 km/enlem,
111.320·cos(φ) km/boylam). Şehir ölçeğinde (≲50 km AOI, |φ|≲55°) doğrudur;
ülke ölçeği veya yüksek enlemlerde sonuçlar bozulur — o durumda veriyi
yerel projeksiyona çevirip öyle besleyin.

### Kurulum (offline / air-gap)
```bash
pip install --no-index dist/sinama-5.0.0-py3-none-any.whl
SINAMA_VERI_KOKU=/opt/suc_veri sinama-mcp
# veya paket dizininden:
SINAMA_VERI_KOKU=/opt/suc_veri python -m sinama
```

### Test katmanları
1. `python -m unittest discover -s tests` — 19 birim testi (golden-value)
2. `python test_mcp.py` — uçtan uca stdio + güvenlik regresyonları
3. `sh test.sh` — air-gap tek komut (birim + entegrasyon + demolar)

### Faz 4 notu (YAGNI)
Uzamsal indeksleme / streaming / native hızlandırma, plan gereği yalnızca
profillenmiş darboğaz gösterildiğinde eklenecektir.


## v5.1 — Faz 1.5: Veri Profili ve Uygunluk Kapısı

Çekirdek ilke: veri uygunluğu modelin öznel yargısı değil, çalıştırmadan
ÖNCE hesaplanan deterministik ön-uçuştur. Kod kapıyı tutar, model kapının
kararına göre analiz seçer.

- **veri_kalitesi aracı:** her analizden önce çağrılır (DOKTRIN.md kural 1).
  Profil: duplikat, eksiklik, tarih başarısı, koordinat geçerliliği,
  zaman kapsamı, dispersiyon, Benford mertebesi, kardinalite.
- **Fitness gate:** `analiz` parametresi verilirse uygun/uygun-değil kararı
  + sebepler. Payda'sız oran, tek-nokta KDE, tek-mertebeli Benford,
  nominalde ortalama → REDDEDİLİR.
- **Sessiz filtreleme yasağı:** mekânsal araç çıktılarındaki `kapsam`
  bloğu girdi N → analize giren N → dışlanma sebebini zorunlu gösterir.
- **Dağılımsal uygunluk:** bolge_anomali artık BH-FDR q-değeri + aşırı
  yayılım notu döner; Holt-Winters öncesi otokorelasyon denetimi gate'te.
- **Tahribatsızlık:** hiçbir araç kayıt silmez/değer uydurmaz;
  duplikat_isaretle yalnız işaretler, duyarlilik_analizi aykırı değeri
  dahil/hariç iki özetle raporlar, kategori birleştirme insan onaylıdır.
- **DOKTRIN.md:** agent'ınızın system prompt'una eklenecek 13 zorunlu kural.


## v5.2 — Weisburd & Britt Genişletmesi (Hipotez Testleri + Regresyon)

45 araç. Yeni modüller hipotez.py ve regresyon.py; dağılım altyapısı
(t/F CDF, ters normal) saf Python'da incomplete beta üzerinden yazıldı.

### P0 — Temel çıkarımsal testler
t_testi (tek/bağımsız/Welch/bağımlı), iki_oran_testi (+GA), fisher_exact
(iki yönlü + her iki kuyruk; Cochran ihlalinde gate otomatik yönlendirir),
binomial_test, mann_whitney (tie düzeltmeli), spearman, kendall (tau-b),
phi, dagilim_olculeri (IQR/MAD/CV).

### P1 — Çok gruplu ve güç
anova (+eta² + Bonferroni pairwise; Tukey HSD kritik değerleri saf
Python'da pratik olmadığından Bonferroni kullanılır — bilinçli sınır),
kruskal_wallis (tie düzeltmeli), randomizasyon_testi (varsayımsız),
guc_analizi (oran/ortalama için örneklem büyüklüğü — kitabın
"başarısızlığa tasarlanmış çalışmadan kaçınma" ilkesi; DiD öncesi
"kaç hafta veri gerekir?" sorusunun cevabı).

### P2 — Çok değişkenli
coklu_regresyon (beta/SE/t/p, R², düzeltilmiş R², F, VIF; tekil matris
sessizce geçilmez, bildirilir), lojistik_regresyon (IRLS, Wald z/p,
odds oranı, McFadden R², yakınsama bayrağı; iki çıktı da insan onayı
bayraklıdır — ilişki analizidir, karar aracı değildir).

### Bilinçli kapsam dışı (dürüstlük notu)
Çok düzeyli modeller, multinomial/ordinal lojistik ve Tukey HSD kritik
değerleri saf standart kütüphanede opak/kırılgan olacağı için ALINMADI;
gerektiğinde bu analizler için R/SPSS önerilir.

## v6.5 — Dayanıklılık (H1 kanıt + H2 hata taksonomisi + H6.1 release)

GELISME_PLANI'nin P0 demeti. **H1:** manifesto yazımı atomik (temp +
os.replace), olay akışı fsync'li, delta sayacı akıştan türetilir —
çökme sonrası mükerrer olay yapısal olarak imkânsız; manifesto
yazılamazsa hata gürültülü, `yukle` gecmisi akıştan onarır
(kanit_uyari ile bildirerek). **H2:** hata taksonomisi — her hata
`HATA [tip]: mesaj + ÖNERİ` biçiminde döner (veri / kullanim / kapi /
guvenlik / dongu / sistem); agent hata tipinden düzeltici eylem seçer.
`isle()` ince boru hattına ayrıldı. **H6.1:** `release.sh` tek komutla
doğrulanmış paket üretir (test → /tmp'de zip → taze açılımda tam test
→ hedefe taşı). 149 birim test; DOKTRIN kural 22 yapısaldır.

## v6.6 — Güven tabanı (H3 test tabanı + H6.2 protokol anlaşması)

Testsiz dört modüle golden testler (zaman/orneklem/skor/degerlendirme —
zaman %100 kapsam; 0→5'e "değişim yok" diyen sessiz yanlış bulunup
düzeltildi). **Sözleşme testi jeneratörü:** 60 aracın tamamı kayıt
üzerinden taranır — şema + minimal çağrı + {sonuc, meta} sözleşmesi;
yeni araç otomatik kapsanır (DOKTRIN kural 23). **Kapsam cırcır
kapısı:** stdlib trace ile ölçüm; kapsam_taban.json altına gerileme
test.sh'ı kırar, yeni modül %80 normuna tabidir. **Protokol
anlaşması:** initialize desteklenen sürümleri beyan eder, bilinmeyen
istemci sürümü uyarıyla devam eder. 198 birim test.

## v6.7 — Olgunlaştırma (H5 loglama/doküman + H4-u katman yönü)

Seviyeli loglama (stdlib logging, SINAMA_LOG_SEVIYE; audit
bağımsız). Doküman standardı: public docstring %100, birimli
parametreler belgeli, genel %89.4 (DOKTRIN 25). Katman bağımlılık yönü
AST taramasıyla yapısal (DOKTRIN 24) — cekirdek/veri.py'nin ters
bağımlılığı bulunup düzeltildi: guvenlik primitifi cekirdek'e taşındı
(sys.modules yönlendirmesiyle tam uyumluluk). Kapsam taban yükseltmesi:
ag %97.2, istatistik %89.3, çekirdek genel %83.1. H4 tetikleyicileri
ölçüldü, YAGNI gereği açılmadı. 237 birim test.

## v6.8 — Kapsam borcu turu (GELISME_PLANI H3 cırcır borcu)

Kalan 5 düşük kapsamlı çekirdek modülüne golden testleri: ileri
(cografi_profil, risk_arazi, k_means, donemsel_hotspot_karsilastirma,
olaylar_arasi_sure, benford/poisson kenarları) %55.9→%96.0; iliski
(lambda_, gamma_, capraz_ki_kare, suc_orani) %72.0→%92.1; kume
(carpisma, levenshtein) %73.5→%93.9; olcek (olcum_duzeyi_belirle,
cronbach_alfa, min_max, endeks_kur) %67.2→%98.4; veri (csv_yukle
sniffer/kesme, _sayi_coz binlik-virgül tuzağı, tip_tahmin) %77.5→%95.0.
**Çekirdeğin tamamı ≥%82, genel %83.1→%93.1.** Taban cırcırla
sabitlendi. 53 yeni test; toplam 290 birim test.
