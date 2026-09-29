# -*- coding: utf-8 -*-
r"""
kiyas/uretec.py — BMK vakalarının tohumlu veri üreteçleri (A3).

Veri dosyası YOK: her vaka, spesifikasyondaki parametreler ve bir tohumla
çalışma anında kurulur. Gerçek (planted truth) üreteçte tanımlıdır; bu
dosya ön-kayıt kilidine (kiyas/kilit.json) dahildir — sonuç görüldükten sonra
değiştirilirse koşucu çalışmayı reddeder.

Tekrar üretilebilirlik: yalnız random.Random(tohum).random() kullanılır;
normal ve Poisson çekilişleri burada elle türetilir. Böylece sonuçlar Python
sürümleri ve işletim sistemleri arasında birebir aynıdır (random.gauss gibi
yüksek düzey yardımcıların sürümler arası değişme riski yoktur).
"""
import datetime
import math
import random

KM_ENLEM = 1 / 111.32          # 1 km kaç derece enlem
KM_BOYLAM_41 = 1 / 84.02       # 41° enlemde 1 km kaç derece boylam


class Tohum:
    """Yalnız random() üzerine kurulu, sürümden bağımsız rastgele kaynak."""

    def __init__(self, tohum):
        self._r = random.Random(tohum)

    def u(self):
        """[0, 1) tekdüze."""
        return self._r.random()

    def tekduze(self, a, b):
        """[a, b) tekdüze."""
        return a + (b - a) * self._r.random()

    def normal(self, ort, sapma):
        """Box-Muller ile normal çekiliş."""
        u1 = 1.0 - self._r.random()   # (0, 1]
        u2 = self._r.random()
        return ort + sapma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)

    def poisson(self, lam):
        """Knuth yöntemi (küçük λ için yeterli; burada λ ≤ 50)."""
        esik, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= self._r.random()
            if p <= esik:
                return k
            k += 1

    def sec(self, liste):
        """Listeden tekdüze bir öğe."""
        return liste[int(self._r.random() * len(liste))]


def _kutu(merkez_lat, merkez_lon, kenar_km):
    """Merkez etrafında kenar_km boyutunda kare kutu (lat0, lat1, lon0, lon1)."""
    y_lat = kenar_km / 2 * KM_ENLEM
    y_lon = kenar_km / 2 * KM_BOYLAM_41
    return merkez_lat - y_lat, merkez_lat + y_lat, merkez_lon - y_lon, merkez_lon + y_lon


def v1_kumelenme(p, tohum, varyant):
    """V1: 'odakli' (gerçek küme) ya da 'csr' (tamamen rastgele) nokta deseni.

    Returns:
        (satirlar, gercek) — gercek: odak merkezi ve odaktaki nokta sayısı.
    """
    t = Tohum(tohum)
    lat0, lat1, lon0, lon1 = _kutu(p["merkez_lat"], p["merkez_lon"], p["kenar_km"])
    n = p["n"]
    n_odak = round(n * p["odak_orani"]) if varyant == "odakli" else 0
    satirlar = []
    for i in range(n_odak):
        satirlar.append({"lat": t.normal(p["merkez_lat"], p["odak_sigma_km"] * KM_ENLEM),
                         "lon": t.normal(p["merkez_lon"], p["odak_sigma_km"] * KM_BOYLAM_41)})
    for i in range(n - n_odak):
        satirlar.append({"lat": t.tekduze(lat0, lat1), "lon": t.tekduze(lon0, lon1)})
    # Satır sırası gerçeği ele vermesin (odak noktaları başta olmasın):
    # aynı tohumla Fisher-Yates karıştırması.
    for i in range(len(satirlar) - 1, 0, -1):
        j = int(t.u() * (i + 1))
        satirlar[i], satirlar[j] = satirlar[j], satirlar[i]
    for i, s in enumerate(satirlar):
        s.update({"id": f"v1-{i}", "tarih": p["tarih"],
                  "lat": round(s["lat"], 6), "lon": round(s["lon"], 6)})
    return satirlar, {"odak": (p["merkez_lat"], p["merkez_lon"]), "n_odak": n_odak}


