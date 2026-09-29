import os
import subprocess
import sys
import unittest
import io
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
from unittest import mock

import kapsam_olc


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestTestKapisi(unittest.TestCase):
    def _check_process(self, condition, optimize=False):
        code = (
            "from test_mcp import check; "
            f"check('sentetik', {condition})"
        )
        cmd = [sys.executable]
        if optimize:
            cmd.append("-O")
        cmd += ["-c", code]
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", timeout=10)

    def test_check_true_false_ve_optimizasyon(self):
        for optimize in (False, True):
            self.assertEqual(self._check_process("True", optimize).returncode, 0)
            self.assertNotEqual(self._check_process("False", optimize).returncode, 0)

    def test_import_alt_surec_baslatmaz(self):
        p = self._check_process("True")
        self.assertNotIn("TEST BİTTİ", p.stdout)
        self.assertIn("sentetik: True", p.stdout)

    def test_kapsam_basarisiz_testi_fataldir(self):
        code = (
            "import kapsam_olc; "
            "kapsam_olc.olc=lambda: ({}, type('R',(),{'wasSuccessful':lambda s:False})()); "
            "kapsam_olc.sys.argv=['kapsam_olc.py']; "
            "raise SystemExit(kapsam_olc.main())"
        )
        p = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("taban güncellenmedi", p.stdout)

    def test_import_hicbir_yan_etki_uretmez(self):
        code = """
from unittest.mock import patch
with patch('subprocess.Popen', side_effect=AssertionError('process')), \
     patch('os.makedirs', side_effect=AssertionError('mkdir')), \
     patch('random.seed', side_effect=AssertionError('seed')):
    import test_mcp
"""
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1")
            p = subprocess.run([sys.executable, "-c", code], cwd=tmp, env=env,
                               capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout, "")
            self.assertEqual(os.listdir(tmp), [])

    def test_kapsam_basari_esik_alti_ve_bos_rapor(self):
        with tempfile.TemporaryDirectory() as tmp:
            taban = Path(tmp) / "taban.json"
            taban.write_text('{"sinama/cekirdek/a.py": 80}', encoding="utf-8")
            result = mock.Mock()
            result.wasSuccessful.return_value = True
            for report, expected in (({"sinama/cekirdek/a.py": (9, 1)}, 0),
                                     ({"sinama/cekirdek/a.py": (7, 3)}, 1), ({}, 1)):
                with self.subTest(report=report), redirect_stdout(io.StringIO()), \
                     mock.patch.object(kapsam_olc, "TABAN_DOSYA", str(taban)), \
                     mock.patch.object(kapsam_olc, "olc", return_value=(report, result)):
                    self.assertEqual(kapsam_olc.main([]), expected)

    def test_basarisiz_test_taban_guncelleyemez(self):
        with tempfile.TemporaryDirectory() as tmp:
            taban = Path(tmp) / "taban.json"
            taban.write_text('{"koru": 90}', encoding="utf-8")
            before = taban.read_bytes()
            result = mock.Mock()
            result.wasSuccessful.return_value = False
            with redirect_stdout(io.StringIO()), \
                 mock.patch.object(kapsam_olc, "TABAN_DOSYA", str(taban)), \
                 mock.patch.object(kapsam_olc, "olc", return_value=({"a": (1, 0)}, result)):
                self.assertNotEqual(kapsam_olc.main(["--taban-guncelle"]), 0)
            self.assertEqual(taban.read_bytes(), before)

    def test_coverdir_mevcut_dosyalar_korunur_ayri_cagri_ayri_dizin(self):
        with tempfile.TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / "onceki.cover"
            sentinel.write_text("sentetik önceki sonuç", encoding="utf-8")
            used = []
            def measure(hedef_paket, coverdir):
                used.append(coverdir)
                self.assertNotEqual(Path(coverdir), Path(tmp))
                self.assertTrue(Path(coverdir).is_dir())
                return {}, mock.Mock()
            with mock.patch.object(kapsam_olc, "_olc_dizinde", side_effect=measure):
                kapsam_olc.olc(coverdir=tmp)
                kapsam_olc.olc(coverdir=tmp)
                kapsam_olc.olc()
            self.assertEqual(len(set(used)), 3)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentetik önceki sonuç")
            self.assertFalse(Path(used[-1]).exists())

    def test_mcp_timeout_sonrasi_process_ve_pipe_kapanir(self):
        from test_mcp import MCPProcess
        p = MCPProcess(dict(os.environ), command=[sys.executable, "-c",
                       "import time; time.sleep(60)"], timeout=0.05)
        try:
            with self.assertRaises(AssertionError):
                p.recv()
        finally:
            p.close()
        self.assertIsNotNone(p.p.poll())
        self.assertTrue(all(s.closed for s in (p.p.stdin, p.p.stdout, p.p.stderr)))
        self.assertTrue(all(not t.is_alive() for t in p.threads))

    def test_mcp_yazma_timeout_ve_eof(self):
        from test_mcp import MCPProcess
        p = MCPProcess(dict(os.environ), command=[sys.executable, "-c",
                       "import time; time.sleep(60)"], timeout=0.05)
        try:
            with self.assertRaisesRegex(AssertionError, "yazma zaman aşımı"):
                p.send({"sentetik": "x" * 2000000})
        finally:
            p.close()
        self.assertTrue(all(not t.is_alive() for t in p.threads))
        p = MCPProcess(dict(os.environ), command=[sys.executable, "-c", "pass"])
        try:
            with self.assertRaisesRegex(AssertionError, "kapandı"):
                p.recv()
        finally:
            p.close()

    def test_gercek_main_check_hatasinda_temizlik_ve_O_exit(self):
        # Tam tur değil: ilk initialize assertion'ına hata enjekte edilir.
        code = """
import os
import test_mcp as m
original_check, original_process = m.check, m.MCPProcess
processes, roots = [], []
def create(env):
    roots.append(os.path.dirname(env['SINAMA_LOG_DIR']))
    p = original_process(env)
    processes.append(p)
    return p
def fail(label, condition):
    original_check(label, False if label == 'initialize' else condition)
m.MCPProcess, m.check = create, fail
try:
    m.main()
finally:
    if not processes or any(p.p.poll() is None for p in processes):
        raise RuntimeError('process kaldı')
    if any(not s.closed for p in processes for s in (p.p.stdin, p.p.stdout, p.p.stderr)):
        raise RuntimeError('pipe kaldı')
    if any(t.is_alive() for p in processes for t in p.threads):
        raise RuntimeError('thread kaldı')
    if any(os.path.exists(root) for root in roots):
        raise RuntimeError('geçici dizin kaldı')
    print('TEMIZLIK_OK')
"""
        p = subprocess.run([sys.executable, "-O", "-c", code], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("AssertionError: initialize", p.stderr)
        self.assertIn("TEMIZLIK_OK", p.stdout)
        self.assertNotIn("TEST BİTTİ", p.stdout)

    def test_olc_unittest_sonucunu_saklar_pathi_geri_koyar(self):
        result = unittest.TestResult()
        result.failures.append((None, "sentetik hata"))
        tracer = mock.Mock()
        tracer.runfunc.side_effect = lambda fn: fn()
        old_path = sys.path[:]
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(kapsam_olc.trace, "Trace", return_value=tracer), \
             mock.patch.object(kapsam_olc.unittest, "TestLoader") as loader, \
             mock.patch.object(kapsam_olc.unittest, "TextTestRunner") as runner:
            loader.return_value.loadTestsFromName.return_value = unittest.TestSuite()
            runner.return_value.run.return_value = result
            report, actual = kapsam_olc._olc_dizinde("sinama/cekirdek", tmp)
        self.assertIs(actual, result)
        self.assertFalse(actual.wasSuccessful())
        self.assertEqual(report, {})
        self.assertEqual(sys.path, old_path)

    def test_cli_gecersiz_arguman_2(self):
        p = subprocess.run([sys.executable, "kapsam_olc.py", "--yok"], cwd=ROOT,
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 2)

    def test_taban_guncelleme_eski_siniri_dusurmez(self):
        with tempfile.TemporaryDirectory() as tmp:
            taban = Path(tmp) / "taban.json"
            taban.write_text('{"a": 90}', encoding="utf-8")
            result = mock.Mock()
            result.wasSuccessful.return_value = True
            # Yuvarlama toleransında olsa bile 90 -> 89.9 düşüş yasak.
            with redirect_stdout(io.StringIO()), \
                 mock.patch.object(kapsam_olc, "TABAN_DOSYA", str(taban)), \
                 mock.patch.object(kapsam_olc, "olc", return_value=({"a": (899, 101)}, result)):
                self.assertEqual(kapsam_olc.main(["--taban-guncelle"]), 0)
            import json
            self.assertEqual(json.loads(taban.read_text(encoding="utf-8")), {"a": 90})

if __name__ == "__main__":
    unittest.main()
