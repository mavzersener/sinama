# -*- coding: utf-8 -*-
r"""
arayuz/araclar.py — 57 MCP aracı: çekirdek modüller üstünde ince
adaptörler (v6.1, G1). Gate mantığı BURADA YOKTUR; bağlam kancaları
ortak.py'de, karar kalite.kapi'de, uygulama dispatch'tedir.
"""

from ..cekirdek import (veri, istatistik, zaman, mekan, tekrar, ag, kume,
                        skor, orneklem, iliski, olcek, degerlendirme, ileri,
                        hipotez, regresyon, zarar, mekansal_istatistik, teori,
                        oneri)
from ..cekirdek.hatalar import VeriHatasi, KullanimHatasi
from ..surec import dongu, rapor
from ..bilim import calisma
from ..kalite.kapi import KapiRed
from .ortak import (arac, sema, S_KAYIT, ALANLAR_PROP, ALAN, SEMA_IKI,
                    SEMA_GRUP, SEMA_REG, ARACLAR, kayitlari_getir,
                    noktalari_getir, quadratic_guard, kapsam_uret,
                    kayitlari_kisitla, sayisal_vektor, grup_vektorleri,
                    iki_vektor, _matris_getir, _reg_hazirla, arac_yurut,
                    baglam, _log_dir, dispatch_gate, ARAC_GATE)
from ..cekirdek.kaynak_butce import _sim_butce, _pozitif

@arac("veri_ozeti", "Kayıt sayısı, alanlar ve eksik veri raporu", S_KAYIT)
def _(a):
    k = kayitlari_getir(a)
    return {"satir_sayisi": len(k),
            "kesildi": veri.son_okuma.get("kesildi", False),
            "alanlar": list(k[0].keys()) if k else [],
            "eksik": veri.eksik_raporu(k)}



@arac("frekans", "Bir alanın değer dağılımı", sema(ALAN, ["alan"]))
def _(a):
    return dict(istatistik.frekans(kayitlari_getir(a), a["alan"]))



@arac("capraz_tablo", "İki kategorik alanın çapraz tablosu",
      sema({"a": {"type": "string"}, "b": {"type": "string"}}, ["a", "b"]))
def _(a):
    return istatistik.capraz_tablo(kayitlari_getir(a), a["a"], a["b"])



@arac("saat_dagilimi", "0-23 saat dilimi olay dağılımı", S_KAYIT)
def _(a):
    return zaman.saat_dagilimi(kayitlari_getir(a))



@arac("gun_dagilimi", "Haftanın günü dağılımı (0=Pzt)", S_KAYIT)
def _(a):
    return zaman.gun_dagilimi(kayitlari_getir(a))



@arac("ay_serisi", "Ay bazlı olay serisi", S_KAYIT)
def _(a):
    return zaman.ay_dagilimi(kayitlari_getir(a))



@arac("aoristik", "Aoristik saat dağılımı: belirsiz (aralık) olay zamanları için",
      sema({"bas_alan": {"type": "string", "default": "baslangic"},
            "bit_alan": {"type": "string", "default": "bitis"}}))
def _(a):
    k = kayitlari_getir(a)
    return {"dagilim": zaman.aoristik_dagilim(
        k, a.get("bas_alan", "baslangic"), a.get("bit_alan", "bitis")),
        "not": ("her olay, başlangıç-bitiş aralığındaki saatlere 1/uzunluk "
                "ağırlıkla yayılır; orta nokta atamaktan daha dürüst (R09).")}



@arac("trend", "Günlük seride doğrusal trend", S_KAYIT)
def _(a):
    _, seri = zaman.gunluk_seri(kayitlari_getir(a))
    return istatistik.dogrusal_trend(seri)



@arac("grid_hotspot", "Grid hotspot: hücre başına olay sayısı",
      sema({"hucre_km": {"type": "number", "default": 0.5}}))
def _(a):
    k = kayitlari_getir(a)
    pts = [q for q in (veri.koordinat_al(r) for r in k) if q]
    quadratic_guard(pts, "grid_hotspot")
    return {"hucreler": mekan.grid_hotspot(pts, a.get("hucre_km", 0.5))[:50],
            "kapsam": kapsam_uret(k, len(pts), "geçersiz/eksik koordinat")}



@arac("mekansal_kumelenme",
      "Global Moran's I: olay dağılımı kümeli mi, dağınık mı, rastgele mi",
      sema({"hucre_km": {"type": "number", "default": 0.5},
            "bant_km": {"type": "number",
                        "description": "komşuluk eşiği (boş=otomatik)"}}))
def _(a):
    k = kayitlari_getir(a)
    pts = [q for q in (veri.koordinat_al(r) for r in k) if q]
    quadratic_guard(pts, "mekansal_kumelenme")
    hucre_km = a.get("hucre_km", 0.5)
    hucreler = mekan.grid_hotspot(pts, hucre_km)
    # bant verilmezse grid-farkında varsayılan: komşu hücreler (köşegen dahil)
    bant = a.get("bant_km") or hucre_km * 1.5
    sonuc = mekansal_istatistik.global_moran(hucreler, bant)
    sonuc["kapsam"] = kapsam_uret(k, len(pts), "geçersiz/eksik koordinat")
    return sonuc



@arac("sicak_nokta_gi",
      "Getis-Ord Gi*: istatistiksel anlamlı sıcak/soğuk noktalar (z + güven)",
      sema({"hucre_km": {"type": "number", "default": 0.5},
            "bant_km": {"type": "number",
                        "description": "komşuluk eşiği (boş=otomatik)"}}))
def _(a):
    k = kayitlari_getir(a)
    pts = [q for q in (veri.koordinat_al(r) for r in k) if q]
    quadratic_guard(pts, "sicak_nokta_gi")
    hucre_km = a.get("hucre_km", 0.5)
    hucreler = mekan.grid_hotspot(pts, hucre_km)
    bant = a.get("bant_km") or hucre_km * 1.5
    sonuc = mekansal_istatistik.getis_ord(hucreler, bant)
    if "sonuclar" in sonuc:
        sonuc["sonuclar"] = sonuc["sonuclar"][:100]
    sonuc["kapsam"] = kapsam_uret(k, len(pts), "geçersiz/eksik koordinat")
    return sonuc



@arac("analiz_oner",
      "Karar ağacı önericisi: veri yapısı + soruya göre uygun analizleri (mevcut/yok) sıralar",
      sema({"soru": {"type": "string", "description": "kullanıcının sorusu (opsiyonel)"},
            "maks": {"type": "number", "default": 6}}))
def _(a):
    k = kayitlari_getir(a)
    return oneri.oner(k, a.get("soru"), int(a.get("maks", 6)))



@arac("teori_yorumu",
      "Kriminolojik teori yorumu: bir bulguyu (sıcak nokta/aykırı/tekrar...) teoriye + müdahaleye bağlar",
      {"type": "object",
       "properties": {"bulgu": {"type": "string",
                                "description": "bulgu türü (bkz. gecerli_bulgular)"}},
       "required": ["bulgu"]})
def _(a):
    return teori.yorumla(a["bulgu"])



@arac("risk_arazi",
      "Risk Terrain Modeling: çevresel risk faktörlerinden kalıcı risk yüzeyi",
      sema({"faktor_alan": {"type": "string",
                            "description": "risk faktörü tür alanı (ör. tesis_turu)"},
            "hucre_km": {"type": "number", "default": 0.3},
            "yaricap_km": {"type": "number", "default": 0.4}},
           ["faktor_alan"]))
def _(a):
    k = kayitlari_getir(a)
    alan = a["faktor_alan"]
    faktorler = []
    for r in k:
        q = veri.koordinat_al(r)
        t = r.get(alan)
        if q and t is not None and t != "":
            faktorler.append((q[0], q[1], t))
    quadratic_guard(faktorler, "risk_arazi")
    sonuc = mekansal_istatistik.risk_arazi(
        faktorler, a.get("hucre_km", 0.3), a.get("yaricap_km", 0.4))
    sonuc["kapsam"] = kapsam_uret(k, len(faktorler), "geçersiz koordinat/tür")
    return sonuc



