# -*- coding: utf-8 -*-
r"""
kiyas/v7/uretec_v7.py — BMK v7'nin vaka üreteci (V13, ETKİ: müdahale değerlendirmesi).

Bölge × ay Poisson kayıtları: M (müdahale), K (kontrol), T (tampon). Kesinti
ayından sonra her bölgenin oranı `carpan_sonra` ile çarpılır; isteğe bağlı
`zirve` müdahale öncesi seçilmiş aylarda bir bölgeyi çarpar (ortalamaya dönüş
senaryosu); isteğe bağlı `yayilim_k` bölge başına gama(k) karışımıyla aşırı
yayılım üretir (k tam sayı, ≥ 1). Kayıt: {tarih, bolge, id}. Yalnız random()
kullanılır; gerçek veriye yazılmaz; satır sırası tarihe göredir.
"""
import datetime
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uretec import Tohum  # noqa: E402  (v0, kilitli ve değişmemiş)

BOLGELER = ("M", "K", "T")


def parametreler(vaka, senaryo):
    """Ortak parametrelerin üzerine senaryonun değişenleri."""
    p = dict(vaka["uretec"]["ortak_parametreler"])
    p.update(vaka["senaryolar"][senaryo]["degisen"])
    return p


def v13_bolgeler(p, tohum):
    """Returns: (satirlar, gercek)."""
    t = Tohum(tohum)
    bas = datetime.date.fromisoformat(p["baslangic"])
    zirve = p.get("zirve") or {}
    k_bolge = p.get("yayilim_k") or {}
    satirlar = []
    for ay in range(p["ay_sayisi"]):
        y, m = bas.year + (bas.month - 1 + ay) // 12, (bas.month - 1 + ay) % 12 + 1
        ay_bas = datetime.date(y, m, 1)
        ay_son = datetime.date(y + (m // 12), m % 12 + 1, 1) - datetime.timedelta(days=1)
        gun_sayisi = (ay_son - ay_bas).days + 1
        sonra = ay >= p["kesinti_ayi"] - 1
        for b in BOLGELER:
            lam = p["lambda"][b] * (p["carpan_sonra"].get(b, 1.0) if sonra else 1.0)
            if zirve.get("bolge") == b and (ay + 1) in zirve.get("aylar", ()):
                lam *= zirve["carpan"]
            k = k_bolge.get(b)
            if k:
                if k != int(k) or k < 1:
                    raise ValueError("yayilim_k tam sayı ve ≥ 1 olmalı")
                lam = lam * sum(-math.log(1.0 - t.u()) for _ in range(int(k))) / k
            for _ in range(t.poisson(lam)):
                gun = ay_bas + datetime.timedelta(days=int(t.u() * gun_sayisi))
                satirlar.append({"tarih": gun.isoformat(), "bolge": b})
    satirlar.sort(key=lambda s: (s["tarih"], s["bolge"]))
    for i, s in enumerate(satirlar):
        s["id"] = f"v13-{i}"
    ky = bas.year + (bas.month - 1 + p["kesinti_ayi"] - 1) // 12
    km = (bas.month - 1 + p["kesinti_ayi"] - 1) % 12 + 1
    return satirlar, {"kesinti_tarihi": datetime.date(ky, km, 1).isoformat()}
