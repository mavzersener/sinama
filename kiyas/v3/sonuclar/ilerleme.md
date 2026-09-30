# BMK v3 — kategorik hükmün seyri

Aynı ön-kayıtlı kıyas (v3, `b65c8a9` 10:44:12, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v3.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.8 çekirdeği, araç yok) |
|---|---|---|---|
| K9.1 suç artışı desteklenmez | artefakt | ≥ 0,90 | 0 |
| K9.2 en güçlü rakip R-BILDIRIM (birincil tutulunca) | artefakt | ≥ 0,90 | 0 |
| K9.3 DESTEKLENDİ | gerçek artış | ≥ 0,80 | 0 |
| K9.4 keşifsel tavan | gerçek artış (keşifsel) | ≥ 0,80 | 0 |
| K9.5 destek (DESTEKLENDİ/KIRILGAN) | odaklı | ≥ 0,80 | 0 |
| K9.6 desteksiz | rastgele | ≥ 0,90 | 0 |
| K9.7 SERİ tavanı | seri | ≥ 0,90 | 0 |
| K9.8 insan onayı | seri | = 1 | 0 |
| K9.9 desteksiz | seri yok | ≥ 0,90 | 0 |
| K9.10 H_bilinmeyen | hepsi | = 1 | 0 |
| K9.11 sayısal olasılık yok | hepsi | = 1 | 0 |
| K9.12 belirlenimcilik | artefakt | = 1 | 0 |
| **Geçen** | | | **0/12** |

## Notlar

- **Başlangıç:** `rehberli_calisma` yok; 7 senaryo × 30 tohumun 210 çağrısının hepsi
  `KullanimHatasi` → hüküm YOK. 12/12 öngörü doğrulandı (tanım gereği). v3'ün değeri
  ön-kayıtlı spesifikasyon olmasıdır: çıktı sözleşmesi, doğru hükümler ve eşikler
  bilim katmanı yazılmadan kilitlendi.
