# -*- coding: utf-8 -*-
"""
test_paket_kimligi.py — testler DOĞRU kodu mu sınıyor? (A2.2)

Hasat anında paket adı `suc_analizi` idi ve kanonik C:\\Projects\\suc_analizi
bu makinenin üç ortamına editable kuruluydu: cekirdek/ dışından yapılan bir
import kanoniği alıyor, test yanlış kodu sınayıp yeşil geçebiliyordu. Ad
`sinama` oldu; bu testler o sınıf hatanın geri dönmesini engeller.
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sinama  # noqa: E402
from sinama.arayuz import sunucu  # noqa: E402


def _ic_mi(yol, kok):
    """yol, kok dizininin içinde mi (büyük/küçük harf ve ayraç duyarsız)."""
    yol, kok = os.path.normcase(os.path.abspath(yol)), os.path.normcase(os.path.abspath(kok))
    return os.path.commonpath([yol, kok]) == kok


class TestPaketKimligi(unittest.TestCase):
    def test_sinama_bu_agactan_gelir(self):
        self.assertTrue(_ic_mi(sinama.__file__, ROOT),
                        f"sinama başka yerden geldi: {sinama.__file__}")

    def test_eski_paket_adi_hicbir_yoldan_yuklenmez(self):
        paket = sunucu.arac_calistir("frekans", {"satirlar": [{"tur": "a"}, {"tur": "b"}],
                                                 "alan": "tur"})
        self.assertIn("sonuc", paket)
        self.assertNotIn("suc_analizi", sys.modules,
                         "sinama kodu kanonik suc_analizi paketine bağımlı hâle gelmiş")

    def test_alt_surec_ayni_agaci_gorur(self):
        # MCP sunucusu ve testlerin açtığı alt süreçler PYTHONPATH=ROOT ile koşar.
        kod = "import sinama, os; print(os.path.abspath(sinama.__file__))"
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1")
            p = subprocess.run([sys.executable, "-c", kod], cwd=tmp, env=env,
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(_ic_mi(p.stdout.strip(), ROOT), p.stdout)

    def test_kurulu_baska_bir_sinama_golgelemez(self):
        # Nötr bir dizinden (PYTHONPATH yok) sinama ya hiç bulunmamalı ya da
        # bu ağacı göstermeli; başka bir kopya kuruluysa bu test kırılır.
        kod = ("import importlib.util, os; s = importlib.util.find_spec('sinama'); "
               "print(os.path.abspath(s.origin) if s else '')")
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            p = subprocess.run([sys.executable, "-c", kod], cwd=tmp, env=env,
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        bulunan = p.stdout.strip()
        if bulunan:
            self.assertTrue(_ic_mi(bulunan, ROOT), f"gölgeleyen kopya: {bulunan}")


if __name__ == "__main__":
    unittest.main()
