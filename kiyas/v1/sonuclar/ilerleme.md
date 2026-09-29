# BMK v1 — bilimsel gücün seyri

Aynı ön-kayıtlı kıyas (v1, eşikler değişmedi), değişen çekirdek. Her sütun bir
çekirdek değişikliğinden sonraki tam ölçümdür; sayılar o commit'teki `v1.json`'dadır.
Kalın: önceki sütuna göre değişen.

| Ölçüt | Eşik | İlk ölçüm `169e7e4` | A4.5 LISA + anomali FDR |
|---|---|---|---|
| K2b.1 kanal sayımı birebir | = 1 | 1,000 | 1,000 |
| K4.1 LISA gücü | ≥ 0,90 | 1,000 | **0,467** |
| K4.2 LISA yanlış alarmı | ≤ 0,10 | 0,800 | **0,033** |
| K5.1 yükselen sıcak nokta gücü | ≥ 0,90 | 0,700 | 0,700 |
| K5.2 yükselen sıcak nokta yanlış alarmı | ≤ 0,10 | 0,900 | 0,900 |
| K6.1 anomali gücü | ≥ 0,90 | 0,967 | 0,967 |
| K6.2 anomali yanlış alarmı | ≤ 0,10 | 0,400 | **0,067** |
| K7.1 yayılmış seri geri çağırma | ≥ 0,80 | 0,253 | 0,253 |
| K7.2 bağımsızlardan yanlış çift | ≤ 1 | 0,167 | 0,167 |
| **Geçen** | | **4/9** | **5/9** |

## Notlar

- **A4.5 — bölge anomalisi:** "anlamli" kararı düzeltmesiz p ≤ 0,01 yerine q ≤ 0,05
  (FDR). Yanlış alarm %40 → %7, güç %97'de kaldı. Öngörüler (ölçümden önce) doğru.
- **A4.5 — LISA:** karar Benjamini–Hochberg FDR ile. Sahte küme %80 → %3. **Bedel:
  güç %100 → %47** — öngörüm ("≥ 0,90'da kalır") YANLIŞ çıktı. Ön-kayıt dışı keşif
  (`kiyas/kesif/a45_lisa_guc.py`) iki hipotezi sınadı ve ikisini de çürüttü:
  odak boyutu (σ 0,15/0,40/0,60 km → güç 0,47/0,83/0,43) ve permütasyon çözünürlüğü
  (9.999 permütasyonda odak p medyanı 0,0026, güç 0,33 — 999'daki 0,001'ler gürültü).
  Sonuç: LISA istatistiği bu desende gerçekten zayıf; 36 hücrede hata kontrolü altında
  kompakt sıcak noktayı güvenilir kanıtlayamaz. Gi* aynı veride FDR'li %90 güç korur
  (v0 K1.5) — sıcak nokta tespiti için tasarlanmış yöntemdir; LISA komşu benzerliği ve
  aykırı değer içindir.
  **Karar (ilkelerden):** FDR korunur — düzeltmesiz LISA'nın %80 sahte kümesi, kolluk
  bağlamında kaçırılan kümeden daha ağırdır ve kaçırılan kümeyi Gi* hattı yakalar.
  K4.1 başarısızlığı yöntemin dürüst sınırı olarak kalır; eşik gevşetilmedi. Araç
  uyarısı: sıcak nokta sorusu için `sicak_nokta_gi`; düzeltmesiz sayı kanıt değil.
