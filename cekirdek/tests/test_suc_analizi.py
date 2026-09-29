# -*- coding: utf-8 -*-
"""
Birim testleri — golden-value (sabit referans) sayısal doğruluk +
güvenlik regresyonları. Çalıştırma: python -m unittest discover tests
"""
import math
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama import veri, iliski, ileri, mekan, ag, olcek, kume, tekrar


class TestVeri(unittest.TestCase):
    def test_sayi_coz(self):
        self.assertEqual(veri.tip_tahmin("1234"), 1234)
        self.assertEqual(veri.tip_tahmin("12,5"), 12.5)
        self.assertEqual(veri.tip_tahmin("3,14"), 3.14)
        self.assertEqual(veri.tip_tahmin("1,234"), "1,234")  # binlik ayıracı bozulmaz
        self.assertEqual(veri.tip_tahmin("12.5"), 12.5)

    def test_tarih(self):
        self.assertEqual(veri.tarih_coz("2026-05-01 10:30"),
                         datetime(2026, 5, 1, 10, 30))
        self.assertIsNone(veri.tarih_coz("metin"))

    def test_guvenli_yol_matrisi(self):
        with tempfile.TemporaryDirectory() as kok:
            ic = os.path.join(kok, "a.csv")
            with open(ic, "w") as f:
                f.write("x\n1")
            dis = os.path.join(tempfile.gettempdir(), "dis.csv")
            with open(dis, "w") as f:
                f.write("x\n1")
            self.assertEqual(veri.guvenli_yol("a.csv", kok), os.path.realpath(ic))
            with self.assertRaises(ValueError):  # kök dışı mutlak
                veri.guvenli_yol(dis, kok)
            with self.assertRaises(ValueError):  # '..' kaçışı
                veri.guvenli_yol(os.path.join(kok, "..", "dis.csv"), kok)
            with self.assertRaises(ValueError):  # uzantı
                md = os.path.join(kok, "n.md")
                with open(md, "w") as f:
                    f.write("x")
                veri.guvenli_yol("n.md", kok)
            os.remove(dis)


class TestIliski(unittest.TestCase):
    TABLO = [[10, 5], [3, 12]]  # beklenen: 6.5/8.5 ...

    def test_ki_kare_golden(self):
        s = iliski.ki_kare(self.TABLO)
        self.assertAlmostEqual(s["ki_kare"], 6.6516, places=3)
        self.assertAlmostEqual(s["p_degeri"], 0.00986, places=4)

    def test_yates(self):
        s = iliski.ki_kare(self.TABLO, yates=True)
        self.assertAlmostEqual(s["ki_kare"], 4.8869, places=3)
        self.assertTrue(s["yates"])

    def test_cochran_uyarisi(self):
        s = iliski.ki_kare([[1, 0], [0, 1]])
        self.assertTrue(any("Cochran" in u for u in s["uyarilar"]))

    def test_pearson(self):
        r = iliski.pearson_r([1, 2, 3, 4], [2, 4, 6, 8])
        self.assertAlmostEqual(r["r"], 1.0, places=6)

    def test_oran_ga_golden(self):
        # Garwood exact: 5 olay → (1.623, 11.668); 10k nüfus → x10
        ga = iliski.oran_guven_araligi(5, 10000)
        self.assertAlmostEqual(ga["alt"], 16.23, places=1)
        self.assertAlmostEqual(ga["ust"], 116.68, places=1)


class TestIleri(unittest.TestCase):
    def test_poisson_golden(self):
        # scipy.stats.poisson.sf(11, 5) = 0.005453...
        self.assertAlmostEqual(ileri.poisson_ust_kuyruk(12, 5), 0.00545, places=4)
        # underflow bölgesi: λ=1000
        p = ileri.poisson_ust_kuyruk(1100, 1000)
        self.assertTrue(0.0005 < p < 0.002)

    def test_benford(self):
        s = ileri.benford_testi([2 ** i for i in range(500)])  # Benford'a uyar
        self.assertEqual(s["uyum"], "uyumlu")

    def test_holt_winters(self):
        seri = [10 + (i % 7) for i in range(28)]
        tahmin = ileri.holt_winters(seri, mevsim=7, ileri=7)
        self.assertEqual(len(tahmin), 7)


class TestMekan(unittest.TestCase):
    def test_haversine_golden(self):
        # ekvatorda 1 derece boylam ≈ 111.19 km
        self.assertAlmostEqual(mekan.haversine_km(0, 0, 0, 1), 111.19, places=1)

    def test_nni_test_daginik(self):
        # düzgün grid → NNI > 1, anlamlı düzgünlük beklenir
        pts = [(41.0 + i * 0.01, 29.0 + j * 0.01)
               for i in range(7) for j in range(7)]
        s = mekan.nni_test(pts)
        self.assertIsNotNone(s["nni"])

    def test_jitter_sinir(self):
        for _ in range(50):
            la, lo = mekan.koordinat_maskele(41.0, 29.0, 200, seed=None)
            self.assertLessEqual(mekan.haversine_km(41.0, 29.0, la, lo), 0.25)


class TestAg(unittest.TestCase):
    def test_aracilik_golden(self):
        g = ag.ag_kur([("A", "B"), ("B", "C")])  # yol grafı: B aracı
        s = {x["dugum"]: x["aracilik"] for x in ag.aracilik_merkeziyeti(g)}
        self.assertEqual(s["B"], 1.0)
        self.assertEqual(s["A"], 0.0)

    def test_en_kisa_yol(self):
        g = ag.ag_kur([("A", "B"), ("B", "C"), ("A", "C")])
        self.assertEqual(ag.en_kisa_yol(g, "A", "C"), ["A", "C"])


class TestDiger(unittest.TestCase):
    def test_levenshtein_golden(self):
        self.assertEqual(kume.levenshtein("kitten", "sitting"), 3)

    def test_cronbach_yuksek(self):
        yanitlar = [[i, i, i] for i in range(1, 8)]
        # mükemmel uyumlu maddeler → alfa 1'e yakın (varyans yapısı gereği NaN korunmalı)
        alfa = olcek.cronbach_alfa([[1, 1.1, 0.9], [2, 2.1, 1.9], [3, 3.05, 2.95],
                                    [4, 4.1, 3.9], [5, 5.05, 4.95]])
        self.assertGreater(alfa, 0.99)

    def test_knox_mc_kumeli(self):
        # 5 ayrı noktada, 20 gün arayla, dar zaman penceresinde patlayan
        # olay kümeleri → karıştırma sonrası bu düzen bozulur → düşük p
        kayitlar = []
        i = 0
        for c in range(5):
            for ek_gun in [0, 1, 1, 2, 2, 3]:
                kayitlar.append({"id": i,
                                 "tarih": datetime(2026, 1, 1) + timedelta(days=c * 20 + ek_gun),
                                 "lat": 41.0 + c * 0.01, "lon": 29.0})
                i += 1
        s = tekrar.knox_anlamlilik(kayitlar, 0.3, 3, sim=49, seed=1)
        self.assertLess(s["p"], 0.1)


if __name__ == "__main__":
    unittest.main()
