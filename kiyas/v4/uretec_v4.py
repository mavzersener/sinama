# -*- coding: utf-8 -*-
r"""
kiyas/v4/uretec_v4.py — BMK v4'ün vaka üreteci (V10, hüküm sağlamlığı).

İki kanallı aylık Poisson kayıtları: karakol baştan vardır, kesinti ayından sonra
karakol_carpani ile çarpılır; çevrimiçi ya kesinti ayında başlar ya da baştan
vardır ve cevrimici_carpani ile çarpılır. Çekiliş sırası v0 v2_bildirim ve v3
v9_gercek_artis ile aynıdır (λ = 0 kanalı için çekiliş yapılmaz): saf artefakt
ve gerçek artış senaryoları o üreteçlerin verisini kimlikler dışında birebir
üretir (testle kilitli). Gerçek veriye yazılmaz; satır sırası tarihe göredir.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uretec import Tohum  # noqa: E402  (v0, kilitli ve değişmemiş)


def parametreler(vaka, senaryo):
    """Ortak parametrelerin üzerine senaryonun değişenleri."""
    p = dict(vaka["uretec"]["ortak_parametreler"])
    p.update(vaka["senaryolar"][senaryo]["degisen"])
    return p


def v10_kanallar(p, tohum):
    """Returns: (satirlar, gercek) — gercek: kesinti tarihi ve kanal düzeni."""
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
        if p["cevrimici"] == "bastan":
            kanallar.append(("cevrimici", p["cevrimici_lambda"] * p["cevrimici_carpani"] if sonra
                             else p["cevrimici_lambda"]))
        elif sonra:
            kanallar.append(("cevrimici", p["cevrimici_lambda"]))
        for kanal, lam in kanallar:
            if lam <= 0:
                continue
            for _ in range(t.poisson(lam)):
                gun = ay_bas + datetime.timedelta(days=int(t.u() * gun_sayisi))
                satirlar.append({"tarih": gun.isoformat(), "kanal": kanal, "yil": str(gun.year)})
    satirlar.sort(key=lambda s: s["tarih"])
    for i, s in enumerate(satirlar):
        s["id"] = f"v10-{i}"
    ky = bas.year + (bas.month - 1 + p["kesinti_ayi"] - 1) // 12
    km = (bas.month - 1 + p["kesinti_ayi"] - 1) % 12 + 1
    return satirlar, {"kesinti_tarihi": datetime.date(ky, km, 1).isoformat(),
                      "cevrimici": p["cevrimici"]}
