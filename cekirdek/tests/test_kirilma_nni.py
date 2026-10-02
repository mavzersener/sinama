# -*- coding: utf-8 -*-
"""
test_kirilma_nni.py — A4.15: kalibre kalıcı artış alarmı (kendinden başlayan CUSUM)
ve NNI'nın dürüst varsayılanı (Donnelly + yansız sınır kutusu). Veriler sabit
tohumlu, deterministik ve sentetiktir.
"""
import datetime
import math
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama.arayuz import sunucu  # noqa: E402
from sinama.cekirdek import ileri, mekan  # noqa: E402

BAS = datetime.date(2024, 1, 1)
_ESKI_LOG = os.environ.get("SINAMA_LOG_DIR")


def setUpModule():
    """Araç çağrıları keşif oturumu yazar: geçici dizine (yalıtılmış koşuda da)."""
    os.environ["SINAMA_LOG_DIR"] = tempfile.mkdtemp(prefix="kirilma_nni_")


def tearDownModule():
    """Ortamı geri yükler."""
    if _ESKI_LOG is None:
        os.environ.pop("SINAMA_LOG_DIR", None)
    else:
        os.environ["SINAMA_LOG_DIR"] = _ESKI_LOG


def poisson(r, lam):
    """Knuth Poisson çekilişi."""
    esik, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= r.random()
        if p <= esik:
            return k
        k += 1


