# -*- coding: utf-8 -*-
"""
test_kanit_muhakeme.py — Faz C kanıtları (v6.2):
  K9  olay akışı her adımda delta olarak yazılır; tekrar kaydetme
      olayı ÇOĞALTMAZ (değişmez akış, tek kaynak)
  K10 projeksiyon, manifesto gecmisiyle birebir örtüşür
      (manifesto = akışın anlamsal görünümü)
  K11 olay akışında PII değeri yoktur (anahtar/özet sözleşmesi)
  K12 resmî oturumda gerekçesiz analiz adımı yapısal reddedilir;
      eksik gerekçe alanı reddedilir; keşif oturumu muaftır
  K13 yorumsuz adımla sonuca geçiş yapısal reddedilir
  K14 muhakeme izi olgu/gerekçe görsel ayrımıyla işlenir
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama.surec import dongu, rapor, kanit


def _resmi_dongu():
    d = dongu.AnalizDongusu({"karar": "devriye", "urun_turu": "taktik"})
    d.planla()
    d.veri_bagla({"n": 120, "uyarilar": []})
    d.analize_gec({"uygun": True, "sebepler": ["ok"]})
    return d


GEREKCE = {"hipotez": "hafta sonu gece kümelenmesi",
           "yorum": "NNI z=-3.2, p<0.01; tesadüfle açıklanamaz",
           "cikarim": "Cuma-Ctesi 22-02 devriyesi önerilir",
           "alternatifler": ["raporlama davranışı değişimi",
                             "tek büyük etkinlik etkisi"]}


class TestK9_OlayAkisiDelta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_her_adim_olay_olur_tekrar_cogaltmaz(self):
        d = _resmi_dongu()
        d.analiz_kaydet("nni", {"nni": 0.62}, GEREKCE)
        dongu.kaydet(d, self.tmp)
        dongu.kaydet(d, self.tmp)  # ikinci kayıt: yeni adım yok
        olaylar = kanit.oku(self.tmp, d.manifesto["oturum_id"])
        self.assertEqual(len(olaylar), len(d.manifesto["gecmis"]))
        d.analiz_kaydet("grid_hotspot", {"hucre": 4}, GEREKCE)
        dongu.kaydet(d, self.tmp)
        olaylar2 = kanit.oku(self.tmp, d.manifesto["oturum_id"])
        self.assertEqual(len(olaylar2), len(olaylar) + 1)

    def test_kalici_oturumda_delta_devam_eder(self):
        d = _resmi_dongu()
        d.analiz_kaydet("nni", {"nni": 0.62}, GEREKCE)
        dongu.kaydet(d, self.tmp)
        d2 = dongu.yukle(d.manifesto["oturum_id"], self.tmp)
        d2.analiz_kaydet("trend", {"egim": 0.3}, GEREKCE)
        dongu.kaydet(d2, self.tmp)
        olaylar = kanit.oku(self.tmp, d.manifesto["oturum_id"])
        self.assertEqual(len(olaylar), len(d2.manifesto["gecmis"]))


class TestK10_ProjeksiyonTekKaynak(unittest.TestCase):
    def test_projeksiyon_manifestoyla_ortusur(self):
        tmp = tempfile.mkdtemp()
        d = _resmi_dongu()
        d.analiz_kaydet("nni", {"nni": 0.62}, GEREKCE)
        d.analiz_kaydet("grid_hotspot", {"hucre": 4}, GEREKCE)
        dongu.kaydet(d, tmp)
        olaylar = kanit.oku(tmp, d.manifesto["oturum_id"])
        gorunum = kanit.projeksiyon(olaylar)
        self.assertEqual(gorunum["adim_sayisi"], len(d.manifesto["gecmis"]))
        akis_araclar = [a["arac"] for a in gorunum["adimlar"]]
        gecmis_araclar = [g["arac"] for g in d.manifesto["gecmis"]]
        self.assertEqual(akis_araclar, gecmis_araclar)


class TestK11_PII_Yok(unittest.TestCase):
    def test_olaylar_deger_tasimaz(self):
        tmp = tempfile.mkdtemp()
        d = _resmi_dongu()
        d.analiz_kaydet("frekans", {"tur": "hırsızlık"}, GEREKCE)
        dongu.kaydet(d, tmp)
        ham = open(kanit._akis_yolu(tmp, d.manifesto["oturum_id"]),
                   encoding="utf-8").read()
        for o in kanit.oku(tmp, d.manifesto["oturum_id"]):
            self.assertIn("zaman", o)
            self.assertIn("olay", o)
        # Paket 06: olay şeması sürümlüdür; gerekçe yalnız manifestoda,
        # olayda ise kanonik commitment olarak bulunabilir. v2: "zincir"
        # yapısal sürüm alanıdır (değer taşımaz, PII değil).
        izinli = {"zaman", "surum", "olay", "faz", "ozet",
                  "gerekce_digest", "onceki_hash", "zincir"}
        for o in kanit.oku(tmp, d.manifesto["oturum_id"]):
            self.assertTrue(set(o) <= izinli, f"beklenmedik alan: {set(o) - izinli}")
        # argüman DEĞERİ sızıntısı yok: kişi adı/telefon kalıbı bulunmamalı
        self.assertNotIn("Vatandas", ham)
        self.assertNotIn("0555", ham)


class TestK12_GerekceZorunlu(unittest.TestCase):
    def test_resmi_oturumda_gerekcesiz_red(self):
        d = _resmi_dongu()
        with self.assertRaises(dongu.DonguHatasi):
            d.analiz_kaydet("nni", {"nni": 0.62})

    def test_eksik_alan_red(self):
        d = _resmi_dongu()
        with self.assertRaises(dongu.DonguHatasi):
            d.analiz_kaydet("nni", {"nni": 0.62}, {"hipotez": "x"})

    def test_kesif_oturumu_muaf(self):
        d = dongu.AnalizDongusu({"karar": "keşif: nni"}, mod="kesif")
        d.planla()
        d.veri_bagla({"n": 50})
        d.analize_gec({"uygun": True, "sebepler": []})
        sonuc = d.analiz_kaydet("nni", {"nni": 0.62})  # gerekçesiz olur
        self.assertEqual(sonuc["kaydedildi"], "nni")


class TestK13_YorumsuzSonucRed(unittest.TestCase):
    def test_gercekci_senaryo_eski_manifesto(self):
        d = _resmi_dongu()
        # eski sürümden kalma / elle enjekte edilmiş gerekçesiz adım
        d.manifesto["gecmis"].append(
            {"zaman": "2026-07-01T00:00:00", "faz": "ANALIZ",
             "arac": "grid_hotspot", "ozet": "{...}"})
        with self.assertRaises(dongu.DonguHatasi) as cm:
            d.sonucla("mudahale_onerildi", {"onaylayan": "analist"})
        self.assertIn("yorumsuz", str(cm.exception))


class TestK14_MuhakemeIzi(unittest.TestCase):
    def test_olgu_gerekce_ayrimi(self):
        d = _resmi_dongu()
        d.analiz_kaydet("nni", {"nni": 0.62, "p": 0.001}, GEREKCE)
        iz = rapor.muhakeme_izi(d.manifesto)
        self.assertIn("Muhakeme İzi", iz)
        self.assertIn("OLGU (K1/K2)", iz)
        self.assertIn("GEREKÇE (K3", iz)
        self.assertIn("hafta sonu gece kümelenmesi", iz)
        self.assertIn("raporlama davranışı değişimi", iz)  # alternatifler

    def test_bos_oturum(self):
        d = dongu.AnalizDongusu({"karar": "x"})
        self.assertIn("analiz adımı yok", rapor.muhakeme_izi(d.manifesto))


if __name__ == "__main__":
    unittest.main()


class TestK15_HashZinciri(unittest.TestCase):
    """P2 (v6.4): olay akışı kurcalama-kanıtlı — her kayıt öncekinin
    SHA-256'sına zincirlenir; kanit.dogrula bütünlüğü sınar."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_saglam_zincir(self):
        for i in range(4):
            kanit.olay_yaz(self.tmp, "ot1", {"olay": f"adim{i}",
                                             "faz": "ANALIZ", "ozet": "x"})
        d = kanit.dogrula(self.tmp, "ot1")
        self.assertTrue(d["saglam"])
        self.assertEqual(d["olay_sayisi"], 4)
        self.assertIsNone(d["bozuk_adim"])

    def test_kurcalama_saptanir(self):
        import json as _j
        for i in range(3):
            kanit.olay_yaz(self.tmp, "ot2", {"olay": f"adim{i}",
                                             "faz": "ANALIZ", "ozet": "x"})
        yol = kanit._akis_yolu(self.tmp, "ot2")
        satirlar = open(yol, encoding="utf-8").read().splitlines()
        bozuk = _j.loads(satirlar[1])
        bozuk["ozet"] = "DEĞİŞTİRİLDİ"
        satirlar[1] = _j.dumps(bozuk, ensure_ascii=False)
        open(yol, "w", encoding="utf-8").write("\n".join(satirlar) + "\n")
        d = kanit.dogrula(self.tmp, "ot2")
        self.assertFalse(d["saglam"])
        self.assertEqual(d["bozuk_adim"], 2)  # 1'in değişimi 2'de saptanır

    def test_dongu_kaydet_zincirli(self):
        d = _resmi_dongu()
        d.analiz_kaydet("nni", {"nni": 0.62}, GEREKCE)
        dongu.kaydet(d, self.tmp)
        d.analiz_kaydet("trend", {"egim": 0.1}, GEREKCE)
        dongu.kaydet(d, self.tmp)
        self.assertTrue(kanit.dogrula(self.tmp,
                                      d.manifesto["oturum_id"])["saglam"])
