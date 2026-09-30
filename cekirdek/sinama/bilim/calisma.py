# -*- coding: utf-8 -*-
"""
calisma.py — Bilim çalışması: Soru → Plan → Hüküm (ADR-001 md.3, ADR-002 §7).

Dört adım, mevcut PPDAC oturumunda ve AYNI hash zincirinde:

1. ``baslat``      PROBLEM → PLAN: soru türü şablonundan hipotez seti (birincil +
                   RAK rakipleri + H_bilinmeyen) ve analiz parametreleri.
2. ``hipotez_ekle`` (isteğe bağlı, yalnız PLAN'da, kilitten önce) serbest metinli
                   rakip; makinece sınanamaz → hep "çözülmedi" (hüküm en çok KIRILGAN).
3. ``kanit_bagla`` doğrulayıcıda protokol (hipotezler + parametreler + sürümler)
                   veriden ÖNCE kilitlenir; VERİ (profil + kapı) → ANALİZ (sınamalar,
                   her biri gerekçeli adım).
4. ``hukum_uret``  kanıt paketi dondurulur, hash'i zincire taahhüt edilir. SONUÇ
                   fazına geçilmez: hüküm taslaktır, insan onayı dongu_sonuc ile verilir.

``sinama_plani`` saf okumadır: hangi aracın hangi öngörüyü sınadığını ve verilen
parametrelerle neyin ÖNCEDEN çözülemeyeceğini veriye bakmadan söyler. ``rehberli``
bu adımların tek deterministik bileşimidir (Rehberli yüz); ayrıntılı araçlar dil
modeli ve Atölye içindir. Durum ``manifesto["bilimsel"]`` içinde kalıcıdır.
"""
import json

from ..cekirdek import veri
from ..cekirdek.hatalar import KullanimHatasi
from ..surec import dongu, kanit, kilit
from . import hukum, rak, sablon, sinamalar

URUN_TURU = {"ARTIS": "stratejik", "YOGUNLASMA": "taktik", "SERI": "sorun_cozme",
             "ETKI": "sorun_cozme"}
PARAMETRELER = ("kanal_alan", "mo_alan", "bolge_alan", "mudahale", "kontrol", "tampon",
                "kesinti_tarihi")
SERBEST_ONEK = "R-SERBEST-"
ETKI_DUZEYLERI = ("yüksek", "orta")
SERBEST_SINAMA = "v1'de makinece sınanamaz (serbest öngörü dili yok)"


def _kisa_ozet(ad, sonuc):
    """Manifestoya yazılan kısa sayısal özet (ham kayıt/kimlik yok)."""
    if isinstance(sonuc, list):
        return {"aday": len(sonuc), "guclu": sum(1 for c in sonuc if c.get("katman") == "güçlü")}
    if not isinstance(sonuc, dict):
        return {}
    alanlar = {"trend": ("egim", "p"), "t_testi": ("t", "p", "ortalama"),
               "sicak_nokta_gi": ("sicak", "soguk", "n")}.get(ad, ())
    return {k: sonuc.get(k) for k in alanlar if isinstance(sonuc.get(k), (int, float))}


def _bilimsel(d):
    """Oturumun bilim durumu; bilim çalışması değilse kullanım hatası."""
    b = d.manifesto.get("bilimsel")
    if not b:
        raise KullanimHatasi("bu oturum bir bilim çalışması değil",
                             oneri="calisma_baslat (ya da rehberli_calisma) ile açın")
    return b


def _protokol_metni(b):
    """Kilidin dondurduğu protokol: hipotez seti + analiz parametreleri + sürümler.
    Parametreler (kontrol bölgesi, kesinti tarihi, kanal alanı...) araştırmacının
    serbestlik derecesidir; veriden önce sabitlenmezse ön-kayıt eksik kalır."""
    return json.dumps({"hipotezler": b["hipotezler"], "parametreler": b["parametreler"],
                       "surumler": {"rak": b["rak_surumu"], "sablon": b["sablon_surumu"],
                                    "kural": b["kural_surumu"],
                                    "sinama": sinamalar.SINAMA_SURUMU}},
                      ensure_ascii=False, sort_keys=True)


