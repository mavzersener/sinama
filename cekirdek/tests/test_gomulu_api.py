# -*- coding: utf-8 -*-
"""Gömülü kullanım sözleşmesi: sunucu.arac_calistir.

DataFlow ml-service köprüsü iç ayrıntı olan _arac_yurut'u bağlamsız
çağırıyordu; istek bağlamı (istek_baglam) gelince gate'siz iz-zorunlu 23
araç AttributeError'la çöktü, diğerlerinde satir/kesildi/uyarı metadatası
sessizce kayboldu. Bu testler kamusal girişin MCP yoluyla aynı paketi
ürettiğini ve bağlamsız iç çağrının artık sebebini söyleyerek durduğunu
sabitler.
"""
import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from sinama.arayuz import sunucu
from sinama.arayuz.istek_baglam import baglam
from sinama.arayuz.ortak import AracSemaHatasi
from sinama.cekirdek import veri
from sinama.cekirdek.hatalar import KullanimHatasi, SucAnaliziHatasi

SATIRLAR = [
    {"olay_id": f"E{i}", "tur": "hirsizlik" if i % 3 else "gasp",
     "grid_id": f"G{i % 4}", "zaman": f"2026-01-{(i % 28) + 1:02d}T10:00:00",
     "lat": 41.0 + (i % 5) * 0.004, "lon": 29.0 + (i % 7) * 0.004}
    for i in range(1, 41)
]


class TestGomuluApi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = patch.dict(os.environ, SINAMA_LOG_DIR=self.tmp.name,
                         SINAMA_VERI_KOKU=self.tmp.name)
        env.start()
        self.addCleanup(env.stop)

    def mcp(self, ad, arg):
        """Aynı çağrıyı MCP tools/call yolundan geçirip paketi döner."""
        r = sunucu.isle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": ad, "arguments": arg}})
        self.assertFalse(r["result"]["isError"], r)
        return json.loads(r["result"]["content"][0]["text"])

    def test_gatesiz_iz_zorunlu_arac_baglam_disindan_calisir(self):
        # Eski köprüde tam bu çağrı 500 "beklenmeyen hata: AttributeError"du.
        paket = sunucu.arac_calistir("frekans", {"satirlar": SATIRLAR, "alan": "tur"})
        self.assertEqual(paket["sonuc"]["hirsizlik"] + paket["sonuc"]["gasp"], 40)
        self.assertEqual(paket["meta"]["satir"], 40)  # bağlamsız yolda None'dı
        self.assertIs(paket["meta"]["kesildi"], False)
        self.assertIn("oturum_izlendi", paket["meta"])  # keşif izi açıldı

    def test_mcp_ile_birebir_ayni_paket(self):
        for ad, arg in [("frekans", {"satirlar": SATIRLAR, "alan": "tur"}),
                        ("grid_hotspot", {"satirlar": SATIRLAR, "hucre_km": 0.5})]:
            with self.subTest(arac=ad):
                self.assertEqual(sunucu.arac_calistir(ad, copy.deepcopy(arg)),
                                 self.mcp(ad, copy.deepcopy(arg)))

    def test_gateli_arac_gate_metasini_tasir(self):
        paket = sunucu.arac_calistir("grid_hotspot",
                                     {"satirlar": SATIRLAR, "hucre_km": 0.5})
        self.assertIn("gate", paket["meta"])
        self.assertTrue(paket["meta"]["gate"]["uygun"])
        self.assertFalse(any(k.startswith("_") for k in paket["meta"]["gate"]))

    def test_kesilme_metadatada_gorunur(self):
        with patch.object(veri, "MAKS_SATIR", 10):
            paket = sunucu.arac_calistir("frekans", {"satirlar": SATIRLAR, "alan": "tur"})
        self.assertEqual(paket["meta"]["satir"], 10)
        self.assertIs(paket["meta"]["kesildi"], True)

    def test_cagiranin_argumani_degismez(self):
        arg = {"satirlar": copy.deepcopy(SATIRLAR), "alan": "tur"}
        eski = copy.deepcopy(arg)
        sunucu.arac_calistir("frekans", arg)
        self.assertEqual(arg, eski)

    def test_hatalar_tipli_yayilir(self):
        with self.assertRaises(KullanimHatasi):
            sunucu.arac_calistir("boyle_arac_yok", {})
        with self.assertRaises(KullanimHatasi):
            sunucu.arac_calistir("frekans", [("alan", "tur")])
        with self.assertRaises(AracSemaHatasi) as ctx:
            sunucu.arac_calistir("frekans", {"satirlar": SATIRLAR})  # 'alan' eksik
        self.assertEqual(ctx.exception.tip, "kullanim")

    def test_baglam_her_durumda_kapanir(self):
        sunucu.arac_calistir("frekans", {"satirlar": SATIRLAR, "alan": "tur"})
        self.assertIsNone(baglam())
        with self.assertRaises(SucAnaliziHatasi):
            sunucu.arac_calistir("frekans", {"satirlar": SATIRLAR})
        self.assertIsNone(baglam())

    def test_ic_yol_baglamsiz_sebebini_soyler(self):
        with self.assertRaises(RuntimeError) as ctx:
            sunucu._arac_yurut("frekans", {"satirlar": SATIRLAR, "alan": "tur"})
        self.assertIn("arac_calistir", str(ctx.exception))

    def test_kamusal_adlarda(self):
        self.assertIn("arac_calistir", sunucu.__all__)


if __name__ == "__main__":
    unittest.main()
