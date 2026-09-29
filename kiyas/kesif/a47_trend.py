# -*- coding: utf-8 -*-
"""kiyas/kesif/a47_trend.py — A4.7 sonrası EK ÖLÇÜM (ÖN-KAYIT DIŞI).

A4.7 trend yorumuna eğim t-testi ekledi. Öngörü "K2.2 = 1,00 kalır" idi;
ölçüm 0,967 verdi (30 tohumun 1'inde tüm kayıtlarda "anlamlı trend yok").
Bu betik kaybedilen tohumu ve nedenini gösterir: günlük seri, eğim, p,
kesinti öncesi/sonrası ortalama ve ITS (kesinti_analizi, aylık) sonucu.
Kullanım (depo kökünden):
    PYTHONUTF8=1 python kiyas/kesif/a47_trend.py
"""
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
import kos  # noqa: E402  (ortamı depo dışına yönlendirir)
import uretec  # noqa: E402

vaka = kos.vaka_oku("v2_bildirim.json")
p = vaka["uretec"]["parametreler"]
pler = []
for t in kos.tohumlar(vaka, None):
    s, g = uretec.v2_bildirim(p, t)
    tr = kos.arac("trend", s)["sonuc"]
    pler.append((tr["p"], t))
    if tr["yorum"] != "artan":
        its = kos.arac("kesinti_analizi", s, kesinti_tarihi=g.get("kesinti_tarihi")
                       or f"2025-{p['kesinti_ayi'] - 12:02d}-01")["sonuc"]
        print(f"tohum {t}: trend={tr['yorum']} eğim={tr['egim']} p={tr['p']} | "
              f"ITS seviye={its['seviye_degisimi']} eğim_değişimi={its['egim_degisimi']} "
              f"DW={its['durbin_watson']} uyarılar={its['uyarilar']}")
pler.sort()
print("trend p dağılımı (en büyük 5):", pler[-5:])
