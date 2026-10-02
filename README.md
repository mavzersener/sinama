# Sınama — bilimsel suç analizi

Bir soruya, veriye dayanan ve dürüst bir bilimsel cevap veren suç analizi programı.

**Soru → Plan → Hüküm.** Analist sorusunu sorar ve verisini verir. Sistem birincil
hipotezi, rakip açıklamaları ve "bilinmeyen" seçeneğini sınanabilir biçimde kurar,
uygun yöntemleri kendisi seçer ve sonucu kanıtı, belirsizliği ve en güçlü rakip
açıklamasıyla birlikte sunar.

> **Durum: A7 — kaynak depoların dondurulması (onay bekliyor).** Çekirdek (`cekirdek/`),
> bilim katmanı ve BMK v0–v10 (`kiyas/`), tek süreç arka uç ile iki yüz — Rehberli `/`,
> Atölye `/atolye/` (`uygulama/`) — tamam; A0–A6 kapanış dosyaları `KARARLAR/`'da.
> Karar: [KARARLAR/ADR-001](KARARLAR/ADR-001-tek-program.md) ·
> Hasat defteri: [HASAT.md](HASAT.md) ·
> Yapay zekâ ajanları için: [AGENTS.md](AGENTS.md)

## İlkeler

- **Sade arayüz, güçlü arka plan.** Kullanıcı onlarca yöntem arasından seçim yapmaz;
  sistem seçer, gerekçesi bir tık ötededir.
- **Sade ama dürüst.** Her hüküm en güçlü rakip açıklamayı ve "neden emin değiliz"
  satırını gösterir.
- **Hesabı makine yapar.** Kanıt üreten her hesap sunucuda, tek motorda koşar; dil
  modeli opsiyoneldir ve sayı üretmez.
- **Veri depoda durmaz.** Veri kökü depo dışındadır; özel veri ve sır bu depoya
  giremez.

## İki yüz, tek arka uç

| Yüz | Kimin için | Ne yapar |
|---|---|---|
| Rehberli (varsayılan) | her analist | Soru → Plan → Hüküm kartı |
| Atölye | uzman | no-code iş akışı editörü (DataFlow mirası) |

## Düzen

```text
sinama/
  cekirdek/   deterministik suç analizi yöntemleri ve bilim katmanı (stdlib; suc_analizi mirası)
  uygulama/   tek FastAPI arka ucu; web/ Rehberli, atolye/ Atölye (DataFlow mirası)
  kiyas/      Bilimsel Muhakeme Kıyası (BMK) ve yöntem keşifleri (kesif/)
  betikler/   depo araçları (veri bekçisi, paketleme, eşdeğerlik, dondurma)
  tests/      testler (test verisi yalnız sentetik ve yalnız */sentetik/ altında)
  KARARLAR/   ADR'ler ve aşama kapanış dosyaları
```

## Geliştirme

```bash
git config core.hooksPath .githooks
```

```bash
PYTHONUTF8=1 python -m unittest discover -s tests
```

Kancalar her klonda bir kez etkinleştirilir. Commit öncesi veri bekçisi ve testler,
push öncesi itilecek tüm commit'lerin bekçi taraması çalışır.
