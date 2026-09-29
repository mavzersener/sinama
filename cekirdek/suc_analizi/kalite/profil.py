# -*- coding: utf-8 -*-
r"""
kalite/profil.py — deterministik veri profili (v6.1, G1).
veri_profili buraya taşındı; istatistik testi ÇALIŞTIRMAZ, yalnız kalite
ve uygunluk sinyali üretir. Geriye uyumluluk: veri.veri_profili buraya
delege eder.
"""

import statistics

from ..cekirdek import veri

def veri_profili(kayitlar, kritik_alanlar=("tarih", "lat", "lon"),
                 sayisal_alan=None, tarih_alan="tarih"):
    """
    Analiz öncesi deterministik veri profili (istatistik testi ÇALIŞTIRMAZ;
    yalnız kalite ve uygunluk sinyali üretir).
    """
    n = len(kayitlar)
    if n == 0:
        return {"n": 0, "uyarilar": ["veri boş"]}
    prof = {"n": n, "kesildi": veri.son_okuma.get("kesildi", False), "uyarilar": []}

    # 1) Tam-satır duplikat oranı
    imzalar = [tuple(sorted((k, str(v)) for k, v in r.items())) for r in kayitlar]
    prof["duplikat_oran"] = round(1 - len(set(imzalar)) / n, 3)

    # 2) Eksiklik (alan başına oran) + kritik alan vurgusu
    ham = veri.eksik_raporu(kayitlar)
    prof["eksik_oran"] = {a: round(c / n, 3) for a, c in ham.items()}
    prof["kritik_eksik"] = {a: prof["eksik_oran"].get(a, 1.0)
                            for a in kritik_alanlar}

    # 3) Tarih ayrıştırma başarı oranı (sessiz format kaybını yakalar)
    if tarih_alan in ham:
        ok = sum(1 for r in kayitlar if veri.tarih_coz(r.get(tarih_alan)) is not None)
        prof["tarih_basari_oran"] = round(ok / n, 3)

    # 4) Koordinat geçerliliği + tek-nokta (geokodlama hatası) işareti
    pts = [veri.koordinat_al(r) for r in kayitlar]
    gecerli = [q for q in pts if q]
    prof["koordinat_gecerli_oran"] = round(len(gecerli) / n, 3)
    prof["koordinat_tek_nokta"] = (len(set(gecerli)) == 1) if gecerli else False

    # 5) Zaman kapsamı (trend/Holt-Winters yeterliliği için)
    ts = sorted(x for x in (veri.tarih_coz(r.get(tarih_alan)) for r in kayitlar) if x)
    if ts:
        prof["zaman_kapsam"] = {"bas": str(ts[0].date()),
                                "bit": str(ts[-1].date()),
                                "gun": (ts[-1] - ts[0]).days + 1,
                                "olayli_gun": len({x.date() for x in ts})}

    # 6) Sayısal alan: dağılımsal işaretler (K10)
    if sayisal_alan:
        vals = [v for v in (veri.tip_tahmin(r.get(sayisal_alan)) for r in kayitlar)
                if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(vals) >= 10:
            mu = statistics.fmean(vals)
            if mu:
                prof["dispersiyon_orani"] = round(
                    statistics.pvariance(vals) / mu, 2)
            prof["benford_mertebe"] = len(
                {len(str(abs(int(v)))) for v in vals if v})

    # 7) Kategorik kardinalite (ki-kare hücre seyrekliği ön sinyali)
    prof["kardinalite"] = {}
    for a in ham:
        degerler = {str(r.get(a)) for r in kayitlar
                    if r.get(a) not in (None, "")}
        if 1 < len(degerler) <= 50:
            prof["kardinalite"][a] = len(degerler)

    _profil_uyarilari(prof)
    return prof


def _profil_uyarilari(prof):
    """Eşik tabanlı uyarı metinleri — profil üretiminin son adımı."""
    u = prof["uyarilar"]
    if prof.get("kesildi"):
        u.append("veri MAKS_SATIR tavanında kesildi; profil ve sonuçlar eksik olabilir")
    if prof.get("duplikat_oran", 0) > 0.01:
        u.append(f"tam-duplikat oranı %{100 * prof['duplikat_oran']:.1f}; "
                 "duplikat_isaretle ile inceleyin (otomatik silme YOK)")
    for a, o in prof.get("kritik_eksik", {}).items():
        if o > 0.2:
            u.append(f"kritik alan '{a}' %{100 * o:.0f} eksik")
    if 0 < prof.get("tarih_basari_oran", 1) < 0.9:
        u.append(f"tarih ayrıştırma başarısı %{100 * prof['tarih_basari_oran']:.0f}; "
                 "format karışıklığı olabilir — sessiz dışlama riski")
    if 0 < prof.get("koordinat_gecerli_oran", 1) < 0.9:
        u.append(f"geçerli koordinat %{100 * prof['koordinat_gecerli_oran']:.0f}")
    if prof.get("koordinat_tek_nokta"):
        u.append("tüm koordinatlar tek noktada; geokodlama hatası şüphesi")
    if prof.get("dispersiyon_orani", 0) and prof["dispersiyon_orani"] > 1.5:
        u.append(f"aşırı yayılım (var/mean={prof['dispersiyon_orani']}); "
                 "naif Poisson varsayımı bozulur")
    if prof.get("benford_mertebe", 99) < 3:
        u.append("veri <3 büyüklük mertebesi kapsıyor; Benford anlamsız")
