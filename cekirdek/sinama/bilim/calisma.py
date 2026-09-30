# -*- coding: utf-8 -*-
"""
calisma.py — Rehberli akış: Soru → Plan → Hüküm (ADR-001 md.3, ADR-002 §7).

Tek deterministik akış, mevcut PPDAC oturumunda ve AYNI hash zincirinde:
PROBLEM → PLAN (hipotez seti; doğrulayıcıda veriden ÖNCE kilit) → VERİ
(profil + kapı) → ANALİZ (sınamalar, her biri gerekçeli adım) → hüküm (kanıt
paketi dondurulur, hash'i zincire taahhüt edilir). SONUÇ fazına geçilmez:
hüküm taslaktır, insan onayı dongu_sonuc ile verilir.
"""
import json

from ..cekirdek import veri
from ..cekirdek.hatalar import KullanimHatasi
from ..surec import dongu, kanit, kilit
from . import hukum, rak, sablon, sinamalar

URUN_TURU = {"ARTIS": "stratejik", "YOGUNLASMA": "taktik", "SERI": "sorun_cozme"}


def _kisa_ozet(ad, sonuc):
    """Manifestoya yazılan kısa sayısal özet (ham kayıt/kimlik yok)."""
    if isinstance(sonuc, list):
        return {"aday": len(sonuc), "guclu": sum(1 for c in sonuc if c.get("katman") == "güçlü")}
    if not isinstance(sonuc, dict):
        return {}
    alanlar = {"trend": ("egim", "p"), "t_testi": ("t", "p", "ortalama"),
               "sicak_nokta_gi": ("sicak", "soguk", "n")}.get(ad, ())
    return {k: sonuc.get(k) for k in alanlar if isinstance(sonuc.get(k), (int, float))}


