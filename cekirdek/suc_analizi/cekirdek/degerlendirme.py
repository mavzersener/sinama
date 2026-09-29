# -*- coding: utf-8 -*-
"""
degerlendirme.py — Program/müdahale değerlendirme
(Maxfield & Babbie, Bölüm 13: evaluation research, quasi-experimental
designs, problem analysis).
"""

import math
import statistics


def _normal_iki_yonlu(z):
    """|z| için iki yönlü normal p-değeri (math.erf)."""
    return round(2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))), 5)


def oncesi_sonrasi(once, sonra):
    """
    Basit öncesi-sonrası karşılaştırma (tek grup, yarı-deneysel).
    once, sonra: dönemlik olay sayıları (veya seriler).
    """
    o = sum(once) if isinstance(once, (list, tuple)) else once
    s = sum(sonra) if isinstance(sonra, (list, tuple)) else sonra
    degisim = None if o == 0 else round(100.0 * (s - o) / o, 2)
    if o == 0:
        # yüzde tanımsız ama YÖN tanımlı: 0'dan artışa "değişim yok"
        # demek sessiz yanlıştır (v6.6 düzeltmesi)
        yorum = "artış" if s > 0 else "değişim yok"
    else:
        yorum = ("azalma" if degisim < 0 else
                 ("artış" if degisim > 0 else "değişim yok"))
    return {"once": o, "sonra": s, "degisim_yuzde": degisim,
            "yorum": yorum}


def farklarin_farki(mudahale_once, mudahale_sonra, kontrol_once, kontrol_sonra):
    """
    Difference-in-differences (yarı-deneysel tasarım, Ch 13):
    müdahale etkisi = (M_sonra - M_önce) - (K_sonra - K_önce).
    """
    m = oncesi_sonrasi(mudahale_once, mudahale_sonra)
    k = oncesi_sonrasi(kontrol_once, kontrol_sonra)
    did = (m["sonra"] - m["once"]) - (k["sonra"] - k["once"])
    return {"mudahale": m, "kontrol": k, "did_etki": did,
            "yorum": f"Müdahale bölgesinde kontrole göre net {did:+} olay farkı"}


def wdd_testi(t_once, t_sonra, k_once, k_sonra,
              yd_once=None, yd_sonra=None, ydk_once=None, ydk_sonra=None):
    """Weighted Displacement Difference testi (Wheeler & Ratcliffe 2018,
    Chainey Böl.10): yer değiştirmeyi (displacement) hesaba katarak müdahale
    etkisinin İSTATİSTİKSEL anlamlılığını sınar. DiD'in üstüne z-testi ekler.

    Alanlar (olay SAYILARI): tedavi (t), tedavi kontrolü (k), opsiyonel
    yer-değiştirme tamponu (yd) ve onun kontrolü (ydk); her biri önce/sonra.
    WDD = (t_s-t_o) - (k_s-k_o) + (yd_s-yd_o) - (ydk_s-ydk_o).
    Varyans: tüm sayımların toplamı (Poisson: var≈sayım); z=WDD/√var.

    Yorum: tedavi_etkisi negatif+anlamlı → müdahale suçu azalttı; yer
    değiştirme etkisi POZİTİF → suç tampona kaydı (displacement), NEGATİF →
    fayda yayılımı (diffusion of benefits).
    """
    tedavi = (t_sonra - t_once) - (k_sonra - k_once)
    sayimlar = [t_once, t_sonra, k_once, k_sonra]
    yer_deg = None
    wdd = tedavi
    tampon_var = None not in (yd_once, yd_sonra, ydk_once, ydk_sonra)
    if tampon_var:
        yer_deg = (yd_sonra - yd_once) - (ydk_sonra - ydk_once)
        wdd = tedavi + yer_deg
        sayimlar += [yd_once, yd_sonra, ydk_once, ydk_sonra]
    var = sum(sayimlar)
    se = math.sqrt(var) if var > 0 else 0.0
    z = wdd / se if se > 0 else 0.0
    p = _normal_iki_yonlu(z)

    if p < 0.05 and tedavi < 0:
        yorum = "müdahale suçu ANLAMLI ölçüde azalttı (kontrole göre)"
    elif p < 0.05 and tedavi > 0:
        yorum = "tedavi bölgesinde ANLAMLI artış (istenmeyen)"
    else:
        yorum = "etki rastlantıdan ayırt edilemez (anlamlı değil)"
    sonuc = {"wdd": wdd, "tedavi_etkisi": tedavi,
             "se": round(se, 3), "z": round(z, 4), "p": p, "yorum": yorum}
    if tampon_var:
        sonuc["yer_degistirme_etkisi"] = yer_deg
        sonuc["yer_degistirme_yorumu"] = (
            "fayda yayılımı (tampon da iyileşti)" if yer_deg < 0 else
            "yer değiştirme: suç tampona kaydı" if yer_deg > 0 else
            "tamponda net değişim yok")
    return sonuc


def kesinti_analizi(seri, kesinti_noktasi):
    """
    Kesintili zaman serisi (basit): kesinti öncesi/sonrası ortalama seviye
    ve eğim karşılaştırması. seri: sayı listesi.
    """
    once = list(seri[:kesinti_noktasi])
    sonra = list(seri[kesinti_noktasi:])
    if len(once) < 2 or len(sonra) < 2:
        return None
    def egim(s):
        """En küçük kareler eğimi (dönem başına değişim; iç yardımcı).
        """
        n = len(s)
        mx = (n - 1) / 2
        my = statistics.fmean(s)
        pay = sum((i - mx) * (v - my) for i, v in enumerate(s))
        payda = sum((i - mx) ** 2 for i in range(n)) or 1e-9
        return pay / payda
    return {
        "once_ortalama": round(statistics.fmean(once), 3),
        "sonra_ortalama": round(statistics.fmean(sonra), 3),
        "once_egim": round(egim(once), 4),
        "sonra_egim": round(egim(sonra), 4),
        "seviye_farki": round(statistics.fmean(sonra) - statistics.fmean(once), 3),
    }


def sara_kontrol_listesi():
    """Problem yönelimli polislik SARA döngüsü hatırlatıcısı (Ch 13)."""
    return {
        "Tarama (Scanning)": "tekrar eden sorunları tanımla — frekans, hotspot, mükerrer mağduriyet",
        "Analiz (Analysis)": "üçgen: kurban-fail-yer; zaman/mekân/MO deseni çıkar",
        "Müdahale (Response)": "bulguya özgü müdahale tasarla; sorumlu birim ata",
        "Değerlendirme (Assessment)": "oncesi_sonrasi / farklarin_farki ile etkiyi ölç",
    }
