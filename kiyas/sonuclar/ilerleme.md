# BMK v0 — bilimsel gücün seyri

Aynı ön-kayıtlı kıyas (v0, eşikler değişmedi), değişen çekirdek. Her sütun bir
çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v0.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Eşik | İlk ölçüm `ef1b5a6` | A4.1 Gi* FDR | A4.2 seri adayı | A4.7 trend + ITS |
|---|---|---|---|---|---|
| K1.1 NNI gücü | ≥ 0,90 | 0,233 | 0,233 | 0,233 | 0,233 |
| K1.2 NNI yanlış alarmı | ≤ 0,10 | 0,000 | 0,000 | 0,000 | 0,000 |
| K1.3 Moran gücü | ≥ 0,90 | 0,967 | 0,967 | 0,967 | 0,967 |
| K1.4 Moran yanlış alarmı | ≤ 0,10 | 0,000 | 0,000 | 0,000 | 0,000 |
| K1.5 Gi* gücü | ≥ 0,90 | 1,000 | **0,900** | 0,900 | 0,900 |
| K1.6 Gi* yanlış alarmı | ≤ 0,10 | 0,700 | **0,000** | 0,000 | 0,000 |
| K2.1 CUSUM kırılma zamanı | ≥ 0,90 | 0,467 | 0,467 | 0,467 | 0,467 |
| K2.2 kayıtlı artış | ≥ 0,90 | 1,000 | 1,000 | 1,000 | **0,967** |
| K2.3 sahte trend | ≤ 0,10 | 1,000 | 1,000 | 1,000 | **0,067** |
| K2.4 kanal ayrıştırma (ölçüt hatalı) | ≥ 0,90 | 0,800 | 0,800 | 0,800 | 0,800 |
| K2.5 ITS aracı | = 1 | 0 | 0 | 0 | **1** |
| K3.1 seri geri çağırma | ≥ 0,90 | 1,000 | 1,000 | 1,000 | 1,000 |
| K3.2 seri kesinliği | ≥ 0,90 | 0,050 | 0,050 | **0,970** | 0,970 |
| K3.3 "benzerlik ≠ kimlik" uyarısı | = 1 | 0 | 0 | **1** | 1 |
| K3.4 insan onayı | = 1 | 0 | 0 | **1** | 1 |
| **Geçen** | | **6/15** | **7/15** | **10/15** | **12/15** |

## Notlar

- **A4.1 (Gi* FDR):** karar düzeltmesiz %90 bandı yerine Benjamini–Hochberg
  (q ≤ 0,05) ile verilir. Rastgele desenlerde sahte sıcak nokta %70 → %0.
  **Bedel:** güç %100 → %90 (tam eşikte; 30 tohumun 3'ünde gerçek odak işaretlenmedi).
  Bu, çoklu test düzeltmesinin bilinen ödünleşimidir. q eşiği sonuca bakılarak
  gevşetilmedi (0,05 standart değer); güç kaybı ileride daha güçlü bir yöntemle
  (ör. komşuluk bağımlılığını hesaba katan düzeltme) ele alınabilir — yeni ölçümle.
- **A4.2 (seri adayı):** MO benzerliği taban oranıyla ağırlıklı (IDF-Jaccard) +
  uzay-zaman yakınlığı (varsayılan 2 km / 60 gün); her çift "seri adayı" ve
  `ayni_fail_cikarimi: false`; uyarı + insan onayı. Kesinlik %5 → %97, geri çağırma
  %100'de kaldı; tohum başına işaretlenen çift 201,6 → 10,3, bağımsız faillerden
  yanlış çift 190 → 0,33. Ölçümden önce yazılan dört öngörünün dördü doğru çıktı.
  **Dikkat (genelleme):** V3 tek bir senaryodur; seri kayıtları 250 m ve 21 gün
  içinde. Daha geniş alana yayılan seriler varsayılan 2 km / 60 gün süzgecine
  takılır — bunu ölçmek için BMK v1'e yayılan seri varyantı eklenmeli.
  Aynı sınıftan `bulanik_eslesme` ve `ag_analizi`'ye de insan onayı + uyarı
  eklendi; bunlar BMK'da **ölçülmüyor** (ilke gereği, ölçüm değil).
- **A4.7 (trend anlamlılığı + ITS aracı):** `dogrusal_trend` yönü yalnız eğim
  t-testi anlamlıysa (p < 0,05) söyler; `kesinti_analizi` önce/sonra ortalamasından
  segmentli regresyona (seviye ve eğim değişimi, t tabanlı %95 GA, Durbin–Watson,
  nedensellik notu) yükseltildi ve ancak ondan sonra araç olarak açıldı.
  Oranı sabit kanalda sahte trend %100 → %6,7 (2/30; nominal %5 ile tutarlı);
  ITS aracı açık. **Öngörü hatası:** "K2.2 1,00 kalır" dedim, ölçüm 0,967.
  Neden (keşif, `kiyas/kesif/a47_trend.py`): t-testi kalibre (tohumlar arası eğim
  sd 0,000215 ≈ model se 0,000217); analitik güç ≈ %97,9 → 30 tohumda beklenen
  ~0,6 kaçırma, gözlenen 1 (tohum 23, p = 0,15; aynı tohumda aylık ITS de sınırda:
  seviye +9,7, GA [−0,5; 20,0]). Yani kusur değil, gücü hesaplamadan öngörü yazmak.
  Ders: bir anlamlılık sınaması eklerken öngörüden önce güç hesaplanır.
  **Aynı sınıf denetimi (0/0'dan çıkarım):** `coklu_ols` tam uyumda (artıklar ≈ 0)
  t = beta/1e-9 ile t ve p uyduruyordu (y = 2x → t = 2·10⁹; ITS'te gürültüden
  p = 0,057); sabit y'de R² = 1,0 veriyordu. `lojistik` tam ayrışmada yakınsamadan
  Wald p = 0,94 ("etki yok") raporluyordu. Üçünde de çıkarım artık tanımsız (None +
  not) ya da hata; MCP demosunun `coklu_regresyon` ve `lojistik_regresyon` örnekleri
  tam da bu durumlardı. BMK'da ölçülmüyor (birim testleri + mutasyonla sınandı).
