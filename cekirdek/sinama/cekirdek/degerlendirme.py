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


def kesinti_analizi(seri, kesinti_noktasi, guven=0.95):
    """
    Kesintili zaman serisi (ITS) — segmentli regresyon (A4.7):
        y_t = β0 + β1·t + β2·D_t + β3·(t − t0)·D_t + ε_t,   D_t = 1 (t ≥ t0)
    β2 kesintideki SEVİYE değişimi, β3 EĞİM değişimi; her biri SE, p ve güven
    aralığıyla (OLS, regresyon.coklu_ols). Artık otokorelasyonu için
    Durbin-Watson; 1,5–2,5 dışında p ve GA güvenilmez (uyarı). Önceki sürüm
    yalnız öncesi/sonrası ortalama ve eğim veriyordu — belirsizlik yoktu (BMK
    v0 K2.5 bu aracı açık bulamadı; açmadan önce yükseltildi).

    TEK GRUP ITS NEDENSELLİK KANITLAMAZ: kesintiyle eşzamanlı başka bir
    değişiklik (ör. yeni bildirim kanalı, kayıt pratiği) aynı seviye
    sıçramasını üretir. Kontrol serisi olmadan etki "müdahalenin" değil
    "kesinti zamanındaki bir değişikliğin"dir.

    Args:
        seri: dönemlik değerler (ör. aylık olay sayısı).
        kesinti_noktasi: kesintinin ilk dönemi (0 tabanlı indeks).
        guven: güven düzeyi (varsayılan 0,95).

    Returns:
        None (her iki tarafta < 2 dönem) ya da betimsel alanlar
        (once/sonra_ortalama, once/sonra_egim, seviye_farki) + model alanları
        (seviye_degisimi, egim_degisimi, once_trend: {tahmin, se, p, ga_alt,
        ga_ust}; karsiolgusal_son, gozlenen_son, durbin_watson, uyarilar, not).
    """
    from .hipotez import t_ppf
    from .regresyon import coklu_ols

    once = list(seri[:kesinti_noktasi])
    sonra = list(seri[kesinti_noktasi:])
    if len(once) < 2 or len(sonra) < 2:
        return None

    def egim(s):
        """En küçük kareler eğimi (dönem başına değişim; iç yardımcı)."""
        n = len(s)
        mx = (n - 1) / 2
        my = statistics.fmean(s)
        pay = sum((i - mx) * (v - my) for i, v in enumerate(s))
        payda = sum((i - mx) ** 2 for i in range(n)) or 1e-9
        return pay / payda

    sonuc = {
        "once_ortalama": round(statistics.fmean(once), 3),
        "sonra_ortalama": round(statistics.fmean(sonra), 3),
        "once_egim": round(egim(once), 4),
        "sonra_egim": round(egim(sonra), 4),
        "seviye_farki": round(statistics.fmean(sonra) - statistics.fmean(once), 3),
        "n_once": len(once), "n_sonra": len(sonra),
        "not": ("tek grup ITS nedensellik kanıtlamaz: kesintiyle eşzamanlı başka bir "
                "değişiklik (ör. bildirim kanalı) aynı etkiyi üretir; kontrol serisi yoksa "
                "etki kesinti ZAMANINDAKİ bir değişikliğe aittir"),
    }
    uyarilar = []
    n = len(seri)
    if n < 6:
        uyarilar.append("segmentli regresyon için en az 6 dönem gerekir; yalnız betimsel sonuç")
        sonuc.update({"model": None, "uyarilar": uyarilar})
        return sonuc
    t0 = kesinti_noktasi
    X = [[t, 1.0 if t >= t0 else 0.0, float(t - t0) if t >= t0 else 0.0] for t in range(n)]
    ols = coklu_ols(X, [float(v) for v in seri],
                    adlar=["zaman", "seviye_degisimi", "egim_degisimi"], vif_hesapla=False)
    if not ols or "hata" in ols:
        uyarilar.append("segmentli regresyon kurulamadı: " + (ols or {}).get("hata", "yetersiz veri"))
        sonuc.update({"model": None, "uyarilar": uyarilar})
        return sonuc
    k = {c["degisken"]: c for c in ols["katsayilar"]}
    tk = t_ppf(1 - (1 - guven) / 2, n - 4)

    def ozet(c):
        """Katsayı → {tahmin, se, p, ga_alt, ga_ust} (iç yardımcı)."""
        if c["p"] is None:  # tam uyum: çıkarım tanımsız (regresyon.coklu_ols)
            return {"tahmin": c["beta"], "se": None, "p": None,
                    "ga_alt": None, "ga_ust": None}
        return {"tahmin": c["beta"], "se": c["se"], "p": c["p"],
                "ga_alt": round(c["beta"] - tk * c["se"], 4),
                "ga_ust": round(c["beta"] + tk * c["se"], 4)}

    e = ols["artik"]
    payda = sum(x * x for x in e)
    dw = sum((e[i] - e[i - 1]) ** 2 for i in range(1, n)) / payda if payda > 1e-12 else None
    if dw is not None and not 1.5 <= dw <= 2.5:
        uyarilar.append(f"artık otokorelasyonu (Durbin-Watson {round(dw, 2)}): p ve güven "
                        "aralıkları güvenilmez")
    uyarilar += [f"segmentli regresyon: {x}" for x in ols.get("notlar", [])]
    if len(once) < 8 or len(sonra) < 8:
        uyarilar.append("her iki tarafta en az 8 dönem önerilir (Wagner vd. 2002); "
                        "kısa seride tahminler kararsızdır")
    b0, b1 = k["sabit"]["beta"], k["zaman"]["beta"]
    sonuc.update({
        "model": "segmentli OLS", "guven": guven,
        "seviye_degisimi": ozet(k["seviye_degisimi"]),
        "egim_degisimi": ozet(k["egim_degisimi"]),
        "once_trend": ozet(k["zaman"]),
        "karsiolgusal_son": round(b0 + b1 * (n - 1), 3),
        "gozlenen_son": seri[-1],
        "durbin_watson": round(dw, 3) if dw is not None else None,
        "uyarilar": uyarilar,
    })
    return sonuc


