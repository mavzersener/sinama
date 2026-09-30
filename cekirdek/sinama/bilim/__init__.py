# -*- coding: utf-8 -*-
"""
sinama.bilim — bilim katmanı v1 (ADR-002).

Soru → hipotez seti (birincil + rakipler + H_bilinmeyen) → sınamalar → kategorik
hüküm. Mevcut PPDAC oturumu ve hash zinciri üstünde çalışır; ikinci bir kayıt
defteri açmaz. Olasılık, yüzde ya da güven puanı üretmez (AGENTS kural 6).

- rak: Rakip Açıklama Kataloğu (RAK) v1
- sablon: soru türü şablonları (ARTIS, YOGUNLASMA, SERI)
- sinamalar: öngörü ve rakiplerin deterministik değerlendirmesi
- hukum: sürümlü, sıralı hüküm kuralları (saf işlev)
- calisma: Rehberli akış (Soru → Plan → Hüküm)
"""
