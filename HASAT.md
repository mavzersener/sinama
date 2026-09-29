# Hasat defteri

Program mevcut projelerden **hasatla** kurulur: kod yeniden yazılmaz, testleriyle
taşınır ve her parçanın kaynağı buraya yazılır (ADR-001 md.2).

## Kurallar

1. Kaynaktan yalnız **izlenen dosyalar** alınır:
   `git -C <kaynak> archive <commit> -- <yol> | tar -x -C <hedef>`.
   Çalışma ağacı kopyalanmaz — DataFlow'da ignore'lu `kanit/` (özel imza anahtarı),
   `uploads/` (veri setleri) ve `.env` fiziksel olarak durur.
2. Her hasat bir kayıt satırıdır: hedef, kaynak depo, commit, alınan yol(lar),
   gelen testler, not.
3. Parça testleriyle gelir; testler burada da yeşil olmadan commit yapılmaz.
4. Uyarlama gerekiyorsa önce birebir hasat commit'i, sonra ayrı uyarlama commit'i —
   fark izlenebilir kalır.
5. Git'siz kaynaktan (ör. hazırlık kopyası) alınan her dosyanın SHA-256'sı not
   sütununa yazılır.
6. Hasat edilen parça bekçiden geçer; bekçiyi hasat için gevşetmek yasaktır.

## Kayıtlar

| Tarih | Hedef | Kaynak depo | Commit | Alınan | Testler | Not |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | henüz hasat yok (A0) |

## Kaynak depoların başları (29.09.2026)

| Depo | Baş | Rol |
|---|---|---|
| `C:\Projects\suc_analizi` | `20d6e2c` | çekirdek (A2) |
| `Documents\ChatGPT\JSGA Kolluk\duzeltme_suc_analizi` | git'siz | yalnız P06 mahremiyet turu (A2; `kanit.py` elle üçlü birleştirme) |
| `C:\Projects\science_gpt` | `190da89` | bilim katmanı şemaları, statsmodels doğrulama motoru (A4) |
| `C:\Projects\DataFlow` | `5ea8652` | Rehberli (A5), Atölye (A6), tek arka uç temeli ml-service (A5) |
| `C:\Projects\harp_pol_x` | `fbf3f31` | BMK üreteci, rakip açıklama tohumları, kurallar (A3–A4) |
| `C:\Projects\AnlamCekirdegi` | `3ede056` | epistemik sözlük, `llm_packet` fikri (A4+) |
| `C:\Projects\YerelAjan_v2` | `d11fceb` | llama.cpp ayar dersleri (bilgi; kod alınmaz) |
| `C:\Projects\CinKollukKatalog` | git'siz | kanıt gücünü türetme ilkesi (bilgi; kod alınmaz) |

## Hasat adayları

| Kaynak | Alınacak | Aşama |
|---|---|---|
| suc_analizi | 78 yöntemlik stdlib çekirdek ve altın testleri; uygunluk kapısı; PPDAC oturumu; kanıt zinciri v2; ön-kayıt kilidi; provenans; `analiz_oner` karar ağacı (R01–R45); `olay/1` şeması; teori yorumu; deterministik anlatı (`makale`) | A2 |
| hazırlık kopyası | P06: güvenli özet, gerekçe özeti (digest), olay akışında PII yok | A2 |
| science_gpt | araştırma protokolü şemaları ve kilit; DOI/ISBN doğrulama; statsmodels yürütücüleri ve tanıları (P5/P6); "sayılar yalnız deterministik kaynaktan" (P7); LLM istem sürümleme | A4 |
| DataFlow | Rehberli Mod akışı ve sonuç görselleri; tipli hata kartları; tam CSV okuma; CSV dışa aktarma güvenliği; DEMO işareti; referans (oracle) test deseni; güvenli ifade dili; no-code editör | A5–A6 |
| DataFlow ml-service | FastAPI iskeleti ve suc köprüsü → tek arka uç temeli | A5 |
| harp_pol_x | simülatörün karıştırıcı çarpanları (devriye/kamera/bildirim/caydırıcılık); alternatif açıklama tohumları; `calibrated_probability_claim: False` koruması; "incelenmemiş hipotezle kapanış yok" kuralı | A3–A4 |
| AnlamCekirdegi | `truth_status` sözlüğü; açık dünya ilkesi; dikkat bütçesi; graf sınırlı LLM paketi fikri | A4+ |

## Alınmayacaklar

- DataFlow Node arka ucu (Hono/tRPC/MySQL/Kimi-OAuth): ön yüzün kullandığı 22 uç
  (13 tRPC + 9 REST) FastAPI + SQLite'a **taşınır**; kod alınmaz.
- HARP iskelet ajanları (konvoy, AML grafı, duygu/aldatma, federe koordinatör,
  frugal router vb.).
- Tahminci kara kutu ML (sklearn/xgboost düğümleri) — MVP dışı.
- Her türlü oturum/log/kanıt kaydı, suc_analizi `oturumlar/` (sentetik test oturumları dahil).
- DataFlow'un başka projelere ait plan belgeleri (`GELISTIRME_PLANI_*`).

## Hasattan önce incelenecekler

- HARP `data/open_crime_bank`: kaynağı ve lisansı.
- science_gpt `examples/*.csv`: gerçekten sentetik mi?
- HARP `tests/fixtures/dataflow_kanit/genel_anahtar.pem`: genel anahtar (sır değil);
  gerekirse izin listesine gerekçeyle.

## "Bir daha asla" test adayları

Hasatla birlikte her biri bu depoda bir teste dönüşür.

| Ders | Kaynak |
|---|---|
| stdio/konsol cp1252 → UTF-8 kilidi | suc_analizi `f07b31e` |
| ISO 8601 `T` ayraçlı tarih çözümü | suc_analizi `f83ce1e` |
| İstek bağlamı kurulmadan yürütme → 23 araç 500 | suc_analizi `dd004c9` |
| Alternatif girdi kipinde eksik argüman → çıplak 500 | suc_analizi `1f211c0` |
| Zincir v1: ortadaki kayıt kurcalaması saptanmıyordu | suc_analizi `5c27920` |
| Olay akışına PII ve dinamik grup etiketi | P06 (hazırlık kopyası) |
| Tarayıcıda ilk 5000 satırda sessiz kesme | DataFlow Faz 3 |
| Aykırı değerin yanlış satıra atanması | DataFlow Faz 1 |
| Grafik düğümünün uydurma veri çizmesi | DataFlow Faz 1 |
| DB zaman damgalarında +8 saat kayması | DataFlow Faz 2 |
| `extend_field` ifadesinin `new Function` ile çalışması | DataFlow Faz 4 |
| CSV dışa aktarmada formül enjeksiyonu | DataFlow Faz 5 |
| Boş koordinat hücrelerinin özellik sayısını düşürmesi | DataFlow `ae706ce` |
| `İ` → `i̇` birleşik nokta normalizasyonu | DataFlow Hedeften Akış |
| Doğrulayıcı okuyucusunun bozuk satırda fırlatması | DataFlow/HARP 24.09 |
