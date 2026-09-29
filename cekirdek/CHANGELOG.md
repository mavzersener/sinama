# CHANGELOG

## [Yayımlanmamış]

### Gömülü kullanım sözleşmesi: `sunucu.arac_calistir(ad, arg)`
MCP dışındaki çağıranların (DataFlow ml-service köprüsü, dışa aktarılan
Python betikleri) TEK kamusal girişi. İstek bağlamını kendisi kurar;
paket MCP `tools/call` ile birebir aynıdır (ortak `_paket_uret`), hatalar
tipli (`SucAnaliziHatasi` alt sınıfları) yayılır, denetim satırı yazılır.
`_arac_yurut` bağlamsız çağrılırsa artık `RuntimeError` ile sebebini
söyler — önceden gate'siz iz-zorunlu 23 araçta anlamsız `AttributeError`,
diğerlerinde sessizce eksik metadata (satir/kesildi/uyarılar) üretiyordu.
Test: `tests/test_gomulu_api.py`.

### 07 — kanıt zinciri: bağ alanı hash'e dahil (GÜVENLİK)
v1 `_kayit_hash` `onceki_hash`'i hash DIŞINDA bırakıyordu: ortadaki bir
kaydı değiştirip yalnız bir sonrakinin bağını güncellemek `dogrula()`'yı
"sağlam" bırakıyor, zincirin baş ve son hash'i değişmiyordu (dış çapa bile
yakalayamazdı; 23 Eyl 2026'da deneyle doğrulandı). Yeni kayıtlar v2
(`"zincir": 2`): bağ dahil tüm kayıt hash'lenir. `dogrula()` artık
`zincir_son_hash` (dış çapa için) döner; eski v1 kayıtlar okunur ama
`korumasiz_olay` + `uyari` ile raporlanır; v2'den sonra v1 (sürüm düşürme)
reddedilir. Test: `tests/test_duzeltme_07_zincir.py`.

### 06 — alternatif girdi kipinde eksik argüman artık tipli hata
x/y dizisi VEYA satirlar+alan kabul eden araçlar (anova, kruskal_wallis,
mann_whitney, randomizasyon_testi, kendall, spearman, t_testi) ve
guc_analizi (tip=oran → p1/p2) kipin gerektirdiği argüman eksikken
KeyError atıp 'sistem' hatası (HTTP köprüsünde çıplak 500) veriyordu.
`arac_yurut`: şemada tanımlı ama çağrıda verilmemiş argümanın KeyError'ı
→ `KullanimHatasi`; iç/veri KeyError'ları maskelenmez. DataFlow'un
tüm-araç duman testi buldu. Test: `tests/test_duzeltme_06_eksik_kip.py`.

### Denetim düzeltme turu 01-05
Test kapısı (`-O` altında da fatal), oturum yolu beyaz listesi, regresyonda
atomik tam-kayıt seçimi, istek bağlamı + hesaplama tavanları, zorunlu araç
politikası. Ayrıntı: `tests/test_duzeltme_0*.py`.

## [6.8.0] — Kapsam borcu turu (H3 cırcır borcunun kapatılması)

### Yeni golden testleri (+53 test, toplam 290)
- `tests/test_ileri.py` — donemsel_hotspot_karsilastirma (5 sınıf tek
  senaryoda + tolerans kenarı), olaylar_arasi_sure, cografi_profil
  (grid yapısı + golden hücre + azalan sıralama), risk_arazi
  (ağırlıklı golden), k_means (seeded golden + tekrarlanabilirlik),
  benford (n<10 → None, şüpheli golden, doğal veri uyumlu),
  poisson_ust_kuyruk kenarları.
- `tests/test_iliski.py` — lambda_ (PRE golden 0.6, boş/tek-değişken
  kenarları), gamma_ (±1.0, tied → None), capraz_ki_kare golden
  (7.2 / df=1 / p=0.00729 / Cramér V 0.6) + Cochran uyarısı,
  suc_orani golden + sıfır nüfus.
- `tests/test_kume_olcek_veri.py` — carpisma (normalize kesişim,
  boş liste, None dışlama), levenshtein (klasik golden 3, boş metin,
  normalizasyon-önce), olcum_duzeyi_belirle (3 dal), cronbach_alfa
  golden 0.9529 + tanımsızlık kenarları, min_max (ters + sabit seri
  0.5), endeks_kur golden (ağırlık + ters gösterge + tahribatsızlık),
  csv_yukle (sniffer ';', maks_satir kesme bayrağı), _sayi_coz
  binlik-virgül tuzağı ('1,234' sayı SAYILMAZ), tip_tahmin/tarih_coz/
  eksik_raporu/normalize_metin.

