# -*- coding: utf-8 -*-
"""B05: araç politikası kaydının asgari sözleşmesi."""

import unittest

from suc_analizi.arayuz import araclar  # noqa: F401 - kayıt yan etkisi
from suc_analizi.arayuz import ortak
from suc_analizi.arayuz.ortak import ARACLAR
from suc_analizi.cekirdek.hatalar import KullanimHatasi


class AracPolitikasiTesti(unittest.TestCase):
    def test_kayitli_her_aracin_acik_politikasi_vardir(self):
        zorunlu = {"sinif", "insan_onayi", "iz_zorunlu", "veri_sinifi",
                   "butce_turu"}
        for ad, kayit in ARACLAR.items():
            with self.subTest(arac=ad):
                politika = kayit["politika"]
                self.assertTrue(zorunlu <= set(politika))
                self.assertNotEqual(politika["gate"] is None,
                                    politika["muafiyet_gerekcesi"] is None)
                if politika["sinif"] == "analitik":
                    self.assertTrue(politika["iz_zorunlu"])

    def test_uyumluluk_gorunumleri_politikadan_turetilir(self):
        self.assertEqual(ortak.ARAC_GATE,
                         {ad: p["politika"]["gate"] for ad, p in ARACLAR.items()
                          if p["politika"]["gate"] is not None})
        self.assertEqual(ortak.INSAN_ONAYI,
                         frozenset(ad for ad, p in ARACLAR.items()
                                   if p["politika"]["insan_onayi"]))

    def test_politikasiz_dekorator_kaydi_reddedilir(self):
        with self.assertRaises(KullanimHatasi):
            ortak.arac("sentetik_politikasiz", "test", {"type": "object"})(
                lambda _a: {})
        self.assertNotIn("sentetik_politikasiz", ARACLAR)


if __name__ == "__main__":
    unittest.main()
