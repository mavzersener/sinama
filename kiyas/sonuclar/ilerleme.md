# BMK v0 — bilimsel gücün seyri

Aynı ön-kayıtlı kıyas (v0, eşikler değişmedi), değişen çekirdek. Her sütun bir
çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v0.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Eşik | İlk ölçüm `ef1b5a6` | A4.1 Gi* FDR |
|---|---|---|---|
| K1.1 NNI gücü | ≥ 0,90 | 0,233 | 0,233 |
| K1.2 NNI yanlış alarmı | ≤ 0,10 | 0,000 | 0,000 |
| K1.3 Moran gücü | ≥ 0,90 | 0,967 | 0,967 |
| K1.4 Moran yanlış alarmı | ≤ 0,10 | 0,000 | 0,000 |
| K1.5 Gi* gücü | ≥ 0,90 | 1,000 | **0,900** |
| K1.6 Gi* yanlış alarmı | ≤ 0,10 | 0,700 | **0,000** |
| K2.1 CUSUM kırılma zamanı | ≥ 0,90 | 0,467 | 0,467 |
| K2.2 kayıtlı artış | ≥ 0,90 | 1,000 | 1,000 |
| K2.3 sahte trend | ≤ 0,10 | 1,000 | 1,000 |
| K2.4 kanal ayrıştırma (ölçüt hatalı) | ≥ 0,90 | 0,800 | 0,800 |
| K2.5 ITS aracı | = 1 | 0 | 0 |
| K3.1 seri geri çağırma | ≥ 0,90 | 1,000 | 1,000 |
| K3.2 seri kesinliği | ≥ 0,90 | 0,050 | 0,050 |
| K3.3 "benzerlik ≠ kimlik" uyarısı | = 1 | 0 | 0 |
| K3.4 insan onayı | = 1 | 0 | 0 |
| **Geçen** | | **6/15** | **7/15** |

## Notlar

- **A4.1 (Gi* FDR):** karar düzeltmesiz %90 bandı yerine Benjamini–Hochberg
  (q ≤ 0,05) ile verilir. Rastgele desenlerde sahte sıcak nokta %70 → %0.
  **Bedel:** güç %100 → %90 (tam eşikte; 30 tohumun 3'ünde gerçek odak işaretlenmedi).
  Bu, çoklu test düzeltmesinin bilinen ödünleşimidir. q eşiği sonuca bakılarak
  gevşetilmedi (0,05 standart değer); güç kaybı ileride daha güçlü bir yöntemle
  (ör. komşuluk bağımlılığını hesaba katan düzeltme) ele alınabilir — yeni ölçümle.
