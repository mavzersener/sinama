# -*- coding: utf-8 -*-
"""
test_kiyas_v9.py — BMK v9 altyapısı (V16 CUSUM kalibrasyonu). ÖN-KAYIT GEREĞİ gerçek
araç çağrılmaz: senaryoların v8 üreteciyle kurulması, ölçüt hesabı (sahte ilk alarm
farklarıyla, havuzlanmış kalibrasyon dahil) ve kilit (bekçiden geçen biçim dahil).
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for alt in ("kiyas", os.path.join("kiyas", "v3"), os.path.join("kiyas", "v8"), os.path.join("kiyas", "v9")):
    sys.path.insert(0, os.path.join(KOK, alt))
import uretec_v8  # noqa: E402
import kos_v9  # noqa: E402

V16 = kos_v9.vaka_oku()


class Yapi(unittest.TestCase):
    def test_senaryolar_v8_ile_ayni_tohumlar_yeni(self):
        with open(os.path.join(KOK, "kiyas", "v8", "vakalar", "v15_cusum.json"), encoding="utf-8") as f:
            v15 = json.load(f)
        self.assertEqual(set(V16["senaryolar"]), set(v15["senaryolar"]))
        for s in V16["senaryolar"]:
            self.assertEqual(uretec_v8.parametreler(V16, s), uretec_v8.parametreler(v15, s))
            self.assertEqual(kos_v9.kos_v8.tohumlar(V16, s), list(range(10201, 10401)))
        self.assertEqual([o["kimlik"] for o in V16["cekirdek_olcutleri"]],
                         [f"K16.{i}" for i in range(1, 8)])


class OlcutHesabi(unittest.TestCase):
    def test_degerler(self):
        f = {"sabit": [None, 30, None, None], "sabit_nb": [None, None], "sabit_dusuk": [-200, None],
             "artis30": [-16, -15, 180, 181, None], "artis50": [90, 91, -10], "artis30_nb": [None, -16, -15, 400]}
        self.assertEqual(kos_v9.v16_degerler(f), {"K16.1": 0.25, "K16.2": 0.0, "K16.3": 0.5, "K16.4": 0.4,
                                                  "K16.5": 0.6667, "K16.6": 0.75, "K16.7": 0.25})

    def test_havuz_yalniz_degisimsiz_senaryolar(self):
        f = {s: [None] * 4 for s in V16["senaryolar"]}
        f["artis30"] = [10] * 4
        self.assertEqual(kos_v9.v16_degerler(f)["K16.7"], 0.0)
        f["sabit_dusuk"] = [5, None, None, None]
        self.assertEqual(kos_v9.v16_degerler(f)["K16.7"], round(1 / 12, 4))


class Kilit(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v9_")
        for yol in kos_v9.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v9.KOK, kos_v9.KILIT)
        kos_v9.KOK = self.gecici
        kos_v9.KILIT = os.path.join(self.gecici, "kiyas", "v9", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v9.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v9.KOK, kos_v9.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v9.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_ve_bekciden_gecer(self):
        self.assertFalse(self._bozuk_mu())
        sys.path.insert(0, os.path.join(KOK, "betikler"))
        import veri_bekcisi
        with open(kos_v9.KILIT, encoding="utf-8") as f:
            self.assertEqual(veri_bekcisi.icerik_denetle(f.read().encode("utf-8")), [])

    def test_v8_uretec_degisirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v8", "uretec_v8.py")
        with open(yol, "a", encoding="utf-8") as f:
            f.write("\n# değişiklik\n")
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