### Kapsam sonucu (cırcır tabanı güncellendi)
ileri %55.9→%96.0 · iliski %72.0→%92.1 · kume %73.5→%93.9 ·
olcek %67.2→%98.4 · veri %77.5→%95.0.
**Çekirdeğin 18 modülünün tamamı ≥%82; genel %83.1→%93.1.**
Davranış değişikliği yok; yalnız test + taban.

## [6.7.0] — Olgunlaştırma (GELISME_PLANI Faz H5 + H4-u)

### H5.1 — seviyeli loglama
`log()` artık stdlib logging üzerinden: paket loglayıcısı (zaman damgası
+ seviye + modül etiketi, stderr; stdout yalnız JSON-RPC). Seviye
`SUC_ANALIZI_LOG_SEVIYE` ile ayarlanır. Seviye atamaları: kanıt kaybı
ve iç hata ERROR, kapı reddi/doğrulama INFO, politika/protokol WARNING.
Audit akışı bağımsız kalır (kanıt niteliği).

### H5.2 — doküman standardı (DOKTRIN kural 25, YAPISALDIR)
28 eksik public docstring tamamlandı (Args/Returns + birim); mevcut
docstring'lere birimli parametre belgeleri eklendi (hucre_km, bant_km,
alan_km2, tolerans_km, mesafe_km...). AST meta-testi: public %100
docstring, birimli parametreler docstring'de anılır, genel kapsam
(kayıtlı araç adaptörleri hariç) %89.4 ≥ %85.

### H4-u — katman bağımlılık yönü (DOKTRIN kural 24, YAPISALDIR)
AST import taraması: cekirdek→yok, kalite→cekirdek, surec→+kalite,
arayuz→hepsi. **Gerçek ihlal bulundu ve düzeltildi:** cekirdek/veri.py
kalite.guvenlik'i import ediyordu (ters bağımlılık) — guvenlik
primitifi cekirdek/'e TAŞINDI; kalite/guvenlik.py sys.modules
yönlendirmesiyle tam uyumluluk sağlar (monkeypatch dahil). veri.py'nin
iki v6.1 uyumluluk şimi (kalite.profil/kapi) sabit istisna kümesi
olarak işlendi — büyümesi test kırar.

### Tetikleyici raporu (YAGNI)
H4.1/H4.2/H4.3 tetikleyicileri ÖLÇÜLDÜ ve açılmadı: 60 < 70 araç,
ortak.py 445 < 500 satır, yeni kapı kuralı yok.

### Kapsam taban yükseltmesi
ag.py %50.3 → %97.2 (yeni test_ag.py: üçgen/yol/köprülü çift üçgen
goldens; pagerank 1/3, topluluk, ego, birlikte-olay ağırlıkları).
istatistik.py %63.4 → %89.3 (yeni test_istatistik.py: yüzdelik, kayan
ortalama uç davranışı, trend, z-skor — küçük örneklem maskeleme
tuzağı testle sabit). Çekirdek genel: %78.5 → %83.1.

### Testler
237 birim test (39 yeni: test_olgunlastirma.py, test_ag.py,
test_istatistik.py) + MCP entegrasyonu yeşil.

## [6.6.0] — Güven tabanı (GELISME_PLANI Faz H3 + H6.2)

Test tabanının kapatılması ve kalıcı sözleşme/kapsam kapıları.

### H3.1 — zaman.py golden testleri (yeni test_zaman.py, 12 test)
saat/gun/ay dağılımları, gunluk_seri (sıfır-doldurma, hafta sonu
kenarı, boş/tek gün), aoristik_dagilim (ağırlık paylaşımı, geçersiz
aralık, gösterim yuvarlaması sözleşmesi). Bu modül kontrol_grafigi /
cusum / trend / gun_saat_analizi'nin tabanıydı ve testsuzdu (D1 bulgusu).

### H3.2 — orneklem / skor / degerlendirme golden testleri
(30 test) tabakalı örneklem tabaka oranları (60/40 → 6/4), küçük
tabaka max(1,·) kuralı, orantısız eşit pay; ağırlık toplamı, eşik
yönü, gruplu toplam; oncesi_sonrasi, DiD (-8 golden), kesinti
seviye/eğim. **Gerçek hata bulundu ve düzeltildi:** oncesi_sonrasi
0→5 geçişine "değişim yok" diyordu (yüzde tanımsız ama yön tanımlı)
— artık "artış" döner (sessiz yanlış giderildi).

