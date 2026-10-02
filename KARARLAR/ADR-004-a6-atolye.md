# ADR-004 — A6: Atölye (DataFlow no-code editörünün Sınama'ya taşınması)

- **Durum:** Kabul edildi — 02.10.2026, **varsayılan tercihlerle**, proje sahibinin "tüm
  aşamaları tamamla" talimatına dayanarak (sahip bilgisayar başında değilken yazıldı; her
  varsayılan aşağıda işaretli, itirazda geri alınır).
- **Kapsam:** ADR-001 A6 — "Atölye: editör ve 22 ucun FastAPI'ye taşınması; çıkış ölçütü
  DataFlow testleriyle eşdeğerlik → DataFlow dondurulur".

## Bağlam

- DataFlow (`C:\Projects\DataFlow@5ea8652`): React 19 + React Flow düğüm editörü (96 düğüm),
  tarayıcı motoru, Hono + tRPC + MySQL arka ucu (22 prosedür + HTTP uçları), Kimi OAuth,
  S3/yerel depolama, Ed25519 imzalı kanıt defteri, ml-service (scikit-learn), Science GPT,
  YerelAjan ve HARP vekilleri. Başlangıç ölçümü (yalıtılmış kopya, `npm ci` + vitest):
  **1047 test — 1040 geçti, 7 atlandı, 0 kaldı**.
- ADR-001: tek arka uç (Python/FastAPI), tek süreç, tek port, SQLite/JSONL; dil modeli
  sayı üretmez; kanıt üreten hesap sunucuda, tek motorda (AGENTS kural 5); MVP dışı:
  tahminci kara kutu ML, çok kullanıcı, bulut barındırma.

## Karar

1. **Hasat, yeniden yazım değil.** DataFlow'un ön yüzü (`src/`, birim testleri,
   yapılandırma) `git archive` ile `uygulama/atolye/`'ye birebir alınır; uyarlamalar ayrı
   commit'lerde (HASAT kural 4). Atölye ayrı bir Vite uygulamasıdır, aynı FastAPI süreci
   tarafından `/atolye/` altında sunulur (tek süreç, tek port). Rehberli `/`'de kalır.
2. **22 uç → FastAPI** (`uygulama/atolye_sunucu.py`), DataFlow'un HTTP sözleşmeleriyle:
   - tRPC prosedürleri (workflow 8, dataset 4, audit 2, catalog 4, feedback 3, auth 2) →
     `POST /api/atolye/rpc/{yol}` (JSON). Ön yüzdeki `providers/trpc.tsx` aynı arayüzü
     (`trpc.x.y.useQuery/useMutation`, `useUtils`) bu uca bağlayan bir bağdaştırıcıyla
     değiştirilir (tek uyarlama noktası; çağıran bileşenler değişmez).
   - Kalıcılık **SQLite** (`<veri kökü>/atolye.sqlite3`, stdlib `sqlite3`); şema DataFlow
     tablolarının aynısı (users, workflows, executions, audit_logs, datasets, feedback).
   - Veri setleri: `/api/datasets/upload|{id}/download|{id}` → `<veri kökü>/veri/atolye/`
     (S3 yok). *Varsayılan:* çok parçalı yükleme için `python-multipart`.
   - Kanıt defteri: `/api/evidence/record|public-key|verify` Python'a taşınır — DataFlow'un
     kendi Python doğrulayıcısı (`scripts/kanit_dogrula.py`, RFC 8785 kanonik JSON) hasat
     edilir; imza Ed25519 (`cryptography`). Anahtar ve defter veri kökünde
     (`<veri kökü>/kanit/`). Biçim (`dataflow.kanit-defteri/1`) BİREBİR — DataFlow'da üretilen
     defter Sınama'da doğrulanabilir.
   - Suç analizi köprüsü: `/api/ml/suc/manifest`, `/api/ml/suc/{arac}` → çekirdeğin
     `arac_calistir`'ı (MCP ve Rehberli ile aynı boru hattı; ml-service artık gerekmez).
   - Ajan: `/api/agent/insight` → YerelAjan vekili korunur (opsiyonel; erişilemezse 503).
3. **Kimlik:** tek yerel kullanıcı (`id 1`, rol `admin`), oturum yok; `auth.me` onu döner,
   `/api/dev-login` Atölye'ye yönlendirir. Sunucu yalnız 127.0.0.1 (A5'le aynı).
4. **Kapsam dışı (A6)**, uçları tipli 503 ile kapanır ve arayüz nedenini söyler:
   - ml-service algoritmaları (`/api/ml/ml/*`: RF, SVM, GB, lojistik, PCA, ARIMA, SHAP…) —
     ADR-001 MVP dışı "tahminci kara kutu ML".
   - Akademik Mod (`/api/science/*`, Science GPT) — Sınama'da halefi Rehberli yüz ve bilim
     katmanıdır (ön-kayıt, hipotez seti, kategorik hüküm).
   - HARP dış çapası (`/api/evidence/harp-esitle`, iletim) — dış sistem; makbuz alanı
     `{"durum": "yapilandirilmamis"}` olarak sözleşmede kalır.
   - Kimi OAuth, S3, MySQL — tek yerel kullanıcı ve SQLite ile gereksiz.
5. **Tarayıcı motoru = önizleme** (AGENTS kural 5). İşleme/temel istatistik düğümleri
   tarayıcıda koşmaya devam eder ama sonuçları "önizleme" olarak işaretlenir; kanıt yalnız
   sunucuda üretilir: `suc_*` düğümleri (çekirdek, PPDAC keşif oturumu + hash zinciri) ve
   kanıt paketi (imzalı defter).
6. **Eşdeğerlik ölçütü (uygulamadan ÖNCE ön-kayıt, `uygulama/atolye/ESDEGERLIK.md`):**
   DataFlow'un 1047 testi üç sınıfa ayrılır — (A) taşınan ön yüz testleri Sınama'da
   DEĞİŞTİRİLMEDEN geçmeli; (B) sunucu testleri Python karşılıklarıyla (durum durum
   eşleme listesi) geçmeli; (C) kapsam dışı (nedenli). Ek: Atölye uçtan uca Playwright
   testi (editör, demo akışı, kaydet/aç, sunucuda `suc_*` düğümü, kanıt paketi + doğrulama).
7. **DataFlow'un dondurulması** A6'nın son adımıdır ama kaynak depoya yazmak gerektirir
   (AGENTS kural 3) → A7 ile birlikte proje sahibinin açık onayına bırakılır; Sınama tarafı
   hazırlanır (betik + kuru çalıştırma).

## Sonuçlar

- (+) DataFlow'un editörü ve kanıt defteri tek süreçte, tek motorla; kanıt defteri biçimi
  korunduğu için eski kayıtlar doğrulanabilir.
- (−) ML ve Akademik Mod düğümleri Atölye'de kapalı (ADR-001 MVP dışı / Rehberli halef).
- (−) Ön yüz bağımlılıkları büyür (React Flow, Recharts, Zustand, react-query); çekirdek
  standart kitaplık kalır.
