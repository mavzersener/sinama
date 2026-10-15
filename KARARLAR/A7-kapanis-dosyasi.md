# A7 kapanış dosyası — kaynak depoların dondurulması

- **Durum:** Dondurma **uygulandı — 15.10.2026**, proje sahibinin açık onayıyla
  ("A7 dondurmasını uygulayıp A6–A7 commit'lerini push'la" talimatına "ok").
  Aşamanın biçimsel kapanışı CI sonucu görüldükten sonra proje sahibinindir
  (ADR-001: aşamayı proje sahibi kapatır).
- **Çıkış ölçütü (ADR-001):** "etiket ve yönlendirme". Karar belgeleri:
  [ADR-001](ADR-001-tek-program.md) (A7 satırı), DataFlow için [ADR-004 md. 7](ADR-004-a6-atolye.md).
- **Araç:** `betikler/a7_dondur.py` — kuru çalıştırma 02.10.2026'da HAZIR'dı;
  uygulama öncesi 15.10.2026'da yeniden koşuldu, tüm ön koşullar yine sağlandı.

## 1. Kanıt

| Depo | Taban (hasat) | Dondurma commit'i | Etiket | İçerik |
|---|---|---|---|---|
| `C:\Projects\suc_analizi` | `20d6e2c` | `01462e7` | `sinama-dondurma` | README başına yönlendirme bloğu + `DONDURULDU.md` (tek commit, deponun kendi kancalarıyla) |
| `C:\Projects\DataFlow` | `5ea8652` | `3d3d9d0` | `sinama-dondurma` | aynı; ek koşul A6 eşdeğerliği E1–E5 (`uygulama/atolye_esdegerlik/sonuc.json`) doğrulandı |

- Kod silinmedi; depolar çalışır durumda, geçmiş yerinde. Geri dönüş her biri için:
  `git revert <dondurma commit'i>` ve `git tag -d sinama-dondurma`.
- Kaynak depoların uzaklarına hiçbir şey gönderilmedi (betik push yapmaz).
- DataFlow'nun dondurulmasıyla A6 çıkış ölçütünün ikinci yarısı ("→ DataFlow dondurulur")
  da tamamlanmış oldu; A6'nın tek açık devri kalmadı (CI doğrulaması bu push'la koşar).

## 2. Dondurulmayanlar (betikte gerekçeli, değişmedi)

| Depo | Neden |
|---|---|
| science_gpt | yalnız kavram hasadı (ADR-002); ayrı motor — dondurma kararı proje sahibinde |
| harp_pol_x | dış sistem (HARP denetim otoritesi); yalnız kavram hasadı — çalışmaya devam eder |
| AnlamCekirdegi | ADR-001 md. 6: ayrı yaşar (MCP/dışa aktarımla bağlanır) |
| YerelAjan_v2 | ADR-001 md. 6: ayrı yaşar |
| duzeltme_suc_analizi | git'siz hazırlık kopyası; A2'de birleştirildi — etiketlenemez, dokunulmaz |

## 3. Açık kalanlar (devir)

| Konu | Not |
|---|---|
| CI'da A6 + A7 | A6–A7 commit'leri bu onayla push'landı; CI (bekçi tüm geçmişte, çekirdek tam kapı Linux/Windows, Atölye derleme/vitest/eşdeğerlik) sonucu beklenecek |
| HARP'ın P06 yarısı | ADR-001 açık konusu: HARP dondurulmuş `suc_analizi`'yi kullanmaya devam ediyor (kod yerinde, bozulma yok); P06 mahremiyet düzeltmesi yalnız Sınama'da. Birleşik düzeltmenin HARP tarafına taşınması kararı proje sahibinde |
| science_gpt'nin dondurulup dondurulmayacağı | yalnız kavram hasadı yapıldı; karar sahibin |

## 4. ADR-001 aşama tablosu

A7 uygulandı; ADR-001'in A0–A7 tablosundaki tüm aşamaların uygulaması tamamlandı.
Biçimsel kapanış kaydı ADR-001 İlerleme tablosundadır.