### H3.3 — araç sözleşme testi jeneratörü (yeni test_sozlesme.py)
60 aracın tamamı kayıt üzerinden taranır: şema iyi biçimliliği,
minimal geçerli çağrının -32602'siz çalışması, {sonuc, meta}
sözleşmesi, meta.uyarilar liste tipi. Yeni araç OTOMATIK kapsanır;
özel argüman gerekiyorsa test düşer (ARG_OZEL tablosu güncellenir).
Döngü ailesi (9 araç) PPDAC sırasıyla uçtan uca koşar + kanit_dogrula.
DOKTRIN kural 23 (YAPISALDIR) işlendi.

### H3.4 — kapsam ölçümü + cırcır kapısı (yeni kapsam_olc.py)
stdlib `trace` ile satır kapsamı; suite izleme altında kurulur
(import-üst-düzey satırlar doğru sayılır). Cırcır: kapsam_taban.json
altına gerileme başarısız sayılır; tabanda olmayan (yeni) modül %80
normuna tabidir. test.sh'a kapı olarak işlendi. İlk taban: çekirdek
genel %78.5 (zaman/degerlendirme/zarar %100).

### H6.2 — protokol anlaşması
initialize cevabı desteklenenProtokoller listesini beyan eder;
bilinmeyen istemci sürümü reddedilmez — sunucu kendi sürümüyle devam
eder + protokolUyari notu düşer (MCP + birim testleri).

### Testler
198 birim test (48 yeni) + MCP'de protokol anlaşması senaryosu.

### Düzeltme — test ortamı sızıntısı
test_kapi_doktrin tearDown'u SUC_ANALIZI_LOG_DIR'i pop() ile
kaldırıyordu; alfabetik olarak sonra koşan sözleşme testleri keşif
oturumlarını paket kökündeki ./oturumlar'a yazıyordu (v6.6 zip'ine
351 artık dosya sızdı, yakalandı). tearDown artık eski değeri geri
yükler; test_sozlesme ortamı setUpClass'ta yeniden kurar; release.sh
temizlik listesine oturumlar eklendi + zip kalabalık koruması
(>150 dosya = hata) ve oturum-artığı denetimi eklendi.

## [6.5.0] — Dayanıklılık (GELISME_PLANI Faz H1 + H2 + H6.1)

Birleşik gelişme planının P0 demeti: kanıt dayanıklılığı ve hata
taksonomisi. Her madde plan belgesindeki ölçülmüş bulguya bağlıdır.

### H1 — Kanıt dayanıklılığı (DOKTRIN kural 22, YAPISALDIR)
- **H1.1 atomik manifesto**: `kanit.atomik_json_yaz` (temp + fsync +
  `os.replace`) — çökme her noktada olursa olsun manifesto ya eski tam
  içeriği ya yeni tam içeriği taşır; yarım JSON imkânsız.
- **H1.2 fsync + idempotent delta**: olay yazımı fsync ile kapanır;
  delta başlangıcı manifestodaki sayaçtan DEĞİL akışın kendisinden
  türetilir (`olay_sayaci` alanı kaldırıldı) → olay yazıldıktan sonra
  çökme olursa yeniden kayıt olayı ÇOĞALTMAZ.
- **H1.3 kanıt kaybı gürültülü**: resmî modda manifesto yazım hatası
  `DonguHatasi` fırlatır (olaylar akışta sağlam kalır); keşif modunda
  sonuç `meta.kanit_durumu: "YAZILAMADI"` + `uyarilar[0]` "KANIT KAYBI"
  bayrağıyla döner — analiz durmaz ama kayıp asla sessiz değildir.
