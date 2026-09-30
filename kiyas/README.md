# Bilimsel Muhakeme Kıyası (BMK)

Programın bilimsel gücünü **ölçmek** için gerçeği önceden bilinen sentetik vakalar
(ADR-001 md.7). "Daha iyi oldu" iddiası ancak bu kıyasta ölçülürse geçerlidir.

## Kurallar

1. **Ön-kayıt.** Vakalar (soru, gerçek, doğru hüküm, eşikler, öngörüler), üreteç ve
   koşucu ilk ölçümden ÖNCE `kilit.json`'da SHA-256 ile kilitlenir. Kilitli bir dosya
   değişirse koşucu ölçmeyi reddeder. Değişiklik yeni sürümle ve gerekçesiyle yapılır;
   eşik ya da gerçek, sonuç görüldükten sonra ayarlanmaz.
2. **Veri dosyası yok.** Her vaka tohumlu üreteçle çalışma anında kurulur
   (`uretec.py`, yalnız `random.random()` — sürümler ve işletim sistemleri arasında
   birebir aynı). Gerçek veriye yazılmaz; ölçücü ayrıca görür.
3. **Başarısız ölçüt bir bulgudur.** Kıyas ölçer, kapı değildir. CI yalnız kilidin
   sağlamlığını ve yeniden ölçümün kayıtlı sonuçla birebir aynı olduğunu denetler.
4. **Araçlar resmi yoldan çağrılır** (`sinama.arayuz.sunucu.arac_calistir`, MCP ile aynı
   boru hattı) ve sade kullanıcının göreceği varsayılan argümanlarla.
5. **Sonuç dosyası davranışın aynasıdır.** `sonuclar/v0.json` güncel çekirdeğin v0
   kıyasındaki sonucudur; çekirdek davranışını değiştiren commit onu AYNI commit'te
   günceller (CI `--dogrula` bunu zorlar) — her bilimsel davranış değişikliği diff'te
   görünür. İlk ölçüm `sonuclar/v0_ilk_olcum.json`'da dondurulmuştur (önce/sonra için).
6. **Tohum ayrımı.** Her sürümün ölçüm tohumları ayrıdır (v0 1–30, v1 101–130,
   v2 201–230). Bir ön-kayıttan sonra yapılan YÖNTEM TASARIMI keşfi yalnız 900 ve
   üstü tohumlarla yapılır; ölçüm tohumları tasarımda kullanılmaz — yöntem ölçüm
   verisine uydurulursa önce/sonra farkı iyimser yanlı olur.

## Sürümler

- **v0** (`kilit.json`, `vakalar/`, `sonuclar/v0*.json`): V1 kümelenme, V2 bildirim
  artefaktı, V3 ortak MO. Donmuştur; K2.4 ölçütü hatalıdır (v1'de V2b ile değiştirildi).
- **v1** (`v1/`): V2b kanal sayımı, V4 LISA, V5 yükselen sıcak nokta, V6 bölge
  anomalisi, V7 yayılmış seri. v0'a dokunmadan eklendi; kendi kilidi v0
  bağımlılıklarını da kapsar. Bulgular: `v1/sonuclar/v1_bulgular.md`.
- **v2** (`v2/`): V8 seri bağlantısı — dört varyant (sıkı = V3, yayılmış = V7,
  davranışı tutarsız seri, seri yok) ve katman farkındalıklı ölçütler: tüm adaylarda
  geri çağırma, güçlü katmanda kesinlik, aday listesi kesinliği, seri yokken aile
  yanlış alarmı, çıktı sözleşmesi (`katman` + `kanit` hatları). Ölçüm öncesi tasarım
  hipotezi vaka dosyasında zaman damgalıdır.
- **v3** (`v3/`): V9 kategorik hüküm (ADR-002) — Rehberli akış (`rehberli_calisma`)
  gerçeği bilinen yedi senaryoda: bildirim artefaktı, gerçek artış (doğrulayıcı ve
  keşifsel), odaklı/rastgele, seri/seri yok. Ölçütler: doğru kategori, en güçlü rakip,
  keşifsel ve SERİ tavanları, insan onayı, H_bilinmeyen, sayısal olasılık yokluğu,
  belirlenimcilik. Bilim katmanı UYGULANMADAN önce kilitlendi; çıktı sözleşmesi vaka
  dosyasındadır.

## Düzeyler

- **v0 — çekirdek:** araçların gerçeğe göre doğruluğu, yanlış alarmı ve çıktı
  sözleşmesi (deterministik).
- **A5 — sistem:** dil modeli + araçlar; hüküm, rakip açıklama kapsamı, yasak iddialar
  (`sistem_olcutleri`).

## Komutlar (depo kökünden)

```bash
PYTHONUTF8=1 python kiyas/kos.py
```

```bash
PYTHONUTF8=1 python kiyas/kos.py --dogrula
```

```bash
PYTHONUTF8=1 python kiyas/v1/kos_v1.py --dogrula
```

```bash
PYTHONUTF8=1 python kiyas/v2/kos_v2.py --dogrula
```

```bash
PYTHONUTF8=1 python kiyas/v3/kos_v3.py --dogrula
```
