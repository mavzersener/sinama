# -*- coding: utf-8 -*-
"""
oneri.py — veri-yapısı + soru odaklı analiz öneri motoru (karar ağacı
uygulaması, v1.0). Statik ürün-türü şablonlarının yerine/yanına, dosyanın
GERÇEK yapısını (sütun tipleri, koordinat, zaman, ilişki, payda) profilleyip
uygun analiz ailesini önerir.

İlkeler (karar ağacı §2): önce problem sonra yöntem; önce veri üretim süreci;
karmaşık ≠ iyi; evrensel eşik yok; risk ≠ kesin tahmin. Her öneri GERÇEK bir
araca ya da 'bu sürümde yok' etiketine bağlanır (vaat edilmeyeni vaatme).

DÜRÜSTLÜK: karar ağacının atıfta bulunduğu bazı yöntemler bu stdlib sürümünde
yoktur (multinomial/ordinal lojistik, çok düzeyli, GWR, Poisson/ZIP regresyon,
telefon/baz, finansal akış, metin madenciliği). Bunlar 'mevcut=False' ile
önerilir; kullanıcı yanıltılmaz.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from . import veri

# ---- soru (niyet) anahtarları: karar ağacı §3 üst düzey sorular ----
_NIYET = {
    "betimleme": r"ne oluyor|genel|dağılım|özet|betim|kaç|sayı",
    "zaman": r"ne zaman|saat|gün|ay|mevsim|trend|eğilim|zaman|dönem",
    "mekan": r"nerede|harita|sıcak nokta|hotspot|yoğun|konum|bölge|mekan|coğraf",
    "tekrar": r"tekrar|yakın tekrar|kalıcı|yeni|ortaya çık|mükerrer|seri",
    "iliski": r"bağlant|ilişk|ağ|kim kime|birlikte|şebeke|transfer",
    "acikla": r"hangi değişken|ilişkili|açıkla|etki|neden|regres",
    "risk": r"risk|gelecek|tahmin|nerede daha|beklenen",
    "mudahale": r"müdahale|işe yara|etki|önce sonra|değerlendir|azalt",
}


def _normalize(s: str) -> str:
    return (str(s or "").lower().replace("ı", "i").replace("ğ", "g")
            .replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c"))


_ID_OLAY = ("olay_id", "vaka_id", "event_id", "id", "kayit_id", "olay_no")
_ID_KISI = ("kisi_id", "magdur_id", "fail_id", "tc", "kimlik_no", "supheli_id")


def birim_tespit(kayitlar: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analiz birimi sezgisel tespiti (karar ağacı Düğüm 1.2 / R02): satır
    neyi temsil ediyor? Belirsizse model kurulmamalı (kullanıcıya sor).

    Returns: {birim, guven (0-1), gerekce, belirsiz (bool)}.
    birim ∈ {olay, kişi/varlık, bölge/bölge-dönem, kayıt, belirsiz}.
    """
    n = len(kayitlar)
    if n == 0:
        return {"birim": "belirsiz", "guven": 0.0, "gerekce": "veri yok", "belirsiz": True}
    alanlar = list(kayitlar[0].keys())
    a_norm = {_normalize(a): a for a in alanlar}

    def benzersizlik(alan):
        """Bir alanın benzersiz değer oranı (1.0 = satır başına tekil)."""
        d = [k.get(alan) for k in kayitlar if k.get(alan) not in (None, "")]
        return len(set(d)) / len(d) if d else 0.0

    # adı id gibi olan VEYA benzersizliği yüksek sütunlar
    olay_id = next((a_norm[a] for a in _ID_OLAY if a in a_norm), None)
    kisi_id = next((a_norm[a] for a in _ID_KISI if a in a_norm), None)
    bolge = next((a_norm[a] for a in ("grid_id", "bolge", "mahalle", "ilce", "il")
                  if a in a_norm), None)
    sayim_alan = next((a_norm[a] for a in ("olay_sayisi", "sayi", "adet", "count",
                                           "olay", "toplam")
                       if a in a_norm), None)

    # 1) benzersiz olay kimliği → olay düzeyi
    if olay_id and benzersizlik(olay_id) >= 0.98:
        return {"birim": "olay", "guven": 0.9,
                "gerekce": f"'{olay_id}' satır başına benzersiz (olay düzeyi)",
                "belirsiz": False}
    # 2) bölge + sayım alanı ve satır≈bölge → toplulaştırılmış bölge(-dönem)
    if bolge and sayim_alan and benzersizlik(bolge) >= 0.5:
        return {"birim": "bölge/bölge-dönem", "guven": 0.8,
                "gerekce": f"'{bolge}' + '{sayim_alan}': toplulaştırılmış areal veri",
                "belirsiz": False}
    # 3) kişi kimliği tekrarlı → kişi/varlık düzeyi
    if kisi_id:
        bz = benzersizlik(kisi_id)
        return {"birim": "kişi/varlık", "guven": 0.75 if bz < 0.98 else 0.6,
                "gerekce": f"'{kisi_id}' kişi/varlık kimliği" +
                           (" (tekrarlı ölçüm)" if bz < 0.98 else ""),
                "belirsiz": False}
    # 4) benzersiz herhangi bir id → jenerik kayıt düzeyi
    for a in alanlar:
        if benzersizlik(a) >= 0.98 and n >= 5:
            return {"birim": "kayıt", "guven": 0.5,
                    "gerekce": f"'{a}' benzersiz ama tür belirsiz (olay mı kişi mi?)",
                    "belirsiz": True}
    # 5) belirsiz
    return {"birim": "belirsiz", "guven": 0.2,
            "gerekce": "benzersiz kimlik yok; satırın temsil ettiği birim belirsiz",
            "belirsiz": True}


