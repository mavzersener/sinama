# uygulama — Sınama'nın tek süreç arka ucu ve Rehberli yüzü (A5, ADR-003)

Üç ekran: **Soru → Plan → Hüküm**. Hesap çekirdekte, tek motorda (`cekirdek/`, standart
kitaplık); bu dizin yalnız HTTP ve ön yüz katmanıdır. Türkçe varsayılan, İngilizce seçenek.

## Çalıştırma (depo kökünden)

```bash
python -m pip install -r uygulama/gereksinimler.txt
```

```bash
cd uygulama/web && npm ci && npm run build
```

```bash
PYTHONUTF8=1 python -m uygulama --veri-koku C:/yol/depo-disi/veri
```

Tarayıcı: <http://127.0.0.1:8810>. Yalnız geri döngü adresine bağlanır.

- **Veri kökü** depo dışında olmalıdır (içindeyse arka uç başlamaz). Verilmezse
  `SINAMA_VERI_KOKU`, o da yoksa `%LOCALAPPDATA%\sinama`. Düzen: `veri/` (girdi CSV'leri,
  yüklemeler), `oturumlar/` (oturum + kanıt zinciri).
- **Dil modeli** opsiyoneldir (`--dil-modeli http://127.0.0.1:8080`, `yok` → kapalı): soru
  türü önerisi ve hükmün sade dille özeti; sayı üretmez, hükmü değiştiremez. Kapalıyken
  öneri kural tabanlıdır ve akış tam çalışır.
- Geliştirme: arka uç çalışırken `cd uygulama/web && npm run dev` (Vite, `/api` arka uca aktarılır).
- `--ac` başlayınca tarayıcıyı açar.

## İnternetsiz kurulum paketi

```bash
PYTHONUTF8=1 python betikler/a5_paketle.py --cikti C:/paketler
```

Depo kaynağı (`git archive HEAD`, yalnız izlenen dosyalar), derlenmiş ön yüz, Python
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
