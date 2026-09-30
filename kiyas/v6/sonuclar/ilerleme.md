# BMK v6 — bileşene özgü yayılımın seyri

Aynı ön-kayıtlı kıyas (v6, `84c4b3e` 18:25:07, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v6.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (sınama v1.1) | A4.12 sınama v1.3 |
|---|---|---|---|---|
| K12.1 aşırı iddia yok | karma, iki kanal NB (100) | ≥ 0,90 | 0,960 | 0,960 |
| K12.2 aşırı iddia yok | karma, sürekli NB (100) | ≥ 0,90 | 0,970 | **1,000** |
| K12.3 aşırı iddia yok | karma, yeni NB (100) | ≥ 0,90 | 0,990 | **0,920** |
| K12.4 aşırı iddia yok | kısmi, yeni NB (100) | ≥ 0,90 | 1,000 | 1,000 |
| K12.5 aşırı iddia yok | saf, sürekli NB (100) | ≥ 0,90 | 1,000 | 1,000 |
| K12.6 DESTEKLENDİ | güç, yeni NB (180) | ≥ 0,80 | 0,772 | **0,856** |
| K12.7 DESTEKLENDİ | güç, Poisson (180) | ≥ 0,80 | 0,889 | **0,900** |
| K12.8 iki bileşenin yayılım p'si | hepsi | = 1 | 0 | **1** |
| **Geçen** | | | **6/8** | **8/8** |

## Notlar

- **Başlangıç:** 8/8 öngörü doğrulandı (K12.6 öngörü ≈ 0,73, ölçüm 0,772; K12.2 zayıf
  öngörü tuttu, 0,97). v1.1 yeni kanalın büyük φ'sini sürekli kanalın terimlerine de
  uyguladığı için yeni kanal çok yayılımlıyken güç eşiğin altında.
- **A4.12 — sınama v1.3 (bileşene özgü, kendi Fisher testiyle kapılı φ).** 6/8 → 8/8.
  Uygulama öngörüsüyle: K12.6 0,856 (0,83–0,88 ✓), K12.7 0,90 (0,87–0,94 ✓), K12.8 1 ✓,
  K12.1 0,96 ✓; K12.2 1,00 (≈ 0,93 — üstünde); **K12.3 0,92 (≈ 0,95 — altında)**.
- **Bedel (olduğu gibi):** yeni kanalı çok yayılımlı karmada aşırı iddia 1/100 → 8/100
  (eşik geçildi). Bir kısmı v1.1'in kazara aşırı ihtiyatlılığının kalkması; ama %8 nominal
  %5'in üstünde — tahmin edilen φ'nin gürültüsü z'yi t-benzeri kalın kuyruklu yapıyor
  olabilir. v1.4 adayı: kritik değer için φ'nin serbestlik derecesiyle t.
