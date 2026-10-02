# uygulama — Sınama'nın tek süreç arka ucu, Rehberli ve Atölye yüzleri (A5 ADR-003, A6 ADR-004)

- **Rehberli** (`/`): üç ekran **Soru → Plan → Hüküm**; Türkçe varsayılan, İngilizce seçenek.
- **Atölye** (`/atolye/`): DataFlow'un düğüm editörü (hasat, `atolye/`); keşif ve önizleme.

Hesap çekirdekte, tek motorda (`cekirdek/`, standart kitaplık); bu dizin yalnız HTTP ve ön yüz
katmanıdır. İki yüz aynı süreçte, aynı portta çalışır.

## Çalıştırma (depo kökünden)

```bash
python -m pip install -r uygulama/gereksinimler.txt
```

```bash
cd uygulama/web && npm ci && npm run build
```

```bash
cd uygulama/atolye && npm ci && npm run build
```

```bash
PYTHONUTF8=1 python -m uygulama --veri-koku C:/yol/depo-disi/veri
```

Tarayıcı: <http://127.0.0.1:8810> (Rehberli), <http://127.0.0.1:8810/atolye/> (Atölye). Yalnız
geri döngü adresine bağlanır; Atölye uçları geri döngü dışından gelen isteği ayrıca reddeder.

- **Veri kökü** depo dışında olmalıdır (içindeyse arka uç başlamaz). Verilmezse
  `SINAMA_VERI_KOKU`, o da yoksa `%LOCALAPPDATA%\sinama`. Düzen: `veri/` (girdi CSV'leri,
  yüklemeler), `oturumlar/` (oturum + kanıt zinciri).
- **Dil modeli** opsiyoneldir (`--dil-modeli http://127.0.0.1:8080`, `yok` → kapalı): soru
  türü önerisi ve hükmün sade dille özeti; sayı üretmez, hükmü değiştiremez. Kapalıyken
  öneri kural tabanlıdır ve akış tam çalışır.
- Geliştirme: arka uç çalışırken `cd uygulama/web && npm run dev` (Vite, `/api` arka uca aktarılır).
- `--ac` başlayınca tarayıcıyı açar.

## Atölye (A6, ADR-004)

DataFlow'un ön yüzü birebir hasat edildi (`atolye/`, uyarlamalar `HASAT.md`'de); arka ucu
Python'a taşındı:

- `atolye_sunucu.py` — DataFlow'un 23 tRPC prosedürü `POST /api/atolye/rpc/<grup.prosedür>`
  (sözleşme birebir), veri seti yükle/indir/sil, kanıt defteri uçları, suç analizi köprüsü
  (`/api/ml/suc/*` → çekirdeğin `arac_calistir`'ı), YerelAjan vekili (`SINAMA_AJAN_URL`,
  varsayılan `http://localhost:8800`).
- `atolye_depo.py` — SQLite (`<veri kökü>/atolye.sqlite3`, DataFlow tabloları); yüklenen
  veri setleri `<veri kökü>/veri/atolye/`.
- `kanit_defteri.py` — Ed25519 imzalı, hash zincirli kanıt defteri (`<veri kökü>/kanit/`),
  biçim DataFlow'unkiyle aynı (`dataflow.kanit-defteri/1`); DataFlow'un bağımsız doğrulayıcısı
  `atolye/scripts/kanit_dogrula.py` her iki yönde çalışır.
- Tek yerel kullanıcı (rol admin), oturum yok. Kapsam dışı (tipli 503 ve neden): sunucu
  taraflı ML algoritmaları (MVP dışı), Akademik Mod (halefi Rehberli), HARP dış çapası.
- **Tarayıcı motoru önizlemedir** (AGENTS kural 5): sonuç kartında ÖNİZLEME / SUNUCU /
  DİL MODELİ işareti. Kanıt yalnız sunucuda üretilir: suç analizi düğümleri (`suc_*`) ve
  kanıt paketi.
- Geliştirme: arka uç çalışırken `cd uygulama/atolye && npm run dev` (Vite, `/api` aktarılır).

Eşdeğerlik (ön-kayıt `atolye_esdegerlik/ESDEGERLIK.md`):

```bash
PYTHONUTF8=1 python betikler/a6_esdegerlik.py
```

E1 taşınan 914 ön yüz testi değiştirilmeden, E2 DataFlow'un 88 sunucu testinin Python
karşılıkları (`tests/test_atolye_*.py`, `# DataFlow:` işaretli), E3 Atölye uçtan uca
(`cd uygulama/atolye && npm run e2e`), E4 kanıt defteri biçim uyumu, E5 tek süreç.

## İnternetsiz kurulum paketi

```bash
PYTHONUTF8=1 python betikler/a5_paketle.py --cikti C:/paketler
```

Depo kaynağı (`git archive HEAD`, yalnız izlenen dosyalar), derlenmiş iki ön yüz, Python
tekerlekleri, `KURULUM.md`, `baslat.bat` ve `SHA256SUMS.txt` tek zip'te; çıktı depo dışında
olmalıdır. Tekerlekler paketleyen yorumlayıcı içindir (farklı hedef: `--python-surumu`,
`--platform`).

## Uçtan uca ekran testi

```bash
cd uygulama/web && npm run build && npm run e2e
```

Playwright gerçek tarayıcıda üç ekranı gerçek arka uçla koşar (`e2e/sunucu.py`: geçici veri
kökü, BMK üreteçlerinden sentetik veri, dil modeli kapalı). Python yorumlayıcısı
`SINAMA_PY` ile verilebilir. CI'da `uygulama` işinde koşar.

## Ölçüm

BMK v10 (`kiyas/v10/`): HTTP hükmü = MCP hükmü, veri kökü, ekran sözleşmesi, yasak alanlar,
tr/en sözlük tamlığı, dil modelsiz çalışma, bağlanma adresi. Sözlükler
`web/src/i18n/{tr,en}.json` — yeni bir `t('…')` anahtarı iki dosyaya da eklenmezse ölçüt düşer.
