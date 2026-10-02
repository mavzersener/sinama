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
7. **Tek istisna (bekçi uyumu):** bekçinin kişisel veri kuralına takılan sentetik
   test değerlerine yalnız `bekci:izin` yorumu eklenebilir ve bu ekleme birebir
   hasat commit'ine girer (bekçi o commit'i başka türlü geçirmez; `--no-verify`
   ise push'ta yakalanır). Commit mesajı değişen satırları listeler; farkın yalnız
   yorum eklemesi olduğu, satır sonu yorumu ayıklanmış karşılaştırmayla kanıtlanır.

## Kayıtlar

| Tarih | Hedef | Kaynak depo | Commit | Alınan | Testler | Not |
|---|---|---|---|---|---|---|
| 29.09.2026 | `cekirdek/` | `C:\Projects\suc_analizi` | `20d6e2c` | izlenen ağacın tamamı; hariç: `oturumlar/` (sentetik test oturumları), `.githooks/` (kanonik depoya özgü tüketici kapıları), `.gitattributes` (kök kapsıyor), `suc_analizi_audit.log` (izlenen boş log), `release.sh` (Kimi ortamına, `/mnt/agents/output`'a yazıyor) | 493 birim (1 atlama) + kapsam kapısı + `test_mcp.py` 132 kontrol + 2 demo — hepsi yeşil | 93 dosya; 92'si kaynak blob'larıyla birebir. `tests/test_faz_f.py`: 2 satıra yalnız `bekci:izin` yorumu (kural 7) |
| 29.09.2026 | `cekirdek/sinama/surec/{kanit,dongu,rapor}.py`, `cekirdek/test_mcp.py`, `cekirdek/tests/{test_kanit_muhakeme,test_duzeltme_06_mahremiyet}.py` | `Documents\ChatGPT\JSGA Kolluk\duzeltme_suc_analizi` (git'siz, P06 mahremiyet turu) | ata: kanonik `2330936` (baseline_06 hash'leriyle doğrulandı; `dongu.py` kanonikte karışık satır sonluydu, normalleştirilmiş içerik ataya eşit) | üçlü birleştirme (`git merge-file --diff3`), ad dönüşümü ata ve kopyaya da uygulandı; `dongu`, `rapor`, `test_mcp` temiz; `kanit.py` 6 + `test_kanit_muhakeme.py` 1 çatışma elle, gerekçeli çözüldü | P06 5 test + bağımsız kabul betiği (ad dönüşümlü geçici kopya) + yeni `test_duzeltme_08_p06_v2.py` (3; iki mutasyon yakalandı); tam kapı 505 test | kaynak SHA-256 (ilk 12): kanit `9c34e645a1f5`, dongu `3753b0a7c5d9`, rapor `ec566113eaf7`, test_mcp `ea9ab3457adc`, test_kanit_muhakeme `aa74302d317f`, test_duzeltme_06 `1f038be90aed` |
| 02.10.2026 | `uygulama/web/` (A5, ADR-003) | `C:\Projects\DataFlow` | `5ea8652` | `tailwind.config.js`, `postcss.config.js`, `src/components/ui/{button,card}.tsx`, `src/lib/utils.ts`, `src/index.css` (git archive; 6 dosya, blob'larla birebir) | ön yüz derlemesi (`tsc -b && vite build`) A5.2'de | `index.css` React Flow stilleri ve `overflow: hidden` gövdesi taşıyor — A5.2'de ayrı uyarlama commit'i |
| 02.10.2026 | `uygulama/atolye/` (A6, ADR-004) | `C:\Projects\DataFlow` | `5ea8652` | `src/` (tamamı), `contracts/`, A sınıfı 34 test dosyası (`tests/`), yapılandırma (`index.html`, `package.json`, `package-lock.json`, `vite.config.ts`, `vitest.config.ts`, `tsconfig*.json`, `tailwind.config.js`, `postcss.config.js`, `components.json`, `eslint.config.js`), `scripts/{generate_suc_nodes,kanit_dogrula}.py` — 128 dosya | eşdeğerlik E1 (ön-kayıt `93fd618`): uyarlamadan sonra ölçülür | `tests/setup.ts` ALINMADI: sahte parolalı `DATABASE_URL` (bekçi sır kuralı atlanamaz; MySQL Atölye'de yok) — uyarlama commit'inde o satır olmadan yazıldı. `tests/demo-isareti.test.ts`: 1 satıra yalnız `bekci:izin` (sentetik telefon biçimi; kural 7, yorum ayıklanmış karşılaştırma birebir). Ek hasat `443bcf4`: `tests/veri/uretici.ts` (matris testinin üreteci), `tests/ui/` (DataFlow Playwright arayüz testleri) — 7 dosya, birebir |

## Kavram hasadı (kod alınmadan)

Kaynağın kodu taşınamadığında (bağımlılık ya da ilke çatışması) yalnız kavram alınır;
izlenebilirlik için kaynak@commit burada yazılır.

| Tarih | Hedef | Kaynak | Alınan kavram | Alınmayan (neden) |
|---|---|---|---|---|
| 30.09.2026 | `cekirdek/sinama/bilim/` (ADR-002) | `science_gpt@190da89` `src/science_gpt/domain.py` | araştırma amacı ayrımı (confirmatory/exploratory → keşifsel tavanı); kilit = onay + içerik hash'i (mevcut ön-kayıt kilidi hipotez setini kapsar) | pydantic modelleri (çekirdek yalnız standart kütüphane) |
| 30.09.2026 | `cekirdek/sinama/bilim/hukum.py` | `harp_pol_x@fbf3f31` `src/harppolx/schemas.py` | `reasoning_trail` (kural, girdi, sonuç) → hüküm `kurallar` izi; `requires_human_review` → `insan_onayi_gerekir` | `confidence` / `priority_score` ondalıkları (AGENTS kural 6: sahte olasılık) |
| 02.10.2026 | `uygulama/sunucu.py` (A5) | `DataFlow@5ea8652` `ml-service/app/routers/suc_analizi_koprusu.py` | çekirdeğe yalnız kamusal `arac_calistir` ile girmek (MCP ile aynı boru hattı); hata tipi → HTTP durumu (kapı 422, istemci 400, sistem 500) | FastAPI iskeleti ve ML yığını (pandas/sklearn/shap — çekirdek stdlib), yalnız satır içi veri ilkesi (A5'te veri kökünden yol hapsiyle dosya okunur) |

## Uyarlamalar (hasattan sonra, ayrı commit'lerle)

| Tarih | Kapsam | Ne değişti | Doğrulama |
|---|---|---|---|
| 29.09.2026 | `cekirdek/` | paket `suc_analizi` → `sinama`, `SUC_ANALIZI_*` → `SINAMA_*`, dağıtım/komut/MCP adı `sinama`; CHANGELOG tarihçesi eski adla kaldı | 497 test (493 + 4 paket kimliği), kapsam kapısı aynı 23 modül / %93,7, test_mcp 132/0, demolar; paket kimliği testi mutasyonla sınandı |
| 02.10.2026 | `uygulama/web/src/index.css` (A5.2) | React Flow stilleri (DataFlow tuvaline özgü) çıkarıldı; gövdeden `overflow: hidden` ve `#root` 100vh kilidi kaldırıldı (Rehberli ekranlar kayar); yazı tipi eklendi. Tema değişkenleri birebir | `tsc -b && vite build`; üç ekran tarayıcıda uçtan uca (TR/EN) |
| 02.10.2026 | `uygulama/atolye/` (A6 uyarlama 1) | `src/providers/trpc.tsx`: tRPC istemcisi → `POST /api/atolye/rpc/<yol>` bağdaştırıcısı (aynı `useQuery/useMutation/useUtils` arayüzü, satır türleri drizzle şemasından); `vite.config.ts`: `base: /atolye/`, `/api` → 127.0.0.1:8810 vekili, Hono dev sunucusu ve Kimi eklentisi çıktı; `package.json`: sunucu bağımlılıkları (Hono, tRPC, drizzle, mysql2, S3, jose, zod…) ve `db:*`/`start`/`matris` betikleri çıktı; `tsconfig.json`: hasat edilmeyen `tsconfig.server.json` başvurusu çıktı; `tests/setup.ts`: `DATABASE_URL` satırı olmadan | `tsc -b`; vitest **914/914** (E1, ön-kayıt `93fd618`) |

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
