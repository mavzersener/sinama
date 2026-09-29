# -*- coding: utf-8 -*-
"""
test_kilit_veri_kimligi.py — Ön-kayıt ve veri kimliği testleri (v6.9).

SINIF 1 — DosyaKimligiTestleri:
  dosya_kimligi() SHA-256 ve boyut hesaplaması sınanır;
  dosya adı tam yol değil, taban ad olmalı;
  olmayan dosya VeriHatasi fırlatır.

SINIF 2 — OnKayitTestleri:
  protokol kilidi (ön-kayıt) sınanır:
  - doğrulayıcı çalışmada kilit veriden ÖNCE zorunlu;
  - kilit sonrası protokol değişirse bütünlük False;
  - çift kilit, boş hipotez, yanlış faz reddi;
  - operasyonel varsayılan; veri kimliği yazılır.
"""

import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama.surec import dongu, kanit, kilit
from sinama.cekirdek.hatalar import VeriHatasi


class DosyaKimligiTestleri(unittest.TestCase):
    """
    kanit.dosya_kimligi() fonksiyonunun SHA-256, boyut ve adlandırma
    kurallarını sınar.
    """

    def setUp(self):
        """Her test için geçici dizin ve dosya oluştur."""
        self.tmp = tempfile.mkdtemp()

    def test_sha256_ve_boyut_dogru(self):
        """
        Bilinen içerikli dosyanın SHA-256 ve boyutu doğru hesaplanır.
        """
        # Geçici dosya oluştur ve bilinen bayt yaz.
        icerik = b"Turkey crime analysis test data"
        dosya_yolu = os.path.join(self.tmp, "test_verisi.csv")
        with open(dosya_yolu, "wb") as f:
            f.write(icerik)

        # kanit.dosya_kimligi çıktısını al.
        kimlik = kanit.dosya_kimligi(dosya_yolu)

        # Beklenen SHA-256'yi hashlib ile hesapla.
        beklenen_sha256 = hashlib.sha256(icerik).hexdigest()

        # Sonuçları karşılaştır.
        self.assertEqual(kimlik["sha256"], beklenen_sha256,
                         "SHA-256 uyuşmadı")
        self.assertEqual(kimlik["boyut"], len(icerik),
                         "boyut uyuşmadı")

    def test_dosya_adi_tam_yol_icermez(self):
        """
        Döndürülen 'dosya_adi' tam yol değil, yalnız taban addır;
        dizin ayıracı (os.sep) içermez.
        """
        icerik = b"simple test"
        alt_dizin = os.path.join(self.tmp, "alt")
        os.makedirs(alt_dizin, exist_ok=True)
        dosya_yolu = os.path.join(alt_dizin, "veri.txt")
        with open(dosya_yolu, "wb") as f:
            f.write(icerik)

        kimlik = kanit.dosya_kimligi(dosya_yolu)

        # dosya_adi sadece "veri.txt" olmalı, tam yol olmamalı.
        self.assertEqual(kimlik["dosya_adi"], "veri.txt",
                         "dosya_adi tam yol içeriyor")
        self.assertNotIn(os.sep, kimlik["dosya_adi"],
                         f"dosya_adi dizin ayıracı içeriyor: {kimlik['dosya_adi']}")

    def test_olmayan_dosya_veri_hatasi(self):
        """
        Olmayan dosya yolunun geçilmesi VeriHatasi fırlatır.
        """
        olmayan_yol = os.path.join(self.tmp, "olmayan_dosya.csv")

        with self.assertRaises(VeriHatasi) as cm:
            kanit.dosya_kimligi(olmayan_yol)

        # Hata mesajında "bulunamadı" veya benzeri text olmalı.
        self.assertIn("bulunamadı", str(cm.exception).lower())


