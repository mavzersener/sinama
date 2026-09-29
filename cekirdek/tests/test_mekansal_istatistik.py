# -*- coding: utf-8 -*-
"""mekansal_istatistik: Global Moran's I, Getis-Ord Gi*, eşitlik testleri."""
import unittest

from suc_analizi.cekirdek import mekansal_istatistik as mi


def _grid(deger_fn, boyut=6, adim=0.02):
    """boyut×boyut düzenli grid; deger_fn(i,j) → adet."""
    return [{"lat": 39.0 + i * adim, "lon": 32.0 + j * adim, "adet": deger_fn(i, j)}
            for i in range(boyut) for j in range(boyut)]


class TestGlobalMoran(unittest.TestCase):
    def test_kumeli_desen_anlamli_pozitif(self):
        # sol-üst köşe yüksek → güçlü pozitif otokorelasyon
        h = _grid(lambda i, j: 20 if (i < 2 and j < 2) else 1)
        r = mi.global_moran(h, bant_km=2.5)
        self.assertGreater(r["I"], r["beklenen"])
        self.assertLess(r["p"], 0.05)
        self.assertIn("KÜMELENME", r["yorum"])

    def test_dama_deseni_negatif(self):
        # satranç (komşular zıt) → negatif otokorelasyon
        h = _grid(lambda i, j: 10 if (i + j) % 2 == 0 else 1)
        r = mi.global_moran(h, bant_km=2.5)  # rook komşuluk
        self.assertLess(r["I"], r["beklenen"])

    def test_esit_degerler_tanimsiz(self):
        h = _grid(lambda i, j: 5)
        r = mi.global_moran(h, bant_km=2.5)
        self.assertIn("hata", r)

    def test_az_hucre_reddi(self):
        h = [{"lat": 39.0, "lon": 32.0, "adet": 3}, {"lat": 39.1, "lon": 32.1, "adet": 5}]
        self.assertIn("hata", mi.global_moran(h))

    def test_beklenen_deger_formulu(self):
        h = _grid(lambda i, j: (i * 6 + j) % 7 + 1)
        r = mi.global_moran(h, bant_km=2.5)
        self.assertAlmostEqual(r["beklenen"], -1.0 / (len(h) - 1), places=4)


class TestGetisOrd(unittest.TestCase):
    def test_yuksek_hucreler_sicak(self):
        h = _grid(lambda i, j: 20 if (i < 2 and j < 2) else 1)
        r = mi.getis_ord(h, bant_km=2.5)
        self.assertGreater(r["sicak"], 0)
        # en yüksek gi_z'li hücre yüksek adetli olmalı
        self.assertEqual(r["sonuclar"][0]["adet"], 20)
        self.assertEqual(r["sonuclar"][0]["tur"], "sıcak")

    def test_guven_bantlari(self):
        h = _grid(lambda i, j: 20 if (i < 2 and j < 2) else 1)
        r = mi.getis_ord(h, bant_km=2.5)
        guvenler = {s["guven"] for s in r["sonuclar"] if s["guven"]}
        self.assertTrue(guvenler <= {"%90", "%95", "%99"})

    def test_esit_deger_tanimsiz(self):
        r = mi.getis_ord(_grid(lambda i, j: 4), bant_km=2.5)
        self.assertIn("hata", r)


class TestYerelMoran(unittest.TestCase):
    def test_kose_kumesi_HH(self):
        h = _grid(lambda i, j: 20 if (i < 2 and j < 2) else 1)
        r = mi.yerel_moran(h, bant_km=2.5)
        self.assertGreater(r["ozet"]["HH"], 0)
        hh = [s for s in r["sonuclar"] if s["kumeleme"] == "HH"]
        self.assertTrue(all(s["adet"] == 20 for s in hh))

    def test_heterojen_ada_aykiri_uretir(self):
        import random
        rng = random.Random(7)
        h = [{"lat": 39.0 + i * 0.02, "lon": 32.0 + j * 0.02,
              "adet": (80 if (i == 3 and j == 3) else rng.randint(1, 5))}
             for i in range(6) for j in range(6)]
        r = mi.yerel_moran(h, bant_km=2.5)
        # ada çevresinde mekânsal aykırı değer (HL/LH) beklenir
        self.assertGreater(r["ozet"]["HL"] + r["ozet"]["LH"], 0)

    def test_determinist_sabit_seed(self):
        h = _grid(lambda i, j: 20 if (i < 2 and j < 2) else 1)
        a = mi.yerel_moran(h, bant_km=2.5, seed=42)
        b = mi.yerel_moran(h, bant_km=2.5, seed=42)
        self.assertEqual([s["p"] for s in a["sonuclar"]],
                         [s["p"] for s in b["sonuclar"]])

    def test_esit_deger_tanimsiz(self):
        self.assertIn("hata", mi.yerel_moran(_grid(lambda i, j: 5), bant_km=2.5))

    def test_az_hucre_reddi(self):
        h = [{"lat": 39.0, "lon": 32.0, "adet": 3},
             {"lat": 39.1, "lon": 32.1, "adet": 5}]
        self.assertIn("hata", mi.yerel_moran(h))

    def test_ozet_toplami_n(self):
        h = _grid(lambda i, j: 20 if (i < 2 and j < 2) else (i + j) % 4 + 1)
        r = mi.yerel_moran(h, bant_km=2.5)
        self.assertEqual(sum(r["ozet"].values()), r["n"])