def profil_cikar(kayitlar: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Dosya yapısını profiller: sütun tipleri + mekân/zaman/ilişki sinyalleri.
    Returns: {n, kategorik, surekli, sayim, koordinat_oran, zaman, zaman_aralik,
              bolge_alani, kaynak_hedef, tutar_alani, kimlik_alani, metin_alani}.
    """
    n = len(kayitlar)
    if n == 0:
        return {"n": 0, "hata": "veri yok"}
    alanlar = list(kayitlar[0].keys())
    ornek = kayitlar[: min(n, 500)]

    kategorik, surekli, sayim, tarih_alan = [], [], [], []
    for alan in alanlar:
        degerler = [k.get(alan) for k in ornek if k.get(alan) not in (None, "")]
        if not degerler:
            continue
        # tarih mi?
        tarih_orani = sum(1 for d in degerler if veri.tarih_coz(d) is not None) / len(degerler)
        if tarih_orani > 0.7:
            tarih_alan.append(alan)
            continue
        # sayısal mı?
        sayi = []
        for d in degerler:
            try:
                sayi.append(float(str(d).replace(",", ".")))
            except (TypeError, ValueError):
                pass
        sayisal_oran = len(sayi) / len(degerler)
        farkli = len(set(degerler))
        if sayisal_oran > 0.9:
            if all(float(v).is_integer() and v >= 0 for v in sayi) and farkli <= max(20, n // 3):
                sayim.append(alan)
            surekli.append(alan)
        elif farkli <= min(20, max(2, n // 2)):
            kategorik.append(alan)

    # koordinat oranı
    gecerli_koord = sum(1 for k in ornek if veri.koordinat_al(k)) / len(ornek)

    # zaman aralığı (başlangıç-bitiş çifti)
    a_norm = {_normalize(a): a for a in alanlar}
    zaman_aralik = None
    for bas, bit in [("baslangic", "bitis"), ("bas", "bit"),
                     ("baslangic_zaman", "bitis_zaman"), ("ilk", "son")]:
        if bas in a_norm and bit in a_norm:
            zaman_aralik = (a_norm[bas], a_norm[bit])
            break

    # bölge alanı (düşük kardinaliteli kategorik; koordinat yoksa öncelikli)
    bolge_alani = None
    for aday in ("grid_id", "bolge", "mahalle", "ilce", "il", "bolge_id", "alan"):
        if aday in a_norm:
            bolge_alani = a_norm[aday]
            break
    if bolge_alani is None and kategorik:
        bolge_alani = kategorik[0]

    # kaynak-hedef (ilişki/ağ)
    kaynak_hedef = None
    for kay, hed in [("kaynak", "hedef"), ("source", "target"),
                     ("arayan", "aranan"), ("gonderen", "alici"),
                     ("kaynak_hesap", "hedef_hesap"), ("dugum1", "dugum2")]:
        if kay in a_norm and hed in a_norm:
            kaynak_hedef = (a_norm[kay], a_norm[hed])
            break

    # tutar (finansal)
    tutar_alani = next((a_norm[a] for a in ("tutar", "miktar", "amount", "zarar_tl")
                        if a in a_norm), None)

    # nüfus/maruz kalma (payda) alanı — oran analizi için
    nufus_alani = next((a_norm[a] for a in ("nufus", "population", "maruz_kalma",
                                            "ziyaretci", "kapasite")
                        if a in a_norm), None)

    # kimlik (tekrar mağduriyet için: mağdur/yer id + tekrar yapısı)
    kimlik_alani = next((a_norm[a] for a in ("magdur_id", "yer_id", "hedef_id",
                                             "kimlik", "adres")
                         if a in a_norm), None)

    return {"n": n, "alanlar": alanlar,
            "kategorik": kategorik, "surekli": surekli, "sayim": sayim,
            "koordinat_oran": round(gecerli_koord, 3),
            "zaman": tarih_alan, "zaman_aralik": zaman_aralik,
            "bolge_alani": bolge_alani, "kaynak_hedef": kaynak_hedef,
            "tutar_alani": tutar_alani, "kimlik_alani": kimlik_alani,
            "nufus_alani": nufus_alani, "birim": birim_tespit(kayitlar)}


# analiz adı -> (araç veya None=bu sürümde yok)
def _o(analiz, arac, gerekce, kural, uyari=None, oncelik=3):
    return {"analiz": analiz, "arac": arac, "mevcut": arac is not None,
            "gerekce": gerekce, "kaynak_kural": kural,
            "uyari": uyari, "_oncelik": oncelik}


def oner(kayitlar: List[Dict[str, Any]], soru: Optional[str] = None,
         maks: int = 6) -> Dict[str, Any]:
    """Veri profili + (opsiyonel) soruya göre sıralı analiz önerileri.
    Returns: {profil_ozet, oneriler:[...], not}.
    """
    p = profil_cikar(kayitlar)
    if p.get("hata"):
        return {"hata": p["hata"]}
    g = _normalize(soru) if soru else ""
    niyetler = {ad for ad, dsn in _NIYET.items()
                if g and re.search(_normalize(dsn), g)}

    oner_list: List[Dict[str, Any]] = []

    # R02: analiz birimi belirsizse ÖNCE kullanıcıya sor (model kurma)
    birim = p.get("birim", {})
    if birim.get("belirsiz"):
        oner_list.append(_o(f"Analiz birimi belirsiz ({birim.get('gerekce', '')})", None,
                            "satırın temsil ettiği birim netleşmeden model kurulmamalı",
                            "R02", uyari="olay/kişi/bölge satırları karışıksa frekans ve "
                                         "standart hatalar yanlış hesaplanır", oncelik=-110))

    # R03: kalite kapısı — niyet-boost'undan bağımsız HER ZAMAN ilk (Düğüm 2)
    oner_list.append(_o("Veri kalite kapısı", "veri_kalitesi",
                        "analiz öncesi mükerrer/eksik/zaman/konum kontrolü", "R03",
                        oncelik=-100))

    # R06: yalnız kategorik → frekans/çapraz
    if p["kategorik"]:
        oner_list.append(_o("Frekans ve dağılım", "frekans",
                            "kategorik alan(lar) mevcut", "R06", oncelik=2))
        if len(p["kategorik"]) >= 2:
            oner_list.append(_o("Çapraz tablo", "capraz_tablo",
                                "iki kategorik alan ilişkisi", "R06", oncelik=3))

    # R07: sürekli ölçüm → dağılım
    if p["surekli"]:
        oner_list.append(_o("Sürekli dağılım (medyan/çeyrek/aykırı)", "dagilim_olculeri",
                            "sürekli ölçüm alan(lar)ı mevcut", "R07", oncelik=3))

    # R08/R09: zaman
    if p["zaman_aralik"]:
        oner_list.append(_o("Aoristik zaman analizi", "aoristik",
                            "olay zamanı aralık (başlangıç-bitiş); orta nokta atama yanıltıcı",
                            "R09", oncelik=1))
    if p["zaman"]:
        oner_list.append(_o("Saat/gün/ay örüntüsü", "gun_saat_analizi",
                            "kesin tarih/saat mevcut", "R08",
                            uyari="mevsimsellik ve kayıt politikası değişimini kontrol et", oncelik=2))
        oner_list.append(_o("Eğilim ve değişim sinyali", "trend",
                            "düzenli dönem serisi", "R10", oncelik=3))

    # R11/R13: mekân (koordinat)
    if p["koordinat_oran"] >= 0.5:
        oner_list.append(_o("Yoğunluk / sıcak nokta", "grid_hotspot",
                            f"geçerli koordinat oranı %{int(p['koordinat_oran']*100)}", "R11",
                            uyari="sıcak nokta kayıt yoğunluğunu da yansıtabilir (yanlılık)", oncelik=1))
        oner_list.append(_o("İstatistiksel sıcak/soğuk nokta (Getis-Ord Gi*)", "sicak_nokta_gi",
                            "anlamlı yoğunlaşma testi", "R13", oncelik=2))
        oner_list.append(_o("Mekânsal küme vs aykırı (LISA)", "yerel_kumeleme",
                            "yerel küme/aykırı ayrımı", "R13", oncelik=3))
        oner_list.append(_o("Genel yönelim ve yayılım (merkez/elips)", "merkezsel_egilim",
                            "nokta dağılımının merkezi ve yönü", "R11", oncelik=4))
    elif p["koordinat_oran"] < 0.5 and (soru is None or "mekan" in niyetler):
        oner_list.append(_o("Mekânsal analiz", None,
                            "koordinat yetersiz; önce coğrafi kodlama + kalite raporu",
                            "R11/3C.1", uyari="konum kalitesi düşük", oncelik=5))

    # R15/R16: konum+zaman → yakın tekrar; kimlik+zaman → tekrar mağduriyet
    if p["koordinat_oran"] >= 0.5 and p["zaman"]:
        oner_list.append(_o("Yakın tekrar (near-repeat)", "yakin_tekrar",
                            "konum + zaman mevcut", "R15",
                            uyari="yakınlık nedensellik/aynı fail kanıtı DEĞİL", oncelik=2))
    if (p["kimlik_alani"] or p["bolge_alani"]) and p["zaman"]:
        oner_list.append(_o("Tekrar mağduriyet", "mukerrer_magduriyet",
                            "mağdur/yer kimliği + tarih", "R16", oncelik=3))

    # R17: birden fazla dönem + konum/bölge → kalıcı/yeni örüntü
    if (p["bolge_alani"] or p["koordinat_oran"] >= 0.5) and p["zaman"]:
        oner_list.append(_o("Kalıcı/yeni gelişen örüntü (emerging)", "yukselen_sicak_nokta",
                            "bölge + zaman: kalıcı/yükselen/sönen sınıflaması", "R17", oncelik=3))

    # R19: ilişki ağı
    if p["kaynak_hedef"]:
        oner_list.append(_o("İlişki/ağ analizi", "ag_analizi",
                            "kaynak-hedef varlık çiftleri mevcut", "R19",
                            uyari="çok bağlantılı olmak suçluluk anlamına gelmez", oncelik=2))
        if p["tutar_alani"]:
            oner_list.append(_o("Finansal akış örüntüleri", None,
                               "kaynak+hedef+tutar var; özel akış aracı bu sürümde yok",
                               "R20", uyari="örüntü tek başına suç kanıtı değil", oncelik=5))

    # R12: bölge alanı → oran (payda kontrolü)
    if p["bolge_alani"]:
        if p.get("nufus_alani"):
            oner_list.append(_o("Nüfusa oranlı bölge analizi (ham vs oran)", "bolge_oran",
                                "bölge + nüfus alanı: ham sayı yanıltıcı olabilir", "R12",
                                uyari="kalabalık bölge yüksek sayılı ama düşük oranlı olabilir", oncelik=3))
        else:
            oner_list.append(_o("Bölgesel karşılaştırma (payda EKSİK)", "bolge_oran",
                                "bölge alanı var ama nüfus yok; yalnız ham sayı", "R12",
                                uyari="nüfus (payda) olmadan oran haritası üretme", oncelik=5))

    # R18: zarar ağırlığı
    if p["tutar_alani"]:
        oner_list.append(_o("Hacim + zarar birlikte", "hacim_zarar_karsilastir",
                            "zarar/tutar alanı mevcut", "R18",
                            uyari="zarar endeksi olay hacminin yerine geçmez, yanına konur", oncelik=4))

    # açıklayıcı model (soru 'hangi değişkenle ilişkili')
    if "acikla" in niyetler and p["surekli"]:
        oner_list.append(_o("Çoklu doğrusal regresyon", "coklu_regresyon",
                            "sürekli sonuç + açıklayıcı değişkenler", "R26",
                            uyari="artık/varsayım tanıları zorunlu; korelasyon nedensellik değil", oncelik=3))
        if p["koordinat_oran"] >= 0.5:
            oner_list.append(_o("Mekânsal regresyon tanısı (artık otokorelasyonu)", "mekansal_regresyon",
                                "mekânsal veride OLS yanlılığı kontrolü", "R34", oncelik=4))

    # bu sürümde OLMAYAN ama soru ima ederse dürüstçe belirt
    if "acikla" in niyetler and p["sayim"]:
        oner_list.append(_o("Sayım regresyonu (Poisson/NB/ZIP)", None,
                            "sayım sonucu için; bu sürümde yok (bolge_anomali kuyruk testi var)",
                            "R30-R32", oncelik=6))

    # R39-R43: müdahale değerlendirme
    if "mudahale" in niyetler:
        oner_list.append(_o("Farkların farkı (kontrol gruplu)", "degerlendirme_did",
                            "müdahale + karşılaştırma alanı", "R40", oncelik=2))
        oner_list.append(_o("Yer değiştirme testi (WDD)", "wdd_testi",
                            "tampon + kontrol alanı ile displacement", "R42", oncelik=3))

    # risk ufku (soru 'risk')
    if "risk" in niyetler:
        oner_list.append(_o("Acil risk (yakın tekrar)", "yakin_tekrar",
                            "önceki olay çevresinde kısa vadeli risk", "3I.1-acil", oncelik=2))
        oner_list.append(_o("Kalıcı risk (Risk Terrain)", "risk_arazi",
                            "çevresel faktör co-location → kalıcı risk", "3I.1-kalıcı", oncelik=3))

    # soru varsa niyet-eşleşen ailelere öncelik ver
    if niyetler:
        aile_kural = {"betimleme": ("R06", "R07"), "zaman": ("R08", "R09", "R10"),
                      "mekan": ("R11", "R13", "R15"), "tekrar": ("R15", "R16", "R17"),
                      "iliski": ("R19", "R20"), "acikla": ("R26", "R34", "R30-R32"),
                      "risk": ("3I.1-acil", "3I.1-kalıcı"), "mudahale": ("R40", "R42")}
        ilgili = set()
        for nt in niyetler:
            ilgili.update(aile_kural.get(nt, ()))
        for o in oner_list:
            if o["kaynak_kural"] in ilgili:
                o["_oncelik"] -= 2  # öne çek

    # sırala + tekilleştir (araç bazında)
    gorulen = set()
    oner_list.sort(key=lambda o: o["_oncelik"])
    secili = []
    for o in oner_list:
        anahtar = o["arac"] or o["analiz"]
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        o.pop("_oncelik", None)
        secili.append(o)

    profil_ozet = {k: p[k] for k in ("n", "birim", "kategorik", "surekli", "sayim",
                                     "koordinat_oran", "zaman", "zaman_aralik",
                                     "bolge_alani", "kaynak_hedef", "tutar_alani")}
    return {"profil_ozet": profil_ozet,
            "oneriler": secili[: maks + 1],  # +1: kalite ilk sırada
            "not": ("Öneriler veri yapısı + soruya göredir; 'mevcut=false' olanlar "
                    "bu sürümde yoktur. Nihai yöntem seçimi ve yorum insan analiste aittir.")}
