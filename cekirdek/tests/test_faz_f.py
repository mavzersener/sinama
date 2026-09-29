# -*- coding: utf-8 -*-
"""
test_faz_f.py — Faz F (v6.4): doktrin-enforcement suite genişlemesi.
Her YAPISAL doktrin kuralı için en az bir kanıt testi + kapsam haritası.
  K15 yol hapsi primitifleri + amaca özel uzantı (.json ağırlık düzeltmesi)
  K16 tavanlar: quadratic guard, MAKS_SATIR, MAKS_DOSYA
  K17 audit sözleşmesi: argüman anahtarları yazılır, değerler ASLA
  K18 şema doğrulama: -32602 (bilinmeyen alan, tip, required)
  K19 FDR otomatik: bolge_anomali q-değerleri yapısal
  K20 nominal alanda sayısal özet yapısal reddedilir
  K21 kurum ağırlık tablosu uçtan uca (v6.4'te bulunan .json hatası)
"""
import json
import logging
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama import kalite, veri
from sinama.arayuz import ortak, sunucu as srv, sema as sema_mod
from sinama.cekirdek import ileri, zarar


class TestK15_YolHapsi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SINAMA_VERI_KOKU"] = self.tmp
        with open(os.path.join(self.tmp, "ok.csv"), "w") as f:
            f.write("a\n1\n")

    def test_nokta_nokta_kacis_red(self):
        with self.assertRaises(ValueError):
            veri.guvenli_yol("../gizli.csv")

    def test_mutlak_dis_yol_red(self):
        with self.assertRaises(ValueError):
            veri.guvenli_yol("/etc/passwd")

    def test_json_varsayilan_red(self):
        with self.assertRaises(ValueError):
            veri.guvenli_yol("ok.json")

    def test_amaca_ozel_uzanti_json_kabul(self):
        with open(os.path.join(self.tmp, "ag.json"), "w") as f:
            f.write("{}")
        yol = veri.guvenli_yol("ag.json", izinli_uzantilar={".json"})
        self.assertTrue(yol.endswith("ag.json"))

    def tearDown(self):
        os.environ.pop("SINAMA_VERI_KOKU", None)


class TestK16_Tavanlar(unittest.TestCase):
    def test_quadratic_guard(self):
        with self.assertRaises(ValueError):
            ortak.quadratic_guard([(0, 0)] * (ortak.MAKS_QUADRATIC_N + 1),
                                  "nni")

    def test_inline_tavan(self):
        # sözleşme: sessiz kırpma YOK — kırpılır + son_okuma["kesildi"]
        # bayrağı meta'ya düşer (görünür veri kaybı, gizli değil)
        eski = veri.MAKS_SATIR
        veri.MAKS_SATIR = 10
        try:
            sonuc = ortak.kayitlari_getir(
                {"satirlar": [{"a": i} for i in range(11)]})
            self.assertEqual(len(sonuc), 10)
            self.assertTrue(veri.son_okuma["kesildi"])
        finally:
            veri.MAKS_SATIR = eski

    def test_dosya_boyut_tavani(self):
        from sinama.kalite import guvenlik
        tmp = tempfile.mkdtemp()
        os.environ["SINAMA_VERI_KOKU"] = tmp
        with open(os.path.join(tmp, "k.csv"), "w") as f:
            f.write("a\n1\n")
        eski = guvenlik.MAKS_DOSYA_MB
        guvenlik.MAKS_DOSYA_MB = 0
        try:
            with self.assertRaises(ValueError):
                veri.guvenli_yol("k.csv")
        finally:
            guvenlik.MAKS_DOSYA_MB = eski
            os.environ.pop("SINAMA_VERI_KOKU", None)


class TestK17_AuditSozlesme(unittest.TestCase):
    def test_anahtar_yazar_deger_yazmaz(self):
        tmp = tempfile.mkdtemp()
        dosya = os.path.join(tmp, "audit.log")
        logger = logging.getLogger("audit_test_" + os.path.basename(tmp))
        logger.handlers = []
        logger.addHandler(logging.FileHandler(dosya, encoding="utf-8"))
        logger.setLevel(logging.INFO)
        eski = ortak.AUDIT
        ortak.AUDIT = logger
        try:
            ortak.audit_yaz("grid_hotspot",
                            {"csv_yolu": "olaylar.csv",
                             "magdur_ad": "Vatandas Yilmaz",
                             "telefon": "05551112233"}, 120, 3.5, False)  # bekci:izin (sentetik)
        finally:
            ortak.AUDIT = eski
        icerik = open(dosya, encoding="utf-8").read()
        self.assertIn("csv_yolu", icerik)          # anahtar var
        self.assertIn("magdur_ad", icerik)          # anahtar var
        self.assertNotIn("Vatandas", icerik)        # değer YOK
        self.assertNotIn("05551112233", icerik)     # değer YOK  bekci:izin (sentetik)