@arac("mekansal_regresyon",
      "Mekânsal regresyon tanısı: OLS + artık otokorelasyonu (mekânsal model gerekli mi)",
      sema({"hedef": {"type": "string", "description": "bağımlı alan (ör. olay_sayisi)"},
            "degiskenler": {"type": "array", "description": "bağımsız alan adları"},
            "bant_km": {"type": "number", "description": "komşuluk (boş=otomatik)"}},
           ["hedef", "degiskenler"]))
def _(a):
    X, y, degiskenler, koord, kapsam = _reg_hazirla(a, mekansal=True)
    sonuc = mekansal_istatistik.mekansal_regresyon_tani(y, X, koord, degiskenler,
                                                       a.get("bant_km"))
    if isinstance(sonuc, dict):
        sonuc['kapsam'] = kapsam
    return sonuc



@arac("cografi_profil",
      "Coğrafi profilleme: seri suçtan failin olası çapa (ikamet) bölgesi",
      sema({"hucre_km": {"type": "number", "default": 0.3},
            "decay_km": {"type": "number", "description": "azalım ölçeği (boş=otomatik)"},
            "buffer_km": {"type": "number", "default": 0,
                          "description": "Rossmo tampon bölgesi (0=Dragnet)"}}))
def _(a):
    k = kayitlari_getir(a)
    pts = [q for q in (veri.koordinat_al(r) for r in k) if q]
    quadratic_guard(pts, "cografi_profil")
    sonuc = mekansal_istatistik.cografi_profil(
        pts, a.get("hucre_km", 0.3), a.get("decay_km"), a.get("buffer_km", 0))
    sonuc["kapsam"] = kapsam_uret(k, len(pts), "geçersiz/eksik koordinat")
    return sonuc



@arac("merkezsel_egilim",
      "Sentrografik: ortalama merkez + standart mesafe + sapma elipsi (yayılım yönü)",
      sema({"agirlik_alan": {"type": "string",
                             "description": "opsiyonel ağırlık alanı (ör. zarar_tl)"}}))
def _(a):
    k = kayitlari_getir(a)
    alan = a.get("agirlik_alan")
    pts, agr = [], []
    for r in k:
        q = veri.koordinat_al(r)
        if not q:
            continue
        pts.append(q)
        if alan:
            try:
                agr.append(float(r.get(alan)))
            except (TypeError, ValueError):
                agr.append(0.0)
    quadratic_guard(pts, "merkezsel_egilim")
    sonuc = mekansal_istatistik.merkezsel(pts, agr if alan else None)
    sonuc["kapsam"] = kapsam_uret(k, len(pts), "geçersiz/eksik koordinat")
    return sonuc



@arac("yerel_kumeleme",
      "Local Moran's I (LISA): sıcak/soğuk küme vs mekânsal aykırı değer (HH/LL/HL/LH)",
      sema({"hucre_km": {"type": "number", "default": 0.5},
            "bant_km": {"type": "number",
                        "description": "komşuluk eşiği (boş=otomatik)"}}))
def _(a):
    k = kayitlari_getir(a)
    pts = [q for q in (veri.koordinat_al(r) for r in k) if q]
    quadratic_guard(pts, "yerel_kumeleme")
    hucre_km = a.get("hucre_km", 0.5)
    hucreler = mekan.grid_hotspot(pts, hucre_km)
    bant = a.get("bant_km") or hucre_km * 1.5
    sonuc = mekansal_istatistik.yerel_moran(hucreler, bant)
    if "sonuclar" in sonuc:
        sonuc["sonuclar"] = sonuc["sonuclar"][:100]
    sonuc["kapsam"] = kapsam_uret(k, len(pts), "geçersiz/eksik koordinat")
    return sonuc



def _bolge_donem_serileri(kayitlar, bolge_alan, zaman_alan, donem):
    """Kayıtları bölge×dönem sayım serilerine böler (zaman aralığı donem eşit
    parçaya). Dönüş: ({bolge: [c0..c(donem-1)]}, gecerli_sayi)."""
    olaylar = []
    for r in kayitlar:
        b = r.get(bolge_alan)
        d = veri.tarih_coz(r.get(zaman_alan))
        if b is not None and b != "" and d is not None:
            olaylar.append((str(b), d))
    if not olaylar:
        return {}, 0
    zamanlar = [d for _, d in olaylar]
    t0, t1 = min(zamanlar), max(zamanlar)
    aralik = (t1 - t0).total_seconds() or 1.0
    seriler = {}
    for b, d in olaylar:
        idx = int((d - t0).total_seconds() / aralik * donem)
        idx = min(idx, donem - 1)
        seriler.setdefault(b, [0] * donem)[idx] += 1
    return seriler, len(olaylar)


@arac("yukselen_sicak_nokta",
      "Emerging Hotspot: bölgeleri kalıcı/yoğunlaşan/yeni/sönen/tarihsel sınıflar",
      sema({"bolge_alan": {"type": "string"}, "zaman_alan": {"type": "string"},
            "donem_sayisi": {"type": "number", "default": 4}},
           ["bolge_alan", "zaman_alan"]))
def _(a):
    k = kayitlari_getir(a)
    donem = int(a.get("donem_sayisi", 4))
    seriler, gecerli = _bolge_donem_serileri(k, a["bolge_alan"], a["zaman_alan"], donem)
    sonuc = mekansal_istatistik.emerging_hotspot(seriler)
    if "sonuclar" in sonuc:
        sonuc["sonuclar"] = sonuc["sonuclar"][:100]
    sonuc["kapsam"] = kapsam_uret(k, gecerli, "geçersiz bölge/zaman")
    return sonuc



@arac("konsantrasyon_dagilimi",
      "CCDI: suç artışı eski sıcak noktalardan mı (yoğunlaşma) yeni alanlardan mı (dağılma)",
      sema({"bolge_alan": {"type": "string"}, "zaman_alan": {"type": "string"}},
           ["bolge_alan", "zaman_alan"]))
def _(a):
    k = kayitlari_getir(a)
    seriler, _g = _bolge_donem_serileri(k, a["bolge_alan"], a["zaman_alan"], 2)
    bolgeler = sorted(seriler)
    once = [seriler[b][0] for b in bolgeler]
    sonra = [seriler[b][1] for b in bolgeler]
    return mekansal_istatistik.konsantrasyon_dagilim(once, sonra)



@arac("esitlik_analizi",
      "Dağılım eşitsizliği: Gini + bölgesel disparite (adalet-kısıtlı kaynak)",
      sema({"alan": {"type": "string",
                     "description": "bölge/grup alanı (ör. grid_id, bolge)"}},
           ["alan"]))
def _(a):
    k = kayitlari_getir(a)
    alan = a["alan"]
    sayim = istatistik.frekans(k, alan)
    return {**mekansal_istatistik.esitlik(list(sayim.values())),
            "bolge_sayisi": len(sayim), "alan": alan}



@arac("kde_yogunluk", "KDE ısı yoğunluğu (saf Python)",
      sema({"bant_km": {"type": "number", "default": 0.4},
            "hucre_km": {"type": "number", "default": 0.3}}))
def _(a):
    k = kayitlari_getir(a)
    pts = [q for q in (veri.koordinat_al(r) for r in k) if q]
    quadratic_guard(pts, "kde_yogunluk")
    mekan._kde_butce(pts, a.get('bant_km', .4), a.get('hucre_km', .3))
    return {"hucreler": mekan.kde_yogunluk(pts, a.get("bant_km", 0.4),
                              a.get("hucre_km", 0.3))[:100],
            "kapsam": kapsam_uret(k, len(pts), "geçersiz/eksik koordinat")}



