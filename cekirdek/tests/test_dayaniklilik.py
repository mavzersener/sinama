# -*- coding: utf-8 -*-
"""
test_dayaniklilik.py — v6.5 kanıtları (GELISME_PLANI H1 + H2):
  K22 kanıt yazımı atomiktir; kanıt kaybı asla sessiz değildir;
      çökme sonrası onarım yapısaldır (DOKTRIN kural 22)
  H2  hata taksonomisi: her hata TİP taşır; sunucu tipi yapısal
      olarak bildirir (agent düzeltici eylem seçebilir)
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi.cekirdek import regresyon
from suc_analizi.cekirdek.hatalar import (SucAnaliziHatasi, VeriHatasi,
                                          GuvenlikHatasi, KullanimHatasi)
from suc_analizi.kalite import guvenlik, KapiRed
from suc_analizi.surec import dongu, kanit

GEREKCE = {"hipotez": "h", "yorum": "y"}


def _resmi_dongu():
    d = dongu.AnalizDongusu({"karar": "devriye", "urun_turu": "taktik"})
    d.planla()
    d.veri_bagla({"n": 120, "uyarilar": []})
    d.analize_gec({"uygun": True, "sebepler": ["ok"]})
    return d


class TestK22_KanitDayanikliligi(unittest.TestCase):
    """DOKTRIN 22: kanıt yazımı atomiktir; kaybı asla sessiz değildir."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_atomik_yazim_yarim_dosya_birakmaz(self):
        d = _resmi_dongu()
        dongu.kaydet(d, self.tmp)
        oturumlar = os.path.join(self.tmp, "oturumlar")
        self.assertEqual([f for f in os.listdir(oturumlar)
                          if f.endswith(".tmp")], [])
        m = json.load(open(os.path.join(
            oturumlar, f"{d.manifesto['oturum_id']}.json"),
            encoding="utf-8"))
        self.assertEqual(m["oturum_id"], d.manifesto["oturum_id"])

    def test_manifesto_yazim_hatasi_gurultulu_ve_akis_saglam(self):
        """H1.3 (resmî): manifesto yazılamazsa DonguHatasi; olaylar
        akışta SAĞLAM kalır (kanıt kaybolmaz, hata sessiz değildir)."""
        d = _resmi_dongu()
        d.analiz_kaydet("nni", {"nni": 0.62}, GEREKCE)
        gercek = kanit.atomik_json_yaz
        def _bozuk(*a, **k):
            raise OSError("disk dolu")
        try:
            kanit.atomik_json_yaz = _bozuk
            with self.assertRaises(dongu.DonguHatasi) as cm:
                dongu.kaydet(d, self.tmp)
        finally:
            kanit.atomik_json_yaz = gercek
        self.assertIn("akış", str(cm.exception))
        # olaylar akışa yazıldı ve zincir sağlam — kanıt kaybolmadı
        olaylar = kanit.oku(self.tmp, d.manifesto["oturum_id"])
        self.assertEqual(len(olaylar), len(d.manifesto["gecmis"]))
        self.assertTrue(kanit.dogrula(self.tmp,
                                      d.manifesto["oturum_id"])["saglam"])

    def test_cokme_sonrasi_akistan_onarim(self):
        """H1.4: olay yazıldı, manifesto yazılamadı (çökme) → yukle
        gecmis'i akıştan ONARIR ve kanit_uyari işaretler."""
        d = _resmi_dongu()
        d.analiz_kaydet("nni", {"nni": 0.62}, GEREKCE)
        dongu.kaydet(d, self.tmp)
        oid = d.manifesto["oturum_id"]
        # çökme simülasyonu: manifestoyu bir adım GERİYE al (akış ileride)
        yol = os.path.join(self.tmp, "oturumlar", f"{oid}.json")
        with open(yol, encoding="utf-8") as f:
            m = json.load(f)
        m["gecmis"] = m["gecmis"][:-1]
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False)
        d2 = dongu.yukle(oid, self.tmp)
        self.assertIn("kanit_uyari", d2.manifesto)
        self.assertIn("onarım", d2.manifesto["kanit_uyari"])
        self.assertEqual(len(d2.manifesto["gecmis"]),
                         len(kanit.oku(self.tmp, oid)))
        self.assertEqual(d2.manifesto["gecmis"][-1]["arac"], "nni")
        # onarım sonrası kaydetme olayı ÇOĞALTMAZ (idempotent)
        dongu.kaydet(d2, self.tmp)
        self.assertEqual(len(kanit.oku(self.tmp, oid)),
                         len(d2.manifesto["gecmis"]))

    def test_akis_eksikse_uyari_sessiz_degil(self):
        d = _resmi_dongu()
        dongu.kaydet(d, self.tmp)
        oid = d.manifesto["oturum_id"]
        os.remove(kanit._akis_yolu(self.tmp, oid))  # akış kaybı
        d2 = dongu.yukle(oid, self.tmp)
        self.assertIn("eksik", d2.manifesto["kanit_uyari"])
        self.assertIn("kanit_dogrula", d2.manifesto["kanit_uyari"])

    def test_zincir_bozuksa_onarim_yapilmaz(self):
        d = _resmi_dongu()
        d.analiz_kaydet("nni", {"nni": 0.62}, GEREKCE)
        dongu.kaydet(d, self.tmp)
        oid = d.manifesto["oturum_id"]
        # zinciri kurcala + manifestoyu geriye al
        yol = kanit._akis_yolu(self.tmp, oid)
        satirlar = open(yol, encoding="utf-8").read().splitlines()
        bozuk = json.loads(satirlar[1])
        bozuk["ozet"] = "KURCALANDI"
        satirlar[1] = json.dumps(bozuk, ensure_ascii=False)
        open(yol, "w", encoding="utf-8").write("\n".join(satirlar) + "\n")
        myol = os.path.join(self.tmp, "oturumlar", f"{oid}.json")
        with open(myol, encoding="utf-8") as f:
            m = json.load(f)
        eski_n = len(m["gecmis"]) - 1
        m["gecmis"] = m["gecmis"][:eski_n]
        with open(myol, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False)
        d2 = dongu.yukle(oid, self.tmp)
        self.assertIn("BOZUK", d2.manifesto["kanit_uyari"])
        self.assertEqual(len(d2.manifesto["gecmis"]), eski_n)  # onarılmadı

    def test_kesif_kanit_kaybi_meta_bayragi(self):
        """H1.3 (keşif): yazılamayan adım meta'da GÜRÜLTÜLÜ işaretlenir."""
        from suc_analizi.arayuz import sunucu
        paket = sunucu._basari_paketi(
            "nni", {"nni": 0.62},
            {"uygun": True, "sebepler": ["belirgin engel yok"]},
            "YAZILAMADI")
        meta = paket["meta"]
        self.assertEqual(meta["kanit_durumu"], "YAZILAMADI")
        self.assertFalse(meta["oturum_izlendi"])
        self.assertTrue(any("KANIT KAYBI" in u
                            for u in meta["uyarilar"]))


