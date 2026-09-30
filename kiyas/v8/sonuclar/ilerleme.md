# BMK v8 — NNI ve CUSUM'un seyri

Aynı ön-kayıtlı kıyas (v8, `59586b0`, eşikler değişmedi), değişen çekirdek. Her sütun
bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v8.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.14) |
|---|---|---|---|
| K14.1 yön iddiası yok | CSR n=200 | ≤ 0,10 | 0,26 |
| K14.2 yan \|ort. NNI − 1\| | CSR n=200 | ≤ 0,03 | 0,0452 |
| K14.3 yön iddiası yok | CSR n=50 | ≤ 0,10 | 0,34 |
| K14.4 kümelenme gücü | güçlü yaygın küme | ≥ 0,90 | 1,00 |
| K14.5 kümelenme gücü | orta yaygın küme n=50 | ≥ 0,80 | 0,74 |
| K14.6 "küresel ölçü" uyarısı | yerel odak | = 1 | 0 |
| K15.1 seri boyunca yanlış alarm | sabit | ≤ 0,10 | 0,89 |
| K15.2 seri boyunca yanlış alarm | sabit NB | ≤ 0,10 | 1,00 |
| K15.3 seri boyunca yanlış alarm | seyrek | ≤ 0,10 | 0,96 |
| K15.4 ilk alarm [−15, +180] | %30 artış | ≥ 0,80 | 0,59 |
| K15.5 ilk alarm [−15, +90] | %50 artış | ≥ 0,80 | 0,67 |
| K15.6 önce alarm yok | %30 artış NB | ≥ 0,90 | 0,43 |
| **Geçen** | | | **1/12** |

## Notlar

- **Başlangıç:** V14 1/6, V15 0/6; 12/12 öngörü doğrulandı. Rastgele desende NNI'nın
  yanlış iddiaları hep "düzgün dağılım" yönünde (n=200 %26, n=50 %34): kenar
  düzeltmesiz beklenen uzaklık ve küçülmüş sınır kutusu NNI'yı 1'in üstüne iter
  (ortalama 1,045; n=50'de 1,124). Aynı yan orta kümelenmeyi maskeliyor (K14.5 0,74).
- CUSUM değişimsiz seride %89 (NB %100, seyrek %96) en az bir alarm veriyor; ilk
  alarmların medyanı kesintiden 6–9 ay ÖNCE. %30 artışta 18/100 tohumda ilk alarm
  kesintiden önce. v0 K2.1'in 0,467'si bu gürültünün şanslı kısmıdır.
