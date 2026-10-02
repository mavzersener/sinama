# -*- coding: utf-8 -*-
"""
e2e/sunucu.py — uçtan uca ekran testleri için arka uç: geçici (depo dışı) veri kökü,
BMK üreteçlerinden sentetik veri (v0 V2 bildirim artefaktı, v7 V13 gerçek etki), dil
modeli kapalı, 127.0.0.1:8812. Playwright webServer olarak başlatır.
"""
import atexit
import csv
import json
import os
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
for alt in ("", "kiyas", os.path.join("kiyas", "v7")):
    sys.path.insert(0, os.path.join(KOK, alt))

import uretec  # noqa: E402
import uretec_v7  # noqa: E402
import uvicorn  # noqa: E402
from uygulama.sunucu import uygulama_olustur  # noqa: E402


def yaz(yol, satirlar, alanlar):
    """Sentetik satırları CSV'ye yazar."""
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alanlar)
        w.writeheader()
        for s in satirlar:
            w.writerow({k: s[k] for k in alanlar})


def main():
    """Veri kökünü kurar ve sunucuyu başlatır."""
    kok = tempfile.mkdtemp(prefix="sinama_e2e_")
    atexit.register(shutil.rmtree, kok, ignore_errors=True)
    os.makedirs(os.path.join(kok, "veri"))
    p = {"baslangic": "2024-01-01", "ay_sayisi": 24, "kesinti_ayi": 13, "karakol_lambda": 40,
         "cevrimici_lambda": 12}
    yaz(os.path.join(kok, "veri", "bildirim.csv"), uretec.v2_bildirim(p, 950)[0], ["id", "tarih", "kanal"])
    with open(os.path.join(KOK, "kiyas", "v7", "vakalar", "v13_etki.json"), encoding="utf-8") as f:
        v7 = json.load(f)
    satirlar, _ = uretec_v7.v13_bolgeler(uretec_v7.parametreler(v7, "gercek_etki"), 951)
    yaz(os.path.join(kok, "veri", "etki.csv"), satirlar, ["id", "tarih", "bolge"])
    uvicorn.run(uygulama_olustur(veri_koku=kok, dil_modeli_url=None), host="127.0.0.1", port=8812,
                log_level="warning")


if __name__ == "__main__":
    main()
