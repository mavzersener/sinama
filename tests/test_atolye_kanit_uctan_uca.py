# -*- coding: utf-8 -*-
"""
test_atolye_kanit_uctan_uca.py — A6 eşdeğerlik E2: DataFlow `kanit-uctan-uca` testlerinin
karşılıkları (8).

Bu senaryoların yarısı ön yüzün kanıt düğümünü (JS yürütücü) sınar; o kod Sınama'da
DEĞİŞTİRİLMEDEN taşındı. Karşılık bu yüzden "Python sunucu + aynı JS yürütücü"dür:
gerçek Sınama arka ucu (uvicorn, 127.0.0.1, geçici veri kökü) kurulur, JS senaryoları
(`atolye/tests/sinama/kanit-uctan-uca.sinama.ts`) ona karşı vitest ile koşar ve her
DataFlow testinin karşılığı aşağıda adıyla denetlenir. Node, Atölye bağımlılıkları
(`npm ci`), uvicorn ya da cryptography yoksa atlanır.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATOLYE = os.path.join(KOK, "uygulama", "atolye")
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "cekirdek"))

try:
    import uvicorn
    from uygulama import kanit_defteri  # noqa: F401 — cryptography denetimi
    from uygulama import sunucu as uyg
except ImportError:   # pragma: no cover
    uyg = None
NPX = shutil.which("npx")
HAZIR = uyg is not None and NPX and os.path.isdir(os.path.join(ATOLYE, "node_modules", "vitest"))

YURUTUCU = "kanıt paketi — yürütücü + defter"
DOGRULAYICI = "kanıt paketi — bağımsız Python doğrulayıcısı"


def bos_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(HAZIR, "node/npx, atolye node_modules, uvicorn ya da cryptography yok")
class TestKanitUctanUca(unittest.TestCase):
    sonuclar = {}

    @classmethod
    def setUpClass(cls):
        cls.kok = tempfile.mkdtemp(prefix="sinama_kanit_uu_")
        cls.eski = {k: os.environ.get(k) for k in ("SINAMA_VERI_KOKU", "SINAMA_LOG_DIR")}
        app = cls.app = uyg.uygulama_olustur(veri_koku=cls.kok, dil_modeli_url=None)
        port = bos_port()
        cls.sunucu = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        cls.iplik = threading.Thread(target=cls.sunucu.run, daemon=True)
        cls.iplik.start()
        bitis = time.time() + 30
        while not cls.sunucu.started and time.time() < bitis:
            time.sleep(0.05)
        rapor = os.path.join(cls.kok, "vitest.json")
        r = subprocess.run([NPX, "vitest", "run", "--config", "vitest.sinama.config.ts", "--reporter=json",
                            f"--outputFile={rapor}"], cwd=ATOLYE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600,
                           env={**os.environ, "SINAMA_ATOLYE_URL": f"http://127.0.0.1:{port}",
                                "SINAMA_KANIT_DIZINI": os.path.join(cls.kok, "kanit"),
                                "KANIT_PY": sys.executable, "PYTHONUTF8": "1"},
                           shell=sys.platform == "win32")
        cls.cikti = r.stdout[-3000:] + r.stderr[-3000:]
        if os.path.exists(rapor):
            with open(rapor, encoding="utf-8") as f:
                for dosya in json.load(f)["testResults"]:
                    for a in dosya["assertionResults"]:
                        cls.sonuclar[" › ".join(a["ancestorTitles"] + [a["title"]])] = (
                            a["status"], " ".join(a.get("failureMessages") or [])[:1500])

    @classmethod
    def tearDownClass(cls):
        cls.sunucu.should_exit = True
        cls.iplik.join(timeout=10)
        cls.app.state.atolye["depo"].kapat()
        for k, v in cls.eski.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        shutil.rmtree(cls.kok, ignore_errors=True)

    def gecti(self, ad):
        self.assertIn(ad, self.sonuclar, f"JS senaryosu koşmadı: {ad}\n{self.cikti}")
        durum, hata = self.sonuclar[ad]
        self.assertEqual(durum, "passed", hata)

    def test_demo(self):
        # DataFlow: tests/kanit-uctan-uca.test.ts › kanıt paketi — yürütücü + defter › demo veriden paket ÜRETİLMEZ (eskiden "court-admissible" paket çıkıyordu)
        self.gecti(f'{YURUTUCU} › demo veriden paket ÜRETİLMEZ (eskiden "court-admissible" paket çıkıyordu)')

    def test_kayitli(self):
        # DataFlow: tests/kanit-uctan-uca.test.ts › kanıt paketi — yürütücü + defter › gerçek veride KAYITLI: tüm satırların hash'i, oturumdaki aktör, defter sırası
        self.gecti(f"{YURUTUCU} › gerçek veride KAYITLI: tüm satırların hash'i, oturumdaki aktör, defter sırası")

    def test_kayitsiz(self):
        # DataFlow: tests/kanit-uctan-uca.test.ts › kanıt paketi — yürütücü + defter › oturum yoksa paket KAYITSIZ işaretlenir ve bunu söyler
        self.gecti(f"{YURUTUCU} › sunucuya ulaşılamazsa paket KAYITSIZ işaretlenir ve bunu söyler")

    def test_sayi_bicimi(self):
        # DataFlow: tests/kanit-uctan-uca.test.ts › kanıt paketi — bağımsız Python doğrulayıcısı › JS sayı biçimi Python es_sayi ile bayt bayt aynı (RFC 8785)
        self.gecti(f"{DOGRULAYICI} › JS sayı biçimi Python es_sayi ile bayt bayt aynı (RFC 8785)")

    def test_gecerli(self):
        # DataFlow: tests/kanit-uctan-uca.test.ts › kanıt paketi — bağımsız Python doğrulayıcısı › KAYITLI paket + defter: GEÇERLİ (çıkış 0)
        self.gecti(f"{DOGRULAYICI} › KAYITLI paket + defter: GEÇERLİ (çıkış 0)")

    def test_tek_hucre(self):
        # DataFlow: tests/kanit-uctan-uca.test.ts › kanıt paketi — bağımsız Python doğrulayıcısı › tek hücre değiştirilirse BAŞARISIZ (çıkış 1)
        self.gecti(f"{DOGRULAYICI} › tek hücre değiştirilirse BAŞARISIZ (çıkış 1)")

    def test_paket_makbuz(self):
        # DataFlow: tests/kanit-uctan-uca.test.ts › kanıt paketi — bağımsız Python doğrulayıcısı › paket ve makbuz birlikte değiştirilse de imza yakalar (çıkış 1)
        self.gecti(f"{DOGRULAYICI} › paket ve makbuz birlikte değiştirilse de imza yakalar (çıkış 1)")

    def test_kayitsiz_yanlis_anahtar(self):
        # DataFlow: tests/kanit-uctan-uca.test.ts › kanıt paketi — bağımsız Python doğrulayıcısı › KAYITSIZ paket: EKSİK (çıkış 2), yanlış anahtar: BAŞARISIZ (çıkış 1)
        self.gecti(f"{DOGRULAYICI} › KAYITSIZ paket: EKSİK (çıkış 2), yanlış anahtar: BAŞARISIZ (çıkış 1)")


if __name__ == "__main__":
    unittest.main()
