# -*- coding: utf-8 -*-
"""
mekan.py — Mekânsal analiz: mesafe, grid hotspot, KDE ısı yoğunluğu,
en yakın komşu indeksi (NNI), hotspot hücre çıkarımı.
Sadece standart kütüphane (math). Harita kütüphanesi GEREKMEZ;
çıktılar (lat, lon, deger) demetleri olarak döner, istenen CBS'ye aktarılır.
"""

import math
import random
from .kaynak_butce import _pozitif, _grid_butce, MAKS_GRID
from .hatalar import KullanimHatasi

R_DUNYA_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    """İki koordinat arası büyük daire mesafesi (km)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_DUNYA_KM * math.asin(math.sqrt(a))


def sinir_kutusu(noktalar):
    """[(lat, lon), ...] için (min_lat, min_lon, max_lat, max_lon)."""
    latlar = [p[0] for p in noktalar]
    lonlar = [p[1] for p in noktalar]
    return (min(latlar), min(lonlar), max(latlar), max(lonlar))


def grid_hotspot(noktalar, hucre_km=0.5):
    """
    Noktaları kare grid hücrelerine böler, hücre başına olay sayısı verir.
    Args: hucre_km (km) — hücre kenar uzunluğu.
    Dönüş: [{'lat': merkez_lat, 'lon': merkez_lon, 'adet': n}, ...]
    """
    _pozitif(hucre_km, 'hucre_km')
    # Seyrek grid: yalnız dolu hücreler tutulur; hücre sayısı en fazla n.
    if len(noktalar) > MAKS_GRID:
        raise KullanimHatasi('grid: dolu hücre üst sınırı bütçeyi aşıyor')
    if not noktalar:
        return []
    min_lat, min_lon, _, _ = sinir_kutusu(noktalar)
    # 1 derece enlem ~110.574 km; boylam enleme bağlı
    d_lat = hucre_km / 110.574
    ort_lat = math.radians(sum(p[0] for p in noktalar) / len(noktalar))
    d_lon = hucre_km / (111.320 * math.cos(ort_lat) or 1e-9)
    hücreler = {}
    for lat, lon in noktalar:
        i = int((lat - min_lat) / d_lat) if d_lat > 0 else 0
        j = int((lon - min_lon) / d_lon) if d_lon > 0 else 0
        anahtar = (i, j)
        hücreler[anahtar] = hücreler.get(anahtar, 0) + 1
    sonuc = []
    for (i, j), adet in hücreler.items():
        sonuc.append({
            "lat": min_lat + (i + 0.5) * d_lat,
            "lon": min_lon + (j + 0.5) * d_lon,
            "adet": adet,
        })
    sonuc.sort(key=lambda h: -h["adet"])
    return sonuc


def _kde_butce(noktalar, bant_km, hucre_km):
    """KDE'nin gerçek grid boyutlarıyla tavanı pahalı döngüden önce denetler."""
    _pozitif(bant_km, 'bant_km')
    _pozitif(hucre_km, 'hucre_km')
    if not math.isfinite(bant_km * bant_km) or bant_km * bant_km == 0 or hucre_km / 110.574 == 0:
        raise KullanimHatasi('bant_km/hucre_km: temsil edilebilir ölçek gerekli')
    if not noktalar:
        return None
    min_lat, min_lon, max_lat, max_lon = sinir_kutusu(noktalar)
    d_lat = hucre_km / 110.574
    ort_lat = math.radians(sum(p[0] for p in noktalar) / len(noktalar))
    km_lon = 111.320 * math.cos(ort_lat) or 1e-9
    d_lon = hucre_km / km_lon
    try:
        n_i = int((max_lat - min_lat) / d_lat) + 2
        n_j = int((max_lon - min_lon) / d_lon) + 2
    except (ValueError, OverflowError, ZeroDivisionError):
        raise KullanimHatasi('KDE: temsil edilebilir grid boyutu gerekli') from None
    _grid_butce(len(noktalar), n_i, n_j)
    return min_lat, min_lon, d_lat, d_lon, km_lon, n_i, n_j


