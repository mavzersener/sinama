# -*- coding: utf-8 -*-
"""test_kesinti_araci.py — kesinti_analizi aracı (A4.7): kayıt → dönem serisi → ITS.

BMK v0 K2.5: ITS çekirdekte vardı ama araç olarak açık değildi; açılmadan önce
segmentli regresyona (belirsizlikle) yükseltildi. Veri sentetiktir.
"""
import datetime
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sinama.arayuz import sunucu  # noqa: E402
from sinama.cekirdek.hatalar import KullanimHatasi  # noqa: E402


def aylik_kayitlar(sayimlar, bas=datetime.date(2024, 1, 1)):
    """Her ay için verilen sayıda kaydı ayın 10'una yazar."""
    satirlar = []
    for ay, n in enumerate(sayimlar):
        y, m = bas.year + (bas.month - 1 + ay) // 12, (bas.month - 1 + ay) % 12 + 1
        satirlar += [{"tarih": f"{y}-{m:02d}-10"} for _ in range(n)]
    return satirlar


class TestKesintiAraci(unittest.TestCase):
    def test_aylik_seviye_sicramasi(self):
        onces = [40, 42, 39, 41, 38, 43, 40, 41, 39, 42, 40, 41]
        sayim = onces + [x + 15 for x in onces]
        p = sunucu.arac_calistir("kesinti_analizi",
                                 {"satirlar": aylik_kayitlar(sayim), "kesinti_tarihi": "2025-01-01"})
        s = p["sonuc"]
        self.assertEqual((s["donem"], s["donem_sayisi"], s["kesinti_donemi"]), ("ay", 24, 12))
        self.assertEqual(s["seri"], sayim)
        self.assertLess(s["seviye_degisimi"]["p"], 0.05)
        self.assertTrue(s["seviye_degisimi"]["ga_alt"] > 0)
        self.assertIn("nedensellik", " ".join(p["meta"]["uyarilar"]))

    def test_aralik_disi_kesinti_kullanim_hatasi(self):
        with self.assertRaises(KullanimHatasi):
            sunucu.arac_calistir("kesinti_analizi",
                                 {"satirlar": aylik_kayitlar([5] * 6), "kesinti_tarihi": "2030-01-01"})


if __name__ == "__main__":
    unittest.main()