@arac("nni", "NNI + z-testi ile kümelenme anlamlılığı (kenar_duzeltme=true "
      "ile Donnelly kenar düzeltmesi, v6.3)",
      sema({"kenar_duzeltme": {"type": "boolean"},
            "cevre_km": {"type": "number"}}))
def _(a):
    k = kayitlari_getir(a)
    pts = [q for q in (veri.koordinat_al(r) for r in k) if q]
    quadratic_guard(pts, "nni")
    sonuc = mekan.nni_test(pts,
                           kenar_duzeltme=bool(a.get("kenar_duzeltme")),
                           cevre_km=a.get("cevre_km")) or {}
    sonuc["kapsam"] = kapsam_uret(k, len(pts), "geçersiz/eksik koordinat")
    return sonuc


@arac("oran_karsilastir", "İki Poisson oranının koşullu exact karşılaştırması "
      "(v6.3): RR + Clopper-Pearson GA + exact p. Ör: öncesi/sonrası, "
      "müdahale/kontrol bölgesi",
      {"type": "object",
       "properties": {"k1": {"type": "integer"}, "e1": {"type": "number"},
                      "k2": {"type": "integer"}, "e2": {"type": "number"}},
       "required": ["k1", "e1", "k2", "e2"]})
def _(a):
    sonuc = iliski.iki_poisson_orani(a["k1"], a["e1"], a["k2"], a["e2"])
    if sonuc is None:
        raise VeriHatasi("maruz kalma (e1, e2) sıfırdan büyük olmalı",
                         oneri="kişi-yıl/kişi sayısı alanlarını denetleyin")
    return sonuc



@arac("mukerrer_magduriyet", "Aynı adres/mağdur için tekrar eden olaylar",
      sema(ALAN, ["alan"]))
def _(a):
    return tekrar.mukerrer_magduriyet(kayitlari_getir(a), a["alan"])



@arac("yakin_tekrar", "Near-repeat çiftleri; sim>0 ile Monte Carlo p-değeri",
      sema({"mesafe_km": {"type": "number", "default": 0.4},
            "gun": {"type": "integer", "default": 14},
            "sim": {"type": "integer", "default": 0}}))
def _(a):
    k = kayitlari_getir(a)
    quadratic_guard(k, "yakin_tekrar")
    _sim_butce(len(k), a.get('sim', 0), sifir_izinli=True)
    _pozitif(a.get('mesafe_km', .4), 'mesafe_km')
    gecerli = [r for r in k
               if r.get("tarih") is not None and veri.koordinat_al(r)]
    sonuc = {"ciftler": tekrar.yakin_tekrar_ciftleri(
        k, a.get("mesafe_km", 0.4), a.get("gun", 14))[:200],
        "kapsam": kapsam_uret(k, len(gecerli), "eksik tarih veya koordinat")}
    if a.get("sim", 0) > 0:
        sonuc["anlamlilik"] = tekrar.knox_anlamlilik(
            k, a.get("mesafe_km", 0.4), a.get("gun", 14), a["sim"])
    return sonuc



@arac("knox_tablosu", "Knox uzay-zaman tablosu; sim>0 ile MC anlamlılık",
      sema({"mesafe_km": {"type": "number", "default": 0.4},
            "gun": {"type": "integer", "default": 14},
            "sim": {"type": "integer", "default": 0}}))
def _(a):
    k = kayitlari_getir(a)
    quadratic_guard(k, "knox_tablosu")
    _sim_butce(len(k), a.get('sim', 0), sifir_izinli=True)
    _pozitif(a.get('mesafe_km', .4), 'mesafe_km')
    sonuc = {"tablo": {str(x): v for x, v in
                       tekrar.knox_tablosu(k).items()}}
    if a.get("sim", 0) > 0:
        sonuc["anlamlilik"] = tekrar.knox_anlamlilik(
            k, a.get("mesafe_km", 0.4), a.get("gun", 14), a["sim"])
    return sonuc



@arac("seri_eslestirme", "Seri suç ADAYI eşleştirme: kanıt hatları (MO ayırt edici "
      "paylaşım testi + FDR; uzay; zaman) ve katman (güçlü: hatlar örtüşür; zayıf: "
      "yalnız MO). Aday bir inceleme hipotezidir, aynı fail iddiası değildir",
      sema({"mo_alan": {"type": "string"},
            "esik": {"type": "number",
                     "description": "isteğe bağlı ek Ružička benzerlik alt sınırı (boş=yok)"},
            "mesafe_km": {"type": "number", "default": tekrar.SERI_MESAFE_KM},
            "gun": {"type": "integer", "default": tekrar.SERI_GUN},
            "q_esik": {"type": "number", "default": tekrar.SERI_Q,
                       "description": "MO testi için FDR düzeyi (0-1)"}}, ["mo_alan"]))
def _(a):
    k = kayitlari_getir(a)
    quadratic_guard(k, "seri_eslestirme")
    _pozitif(a.get("mesafe_km", tekrar.SERI_MESAFE_KM), "mesafe_km")
    q = a.get("q_esik", tekrar.SERI_Q)
    _pozitif(q, "q_esik")
    if q >= 1:
        raise KullanimHatasi("q_esik: 0 ile 1 arasında olmalı")
    return tekrar.seri_eslestirme(k, a["mo_alan"], a.get("esik"),
                                  a.get("mesafe_km", tekrar.SERI_MESAFE_KM),
                                  a.get("gun", tekrar.SERI_GUN), q)



@arac("gun_saat_analizi", "Gün×saat ısı matrisi + en riskli dilimler", S_KAYIT)
def _(a):
    m = ileri.gun_saat_matrisi(kayitlari_getir(a))
    return {"matris": {str(g): v for g, v in m.items()},
            "en_riskli": ileri.en_riskli_dilimler(m, 10)}



@arac("kontrol_grafigi", "Günlük seride ±3σ aşım günleri", S_KAYIT)
def _(a):
    _, seri = zaman.gunluk_seri(kayitlari_getir(a))
    return ileri.kontrol_grafigi(seri)



@arac("cusum", "Günlük seride kalıcı artış (CUSUM) alarmları", S_KAYIT)
def _(a):
    _, seri = zaman.gunluk_seri(kayitlari_getir(a))
    return ileri.cusum(seri)



@arac("bolge_anomali", "Bölge bazında Poisson anomali (p-değerli)",
      sema({"bolge_alan": {"type": "string"}}, ["bolge_alan"]))
def _(a):
    k = kayitlari_getir(a)
    sayim = {}
    for r in k:
        b = str(r.get(a["bolge_alan"]))
        sayim[b] = sayim.get(b, 0) + 1
    return ileri.bolge_anomali(sayim)



@arac("suc_oranlari", "100.000 nüfus başına oran + Poisson güven aralığı",
      {"type": "object",
       "properties": {"bolgeler": {"type": "array",
                      "description": "[{bolge, olay, nufus}]"}},
       "required": ["bolgeler"]})
def _(a):
    # gate artık dispatch yolunda merkezi (ARAC_GATE → kalite.kapi); v6.0
    return iliski.oran_tablosu(a["bolgeler"])



@arac("bolge_oran",
      "Bölge oranı: kayıtları bölgeye göre topla + nüfusa oranla (ham vs oran, R12)",
      sema({"bolge_alan": {"type": "string"},
            "nufus_alan": {"type": "string",
                           "description": "kayıt başına bölge nüfusu (opsiyonel)"}},
           ["bolge_alan"]))
