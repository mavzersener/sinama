# BMK v8 — NNI ve CUSUM'un seyri

Aynı ön-kayıtlı kıyas (v8, `59586b0`, eşikler değişmedi), değişen çekirdek. Her sütun
bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v8.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.14) | A4.15 NNI + CUSUM |
|---|---|---|---|---|
| K14.1 yön iddiası yok | CSR n=200 | ≤ 0,10 | 0,26 | **0,05** |
| K14.2 yan \|ort. NNI − 1\| | CSR n=200 | ≤ 0,03 | 0,0452 | **0,0040** |
| K14.3 yön iddiası yok | CSR n=50 | ≤ 0,10 | 0,34 | **0,03** |
| K14.4 kümelenme gücü | güçlü yaygın küme | ≥ 0,90 | 1,00 | 1,00 |
| K14.5 kümelenme gücü | orta yaygın küme n=50 | ≥ 0,80 | 0,74 | **0,93** |
| K14.6 "küresel ölçü" uyarısı | yerel odak | = 1 | 0 | **1** |
| K15.1 seri boyunca yanlış alarm | sabit | ≤ 0,10 | 0,89 | **0,14** |
| K15.2 seri boyunca yanlış alarm | sabit NB | ≤ 0,10 | 1,00 | **0,07** |
| K15.3 seri boyunca yanlış alarm | seyrek | ≤ 0,10 | 0,96 | **0,08** |
| K15.4 ilk alarm [−15, +180] | %30 artış | ≥ 0,80 | 0,59 | **0,74** |
| K15.5 ilk alarm [−15, +90] | %50 artış | ≥ 0,80 | 0,67 | **0,88** |
| K15.6 önce alarm yok | %30 artış NB | ≥ 0,90 | 0,43 | **0,99** |
| **Geçen** | | | **1/12** | **10/12** |

## Notlar

- **Başlangıç:** V14 1/6, V15 0/6; 12/12 öngörü doğrulandı. Rastgele desende NNI'nın
  yanlış iddiaları hep "düzgün dağılım" yönünde (n=200 %26, n=50 %34): kenar
  düzeltmesiz beklenen uzaklık ve küçülmüş sınır kutusu NNI'yı 1'in üstüne iter
  (ortalama 1,045; n=50'de 1,124). Aynı yan orta kümelenmeyi maskeliyor (K14.5 0,74).
- CUSUM değişimsiz seride %89 (NB %100, seyrek %96) en az bir alarm veriyor; ilk
  alarmların medyanı kesintiden 6–9 ay ÖNCE. %30 artışta 18/100 tohumda ilk alarm
  kesintiden önce. v0 K2.1'in 0,467'si bu gürültünün şanslı kısmıdır.
- **A4.15 — NNI dürüst varsayılan + kalibre CUSUM.** 1/12 → 10/12 (V14 6/6, V15 4/6).
  NNI: Donnelly kenar düzeltmesi varsayılan, alan/çevre verilmezse sınır kutusu
  (n+1)/(n−1) ile yansız genişletilir, "küresel ölçü — yerel soru için sicak_nokta_gi"
  uyarısı. Rastgele desende yön iddiası %26 → %5 (n=50: %34 → %3), ortalama NNI
  1,045 → 1,004; orta kümelenmede güç 0,74 → 0,93; güçlü kümelenme 1,00 korundu.
  CUSUM: kendinden başlayan (her dönem önceki dönemlerle standartlaştırılır, t → normal),
  eşik seri düzeyinde Monte Carlo ile kalibre (bağımsız normal adımlarda %5), dönem
  otomatik (aylık ardışık-fark yayılım testi anlamlıysa ay, değilse hafta). Değişimsiz
  seride alarm %89 → %14, NB %100 → %7, seyrek %96 → %8; NB'de önce alarm %57 → %1.
- **Öngörü denetimi (uygulama öngörüsü vaka dosyalarında, `59586b0`):** 12 aralığın 10'u
  tuttu. **YANLIŞ:** K15.1 0,14 (öngörü 0,00–0,07) — ölçüt KALDI. Tasarım tohumlarında
  (900–999) 0,03 görmüştüm; 400 yeni tasarım tohumunda (1000–1399, ölçüm sonrası teşhis)
  oran %8,3 (günlük sabit oranlı üreteçte %9,2): gerçek yanlış alarm nominal %5'in
  üstünde, 100 tohumluk keşif şanslıydı, ölçüm tohumları ters yönde. Neden ay uzunluğu ya
  da dönem kapısı DEĞİL (ikisi de dışlandı); aday: haftalık Poisson sayımların sağa
  çarpıklığı (λ ≈ 9/hafta) — t → normal dönüşümü normalliği varsayıyor. K15.4 0,74
  (öngörü 0,68–0,85, sınırda KALABİLİR) — KALDI; %30 artış 24 aylık seride bu yanlış alarm
  düzeyinde bilgi sınırına yakın.
- **Karar:** ana hatta alınır — hiçbir koruma ölçütü düşmedi (K14.4, v0 K1.2 korundu),
  her ölçüt iyileşti; K15.1'in açığı ölçülmüş olarak belgelenir ve araç uyarısı ölçülen
  oranı söyler (%5 iddiası kaldırıldı). v9 adayı: çarpıklığı gideren dönüşüm (Anscombe)
  ya da Poisson parametrik önyükleme ile eşik — yeni tohumlarla ön-kayıt.
- v0: K1.1 0,233 → **0,567** (öngörü 0,40–0,60 ✓; yine KALDI — NNI küresel ölçü), K1.2 0
  (korundu), K2.1 0,467 → **0,400** (öngörü 0,35–0,60 ✓; yine KALDI). v1–v7 birebir aynı.
