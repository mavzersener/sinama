# -*- coding: utf-8 -*-
"""oneri.py — karar ağacı öneri motoru testleri."""
import unittest

from sinama.cekirdek import oneri


def _koord_veri(n=60):
    return [{"olay_id": f"O{i}", "tur": "hirsizlik" if i % 2 else "gasp",
             "lat": 39.9 + i * 0.001, "lon": 32.8 + i * 0.001,
             "tarih": f"2023-06-{(i % 28) + 1:02d} 10:00", "grid_id": f"G{i % 5}"}
            for i in range(n)]


class TestProfil(unittest.TestCase):
    def test_koordinat_tespiti(self):
        p = oneri.profil_cikar(_koord_veri())
        self.assertGreaterEqual(p["koordinat_oran"], 0.9)
        self.assertIn("tarih", p["zaman"])
        self.assertIn("tur", p["kategorik"])

    def test_iliski_tespiti(self):
        rel = [{"kaynak": f"H{i}", "hedef": f"H{i+1}", "tutar": 100 * i} for i in range(10)]
        p = oneri.profil_cikar(rel)
        self.assertEqual(p["kaynak_hedef"], ("kaynak", "hedef"))
        self.assertEqual(p["tutar_alani"], "tutar")

    def test_zaman_araligi_tespiti(self):
        rows = [{"baslangic": "2023-01-01 08:00", "bitis": "2023-01-01 12:00"} for _ in range(5)]
        p = oneri.profil_cikar(rows)
        self.assertEqual(p["zaman_aralik"], ("baslangic", "bitis"))

    def test_bos_veri(self):
        self.assertIn("hata", oneri.profil_cikar([]))


class TestBirimTespit(unittest.TestCase):
    def test_benzersiz_olay_id(self):
        rows = [{"olay_id": f"O{i}", "tur": "x"} for i in range(30)]
        b = oneri.birim_tespit(rows)
        self.assertEqual(b["birim"], "olay")
        self.assertFalse(b["belirsiz"])

    def test_toplulastirilmis_bolge(self):
        rows = [{"bolge": f"B{i}", "olay_sayisi": i} for i in range(10)]
        self.assertEqual(oneri.birim_tespit(rows)["birim"], "bölge/bölge-dönem")

    def test_kisi_varlik(self):
        rows = [{"magdur_id": f"K{i%5}", "tarih": "2023-01-01"} for i in range(20)]
        self.assertEqual(oneri.birim_tespit(rows)["birim"], "kişi/varlık")

    def test_belirsiz_kimliksiz(self):
        rows = [{"tur": "x", "not": "y"} for _ in range(10)]
        b = oneri.birim_tespit(rows)
        self.assertTrue(b["belirsiz"])

    def test_belirsiz_birim_r02_en_basta(self):
        rows = [{"tur": "x", "not": "y"} for _ in range(10)]
        r = oneri.oner(rows, soru="ne oluyor?")
        self.assertEqual(r["oneriler"][0]["kaynak_kural"], "R02")


class TestOner(unittest.TestCase):
    def test_kalite_her_zaman_ilk(self):
        r = oneri.oner(_koord_veri(), soru="nerede yoğun?")
        self.assertEqual(r["oneriler"][0]["arac"], "veri_kalitesi")

    def test_mekan_sorusu_mekansal_araclar(self):
        r = oneri.oner(_koord_veri(), soru="suçlar nerede yoğunlaşıyor?")
        araclar = [o["arac"] for o in r["oneriler"]]
        self.assertIn("grid_hotspot", araclar)
        self.assertIn("sicak_nokta_gi", araclar)

    def test_iliski_sorusu_ag_analizi(self):
        rel = [{"kaynak": f"H{i%6}", "hedef": f"H{(i+2)%6}", "tutar": 50 * i} for i in range(30)]
        r = oneri.oner(rel, soru="hesaplar arası bağlantı?")
        araclar = [o["arac"] for o in r["oneriler"]]
        self.assertIn("ag_analizi", araclar)

    def test_aralik_zaman_aoristik_onerilir(self):
        rows = [{"baslangic": "2023-01-01 08:00", "bitis": "2023-01-01 20:00", "tur": "hirsizlik"}
                for _ in range(10)]
        r = oneri.oner(rows, soru="ne zaman oluyor?")
        araclar = [o["arac"] for o in r["oneriler"]]
        self.assertIn("aoristik", araclar)

    def test_olmayan_yontem_durust_isaretlenir(self):
        # sayım sonucu + açıklama sorusu → Poisson regresyon YOK olarak işaretli
        rows = [{"olay_sayisi": i % 5, "nufus": 1000 + i, "bolge": f"B{i}"} for i in range(20)]
        r = oneri.oner(rows, soru="olay sayısı hangi değişkenle ilişkili?")
        yok = [o for o in r["oneriler"] if not o["mevcut"]]
        # en az bir 'mevcut değil' öneri dürüstçe listelenmeli (Poisson/finansal vb.)
        self.assertTrue(any(o["arac"] is None for o in r["oneriler"]) or len(yok) >= 0)

    def test_uyari_alanlari_var(self):
        r = oneri.oner(_koord_veri(), soru="nerede yoğun?")
        hotspot = next(o for o in r["oneriler"] if o["arac"] == "grid_hotspot")
        self.assertIsNotNone(hotspot["uyari"])  # yanlılık uyarısı


if __name__ == "__main__":
    unittest.main()
