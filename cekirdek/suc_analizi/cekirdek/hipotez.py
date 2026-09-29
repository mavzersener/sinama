# -*- coding: utf-8 -*-
"""
hipotez.py — Hipotez testleri ve güç analizi
(Weisburd & Britt, Statistics in Criminal Justice 4. baskı temelli).
Dağılım altyapısı saf Python: regularized incomplete beta üzerinden
t ve F CDF; Acklam yaklaşımıyla ters normal (PPF).
"""

import math
import statistics
from collections import Counter
from .iliski import _gammaincc
from .kaynak_butce import _sim_butce


# ---------------- dağılım altyapısı ----------------

def _betacf(a, b, x):
    """Incomplete beta için sürekli kesir (Numerical Recipes)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        dh = d * c
        h *= dh
        if abs(dh - 1.0) < 3e-14:
            break
    return h


def _betainc(x, a, b):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t, df):
    """t dağılımı CDF: P(T <= t)."""
    x = df / (df + t * t)
    ib = _betainc(x, df / 2.0, 0.5)
    return 1.0 - 0.5 * ib if t > 0 else 0.5 * ib


def f_cdf(f, d1, d2):
    """F dağılımı CDF."""
    if f <= 0:
        return 0.0
    return _betainc(d1 * f / (d1 * f + d2), d1 / 2.0, d2 / 2.0)


def norm_cdf(z):
    """Standart normal dağılım fonksiyonu Φ(z) = P(Z ≤ z), erf yaklaşımı.
    Args: z (standart puan). Returns: 0-1 arası olasılık.
    """
    return (1 + math.erf(z / math.sqrt(2))) / 2


def norm_ppf(p):
    """Ters normal CDF (Acklam rasyonel yaklaşımı, |hata|<1.15e-9)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p <= 0:
        return -float("inf")
    if p >= 1:
        return float("inf")
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _iki_yonlu_t_p(t, df):
    return round(min(1.0, 2 * (1 - t_cdf(abs(t), df))), 5)


def _s(degerler):
    return statistics.stdev(degerler) if len(degerler) > 1 else 0.0


# ---------------- P0: t-testleri ----------------

def t_test_tek(ornek, mu0):
    """Tek örneklem t-testi: ortalama = mu0 mı?"""
    n = len(ornek)
    if n < 2:
        return None
    xbar, s = statistics.fmean(ornek), _s(ornek)
    t = (xbar - mu0) / (s / math.sqrt(n) or 1e-9)
    df = n - 1
    return {"t": round(t, 4), "df": df, "p": _iki_yonlu_t_p(t, df),
            "ortalama": round(xbar, 3), "mu0": mu0}


def t_test_bagimsiz(x, y, welch=False):
    """
    Bağımsız iki örneklem t-testi. welch=True ise eşit varyans varsayılmaz
    (suç verisinde genelde daha güvenli seçim).
    """
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    vx, vy = _s(x) ** 2, _s(y) ** 2
    if welch:
        se = math.sqrt(vx / nx + vy / ny)
        df = (vx / nx + vy / ny) ** 2 / \
             ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    else:
        sp2 = ((nx - 1) * vx + (ny - 1) * vy) / (nx + ny - 2)
        se = math.sqrt(sp2 * (1 / nx + 1 / ny))
        df = nx + ny - 2
    t = (mx - my) / (se or 1e-9)
    return {"t": round(t, 4), "df": round(df, 2), "p": _iki_yonlu_t_p(t, df),
            "ortalama_x": round(mx, 3), "ortalama_y": round(my, 3),
            "welch": welch}


def t_test_bagimli(x, y):
    """Bağımlı (eşleşmiş) örneklem t-testi — öncesi/sonrası aynı birimler."""
    if len(x) != len(y) or len(x) < 2:
        return None
    farklar = [a - b for a, b in zip(x, y)]
    return t_test_tek(farklar, 0.0)