- **H1.4 yukle uzlaştırması**: akış manifestodan ilerideyse (çökme
  senaryosu) ve zincir sağlamsa gecmis akıştan ONARILIR; zincir bozuksa
  / akış eksikse onarım yapılmaz, `kanit_uyari` + `kanit_dogrula`
  önerisi işaretlenir (`dongu_durum`'da görünür).

### H2 — Hata taksonomisi + dispatch boru hattı
- **H2.1** `cekirdek/hatalar.py`: tek kök `SucAnaliziHatasi`;
  `VeriHatasi` / `GuvenlikHatasi` / `KullanimHatasi` (üçü de ValueError
  uyumlu — mevcut kanıtlar bozulmaz); `KapiRed.tip="kapi"`,
  `DonguHatasi.tip="dongu"`. 17 raise noktası sınıflandırıldı.
  Hata cevabı artık yapısal: `HATA [tip]: mesaj` + `ÖNERİ: ...` —
  istemci (yerel agent) hata tipinden düzeltici eylem seçebilir.
- **H2.2** `isle()` boru hattına ayrıldı (`_arac_yurut` /
  `_basari_paketi` / `_hata_cevap`); davranış bit-bit aynı (tüm
  regresyon testleri değişmeden yeşil).
- **H2.3** her hata tipi için MCP seviyesi kanıt (4 senaryo) + birim
  testleri (sahte araçla sistem tipi: iç ayrıntı sızmaz).

### H6.1 — release.sh
Tek komut: sürüm tutarlılığı (init/ortak/pyproject/CHANGELOG — 4 kaynak
tek gerçek) → tam test paketi → zip /tmp'de kurulur → taze açılımda tam
test → ancak hepsi yeşilse hedefe taşınır. v6.4'te yaşanan boş-zip
(0 bayt) vakası yapısal olarak tekrarlanamaz; zip dosya sayısı <20 ise
betik kendini durdurur.

### Not — korunan sözleşme
regresyon/iliski modüllerinin "yumuşak hata" dönüşü (`{"hata": ...}`)
bilinçli olarak KORUNUR (test_hipotez.py sabiti: "sessiz geçmemeli,
bildirmeli"); taksonomi sert hatalar içindir.

### Testler
149 birim test (12 yeni: test_dayaniklilik.py — K22 + taksonomi) +
MCP entegrasyonunda 6 yeni v6.5 senaryosu. DOKTRIN_KAPSAM'a kural 22
işlendi.

## [6.4.0] — Faz F + P2 + ölçümlü Faz G (kontrollü ilerleme)

### Faz G — mekânsal grid indeksi (ÖLÇÜMLE haklı çıktı)
- Ölçüm (MAKS_QUADRATIC_N=5000 sınırında): NNI çiftleri 22.3s, Knox çift
  sayımı 5.9s — belgedeki YAGNI kapısı ("ancak ölçülen darboğazda") açıldı.
- mekan.py: _grid_kur/_hucre_min_km/yakin_ciftler_hizli +
  en_yakin_komsu_mesafeleri'nde genişleyen-halka araması. Grid yalnız
  aday budar; nihai mesafeler haversine ile hesaplanır → sonuçlar kaba
  kuvvetle BİREBİR aynı (doğruluk testleri: 3 seed + ıssız nokta).
- Sonuç: NNI 22.3s → 0.25s (~89×), Knox çift sayımı 5.9s → 0.03s (~197×).
  tekrar.py üç döngü (yakin_tekrar_ciftleri, _cift_sayisi, knox_tablosu)
  grid'e geçti.

### P2 — hash-zinciri (ertelenen madde tamamlandı)
- kanit.olay_yaz her kaydı öncekinin SHA-256'sına zincirler
  (onceki_hash); kanit.dogrula(log_dir, oturum_id) bütünlüğü sınar.
- Kurcalama testi: değiştirilen kayıt bir SONRAKİ adımda saptanır.
- Yeni araç: kanit_dogrula (60 araç).

### Faz F — doktrin-enforcement suite genişlemesi
- test_faz_f.py (15 test): yol hapsi primitifleri, tavanlar (quadratic/
  inline/dosya boyutu), audit sözleşmesi (anahtar var, değer yok),
  şema -32602 (tip/required/enum), FDR otomatiği, nominal red.
- DOKTRIN_KAPSAM haritası + meta-test: her YAPISAL kuralın (1-21;
  yargısal 12/13 hariç) en az bir kanıt testi var; harita bozulursa
  test düşer. Suite artık kalıcı alışkanlık olarak kendini denetler.
- Sözleşme netleştirmeleri (testle sabitlendi): inline tavan = kırp +
  kesildi bayrağı (sessiz kırpma yok); bilinmeyen argüman toleransı.

### Bu fazda bulunan ve düzeltilen YAPISAL hatalar
- CHI kurum ağırlık tablosu (.json) uzantı whitelist'ine takılıyordu —
  DOKTRIN 17/18 fiilen kullanılamıyordu. guvenli_yol'a amaca özel
  izinli_uzantilar parametresi; regresyon testi TestK21.
- kapi()'daki nominal-ortalama kuralı hiçbir araca bağlı değildi (ölü
  kural). dagilim_olculeri artık ARAC_GATE'te; nominal alan → KapiRed
  (TestK20).

### Test
- Toplam: 137 birim testi + tam MCP entegrasyonu (60 araç), hepsi yeşil.

## [6.3.0] — Faz E: metodolojik derinlik

Birleşik mimari belgesinin Faz E'si. Listedeki Knox MC p, NNI z, oran
GA, Cochran/Yates v5.x'te yapısaldı; bu faz kalan boşlukları kapatır ve
mevcutları derinleştirir.

### E1 — Aşırı yayılım: uyarıdan düzeltmeye (ileri.py)
- bolge_anomali artık aşırı yayılımda p-değerlerini NEGATİF BİNOM
  modelinden hesaplar (naif Poisson'un yanlış-pozitifleri yapısal
  olarak elenir); Poisson p'leri 'p_poisson' alanında karşılaştırma
  için korunur.
- Model seçimi FORMAL test ile: Fisher dispersiyon testi
  (T = Σ(x-μ)²/μ ~ χ²(n-1), üst kuyruk _gammaincc).
- Maskeleme önlemi: yayılım parametresi üst %10 kırpılmış momentlerden
  tahmin edilir — tek uç bölge varyansı şişirip kendini NB null'a
  boğduramaz (regresyon testi: [5×11, 100] senaryosunda m11 yakalanır).
- neg_binom_ust_kuyruk: _betainc üzerinden; el-hesabı golden
  (NB(r=2,p=0.5): P(X≥2)=0.5) ile doğrulandı; yayılım yoksa Poisson'a
  düşer. Çıktıya model, dispersiyon_orani, fisher_dispersiyon_p eklenir.

### E2 — İki Poisson oranı exact karşılaştırma (iliski.py + yeni araç)
- iki_poisson_orani: koşullu exact test (k1 | n ~ Bin(p0=e1/(e1+e2)),
  Krishnamoorthy & Thomson), RR + Clopper-Pearson dönüşüm GA
  (_beta_kuantil biseksiyonu). Yeni MCP aracı: oran_karsilastir.
- Doğrulama: koşullu p, binomial_test ile birebir; RR=3.0 golden;
  eşit oranda GA 1'i içerir; R poisson.test mid-P ile uyumlu (exact CP
  biraz geniştir, beklenen davranış).

