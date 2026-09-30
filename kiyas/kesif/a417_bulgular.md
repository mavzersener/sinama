# A4.17 keşfi — sınama v1.4 adayı (t kritik değer) REDDEDİLDİ, ön-kayda gitmedi

Ön-kayıt dışı keşif, tasarım tohumları (2000–2399, 3000–3299); ölçüm tohumları görülmedi.
Çekirdek değişmedi (aday çalışma ağacında denendi, geri alındı).

## Soru

Sınama v1.3'ün aşırı iddiası (BMK v6 `karma_yeni_nb` 8/100, nominal %5) gerçek mi; kaynağı
yayılım çarpanının az sayıda aydan KESTİRİLMESİ mi (oran t dağılır ama kritik değer z)?

## Ölçüm

`a417_t_kritik.py` (resmi Rehberli akış, gerçek kod durumları):

| Senaryo | v1.3 | v1.4 adayı (Satterthwaite t) |
|---|---|---|
| karma, yeni kanal NB k=1 (400 tohum) | 30/400 = 0,075 | 30/400 = 0,075 |
| karma, iki kanal NB k=8 (200) | 0,060 | — (koşu durduruldu) |
| karma, Poisson (200) | 0,070 | — |
| güç, yeni kanal NB (200) | 0,915 | — |
| güç, Poisson (200) | 0,930 | — |

- Aşırı iddia gerçek ama küçük: %6–7,5 (BMK v6'daki %8 ile tutarlı).
- **t kritik değer HİÇBİR hükmü değiştirmedi** (30/400 → 30/400): aşırı iddia eden
  koşularda z, t eşiğinin (≈ 1,80) de çok üstünde. Aday etkisiz → ön-kayda gönderilmedi.
- İkinci hipotez (ayrım noktası yanı, `a417_bolme_yani.py`, 300 tohum): v1.3'te Poisson
  karmada ortalama z +0,047, z > 1,645 oranı 0,057 — yan ihmal edilebilir; B1 (tüm yeni
  kanal olayları "sonra") aşırı düzeltiyor (ort. z −0,315), B2 (ilk olay) +0,028. Hipotez
  ÇÜRÜDÜ; ayrım noktası değiştirilmez.

## Sonuç

Kalan aşırı iddia (%6–7,5), çok ağır kuyruklu aylık yayılımda (gama k = 1, φ ≈ 13) 11
aydan kestirilen φ'nin çarpık örnekleme dağılımından kaynaklanıyor olabilir (hipotez,
sınanmadı). Nominalin 1–2,5 puan üstünde ve BMK eşikleri içinde; **ölçülmüş sınır olarak
açık kalır.** Aday düzeltmeler (önyükleme ile φ belirsizliği, daha uzun temel dönem
koşulu) yeni keşif ve ön-kayıt ister.
