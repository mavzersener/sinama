# -*- coding: utf-8 -*-
"""
test_ileri.py — ileri.py golden testleri (v6.8 kapsam borcu turu).
Hedef: cografi_profil, risk_arazi, k_means, donemsel_hotspot_karsilastirma,
olaylar_arasi_sure, benford_testi kenarları, poisson_ust_kuyruk kenarları.
Tüm golden değerler yorumlayıcıyla doğrulanıp sabitlendi.
"""

import random
import unittest
from datetime import datetime

from sinama.cekirdek import ileri


class TestDonemselHotspot(unittest.TestCase):
    """İki dönem grid karşılaştırması: 5 sınıfın tamamı tek senaryoda."""

    ONCE = [{"lat": 41.0, "lon": 29.0, "adet": 10},
            {"lat": 41.1, "lon": 29.1, "adet": 8},
            {"lat": 41.2, "lon": 29.2, "adet": 5},
            {"lat": 41.3, "lon": 29.3, "adet": 4}]
    SONRA = [{"lat": 41.001, "lon": 29.001, "adet": 15},
             {"lat": 41.101, "lon": 29.101, "adet": 3},
             {"lat": 41.201, "lon": 29.201, "adet": 5},
             {"lat": 41.5, "lon": 29.5, "adet": 7}]

    def test_bes_sinif_golden(self):
        sonuc = ileri.donemsel_hotspot_karsilastirma(self.ONCE, self.SONRA)
        siniflar = {s["sinif"] for s in sonuc}
        self.assertEqual(siniflar,
                         {"yükselen", "zayıflayan", "kalıcı", "sönen", "yeni"})
        self.assertEqual(len(sonuc), 5)
        yukselen = next(s for s in sonuc if s["sinif"] == "yükselen")
        self.assertEqual((yukselen["once"], yukselen["sonra"]), (10, 15))
        sonen = next(s for s in sonuc if s["sinif"] == "sönen")
        self.assertEqual((sonen["once"], sonen["sonra"]), (4, 0))
        yeni = next(s for s in sonuc if s["sinif"] == "yeni")
        self.assertEqual((yeni["once"], yeni["sonra"]), (0, 7))

    def test_tolerans_disi_eslesmez(self):
        # 0.3 km'den uzak nokta eşleşmemeli: iki ayrı sınıf çıkar
        once = [{"lat": 41.0, "lon": 29.0, "adet": 5}]
        sonra = [{"lat": 41.05, "lon": 29.0, "adet": 5}]  # ~5.5 km
        sonuc = ileri.donemsel_hotspot_karsilastirma(once, sonra)
        siniflar = sorted(s["sinif"] for s in sonuc)
        self.assertEqual(siniflar, ["sönen", "yeni"])


class TestOlaylarArasiSure(unittest.TestCase):
    def test_golden(self):
        t = [datetime(2025, 1, 12), datetime(2025, 1, 1),
             datetime(2025, 1, 5, 12), datetime(2025, 1, 4)]  # sırasız verilir
        self.assertEqual(ileri.olaylar_arasi_sure(t),
                         {"n_aralik": 3, "ortalama_gun": 3.67,
                          "medyan_gun": 3.0, "min_gun": 1.5, "maks_gun": 6.5})

    def test_tek_olay_none(self):
        self.assertIsNone(ileri.olaylar_arasi_sure([datetime(2025, 1, 1)]))
        self.assertIsNone(ileri.olaylar_arasi_sure([]))


class TestCografiProfil(unittest.TestCase):
    """Rossmo CGT: grid yapısı ve sıralama sözleşmesi + golden hücre."""

    PTS = [(41.0, 29.0), (41.002, 29.001), (40.998, 29.001)]

    def test_uc_noktadan_az_bos(self):
        self.assertEqual(ileri.cografi_profil(self.PTS[:2]), [])

    def test_golden_ve_siralama(self):
        prof = ileri.cografi_profil(self.PTS, tampon_km=0.5, hucre_km=0.5)
        self.assertEqual(len(prof), 6)
        # azalan olasılık sıralı
        p = [h["olasilik"] for h in prof]
        self.assertEqual(p, sorted(p, reverse=True))
        # en yüksek hücre golden (yorumlayıcıdan sabitlendi)
        self.assertEqual(prof[0], {"lat": 40.995739, "lon": 28.998454,
                                   "olasilik": 4.8264})
        self.assertEqual(prof[-1]["olasilik"], 4.0477)