def oran_degisimi_ayristirma(a_once, a_sonra, b_once, b_sonra, sure_once, sure_sonra,
                             dispersiyon=1.0, dispersiyon_b=None):
    """İki bileşenli sayımda oran artışının ayrıştırılması (A4.10).

    Toplam = A + B iken önce→sonra oran değişimini bileşenlere ayırır ve
    "artışın çoğu A'dan mı" sorusunu sınar: fark = ΔA − ΔB (gün başına oran).
    fark > 0 ⟺ A'nın artışı, toplam artışın yarısından fazlası. Varyans
    Poisson × yayılım çarpanı (quasi-Poisson, φ ≥ 1).

    Neden: bir rakip açıklamayı ("artış yeni kanaldan") yalnız A'da ANLAMLI bir
    artış olmasıyla dışlamak, (1) o sınamanın I. tip hatasını hükme taşır ve
    (2) A'daki küçük ama gerçek artışta rakibi, artışın çoğunu açıkladığı hâlde
    dışlar (BMK v4 K10.2/K10.4). Etki büyüklüğü (pay_a) ile sınanır.

    Args:
        a_once, a_sonra, b_once, b_sonra: bileşen sayımları (önce/sonra).
        sure_once, sure_sonra: dönem uzunlukları (gün).
        dispersiyon: A'nın (ya da ortak) yayılım çarpanı (≥ 1; Poisson için 1).
        dispersiyon_b: B'nin yayılım çarpanı (≥ 1); None ise A'nınki (v1.3:
            bileşenlerin yayılımı farklıysa ortak çarpan baskın bileşenin
            varyansını yanlış tahmin eder — BMK v5, v1.2 reddi).

    Returns:
        None (dönem uzunluğu sıfır) ya da {degisim_a, degisim_b (gün başına),
        fark, se, z (se sıfırsa None), pay_a (toplam artış ≤ 0 ise None),
        dispersiyon, dispersiyon_b}.
    """
    if sure_once <= 0 or sure_sonra <= 0:
        return None
    phi = max(1.0, dispersiyon)
    phi_b = phi if dispersiyon_b is None else max(1.0, dispersiyon_b)
    da = a_sonra / sure_sonra - a_once / sure_once
    db = b_sonra / sure_sonra - b_once / sure_once
    var = (phi * (a_sonra / sure_sonra ** 2 + a_once / sure_once ** 2)
           + phi_b * (b_sonra / sure_sonra ** 2 + b_once / sure_once ** 2))
    se = math.sqrt(var)
    fark = da - db
    toplam = da + db
    return {"degisim_a": round(da, 5), "degisim_b": round(db, 5), "fark": round(fark, 5),
            "se": round(se, 5), "z": round(fark / se, 3) if se > 0 else None,
            "pay_a": round(da / toplam, 3) if toplam > 0 else None,
            "dispersiyon": round(phi, 3), "dispersiyon_b": round(phi_b, 3)}


