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

    def test_sara_listesi(self):
        self.assertEqual(len(degerlendirme.sara_kontrol_listesi()), 4)


if __name__ == "__main__":
    unittest.main()
