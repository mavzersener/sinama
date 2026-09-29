# -*- coding: utf-8 -*-
"""
test_surum.py — sürüm tutarlılığı (H6.3): dört kaynak tek gerçek.
__init__.__version__ == ortak.SURUM == pyproject.version == CHANGELOG
başlığı. Sürüm yükseltirken birini unutmak yapısal olarak yakalanır.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSurumTutarliligi(unittest.TestCase):
    def test_dort_kaynak_tek_gercek(self):
        from suc_analizi import __version__ as v1
        from suc_analizi.arayuz.ortak import SURUM as v2
        with open(os.path.join(KOK, "pyproject.toml"),
                  encoding="utf-8") as f:
            v3 = re.search(r'^version\s*=\s*"([^"]+)"', f.read(),
                           re.M).group(1)
        with open(os.path.join(KOK, "CHANGELOG.md"),
                  encoding="utf-8") as f:
            cl = f.read()
        self.assertEqual(v1, v2, "init ↔ ortak uyuşmazlığı")
        self.assertEqual(v1, v3, "init ↔ pyproject uyuşmazlığı")
        self.assertIn(f"[{v1}]", cl, f"CHANGELOG'da [{v1}] başlığı yok")


if __name__ == "__main__":
    unittest.main()
