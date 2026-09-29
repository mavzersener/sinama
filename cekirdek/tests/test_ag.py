# -*- coding: utf-8 -*-
"""
test_ag.py — ag.py golden testleri (v6.7, kapsam taban yükseltmesi).
Küçük, elle doğrulanabilen graf örnekleri: üçgen, yol, köprülü çift
üçgen, ortak olaya karışma ağı.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi.cekirdek import ag


class TestAgKur(unittest.TestCase):
    def test_cift_yon_ve_agirlik(self):
        g = ag.ag_kur([("A", "B", 2)])
        self.assertEqual(g["A"], {"B": 2})
        self.assertEqual(g["B"], {"A": 2})  # yönsüz

    def test_agirliklar_toplanir(self):
        g = ag.ag_kur([("A", "B", 2), ("A", "B", 3)])
        self.assertEqual(g["A"]["B"], 5.0)

    def test_bos(self):
        self.assertEqual(ag.ag_kur([]), {})


class TestDereceMerkeziyeti(unittest.TestCase):
    def test_golden(self):
        g = ag.ag_kur([("A", "B", 2), ("B", "C", 3)])
        d = ag.derece_merkeziyeti(g)
        self.assertEqual(d[0], {"dugum": "B", "derece": 2,
                                "agirlikli_derece": 5.0})
        self.assertEqual(d[1]["dugum"], "C")  # 3.0 > 2.0

    def test_bos(self):
        self.assertEqual(ag.derece_merkeziyeti({}), [])


class TestBagliBilesenler(unittest.TestCase):
    def test_iki_bilesen_golden(self):
        g = ag.ag_kur([("A", "B"), ("C", "D")])
        b = ag.bagli_bilesenler(g)
        self.assertEqual([sorted(x) for x in b],
                         [["A", "B"], ["C", "D"]])

    def test_tek_bilesen(self):
        g = ag.ag_kur([("A", "B"), ("B", "C")])
        self.assertEqual(len(ag.bagli_bilesenler(g)), 1)


class TestBirlikteOlayAg(unittest.TestCase):
    def test_golden(self):
        # o1: X,Y,Z; o2: X,Y → X-Y ağırlığı 2, X-Z ve Y-Z 1
        k = [{"olay": "o1", "kisi": "X"}, {"olay": "o1", "kisi": "Y"},
             {"olay": "o1", "kisi": "Z"}, {"olay": "o2", "kisi": "X"},
             {"olay": "o2", "kisi": "Y"}]
        e = sorted(ag.birlikte_olay_ag(k, "olay", "kisi"))
        self.assertEqual(e, [("X", "Y", 2.0), ("X", "Z", 1.0),
                             ("Y", "Z", 1.0)])

    def test_eksik_alan_atlanir(self):
        k = [{"olay": "o1"}, {"kisi": "X"}]
        self.assertEqual(ag.birlikte_olay_ag(k, "olay", "kisi"), [])


class TestToplulukTespiti(unittest.TestCase):
    def test_koprulu_iki_ucgen_golden(self):
        # iki üçgen + tek köprü: topluluklar üçgenler olmalı (seed sabit)
        g = ag.ag_kur([("A", "B"), ("B", "C"), ("A", "C"),
                       ("D", "E"), ("E", "F"), ("D", "F"), ("C", "D")])
        t = ag.topluluk_tespiti(g, seed=42)
        kumeler = sorted(sorted(v) for v in t.values())
        self.assertEqual(kumeler, [["A", "B", "C"], ["D", "E", "F"]])

    def test_tekrarlanabilirlik(self):
        g = ag.ag_kur([("A", "B"), ("B", "C"), ("A", "C")])
        self.assertEqual(ag.topluluk_tespiti(g, seed=1),
                         ag.topluluk_tespiti(g, seed=1))


class TestPagerank(unittest.TestCase):
    def test_ucgen_simetrik_golden(self):
        # simetrik üçgende durağan dağılım tam 1/3
        p = ag.pagerank(ag.ag_kur([("A", "B"), ("B", "C"), ("C", "A")]))
        for r in p:
            self.assertAlmostEqual(r["skor"], 1 / 3, places=4)

    def test_bos(self):
        self.assertEqual(ag.pagerank({}), [])


class TestEgoAgi(unittest.TestCase):
    def test_bir_adim_golden(self):
        g = ag.ag_kur([("A", "B"), ("B", "C"), ("A", "C"), ("C", "D")])
        self.assertEqual(sorted(ag.ego_agi(g, "A", 1)), ["A", "B", "C"])

    def test_iki_adim_golden(self):
        g = ag.ag_kur([("A", "B"), ("B", "C"), ("A", "C"), ("C", "D")])
        self.assertEqual(sorted(ag.ego_agi(g, "A", 2)), ["A", "B", "C", "D"])

    def test_olmayan_dugum(self):
        self.assertEqual(ag.ego_agi({}, "X"), {})


if __name__ == "__main__":
    unittest.main()
