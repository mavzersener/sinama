# -*- coding: utf-8 -*-
r"""
kiyas/v2/uretec_v2.py — BMK v2'nin vaka üreteci (V8, seri bağlantısı).

Sıkı / yayılmış / seri yok varyantları v0 üretecini (kiyas/uretec.py,
v3_seri) DEĞİŞTİRİLMEDEN, yalnız parametreyle çağırır. Yeni olan tek şey
davranış tutarsızlığıdır ('seri_mo_alt_kume'): her seri olayı ayırt edici
davranışların rastgele bir alt kümesini taşır. Yapı v3_seri ile aynıdır;
gerçek (grup) VERİYE YAZILMAZ, satır sırası tarihe göredir.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uretec  # noqa: E402  (v0, kilitli ve değişmemiş)
from uretec import KM_BOYLAM_41, KM_ENLEM, Tohum, _kutu  # noqa: E402


def parametreler(vaka, varyant):
    """Ortak parametrelerin üzerine varyantın değişenlerini yazar."""
    p = dict(vaka["uretec"]["ortak_parametreler"])
    p.update(vaka["uretec"]["varyantlar"][varyant]["degisen"])
    return p


def v8_seri(p, tohum):
    """V8 verisi. 'seri_mo_alt_kume' yoksa v0 v3_seri'nin kendisidir.

    Returns:
        (satirlar, gercek) — gercek: {'grup': {id: grup}, 'seri': [id, ...]}.
    """
    if "seri_mo_alt_kume" not in p:
        return uretec.v3_seri(p, tohum)
    return _v8_tutarsiz(p, tohum)


def _v8_tutarsiz(p, tohum):
    """v3_seri ile aynı yapı; tek fark: her seri olayı ayırt edici MO'nun
    rastgele k'lık alt kümesini (özgün sırasıyla) + 1 genel kelime taşır."""
    t = Tohum(tohum)
    lat0, lat1, lon0, lon1 = _kutu(p["merkez_lat"], p["merkez_lon"], p["kenar_km"])
    bas = datetime.date.fromisoformat(p["baslangic"])
    havuz = p["genel_kelimeler"]
    satirlar, gruplar = [], {}

    def ekle(grup, mo, lat, lon, gun):
        """Bir kaydı ekler; grup yalnız ölçücüye gider."""
        kimlik = f"v8-{len(satirlar)}"
        satirlar.append({"id": kimlik, "mo": " ".join(mo),
                         "lat": round(lat, 6), "lon": round(lon, 6),
                         "tarih": (bas + datetime.timedelta(days=gun)).isoformat()})
        gruplar[kimlik] = grup

    def alt_kume(liste, k):
        """Yerine koymadan k öğe; özgün sıra korunur."""
        kalan = list(range(len(liste)))
        secilen = [kalan.pop(int(t.u() * len(kalan))) for _ in range(k)]
        return [liste[i] for i in sorted(secilen)]

    s_lat, s_lon = t.tekduze(lat0, lat1), t.tekduze(lon0, lon1)
    s_gun = int(t.u() * (p["gun_sayisi"] - p["seri_gun"]))
    for _ in range(p["n_seri"]):
        mo = alt_kume(p["seri_mo"], p["seri_mo_alt_kume"]) + [t.sec(havuz)]
        ekle("seri", mo,
             s_lat + t.tekduze(-1, 1) * p["seri_yaricap_km"] * KM_ENLEM,
             s_lon + t.tekduze(-1, 1) * p["seri_yaricap_km"] * KM_BOYLAM_41,
             s_gun + int(t.u() * p["seri_gun"]))
    for _ in range(p["n_ortak"]):
        ekle("ortak_mo", list(p["ortak_mo"]) + [t.sec(havuz)],
             t.tekduze(lat0, lat1), t.tekduze(lon0, lon1), int(t.u() * p["gun_sayisi"]))
    for _ in range(p["n_diger"]):
        ekle("diger", [t.sec(havuz) for _ in range(p["diger_kelime"])],
             t.tekduze(lat0, lat1), t.tekduze(lon0, lon1), int(t.u() * p["gun_sayisi"]))
    sira = sorted(range(len(satirlar)), key=lambda i: (satirlar[i]["tarih"], i))
    yeni, yeni_grup = [], {}
    for yeni_i, eski_i in enumerate(sira):
        s = dict(satirlar[eski_i])
        yeni_grup[f"v8-{yeni_i}"] = gruplar[s["id"]]
        s["id"] = f"v8-{yeni_i}"
        yeni.append(s)
    return yeni, {"grup": yeni_grup,
                  "seri": sorted(k for k, g in yeni_grup.items() if g == "seri")}