class TestMerkezsel(unittest.TestCase):
    def test_dogu_bati_yayilim_aci_90(self):
        pts = [(39.0, 32.0 + i * 0.05) for i in range(9)]
        r = mi.merkezsel(pts)
        self.assertAlmostEqual(r["elips"]["aci_derece"], 90.0, delta=1.0)

    def test_kuzey_guney_yayilim_aci_0(self):
        pts = [(39.0 + i * 0.05, 32.0) for i in range(9)]
        r = mi.merkezsel(pts)
        self.assertTrue(r["elips"]["aci_derece"] < 1.0 or r["elips"]["aci_derece"] > 179.0)

    def test_ortalama_merkez_dogru(self):
        pts = [(39.0, 32.0), (41.0, 34.0)]  # <3 → hata; genişlet
        pts = [(39.0, 32.0), (41.0, 34.0), (40.0, 33.0)]
        r = mi.merkezsel(pts)
        self.assertAlmostEqual(r["ortalama_merkez"]["lat"], 40.0, places=4)
        self.assertAlmostEqual(r["ortalama_merkez"]["lon"], 33.0, places=4)

    def test_agirlikli_merkez_kayar(self):
        r = mi.merkezsel([(39.0, 32.0), (39.0, 32.0), (40.0, 33.0)],
                         agirliklar=[1, 1, 100])
        self.assertGreater(r["ortalama_merkez"]["lat"], 39.9)
        self.assertTrue(r["agirlikli"])

    def test_az_nokta_reddi(self):
        self.assertIn("hata", mi.merkezsel([(39.0, 32.0), (40.0, 33.0)]))

    def test_agirlik_uyusmazligi(self):
        self.assertIn("hata", mi.merkezsel([(39, 32), (40, 33), (41, 34)], agirliklar=[1, 2]))


class TestRiskArazi(unittest.TestCase):
    FAKTORLER = [
        (39.92, 32.85, "bar"), (39.921, 32.851, "atm"), (39.919, 32.849, "otogar"),
        (39.98, 32.90, "bar"), (39.95, 32.88, "atm"),
    ]

    def test_colocation_en_yuksek_risk(self):
        r = mi.risk_arazi(self.FAKTORLER, hucre_km=0.3, yaricap_km=0.5)
        self.assertEqual(r["maks_risk"], 3)
        self.assertEqual(len(r["sonuclar"][0]["turler"]), 3)

    def test_faktor_turleri_listesi(self):
        r = mi.risk_arazi(self.FAKTORLER, hucre_km=0.3, yaricap_km=0.5)
        self.assertEqual(set(r["faktor_turleri"]), {"bar", "atm", "otogar"})

    def test_az_faktor_reddi(self):
        self.assertIn("hata", mi.risk_arazi([(39.0, 32.0, "bar")]))

    def test_ayni_tur_risk_bir(self):
        # yalnız 'bar' türü (co-location yok) → risk en fazla 1
        r = mi.risk_arazi([(39.0, 32.0, "bar"), (39.03, 32.03, "bar")],
                          hucre_km=0.5, yaricap_km=0.5)
        self.assertEqual(r["maks_risk"], 1)


class TestMekansalRegresyonTani(unittest.TestCase):
    KOORD = [(39.0 + i * 0.02, 32.0 + j * 0.02) for i in range(6) for j in range(6)]

    def test_mekansal_artik_ols_yanli(self):
        import random
        rng = random.Random(5)
        n = len(self.KOORD)
        X = [[rng.gauss(0, 1)] for _ in range(n)]
        y = [(self.KOORD[k][0] - 39.0) * 50 + rng.gauss(0, 0.3) for k in range(n)]
        r = mi.mekansal_regresyon_tani(y, X, self.KOORD, ["x"], bant_km=2.5)
        self.assertLess(r["artik_moran"]["p"], 0.05)
        self.assertIn("yanlı", r["karar"])

    def test_dogrusal_artik_ols_gecerli(self):
        import random
        rng = random.Random(9)
        n = len(self.KOORD)
        X = [[rng.gauss(0, 1)] for _ in range(n)]
        y = [3 * X[k][0] + rng.gauss(0, 0.2) for k in range(n)]
        r = mi.mekansal_regresyon_tani(y, X, self.KOORD, ["x"], bant_km=2.5)
        self.assertGreater(r["artik_moran"]["p"], 0.05)
        self.assertIn("geçerli", r["karar"])

    def test_az_gozlem_reddi(self):
        r = mi.mekansal_regresyon_tani([1, 2, 3], [[1], [2], [3]],
                                       [(39, 32), (39, 33), (39, 34)], ["x"])
        self.assertIn("hata", r)


