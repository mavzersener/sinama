# -*- coding: utf-8 -*-
"""
test_kiyas_v2.py — BMK v2 altyapısı (seri bağlantısı). ÖN-KAYIT GEREĞİ gerçek
araç çağrılmaz: üreteç determinizmi, varyantların iddia edilen kaynaklarla
(V3, V7) birebir aynılığı, gerçeğin sağlamlığı, veriye gerçek sızmaması,
ölçüt hesabının SAHTE araçlarla doğruluğu ve kilidin kurcalamayı yakalaması.
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v2"))
import uretec  # noqa: E402
import uretec_v2  # noqa: E402
import kos_v2  # noqa: E402


def json_oku(*yol):
    with open(os.path.join(KOK, *yol), encoding="utf-8") as f:
        return json.load(f)


V8 = json_oku("kiyas", "v2", "vakalar", "v8_seri_katman.json")
P = {v: uretec_v2.parametreler(V8, v) for v in kos_v2.VARYANTLAR}


class Kaynaklar(unittest.TestCase):
    def test_siki_v3_ile_ayni(self):
        p3 = json_oku("kiyas", "vakalar", "v3_seri.json")["uretec"]["parametreler"]
        self.assertEqual(P["siki"], p3)
        self.assertEqual(uretec_v2.v8_seri(P["siki"], 205), uretec.v3_seri(p3, 205))

    def test_yayilmis_v7_ile_ayni(self):
        p7 = json_oku("kiyas", "v1", "vakalar", "v7_yayilan_seri.json")["uretec"]["parametreler"]
        self.assertEqual(P["yayilmis"], p7)

    def test_tohumlar_oncekilerle_cakismaz(self):
        self.assertEqual(kos_v2.tohumlar(V8), list(range(201, 231)))


class Determinizm(unittest.TestCase):
    def test_ayni_tohum_ayni_veri(self):
        for v in kos_v2.VARYANTLAR:
            with self.subTest(v=v):
                self.assertEqual(uretec_v2.v8_seri(P[v], 7), uretec_v2.v8_seri(P[v], 7))
                self.assertNotEqual(uretec_v2.v8_seri(P[v], 7), uretec_v2.v8_seri(P[v], 8))


class GercekSaglamligi(unittest.TestCase):
    def test_tutarsiz_seri_bes_davranis_ve_siki_uzay_zaman(self):
        satirlar, g = uretec_v2.v8_seri(P["tutarsiz"], 3)
        self.assertEqual(len(satirlar), 60)
        seri_kume = set(P["tutarsiz"]["seri_mo"])
        genel = set(P["tutarsiz"]["genel_kelimeler"])
        kayit = {s["id"]: s for s in satirlar}
        self.assertEqual(len(g["seri"]), 5)
        kumeler = []
        for k in g["seri"]:
            kelimeler = kayit[k]["mo"].split()
            self.assertEqual(len([w for w in kelimeler if w in seri_kume]), 5)
            self.assertEqual(len(kelimeler), 6)
            self.assertIn(kelimeler[-1], genel)
            kumeler.append(set(kelimeler) & seri_kume)
        self.assertGreater(len({frozenset(k) for k in kumeler}), 1)  # gerçekten tutarsız
        gunler = [datetime.date.fromisoformat(kayit[k]["tarih"]) for k in g["seri"]]
        self.assertLessEqual((max(gunler) - min(gunler)).days, P["tutarsiz"]["seri_gun"])
        # ±0,25 km kare içinde: iki olay arası en çok köşegen 0,5·√2 km
        for a in g["seri"]:
            for b in g["seri"]:
                d = kos_v2.kos.km(kayit[a]["lat"], kayit[a]["lon"], kayit[b]["lat"], kayit[b]["lon"])
                self.assertLessEqual(d, 0.5 * 2 ** 0.5 + 1e-3)
        # seri dışı kayıtlarda ayırt edici davranış yok
        for k, s in kayit.items():
            if g["grup"][k] != "seri":
                self.assertFalse(set(s["mo"].split()) & seri_kume)

    def test_seri_yok_varyantinda_seri_yok(self):
        satirlar, g = uretec_v2.v8_seri(P["seri_yok"], 3)
        self.assertEqual((len(satirlar), g["seri"]), (60, []))
        seri_kume = set(P["seri_yok"]["seri_mo"])
        self.assertFalse(any(set(s["mo"].split()) & seri_kume for s in satirlar))

    def test_veride_gercek_yok(self):
        for v in kos_v2.VARYANTLAR:
            satirlar, _ = uretec_v2.v8_seri(P[v], 4)
            with self.subTest(v=v):
                self.assertTrue(all(set(s) == {"id", "mo", "lat", "lon", "tarih"} for s in satirlar))
                tarihler = [s["tarih"] for s in satirlar]
                self.assertEqual(tarihler, sorted(tarihler))


class OlcutHesabi(unittest.TestCase):
    """Koşucunun ölçüt hesabı SAHTE araçlarla (gerçek araç çağrılmaz)."""

    def setUp(self):
        self.eski_arac, self.eski_uret = kos_v2.kos.arac, kos_v2.uretec_v2.v8_seri
        self.son = {}

        def uret(p, t):
            satirlar, gercek = self.eski_uret(p, t)
            self.son["gercek"] = gercek
            return satirlar, gercek
        kos_v2.uretec_v2.v8_seri = uret

    def tearDown(self):
        kos_v2.kos.arac, kos_v2.uretec_v2.v8_seri = self.eski_arac, self.eski_uret

    def _kos(self, cevap):
        def sahte(ad, satirlar, **arg):
            self.assertEqual((ad, arg), ("seri_eslestirme", {"mo_alan": "mo"}))
            return {"sonuc": cevap(self.son["gercek"]), "meta": {}}
        kos_v2.kos.arac = sahte
        _, olcutler, ek = kos_v2.v8(adet=3)
        return {o["kimlik"]: o["deger"] for o in olcutler}, ek

    @staticmethod
    def _dogru(g, **alan):
        s = g["seri"]
        return [dict(id1=a, id2=b, **alan) for i, a in enumerate(s) for b in s[i + 1:]]

    @staticmethod
    def _ortak_cift(g, **alan):
        o = [k for k, x in sorted(g["grup"].items()) if x == "ortak_mo"]
        return [dict(id1=o[0], id2=o[1], **alan)]

    def test_kahin(self):
        tam = {"katman": "güçlü", "kanit": {"mo": 1, "uzay": 1, "zaman": 1}}
        d, _ = self._kos(lambda g: self._dogru(g, **tam))
        self.assertEqual(d, {"K8.1": 1.0, "K8.2": 1.0, "K8.3": 1.0, "K8.4": 1.0, "K8.5": 1.0,
                             "K8.6": 0.0, "K8.7": 1.0, "K8.8": 1.0, "K8.9": 0.0, "K8.10": 1.0})

    def test_bos_cevap(self):
        d, _ = self._kos(lambda g: [])
        self.assertEqual(set(d.values()), {0.0})

    def test_katmansiz_cift_guclu_sayilir(self):
        d, ek = self._kos(lambda g: self._dogru(g) + self._ortak_cift(g))
        k = round(10 / 11, 4)   # havuzlanmış: 30/33
        self.assertEqual(d, {"K8.1": 1.0, "K8.2": k, "K8.3": k, "K8.4": 1.0, "K8.5": k,
                             "K8.6": 1.0, "K8.7": 1.0, "K8.8": k, "K8.9": 1.0, "K8.10": 0.0})
        self.assertEqual(ek["siki"]["ort_g"], 11)

    def test_zayif_katman_g_disinda(self):
        zayif = {"katman": "zayıf", "kanit": {"mo": 1, "uzay": 0, "zaman": 0}}
        d, ek = self._kos(lambda g: self._dogru(g, **zayif) + self._ortak_cift(g, **zayif))
        k = round(10 / 11, 4)
        self.assertEqual(d, {"K8.1": 1.0, "K8.2": 0.0, "K8.3": k, "K8.4": 1.0, "K8.5": k,
                             "K8.6": 0.0, "K8.7": 1.0, "K8.8": k, "K8.9": 0.0, "K8.10": 1.0})
        self.assertEqual(ek["siki"]["dogru_zayif_katmanda"], 30)

    def test_eksik_kanit_hatti_sozlesmeyi_bozar(self):
        eksik = {"katman": "güçlü", "kanit": {"mo": 1, "uzay": 1}}
        d, _ = self._kos(lambda g: self._dogru(g, **eksik))
        self.assertEqual(d["K8.10"], 0.0)


class Toplama(unittest.TestCase):
    """Toplama kuralları, farkın görüneceği elle kurulmuş sayımlarla."""

    GERCEK = {"seri": ["s1", "s2"],
              "grup": {"s1": "seri", "s2": "seri", "o1": "ortak_mo", "o2": "ortak_mo",
                       "d1": "diger"}}

    def test_yalniz_iki_ucu_ortak_mo_olan_cift_bagimsiz_yanlis(self):
        s = kos_v2.tohum_olc([{"id1": "o1", "id2": "o2"}, {"id1": "o1", "id2": "d1"},
                              {"id1": "s1", "id2": "o1"}], self.GERCEK)
        self.assertEqual((s["g_ortak_yanlis"], s["g"], s["c_dogru"]), (1, 3, 0))

    def test_kesinlik_havuzlanmis_ve_g_dolu_tohum_orani(self):
        a = kos_v2.tohum_olc([{"id1": "s1", "id2": "s2"}], self.GERCEK)          # 1/1
        b = kos_v2.tohum_olc([{"id1": "o1", "id2": "o2"}, {"id1": "o1", "id2": "d1"},
                              {"id1": "o2", "id2": "d1"}], self.GERCEK)          # 0/3
        c = kos_v2.tohum_olc([], self.GERCEK)
        o = kos_v2.ozetle([a, b, c])
        self.assertEqual(o["kesinlik_c"], 0.25)          # havuz 1/4 (tohum ortalaması 0,5 olurdu)
        self.assertEqual(o["g_dolu_tohum"], round(2 / 3, 4))   # sayı ortalaması 1,33 olurdu
        self.assertEqual(o["geri_cagirma"], round(1 / 3, 4))


class Kilit(unittest.TestCase):
    """Kilit mantığı geçici kopyada sınanır (gerçek kilide dokunulmaz)."""

    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v2_")
        for yol in kos_v2.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v2.KOK, kos_v2.KILIT)
        kos_v2.KOK = self.gecici
        kos_v2.KILIT = os.path.join(self.gecici, "kiyas", "v2", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v2.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v2.KOK, kos_v2.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v2.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_kilit_gecer(self):
        self.assertFalse(self._bozuk_mu())

    def test_esik_gevsetilirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v2", "vakalar", "v8_seri_katman.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][4]["esik"] = 0.3   # sonucu görüp eşiği gevşetmek
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())

    def test_v0_bagimliligi_degisirse_de_reddedilir(self):
        with open(os.path.join(self.gecici, "kiyas", "uretec.py"), "a", encoding="utf-8") as f:
            f.write("\n# sonradan değişiklik\n")
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
