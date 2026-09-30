# -*- coding: utf-8 -*-
"""
test_kiyas_v5.py — BMK v5 altyapısı (V11 yayılım çarpanı). ÖN-KAYIT GEREĞİ
gerçek araç çağrılmaz: Poisson senaryolarının v4 üretecinin kendisi olduğu,
NB üretecinin ortalamayı koruyup aşırı yayılım ürettiği, ölçüt hesabının sahte
araçla doğruluğu ve kilidin kurcalamayı yakalaması.
"""
import json
import os
import shutil
import statistics
import sys
import tempfile
import unittest
from collections import Counter

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for alt in ("kiyas", os.path.join("kiyas", "v3"), os.path.join("kiyas", "v4"), os.path.join("kiyas", "v5")):
    sys.path.insert(0, os.path.join(KOK, alt))
import uretec_v4  # noqa: E402
import uretec_v5  # noqa: E402
import kos_v5  # noqa: E402

with open(os.path.join(KOK, "kiyas", "v5", "vakalar", "v11_yayilim.json"), encoding="utf-8") as f:
    V11 = json.load(f)
P = {s: uretec_v5.parametreler(V11, s) for s in kos_v5.SENARYOLAR}


def aylik_karakol(satirlar, once):
    say = Counter(s["tarih"][:7] for s in satirlar if s["kanal"] == "karakol"
                  and (s["tarih"] < "2025-01-01") == once)
    return [say.get(f"{2024 if once else 2025}-{m:02d}", 0) for m in range(1, 13)]


class Uretec(unittest.TestCase):
    def test_poisson_senaryolari_v4_ureteci(self):
        for s in ("kismi_artefakt", "karma", "gercek_artis_kucuk_kanal"):
            self.assertEqual(uretec_v5.v11_kanallar(P[s], 503), uretec_v4.v10_kanallar(P[s], 503))

    def test_nb_determinizm_ortalama_ve_yayilim(self):
        s = "saf_artefakt_nb"
        self.assertEqual(uretec_v5.v11_kanallar(P[s], 7), uretec_v5.v11_kanallar(P[s], 7))
        aylar = [x for t in range(40) for x in aylik_karakol(uretec_v5.v11_kanallar(P[s], t)[0], True)]
        ort = statistics.fmean(aylar)
        self.assertAlmostEqual(ort, 40, delta=2.0)
        self.assertGreater(statistics.variance(aylar) / ort, 3.5)      # beklenen ≈ 1 + 40/8 = 6
        pois = [x for t in range(40) for x in aylik_karakol(uretec_v4.v10_kanallar(P["karma"], t)[0], True)]
        self.assertLess(statistics.variance(pois) / statistics.fmean(pois), 1.6)

    def test_nb_yalniz_kesinti_duzeni(self):
        with self.assertRaises(ValueError):
            uretec_v5.v11_kanallar({**P["saf_artefakt_nb"], "cevrimici": "bastan"}, 1)

    def test_tohumlar(self):
        self.assertEqual(kos_v5.tohumlar(V11, "gercek_artis_kucuk_kanal"), list(range(501, 701)))
        self.assertEqual(kos_v5.tohumlar(V11, "karma_nb"), list(range(501, 561)))
        self.assertEqual(kos_v5.tohumlar(V11, "karma_nb", 2), [501, 502])


def ozet(kategori, birincil="tutuldu"):
    return {"kategori": kategori, "birincil": birincil, "rakip": "R-BILDIRIM", "rakipler": (),
            "onay": True, "bilinmeyen": True, "yasak_yok": True}


class OlcutHesabi(unittest.TestCase):
    def test_degerler_ve_kosullu_rapor(self):
        k = {s: [(ozet("KIRILGAN"), True)] * 2 for s in kos_v5.SENARYOLAR}
        k["gercek_artis_kucuk_kanal"] = [(ozet("DESTEKLENDİ"), True), (ozet("KIRILGAN"), True)]
        k["karma_nb"] = [(ozet("DESTEKLENDİ"), True), (ozet("ÇEKİMSER", "sınanamadı"), False)]
        k["gercek_artis_kucuk_kanal_nb"] = [(ozet("KIRILGAN"), False)]   # ek; K11.7 dışında
        d = kos_v5.degerler_uret(k)
        self.assertEqual(d, {"K11.1": 1.0, "K11.2": 1.0, "K11.3": 0.5, "K11.4": 1.0,
                             "K11.5": 1.0, "K11.6": 0.0, "K11.7": 1.0})

    def test_yok_hic_dogru_sayilmaz(self):
        yok = kos_v5.kos_v3.ozet_cikar(None)
        k = {s: [(yok, False)] * 2 for s in kos_v5.SENARYOLAR}
        self.assertEqual(set(kos_v5.degerler_uret(k).values()), {0.0})

    def test_yayilim_p_sayisal_olmali(self):
        def sonuc(olcum):
            return {"hukum": {"rakipler": [{"kod": "R-BILDIRIM", "olcum": olcum}]}}
        self.assertTrue(kos_v5.yayilim_p_var(sonuc({"yayilim_p": 0.3})))
        self.assertFalse(kos_v5.yayilim_p_var(sonuc({"yayilim": 2.0})))
        self.assertFalse(kos_v5.yayilim_p_var(sonuc({"yayilim_p": False})))
        self.assertFalse(kos_v5.yayilim_p_var(None))


class Uctan(unittest.TestCase):
    def setUp(self):
        self.eski = kos_v5.kos.arac

    def tearDown(self):
        kos_v5.kos.arac = self.eski

    def test_sahte_arac(self):
        cagri = []

        def sahte(ad, satirlar, **arg):
            cagri.append(ad)
            return {"sonuc": {"hipotezler": [{"tur": "BILINMEYEN"}],
                              "hukum": {"kategori": "DESTEKLENDİ", "birincil_ongoru": "tutuldu",
                                        "en_guclu_rakip": None, "insan_onayi_gerekir": True,
                                        "rakipler": [{"kod": "R-BILDIRIM", "durum": "dışlandı",
                                                      "olcum": {"yayilim_p": 0.4}}]}}, "meta": {}}
        kos_v5.kos.arac = sahte
        _, olcutler, ek = kos_v5.v11(adet=2)
        d = {o["kimlik"]: o["deger"] for o in olcutler}
        self.assertEqual(d, {"K11.1": 0.0, "K11.2": 0.0, "K11.3": 1.0, "K11.4": 0.0,
                             "K11.5": 0.0, "K11.6": 0.0, "K11.7": 1.0})
        self.assertEqual(len(cagri), 7 * 2)
        self.assertEqual(ek["nb_guc_destek_orani"], 1.0)


class Kilit(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v5_")
        for yol in kos_v5.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v5.KOK, kos_v5.KILIT)
        kos_v5.KOK = self.gecici
        kos_v5.KILIT = os.path.join(self.gecici, "kiyas", "v5", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v5.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v5.KOK, kos_v5.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v5.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_kilit_gecer(self):
        self.assertFalse(self._bozuk_mu())

    def test_v4_bagimliligi_degisirse_reddedilir(self):
        with open(os.path.join(self.gecici, "kiyas", "v4", "uretec_v4.py"), "a", encoding="utf-8") as f:
            f.write("\n# sonradan değişiklik\n")
        self.assertTrue(self._bozuk_mu())

    def test_esik_gevsetilirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v5", "vakalar", "v11_yayilim.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][2]["esik"] = 0.70
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
