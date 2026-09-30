# -*- coding: utf-8 -*-
"""
test_kiyas_v7.py — BMK v7 altyapısı (V13 ETKİ). ÖN-KAYIT GEREĞİ gerçek araç
çağrılmaz: üretecin bölge/senaryo yapısı, argüman çözümü, ölçüt hesabı (sahte
özetlerle) ve kilit (bekçiden geçen biçim dahil).
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
for alt in ("kiyas", os.path.join("kiyas", "v3"), os.path.join("kiyas", "v4"), os.path.join("kiyas", "v7")):
    sys.path.insert(0, os.path.join(KOK, alt))
import uretec_v7  # noqa: E402
import kos_v7  # noqa: E402

with open(os.path.join(KOK, "kiyas", "v7", "vakalar", "v13_etki.json"), encoding="utf-8") as f:
    V13 = json.load(f)
P = {s: uretec_v7.parametreler(V13, s) for s in kos_v7.SENARYOLAR}


def ortalama(senaryo, bolge, once, n=30):
    toplam = 0
    for t in range(n):
        s, _ = uretec_v7.v13_bolgeler(P[senaryo], t)
        toplam += sum(1 for x in s if x["bolge"] == bolge and (x["tarih"] < "2025-01-01") == once)
    return toplam / (n * 12)


class Uretec(unittest.TestCase):
    def test_senaryo_yapisi(self):
        self.assertAlmostEqual(ortalama("gercek_etki", "M", False) / ortalama("gercek_etki", "M", True), 0.65, delta=0.04)
        self.assertAlmostEqual(ortalama("gercek_etki", "K", False) / ortalama("gercek_etki", "K", True), 1.0, delta=0.04)
        self.assertAlmostEqual(ortalama("genel_dusus", "K", False) / ortalama("genel_dusus", "K", True), 0.65, delta=0.04)
        self.assertAlmostEqual(ortalama("yer_degistirme", "T", False) / ortalama("yer_degistirme", "T", True), 1.56, delta=0.08)

    def test_zirve_yalniz_on_iki_ay(self):
        say = Counter()
        for t in range(30):
            for x in uretec_v7.v13_bolgeler(P["ortalamaya_donus"], t)[0]:
                if x["bolge"] == "M" and x["tarih"] < "2025-01-01":
                    say[int(x["tarih"][5:7])] += 1
        zirve = statistics.fmean(say[a] for a in (10, 11, 12)) / 30
        temel = statistics.fmean(say[a] for a in range(1, 10)) / 30
        self.assertAlmostEqual(zirve / temel, 1.8, delta=0.12)

    def test_nb_yayilim_ve_determinizm(self):
        aylar = []
        for t in range(30):
            s, _ = uretec_v7.v13_bolgeler(P["etkisiz_nb"], t)
            c = Counter(x["tarih"][:7] for x in s if x["bolge"] == "M")
            aylar += [c.get(f"2024-{a:02d}", 0) for a in range(1, 13)]
        self.assertGreater(statistics.variance(aylar) / statistics.fmean(aylar), 3.5)
        self.assertEqual(uretec_v7.v13_bolgeler(P["etkisiz_nb"], 3), uretec_v7.v13_bolgeler(P["etkisiz_nb"], 3))
        with self.assertRaises(ValueError):
            uretec_v7.v13_bolgeler({**P["etkisiz_nb"], "yayilim_k": {"M": 1.5}}, 1)

    def test_argumanlar_ve_tohumlar(self):
        cv = kos_v7.cagri_vakasi(V13)
        self.assertEqual(cv["senaryolar"]["gercek_etki"]["argumanlar"]["kontrol"], "K")
        self.assertNotIn("kontrol", cv["senaryolar"]["kontrolsuz"]["argumanlar"])
        self.assertNotIn("tampon", cv["senaryolar"]["kontrolsuz"]["argumanlar"])
        self.assertEqual(kos_v7.tohumlar(V13, "gercek_etki"), list(range(10001, 10101)))


def ozet(kategori, birincil="tutuldu", rakip=None):
    return {"kategori": kategori, "birincil": birincil, "rakip": rakip, "rakipler": (),
            "onay": True, "bilinmeyen": True, "yasak_yok": True}


class OlcutHesabi(unittest.TestCase):
    def test_degerler(self):
        k = {s: [ozet("BELİRSİZ", "belirsiz")] * 2 for s in kos_v7.SENARYOLAR}
        k["gercek_etki"] = [ozet("DESTEKLENDİ"), ozet("BELİRSİZ", "belirsiz")]
        k["ortalamaya_donus"] = [ozet("BELİRSİZ", rakip="R-ORTALAMAYA-DONUS"),
                                 ozet("BELİRSİZ", rakip="R-YER-DEGISTIRME"), ozet("BELİRSİZ", "belirsiz")]
        k["yer_degistirme"] = [ozet("BELİRSİZ", rakip="R-YER-DEGISTIRME"), ozet("DESTEKLENDİ"),
                               ozet("BELİRSİZ", "belirsiz", rakip="R-YER-DEGISTIRME")]
        k["kontrolsuz"] = [ozet("KIRILGAN", rakip="R-ESZAMANLI"), ozet("DESTEKLENDİ"),
                           ozet("BELİRSİZ", "belirsiz")]
        self.assertEqual(kos_v7.degerler_uret(k),
                         {"K13.1": 0.5, "K13.2": 1.0, "K13.3": 1.0, "K13.4": 0.5, "K13.5": round(2 / 3, 4),
                          "K13.6": 0.5, "K13.7": 0.5, "K13.8": 1.0, "K13.9": 1.0})

    def test_yok_sifir(self):
        yok = kos_v7.kos_v3.ozet_cikar(None)
        self.assertEqual(set(kos_v7.degerler_uret({s: [yok] for s in kos_v7.SENARYOLAR}).values()), {0.0})


class Kilit(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v7_")
        for yol in kos_v7.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v7.KOK, kos_v7.KILIT)
        kos_v7.KOK = self.gecici
        kos_v7.KILIT = os.path.join(self.gecici, "kiyas", "v7", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v7.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v7.KOK, kos_v7.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v7.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_ve_bekciden_gecer(self):
        self.assertFalse(self._bozuk_mu())
        sys.path.insert(0, os.path.join(KOK, "betikler"))
        import veri_bekcisi
        with open(kos_v7.KILIT, encoding="utf-8") as f:
            self.assertEqual(veri_bekcisi.icerik_denetle(f.read().encode("utf-8")), [])

    def test_esik_gevsetilirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v7", "vakalar", "v13_etki.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][6]["esik"] = 0.5
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
