# -*- coding: utf-8 -*-
"""kiyas/kesif/a46_yukselen.py — A4.6 sonrası EK ÖLÇÜM (ÖN-KAYIT DIŞI).

Kilitli v1 koşucusu K5.2'de yalnız "yeni sıcak nokta / yoğunlaşan / kalıcı"
etiketlerini sahte alarm sayar. A4.6 yeni bir "son dönemde sıcak" kategorisi
ekledi; o da bir sıcaklık iddiasıdır. Onu sayılmayan kategoriye kaydırmak
ölçütü oyuna getirmek olur — bu betik homojen veride "sıcak değil" DIŞINDAKİ
her kategoriyi sayar. Kullanım (depo kökünden):
    PYTHONUTF8=1 python kiyas/kesif/a46_yukselen.py
"""
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v1"))
import kos_v1  # noqa: E402  (ortamı depo dışına yönlendirir)
import uretec_v1  # noqa: E402

p = kos_v1.vaka_oku("v5_yukselen.json")["uretec"]["parametreler"]
herhangi, dagilim, artan_kat = [], {}, {}
for t in range(101, 131):
    for v in ("homojen", "artan"):
        s, g = uretec_v1.v5_yukselen(p, t, v)
        r = kos_v1.kos.arac("yukselen_sicak_nokta", s, bolge_alan="bolge", zaman_alan="tarih")["sonuc"]
        kat = {x["bolge"]: x["kategori"] for x in r["sonuclar"]}
        if v == "homojen":
            iddia = [b for b, k in kat.items() if k != "sıcak değil"]
            herhangi.append(bool(iddia))
            for b in iddia:
                dagilim[kat[b]] = dagilim.get(kat[b], 0) + 1
        else:
            artan_kat[kat[g["artan"]]] = artan_kat.get(kat[g["artan"]], 0) + 1
print(f"homojende HERHANGİ bir sıcaklık iddiası olan tohum oranı: {kos_v1.kos.oran(herhangi):.3f} | kategoriler: {dagilim}")
print(f"artan bölgenin kategorileri: {artan_kat}")
