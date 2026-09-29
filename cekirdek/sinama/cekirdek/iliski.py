# -*- coding: utf-8 -*-
"""
iliski.py — İlişki ölçüleri ve çıkarımsal istatistik
(Maxfield & Babbie, Bölüm 14: rates, association measures, chi square;
Bölüm 6: suç oranları).
Nominal: lambda + Cramér V | Ordinal: gamma | Aralık: Pearson r.
"""

import math
import statistics
from collections import Counter


# --- Suç oranları (Ch 6/14: computing rates) ---

def suc_orani(olay_sayisi, nufus, birim=100000):
    """100.000 kişi başına suç oranı (UCR standardı)."""
    if not nufus:
        return None
    return round(olay_sayisi / nufus * birim, 2)


def oran_tablosu(veri):
    """
    veri: [{'bolge':..., 'olay':..., 'nufus':...}, ...]
    Her bölge için oran hesaplar, azalan sıralar.
    """
    sonuc = []
    for v in veri:
        ga = oran_guven_araligi(v.get("olay", 0), v.get("nufus", 0))
        if ga is not None:
            sonuc.append({"bolge": v.get("bolge"),
                          "oran_100binde": ga["oran"],
                          "ga_alt": ga["alt"], "ga_ust": ga["ust"],
                          "uyari": ga["uyari"],
                          "olay": v.get("olay"), "nufus": v.get("nufus")})
    sonuc.sort(key=lambda x: -x["oran_100binde"])
    return sonuc


def ham_oran_karsilastir(veri, birim=100000):
    """Ham sayı vs nüfusa-oranlı sıralama ayrışması (karar ağacı R12): kalabalık
    bölge doğal olarak yüksek SAYILIDIR ama yüksek ORANLI olmayabilir. İki
    sıralama arasındaki farkı gösterir.

    veri: [{bolge, olay, nufus}]. Nüfus eksik/sıfır olan bölge oran dışıdır.
    Returns: {bolgeler:[{bolge, olay, nufus, oran, sira_sayim, sira_oran,
    sapma}], ayrisma:[en çok sapan], not}.
    """
    gecerli = [v for v in veri if v.get("nufus")]
    if len(gecerli) < 2:
        return {"hata": "oran karşılaştırması için ≥2 nüfuslu bölge gerekir",
                "not": "nüfus (payda) olmadan yalnız ham sayı yorumlanır (R12)"}
    for v in gecerli:
        v["_oran"] = suc_orani(v.get("olay", 0), v["nufus"], birim)
    sayim_sirali = sorted(gecerli, key=lambda v: -v.get("olay", 0))
    oran_sirali = sorted(gecerli, key=lambda v: -(v["_oran"] or 0))
    sira_sayim = {id(v): i + 1 for i, v in enumerate(sayim_sirali)}
    sira_oran = {id(v): i + 1 for i, v in enumerate(oran_sirali)}
    bolgeler = []
    for v in gecerli:
        ss, so = sira_sayim[id(v)], sira_oran[id(v)]
        bolgeler.append({"bolge": v.get("bolge"), "olay": v.get("olay"),
                         "nufus": v["nufus"], "oran_100binde": v["_oran"],
                         "sira_sayim": ss, "sira_oran": so, "sapma": ss - so})
    bolgeler.sort(key=lambda b: -b["sapma"])  # + = orana göre yüksek, sayıda düşük
    ayrisma = [b for b in bolgeler if abs(b["sapma"]) >= 2][:10]
    return {"bolgeler": sorted(bolgeler, key=lambda b: -b["oran_100binde"]),
            "ayrisma": ayrisma,
            "not": ("sapma>0: orana göre yüksek ama ham sayıda düşük (GERÇEKTEN "
                    "riskli, sayı bakılırsa gözden kaçar); sapma<0: sayıda yüksek "
                    "ama orana göre düşük (nüfus şişirmesi). Ham sayı haritası "
                    "yanıltıcı olabilir (R12).")}


# --- Ki-kare (Ch 14: chi square) ---

def _gammaincc(a, x):
    """Regularized upper incomplete gamma Q(a,x) — saf Python."""
    if x <= 0:
        return 1.0
    if x < a + 1.0:  # seri açılımı (P hesapla, Q = 1-P)
        toplam, terim = 1.0 / a, 1.0 / a
        for n in range(1, 300):
            terim *= x / (a + n)
            toplam += terim
            if abs(terim) < abs(toplam) * 1e-12:
                break
        return max(0.0, 1.0 - toplam * math.exp(-x + a * math.log(x) - math.lgamma(a)))
    # sürekli kesir açılımı
    b = x + 1.0 - a
    c, d = 1e30, 1.0 / b
    h = d
    for i in range(1, 300):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        dh = d * c
        h *= dh
        if abs(dh - 1.0) < 1e-12:
            break
    return max(0.0, min(1.0, math.exp(-x + a * math.log(x) - math.lgamma(a)) * h))