def baslat(soru_turu, amac, onaylayan=None, soru=None, **parametreler):
    """Adım 1 — çalışmayı başlatır: döngü (PROBLEM → PLAN) + hipotez seti.

    Args:
        soru_turu: ARTIS | YOGUNLASMA | SERI | ETKI.
        amac: dogrulayici | kesifsel | operasyonel.
        onaylayan: doğrulayıcı çalışmada kilidi alacak kişi (zorunlu).
        soru: kullanıcının soru metni (kayıt için).
        **parametreler: analiz parametreleri (PARAMETRELER): ARTIS'te kanal_alan
            (R-BILDIRIM için), SERI'de mo_alan (zorunlu), ETKİ'de bolge_alan, mudahale,
            kesinti_tarihi (zorunlu) ile kontrol, tampon (isteğe bağlı — yoksa ilgili
            rakipler çözülemez).

    Returns:
        PLAN fazındaki AnalizDongusu (henüz diske yazılmamış).
    """
    bilinmeyen = set(parametreler) - set(PARAMETRELER)
    if bilinmeyen:
        raise KullanimHatasi(f"bilinmeyen parametre: {sorted(bilinmeyen)}")
    p = {k: v for k, v in parametreler.items() if v not in (None, "")}
    if soru_turu not in sablon.SABLONLAR:
        raise KullanimHatasi(f"soru_turu şunlardan biri olmalı: {list(sablon.TURLER)}")
    if amac not in kilit.AMACLAR:
        raise KullanimHatasi(f"amac şunlardan biri olmalı: {list(kilit.AMACLAR)}")
    if amac == "dogrulayici" and not (onaylayan or "").strip():
        raise KullanimHatasi("doğrulayıcı çalışmada 'onaylayan' zorunlu: hipotez seti "
                             "veriden önce onun adıyla kilitlenir")
    if soru_turu == "SERI" and not p.get("mo_alan"):
        raise KullanimHatasi("SERI sorusu için mo_alan zorunlu")
    if soru_turu == "ETKI":
        if not all(p.get(k) for k in ("bolge_alan", "mudahale", "kesinti_tarihi")):
            raise KullanimHatasi("ETKI sorusu için bolge_alan, mudahale ve kesinti_tarihi zorunlu")
        if veri.tarih_coz(p["kesinti_tarihi"]) is None:
            raise KullanimHatasi("kesinti_tarihi çözülemedi")

    d = dongu.AnalizDongusu({"karar": soru or f"{soru_turu} sorusu", "soru_turu": soru_turu,
                             "urun_turu": URUN_TURU[soru_turu]}, mod="resmi", amac=amac)
    d.planla()
    hipotezler = sablon.hipotez_seti(soru_turu)
    set_metni = json.dumps(hipotezler, ensure_ascii=False, sort_keys=True)
    d.manifesto["bilimsel"] = {"surum": "bilim-v1", "soru_turu": soru_turu,
                               "hipotezler": hipotezler, "rak_surumu": rak.RAK_SURUMU,
                               "sablon_surumu": sablon.SABLON_SURUMU,
                               "kural_surumu": hukum.KURAL_SURUMU,
                               "parametreler": p, "onaylayan": onaylayan}
    d.bilimsel_kaydet("hipotez_seti", {"hipotez_sayisi": len(hipotezler)},
                      {"hipotez": set_metni, "yorum": "şablondan kuruldu; H_bilinmeyen zorunlu"})
    return d


