# -*- coding: utf-8 -*-
"""
test_kume_olcek_veri.py — kume/olcek/veri golden + kenar testleri
(v6.8 kapsam borcu turu). Tüm golden değerler yorumlayıcıdan sabitlendi.
"""

import os
import tempfile
import unittest
from datetime import datetime

from sinama.cekirdek import kume, olcek, veri


class TestCarpisma(unittest.TestCase):
    def test_uc_liste_ortak(self):
        a = [{"k": "Ahmet"}, {"k": "Mehmet"}]
        b = [{"k": "AHMET "}, {"k": "Ayşe"}]
        c = [{"k": " ahmet"}, {"k": "Zeynep"}]
        # normalize_metin sayesinde yazım/boşluk farkları eşleşir
        self.assertEqual(kume.carpisma([a, b, c], "k"), {"ahmet"})

    def test_bos_liste_bos_kume(self):
        self.assertEqual(kume.carpisma([], "k"), set())

    def test_none_degerler_dislanir(self):
        a = [{"k": None}, {"k": "x"}]
        b = [{"k": "x"}]
        self.assertEqual(kume.carpisma([a, b], "k"), {"x"})


class TestLevenshtein(unittest.TestCase):
    def test_klasik_golden(self):
        self.assertEqual(kume.levenshtein("kitten", "sitting"), 3)

    def test_bos_metinler(self):
        self.assertEqual(kume.levenshtein("", "abc"), 3)
        self.assertEqual(kume.levenshtein("abc", ""), 3)
        self.assertEqual(kume.levenshtein("", ""), 0)

    def test_normalizasyon_once(self):
        # büyük/küçük harf ve boşluk farkı mesafe ÜRETMEZ
        self.assertEqual(kume.levenshtein("A B ", "a  b"), 0)

    def test_benzerlik_orani(self):
        self.assertEqual(kume.benzerlik_orani("ahmet", "ahmed"), 0.8)
        self.assertEqual(kume.benzerlik_orani("", ""), 1.0)


class TestOlcumDuzeyi(unittest.TestCase):
    def test_sayisal(self):
        self.assertEqual(olcek.olcum_duzeyi_belirle([1, 2.5, "3"]),
                         "aralik/oran (ortalama, std, Pearson uygulanabilir)")

    def test_nominal_ikili(self):
        self.assertEqual(olcek.olcum_duzeyi_belirle(["a", "b", "a"]),
                         "nominal-ikili (mod, lambda, ki-kare uygulanabilir)")

    def test_nominal_ordinal(self):
        self.assertEqual(
            olcek.olcum_duzeyi_belirle(["x", "y", "z", "w"]),
            "nominal/ordinal (mod, frekans, ki-kare, gamma uygulanabilir; "
            "ortalama UYGUN DEĞİL)")


class TestCronbachAlfa(unittest.TestCase):
    MADDE = [[5, 4, 4], [4, 5, 5], [1, 2, 1], [2, 1, 2], [5, 5, 4]]

    def test_golden(self):
        self.assertEqual(olcek.cronbach_alfa(self.MADDE), 0.9529)

    def test_sifir_toplam_varyans_none(self):
        # herkes aynı toplamı alıyorsa alfa tanımsız
        self.assertIsNone(olcek.cronbach_alfa([[1, 2], [1, 2]]))

    def test_tek_madde_none(self):
        self.assertIsNone(olcek.cronbach_alfa([[1], [2], [3]]))


