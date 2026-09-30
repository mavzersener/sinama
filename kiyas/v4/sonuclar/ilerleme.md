# BMK v4 — hüküm sağlamlığının seyri

Aynı ön-kayıtlı kıyas (v4, `4f23e69` 11:52:06, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v4.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.9, bilim v1) |
|---|---|---|---|
| K10.1 aşırı iddia yok | saf artefakt | ≥ 0,90 | 1,000 |
| K10.2 aşırı iddia yok | kısmi artefakt | ≥ 0,90 | 0,767 |
| K10.3 en güçlü rakip R-BILDIRIM | kısmi artefakt | ≥ 0,90 | 0,767 |
| K10.4 aşırı iddia yok | karma | ≥ 0,90 | 0,000 |
| K10.5 DESTEKLENDİ | gerçek artış + küçük yeni kanal | ≥ 0,80 | 0,967 |
| K10.6 DESTEKLENDİ | gerçek artış | ≥ 0,80 | 1,000 |
| K10.7 etki büyüklüğü raporu | yeni kanallı dört senaryo | = 1 | 0 |
| **Geçen** | | | **3/7** |

## Notlar

- **Başlangıç:** 7/7 öngörü yönüyle doğrulandı. Kısmi artefaktta 30 tohumun 7'sinde
  yanlış DESTEKLENDİ (sürekli kanaldaki +4/ay'lık gerçek artış anlamlı çıkınca rakip
  dışlanıyor); karmada 30/30 (öngörü 0,03–0,10 — gerçek değer aralığın altında: +12/ay
  adımda sürekli kanal trend testinin gücü tahminimden yüksek). Saf artefaktta 4
  tohumda birincil tutulmadı (R-BILDIRIM uygulanamaz), 26'sında destekleniyor.