def _(a):
    from collections import Counter
    k = kayitlari_getir(a)
    bolge_alan, nufus_alan = a["bolge_alan"], a.get("nufus_alan")
    sayim = Counter(str(r.get(bolge_alan)) for r in k if r.get(bolge_alan) not in (None, ""))
    nufus = {}
    if nufus_alan:
        for r in k:
            b = str(r.get(bolge_alan))
            if b not in nufus and r.get(nufus_alan) not in (None, ""):
                try:
                    nufus[b] = float(r.get(nufus_alan))
                except (TypeError, ValueError):
                    pass
    if not nufus_alan or not nufus:
        return {"sayimlar": dict(sayim.most_common()),
                "not": ("nüfus (payda) verilmedi; yalnız HAM SAYI. Bölge "
                        "nüfusları farklıysa ham sayı karşılaştırması yanıltıcıdır "
                        "(R12) — nufus_alan verin.")}
    veri = [{"bolge": b, "olay": sayim.get(b, 0), "nufus": nufus.get(b)}
            for b in sayim]
    return iliski.ham_oran_karsilastir(veri)



@arac("ki_kare_testi", "Ki-kare bağımsızlık testi (Yates/Cochran destekli)",
      sema({"a": {"type": "string"}, "b": {"type": "string"},
            "yates": {"type": "boolean", "default": False}}, ["a", "b"]))
def _(a):
    k = kayitlari_getir(a)
    av = sorted({str(r.get(a["a"])) for r in k})
    bv = sorted({str(r.get(a["b"])) for r in k})
    ai = {v: i for i, v in enumerate(av)}
    bi = {v: j for j, v in enumerate(bv)}
    tablo = [[0] * len(bv) for _ in av]
    for r in k:
        tablo[ai[str(r.get(a["a"]))]][bi[str(r.get(a["b"]))]] += 1
    sonuc = iliski.ki_kare(tablo, yates=a.get("yates", False))
    if sonuc:
        sonuc["satirlar"] = av
        sonuc["sutunlar"] = bv
        if a.get("_gate_karar"):  # merkezi kapı kararı (dispatch, v6.0)
            sonuc["gate"] = a["_gate_karar"]
    return sonuc



@arac("pearson", "İki sayısal alan için Pearson r ve r²",
      sema({"x": {"type": "string"}, "y": {"type": "string"}}, ["x", "y"]))
def _(a):
    k = kayitlari_getir(a)
    xs, ys = [], []
    for r in k:
        try:
            xs.append(float(r.get(a["x"])))
            ys.append(float(r.get(a["y"])))
        except (TypeError, ValueError):
            continue
    return iliski.pearson_r(xs, ys)



@arac("endeks_hesapla", "Ağırlıklı bileşik endeks (Index of Disorder)",
      sema({"gostergeler": {"type": "array"},
            "agirliklar": {"type": "object"},
            "tersler": {"type": "array"}}, ["gostergeler"]))
def _(a):
    return olcek.endeks_kur(kayitlari_getir(a), a["gostergeler"],
                            a.get("agirliklar"), a.get("tersler"))



@arac("degerlendirme_did", "Farkların farkı ile müdahale etkisi",
      {"type": "object",
       "properties": {"mudahale_once": {"type": "number"},
                      "mudahale_sonra": {"type": "number"},
                      "kontrol_once": {"type": "number"},
                      "kontrol_sonra": {"type": "number"}},
       "required": ["mudahale_once", "mudahale_sonra",
                    "kontrol_once", "kontrol_sonra"]})
def _(a):
    return degerlendirme.farklarin_farki(a["mudahale_once"], a["mudahale_sonra"],
                                         a["kontrol_once"], a["kontrol_sonra"])



def _donem_serisi(kayitlar, tarih_alan, donem):
    """Kayıtları eksiksiz dönem sayım serisine çevirir (boş dönem = 0).

    Returns: (baslangic_datetime, sayimlar) ya da (None, []) — tarih yoksa.
    Dönem indeksi: gun = gün farkı, hafta = gün farkı // 7, ay = takvim ayı farkı.
    """
    tarihler = [d for d in (veri.tarih_coz(r.get(tarih_alan)) for r in kayitlar) if d]
    if not tarihler:
        return None, []
    bas = min(tarihler)
    sayim = {}
    for d in tarihler:
        i = _donem_indeksi(bas, d, donem)
        sayim[i] = sayim.get(i, 0) + 1
    return bas, [sayim.get(i, 0) for i in range(max(sayim) + 1)]


def _donem_indeksi(bas, d, donem):
    """bas'tan d'ye dönem indeksi (gun/hafta/ay)."""
    if donem == "ay":
        return (d.year - bas.year) * 12 + (d.month - bas.month)
    gun = (d.date() - bas.date()).days
    return gun // 7 if donem == "hafta" else gun


@arac("kesinti_analizi",
      "Kesintili zaman serisi (ITS): kesinti tarihindeki SEVİYE ve EĞİM değişimi, "
      "güven aralığı ve p ile (segmentli regresyon). Tek grup ITS nedensellik kanıtlamaz",
      sema({"kesinti_tarihi": {"type": "string",
                               "description": "kesintinin ilk günü (YYYY-AA-GG)"},
            "donem": {"type": "string", "enum": ["gun", "hafta", "ay"], "default": "ay"},
            "tarih_alan": {"type": "string", "default": "tarih"}}, ["kesinti_tarihi"]))
def _(a):
    k = kayitlari_getir(a)
    donem = a.get("donem", "ay")
    kesinti = veri.tarih_coz(a["kesinti_tarihi"])
    if kesinti is None:
        raise KullanimHatasi("kesinti_tarihi çözülemedi",
                             oneri="YYYY-AA-GG biçiminde bir tarih verin")
    bas, seri = _donem_serisi(k, a.get("tarih_alan", "tarih"), donem)
    if bas is None:
        raise VeriHatasi("tarih içeren kayıt yok",
                         oneri="tarih_alan'ı ve tarih biçimini denetleyin")
    t0 = _donem_indeksi(bas, kesinti, donem)
    if not 0 < t0 < len(seri):
        raise KullanimHatasi("kesinti_tarihi verinin tarih aralığının içinde olmalı",
                             oneri="kesintiden önce ve sonra en az birer dönem veri gerekir")
    sonuc = degerlendirme.kesinti_analizi(seri, t0)
    if sonuc is None:
        raise VeriHatasi("kesintinin her iki tarafında en az 2 dönem gerekir",
                         oneri="daha uzun bir seri ya da daha kısa dönem (hafta/gün) kullanın")
    sonuc.update({"donem": donem, "donem_sayisi": len(seri), "kesinti_donemi": t0})
    if len(seri) <= 400:
        sonuc["seri"] = seri
    return sonuc


@arac("wdd_testi",
      "WDD testi: yer değiştirmeyi hesaba katarak müdahale etkisinin anlamlılığı",
      {"type": "object",
       "properties": {"t_once": {"type": "number"}, "t_sonra": {"type": "number"},
                      "k_once": {"type": "number"}, "k_sonra": {"type": "number"},
                      "yd_once": {"type": "number", "description": "yer-değiştirme tamponu önce"},
                      "yd_sonra": {"type": "number"},
                      "ydk_once": {"type": "number", "description": "tampon kontrolü önce"},
                      "ydk_sonra": {"type": "number"}},
       "required": ["t_once", "t_sonra", "k_once", "k_sonra"]})
def _(a):
    return degerlendirme.wdd_testi(
        a["t_once"], a["t_sonra"], a["k_once"], a["k_sonra"],
        a.get("yd_once"), a.get("yd_sonra"), a.get("ydk_once"), a.get("ydk_sonra"))



@arac("benford", "Benford yasası: uydurma sayı tespiti",
      sema(ALAN, ["alan"]))
def _(a):
    # mertebe gate'i dispatch yolunda merkezi (uygun değilse KapiRed); v6.0
    k = kayitlari_getir(a)
    return ileri.benford_testi([r.get(a["alan"]) for r in k])



