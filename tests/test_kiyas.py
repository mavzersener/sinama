# -*- coding: utf-8 -*-
"""
test_kiyas.py — BMK altyapısı (A3). ÖN-KAYIT GEREĞİ bu testler hiçbir
ölçüm koşmaz (araç çağırmaz): üreteçlerin determinizmini, gerçeğin
sağlamlığını, veriye gerçek sızmadığını ve kilidin kurcalamayı yakaladığını
sınar. Ölçüm sonucu görmeden eşik ayarlanmaz.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
import uretec  # noqa: E402
import kos  # noqa: E402


def vaka(ad):
    """Vaka spesifikasyonunu okur."""
    with open(os.path.join(KOK, "kiyas", "vakalar", ad), encoding="utf-8") as f:
        return json.load(f)


P1 = vaka("v1_kumelenme.json")["uretec"]["parametreler"]
P2 = vaka("v2_bildirim.json")["uretec"]["parametreler"]
P3 = vaka("v3_seri.json")["uretec"]["parametreler"]


class Determinizm(unittest.TestCase):
    def test_rastgele_kaynak_surumden_bagimsiz(self):
        # random.Random(1).random() yıllardır bu değerdir; değişirse Python
        # tohumlama davranışı değişmiş demektir ve kayıtlı sonuçlar bayatlar.
        self.assertEqual(uretec.Tohum(1).u(), 0.13436424411240122)

    def test_ayni_tohum_ayni_veri(self):
        self.assertEqual(uretec.v1_kumelenme(P1, 7, "odakli"), uretec.v1_kumelenme(P1, 7, "odakli"))
        self.assertEqual(uretec.v2_bildirim(P2, 7), uretec.v2_bildirim(P2, 7))
        self.assertEqual(uretec.v3_seri(P3, 7), uretec.v3_seri(P3, 7))
        self.assertNotEqual(uretec.v1_kumelenme(P1, 7, "csr"), uretec.v1_kumelenme(P1, 8, "csr"))


class GercekSaglamligi(unittest.TestCase):
    def test_v1_odak_gercekten_var_ve_csr_kutuda(self):
        satirlar, g = uretec.v1_kumelenme(P1, 3, "odakli")
        olat, olon = g["odak"]
        yakin = sum(1 for s in satirlar if kos.km(s["lat"], s["lon"], olat, olon) <= 0.45)
        self.assertEqual(len(satirlar), P1["n"])
        self.assertGreaterEqual(yakin, 0.9 * g["n_odak"])
        csr, g2 = uretec.v1_kumelenme(P1, 3, "csr")
        self.assertEqual(g2["n_odak"], 0)
        lat0, lat1, lon0, lon1 = uretec._kutu(P1["merkez_lat"], P1["merkez_lon"], P1["kenar_km"])
        self.assertTrue(all(lat0 <= s["lat"] <= lat1 and lon0 <= s["lon"] <= lon1 for s in csr))

    def test_v2_yeni_kanal_yalniz_kesintiden_sonra(self):
        satirlar, g = uretec.v2_bildirim(P2, 3)
        self.assertEqual(g["kesinti_tarihi"], "2025-01-01")
        self.assertTrue(all(s["tarih"] >= g["kesinti_tarihi"]
                            for s in satirlar if s["kanal"] == "cevrimici"))
        self.assertTrue(any(s["kanal"] == "cevrimici" for s in satirlar))

    def test_v3_gruplar_ve_serinin_uzay_zaman_yakinligi(self):
        satirlar, g = uretec.v3_seri(P3, 3)
        say = {}
        for grup in g["grup"].values():
            say[grup] = say.get(grup, 0) + 1
        self.assertEqual(say, {"seri": 5, "ortak_mo": 20, "diger": 35})
        seri = [s for s in satirlar if s["id"] in g["seri"]]
        for a in seri:
            for b in seri:
                self.assertLessEqual(kos.km(a["lat"], a["lon"], b["lat"], b["lon"]), 0.75)


class SizintiYok(unittest.TestCase):
    """Gerçek veriye yazılırsa A5'te dil modeli cevabı veriden okur."""

    def test_alanlar_gercegi_tasimaz(self):
        v1, _ = uretec.v1_kumelenme(P1, 5, "odakli")
        v2, _ = uretec.v2_bildirim(P2, 5)
        v3, _ = uretec.v3_seri(P3, 5)
        self.assertTrue(all(set(s) <= {"id", "lat", "lon", "tarih"} for s in v1))
        self.assertTrue(all(set(s) <= {"id", "tarih", "kanal", "yil"} for s in v2))
        self.assertTrue(all(set(s) <= {"id", "mo", "lat", "lon", "tarih"} for s in v3))

    def test_satir_sirasi_gercegi_ele_vermez(self):
        satirlar, g = uretec.v1_kumelenme(P1, 5, "odakli")
        olat, olon = g["odak"]
        bas = satirlar[:g["n_odak"]]
        yakin = sum(1 for s in bas if kos.km(s["lat"], s["lon"], olat, olon) <= 0.45)
        self.assertLess(yakin, 0.8 * len(bas), "odak noktaları hâlâ listenin başında")
        v3, g3 = uretec.v3_seri(P3, 5)
        ilk5 = [s["id"] for s in v3[:5]]
        self.assertNotEqual(sorted(ilk5), sorted(g3["seri"]), "seri kayıtları hâlâ başta")


class OnKayitKilidi(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_")
        for yol in kos.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos.KOK, kos.KILIT)
        kos.KOK = self.gecici
        kos.KILIT = os.path.join(self.gecici, "kiyas", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos.KOK, kos.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def test_sagam_kilit_gecer_ve_crlf_bozmaz(self):
        self.assertEqual(kos.kilit_dogrula()["surum"], "v0")
        yol = os.path.join(self.gecici, "kiyas", "uretec.py")
        with open(yol, "rb") as f:
            ham = f.read()
        with open(yol, "wb") as f:
            f.write(ham.replace(b"\n", b"\r\n"))
        self.assertEqual(kos.kilit_dogrula()["surum"], "v0")

    def test_esik_degisirse_olcum_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "vakalar", "v3_seri.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][1]["esik"] = 0.01   # sonucu görüp eşiği düşürmek
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                with self.assertRaises(SystemExit) as c:
                    kos.kilit_dogrula()
            finally:
                sys.stderr = eski_err
        self.assertEqual(c.exception.code, 2)

    def test_kilit_ikinci_kez_yazilamaz(self):
        with self.assertRaises(SystemExit):
            kos.kilitle()


if __name__ == "__main__":
    unittest.main()
