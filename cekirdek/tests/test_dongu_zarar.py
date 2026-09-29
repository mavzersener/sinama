# -*- coding: utf-8 -*-
"""v5.3 birim testleri: zarar (CHI) + PPDAC döngü + rapor."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi import zarar, dongu, rapor, mekan, veri


KAYIT = ([{"tur": "hırsızlık", "mahalle": "A", "lat": 41.0, "lon": 29.0}] * 50
         + [{"tur": "kapkaç", "mahalle": "B", "lat": 41.01, "lon": 29.01}] * 10
         + [{"tur": "gasb", "mahalle": "C", "lat": 41.02, "lon": 29.02}] * 3
         + [{"tur": "cinayet", "mahalle": "D", "lat": 41.03, "lon": 29.03}] * 1)


class TestZarar(unittest.TestCase):
    def test_tablo(self):
        s = zarar.zarar_tablosu(KAYIT, grup_alan="mahalle")
        self.assertEqual(s["olay_sayisi"], 64)
        self.assertAlmostEqual(s["gruplar"]["C"]["zarar"], 2190.0)

    def test_hacim_zarar_ayrisma(self):
        # hacim: A>B>C; zarar: C (2190) > B (1800) → C "seyrek ama ağır"
        s = zarar.hacim_zarar_karsilastir(KAYIT, "mahalle")
        c = next(x for x in s if x["grup"] == "D")  # 1 olay ama 5475 zarar
        self.assertEqual(c["sinif"], "seyrek ama ağır (gözden kaçan risk)")

    def test_power_few(self):
        s = zarar.power_few(KAYIT, "mahalle")
        self.assertEqual(s["birimler"][0], "D")  # cinayet: tek olay, en yüksek zarar
        self.assertLessEqual(s["yogunlasma_orani"], 1.0)

    def test_bilinmeyen_tur_diger(self):
        self.assertEqual(zarar.olay_zarari("bilinmeyen_xyz", zarar.VARSAYILAN_AGIRLIKLAR), 10)

    def test_kurum_tablosu(self):
        with tempfile.TemporaryDirectory() as d:
            import json
            yol = os.path.join(d, "agirlik.json")
            with open(yol, "w") as f:
                json.dump({"hırsızlık": 5}, f)
            tablo = zarar.agirlik_tablosu_yukle(yol)
            self.assertEqual(tablo["hırsızlık"], 5)

    def test_agirlikli_kde(self):
        pts = [(41.0, 29.0), (41.001, 29.001), (41.05, 29.05)]
        h1 = mekan.kde_yogunluk(pts, 0.5, 0.2)
        h2 = mekan.kde_yogunluk(pts, 0.5, 0.2, [100.0, 100.0, 1.0])
        self.assertNotEqual(h1[0]["yogunluk"], h2[0]["yogunluk"])

    def test_gate_homojen(self):
        karar = veri.analiz_uygun_mu({"n": 100}, "zarar_analizi",
                                     tur_kardinalite=1)
        self.assertTrue(any("homojen" in s for s in karar["sebepler"]))


class TestDongu(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def _tam_dongu(self):
        d = dongu.AnalizDongusu({"soran": "amir", "karar": "devriye planı",
                                 "urun_turu": "taktik"})
        d.planla()
        d.veri_bagla({"n": 100, "uyarilar": []})
        d.analize_gec({"uygun": True, "sebepler": ["ok"]})
        d.analiz_kaydet("grid_hotspot", {"hucre": 3},
                        {"hipotez": "gece kümelenmesi var",
                         "yorum": "3 hücre belirgin"})
        d.sonucla("sorun_dogrulandi", {"onaylayan": "analist_x"})
        d.izleme_plani("haftalık olay", 30, "2026-08-01")
        return d

    def test_tam_dongu(self):
        d = self._tam_dongu()
        self.assertEqual(d.manifesto["faz"], "SONUC")
        self.assertEqual(len(d.manifesto["gecmis"]), 6)
        self.assertIsNotNone(d.manifesto["izleme"])

    def test_faz_atlama_reddedilir(self):
        d = dongu.AnalizDongusu({"karar": "x"})
        with self.assertRaises(dongu.DonguHatasi):
            d.veri_bagla({})  # planla() atlandı

    def test_gate_red_engeller(self):
        d = dongu.AnalizDongusu({"karar": "x"})
        d.planla()
        d.veri_bagla({"n": 5})
        with self.assertRaises(dongu.DonguHatasi):
            d.analize_gec({"uygun": False, "sebepler": ["n yetersiz"]})

    def test_insan_onayi_zorunlu(self):
        d = dongu.AnalizDongusu({"karar": "x"})
        d.planla(); d.veri_bagla({"n": 100})
        d.analize_gec({"uygun": True})
        with self.assertRaises(dongu.DonguHatasi):
            d.sonucla("sorun_dogrulandi", {})  # onaylayan yok

    def test_kalicilik(self):
        d = self._tam_dongu()
        dongu.kaydet(d, self.tmp)
        y = dongu.yukle(d.manifesto["oturum_id"], self.tmp)
        self.assertEqual(y.manifesto["faz"], "SONUC")
        self.assertEqual(len(dongu.listele(self.tmp)), 1)

    def test_plan_sablonlari(self):
        for urun in ("taktik", "stratejik", "sorun_cozme"):
            d = dongu.AnalizDongusu({"karar": "x", "urun_turu": urun})
            plan = d.planla()
            self.assertIn("veri_kalitesi", plan["onerilen"])
            self.assertIn("brifing_uret", plan["onerilen"])


class TestRapor(unittest.TestCase):
    def test_belirsizlik_zorunlu(self):
        with self.assertRaises(ValueError):
            rapor.taktik_brifing({"karar": "x"}, belirsizlik=None)

    def test_brifing_icerik(self):
        u = rapor.taktik_brifing(
            {"karar": "devriye", "soran": "amir"},
            hotspot=[{"lat": 41, "lon": 29, "adet": 10}],
            power_few={"birimler": ["A"], "birim_sayisi": 1, "toplam_birim": 5,
                       "yogunlasma_orani": 0.2},
            belirsizlik=["küçük örneklem"])
        self.assertIn("Taktik Brifing", u)
        self.assertIn("küçük örneklem", u)
        self.assertIn("insan onayı", u)


if __name__ == "__main__":
    unittest.main()
