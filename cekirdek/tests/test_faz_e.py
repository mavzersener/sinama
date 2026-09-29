# -*- coding: utf-8 -*-
"""
test_faz_e.py — Faz E (v6.3) metodolojik derinlik testleri.
  E1  aşırı yayılım: negatif binom üst kuyruk (EL HESABI golden),
      bolge_anomali otomatik model seçimi, naif-Poisson şişkinliği
  E2  iki Poisson oranı: koşullu exact p tutarlılığı, RR golden,
      Clopper-Pearson GA özellikleri
  E3  NNI Donnelly kenar düzeltmesi: yön + beklenen alanı + geriye
      uyumluluk (varsayılan kapalı)
  E4  Knox analitik beklenti: MC ortalamasına yakınsama, alan varlığı
"""
import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama.cekirdek import ileri, iliski, mekan, tekrar, hipotez


class TestE1_NegatifBinom(unittest.TestCase):
    def test_golden_el_hesabi(self):
        # NB(r=2, p=0.5): mu=2, var=4.
        # P(X=0)=0.25, P(X=1)=0.25 → P(X>=2)=0.5 (el hesabı)
        self.assertAlmostEqual(
            ileri.neg_binom_ust_kuyruk(2, 2.0, 4.0), 0.5, places=6)

    def test_yayilim_yoksa_poisson_duser(self):
        # varyans <= beklenen → Poisson ile birebir
        nb = ileri.neg_binom_ust_kuyruk(10, 5.0, 4.0)
        po = ileri.poisson_ust_kuyruk(10, 5.0)
        self.assertAlmostEqual(nb, po, places=9)

    def test_model_secimi(self):
        import random
        rng = random.Random(42)
        asiri = {f"b{i}": max(0, int(rng.gauss(10, 12))) for i in range(12)}
        self.assertEqual(ileri.bolge_anomali(asiri)["model"], "neg-binom")
        homojen = {f"b{i}": 9 + (i % 3) for i in range(12)}
        self.assertEqual(ileri.bolge_anomali(homojen)["model"], "poisson")

    def test_nb_daha_muhafazakar(self):
        # aşırı yayılımda, UZAK KUYRUKTAKİ anomali adaylarında NB üst-kuyruk
        # p'si Poisson'dan büyük olmalı (naif Poisson'un yanlış-pozitifleri
        # elenir). Not: ortalama civarında NB p'si küçülebilir — bu doğru
        # davranıştır (ağır kuyruklu null); muhafazakârlık özelliği
        # yalnız belirgin sapmalarda geçerlidir.
        sayim = {f"b{i}": v for i, v in
                 enumerate([2, 3, 3, 4, 4, 5, 5, 6, 7, 9, 12, 40])}
        s = ileri.bolge_anomali(sayim)
        self.assertEqual(s["model"], "neg-binom")
        uzak = [t for t in s["tum_sonuclar"]
                if t["gozlenen"] >= 2 * t["beklenen"]]
        self.assertTrue(uzak)
        for t in uzak:
            self.assertGreaterEqual(t["p"], t["p_poisson"])
        # gerçek anomali (40) NB altında da yakalanır (maskeleme yok)
        b11 = next(t for t in s["tum_sonuclar"] if t["gozlenen"] == 40)
        self.assertLess(b11["p"], 0.05)
        # marjinal sapmada NB muhafazakâr: b10 (12) p şişkinliği giderilmiş
        b10 = next(t for t in s["tum_sonuclar"] if t["gozlenen"] == 12)
        self.assertGreater(b10["p"], b10["p_poisson"])

    def test_maskeleme_onlemi(self):
        # tek uç bölge varyansı şişirip kendini NB null'a boğduramaz
        sayim = {f"m{i}": 5 for i in range(11)}
        sayim["m11"] = 100
        s = ileri.bolge_anomali(sayim)
        self.assertIn("m11", [b["bolge"] for b in s["anlamli"]])

    def test_fisher_alani_raporlanir(self):
        sayim = {f"m{i}": 5 for i in range(11)}
        sayim["m11"] = 100
        s = ileri.bolge_anomali(sayim)
        self.assertIn("fisher_dispersiyon_p", s)
        self.assertEqual(s["model"], "neg-binom")