class TestRiskArazi(unittest.TestCase):
    def test_bos_katman_bos(self):
        self.assertEqual(ileri.risk_arazi({}), [])

    def test_agirlikli_golden(self):
        kat = {"bar": [(41.0, 29.0), (41.001, 29.0)],
               "park": [(41.0005, 29.0003)]}
        rt = ileri.risk_arazi(kat, hucre_km=0.2, etki_km=0.3,
                              agirliklar={"bar": 2.0})
        self.assertEqual(len(rt), 1)
        # 2 bar x 2.0 + 1 park x 1.0 = 5.0
        self.assertEqual(rt[0], {"lat": 41.000904, "lon": 29.00119,
                                 "risk_skoru": 5.0})

    def test_agirliksiz_varsayilan_bir(self):
        kat = {"bar": [(41.0, 29.0)]}
        rt = ileri.risk_arazi(kat, hucre_km=0.2, etki_km=0.3)
        self.assertTrue(all(h["risk_skoru"] >= 1.0 for h in rt))


class TestKMeans(unittest.TestCase):
    NOKTALAR = [(0.0, 0.0), (0.1, 0.0), (0.0, 0.1),
                (10.0, 10.0), (10.1, 10.0), (10.0, 10.1)]

    def test_seeded_golden(self):
        km = ileri.k_means(self.NOKTALAR, k=2, seed=42)
        self.assertEqual(km["merkezler"], [[10.03333, 10.03333],
                                           [0.03333, 0.03333]])
        self.assertEqual(km["etiketler"], [1, 1, 1, 0, 0, 0])
        self.assertEqual(km["kume_buyuklukleri"], {0: 3, 1: 3})

    def test_tekrarlanabilirlik(self):
        a = ileri.k_means(self.NOKTALAR, k=2, seed=7)
        b = ileri.k_means(self.NOKTALAR, k=2, seed=7)
        self.assertEqual(a, b)


class TestBenfordKenarlari(unittest.TestCase):
    def test_az_veri_none(self):
        # n < 10: test anlamsız, None (sessiz yanlış üretme)
        self.assertIsNone(ileri.benford_testi([10, 15, 20, -30, 0, 5]))
        self.assertIsNone(ileri.benford_testi([]))

    def test_supheli_golden(self):
        random.seed(1)
        vals = [random.choice([120, 150, 180, 200, 220, 350, 900, 1100])
                for _ in range(30)]
        sonuc = ileri.benford_testi(vals)
        self.assertEqual(sonuc["n"], 30)
        self.assertEqual(sonuc["ki_kare"], 31.17)
        self.assertEqual(sonuc["uyum"], "şüpheli (Benford'dan sapma)")
        self.assertEqual(sonuc["gozlenen"][1], 18)

    def test_dogal_veri_uyumlu(self):
        random.seed(1)
        dogal = [10 ** random.uniform(1, 3) for _ in range(200)]
        sonuc = ileri.benford_testi(dogal)
        self.assertEqual(sonuc["uyum"], "uyumlu")
        self.assertEqual(sonuc["n"], 200)


class TestPoissonKuyrukKenarlari(unittest.TestCase):
    def test_sifir_gozlenen_bir(self):
        # beklenen 5 iken 0 olay: P(X>=0) = 1
        self.assertEqual(ileri.poisson_ust_kuyruk(0, 5), 1.0)

    def test_beklenen_kadar_gozlenen(self):
        self.assertEqual(ileri.poisson_ust_kuyruk(5, 5), 0.55951)


if __name__ == "__main__":
    unittest.main()