def rehberli(kaynak, kayitlar, soru_turu, amac, log_dir, yurut_ham, kapi_karari,
             onaylayan=None, kanal_alan=None, mo_alan=None, soru=None):
    """Rehberli çalışma: hipotez seti → sınamalar → kategorik hüküm.

    Args:
        kaynak: araçlara iletilecek veri kaynağı ({'satirlar': ...} ya da {'csv_yolu': ...}).
        kayitlar: aynı kaynağın tiplenmiş kayıtları (yerel denetimler için).
        soru_turu: ARTIS | YOGUNLASMA | SERI.
        amac: dogrulayici | kesifsel | operasyonel.
        log_dir: oturum ve kanıt zinciri dizini.
        yurut_ham: (ad, arg) → araç sonucu (resmi yol: şema + kapı + hesap).
        kapi_karari: (ad, arg) → aracın TEK kapı otoritesinden karar
            ({uygun, sebepler, ...}); oturum kapısı tahmini bir analiz adıyla
            değil, birincil sınamayı koşacak aracın kendi kapısıyla verilir.
        onaylayan: doğrulayıcı çalışmada kilidi alan kişi (zorunlu).
        kanal_alan: ARTIS'te bildirim kanalı/kaynak alanı (R-BILDIRIM için).
        mo_alan: SERI'de MO metni alanı (zorunlu).
        soru: kullanıcının soru metni (kayıt için).

    Returns:
        {oturum_id, soru_turu, amac, kilit_hash, hipotezler, sinamalar, hukum}
    """
    if soru_turu not in sablon.SABLONLAR:
        raise KullanimHatasi(f"soru_turu şunlardan biri olmalı: {list(sablon.TURLER)}")
    if amac not in kilit.AMACLAR:
        raise KullanimHatasi(f"amac şunlardan biri olmalı: {list(kilit.AMACLAR)}")
    if amac == "dogrulayici" and not (onaylayan or "").strip():
        raise KullanimHatasi("doğrulayıcı çalışmada 'onaylayan' zorunlu: hipotez seti "
                             "veriden önce onun adıyla kilitlenir")
    if soru_turu == "SERI" and not mo_alan:
        raise KullanimHatasi("SERI sorusu için mo_alan zorunlu")

    d = dongu.AnalizDongusu({"karar": soru or f"{soru_turu} sorusu", "soru_turu": soru_turu,
                             "urun_turu": URUN_TURU[soru_turu]}, mod="resmi", amac=amac)
    d.planla()
    hipotezler = sablon.hipotez_seti(soru_turu)
    set_metni = json.dumps(hipotezler, ensure_ascii=False, sort_keys=True)
    d.manifesto["bilimsel"] = {"surum": "bilim-v1", "soru_turu": soru_turu,
                               "hipotezler": hipotezler, "rak_surumu": rak.RAK_SURUMU,
                               "sablon_surumu": sablon.SABLON_SURUMU,
                               "kural_surumu": hukum.KURAL_SURUMU}
    d.bilimsel_kaydet("hipotez_seti", {"hipotez_sayisi": len(hipotezler)},
                      {"hipotez": set_metni, "yorum": "şablondan kuruldu; H_bilinmeyen zorunlu"})
    if amac == "dogrulayici":
        d.protokol_kilitle(set_metni, onaylayan)

    profil = veri.veri_profili(kayitlar)
    d.veri_bagla(profil)
    ongoru_araci = sablon.SABLONLAR[soru_turu]["ongoru"]["arac"]
    arg0 = {**kaynak, "mo_alan": mo_alan} if soru_turu == "SERI" else dict(kaynak)
    uygunluk = kapi_karari(ongoru_araci, arg0)
    d.manifesto["gate_kararlari"].append({"faz": "VERI-kapi", **uygunluk})

    sinama_izi = []
    if uygunluk.get("uygun"):
        d.analize_gec(uygunluk)

        def yurut(ad, arg, hipotez, amac_metni):
            """Aracı resmi yoldan koşar ve gerekçeli ANALİZ adımı olarak kaydeder."""
            sonuc = yurut_ham(ad, arg)
            d.analiz_kaydet(ad, _kisa_ozet(ad, sonuc), {"hipotez": hipotez, "yorum": amac_metni})
            sinama_izi.append({"arac": ad, "hipotez": hipotez, "amac": amac_metni})
            return sonuc

        if soru_turu == "ARTIS":
            birincil, rakipler, saglamlik = sinamalar.artis(kaynak, kayitlar, yurut, kanal_alan)
        elif soru_turu == "YOGUNLASMA":
            birincil, rakipler, saglamlik = sinamalar.yogunlasma(kaynak, kayitlar, yurut)
        else:
            birincil, rakipler, saglamlik = sinamalar.seri(kaynak, kayitlar, yurut, mo_alan)
    else:
        neden = "; ".join(uygunluk.get("sebepler") or []) or "veri uygun değil"
        birincil = {"durum": "sınanamadı", "gerekce": f"kapı reddi: {neden}"}
        rakipler = [sinamalar._rakip(k, "çözülmedi", "veri analize uygun değil")
                    for k in rak.uygulanabilir(soru_turu)]
        saglamlik = []

    dongu.kaydet(d, log_dir)
    zincir = kanit.dogrula(log_dir, d.manifesto["oturum_id"])
    paket = {"soru_turu": soru_turu, "amac": amac, "kilitli": bool(d.manifesto.get("kilit")),
             "zincir_saglam": bool(zincir.get("saglam")), "birincil": birincil,
             "rakipler": rakipler, "saglamlik": saglamlik}
    h = hukum.hukum_ver(paket)
    d.manifesto["bilimsel"].update({"paket": paket, "hukum": h})
    d.bilimsel_kaydet("hukum", {"rakip_sayisi": len(rakipler)},
                      {"hipotez": "H1", "yorum": h["ifade"], "kategori": h["kategori"],
                       "paket_hash": h["paket_hash"], "kural_surumu": h["kural_surumu"]})
    dongu.kaydet(d, log_dir)
    return {"oturum_id": d.manifesto["oturum_id"], "soru_turu": soru_turu, "amac": amac,
            "kilit_hash": (d.manifesto.get("kilit") or {}).get("hash"),
            "hipotezler": hipotezler, "sinamalar": sinama_izi, "hukum": h}
