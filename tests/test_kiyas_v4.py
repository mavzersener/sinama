# -*- coding: utf-8 -*-
"""
test_kiyas_v4.py — BMK v4 altyapısı (V10 hüküm sağlamlığı). ÖN-KAYIT GEREĞİ
gerçek araç çağrılmaz: senaryoların iddia edilen kaynaklarla (v0 V2, v3 gerçek
artış) kimlikler dışında birebir aynılığı, gerçeğin sağlamlığı, ölçüt hesabının
sahte araçla doğruluğu ve kilidin kurcalamayı yakalaması.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v3"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v4"))
import uretec  # noqa: E402
import uretec_v3  # noqa: E402
import uretec_v4  # noqa: E402
import kos_v4  # noqa: E402


def json_oku(*yol):
    with open(os.path.join(KOK, *yol), encoding="utf-8") as f:
        return json.load(f)


V10 = json_oku("kiyas", "v4", "vakalar", "v10_hukum_saglamligi.json")
P = {s: uretec_v4.parametreler(V10, s) for s in kos_v4.SENARYOLAR}


def kimliksiz(satirlar):
    return [{k: v for k, v in s.items() if k != "id"} for s in satirlar]


def kanal_sayim(satirlar, kanal, once):
    return sum(1 for s in satirlar if s["kanal"] == kanal and (s["tarih"] < "2025-01-01") == once)


class Kaynaklar(unittest.TestCase):
    def test_saf_artefakt_v0_v2_verisi(self):
        p2 = json_oku("kiyas", "vakalar", "v2_bildirim.json")["uretec"]["parametreler"]
        for t in (401, 417):
            self.assertEqual(kimliksiz(uretec_v4.v10_kanallar(P["saf_artefakt"], t)[0]),
                             kimliksiz(uretec.v2_bildirim(p2, t)[0]))

    def test_gercek_artis_v3_verisi(self):
        v9 = json_oku("kiyas", "v3", "vakalar", "v9_hukum.json")
        p9 = uretec_v3.parametreler(v9, "gercek_artis")
        for t in (401, 417):
            self.assertEqual(kimliksiz(uretec_v4.v10_kanallar(P["gercek_artis"], t)[0]),
                             kimliksiz(uretec_v3.v9_gercek_artis(p9, t)[0]))

    def test_tohumlar(self):
        self.assertEqual(kos_v4.tohumlar(V10), list(range(401, 431)))


class GercekSaglamligi(unittest.TestCase):
    def test_determinizm(self):
        for s in kos_v4.SENARYOLAR:
            self.assertEqual(uretec_v4.v10_kanallar(P[s], 7), uretec_v4.v10_kanallar(P[s], 7))

    def test_senaryo_yapisi(self):
        # çok tohumlu toplamlar: gerçek oranlara yakın olmalı
        def toplam(s, kanal, once):
            return sum(kanal_sayim(uretec_v4.v10_kanallar(P[s], t)[0], kanal, once)
                       for t in range(20))
        for s, carpan in (("kismi_artefakt", 1.1), ("karma", 1.3), ("gercek_artis_kucuk_kanal", 1.3)):
            oran = toplam(s, "karakol", False) / toplam(s, "karakol", True)
            self.assertAlmostEqual(oran, carpan, delta=0.03, msg=s)
            self.assertEqual(toplam(s, "cevrimici", True), 0, s)
        self.assertAlmostEqual(toplam("gercek_artis_kucuk_kanal", "cevrimici", False) / (20 * 12), 2, delta=0.2)
        self.assertAlmostEqual(toplam("karma", "cevrimici", False) / (20 * 12), 12, delta=0.5)


def ozet(kategori, birincil="tutuldu", rakip="R-BILDIRIM"):
    return {"kategori": kategori, "birincil": birincil, "rakip": rakip, "rakipler": (),
            "onay": True, "bilinmeyen": True, "yasak_yok": True}


class OlcutHesabi(unittest.TestCase):
    def _k(self, **s):
        k = {x: [(ozet("DESTEKLENDİ"), True)] * 4 for x in kos_v4.SENARYOLAR}
        k.update(s)
        return k

    def test_desteksiz_ve_kosullu_olcutler(self):
        k = self._k(kismi_artefakt=[(ozet("BELİRSİZ"), True), (ozet("KIRILGAN", rakip="R-MEVSIM"), True),
                                    (ozet("BELİRSİZ", birincil="belirsiz"), False),
                                    (ozet("ÇEKİMSER", birincil="sınanamadı"), False)],
                    gercek_artis_kucuk_kanal=[(ozet("DESTEKLENDİ"), True), (ozet("KIRILGAN"), True)])
        d = kos_v4.degerler_uret(k)
        self.assertEqual(d["K10.2"], 0.75)                  # ÇEKİMSER desteksiz sayılmaz
        self.assertEqual(d["K10.3"], 0.5)                   # yalnız tutulan 2 tohum (hepsinde 0,75 olurdu)
        self.assertEqual(d["K10.1"], 0.0)
        self.assertEqual((d["K10.5"], d["K10.6"]), (0.5, 1.0))   # senaryolar karışmaz
        self.assertEqual(d["K10.7"], 1.0)                   # tutulmayanlar paydada değil

    def test_yok_hic_dogru_sayilmaz(self):
        yok = kos_v4.kos_v3.ozet_cikar(None)
        k = {x: [(yok, False)] * 3 for x in kos_v4.SENARYOLAR}
        self.assertEqual(set(kos_v4.degerler_uret(k).values()), {0.0})

    def test_bildirim_olcumu_sayisal_olmali(self):
        def sonuc(olcum):
            return {"hukum": {"rakipler": [{"kod": "R-MEVSIM", "olcum": {"surekli_artis_payi": 0.4}},
                                           {"kod": "R-BILDIRIM", "durum": "çözülmedi", **olcum}]}}
        self.assertTrue(kos_v4.bildirim_olcumu_var(sonuc({"olcum": {"surekli_artis_payi": 0.25}})))
        self.assertFalse(kos_v4.bildirim_olcumu_var(sonuc({"olcum": {"surekli_artis_payi": True}})))
        self.assertFalse(kos_v4.bildirim_olcumu_var(sonuc({"olcum": {"surekli_artis_payi": "0,25"}})))
        self.assertFalse(kos_v4.bildirim_olcumu_var(sonuc({})))
        self.assertFalse(kos_v4.bildirim_olcumu_var(None))


class Uctan(unittest.TestCase):
    def setUp(self):
        self.eski = kos_v4.kos.arac

    def tearDown(self):
        kos_v4.kos.arac = self.eski

    def test_sahte_arac_ve_arguman(self):
        cagrilar = []

        def sahte(ad, satirlar, **arg):
            cagrilar.append((ad, arg))
            return {"sonuc": {"hipotezler": [{"tur": "BILINMEYEN"}],
                              "hukum": {"kategori": "KIRILGAN", "birincil_ongoru": "tutuldu",
                                        "en_guclu_rakip": "R-BILDIRIM", "insan_onayi_gerekir": True,
                                        "rakipler": [{"kod": "R-BILDIRIM", "durum": "çözülmedi",
                                                      "olcum": {"surekli_artis_payi": 0.5}}]}},
                    "meta": {}}
        kos_v4.kos.arac = sahte
        _, olcutler, ek = kos_v4.v10(adet=2)
        d = {o["kimlik"]: o["deger"] for o in olcutler}
        self.assertEqual(d, {"K10.1": 1.0, "K10.2": 1.0, "K10.3": 1.0, "K10.4": 1.0,
                             "K10.5": 0.0, "K10.6": 0.0, "K10.7": 1.0})
        self.assertEqual({c[0] for c in cagrilar}, {"rehberli_calisma"})
        self.assertEqual({(a["soru_turu"], a["amac"], a["onaylayan"], a["kanal_alan"]) for _, a in cagrilar},
                         {("ARTIS", "dogrulayici", "BMK v3", "kanal")})
        self.assertEqual(ek["r_bildirim_durumu"]["karma"], {"çözülmedi": 2})

    def test_arac_yoksa_sifir(self):
        def yok(ad, satirlar, **arg):
            raise KeyError(ad)
        kos_v4.kos.arac = yok
        _, olcutler, ek = kos_v4.v10(adet=1)
        self.assertEqual({o["deger"] for o in olcutler}, {0.0})
        self.assertEqual(ek["hata_ya_da_yok"]["karma"], {"KeyError": 1})


class Kilit(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v4_")
        for yol in kos_v4.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v4.KOK, kos_v4.KILIT)
        kos_v4.KOK = self.gecici
        kos_v4.KILIT = os.path.join(self.gecici, "kiyas", "v4", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v4.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v4.KOK, kos_v4.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v4.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_kilit_gecer(self):
        self.assertFalse(self._bozuk_mu())

    def test_v3_sozlesme_kodu_degisirse_reddedilir(self):
        with open(os.path.join(self.gecici, "kiyas", "v3", "kos_v3.py"), "a", encoding="utf-8") as f:
            f.write("\n# sonradan değişiklik\n")
        self.assertTrue(self._bozuk_mu())

    def test_esik_gevsetilirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v4", "vakalar", "v10_hukum_saglamligi.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][3]["esik"] = 0.05
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
