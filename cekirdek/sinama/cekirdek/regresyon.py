# -*- coding: utf-8 -*-
"""
regresyon.py — Çoklu OLS ve lojistik regresyon (P2; Weisburd & Britt
Ch 13-15 temelli). Saf Python: normal denklemler + Gauss eliminasyonu,
IRLS ile lojistik.
"""

import math
import statistics
from .hipotez import t_cdf, f_cdf, norm_cdf
from .hatalar import VeriHatasi


def _sonlu_sayi(v):
    """Bool ve sonlu olmayan değerleri reddeden ortak sayısal dönüşüm."""
    try:
        if isinstance(v, bool):
            raise ValueError
        sonuc = float(v)
        if not math.isfinite(sonuc):
            raise ValueError
        return sonuc
    except (TypeError, ValueError, OverflowError):
        raise VeriHatasi("sonlu sayısal değer gerekli") from None


def _tasarim_dogrula(X, y, adlar=None):
    """Eşleşmiş, dolu ve dikdörtgen tasarımı kopyalayarak doğrular."""
    if (not isinstance(X, (list, tuple)) or not X or
            not isinstance(y, (list, tuple)) or len(X) != len(y) or
            not isinstance(X[0], (list, tuple)) or not X[0]):
        raise VeriHatasi("X/y: dolu ve eşit uzunluklu tasarım gerekli")
    k = len(X[0])
    if any(not isinstance(row, (list, tuple)) or len(row) != k for row in X):
        raise VeriHatasi("X: düzensiz satır boyutu")
    if adlar is not None and (not isinstance(adlar, (list, tuple)) or len(adlar) != k):
        raise VeriHatasi("degiskenler: tasarımla aynı sayıda ad gerekli")
    return [[_sonlu_sayi(v) for v in row] for row in X], [_sonlu_sayi(v) for v in y]


