# -*- coding: utf-8 -*-
r"""
kiyas/v8/uretec_v8.py — BMK v8'in vaka üreteci (V14 nokta deseni / NNI, V15 kırılma / CUSUM).

V14: 3×3 km kutuda nokta desenleri — tamamen rastgele (CSR), yaygın kümelenme
(Thomas süreci: tekdüze ebeveynler, her birinin çevresinde normal dağılmış
çocuklar; kutu dışına düşen çocuk yeniden çekilir — pencere CSR ile aynı kalır,
kümelenme sınır kutusunun büyümesinden türemez), yerel odak (v0 V1 gibi).
V15: günlük olay kayıtları; ay başına Poisson(λ), kesinti ayından sonra λ ×
`carpan_sonra`; isteğe bağlı `yayilim_k` ay başına gama(k) karışımıyla aşırı yayılım
(k tam sayı, ≥ 1). Yalnız random() kullanılır; gerçek veriye yazılmaz.
"""
import datetime
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uretec import KM_BOYLAM_41, KM_ENLEM, Tohum, _kutu  # noqa: E402  (v0, kilitli)


def parametreler(vaka, senaryo):
    """Vakanın ortak parametrelerinin üzerine senaryonun değişenleri."""
    p = dict(vaka["uretec"]["ortak_parametreler"])
    p.update(vaka["senaryolar"][senaryo]["degisen"])
    return p


def v14_noktalar(p, tohum):
    """Returns: (satirlar, gercek) — desen: csr | kume | odak."""
    t = Tohum(tohum)
    lat0, lat1, lon0, lon1 = _kutu(p["merkez_lat"], p["merkez_lon"], p["kenar_km"])
    n, desen = p["n"], p["desen"]
    noktalar = []
    if desen == "csr":
        noktalar = [(t.tekduze(lat0, lat1), t.tekduze(lon0, lon1)) for _ in range(n)]
    elif desen == "kume":
        ebeveyn = [(t.tekduze(lat0, lat1), t.tekduze(lon0, lon1)) for _ in range(p["ebeveyn"])]
        for i in range(n):
            e = ebeveyn[i % len(ebeveyn)]
            while True:   # çocuk kutu dışına düşerse yeniden çekilir: pencere CSR ile aynı
                a = t.normal(e[0], p["sigma_km"] * KM_ENLEM)
                b = t.normal(e[1], p["sigma_km"] * KM_BOYLAM_41)
                if lat0 <= a <= lat1 and lon0 <= b <= lon1:
                    break
            noktalar.append((a, b))
    elif desen == "odak":
        n_odak = round(n * p["odak_orani"])
        noktalar = [(t.normal(p["merkez_lat"], p["sigma_km"] * KM_ENLEM),
                     t.normal(p["merkez_lon"], p["sigma_km"] * KM_BOYLAM_41)) for _ in range(n_odak)]
        noktalar += [(t.tekduze(lat0, lat1), t.tekduze(lon0, lon1)) for _ in range(n - n_odak)]
    else:
        raise ValueError(f"bilinmeyen desen: {desen}")
    # satır sırası gerçeği ele vermesin: Fisher-Yates
    for i in range(len(noktalar) - 1, 0, -1):
        j = int(t.u() * (i + 1))
        noktalar[i], noktalar[j] = noktalar[j], noktalar[i]
    satirlar = [{"id": f"v14-{i}", "tarih": "2025-06-01", "lat": round(a, 6), "lon": round(b, 6)}
                for i, (a, b) in enumerate(noktalar)]
    return satirlar, {"desen": desen}


def v15_seri(p, tohum):
    """Returns: (satirlar, gercek) — gercek: kesinti günü (ilk kayıt gününden itibaren)."""
    t = Tohum(tohum)
    bas = datetime.date.fromisoformat(p["baslangic"])
    k = p.get("yayilim_k")
    if k is not None and (k != int(k) or k < 1):
        raise ValueError("yayilim_k tam sayı ve ≥ 1 olmalı")
    satirlar = []
    for ay in range(p["ay_sayisi"]):
        y, m = bas.year + (bas.month - 1 + ay) // 12, (bas.month - 1 + ay) % 12 + 1
        ay_bas = datetime.date(y, m, 1)
        ay_son = datetime.date(y + (m // 12), m % 12 + 1, 1) - datetime.timedelta(days=1)
        gun_sayisi = (ay_son - ay_bas).days + 1
        lam = p["lambda"] * (p["carpan_sonra"] if ay >= p["kesinti_ayi"] - 1 else 1.0)
        if k:
            lam = lam * sum(-math.log(1.0 - t.u()) for _ in range(int(k))) / k
        for _ in range(t.poisson(lam)):
            gun = ay_bas + datetime.timedelta(days=int(t.u() * gun_sayisi))
            satirlar.append({"tarih": gun.isoformat()})
    satirlar.sort(key=lambda s: s["tarih"])
    for i, s in enumerate(satirlar):
        s["id"] = f"v15-{i}"
    ky = bas.year + (bas.month - 1 + p["kesinti_ayi"] - 1) // 12
    km = (bas.month - 1 + p["kesinti_ayi"] - 1) % 12 + 1
    ilk = datetime.date.fromisoformat(satirlar[0]["tarih"]) if satirlar else bas
    return satirlar, {"kesinti_gunu": (datetime.date(ky, km, 1) - ilk).days}
