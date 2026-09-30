# BMK v5 — yayılım çarpanının seyri

Aynı ön-kayıtlı kıyas (v5, `430fcd0` 17:13:48, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v5.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.10, sınama v1.1) |
|---|---|---|---|
| K11.1 aşırı iddia yok | kısmi artefakt (Poisson, 60) | ≥ 0,90 | 1,000 |
| K11.2 aşırı iddia yok | karma (Poisson, 60) | ≥ 0,90 | 0,950 |
| K11.3 DESTEKLENDİ | gerçek artış + küçük kanal (Poisson, 200) | ≥ 0,88 | 0,920 |
| K11.4 aşırı iddia yok | saf artefakt (NB, 60) | ≥ 0,90 | 1,000 |
| K11.5 aşırı iddia yok | kısmi artefakt (NB, 60) | ≥ 0,90 | 1,000 |
| K11.6 aşırı iddia yok | karma (NB, 60) | ≥ 0,90 | 0,950 |
| K11.7 yayılım testi p'si raporu | ölçüt senaryoları | = 1 | 0 |
| **Geçen** | | | **6/7** |

Ek (ölçüt değil): NB güç senaryosunda DESTEKLENDİ 0,217 (13/60).

## Notlar

- **Başlangıç:** 7 öngörünün 6'sı doğrulandı. **Öngörü hatası: K11.3** — "başarısız,
  ≈ 0,83–0,90" dedim; v1.1 200 tohumda 0,92 (184/200). v1.1'in Poisson verideki güç
  kaybı keşfin (901–960: 50/60) gösterdiğinden küçük: üç ölçümün toplamı (keşif 50/60,
  v4 27/30, v5 184/200) 261/290 = 0,90; φ = 1'in keşif gücü 55/60. 60 tohumluk
  keşifteki 5 tohumluk fark gürültü içindeydi. Sonuç: v1.2'nin "gücü geri getirir"
  gerekçesi zayıfladı; v1.2 A4.6 ile tutarlılık ve kanıtsız φ̂ kullanmama ilkesiyle
  ölçülür, kazancı olduğu gibi raporlanır.
- NB karmada 3/60 aşırı iddia (öngörü ≈ 0,95 — doğru); NB güç 13/60 (öngörü ≈ 0,3,
  üç varyantta da düşük — aşırı yayılımda veri az bilgi taşır).
- CI: BMK işi sürüm başına paralel matrise bölündü (v0–v4 tek işte 8 dk sürüyordu;
  v5 ~10 dk ekliyor, 15 dk sınırı aşılırdı).
