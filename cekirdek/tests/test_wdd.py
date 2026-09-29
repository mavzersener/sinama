# -*- coding: utf-8 -*-
"""WDD testi (Weighted Displacement Difference) — degerlendirme.wdd_testi."""
import unittest

from suc_analizi.cekirdek import degerlendirme as d


class TestWDD(unittest.TestCase):
    def test_anlamli_azalma(self):
        r = d.wdd_testi(100, 60, 100, 98)
        self.assertEqual(r["tedavi_etkisi"], -38)
        self.assertLess(r["p"], 0.05)
        self.assertIn("azalt", r["yorum"])

    def test_anlamsiz_kucuk_degisim(self):
        r = d.wdd_testi(100, 98, 100, 99)
        self.assertGreater(r["p"], 0.05)

    def test_displacement_pozitif(self):
        r = d.wdd_testi(100, 60, 100, 98, yd_once=50, yd_sonra=55,
                        ydk_once=50, ydk_sonra=50)
        self.assertEqual(r["yer_degistirme_etkisi"], 5)
        self.assertIn("kaydı", r["yer_degistirme_yorumu"])
        self.assertEqual(r["wdd"], -33)  # -38 + 5

    def test_diffusion_negatif(self):
        r = d.wdd_testi(100, 60, 100, 98, yd_once=50, yd_sonra=40,
                        ydk_once=50, ydk_sonra=50)
        self.assertEqual(r["yer_degistirme_etkisi"], -10)
        self.assertIn("yayılım", r["yer_degistirme_yorumu"])

    def test_tamponsuz_did_ile_ayni_etki(self):
        # tampon yoksa WDD = tedavi etkisi (DiD)
        r = d.wdd_testi(20, 10, 18, 16)
        self.assertEqual(r["wdd"], r["tedavi_etkisi"])
        self.assertNotIn("yer_degistirme_etkisi", r)

    def test_anlamli_artis_istenmeyen(self):
        # tedavi bölgesinde anlamlı ARTIŞ (istenmeyen)
        r = d.wdd_testi(60, 100, 98, 100)
        self.assertEqual(r["tedavi_etkisi"], 38)
        self.assertLess(r["p"], 0.05)
        self.assertIn("istenmeyen", r["yorum"])

    def test_tampon_net_degisim_yok(self):
        r = d.wdd_testi(100, 60, 100, 98, yd_once=50, yd_sonra=50,
                        ydk_once=50, ydk_sonra=50)
        self.assertEqual(r["yer_degistirme_etkisi"], 0)
        self.assertIn("net değişim yok", r["yer_degistirme_yorumu"])

    def test_varyans_poisson_toplami(self):
        # se = sqrt(tüm sayımların toplamı)
        import math
        r = d.wdd_testi(100, 60, 100, 98)
        self.assertAlmostEqual(r["se"], math.sqrt(100 + 60 + 100 + 98), places=2)


if __name__ == "__main__":
    unittest.main()
