# -*- coding: utf-8 -*-
"""
test_a5_paketle.py — internetsiz kurulum paketi (A5): çıktı depo dışında, kaynak yalnız
izlenen dosyalardan (git archive), özet listesi belirlenimci. Ağ kullanılmaz.
"""
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "betikler"))
import a5_paketle  # noqa: E402


class TestPaketle(unittest.TestCase):
    def test_depo_ici_cikti_reddedilir(self):
        for yol in (KOK, os.path.join(KOK, "uygulama")):
            with self.assertRaises(SystemExit):
                a5_paketle.paketle(yol, tekerlek=False)
        self.assertFalse(a5_paketle.depo_icinde_mi(tempfile.gettempdir()))

    def test_kaynak_yalniz_izlenen_dosyalar(self):
        gecici = tempfile.mkdtemp(prefix="paket_test_")
        try:
            a5_paketle.kaynak_ac(gecici)
            kok = os.path.join(gecici, "sinama")
            self.assertTrue(os.path.isfile(os.path.join(kok, "uygulama", "sunucu.py")))
            self.assertTrue(os.path.isfile(os.path.join(kok, "cekirdek", "sinama", "bilim", "hukum.py")))
            for yasak in ("oturumlar", "node_modules", "dist", ".env"):
                bulunan = [d for d, alt, dosya in os.walk(kok) if yasak in alt or yasak in dosya]
                self.assertEqual(bulunan, [], yasak)
            satirlar = a5_paketle.ozet_listesi(kok)
            self.assertEqual(satirlar, sorted(satirlar, key=lambda s: s.split("  ", 1)[1]))
            self.assertTrue(all(len(s.split("  ", 1)[0]) == 64 for s in satirlar))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
