# -*- coding: utf-8 -*-
"""
test_kiyas_v10.py — BMK v10 altyapısı (V17, A5 Rehberli arka uç). ÖN-KAYIT GEREĞİ
gerçek arka uç çağrılmaz: akış listesi, ekran sözleşmesi denetçileri, yasak anahtar
denetimi, çeviri denetçisi (geçici sözlüklerle) ve kilit.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v10"))
import kos_v10  # noqa: E402
from sinama.bilim import hukum, rak  # noqa: E402

V17 = kos_v10.vaka_oku()


def hukum_ornegi(**kw):
    h = {"kategori": "KIRILGAN", "kurallar": [{"kural": "K4-kirilgan"}], "rakipler": [],
         "sonraki_en_iyi_kanit": [], "durum": "taslak", "insan_onayi_gerekir": True,
         "ifade": "… Modellenmemiş açıklamalar (H_bilinmeyen) açık kalır."}
    h.update(kw)
    return h


class Akislar(unittest.TestCase):
    def test_yirmi_akis_ve_onaylayan(self):
        liste = kos_v10.akislar(V17)
        self.assertEqual(len(liste), 7 * 2 + 3 * 2)
        self.assertEqual(len({e for e, _, _ in liste}), len(liste))
        for etiket, arg, satirlar in liste:
            self.assertTrue(satirlar, etiket)
            self.assertEqual("onaylayan" in arg, arg["amac"] == "dogrulayici", etiket)
        kontrolsuz = [a for e, a, _ in liste if e.startswith("v7/kontrolsuz")]
        self.assertTrue(kontrolsuz and all("kontrol" not in a for a in kontrolsuz))


class Denetciler(unittest.TestCase):
    def test_plan_ve_hukum(self):
        plan = {"ulasilabilir_en_ust": "KIRILGAN", "rakipler": [{"kod": "R-VERI", "cozulebilir": True}]}
        self.assertTrue(kos_v10.plan_tam(plan))
        self.assertFalse(kos_v10.plan_tam({**plan, "ulasilabilir_en_ust": "YÜKSEK"}))
        self.assertFalse(kos_v10.plan_tam({**plan, "rakipler": [{"kod": "R-VERI"}]}))
        self.assertTrue(kos_v10.hukum_tam(hukum_ornegi()))
        for bozuk in ({"durum": "kesin"}, {"insan_onayi_gerekir": False}, {"kurallar": []},
                      {"ifade": "notsuz"}, {"kategori": "%80"}, {"sonraki_en_iyi_kanit": None}):
            self.assertFalse(kos_v10.hukum_tam(hukum_ornegi(**bozuk)), bozuk)

    def test_yasak_anahtar(self):
        self.assertTrue(kos_v10.yasak_yok({"hukum": hukum_ornegi()}))
        self.assertFalse(kos_v10.yasak_yok({"hukum": {"guven_puani": 0.8}}))
        self.assertFalse(kos_v10.yasak_yok([{"a": {"Olasilik": 1}}]))


class Ceviri(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="ceviri_v10_")
        self.eski = (kos_v10.CEVIRI, kos_v10.KAYNAK)
        kos_v10.CEVIRI = os.path.join(self.gecici, "i18n")
        kos_v10.KAYNAK = self.gecici
        os.makedirs(kos_v10.CEVIRI)
        with open(hukum.__file__, encoding="utf-8") as f:
            import re
            kurallar = set(re.findall(r'kural\("([A-Za-z0-9-]+)"', f.read()))
        self.tam = {f"kategori.{k}": k for k in hukum.KATEGORILER}
        self.tam.update({f"durum.{d}": d for d in rak.DURUMLAR})
        self.tam.update({f"birincil.{d}": d for d in ("tutuldu", "karşıt", "belirsiz", "sınanamadı")})
        self.tam.update({f"rakip.{k}": k for k in rak.KATALOG})
        self.tam.update({f"soru_turu.{t}": t for t in ("ARTIS", "YOGUNLASMA", "ETKI", "SERI")})
        self.tam.update({f"amac.{a}": a for a in ("operasyonel", "dogrulayici", "kesifsel")})
        self.tam.update({f"kural.{k}": k for k in kurallar})
        self.tam["ekran.soru"] = "Soru"
        with open(os.path.join(self.gecici, "Ekran.tsx"), "w", encoding="utf-8") as f:
            f.write("const a = t('ekran.soru'); const b = t(\"ekran.soru\");\n")

    def tearDown(self):
        kos_v10.CEVIRI, kos_v10.KAYNAK = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def yaz(self, tr, en):
        for dil, s in (("tr", tr), ("en", en)):
            with open(os.path.join(kos_v10.CEVIRI, f"{dil}.json"), "w", encoding="utf-8") as f:
                json.dump(s, f, ensure_ascii=False)

    def test_tam_ve_eksikler(self):
        self.assertEqual(kos_v10.ceviri_denetle(), (False, ["tr.json yok"]))
        self.yaz(self.tam, self.tam)
        self.assertEqual(kos_v10.ceviri_denetle(), (True, []))
        en = dict(self.tam)
        en["ekran.soru"] = " "
        en["fazla"] = "x"
        self.yaz(self.tam, en)
        tam, eksik = kos_v10.ceviri_denetle()
        self.assertFalse(tam)
        self.assertIn("en:ekran.soru", eksik)
        self.assertIn("yalnız birinde:fazla", eksik)
        tr = {k: v for k, v in self.tam.items() if k != "rakip.R-VERI"}
        self.yaz(tr, {k: v for k, v in self.tam.items() if k != "rakip.R-VERI"})
        self.assertIn("tr:rakip.R-VERI", kos_v10.ceviri_denetle()[1])


class Kilit(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="kilit_v10_")
        for yol in kos_v10.KILITLI:
            hedef = os.path.join(self.gecici, yol)
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), hedef)
        self.eski = (kos_v10.KOK, kos_v10.KILIT)
        kos_v10.KOK = self.gecici
        kos_v10.KILIT = os.path.join(self.gecici, "kiyas", "v10", "kilit.json")
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_out, sys.stdout = sys.stdout, bos
            try:
                kos_v10.kilitle()
            finally:
                sys.stdout = eski_out

    def tearDown(self):
        kos_v10.KOK, kos_v10.KILIT = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def _bozuk_mu(self):
        with open(os.devnull, "w", encoding="utf-8") as bos:
            eski_err, sys.stderr = sys.stderr, bos
            try:
                kos_v10.kilit_dogrula()
                return False
            except SystemExit as e:
                return e.code == 2
            finally:
                sys.stderr = eski_err

    def test_saglam_ve_bekciden_gecer(self):
        self.assertFalse(self._bozuk_mu())
        sys.path.insert(0, os.path.join(KOK, "betikler"))
        import veri_bekcisi
        with open(kos_v10.KILIT, encoding="utf-8") as f:
            self.assertEqual(veri_bekcisi.icerik_denetle(f.read().encode("utf-8")), [])

    def test_vaka_degisirse_reddedilir(self):
        yol = os.path.join(self.gecici, "kiyas", "v10", "vakalar", "v17_rehberli_arka_uc.json")
        with open(yol, encoding="utf-8") as f:
            v = json.load(f)
        v["cekirdek_olcutleri"][0]["esik"] = 0.5
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(v, f)
        self.assertTrue(self._bozuk_mu())


if __name__ == "__main__":
    unittest.main()