def seri(tohum, aylik, carpan=1.0, kesinti=12, gama_k=None, ay=24):
    """Ay başına Poisson(λ) olay günü; kesinti ayından sonra λ × carpan."""
    r = random.Random(tohum)
    gunler = []
    for i in range(ay):
        y, m = 2024 + i // 12, i % 12 + 1
        gun_sayisi = (datetime.date(y + m // 12, m % 12 + 1, 1) - datetime.date(y, m, 1)).days
        lam = aylik * (carpan if i >= kesinti else 1.0)
        if gama_k:
            lam *= r.gammavariate(gama_k, 1 / gama_k)
        gunler += [datetime.date(y, m, 1 + int(r.random() * gun_sayisi)) for _ in range(poisson(r, lam))]
    return sorted(gunler)


class TestKirilmaCusum(unittest.TestCase):
    def test_degisimsiz_seride_alarm_yok(self):
        alarmlar = [ileri.kirilma_cusum(seri(t, 40))[0] for t in range(10)]
        self.assertLessEqual(sum(1 for a in alarmlar if a), 1)

    def test_kalici_artista_kesintiden_sonra_alarm(self):
        kesinti = (datetime.date(2025, 1, 1) - BAS).days
        for t in range(5):
            gunler = seri(t, 40, carpan=1.6)
            alarmlar, donem = ileri.kirilma_cusum(gunler)
            self.assertTrue(alarmlar, t)
            self.assertEqual(donem, "hafta")
            ilk = alarmlar[0]
            self.assertGreaterEqual(ilk["gun"] - (gunler[0] - BAS).days, kesinti - 15)
            self.assertEqual(set(ilk), {"gun", "tarih", "donem", "cusum", "esik"})
            self.assertGreater(ilk["cusum"], ilk["esik"])
            # gün alanı ilk kayıttan itibaren dönemin son günüdür
            self.assertEqual(ilk["gun"], (datetime.date.fromisoformat(ilk["tarih"]) - gunler[0]).days)

    def test_aylar_arasi_heterojenlik_ayliga_gecer(self):
        donemler = [ileri.kirilma_cusum(seri(t, 40, gama_k=4))[1] for t in range(5)]
        self.assertEqual(donemler.count("ay"), 5)
        self.assertEqual(ileri.kirilma_cusum(seri(1, 40), donem="ay")[1], "ay")

    def test_ay_yayilim_testi(self):
        self.assertEqual(ileri.ay_yayilim_p([40] * 24), 1.0)          # hiç fark yok
        self.assertLess(ileri.ay_yayilim_p([20, 60] * 12), 0.01)       # aylar arası salınım
        # tek basamak (kalıcı artış) yayılım sayılmaz
        self.assertGreater(ileri.ay_yayilim_p([40] * 12 + [52] * 12), 0.05)
        self.assertEqual(ileri.ay_yayilim_p([10] * 12), 1.0)          # küçük λ: Knuth yolu
        self.assertLess(ileri.ay_yayilim_p([2, 18] * 6), 0.01)
        self.assertIsNone(ileri.ay_yayilim_p([5, 5]))
        self.assertIsNone(ileri.ay_yayilim_p([0, 0, 0]))

    def test_esik_kalibrasyonu(self):
        h05, h01 = ileri._cusum_esigi(50, 0.5, 0.05), ileri._cusum_esigi(50, 0.5, 0.01)
        self.assertLess(h05, h01)
        self.assertLess(ileri._cusum_esigi(20, 0.5, 0.05), h05)   # uzun seri → yüksek eşik
        self.assertEqual(h05, ileri._cusum_esigi(50, 0.5, 0.05))   # belirlenimci
        # bağımsız N(0,1) adımlarda seri düzeyinde yanlış alarm ≈ alfa
        r = random.Random(7)
        alarm = 0
        for _ in range(1000):
            s = 0.0
            for _ in range(50):
                s = max(0.0, s + r.gauss(0, 1) - 0.5)
                if s > h05:
                    alarm += 1
                    break
        self.assertAlmostEqual(alarm / 1000, 0.05, delta=0.02)

    def test_kendinden_standartlastirma_elle(self):
        from statistics import NormalDist
        from sinama.cekirdek.hipotez import t_cdf
        z = ileri._kendinden_z([10, 12, 8, 10, 14], 3)
        self.assertEqual(len(z), 2)
        self.assertEqual(z[0], 0.0)                       # 10, önceki ortalamaya eşit
        sd = (8 / 3) ** 0.5                                 # [10, 12, 8, 10] örneklem sapması
        tt = (14 - 10) / (sd * (1 + 1 / 4) ** 0.5)
        self.assertAlmostEqual(z[1], NormalDist().inv_cdf(t_cdf(tt, 3)), places=12)
        self.assertEqual(ileri._kendinden_z([5, 5, 5, 9], 3), [0.0])   # sıfır sapma

    def test_anscombe_donusumu_uygulanir(self):
        # A4.16: sayımlar standartlaştırmadan önce 2√(x + 3/8) ile dönüştürülür (BMK v9)
        gunler = seri(3, 40, carpan=1.6)
        alarm = ileri.kirilma_cusum(gunler, donem="hafta")[0][0]
        sayim, _ = ileri._donem_sayimlari(gunler, "hafta")
        z = ileri._kendinden_z([2 * math.sqrt(c + 3 / 8) for c in sayim], 8)
        h = ileri._cusum_esigi(len(z), 0.5, 0.05)
        s = 0.0
        for d in z:
            s = max(0.0, s + d - 0.5)
            if s > h:
                break
        self.assertEqual(alarm["cusum"], round(s, 3))

    def test_isinma_doneminde_izlenmez(self):
        # 5. haftadaki sıçrama ısınma (8 hafta) içinde: alarm yok; aynı sıçrama 30. haftada: alarm
        def haftalik(sayimlar):
            return [BAS + datetime.timedelta(days=7 * i + j % 7) for i, c in enumerate(sayimlar)
                    for j in range(c)]
        taban = [9, 10, 8, 11, 10, 9, 10, 11, 9, 10] * 6
        erken = list(taban)
        erken[4] = 60
        gec = list(taban)
        gec[30] = 60
        self.assertEqual(ileri.kirilma_cusum(haftalik(erken), donem="hafta")[0], [])
        self.assertTrue(ileri.kirilma_cusum(haftalik(gec), donem="hafta")[0])
        self.assertEqual(ileri.KIRILMA_ISINMA, {"hafta": 8, "ay": 6})

    def test_kisa_ve_bos_seri(self):
        self.assertEqual(ileri.kirilma_cusum([]), ([], None))
        kisa = [BAS + datetime.timedelta(days=i) for i in range(40)]
        self.assertEqual(ileri.kirilma_cusum(kisa, donem="hafta")[0], [])
        sabit = [BAS + datetime.timedelta(days=7 * i + j) for i in range(30) for j in range(3)]
        self.assertEqual(ileri.kirilma_cusum(sabit, donem="hafta")[0], [])   # sıfır sapma

    def test_arac_sozlesmesi(self):
        satirlar = [{"tarih": g.isoformat()} for g in seri(3, 40, carpan=1.6)]
        r = sunucu.arac_calistir("cusum", {"satirlar": satirlar})
        self.assertIsInstance(r["sonuc"], list)
        self.assertTrue(r["sonuc"])
        self.assertTrue(any("kalibre" in u for u in r["meta"]["uyarilar"]))
        ay = sunucu.arac_calistir("cusum", {"satirlar": satirlar, "donem": "ay"})["sonuc"]
        self.assertEqual({a["donem"] for a in ay}, {"ay"})


class TestNniVarsayilan(unittest.TestCase):
    def noktalar(self, tohum, n):
        r = random.Random(tohum)
        return [(41.0 + r.random() * 0.027, 29.0 + r.random() * 0.036) for _ in range(n)]

    def test_rastgele_desende_yan_yok(self):
        yeni = [mekan.nni_test(self.noktalar(t, 50)) for t in range(40)]
        eski = [mekan.nni_test(self.noktalar(t, 50), kenar_duzeltme=False) for t in range(40)]
        ort_yeni = sum(s["nni"] for s in yeni) / 40
        ort_eski = sum(s["nni"] for s in eski) / 40
        self.assertLess(abs(ort_yeni - 1), 0.03)
        self.assertGreater(ort_eski, ort_yeni + 0.03)          # düzeltmesiz: dağınık yanı
        self.assertLessEqual(sum(1 for s in yeni if s["p"] < 0.05), 4)
        self.assertTrue(all(s["kenar_duzeltme"] for s in yeni))

    def test_yansiz_kutu_yalniz_alan_tahmininde(self):
        pts = self.noktalar(1, 30)
        verilen = mekan.nni_test(pts, alan_km2=9.0, cevre_km=12.0)
        self.assertEqual(verilen, mekan.nni_test(pts, alan_km2=9.0, cevre_km=12.0))
        tahmini = mekan.nni_test(pts)
        self.assertNotEqual(verilen["beklenen"], tahmini["beklenen"])

    def test_arac_varsayilani_ve_uyari(self):
        satirlar = [{"lat": a, "lon": b} for a, b in self.noktalar(2, 60)]
        r = sunucu.arac_calistir("nni", {"satirlar": satirlar})
        self.assertTrue(r["sonuc"]["kenar_duzeltme"])
        self.assertTrue(any("yerel" in u and "sicak_nokta_gi" in u for u in r["meta"]["uyarilar"]))
        eski = sunucu.arac_calistir("nni", {"satirlar": satirlar, "kenar_duzeltme": False})["sonuc"]
        self.assertFalse(eski["kenar_duzeltme"])
        alanli = sunucu.arac_calistir("nni", {"satirlar": satirlar, "alan_km2": 9.0, "cevre_km": 12.0})
        self.assertEqual(alanli["sonuc"]["beklenen"],
                         mekan.nni_test([(s["lat"], s["lon"]) for s in satirlar], alan_km2=9.0,
                                        cevre_km=12.0)["beklenen"])


if __name__ == "__main__":
    unittest.main()
