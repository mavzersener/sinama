# -*- coding: utf-8 -*-
"""
test_iliski.py — iliski.py golden testleri (v6.8 kapsam borcu turu).
Hedef: lambda_, gamma_, capraz_ki_kare, suc_orani.
(oran_guven_araligi / iki_poisson_orani test_faz_e'de kapsanmıştı.)
"""

import unittest

from sinama.cekirdek import iliski


def _kayitlar():
    # A mahallesinde hırsızlık ağırlıklı, B'de dolandırıcılık ağırlıklı
    return ([{"mah": "A", "tur": "hirsizlik"}] * 8
            + [{"mah": "A", "tur": "dolandiricilik"}] * 2
            + [{"mah": "B", "tur": "dolandiricilik"}] * 8
            + [{"mah": "B", "tur": "hirsizlik"}] * 2)


class TestLambda(unittest.TestCase):
    def test_golden(self):
        # PRE: mod_genel=hirsizlik(10) -> hata1=10; grup içi hatalar 2+2=4
        # lambda = (10-4)/10 = 0.6
        self.assertEqual(iliski.lambda_(_kayitlar(), "mah", "tur"), 0.6)

    def test_bos_none(self):
        self.assertIsNone(iliski.lambda_([], "mah", "tur"))

    def test_tek_degisken_sifir(self):
        # bagimli tek değerliyse hata1=0 -> 0.0 (bölme hatası yok)
        self.assertEqual(iliski.lambda_([{"a": "X", "b": "Y"}] * 5, "a", "b"),
                         0.0)

    def test_iliski_yoksa_sifir(self):
        # bagimsiz bilgisi tahmini iyileştirmiyor
        k = [{"a": "X", "b": "p"}, {"a": "X", "b": "q"},
             {"a": "Y", "b": "p"}, {"a": "Y", "b": "q"}]
        self.assertEqual(iliski.lambda_(k, "a", "b"), 0.0)


class TestGamma(unittest.TestCase):
    def test_tam_uyumlu(self):
        self.assertEqual(iliski.gamma_([(1, 1), (2, 2), (3, 3), (4, 4)]), 1.0)

    def test_tam_uyumsuz(self):
        self.assertEqual(iliski.gamma_([(1, 4), (2, 3), (3, 2), (4, 1)]), -1.0)

    def test_esitlikler_yok_sayilir(self):
        # tüm çiftler x'te bağlı (tied): nc+nd=0 -> None
        self.assertIsNone(iliski.gamma_([(1, 1), (1, 2)]))


class TestCaprazKiKare(unittest.TestCase):
    def test_golden(self):
        sonuc = iliski.capraz_ki_kare(_kayitlar(), "mah", "tur")
        self.assertEqual(sonuc["ki_kare"], 7.2)
        self.assertEqual(sonuc["df"], 1)
        self.assertEqual(sonuc["p_degeri"], 0.00729)
        self.assertEqual(sonuc["cramer_v"], 0.6)
        self.assertEqual(sonuc["satirlar"], ["A", "B"])
        self.assertEqual(sonuc["sutunlar"], ["dolandiricilik", "hirsizlik"])
        self.assertEqual(sonuc["beklenen"], [[5.0, 5.0], [5.0, 5.0]])
        self.assertEqual(sonuc["uyarilar"], [])

    def test_cochran_uyarisi(self):
        # beklenen <5 hücreleri baskın: Cochran uyarısı çıkmalı
        k = [{"a": "X", "b": "p"}] * 5 + [{"a": "X", "b": "q"}] * 1 \
            + [{"a": "Y", "b": "p"}] * 1 + [{"a": "Y", "b": "q"}] * 1
        sonuc = iliski.capraz_ki_kare(k, "a", "b")
        self.assertTrue(any("Cochran" in u for u in sonuc["uyarilar"]))


class TestSucOrani(unittest.TestCase):
    def test_golden(self):
        self.assertEqual(iliski.suc_orani(250, 50000), 500.0)

    def test_sifir_nufus_none(self):
        self.assertIsNone(iliski.suc_orani(10, 0))


if __name__ == "__main__":
    unittest.main()
