# -*- coding: utf-8 -*-
"""
tekrar.py — Mükerrer mağduriyet ve yakın-tekrar (near-repeat) analizi.
Kayıt alanları: id, tarih (datetime), lat, lon, adres/mağdur anahtarı.
Sadece standart kütüphane.
"""

import math
import random
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from .mekan import haversine_km
from .veri import koordinat_al
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


SERI_MESAFE_KM = 2.0
SERI_GUN = 60


def _tarih_gunu(v):
    """datetime/date ya da ISO metni → gün sırası (toordinal); çözülemezse None."""
    if hasattr(v, "toordinal"):
        return v.toordinal()
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date.fromisoformat(v[:10]).toordinal()
        except ValueError:
            return None
    return None


def seri_eslestirme(kayitlar, mo_alan, benzerlik_esik=0.6,
                    mesafe_km=SERI_MESAFE_KM, gun=SERI_GUN):
    """
    Seri suç ADAYI eşleştirme (A4.2): MO benzerliği TABAN ORANIYLA ağırlıklı
    ve uzay-zaman yakınlığıyla birlikte.

    Neden: düz Jaccard, çok yaygın bir MO ifadesini ("kapı kırılarak girildi")
    paylaşan BAĞIMSIZ olayları seri sayıyordu (BMK v0 K3.2: kesinlik %5;
    bağımsız faillerin 190 çiftinin 190'ı işaretlendi). Bağlantı analizi
    literatüründe davranışın ayırt ediciliği (nadirliği) ile olaylar arası
    mesafe ve zaman en güçlü ayırıcılardır (Bennell & Canter 2002;
    Bennell & Jones 2005).

    - Benzerlik: IDF ağırlıklı Jaccard (Ružička),
      Σ idf(A∩B) / Σ idf(A∪B), idf(t) = ln(N / df(t)); N ve df bu veri
      setindeki MO'lu kayıtlardan. Her kayıtta geçen kelimenin ağırlığı 0'dır.
    - Uzay-zaman: iki kayıtta da koordinat VE tarih varsa çift ancak
      mesafe ≤ mesafe_km ve gün farkı ≤ gun ise aday olur; yoksa çift
      'uzay_zaman': 'bilinmiyor' ile döner (yalnız MO — zayıf kanıt).
    - Dönen her çift bir SERİ ADAYIDIR: inceleme hipotezi, aynı fail ya da
      kimlik iddiası DEĞİLDİR ('ayni_fail_cikarimi': False).

    Args:
        kayitlar: olay kayıtları ('id', MO alanı; varsa lat/lon ve tarih).
        mo_alan: MO metninin alanı.
        benzerlik_esik: ağırlıklı benzerlik eşiği (varsayılan 0,6).
        mesafe_km: uzay yakınlığı üst sınırı (km).
        gun: zaman yakınlığı üst sınırı (gün).

    Returns:
        [{id1, id2, benzerlik, jaccard, mesafe_km, gun_farki, uzay_zaman,
          ayni_fail_cikarimi}] — benzerliğe göre azalan.
    """
    def kelime_kumesi(s):
        """Metni küçük harfli kelime kümesine çevirir (iç yardımcı)."""
        return set(str(s or "").lower().split())

    girdiler = []
    for k in kayitlar:
        kume = kelime_kumesi(k.get(mo_alan))
        if kume:
            girdiler.append((k.get("id"), kume, koordinat_al(k), _tarih_gunu(k.get("tarih"))))
    n = len(girdiler)
    df = Counter(t for _, kume, _, _ in girdiler for t in kume)
    idf = {t: math.log(n / d) for t, d in df.items()}

    sonuc = []
    for (id1, a, k1, t1), (id2, b, k2, t2) in combinations(girdiler, 2):
        birlesim = sum(idf[t] for t in a | b)
        if birlesim <= 0:
            continue
        agirlikli = sum(idf[t] for t in a & b) / birlesim
        if agirlikli < benzerlik_esik:
            continue
        if str(id1) > str(id2):   # çift içi sıra girdi sırasına bağlı olmasın
            id1, id2 = id2, id1
        cift = {"id1": id1, "id2": id2, "benzerlik": round(agirlikli, 3),
                "jaccard": round(len(a & b) / len(a | b), 3),
                "mesafe_km": None, "gun_farki": None,
                "uzay_zaman": "bilinmiyor", "ayni_fail_cikarimi": False}
        if k1 and k2 and t1 is not None and t2 is not None:
            mesafe = haversine_km(k1[0], k1[1], k2[0], k2[1])
            fark = abs(t1 - t2)
            if mesafe > mesafe_km or fark > gun:
                continue
            cift.update({"mesafe_km": round(mesafe, 3), "gun_farki": fark,
                         "uzay_zaman": "yakin"})
        sonuc.append(cift)
    sonuc.sort(key=lambda x: (-x["benzerlik"], str(x["id1"]), str(x["id2"])))
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
