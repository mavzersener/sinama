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
