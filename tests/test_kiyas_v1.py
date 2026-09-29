# -*- coding: utf-8 -*-
"""
test_kiyas_v1.py — BMK v1 altyapısı (A4). ÖN-KAYIT GEREĞİ ölçüm koşmaz (araç
çağırmaz): yeni üreteçlerin determinizmi, gerçeğin sağlamlığı, veriye gerçek
sızmaması ve v1 kilidinin (v0 bağımlılıkları dahil) kurcalamayı yakalaması.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v1"))
import uretec_v1  # noqa: E402
import kos_v1  # noqa: E402


def vaka(ad):
    """v1 vaka spesifikasyonunu okur."""
    with open(os.path.join(KOK, "kiyas", "v1", "vakalar", ad), encoding="utf-8") as f:
        return json.load(f)


P5 = vaka("v5_yukselen.json")["uretec"]["parametreler"]
P6 = vaka("v6_anomali.json")["uretec"]["parametreler"]


def bolge_donem_sayilari(satirlar, p):
    """Gerçeğin sağlamlığı için bölge×dönem sayımı (araç değil, doğrudan)."""
    import datetime
    bas = datetime.date.fromisoformat(p["baslangic"])
    say = {}
    for s in satirlar:
        d = (datetime.date.fromisoformat(s["tarih"]) - bas).days // p["donem_gun"]
        say.setdefault(s["bolge"], [0] * p["donem_sayisi"])[d] += 1
    return say


class Determinizm(unittest.TestCase):
    def test_ayni_tohum_ayni_veri(self):
        self.assertEqual(uretec_v1.v5_yukselen(P5, 7, "artan"), uretec_v1.v5_yukselen(P5, 7, "artan"))
        self.assertEqual(uretec_v1.v6_anomali(P6, 7, "anomali"), uretec_v1.v6_anomali(P6, 7, "anomali"))
        self.assertNotEqual(uretec_v1.v6_anomali(P6, 7, "homojen"), uretec_v1.v6_anomali(P6, 8, "homojen"))


class GercekSaglamligi(unittest.TestCase):
    def test_v5_artan_bolge_gercekten_artiyor(self):
        satirlar, g = uretec_v1.v5_yukselen(P5, 3, "artan")
        seri = bolge_donem_sayilari(satirlar, P5)[g["artan"]]
        self.assertGreater(seri[-1], 2 * seri[0])
        self.assertEqual(uretec_v1.v5_yukselen(P5, 3, "homojen")[1]["artan"], None)
        self.assertEqual(len(bolge_donem_sayilari(satirlar, P5)), P5["bolge_sayisi"])

    def test_v6_anomali_bolgesi_ayrisiyor(self):
        satirlar, g = uretec_v1.v6_anomali(P6, 3, "anomali")
        say = {}
        for s in satirlar:
            say[s["bolge"]] = say.get(s["bolge"], 0) + 1
        digerleri = [n for b, n in say.items() if b != g["anomali"]]
        self.assertGreater(say[g["anomali"]], max(digerleri))


class SizintiYok(unittest.TestCase):
    def test_alanlar_ve_adlar_gercegi_tasimaz(self):
        v5, g5 = uretec_v1.v5_yukselen(P5, 5, "artan")
        v6, g6 = uretec_v1.v6_anomali(P6, 5, "anomali")
        self.assertTrue(all(set(s) <= {"id", "bolge", "tarih"} for s in v5))
        self.assertTrue(all(set(s) <= {"id", "bolge"} for s in v6))
        adlar = {s["bolge"] for s in v5}
        self.assertTrue(all(a.startswith("B") and a[1:].isdigit() for a in adlar))
        # satır sırası artan bölgeyi başa koymaz (tarihe göre sıralı)
        self.assertEqual(v5, sorted(v5, key=lambda s: (s["tarih"], s["bolge"])))


class V1Kilidi(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v1_")
        for yol in kos_v1.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v1.KOK, kos_v1.KILIT)
        kos_v1.KOK = self.gecici
        kos_v1.KILIT = os.path.join(self.gecici, "kiyas", "v1", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v1.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v1.KOK, kos_v1.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v1.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_kilit_gecer(self):
        self.assertFalse(self._bozuk_mu())

    def test_v1_esigi_degisirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v1", "vakalar", "v6_anomali.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][1]["esik"] = 0.9   # sonucu görüp eşiği gevşetmek
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())

    def test_v0_bagimliligi_degisirse_de_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "uretec.py")
        with open(yol, "a", encoding="utf-8") as f:
            f.write("\n# sonradan değişiklik\n")
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