def kde_yogunluk(noktalar, bant_km=0.3, hucre_km=0.25, agirliklar=None):
    """
    Gauss çekirdekli KDE (Kernel Density Estimation) — saf Python.
    Args: bant_km (km) — çekirdek bant genişliği; hucre_km (km) — çıktı
    grid çözünürlüğü.
    agirliklar verilirse (noktalarla aynı uzunlukta) zarar-ağırlıklı KDE
    yapılır (harm-spot; CHI Bölüm 13 mantığı).
    Dönüş: [{'lat':..., 'lon':..., 'yogunluk':...}, ...] (azalan sıralı)
    """
    grid = _kde_butce(noktalar, bant_km, hucre_km)
    if not noktalar:
        return []
    if agirliklar is None:
        agirliklar = [1.0] * len(noktalar)
    min_lat, min_lon, d_lat, d_lon, km_lon, n_i, n_j = grid
    h2 = bant_km ** 2
    sonuc = []
    for i in range(n_i):
        lat = min_lat + (i + 0.5) * d_lat
        for j in range(n_j):
            lon = min_lon + (j + 0.5) * d_lon
            toplam = 0.0
            for (p_lat, p_lon), w in zip(noktalar, agirliklar):
                dy = (p_lat - lat) * 110.574
                dx = (p_lon - lon) * km_lon
                d2 = dx * dx + dy * dy
                if d2 <= 9 * h2:  # 3*bant ötesi katkı ihmal edilir
                    toplam += w * math.exp(-d2 / (2 * h2))
            if toplam > 0:
                sonuc.append({"lat": round(lat, 6), "lon": round(lon, 6),
                              "yogunluk": round(toplam, 4)})
    sonuc.sort(key=lambda h: -h["yogunluk"])
    return sonuc


