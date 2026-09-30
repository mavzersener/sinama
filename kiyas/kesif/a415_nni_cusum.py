# -*- coding: utf-8 -*-
"""
a415_nni_cusum.py — KEŞİF (ön-kayıt dışı): NNI ve CUSUM araçlarının varsayılan
davranışı, v8 senaryolarında, tasarım tohumlarıyla (900–999).

Araçlar resmi yoldan ve VARSAYILAN argümanlarla çağrılır; betik çekirdeğin o anki
durumunu ölçer (aday uygulama da gerçek kod durumunda, `git stash` ile karşılaştırılır
— A4.12 dersi: keşif kodu uygulamayla özdeş olmalı). Kilitli dosyalara dokunmaz.

Kullanım (depo kökünden): python kiyas/kesif/a415_nni_cusum.py [adet]
"""
import os
import statistics
import sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, "cekirdek"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v8"))

from sinama.arayuz import sunucu  # noqa: E402
import uretec_v8  # noqa: E402

NOKTA = {"merkez_lat": 41.0135, "merkez_lon": 29.0179, "kenar_km": 3.0, "n": 200}
SERI = {"baslangic": "2024-01-01", "ay_sayisi": 24, "kesinti_ayi": 13, "lambda": 40,
        "carpan_sonra": 1.0}
V14 = {"csr": {"desen": "csr"}, "csr_kucuk": {"desen": "csr", "n": 50},
       "kume": {"desen": "kume", "ebeveyn": 10, "sigma_km": 0.15},
       "kume_kucuk": {"desen": "kume", "ebeveyn": 5, "sigma_km": 0.25, "n": 50},
       "odak": {"desen": "odak", "odak_orani": 0.30, "sigma_km": 0.15}}
V15 = {"sabit": {}, "sabit_nb": {"yayilim_k": 8}, "sabit_dusuk": {"lambda": 12},
       "artis30": {"carpan_sonra": 1.3}, "artis50": {"carpan_sonra": 1.5},
       "artis30_nb": {"carpan_sonra": 1.3, "yayilim_k": 8}}


def arac(ad, satirlar):
    """Aracı resmi yoldan varsayılan argümanlarla çağırır."""
    return sunucu.arac_calistir(ad, {"satirlar": satirlar})


def main(adet=100):
    tohumlar = range(900, 900 + adet)
    print(f"== V14 NNI ({adet} tohum)")
    for ad, d in V14.items():
        p = {**NOKTA, **d}
        nni, kume, duzgun, uyari = [], 0, 0, 0
        for t in tohumlar:
            r = arac("nni", uretec_v8.v14_noktalar(p, t)[0])
            s = r["sonuc"]
            nni.append(s["nni"])
            kume += s["nni"] < 1 and s["p"] < 0.05
            duzgun += s["nni"] > 1 and s["p"] < 0.05
            uyari += any("yerel" in u for u in r["meta"]["uyarilar"])
        print(f"{ad:10s} ort NNI {statistics.mean(nni):.4f}  kümelenme {kume / adet:.2f}  "
              f"düzgün {duzgun / adet:.2f}  yerel-uyarı {uyari / adet:.2f}")
    print(f"== V15 CUSUM ({adet} tohum)")
    for ad, d in V15.items():
        p = {**SERI, **d}
        say = dict.fromkeys(("yok", "önce", "[-15,60]", "[-15,90]", "[-15,180]"), 0)
        gecikme = []
        for t in tohumlar:
            satirlar, g = uretec_v8.v15_seri(p, t)
            alarmlar = arac("cusum", satirlar)["sonuc"]
            if not alarmlar:
                say["yok"] += 1
                continue
            fark = alarmlar[0]["gun"] - g["kesinti_gunu"]
            gecikme.append(fark)
            say["önce"] += fark < -15
            for ust in (60, 90, 180):
                say[f"[-15,{ust}]"] += -15 <= fark <= ust
        print(f"{ad:11s} " + "  ".join(f"{k} {v / adet:.2f}" for k, v in say.items())
              + f"  medyan gecikme {statistics.median(gecikme) if gecikme else None}")


if __name__ == "__main__":
    for akis in (sys.stdout, sys.stderr):
        akis.reconfigure(encoding="utf-8")
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 100)
