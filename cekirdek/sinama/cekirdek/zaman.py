# -*- coding: utf-8 -*-
"""
zaman.py — Zamansal analiz: saat/gün/ay dağılımı, dönemsel seri, aoristik.
Kayıtlarda 'tarih' alanı datetime olmalı (veri.tarih_coz kullanın).
"""

from collections import Counter
from datetime import timedelta


def saat_dagilimi(kayitlar, alan="tarih"):
    """0-23 saat dilimi dağılımı."""
    c = Counter()
    for k in kayitlar:
        t = k.get(alan)
        if t is not None:
            c[t.hour] += 1
    return dict(sorted(c.items()))


def gun_dagilimi(kayitlar, alan="tarih"):
    """Haftanın günü dağılımı (0=Pazartesi ... 6=Pazar)."""
    c = Counter()
    for k in kayitlar:
        t = k.get(alan)
        if t is not None:
            c[t.weekday()] += 1
    return dict(sorted(c.items()))


def ay_dagilimi(kayitlar, alan="tarih"):
    """Yıl-ay bazında seri: {'2025-01': n, ...} sıralı."""
    c = Counter()
    for k in kayitlar:
        t = k.get(alan)
        if t is not None:
            c[f"{t.year}-{t.month:02d}"] += 1
    return dict(sorted(c.items()))


def gunluk_seri(kayitlar, alan="tarih"):
    """Eksik günleri 0 ile doldurulmuş günlük seri (trend için)."""
    c = Counter()
    for k in kayitlar:
        t = k.get(alan)
        if t is not None:
            c[t.date()] += 1
    if not c:
        return [], []
    gunler = sorted(c)
    tum, degerler = [], []
    d = gunler[0]
    while d <= gunler[-1]:
        tum.append(str(d))
        degerler.append(c.get(d, 0))
        d += timedelta(days=1)
    return tum, degerler


def aoristik_dagilim(kayitlar, bas_alan="baslangic", bit_alan="bitis"):
    """
    Başlangıç-bitiş aralığı bilinen olaylar için aoristik saat dağılımı:
    olayın her saat dilimine 1/aralık_uzunluğu ağırlıkla pay verilir.
    """
    c = Counter()
    for k in kayitlar:
        b, s = k.get(bas_alan), k.get(bit_alan)
        if b is None or s is None or s < b:
            continue
        saat_sayisi = int((s - b).total_seconds() // 3600) + 1
        agirlik = 1.0 / saat_sayisi
        for i in range(saat_sayisi):
            c[(b + timedelta(hours=i)).hour] += agirlik
    return {h: round(c.get(h, 0.0), 2) for h in range(24)}
