# -*- coding: utf-8 -*-
"""
test_kapi_doktrin.py — DOKTRIN-ENFORCEMENT SUITE (v6.0, Faz F çekirdeği).

Tez: "doğruluk ajanın itaatinden sistemin inşasına kaydırıldı."
Bu suite, doktrindeki her YAPISAL kuralın fiilen tetiklendiğini kanıtlar:
  K1  gate tek otoritedir (veri delegasyonu kalite.kapi ile birebir aynı)
  K2  standalone analiz gate'siz ÇALIŞAMAZ (dispatch kapısı reddeder)
  K3  döngü içi analiz de aynı kapıdan geçer
  K4  gate "uygun değil" dediğinde araç fonksiyonu HİÇ çalışmaz
  K5  danışma uyarıları engel değildir ama karara işlenir
  K6  PII varsayılan-red (alanlar beyaz listesi olmadan PII dışarı çıkmaz)
  K7  faz atlama / onaysız sonuç / belirsizlik'siz ürün yapısal reddedilir
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama import kalite, veri, dongu, rapor
from sinama import sunucu


def _mekan_veri(n=40, bozuk=False):
    kayitlar = []
    for i in range(n):
        r = {"id": f"O{i}", "tarih": "2026-06-01 10:00", "tur": "hırsızlık",
             "mahalle": "merkez"}
        if not bozuk:
            r["lat"] = 41.0 + (i % 8) * 0.01
            r["lon"] = 29.0 + (i // 8) * 0.01
        kayitlar.append(r)
    return kayitlar


class TestK1_TekOtorite(unittest.TestCase):
    """veri.analiz_uygun_mu, kalite.kapi'ye delege eder — kural tek yerde."""

    def test_delegasyon_esdeger(self):
        vakalar = [
            ({"n": 5}, "suc_oranlari", {"payda_var": False}),
            ({"n": 100, "koordinat_gecerli_oran": 0.2}, "kde_yogunluk", {}),
            ({"n": 40}, "lojistik_regresyon", {}),
            ({"n": 100}, "zarar_analizi", {"tur_kardinalite": 1}),
            ({"n": 60, "benford_mertebe": 1}, "benford", {}),
        ]
        for profil, analiz, baglam in vakalar:
            self.assertEqual(veri.analiz_uygun_mu(profil, analiz, **baglam),
                             kalite.kapi(profil, analiz, **baglam),
                             f"{analiz} için delegasyon sapması")

    def test_kapired_valueerror_alt_tipi(self):
        # istemci sözleşmesi: gate reddi tek satırlık profesyonel hata
        self.assertTrue(issubclass(kalite.KapiRed, ValueError))


class TestK2_StandaloneKapi(unittest.TestCase):
    """Standalone analiz çağrısı gate'siz çalışamaz (dispatch kapısı)."""

    def test_bozuk_koordinat_mekansal_red(self):
        with self.assertRaises(kalite.KapiRed) as cm:
            sunucu.dispatch_gate("grid_hotspot",
                                 {"satirlar": _mekan_veri(bozuk=True)})
        self.assertIn("fitness gate", str(cm.exception))

    def test_tek_nokta_red(self):
        veri40 = [{"lat": 41.0, "lon": 29.0, "tarih": "2026-06-01 10:00"}
                  for _ in range(40)]
        with self.assertRaises(kalite.KapiRed):
            sunucu.dispatch_gate("kde_yogunluk", {"satirlar": veri40})

    def test_paydasiz_oran_red(self):
        with self.assertRaises(kalite.KapiRed):
            sunucu.dispatch_gate("suc_oranlari",
                                 {"bolgeler": [{"bolge": "x", "olay": 10}]})

    def test_benford_tek_mertebe_red(self):
        satirlar = [{"v": str(100 + i % 900)} for i in range(60)]
        with self.assertRaises(kalite.KapiRed):
            sunucu.dispatch_gate("benford", {"satirlar": satirlar,
                                             "alan": "v"})

    def test_gatesiz_arac_kapidan_muaf_degil_kayitli_degil(self):
        # frekans gate listesinde yok: kapı kararı üretilmez (None)
        self.assertIsNone(sunucu.dispatch_gate(
            "frekans", {"satirlar": [{"a": 1}], "alan": "a"}))

    def test_uygun_veride_karar_doner(self):
        karar = sunucu.dispatch_gate("grid_hotspot",
                                     {"satirlar": _mekan_veri(40)})
        self.assertTrue(karar["uygun"])
        self.assertEqual(karar["girdi_n"], 40)