def ki_kare(tablo, yates=False):
    """
    Bağımsızlık ki-kare testi (Ch 14).
    tablo: [[gözlenen...], ...] satır listesi.
    yates=True: 2x2 tablolarda Yates süreklilik düzeltmesi uygular.
    Dönüş: {'ki_kare', 'df', 'p_degeri', 'cramer_v', 'beklenen', 'uyarilar'}
    Sıfır hipotezi: iki değişken arasında ilişki yok.
    """
    R, C = len(tablo), len(tablo[0])
    satir_t = [sum(s) for s in tablo]
    sutun_t = [sum(tablo[i][j] for i in range(R)) for j in range(C)]
    N = sum(satir_t)
    if N == 0 or R < 2 or C < 2:
        return None
    beklenen = [[satir_t[i] * sutun_t[j] / N for j in range(C)] for i in range(R)]
    x2 = 0.0
    yates_aktif = yates and R == 2 and C == 2
    for i in range(R):
        for j in range(C):
            e = beklenen[i][j]
            if e > 0:
                fark = abs(tablo[i][j] - e)
                if yates_aktif:
                    fark = max(0.0, fark - 0.5)
                x2 += fark ** 2 / e
    df = (R - 1) * (C - 1)
    p = _gammaincc(df / 2.0, x2 / 2.0)
    v = math.sqrt(x2 / (N * min(R - 1, C - 1)))
    # Cochran kuralı: beklenen hücrelerin >%20'si <5 ise test güvenilmez
    kucuk = sum(1 for satir in beklenen for e in satir if e < 5)
    uyarilar = []
    if kucuk > 0:
        oran_k = kucuk / (R * C)
        if oran_k > 0.2 or any(e < 1 for satir in beklenen for e in satir):
            uyarilar.append(
                f"Cochran kuralı ihlali: {kucuk} hücrede beklenen <5; "
                "p-değeri güvenilmez, kategori birleştirme önerilir")
    if N > 1000:
        uyarilar.append("büyük örneklem: ki-kare kolay anlamlı çıkar; "
                        "etki büyüklüğü için Cramér V'yi esas alın")
    return {"ki_kare": round(x2, 4), "df": df, "p_degeri": round(p, 5),
            "cramer_v": round(v, 4), "yates": yates_aktif,
            "uyarilar": uyarilar,
            "beklenen": [[round(e, 2) for e in satir] for satir in beklenen]}


def capraz_ki_kare(kayitlar, alan_a, alan_b):
    """Kayıtlardan çapraz tablo kurup ki-kare uygular."""
    a_vals = sorted({str(k.get(alan_a)) for k in kayitlar})
    b_vals = sorted({str(k.get(alan_b)) for k in kayitlar})
    a_idx = {v: i for i, v in enumerate(a_vals)}
    b_idx = {v: j for j, v in enumerate(b_vals)}
    tablo = [[0] * len(b_vals) for _ in a_vals]
    for k in kayitlar:
        tablo[a_idx[str(k.get(alan_a))]][b_idx[str(k.get(alan_b))]] += 1
    sonuc = ki_kare(tablo)
    if sonuc:
        sonuc["satirlar"] = a_vals
        sonuc["sutunlar"] = b_vals
    return sonuc


# --- İlişki ölçüleri (Ch 14: measures of association) ---

def lambda_(kayitlar, bagimsiz, bagimli):
    """
    Nominal değişkenler için lambda (PRE: tahmin hatasında azalma oranı).
    bagimsiz bilgisiyle bagimli değişkeni tahmin etmede iyileşme.
    """
    if not kayitlar:
        return None
    toplam = len(kayitlar)
    mod_genel = Counter(str(k.get(bagimli)) for k in kayitlar).most_common(1)[0][1]
    hata1 = toplam - mod_genel
    hata2 = 0
    gruplar = {}
    for k in kayitlar:
        gruplar.setdefault(str(k.get(bagimsiz)), []).append(str(k.get(bagimli)))
    for g, degerler in gruplar.items():
        hata2 += len(degerler) - Counter(degerler).most_common(1)[0][1]
    if hata1 == 0:
        return 0.0
    return round((hata1 - hata2) / hata1, 4)


def gamma_(ikili):
    """
    Ordinal ilişki için gamma. ikili: [(x, y), ...] sıralanabilir çiftler.
    Uyumlu (concordant) vs uyumsuz (discordant) çift sayımı.
    """
    nc = nd = 0
    n = len(ikili)
    for i in range(n):
        for j in range(i + 1, n):
            dx = (ikili[i][0] > ikili[j][0]) - (ikili[i][0] < ikili[j][0])
            dy = (ikili[i][1] > ikili[j][1]) - (ikili[i][1] < ikili[j][1])
            p = dx * dy
            if p > 0:
                nc += 1
            elif p < 0:
                nd += 1
    if nc + nd == 0:
        return None
    return round((nc - nd) / (nc + nd), 4)


