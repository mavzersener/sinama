# -*- coding: utf-8 -*-
"""
olay/1 ortak olay şeması doğrulayıcısı testleri.
Zorunlu alanlar, şema kuralları, hata mesajları, doluluk oranları.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi import veri


# Test verileri

GECERLI_OLAY = [
    {
        "olay_id": "evt001",
        "zaman": "2026-05-01 10:00:00",
        "tur": "hırsızlık",
        "lat": "41.0",
        "lon": "29.0",
        "guvenilirlik": "0.8",
        "zarar": "1500"
    }
]

GECERLI_GRID = [
    {
        "olay_id": "evt002",
        "zaman": "2026-05-01",
        "tur": "kapkaç",
        "grid_id": "A1B2",
        "zarar": "25000"
    }
]

GECERLI_KARISIK = [
    {
        "olay_id": "evt001",
        "zaman": "2026-05-01 10:00:00",
        "tur": "hırsızlık",
        "lat": "41.0",
        "lon": "29.0",
        "guvenilirlik": "0.8",
        "zarar": "1500"
    },
    {
        "olay_id": "evt002",
        "zaman": "02.05.2026",
        "tur": "dolandırıcılık",
        "grid_id": "B3C4",
        "guvenilirlik": "0.5",
        "zarar": "4000"
    },
    {
        "olay_id": "evt003",
        "zaman": "2026/05/03",
        "tur": "kavga",
        "lat": "40.95",
        "lon": "28.95",
        "zarar": "300"
    }
]

TEKRARLANAN_ID = [
    {"olay_id": "evt001", "zaman": "2026-05-01", "tur": "hırsızlık", "lat": "41.0", "lon": "29.0"},
    {"olay_id": "evt001", "zaman": "2026-05-02", "tur": "kapkaç", "lat": "41.1", "lon": "29.1"}
]

KOTU_ZAMAN = [
    {"olay_id": "evt001", "zaman": "BOZUK", "tur": "hırsızlık", "lat": "41.0", "lon": "29.0"}
]

KOTU_KOORDINAT = [
    {"olay_id": "evt001", "zaman": "2026-05-01", "tur": "hırsızlık", "lat": "91.0", "lon": "29.0"},  # geçersiz lat
    {"olay_id": "evt002", "zaman": "2026-05-02", "tur": "kapkaç", "lat": "", "lon": ""},  # boş koordinat, grid_id yok
]

KOTU_GUVENILIRLIK = [
    {"olay_id": "evt001", "zaman": "2026-05-01", "tur": "hırsızlık", "lat": "41.0", "lon": "29.0", "guvenilirlik": "1.5"}
]

KOTU_ZAMAN_BITIS = [
    {
        "olay_id": "evt001",
        "zaman": "2026-05-01 10:00",
        "zaman_bitis": "2026-05-01 09:00",
        "tur": "hırsızlık",
        "lat": "41.0",
        "lon": "29.0"
    }
]

KOTU_ZAMAN_BITIS_COZULEMEZ = [
    {
        "olay_id": "evt001",
        "zaman": "2026-05-01 10:00",
        "zaman_bitis": "BOZUK_TARIH",
        "tur": "hırsızlık",
        "lat": "41.0",
        "lon": "29.0"
    }
]

BOZUK_GUVENILIRLIK_TURU = [
    {
        "olay_id": "evt001",
        "zaman": "2026-05-01",
        "tur": "hırsızlık",
        "lat": "41.0",
        "lon": "29.0",
        "guvenilirlik": "yanlış"
    }
]


class TestOlaySema(unittest.TestCase):
    def test_gecerli_koordinat(self):
        """Geçerli lat/lon'lu kayıt."""
        sonuc = veri.olay_dogrula(GECERLI_OLAY)
        self.assertTrue(sonuc["gecerli"])
        self.assertEqual(len(sonuc["hatalar"]), 0)
        self.assertEqual(sonuc["kayit_sayisi"], 1)
        self.assertEqual(sonuc["sema"], "olay/1")

    def test_gecerli_grid(self):
        """Geçerli grid_id'li kayıt."""
        sonuc = veri.olay_dogrula(GECERLI_GRID)
        self.assertTrue(sonuc["gecerli"])
        self.assertEqual(len(sonuc["hatalar"]), 0)

    def test_gecerli_karisik(self):
        """Koordinat ve grid_id karışık geçerli kayıtlar."""
        sonuc = veri.olay_dogrula(GECERLI_KARISIK)
        self.assertTrue(sonuc["gecerli"])
        self.assertEqual(len(sonuc["hatalar"]), 0)
        self.assertEqual(sonuc["kayit_sayisi"], 3)

    def test_bos_liste(self):
        """Boş kayıt listesi."""
        sonuc = veri.olay_dogrula([])
        self.assertFalse(sonuc["gecerli"])
        self.assertIn("kayıt yok", sonuc["hatalar"])
        self.assertEqual(sonuc["kayit_sayisi"], 0)

    def test_tekrarlanan_olay_id(self):
        """Tekrarlanan olay_id."""
        sonuc = veri.olay_dogrula(TEKRARLANAN_ID)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("tekrarlanıyor" in h for h in sonuc["hatalar"]))

    def test_bozuk_zaman(self):
        """Çözülemeyen zaman alanı."""
        sonuc = veri.olay_dogrula(KOTU_ZAMAN)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("zaman çözülemiyor" in h for h in sonuc["hatalar"]))

    def test_bozuk_koordinat(self):
        """Geçersiz koordinat ve grid_id yok."""
        sonuc = veri.olay_dogrula(KOTU_KOORDINAT)
        self.assertFalse(sonuc["gecerli"])
        # İlk kayıt: geçersiz lat (91.0) → hata
        # İkinci kayıt: boş lat/lon ve grid_id yok → hata
        self.assertGreaterEqual(len(sonuc["hatalar"]), 2)

    def test_guvenilirlik_araligi(self):
        """guvenilirlik aralık dışı."""
        sonuc = veri.olay_dogrula(KOTU_GUVENILIRLIK)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("guvenilirlik aralık dışı" in h for h in sonuc["hatalar"]))

    def test_zaman_bitis_kont(self):
        """zaman_bitis < zaman kontrolü."""
        sonuc = veri.olay_dogrula(KOTU_ZAMAN_BITIS)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("zaman_bitis zaman'dan önce" in h for h in sonuc["hatalar"]))

    def test_doluluk_oranlari(self):
        """Doluluk oranları doğru hesaplanıyor mu?"""
        sonuc = veri.olay_dogrula(GECERLI_KARISIK)
        doluluk = sonuc["doluluk"]
        self.assertIn("olay_id", doluluk)
        self.assertEqual(doluluk["olay_id"], 1.0)  # Tüm kayıtlarda var
        self.assertEqual(doluluk["zaman"], 1.0)
        self.assertEqual(doluluk["tur"], 1.0)
        # lat/lon: 2/3'ü var (evt003'te var), grid_id: 1/3'ü var (evt002'de var)
        self.assertAlmostEqual(doluluk["lat"], round(2/3, 2))
        self.assertAlmostEqual(doluluk["lon"], round(2/3, 2))
        self.assertAlmostEqual(doluluk["grid_id"], round(1/3, 2))

    def test_hata_kirpmasi(self):
        """maks_hata_ornegi uygulanıyor mu?"""
        # Çok sayıda hata üreten kayıtlar
        bozuk_kayitlar = [
            {"olay_id": "", "zaman": "BOZUK", "tur": "", "lat": "100", "lon": "200"}
            for _ in range(50)
        ]
        sonuc = veri.olay_dogrula(bozuk_kayitlar, maks_hata_ornegi=5)
        # max 5 örnek + "... ve N hata daha" satırı
        self.assertLessEqual(len(sonuc["hatalar"]), 6)
        self.assertTrue(any("... ve" in h for h in sonuc["hatalar"]))

    def test_satir_indeksi(self):
        """Hata mesajlarında satır indeksi var mı?"""
        sonuc = veri.olay_dogrula(KOTU_ZAMAN)
        self.assertTrue(any("satır" in h for h in sonuc["hatalar"]))

    def test_bosaltilmis_alanlar(self):
        """Boş olay_id ve tur tespiti."""
        kayitlar = [
            {"olay_id": "", "zaman": "2026-05-01", "tur": "hırsızlık", "lat": "41.0", "lon": "29.0"},
            {"olay_id": "evt001", "zaman": "2026-05-02", "tur": "", "lat": "41.1", "lon": "29.1"}
        ]
        sonuc = veri.olay_dogrula(kayitlar)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("olay_id boş" in h for h in sonuc["hatalar"]))
        self.assertTrue(any("tur boş" in h for h in sonuc["hatalar"]))

    def test_zarar_kontrolu(self):
        """Negatif zarar kontrolü."""
        kayitlar = [
            {"olay_id": "evt001", "zaman": "2026-05-01", "tur": "hırsızlık", "lat": "41.0", "lon": "29.0", "zarar": "-500"}
        ]
        sonuc = veri.olay_dogrula(kayitlar)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("zarar negatif" in h for h in sonuc["hatalar"]))

    def test_zaman_bitis_cozulemez(self):
        """zaman_bitis çözülemeyen tarih."""
        sonuc = veri.olay_dogrula(KOTU_ZAMAN_BITIS_COZULEMEZ)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("zaman_bitis çözülemiyor" in h for h in sonuc["hatalar"]))

    def test_guvenilirlik_sayi_degil(self):
        """guvenilirlik sayıya çevrilenemez."""
        sonuc = veri.olay_dogrula(BOZUK_GUVENILIRLIK_TURU)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("guvenilirlik sayıya çevrilemez" in h for h in sonuc["hatalar"]))

    def test_zarar_sayi_degil(self):
        """zarar sayıya çevrilenemez."""
        kayitlar = [
            {"olay_id": "evt001", "zaman": "2026-05-01", "tur": "hırsızlık", "lat": "41.0", "lon": "29.0", "zarar": "yanlış"}
        ]
        sonuc = veri.olay_dogrula(kayitlar)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("zarar sayıya çevrilemez" in h for h in sonuc["hatalar"]))

    def test_zaman_bitis_ile_gecerli(self):
        """Geçerli zaman_bitis ile kayıt."""
        kayitlar = [
            {
                "olay_id": "evt001",
                "zaman": "2026-05-01 10:00",
                "zaman_bitis": "2026-05-01 12:00",
                "tur": "hırsızlık",
                "lat": "41.0",
                "lon": "29.0"
            }
        ]
        sonuc = veri.olay_dogrula(kayitlar)
        self.assertTrue(sonuc["gecerli"])
        self.assertEqual(sonuc["doluluk"]["zaman_bitis"], 1.0)

    def test_bos_olay_id_ozel(self):
        """Whitespace-only olay_id tespiti."""
        kayitlar = [
            {"olay_id": "   ", "zaman": "2026-05-01", "tur": "hırsızlık", "lat": "41.0", "lon": "29.0"}
        ]
        sonuc = veri.olay_dogrula(kayitlar)
        self.assertFalse(sonuc["gecerli"])
        self.assertTrue(any("olay_id boş" in h for h in sonuc["hatalar"]))

    def test_multiple_hatalar(self):
        """Birden çok hata birlikte."""
        kayitlar = [
            {"olay_id": "", "zaman": "BOZUK", "tur": "", "lat": "100", "lon": "180", "guvenilirlik": "2"}
        ]
        sonuc = veri.olay_dogrula(kayitlar)
        self.assertFalse(sonuc["gecerli"])
        self.assertGreaterEqual(len(sonuc["hatalar"]), 3)  # olay_id, zaman, tur en az


if __name__ == "__main__":
    unittest.main()


class TestIso8601Zaman(unittest.TestCase):
    """olay/1 kanonik zaman biçimi ('T' ayraçlı ISO 8601) çözülmeli."""

    def test_iso_t_ayracli_zaman_gecerli(self):
        kayitlar = [{"olay_id": "E1", "zaman": "2026-06-01T08:30:00",
                     "tur": "hirsizlik", "grid_id": "G1"}]
        rapor = veri.olay_dogrula(kayitlar)
        self.assertTrue(rapor["gecerli"], rapor["hatalar"])