def oran_orani_farki(a_once, a_sonra, b_once, b_sonra, dispersiyon_a=1.0, dispersiyon_b=1.0):
    """Oran oranlarının log farkı (A4.13, ETKİ): ln(a_s/a_ö) − ln(b_s/b_ö).

    İki bölge aynı öncesi/sonrası pencerelerini paylaştığından pencere
    uzunlukları sadeleşir (ham WDD sayım farkı ise bölge hacimleri farklıysa
    ölçeğe bağımlıdır). Varyans bileşene özgü quasi-Poisson:
    φ_a(1/a_ö + 1/a_s) + φ_b(1/b_ö + 1/b_s).

    Args:
        a_once, a_sonra: A bölgesinin (ör. müdahale) sayımları.
        b_once, b_sonra: B bölgesinin (ör. kontrol) sayımları.
        dispersiyon_a, dispersiyon_b: yayılım çarpanları (≥ 1).

    Returns:
        None (bir sayım 0 → log tanımsız) ya da {log_fark, oran (oran oranı),
        se, z, ga_alt, ga_ust (oran ölçeğinde %95), dispersiyon_a, dispersiyon_b}.
    """
    if min(a_once, a_sonra, b_once, b_sonra) <= 0:
        return None
    pa, pb = max(1.0, dispersiyon_a), max(1.0, dispersiyon_b)
    lf = math.log(a_sonra / a_once) - math.log(b_sonra / b_once)
    se = math.sqrt(pa * (1 / a_once + 1 / a_sonra) + pb * (1 / b_once + 1 / b_sonra))
    return {"log_fark": round(lf, 5), "oran": round(math.exp(lf), 4), "se": round(se, 5),
            "z": round(lf / se, 3),
            "ga_alt": round(math.exp(lf - 1.959964 * se), 4),
            "ga_ust": round(math.exp(lf + 1.959964 * se), 4),
            "dispersiyon_a": round(pa, 3), "dispersiyon_b": round(pb, 3)}


def oran_farki_log(n_once, n_sonra, sure_once, sure_sonra, dispersiyon=1.0):
    """Tek bölgede iki dönemin oran oranı (A4.13): ln((n_s/g_s)/(n_ö/g_ö)),
    varyans φ(1/n_ö + 1/n_s). Kontrol bölgesi yokken ortalamaya dönüş sınaması.

    Returns: None (sayım ya da süre sıfır) ya da {log_fark, oran, se, z, dispersiyon}.
    """
    if min(n_once, n_sonra) <= 0 or min(sure_once, sure_sonra) <= 0:
        return None
    phi = max(1.0, dispersiyon)
    lf = math.log((n_sonra / sure_sonra) / (n_once / sure_once))
    se = math.sqrt(phi * (1 / n_once + 1 / n_sonra))
    return {"log_fark": round(lf, 5), "oran": round(math.exp(lf), 4), "se": round(se, 5),
            "z": round(lf / se, 3), "dispersiyon": round(phi, 3)}


def sara_kontrol_listesi():
    """Problem yönelimli polislik SARA döngüsü hatırlatıcısı (Ch 13)."""
    return {
        "Tarama (Scanning)": "tekrar eden sorunları tanımla — frekans, hotspot, mükerrer mağduriyet",
        "Analiz (Analysis)": "üçgen: kurban-fail-yer; zaman/mekân/MO deseni çıkar",
        "Müdahale (Response)": "bulguya özgü müdahale tasarla; sorumlu birim ata",
        "Değerlendirme (Assessment)": "oncesi_sonrasi / farklarin_farki ile etkiyi ölç",
    }
