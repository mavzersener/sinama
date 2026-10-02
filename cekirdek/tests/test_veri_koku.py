# -*- coding: utf-8 -*-
"""
test_veri_koku.py — A5.1 (ADR-003 md. 3): veri kökü ve oturum dizini çalışma
dizinine DÜŞMEZ. Ortam değişkeni yoksa platformun kullanıcı veri dizini.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama.arayuz import ortak  # noqa: E402
from sinama.cekirdek import guvenlik  # noqa: E402


class TestVarsayilanKok(unittest.TestCase):
    def test_windows_localappdata(self):
        with mock.patch.object(guvenlik.os, "name", "nt"), \
                mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Kullanici\AppData\Local"}):
            self.assertEqual(guvenlik.varsayilan_veri_koku(),
                             os.path.join(r"C:\Kullanici\AppData\Local", "sinama"))

    def test_xdg_ve_ev_dizini(self):
        with mock.patch.object(guvenlik.os, "name", "posix"), \
                mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/veri/xdg"}):
            self.assertEqual(guvenlik.varsayilan_veri_koku(), os.path.join("/veri/xdg", "sinama"))
        ortam = {k: v for k, v in os.environ.items() if k != "XDG_DATA_HOME"}
        with mock.patch.object(guvenlik.os, "name", "posix"), mock.patch.dict(os.environ, ortam, clear=True):
            self.assertEqual(guvenlik.varsayilan_veri_koku(),
                             os.path.join(os.path.expanduser("~"), ".local", "share", "sinama"))


class TestCalismaDizinineDusmez(unittest.TestCase):
    def test_ortam_yokken_cwd_degil(self):
        ortam = {k: v for k, v in os.environ.items() if k not in ("SINAMA_VERI_KOKU", "SINAMA_LOG_DIR")}
        gecici = tempfile.mkdtemp(prefix="cwd_")
        eski = os.getcwd()
        try:
            os.chdir(gecici)
            with mock.patch.dict(os.environ, ortam, clear=True):
                self.assertNotEqual(guvenlik.veri_koku(), os.path.realpath(gecici))
                self.assertEqual(guvenlik.veri_koku(), os.path.realpath(guvenlik.varsayilan_veri_koku()))
                self.assertEqual(ortak._log_dir(), guvenlik.veri_koku())
        finally:
            os.chdir(eski)

    def test_ortam_degiskenleri_oncelikli(self):
        with mock.patch.dict(os.environ, {"SINAMA_VERI_KOKU": "/a/veri", "SINAMA_LOG_DIR": "/b/log"}):
            self.assertEqual(guvenlik.veri_koku(), os.path.realpath("/a/veri"))
            self.assertEqual(ortak._log_dir(), "/b/log")
        with mock.patch.dict(os.environ, {"SINAMA_VERI_KOKU": "/a/veri"}):
            os.environ.pop("SINAMA_LOG_DIR", None)
            self.assertEqual(ortak._log_dir(), os.path.realpath("/a/veri"))


if __name__ == "__main__":
    unittest.main()