def pearson_r(xs, ys):
    """Pearson r ve r^2 (aralık/oran değişkenleri)."""
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    r = sxy / math.sqrt(sxx * syy)
    return {"r": round(r, 4), "r_kare": round(r ** 2, 4), "n": n}


# --- Faz 3.3: Oranlar için Poisson exact güven aralığı ---

def _ki_kare_kuantil(p, df):
    """Ki-kare dağılımının p-kuantili (alt kuyruk) — bisection ile ters çevirme."""
    if p <= 0:
        return 0.0
    if p >= 1:
        return float("inf")
    lo, hi = 0.0, max(10.0, df * 4)
    while 1.0 - _gammaincc(df / 2.0, hi / 2.0) < p:
        hi *= 2
        if hi > 1e9:
            break
    for _ in range(200):
        mid = (lo + hi) / 2
        cdf = 1.0 - _gammaincc(df / 2.0, mid / 2.0)
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def oran_guven_araligi(olay, nufus, guven=0.95, birim=100000):
    """
    Suç oranı için Poisson exact güven aralığı (Garwood).
    Küçük nüfuslu bölgelerde ham oran gürültülüdür; GA olmadan
    'yüksek suç bölgesi' çıkarımı yapılmamalıdır.
    Dönüş: {'oran', 'alt', 'ust', 'guven', 'olay', 'nufus', 'uyari'}
    """
    if not nufus or olay < 0:
        return None
    alfa = 1 - guven
    if olay == 0:
        alt_olay = 0.0
    else:
        alt_olay = 0.5 * _ki_kare_kuantil(alfa / 2, 2 * olay)
    ust_olay = 0.5 * _ki_kare_kuantil(1 - alfa / 2, 2 * (olay + 1))
    carpan = birim / nufus
    uyari = None
    if olay < 20:
        uyari = ("az olay sayısı: güven aralığı geniş, oranı tek başına "
                 "yorumlamayın")
    return {"oran": round(olay * carpan, 2), "alt": round(alt_olay * carpan, 2),
            "ust": round(ust_olay * carpan, 2), "guven": guven,
            "olay": olay, "nufus": nufus, "uyari": uyari}


def _beta_kuantil(q, a, b):
    """Beta dağılımının q-kuantili — _betainc üzerinde biseksiyon (Faz E2)."""
    from .hipotez import _betainc
    if q <= 0:
        return 0.0
    if q >= 1:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(64):
        ort = (lo + hi) / 2
        if _betainc(ort, a, b) < q:
            lo = ort
        else:
            hi = ort
    return (lo + hi) / 2


def iki_poisson_orani(k1, e1, k2, e2, guven=0.95):
    """
    İki Poisson oranının koşullu EXACT karşılaştırması (v6.3, Faz E2).
    Ör: bölge A vs B, öncesi/sonrası, müdahale/kontrol.

    Koşullu test (Krishnamoorthy & Thomson 2004): toplam olay koşulunda
    k1 ~ Binomial(n=k1+k2, p0=e1/(e1+e2)); iki yönlü exact p.
    Oran oranı (RR) için exact GA: p'nin Clopper-Pearson sınırlarından
    dönüşüm — RR_ga = (p_ga/(1-p_ga)) * (e2/e1).

    Dönüş: {oran1, oran2, oran_orani, ga_alt, ga_ust, p, n, yorum}
    """
    from .hipotez import binomial_test
    if e1 <= 0 or e2 <= 0:
        return None
    n = k1 + k2
    if n == 0:
        return {"hata": "iki grupta da olay yok; test anlamsız"}
    p0 = e1 / (e1 + e2)
    p_degeri = binomial_test(k1, n, p0)["p"]
    alfa = 1 - guven
    if k1 == 0:
        p_lo = 0.0
    else:
        p_lo = _beta_kuantil(alfa / 2, k1, n - k1 + 1)
    if k1 == n:
        p_hi = 1.0
    else:
        p_hi = _beta_kuantil(1 - alfa / 2, k1 + 1, n - k1)
    oran1, oran2 = k1 / e1, k2 / e2
    rr = oran1 / oran2 if oran2 > 0 else None
    carpan = e2 / e1
    ga_alt = (p_lo / (1 - p_lo)) * carpan if p_lo < 1 else None
    ga_ust = (p_hi / (1 - p_hi)) * carpan if p_hi < 1 else None
    anlamli = ga_alt is not None and ga_ust is not None and \
        (ga_alt > 1 or ga_ust < 1)
    return {"oran1": round(oran1, 4), "oran2": round(oran2, 4),
            "oran_orani": round(rr, 4) if rr is not None else None,
            "ga_alt": round(ga_alt, 4) if ga_alt is not None else None,
            "ga_ust": round(ga_ust, 4) if ga_ust is not None else None,
            "p": p_degeri, "n": n, "guven": guven,
            "yorum": ("oran farkı anlamlı (GA 1'i dışarıda)"
                      if anlamli else "oran farkı anlamlı değil"),
            "yontem": "koşullu exact (binomial) + Clopper-Pearson RR GA"}
