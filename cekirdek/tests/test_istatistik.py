# -*- coding: utf-8 -*-
"""
test_istatistik.py — istatistik.py golden testleri (v6.7, kapsam taban
yükseltmesi). Değerler elle hesaplanmıştır.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi.cekirdek import istatistik


class TestFrekansCapraz(unittest.TestCase):
    def test_frekans_golden(self):
        k = [{"t": "a"}, {"t": "a"}, {"t": "b"}]
        self.assertEqual(dict(istatistik.frekans(k, "t")), {"a": 2, "b": 1})

    def test_capraz_tablo_golden(self):
        k = [{"a": "x", "b": "p"}, {"a": "x", "b": "q"},
             {"a": "y", "b": "p"}]
        self.assertEqual(istatistik.capraz_tablo(k, "a", "b"),
                         {"x": {"p": 1, "q": 1}, "y": {"p": 1}})


class TestOzet(unittest.TestCase):
    def test_golden(self):
        o = istatistik.ozet([1, 2, 3, 4])
        self.assertEqual(o["n"], 4)
        self.assertEqual(o["ortalama"], 2.5)
        self.assertEqual(o["medyan"], 2.5)
        self.assertAlmostEqual(o["std_sapma"], 1.118033988, places=6)
        self.assertEqual((o["min"], o["maks"]), (1.0, 4.0))

    def test_none_atlanir(self):
        self.assertEqual(istatistik.ozet([1, None, 3])["n"], 2)

    def test_bos(self):
        self.assertEqual(istatistik.ozet([]), {})


class TestYuzdelikIqrMad(unittest.TestCase):
    S = list(range(1, 11))  # 1..10

    def test_yuzdelik_golden(self):
        self.assertEqual(istatistik.yuzdelik(self.S, 50), 5.5)
        self.assertEqual(istatistik.yuzdelik(self.S, 25), 3.25)
        self.assertEqual(istatistik.yuzdelik(self.S, 0), 1)
        self.assertEqual(istatistik.yuzdelik(self.S, 100), 10)

    def test_yuzdelik_bos(self):
        self.assertIsNone(istatistik.yuzdelik([], 50))

    def test_iqr_golden(self):
        self.assertEqual(istatistik.iqr([1, 2, 3, 4, 5]),
                         {"q1": 2.0, "q3": 4.0, "iqr": 2.0})

    def test_mad_golden(self):
        # medyan=3; |x-3|: 2,1,0,1,2 → medyan=1
        self.assertEqual(istatistik.mad([1, 2, 3, 4, 5]), 1.0)


class TestZSkorDegisim(unittest.TestCase):
    def test_z_skor_anomali(self):
        # 9×10 + 50: ort=14, std=12 → z(50)=3.0 (küçük örneklemde aykırı
        # değer std'yi şişirip kendini maskeleyebilir — n büyük tutulur)
        k = [{"v": 10}] * 9 + [{"v": 50}]
        a = istatistik.z_skor_anomali(k, "v", esik=2.0)
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["v"], 50)
        self.assertAlmostEqual(a[0]["z_skor"], 3.0, places=6)

    def test_degisim_orani_golden(self):
        self.assertEqual(istatistik.degisim_orani(100, 125), 25.0)
        self.assertIsNone(istatistik.degisim_orani(0, 5))


class TestKayanTrend(unittest.TestCase):
    def test_kayan_ortalama_golden(self):
        # uçlarda kısa pencere: [1], [1,2], [1,2,3], [2,3,4], [3,4,5]
        self.assertEqual(istatistik.kayan_ortalama([1, 2, 3, 4, 5], 3),
                         [1.0, 1.5, 2.0, 3.0, 4.0])

    def test_dogrusal_trend_golden(self):
        t = istatistik.dogrusal_trend([2, 4, 6, 8])
        self.assertEqual((t["egim"], t["kesim"]), (2.0, 2.0))
        self.assertEqual(t["yorum"], "artan")

    def test_dogrusal_trend_yatay(self):
        self.assertEqual(istatistik.dogrusal_trend([5, 5, 5])["yorum"],
                         "yatay")


if __name__ == "__main__":
    unittest.main()
