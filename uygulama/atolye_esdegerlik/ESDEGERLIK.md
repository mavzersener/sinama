# A6 eşdeğerlik ön-kaydı — Atölye ↔ DataFlow (uygulamadan ÖNCE)

ADR-004 md. 6. Bu dosya, sınıflandırma ve başlangıç ölçümü Atölye hasat edilmeden ve arka uç
yazılmadan önce commit'lenir; ölçütler sonradan gevşetilmez (gerekirse yeni sürüm + gerekçe).

## Başlangıç (DataFlow tarafı)

`C:\Projects\DataFlow@5ea8652` → `git archive` → yalıtılmış kopya → `npm ci` → `vitest run`:
**1047 test — 1040 geçti, 7 atlandı, 0 kaldı.** Dosya dosya sayılar ve B sınıfı test adları:
[`taban_dataflow_5ea8652.json`](taban_dataflow_5ea8652.json).

| Sınıf | Dosya | Geçen | Anlamı |
|---|---|---|---|
| **A** taşınan ön yüz testleri | 39 | 914 | hasat edilen kodla birlikte gelir, Sınama'da **değiştirilmeden** koşar |
| **B** sunucu testleri | 9 | 88 | Python karşılıklarıyla (durum durum) — `tests/test_atolye_*.py` |
| **C** kapsam dışı | 6 | 38 (+7 atlanan) | nedeni JSON'da: oturum yok (dev-login), DataFlow belgesi (durum-belgesi), canlı MySQL (e2e-live, saat-dilimi), depo dışı gerçek CSV (gercek-csv-tani), HARP (kanit-harp) |

B dosyaları: workflow-router 20, dataset-router 13, audit-router 12, integration 4, csv 9,
storage 3, kanit-defteri 13, kanit-rota 6, kanit-uctan-uca 8.

## Ölçütler

| Kimlik | Ölçüt | Eşik |
|---|---|---|
| **E1** | A sınıfı: her dosyada Sınama'da geçen test sayısı = DataFlow başlangıcındaki; kalan 0. Tek istisna `oracle` (pandas/scikit-learn'lü Python yoksa DataFlow'da da `skipIf` ile atlar) — yerelde geçmeli | = 914 / 914 (yerel) |
| **E2** | B sınıfı: 88 testin her biri için `# DataFlow: <dosya> › <test adı>` işaretli bir Python karşılığı var ve geçiyor | = 88 / 88 |
| **E3** | Atölye uçtan uca (Playwright, gerçek tarayıcı + gerçek arka uç): editör açılır; demo akışı koşar ve tarayıcı sonuçları "önizleme" işaretlidir; akış sunucuya kaydedilir, listelenir, yeniden açılır; bir `suc_*` düğümü SUNUCUDA koşar (çekirdek oturum kimliği görünür); kanıt paketi defterde kaydedilir ve `verify` geçerli döner | hepsi |
| **E4** | Kanıt defteri biçim uyumu: DataFlow'un kendi koduyla üretilmiş defter ([`sentetik/dataflow_defteri`](sentetik/dataflow_defteri), 3 kayıt) Sınama'nın Python defteriyle doğrulanır; Sınama'nın yazdığı defter DataFlow'un bağımsız doğrulayıcısıyla (`kanit_dogrula.py`) doğrulanır | ikisi de geçerli |
| **E5** | Tek süreç: Atölye ve Rehberli aynı FastAPI sürecinden (`/atolye/`, `/`); MySQL, S3, ml-service, Kimi gerekmez | = 1 |

## Öngörü

Başlangıç (Sınama, hasattan önce): E1–E5 hepsi 0 (Atölye yok). Uygulama öngörüsü: E1 914/914
(ön yüz kodu birebir; yalnız `providers/trpc.tsx` bağdaştırıcısı ve önizleme işareti değişir —
ikisini test eden A dosyası yok); E2 88/88; E3, E4, E5 = 1. En riskli: E1'de `suc-analizi-nodes`
(düğümler Sınama'nın araç kaydından yeniden üretilecek) ve `oracle` (Python ortamı).
