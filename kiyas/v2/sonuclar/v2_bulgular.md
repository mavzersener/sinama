# BMK v2 — ilk ölçüm ve bulgular (30.09.2026)

- **Ön-kayıt:** `53a4d3a` (09:54:18 +08:00) — V8'in dört varyantı, üreteç ve koşucu
  sonuç görülmeden kilitlendi (v0 bağımlılıkları dahil 5 dosya). **Ölçüm:** bu commit.
- **Kapsam:** çekirdek düzeyi; 30 tohum (201–230, v0/v1 tohumlarıyla çakışmaz);
  `seri_eslestirme` resmi yoldan, varsayılan argümanlarla.
- **Ölçülen çekirdek:** A4.7 sonrası (`00c1f57`): seri eşleştirme A4.2 biçiminde —
  IDF ağırlıklı Jaccard (Ružička) ≥ 0,6 + ikili uzay-zaman süzgeci (2 km / 60 gün),
  katman yok.

## Ön-kayıtlı sonuç: 10 ölçütün 6'sı geçti; 10/10 öngörü doğrulandı

| Ölçüt | Varyant | Değer | Eşik | Sonuç | Öngörü |
|---|---|---|---|---|---|
| K8.1 geri çağırma (C) | sıkı | 1,000 | ≥ 0,90 | geçti | geçer → doğrulandı |
| K8.2 güçlü kesinlik (G) | sıkı | 0,980 | ≥ 0,90 | geçti | geçer → doğrulandı |
| K8.3 aday listesi kesinliği (C) | sıkı | 0,980 | ≥ 0,50 | geçti | geçer → doğrulandı |
| K8.4 geri çağırma (C) | yayılmış | 0,203 | ≥ 0,80 | KALDI | başarısız → doğrulandı |
| K8.5 aday listesi kesinliği (C) | yayılmış | 0,910 | ≥ 0,50 | geçti | geçer → doğrulandı |
| K8.6 bağımsızlardan güçlü yanlış çift | yayılmış | 0,167 | ≤ 1 | geçti | geçer → doğrulandı |
| K8.7 geri çağırma (C) | tutarsız | 0,030 | ≥ 0,80 | KALDI | başarısız → doğrulandı (hesap 0,03–0,15) |
| K8.8 aday listesi kesinliği (C) | tutarsız | 0,563 | ≥ 0,50 | geçti | geçer → doğrulandı (ZAYIF; değer hesaplanan 0,6–0,75 aralığının ALTINDA) |
| K8.9 güçlü aday çıkan tohum | seri yok | 0,200 | ≤ 0,10 | KALDI | başarısız → doğrulandı (ZAYIF; hesap 0,16–0,25) |
| K8.10 çıktı sözleşmesi | hepsi | 0,000 | ≥ 1 | KALDI | başarısız → doğrulandı |

## Bulgular

1. **Davranışı tutarsız seri neredeyse görünmez (K8.7 = %3).** Her olayda 8 ayırt edici
   davranışın 5'ini kullanan fail — gerçek serilerde olağan durum — 10 çiftten ortalama
   0,3'ü ile bağlanabiliyor. Neden hesapla öngörülmüştü: iki olay ortalama 3,1 ayırt
   edici davranış paylaşır; oran benzerliği (Ružička) ≈ 0,35–0,53, eşik 0,6. Sıkı
   varyanttaki %100 başarı, V3'ün "fail her olayda davranışlarının hepsini tekrarlar"
   varsayımının ürünüdür. **Bu v0/v1'in göremediği bir genelleme açığıdır.**
2. **Yayılmış seride geri çağırma %20 (K8.4)** — v1 K7.1 (%25) yeni tohumlarda
   tekrarlandı: ikili 2 km / 60 gün süzgeci.
3. **Seri yokken tohumların %20'sinde güçlü aday (K8.9).** Tohum başına 0,23 aday;
   0,13'ü ortak MO grubundan (rastgele kelimesi de aynı → tanımı özdeş, Ružička = 1),
   geri kalanı genel kelimeleri örtüşen kayıtlar. Oran benzerliği özdeş ama yaygın
   tanımlara en yüksek puanı veriyor.
4. **Tutarsız varyantta kesinlik 0,56 (K8.8 geçti ama anlamsız):** tohum başına 0,53
   adayın 0,3'ü doğru. Az ve rastgele isabetle "kesin" liste; K8.7 ile birlikte okunur.
5. **Katman ve kanıt hattı yok (K8.10 = 0).** Her aday aynı ağırlıkla sunuluyor;
   süzgecin dışarıda bıraktığı çiftler beyan edilmiyor.

## Sıradaki iş (A4.8) — tasarım hipotezi ön-kayıtta zaman damgalı

Tasarım keşfi YALNIZ 900+ tohumlarıyla (README kural 6). Hedef: K8.4, K8.7, K8.9,
K8.10'u, K8.1–K8.3, K8.5, K8.6, K8.8'i ve v0/v1'i geriletmeden iyileştirmek.

- MO kanıtı: orana ek olarak paylaşılan içeriğin ayırt ediciliği (paylaşılan bilgi,
  Σ idf). Hipotez: özdeş yaygın tanım ≈ 5,6 nats, 8 ayırt edici davranış ≈ 20 nats.
- Tek başına MO, tutarsız seriyi (2 ortak davranış ≈ 6 nats) ortak MO'dan
  (≈ 5,6 nats) ayıramaz → uzay-zaman ikinci kanıt hattı olarak birleşmeli.
- Uzay-zaman süzgeç değil kanıt hattı: pencere dışı ama MO'su ayırt edici çift
  atılmaz, "zayıf" katmanda gerekçesiyle sunulur.
- Uyarı: zayıf katman v0 K3.2 / v1 K7.2 gibi "tüm çıktı" ölçütlerini etkileyebilir;
  kilitli ölçütler değişmez, etki olduğu gibi raporlanır.
