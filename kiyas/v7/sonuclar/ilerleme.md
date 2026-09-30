# BMK v7 — ETKİ hükmünün seyri

Aynı ön-kayıtlı kıyas (v7, `2a84f04` 19:54:32, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v7.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (sınama v1.3, ETKİ yok) |
|---|---|---|---|
| K13.1 DESTEKLENDİ | gerçek etki | ≥ 0,80 | 0 |
| K13.2 aşırı iddia yok | genel düşüş | ≥ 0,90 | 0 |
| K13.3 aşırı iddia yok | ortalamaya dönüş | ≥ 0,90 | 0 |
| K13.4 en güçlü R-ORTALAMAYA-DONUS (tutulanlarda) | ortalamaya dönüş | ≥ 0,80 | 0 |
| K13.5 aşırı iddia yok | yer değiştirme | ≥ 0,90 | 0 |
| K13.6 en güçlü R-YER-DEGISTIRME (tutulanlarda) | yer değiştirme | ≥ 0,80 | 0 |
| K13.7 kontrolsüz tavan | kontrolsüz | = 1 | 0 |
| K13.8 aşırı iddia yok | etkisiz | ≥ 0,90 | 0 |
| K13.9 aşırı iddia yok | etkisiz NB | ≥ 0,90 | 0 |
| **Geçen** | | | **0/9** |

## Notlar

- **Başlangıç:** araç ETKI soru türünü tanımıyor (şema: `AracSemaHatasi`, 700 çağrı) →
  hüküm YOK. 9/9 öngörü doğrulandı (tanım gereği).
