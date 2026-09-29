# BMK v0 — ilk ölçüm ve bulgular (29.09.2026)

- **Ön-kayıt:** `db8bf95` (11:47:42 +08:00) — vakalar, üreteç ve koşucu sonuç
  görülmeden kilitlendi. **Ölçüm:** bu commit; sayılar `v0.json`'dadır.
- **Kapsam:** çekirdek düzeyi (araçlar, dil modeli yok); 3 vaka × 30 tohum; araçlar
  resmi yoldan ve sade kullanıcının göreceği **varsayılan** argümanlarla çağrıldı.

## Ön-kayıtlı sonuç: 15 ölçütün 6'sı geçti

| Ölçüt | Değer | Eşik | Sonuç | Öngörü |
|---|---|---|---|---|
| K1.1 NNI gücü | 0,233 | ≥ 0,90 | KALDI | — |
| K1.2 NNI yanlış alarmı | 0,000 | ≤ 0,10 | geçti | — |
| K1.3 Moran gücü | 0,967 | ≥ 0,90 | geçti | — |
| K1.4 Moran yanlış alarmı | 0,000 | ≤ 0,10 | geçti | — |
| K1.5 Gi* gücü | 1,000 | ≥ 0,90 | geçti | — |
| K1.6 Gi* yanlış alarmı (aile) | 0,700 | ≤ 0,10 | KALDI | başarısız → **doğrulandı** |
| K2.1 CUSUM kırılma zamanı | 0,467 | ≥ 0,90 | KALDI | — |
| K2.2 kayıtlı artış (trend) | 1,000 | ≥ 0,90 | geçti | — |
| K2.3 sahte trend (sabit kanal) | 1,000 | ≤ 0,10 | KALDI | başarısız → **doğrulandı** |
| K2.4 kanal ayrıştırma | 0,800 | ≥ 0,90 | KALDI | — (ölçüt tasarım hatası, aşağıda) |
| K2.5 ITS aracı açık | 0 | 1 | KALDI | başarısız → **doğrulandı** |
| K3.1 seri geri çağırma | 1,000 | ≥ 0,90 | geçti | — |
| K3.2 seri kesinliği | 0,050 | ≥ 0,90 | KALDI | başarısız → **doğrulandı** |
| K3.3 "benzerlik ≠ kimlik" uyarısı | 0 | 1 | KALDI | başarısız → **doğrulandı** |
| K3.4 insan onayı | 0 | 1 | KALDI | başarısız → **doğrulandı** |

Kod incelemesinden yazılan 6 öngörünün 6'sı doğrulandı. Öngörülmeyen 3 başarısızlık
(K1.1, K2.1, K2.4) aşağıdaki keşifle açıklandı.

## Bulgular

1. **Gi* rastgele veride "sıcak nokta" üretiyor (K1.6).** Tamamen rastgele desenlerin
   %70'inde en az bir hücre "sıcak" etiketi aldı (tohum başına ortalama 1,6 / ~36
   hücre). Neden: çoklu test düzeltmesi yok ve %90 güven de "sıcak" sayılıyor.
   Çekirdekte `ileri.fdr_benjamini_hochberg` var ama Gi* kullanmıyor. Gerçek kümeyi
   yakalama gücü ise tam (K1.5 = 1,0) — sorun güç değil, yanlış alarm.
2. **Seri eşleştirme ortak MO'yu seri sanıyor (K3.2–K3.4).** Her tohumda, bağımsız
   faillerin 190 çiftinin **190'ı** "seri" işaretlendi; işaretlenen çiftlerin yalnız
   %5'i gerçek seri. Neden: düz Jaccard, MO ifadesinin yaygınlığını (taban oranı)
   hesaba katmıyor; uzay-zaman yakınlığı kullanılmıyor. Çıktı "benzerlik ≠ kimlik"
   uyarısı taşımıyor ve insan onayı istemiyor. Gerçek seriyi bulma gücü tam (K3.1).
3. **Trend, anlamlılık sınamadan yön söylüyor (K2.3).** Oranı sabit karakol kanalında
   30 tohumun 30'unda "artan" ya da "azalan" dedi.
4. **Kesintili zaman serisi aracı yok (K2.5).** `kesinti_analizi` çekirdekte var ama
   araç olarak açık değil; planlayıcı bir kırılmayı sınayamıyor.
5. **CUSUM varsayılanları bu ölçeğe ayarlı değil (K2.1).** Ayrıntı keşifte.
6. **NNI yerel kümeye duyarsız ve varsayılanı yanlı (K1.1).** Ayrıntı keşifte.

## Keşif (ÖN-KAYIT DIŞI — hipotez üretir, ölçüm değildir)

Betik: `kiyas/kesif/v0_nedenler.py` (aynı tohumlar, kilitli dosyalara dokunmaz).

- **K1.1:** kenar düzeltmesiz varsayılanda NNI rastgele veride bile 1,046 (dağınık
  yönüne yanlı). Kenar düzeltmesiyle rastgele 1,015'e iner, güç %23 → %43'e çıkar;
  yine düşük: NNI tüm noktaların ortalamasıdır, %70 arka plan yerel kümeyi seyreltir
  (bu senaryoda kuramsal NNI ≈ 0,93). Sonuç: NNI yerel küme için birincil kanıt
  olmamalı; varsayılan kenar düzeltmeli olmalı.
- **K2.1:** ilk alarmlar kesintiye göre dağınık: 4/30 tohumda 77–281 gün **önce**
  yanlış alarm, 14/30 pencerede, 12/30'da 60 günden geç (en geç +231). Günde ~1,3
  olaylık seyrek seride %30 artış ≈ 0,35 standart sapma; varsayılan CUSUM ~1 sapmalık
  kaymaya ayarlı. Aday çözüm: haftalık/aylık toplama ve eşiğin (h) ortalama çalışma
  uzunluğuna (ARL) göre ayarlanması.
- **K2.4 — ölçüt TASARIM HATASI (koşucu ölçütü, araç değil):** `capraz_tablo` 30/30 tohumda ham veriyle
  birebir doğru saydı. Düşen koşul "artışın ≥ %80'i yeni kanalda"; karakol kanalındaki
  doğal Poisson dalgalanması 6/30 tohumda bunu bozdu. Ölçüt aracın yeteneğini değil
  verinin gürültüsünü ölçtü. Ön-kayıt gereği v0'da değiştirilmedi; v1'de gerekçesiyle
  düzeltilecek (ör. araç sayımı = ham sayım, ya da Poisson toleranslı pay).

## Bilimsel güç için sıradaki işler (A4 girdisi)

Her biri BMK'da **önce/sonra** ölçülerek kabul edilir, görüşle değil:

| Değişiklik | Hedef ölçüt |
|---|---|
| Gi*'ye Benjamini–Hochberg FDR; %90'ı varsayılan "sıcak" saymamak | K1.6 |
| Seri eşleştirmede taban oranı ağırlıklı benzerlik + uzay-zaman; uyarı + insan onayı | K3.2–K3.4 |
| Trende anlamlılık sınaması; anlamsızsa "durağan" | K2.3 |
| `kesinti_analizi`'ni araç olarak açmak | K2.5 |
| CUSUM'u toplanmış seride, ARL'ye göre ayarlı eşikle çalıştırmak | K2.1 |
| NNI'da kenar düzeltmesini varsayılan yapmak; yöntem kartına "yerel kümeye duyarsız" | K1.1 |
| BMK v1: K2.4 ölçütünün düzeltilmesi (gerekçeli yeni sürüm) | K2.4 |
