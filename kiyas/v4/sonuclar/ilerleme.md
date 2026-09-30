# BMK v4 — hüküm sağlamlığının seyri

Aynı ön-kayıtlı kıyas (v4, `4f23e69` 11:52:06, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v4.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.9, bilim v1) | A4.10 sınama v1.1 | A4.12 sınama v1.3 |
|---|---|---|---|---|---|
| K10.1 aşırı iddia yok | saf artefakt | ≥ 0,90 | 1,000 | 1,000 | 1,000 |
| K10.2 aşırı iddia yok | kısmi artefakt | ≥ 0,90 | 0,767 | **1,000** | 1,000 |
| K10.3 en güçlü rakip R-BILDIRIM | kısmi artefakt | ≥ 0,90 | 0,767 | **1,000** | 1,000 |
| K10.4 aşırı iddia yok | karma | ≥ 0,90 | 0,000 | **0,967** | 0,967 |
| K10.5 DESTEKLENDİ | gerçek artış + küçük yeni kanal | ≥ 0,80 | 0,967 | **0,900** | **0,933** |
| K10.6 DESTEKLENDİ | gerçek artış | ≥ 0,80 | 1,000 | 1,000 | 1,000 |
| K10.7 etki büyüklüğü raporu | yeni kanallı dört senaryo | = 1 | 0 | **1** | 1 |
| **Geçen** | | | **3/7** | **7/7** | 7/7 |

## Notlar

- **Başlangıç:** 7/7 öngörü yönüyle doğrulandı. Kısmi artefaktta 30 tohumun 7'sinde
  yanlış DESTEKLENDİ (sürekli kanaldaki +4/ay'lık gerçek artış anlamlı çıkınca rakip
  dışlanıyor); karmada 30/30 (öngörü 0,03–0,10 — gerçek değer aralığın altında: +12/ay
  adımda sürekli kanal trend testinin gücü tahminimden yüksek). Saf artefaktta 4
  tohumda birincil tutulmadı (R-BILDIRIM uygulanamaz), 26'sında destekleniyor.
- **A4.10 — sınama v1.1 (R-BILDIRIM = artış ayrıştırması, etki büyüklüğü).** 3/7 → 7/7.
  Uygulama öngörüsüyle (ön-kayıtta zaman damgalı): hepsi aralıkta; K10.5 0,90 alt uçta.
  Kısmi artefaktta 21 destekleniyor + 9 çözülmedi (DESTEKLENDİ yok); karmada 29/30
  KIRILGAN; küçük yeni kanalda 27 DESTEKLENDİ + 3 KIRILGAN.
- **Bedel:** K10.5 0,967 → 0,90 (güç).
- **Ön-kayıttan sapma:** ön-kayıttaki tasarım tanımı saf Poisson'du; uygulamada
  quasi-Poisson yayılım çarpanı φ eklendi (pencere/grup var/ortalama oranlarının en
  büyüğü, en az 1). Sonuçlar bu sapmalı uygulamanındır.
- **Keşif (ÖN-KAYIT DIŞI, `kiyas/kesif/a410_yayilim.py`, tohum 901–960):** φ
  varyantları (Poisson φ = 1 / en büyük / havuzlanmış Pearson χ²/sd) Poisson ve aşırı
  yayılımlı (negatif binom, gama k = 8 → φ ≈ 6) veride:
  - NB karmada aşırı iddia (DESTEKLENDİ): Poisson 13/60, φ'li iki tahminci 3/60 — **φ
    gerekli**; ama BMK v4 yalnız Poisson veri içerdiği için bu kazancı ÖLÇEMİYOR
    (v4'ün tasarım boşluğu).
  - Poisson küçük kanalda DESTEKLENDİ: Poisson 55/60, φ'li iki tahminci 50/60 —
    "havuzlanmış tahminci gücü geri getirir" hipotezim ÇÜRÜDÜ (iki tahminci aynı).
    Çıkarım (ayrıca ölçülmedi): bedel, gürültülü φ̂'nin 1 tabanıyla kullanılmasından
    — Poisson veride φ̂ > 1 çıkan tohumlarda varyans şişer, < 1'ler tabana takılır;
    ortalama etki yukarı.
  - v1.2 adayı (ilke A4.6'daki bölge anomalisiyle aynı): φ'yi yalnız yayılım
    sınaması Poisson'u reddederse kullanmak; aşırı yayılımlı senaryolar içeren yeni
    ön-kayıtla (v5) ölçülmeli.
- **A4.12 — sınama v1.3:** 7/7; K10.5 0,90 → 0,933 (kısmi artefaktta 23 BELİRSİZ + 7
  KIRILGAN, karmada 1 DESTEKLENDİ — v1.1 ile aynı sayılar).
