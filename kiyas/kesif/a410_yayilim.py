# -*- coding: utf-8 -*-
"""kiyas/kesif/a410_yayilim.py — A4.10 yayılım çarpanı keşfi (ÖN-KAYIT DIŞI).

v1.1'in R-BILDIRIM ayrıştırmasında yayılım çarpanı φ, pencere/grup var/ortalama
oranlarının EN BÜYÜĞÜ olarak tahmin ediliyor. Gürültülü tahminlerin maksimumu
Poisson veride bile yukarı yanlıdır; BMK v4'te K10.5 gücünü (0,967 → 0,90) ve
v3 tohum 314'ü (BELİRSİZ yerine KIRILGAN) bundan etkilendi. Ön-kayıttaki tasarım
tanımı saf Poisson'du (φ = 1). Bu betik üç varyantı YALNIZ 901–960 tohumlarında
karşılaştırır: poisson (φ = 1), en_buyuk (mevcut), havuz (Pearson χ²/sd, tüm
grup-pencere aylarından tek tahmin, en az 1). Ölçüm değildir; bir sonraki
ön-kaydın zeminidir. Aşırı yayılımlı veride doğru φ'nin değerini görmek için
negatif binom senaryosu da vardır (aylık λ gama karışımlı).

Kullanım (depo kökünden):
    PYTHONUTF8=1 python kiyas/kesif/a410_yayilim.py
"""
import json
import os
import statistics
import sys
from collections import Counter

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v3"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v4"))
import kos_v4  # noqa: E402  (ortamı depo dışına yönlendirir)
import uretec_v4  # noqa: E402
from uretec import Tohum  # noqa: E402
from sinama.bilim import sinamalar  # noqa: E402

ASIL = sinamalar._yayilim
_havuz_birikim = []


def havuz(tarihli, gruplar, bas, bit):
    """Pearson χ²/sd'yi grup-pencere aylarından biriktirir; çağıran ikinci kez
    sorduğunda (sonra penceresi) iki pencereyi birlikte döndürür."""
    for grup in gruplar:
        say = Counter((dt.year, dt.month) for dt, k in tarihli if k in grup and bas <= dt <= bit)
        aylar, y, a = [], bas.year, bas.month
        while (y, a) <= (bit.year, bit.month):
            ay_bas = bas.replace(year=y, month=a, day=1, hour=0, minute=0, second=0, microsecond=0)
            sonraki = ay_bas.replace(year=y + (a // 12), month=a % 12 + 1)
            if ay_bas >= bas and sonraki <= bit:
                aylar.append(say.get((y, a), 0))
            y, a = (y + 1, 1) if a == 12 else (y, a + 1)
        if len(aylar) >= 3 and statistics.fmean(aylar) > 0:
            o = statistics.fmean(aylar)
            _havuz_birikim.append((sum((x - o) ** 2 for x in aylar) / o, len(aylar) - 1))
    ki, sd = sum(c for c, _ in _havuz_birikim), sum(d for _, d in _havuz_birikim)
    return max(1.0, ki / sd) if sd else 1.0


VARYANTLAR = {"poisson": lambda *a: 1.0, "en_buyuk": ASIL, "havuz": havuz}


def nb_kanallar(p, tohum, k_sekil=8.0):
    """Aşırı yayılımlı varyant: her ay-kanal λ'sı gama(k, λ/k) ile karışır (NB)."""
    t = Tohum(tohum)
    satirlar, veri = [], uretec_v4.v10_kanallar(p, tohum)[0]
    # aynı kanal/ay yapısını koru, sayıları gama karışımıyla yeniden çek
    say = Counter((s["tarih"][:7], s["kanal"]) for s in veri)
    import math
    for (ay, kanal), n in sorted(say.items()):
        lam = p["karakol_lambda"] if kanal == "karakol" else p["cevrimici_lambda"]
        if ay >= "2025-01" and kanal == "karakol":
            lam *= p["karakol_carpani"]
        # gama(k, lam/k): k tam sayı → üstel toplam
        g = sum(-math.log(1.0 - t.u()) for _ in range(int(k_sekil))) * lam / k_sekil
        for i in range(t.poisson(g)):
            satirlar.append({"tarih": f"{ay}-{1 + i % 28:02d}", "kanal": kanal})
    satirlar.sort(key=lambda s: s["tarih"])
    for i, s in enumerate(satirlar):
        s["id"] = f"nb-{i}"
    return satirlar


vaka = kos_v4.vaka_oku()
TOHUMLAR = range(901, 961)
sonuc = {}
for ad, fn in VARYANTLAR.items():
    sinamalar._yayilim = fn
    for senaryo in ("saf_artefakt", "kismi_artefakt", "karma", "gercek_artis_kucuk_kanal"):
        for nb in (False, True):
            p = uretec_v4.parametreler(vaka, senaryo)
            dag = Counter()
            for t in TOHUMLAR:
                _havuz_birikim.clear()
                satirlar = nb_kanallar(p, t) if nb else uretec_v4.v10_kanallar(p, t)[0]
                s, hata = kos_v4.kos_v3.cagir(vaka, senaryo, satirlar)
                dag["HATA" if hata else s["hukum"]["kategori"]] += 1
            sonuc.setdefault(f"{senaryo}{'_NB' if nb else ''}", {})[ad] = dict(sorted(dag.items()))
sinamalar._yayilim = ASIL
for senaryo, v in sonuc.items():
    print(f"{senaryo:28s} " + " | ".join(f"{ad}: {json.dumps(d, ensure_ascii=False)}" for ad, d in v.items()))