@arac("ag_analizi", "Co-offending ağı: derece/aracılık/topluluk/pagerank/yol",
      {"type": "object",
       "properties": {
           "kenarlar": {"type": "array",
                        "description": "[[dugum1, dugum2, agirlik?], ...]"},
           "analiz": {"type": "string",
                      "enum": ["derece", "aracilik", "topluluk", "pagerank",
                               "bilesen", "yol"]},
           "kaynak": {"type": "string"}, "hedef": {"type": "string"}},
       "required": ["kenarlar", "analiz"]})
def _(a):
    g = ag.ag_kur(a["kenarlar"])
    tur = a["analiz"]
    if tur == "derece":
        return ag.derece_merkeziyeti(g)
    if tur == "aracilik":
        return ag.aracilik_merkeziyeti(g)
    if tur == "topluluk":
        return ag.topluluk_tespiti(g)
    if tur == "pagerank":
        return ag.pagerank(g)
    if tur == "bilesen":
        return ag.bagli_bilesenler(g)
    if tur == "yol":
        return {"yol": ag.en_kisa_yol(g, a.get("kaynak"), a.get("hedef"))}
    return {"hata": "bilinmeyen analiz"}



@arac("risk_skorla", "Ağırlıklı kural motoru ile olay risk skorlama",
      sema({"kurallar": {"type": "array",
            "description": "[{alan, kosul, deger, agirlik}]"}},
           ["kurallar"]))
def _(a):
    return skor.toplu_skorla(kayitlari_getir(a), a["kurallar"])[:100]



@arac("bulanik_eslesme", "İsim/adres yazım farklarına dayanıklı eşleşme",
      sema({"alan": {"type": "string"}, "hedef": {"type": "string"},
            "esik": {"type": "number", "default": 0.8},
            **ALANLAR_PROP}, ["alan", "hedef"]))
def _(a):
    sonuc = kume.bulanik_eslesme(kayitlari_getir(a), a["alan"], a["hedef"],
                                 a.get("esik", 0.8))
    return kayitlari_kisitla(sonuc, a.get("alanlar"))



@arac("orneklem_cek", "Basit/sistematik/tabakalı örneklem",
      sema({"yontem": {"type": "string",
                       "enum": ["basit", "sistematik", "tabakali"]},
            "n": {"type": "integer"},
            "tabaka_alan": {"type": "string"},
            **ALANLAR_PROP}, ["yontem", "n"]))
def _(a):
    k = kayitlari_getir(a)
    if a["yontem"] == "basit":
        sonuc = orneklem.basit_tesadufi(k, a["n"])
    elif a["yontem"] == "sistematik":
        sonuc = orneklem.sistematik(k, a["n"])
    else:
        sonuc = orneklem.tabakali(k, a.get("tabaka_alan", "mahalle"), a["n"])
    return kayitlari_kisitla(sonuc, a.get("alanlar"))



@arac("veri_kalitesi", "DOKTRIN: HER analizden önce çağırın — deterministik "
      "veri profili + isteğe bağlı fitness gate kararı",
      sema({"sayisal_alan": {"type": "string"},
            "analiz": {"type": "string",
                       "description": "verilirse analiz_uygun_mu kararı da döner"},
            "payda_var": {"type": "boolean"},
            "fuzzy": {"type": "boolean",
                      "description": "yazım varyantı adayları (pahalı)"}}))
def _(a):
    k = kayitlari_getir(a)
    prof = veri.veri_profili(k, sayisal_alan=a.get("sayisal_alan"))
    sonuc = {"profil": prof}
    if a.get("analiz"):
        sonuc["uygunluk"] = veri.analiz_uygun_mu(
            prof, a["analiz"], payda_var=a.get("payda_var", False))
    if a.get("fuzzy"):
        # yazım varyantı adayları: yüksek benzerlikli fakat farklı değerler
        adaylar = {}
        for alan, kard in list(prof.get("kardinalite", {}).items())[:5]:
            degerler = sorted({str(r.get(alan)) for r in k
                               if r.get(alan) not in (None, "")})[:200]
            ciftler = []
            for i in range(len(degerler)):
                for j in range(i + 1, len(degerler)):
                    b = kume.benzerlik_orani(degerler[i], degerler[j])
                    if 0.75 <= b < 1.0:
                        ciftler.append([degerler[i], degerler[j], b])
            if ciftler:
                adaylar[alan] = ciftler[:20]
        sonuc["yazim_varianti_adaylari"] = adaylar
        if adaylar:
            sonuc.setdefault("notlar", []).append(
                "kategori birleştirme ÖNERİDİR; insan onayı olmadan uygulanmaz")
    dup = veri.duplikat_isaretle(k)
    sonuc["duplikat_sayisi"] = dup["duplikat_sayisi"]
    sonuc["tahribatsizlik"] = ("hiçbir kayıt silinmedi/uydurulmadı; düzeltmeler "
                               "öneri+insan onayı gerektirir")
    return sonuc



@arac("koordinat_maskele", "KVKK yayın maskesi: koordinatlara jitter uygular",
      sema({"yaricap_m": {"type": "number", "default": 200},
            "seed": {"type": "integer"}}))
def _(a):
    k = kayitlari_getir(a)
    sonuc = []
    for r in k:
        p = veri.koordinat_al(r)
        if p:
            mlat, mlon = mekan.koordinat_maskele(
                p[0], p[1], a.get("yaricap_m", 200), a.get("seed"))
            sonuc.append({"id": r.get("id"), "lat": mlat, "lon": mlon})
    return sonuc



@arac("t_testi", "t-testi: tek örneklem / bağımsız (Welch seçenekli) / bağımlı",
      sema({"tip": {"type": "string", "enum": ["tek", "bagimsiz", "bagimli"]},
            "x": {"type": "array"}, "y": {"type": "array"},
            "mu0": {"type": "number"},
            "welch": {"type": "boolean", "default": True},
            "alan": {"type": "string"}, "grup_alan": {"type": "string"}},
           ["tip"]))
def _(a):
    if a["tip"] == "tek":
        x = sayisal_vektor(a.get("x") or
                           [r.get(a["alan"]) for r in kayitlari_getir(a)])
        return hipotez.t_test_tek(x, a.get("mu0", 0))
    x, y = iki_vektor(a)
    if a["tip"] == "bagimli":
        return hipotez.t_test_bagimli(x, y)
    return hipotez.t_test_bagimsiz(x, y, welch=a.get("welch", True))



@arac("iki_oran_testi", "İki oran z-testi + fark için %95 GA",
      {"type": "object",
       "properties": {"x1": {"type": "integer"}, "n1": {"type": "integer"},
                      "x2": {"type": "integer"}, "n2": {"type": "integer"}},
       "required": ["x1", "n1", "x2", "n2"]})
def _(a):
    return hipotez.iki_oran_testi(a["x1"], a["n1"], a["x2"], a["n2"])



@arac("fisher_exact", "Fisher exact testi (2x2; beklenen<5'te ki-kare yerine)",
      {"type": "object",
       "properties": {"a": {"type": "integer"}, "b": {"type": "integer"},
                      "c": {"type": "integer"}, "d": {"type": "integer"}},
       "required": ["a", "b", "c", "d"]})
def _(a):
    return hipotez.fisher_exact(a["a"], a["b"], a["c"], a["d"])



@arac("binomial_test", "Binomial exact test: oran varsayımla uyumlu mu?",
      {"type": "object",
       "properties": {"x": {"type": "integer"}, "n": {"type": "integer"},
                      "p0": {"type": "number"}},
       "required": ["x", "n", "p0"]})
def _(a):
    return hipotez.binomial_test(a["x"], a["n"], a["p0"])



@arac("mann_whitney", "Mann-Whitney U (nonparametrik iki örneklem)", SEMA_IKI)
def _(a):
    x, y = iki_vektor(a)
    return hipotez.mann_whitney(x, y)