def en_yakin_komsu_mesafeleri(noktalar):
    """
    Her nokta için en yakın komşuya km mesafe listesi.
    v6.4 (Faz G): n > 64 ise grid indeksi + genişleyen halka araması;
    nihai mesafeler haversine_km ile hesaplanır — sonuç kaba kuvvetle
    BİREBİR aynı, süre O(n²) yerine ~O(n) (ölçüm: 22.3s → ~1s).
    """
    n = len(noktalar)
    if n < 2:
        return [0.0] * n
    if n <= 64:
        sonuc = []
        for i in range(n):
            en_kucuk = None
            for j in range(n):
                if i == j:
                    continue
                d = haversine_km(noktalar[i][0], noktalar[i][1],
                                 noktalar[j][0], noktalar[j][1])
                if en_kucuk is None or d < en_kucuk:
                    en_kucuk = d
            if en_kucuk is not None:
                sonuc.append(en_kucuk)
        return sonuc
    # grid yolu: hücre ~ ortalama aralığın 2 katı
    min_lat = min(p[0] for p in noktalar)
    max_lat = max(p[0] for p in noktalar)
    min_lon = min(p[1] for p in noktalar)
    max_lon = max(p[1] for p in noktalar)
    ort_lat = math.radians((min_lat + max_lat) / 2)
    boy = max((max_lat - min_lat) * 110.574, 1e-9)
    en = max((max_lon - min_lon) * 111.320 * math.cos(ort_lat), 1e-9)
    hucre = max(2 * math.sqrt((en * boy) / n), 1e-6)
    grid, xs, ys = _grid_kur(noktalar, hucre)
    sonuc = []
    for i in range(n):
        ci, cj = int(xs[i] // hucre), int(ys[i] // hucre)
        en_kucuk, r = None, 0
        # halka r işlendikten sonra dış hücreler >= r*hucre uzakta; durma
        # koşulu: en_kucuk <= r*hucre (bir sonraki turun başında denetlenir)
        while en_kucuk is None or en_kucuk > (r - 1) * hucre:
            for di in range(-r, r + 1):
                for dj in range(-r, r + 1):
                    if max(abs(di), abs(dj)) != r:
                        continue
                    if _hucre_min_km(xs, ys, i, hucre,
                                     ci + di, cj + dj) > (en_kucuk
                                                          if en_kucuk
                                                          is not None
                                                          else math.inf):
                        continue
                    for j in grid.get((ci + di, cj + dj), []):
                        if j == i:
                            continue
                        d = haversine_km(noktalar[i][0], noktalar[i][1],
                                         noktalar[j][0], noktalar[j][1])
                        if en_kucuk is None or d < en_kucuk:
                            en_kucuk = d
            r += 1
            if r * hucre > math.hypot(en, boy) and en_kucuk is None:
                break  # ıssız nokta: tam tarama
        if en_kucuk is None:  # ıssız nokta güvenliği
            for j in range(n):
                if j == i:
                    continue
                d = haversine_km(noktalar[i][0], noktalar[i][1],
                                 noktalar[j][0], noktalar[j][1])
                if en_kucuk is None or d < en_kucuk:
                    en_kucuk = d
        sonuc.append(en_kucuk)
    return sonuc


def nni(noktalar, alan_km2=None):
    """
    En Yakın Komşu İndeksi (Nearest Neighbor Index).
    NNI < 1: kümelenme, ~1: rastgele, > 1: düzgün dağılım.
    alan_km2 verilmezse sınır kutusu alanı kullanılır.
    """
    n = len(noktalar)
    if n < 2:
        return None
    if alan_km2 is None:
        min_lat, min_lon, max_lat, max_lon = sinir_kutusu(noktalar)
        ort_lat = math.radians((min_lat + max_lat) / 2)
        y = (max_lat - min_lat) * 110.574
        x = (max_lon - min_lon) * 111.320 * math.cos(ort_lat)
        alan_km2 = max(x * y, 1e-9)
    mesafeler = en_yakin_komsu_mesafeleri(noktalar)
    gozlenen = sum(mesafeler) / len(mesafeler)
    beklenen = 0.5 / math.sqrt(n / alan_km2)
    return round(gozlenen / beklenen, 4) if beklenen > 0 else None


def hotspot_hucreler(grid_sonuc, ust_yuzdelik=80):
    """Grid çıktısından üst yüzdelik dilimdeki hotspot hücrelerini seçer."""
    if not grid_sonuc:
        return []
    adetler = sorted(h["adet"] for h in grid_sonuc)
    k = (len(adetler) - 1) * ust_yuzdelik / 100.0
    esik = adetler[int(round(k))]
    return [h for h in grid_sonuc if h["adet"] >= esik]


def koruma_alani(noktalar, merkez, yaricap_km):
    """Merkez (lat, lon) çevresinde yaricap_km içindeki noktaları döner."""
    return [p for p in noktalar
            if haversine_km(p[0], p[1], merkez[0], merkez[1]) <= yaricap_km]


def nni_test(noktalar, alan_km2=None, kenar_duzeltme=True, cevre_km=None):
    """
    NNI + z-istatistiği (Faz 3.3): kümelenmeyi test edilebilir hale getirir.
    SE = 0.26136 / sqrt(n^2 / A); z = (d_göz - d_bek) / SE.
    Args: alan_km2 (km²) — çalışma alanı; cevre_km (km) — kenar düzeltmesi
    için alan çevresi.

    v6.3 (Faz E3): kenar_duzeltme=True ise Donnelly (1978) kenar
    düzeltmesi uygulanır — sınıra yakın noktaların en yakın komşusu
    çalışma alanı dışında kalabileceği için düzeltilmemiş test kümelenme
    yönünde önyargılıdır:
      d_bek' = 0.5/sqrt(n/A) + (0.0514 + 0.041/sqrt(n)) * (P/n)
      Var    = 0.07*A/n^2 + 0.037*P*sqrt(A/n^5)
    cevre_km verilmezse sınır kutusu çevresi kullanılır.

    A4.15: kenar düzeltmesi VARSAYILAN (düzeltmesiz test rastgele desende %21,
    n=50'de %40 sahte "düzgün dağılım" iddia ediyordu — BMK v8). Alan/çevre
    noktaların sınır kutusundan tahmin edilirken kutu kenarları (n+1)/(n-1) ile
    büyütülür: n tekdüze noktanın aralığı gerçek aralığı beklenen (n-1)/(n+1)
    oranında küçümser (yansız aralık tahmini).
    Dönüş: {'nni', 'z', 'p', 'yorum', 'kenar_duzeltme', 'beklenen'}
    """
    n = len(noktalar)
    if n < 2:
        return None
    min_lat, min_lon, max_lat, max_lon = sinir_kutusu(noktalar)
    ort_lat = math.radians((min_lat + max_lat) / 2)
    yansiz = (n + 1) / (n - 1)   # tekdüze aralığın yansız tahmini
    boy = (max_lat - min_lat) * 110.574 * yansiz
    en = (max_lon - min_lon) * 111.320 * math.cos(ort_lat) * yansiz
    if alan_km2 is None:
        alan_km2 = max(en * boy, 1e-9)
    if cevre_km is None:
        cevre_km = 2 * (en + boy)
    mesafeler = en_yakin_komsu_mesafeleri(noktalar)
    gozlenen = sum(mesafeler) / len(mesafeler)
    beklenen = 0.5 / math.sqrt(n / alan_km2)
    se = 0.26136 / math.sqrt(n * n / alan_km2)
    if kenar_duzeltme and cevre_km > 0:
        beklenen = beklenen + (0.0514 + 0.041 / math.sqrt(n)) * (cevre_km / n)
        varyans = 0.07 * alan_km2 / (n * n) + \
            0.037 * cevre_km * math.sqrt(alan_km2 / n ** 5)
        se = math.sqrt(varyans) if varyans > 0 else se
    z = (gozlenen - beklenen) / se if se > 0 else 0.0
    p_degeri = 2 * (1 - (1 + math.erf(abs(z) / math.sqrt(2))) / 2)
    deger = round(gozlenen / beklenen, 4) if beklenen > 0 else None
    if deger is None:
        return None
    if p_degeri < 0.05 and deger < 1:
        yorum = "istatistiksel olarak anlamlı kümelenme"
    elif p_degeri < 0.05 and deger > 1:
        yorum = "istatistiksel olarak anlamlı düzgün dağılım"
    else:
        yorum = "rastgelelikten ayırt edilemiyor"
    return {"nni": deger, "z": round(z, 3), "p": round(p_degeri, 5),
            "yorum": yorum, "kenar_duzeltme": bool(kenar_duzeltme),
            "beklenen": round(beklenen, 6)}


def koordinat_maskele(lat, lon, yaricap_m=200, seed=None):
    """
    KVKK yayın maskesi: noktayı yaricap_m içinde rastgele kaydırır (jitter).
    seed verilirse (veya verilmezse koordinat çifti tohum olur) aynı girdi
    hep aynı maskeli noktayı üretir — tekrar üretilebilir yayın.
    """
    tohum = seed if seed is not None else f"{lat:.6f},{lon:.6f}"
    rng = random.Random(tohum)
    aci = rng.uniform(0, 2 * math.pi)
    mesafe = rng.uniform(0, yaricap_m) / 1000.0  # km
    d_lat = mesafe * math.cos(aci) / 110.574
    d_lon = mesafe * math.sin(aci) / (111.320 * math.cos(math.radians(lat)) or 1e-9)
    return (round(lat + d_lat, 6), round(lon + d_lon, 6))


# ---------------- mekânsal grid indeksi (Faz G, v6.4 — ölçülen darboğaz) ----------------
# Ölçüm: 5000 noktada en_yakin_komsu 22.3s, çift sayımı 5.9s (O(n²)).
# Grid yalnız ADAY budaması yapar; nihai mesafeler her zaman haversine_km
# ile hesaplanır → sonuçlar kaba kuvvetle BİREBİR aynıdır (doğruluk testi:
# tests/test_faz_g.py).

def _grid_kur(noktalar, hucre_km):
    """
    (lat, lon) noktalarını km uzayında hücrelere indisler.
    Dönüş: (grid, xs, ys) — grid: {(ci, cj): [idx]}, xs/ys: km koordinatları.
    """
    from collections import defaultdict
    ort_lat = math.radians(sum(p[0] for p in noktalar) / len(noktalar))
    kx = 111.320 * math.cos(ort_lat)
    xs = [p[1] * kx for p in noktalar]
    ys = [p[0] * 110.574 for p in noktalar]
    grid = defaultdict(list)
    for i in range(len(noktalar)):
        grid[(int(xs[i] // hucre_km), int(ys[i] // hucre_km))].append(i)
    return grid, xs, ys


def _hucre_min_km(xs, ys, i, hucre_km, ci, cj):
    """Nokta i'den (ci,cj) hücresine olası EN KÜÇÜK mesafe (muhafazakâr)."""
    di = abs(int(xs[i] // hucre_km) - ci)
    dj = abs(int(ys[i] // hucre_km) - cj)
    dx = max(0, di - 1) * hucre_km
    dy = max(0, dj - 1) * hucre_km
    return math.hypot(dx, dy)


def yakin_ciftler_hizli(noktalar, esik_km):
    """
    esik_km içindeki TÜM nokta çiftleri: grid budamalı, kaba kuvvetle
    birebir. Dönüş: [(i, j, mesafe_km)] (i < j).
    """
    n = len(noktalar)
    if esik_km <= 0 or n < 2:
        return []
    hucre = esik_km
    grid, xs, ys = _grid_kur(noktalar, hucre)
    sonuc = []
    for i in range(n):
        ci, cj = int(xs[i] // hucre), int(ys[i] // hucre)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for j in grid.get((ci + di, cj + dj), []):
                    if j <= i:
                        continue
                    d = haversine_km(noktalar[i][0], noktalar[i][1],
                                     noktalar[j][0], noktalar[j][1])
                    if d <= esik_km:
                        sonuc.append((i, j, d))
    return sonuc
