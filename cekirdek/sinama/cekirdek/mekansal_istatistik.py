# -*- coding: utf-8 -*-
"""
mekansal_istatistik.py — mekânsal otokorelasyon ve sıcak nokta istatistikleri
(saf stdlib). 2024-2026 suç analizi literatürünün çekirdek yöntemleri:

- Global Moran's I: olay dağılımı kümeli mi, dağınık mı, rastgele mi?
  (Tobler'in 1. yasası — "yakın şeyler daha ilişkilidir"in sınanabilir hâli)
- Getis-Ord Gi*: hücre bazında İSTATİSTİKSEL OLARAK ANLAMLI sıcak/soğuk nokta
  (grid_hotspot yalnız sayım verir; Gi* "bu yoğunluk şans eseri mi?" der).
- Eşitlik endeksi (Gini + bölgesel eşitsizlik): 2025-2026 adalet-kısıtlı
  kaynak dağıtımı temasının ölçüm tarafı — devriye/kaynak ne kadar dengeli?

Girdi grid hücreleridir: [{'lat', 'lon', 'adet'}] (grid_hotspot çıktısı).
Komşuluk mesafe-bantlı ikili ağırlıkla tanımlanır; bant verilmezse her hücrenin
en az bir komşusu olacak en küçük eşik otomatik seçilir (standart uygulama).
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional

from . import mekan
from . import regresyon
from .ileri import fdr_benjamini_hochberg


def _normal_p_iki_yonlu(z: float) -> float:
    """|z| için iki yönlü normal p-değeri (math.erf; ek bağımlılık yok)."""
    return round(2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))), 5)


def _guven_bandi(z: float) -> Optional[str]:
    """Getis-Ord/z eşikleri: %90/95/99 (literatürdeki standart yorum)."""
    a = abs(z)
    if a >= 2.58:
        return "%99"
    if a >= 1.96:
        return "%95"
    if a >= 1.65:
        return "%90"
    return None


def _komsuluk(hucreler: List[Dict[str, Any]], bant_km: Optional[float]):
    """Mesafe-bantlı ikili komşuluk: komsu[i] = i'ye bant_km içindeki j'ler.
    bant_km None ise, her hücrenin ≥1 komşusu olacak en küçük eşik seçilir.
    Dönüş: (komsu_listesi, kullanilan_bant_km).
    """
    n = len(hucreler)
    # Tüm ikili haversine mesafeleri (n küçük tutulur; çağrı yeri sınırlar)
    mesafe = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = mekan.haversine_km(hucreler[i]["lat"], hucreler[i]["lon"],
                                   hucreler[j]["lat"], hucreler[j]["lon"])
            mesafe[i][j] = mesafe[j][i] = d
    if bant_km is None:
        # her hücrenin en yakın komşusuna uzaklığı; en büyüğü = min eşik
        en_yakinlar = []
        for i in range(n):
            digerleri = [mesafe[i][j] for j in range(n) if j != i]
            if digerleri:
                en_yakinlar.append(min(digerleri))
        bant_km = max(en_yakinlar) if en_yakinlar else 1.0
        bant_km = round(bant_km * 1.0001, 6)  # sınır dahil kalsın
    komsu = [[j for j in range(n) if j != i and mesafe[i][j] <= bant_km]
             for i in range(n)]
    return komsu, bant_km


def global_moran(hucreler: List[Dict[str, Any]], bant_km: Optional[float] = None,
                 deger_alan: str = "adet") -> Dict[str, Any]:
    """Global Moran's I: mekânsal otokorelasyon + normal-varsayım z/p.

    I>0 kümelenme, I<0 dağılma (satranç), I≈E[I] rastgele. E[I]=-1/(n-1).
    Args: hucreler (grid hücreleri), bant_km (komşuluk eşiği; None=otomatik).
    Returns: {I, beklenen, z, p, yorum, n, bant_km, kullanilan_deger}.
    """
    n = len(hucreler)
    if n < 3:
        return {"hata": "Moran's I için en az 3 hücre gerekir", "n": n}
    x = [float(h.get(deger_alan, 0) or 0) for h in hucreler]
    ort = sum(x) / n
    sapma = [xi - ort for xi in x]
    payda = sum(s * s for s in sapma)
    if payda == 0:
        return {"hata": "tüm hücre değerleri eşit; otokorelasyon tanımsız", "n": n}

    komsu, bant = _komsuluk(hucreler, bant_km)
    S0 = sum(len(komsu[i]) for i in range(n))  # ikili ağırlık toplamı
    if S0 == 0:
        return {"hata": "komşuluk bulunamadı; bant_km artırın", "n": n, "bant_km": bant}

    pay = 0.0
    for i in range(n):
        for j in komsu[i]:
            pay += sapma[i] * sapma[j]
    I = (n / S0) * (pay / payda)
    beklenen = -1.0 / (n - 1)

    # Normal-varsayım varyansı: Var = (n^2 S1 - n S2 + 3 S0^2)/((n^2-1)S0^2) - E^2
    # İkili simetrik ağırlıkta: S1 = 2*S0; S2 = 4*Σ k_i^2
    S1 = 2.0 * S0
    S2 = 4.0 * sum(len(komsu[i]) ** 2 for i in range(n))
    var = ((n * n * S1 - n * S2 + 3 * S0 * S0) /
           ((n * n - 1) * S0 * S0)) - beklenen * beklenen
    z = (I - beklenen) / math.sqrt(var) if var > 0 else 0.0
    p = _normal_p_iki_yonlu(z)

    if p < 0.05 and I > beklenen:
        yorum = "anlamlı KÜMELENME (yakın hücreler benzer yoğunlukta)"
    elif p < 0.05 and I < beklenen:
        yorum = "anlamlı DAĞILMA (satranç deseni)"
    else:
        yorum = "rastgele dağılımdan ayırt edilemez"

    return {"I": round(I, 5), "beklenen": round(beklenen, 5),
            "z": round(z, 4), "p": p, "yorum": yorum,
            "n": n, "bant_km": round(bant, 4), "kullanilan_deger": deger_alan}


GI_FDR_Q = 0.05


def gi_siniflandir(z_degerleri: List[float], q_esik: float = GI_FDR_Q) -> Dict[str, Any]:
    """Gi* z-skorlarını ÇOKLU TEST DÜZELTMELİ sınıflandırır (A4, BMK K1.6).

    Her hücre ayrı bir testtir; n hücrede düzeltmesiz %95 eşiği rastgele
    desende bile ~%5·n hücreyi "anlamlı" işaretler (BMK v0: tamamen rastgele
    desenlerin %70'inde en az bir sahte "sıcak nokta"). Karar iki yönlü
    p = erfc(|z|/√2) üzerinden Benjamini–Hochberg q-değerleriyle verilir
    (ArcGIS'in Gi* için FDR seçeneğiyle aynı ilke).

    Args:
        z_degerleri: hücre sırasıyla Gi* z-skorları.
        q_esik: yanlış keşif oranı eşiği (varsayılan 0,05).

    Returns:
        {"p": [...], "q": [...], "tur": ["sıcak"|"soğuk"|"anlamsız", ...]}
    """
    p = [math.erfc(abs(z) / math.sqrt(2.0)) for z in z_degerleri]
    q = fdr_benjamini_hochberg(p)
    tur = [("sıcak" if z > 0 else "soğuk") if qi <= q_esik and z != 0 else "anlamsız"
           for z, qi in zip(z_degerleri, q)]
    return {"p": p, "q": q, "tur": tur}


def getis_ord(hucreler: List[Dict[str, Any]], bant_km: Optional[float] = None,
              deger_alan: str = "adet", q_esik: float = GI_FDR_Q) -> Dict[str, Any]:
    """Getis-Ord Gi*: hücre bazında sıcak/soğuk nokta, çoklu test düzeltmeli.

    Gi* kendini de komşu sayar (yıldız). z>0 sıcak (yüksek değer kümesi),
    z<0 soğuk. KARAR ('tur') Benjamini–Hochberg FDR ile verilir
    (gi_siniflandir). 'guven' düzeltmesiz z bandıdır (|z|≥1.65 %90, ≥1.96 %95,
    ≥2.58 %99) — literatürle karşılaştırma için bilgi amaçlıdır, tek başına
    karar için KULLANILMAZ.
    Returns: {sonuclar:[{lat,lon,adet,gi_z,p,q,guven,tur}], sicak, soguk,
              coklu_test, n, bant_km}.
    """
    n = len(hucreler)
    if n < 3:
        return {"hata": "Gi* için en az 3 hücre gerekir", "n": n}
    x = [float(h.get(deger_alan, 0) or 0) for h in hucreler]
    X = sum(x) / n
    S = math.sqrt(max(sum(xi * xi for xi in x) / n - X * X, 0.0))
    if S == 0:
        return {"hata": "tüm hücre değerleri eşit; Gi* tanımsız", "n": n}

    komsu, bant = _komsuluk(hucreler, bant_km)
    zler = []
    for i in range(n):
        yildiz = komsu[i] + [i]  # kendini dahil et
        w = len(yildiz)
        lag = sum(x[j] for j in yildiz)
        payda = S * math.sqrt(max((n * w - w * w) / (n - 1), 1e-12))
        zler.append((lag - X * w) / payda if payda > 0 else 0.0)
    karar = gi_siniflandir(zler, q_esik)
    sonuclar = []
    for i, gi in enumerate(zler):
        sonuclar.append({"lat": round(hucreler[i]["lat"], 6),
                         "lon": round(hucreler[i]["lon"], 6),
                         "adet": hucreler[i].get(deger_alan),
                         "gi_z": round(gi, 4),
                         "p": round(karar["p"][i], 6), "q": karar["q"][i],
                         "guven": _guven_bandi(gi), "tur": karar["tur"][i]})
    sonuclar.sort(key=lambda s: -s["gi_z"])
    sicak = karar["tur"].count("sıcak")
    soguk = karar["tur"].count("soğuk")
    duz_sicak = sum(1 for z in zler if z > 0 and _guven_bandi(z))
    duz_soguk = sum(1 for z in zler if z < 0 and _guven_bandi(z))
    return {"sonuclar": sonuclar, "sicak": sicak, "soguk": soguk,
            "coklu_test": {"yontem": "Benjamini-Hochberg FDR", "q_esik": q_esik,
                           "test_sayisi": n,
                           "duzeltmesiz_sicak": duz_sicak,
                           "duzeltmesiz_soguk": duz_soguk},
            "n": n, "bant_km": round(bant, 4),
            "not": ("Gi* z-skoru olay YOĞUNLUĞUNU test eder; kayıt yoğunluğu "
                    "gerçek suç yoğunluğundan sapabilir (raporlama yanlılığı). "
                    "'tur' çoklu test düzeltmelidir (FDR); 'guven' düzeltmesiz "
                    "z bandıdır ve tek başına karar için kullanılmaz.")}


def yerel_moran(hucreler: List[Dict[str, Any]], bant_km: Optional[float] = None,
                deger_alan: str = "adet", permutasyon: int = 999,
                seed: int = 42) -> Dict[str, Any]:
    """Local Moran's I (LISA, Anselin 1995): sıcak/soğuk kümeyi mekânsal
    AYKIRI DEĞERDEN ayırır. Getis-Ord "nerede yüksek" der; LISA ayrıca
    "yüksek ama çevresi düşük" (aykırı) hücreleri işaretler.

    Kümeleme türleri (yalnız anlamlı hücrelerde):
      HH yüksek-yüksek (sıcak küme), LL düşük-düşük (soğuk küme),
      HL yüksek-düşük (aykırı: yüksek ada), LH düşük-yüksek (aykırı: düşük ada).
    Anlamlılık koşullu permütasyonla (GeoDa/PySAL yöntemi); seed sabit →
    determinist (golden test dostu).
    Returns: {sonuclar:[{lat,lon,adet,Ii,p,kumeleme}], ozet:{...}, n, bant_km}.
    """
    n = len(hucreler)
    if n < 3:
        return {"hata": "Local Moran için en az 3 hücre gerekir", "n": n}
    x = [float(h.get(deger_alan, 0) or 0) for h in hucreler]
    ort = sum(x) / n
    sapma = [xi - ort for xi in x]
    m2 = sum(s * s for s in sapma) / n
    if m2 == 0:
        return {"hata": "tüm hücre değerleri eşit; LISA tanımsız", "n": n}

    komsu, bant = _komsuluk(hucreler, bant_km)
    rng = random.Random(seed)
    sonuclar = []
    ozet = {"HH": 0, "LL": 0, "HL": 0, "LH": 0, "anlamsız": 0, "izole": 0}
    for i in range(n):
        k = len(komsu[i])
        if k == 0:
            sonuclar.append({"lat": round(hucreler[i]["lat"], 6),
                             "lon": round(hucreler[i]["lon"], 6),
                             "adet": hucreler[i].get(deger_alan),
                             "Ii": 0.0, "p": None, "kumeleme": "izole"})
            ozet["izole"] += 1
            continue
        # satır-standart ağırlık (komşu ortalaması): lag = Σ w_ij sapma_j
        lag = sum(sapma[j] for j in komsu[i]) / k
        Ii = (sapma[i] / m2) * lag
        # koşullu permütasyon: x_i sabit, çevredeki k değeri havuzdan çek
        havuz = [sapma[j] for j in range(n) if j != i]
        asiri = 0
        for _ in range(permutasyon):
            ornek = rng.sample(havuz, k)
            Ii_sim = (sapma[i] / m2) * (sum(ornek) / k)
            if abs(Ii_sim) >= abs(Ii):
                asiri += 1
        p = round((asiri + 1) / (permutasyon + 1), 4)
        if p < 0.05:
            if sapma[i] > 0 and lag > 0:
                kume = "HH"
            elif sapma[i] < 0 and lag < 0:
                kume = "LL"
            elif sapma[i] > 0 and lag < 0:
                kume = "HL"
            else:
                kume = "LH"
        else:
            kume = "anlamsız"
        ozet[kume] += 1
        sonuclar.append({"lat": round(hucreler[i]["lat"], 6),
                         "lon": round(hucreler[i]["lon"], 6),
                         "adet": hucreler[i].get(deger_alan),
                         "Ii": round(Ii, 4), "p": p, "kumeleme": kume})
    sonuclar.sort(key=lambda s: (s["kumeleme"] == "anlamsız", -(s["Ii"] or 0)))
    return {"sonuclar": sonuclar, "ozet": ozet, "n": n,
            "bant_km": round(bant, 4),
            "not": ("HL/LH mekânsal aykırı değerdir (çevresinden farklı ada); "
                    "HH/LL kümedir. Anlamlılık koşullu permütasyonla (seed sabit).")}


def merkezsel(noktalar: List[tuple], agirliklar: Optional[List[float]] = None) -> Dict[str, Any]:
    """Sentrografik istatistik (Chainey Böl.2): ortalama merkez + standart
    mesafe + standart sapma elipsi. Suçun "ağırlık merkezini" ve yayılım
    yönünü özetler; dönemler arası merkez kayması eğilim izlemede kullanılır.

    Args: noktalar [(lat, lon), ...]; agirliklar (opsiyonel, ör. zarar/olay
    yoğunluğu → ağırlıklı merkez). Sapma/elips yerel km düzleminde (şehir
    ölçeğinde geçerli equirectangular yaklaşım).
    Returns: {ortalama_merkez{lat,lon}, standart_mesafe_km,
              elips{aci_derece, buyuk_eksen_km, kucuk_eksen_km, yon_orani}, n}.
    """
    n = len(noktalar)
    if n < 3:
        return {"hata": "sentrografik ölçüm için en az 3 nokta gerekir", "n": n}
    if agirliklar is None:
        agirliklar = [1.0] * n
    if len(agirliklar) != n:
        return {"hata": "ağırlık sayısı nokta sayısıyla eşleşmiyor"}
    w_top = sum(agirliklar)
    if w_top <= 0:
        return {"hata": "ağırlık toplamı sıfır/negatif"}

    # (ağırlıklı) ortalama merkez
    lat0 = sum(agirliklar[i] * noktalar[i][0] for i in range(n)) / w_top
    lon0 = sum(agirliklar[i] * noktalar[i][1] for i in range(n)) / w_top

    # yerel km sapmaları (equirectangular): dy=kuzey, dx=doğu
    cos_lat = math.cos(math.radians(lat0)) or 1e-9
    dx = [(noktalar[i][1] - lon0) * 111.320 * cos_lat for i in range(n)]
    dy = [(noktalar[i][0] - lat0) * 110.574 for i in range(n)]

    # standart mesafe (ağırlıklı): SD = sqrt(Σ w(dx²+dy²) / Σw)
    sd = math.sqrt(sum(agirliklar[i] * (dx[i] ** 2 + dy[i] ** 2)
                       for i in range(n)) / w_top)

    # standart sapma elipsi (Yuill formülü, ağırlıklı)
    sxx = sum(agirliklar[i] * dx[i] ** 2 for i in range(n))
    syy = sum(agirliklar[i] * dy[i] ** 2 for i in range(n))
    sxy = sum(agirliklar[i] * dx[i] * dy[i] for i in range(n))
    A = sxx - syy
    B = math.sqrt(A * A + 4 * sxy * sxy)
    if abs(sxy) < 1e-12:
        theta = 0.0 if A >= 0 else math.pi / 2  # eksene hizalı
    else:
        theta = math.atan((A + B) / (2 * sxy))
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    sig_x = math.sqrt(2.0 * sum(agirliklar[i] * (dx[i] * cos_t - dy[i] * sin_t) ** 2
                                for i in range(n)) / w_top)
    sig_y = math.sqrt(2.0 * sum(agirliklar[i] * (dx[i] * sin_t + dy[i] * cos_t) ** 2
                                for i in range(n)) / w_top)
    buyuk, kucuk = max(sig_x, sig_y), min(sig_x, sig_y)
    # yön: kuzeyden saat yönünde derece (coğrafi konvansiyon); büyük eksen ekseni
    theta_buyuk = theta if sig_x >= sig_y else theta + math.pi / 2
    aci = (90.0 - math.degrees(theta_buyuk)) % 180.0

    return {"ortalama_merkez": {"lat": round(lat0, 6), "lon": round(lon0, 6)},
            "standart_mesafe_km": round(sd, 4),
            "elips": {"aci_derece": round(aci, 1),
                      "buyuk_eksen_km": round(buyuk, 4),
                      "kucuk_eksen_km": round(kucuk, 4),
                      "yon_orani": round(buyuk / kucuk, 3) if kucuk > 1e-6 else None},
            "n": n, "agirlikli": any(w != 1.0 for w in agirliklar),
            "not": ("aci_derece: büyük eksenin kuzeyden saat yönü açısı (yayılım "
                    "yönü); yon_orani 1'e yakınsa dağılım daireseldir/yönsüz.")}


def risk_arazi(faktor_noktalari: List[tuple], hucre_km: float = 0.3,
               yaricap_km: float = 0.4) -> Dict[str, Any]:
    """Risk Terrain Modeling (Chainey Böl.9, Caplan & Kennedy): çevresel risk
    faktörlerinden KALICI risk yüzeyi. Suç geçmişinden bağımsız — bir yerin
    koşulları suça ne kadar elverişli? Birden çok risk faktörü türünün bir
    arada bulunduğu (co-location) hücreler en yüksek risklidir.

    Args: faktor_noktalari [(lat, lon, tur)] — risk faktörleri ve türleri
    (ör. bar, ATM, otogar); hucre_km (ızgara), yaricap_km (etki yarıçapı).
    Hücre riski = yarıçap içindeki FARKLI faktör türü sayısı.
    Returns: {sonuclar:[{lat,lon,risk,turler}], maks_risk, faktor_turleri, n}.
    """
    n = len(faktor_noktalari)
    if n < 2:
        return {"hata": "RTM için en az 2 risk faktörü gerekir", "n": n}
    lats = [p[0] for p in faktor_noktalari]
    lons = [p[1] for p in faktor_noktalari]
    turler = sorted({str(p[2]) for p in faktor_noktalari})

    d_lat = hucre_km / 110.574
    ort_lat = math.radians(sum(lats) / n)
    d_lon = hucre_km / ((111.320 * math.cos(ort_lat)) or 1e-9)
    pay = yaricap_km
    pay_lat = pay / 110.574
    pay_lon = pay / ((111.320 * math.cos(ort_lat)) or 1e-9)
    min_lat, max_lat = min(lats) - pay_lat, max(lats) + pay_lat
    min_lon, max_lon = min(lons) - pay_lon, max(lons) + pay_lon
    ni = int((max_lat - min_lat) / d_lat) + 1 if d_lat > 0 else 1
    nj = int((max_lon - min_lon) / d_lon) + 1 if d_lon > 0 else 1
    if ni * nj > 20000:
        return {"hata": "ızgara çok büyük; hucre_km artırın", "hucre": ni * nj}

    sonuclar = []
    maks = 0
    for a in range(ni):
        clat = min_lat + (a + 0.5) * d_lat
        for b in range(nj):
            clon = min_lon + (b + 0.5) * d_lon
            yakin_turler = set()
            for k in range(n):
                if mekan.haversine_km(clat, clon, lats[k], lons[k]) <= yaricap_km:
                    yakin_turler.add(str(faktor_noktalari[k][2]))
            if yakin_turler:
                sonuclar.append({"lat": round(clat, 6), "lon": round(clon, 6),
                                 "risk": len(yakin_turler),
                                 "turler": sorted(yakin_turler)})
                maks = max(maks, len(yakin_turler))
    sonuclar.sort(key=lambda s: -s["risk"])
    return {"sonuclar": sonuclar[:100], "maks_risk": maks,
            "faktor_turleri": turler, "n_faktor": n,
            "not": ("risk = hücre yakınındaki farklı risk faktörü türü sayısı; "
                    "yüksek risk = çok türün bir arada olduğu KALICI risk "
                    "bölgesi (suç geçmişinden bağımsız, önleyici hedefleme).")}


def mekansal_regresyon_tani(y: List[float], X: List[List[float]],
                            koordinatlar: List[tuple],
                            adlar: Optional[List[str]] = None,
                            bant_km: Optional[float] = None) -> Dict[str, Any]:
    """Mekânsal regresyon TANISI (Chainey Böl.8): OLS çalıştırır, sonra
    ARTIKLARI mekânsal otokorelasyon için Moran's I ile sınar. Artıklar
    mekânsal kümeliyse OLS varsayımı (bağımsız artıklar) çiğnenmiştir →
    katsayı/standart hata YANLIDIR, mekânsal regresyon (lag/error) gerekir.

    Tam ML mekânsal regresyon yerine bu SAĞLAM tanıyı sunar (kitabın pratik
    çekirdek iş akışı). Args: y (bağımlı), X (bağımsız satırlar), koordinatlar
    [(lat,lon)] (bölge merkezleri), adlar (değişken adları), bant_km (km,
    artık komşuluk eşiği; boş=otomatik).
    Returns: {ols{r_kare, katsayilar...}, artik_moran{I,z,p}, karar}.
    """
    n = len(y)
    if n < 5 or len(X) != n or len(koordinatlar) != n:
        return {"hata": "y, X ve koordinat sayıları eşit ve n≥5 olmalı", "n": n}
    ols = regresyon.coklu_ols(X, y, adlar)
    if ols is None or "hata" in ols:
        return {"hata": (ols or {}).get("hata", "OLS başarısız"), "n": n}
    artik = ols["artik"]
    hucreler = [{"lat": koordinatlar[i][0], "lon": koordinatlar[i][1],
                 "adet": artik[i]} for i in range(n)]
    moran = global_moran(hucreler, bant_km)
    if "hata" in moran:
        return {"ols_r_kare": ols["r_kare"], "artik_moran": moran,
                "karar": "artık otokorelasyonu hesaplanamadı", "n": n}
    if moran["p"] < 0.05 and moran["I"] > moran["beklenen"]:
        karar = ("ARTIKLAR MEKÂNSAL KÜMELİ → OLS yanlı; mekânsal regresyon "
                 "(spatial lag/error) önerilir. Katsayı anlamlılıklarına "
                 "olduğu gibi güvenmeyin.")
    else:
        karar = "artıklar mekânsal bağımsız → OLS bu veride geçerli"
    return {"ols": {"r_kare": ols["r_kare"],
                    "duzeltilmis_r_kare": ols["duzeltilmis_r_kare"],
                    "katsayilar": ols["katsayilar"], "p_F": ols.get("p_F")},
            "artik_moran": {"I": moran["I"], "z": moran["z"], "p": moran["p"],
                            "bant_km": moran["bant_km"]},
            "karar": karar, "n": n}


def cografi_profil(suc_noktalari: List[tuple], hucre_km: float = 0.3,
                   decay_km: Optional[float] = None,
                   buffer_km: float = 0.0) -> Dict[str, Any]:
    """Coğrafi profilleme olasılık yüzeyi (Chainey Böl.7): seri bir suç
    dizisinden failin olası çapa (ikamet) bölgesini tahmin eder. Her grid
    hücresine tüm suçlardan mesafe-azalımı katkısı toplanır.

    Model: negatif üstel azalım (Dragnet) f(d)=exp(-d/decay). buffer_km>0 ise
    Rossmo tampon bölgesi eklenir (fail suç işlediği yerin çok yakınında
    oturmaz → yüzey halka biçimini alır): f(d)*=(1-exp(-d/buffer)).

    Args: suc_noktalari [(lat,lon)]; hucre_km (km, ızgara hücre kenarı);
    decay_km (km, azalım ölçeği; boş=suçlar-arası ortalama mesafeden);
    buffer_km (km, Rossmo tampon; 0=Dragnet).
    Returns: {tepe{lat,lon,skor}, yuzey:[{lat,lon,skor}], n_suc}.
    """
    n = len(suc_noktalari)
    if n < 2:
        return {"hata": "coğrafi profil için en az 2 suç noktası gerekir", "n_suc": n}
    lats = [p[0] for p in suc_noktalari]
    lons = [p[1] for p in suc_noktalari]

    if decay_km is None:
        # suçlar-arası ortalama mesafe (ölçek); sıfırsa güvenli varsayılan
        d_top, c = 0.0, 0
        for i in range(n):
            for j in range(i + 1, n):
                d_top += mekan.haversine_km(lats[i], lons[i], lats[j], lons[j])
                c += 1
        decay_km = (d_top / c) if c and d_top > 0 else 1.0
    decay_km = max(decay_km, 1e-6)

    # çalışma alanı: suçların sınır kutusu + kenar payı
    pay = max(decay_km, hucre_km * 2)
    d_lat = hucre_km / 110.574
    ort_lat = math.radians(sum(lats) / n)
    d_lon = hucre_km / ((111.320 * math.cos(ort_lat)) or 1e-9)
    pay_lat = pay / 110.574
    pay_lon = pay / ((111.320 * math.cos(ort_lat)) or 1e-9)
    min_lat, max_lat = min(lats) - pay_lat, max(lats) + pay_lat
    min_lon, max_lon = min(lons) - pay_lon, max(lons) + pay_lon
    ni = int((max_lat - min_lat) / d_lat) + 1 if d_lat > 0 else 1
    nj = int((max_lon - min_lon) / d_lon) + 1 if d_lon > 0 else 1
    # ızgara patlamasını engelle (quadratic_guard çağrı yerinde de var)
    if ni * nj > 20000:
        return {"hata": "ızgara çok büyük; hucre_km artırın", "hucre": ni * nj}

    yuzey = []
    tepe = None
    for a in range(ni):
        clat = min_lat + (a + 0.5) * d_lat
        for b in range(nj):
            clon = min_lon + (b + 0.5) * d_lon
            skor = 0.0
            for k in range(n):
                d = mekan.haversine_km(clat, clon, lats[k], lons[k])
                f = math.exp(-d / decay_km)
                if buffer_km > 0:
                    f *= (1.0 - math.exp(-d / buffer_km))
                skor += f
            yuzey.append((clat, clon, skor))
            if tepe is None or skor > tepe[2]:
                tepe = (clat, clon, skor)

    maks = tepe[2] or 1.0
    yuzey.sort(key=lambda c: -c[2])
    ust = [{"lat": round(c[0], 6), "lon": round(c[1], 6),
            "skor": round(c[2] / maks, 4)} for c in yuzey[:100]]
    return {"tepe": {"lat": round(tepe[0], 6), "lon": round(tepe[1], 6),
                     "skor": 1.0},
            "yuzey": ust, "n_suc": n,
            "decay_km": round(decay_km, 4), "buffer_km": buffer_km,
            "not": ("tepe = en olası çapa (ikamet) bölgesi; yüzey normalize "
                    "(0-1). Tampon>0 ise Rossmo halka modeli. Yalnız araştırma "
                    "amaçlı — tek başına şüpheli belirlemez.")}


def _mann_kendall(seri: List[float]) -> Dict[str, Any]:
    """Mann-Kendall monotonik trend testi (stdlib). Dönüş: {S, tau, z, p, yon}."""
    n = len(seri)
    if n < 3:
        return {"S": 0, "tau": 0.0, "z": 0.0, "p": 1.0, "yon": "belirsiz"}
    S = 0
    for i in range(n):
        for j in range(i + 1, n):
            d = seri[j] - seri[i]
            S += (d > 0) - (d < 0)
    var = n * (n - 1) * (2 * n + 5) / 18.0
    if S > 0:
        z = (S - 1) / math.sqrt(var) if var > 0 else 0.0
    elif S < 0:
        z = (S + 1) / math.sqrt(var) if var > 0 else 0.0
    else:
        z = 0.0
    p = _normal_p_iki_yonlu(z)
    tau = S / (0.5 * n * (n - 1)) if n > 1 else 0.0
    if p < 0.10 and S > 0:
        yon = "artan"
    elif p < 0.10 and S < 0:
        yon = "azalan"
    else:
        yon = "durağan"
    return {"S": S, "tau": round(tau, 4), "z": round(z, 4), "p": p, "yon": yon}


def emerging_hotspot(seriler: Dict[str, List[float]],
                     sicak_yuzdelik: float = 90.0) -> Dict[str, Any]:
    """Emerging Hotspot Analysis (Chainey Böl.6): her bölgenin zaman serisini
    Mann-Kendall trendi + sıcaklık durumuna göre sınıflar. Kalıcı/yoğunlaşan/
    yeni/sönen/tarihsel/sporadik ayrımı yapar (ESRI EHSA sadeleştirmesi).

    Args: seriler {bölge: [dönem0_sayı, dönem1_sayı, ...]}; tüm seriler eşit
    uzunlukta olmalı. sicak_yuzdelik: bir dönemde "sıcak" sayılma eşiği
    (bölgeler arası yüzdelik).
    Returns: {sonuclar:[{bolge, kategori, tau, trend_p, son, ilk}], ozet, n_donem}.
    """
    if not seriler:
        return {"hata": "seri yok"}
    uzunluklar = {len(s) for s in seriler.values()}
    if len(uzunluklar) != 1:
        return {"hata": "tüm bölge serileri eşit uzunlukta olmalı"}
    T = uzunluklar.pop()
    if T < 3:
        return {"hata": "en az 3 dönem gerekir", "n_donem": T}

    # her dönem için bölgeler-arası sıcaklık eşiği (yüzdelik)
    def _yuzdelik(degerler, y):
        d = sorted(degerler)
        if not d:
            return 0.0
        k = (len(d) - 1) * y / 100.0
        alt = int(k)
        return d[alt] + (k - alt) * (d[min(alt + 1, len(d) - 1)] - d[alt])

    esikler = [_yuzdelik([s[t] for s in seriler.values()], sicak_yuzdelik)
               for t in range(T)]
    yari = max(1, T // 2)

    sonuclar = []
    ozet: Dict[str, int] = {}
    for bolge, seri in seriler.items():
        mk = _mann_kendall(seri)
        sicak_donem = [seri[t] >= esikler[t] and seri[t] > 0 for t in range(T)]
        sicak_oran = sum(sicak_donem) / T
        ilk_sicak = any(sicak_donem[:yari])
        son_sicak = any(sicak_donem[T - yari:])
        if son_sicak and mk["yon"] == "artan" and not ilk_sicak:
            kat = "yeni sıcak nokta"
        elif son_sicak and mk["yon"] == "artan":
            kat = "yoğunlaşan"
        elif son_sicak and mk["yon"] == "azalan":
            kat = "sönen"
        elif son_sicak and ilk_sicak:
            kat = "kalıcı"
        elif ilk_sicak and not son_sicak:
            kat = "tarihsel"
        elif sicak_oran > 0 and 0.0 < sicak_oran < 0.5:
            kat = "sporadik"
        else:
            kat = "sıcak değil"
        ozet[kat] = ozet.get(kat, 0) + 1
        sonuclar.append({"bolge": bolge, "kategori": kat,
                         "tau": mk["tau"], "trend_p": mk["p"],
                         "son": seri[-1], "ilk": seri[0]})
    sira = {"yeni sıcak nokta": 0, "yoğunlaşan": 1, "kalıcı": 2, "sönen": 3,
            "tarihsel": 4, "sporadik": 5, "sıcak değil": 6}
    sonuclar.sort(key=lambda s: (sira.get(s["kategori"], 9), -s["son"]))
    return {"sonuclar": sonuclar, "ozet": ozet, "n_donem": T,
            "not": ("kategori zaman serisi trendine (Mann-Kendall) + sıcaklık "
                    "durumuna dayanır; 'yeni sıcak nokta' ve 'yoğunlaşan' "
                    "öncelikli müdahale adaylarıdır.")}


def konsantrasyon_dagilim(once: List[float], sonra: List[float]) -> Dict[str, Any]:
    """Crime Concentration Dispersion (Chainey Böl.6): suç ARTIŞI eski sıcak
    noktalardan mı (yoğunlaşma) yoksa yeni alanlardan mı (dağılma) geliyor?
    Bölge yoğunlaşmasını (Gini) önce/sonra karşılaştırır.

    Args: once/sonra — bölge başına olay sayıları (AYNI sıralı bölgeler).
    Returns: {toplam_degisim, gini_once, gini_sonra, yorum}.
    """
    if len(once) != len(sonra) or len(once) < 2:
        return {"hata": "önce/sonra eşit uzunlukta ve ≥2 bölge olmalı"}
    g_o = esitlik(once).get("gini")
    g_s = esitlik(sonra).get("gini")
    top_o, top_s = sum(once), sum(sonra)
    degisim = top_s - top_o
    if g_o is None or g_s is None:
        return {"hata": "Gini hesaplanamadı"}
    if degisim <= 0:
        yon = "artış yok; dağılım analizi artış dönemleri için anlamlıdır"
    elif g_s > g_o + 0.02:
        yon = "YOĞUNLAŞMA: artış mevcut sıcak noktalarda (hotspot'lar ısındı)"
    elif g_s < g_o - 0.02:
        yon = "DAĞILMA: artış yeni alanlara yayıldı (yeni sıcak noktalar)"
    else:
        yon = "artış mevcut yoğunlaşma desenini korudu"
    return {"toplam_degisim": degisim, "gini_once": round(g_o, 4),
            "gini_sonra": round(g_s, 4), "yorum": yon}


def esitlik(degerler: List[float]) -> Dict[str, Any]:
    """Kaynak/olay dağılımının eşitsizliği: Gini + bölgesel eşitsizlik ölçüleri.

    2025-2026 adalet-kısıtlı kaynak dağıtımı temasının ölçüm tarafı. Gini 0=tam
    eşit, 1=tam yoğunlaşmış. MRD (min bölgesel disparite) = (maks-min)/ortalama.
    Args: degerler (bölge başına sayı/kaynak listesi).
    Returns: {gini, mrd, ust_pay_yuzde, n, yorum}.
    """
    d = sorted(float(v) for v in degerler if v is not None)
    n = len(d)
    if n == 0:
        return {"hata": "değer yok"}
    toplam = sum(d)
    if toplam == 0:
        return {"gini": 0.0, "mrd": 0.0, "ust_pay_yuzde": 0.0, "n": n,
                "yorum": "tüm bölgeler sıfır"}
    # Gini (sıralı formül): G = (2*Σ i*d_i)/(n*Σ d_i) - (n+1)/n
    kumulatif = sum((i + 1) * d[i] for i in range(n))
    gini = (2.0 * kumulatif) / (n * toplam) - (n + 1.0) / n
    ort = toplam / n
    mrd = (d[-1] - d[0]) / ort if ort > 0 else 0.0
    # üst %20 bölgenin toplam paydaki yüzdesi (yoğunlaşma göstergesi)
    ust_k = max(1, n // 5)
    ust_pay = sum(d[-ust_k:]) / toplam * 100.0
    if gini >= 0.6:
        yorum = "yüksek yoğunlaşma (az bölgede çok yük)"
    elif gini >= 0.4:
        yorum = "orta düzey eşitsizlik"
    else:
        yorum = "görece dengeli dağılım"
    return {"gini": round(gini, 4), "mrd": round(mrd, 4),
            "ust_pay_yuzde": round(ust_pay, 2), "n": n, "yorum": yorum}
