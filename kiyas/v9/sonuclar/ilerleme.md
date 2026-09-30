# BMK v9 — CUSUM kalibrasyonunun seyri

Aynı ön-kayıtlı kıyas (v9, `5bb9a45`, eşikler değişmedi), değişen çekirdek. Her sütun
bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v9.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.15) | A4.16 Anscombe |
|---|---|---|---|---|
| K16.1 seri boyunca yanlış alarm | sabit | ≤ 0,10 | 0,090 | **0,025** |
| K16.2 seri boyunca yanlış alarm | sabit NB | ≤ 0,10 | 0,065 | **0,030** |
| K16.3 seri boyunca yanlış alarm | seyrek | ≤ 0,10 | 0,075 | **0,020** |
| K16.4 ilk alarm [−15, +180] | %30 artış | ≥ 0,80 | 0,735 | **0,685** |
| K16.5 ilk alarm [−15, +90] | %50 artış | ≥ 0,80 | 0,890 | **0,865** |
| K16.6 önce alarm yok | %30 artış NB | ≥ 0,90 | 0,980 | **0,995** |
| K16.7 havuzlanmış yanlış alarm (600 seri) | üç değişimsiz | ≤ 0,07 | 0,0767 | **0,025** |
| **Geçen** | | | **5/7** | **6/7** |

## Notlar

- **Başlangıç:** 5/7; 7 öngörünün 6'sı doğrulandı. YANLIŞ: K16.3 (seyrek) "sınırda
  KALIR" dedim, 0,075 ile geçti (tasarımda 0,105). Havuzlanmış yanlış alarm %7,7 —
  teşhisteki ~%8 ile tutarlı; nominal %5'in üstünde, K16.7 KALDI.
- **A4.16 — Anscombe dönüşümü (`kirilma_cusum`: sayımlar standartlaştırmadan önce
  2√(x + 3/8)).** 5/7 → 6/7. Havuzlanmış yanlış alarm %7,7 → %2,5 (600 seri; hedef %5 —
  biraz ihtiyatlı). Uygulama öngörüsü (vaka dosyasında, `5bb9a45`): 7 aralığın 6'sı tuttu;
  K16.7 0,025 aralığın (0,03–0,06) hemen altında (beklenenden ihtiyatlı). Bedel: %30
  artışta [−15, +180] 0,735 → 0,685 (zaten KALIYORDU; öngörülen 0,66–0,80), %50 artışta
  0,89 → 0,865 (koruma eşiği 0,80 üstünde). NB'de önce alarm 0,02 → 0,005.
- Çekirdek, tasarım adayıyla birebir (tasarım tohumları 1000–1599'da aynı sayılar).
- K16.4 (%30 artış, 24 ay, [−15, +180]) yöntem sınırı olarak kalır: yanlış alarmı %5'te
  tutan her sıralı test bu gürültüde (aylık λ = 40) artışı ancak ~3 ayda yakalar.
