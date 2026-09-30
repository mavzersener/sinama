# BMK v9 — CUSUM kalibrasyonunun seyri

Aynı ön-kayıtlı kıyas (v9, `5bb9a45`, eşikler değişmedi), değişen çekirdek. Her sütun
bir çekirdek değişikliğinden sonra yapılan tam ölçümdür; sayılar o commit'teki
`v9.json`'dadır. Kalın: önceki sütuna göre değişen.

| Ölçüt | Senaryo | Eşik | Başlangıç (A4.15) |
|---|---|---|---|
| K16.1 seri boyunca yanlış alarm | sabit | ≤ 0,10 | 0,090 |
| K16.2 seri boyunca yanlış alarm | sabit NB | ≤ 0,10 | 0,065 |
| K16.3 seri boyunca yanlış alarm | seyrek | ≤ 0,10 | 0,075 |
| K16.4 ilk alarm [−15, +180] | %30 artış | ≥ 0,80 | 0,735 |
| K16.5 ilk alarm [−15, +90] | %50 artış | ≥ 0,80 | 0,890 |
| K16.6 önce alarm yok | %30 artış NB | ≥ 0,90 | 0,980 |
| K16.7 havuzlanmış yanlış alarm (600 seri) | üç değişimsiz | ≤ 0,07 | 0,0767 |
| **Geçen** | | | **5/7** |

## Notlar

- **Başlangıç:** 5/7; 7 öngörünün 6'sı doğrulandı. YANLIŞ: K16.3 (seyrek) "sınırda
  KALIR" dedim, 0,075 ile geçti (tasarımda 0,105). Havuzlanmış yanlış alarm %7,7 —
  teşhisteki ~%8 ile tutarlı; nominal %5'in üstünde, K16.7 KALDI.