class TestE2_IkiPoissonOrani(unittest.TestCase):
    def test_kosullu_p_tutarliligi(self):
        s = iliski.iki_poisson_orani(30, 100, 20, 200)
        beklenen = hipotez.binomial_test(30, 50, 100 / 300)["p"]
        self.assertAlmostEqual(s["p"], beklenen, places=6)

    def test_rr_golden(self):
        # oran1 = 30/100 = 0.3, oran2 = 20/200 = 0.1 → RR = 3.0
        s = iliski.iki_poisson_orani(30, 100, 20, 200)
        self.assertEqual(s["oran_orani"], 3.0)
        # R poisson.test mid-P GA ≈ (1.69, 5.41); exact CP biraz geniştir
        self.assertLess(s["ga_alt"], 1.0 * 3)   # alt < nokta tahmin
        self.assertGreater(s["ga_ust"], 3.0)    # üst > nokta tahmin
        self.assertGreater(s["ga_alt"], 1.0)    # anlamlı

    def test_esit_oran_ga_bir_icerir(self):
        s = iliski.iki_poisson_orani(10, 100, 20, 200)
        self.assertEqual(s["oran_orani"], 1.0)
        self.assertLess(s["ga_alt"], 1.0)
        self.assertGreater(s["ga_ust"], 1.0)
        self.assertIn("anlamlı değil", s["yorum"])

    def test_sifir_olay(self):
        s = iliski.iki_poisson_orani(0, 100, 10, 100)
        self.assertEqual(s["ga_alt"], 0.0)
        s2 = iliski.iki_poisson_orani(0, 0, 5, 100)
        self.assertIsNone(s2)


class TestE3_Donnelly(unittest.TestCase):
    def setUp(self):
        self.pts = [(41.0 + (i % 10) * 0.002, 29.0 + (i // 10) * 0.002)
                    for i in range(100)]

    def test_beklenen_artar(self):
        duz = mekan.nni_test(self.pts)
        don = mekan.nni_test(self.pts, kenar_duzeltme=True)
        self.assertGreater(don["beklenen"], duz["beklenen"])
        self.assertTrue(don["kenar_duzeltme"])
        self.assertFalse(duz["kenar_duzeltme"])

    def test_z_yonu_kumeleye_karsi_muhafazakar(self):
        # düzgün ızgarada Donnelly z'yi küçültmeli (kenar önyargısı giderilir)
        duz = mekan.nni_test(self.pts)
        don = mekan.nni_test(self.pts, kenar_duzeltme=True)
        self.assertLess(abs(don["z"]), abs(duz["z"]) + 1e-9)

    def test_geriye_uyumluluk(self):
        # eski tek-argüman çağrı aynen çalışır, alanlar eklenir
        s = mekan.nni_test(self.pts)
        self.assertIn("nni", s)
        self.assertIn("beklenen", s)


class TestE4_KnoxAnalitik(unittest.TestCase):
    def test_analitik_mc_yakin(self):
        base = datetime(2026, 1, 1)
        kay = []
        for c in range(5):
            for j in range(6):
                kay.append({"lat": 41.0 + c * 0.05 + (j % 2) * 0.001,
                            "lon": 29.0 + c * 0.05 + (j // 2) * 0.001,
                            "tarih": base + timedelta(days=c * 20 + j)})
        s = tekrar.knox_anlamlilik(kay, mesafe_km=0.4, gun=7,
                                   sim=199, seed=1)
        self.assertIn("beklenen_analitik", s)
        # analitik beklenti ile MC ortalaması birbirine yakınsamalı
        self.assertAlmostEqual(s["beklenen_analitik"],
                               s["beklenen_ortalama"], delta=3.0)
        # kümeli veri: gözlenen her iki beklentinin de üstünde
        self.assertGreater(s["gozlenen"], s["beklenen_analitik"])


if __name__ == "__main__":
    unittest.main()