class TestK18_SemaDogrulama(unittest.TestCase):
    def _cagir_ham(self, ad, arg):
        return srv.isle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": ad, "arguments": arg}})

    def test_enum_ihlali_32602(self):
        c = self._cagir_ham("t_testi", {"tip": "olmayan_tip",
                                        "x": [1.0, 2.0, 3.0]})
        self.assertEqual(c["error"]["code"], -32602)

    def test_tip_uyusmazligi_32602(self):
        c = self._cagir_ham("frekans", {"satirlar": "bu bir liste değil",
                                        "alan": "a"})
        self.assertEqual(c["error"]["code"], -32602)

    def test_required_eksik_32602(self):
        c = self._cagir_ham("frekans", {"satirlar": [{"a": 1}]})
        self.assertEqual(c["error"]["code"], -32602)

    def test_bilinmeyen_arac_32602(self):
        c = self._cagir_ham("olmayan_arac", {})
        self.assertEqual(c["error"]["code"], -32602)


class TestK19_FDR_Otomatik(unittest.TestCase):
    def test_q_alanlari_yapisal(self):
        sayim = {f"b{i}": v for i, v in enumerate([5, 5, 6, 6, 7, 7, 8, 30])}
        s = ileri.bolge_anomali(sayim)
        self.assertTrue(all("q" in t for t in s["tum_sonuclar"]))
        # q, p sırasıyla monoton (BH özelliği)
        qs = [t["q"] for t in s["tum_sonuclar"]]
        self.assertEqual(qs, sorted(qs))

    def test_anlamli_karari_q_ile(self):
        # A4.5 (BMK v1 K6.2): 50 bölgede tek sınırda sapma. Düzeltmesiz
        # p ≤ 0,01 onu "anlamlı" sayardı; çoklu testte (q) elenmeli.
        sayim = {f"b{i:02d}": 20 for i in range(49)}
        sayim["b49"] = 33
        s = ileri.bolge_anomali(sayim)
        b49 = next(t for t in s["tum_sonuclar"] if t["bolge"] == "b49")
        self.assertLess(b49["p"], 0.01)
        self.assertGreater(b49["q"], 0.05)
        self.assertEqual(s["anlamli"], [])


class TestK20_NominalRed(unittest.TestCase):
    def test_nominal_alan_kapi_reddi(self):
        satirlar = [{"tur": "hırsızlık"} for _ in range(30)]
        with self.assertRaises(kalite.KapiRed):
            srv.dispatch_gate("dagilim_olculeri",
                              {"satirlar": satirlar, "alan": "tur"})

    def test_sayisal_alan_gecer(self):
        satirlar = [{"v": str(10 + i * 3)} for i in range(30)]
        karar = srv.dispatch_gate("dagilim_olculeri",
                                  {"satirlar": satirlar, "alan": "v"})
        self.assertTrue(karar["uygun"])