### E3 — NNI Donnelly kenar düzeltmesi (mekan.py)
- nni_test(kenar_duzeltme=True): beklenen mesafe ve varyansa Donnelly
  (1978) çevre terimleri eklenir (sınıra yakın noktaların komşusu alan
  dışında kalabilir — düzeltilmemiş test kümelenme yönünde önyargılı).
  Geriye uyumlu: varsayılan kapalı; çevre verilmezse sınır kutusundan.
  nni aracında kenar_duzeltme/cevre_km parametreleri.

### E4 — Knox analitik beklenti (tekrar.py)
- knox_anlamlilik çıktısına beklenen_analitik: bağımsızlık altında
  E = (uzay-yakın × zaman-yakın) / toplam çift — MC ortalamasının
  yakınsaması gereken değer; test MC ile örtüşmeyi doğrular.

### Test
- tests/test_faz_e.py (14 test): el-hesabı golden, model seçimi,
  muhafazakârlık (uzak kuyruk), maskeleme önlemi, koşullu p tutarlılığı,
  RR/GA özellikleri, Donnelly yön, Knox analitik-MC yakınsaması.
- test_mcp.py: oran_karsilastir, nni Donnelly, bolge_anomali NB.
- Toplam: 116 birim testi + tam entegrasyon regresyonu, hepsi yeşil.

## [6.2.0] — Faz C: birleşik kanıt mimarisi + muhakeme izi

Birleşik mimari belgesinin Faz C'si (G5 + Faz 1.6). Üç katman, tek
kaynak — kanıt sistemleri çoğalmaz, katmanlanır.

### Katman 1 — OLAY AKIŞI (surec/kanit.py, YENİ)
- Oturum bazlı, değişmez (append-only) JSONL: oturumlar/{id}.olaylar.jsonl.
- dongu.kaydet her çağrıldığında yeni gecmiş adımları akışa DELTA olarak
  işler (olay_sayaci); tekrar kaydetme olayı çoğaltmaz, yüklenen
  oturumda delta kaldığı yerden devam eder.
- PII sözleşmesi: olaylar yalnız {zaman, olay, faz, ozet, gerekce,
  onceki_hash} alanlarından kurulur; argüman değeri yazılmaz.
- YAGNI: hash-zinciri (tamper-evident bütünlük) belge §6 gereği P2'ye
  ertelendi; onceki_hash alanı şemada hazır.
- Global audit.log güvenlik/operasyon kaydı olarak kalır; kanit akışı
  analitik kanıttır — örtüşmez, kaygılar ayrıdır.

