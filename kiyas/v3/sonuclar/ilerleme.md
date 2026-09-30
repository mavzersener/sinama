# BMK v3 — kategorik hükmün seyri

Aynı ön-kayıtlı kıyas (v3, `b65c8a9` 10:44:12, eşikler değişmedi), değişen çekirdek.
Her sütun bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v3.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.8 çekirdeği, araç yok) | A4.9 bilim katmanı v1 | A4.10 sınama v1.1 |
|---|---|---|---|---|---|
| K9.1 suç artışı desteklenmez | artefakt | ≥ 0,90 | 0 | **0,967** | 0,967 |
| K9.2 en güçlü rakip R-BILDIRIM (birincil tutulunca) | artefakt | ≥ 0,90 | 0 | **0,967** | **1,000** |
| K9.3 DESTEKLENDİ | gerçek artış | ≥ 0,80 | 0 | **1,000** | 1,000 |
| K9.4 keşifsel tavan | gerçek artış (keşifsel) | ≥ 0,80 | 0 | **1,000** | 1,000 |
| K9.5 destek (DESTEKLENDİ/KIRILGAN) | odaklı | ≥ 0,80 | 0 | **0,933** | 0,933 |
| K9.6 desteksiz | rastgele | ≥ 0,90 | 0 | **1,000** | 1,000 |
| K9.7 SERİ tavanı | seri | ≥ 0,90 | 0 | **1,000** | 1,000 |
| K9.8 insan onayı | seri | = 1 | 0 | **1** | 1 |
| K9.9 desteksiz | seri yok | ≥ 0,90 | 0 | **1,000** | 1,000 |
| K9.10 H_bilinmeyen | hepsi | = 1 | 0 | **1** | 1 |
| K9.11 sayısal olasılık yok | hepsi | = 1 | 0 | **1** | 1 |
| K9.12 belirlenimcilik | artefakt | = 1 | 0 | **1** | 1 |
| **Geçen** | | | **0/12** | **12/12** | 12/12 |

## Notlar

- **Başlangıç:** `rehberli_calisma` yok; 7 senaryo × 30 tohumun 210 çağrısının hepsi
  `KullanimHatasi` → hüküm YOK. 12/12 öngörü doğrulandı (tanım gereği). v3'ün değeri
  ön-kayıtlı spesifikasyon olmasıdır: çıktı sözleşmesi, doğru hükümler ve eşikler
  bilim katmanı yazılmadan kilitlendi.
- **A4.9 — bilim katmanı v1 (ADR-002).** `sinama/bilim/`: RAK v1 (7 rakip), soru türü
  şablonları (ARTIS, YOGUNLASMA, SERI), deterministik sınamalar, sürümlü hüküm
  kuralları (`hukum-v1`), Rehberli akış `rehberli_calisma`. 0/12 → 12/12; v0/v1/v2
  birebir aynı.
- **Uygulama öngörüsüyle karşılaştırma (ön-kayıtta zaman damgalı):** yönlerin hepsi
  doğru; nicel aralıklar 4 ölçütte gerçeğin ALTINDA kaldı (ihtiyatlı güç tahmini):
  K9.1 ve K9.2 0,967 (öngörü 0,93–0,95), K9.3 1,00 (0,85–0,95), K9.5 0,933 (0,85–0,90).
- **Kalan hatalar ve mekanizmaları (incelendi):**
  - Artefakt tohum 314 → yanlış DESTEKLENDİ: sürekli kanalın (karakol) trend testi
    sahte anlamlı (p = 0,010) → R-BILDIRIM dışlandı. Öngörülen mekanizma. **Tasarım
    zayıflığı:** rakibi tek bir ayırt edici sınamanın ANLAMLILIĞIYLA dışlamak, o
    sınamanın I. tip hatasını doğrudan hükme taşır. v1.1 adayı: sürekli kanaldaki
    artışın toplam artışla orantılı olduğunu (etki büyüklüğü) da istemek.
  - Odaklı tohum 306 ve 324 → BELİRSİZ: Gi* FDR sonrası sıcak hücre bulamadı
    (aracın gücü, v0 K1.5 = 0,90). "Doğrulanmadı ≠ yanlış"; hüküm katmanı güç eklemez.
- **Aynı sınıf denetimi (A4.9):** `hipotez.t_test_tek` / `t_test_bagimsiz` / `anova`
  varyans sıfırken istatistiği fark/1e-9 ile uyduruyordu (sabit farkta t = 1,5·10¹⁰);
  Welch df 0/0 ile çöküyordu → istatistik None, p = 0 (fark varsa, sınır değeri) ya
  da None. `dongu_veri` oturum kapısı araç adıyla çağrılınca 11 araçta mekânsal/zarar
  kuralını atlayıp yanıltıcı "uygun" kaydediyordu → aracın kapı analiz adına çevrilir.
  Rehberli akışın oturum kapısı da aynı hatayla yazılmıştı (koordinatsız veride
  oturum ANALİZ'e geçti) — birim testi yakaladı; kapı artık aracın tek otoritesinden
  (`dispatch_gate`).
- **A4.10 — sınama v1.1.** v3 gerileme bekçisidir; iyileşme v4'te (yeni tohumlar)
  iddia edilir. K9.2 0,967 → 1,00. **Öngörü hatası:** "K9.1 → 1,00" dedim, 0,967'de
  kaldı. Tohum 314 DESTEKLENDİ'den KIRILGAN'a geçti (aşırı iddia kalktı) ama K9.1
  yalnız BELİRSİZ/ÇELİŞKİLİ'yi doğru sayar. Neden: karakol o tohumda tesadüfen +%13
  (453 → 513); ayrıştırmada pay 0,32, z −1,39 (φ = 2,2) → çözülmedi. Poisson
  varsayımıyla z −2,07 → destekleniyor olurdu: φ tahmininin yukarı yanlılığı
  (bkz. v4 ilerleme, keşif).
