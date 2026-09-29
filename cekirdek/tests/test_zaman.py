# -*- coding: utf-8 -*-
"""
test_zaman.py — zaman.py golden testleri (v6.6, GELISME_PLANI H3.1).
kontrol_grafigi / cusum / trend / gun_saat_analizi bu modülün
gunluk_seri'sine dayanır — taban burada sınanır. Değerler elle
hesaplanmıştır; hafta sonu / kayıp gün / kayıp alan kenarları dahil.
"""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi.cekirdek import zaman


def K(gun, saat=12, dakika=0, ay=7):
    return {"tarih": datetime(2026, ay, gun, saat, dakika)}


class TestSaatDagilimi(unittest.TestCase):
    def test_golden(self):
        k = [K(1, 8, 15), K(1, 8, 45), K(2, 22)]
        self.assertEqual(zaman.saat_dagilimi(k), {8: 2, 22: 1})

    def test_none_atlanir(self):
        self.assertEqual(zaman.saat_dagilimi([K(1, 8), {"tarih": None}, {}]),
                         {8: 1})


class TestGunDagilimi(unittest.TestCase):
    def test_golden(self):
        # 2026-07-13 Pazartesi (weekday=0), 2026-07-18 Cumartesi (=5)
        k = [K(13), K(13), K(18)]
        self.assertEqual(zaman.gun_dagilimi(k), {0: 2, 5: 1})

    def test_none_atlanir(self):
        self.assertEqual(zaman.gun_dagilimi([{"tarih": None}]), {})


class TestAyDagilimi(unittest.TestCase):
    def test_golden_sirali(self):
        k = [K(5, ay=4), K(3, ay=3), K(20, ay=3)]
        self.assertEqual(zaman.ay_dagilimi(k),
                         {"2026-03": 2, "2026-04": 1})


class TestGunlukSeri(unittest.TestCase):
    def test_golden_sifir_doldurma(self):
        # 1, 2 ve 4. günler var; 3. gün 0 ile doldurulur
        k = [K(1), K(2), K(2), K(4)]
        gunler, seri = zaman.gunluk_seri(k)
        self.assertEqual(gunler, ["2026-07-01", "2026-07-02",
                                  "2026-07-03", "2026-07-04"])
        self.assertEqual(seri, [1, 2, 0, 1])

    def test_hafta_sonu_kenari(self):
        # Cuma (17) + Pazartesi (20): Cmt/Pazar sıfırla dolar
        k = [K(17), K(20)]
        gunler, seri = zaman.gunluk_seri(k)
        self.assertEqual(gunler, ["2026-07-17", "2026-07-18",
                                  "2026-07-19", "2026-07-20"])
        self.assertEqual(seri, [1, 0, 0, 1])

    def test_bos_girdi(self):
        self.assertEqual(zaman.gunluk_seri([]), ([], []))
        self.assertEqual(zaman.gunluk_seri([{"tarih": None}]), ([], []))

    def test_tek_gun(self):
        gunler, seri = zaman.gunluk_seri([K(9)])
        self.assertEqual((gunler, seri), (["2026-07-09"], [1]))


class TestAoristikDagilim(unittest.TestCase):
    def test_golden_agirlik_paylasimi(self):
        # 22:00 → 01:00: 4 saat dilimi, her birine 0.25 ağırlık
        k = [{"baslangic": datetime(2026, 7, 1, 22),
              "bitis": datetime(2026, 7, 2, 1)}]
        d = zaman.aoristik_dagilim(k)
        self.assertEqual(d[22], 0.25)
        self.assertEqual(d[23], 0.25)
        self.assertEqual(d[0], 0.25)
        self.assertEqual(d[1], 0.25)
        self.assertEqual(d[12], 0.0)

    def test_gecersiz_aralik_atlanir(self):
        k = [{"baslangic": datetime(2026, 7, 2, 5),
              "bitis": datetime(2026, 7, 2, 3)}]  # bitis < başlangıç
        self.assertEqual(sum(zaman.aoristik_dagilim(k).values()), 0.0)

    def test_toplam_korunur(self):
        # sözleşme: saatler 2 basamağa yuvarlanır (gösterim için) —
        # 1/3 ağırlıklı olay 0.33×3=0.99 verir; toplam kütle kaybı
        # olay başına ≤ 0.01'dir. Bu test sözleşmeyi sabitler.
        k = [{"baslangic": datetime(2026, 7, 1, 10),
              "bitis": datetime(2026, 7, 1, 11)},
             {"baslangic": datetime(2026, 7, 1, 10),
              "bitis": datetime(2026, 7, 1, 12)}]
        self.assertAlmostEqual(sum(zaman.aoristik_dagilim(k).values()),
                               1.99, places=6)


if __name__ == "__main__":
    unittest.main()
