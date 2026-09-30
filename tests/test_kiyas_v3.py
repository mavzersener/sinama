# -*- coding: utf-8 -*-
"""
test_kiyas_v3.py — BMK v3 altyapısı (ADR-002 kategorik hüküm). ÖN-KAYIT GEREĞİ
gerçek araç çağrılmaz: senaryoların iddia edilen kaynaklarla (v0 V1/V2, v2 V8)
birebir aynılığı, yeni üretecin determinizmi ve gerçeğin sağlamlığı, ölçüt
hesabının SAHTE araçlarla doğruluğu, kilidin kurcalamayı yakalaması.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v2"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v3"))
import uretec  # noqa: E402
import uretec_v2  # noqa: E402
import uretec_v3  # noqa: E402
import kos_v3  # noqa: E402


def json_oku(*yol):
    with open(os.path.join(KOK, *yol), encoding="utf-8") as f:
        return json.load(f)


V9 = json_oku("kiyas", "v3", "vakalar", "v9_hukum.json")


class Kaynaklar(unittest.TestCase):
    def test_artefakt_v0_v2_ile_ayni(self):
        p2 = json_oku("kiyas", "vakalar", "v2_bildirim.json")["uretec"]["parametreler"]
        self.assertEqual(uretec_v3.parametreler(V9, "artefakt"), p2)
        self.assertEqual(uretec_v3.uret(V9, "artefakt", 305), uretec.v2_bildirim(p2, 305))

    def test_odakli_csr_v0_v1_ile_ayni(self):
        p1 = json_oku("kiyas", "vakalar", "v1_kumelenme.json")["uretec"]["parametreler"]
        for s, v in (("odakli", "odakli"), ("csr", "csr")):
            self.assertEqual(uretec_v3.parametreler(V9, s), p1)
            self.assertEqual(uretec_v3.uret(V9, s, 305), uretec.v1_kumelenme(p1, 305, v))

    def test_seri_ve_seri_yok_v2_v8_ile_ayni(self):
        v8 = json_oku("kiyas", "v2", "vakalar", "v8_seri_katman.json")
        for s in ("seri", "seri_yok"):
            p8 = uretec_v2.parametreler(v8, "siki" if s == "seri" else "seri_yok")
            self.assertEqual(uretec_v3.parametreler(V9, s), p8)
            self.assertEqual(uretec_v3.uret(V9, s, 305), uretec_v2.v8_seri(p8, 305))

    def test_kesifsel_ayni_veri(self):
        self.assertEqual(uretec_v3.uret(V9, "gercek_artis", 305),
                         uretec_v3.uret(V9, "gercek_artis_kesifsel", 305))

    def test_tohumlar_oncekilerle_cakismaz(self):
        self.assertEqual(kos_v3.tohumlar(V9), list(range(301, 331)))


class GercekArtis(unittest.TestCase):
    P = uretec_v3.parametreler(V9, "gercek_artis")

    def test_determinizm(self):
        self.assertEqual(uretec_v3.v9_gercek_artis(self.P, 7), uretec_v3.v9_gercek_artis(self.P, 7))
        self.assertNotEqual(uretec_v3.v9_gercek_artis(self.P, 7), uretec_v3.v9_gercek_artis(self.P, 8))

    def test_iki_kanal_bastan_var_ve_ikisi_de_artiyor(self):
        satirlar, g = uretec_v3.v9_gercek_artis(self.P, 3)
        self.assertEqual(g["kesinti_tarihi"], "2025-01-01")
        self.assertTrue(all(set(s) == {"tarih", "kanal", "yil", "id"} for s in satirlar))
        for kanal in ("karakol", "cevrimici"):
            once = sum(1 for s in satirlar if s["kanal"] == kanal and s["tarih"] < "2025-01-01")
            sonra = sum(1 for s in satirlar if s["kanal"] == kanal and s["tarih"] >= "2025-01-01")
            self.assertGreater(once, 0, kanal)
            self.assertGreater(sonra / once, 1.15, kanal)
        tarihler = [s["tarih"] for s in satirlar]
        self.assertEqual(tarihler, sorted(tarihler))


def ozet(kategori, birincil="tutuldu", rakip="R-BILDIRIM", onay=True, bilinmeyen=True,
         yasak_yok=True, rakipler=()):
    return {"kategori": kategori, "birincil": birincil, "rakip": rakip, "rakipler": rakipler,
            "onay": onay, "bilinmeyen": bilinmeyen, "yasak_yok": yasak_yok}


class OlcutHesabi(unittest.TestCase):
    """Saf ölçüt hesabı (gerçek araç çağrılmaz)."""

    def _kosular(self, **senaryo):
        k = {s: [ozet("KIRILGAN")] * 4 for s in kos_v3.SENARYOLAR}
        k.update(senaryo)
        return k

    def test_tavan_tek_destekle_sifirlanir(self):
        self.assertEqual(kos_v3.tavanli([ozet("KIRILGAN")] * 3, "KIRILGAN"), 1.0)
        self.assertEqual(kos_v3.tavanli([ozet("KIRILGAN")] * 3 + [ozet("DESTEKLENDİ")], "KIRILGAN"), 0.0)

    def test_k92_yalniz_birincili_tutulanlarda(self):
        k = self._kosular(artefakt=[ozet("BELİRSİZ"), ozet("BELİRSİZ"),
                                    ozet("BELİRSİZ", birincil="belirsiz", rakip="R-RASTLANTI"),
                                    ozet("DESTEKLENDİ", rakip="R-VERI")])
        d = kos_v3.degerler_uret(k, k["artefakt"])
        self.assertEqual(d["K9.1"], 0.75)
        self.assertEqual(d["K9.2"], round(2 / 3, 4))

    def test_yok_hicbir_olcutte_dogru_sayilmaz(self):
        yok = kos_v3.ozet_cikar(None)
        k = {s: [yok] * 3 for s in kos_v3.SENARYOLAR}
        d = kos_v3.degerler_uret(k, k["artefakt"])
        self.assertEqual(set(d.values()), {0.0})

    def test_ozet_cikar_sozlesme_alanlari_ve_yasak_anahtar(self):
        sonuc = {"hipotezler": [{"tur": "BIRINCIL"}, {"tur": "BILINMEYEN"}],
                 "hukum": {"kategori": "KIRILGAN", "birincil_ongoru": "tutuldu",
                           "en_guclu_rakip": "R-PAYDA", "insan_onayi_gerekir": False,
                           "rakipler": [{"kod": "R-PAYDA", "durum": "çözülmedi"}],
                           "gerekce": [{"kural": "K4", "Guven_Puani": 0.7}]}}
        o = kos_v3.ozet_cikar(sonuc)
        self.assertEqual((o["kategori"], o["rakip"], o["bilinmeyen"], o["onay"]),
                         ("KIRILGAN", "R-PAYDA", True, False))
        self.assertFalse(o["yasak_yok"])        # iç içe, büyük harfli anahtar da yakalanır
        del sonuc["hukum"]["gerekce"]
        self.assertTrue(kos_v3.ozet_cikar(sonuc)["yasak_yok"])

    def test_belirlenimcilik_rakip_durumuna_duyarli(self):
        a = ozet("BELİRSİZ", rakipler=(("R-BILDIRIM", "destekleniyor"),))
        b = ozet("BELİRSİZ", rakipler=(("R-BILDIRIM", "çözülmedi"),))
        k = self._kosular(artefakt=[a, a])
        self.assertEqual(kos_v3.degerler_uret(k, [a, b])["K9.12"], 0.5)


class Uctan(unittest.TestCase):
    """v9() akışı SAHTE araçla: çağrı argümanları ve YOK yolu."""

    def setUp(self):
        self.eski = kos_v3.kos.arac

    def tearDown(self):
        kos_v3.kos.arac = self.eski

    def test_arac_yoksa_hepsi_sifir_ve_hata_sayilir(self):
        def yok(ad, satirlar, **arg):
            raise KeyError(ad)
        kos_v3.kos.arac = yok
        _, olcutler, ek = kos_v3.v9(adet=2)
        self.assertEqual({o["deger"] for o in olcutler}, {0.0})
        self.assertEqual(ek["hata_ya_da_yok"]["seri"], {"KeyError": 2})

    def test_cagri_argumanlari_ve_sabit_kirilgan(self):
        cagrilar = []

        def sahte(ad, satirlar, **arg):
            cagrilar.append(arg)
            self.assertEqual(ad, "rehberli_calisma")
            return {"sonuc": {"hipotezler": [{"tur": "BIRINCIL"}, {"tur": "BILINMEYEN"}],
                              "hukum": {"kategori": "KIRILGAN", "birincil_ongoru": "tutuldu",
                                        "en_guclu_rakip": "R-BILDIRIM", "insan_onayi_gerekir": True,
                                        "rakipler": [{"kod": "R-BILDIRIM", "durum": "çözülmedi"}]}},
                    "meta": {}}
        kos_v3.kos.arac = sahte
        _, olcutler, _ = kos_v3.v9(adet=2)
        d = {o["kimlik"]: o["deger"] for o in olcutler}
        self.assertEqual(d, {"K9.1": 0.0, "K9.2": 1.0, "K9.3": 0.0, "K9.4": 1.0, "K9.5": 1.0,
                             "K9.6": 0.0, "K9.7": 1.0, "K9.8": 1.0, "K9.9": 0.0, "K9.10": 1.0,
                             "K9.11": 1.0, "K9.12": 1.0})
        turler = {(c["soru_turu"], c["amac"], "onaylayan" in c, c.get("kanal_alan"), c.get("mo_alan"))
                  for c in cagrilar}
        self.assertEqual(turler, {("ARTIS", "dogrulayici", True, "kanal", None),
                                  ("ARTIS", "kesifsel", False, "kanal", None),
                                  ("YOGUNLASMA", "dogrulayici", True, None, None),
                                  ("SERI", "dogrulayici", True, None, "mo")})
        self.assertEqual(len(cagrilar), 7 * 2 + 2)   # 7 senaryo × 2 tohum + artefakt tekrarı

    def test_sozlesme_disi_cikti_yok_sayilir(self):
        kos_v3.kos.arac = lambda ad, satirlar, **arg: {"sonuc": [1, 2], "meta": {}}
        _, olcutler, ek = kos_v3.v9(adet=1)
        self.assertEqual({o["deger"] for o in olcutler}, {0.0})
        self.assertEqual(ek["hata_ya_da_yok"]["csr"], {"sozlesme_disi": 1})


class Kilit(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v3_")
        for yol in kos_v3.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v3.KOK, kos_v3.KILIT)
        kos_v3.KOK = self.gecici
        kos_v3.KILIT = os.path.join(self.gecici, "kiyas", "v3", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v3.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v3.KOK, kos_v3.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v3.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_kilit_gecer(self):
        self.assertFalse(self._bozuk_mu())

    def test_esik_gevsetilirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v3", "vakalar", "v9_hukum.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][2]["esik"] = 0.5
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())

    def test_v2_bagimliligi_degisirse_de_reddedilir(self):
        with open(os.path.join(self.gecici, "kiyas", "v2", "uretec_v2.py"), "a", encoding="utf-8") as f:
            f.write("\n# sonradan değişiklik\n")
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