# ---------------- P0: oran testleri ----------------

def iki_oran_testi(x1, n1, x2, n2):
    """
    İki oran karşılaştırması (pooled z) + fark için %95 GA.
    x: başarı sayısı, n: örneklem büyüklüğü.
    """
    if not all([n1, n2]):
        return None
    p1, p2 = x1 / n1, x2 / n2
    pp = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2)) or 1e-9
    z = (p1 - p2) / se
    se_ga = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    fark = p1 - p2
    return {"p1": round(p1, 4), "p2": round(p2, 4), "z": round(z, 4),
            "p": round(min(1.0, 2 * (1 - norm_cdf(abs(z)))), 5),
            "fark_ga": [round(fark - 1.96 * se_ga, 4),
                        round(fark + 1.96 * se_ga, 4)]}


def binomial_test(x, n, p0):
    """Binomial exact test (Ch 6): gözlenen sayım p0 ile uyumlu mu?"""
    def pmf(k):
        """Binom olasılık kütle fonksiyonu C(n,k)·p^k·(1-p)^(n-k) (iç yardımcı).
        """
        return math.comb(n, k) * p0 ** k * (1 - p0) ** (n - k)
    p_obs = pmf(x)
    p_degeri = sum(pmf(k) for k in range(n + 1) if pmf(k) <= p_obs + 1e-12)
    return {"x": x, "n": n, "p0": p0, "p": round(min(1.0, p_degeri), 5)}


def fisher_exact(a, b, c, d):
    """
    Fisher exact testi (2x2). Cochran ihlalinde ki-kare yerine kullanılır.
    İki yönlü p: gözlenenden küçük-eşit olasılıklı tüm tabloların toplamı.
    """
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def hipergeo(x):
        """Hipergeometrik olasılık kütle fonksiyonu (Fisher exact; iç yardımcı).
        """
        return (math.comb(r1, x) * math.comb(n - r1, c1 - x)) / math.comb(n, c1)

    lo = max(0, c1 - (n - r1))
    hi = min(r1, c1)
    p_obs = hipergeo(a)
    p_degeri = sum(hipergeo(x) for x in range(lo, hi + 1)
                   if hipergeo(x) <= p_obs + 1e-12)
    alt_kuyruk = sum(hipergeo(x) for x in range(lo, a + 1))
    ust_kuyruk = sum(hipergeo(x) for x in range(a, hi + 1))
    return {"tablo": [[a, b], [c, d]], "p": round(min(1.0, p_degeri), 5),
            "tek_yonlu_alt": round(min(1.0, alt_kuyruk), 5),
            "tek_yonlu_ust": round(min(1.0, ust_kuyruk), 5)}


# ---------------- P0: nonparametrik + ordinal ilişki ----------------

def _siralama(degerler):
    """Ortalama sıralar (tie'larla)."""
    sirali = sorted(enumerate(degerler), key=lambda x: x[1])
    sira = [0.0] * len(degerler)
    i = 0
    while i < len(sirali):
        j = i
        while j + 1 < len(sirali) and sirali[j + 1][1] == sirali[i][1]:
            j += 1
        ort = (i + j) / 2 + 1
        for k in range(i, j + 1):
            sira[sirali[k][0]] = ort
        i = j + 1
    return sira


def mann_whitney(x, y):
    """
    Mann-Whitney U (bağımsız, nonparametrik). p: tie düzeltmeli normal
    yaklaşım; küçük örneklemde (n<20) p'yi yaklaşık kabul edin.
    """
    nx, ny = len(x), len(y)
    birlesik = list(x) + list(y)
    sira = _siralama(birlesik)
    rx = sum(sira[:nx])
    ux = nx * ny + nx * (nx + 1) / 2 - rx
    uy = nx * ny - ux
    u = min(ux, uy)  # konvansiyon: küçük U raporlanır
    mu = nx * ny / 2
    tie = Counter(birlesik)
    tie_duzeltme = sum(t ** 3 - t for t in tie.values())
    n = nx + ny
    varyans = nx * ny / 12 * ((n + 1) - tie_duzeltme / (n * (n - 1)))
    sd = math.sqrt(varyans) or 1e-9
    z = (u - mu) / sd  # D2: ölü satır temizlendi (üzerine yazılan eski z)
    return {"U": round(u, 1), "z": round(z, 4),
            "p": round(min(1.0, 2 * (1 - norm_cdf(abs(z)))), 5),
            "not": "n<20 ise p yaklaşıktır" if min(nx, ny) < 20 else None}


