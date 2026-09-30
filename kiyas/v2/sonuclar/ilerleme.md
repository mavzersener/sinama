# BMK v2 — bilimsel gücün seyri

Aynı ön-kayıtlı kıyas (v2, eşikler değişmedi), değişen çekirdek. Her sütun bir
çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v2.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Varyant | Eşik | İlk ölçüm (A4.7 çekirdeği) | A4.8 kanıt hatları + katman |
|---|---|---|---|---|
| K8.1 geri çağırma (C) | sıkı | ≥ 0,90 | 1,000 | 1,000 |
| K8.2 güçlü kesinlik (G) | sıkı | ≥ 0,90 | 0,980 | **0,974** |
| K8.3 aday listesi kesinliği (C) | sıkı | ≥ 0,50 | 0,980 | **0,968** |
| K8.4 geri çağırma (C) | yayılmış | ≥ 0,80 | 0,203 | **1,000** |
| K8.5 aday listesi kesinliği (C) | yayılmış | ≥ 0,50 | 0,910 | **0,990** |
| K8.6 bağımsızlardan güçlü yanlış çift | yayılmış | ≤ 1 | 0,167 | **0,000** |
| K8.7 geri çağırma (C) | tutarsız | ≥ 0,80 | 0,030 | **0,830** |
| K8.8 aday listesi kesinliği (C) | tutarsız | ≥ 0,50 | 0,563 | **0,973** |
| K8.9 güçlü aday çıkan tohum | seri yok | ≤ 0,10 | 0,200 | **0,000** |
| K8.10 çıktı sözleşmesi | hepsi | ≥ 1 | 0 | **1** |
| **Geçen** | | | **6/10** | **10/10** |

## Notlar

- **A4.8 — kanıt hatları + katman.** MO kanıtı artık bir anlamlılık testi: paylaşılan
  bilgi I = Σ idf (nats); p = rastgele bir kaydın bu kadar ayırt edici bilgi paylaşma
  olasılığı (terimler bağımsız, hangi alt kümenin paylaşıldığı çokluğu dahil; iki yönün
  büyüğü). Benjamini–Hochberg iki ailede: uzay-zaman penceresindeki çiftler (pencere
  MO'dan bağımsız seçildiği için geçerli bağımsız süzgeçleme) ve tüm çiftler. Katman:
  güçlü = MO anlamlı + pencere içi; zayıf = MO tüm çiftlerde bile anlamlı ama pencere
  dışı ya da konum/tarih yok. Ružička eşiği kalktı (isteğe bağlı ek süzgeç).
- **Öngörüler (ölçümden önce, sohbette ve commit'te):** v2 10/10, K8.7 ≈ 0,82–0,84
  (zayıf öngörü), v1 8/9, v0 12/15 ve K3.2 ≈ 0,96–0,98 — hepsi doğrulandı. Tasarım
  keşfi yalnız 901–930 tohumlarıyla yapıldı (`kiyas/kesif/a48_seri_tasarim.py`).
- **Kazanç:** yayılmış seri %20 → %100, tutarsız seri %3 → %83, seri yokken güçlü aday
  çıkan tohum %20 → %0, çıktı sözleşmesi 0 → 1.
- **Bedel ve sınırlar (olduğu gibi):**
  - Sıkı varyantta güçlü katman kesinliği 0,980 → 0,974. BH uyarlanabilir: gerçek seri
    çiftleri pencere ailesinde üst sıraları doldurunca, pencere içine düşen özdeş-yaygın
    bir ortak MO çifti (p ≈ 0,004) de eşiği geçebiliyor (tohum başına 0,17; seri
    yokken 0). FDR hatanın ORANINI denetler, sıfırlamaz.
  - Tutarsız seride yalnız 2 ayırt edici davranış paylaşan çiftler (%18) bağlanamıyor:
    60 kayıtta iki orta nadirlikte davranış, 1.770 çiftlik aramada tesadüften
    ayrılamaz (keşif: K = 2 çiftlerin 50'sinden 1'i). Grup düzeyinde seri yine
    bağlanır: keşifte (901–930, ön-kayıt dışı) üç seri varyantının 30 tohumunun
    hepsinde 5 üye bulunan çiftlerle tek bileşende; çift düzeyinde eksik kalır.
  - Terimler bağımsız sayılır: hep birlikte geçen yaygın kalıp ifadeler olduğundan
    ayırt edici görünür (V8'de 3 kelimelik kalıp eşiği geçmiyor; daha uzun kalıplar
    ölçülmedi). Araç uyarısında beyan edildi.