def hipotez_ekle(d, ifade, mekanizma=None, sonraki_kanit=None, etki="yüksek"):
    """Adım 2 (isteğe bağlı) — serbest metinli rakip açıklama ekler.

    Yalnız PLAN fazında ve kilitten önce (veriye bakılmadan). Serbest rakibin
    makinece sınanabilir öngörüsü yoktur (v1): kanıtta hep "çözülmedi" kalır, bu
    yüzden hüküm en çok KIRILGAN olur. H_bilinmeyen korunur (hep sonda; silinemez,
    değiştirilemez) ve şablon hipotezleri değiştirilemez.

    Args:
        d: bilim çalışmasının döngüsü.
        ifade: rakip açıklamanın bir cümlelik ifadesi.
        mekanizma: deseni nasıl üreteceği (isteğe bağlı).
        sonraki_kanit: bu rakibi ayırt edecek veri ya da sınama (isteğe bağlı).
        etki: 'yüksek' | 'orta' (varsayılan ihtiyatlı: yüksek).

    Returns:
        Eklenen hipotez kaydı.
    """
    b = _bilimsel(d)
    if d.manifesto.get("kilit"):
        raise kilit.KilitHatasi("protokol kilitli: ön-kayıttan sonra hipotez eklenemez",
                                oneri="protokolü değiştirmeniz gerekiyorsa yeni bir çalışma açın")
    if d.manifesto["faz"] != "PLAN":
        raise KullanimHatasi(f"hipotez yalnız PLAN fazında (veriye bakılmadan) eklenir; "
                             f"mevcut faz: {d.manifesto['faz']}",
                             oneri="veriden sonra düşünülen açıklama yeni bir keşifsel çalışmadır")
    if not (ifade or "").strip():
        raise KullanimHatasi("ifade boş olamaz")
    if etki not in ETKI_DUZEYLERI:
        raise KullanimHatasi(f"etki şunlardan biri olmalı: {list(ETKI_DUZEYLERI)}")
    sira = 1 + sum(1 for h in b["hipotezler"] if h["kimlik"].startswith(SERBEST_ONEK))
    yeni = {"kimlik": f"{SERBEST_ONEK}{sira}", "tur": "RAKIP", "serbest": True,
            "ifade": ifade.strip(), "mekanizma": (mekanizma or "").strip(),
            "sinama": SERBEST_SINAMA, "etki": etki,
            "sonraki_kanit": (sonraki_kanit or "").strip()
            or "bu açıklamayı ayırt edecek veri ya da sınama (tanımlanmadı)"}
    # H_bilinmeyen her zaman son hipotezdir; ekleme onun ÖNÜNE yapılır
    b["hipotezler"].insert(len(b["hipotezler"]) - 1, yeni)
    d.bilimsel_kaydet("hipotez_ekle", {"kimlik": yeni["kimlik"]},
                      {"hipotez": json.dumps(yeni, ensure_ascii=False, sort_keys=True),
                       "yorum": "serbest rakip: makinece sınanamaz → çözülmedi"})
    return yeni


def _rakip_plani(kod, p):
    """Bir katalog rakibinin sınama planı: parametrelerden ÖNCEDEN çözülemez mi."""
    k = rak.KATALOG[kod]
    cozulebilir, gereksinim = True, None
    if kod == "R-BILDIRIM" and not p.get("kanal_alan"):
        cozulebilir, gereksinim = False, "kanal/kaynak alanı verilmedi (kanal_alan)"
    elif kod == "R-PAYDA":
        cozulebilir, gereksinim = False, "v1'de risk altındaki nüfus/hedef girdisi yok"
    elif kod == "R-ESZAMANLI" and not p.get("kontrol"):
        cozulebilir, gereksinim = False, "kontrol bölgesi verilmedi"
    elif kod == "R-YER-DEGISTIRME" and not (p.get("tampon") and p.get("kontrol")):
        cozulebilir, gereksinim = False, "tampon ve kontrol bölgesi birlikte gerekir"
    elif kod == "R-MEVSIM":
        gereksinim = "veriye bağlı: en az 24 ay"
    elif kod == "R-ORTALAMAYA-DONUS":
        gereksinim = (f"veriye bağlı: müdahale öncesi son {sinamalar.SON_DONEM_GUN} günden "
                      f"önce en az {sinamalar.SON_DONEM_GUN} günlük temel dönem")
    return {"kod": kod, "sinama": k["sinama"], "cozulebilir": cozulebilir,
            "gereksinim": gereksinim, "sonraki_kanit": k["sonraki_kanit"]}


def sinama_plani(d):
    """Sınama planı — saf okuma (zincire yazmaz), veriye BAKMADAN.

    Hangi aracın birincil öngörüyü sınadığını, her rakibin ayırt edici sınamasını ve
    verilen parametrelerle hangi rakiplerin ÖNCEDEN çözülemeyeceğini söyler; buradan
    ulaşılabilir en üst kategori (tavan) ve nedenleri çıkar. Plan hipotez seti,
    parametreler ve sürümlerin deterministik işlevidir: kilit onu da kapsar.

    Args:
        d: bilim çalışmasının döngüsü.

    Returns:
        {soru_turu, amac, birincil, rakipler, ulasilabilir_en_ust, tavan_nedenleri,
         sinama_surumu}
    """
    b = _bilimsel(d)
    tur, p = b["soru_turu"], b["parametreler"]
    s = sablon.SABLONLAR[tur]
    arac = s["ongoru"]["arac"]
    if tur == "ETKI" and not p.get("kontrol"):
        arac = "kesinti_analizi"
    birincil = {"hipotez": "H1", "arac": arac, "kosul": s["ongoru"]["kosul"],
                "kapi_araci": s.get("kapi_araci", s["ongoru"]["arac"]),
                "gerekli_alanlar": list(s["gerekli_alanlar"])}
    rakipler = []
    for h in b["hipotezler"]:
        if h["tur"] != "RAKIP":
            continue
        if h.get("serbest"):
            rakipler.append({"kod": h["kimlik"], "sinama": SERBEST_SINAMA, "cozulebilir": False,
                             "gereksinim": "serbest rakip", "sonraki_kanit": h["sonraki_kanit"]})
        else:
            rakipler.append(_rakip_plani(h["kimlik"], p))
    nedenler = []
    if d.manifesto.get("amac") != "dogrulayici":
        nedenler.append(f"{d.manifesto.get('amac')} çalışma en çok KIRILGAN")
    if tur in hukum.TAVANLI_TURLER:
        nedenler.append("SERİ en çok KIRILGAN: desen ≠ fail")
    nedenler += [f"önceden çözülemez rakip: {r['kod']} ({r['gereksinim']})"
                 for r in rakipler if not r["cozulebilir"]]
    return {"soru_turu": tur, "amac": d.manifesto.get("amac"), "birincil": birincil,
            "rakipler": rakipler,
            "ulasilabilir_en_ust": "KIRILGAN" if nedenler else "DESTEKLENDİ",
            "tavan_nedenleri": nedenler, "sinama_surumu": sinamalar.SINAMA_SURUMU}