class OnKayitTestleri(unittest.TestCase):
    """
    Ön-kayıt (protokol kilidi) ve veri kimliği işlevini sınar.
    Kilit, doğrulayıcı çalışmalarda veriden ÖNCE alınmalıdır.
    """

    def setUp(self):
        """Her test için geçici dizin oluştur."""
        self.tmp = tempfile.mkdtemp()

    def test_dogrulayici_akis_saglam(self):
        """
        Doğrulayıcı oturumda, planla() → protokol_kilitle() →
        veri_bagla() akışı saglam çalışır; onkayit_dogrula sonuç
        doğru alanları taşır.
        """
        d = dongu.AnalizDongusu(
            {"soran": "X", "urun_turu": "taktik"},
            amac="dogrulayici"
        )

        # Akış: planla → kilitle → veri_bagla
        d.planla()
        d.protokol_kilitle("bir hipotez cumlesi", "Sener")
        d.veri_bagla({"n": 120, "uyarilar": []})

        # Ön-kayıt doğrulaması.
        sonuc = d.onkayit_dogrula()

        # Beklenen alanlar ve değerler.
        self.assertTrue(sonuc["kilitli"], "kilitli olmalı")
        self.assertTrue(sonuc["butunluk"], "bütünlük sağlam olmalı")
        self.assertTrue(sonuc["sira_saglam"], "sıra sağlam olmalı")
        self.assertTrue(sonuc["dogrulayici_iddia_edilebilir"],
                        "doğrulayıcı iddia yapılabilir olmalı")

    def test_kilitsiz_dogrulayici_veri_baglanamaz(self):
        """
        Doğrulayıcı (amac='dogrulayici') oturumda, protokol
        kilitlenmeden veri_bagla çağrılırsa KilitHatasi fırlatılır.
        """
        d = dongu.AnalizDongusu(
            {"soran": "X", "urun_turu": "taktik"},
            amac="dogrulayici"
        )

        d.planla()

        # Kilit almadan doğrudan veri_bagla çağrısı.
        with self.assertRaises(kilit.KilitHatasi) as cm:
            d.veri_bagla({"n": 120, "uyarilar": []})

        self.assertIn("kilitlenmeden", str(cm.exception))

    def test_kilit_sonrasi_degisiklik_yakalanir(self):
        """
        Protokol kilitledikten sonra, manifesto alanları (talep/plan)
        değiştirilirse, onkayit_dogrula() bütünlük=False dönündürür.
        """
        d = dongu.AnalizDongusu(
            {"soran": "X", "urun_turu": "taktik"},
            amac="dogrulayici"
        )

        d.planla()
        d.protokol_kilitle("bir hipotez cumlesi", "Sener")
        d.veri_bagla({"n": 120, "uyarilar": []})

        # Kilitledikten sonra talep alanını değiştir.
        d.manifesto["talep"]["karar"] = "DEĞIŞTIRILDI"

        # Doğrulama: bütünlük False, doğrulayıcı iddiası False olmalı.
        sonuc = d.onkayit_dogrula()

        self.assertFalse(sonuc["butunluk"],
                         "bütünlük False olmalı; protokol değiştirildi")
        self.assertFalse(sonuc["dogrulayici_iddia_edilebilir"],
                         "doğrulayıcı iddiası False olmalı")

    def test_cift_kilit_reddedilir(self):
        """
        Zaten kilitli bir protokole ikinci kez protokol_kilitle
        çağrılırsa KilitHatasi fırlatılır.
        """
        d = dongu.AnalizDongusu(
            {"soran": "X", "urun_turu": "taktik"},
            amac="dogrulayici"
        )

        d.planla()
        d.protokol_kilitle("hipotez bir", "Sener")

        # İkinci kilitleme denemesi.
        with self.assertRaises(kilit.KilitHatasi) as cm:
            d.protokol_kilitle("hipotez iki", "Sener")

        self.assertIn("zaten kilitli", str(cm.exception))

    def test_bos_hipotez_reddedilir(self):
        """
        Boş veya yalnız whitespace hipotez ile protokol_kilitle
        çağrılırsa KilitHatasi fırlatılır.
        """
        d = dongu.AnalizDongusu(
            {"soran": "X", "urun_turu": "taktik"},
            amac="dogrulayici"
        )

        d.planla()

        # Boş hipotez (sadece space).
        with self.assertRaises(kilit.KilitHatasi) as cm:
            d.protokol_kilitle("   ", "Sener")

        self.assertIn("boş", str(cm.exception).lower())

    def test_yanlis_fazda_kilit_reddedilir(self):
        """
        planla() çağrılmadan (yani PROBLEM fazındayken)
        protokol_kilitle çağrılırsa KilitHatasi fırlatılır.
        """
        d = dongu.AnalizDongusu(
            {"soran": "X", "urun_turu": "taktik"},
            amac="dogrulayici"
        )

        # planla() ÇAĞRILmadı → faz hala "PROBLEM".

        with self.assertRaises(kilit.KilitHatasi) as cm:
            d.protokol_kilitle("hipotez", "Sener")

        self.assertIn("PLAN", str(cm.exception))

    def test_operasyonel_varsayilan_degismedi(self):
        """
        amac parametresi verilmeden AnalizDongusu oluşturulunca
        manifesto['amac'] varsayılan olarak 'operasyonel' olur;
        bu oturumda kilit zorunlu değildir.
        """
        d = dongu.AnalizDongusu({"soran": "Y"})
        # amac verilmedi → varsayılan 'operasyonel' olmalı.

        self.assertEqual(d.manifesto["amac"], "operasyonel",
                         "varsayılan amac 'operasyonel' olmalı")

        # Operasyonel oturumda kilit olmadan çalışmalı.
        d.planla()
        d.veri_bagla({"n": 50, "uyarilar": []})

        # Doğrulama: kilidi False, iddia False (beklendik).
        sonuc = d.onkayit_dogrula()

        self.assertFalse(sonuc["kilitli"],
                         "operasyonel çalışma kilitlenmemiş olmalı")
        self.assertFalse(sonuc["dogrulayici_iddia_edilebilir"],
                         "operasyonel çalışmada doğrulayıcı iddiası False")

    def test_gecersiz_amac_reddedilir(self):
        """
        Geçersiz amac değeri (kilit.AMACLAR listesinde olmayan) ile
        AnalizDongusu oluşturma DonguHatasi fırlatır.
        """
        with self.assertRaises(dongu.DonguHatasi) as cm:
            dongu.AnalizDongusu({"soran": "Z"}, amac="saçma")

        self.assertIn("amac", str(cm.exception).lower())

    def test_veri_bagla_kimlik_yazar(self):
        """
        veri_bagla() ile veri_yolu parametresi geçilirse,
        manifestoya veri_kimligi (sha256 + boyut) yazılır.
        veri_yolu VERİLMEZSE alanı None kalır.
        """
        # İLK KASE: veri_yolu VERİLİRSE
        icerik = b"Turkey crime analysis data file"
        veri_dosya = os.path.join(self.tmp, "veri.csv")
        with open(veri_dosya, "wb") as f:
            f.write(icerik)

        d1 = dongu.AnalizDongusu({"soran": "A"})
        d1.planla()
        d1.veri_bagla({"n": 10, "uyarilar": []}, veri_yolu=veri_dosya)

        # Veri kimliği yazılmalı.
        self.assertIsNotNone(d1.manifesto["veri_kimligi"],
                             "veri_kimligi None olmamalı")
        self.assertIn("sha256", d1.manifesto["veri_kimligi"])
        self.assertIn("boyut", d1.manifesto["veri_kimligi"])
        self.assertEqual(d1.manifesto["veri_kimligi"]["boyut"], len(icerik))

        # İKİNCİ KASE: veri_yolu VERİLMEZSE
        d2 = dongu.AnalizDongusu({"soran": "B"})
        d2.planla()
        d2.veri_bagla({"n": 5, "uyarilar": []})

        # Veri kimliği None kalmalı.
        self.assertIsNone(d2.manifesto["veri_kimligi"],
                          "veri_kimligi None olmalı (yolu verilmedi)")


if __name__ == "__main__":
    unittest.main()
