# -*- coding: utf-8 -*-
"""06: alternatif girdi kipli araçlarda eksik argüman → tipli kullanım hatası.

DataFlow köprüsündeki tüm-araç duman testi buldu: x/y dizisi VEYA
satirlar+alan kabul eden araçlar şemada hiçbir alanı zorunlu tutamadığı
için, kipin gerektirdiği argüman eksikken adaptör a["alan"] ile KeyError
atıyor ve MCP'de 'sistem', HTTP köprüsünde çıplak 500 dönüyordu.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

from sinama.arayuz import ortak, sunucu
from sinama.cekirdek.hatalar import KullanimHatasi

SATIRLAR = [{"olay_id": f"E{i}", "tur": "a" if i % 2 else "b", "deger": float(i)}
            for i in range(1, 31)]

# Duman testinde KeyError→500 veren araçlar ve eksik bırakılan argümanlar.
VAKALAR = [
    ("anova", {"satirlar": SATIRLAR}),
    ("kruskal_wallis", {"satirlar": SATIRLAR}),
    ("mann_whitney", {"satirlar": SATIRLAR}),
    ("randomizasyon_testi", {"satirlar": SATIRLAR}),
    ("kendall", {"satirlar": SATIRLAR}),
    ("spearman", {"satirlar": SATIRLAR}),
    ("t_testi", {"satirlar": SATIRLAR}),
    ("guc_analizi", {"tip": "oran"}),  # oran kipi p1/p2 ister
]


class TestEksikKip(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = patch.dict(os.environ, SINAMA_LOG_DIR=tmp.name,
                         SINAMA_VERI_KOKU=tmp.name)
        env.start()
        self.addCleanup(env.stop)

    def test_eksik_kip_argumani_kullanim_hatasidir(self):
        for ad, arg in VAKALAR:
            with self.subTest(arac=ad):
                with self.assertRaises(KullanimHatasi) as ctx:
                    sunucu.arac_calistir(ad, arg)
                self.assertEqual(ctx.exception.tip, "kullanim")
                self.assertIn(f"{ad}.", str(ctx.exception))

    def test_mcp_yolu_da_sistem_degil_kullanim_der(self):
        r = sunucu.isle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": "anova",
                                    "arguments": {"satirlar": SATIRLAR}}})
        metin = r["result"]["content"][0]["text"]
        self.assertTrue(r["result"]["isError"])
        self.assertTrue(metin.startswith("HATA [kullanim]"), metin)

    def test_ic_keyerror_maskelenmez(self):
        # Şemada OLMAYAN anahtarın KeyError'ı gerçek bir iç hatadır;
        # kullanıcı hatasına çevrilip gizlenmemeli.
        kayit = ortak.ARACLAR["frekans"]
        with patch.dict(kayit, fn=lambda a: {}["ic_anahtar"]):
            with self.assertRaises(KeyError):
                sunucu.arac_calistir("frekans", {"satirlar": SATIRLAR, "alan": "tur"})

    def test_verilmis_argumanin_keyerror_u_maskelenmez(self):
        # 'alan' verilmiş ama araç içinde yine KeyError('alan') doğarsa bu
        # eksik argüman değil iç hatadır.
        kayit = ortak.ARACLAR["frekans"]
        with patch.dict(kayit, fn=lambda a: {}["alan"]):
            with self.assertRaises(KeyError):
                sunucu.arac_calistir("frekans", {"satirlar": SATIRLAR, "alan": "tur"})


if __name__ == "__main__":
    unittest.main()
