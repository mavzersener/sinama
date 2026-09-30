# -*- coding: utf-8 -*-
"""kiyas/kesif/a417_bolme_yani.py — KEŞİF (ön-kayıt dışı, tasarım tohumları 3000–3299).

Hipotez: R-BILDIRIM ayrıştırmasının ayrım noktası (yeni kanalın %5'lik tarihi) yeni
kanalın ilk olaylarını "öncesi"ne yazarak z'yi sürekli kanallar lehine kaydırıyor
(aşırı iddia). Ayrıştırma çekirdeğin işleviyle (degerlendirme.oran_degisimi_ayristirma),
ayrım noktası üç biçimde: v1.3 (%5'lik), B1 (yeni kanalın tüm olayları sonrası), B2
(ilk olay). Çekirdek değiştirilmez. Kullanım: python kiyas/kesif/a417_bolme_yani.py
"""
import os
import statistics
import sys
from collections import Counter

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for alt in ("kiyas", os.path.join("kiyas", "v6"), "cekirdek"):
    sys.path.insert(0, os.path.join(KOK, alt))
import uretec_v6  # noqa: E402
from sinama.cekirdek import degerlendirme, veri  # noqa: E402
from sinama.bilim import sinamalar as S  # noqa: E402

TEMEL = {"baslangic": "2024-01-01", "ay_sayisi": 24, "kesinti_ayi": 13,
         "karakol_lambda": 40, "cevrimici_lambda": 12, "cevrimici": "kesinti"}
SEN = {"karma_poisson": {"karakol_carpani": 1.3, "yayilim_k": {}},
       "saf_bildirim": {"karakol_carpani": 1.0, "yayilim_k": {}}}


def z_hesap(kayitlar, kip):
    """Ayrıştırmanın z'si; kip ayrım noktasını ve yeni kanal sayımını belirler."""
    tarihli = S._tarihli(veri.tiplendir(kayitlar), "kanal")
    surekli = S._surekli_kanallar(tarihli)
    yeni = [k for k in sorted({k for _, k in tarihli}, key=str) if k not in surekli]
    yt = sorted(dt for dt, k in tarihli if k in yeni)
    t_k = yt[0] if kip == "B2" else yt[int(S.YENI_KANAL_YUZDELIK * len(yt))]
    t0, t1 = min(dt for dt, _ in tarihli), max(dt for dt, _ in tarihli)
    g_o, g_s = (t_k.date() - t0.date()).days, (t1.date() - t_k.date()).days + 1
    say = Counter((k in surekli, dt >= t_k) for dt, k in tarihli)
    b_o, b_s = say[(False, False)], say[(False, True)]
    if kip == "B1":
        b_o, b_s = 0, b_o + b_s
    r = degerlendirme.oran_degisimi_ayristirma(say[(True, False)], say[(True, True)], b_o, b_s, g_o, g_s)
    return r["z"]


if __name__ == "__main__":
    for akis in (sys.stdout, sys.stderr):
        akis.reconfigure(encoding="utf-8")
    for ad, d in SEN.items():
        p = {**TEMEL, **d}
        satir = []
        for kip in ("v1.3", "B1", "B2"):
            zs = [z_hesap(uretec_v6.v12_kanallar(p, t)[0], kip) for t in range(3000, 3300)]
            satir.append(f"{kip}: ort z {statistics.fmean(zs):+.3f}, z>1.645 "
                         f"{sum(z > 1.645 for z in zs) / len(zs):.3f}, z<-1.645 "
                         f"{sum(z < -1.645 for z in zs) / len(zs):.3f}")
        print(ad, "|", " | ".join(satir), flush=True)
