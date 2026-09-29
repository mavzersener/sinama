# -*- coding: utf-8 -*-
"""
orneklem.py — Örnekleme ve örnekleme hatası (Maxfield & Babbie, Bölüm 8).
Olasılık örneklemesi, örnekleme hatası, güven aralığı, örneklem büyüklüğü.
"""

import math
import random

Z_TABLO = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}


def basit_tesadufi(kayitlar, n, seed=None):
    """Basit tesadüfi örneklem."""
    rng = random.Random(seed)
    n = min(n, len(kayitlar))
    return rng.sample(kayitlar, n)


def sistematik(kayitlar, n, seed=None):
    """Sistematik örneklem: k = N/n aralıkla, rastgele başlangıçla."""
    N = len(kayitlar)
    if N == 0 or n <= 0:
        return []
    k = max(1, N // n)
    rng = random.Random(seed)
    bas = rng.randint(0, k - 1)
    return [kayitlar[i] for i in range(bas, N, k)][:n]


def tabakali(kayitlar, tabaka_alan, n, orantili=True, seed=None):
    """
    Tabakalı örneklem. orantili=True ise her tabakadan büyüklüğü oranında,
    False ise eşit sayıda birim çeker (orantısız tabakalı).
    """
    rng = random.Random(seed)
    tabakalar = {}
    for k in kayitlar:
        tabakalar.setdefault(str(k.get(tabaka_alan)), []).append(k)
    sonuc = []
    N = len(kayitlar)
    for t, birimler in sorted(tabakalar.items()):
        if orantili:
            ni = max(1, round(n * len(birimler) / N))
        else:
            ni = max(1, n // max(1, len(tabakalar)))
        sonuc.extend(rng.sample(birimler, min(ni, len(birimler))))
    return sonuc


def ornekleme_hatasi(p, n):
    """Oran için standart hata: SE = sqrt(p(1-p)/n)."""
    if n <= 0:
        return None
    return round(math.sqrt(p * (1 - p) / n), 4)


def guven_araligi_oran(p, n, guven=0.95):
    """
    Oran için güven aralığı (Ch 8: confidence levels and intervals).
    Dönüş: {'oran', 'se', 'alt', 'ust', 'guven'}
    """
    z = Z_TABLO.get(guven, 1.96)
    se = ornekleme_hatasi(p, n)
    if se is None:
        return None
    return {"oran": round(p, 4), "se": se,
            "alt": round(max(0.0, p - z * se), 4),
            "ust": round(min(1.0, p + z * se), 4), "guven": guven}


def guven_araligi_ortalama(ortalama, std, n, guven=0.95):
    """Ortalama için güven aralığı."""
    if n <= 0:
        return None
    z = Z_TABLO.get(guven, 1.96)
    se = std / math.sqrt(n)
    return {"ortalama": round(ortalama, 3), "se": round(se, 4),
            "alt": round(ortalama - z * se, 3),
            "ust": round(ortalama + z * se, 3), "guven": guven}


def orneklem_buyuklugu(hata_payi, p=0.5, guven=0.95):
    """
    İstenen hata payı için gerekli örneklem büyüklüğü:
    n = z^2 * p(1-p) / e^2  (p=0.5 en kötü durum).
    """
    z = Z_TABLO.get(guven, 1.96)
    return math.ceil(z * z * p * (1 - p) / (hata_payi ** 2))
