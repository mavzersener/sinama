# -*- coding: utf-8 -*-
"""Veri bekçisi testleri (ADR-001 md.5).

Sır ve kişisel veri örnekleri bu dosyada LİTERAL olarak durmaz, çalışma
anında parçalardan kurulur — yoksa bekçi kendi testini haklı olarak reddeder.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "betikler"))
import veri_bekcisi as vb  # noqa: E402


def tc_uret(ilk9):
    """İlk 9 haneden sağlama toplamı geçerli bir TC dizgesi kurar."""
    d = [int(c) for c in ilk9]
    d10 = (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10
    d11 = (sum(d) + d10) % 10
    return ilk9 + str(d10) + str(d11)


def github_token():
    return "gh" + "p_" + "A1" * 20


def kurallar(bulgular):
    return [kural for _, kural, _ in bulgular]


class YolKurallari(unittest.TestCase):
    def test_veri_dosyasi_yalniz_sentetik_altinda(self):
        self.assertTrue(vb.yol_denetle("veri/olaylar.csv", 10))
        self.assertEqual(vb.yol_denetle("tests/sentetik/olaylar.csv", 10), [])
        self.assertTrue(vb.yol_denetle("a/kayit.jsonl", 10))
        self.assertTrue(vb.yol_denetle("suc_analizi_audit.log", 0),
                        "boş log da yasak: içerik değil tür kuralı")

    def test_env_ve_anahtar_her_yerde_yasak(self):
        self.assertTrue(vb.yol_denetle(".env", 10))
        self.assertTrue(vb.yol_denetle("sunucu/prod.env", 10))
        self.assertTrue(vb.yol_denetle("tests/sentetik/imza.pem", 10))
        self.assertEqual(vb.yol_denetle(".env.ornek", 10), [])

    def test_belge_ve_oturum_dizini(self):
        self.assertTrue(vb.yol_denetle("rapor/bilgi_notu.docx", 10))
        self.assertEqual(vb.yol_denetle("tests/sentetik/sablon.docx", 10), [])
        self.assertTrue(vb.yol_denetle("oturumlar/abc123.json", 10))

    def test_kod_dosyasi_adi_veri_olsa_da_serbest(self):
        # 'veri.py' ya da 'kanit/zincir.py' kod modülüdür, veri değil.
        self.assertEqual(vb.yol_denetle("cekirdek/veri.py", 10), [])
        self.assertEqual(vb.yol_denetle("kanit/zincir.py", 10), [])

    def test_boyut_siniri_ve_izin_listesi(self):
        buyuk = vb.BOYUT_SINIRI + 1
        self.assertTrue(vb.yol_denetle("arayuz/logo.png", buyuk))
        self.assertEqual(
            vb.yol_denetle("arayuz/logo.png", buyuk, frozenset({"arayuz/logo.png"})), [])


class IcerikSirlari(unittest.TestCase):
    def test_ozel_anahtar_blogu(self):
        blok = ("-----BEGIN " + "PRIVATE KEY-----\nMIIEv\n").encode()
        b = vb.icerik_denetle(blok)
        self.assertIn("özel anahtar bloğu", kurallar(b))
        self.assertNotIn("MIIEv", str(b))

    def test_token_maskelenir(self):
        token = github_token()
        b = vb.icerik_denetle(f"x = '{token}'\n".encode())
        self.assertIn("GitHub token", kurallar(b))
        self.assertNotIn(token, str(b), "rapor sırrın kendisini sızdırmamalı")

    def test_sir_atamasi_gercek_deger_ile_kod_ayrilir(self):
        self.assertTrue(vb.icerik_denetle(("HARP_TOKEN=" + "ab12" * 5).encode()))
        self.assertEqual(vb.icerik_denetle(b"HARP_TOKEN = os.environ.get('HARP_TOKEN')"), [])
        self.assertEqual(vb.icerik_denetle(b"SESSION_SECRET = ayarlar.oturum_gizli_degeri"), [])

    def test_parolali_url_yer_tutucu_serbest(self):
        gercek = "mysql://kullanici:" + "Gizli" + "123" + "@localhost/db"
        self.assertTrue(vb.icerik_denetle(gercek.encode()))
        self.assertEqual(vb.icerik_denetle(b"mysql://<kullanici>:<parola>@localhost/db"), [])

    def test_izin_isareti_sirri_atlamaz(self):
        satir = f"t = '{github_token()}'  # " + "bekci" + ":izin"
        self.assertIn("GitHub token", kurallar(vb.icerik_denetle(satir.encode())))

    def test_ikili_icerik_taranmaz(self):
        self.assertEqual(vb.icerik_denetle(b"\x00\x01" + github_token().encode()), [])


class IcerikKisiselVeri(unittest.TestCase):
    def test_tc_saglama_toplami(self):
        gecerli = tc_uret("123456789")
        self.assertTrue(vb.tc_gecerli(gecerli))
        self.assertIn("TC kimlik no (sağlama geçerli)",
                      kurallar(vb.icerik_denetle(gecerli.encode())))
        gecersiz = gecerli[:-1] + str((int(gecerli[-1]) + 1) % 10)
        self.assertEqual(vb.icerik_denetle(gecersiz.encode()), [])

    def test_izin_isareti_kisisel_veriyi_atlar(self):
        satir = tc_uret("123456789") + "  # " + "bekci" + ":izin sentetik"
        self.assertEqual(vb.icerik_denetle(satir.encode()), [])

    def test_cep_telefonu(self):
        self.assertIn("cep telefonu",
                      kurallar(vb.icerik_denetle(("0" + "53" + "2 123 45 67").encode())))

    def test_eposta_ornek_alanlar_serbest(self):
        kisisel = "ali" + "@" + "ornek.com.tr"
        self.assertIn("e-posta adresi", kurallar(vb.icerik_denetle(kisisel.encode())))
        self.assertEqual(vb.icerik_denetle(b"kisi@example.com git@github.com:x/y.git"), [])


class GitEntegrasyonu(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="bekci_")
        self._g("init", "-q", "-b", "main")

    def tearDown(self):
        shutil.rmtree(self.kok, ignore_errors=True)

    def _g(self, *arg):
        s = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "user.name=t",
                            "-c", "user.email=t@example.com", "-c", "core.hooksPath=",
                            "-C", self.kok, *arg], capture_output=True, check=True)
        return s.stdout.decode().strip()

    def _yaz(self, yol, icerik):
        tam = os.path.join(self.kok, yol)
        os.makedirs(os.path.dirname(tam) or self.kok, exist_ok=True)
        with open(tam, "w", encoding="utf-8", newline="\n") as f:
            f.write(icerik)

    def test_staged_icerigi_denetler_calisma_agacini_degil(self):
        self._yaz("a.py", "print('merhaba')\n")
        self._yaz("veri.csv", "a,b\n1,2\n")
        self._g("add", "-f", "a.py", "veri.csv")
        # Çalışma ağacında sonradan eklenen sır index'te yok → sayılmamalı.
        self._yaz("a.py", f"t = '{github_token()}'\n")
        ihlaller = vb.staged_denetle(self.kok)
        self.assertEqual([k for k, _, _ in ihlaller], ["veri.csv"])

    def test_ara_committe_eklenip_silinen_sir_yakalanir(self):
        self._yaz("ayar.py", f"t = '{github_token()}'\n")
        self._g("add", "ayar.py")
        self._g("commit", "-q", "-m", "sır eklendi")
        c1 = self._g("rev-parse", "HEAD")
        self._yaz("ayar.py", "t = None\n")
        self._g("commit", "-q", "-am", "sır silindi")
        c2 = self._g("rev-parse", "HEAD")
        satir = f"refs/heads/main {c2} refs/heads/main {vb.SIFIR}"
        ihlaller = vb.push_denetle(self.kok, "origin", [satir])
        self.assertTrue(any(k.startswith(c1[:7]) for k, _, _ in ihlaller),
                        f"ara commit'teki sır kaçtı: {ihlaller}")

    def test_izin_dosyasi_gerekcesiz_satiri_reddeder(self):
        self._yaz(vb.IZIN_DOSYASI, "arayuz/logo.png\n")
        with self.assertRaises(vb.BekciHatasi):
            vb.izinleri_oku(self.kok)
        self._yaz(vb.IZIN_DOSYASI, "arayuz/logo.png  # marka görseli, 2.3 MB\n")
        self.assertEqual(vb.izinleri_oku(self.kok), frozenset({"arayuz/logo.png"}))


class UzakTuru(unittest.TestCase):
    def test_yerel_ve_ag_uzaklari(self):
        self.assertTrue(vb.yerel_url_mi("D:/yedekTemmuz2026/git_yedek/sinama.git"))
        self.assertTrue(vb.yerel_url_mi("/d/yedek/sinama.git"))
        self.assertFalse(vb.yerel_url_mi("https://github.com/kisi/sinama.git"))
        self.assertFalse(vb.yerel_url_mi("git@github.com:kisi/sinama.git"))


if __name__ == "__main__":
    unittest.main()
