# -*- coding: utf-8 -*-
r"""
kiyas/v5/uretec_v5.py — BMK v5'in vaka üreteci (V11, yayılım çarpanı).

asiri_yayilim_k yoksa v4 v10_kanallar'ın KENDİSİ çağrılır (Poisson, değişmeden).
Varsa aynı kanal/ay düzeninde her ay-kanal oranı gama(k, 1/k) karışımıyla
(ortalama 1, varyans 1/k) çarpılır → negatif binom; aylık φ = 1 + λ/k. Gama
çekilişi k üstel değişkenin toplamıdır (k tam sayı); yalnız random() kullanılır.
Gerçek veriye yazılmaz; satır sırası tarihe göredir.
"""
import datetime
import math
import os
import sys

KIYAS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIYAS)
sys.path.insert(0, os.path.join(KIYAS, "v4"))
import uretec_v4  # noqa: E402  (v4, kilitli ve değişmemiş)
from uretec import Tohum  # noqa: E402


def parametreler(vaka, senaryo):
    """Ortak parametrelerin üzerine senaryonun değişenleri."""
    p = dict(vaka["uretec"]["ortak_parametreler"])
    p.update(vaka["senaryolar"][senaryo]["degisen"])
    return p


def v11_kanallar(p, tohum):
    """Returns: (satirlar, gercek)."""
    k = p.get("asiri_yayilim_k")
    if k is None:
        return uretec_v4.v10_kanallar(p, tohum)
    if p["cevrimici"] != "kesinti":
        raise ValueError("NB üreteci yalnız cevrimici='kesinti' düzenini destekler")
    t = Tohum(tohum)
    bas = datetime.date.fromisoformat(p["baslangic"])
    satirlar = []
    for ay in range(p["ay_sayisi"]):
        y, m = bas.year + (bas.month - 1 + ay) // 12, (bas.month - 1 + ay) % 12 + 1
        ay_bas = datetime.date(y, m, 1)
        ay_son = datetime.date(y + (m // 12), m % 12 + 1, 1) - datetime.timedelta(days=1)
        gun_sayisi = (ay_son - ay_bas).days + 1
        sonra = ay >= p["kesinti_ayi"] - 1
        kanallar = [("karakol", p["karakol_lambda"] * p["karakol_carpani"] if sonra
                     else p["karakol_lambda"])]
        if sonra:
            kanallar.append(("cevrimici", p["cevrimici_lambda"]))
        for kanal, lam in kanallar:
            gama = sum(-math.log(1.0 - t.u()) for _ in range(int(k))) / k
            for _ in range(t.poisson(lam * gama)):
                gun = ay_bas + datetime.timedelta(days=int(t.u() * gun_sayisi))
                satirlar.append({"tarih": gun.isoformat(), "kanal": kanal, "yil": str(gun.year)})
    satirlar.sort(key=lambda s: s["tarih"])
    for i, s in enumerate(satirlar):
        s["id"] = f"v11-{i}"
    return satirlar, {"asiri_yayilim_k": k}
