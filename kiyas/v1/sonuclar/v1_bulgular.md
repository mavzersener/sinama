# BMK v1 — ilk ölçüm ve bulgular (29.09.2026)

- **Ön-kayıt:** `cc193d6` (14:57:26 +08:00) — 5 vaka, üreteç ve koşucu sonuç
  görülmeden kilitlendi (v0 bağımlılıkları dahil 9 dosya). **Ölçüm:** bu commit.
- **Kapsam:** çekirdek düzeyi; 30 tohum (101–130, v0 tohumlarıyla çakışmaz);
  araçlar resmi yoldan ve varsayılan argümanlarla.
- **Ölçülen çekirdek:** A4.2 sonrası (`025e041`): Gi* FDR'li, seri eşleştirme
  taban oranı + uzay-zaman'lı.

## Ön-kayıtlı sonuç: 9 ölçütün 4'ü geçti; 6/6 öngörü doğrulandı

| Ölçüt | Değer | Eşik | Sonuç | Öngörü |
|---|---|---|---|---|
| K2b.1 kanal sayımı ham sayımla birebir | 1,000 | = 1 | geçti | geçer → doğrulandı (v0 keşfiyle bilgilendirilmiş) |
| K4.1 LISA gücü | 1,000 | ≥ 0,90 | geçti | — |
| K4.2 LISA yanlış alarmı (aile) | 0,800 | ≤ 0,10 | KALDI | başarısız → **doğrulandı** |
| K5.1 yükselen sıcak nokta gücü | 0,700 | ≥ 0,90 | KALDI | — (öngörülmedi) |
| K5.2 yükselen sıcak nokta yanlış alarmı | 0,900 | ≤ 0,10 | KALDI | başarısız → **doğrulandı** |
| K6.1 anomali gücü | 0,967 | ≥ 0,90 | geçti | — |
| K6.2 anomali yanlış alarmı (aile) | 0,400 | ≤ 0,10 | KALDI | başarısız → **doğrulandı** |
| K7.1 yayılmış seri geri çağırma | 0,253 | ≥ 0,80 | KALDI | başarısız → **doğrulandı** |
| K7.2 bağımsızlardan yanlış çift | 0,167 | ≤ 1 | geçti | geçer → **doğrulandı** |

## Bulgular

1. **LISA rastgele desende küme ve aykırı değer "buluyor" (K4.2 = %80).** Tohum başına
   ~2 anlamlı hücre; dört türe de dağılmış (HH 21, LL 13, HL 15, LH 13 / 30 tohum).
   Neden: hücre başına düzeltmesiz p < 0,05 — A4.1 öncesi Gi* ile aynı kusur.
2. **Yükselen sıcak nokta homojen veride sıcak nokta ilan ediyor (K5.2 = %90).** Çoğu
   "kalıcı" (30 tohumda 60 bölge), bir kısmı "yeni sıcak nokta" (9). Neden: "sıcak"
   bölgeler arası GÖRELİ yüzdelik (her dönem tanım gereği ~%10 bölge sıcak) ve
   "kalıcı" kategorisi anlamlılık sınaması içermiyor.
3. **Bölge anomalisi 50 homojen bölgede %40 sahte "anlamlı" (K6.2).** Kod
   incelemesinden hesaplanan ≈ %40 ile birebir. Neden: "anlamli" listesi düzeltmesiz
   p ≤ 0,01; q (FDR) hesaplanıyor ama karar onunla verilmiyor.
4. **Yayılmış seride geri çağırma %25 (K7.1).** A4.2'nin varsayılan 2 km / 60 gün
   süzgecinin bedeli ölçüldü; kesinlik korunuyor (bağımsızlardan yanlış çift 0,17).
   Karar gerektirir: dar süzgeç (yüksek kesinlik) mi, geniş/katmanlı aday (yüksek
   geri çağırma) mı — yalnız ölçümle seçilmeli.

## Keşif (ÖN-KAYIT DIŞI — hipotez üretir, ölçüm değildir)

Betik: `kiyas/kesif/v1_nedenler.py`.

- **K5.1 (güç %70, öngörülmedi):** varsayılan 4 dönemle Mann-Kendall en iyi p = 0,089;
  yalnız kusursuz artan seri anlamlı olur, tek ters çiftte p = 0,31. Artan bölgenin
  serisi 21/30 tohumda kusursuz arttı. Kategoriler: yoğunlaşan 14, yeni 7, kalıcı 5,
  **sıcak değil 4**.
- **Sınıflandırma boşluğu (yeni kusur):** son yarıda sıcak, ilk yarıda değil ve trendi
  anlamsız bölge "sıcak değil" olur (sıcak dönem oranı tam 0,5, `0 < oran < 0,5`
  koşulunu sağlamaz, hiçbir dala girmez). Oranı üç katına çıkan bölge böyle "görünmez"
  oldu. Elle yazılmış girdiyle doğrulandı: `[10, 11, 40, 38]` → "sıcak değil";
  `[10, 11, 38, 40]` → "yeni sıcak nokta".
- **Eşitlik kusuru (yeni):** eşik `>=` ile karşılaştırıldığı için tüm bölgeler eşitken
  HEPSİ "sıcak" sayılır: 10 eşit bölgenin 10'u "kalıcı sıcak nokta".

## Sıradaki işler (A4)

| Değişiklik | Hedef ölçüt |
|---|---|
| LISA'ya Benjamini–Hochberg FDR (Gi* ile aynı yardımcı) | K4.2 |
| Bölge anomalisinde "anlamli" kararını q ile vermek | K6.2 |
| Yükselen sıcak noktada sıcaklığı anlamlılıkla (ör. Gi*/Poisson + FDR) tanımlamak; sınıflandırma boşluğu ve eşitlik kusuru; dönem sayısı–güç uyarısı | K5.1, K5.2 |
| Seri eşleştirmede süzgeç politikası (dar mı katmanlı mı) — önce karar, sonra ölçüm | K7.1 |
