# -*- coding: utf-8 -*-
"""bolge_oran / ham_oran_karsilastir — nüfusa oranlı bölge analizi (R12)."""
import unittest

from suc_analizi.cekirdek import iliski


class TestHamOranKarsilastir(unittest.TestCase):
    VERI = [{"bolge": "A_kalabalik", "olay": 100, "nufus": 100000},
            {"bolge": "B_orta", "olay": 40, "nufus": 20000},
            {"bolge": "C_kucuk", "olay": 15, "nufus": 2000}]

    def test_kalabalik_bolge_negatif_sapma(self):
        r = iliski.ham_oran_karsilastir(self.VERI)
        d = {b["bolge"]: b for b in r["bolgeler"]}
        # yüksek sayı, düşük oran → nüfus şişmesi → sapma<0
        self.assertLess(d["A_kalabalik"]["sapma"], 0)

    def test_kucuk_bolge_pozitif_sapma_gercekten_riskli(self):
        r = iliski.ham_oran_karsilastir(self.VERI)
        d = {b["bolge"]: b for b in r["bolgeler"]}
        # düşük sayı, yüksek oran → gerçekten riskli → sapma>0
        self.assertGreater(d["C_kucuk"]["sapma"], 0)

    def test_oran_hesabi(self):
        r = iliski.ham_oran_karsilastir(self.VERI)
        d = {b["bolge"]: b for b in r["bolgeler"]}
        self.assertAlmostEqual(d["C_kucuk"]["oran_100binde"], 750.0, places=1)

    def test_nufussuz_reddi(self):
        r = iliski.ham_oran_karsilastir([{"bolge": "A", "olay": 5, "nufus": 0}])
        self.assertIn("hata", r)


class TestBolgeOranArac(unittest.TestCase):
    def test_nufussuz_ham_sayi_uyarisi(self):
        from suc_analizi.arayuz import araclar  # noqa: F401
        from suc_analizi.arayuz.ortak import ARACLAR
        rows = [{"grid_id": "G1"}] * 50 + [{"grid_id": "G2"}] * 10
        r = ARACLAR["bolge_oran"]["fn"]({"satirlar": rows, "bolge_alan": "grid_id"})
        self.assertIn("sayimlar", r)
        self.assertIn("R12", r["not"])

    def test_nufuslu_oran_karsilastirma(self):
        from suc_analizi.arayuz import araclar  # noqa: F401
        from suc_analizi.arayuz.ortak import ARACLAR
        rows = ([{"grid_id": "A", "nufus": 100000}] * 100 +
                [{"grid_id": "C", "nufus": 2000}] * 15)
        r = ARACLAR["bolge_oran"]["fn"]({"satirlar": rows, "bolge_alan": "grid_id",
                                         "nufus_alan": "nufus"})
        self.assertIn("bolgeler", r)
        d = {b["bolge"]: b for b in r["bolgeler"]}
        self.assertGreater(d["C"]["sapma"], 0)  # küçük ama yüksek oranlı


if __name__ == "__main__":
    unittest.main()