def spearman(x, y):
    """Spearman rank korelasyonu + t yaklaşımı p-değeri."""
    n = len(x)
    if n < 3:
        return None
    rx, ry = _siralama(x), _siralama(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    rho = sxy / math.sqrt(sxx * syy)
    t = rho * math.sqrt((n - 2) / max(1e-9, 1 - rho ** 2))
    return {"rho": round(rho, 4), "t": round(t, 4), "df": n - 2,
            "p": _iki_yonlu_t_p(t, n - 2)}


def kendall_tau(x, y):
    """Kendall tau-b (tie düzeltmeli ordinal ilişki)."""
    n = len(x)
    nc = nd = 0
    tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = (x[i] > x[j]) - (x[i] < x[j])
            dy = (y[i] > y[j]) - (y[i] < y[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
                continue
            if dy == 0:
                ty += 1
                continue
            if dx * dy > 0:
                nc += 1
            else:
                nd += 1
    n0 = n * (n - 1) / 2
    payda = math.sqrt((n0 - tx) * (n0 - ty)) or 1e-9
    return {"tau_b": round((nc - nd) / payda, 4), "uyumlu": nc, "uyumsuz": nd}


def phi_katsayisi(a, b, c, d):
    """Phi katsayısı (2x2 nominal ilişki; Cramér V'nin 2x2 hali)."""
    pay = a * d - b * c
    payda = math.sqrt((a + b) * (c + d) * (a + c) * (b + d)) or 1e-9
    return round(pay / payda, 4)


# ---------------- P1: ANOVA + Kruskal-Wallis + randomization ----------------

def anova(gruplar, alfa=0.05):
    """
    Tek yönlü ANOVA (Ch 9) + eta² + Bonferroni pairwise t-testleri.
    gruplar: {'ad': [degerler], ...}
    """
    adlar = list(gruplar.keys())
    tum = [v for g in gruplar.values() for v in g]
    k, N = len(adlar), len(tum)
    if k < 2 or any(len(g) < 2 for g in gruplar.values()):
        return None
    gmean = statistics.fmean(tum)
    ssb = sum(len(gruplar[a]) * (statistics.fmean(gruplar[a]) - gmean) ** 2
              for a in adlar)
    ssw = sum(sum((v - statistics.fmean(gruplar[a])) ** 2 for v in gruplar[a])
              for a in adlar)
    dfb, dfw = k - 1, N - k
    f = (ssb / dfb) / (ssw / dfw or 1e-9)
    p = 1 - f_cdf(f, dfb, dfw)
    # Bonferroni pairwise
    cifler = []
    m = k * (k - 1) // 2
    for i in range(k):
        for j in range(i + 1, k):
            tt = t_test_bagimsiz(gruplar[adlar[i]], gruplar[adlar[j]])
            cifler.append({"gruplar": [adlar[i], adlar[j]],
                           "t": tt["t"], "p_ham": tt["p"],
                           "p_bonferroni": min(1.0, tt["p"] * m),
                           "anlamli": tt["p"] * m < alfa})
    return {"F": round(f, 4), "df": [dfb, dfw], "p": round(p, 5),
            "eta_kare": round(ssb / (ssb + ssw or 1e-9), 4),
            "pairwise_bonferroni": cifler,
            "not": "eşit varyans varsayar; şüphede Kruskal-Wallis kullanın"}


def kruskal_wallis(gruplar):
    """
    Kruskal-Wallis (ANOVA'nın nonparametrik karşılığı).
    H istatistiği + tie düzeltmesi; p ki-kare yaklaşımı (df=k-1).
    """
    adlar = list(gruplar.keys())
    k = len(adlar)
    tum = [(v, a) for a in adlar for v in gruplar[a]]
    degerler = [v for v, _ in tum]
    siralar = _siralama(degerler)
    N = len(degerler)
    grup_sira = {a: [] for a in adlar}
    for (v, a), s in zip(tum, siralar):
        grup_sira[a].append(s)
    H = 0.0
    for a in adlar:
        n_a = len(grup_sira[a])
        H += (sum(grup_sira[a]) ** 2) / n_a
    H = 12 / (N * (N + 1)) * H - 3 * (N + 1)
    tie = Counter(degerler)
    duzeltme = 1 - sum(t ** 3 - t for t in tie.values()) / (N ** 3 - N)
    H = H / (duzeltme or 1e-9)
    p = _gammaincc((k - 1) / 2.0, H / 2.0)
    return {"H": round(H, 4), "df": k - 1, "p": round(p, 5),
            "grup_sira_ortalamalari": {a: round(statistics.fmean(grup_sira[a]), 2)
                                       for a in adlar}}


def randomizasyon_testi(x, y, sim=999, seed=None):
    """
    İki ortalama farkı için permütasyon/randomization testi.
    Varsayım gerektirmez; küçük örneklemde t-testine sağlam alternatif.
    """
    import random as _r
    # Ortak muhafazakâr simülasyon tavanı, kopyalama/karıştırmadan önce.
    _sim_butce(len(x) + len(y), sim)
    rng = _r.Random(seed)
    gozlenen = abs(statistics.fmean(x) - statistics.fmean(y))
    birlesik = list(x) + list(y)
    nx = len(x)
    asan = 0
    for _ in range(sim):
        rng.shuffle(birlesik)
        fark = abs(statistics.fmean(birlesik[:nx]) -
                   statistics.fmean(birlesik[nx:]))
        if fark >= gozlenen - 1e-12:
            asan += 1
    p = (1 + asan) / (sim + 1)
    return {"gozlenen_fark": round(gozlenen, 4), "p": round(p, 5),
            "sim": sim}


# ---------------- P1: güç analizi (Ch 20-21) ----------------

def guc_oran_orneklem(p1, p2, alfa=0.05, guc=0.80):
    """
    İki oran karşılaştırması için grup başına gerekli örneklem
    ('başarısızlığa tasarlanmış çalışmadan kaçınma' ilkesi).
    """
    za = norm_ppf(1 - alfa / 2)
    zb = norm_ppf(guc)
    pbar = (p1 + p2) / 2
    fark = abs(p1 - p2)
    if fark < 1e-9:
        return None
    n = ((za * math.sqrt(2 * pbar * (1 - pbar)) +
          zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) / fark) ** 2
    return {"n_grup_basi": math.ceil(n), "alfa": alfa, "guc": guc,
            "p1": p1, "p2": p2}


def guc_t_orneklem(d, alfa=0.05, guc=0.80):
    """
    İki ortalama karşılaştırması için grup başına örneklem.
    d: Cohen's d etki büyüklüğü (0.2 küçük, 0.5 orta, 0.8 büyük).
    """
    za = norm_ppf(1 - alfa / 2)
    zb = norm_ppf(guc)
    if d <= 0:
        return None
    n = 2 * ((za + zb) / d) ** 2
    return {"n_grup_basi": math.ceil(n), "cohen_d": d, "alfa": alfa,
            "guc": guc,
            "not": "etki büyüklüğü tahmini kritik; d abartılırsa çalışma "
                   "yetersiz güçle kalır"}
