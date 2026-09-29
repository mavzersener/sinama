# -*- coding: utf-8 -*-
"""mekansal_istatistik: Global Moran's I, Getis-Ord Gi*, eşitlik testleri."""
import unittest

from sinama.cekirdek import mekansal_istatistik as mi


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

    # --- A4: çoklu test düzeltmesi (BMK v0 K1.6: rastgele desenlerin %70'inde
    # sahte "sıcak nokta" — düzeltmesiz %90 bandı karar veriyordu) ---
    def test_zayif_tek_hucre_coklu_testte_elenir(self):
        # |z|=1.8 düzeltmesiz %90'dır; 36 testte FDR'den geçmemeli
        k = mi.gi_siniflandir([1.8] + [0.0] * 35)
        self.assertEqual(set(k["tur"]), {"anlamsız"})
        self.assertLess(k["p"][0], 0.10)            # düzeltmesiz "anlamlı" olurdu

    def test_guclu_hucre_duzeltmeden_sonra_da_anlamli(self):
        k = mi.gi_siniflandir([4.0, -4.0] + [0.0] * 34)
        self.assertEqual(k["tur"][:2], ["sıcak", "soğuk"])
        self.assertEqual(set(k["tur"][2:]), {"anlamsız"})
        self.assertTrue(all(q >= p - 1e-9 for p, q in zip(k["p"], k["q"])))

    def test_cikti_coklu_test_ozeti_ve_tutarlilik(self):
        h = _grid(lambda i, j: 20 if (i < 2 and j < 2) else 1)
        r = mi.getis_ord(h, bant_km=2.5)
        ct = r["coklu_test"]
        self.assertEqual(ct["yontem"], "Benjamini-Hochberg FDR")
        self.assertEqual(ct["test_sayisi"], len(h))
        self.assertEqual(r["sicak"], sum(1 for s in r["sonuclar"] if s["tur"] == "sıcak"))
        self.assertGreaterEqual(ct["duzeltmesiz_sicak"], r["sicak"])
        self.assertTrue(all("p" in s and "q" in s for s in r["sonuclar"]))


