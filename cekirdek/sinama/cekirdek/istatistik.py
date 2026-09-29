# -*- coding: utf-8 -*-
"""
istatistik.py — Özet istatistik, frekans, çapraz tablo, anomali, trend.
Sadece standart kütüphane (math, statistics, collections).
"""

import math
import statistics
from collections import Counter, defaultdict

from .hipotez import _iki_yonlu_t_p


def frekans(kayitlar, alan):
    """Tek alan frekans dağılımı.
    Args: kayitlar (kayıt listesi), alan (sayılacak alan).
    Returns: {değer: adet} (Counter).
    """
    return Counter(str(k.get(alan)) for k in kayitlar)


def ozet(degerler):
    """Sayısal özet istatistik.
    Args: degerler (sayı listesi; None atlanır).
    Returns: {n, ortalama, medyan, std_sapma (popülasyon), min, maks};
    boş girdide {}.
    """
    d = [float(x) for x in degerler if x is not None]
    if not d:
        return {}
    return {
        "n": len(d),
        "ortalama": statistics.fmean(d),
        "medyan": statistics.median(d),
        "std_sapma": statistics.pstdev(d) if len(d) > 1 else 0.0,
        "min": min(d),
        "maks": max(d),
    }


def capraz_tablo(kayitlar, satir_alan, sutun_alan):
    """İki kategorik alanın çapraz tablosu.
    Args: kayitlar, satir_alan, sutun_alan.
    Returns: {satır_değeri: {sütun_değeri: adet}}.
    """
    tablo = defaultdict(Counter)
    for k in kayitlar:
        tablo[str(k.get(satir_alan))][str(k.get(sutun_alan))] += 1
    return {r: dict(c) for r, c in tablo.items()}


def yuzdelik(degerler, p):
    """Doğrusal enterpolasyonlu yüzdelik.
    Args: degerler (sayı listesi), p (yüzde, 0-100).
    Returns: p'inci yüzdelik; boş girdide None.
    """
    d = sorted(float(x) for x in degerler)
    if not d:
        return None
    if len(d) == 1:
        return d[0]
    k = (len(d) - 1) * (p / 100.0)
    alt = int(math.floor(k))
    ust = int(math.ceil(k))
    if alt == ust:
        return d[alt]
    return d[alt] + (d[ust] - d[alt]) * (k - alt)


def z_skor_anomali(kayitlar, alan, esik=2.0):
    """|z| ≥ esik kayıtları z_skor alanı ekleyerek döner.
    Args: kayitlar, alan (sayısal), esik (varsayılan 2.0).
    Returns: anomali kayıt listesi.
    """
    degerler = []
    for k in kayitlar:
        try:
            degerler.append(float(k.get(alan)))
        except (TypeError, ValueError):
            degerler.append(None)
    gecerli = [d for d in degerler if d is not None]
    if len(gecerli) < 2:
        return []
    mu = statistics.fmean(gecerli)
    sd = statistics.pstdev(gecerli) or 1e-9
    sonuc = []
    for k, d in zip(kayitlar, degerler):
        if d is None:
            continue
        z = (d - mu) / sd
        if abs(z) >= esik:
            yeni = dict(k)
            yeni["z_skor"] = round(z, 3)
            sonuc.append(yeni)
    return sonuc


def degisim_orani(eski, yeni):
    """Yüzde değişim: 100*(yeni-eski)/eski.
    Args: eski, yeni (sayı).
    Returns: yüzde (örn. -28.57); eski=0 ise None.
    """
    if eski == 0:
        return None
    return round(100.0 * (yeni - eski) / eski, 2)


def kayan_ortalama(seri, pencere=7):
    """Kayan ortalama serisi.
    Args: seri (dönemlik değerler), pencere (dönem sayısı — günlük seride gün).
    Returns: her nokta için pencere ortalaması (uçlarda kısa pencere).
    """
    sonuc = []
    for i in range(len(seri)):
        bas = max(0, i - pencere + 1)
        parca = seri[bas:i + 1]
        sonuc.append(round(statistics.fmean(parca), 3) if parca else None)
    return sonuc


