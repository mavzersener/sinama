# -*- coding: utf-8 -*-
"""kiyas/kesif/a412_bilesen_yayilim.py — sınama v1.3 keşfi (ÖN-KAYIT DIŞI).

v1.2'nin dersi: keşif, uygulanan tahminciyle BİREBİR aynı kodu ölçmeli (a410'daki
"havuz" varyantı maymun yamasıyla farklı bir tahminciyi ölçmüştü). Bu betik yama
YAPMAZ: depodaki çekirdek o an ne ise (v1.1 commit'i ya da çalışma ağacındaki
v1.3) onu resmi Rehberli akıştan koşar. Karşılaştırma iki kod durumunda ayrı
koşularla yapılır. Tohumlar yalnız 901+ (ölçüm tohumları görülmez).

Aday senaryolar: kanalların yayılımı farklı (v6 üreteci, kanal başına k).
Kullanım (depo kökünden):
    PYTHONUTF8=1 python kiyas/kesif/a412_bilesen_yayilim.py [etiket]
"""
import json
import os
import sys
from collections import Counter

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for alt in ("kiyas", os.path.join("kiyas", "v3"), os.path.join("kiyas", "v6")):
    sys.path.insert(0, os.path.join(KOK, alt))
import kos_v3  # noqa: E402  (ortamı depo dışına yönlendirir; sözleşme kodu)
import uretec_v6  # noqa: E402
from sinama.bilim import sinamalar  # noqa: E402

TEMEL = {"baslangic": "2024-01-01", "ay_sayisi": 24, "kesinti_ayi": 13,
         "karakol_lambda": 40, "cevrimici_lambda": 12, "cevrimici": "kesinti"}
SENARYOLAR = {   # ad: (değişen, tohum sayısı, ölçülen)
    "karma_nb_ikisi": ({"karakol_carpani": 1.3, "yayilim_k": {"karakol": 8, "cevrimici": 8}}, 60, "asiri"),
    "karma_s_nb": ({"karakol_carpani": 1.3, "yayilim_k": {"karakol": 8, "cevrimici": None}}, 60, "asiri"),
    "karma_y_nb": ({"karakol_carpani": 1.3, "yayilim_k": {"karakol": None, "cevrimici": 1}}, 60, "asiri"),
    "kismi_y_nb": ({"karakol_carpani": 1.1, "yayilim_k": {"karakol": None, "cevrimici": 1}}, 60, "asiri"),
    "saf_s_nb": ({"karakol_carpani": 1.0, "yayilim_k": {"karakol": 8, "cevrimici": None}}, 60, "asiri"),
    "guc_y_nb": ({"karakol_carpani": 1.3, "cevrimici_lambda": 2,
                  "yayilim_k": {"karakol": None, "cevrimici": 1}}, 100, "guc"),
    "guc_poisson": ({"karakol_carpani": 1.3, "cevrimici_lambda": 2, "yayilim_k": {}}, 100, "guc"),
}
VAKA = {"arac": "rehberli_calisma",
        "senaryolar": {ad: {"soru_turu": "ARTIS", "amac": "dogrulayici",
                            "argumanlar": {"kanal_alan": "kanal"}} for ad in SENARYOLAR}}

etiket = sys.argv[1] if len(sys.argv) > 1 else sinamalar.SINAMA_SURUMU
sonuc = {}
for ad, (degisen, adet, olcu) in SENARYOLAR.items():
    p = {**TEMEL, **degisen}
    dag = Counter()
    for t in range(901, 901 + adet):
        s, hata = kos_v3.cagir(VAKA, ad, uretec_v6.v12_kanallar(p, t)[0])
        dag["HATA" if hata else s["hukum"]["kategori"]] += 1
    n = sum(dag.values())
    deger = (n - dag["DESTEKLENDİ"] - dag["ÇEKİMSER"] - dag["HATA"]) / n if olcu == "asiri" \
        else dag["DESTEKLENDİ"] / n
    sonuc[ad] = {"olcu": olcu, "deger": round(deger, 3), "dagilim": dict(sorted(dag.items()))}
    print(f"[{etiket}] {ad:16s} {olcu:5s} {deger:.3f} {json.dumps(dict(sorted(dag.items())), ensure_ascii=False)}",
          flush=True)
