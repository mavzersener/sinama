# -*- coding: utf-8 -*-
r"""
kiyas/v1/uretec_v1.py — BMK v1'in yeni vaka üreteçleri (V5, V6).

v0 üreteci (kiyas/uretec.py) DEĞİŞTİRİLMEDEN kullanılır; tohumlu rastgele
kaynak (Tohum) oradan gelir — yalnız random.random(), sürümden bağımsız.
Gerçek (hangi bölgenin arttığı / anomali olduğu) VERİYE YAZILMAZ: bölge adları
tohumla seçilen bölgeyi ele vermez, satır sırası tarihe göredir.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uretec import Tohum  # noqa: E402  (v0, kilitli ve değişmemiş)


def _bolge_adlari(n):
    """Nötr bölge adları: B00, B01, ... (gerçeği taşımaz)."""
    return [f"B{i:02d}" for i in range(n)]


def v5_yukselen(p, tohum, varyant):
    """V5: bölge × dönem olayları. 'homojen': her bölge her dönem Poisson(λ);
    'artan': tohumla seçilen TEK bölgenin oranı dönemlerle çarpanlarla artar.

    Returns:
        (satirlar, gercek) — gercek: artan bölgenin adı (homojende None).
    """
    t = Tohum(tohum)
    adlar = _bolge_adlari(p["bolge_sayisi"])
    artan = adlar[int(t.u() * len(adlar))] if varyant == "artan" else None
    bas = datetime.date.fromisoformat(p["baslangic"])
    satirlar = []
    for d in range(p["donem_sayisi"]):
        donem_bas = bas + datetime.timedelta(days=d * p["donem_gun"])
        for ad in adlar:
            lam = p["lambda"] * (p["artan_carpanlar"][d] if ad == artan else 1.0)
            for _ in range(t.poisson(lam)):
                gun = donem_bas + datetime.timedelta(days=int(t.u() * p["donem_gun"]))
                satirlar.append({"bolge": ad, "tarih": gun.isoformat()})
    satirlar.sort(key=lambda s: (s["tarih"], s["bolge"]))
    for i, s in enumerate(satirlar):
        s["id"] = f"v5-{i}"
    return satirlar, {"artan": artan}


def v6_anomali(p, tohum, varyant):
    """V6: bölge başına olay sayısı. 'homojen': hepsi Poisson(λ); 'anomali':
    tohumla seçilen TEK bölge Poisson(anomali_λ).

    Returns:
        (satirlar, gercek) — gercek: anomali bölgesinin adı (homojende None).
    """
    t = Tohum(tohum)
    adlar = _bolge_adlari(p["bolge_sayisi"])
    anomali = adlar[int(t.u() * len(adlar))] if varyant == "anomali" else None
    satirlar = []
    for ad in adlar:
        lam = p["anomali_lambda"] if ad == anomali else p["lambda"]
        satirlar.extend({"bolge": ad} for _ in range(t.poisson(lam)))
    for i, s in enumerate(satirlar):
        s["id"] = f"v6-{i}"
    return satirlar, {"anomali": anomali}