class TestCografiProfil(unittest.TestCase):
    SUCLAR = [(39.92, 32.85), (39.94, 32.87), (39.90, 32.83), (39.93, 32.84)]

    def _merkez(self):
        import statistics
        return (statistics.mean(p[0] for p in self.SUCLAR),
                statistics.mean(p[1] for p in self.SUCLAR))

    def test_dragnet_tepe_merkeze_yakin(self):
        r = mi.cografi_profil(self.SUCLAR, hucre_km=0.5)
        d = mi.mekan.haversine_km(r["tepe"]["lat"], r["tepe"]["lon"], *self._merkez())
        self.assertLess(d, 1.5)  # tampon yok → merkeze yakın
        self.assertEqual(r["tepe"]["skor"], 1.0)  # normalize

    def test_rossmo_tampon_tepeyi_uzaklastirir(self):
        d = mi.cografi_profil(self.SUCLAR, hucre_km=0.5)
        b = mi.cografi_profil(self.SUCLAR, hucre_km=0.5, buffer_km=2.0)
        m = self._merkez()
        dd = mi.mekan.haversine_km(d["tepe"]["lat"], d["tepe"]["lon"], *m)
        db = mi.mekan.haversine_km(b["tepe"]["lat"], b["tepe"]["lon"], *m)
        self.assertGreater(db, dd)  # halka etkisi

    def test_az_nokta_reddi(self):
        self.assertIn("hata", mi.cografi_profil([(39.0, 32.0)]))

    def test_yuzey_dondurur(self):
        r = mi.cografi_profil(self.SUCLAR, hucre_km=0.5)
        self.assertTrue(len(r["yuzey"]) > 0)
        self.assertTrue(all(0 <= c["skor"] <= 1.0 for c in r["yuzey"]))


class TestEmergingHotspot(unittest.TestCase):
    SERILER = {
        "artan": [1, 2, 4, 7, 12, 20],
        "kalici": [15, 16, 14, 17, 15, 16],
        "tarihsel": [18, 16, 12, 5, 2, 1],
        "soguk": [0, 1, 0, 1, 0, 1],
    }

    def test_artan_yeni_sicak_nokta(self):
        r = mi.emerging_hotspot(self.SERILER)
        kat = {s["bolge"]: s["kategori"] for s in r["sonuclar"]}
        self.assertEqual(kat["artan"], "yeni sıcak nokta")

    def test_kalici_ve_tarihsel(self):
        r = mi.emerging_hotspot(self.SERILER)
        kat = {s["bolge"]: s["kategori"] for s in r["sonuclar"]}
        self.assertEqual(kat["kalici"], "kalıcı")
        self.assertEqual(kat["tarihsel"], "tarihsel")

    def test_esit_olmayan_uzunluk_reddi(self):
        self.assertIn("hata", mi.emerging_hotspot({"a": [1, 2, 3], "b": [1, 2]}))

    def test_az_donem_reddi(self):
        self.assertIn("hata", mi.emerging_hotspot({"a": [1, 2], "b": [3, 4]}))

    def test_mann_kendall_artan(self):
        r = mi._mann_kendall([1, 2, 3, 4, 5, 6])
        self.assertEqual(r["yon"], "artan")
        self.assertAlmostEqual(r["tau"], 1.0, places=2)


class TestKonsantrasyonDagilim(unittest.TestCase):
    def test_yogunlasma(self):
        r = mi.konsantrasyon_dagilim([10, 1, 1, 1], [30, 1, 1, 1])
        self.assertIn("YOĞUNLAŞMA", r["yorum"])
        self.assertGreater(r["gini_sonra"], r["gini_once"])

    def test_dagilma(self):
        r = mi.konsantrasyon_dagilim([10, 0, 0, 0], [10, 8, 8, 8])
        self.assertIn("DAĞILMA", r["yorum"])

    def test_artis_yoksa_not(self):
        r = mi.konsantrasyon_dagilim([10, 10], [5, 5])
        self.assertIn("artış yok", r["yorum"])

    def test_uzunluk_uyusmazligi(self):
        self.assertIn("hata", mi.konsantrasyon_dagilim([1, 2, 3], [1, 2]))


class TestEsitlik(unittest.TestCase):
    def test_tam_esit_gini_sifir(self):
        r = mi.esitlik([10, 10, 10, 10])
        self.assertAlmostEqual(r["gini"], 0.0, places=3)

    def test_yogunlasma_yuksek_gini(self):
        r = mi.esitlik([0, 0, 0, 100])
        self.assertGreater(r["gini"], 0.6)
        self.assertIn("yoğunlaşma", r["yorum"])

    def test_mrd_hesabi(self):
        r = mi.esitlik([2, 4, 6, 8])  # ort=5, (8-2)/5=1.2
        self.assertAlmostEqual(r["mrd"], 1.2, places=3)

    def test_bos_ve_sifir(self):
        self.assertIn("hata", mi.esitlik([]))
        self.assertEqual(mi.esitlik([0, 0, 0])["gini"], 0.0)


if __name__ == "__main__":
    unittest.main()
