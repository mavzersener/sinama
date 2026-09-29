# -*- coding: utf-8 -*-
"""
zarar.py — Crime Harm Index (CHI) ve power-few analizi
(The Crime Analyst's Companion, Bölüm 13; Sherman/Neyroud/Cambridge CHI
geleneği). İlke: olayları sayıyla değil ZARARLA ağırlıklandır.

Ağırlık tablosu jürisdiksyona özeldir: "ilk suçlu için başlangıç cezası
(gün)" mantığıyla kurum kendi tablosunu JSON olarak verir. Varsayılan tablo
yalnızca ÖRNEKTİR; üretimde kurum tablosu kullanılmalıdır (demokratik
meşruiyet ilkesi — ağırlıkları analist değil mevzuat belirler).
"""

import json
import os

# ÖRNEK tablo (gün cinsinden); kurum kendi mevzuatına göre değiştirmelidir
VARSAYILAN_AGIRLIKLAR = {
    "cinayet": 5475, "adam öldürme": 5475,
    "cinsel saldırı": 1825,
    "gasb": 730, "soygun": 730,
    "kasten yaralama": 365, "ağır yaralama": 730,
    "kapkaç": 180,
    "hırsızlık": 90, "konut hırsızlığı": 180, "işyeri hırsızlığı": 120,
    "oto hırsızlığı": 120,
    "dolandırıcılık": 60,
    "mala zarar verme": 30,
    "kavga": 14,
    "uyuşturucu": 30,
    "diğer": 10,
}


def agirlik_tablosu_yukle(yol=None):
    """Kurum ağırlık tablosunu JSON'dan yükler; yoksa örnek tablo."""
    if yol and os.path.isfile(yol):
        with open(yol, encoding="utf-8") as f:
            tablo = json.load(f)
        return {str(k).lower(): float(v) for k, v in tablo.items()}
    return dict(VARSAYILAN_AGIRLIKLAR)


def olay_zarari(tur, agirliklar):
    """Tek olayın zarar puanı; bilinmeyen tür 'diğer' ağırlığı alır."""
    return agirliklar.get(str(tur).lower().strip(),
                          agirliklar.get("diğer", 10))


def zarar_tablosu(kayitlar, tur_alan="tur", agirliklar=None, grup_alan=None):
    """
    Toplam ve grup bazında zarar.
    Dönüş: {'toplam_zarar', 'olay_sayisi', 'ortalama_zarar',
            'gruplar': {grup: {'zarar', 'adet', 'pay'}}} (azalan sıralı)
    """
    agirliklar = agirliklar or agirlik_tablosu_yukle()
    gruplar = {}
    toplam = 0.0
    for k in kayitlar:
        z = olay_zarari(k.get(tur_alan), agirliklar)
        toplam += z
        g = str(k.get(grup_alan)) if grup_alan else "_toplam"
        e = gruplar.setdefault(g, {"zarar": 0.0, "adet": 0})
        e["zarar"] += z
        e["adet"] += 1
    for g, e in gruplar.items():
        e["zarar"] = round(e["zarar"], 1)
        e["pay"] = round(e["zarar"] / (toplam or 1e-9), 4)
    sirali = dict(sorted(gruplar.items(), key=lambda x: -x[1]["zarar"]))
    return {"toplam_zarar": round(toplam, 1), "olay_sayisi": len(kayitlar),
            "ortalama_zarar": round(toplam / (len(kayitlar) or 1), 2),
            "gruplar": sirali}


def power_few(kayitlar, grup_alan, tur_alan="tur", agirliklar=None,
              hedef_pay=0.5):
    """
    Power Few: toplam zararın hedef_pay'ını (varsayılan %50) üreten en
    küçük birim kümesi (fail/kurban/adres/mahalle).
    Dönüş: {'birimler': [...], 'birim_sayisi', 'toplam_birim',
            'yogunlasma_orani', 'pareto': [...]}
    """
    tablo = zarar_tablosu(kayitlar, tur_alan, agirliklar, grup_alan)
    toplam = tablo["toplam_zarar"]
    birimler, pareto = [], []
    birikim = 0.0
    for g, e in tablo["gruplar"].items():
        birikim += e["zarar"]
        pareto.append({"birim": g, "zarar": e["zarar"], "adet": e["adet"],
                       "kumulatif_pay": round(birikim / (toplam or 1e-9), 4)})
        if birikim / (toplam or 1e-9) <= hedef_pay or not birimler:
            birimler.append(g)
    return {"birimler": birimler,
            "birim_sayisi": len(birimler),
            "toplam_birim": len(tablo["gruplar"]),
            "yogunlasma_orani": round(
                len(birimler) / (len(tablo["gruplar"]) or 1), 3),
            "hedef_pay": hedef_pay,
            "pareto": pareto[:50]}


def hacim_zarar_karsilastir(kayitlar, grup_alan, tur_alan="tur",
                            agirliklar=None):
    """
    Hacim (adet) sıralaması ile zarar sıralamasının ayrışması.
    'sayıyla yoğun ama zararsız' vs 'seyrek ama ağır' birimleri gösterir.
    Dönüş: her grup için hacim_sirasi, zarar_sirasi, fark ve sinif.
    """
    tablo = zarar_tablosu(kayitlar, tur_alan, agirliklar, grup_alan)["gruplar"]
    hacim_sira = {g: i + 1 for i, (g, _) in enumerate(
        sorted(tablo.items(), key=lambda x: -x[1]["adet"]))}
    zarar_sira = {g: i + 1 for i, g in enumerate(tablo.keys())}
    sonuc = []
    for g in tablo:
        fark = hacim_sira[g] - zarar_sira[g]
        if fark >= 2:
            sinif = "seyrek ama ağır (gözden kaçan risk)"
        elif fark <= -2:
            sinif = "yoğun ama hafif (hacim yanılgısı)"
        else:
            sinif = "uyumlu"
        sonuc.append({"grup": g, "adet": tablo[g]["adet"],
                      "zarar": tablo[g]["zarar"],
                      "hacim_sirasi": hacim_sira[g],
                      "zarar_sirasi": zarar_sira[g],
                      "fark": fark, "sinif": sinif})
    sonuc.sort(key=lambda x: x["zarar_sirasi"])
    return sonuc
