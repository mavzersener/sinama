# BMK v7 — ETKİ hükmünün seyri

Aynı ön-kayıtlı kıyas (v7, `2a84f04` 19:54:32, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v7.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (sınama v1.3, ETKİ yok) | A4.13 ETKİ |
|---|---|---|---|---|
| K13.1 DESTEKLENDİ | gerçek etki | ≥ 0,80 | 0 | **0,940** |
| K13.2 aşırı iddia yok | genel düşüş | ≥ 0,90 | 0 | **0,990** |
| K13.3 aşırı iddia yok | ortalamaya dönüş | ≥ 0,90 | 0 | **1,000** |
| K13.4 en güçlü R-ORTALAMAYA-DONUS (tutulanlarda) | ortalamaya dönüş | ≥ 0,80 | 0 | **1,000** |
| K13.5 aşırı iddia yok | yer değiştirme | ≥ 0,90 | 0 | **1,000** |
| K13.6 en güçlü R-YER-DEGISTIRME (tutulanlarda) | yer değiştirme | ≥ 0,80 | 0 | **0,980** |
| K13.7 kontrolsüz tavan | kontrolsüz | = 1 | 0 | **1** |
| K13.8 aşırı iddia yok | etkisiz | ≥ 0,90 | 0 | **0,960** |
| K13.9 aşırı iddia yok | etkisiz NB | ≥ 0,90 | 0 | **0,980** |
| **Geçen** | | | **0/9** | **9/9** |

## Notlar

- **Başlangıç:** araç ETKI soru türünü tanımıyor (şema: `AracSemaHatasi`, 700 çağrı) →
  hüküm YOK. 9/9 öngörü doğrulandı (tanım gereği).
- **A4.13 — ETKİ soru türü (`7d82250`).** 0/9 → 9/9; v0–v6 birebir aynı. Uygulama
  öngörüsüyle (ön-kayıtta zaman damgalı): K13.1 0,94 (0,90–0,96 ✓), K13.2 0,99 (0,93–0,98 —
  üstünde), K13.3–K13.6 aralıkta, K13.7 = 1 ✓, K13.8 0,96 ✓, K13.9 0,98 ✓.
- Gerçek etkide 6/100 BELİRSİZ: rakiplerin I. tip hatası (öncesi zirve 2, tampon artışı 4).
  Etkisizde 4/100 yanlış DESTEKLENDİ (birincil sınamanın doğal yanlış alarmı; eşik içinde).
- Ek: kontrolsüzde ITS gücü 0,74 (tavan nedeniyle en çok KIRILGAN; 26 BELİRSİZ).
- Gözlem: ortalamaya dönüş senaryosunda birincil 24/100 tutuldu — öncesi zirve bölgenin
  aylık yayılımını büyütüp φ'yi artırıyor, bu da birincil sınamayı ihtiyatlı kılıyor
  (yayılım kapısının koruyucu yan etkisi); tutulanların hepsinde en güçlü rakip doğru.