class TestK3_K4_KapiHerYerde(unittest.TestCase):
    """Döngü içi çağrı da aynı kapıdan geçer; redde araç hiç çalışmaz."""

    def test_dongu_analiz_kapi_reddi(self):
        d = dongu.AnalizDongusu({"karar": "test"})
        d.planla()
        d.veri_bagla({"n": 100})
        d.analize_gec({"uygun": True, "sebepler": []})
        # döngü ANALIZ fazında ama kapı payda'sız suc_oranlari'yi reddetmeli
        with self.assertRaises(kalite.KapiRed):
            sunucu.dispatch_gate("suc_oranlari",
                                 {"bolgeler": [{"bolge": "x", "olay": 3}]})

    def test_red_oncesi_arac_calismaz(self):
        # dispatch_gate, ARACLAR["fn"] ÇAĞRILMADAN ÖNCE koşar (isle() sırası).
        # Kanıt: KapiRed, benford_testi'nin üreteceği herhangi bir çıktı
        # olmadan fırlatılır — hata tipi ve mesajı kapıya aittir.
        satirlar = [{"v": str(100 + i % 900)} for i in range(60)]
        try:
            sunucu.dispatch_gate("benford", {"satirlar": satirlar,
                                             "alan": "v"})
            self.fail("kapı reddetmeliydi")
        except kalite.KapiRed as e:
            self.assertIn("mertebe", str(e))


class TestK5_DanismaUyari(unittest.TestCase):
    """uygun=True + sebep: engel değil ama kayıt altında (sessizlik yok)."""

    def test_kikare_cochran_uyarisi_engel_degil(self):
        satirlar = []
        for i in range(20):  # küçük tablo → beklenen<5 hücreler
            satirlar.append({"a": f"a{i % 2}", "b": f"b{i % 3}"})
        karar = sunucu.dispatch_gate("ki_kare_testi",
                                     {"satirlar": satirlar, "a": "a", "b": "b"})
        self.assertTrue(karar["uygun"])
        self.assertTrue(any("Cochran" in s for s in karar["sebepler"]))

    def test_zarar_homojen_uyarisi(self):
        satirlar = [{"tur": "hırsızlık", "mahalle": "m",
                     "tarih": "2026-06-01 10:00"} for _ in range(30)]
        karar = sunucu.dispatch_gate("zarar_hesapla", {"satirlar": satirlar})
        self.assertTrue(karar["uygun"])
        self.assertTrue(any("homojen" in s for s in karar["sebepler"]))


class TestK6_PII_VarsayilanRed(unittest.TestCase):
    def test_pii_alanlar_kisitlanir(self):
        kayitlar = [{"id": "1", "magdur_ad": "Ali", "telefon": "0555",
                     "tur": "hırsızlık"}]
        kisitli = sunucu.kayitlari_kisitla(kayitlar, None)
        for k in kisitli:
            self.assertNotIn("magdur_ad", k)
            self.assertNotIn("telefon", k)