class TestNormalizeVeEndeks(unittest.TestCase):
    def test_min_max_golden(self):
        self.assertEqual(olcek.min_max_normalize([10, 20, 30]),
                         [0.0, 0.5, 1.0])
        self.assertEqual(olcek.min_max_normalize([10, 20, 30], ters=True),
                         [1.0, 0.5, 0.0])

    def test_min_max_sabit_seri(self):
        # hi == lo: bölme hatası yerine nötr 0.5
        self.assertEqual(olcek.min_max_normalize([7, 7]), [0.5, 0.5])

    def test_endeks_golden(self):
        kay = [{"suc": 10, "is": 5}, {"suc": 20, "is": 10},
               {"suc": 30, "is": 0}]
        sonuc = olcek.endeks_kur(kay, ["suc", "is"],
                                 agirliklar={"suc": 2.0}, tersler=["is"])
        self.assertEqual([k["endeks"] for k in sonuc],
                         [16.67, 33.33, 100.0])
        # tahribatsızlık: özgün alanlar korunur
        self.assertEqual(sonuc[0]["suc"], 10)

    def test_endeks_sayisal_olmayan_sifir(self):
        # float'a çevrilemeyen gösterge değeri 0.0 sayılır (çökme yok)
        kay = [{"suc": "?"}, {"suc": 10}]
        sonuc = olcek.endeks_kur(kay, ["suc"])
        self.assertEqual(len(sonuc), 2)


class TestCsvYukle(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp()
        with open(os.path.join(self.dizin, "t1.csv"), "w",
                  encoding="utf-8") as f:
            f.write("tur;adet\nhirsizlik;3\ndolandiricilik;5\n")
        with open(os.path.join(self.dizin, "t2.csv"), "w",
                  encoding="utf-8") as f:
            f.write("a,b\n1,2\n3,4\n5,6\n")

    def test_sniffer_noktali_virgul(self):
        kay = veri.csv_yukle("t1.csv", kok=self.dizin)
        self.assertEqual(kay, [{"tur": "hirsizlik", "adet": "3"},
                               {"tur": "dolandiricilik", "adet": "5"}])
        self.assertEqual(veri.son_okuma["kesildi"], False)
        self.assertEqual(veri.son_okuma["satir"], 2)

    def test_maks_satir_kesme(self):
        kay = veri.csv_yukle("t2.csv", kok=self.dizin, maks_satir=2)
        self.assertEqual(len(kay), 2)
        self.assertEqual(veri.son_okuma["kesildi"], True)
        self.assertEqual(veri.son_okuma["satir"], 2)

    def test_kesme_yoksa_false(self):
        veri.csv_yukle("t2.csv", kok=self.dizin)
        self.assertEqual(veri.son_okuma["kesildi"], False)
        self.assertEqual(veri.son_okuma["satir"], 3)


class TestSayiVeTipCoz(unittest.TestCase):
    def test_sayi_coz_golden(self):
        self.assertEqual(veri._sayi_coz("12,5"), 12.5)     # Türkçe ondalık
        self.assertEqual(veri._sayi_coz("-7"), -7)
        self.assertEqual(veri._sayi_coz("3.14"), 3.14)

    def test_binlik_virgul_sayi_degil(self):
        # '1,234' İng. binlik biçimidir; sayı SAYILMAZ (sessiz bozulma yok)
        self.assertIsNone(veri._sayi_coz("1,234"))
        self.assertIsNone(veri._sayi_coz("1,2345"))
        self.assertIsNone(veri._sayi_coz("abc"))

    def test_tip_tahmin(self):
        self.assertEqual(veri.tip_tahmin("2025-03-04"),
                         datetime(2025, 3, 4))
        self.assertEqual(veri.tip_tahmin("12,5"), 12.5)
        self.assertEqual(veri.tip_tahmin("abc"), "abc")
        self.assertIsNone(veri.tip_tahmin("  "))
        self.assertIsNone(veri.tip_tahmin(None))

    def test_tarih_coz_turkce_format(self):
        self.assertEqual(veri.tarih_coz("04.03.2025"),
                         datetime(2025, 3, 4))
        self.assertIsNone(veri.tarih_coz("tarih değil"))

    def test_eksik_raporu_golden(self):
        self.assertEqual(veri.eksik_raporu([{"a": 1, "b": ""},
                                            {"a": None, "b": "x"}]),
                         {"a": 1, "b": 1})

    def test_normalize_metin(self):
        self.assertEqual(veri.normalize_metin("  AHMET  Yılmaz "),
                         "ahmet yılmaz")
        self.assertEqual(veri.normalize_metin(None), "")


if __name__ == "__main__":
    unittest.main()