def _gauss_coz(A, b):
    """A x = b — kısmi pivotlu Gauss eliminasyonu."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            raise VeriHatasi("tekil matris (multicollinearity şüphesi)",
                         oneri="birbirinin katı olan değişkenlerden "
                              "birini çıkarın; VIF değerlerine bakın")
        M[col], M[piv] = M[piv], M[col]
        for r in range(col + 1, n):
            oran = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= oran * M[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))) / M[r][r]
    return x


def _xtx(X):
    n = len(X[0])
    return [[sum(row[i] * row[j] for row in X) for j in range(n)]
            for i in range(n)]


def _matris_ters(A):
    """Gauss-Jordan ile ters matris."""
    n = len(A)
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)]
         for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            raise VeriHatasi("tekil matris",
                         oneri="kovaryans matrisi tersinemedi; "
                              "değişken sayısını azaltın")
        M[col], M[piv] = M[piv], M[col]
        d = M[col][col]
        M[col] = [v / d for v in M[col]]
        for r in range(n):
            if r != col and M[r][col] != 0:
                f = M[r][col]
                M[r] = [v - f * w for v, w in zip(M[r], M[col])]
    return [row[n:] for row in M]


def coklu_ols(X, y, adlar=None, vif_hesapla=True):
    """
    Çoklu doğrusal regresyon (OLS).
    X: gözlem x değişken matrisi (sabit terim OTOMATİK eklenir),
    y: hedef vektörü.
    Dönüş: katsayılar (SE, t, p), R², düzeltilmiş R², F, VIF, artıklar.
    """
    X, y = _tasarim_dogrula(X, y, adlar)
    n = len(y)
    k = len(X[0]) if X else 0
    if n < k + 2:
        return None
    Xd = [[1.0] + [float(v) for v in row] for row in X]
    p = k + 1
    xtx = _xtx(Xd)
    xty = [sum(row[i] * row_y for row, row_y in zip(Xd, y)) for i in range(p)]
    try:
        beta = _gauss_coz(xtx, xty)
        xtx_inv = _matris_ters(xtx)
    except ValueError:
        return {"hata": "tekil tasarım matrisi; bir değişken diğerinin "
                        "doğrusal bileşimi (multicollinearity)"}
    ybar = statistics.fmean(y)
    sst = sum((v - ybar) ** 2 for v in y)
    if sst == 0:
        return {"hata": "bağımlı değişken sabit (varyans 0): R² ve katsayı "
                        "çıkarımı tanımsız"}
    y_tahmin = [sum(b * v for b, v in zip(beta, row)) for row in Xd]
    artik = [a - b for a, b in zip(y, y_tahmin)]
    sse = sum(e ** 2 for e in artik)
    # Tam uyum (A4.7): artıklar kayan nokta gürültüsü düzeyindeyse se ≈ 0 ve
    # t = beta/se gürültüden uydurulur (ör. y = 2x'te sabit için p rastgele).
    # Çıkarım tanımsızdır: t, p, F None; katsayılar ve R² yine raporlanır.
    tam_uyum = sse <= 1e-20 * sst
    r2 = 1 - sse / sst
    adj = 1 - (1 - r2) * (n - 1) / (n - p or 1e-9)
    ms_e = sse / (n - p)
    F = ((sst - sse) / k) / (ms_e or 1e-9) if k > 0 and not tam_uyum else None
    p_F = 1 - f_cdf(F, k, n - p) if F else None
    katsayilar = []
    for i in range(p):
        se = math.sqrt(max(0.0, ms_e * xtx_inv[i][i]))
        t = None if tam_uyum else beta[i] / (se or 1e-9)
        katsayilar.append({
            "degisken": ("sabit" if i == 0 else
                         (adlar[i - 1] if adlar else f"x{i}")),
            "beta": round(beta[i], 4), "se": 0.0 if tam_uyum else round(se, 4),
            "t": None if t is None else round(t, 3),
            "p": None if t is None else
                 round(min(1.0, 2 * (1 - t_cdf(abs(t), n - p))), 5)})
    vif = {}
    for j in range(k) if vif_hesapla else []:
        digerleri = [c for c in range(k) if c != j]
        if not digerleri:
            vif[adlar[j] if adlar else f"x{j+1}"] = 1.0
            continue
        Xj = [[row[c] for c in digerleri] for row in X]
        yj = [row[j] for row in X]
        alt = coklu_ols(Xj, yj, vif_hesapla=False)  # D1: özyineleme yok
        r2j = alt["r_kare"] if alt and "r_kare" in alt else 0.0
        vif[adlar[j] if adlar else f"x{j+1}"] = round(
            1 / max(1e-9, 1 - r2j), 2)
    notlar = []
    if tam_uyum:
        notlar.append("tam uyum (artıklar ≈ 0): se/t/p/F tanımsız — veri "
                      "deterministik ilişki ya da aşırı uyum; çıkarım yapılamaz")
    if any(v > 10 for v in vif.values()):
        notlar.append("VIF>10: ciddi multicollinearity; katsayılar kararsız")
    return {"katsayilar": katsayilar, "r_kare": round(r2, 4),
            "duzeltilmis_r_kare": round(adj, 4),
            "F": round(F, 3) if F else None,
            "p_F": round(p_F, 5) if p_F is not None else None,
            "vif": vif, "n": n, "artik_std": round(math.sqrt(ms_e), 4),
            "artik": artik,  # mekânsal regresyon tanısı (artık otokorelasyonu) için
            "notlar": notlar}


def lojistik(X, y, adlar=None, maks_iter=25):
    """
    İkili lojistik regresyon (IRLS).
    y: 0/1. Dönüş: katsayılar (Wald z, p, odds ratio), McFadden R²,
    yakınsama durumu. Risk skorlaması DEĞİL, ilişki analizi aracıdır.
    """
    X, y = _tasarim_dogrula(X, y, adlar)
    n = len(y)
    k = len(X[0]) if X else 0
    if set(y) != {0.0, 1.0}:
        return {"hata": "hedef iki sınıflı (0/1) olmalı"}
    if n < k + 10:
        return {"hata": f"yetersiz örneklem (n={n}, değişken sayısı={k}); "
                        "değişken başına ~10 olay kuralı"}
    Xd = [[1.0] + [float(v) for v in row] for row in X]
    p = k + 1
    beta = [0.0] * p
    yakinsadi = False
    for _ in range(maks_iter):
        eta = [sum(b * v for b, v in zip(beta, row)) for row in Xd]
        mu = [1 / (1 + math.exp(-max(-30, min(30, e)))) for e in eta]
        W = [max(1e-8, m * (1 - m)) for m in mu]
        z = [e + (yy - m) / w for e, yy, m, w in zip(eta, y, mu, W)]
        # ağırlıklı en küçük kareler adımı
        xtwx = [[sum(row[i] * row[j] * w for row, w in zip(Xd, W))
                 for j in range(p)] for i in range(p)]
        xtwz = [sum(row[i] * w * zz for row, w, zz in zip(Xd, W, z))
                for i in range(p)]
        try:
            yeni_beta = _gauss_coz(xtwx, xtwz)
        except ValueError:
            return {"hata": "tekil matris; ayrılık (separation) şüphesi"}
        if max(abs(a - b) for a, b in zip(yeni_beta, beta)) < 1e-7:
            beta = yeni_beta
            yakinsadi = True
            break
        beta = yeni_beta
    eta = [sum(b * v for b, v in zip(beta, row)) for row in Xd]
    mu = [1 / (1 + math.exp(-max(-30, min(30, e)))) for e in eta]
    W = [max(1e-8, m * (1 - m)) for m in mu]
    xtwx = [[sum(row[i] * row[j] * w for row, w in zip(Xd, W))
             for j in range(p)] for i in range(p)]
    try:
        cov = _matris_ters(xtwx)
    except ValueError:
        cov = [[0.0] * p for _ in range(p)]
    # log-olabilirlikler (McFadden R²)
    ll_model = sum(yy * math.log(max(1e-12, m)) +
                   (1 - yy) * math.log(max(1e-12, 1 - m))
                   for yy, m in zip(y, mu))
    p1 = sum(y) / n
    ll_null = n * (p1 * math.log(max(1e-12, p1)) +
                   (1 - p1) * math.log(max(1e-12, 1 - p1)))
    katsayilar = []
    for i in range(p):
        se = math.sqrt(max(0.0, cov[i][i]))
        # Yakınsamamış kestirimde (tipik: tam ayrışma) beta ve se birlikte
        # şişer, Wald z → 0 ve p ≈ 1 "etki yok" der (Hauck-Donner) — A4.7'de
        # tam ayrışan değişken için p = 0,94 ölçüldü. Çıkarım yapılmaz.
        z = beta[i] / (se or 1e-9) if yakinsadi else None
        katsayilar.append({
            "degisken": ("sabit" if i == 0 else
                         (adlar[i - 1] if adlar else f"x{i}")),
            "beta": round(beta[i], 4), "se": round(se, 4),
            "z": None if z is None else round(z, 3),
            "p": None if z is None else
                 round(min(1.0, 2 * (1 - norm_cdf(abs(z)))), 5),
            "odds_orani": round(math.exp(max(-20, min(20, beta[i]))), 3)})
    notlar = []
    if not yakinsadi:
        notlar.append("maksimum iterasyonda yakınsamadı (tipik neden: tam/yarı "
                      "ayrışma — bir değişken sınıfları kusursuz ayırıyor); "
                      "Wald z/p tanımsız, katsayılar kararsız. Ayrışmayı "
                      "çapraz tabloyla inceleyin")
    notlar.append("ilişki analizidir; tek başına tekil karar girdisi "
                  "yapılmamalıdır")
    return {"katsayilar": katsayilar,
            "mcfadden_r2": round(1 - ll_model / (ll_null or 1e-9), 4),
            "yakinsadi": yakinsadi, "n": n, "notlar": notlar}
