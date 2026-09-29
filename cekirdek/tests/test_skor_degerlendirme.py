# -*- coding: utf-8 -*-
"""
test_skor_degerlendirme.py — skor.py + degerlendirme.py golden testleri
(v6.6, H3.2). Ağırlık toplamı, eşik yönü, DiD ve kesinti elle hesap.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama.cekirdek import skor, degerlendirme


class TestRiskSkoru(unittest.TestCase):
    KURALLAR = [
        {"alan": "tur", "kosul": "==", "deger": "hırsızlık", "agirlik": 2},
        {"alan": "adet", "kosul": ">=", "deger": 3, "agirlik": 1.5},
        {"alan": "adet", "kosul": "<", "deger": 2, "agirlik": 0.5},
        {"alan": "mo", "kosul": "icerir", "deger": "cam", "agirlik": 1},
    ]

    def test_agirlik_toplami_golden(self):
        k = {"tur": "hırsızlık", "adet": 4, "mo": "cam kırılarak"}
        s, tetik = skor.risk_skoru(k, self.KURALLAR)
        self.assertEqual(s, 4.5)  # 2 + 1.5 + 1; <2 koşulu tutmaz
        self.assertEqual(len(tetik), 3)

    def test_hicbiri_tutmazsa_sifir(self):
        s, tetik = skor.risk_skoru({"tur": "uyuşturucu", "adet": 2,
                                    "mo": "sessiz"}, self.KURALLAR)
        self.assertEqual(s, 0.0)
        self.assertEqual(tetik, [])

    def test_sayisal_olmayan_deger_kiyaslanmaz(self):
        k = {"adet": "yok"}
        s, _ = skor.risk_skoru(k, [{"alan": "adet", "kosul": ">=",
                                    "deger": 1, "agirlik": 5}])
        self.assertEqual(s, 0.0)  # istisna değil, koşul tutmaz

    def test_varsayilan_agirlik_bir(self):
        s, tetik = skor.risk_skoru({"tur": "x"}, [{"alan": "tur",
                                                   "deger": "x"}])
        self.assertEqual(s, 1.0)
        self.assertIn("+1.0", tetik[0])

    def test_toplu_skorla_siralama_ve_filtre(self):
        kayitlar = [{"id": "a", "adet": 5}, {"id": "b", "adet": 0},
                    {"id": "c", "adet": 3}]
        kurallar = [{"alan": "adet", "kosul": ">=", "deger": 1,
                     "agirlik": 1}]
        sonuc = skor.toplu_skorla(kayitlar, kurallar)
        self.assertEqual([r["id"] for r in sonuc], ["a", "c"])  # b elenir
        self.assertEqual(sonuc[0]["skor"], 1.0)

    def test_toplu_skorla_agirlik_toplami_golden(self):
        kayitlar = [{"id": "a", "tur": "hırsızlık", "adet": 4}]
        sonuc = skor.toplu_skorla(kayitlar, self.KURALLAR[:2])
        self.assertEqual(sonuc[0]["skor"], 3.5)  # 2 + 1.5


class TestEsikUyarilari(unittest.TestCase):
    def test_duz_ust_alt(self):
        k = [{"id": "a", "adet": 7}, {"id": "b", "adet": 1}]
        self.assertEqual(skor.esik_uyarilari(k, "adet", 5),
                         [{"kayit": "a", "deger": 7.0, "esik": 5}])
        self.assertEqual(skor.esik_uyarilari(k, "adet", 2, yon="alt"),
                         [{"kayit": "b", "deger": 1.0, "esik": 2}])

    def test_gruplu_toplam_golden(self):
        k = [{"mahalle": "merkez", "zarar": 100},
             {"mahalle": "merkez", "zarar": 250},
             {"mahalle": "liman", "zarar": 50}]
        sonuc = skor.esik_uyarilari(k, "zarar", 300, grupla="mahalle")
        self.assertEqual(sonuc, [{"grup": "merkez", "deger": 350.0,
                                  "esik": 300}])

    def test_sayisal_olmayan_atlanir(self):
        k = [{"mahalle": "m", "zarar": "bilinmiyor"}]
        self.assertEqual(skor.esik_uyarilari(k, "zarar", 1, grupla="mahalle"),
                         [])


class TestOncesiSonrasi(unittest.TestCase):
    def test_golden_liste(self):
        r = degerlendirme.oncesi_sonrasi([3, 4], [2, 3])
        self.assertEqual((r["once"], r["sonra"]), (7, 5))
        self.assertEqual(r["degisim_yuzde"], -28.57)
        self.assertEqual(r["yorum"], "azalma")

    def test_sifir_once_none(self):
        r = degerlendirme.oncesi_sonrasi(0, 5)
        self.assertIsNone(r["degisim_yuzde"])
        self.assertEqual(r["yorum"], "artış")

    def test_degisim_yok(self):
        self.assertEqual(degerlendirme.oncesi_sonrasi(5, 5)["yorum"],
                         "değişim yok")


class TestFarklarinFarki(unittest.TestCase):
    def test_golden(self):
        # M: 20→10 (-10); K: 18→16 (-2) → DiD = -10 - (-2) = -8
        r = degerlendirme.farklarin_farki(20, 10, 18, 16)
        self.assertEqual(r["did_etki"], -8)
        self.assertIn("-8", r["yorum"])

    def test_etkisiz_mudahale(self):
        r = degerlendirme.farklarin_farki(20, 18, 16, 14)
        self.assertEqual(r["did_etki"], 0)  # -2 - (-2)


class TestKesintiAnalizi(unittest.TestCase):
    def test_seviye_sicramasi_golden(self):
        r = degerlendirme.kesinti_analizi([2, 2, 2, 2, 8, 8, 8, 8], 4)
        self.assertEqual(r["once_ortalama"], 2)
        self.assertEqual(r["sonra_ortalama"], 8)
        self.assertEqual(r["seviye_farki"], 6)
        self.assertEqual(r["once_egim"], 0)

    def test_egim_golden(self):
        # [1,2,3,4]: aritmetik dizi, eğim tam 1.0
        r = degerlendirme.kesinti_analizi([1, 2, 3, 4, 1, 2, 3, 4], 4)
        self.assertEqual(r["once_egim"], 1.0)

    def test_kisa_seri_none(self):
        self.assertIsNone(degerlendirme.kesinti_analizi([1, 2], 1))

    # A4.7: segmentli regresyon ITS — belirsizlikle.
    GURULTU = [1.5, -2.0, 0.5, 2.5, -1.0, -0.5, 1.0, -2.5, 2.0, 0.0, -1.5, 1.0]

    def test_seviye_sicramasi_guven_araligiyla(self):
        seri = [40 + e for e in self.GURULTU] + [60 + e for e in self.GURULTU]
        r = degerlendirme.kesinti_analizi(seri, 12)
        s = r["seviye_degisimi"]
        self.assertEqual(r["model"], "segmentli OLS")
        self.assertLess(s["p"], 0.05)
        self.assertTrue(s["ga_alt"] <= 20 <= s["ga_ust"], s)
        self.assertGreater(s["ga_alt"], 0)
        self.assertIsNotNone(r["durbin_watson"])

    def test_degisim_yoksa_ga_sifiri_kapsar(self):
        seri = [40 + e for e in self.GURULTU] + [40 + e for e in reversed(self.GURULTU)]
        s = degerlendirme.kesinti_analizi(seri, 12)["seviye_degisimi"]
        self.assertTrue(s["ga_alt"] <= 0 <= s["ga_ust"], s)
        self.assertGreaterEqual(s["p"], 0.05)

    def test_ga_genisligi_t_kritik_degeriyle(self):
        # %95 GA = tahmin ± t(0,975; n-4)·se; n = 24 → sd = 20 → 2,0860.
        seri = [40 + e for e in self.GURULTU] + [60 + e for e in self.GURULTU]
        s = degerlendirme.kesinti_analizi(seri, 12)["seviye_degisimi"]
        self.assertAlmostEqual((s["ga_ust"] - s["ga_alt"]) / (2 * s["se"]),
                               2.0860, delta=0.002)

    def test_tam_uyumda_cikarim_tanimsiz(self):
        r = degerlendirme.kesinti_analizi([1, 2, 3, 4, 5, 6, 20, 21, 22, 23, 24, 25], 6)
        self.assertEqual(r["seviye_degisimi"]["tahmin"], 13.0)  # 20 − karşıolgusal 7
        self.assertIsNone(r["seviye_degisimi"]["p"])
        self.assertIsNone(r["seviye_degisimi"]["ga_alt"])
        self.assertIsNone(r["durbin_watson"])
        self.assertTrue(any("tam uyum" in u for u in r["uyarilar"]))

    def test_sabit_seri_model_kurulamaz(self):
        r = degerlendirme.kesinti_analizi([5] * 12, 6)
        self.assertIsNone(r["model"])
        self.assertEqual(r["seviye_farki"], 0)
        self.assertIn("kurulamadı", r["uyarilar"][0])

    def test_otokorelasyon_uyarisi(self):
        dalga = [1, 3, 6, 8, 9, 8, 6, 3]
        r = degerlendirme.kesinti_analizi(dalga + dalga, 8)
        self.assertLess(r["durbin_watson"], 1.5)
        self.assertTrue(any("Durbin-Watson" in u for u in r["uyarilar"]))

    def test_kisa_seri_yalniz_betimsel_ve_nedensellik_notu(self):
        r = degerlendirme.kesinti_analizi([2, 2, 8, 8], 2)
        self.assertIsNone(r["model"])
        self.assertTrue(r["uyarilar"])
        self.assertIn("nedensellik kanıtlamaz", r["not"])

    def test_sara_listesi(self):
        self.assertEqual(len(degerlendirme.sara_kontrol_listesi()), 4)


if __name__ == "__main__":
    unittest.main()