def dogrusal_trend(seri, alfa=0.05):
    """En küçük kareler doğrusal trend + eğim için t-testi (A4.7).

    BMK v0 K2.3: yorum anlamlılık sınamadan yön söylüyordu — oranı sabit bir
    kanalda 30/30 tohumda "artan"/"azalan". Artık yön yalnız eğim anlamlıysa
    (p < alfa) söylenir.
    Args: seri (dönemlik değerler); alfa (anlamlılık düzeyi).
    Returns: {egim (dönem başına değişim), kesim, se, t, p,
              yorum: artan | azalan (anlamlı) | anlamlı trend yok | yatay | yetersiz veri}.
    """
    n = len(seri)
    if n < 3:
        return {"egim": 0.0, "kesim": seri[0] if seri else 0.0, "yorum": "yetersiz veri"}
    xs = list(range(n))
    mx, my = statistics.fmean(xs), statistics.fmean(seri)
    pay = sum((x - mx) * (y - my) for x, y in zip(xs, seri))
    payda = sum((x - mx) ** 2 for x in xs) or 1e-9
    b = pay / payda
    a = my - b * mx
    if abs(b) < 1e-9:
        return {"egim": 0.0, "kesim": round(a, 4), "se": 0.0, "t": 0.0, "p": 1.0,
                "yorum": "yatay"}
    sse = sum((y - a - b * x) ** 2 for x, y in zip(xs, seri))
    se = math.sqrt(sse / (n - 2) / payda)
    t = b / se if se > 0 else math.copysign(float("inf"), b)
    p = 0.0 if se == 0 else _iki_yonlu_t_p(t, n - 2)
    yorum = ("artan" if b > 0 else "azalan") if p < alfa else "anlamlı trend yok"
    return {"egim": round(b, 4), "kesim": round(a, 4), "se": round(se, 6),
            "t": round(t, 3) if math.isfinite(t) else None, "p": p, "yorum": yorum}


def duyarlilik_analizi(degerler, esik=3.0):
    """
    Aykırı değerde duyarlılık (tahribatsızlık ilkesi): değer ATILMAZ;
    özet, aykırılar dahil ve hariç iki türlü raporlanır, karar insana ayrı
    notla bırakılır. Dönüş: {'dahil', 'haric', 'aykiri_sayisi', 'not'}
    """
    d = [float(x) for x in degerler if x is not None]
    if len(d) < 4:
        return {"dahil": ozet(d), "haric": ozet(d), "aykiri_sayisi": 0,
                "not": "yeterli veri yok"}
    mu = statistics.fmean(d)
    sd = statistics.pstdev(d) or 1e-9
    icerde = [x for x in d if abs(x - mu) / sd < esik]
    aykirilar = len(d) - len(icerde)
    return {"dahil": ozet(d), "haric": ozet(icerde) if icerde else {},
            "aykiri_sayisi": aykirilar,
            "not": ("aykırı değerler ATILMADI; iki özet karşılaştırılıp karar "
                    "insan tarafından gerekçelendirilmelidir")}


def iqr(degerler):
    """Çeyrekler açıklığı (sağlam dağılım ölçüsü)."""
    d = sorted(float(x) for x in degerler)
    if len(d) < 2:
        return None
    q1 = yuzdelik(d, 25)
    q3 = yuzdelik(d, 75)
    return {"q1": round(q1, 3), "q3": round(q3, 3), "iqr": round(q3 - q1, 3)}


def mad(degerler):
    """Medyan mutlak sapma (aykırı değere en dayanıklı ölçü)."""
    d = [float(x) for x in degerler]
    if not d:
        return None
    m = statistics.median(d)
    return round(statistics.median([abs(x - m) for x in d]), 3)


def varyasyon_katsayisi(degerler):
    """CV = std/ortalama — farklı birimlerin yayılımını karşılaştırır."""
    d = [float(x) for x in degerler]
    if len(d) < 2:
        return None
    mu = statistics.fmean(d)
    if mu == 0:
        return None
    return round(statistics.stdev(d) / abs(mu), 4)
