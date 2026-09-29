# -*- coding: utf-8 -*-
"""
kume.py — Küme işlemleri (kesişim/birleşim/fark) ve bulanık eşleşme
(Levenshtein mesafesi, saf Python). Çin modelindeki 关联碰撞分析 karşılığı.
"""

from .veri import normalize_metin


def _anahtar_seti(kayitlar, alan):
    return {normalize_metin(k.get(alan)) for k in kayitlar if k.get(alan) is not None}


def kesisim(liste_a, liste_b, alan):
    """İki kayıt listesinde ortak anahtar değerleri (关联: kesişim)."""
    return _anahtar_seti(liste_a, alan) & _anahtar_seti(liste_b, alan)


def birlesim(liste_a, liste_b, alan):
    """İki listenin alan değerleri kümesinin birleşimi.
    Args: liste_a, liste_b, alan. Returns: değer kümesi.
    """
    return _anahtar_seti(liste_a, alan) | _anahtar_seti(liste_b, alan)


def fark(liste_a, liste_b, alan):
    """A'da olup B'de olmayan anahtarlar (碰撞: çakıştırma/fark)."""
    return _anahtar_seti(liste_a, alan) - _anahtar_seti(liste_b, alan)


def carpisma(listeler, alan):
    """
    N listeyi aynı anda çakıştırır: hepsinde ortak olan anahtarlar.
    listeler: [liste1, liste2, ...]
    """
    if not listeler:
        return set()
    sonuc = _anahtar_seti(listeler[0], alan)
    for l in listeler[1:]:
        sonuc &= _anahtar_seti(l, alan)
    return sonuc


def levenshtein(a, b):
    """İki metin arası düzenleme mesafesi (saf Python, O(len a * len b))."""
    a, b = normalize_metin(a), normalize_metin(b)
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    onceki = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        simdiki = [i]
        for j, cb in enumerate(b, 1):
            simdiki.append(min(onceki[j] + 1, simdiki[-1] + 1,
                               onceki[j - 1] + (ca != cb)))
        onceki = simdiki
    return onceki[-1]


def benzerlik_orani(a, b):
    """0-1 arası benzerlik (1 = aynı)."""
    a, b = normalize_metin(a), normalize_metin(b)
    maks = max(len(a), len(b))
    if maks == 0:
        return 1.0
    return round(1.0 - levenshtein(a, b) / maks, 3)


def bulanik_eslesme(kayitlar, alan, hedef, esik=0.8):
    """
    Alan değerleri hedef metne esik üstü benzeyen kayıtları döner.
    Kimlik/adres yazım farklarını yakalamak için.
    """
    sonuc = []
    for k in kayitlar:
        b = benzerlik_orani(k.get(alan), hedef)
        if b >= esik:
            yeni = dict(k)
            yeni["benzerlik"] = b
            sonuc.append(yeni)
    sonuc.sort(key=lambda x: -x["benzerlik"])
    return sonuc
