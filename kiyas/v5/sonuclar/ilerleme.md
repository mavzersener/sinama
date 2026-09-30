# BMK v5 — yayılım çarpanının seyri

Aynı ön-kayıtlı kıyas (v5, `430fcd0` 17:13:48, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v5.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.10, sınama v1.1) | A4.12 sınama v1.3 |
|---|---|---|---|---|
| K11.1 aşırı iddia yok | kısmi artefakt (Poisson, 60) | ≥ 0,90 | 1,000 | 1,000 |
| K11.2 aşırı iddia yok | karma (Poisson, 60) | ≥ 0,90 | 0,950 | 0,950 |
| K11.3 DESTEKLENDİ | gerçek artış + küçük kanal (Poisson, 200) | ≥ 0,88 | 0,920 | **0,940** |
| K11.4 aşırı iddia yok | saf artefakt (NB, 60) | ≥ 0,90 | 1,000 | 1,000 |
| K11.5 aşırı iddia yok | kısmi artefakt (NB, 60) | ≥ 0,90 | 1,000 | 1,000 |
| K11.6 aşırı iddia yok | karma (NB, 60) | ≥ 0,90 | 0,950 | **0,933** |
| K11.7 yayılım testi p'si raporu | ölçüt senaryoları | = 1 | 0 | **1** |
| **Geçen** | | | **6/7** | **7/7** |

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

## Denenen ve reddedilen

- **Sınama v1.2 — havuzlanmış Fisher-kapılı φ (REDDEDİLDİ, dal `deneme/v1.2-havuz-phi`,
  `d3ef040`; ayrıntı o daldaki `kiyas/v5/sonuclar/v12_reddedildi.md`).** v5'te 6/7:
  K11.3 0,92 → 0,94, K11.7 0 → 1, ama **K11.6 (NB karma, aşırı iddia yok) 0,95 →
  0,883 KALDI** (öngörü 0,93–0,97 yanlış). v4 7/7 (K10.5 0,90 → 0,933), v3 ve v0–v2
  değişmedi. Ana hatta alınmadı: koruma ölçütü küçük güç kazancından önce gelir.
  Neden (çıkarım): havuzlama baskın bileşenin (sürekli kanal, φ ≈ 6) yayılımını yeni
  kanalınkiyle (φ ≈ 2,5) ortalayıp varyansı küçük tahmin eder; v1.1'in en büyük-φ'si
  kazara ihtiyatlı. Keşifteki "havuz" varyantı fiilen öncesi penceresi φ'sine
  yaslanıyordu — keşif kusurum. **v1.3 adayı:** bileşene özgü, kendi Fisher testiyle
  kapılı φ; yeni ön-kayıtla (v6).

## A4.12 — sınama v1.3

- 6/7 → 7/7 (gerileme bekçisi olarak; iyileşme iddiası v6'da). K11.3 0,92 → 0,94;
  K11.7 0 → 1; K11.6 0,95 → 0,933 (4/60 aşırı iddia, eşik üstünde; v1.2'nin 0,883'ü
  gibi kalmadı).
