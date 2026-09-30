# BMK v6 — bileşene özgü yayılımın seyri

Aynı ön-kayıtlı kıyas (v6, `84c4b3e` 18:25:07, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v6.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (sınama v1.1) |
|---|---|---|---|
| K12.1 aşırı iddia yok | karma, iki kanal NB (100) | ≥ 0,90 | 0,960 |
| K12.2 aşırı iddia yok | karma, sürekli NB (100) | ≥ 0,90 | 0,970 |
| K12.3 aşırı iddia yok | karma, yeni NB (100) | ≥ 0,90 | 0,990 |
| K12.4 aşırı iddia yok | kısmi, yeni NB (100) | ≥ 0,90 | 1,000 |
| K12.5 aşırı iddia yok | saf, sürekli NB (100) | ≥ 0,90 | 1,000 |
| K12.6 DESTEKLENDİ | güç, yeni NB (180) | ≥ 0,80 | 0,772 |
| K12.7 DESTEKLENDİ | güç, Poisson (180) | ≥ 0,80 | 0,889 |
| K12.8 iki bileşenin yayılım p'si | hepsi | = 1 | 0 |
| **Geçen** | | | **6/8** |

## Notlar

- **Başlangıç:** 8/8 öngörü doğrulandı (K12.6 öngörü ≈ 0,73, ölçüm 0,772; K12.2 zayıf
  öngörü tuttu, 0,97). v1.1 yeni kanalın büyük φ'sini sürekli kanalın terimlerine de
  uyguladığı için yeni kanal çok yayılımlıyken güç eşiğin altında.
