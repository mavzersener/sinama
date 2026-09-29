# -*- coding: utf-8 -*-
"""
test_orneklem.py — orneklem.py golden testleri (v6.6, H3.2).
Maxfield & Babbie Bölüm 8 formülleri elle hesaplanmış değerlerle;
tabaka oranları ve tekrar üretilebilirlik sabitlenir.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi.cekirdek import orneklem


class TestCekimYontemleri(unittest.TestCase):
    def test_basit_tesadufi_tekrar_uretilebilir(self):
        k = list(range(100))
        self.assertEqual(orneklem.basit_tesadufi(k, 10, seed=7),
                         orneklem.basit_tesadufi(k, 10, seed=7))
        self.assertEqual(len(orneklem.basit_tesadufi(k, 10, seed=7)), 10)

    def test_basit_tesadufi_n_tavani(self):
        self.assertEqual(len(orneklem.basit_tesadufi([1, 2, 3], 99)), 3)

    def test_sistematik_golden(self):
        # N=10, n=5 → k=2; seed=7 ile başlangıç=1 → [1,3,5,7,9]
        k = list(range(10))
        self.assertEqual(orneklem.sistematik(k, 5, seed=7), [1, 3, 5, 7, 9])

    def test_sistematik_bos(self):
        self.assertEqual(orneklem.sistematik([], 5), [])

    def test_tabakali_orantili_golden(self):
        # 60 A + 40 B, n=10 → A'dan 6, B'den 4 (tabaka büyüklüğü oranında)
        k = [{"mahalle": "A"}] * 60 + [{"mahalle": "B"}] * 40
        secim = orneklem.tabakali(k, "mahalle", 10, seed=42)
        a = sum(1 for x in secim if x["mahalle"] == "A")
        b = sum(1 for x in secim if x["mahalle"] == "B")
        self.assertEqual((a, b), (6, 4))

    def test_tabakali_kucuk_tabaka_en_az_bir(self):
        # 1 C / 99 A, n=10 → C: round(0.1)=0 ama max(1,·) ile 1
        k = [{"t": "A"}] * 99 + [{"t": "C"}]
        secim = orneklem.tabakali(k, "t", 10, seed=1)
        self.assertEqual(sum(1 for x in secim if x["t"] == "C"), 1)

    def test_tabakali_orantisiz_esit_pay(self):
        # 3 tabaka, n=9 → her tabakadan max(1, 9//3)=3
        k = ([{"t": "A"}] * 20 + [{"t": "B"}] * 20 + [{"t": "C"}] * 20)
        secim = orneklem.tabakali(k, "t", 9, orantili=False, seed=2)
        from collections import Counter
        self.assertEqual(Counter(x["t"] for x in secim),
                         Counter({"A": 3, "B": 3, "C": 3}))


class TestGuvenAraliklari(unittest.TestCase):
    def test_ornekleme_hatasi_golden(self):
        # sqrt(0.5*0.5/100) = 0.05
        self.assertEqual(orneklem.ornekleme_hatasi(0.5, 100), 0.05)

    def test_ornekleme_hatasi_sifir_n(self):
        self.assertIsNone(orneklem.ornekleme_hatasi(0.5, 0))

    def test_ga_oran_golden(self):
        # 0.5 ± 1.96*0.05 = [0.402, 0.598]
        self.assertEqual(orneklem.guven_araligi_oran(0.5, 100),
                         {"oran": 0.5, "se": 0.05, "alt": 0.402,
                          "ust": 0.598, "guven": 0.95})

    def test_ga_ortalama_golden(self):
        # se = 5/sqrt(25) = 1.0; 10 ± 1.96 = [8.04, 11.96]
        self.assertEqual(orneklem.guven_araligi_ortalama(10, 5, 25),
                         {"ortalama": 10, "se": 1.0, "alt": 8.04,
                          "ust": 11.96, "guven": 0.95})

    def test_orneklem_buyuklugu_golden(self):
        # ceil(1.96² * 0.25 / 0.05²) = ceil(384.16) = 385 (Ch 8, %95, ±%5)
        self.assertEqual(orneklem.orneklem_buyuklugu(0.05), 385)


if __name__ == "__main__":
    unittest.main()
