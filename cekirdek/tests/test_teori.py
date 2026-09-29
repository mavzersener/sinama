# -*- coding: utf-8 -*-
"""teori.py — kriminolojik teori yorum katmanı testleri."""
import unittest

from suc_analizi.cekirdek import teori


class TestTeori(unittest.TestCase):
    def test_kalici_sicak_nokta_teorileri(self):
        r = teori.yorumla("kalici_sicak_nokta")
        self.assertIn("rutin faaliyet", r["teoriler"])
        self.assertIn("yorum", r)
        self.assertIn("oneri", r)
        self.assertIn("uyari", r)

    def test_tum_bulgular_tam_yapida(self):
        for b in teori.BULGU_TURLERI:
            r = teori.yorumla(b)
            self.assertEqual(r["bulgu"], b)
            for alan in ("teoriler", "yorum", "oneri", "uyari"):
                self.assertIn(alan, r)
            self.assertTrue(len(r["teoriler"]) > 0)

    def test_bilinmeyen_bulgu(self):
        r = teori.yorumla("boyle_bir_sey_yok")
        self.assertIn("hata", r)
        self.assertIn("gecerli_bulgular", r)

    def test_mukerrer_magduriyet_rasyonel_tercih(self):
        r = teori.yorumla("mukerrer_magduriyet")
        self.assertIn("rasyonel tercih", r["teoriler"])

    def test_rtm_colocation(self):
        r = teori.yorumla("risk_faktoru_colocation")
        self.assertIn("suç deseni teorisi", r["teoriler"])


if __name__ == "__main__":
    unittest.main()
