# -*- coding: utf-8 -*-
"""
skor.py — Ağırlıklı kural motoru ile risk skorlama ve eşik uyarıları.
Kurallar veri olarak tanımlanır; kod değişikliği gerekmez.
"""

from collections import defaultdict


def risk_skoru(kayit, kurallar):
    """
    kurallar: [{'alan':..., 'kosul': '=='/'>='/ '<='/'icerir', 'deger':..., 'agirlik':...}, ...]
    Koşulu sağlayan kuralların ağırlıkları toplanır.
    Dönüş: (skor, [tetiklenen_kural_aciklamalari])
    """
    skor = 0.0
    tetik = []
    for r in kurallar:
        v = kayit.get(r["alan"])
        hedef, kosul = r.get("deger"), r.get("kosul", "==")
        ok = False
        try:
            if kosul == "==":
                ok = str(v) == str(hedef)
            elif kosul == ">=":
                ok = float(v) >= float(hedef)
            elif kosul == "<=":
                ok = float(v) <= float(hedef)
            elif kosul == ">":
                ok = float(v) > float(hedef)
            elif kosul == "<":
                ok = float(v) < float(hedef)
            elif kosul == "icerir":
                ok = str(hedef).lower() in str(v).lower()
        except (TypeError, ValueError):
            ok = False
        if ok:
            skor += float(r.get("agirlik", 1.0))
            tetik.append(f'{r["alan"]} {kosul} {hedef} (+{r.get("agirlik", 1.0)})')
    return skor, tetik


def toplu_skorla(kayitlar, kurallar, id_alan="id"):
    """Tüm kayıtları skorlar, azalan sıralar; skor>0 olanları döner."""
    sonuc = []
    for k in kayitlar:
        s, tetik = risk_skoru(k, kurallar)
        if s > 0:
            sonuc.append({"id": k.get(id_alan), "skor": round(s, 2),
                          "tetiklenen": tetik})
    sonuc.sort(key=lambda x: -x["skor"])
    return sonuc


def esik_uyarilari(kayitlar, alan, esik, yon="ust", grupla=None):
    """
    Eşik aşımı uyarıları. grupla verilirse (örn. 'mahalle') grup bazında
    toplam/ortalama eşiği aşanları raporlar.
    Dönüş: [{'grup':..., 'deger':..., 'esik':...}]
    """
    if grupla is None:
        sonuc = []
        for k in kayitlar:
            try:
                v = float(k.get(alan))
            except (TypeError, ValueError):
                continue
            if (yon == "ust" and v >= esik) or (yon == "alt" and v <= esik):
                sonuc.append({"kayit": k.get("id"), "deger": v, "esik": esik})
        return sonuc
    toplamlar = defaultdict(float)
    for k in kayitlar:
        try:
            toplamlar[str(k.get(grupla))] += float(k.get(alan))
        except (TypeError, ValueError):
            continue
    return [{"grup": g, "deger": round(v, 2), "esik": esik}
            for g, v in toplamlar.items()
            if (yon == "ust" and v >= esik) or (yon == "alt" and v <= esik)]
