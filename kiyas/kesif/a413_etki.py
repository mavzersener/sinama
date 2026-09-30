# -*- coding: utf-8 -*-
"""kiyas/kesif/a413_etki.py — ETKİ soru türü keşfi (ÖN-KAYIT DIŞI).

BMK v7 vaka dosyasının senaryolarını (kiyas/v7/vakalar/v13_etki.json) keşif
tohumlarında (901–950; ölçüm tohumları 10001+ görülmez) resmi Rehberli akıştan,
depodaki GERÇEK çekirdekle koşar (yama yok). Uygulama öngörüsünün zeminidir.
Kullanım (depo kökünden):
    PYTHONUTF8=1 python kiyas/kesif/a413_etki.py
"""
import json
import os
import sys
from collections import Counter

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for alt in ("kiyas", os.path.join("kiyas", "v3"), os.path.join("kiyas", "v7")):
    sys.path.insert(0, os.path.join(KOK, alt))
import kos_v3  # noqa: E402  (ortamı depo dışına yönlendirir; sözleşme kodu)
import uretec_v7  # noqa: E402

with open(os.path.join(KOK, "kiyas", "v7", "vakalar", "v13_etki.json"), encoding="utf-8") as f:
    VAKA = json.load(f)
TAM = VAKA["argumanlar_tam"]
KONTROLSUZ = {k: TAM[k] for k in ("bolge_alan", "mudahale", "kesinti_tarihi")}
cagri_vaka = {"arac": VAKA["arac"], "senaryolar": {
    s: {**d, "argumanlar": TAM if d["argumanlar"] == "tam" else KONTROLSUZ}
    for s, d in VAKA["senaryolar"].items()}}

for senaryo in VAKA["senaryolar"]:
    p = uretec_v7.parametreler(VAKA, senaryo)
    kat, rakip, tutulan_rakip = Counter(), Counter(), Counter()
    for t in range(901, 951):
        s, hata = kos_v3.cagir(cagri_vaka, senaryo, uretec_v7.v13_bolgeler(p, t)[0])
        if hata:
            kat["HATA:" + hata] += 1
            continue
        h = s["hukum"]
        kat[h["kategori"]] += 1
        if h["birincil_ongoru"] == "tutuldu":
            tutulan_rakip[str(h["en_guclu_rakip"])] += 1
    print(f"{senaryo:17s} {json.dumps(dict(sorted(kat.items())), ensure_ascii=False)} | "
          f"tutulanlarda en güçlü: {json.dumps(dict(sorted(tutulan_rakip.items())), ensure_ascii=False)}",
          flush=True)
