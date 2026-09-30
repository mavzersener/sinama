# -*- coding: utf-8 -*-
"""
P0-P2 golden-value birim testleri (Weisburd & Britt temelli).
Referanslar: standart istatistik tabloları ve textbook örnekleri.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama import hipotez as hp, regresyon as rg, istatistik, veri


class TestDagilimAltyapisi(unittest.TestCase):
    def test_t_cdf(self):
        # t=2.0, df=10 → iki yönlü p = 0.0734
        p = min(1, 2 * (1 - hp.t_cdf(2.0, 10)))
        self.assertAlmostEqual(p, 0.07339, places=4)

    def test_f_cdf(self):
        # F=3.885, df(2,12) → p ≈ 0.05 (tablo değeri)
        p = 1 - hp.f_cdf(3.885, 2, 12)
        self.assertAlmostEqual(p, 0.05, places=2)

    def test_norm_ppf(self):
        self.assertAlmostEqual(hp.norm_ppf(0.975), 1.9599, places=3)
        self.assertAlmostEqual(hp.norm_ppf(0.5), 0.0, places=6)


class TestP0(unittest.TestCase):
    def test_fisher_golden(self):
        # klasik örnek: [[1,9],[11,3]] → p = 0.002759
        self.assertAlmostEqual(hp.fisher_exact(1, 9, 11, 3)["p"],
                               0.002759, places=5)

    def test_binomial_golden(self):
        self.assertAlmostEqual(hp.binomial_test(8, 10, 0.5)["p"],
                               0.10938, places=4)

    def test_t_tek(self):
        s = hp.t_test_tek([2, 4, 6, 8, 10], 5)
        self.assertAlmostEqual(s["t"], 0.7071, places=3)
        self.assertTrue(0.5 < s["p"] < 0.53)

    def test_t_bagimsiz(self):
        s = hp.t_test_bagimsiz([4, 5, 6, 7], [1, 2, 3, 4])
        self.assertGreater(s["t"], 2)
        self.assertLess(s["p"], 0.1)

    def test_t_bagimli(self):
        once = [50, 55, 48, 60, 52]
        sonra = [45, 50, 44, 55, 49]
        s = hp.t_test_bagimli(once, sonra)
        self.assertGreater(s["t"], 2)
        self.assertLess(s["p"], 0.05)

    def test_iki_oran(self):
        s = hp.iki_oran_testi(60, 100, 40, 100)
        self.assertGreater(s["z"], 2)
        self.assertLess(s["p"], 0.01)

    def test_mann_whitney(self):
        s = hp.mann_whitney([1, 2, 3], [4, 5, 6])
        self.assertEqual(s["U"], 0.0)

    def test_spearman_mukemmel(self):
        s = hp.spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50])
        self.assertAlmostEqual(s["rho"], 1.0, places=6)

    def test_kendall(self):
        s = hp.kendall_tau([1, 2, 3, 4], [1, 2, 3, 4])
        self.assertAlmostEqual(s["tau_b"], 1.0, places=6)

    def test_phi(self):
        self.assertAlmostEqual(hp.phi_katsayisi(10, 0, 0, 10), 1.0, places=6)

    def test_dagilim_olculeri(self):
        d = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
        self.assertIsNotNone(istatistik.iqr(d))
        self.assertLess(istatistik.mad(d), 5)  # sağlam
        self.assertGreater(istatistik.varyasyon_katsayisi(d), 0.5)


class TestP1(unittest.TestCase):
    def test_anova_golden(self):
        # A=[1,2,3] B=[4,5,6] C=[7,8,9] → F=27, eta²=0.9
        s = hp.anova({"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9]})
        self.assertAlmostEqual(s["F"], 27.0, places=3)
        self.assertAlmostEqual(s["eta_kare"], 0.9, places=3)
        self.assertEqual(len(s["pairwise_bonferroni"]), 3)

    def test_kruskal_golden(self):
        # aynı veri: H=7.2, p≈0.027
        s = hp.kruskal_wallis({"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9]})
        self.assertAlmostEqual(s["H"], 7.2, places=3)
        self.assertAlmostEqual(s["p"], 0.0273, places=3)

    def test_randomizasyon(self):
        s = hp.randomizasyon_testi([1, 1, 2, 2, 1], [9, 9, 8, 9, 8],
                                   sim=199, seed=1)
        self.assertLess(s["p"], 0.05)

    def test_guc_oran(self):
        s = hp.guc_oran_orneklem(0.5, 0.6)
        self.assertEqual(s["n_grup_basi"], 388)

    def test_guc_t(self):
        s = hp.guc_t_orneklem(0.5)
        self.assertEqual(s["n_grup_basi"], 63)  # 2*((1.96+0.8416)/0.5)^2=62.79→63


class TestP2(unittest.TestCase):
    def test_ols_kesin_fit(self):
        X = [[i, i % 3] for i in range(1, 20)]
        y = [2 + 3 * row[0] - row[1] for row in X]
        s = rg.coklu_ols(X, y, ["x1", "x2"])
        self.assertAlmostEqual(s["r_kare"], 1.0, places=4)

    def test_ols_tam_uyumda_cikarim_uydurulmaz(self):
        # A4.7: se ≈ 0 iken t = beta/1e-9 uyduruluyordu (y = 2x → t = 2e9, p = 0).
        X = [[i] for i in range(1, 11)]
        s = rg.coklu_ols(X, [2 * i for i in range(1, 11)], ["x"])
        self.assertEqual([k["beta"] for k in s["katsayilar"]], [0.0, 2.0])
        self.assertTrue(all(k["t"] is None and k["p"] is None for k in s["katsayilar"]))
        self.assertIsNone(s["F"])
        self.assertTrue(any("tam uyum" in n for n in s["notlar"]))

    def test_lojistik_ayrismada_wald_p_yok(self):
        # A4.7: x > 0 ⇔ y = 1 (tam ayrışma) için Wald p = 0,94 "etki yok" diyordu.
        X = [[x] for x in range(-10, 10)]
        s = rg.lojistik(X, [1 if x > 0 else 0 for x in range(-10, 10)], ["x"])
        self.assertFalse(s["yakinsadi"])
        self.assertTrue(all(k["p"] is None and k["z"] is None for k in s["katsayilar"]))
        self.assertTrue(any("ayrışma" in n for n in s["notlar"]))

    def test_ols_sabit_bagimli_hata(self):
        # sabit y'de R² = 1,0 dönüyordu — model hiçbir şey açıklamıyor.
        s = rg.coklu_ols([[i] for i in range(1, 11)], [5] * 10, ["x"])
        self.assertIn("hata", s)

    def test_ols_tekil_matris(self):
        X = [[i, 2 * i] for i in range(1, 20)]  # x2 = 2*x1 → tekil
        y = [2 + row[0] for row in X]
        s = rg.coklu_ols(X, y, ["x1", "x2"])
        self.assertIn("hata", s)  # sessiz geçmemeli, multicollinearity bildirmeli

    def test_vif_yuksek(self):
        X = [[i, 2 * i + (0.01 if i % 2 else -0.01)] for i in range(1, 20)]
        y = [2 + row[0] for row in X]
        s = rg.coklu_ols(X, y, ["x1", "x2"])
        self.assertGreater(s["vif"]["x1"], 10)
        self.assertTrue(s["notlar"])

    def test_ols_bilinen(self):
        # basit doğrusal: y=2x → beta1=2, sabit=0
        X = [[i] for i in range(1, 11)]
        y = [2 * i for i in range(1, 11)]
        s = rg.coklu_ols(X, y, ["x"])
        self.assertAlmostEqual(s["katsayilar"][1]["beta"], 2.0, places=6)
        self.assertAlmostEqual(s["katsayilar"][0]["beta"], 0.0, places=6)

    def test_lojistik_ayrik(self):
        import random as _r
        rng = _r.Random(3)
        X, y = [], []
        for _ in range(120):
            x = rng.uniform(-4, 4)
            X.append([x])
            y.append(1 if x + rng.gauss(0, 0.5) > 0 else 0)
        s = rg.lojistik(X, y, ["x"])
        self.assertTrue(s["yakinsadi"])
        self.assertGreater(s["katsayilar"][1]["beta"], 0)
        self.assertLess(s["katsayilar"][1]["p"], 0.001)
        self.assertGreater(s["katsayilar"][1]["odds_orani"], 2)

    def test_lojistik_tek_sinif(self):
        s = rg.lojistik([[1], [2], [3]], [1, 1, 1])
        self.assertIn("hata", s)


class TestGateYeni(unittest.TestCase):
    def test_cochran_fisher_onerisi(self):
        karar = veri.analiz_uygun_mu(
            {"n": 20}, "ki_kare_testi", beklenen_hucreler=[1, 2, 1, 3, 30, 40])
        self.assertTrue(any("fisher_exact" in s for s in karar["sebepler"]))

    def test_lojistik_kucuk_n(self):
        karar = veri.analiz_uygun_mu({"n": 40}, "lojistik_regresyon")
        self.assertTrue(any("lojistik" in s for s in karar["sebepler"]))


class TestSifirVaryans(unittest.TestCase):
    """A4.9 (aynı sınıf, 0/0'dan çıkarım): varyans sıfırken t/F = fark/1e-9
    ile uyduruluyordu (sabit farkta t = 1,5·10¹⁰); Welch df 0/0 ile çöküyordu."""

    def test_tek_orneklem(self):
        from sinama.cekirdek import hipotez as h
        r = h.t_test_tek([15] * 12, 0)
        self.assertEqual((r["t"], r["p"]), (None, 0.0))
        self.assertIn("varyansı sıfır", r["not"])
        self.assertIsNone(h.t_test_tek([4] * 5, 4)["p"])      # fark da yok: tanımsız
        self.assertIsNone(h.t_test_bagimli([5, 6], [5, 6])["p"])

    def test_bagimsiz_iki_grup_sabit_welch_cokmez(self):
        from sinama.cekirdek import hipotez as h
        for welch in (True, False):
            r = h.t_test_bagimsiz([3, 3, 3], [5, 5, 5], welch=welch)
            self.assertEqual((r["t"], r["p"]), (None, 0.0))

    def test_anova_grup_ici_varyans_sifir(self):
        from sinama.cekirdek import hipotez as h
        r = h.anova({"a": [1, 1, 1], "b": [2, 2, 2]})
        self.assertEqual((r["F"], r["p"]), (None, 0.0))
        self.assertIs(r["pairwise_bonferroni"][0]["anlamli"], True)
        r = h.anova({"a": [1, 1], "b": [1, 1]})
        self.assertEqual((r["F"], r["p"], r["eta_kare"]), (None, None, None))
        self.assertIsNone(r["pairwise_bonferroni"][0]["anlamli"])

    def test_normal_veride_degismedi(self):
        from sinama.cekirdek import hipotez as h
        self.assertAlmostEqual(h.anova({"a": [1, 2, 3], "b": [2, 3, 4]})["p"], 0.28786, places=5)
        self.assertIsNotNone(h.t_test_tek([1, 2, 4], 0)["t"])


class TestTPpf(unittest.TestCase):
    """A4.7: güven aralığı için ters t (tablo değerleri)."""

    def test_tablo_degerleri_ve_simetri(self):
        from sinama.cekirdek import hipotez as h
        self.assertAlmostEqual(h.t_ppf(0.975, 10), 2.2281, places=4)
        self.assertAlmostEqual(h.t_ppf(0.975, 1), 12.7062, places=3)
        self.assertAlmostEqual(h.t_ppf(0.025, 10), -h.t_ppf(0.975, 10), places=9)
        with self.assertRaises(ValueError):
            h.t_ppf(1.0, 5)


if __name__ == "__main__":
    unittest.main()
