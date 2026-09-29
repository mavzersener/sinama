# -*- coding: utf-8 -*-
"""
tekrar.py — Mükerrer mağduriyet ve yakın-tekrar (near-repeat) analizi.
Kayıt alanları: id, tarih (datetime), lat, lon, adres/mağdur anahtarı.
Sadece standart kütüphane.
"""

import random
from collections import Counter, defaultdict
from itertools import combinations
from .mekan import haversine_km
from .kaynak_butce import _pozitif, _sim_butce


def mukerrer_magduriyet(kayitlar, anahtar_alan, gun_penceresi=365):
    """
    Aynı anahtar (adres/mağdur/tesis) için tekrar eden olayları bulur.
    Dönüş: {anahtar: [kayıt_id'leri]} — yalnızca 2+ olayı olan anahtarlar.
    """
    gruplar = defaultdict(list)
    for k in kayitlar:
        anahtar = str(k.get(anahtar_alan) or "").strip()
        if anahtar:
            gruplar[anahtar].append(k)
    return {a: [x.get("id") for x in v] for a, v in gruplar.items() if len(v) >= 2}


def yakin_tekrar_ciftleri(kayitlar, mesafe_km=0.4, gun=14):
    """
    Knox mantığında yakın-tekrar çiftleri: hem uzayda hem zamanda yakın olay çiftleri.
    kayitlar: [{'id':..., 'tarih': datetime, 'lat':..., 'lon':...}, ...]
    Dönüş: [{'id1','id2','mesafe_km','gun_fark'}]
    """
    gecerli = [k for k in kayitlar
               if k.get("tarih") is not None and k.get("lat") is not None]
    # Faz G (v6.4): grid budaması; nihai mesafe haversine — birebir sonuç
    from .mekan import yakin_ciftler_hizli
    pts = [(k["lat"], k["lon"]) for k in gecerli]
    sonuc = []
    for a, b, d in yakin_ciftler_hizli(pts, mesafe_km):
        gf = abs((gecerli[a]["tarih"] - gecerli[b]["tarih"]).days)
        if gf <= gun:
            sonuc.append({"id1": gecerli[a].get("id"),
                          "id2": gecerli[b].get("id"),
                          "mesafe_km": round(d, 3), "gun_fark": gf})
    return sonuc


def knox_tablosu(kayitlar, mesafe_bantlari=None, gun_bantlari=None):
    """
    Gözlenen çift sayılarını uzay-zaman bantlarına dağıtır (Knox testi tablosu).
    Dönüş: {(mesafe_bandi, gun_bandi): adet}
    """
    if mesafe_bantlari is None:
        mesafe_bantlari = [0.2, 0.5, 1.0, 2.0]
    if gun_bantlari is None:
        gun_bantlari = [7, 14, 28, 56]
    gecerli = [k for k in kayitlar
               if k.get("tarih") is not None and k.get("lat") is not None]
    from .mekan import yakin_ciftler_hizli
    pts = [(k["lat"], k["lon"]) for k in gecerli]
    tablo = Counter()
    for a, b, d in yakin_ciftler_hizli(pts, max(mesafe_bantlari)):
        gf = abs((gecerli[a]["tarih"] - gecerli[b]["tarih"]).days)
        mb = next((m for m in mesafe_bantlari if d <= m), None)
        gb = next((g for g in gun_bantlari if gf <= g), None)
        if mb is not None and gb is not None:
            tablo[(mb, gb)] += 1
    return dict(tablo)


