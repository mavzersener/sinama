# -*- coding: utf-8 -*-
"""
test_a7_dondur.py — dondurma betiği (betikler/a7_dondur.py) GERÇEK kaynak depolara dokunmadan,
geçici git depolarında sınanır: kuru çalıştırma hiçbir şey yazmaz; uygulama tek commit + etiket
üretir; kaynak deponun kancası reddederse iz kalmaz; ön koşul tutmazsa yazılmaz.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "betikler"))

import a7_dondur  # noqa: E402

GIT = shutil.which("git")


def git(yol, *arg):
    return subprocess.run(["git", "-C", yol, *arg], capture_output=True, text=True, check=True,
                          encoding="utf-8").stdout.strip()


@unittest.skipUnless(GIT, "git yok")
class TestDondurma(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp(prefix="dondur_")
        self.depo = os.path.join(self.dizin, "kaynak")
        os.makedirs(self.depo)
        git(self.depo, "init", "-q")
        git(self.depo, "config", "user.email", "test@ornek.invalid")
        git(self.depo, "config", "user.name", "test")
        git(self.depo, "config", "core.autocrlf", "false")
        with open(os.path.join(self.depo, "README.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("# Kaynak\n\nAçıklama.\n")
        git(self.depo, "add", "README.md")
        git(self.depo, "commit", "-q", "-m", "ilk")
        self.taban = git(self.depo, "rev-parse", "--short", "HEAD")
        self.eski = a7_dondur.DEPOLAR
        a7_dondur.DEPOLAR = {"suc_analizi": {**self.eski["suc_analizi"], "yol": self.depo, "taban": self.taban}}

    def tearDown(self):
        a7_dondur.DEPOLAR = self.eski
        shutil.rmtree(self.dizin, ignore_errors=True)

    def kos(self, *arg):
        cikti = io.StringIO()
        with redirect_stdout(cikti):
            kod = a7_dondur.main(list(arg))
        return kod, cikti.getvalue()

    def test_kuru_calistirma_yazmaz(self):
        kod, cikti = self.kos()
        self.assertEqual(kod, 0)
        self.assertIn("HAZIR", cikti)
        self.assertEqual(git(self.depo, "rev-parse", "--short", "HEAD"), self.taban)
        self.assertEqual(git(self.depo, "status", "--porcelain"), "")
        self.assertEqual(git(self.depo, "tag"), "")

    def test_uygula_depo_istemeden_reddeder(self):
        with self.assertRaises(SystemExit):
            with redirect_stdout(io.StringIO()), unittest.mock.patch("sys.stderr", io.StringIO()):
                a7_dondur.main(["--uygula"])

    def test_uygula(self):
        kod, cikti = self.kos("--uygula", "--depo", "suc_analizi")
        self.assertEqual(kod, 0, cikti)
        self.assertEqual(git(self.depo, "rev-list", "--count", "HEAD"), "2")
        self.assertEqual(git(self.depo, "tag"), a7_dondur.ETIKET)
        self.assertEqual(git(self.depo, "rev-parse", f"{a7_dondur.ETIKET}^{{commit}}"), git(self.depo, "rev-parse", "HEAD"))
        with open(os.path.join(self.depo, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        self.assertTrue(readme.startswith("> **DONDURULDU"))
        self.assertTrue(readme.endswith("# Kaynak\n\nAçıklama.\n"))   # eski içerik korunur
        self.assertTrue(os.path.isfile(os.path.join(self.depo, "DONDURULDU.md")))
        self.assertEqual(git(self.depo, "status", "--porcelain"), "")
        # İkinci kez: etiket var → hazır değil, yazılmaz.
        kod, cikti = self.kos("--uygula", "--depo", "suc_analizi")
        self.assertEqual(kod, 1)
        self.assertEqual(git(self.depo, "rev-list", "--count", "HEAD"), "2")

    def test_kanca_reddederse_iz_kalmaz(self):
        kanca = os.path.join(self.depo, ".git", "hooks", "pre-commit")
        with open(kanca, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\necho kapı reddetti\nexit 1\n")
        os.chmod(kanca, 0o755)
        kod, cikti = self.kos("--uygula", "--depo", "suc_analizi")
        self.assertEqual(kod, 1)
        self.assertIn("BAŞARISIZ", cikti)
        self.assertEqual(git(self.depo, "rev-list", "--count", "HEAD"), "1")
        self.assertEqual(git(self.depo, "status", "--porcelain", "--untracked-files=all"), "")
        self.assertEqual(git(self.depo, "tag"), "")

    def test_kirli_ya_da_yeni_commit(self):
        with open(os.path.join(self.depo, "README.md"), "a", encoding="utf-8") as f:
            f.write("değişti\n")
        kod, cikti = self.kos("--uygula", "--depo", "suc_analizi")
        self.assertEqual(kod, 1)
        self.assertIn("✗ izlenen dosyalarda değişiklik yok", cikti)
        git(self.depo, "commit", "-q", "-am", "hasattan sonra")
        kod, cikti = self.kos()
        self.assertIn("✗ hasattan sonra yeni commit yok", cikti)
        self.assertNotIn(a7_dondur.ETIKET, git(self.depo, "tag"))


if __name__ == "__main__":
    unittest.main()