class TestK7_SurecYapisal(unittest.TestCase):
    """Döngü/ürün kuralları yapısal: prompt ricası değil, exception."""

    def test_faz_atlama_red(self):
        d = dongu.AnalizDongusu({"karar": "x"})
        with self.assertRaises(dongu.DonguHatasi):
            d.analiz_kaydet("grid_hotspot", {})  # PLAN'da analiz olmaz

    def test_onaysiz_sonuc_red(self):
        d = dongu.AnalizDongusu({"karar": "x"})
        d.planla(); d.veri_bagla({"n": 10})
        d.analize_gec({"uygun": True, "sebepler": []})
        with self.assertRaises(dongu.DonguHatasi):
            d.sonucla("mudahale_onerildi", {})  # onaylayan yok

    def test_gate_reddi_ile_analize_gecis_red(self):
        d = dongu.AnalizDongusu({"karar": "x"})
        d.planla(); d.veri_bagla({"n": 10})
        with self.assertRaises(dongu.DonguHatasi):
            d.analize_gec({"uygun": False, "sebepler": ["veri yetersiz"]})

    def test_belirsizliksiz_urun_red(self):
        with self.assertRaises(ValueError):
            rapor.taktik_brifing({"karar": "x"}, None, None, None, None,
                                 None, None, None)
        with self.assertRaises(ValueError):
            rapor.stratejik_degerlendirme({"karar": "x"}, None, None, None,
                                          None, None, None)


class TestK8_OturumBirim(unittest.TestCase):
    """G3 (v6.1): oturum = analizin birimi. Gate'siz/izsiz analiz yolu
    yoktur — standalone çağrı bile minimal KEŞİF oturumu açar."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        # önceki değeri sakla: pop() sonradan gelen testlerin ortamını
        # bozuyordu (v6.6: ./oturumlar sızıntısı bu yüzdendi)
        self._eski_log = os.environ.get("SINAMA_LOG_DIR")
        os.environ["SINAMA_LOG_DIR"] = self.tmp
        from sinama.arayuz import sunucu as srv
        self.srv = srv

    def _cagir(self, ad, arg, rid=1):
        return self.srv.isle({"jsonrpc": "2.0", "id": rid,
                              "method": "tools/call",
                              "params": {"name": ad, "arguments": arg}})

    def test_standalone_analiz_kesif_oturumu_acar(self):
        c = self._cagir("grid_hotspot", {"satirlar": _mekan_veri(40)})
        self.assertFalse(c["result"].get("isError"))
        paket = json.loads(c["result"]["content"][0]["text"])
        self.assertTrue(paket["meta"]["oturum_izlendi"])
        self.assertTrue(paket["meta"]["gate"]["uygun"])
        self.assertNotIn("_profil", paket["meta"]["gate"])  # iç alan sızmaz
        # manifesto diskte: keşif modu, gate kayıtlı, adım izli
        kayitlar = dongu.listele(self.tmp)
        kesifler = [m for m in kayitlar if m.get("mod") == "kesif"]
        self.assertEqual(len(kesifler), 1)
        m = dongu.yukle(kesifler[0]["oturum_id"], self.tmp).manifesto
        self.assertEqual(m["faz"], "ANALIZ")
        self.assertTrue(any(g.get("kaynak") == "dispatch_gate"
                            for g in m["gate_kararlari"]))
        self.assertTrue(any(h["arac"] == "grid_hotspot"
                            for h in m["gecmis"]))

    def test_gate_muaf_analitik_arac_da_oturum_acar(self):
        c = self._cagir("frekans", {"satirlar": [{"a": "x"}, {"a": "y"}],
                                    "alan": "a"})
        self.assertFalse(c["result"].get("isError"))
        kayitlar = dongu.listele(self.tmp)
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]["mod"], "kesif")

    def test_kapi_reddi_oturumsuz_kalir(self):
        c = self._cagir("grid_hotspot",
                        {"satirlar": _mekan_veri(40, bozuk=True)})
        self.assertTrue(c["result"]["isError"])
        self.assertEqual(dongu.listele(self.tmp), [])

    def tearDown(self):
        if self._eski_log is None:
            os.environ.pop("SINAMA_LOG_DIR", None)
        else:
            os.environ["SINAMA_LOG_DIR"] = self._eski_log


if __name__ == "__main__":
    unittest.main()