def seri_eslestirme(kayitlar, mo_alan, benzerlik_esik=0.6):
    """
    Basit seri suç eşleştirme: MO metinlerini kelime kümeleriyle
    Jaccard benzerliği üzerinden karşılaştırır.
    """
    def kelime_kumesi(s):
        """Metni küçük harfli kelime kümesine çevirir (Jaccard için; iç yardımcı).
        """
        return set(str(s or "").lower().split())
    kumeler = {k.get("id"): kelime_kumesi(k.get(mo_alan)) for k in kayitlar}
    sonuc = []
    ids = list(kumeler.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = kumeler[ids[i]], kumeler[ids[j]]
            if not a or not b:
                continue
            jacc = len(a & b) / len(a | b)
            if jacc >= benzerlik_esik:
                sonuc.append({"id1": ids[i], "id2": ids[j],
                              "benzerlik": round(jacc, 3)})
    sonuc.sort(key=lambda x: -x["benzerlik"])
    return sonuc


# --- Faz 3.1: Monte Carlo anlamlılık (gözlem ≠ kanıt) ---

def _cift_sayisi(kayitlar, mesafe_km, gun):
    """(uzay, zaman) penceresi içindeki çift sayısı — test istatistiği."""
    gecerli = [k for k in kayitlar
               if k.get("tarih") is not None and k.get("lat") is not None]
    from .mekan import yakin_ciftler_hizli
    pts = [(k["lat"], k["lon"]) for k in gecerli]
    n = 0
    for a, b, d in yakin_ciftler_hizli(pts, mesafe_km):
        if abs((gecerli[a]["tarih"] - gecerli[b]["tarih"]).days) <= gun:
            n += 1
    return n


def knox_anlamlilik(kayitlar, mesafe_km=0.4, gun=14, sim=99, seed=None):
    """
    Knox / near-repeat Monte Carlo permütasyon testi.
    Args: mesafe_km (km) — uzaysal yakınlık eşiği.
    Null hipotez: zaman damgaları mekândan bağımsız (uzay-zaman etkileşimi
    yok). Tarihler noktalar arasında karıştırılır, istatistik yeniden
    hesaplanır; p = (1 + sim >= gözlenen) / (sim + 1).
    Dönüş: {'gozlenen', 'beklenen_ortalama', 'oran', 'p', 'sim', 'yorum'}
    """
    _pozitif(mesafe_km, 'mesafe_km')
    _sim_butce(len(kayitlar), sim)
    gecerli = [dict(k) for k in kayitlar
               if k.get("tarih") is not None and k.get("lat") is not None]
    if len(gecerli) < 3:
        return None
    rng = random.Random(seed)
    gozlenen = _cift_sayisi(gecerli, mesafe_km, gun)
    tarihler = [k["tarih"] for k in gecerli]
    sim_degerler = []
    for _ in range(sim):
        kopya = [dict(k) for k in gecerli]
        karisik = tarihler[:]
        rng.shuffle(karisik)
        for k, trh in zip(kopya, karisik):
            k["tarih"] = trh
        sim_degerler.append(_cift_sayisi(kopya, mesafe_km, gun))
    asan = sum(1 for s in sim_degerler if s >= gozlenen)
    p = (1 + asan) / (sim + 1)
    beklenen = sum(sim_degerler) / len(sim_degerler)
    oran = round(gozlenen / beklenen, 3) if beklenen > 0 else None
    # Faz E4 (v6.3): bağımsızlık altında ANALİTİK beklenti — MC'ye ek olarak.
    # E[uzay-zaman yakın çift] = (uzay-yakın çift × zaman-yakın çift) /
    # toplam çift; MC'nin yakınsaması gereken değer.
    uzay_yakin, zaman_yakin, toplam = 0, 0, 0
    for a, b in combinations(gecerli, 2):
        toplam += 1
        if haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) <= mesafe_km:
            uzay_yakin += 1
        if abs((a["tarih"] - b["tarih"]).days) <= gun:
            zaman_yakin += 1
    beklenen_analitik = (uzay_yakin * zaman_yakin / toplam) if toplam else 0
    return {"gozlenen": gozlenen, "beklenen_ortalama": round(beklenen, 1),
            "beklenen_analitik": round(beklenen_analitik, 1),
            "oran": oran, "p": round(p, 4), "sim": sim,
            "yorum": ("anlamlı yakın-tekrar kümelenmesi" if p < 0.05
                      else "rastgelelik reddedilemedi")}


def yakin_tekrar_anlamlilik(kayitlar, mesafe_km=0.4, gun=14, sim=99, seed=None):
    """yakin_tekrar_ciftleri için anlamlılık sarmalayıcısı (Knox MC).
    Args: mesafe_km (km) — uzaysal yakınlık eşiği."""
    return knox_anlamlilik(kayitlar, mesafe_km, gun, sim, seed)