### Katman 2 — MANİFESTO (projeksiyon)
- kanit.projeksiyon(olaylar): akıştan anlamsal görünüm üretir; test
  manifesto gecmisiyle birebir örtüştüğünü kanıtlar (tek-kaynak testi).

### Katman 3 — MUHAKEME İZİ (rapor.muhakeme_izi, YENİ)
- Her ANALİZ adımı için OLGU (K1/K2 — ölçülen) ve GEREKÇE (K3 — yorum)
  görsel olarak AYRI işlenir (blockquote + açık uyarı: "gerekçe olgu
  değildir").
- brifing_uret oturum_id ile çağrıldığında ürüne muhakeme izi bölümü
  eklenir; yeni muhakeme_izi aracı izi bağımsız döner (58 araç).

### Faz 1.6 — yapılandırılmış gerekçe zorunluluğu (yapısal)
- dongu_analiz şemasında gerekce ZORUNLU (hipotez + yorum; eksik alan
  -32602 / ValueError). Resmî oturumda gerekçesiz analiz adımı
  analiz_kaydet düzeyinde reddedilir; keşif oturumları muaftır.
- sonucla yorumsuzluk kilidi: gerekçesiz ANALİZ adımı varken SONUÇ
  fazına geçilemez (eski manifestolar dahil).
- DOKTRIN kural 21: "her adımda gerekçe" doktrinden inşaya taşındı.

### Test
- tests/test_kanit_muhakeme.py (10 test): delta/çoğaltmama, kalıcı
  delta, projeksiyon örtüşmesi, PII yokluğu, gerekçe reddi, keşif
  muafiyeti, yorumsuz-sonuç kilidi, iz işleme.
- test_mcp.py: gerekçesiz dongu_analiz -32602, gerekçeli tam döngü,
  muhakeme_izi aracı, brifing+iz bütünleşmesi, akış dosyası kanıtı.
- Toplam: 102 birim testi + tam entegrasyon regresyonu, hepsi yeşil.

## [6.1.0] — Faz B: 4-katman refactor + oturum = analizin birimi

Birleşik mimari belgesinin Faz B'si. sunucu.py tanrı-modülü çözüldü;
gate'siz/izsiz analiz yolu yapısal olarak kaldırıldı.

### G1 — Katmanlı modül düzeni (fiziksel)
- cekirdek/: 16 saf modül (veri erişimi + istatistik); iç API sabit.
- kalite/: profil.py (veri_profili), kapi.py (tek gate otoritesi),
  guvenlik.py (yol hapsi + kök). veri.py üçe bölündü; eski adlar
  (veri.guvenli_yol, veri.veri_profili, veri.analiz_uygun_mu) ince
  delegasyonlarla korunur.
- surec/: dongu.py (PPDAC + manifesto), rapor.py (ürünler).
- arayuz/: ortak.py (kayıt/PII/audit/gate kancaları + dispatch_gate),
  araclar.py (57 araç = çekirdek üstü ince adaptörler), sema.py
  (-32602 doğrulayıcı), sunucu.py (YALNIZ JSON-RPC döngüsü + dispatch;
  ~230 satıra indi).
- Geriye uyumluluk: eski düz import yolları (from suc_analizi import
  mekan / import suc_analizi.sunucu) sys.modules takma adlarıyla
  aynen çalışır; pyproject giriş noktası arayuz.sunucu'ya güncellendi.

### G3 — Oturum = analizin birimi
- Gate'li analiz aracı standalone çağrıldığında bile arka planda minimal
  KEŞİF oturumu açılır (mod="kesif"): profil + kapı kararı + adım izi
  manifestoya ve log_dir/oturumlar'a düşer. Keşif oturumları onay/
  izleme istemez; tam PPDAC yalnız resmî oturumlarda zorunludur.
- Manifesto "mod" alanı taşır; dongu.listele mod'u projekte eder.
- meta.oturum_izlendi bayrağı; manifesto yazılamazsa analiz durmaz
  (uyarı loglanır) ama kapı reddi oturumsuz kalır.
- dispatch_gate kararına _profil eklenir (oturuma beslenir; meta'ya
  sızdırılmaz — _gate_meta süzgeci).

### Faz D — düzeltmeler
- D1: VIF özyinelemeli patlaması giderildi — yardımcı regresyonlar
  vif_hesapla=False ile yalnız R² hesaplar (4 değişkende OLS çağrısı
  1+k+... → 5'e indi).
- D2: mann_whitney'deki üzerine yazılan ölü z satırı temizlendi.
- G4 ucuz göçler: profil zorunluluğu (G3 ile yapısal), gate exception
  (v6.0), çok-bölge FDR otomatiği (bolge_anomali q-değerleri, v5.1'den
  beri yapısal — doğrulandı).

### Test
- TestK8_OturumBirim (4 test): standalone çağrı keşif oturumu açar +
  manifesto diskte + gate kaynaklı; gatesiz araç oturum açmaz; kapı
  reddi oturumsuz kalır; iç alan sızıntısı yok.
- Toplam: 92 birim testi + tam MCP entegrasyonu + demolar, hepsi yeşil
  (refactor sonrası sıfır davranış kaybı).

## [6.0.0] — Faz A: tek gate otoritesi (doğruluk itaatten inşaya)

Birleşik mimari belgesinin Faz A'sı. Tez: doğru analiz yapısal olarak en
az dirençli yol, yanlış analiz yapısal olarak zor.

### Yapısal değişiklikler
- YENİ MODÜL kalite.py: tek fitness-gate otoritesi `kapi()` + `KapiRed`
  istisnası. Tüm gate kuralları buraya taşındı; `veri.analiz_uygun_mu`
  geriye uyumluluk için delege eden ince sarmalayıcı (G2 çözüldü).
- Dispatch-path gate (sunucu.ARAC_GATE + dispatch_gate): gate'li her
  analiz aracı — standalone ya da döngü içi — artık çalışmadan ÖNCE
  aynı kapıdan geçer. Araç-içi gate kodu kaldırıldı (suc_oranlari,
  benford, ki_kare); bağlam kancaları yalnız profil/bağlam üretir,
  karar tek otoritededir (G4: "gate'e uy" doktrin ricası → yapı).
- Yeni yapısal bloklar: standalone mekânsal analizler (koordinat <%50
  veya tek nokta → red), benford mertebe <3 → red (önceden yumuşak
  sözlüktü), döngü içi araç çağrıları da dispatch_gate'ten geçer.
- Kapı kararı meta'ya işlenir: meta.gate + danışma sebepleri
  meta.uyarilar'a eklenir (sessiz geçiş yok).
- Döngü manifestosu döngü-içi kapı kararlarını da kaydeder
  (gate_kararlari, faz="ANALIZ-arac").
- Güvenlik blocker doğrulaması (Faz A kapsamı): PII varsayılan-red,
  kök guard, inline tavan, quadratic guard, yol hapsi — hepsi yerinde
  ve regresyon testli.

### Sözleşme değişikliği (kasıtlı)
- Gate reddi artık her araçta tutarlı biçimde isError=true +
  "HATA: fitness gate: ..." döner. benford'un eski `{"uygun": false}`
  yumuşak sözlüğü kaldırıldı.

### Test
- tests/test_kapi_doktrin.py: DOKTRIN-ENFORCEMENT SUITE (17 test) —
  tezin kanıtı: tek otorite eşdeğerliği, standalone/döngü-içi kapı
  reddi, red öncesi araç çalışmaz, danışma uyarıları kayıtlı, PII
  varsayılan-red, faz-atlama/onaysız-sonuç/belirsizlik'siz-ürün reddi.
- test_mcp.py: v6.0 blokları (standalone yapısal red, meta.gate,
  döngü içi kapı reddi, benford sözleşmesi).
- Toplam: 89 birim testi + tam entegrasyon regresyonu, hepsi yeşil.

### Yol haritası notu
Faz B (4-katman refactor, oturum=analiz birimi), Faz C (birleşik kanıt
+ muhakeme izi) bu belgenin sonraki adımlarıdır; bu sürüm Faz A'dır.

## [5.3.0] — Crime Analyst's Companion: PPDAC döngü mimarisi + Crime Harm Index

### Yeni modüller (3) ve araçlar (12, toplam 57)
- dongu.py: PPDAC durum makinesi (PROBLEM → PLAN → VERİ → ANALİZ → SONUÇ,
  döngüsel). Analiz artık tek seferlik fonksiyon değil, kayıtlı bir süreç:
  - Faz atlama engellenir; her geçiş manifestoya işlenir.
  - VERİ→ANALİZ kapısında fitness gate zorunlu (uygun değilse geçiş reddi).
  - SONUÇ fazında insan onayı zorunlu (onaylayan adı kayıt altında).
  - İzleme planı (3T-Tracking) döngüyü kapatır ve yeni döngüyü besler.
  - Oturum manifestoları JSON olarak log_dir/oturumlar altında kalıcı.
  - Ürün şablonları (taktik/stratejik/sorun_cozme) Stratified Analysis
    Model'e göre hedef kitle + önerilen araç listesi döner.
- zarar.py: Crime Harm Index (CHI) — olay sayımı yerine zarar ağırlığı:
  - zarar_hesapla: zarar-ağırlıklı toplam/grup analizi; kurum ağırlık
    tablosu JSON ile jürisdiksiyona özel (demokratik meşruiyet ilkesi).
  - power_few: zararın %50'sini üreten en küçük birim kümesi (Pareto).
  - hacim_zarar_karsilastir: hacim vs zarar sıra ayrışması —
    "seyrek ama ağır (gözden kaçan risk)" / "yoğun ama hafif
    (hacim yanılgısı)" sınıflandırması.
- rapor.py: analiz ÜRÜNLERİ — taktik brifing ve stratejik değerlendirme
  (Markdown). Belirsizlik notu zorunlu alan; eksikse ürün üretilmez.
- mekan.py: ağırlıklı KDE (zarar-ağırlıklı harm-spot haritası).
- Yeni gate tuzakları: zarar_analizi için bilinmeyen tür oranı ve
  ağırlık tablosu uyarıları; CHI araçları insan onayı bayrağında.
- DOKTRIN.md: 14-18 numaralı döngü kuralları (karar çıktısı döngü
  içinde, onaylayan kaydı, izleme planı, kurum ağırlık tablosu).

### Test
- tests/test_dongu_zarar.py: 15 test (toplam 87 birim testi).
- test_mcp.py: v5.3 entegrasyon bloğu — tam PPDAC turu, faz atlama
  reddi, iç içe döngü reddi, onaysız sonuç -32602, belirsizlik'siz
  brifing -32602, CHI araçları.

## [5.2.0] — Weisburd & Britt genişletmesi (P0–P2, hipotez testleri + regresyon)

### Yeni modüller (2) ve araçlar (15, toplam 45)
- hipotez.py: saf Python dağılım altyapısı (regularized incomplete beta
  üzerinden t/F CDF; Acklam ters normal).
  - P0: t-testleri (tek/bağımsız/Welch/bağımlı), iki oran z-testi + GA,
    Fisher exact (iki yönlü + her iki tek yönlü kuyruk), binomial exact,
    Mann-Whitney U (tie düzeltmeli), Spearman (t yaklaşım p), Kendall
    tau-b, phi katsayısı.
  - P1: tek yönlü ANOVA + eta² + Bonferroni pairwise, Kruskal-Wallis
    (tie düzeltmeli), randomization/permütasyon testi, güç analizi
    (oran ve ortalama için grup başına örneklem büyüklüğü).
- regresyon.py (P2): çoklu OLS (beta/SE/t/p, R², düzeltilmiş R², F, VIF,
  tekil matris bildirimi), ikili lojistik regresyon (IRLS, Wald z/p,
  odds oranı, McFadden R², yakınsama bayrağı).
- istatistik.py: IQR, MAD, varyasyon katsayısı (CV).
- Yeni gate eşlemeleri: küçük n güç uyarısı, lojistik n<100 uyarısı,
  Cochran ihlalinde fisher_exact yönlendirmesi.
- Yeni meta uyarıları: normallik varsayımı, eşit varyans, "odds oranı
  olasılık değildir", etki büyüklüğü abartma riski.

### Düzeltme
- Mann-Whitney: U istatistiği min(Ux, Uy) konvansiyonuna çekildi.
- Fisher: tek yönlü p her iki kuyruk için ayrı raporlanıyor.
- Lojistik: tek sınıflı hedef ve yetersiz n artık açıklayıcı hata verir.

### Test
- tests/test_hipotez.py: 22 golden-value testi (toplam 79 birim testi).
  Referanslar: t(2.0, df=10) p=0.0734, F(3.885;2,12) p≈0.05,
  Fisher [[1,9],[11,3]] p=0.002759, binom(8,10,.5) p=0.10938,
  ANOVA F=27/eta²=0.9, Kruskal H=7.2, güç n=388.
- test_mcp.py: 15 yeni aracın uçtan uca testi.

## [5.1.0] — Faz 1.5: Veri Profili ve Uygunluk Kapısı
## [5.0.0] — Faz 0–3 (bağımsız denetim planı icrası)
## [4.0.0] — İlk bağımsız güvenlik denetimi düzeltmeleri
## [3.0.0] — MCP sunucusu (saf Python stdio, 28 araç)
## [2.0.0] — Kitap temelli genişleme (Maxfield & Babbie), ileri analizler
## [1.0.0] — Çekirdek kütüphane (40 analiz)
