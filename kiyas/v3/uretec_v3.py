# -*- coding: utf-8 -*-
r"""
kiyas/v3/uretec_v3.py — BMK v3'ün vaka üreteçleri (V9, kategorik hüküm).

Artefakt, odaklı/CSR ve seri senaryoları v0 (kiyas/uretec.py) ve v2
(kiyas/v2/uretec_v2.py) üreteçlerini DEĞİŞTİRİLMEDEN, parametreyle çağırır.
Yeni olan tek üreteç gerçek artıştır: v2_bildirim ile aynı kayıt biçimi, ama
iki kanal da baştan vardır ve kesinti ayından sonra İKİSİ de artar. Gerçek
veriye yazılmaz; satır sırası tarihe göredir.
"""
import datetime
import os
import sys

KIYAS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KIYAS)
sys.path.insert(0, os.path.join(KIYAS, "v2"))
import uretec  # noqa: E402  (v0, kilitli ve değişmemiş)
import uretec_v2  # noqa: E402  (v2, kilitli ve değişmemiş)
from uretec import Tohum  # noqa: E402


def v9_gercek_artis(p, tohum):
    """Gerçek artış: karakol ve çevrimiçi baştan var; kesinti ayından sonra
    ikisinin de aylık oranı artis_carpani ile çarpılır.

    Returns:
        (satirlar, gercek) — gercek: kesinti tarihi.
    """
    t = Tohum(tohum)
    bas = datetime.date.fromisoformat(p["baslangic"])
    satirlar = []
    for ay in range(p["ay_sayisi"]):
        y, m = bas.year + (bas.month - 1 + ay) // 12, (bas.month - 1 + ay) % 12 + 1
        ay_bas = datetime.date(y, m, 1)
        ay_son = datetime.date(y + (m // 12), m % 12 + 1, 1) - datetime.timedelta(days=1)
        gun_sayisi = (ay_son - ay_bas).days + 1
        carpan = p["artis_carpani"] if ay >= p["kesinti_ayi"] - 1 else 1.0
        for kanal, lam in (("karakol", p["karakol_lambda"]), ("cevrimici", p["cevrimici_lambda"])):
            for _ in range(t.poisson(lam * carpan)):
                gun = ay_bas + datetime.timedelta(days=int(t.u() * gun_sayisi))
                satirlar.append({"tarih": gun.isoformat(), "kanal": kanal, "yil": str(gun.year)})
    satirlar.sort(key=lambda s: s["tarih"])
    for i, s in enumerate(satirlar):
        s["id"] = f"v9-{i}"
    ky = bas.year + (bas.month - 1 + p["kesinti_ayi"] - 1) // 12
    km = (bas.month - 1 + p["kesinti_ayi"] - 1) % 12 + 1
    return satirlar, {"kesinti_tarihi": datetime.date(ky, km, 1).isoformat()}


def parametreler(vaka, senaryo):
    """Senaryonun parametreleri: kendi parametreleri ya da kaynak senaryonunkiler
    (+ varsa değişenler)."""
    s = vaka["senaryolar"][senaryo]
    kaynak = s.get("parametreler_kaynak")
    p = dict(vaka["senaryolar"][kaynak]["parametreler"] if kaynak else s["parametreler"])
    p.update(s.get("degisen", {}))
    return p


def uret(vaka, senaryo, tohum):
    """Senaryonun verisi: (satirlar, gercek)."""
    p = parametreler(vaka, senaryo)
    ad = vaka["senaryolar"][senaryo]["uretec"]
    if ad == "uretec.v2_bildirim":
        return uretec.v2_bildirim(p, tohum)
    if ad == "uretec_v3.v9_gercek_artis":
        return v9_gercek_artis(p, tohum)
    if ad.startswith("uretec.v1_kumelenme["):
        return uretec.v1_kumelenme(p, tohum, ad[len("uretec.v1_kumelenme["):-1])
    if ad == "uretec_v2.v8_seri":
        return uretec_v2.v8_seri(p, tohum)
    raise ValueError(f"bilinmeyen üreteç: {ad}")