class TestK21_KurumAgirlikTablosu(unittest.TestCase):
    """v6.4'te bulunan yapısal hata: .json ağırlık tablosu whitelist'e
    takılıyordu — kurum tablosu (DOKTRIN 17/18) fiilen kullanılamıyordu."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["SINAMA_VERI_KOKU"] = self.tmp
        with open(os.path.join(self.tmp, "kurum.json"), "w") as f:
            json.dump({"hırsızlık": 250, "kapkaç": 500}, f)

    def test_json_agirlik_uçtan_uca(self):
        yol = veri.guvenli_yol("kurum.json", izinli_uzantilar={".json"})
        agirliklar = zarar.agirlik_tablosu_yukle(yol)
        self.assertEqual(agirliklar["hırsızlık"], 250)

    def test_agirlik_yolu_arac_uzerinden(self):
        os.environ["SINAMA_LOG_DIR"] = tempfile.mkdtemp()
        try:
            c = srv.isle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": "zarar_hesapla",
                                     "arguments": {
                                         "satirlar": [{"tur": "hırsızlık"},
                                                      {"tur": "kapkaç"}],
                                         "agirlik_yolu": "kurum.json"}}})
            sonuc = json.loads(c["result"]["content"][0]["text"])["sonuc"]
            self.assertEqual(sonuc["toplam_zarar"], 750)
        finally:
            os.environ.pop("SINAMA_LOG_DIR", None)

    def tearDown(self):
        os.environ.pop("SINAMA_VERI_KOKU", None)


# ---------------- DOKTRİN KAPSAM HARİTASI (meta-kanıt) ----------------
# Her YAPISAL kural için en az bir kanıt testi. Yargısal kurallar
# (12 yayınlama, 13 geri-besleme) kasıtlı olarak kapsam dışı.
DOKTRIN_KAPSAM = {
    1: "TestK2_StandaloneKapi.test_bozuk_koordinat_mekansal_red",
    2: "TestK1_TekOtorite.test_delegasyon_esdeger",
    3: "TestK7_SurecYapisal.test_belirsizliksiz_urun_red",
    4: "TestK6_PII_VarsayilanRed.test_pii_alanlar_kisitlanir",
    5: "TestK15_YolHapsi.test_nokta_nokta_kacis_red",
    6: "TestK16_Tavanlar.test_quadratic_guard",
    7: "TestK18_SemaDogrulama.test_tip_uyusmazligi_32602",
    8: "TestK17_AuditSozlesme.test_anahtar_yazar_deger_yazmaz",
    9: "TestK3_K4_KapiHerYerde.test_red_oncesi_arac_calismaz",
    10: "TestK20_NominalRed.test_nominal_alan_kapi_reddi",
    11: "TestK19_FDR_Otomatik.test_q_alanlari_yapisal",
    14: "TestK7_SurecYapisal.test_faz_atlama_red",
    15: "TestK8_OturumBirim.test_standalone_analiz_kesif_oturumu_acar",
    16: "TestK8_OturumBirim.test_standalone_analiz_kesif_oturumu_acar",
    17: "TestK21_KurumAgirlikTablosu.test_json_agirlik_uçtan_uca",
    18: "TestK21_KurumAgirlikTablosu.test_json_agirlik_uçtan_uca",
    19: "TestK3_K4_KapiHerYerde.test_dongu_analiz_kapi_reddi",
    21: "TestK12_GerekceZorunlu.test_resmi_oturumda_gerekcesiz_red",
    22: "TestK22_KanitDayanikliligi.test_cokme_sonrasi_akistan_onarim",
    23: "TestSozlesmeTumAraclar.test_her_arac_sozlesme_kapsaminda",
    24: "TestKatmanIhlali.test_import_yonu",
    25: "TestDokumanStandardi.test_public_docstring_yuzde_yuz",
}


class TestKapsamHaritasi(unittest.TestCase):
    """Faz F ilkesi: suite kalıcı bir alışkanlıktır — yapısal kural
    ekleyen, kanıt testini de ekler. Bu test haritanın canlılığını denetler."""

    def test_her_yapisal_kural_kanitli(self):
        try:
            import tests.test_kapi_doktrin as kd
            import tests.test_kanit_muhakeme as km
            import tests.test_dayaniklilik as dy
            import tests.test_sozlesme as sz
            import tests.test_olgunlastirma as og
        except ImportError:
            import test_kapi_doktrin as kd
            import test_kanit_muhakeme as km
            import test_dayaniklilik as dy
            import test_sozlesme as sz
            import test_olgunlastirma as og
        moduller = [kd, km, dy, sz, og, sys.modules[__name__]]
        eksik = []
        for kural, yol in sorted(DOKTRIN_KAPSAM.items()):
            sinif_ad, metod_ad = yol.split(".")
            bulundu = any(hasattr(getattr(m, sinif_ad, None) or object(),
                          metod_ad) for m in moduller)
            if not bulundu:
                eksik.append((kural, yol))
        self.assertEqual(eksik, [],
                         f"kapsam haritası bozuk (test yok): {eksik}")


if __name__ == "__main__":
    unittest.main()