@arac("anova", "Tek yönlü ANOVA + eta² + Bonferroni pairwise", SEMA_GRUP)
def _(a):
    return hipotez.anova(grup_vektorleri(a))



@arac("kruskal_wallis", "Kruskal-Wallis (nonparametrik ANOVA)", SEMA_GRUP)
def _(a):
    return hipotez.kruskal_wallis(grup_vektorleri(a))



@arac("spearman", "Spearman rank korelasyonu + p-değeri",
      sema({"x": {"type": "array"}, "y": {"type": "array"},
            "alan_x": {"type": "string"}, "alan_y": {"type": "string"}}))
def _(a):
    if a.get("x") is not None:
        x, y = sayisal_vektor(a["x"]), sayisal_vektor(a["y"])
    else:
        k = kayitlari_getir(a)
        x = sayisal_vektor([r.get(a["alan_x"]) for r in k])
        y = sayisal_vektor([r.get(a["alan_y"]) for r in k])
    return hipotez.spearman(x, y)



@arac("kendall", "Kendall tau-b ordinal ilişki",
      sema({"x": {"type": "array"}, "y": {"type": "array"}}))
def _(a):
    return hipotez.kendall_tau(sayisal_vektor(a["x"]), sayisal_vektor(a["y"]))



@arac("phi", "Phi katsayısı (2x2 nominal ilişki)",
      {"type": "object",
       "properties": {"a": {"type": "integer"}, "b": {"type": "integer"},
                      "c": {"type": "integer"}, "d": {"type": "integer"}},
       "required": ["a", "b", "c", "d"]})
def _(a):
    return {"phi": hipotez.phi_katsayisi(a["a"], a["b"], a["c"], a["d"])}



@arac("randomizasyon_testi", "Permütasyon testi (varsayımsız ortalama farkı)",
      sema({"x": {"type": "array"}, "y": {"type": "array"},
            "sim": {"type": "integer", "default": 999},
            "alan": {"type": "string"}, "grup_alan": {"type": "string"}}))
def _(a):
    x, y = iki_vektor(a)
    return hipotez.randomizasyon_testi(x, y, a.get("sim", 999))



@arac("guc_analizi", "Güç analizi: oran/ortalama için gerekli örneklem",
      {"type": "object",
       "properties": {"tip": {"type": "string", "enum": ["oran", "t"]},
                      "p1": {"type": "number"}, "p2": {"type": "number"},
                      "d": {"type": "number"},
                      "alfa": {"type": "number", "default": 0.05},
                      "guc": {"type": "number", "default": 0.8}},
       "required": ["tip"]})
def _(a):
    if a["tip"] == "oran":
        return hipotez.guc_oran_orneklem(a["p1"], a["p2"],
                                         a.get("alfa", 0.05), a.get("guc", 0.8))
    return hipotez.guc_t_orneklem(a["d"], a.get("alfa", 0.05),
                                  a.get("guc", 0.8))



@arac("coklu_regresyon", "Çoklu OLS: beta, t, p, R², düzeltilmiş R², F, VIF",
      SEMA_REG)
def _(a):
    X, y, adlar, _, kapsam = _reg_hazirla(a)
    sonuc = regresyon.coklu_ols(X, y, adlar)
    if isinstance(sonuc, dict):
        sonuc['kapsam'] = kapsam
    return sonuc



@arac("lojistik_regresyon", "İkili lojistik regresyon: Wald, p, odds oranı",
      SEMA_REG)
def _(a):
    X, y, adlar, _, kapsam = _reg_hazirla(a)
    sonuc = regresyon.lojistik(X, y, adlar)
    if isinstance(sonuc, dict):
        sonuc['kapsam'] = kapsam
    return sonuc



@arac("dagilim_olculeri", "Sağlam dağılım ölçüleri: IQR, MAD, CV",
      sema({"degerler": {"type": "array"}, "alan": {"type": "string"}}))
def _(a):
    if a.get("degerler") is not None:
        d = sayisal_vektor(a["degerler"])
    else:
        d = sayisal_vektor([r.get(a["alan"]) for r in kayitlari_getir(a)])
    return {"iqr": istatistik.iqr(d), "mad": istatistik.mad(d),
            "cv": istatistik.varyasyon_katsayisi(d), "n": len(d)}



@arac("zarar_hesapla", "Crime Harm Index: zarar-ağırlıklı toplam/grup analizi",
      sema({"tur_alan": {"type": "string", "default": "tur"},
            "grup_alan": {"type": "string"},
            "agirlik_yolu": {"type": "string",
                             "description": "kurum ağırlık JSON (veri kökünde)"}}))
def _(a):
    k = kayitlari_getir(a)
    yol = None
    if a.get("agirlik_yolu"):
        yol = veri.guvenli_yol(a["agirlik_yolu"], izinli_uzantilar={".json"})
    agirliklar = zarar.agirlik_tablosu_yukle(yol)
    return zarar.zarar_tablosu(k, a.get("tur_alan", "tur"), agirliklar,
                               a.get("grup_alan"))



@arac("power_few", "Power Few: zararın %50'sini üreten en küçük birim kümesi",
      sema({"grup_alan": {"type": "string"},
            "tur_alan": {"type": "string", "default": "tur"},
            "hedef_pay": {"type": "number", "default": 0.5},
            "agirlik_yolu": {"type": "string"}}, ["grup_alan"]))
def _(a):
    k = kayitlari_getir(a)
    yol = veri.guvenli_yol(a["agirlik_yolu"], izinli_uzantilar={".json"}) if a.get("agirlik_yolu") else None
    return zarar.power_few(k, a["grup_alan"], a.get("tur_alan", "tur"),
                           zarar.agirlik_tablosu_yukle(yol),
                           a.get("hedef_pay", 0.5))



@arac("hacim_zarar_karsilastir", "Hacim vs zarar sıralama ayrışması",
      sema({"grup_alan": {"type": "string"},
            "tur_alan": {"type": "string", "default": "tur"},
            "agirlik_yolu": {"type": "string"}}, ["grup_alan"]))
def _(a):
    k = kayitlari_getir(a)
    yol = veri.guvenli_yol(a["agirlik_yolu"], izinli_uzantilar={".json"}) if a.get("agirlik_yolu") else None
    return zarar.hacim_zarar_karsilastir(k, a["grup_alan"],
                                         a.get("tur_alan", "tur"),
                                         zarar.agirlik_tablosu_yukle(yol))



@arac("agirlikli_kde", "Zarar-ağırlıklı KDE (harm-spot haritası)",
      sema({"bant_km": {"type": "number", "default": 0.4},
            "hucre_km": {"type": "number", "default": 0.3},
            "tur_alan": {"type": "string", "default": "tur"},
            "agirlik_yolu": {"type": "string"}}))
def _(a):
    k = kayitlari_getir(a)
    pts, ws, gecerli = [], [], 0
    yol = veri.guvenli_yol(a["agirlik_yolu"], izinli_uzantilar={".json"}) if a.get("agirlik_yolu") else None
    agirliklar = zarar.agirlik_tablosu_yukle(yol)
    for r in k:
        q = veri.koordinat_al(r)
        if q:
            pts.append(q)
            ws.append(zarar.olay_zarari(r.get(a.get("tur_alan", "tur")),
                                        agirliklar))
            gecerli += 1
    quadratic_guard(pts, "agirlikli_kde")
    mekan._kde_butce(pts, a.get('bant_km', .4), a.get('hucre_km', .3))
    return {"hucreler": mekan.kde_yogunluk(pts, a.get("bant_km", 0.4),
                              a.get("hucre_km", 0.3), ws)[:100],
            "kapsam": kapsam_uret(k, gecerli, "geçersiz/eksik koordinat")}