def v2_bildirim(p, tohum):
    """V2: gerçek suç oranı sabit; kesinti ayından sonra YENİ bir bildirim
    kanalı kayıtları artırır (artefakt). Kanal alanı veride vardır.

    Returns:
        (satirlar, gercek) — gercek: kesinti günü (seri başından itibaren).
    """
    t = Tohum(tohum)
    bas = datetime.date.fromisoformat(p["baslangic"])
    satirlar = []
    for ay in range(p["ay_sayisi"]):
        y, m = bas.year + (bas.month - 1 + ay) // 12, (bas.month - 1 + ay) % 12 + 1
        ay_bas = datetime.date(y, m, 1)
        ay_son = (datetime.date(y + (m // 12), m % 12 + 1, 1) - datetime.timedelta(days=1))
        gun_sayisi = (ay_son - ay_bas).days + 1
        kanallar = [("karakol", p["karakol_lambda"])]
        if ay >= p["kesinti_ayi"] - 1:
            kanallar.append(("cevrimici", p["cevrimici_lambda"]))
        for kanal, lam in kanallar:
            for _ in range(t.poisson(lam)):
                gun = ay_bas + datetime.timedelta(days=int(t.u() * gun_sayisi))
                # "yil" analistin tarihten doğal olarak türettiği alandır; kesintiyi
                # SIZDIRAN bir etiket (ör. once/sonra) veriye konmaz.
                satirlar.append({"tarih": gun.isoformat(), "kanal": kanal,
                                 "yil": str(gun.year)})
    satirlar.sort(key=lambda s: s["tarih"])
    for i, s in enumerate(satirlar):
        s["id"] = f"v2-{i}"
    ky = bas.year + (bas.month - 1 + p["kesinti_ayi"] - 1) // 12
    km = (bas.month - 1 + p["kesinti_ayi"] - 1) % 12 + 1
    ilk_gun = datetime.date.fromisoformat(satirlar[0]["tarih"]) if satirlar else bas
    return satirlar, {"kesinti_tarihi": datetime.date(ky, km, 1).isoformat(),
                      "kesinti_gunu": (datetime.date(ky, km, 1) - ilk_gun).days}


def v3_seri(p, tohum):
    """V3: gerçek seri (ayırt edici MO + uzay-zaman yakınlığı) + çok yaygın
    ortak MO'yu paylaşan BAĞIMSIZ olaylar + diğerleri.

    Returns:
        (satirlar, gercek) — gercek: gerçek seri kimlikleri.
    """
    t = Tohum(tohum)
    lat0, lat1, lon0, lon1 = _kutu(p["merkez_lat"], p["merkez_lon"], p["kenar_km"])
    bas = datetime.date.fromisoformat(p["baslangic"])
    havuz = p["genel_kelimeler"]
    satirlar, gruplar = [], {}

    def ekle(grup, mo, lat, lon, gun):
        """Bir kaydı ekler. Grup (gerçek) veriye YAZILMAZ — yalnız ölçücü görür;
        aksi hâlde A5'te dil modeli cevabı veriden okuyabilirdi."""
        kimlik = f"v3-{len(satirlar)}"
        satirlar.append({"id": kimlik, "mo": " ".join(mo),
                         "lat": round(lat, 6), "lon": round(lon, 6),
                         "tarih": (bas + datetime.timedelta(days=gun)).isoformat()})
        gruplar[kimlik] = grup
        return kimlik

    s_lat, s_lon = t.tekduze(lat0, lat1), t.tekduze(lon0, lon1)
    s_gun = int(t.u() * (p["gun_sayisi"] - p["seri_gun"]))
    for _ in range(p["n_seri"]):
        mo = list(p["seri_mo"]) + [t.sec(havuz)]
        ekle(
            "seri", mo,
            s_lat + t.tekduze(-1, 1) * p["seri_yaricap_km"] * KM_ENLEM,
            s_lon + t.tekduze(-1, 1) * p["seri_yaricap_km"] * KM_BOYLAM_41,
            s_gun + int(t.u() * p["seri_gun"]))
    for _ in range(p["n_ortak"]):
        ekle("ortak_mo", list(p["ortak_mo"]) + [t.sec(havuz)],
             t.tekduze(lat0, lat1), t.tekduze(lon0, lon1), int(t.u() * p["gun_sayisi"]))
    for _ in range(p["n_diger"]):
        ekle("diger", [t.sec(havuz) for _ in range(p["diger_kelime"])],
             t.tekduze(lat0, lat1), t.tekduze(lon0, lon1), int(t.u() * p["gun_sayisi"]))
    # Kayıt sırası grubu ele vermesin (seri kayıtları hep başta olmasın):
    # tarihe göre sırala, kimlikleri yeniden ver.
    sira = sorted(range(len(satirlar)), key=lambda i: (satirlar[i]["tarih"], i))
    yeni, yeni_grup = [], {}
    for yeni_i, eski_i in enumerate(sira):
        s = dict(satirlar[eski_i])
        yeni_grup[f"v3-{yeni_i}"] = gruplar[s["id"]]
        s["id"] = f"v3-{yeni_i}"
        yeni.append(s)
    return yeni, {"grup": yeni_grup,
                  "seri": sorted(k for k, g in yeni_grup.items() if g == "seri")}
