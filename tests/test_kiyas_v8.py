# -*- coding: utf-8 -*-
"""
test_kiyas_v8.py — BMK v8 altyapısı (V14 NNI, V15 CUSUM). ÖN-KAYIT GEREĞİ gerçek
araç çağrılmaz: üretecin desen/seri yapısı, ölçüt hesabı (sahte özetlerle) ve kilit
(bekçiden geçen biçim dahil).
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
for alt in ("kiyas", os.path.join("kiyas", "v3"), os.path.join("kiyas", "v8")):
    sys.path.insert(0, os.path.join(KOK, alt))
import uretec  # noqa: E402
import uretec_v8  # noqa: E402
import kos_v8  # noqa: E402


def vaka(ad):
    with open(os.path.join(KOK, "kiyas", "v8", "vakalar", ad), encoding="utf-8") as f:
        return json.load(f)


V14, V15 = vaka("v14_nni.json"), vaka("v15_cusum.json")


class Uretec(unittest.TestCase):
    def test_desenler_kutuda_ve_belirlenimci(self):
        lat0, lat1, lon0, lon1 = uretec._kutu(41.0135, 29.0179, 3.0)
        for s in V14["senaryolar"]:
            p = uretec_v8.parametreler(V14, s)
            satirlar, g = uretec_v8.v14_noktalar(p, 7)
            self.assertEqual(len(satirlar), p["n"])
            self.assertEqual(g["desen"], p["desen"])
            self.assertEqual(satirlar, uretec_v8.v14_noktalar(p, 7)[0])
        csr = uretec_v8.v14_noktalar(uretec_v8.parametreler(V14, "csr"), 3)[0]
        self.assertTrue(all(lat0 <= s["lat"] <= lat1 and lon0 <= s["lon"] <= lon1 for s in csr))
        with self.assertRaises(ValueError):
            uretec_v8.v14_noktalar({**uretec_v8.parametreler(V14, "csr"), "desen": "yok"}, 1)

    def test_kume_ebeveyn_cevresinde_yogun(self):
        # kümelide en yakın komşu uzaklığı rastgeleden belirgin kısa
        def ort_eyk(s):
            p = uretec_v8.parametreler(V14, s)
            ortalamalar = []
            for t in range(1, 6):
                x = [(r["lat"] / uretec.KM_ENLEM, r["lon"] / uretec.KM_BOYLAM_41)
                     for r in uretec_v8.v14_noktalar(p, t)[0]]
                ortalamalar.append(statistics.fmean(
                    min(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 for b in x if b is not a)
                    for a in x))
            return statistics.fmean(ortalamalar)
        self.assertLess(ort_eyk("kume"), 0.9 * ort_eyk("csr"))

    def test_seri_artis_ve_yayilim(self):
        def aylik(s, t):
            c = Counter(r["tarih"][:7] for r in uretec_v8.v15_seri(uretec_v8.parametreler(V15, s), t)[0])
            return [c.get(f"{y}-{m:02d}", 0) for y in (2024, 2025) for m in range(1, 13)]
        once = [statistics.fmean(aylik("artis30", t)[:12]) for t in range(20)]
        sonra = [statistics.fmean(aylik("artis30", t)[12:]) for t in range(20)]
        self.assertAlmostEqual(statistics.fmean(sonra) / statistics.fmean(once), 1.3, delta=0.05)
        nb = [x for t in range(20) for x in aylik("sabit_nb", t)]
        self.assertGreater(statistics.variance(nb) / statistics.fmean(nb), 3.0)
        _, g = uretec_v8.v15_seri(uretec_v8.parametreler(V15, "artis30"), 1)
        self.assertIn(g["kesinti_gunu"], (365, 366))   # 2025-01-01, ilk kayıt 1–2 Ocak
        with self.assertRaises(ValueError):
            uretec_v8.v15_seri({**uretec_v8.parametreler(V15, "sabit"), "yayilim_k": 2.5}, 1)

    def test_tohumlar(self):
        self.assertEqual(kos_v8.tohumlar(V14, "csr"), list(range(10101, 10201)))
        self.assertEqual(kos_v8.tohumlar(V15, "artis50", 3), [10101, 10102, 10103])


class OlcutHesabi(unittest.TestCase):
    def test_v14(self):
        def o(nni, iddia=None, uyari=False):
            return {"nni": nni, "iddia": iddia, "uyari": uyari}
        k = {"csr": [o(1.05, "düzgün"), o(0.99), o(None)], "csr_kucuk": [o(1.0), o(0.8, "kümelenme")],
             "kume": [o(0.7, "kümelenme"), o(0.9)], "kume_kucuk": [o(0.7, "kümelenme")],
             "odak": [o(0.9, uyari=True), o(0.9)]}
        self.assertEqual(kos_v8.v14_degerler(k), {"K14.1": round(1 / 3, 4), "K14.2": 0.02, "K14.3": 0.5,
                                                  "K14.4": 0.5, "K14.5": 1.0, "K14.6": 0.5})
        k["csr"] = [o(0.95), o(0.97)]           # kümelenme yönündeki yan da mutlak sapmadır
        self.assertEqual(kos_v8.v14_degerler(k)["K14.2"], 0.04)
        k["csr"] = [o(None)]
        self.assertEqual(kos_v8.v14_degerler(k)["K14.2"], 1.0)

    def test_v14_ozet(self):
        yanit = {"sonuc": {"nni": 1.2, "p": 0.01}, "meta": {"uyarilar": ["NNI yerel odağı seyreltir"]}}
        self.assertEqual(kos_v8.nni_ozeti(yanit), {"nni": 1.2, "iddia": "düzgün", "uyari": True})
        self.assertEqual(kos_v8.nni_ozeti({"sonuc": {"nni": 0.9, "p": 0.2}, "meta": {"uyarilar": []}})["iddia"], None)
        self.assertEqual(kos_v8.nni_ozeti(None), {"nni": None, "iddia": None, "uyari": False})

    def test_v15(self):
        f = {"sabit": [None, 30, None, None], "sabit_nb": [None], "sabit_dusuk": [-200, None],
             "artis30": [-16, -15, 180, 181, None], "artis50": [90, 91], "artis30_nb": [None, -16, -15, 400]}
        self.assertEqual(kos_v8.v15_degerler(f), {"K15.1": 0.25, "K15.2": 0.0, "K15.3": 0.5,
                                                  "K15.4": 0.4, "K15.5": 0.5, "K15.6": 0.75})
        self.assertEqual(kos_v8.ilk_alarm_farki({"sonuc": [{"gun": 400}, {"gun": 500}]}, 366), 34)
        self.assertIsNone(kos_v8.ilk_alarm_farki({"sonuc": []}, 366))
        self.assertIsNone(kos_v8.ilk_alarm_farki(None, 366))


class Kilit(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v8_")
        for yol in kos_v8.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v8.KOK, kos_v8.KILIT)
        kos_v8.KOK = self.gecici
        kos_v8.KILIT = os.path.join(self.gecici, "kiyas", "v8", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v8.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v8.KOK, kos_v8.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v8.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_ve_bekciden_gecer(self):
        self.assertFalse(self._bozuk_mu())
        sys.path.insert(0, os.path.join(KOK, "betikler"))
        import veri_bekcisi
        with open(kos_v8.KILIT, encoding="utf-8") as f:
            self.assertEqual(veri_bekcisi.icerik_denetle(f.read().encode("utf-8")), [])

    def test_esik_gevsetilirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v8", "vakalar", "v15_cusum.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][0]["esik"] = 0.9
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