class TestH2_HataTaksonomisi(unittest.TestCase):
    """Her alan hatası TİP + (yerindeyse) ÖNERİ taşır; sunucu yapısal
    bildirir. Sınıflar ValueError uyumlu kalır (geriye dönük kanıtlar)."""

    def test_guvenlik_hatasi(self):
        with self.assertRaises(GuvenlikHatasi) as cm:
            guvenlik.guvenli_yol("/etc/passwd", kok="/tmp")
        e = cm.exception
        self.assertIsInstance(e, ValueError)  # geriye uyumluluk
        self.assertEqual(e.tip, "guvenlik")
        self.assertTrue(e.oneri)

    def test_veri_hatasi_tekil_matris(self):
        with self.assertRaises(VeriHatasi) as cm:
            regresyon._gauss_coz([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0])
        self.assertEqual(cm.exception.tip, "veri")
        self.assertIn("VIF", cm.exception.oneri)

    def test_kullanim_hatasi(self):
        from suc_analizi.arayuz import ortak
        with self.assertRaises(KullanimHatasi) as cm:
            ortak.iki_vektor({"gruplar": {"a": [1], "b": [2], "c": [3]}})
        self.assertEqual(cm.exception.tip, "kullanim")
        self.assertTrue(cm.exception.oneri)

    def test_sinif_hiyerarsisi_ve_tipler(self):
        self.assertEqual(KapiRed.tip, "kapi")
        self.assertEqual(dongu.DonguHatasi.tip, "dongu")
        for s in (KapiRed, dongu.DonguHatasi, VeriHatasi, GuvenlikHatasi,
                  KullanimHatasi):
            self.assertTrue(issubclass(s, SucAnaliziHatasi))

    def _sahte_arac(self, istisna):
        from suc_analizi.arayuz.ortak import ARACLAR
        def fn(a):
            raise istisna
        ARACLAR["sahte_h2"] = {"fn": fn, "aciklama": "t",
                               "sema": {"type": "object",
                                        "properties": {}},
                               "politika": {"sinif": "veri_hazirlama",
                                            "gate": None,
                                            "muafiyet_gerekcesi": "sentetik test",
                                            "insan_onayi": False,
                                            "iz_zorunlu": False,
                                            "veri_sinifi": "sentetik",
                                            "butce_turu": "dogrusal"}}
        self.addCleanup(lambda: ARACLAR.pop("sahte_h2", None))

    def test_sunucu_esleme_veri_tipi(self):
        from suc_analizi.arayuz import sunucu
        self._sahte_arac(VeriHatasi("n yetersiz", oneri="daha fazla veri"))
        r = sunucu.isle({"method": "tools/call", "id": 9,
                         "params": {"name": "sahte_h2", "arguments": {}}})
        metin = r["result"]["content"][0]["text"]
        self.assertTrue(r["result"]["isError"])
        self.assertIn("HATA [veri]: n yetersiz", metin)
        self.assertIn("ÖNERİ: daha fazla veri", metin)

    def test_sunucu_esleme_sistem_tipi(self):
        from suc_analizi.arayuz import sunucu
        self._sahte_arac(RuntimeError("gizli iç ayrıntı"))
        r = sunucu.isle({"method": "tools/call", "id": 10,
                         "params": {"name": "sahte_h2", "arguments": {}}})
        metin = r["result"]["content"][0]["text"]
        self.assertIn("HATA [sistem]:", metin)
        self.assertNotIn("gizli iç ayrıntı", metin)  # traceback sızmaz


class TestH62_ProtokolAnlasmasi(unittest.TestCase):
    """H6.2: initialize desteklenen sürümleri beyan eder; bilinmeyen
    istemci sürümü reddedilmez, uyarı notuyla devam edilir."""

    def _init(self, v):
        from suc_analizi.arayuz import sunucu
        return sunucu.isle({"method": "initialize", "id": 1,
                            "params": {"protocolVersion": v,
                                       "capabilities": {},
                                       "clientInfo": {"name": "t",
                                                      "version": "0"}}})

    def test_bilinen_surum_uyarisiz(self):
        r = self._init("2024-11-05")["result"]
        self.assertEqual(r["protocolVersion"], "2024-11-05")
        self.assertIn("2024-11-05", r["desteklenenProtokoller"])
        self.assertNotIn("protokolUyari", r)

    def test_bilinmeyen_surum_uyariyla_devam(self):
        r = self._init("2025-06-18")["result"]
        self.assertEqual(r["protocolVersion"], "2024-11-05")  # düşmez
        self.assertIn("2025-06-18", r["protokolUyari"])
        self.assertIn("serverInfo", r)


if __name__ == "__main__":
    unittest.main()