@arac("brifing_uret", "Analiz ÜRÜNÜ: taktik brifing / stratejik değerlendirme "
      "(belirsizlik notu zorunlu)",
      {"type": "object",
       "properties": {
           "urun_turu": {"type": "string",
                         "enum": ["taktik", "stratejik"], "default": "taktik"},
           "talep": {"type": "object"},
           "oturum_id": {"type": "string"},
           "hotspot": {"type": "array"}, "gun_saat": {"type": "array"},
           "yakin_tekrar": {}, "power_few": {"type": "object"},
           "trend": {"type": "string"}, "oranlar": {"type": "array"},
           "anomali": {}, "degerlendirme": {"type": "string"},
           "guc": {"type": "string"},
           "belirsizlik": {"type": "array"},
           "ek_notlar": {"type": "array"}},
       "required": ["belirsizlik"]})
def _(a):
    talep = a.get("talep") or {}
    kalite = None
    d = None
    if a.get("oturum_id"):
        d = dongu.yukle(a["oturum_id"], _log_dir())
        talep = talep or d.manifesto["talep"]
        kalite = d.manifesto.get("veri_kalitesi")
    if a.get("urun_turu", "taktik") == "taktik":
        urun = rapor.taktik_brifing(
            talep, kalite, a.get("hotspot"), a.get("gun_saat"),
            a.get("yakin_tekrar"), a.get("power_few"),
            a.get("ek_notlar"), a["belirsizlik"])
    else:
        urun = rapor.stratejik_degerlendirme(
            talep, a.get("trend"), a.get("oranlar"), a.get("anomali"),
            a.get("degerlendirme"), a.get("guc"), a["belirsizlik"])
    if d is not None:  # Katman 3: olgu/gerekçe ayrımlı muhakeme izi (v6.2)
        urun = urun + "\n\n---\n\n" + rapor.muhakeme_izi(d.manifesto)
    return {"urun": urun}


@arac("kanit_dogrula", "Oturumun olay akışı hash-zinciri bütünlüğünü "
      "sına (P2): her kayıt öncekinin SHA-256'sına zincirli",
      {"type": "object",
       "properties": {"oturum_id": {"type": "string"}},
       "required": ["oturum_id"]})
def _(a):
    from ..surec import kanit
    return kanit.dogrula(_log_dir(), a["oturum_id"])


@arac("provenans_hazirlik", "Verinin pakete girmeden ONCEKI hazirligini "
      "beyan olarak kaydet (birlestirme/geokodlama/filtreleme). Bu adimlar "
      "hicbir hash tarafindan kapsanmaz; kayit BEYAN turundedir.",
      {"type": "object",
       "properties": {
           "oturum_id": {"type": "string"},
           "beyan_eden": {"type": "string"},
           "adimlar": {"type": "array",
                       "description": "[{islem, aciklama, kaynak}]"}},
       "required": ["oturum_id", "beyan_eden", "adimlar"]})
def _(a):
    from ..surec import provenans
    d = dongu.yukle(a["oturum_id"], _log_dir())
    beyan = provenans.hazirlik_beyani(d.manifesto, a["adimlar"],
                                      a["beyan_eden"])
    dongu.kaydet(d, _log_dir())
    return beyan


@arac("provenans_dis_denetim", "Dis sistemin (or. Science GPT) denetim "
      "dogrulama sonucunu bu oturuma bagla; iki zincir uclarindan baglanir",
      {"type": "object",
       "properties": {
           "oturum_id": {"type": "string"},
           "sistem": {"type": "string", "default": "science_gpt"},
           "kimlik": {"type": "string",
                      "description": "dis sistemdeki arastirma kimligi"},
           "dogrulama": {"type": "object",
                         "description": "audit/verify yaniti"}},
       "required": ["oturum_id", "kimlik", "dogrulama"]})
def _(a):
    from ..surec import provenans
    d = dongu.yukle(a["oturum_id"], _log_dir())
    bag = provenans.dis_denetim_kaydet(
        d.manifesto, a.get("sistem", "science_gpt"), a["kimlik"],
        a["dogrulama"])
    dongu.kaydet(d, _log_dir())
    return bag


@arac("provenans_ozet", "Uctan uca kaynak zinciri: her halkanin kanit turu "
      "(makine/beyan/eksik) ve zincirdeki kopukluklar",
      {"type": "object",
       "properties": {"oturum_id": {"type": "string"}},
       "required": ["oturum_id"]})
def _(a):
    from ..surec import provenans
    d = dongu.yukle(a["oturum_id"], _log_dir())
    return provenans.zincir_ozeti(d.manifesto, _log_dir())


@arac("muhakeme_izi", "Oturumun muhakeme izi (Katman 3): her analiz adımı "
      "için olgu (K1/K2) ve gerekçe (K3) görsel ayrımlı Markdown",
      {"type": "object",
       "properties": {"oturum_id": {"type": "string"}},
       "required": ["oturum_id"]})
def _(a):
    d = dongu.yukle(a["oturum_id"], _log_dir())
    return {"urun": rapor.muhakeme_izi(d.manifesto)}



@arac("dongu_baslat", "PPDAC döngüsü başlat: talep kaydı + araç planı önerisi",
      {"type": "object",
       "properties": {"soran": {"type": "string"},
                      "karar": {"type": "string",
                                "description": "hangi karar için analiz"},
                      "kapsam": {"type": "string"},
                      "urun_turu": {"type": "string",
                                    "enum": ["taktik", "stratejik", "sorun_cozme"],
                                    "default": "taktik"},
                      "donem": {"type": "string"}},
       "required": ["karar"]})
def _(a):
    d = dongu.AnalizDongusu({k: a.get(k) for k in
                             ("soran", "karar", "kapsam", "urun_turu", "donem")})
    plan = d.planla()
    dongu.kaydet(d, _log_dir())
    return {"oturum_id": d.manifesto["oturum_id"], "faz": "PLAN",
            "plan": plan,
            "sonraki": "dongu_veri ile veri bağlayın"}



@arac("dongu_veri", "Döngü VERİ fazı: profil + fitness gate (otomatik)",
      sema({"oturum_id": {"type": "string"},
            "analiz": {"type": "string"},
            "sayisal_alan": {"type": "string"}}, ["oturum_id"]))
def _(a):
    d = dongu.yukle(a["oturum_id"], _log_dir())
    k = kayitlari_getir(a)
    prof = veri.veri_profili(k, sayisal_alan=a.get("sayisal_alan"))
    d.veri_bagla(prof)
    sonuc = {"faz": "VERI", "profil": prof}
    if a.get("analiz"):
        # Araç adı verilirse kapı, aracın yürütmede kullandığı analiz adıyla
        # değerlendirilir (ör. sicak_nokta_gi → grid_hotspot); yoksa 11 araçta
        # mekânsal/zarar kuralları atlanıp yanıltıcı "uygun" kaydediliyordu.
        kapi_adi = ARAC_GATE[a["analiz"]][0] if a["analiz"] in ARAC_GATE else a["analiz"]
        uygunluk = veri.analiz_uygun_mu(prof, kapi_adi)
        d.manifesto["gate_kararlari"].append({"faz": "VERI-kapi", **uygunluk})
        sonuc["uygunluk"] = uygunluk
        sonuc["kapi_analizi"] = kapi_adi
        sonuc["sonraki"] = ("uygun ise dongu_analize_gec çağırın"
                            if uygunluk["uygun"] else
                            "gate reddetti; veriyi düzeltin veya başka analiz seçin")
    dongu.kaydet(d, _log_dir())
    return sonuc



@arac("dongu_analize_gec", "VERİ→ANALİZ kapısı: kayıtlı gate kararıyla geçiş",
      {"type": "object",
       "properties": {"oturum_id": {"type": "string"},
                      "uygunluk": {"type": "object",
                                   "description": "dongu_veri çıktısındaki karar"}},
       "required": ["oturum_id", "uygunluk"]})