def kanit_bagla(d, kaynak, kayitlar, yurut_ham, kapi_karari):
    """Adım 3 — kilit (doğrulayıcıda) → VERİ (profil + kapı) → ANALİZ (sınamalar).

    Args:
        d: PLAN fazındaki bilim çalışmasının döngüsü.
        kaynak: araçlara iletilecek veri kaynağı ({'satirlar': ...} ya da {'csv_yolu': ...}).
        kayitlar: aynı kaynağın tiplenmiş kayıtları (yerel denetimler için).
        yurut_ham: (ad, arg) → araç sonucu (resmi yol: şema + kapı + hesap).
        kapi_karari: (ad, arg) → aracın TEK kapı otoritesinden karar
            ({uygun, sebepler, ...}); oturum kapısı tahmini bir analiz adıyla
            değil, birincil sınamayı koşacak aracın kendi kapısıyla verilir.

    Returns:
        {birincil, rakipler, saglamlik, sinamalar} — manifestoya da yazılır.
    """
    b = _bilimsel(d)
    if d.manifesto["faz"] != "PLAN":
        raise KullanimHatasi(f"kanıt yalnız bir kez ve PLAN fazında bağlanır; mevcut faz: "
                             f"{d.manifesto['faz']}", oneri="hukum ile hükmü alın")
    tur, p = b["soru_turu"], b["parametreler"]
    if d.manifesto.get("amac") == "dogrulayici":
        d.protokol_kilitle(_protokol_metni(b), b["onaylayan"])

    profil = veri.veri_profili(kayitlar)
    d.veri_bagla(profil)
    kapi_araci = sablon.SABLONLAR[tur].get("kapi_araci", sablon.SABLONLAR[tur]["ongoru"]["arac"])
    arg0 = {**kaynak, "mo_alan": p["mo_alan"]} if tur == "SERI" else dict(kaynak)
    uygunluk = kapi_karari(kapi_araci, arg0)
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

        def kaydet(ad, ozet, hipotez, amac_metni):
            """Araç dışı yerel sınamayı gerekçeli ANALİZ adımı olarak kaydeder."""
            d.analiz_kaydet(ad, ozet, {"hipotez": hipotez, "yorum": amac_metni})
            sinama_izi.append({"arac": ad, "hipotez": hipotez, "amac": amac_metni})

        if tur == "ARTIS":
            birincil, rakipler, saglamlik = sinamalar.artis(kaynak, kayitlar, yurut,
                                                            p.get("kanal_alan"), kaydet)
        elif tur == "YOGUNLASMA":
            birincil, rakipler, saglamlik = sinamalar.yogunlasma(kaynak, kayitlar, yurut)
        elif tur == "ETKI":
            birincil, rakipler, saglamlik = sinamalar.etki(
                kaynak, kayitlar, yurut, kaydet, p["bolge_alan"], p["mudahale"],
                p["kesinti_tarihi"], kontrol=p.get("kontrol"), tampon=p.get("tampon"))
        else:
            birincil, rakipler, saglamlik = sinamalar.seri(kaynak, kayitlar, yurut, p["mo_alan"])
    else:
        neden = "; ".join(uygunluk.get("sebepler") or []) or "veri uygun değil"
        birincil = {"durum": "sınanamadı", "gerekce": f"kapı reddi: {neden}"}
        rakipler = [sinamalar._rakip(k, "çözülmedi", "veri analize uygun değil")
                    for k in rak.uygulanabilir(tur)]
        saglamlik = []
    # serbest rakipler katalog rakiplerinden SONRA; makinece sınanamaz → çözülmedi
    rakipler += [{"kod": h["kimlik"], "durum": "çözülmedi", "etki": h["etki"],
                  "gerekce": "serbest rakip: v1'de makinece sınanabilir öngörüsü yok",
                  "sonraki_kanit": h["sonraki_kanit"]}
                 for h in b["hipotezler"] if h.get("serbest")]
    b["kanit"] = {"birincil": birincil, "rakipler": rakipler, "saglamlik": saglamlik,
                  "sinamalar": sinama_izi}
    return b["kanit"]


