# -*- coding: utf-8 -*-
"""
test_kiyas_v6.py — BMK v6 altyapısı (V12 bileşene özgü yayılım). ÖN-KAYIT GEREĞİ
gerçek araç çağrılmaz: üretecin kanal başına yayılımı, Poisson durumunun v4
üretecinin kendisi olduğu, ölçüt hesabı (sahte araçla) ve kilit.
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
for alt in ("kiyas", os.path.join("kiyas", "v3"), os.path.join("kiyas", "v4"), os.path.join("kiyas", "v6")):
    sys.path.insert(0, os.path.join(KOK, alt))
import uretec_v4  # noqa: E402
import uretec_v6  # noqa: E402
import kos_v6  # noqa: E402

with open(os.path.join(KOK, "kiyas", "v6", "vakalar", "v12_bilesen_yayilim.json"), encoding="utf-8") as f:
    V12 = json.load(f)
P = {s: uretec_v6.parametreler(V12, s) for s in kos_v6.SENARYOLAR}


def aylik(satirlar, kanal, yil):
    say = Counter(s["tarih"][:7] for s in satirlar if s["kanal"] == kanal and s["tarih"].startswith(yil))
    return [say.get(f"{yil}-{m:02d}", 0) for m in range(1, 13)]


def oran(senaryo, kanal, yil, n=40):
    aylar = [x for t in range(n) for x in aylik(uretec_v6.v12_kanallar(P[senaryo], t)[0], kanal, yil)]
    return statistics.fmean(aylar), statistics.variance(aylar) / statistics.fmean(aylar)


class Uretec(unittest.TestCase):
    def test_poisson_durumu_v4_ureteci(self):
        self.assertEqual(uretec_v6.v12_kanallar(P["guc_poisson"], 703), uretec_v4.v10_kanallar(P["guc_poisson"], 703))

    def test_kanal_basina_yayilim(self):
        ort, phi = oran("karma_surekli_nb", "karakol", "2024")
        self.assertAlmostEqual(ort, 40, delta=2)
        self.assertGreater(phi, 3.5)                     # k = 8 → ≈ 6
        ort, phi = oran("karma_surekli_nb", "cevrimici", "2025")
        self.assertAlmostEqual(ort, 12, delta=1)
        self.assertLess(phi, 1.6)                        # Poisson kanal
        ort, phi = oran("karma_yeni_nb", "cevrimici", "2025")
        self.assertGreater(phi, 6)                       # k = 1, λ = 12 → ≈ 13
        _, phi = oran("karma_yeni_nb", "karakol", "2024")
        self.assertLess(phi, 1.6)

    def test_determinizm_ve_gecersiz_k(self):
        s = "karma_ikisi_nb"
        self.assertEqual(uretec_v6.v12_kanallar(P[s], 5), uretec_v6.v12_kanallar(P[s], 5))
        for k in (0.5, 1.5):
            with self.assertRaises(ValueError):
                uretec_v6.v12_kanallar({**P[s], "yayilim_k": {"karakol": k}}, 1)

    def test_tohumlar(self):
        self.assertEqual(kos_v6.tohumlar(V12, "guc_yeni_nb"), list(range(701, 881)))
        self.assertEqual(kos_v6.tohumlar(V12, "karma_ikisi_nb"), list(range(701, 801)))


def ozet(kategori, birincil="tutuldu"):
    return {"kategori": kategori, "birincil": birincil, "rakip": "R-BILDIRIM", "rakipler": (),
            "onay": True, "bilinmeyen": True, "yasak_yok": True}


class OlcutHesabi(unittest.TestCase):
    def test_degerler(self):
        k = {s: [(ozet("KIRILGAN"), True)] * 2 for s in kos_v6.SENARYOLAR}
        k["guc_yeni_nb"] = [(ozet("DESTEKLENDİ"), True), (ozet("KIRILGAN"), True)]
        k["guc_poisson"] = [(ozet("DESTEKLENDİ"), True)] * 2
        k["karma_yeni_nb"] = [(ozet("DESTEKLENDİ"), True), (ozet("ÇEKİMSER", "sınanamadı"), False)]
        self.assertEqual(kos_v6.degerler_uret(k),
                         {"K12.1": 1.0, "K12.2": 1.0, "K12.3": 0.0, "K12.4": 1.0, "K12.5": 1.0,
                          "K12.6": 0.5, "K12.7": 1.0, "K12.8": 1.0})

    def test_iki_bilesen_p_gerekli(self):
        def sonuc(olcum):
            return {"hukum": {"rakipler": [{"kod": "R-BILDIRIM", "olcum": olcum}]}}
        self.assertTrue(kos_v6.yayilim_p_var(sonuc({"yayilim_p": 0.3, "yayilim_p_yeni": 0.02})))
        self.assertFalse(kos_v6.yayilim_p_var(sonuc({"yayilim_p": 0.3})))
        self.assertFalse(kos_v6.yayilim_p_var(sonuc({"yayilim_p": 0.3, "yayilim_p_yeni": None})))
        self.assertFalse(kos_v6.yayilim_p_var(None))

    def test_yok_sifir(self):
        yok = kos_v6.kos_v3.ozet_cikar(None)
        self.assertEqual(set(kos_v6.degerler_uret({s: [(yok, False)] for s in kos_v6.SENARYOLAR}).values()), {0.0})


class Kilit(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v6_")
        for yol in kos_v6.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v6.KOK, kos_v6.KILIT)
        kos_v6.KOK = self.gecici
        kos_v6.KILIT = os.path.join(self.gecici, "kiyas", "v6", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v6.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v6.KOK, kos_v6.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v6.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam(self):
        self.assertFalse(self._bozuk_mu())

    def test_kilit_dosyasi_veri_bekcisinden_gecer(self):
        # düz onaltılık özet bekçinin telefon kuralına takılabiliyordu (v6'da oldu)
        sys.path.insert(0, os.path.join(KOK, "betikler"))
        import veri_bekcisi
        with open(kos_v6.KILIT, encoding="utf-8") as f:
            self.assertEqual(veri_bekcisi.icerik_denetle(f.read().encode("utf-8")), [])
        self.assertEqual(veri_bekcisi.icerik_denetle(b'"x": "sha256:a5950123:45678abc"'), [])
        # eski biçim: bekçinin yakalaması gereken sentetik özet parçası — bekci:izin
        self.assertTrue(veri_bekcisi.icerik_denetle(b'"x": "a5950123456bcd"'))  # bekci:izin

    def test_esik_gevsetilirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v6", "vakalar", "v12_bilesen_yayilim.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][5]["esik"] = 0.6
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