class TestYerelMoran(unittest.TestCase):
    # A4.5: karar Benjamini–Hochberg FDR ile verilir (BMK v1 K4.2: düzeltmesiz
    # p<0,05 rastgele desenlerin %80'inde sahte küme/aykırı değer üretiyordu).
    # Eski iki test (2x2 köşe kümesi ve tek ada, 2–4 komşu) düzeltmesiz kararı
    # kodluyordu: az komşuda koşullu permütasyonun en uç p'si kombinatorik
    # olarak ~0,005'tir ve 36 testte FDR'yi geçemez. Senaryolar FDR altında
    # tespit edilebilir hâle getirildi; kaybolan küçük küme ödünleşim testinde.
    def test_yogun_komsulukta_kume_HH(self):
        h = _grid(lambda i, j: 20 if (2 <= i <= 4 and 2 <= j <= 4) else 1, boyut=7)
        r = mi.yerel_moran(h, bant_km=3.0)          # iç hücrelerde 8 komşu
        self.assertGreater(r["ozet"]["HH"], 0)
        hh = [s for s in r["sonuclar"] if s["kumeleme"] == "HH"]
        self.assertTrue(all(s["adet"] == 20 for s in hh))
        self.assertTrue(all(s["q"] <= r["coklu_test"]["q_esik"] for s in hh))

    def test_yuksek_ada_aykiri_HL(self):
        # haritanın yarısı yüksek: düşük yarıdaki tek yüksek hücrenin çevresinin
        # düşük olması gerçekten olağandışıdır (yalnız düşük haritada değildir)
        h = _grid(lambda i, j: 20 if j < 3 else (20 if (i == 3 and j == 5) else 1), boyut=7)
        r = mi.yerel_moran(h, bant_km=3.0)
        ada = [s for s in r["sonuclar"] if s["lat"] == round(39.0 + 3 * 0.02, 6)
               and s["lon"] == round(32.0 + 5 * 0.02, 6)][0]
        self.assertEqual(ada["kumeleme"], "HL")

    def test_odunlesim_kucuk_kume_yerelde_kaybolur_kanitta_gorunur(self):
        # 2x2 köşe kümesi, 2–4 komşu: FDR sonrası yerel küme YOK — ama kanıt
        # kaybolmaz: düzeltmesiz sayı raporlanır ve global Moran anlamlıdır.
        h = _grid(lambda i, j: 20 if (i < 2 and j < 2) else 1)
        r = mi.yerel_moran(h, bant_km=2.5)
        self.assertEqual(r["ozet"]["HH"], 0)
        self.assertGreaterEqual(r["coklu_test"]["duzeltmesiz_anlamli"], 1)
        self.assertLess(mi.global_moran(h, bant_km=2.5)["p"], 0.05)

    def test_rastgele_desende_sahte_kume_yok(self):
        import random
        rng = random.Random(11)
        h = _grid(lambda i, j: rng.randint(1, 5), boyut=7)
        r = mi.yerel_moran(h, bant_km=3.0)
        anlamli = sum(r["ozet"][t] for t in ("HH", "LL", "HL", "LH"))
        self.assertEqual(anlamli, 0, r["ozet"])

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
    # A4.6: sıcaklık dönem içi ANLAMLILIKLA (bolge_anomali: Poisson/NB + FDR),
    # trend Poisson skor testiyle (quasi-Poisson + FDR). Eski testler 4 bölgelik
    # göreli-yüzdelik davranışını ("her dönemin en yükseği sıcak") kodluyordu;
    # BMK v1'de bu tanım homojen veride %90 sahte sıcak nokta üretti.
    @staticmethod
    def _tek(seri):
        """20 sabit arka plan bölgesi + incelenen tek bölge X; X'in kategorisi."""
        s = {f"bg{i:02d}": [10] * len(seri) for i in range(20)}
        s["X"] = seri
        return next(r for r in mi.emerging_hotspot(s)["sonuclar"] if r["bolge"] == "X")

    def test_kategori_karar_tablosu(self):
        beklenen = {
            (10, 10, 11, 25, 35, 45): "yeni sıcak nokta",
            (30, 30, 30, 30, 30, 30): "kalıcı",
            (40, 38, 35, 10, 10, 10): "tarihsel",
            (30, 35, 42, 50, 60, 70): "yoğunlaşan",
            (70, 60, 50, 42, 35, 30): "sönen",
            (10, 10, 10, 30, 10, 10): "son dönemde sıcak",
            (30, 10, 10, 10, 10, 30): "sporadik",
            (10, 10, 10, 10, 10, 10): "sıcak değil",
        }
        for seri, kat in beklenen.items():
            self.assertEqual(self._tek(list(seri))["kategori"], kat, seri)

    def test_homojen_ve_esit_veride_sicak_nokta_yok(self):
        # eski eşitlik kusuru: eşik >= ile 25 eşit bölgenin HEPSİ "kalıcı" idi
        r = mi.emerging_hotspot({f"b{i}": [12] * 6 for i in range(25)})
        self.assertEqual(r["ozet"], {"sıcak değil": 25})

    def test_siniflandirma_boslugu_kapandi(self):
        # eski kusur: son yarıda sıcak + trend anlamsız → "sıcak değil"
        self.assertEqual(mi._ehsa_kategori([False, False, True, True], "durağan"),
                         "son dönemde sıcak")

    def test_karar_tablosu_eksiksiz(self):
        import itertools
        izinli = {"yeni sıcak nokta", "son dönemde sıcak", "yoğunlaşan", "sönen",
                  "kalıcı", "tarihsel", "sporadik", "sıcak değil"}
        for T in (3, 4, 5, 6):
            for desen in itertools.product([False, True], repeat=T):
                for yon in ("artan", "azalan", "durağan"):
                    kat = mi._ehsa_kategori(list(desen), yon)
                    self.assertIn(kat, izinli)
                    self.assertEqual(kat == "sıcak değil", not any(desen), (desen, yon))

    def test_poisson_trend_skoru(self):
        z = mi._poisson_trend([12, 19, 29, 41])["z"]
        self.assertGreater(z, 3.0)                       # 4 dönemde bile güçlü
        self.assertAlmostEqual(mi._poisson_trend([41, 29, 19, 12])["z"], -z)
        self.assertEqual(mi._poisson_trend([10, 10, 10, 10])["z"], 0.0)
        self.assertEqual(mi._poisson_trend([0, 0, 0])["z"], 0.0)

    def test_sinir_cok_sicak_noktada_orta_sicaklik_maskelenir(self):
        # BELGELENMİŞ SINIR: aynı dönemde birkaç yüksek bölge varsa aşırı
        # yayılım testi NB'ye geçer ve orta yükseklik (30'a karşı 10) sıcak
        # sayılmaz. Bu davranış değişirse bilinçli karar gerekir.
        s = {f"bg{i:02d}": [10] * 6 for i in range(20)}
        s.update({"kalici": [30] * 6, "a": [70] * 6, "b": [40] * 6})
        kat = {r["bolge"]: r["kategori"] for r in mi.emerging_hotspot(s)["sonuclar"]}
        self.assertEqual(kat["kalici"], "sıcak değil")

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