def _(a):
    d = dongu.yukle(a["oturum_id"], _log_dir())
    kayitli = next((k for k in reversed(d.manifesto["gate_kararlari"])
                    if k.get("faz") == "VERI-kapi"), None)
    if kayitli is None:
        raise dongu.DonguHatasi("kayıtlı VERİ gate kararı bulunamadı")
    alanlar = ("uygun", "girdi_n", "sebepler")
    beklenen = {k: kayitli.get(k) for k in alanlar}
    gelen = {k: a["uygunluk"].get(k) for k in alanlar}
    if gelen != beklenen:
        raise dongu.DonguHatasi(
            "istemci uygunluk beyanı kayıtlı gate kararıyla uyuşmuyor")
    sonuc = d.analize_gec(beklenen)
    dongu.kaydet(d, _log_dir())
    return sonuc



@arac("dongu_analiz", "Döngü içinde analiz aracı çalıştır + manifestoya işle "
      "(resmî oturumda gerekçe zorunlu: hipotez + yorum — Faz 1.6)",
      {"type": "object",
       "properties": {"oturum_id": {"type": "string"},
                      "arac": {"type": "string"},
                      "argumanlar": {"type": "object"},
                      "gerekce": {"type": "object",
                                  "description": "{hipotez, yorum, cikarim?, "
                                                 "alternatifler?} — resmî "
                                                 "oturumda zorunlu"}},
       "required": ["oturum_id", "arac", "gerekce"]})
def _(a):
    d = dongu.yukle(a["oturum_id"], _log_dir())
    eksik = dongu.GEREKCE_ZORUNLU - set(a.get("gerekce") or {})
    if eksik:
        raise KullanimHatasi(f"gerekçe eksik alan: {sorted(eksik)}; zorunlu: "
                         f"{sorted(dongu.GEREKCE_ZORUNLU)}",
                         oneri="hipotez ve yorum alanlarını doldurun")
    alt_arg = a.get("argumanlar") or {}
    def _faz_kontrol():
        if d.manifesto["faz"] != "ANALIZ":
            raise dongu.DonguHatasi("analiz hesabı yalnız ANALIZ fazında çalışır")
    sonuc, karar, _ = arac_yurut(
        a["arac"], alt_arg, sadece_analitik=True, hesap_oncesi=_faz_kontrol)
    if karar:
        d.manifesto["gate_kararlari"].append(
            {"faz": "ANALIZ-arac", "arac": a["arac"],
             **{k: v for k, v in karar.items() if not k.startswith("_")}})
    d.analiz_kaydet(a["arac"], sonuc, a.get("gerekce"))
    dongu.kaydet(d, _log_dir())
    if baglam() is not None:
        baglam()["nested_gate"] = karar
        baglam()["nested_kanit_durumu"] = "yazildi"
    return sonuc



@arac("dongu_sonuc", "Döngü SONUÇ fazı: insan onayı zorunlu",
      {"type": "object",
       "properties": {"oturum_id": {"type": "string"},
                      "sonuc_turu": {"type": "string",
                                     "enum": ["sorun_dogrulandi", "sorun_reddedildi",
                                              "izlemeye_alindi", "mudahale_onerildi"]},
                      "onaylayan": {"type": "string"},
                      "onay_notu": {"type": "string"},
                      "bulgular": {"type": "array"}},
       "required": ["oturum_id", "sonuc_turu", "onaylayan"]})
def _(a):
    d = dongu.yukle(a["oturum_id"], _log_dir())
    sonuc = d.sonucla(a["sonuc_turu"],
                      {"onaylayan": a["onaylayan"],
                       "not": a.get("onay_notu", "")},
                      a.get("bulgular"))
    dongu.kaydet(d, _log_dir())
    return sonuc



@arac("dongu_izleme", "Döngüyü kapat: izleme planı (3T-Tracking)",
      {"type": "object",
       "properties": {"oturum_id": {"type": "string"},
                      "metrik": {"type": "string"},
                      "esik": {"type": "number"},
                      "kontrol_tarihi": {"type": "string"},
                      "not": {"type": "string"}},
       "required": ["oturum_id", "metrik", "esik", "kontrol_tarihi"]})
def _(a):
    d = dongu.yukle(a["oturum_id"], _log_dir())
    sonuc = d.izleme_plani(a["metrik"], a["esik"], a["kontrol_tarihi"],
                           a.get("not"))
    dongu.kaydet(d, _log_dir())
    return sonuc



@arac("dongu_durum", "Oturum manifestosu / açık oturum listesi",
      {"type": "object",
       "properties": {"oturum_id": {"type": "string"}}})
def _(a):
    if a.get("oturum_id"):
        return dongu.yukle(a["oturum_id"], _log_dir()).manifesto
    return dongu.listele(_log_dir())




@arac("rehberli_calisma", "Rehberli akış (Soru → Plan → Hüküm, ADR-002): soru türü "
      "şablonundan hipotez seti (birincil + rakipler + H_bilinmeyen), doğrulayıcıda "
      "veriden önce kilit, sınamalar ve kategorik hüküm (DESTEKLENDİ/KIRILGAN/"
      "BELİRSİZ/ÇELİŞKİLİ/ÇEKİMSER) — olasılık yok, hüküm taslak",
      sema({"soru_turu": {"type": "string", "enum": ["ARTIS", "YOGUNLASMA", "SERI", "ETKI"]},
            "amac": {"type": "string", "enum": ["dogrulayici", "kesifsel", "operasyonel"]},
            "onaylayan": {"type": "string",
                          "description": "doğrulayıcı çalışmada kilidi alan kişi (zorunlu)"},
            "kanal_alan": {"type": "string",
                           "description": "ARTIS: bildirim kanalı/kaynak alanı (R-BILDIRIM)"},
            "mo_alan": {"type": "string", "description": "SERI: MO metni alanı (zorunlu)"},
            "soru": {"type": "string", "description": "soru metni (kayıt için)"},
            "bolge_alan": {"type": "string", "description": "ETKI: bölge alanı (zorunlu)"},
            "mudahale": {"type": "string", "description": "ETKI: müdahale bölgesinin değeri (zorunlu)"},
            "kontrol": {"type": "string", "description": "ETKI: kontrol bölgesinin değeri"},
            "tampon": {"type": "string", "description": "ETKI: yer değiştirme tamponunun değeri"},
            "kesinti_tarihi": {"type": "string", "description": "ETKI: müdahalenin başlangıcı (zorunlu)"}},
           ["soru_turu", "amac"]))
def _(a):
    k = kayitlari_getir(a)
    kaynak = {x: a[x] for x in ("satirlar", "csv_yolu") if x in a}
    return calisma.rehberli(kaynak, k, a["soru_turu"], a["amac"], _log_dir(),
                            lambda ad, arg: arac_yurut(ad, arg, sadece_analitik=True)[0],
                            _rehberli_kapi, onaylayan=a.get("onaylayan"),
                            kanal_alan=a.get("kanal_alan"), mo_alan=a.get("mo_alan"),
                            soru=a.get("soru"), bolge_alan=a.get("bolge_alan"),
                            mudahale=a.get("mudahale"), kontrol=a.get("kontrol"),
                            tampon=a.get("tampon"), kesinti_tarihi=a.get("kesinti_tarihi"))


def _rehberli_kapi(ad, arg):
    """Birincil sınama aracının kapı kararı — araç yürütmesiyle AYNI otorite
    (dispatch_gate); ret istisnası karar sözlüğüne çevrilir."""
    try:
        karar = dispatch_gate(ad, dict(arg))
    except KapiRed as e:
        return {"uygun": False, "girdi_n": None, "sebepler": [str(e)]}
    if karar is None:
        return {"uygun": True, "girdi_n": None, "sebepler": [], "not": f"{ad} için kapı tanımlı değil"}
    return {k: v for k, v in karar.items() if not k.startswith("_")}