def _onkayit_gecerli(d, b):
    """Ön-kayıt GEÇERLİ mi: kilit var, bütünlüğü ve sırası sağlam (kilitten önce
    analiz yok), amaç doğrulayıcı ve kilitli protokol hüküm anındaki protokolle
    aynı. Kilidin yalnız varlığı yetmez (A4.14)."""
    kayit = d.manifesto.get("kilit")
    return bool(kayit and d.onkayit_dogrula()["dogrulayici_iddia_edilebilir"]
                and kayit.get("hipotez") == _protokol_metni(b))


def hukum_uret(d, log_dir):
    """Adım 4 — kanıt paketini dondurur, kategorik hükmü üretir ve zincire taahhüt eder.

    Hüküm bir kez üretilir; yeniden çağrı dondurulmuş hükmü aynen döndürür (zincire
    yeni olay yazılmaz).

    Args:
        d: kanıtı bağlanmış bilim çalışmasının döngüsü.
        log_dir: oturum ve kanıt zinciri dizini.

    Returns:
        {oturum_id, soru_turu, amac, kilit_hash, hipotezler, sinamalar, hukum}
    """
    b = _bilimsel(d)
    if "kanit" not in b:
        raise KullanimHatasi("hüküm için önce kanıt bağlanmalı", oneri="kanit_bagla çağırın")
    if "hukum" not in b:
        k = b["kanit"]
        dongu.kaydet(d, log_dir)
        zincir = kanit.dogrula(log_dir, d.manifesto["oturum_id"])
        paket = {"soru_turu": b["soru_turu"], "amac": d.manifesto.get("amac"),
                 "sinama_surumu": sinamalar.SINAMA_SURUMU,
                 "kilitli": _onkayit_gecerli(d, b),
                 "zincir_saglam": bool(zincir.get("saglam")), "birincil": k["birincil"],
                 "rakipler": k["rakipler"], "saglamlik": k["saglamlik"]}
        h = hukum.hukum_ver(paket)
        b.update({"paket": paket, "hukum": h})
        d.bilimsel_kaydet("hukum", {"rakip_sayisi": len(k["rakipler"])},
                          {"hipotez": "H1", "yorum": h["ifade"], "kategori": h["kategori"],
                           "paket_hash": h["paket_hash"], "kural_surumu": h["kural_surumu"]})
        dongu.kaydet(d, log_dir)
    return {"oturum_id": d.manifesto["oturum_id"], "soru_turu": b["soru_turu"],
            "amac": d.manifesto.get("amac"),
            "kilit_hash": (d.manifesto.get("kilit") or {}).get("hash"),
            "hipotezler": b["hipotezler"], "sinamalar": b["kanit"]["sinamalar"],
            "hukum": b["hukum"]}


def rehberli(kaynak, kayitlar, soru_turu, amac, log_dir, yurut_ham, kapi_karari,
             onaylayan=None, soru=None, **parametreler):
    """Rehberli çalışma: baslat → kanit_bagla → hukum_uret tek deterministik akışta.

    Args:
        kaynak, kayitlar, yurut_ham, kapi_karari: bkz. kanit_bagla.
        soru_turu, amac, onaylayan, soru, **parametreler: bkz. baslat.
        log_dir: oturum ve kanıt zinciri dizini.

    Returns:
        {oturum_id, soru_turu, amac, kilit_hash, hipotezler, sinamalar, hukum}
    """
    d = baslat(soru_turu, amac, onaylayan=onaylayan, soru=soru, **parametreler)
    kanit_bagla(d, kaynak, kayitlar, yurut_ham, kapi_karari)
    return hukum_uret(d, log_dir)
