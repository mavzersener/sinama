import json
import os
import tempfile
import unittest
from unittest.mock import patch

from suc_analizi.cekirdek.hatalar import GuvenlikHatasi
from suc_analizi.surec import dongu, kanit


class TestOturumYolu(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.tmp = self.directory.name

    def test_kimlikler_tam_eslesme_ile_sinirli(self):
        for kimlik in ("ot2", "synthetic_chain", "A-1_2"):
            self.assertTrue(kanit._akis_yolu(self.tmp, kimlik).endswith(
                kimlik + ".olaylar.jsonl"))
        for kimlik in ("../outside", r"..\outside", r"C:\relative",
                       r"\\server\share", "a:b", "", None, [], "a.b", "a/b"):
            with self.assertRaises(GuvenlikHatasi, msg=kimlik):
                kanit._akis_yolu(self.tmp, kimlik)

    def test_okuma_yolu_dizin_olusturmaz(self):
        olmayan = os.path.join(self.tmp, "yeni")
        self.assertEqual(kanit.oku(olmayan, "ot2"), [])
        self.assertFalse(os.path.exists(os.path.join(olmayan, "oturumlar")))

    def test_manifesto_ve_akis_normal_kimlikle_kaydedilir(self):
        d = dongu.AnalizDongusu({"karar": "test", "urun_turu": "taktik"},
                                oturum_id="synthetic_chain")
        d.planla()
        dongu.kaydet(d, self.tmp)
        self.assertEqual(dongu.yukle("synthetic_chain", self.tmp).manifesto[
            "oturum_id"], "synthetic_chain")
        self.assertEqual(len(kanit.oku(self.tmp, "synthetic_chain")), 1)

    def test_manifesto_yolu_kacisi_reddeder(self):
        with self.assertRaises(GuvenlikHatasi):
            dongu.yukle("../outside", self.tmp)
        with self.assertRaises(GuvenlikHatasi):
            kanit.dogrula(self.tmp, r"..\outside")

    def test_listele_bozuk_manifestoyu_sessizce_islemez(self):
        os.makedirs(os.path.join(self.tmp, "oturumlar"))
        with open(os.path.join(self.tmp, "oturumlar", "bozuk.json"),
                  "w", encoding="utf-8") as f:
            json.dump({}, f)
        with self.assertRaises(dongu.DonguHatasi):
            dongu.listele(self.tmp)

    def test_atomik_yazim_sabit_temp_dosyasina_dokunmaz(self):
        path = os.path.join(self.tmp, "example.json")
        sentinel = path + ".tmp"
        with open(sentinel, "w", encoding="utf-8") as stream:
            stream.write("koru")
        kanit.atomik_json_yaz(path, {"n": 1})
        with open(sentinel, encoding="utf-8") as stream:
            self.assertEqual(stream.read(), "koru")
        with patch.object(kanit.os, "replace", side_effect=OSError("sentetik")):
            with self.assertRaises(OSError):
                kanit.atomik_json_yaz(path, {"n": 2})
        with open(path, encoding="utf-8") as stream:
            self.assertEqual(json.load(stream), {"n": 1})
        self.assertFalse(any(name.startswith(".oturum_") for name in os.listdir(self.tmp)))

    def test_symlink_kacisi_reddedilir(self):
        d = os.path.join(self.tmp, "oturumlar")
        dis_directory = tempfile.TemporaryDirectory()
        self.addCleanup(dis_directory.cleanup)
        dis = dis_directory.name
        try:
            os.symlink(dis, d, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Windows ortamı sembolik bağ oluşturmaya izin vermedi")
        with self.assertRaises(GuvenlikHatasi):
            kanit._akis_yolu(self.tmp, "ot2", olustur=True)


if __name__ == "__main__":
    unittest.main()
