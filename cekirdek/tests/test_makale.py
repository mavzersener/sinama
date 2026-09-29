# -*- coding: utf-8 -*-
"""
test_makale.py — Olgu listesi ve anlatı doğrulama testleri (v6.9).

SINIF 1 — OlguListesiTestleri:
  olgu_listesi() fonksiyonunun bulgu, yöntem ve sınırlılık olgularını
  doğru ürettiğini sınar.

SINIF 2 — AnlatiDogrulaTestleri:
  anlati_dogrula() fonksiyonunun rakam yasağı, dayanak zorunluluğu ve
  atıf doğrulamasını sınar.
"""

import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sinama.surec import dongu, makale
from sinama.cekirdek.hatalar import KullanimHatasi


class OlguListesiTestleri(unittest.TestCase):
    """
    olgu_listesi() fonksiyonunun bulgu, yöntem, sınırlılık olgularını
    doğru kimlikle ve tutarlı bir şekilde ürettiğini sınar.
    """

    def setUp(self):
        """Her test için temel oturum oluştur ve kurulum yap."""
        self.d = dongu.AnalizDongusu(
            {"soran": "Komutan", "karar": "devriye", "urun_turu": "taktik"},
            amac="operasyonel",
            mod="kesif"
        )
        self.d.planla()

    def test_analiz_adimi_bulgu_uretir(self):
        """
        Analiz fazında kaydedilen adım, olgu_listesi çıktısında tur='bulgu'
        olan bir olgu yaratır; kimliği 'F' ile başlar ve ifade araç adını içerir.
        """
        # Veri ve analiz aşamasına geç.
        self.d.veri_bagla({"n": 338, "uyarilar": []})
        self.d.analize_gec({"uygun": True, "sebepler": []})

        # Analiz adımı kaydet.
        self.d.analiz_kaydet(
            "sicak_nokta_gi",
            "Sicak noktalar hafta sonu yogunlasir"
        )

        # Olgu listesini üret.
        olgular = makale.olgu_listesi(self.d.manifesto)

        # Bulgular içinde 'sicak_nokta_gi' aracını içeren bir olgu var mı?
        bulgular = [o for o in olgular if o["tur"] == "bulgu"]
        self.assertGreater(len(bulgular), 0, "bulgu olgusu üretilmedi")

        # İlk bulgunun kimliği F ile başlamalı.
        ilk_bulgu = bulgular[0]
        self.assertTrue(ilk_bulgu["kimlik"].startswith("F"),
                       f"bulgu kimliği F ile başlamalı, aldı: {ilk_bulgu['kimlik']}")

        # İfadesi aracı ve özeti içermeli.
        self.assertIn("sicak_nokta_gi", ilk_bulgu["ifade"],
                     "ifade aracı adını içermeli")

    def test_kilit_yontem_olgusu_uretir(self):
        """
        Protokol kilitlenirse, olgu_listesi çıktısında tur='yontem' olan
        bir olgu, kilit hash'ini ifadesinde taşımalıdır.
        """
        # Protokolü kilitle.
        kilit_kayit = self.d.protokol_kilitle(
            "Sicak noktalar hafta sonu yogunlasir",
            "Sener"
        )

        # Olgu listesini üret.
        olgular = makale.olgu_listesi(self.d.manifesto)

        # Yöntem olgularını filtrele.
        yontemler = [o for o in olgular if o["tur"] == "yontem"]
        self.assertGreater(len(yontemler), 0, "yöntem olgusu üretilmedi")

        # Kilit hash'ini içeren bir yöntem olgusu olmalı.
        kilit_hash = kilit_kayit["hash"]
        baska_yontem = None
        for o in yontemler:
            if kilit_hash in o["ifade"]:
                baska_yontem = o
                break

        self.assertIsNotNone(baska_yontem,
                            f"kilit hash '{kilit_hash}' hiçbir yöntem olgusunda bulunmadı")

    def test_veri_kimligi_yontem_olgusu(self):
        """
        veri_bagla() çağrısında veri_yolu parametresi verilirse,
        olgu_listesi çıktısında dosyanın SHA-256'sini taşıyan bir
        tur='yontem' olgusu bulunmalıdır.
        """
        # Geçici dosya oluştur.
        tmp = tempfile.mkdtemp()
        icerik = b"test verisi icin data"
        veri_dosya = os.path.join(tmp, "test_veri.csv")
        with open(veri_dosya, "wb") as f:
            f.write(icerik)

        beklenen_sha256 = hashlib.sha256(icerik).hexdigest()

        # AYRI bir oturumda veri_bagla çağır.
        d2 = dongu.AnalizDongusu(
            {"soran": "Test", "urun_turu": "taktik"},
            amac="operasyonel",
            mod="kesif"
        )
        d2.planla()
        d2.veri_bagla({"n": 10, "uyarilar": []}, veri_yolu=veri_dosya)

        # Olgu listesini üret.
        olgular = makale.olgu_listesi(d2.manifesto)

        # SHA-256'yi içeren bir yöntem olgusu bulmalı.
        yontemler = [o for o in olgular if o["tur"] == "yontem"]
        sha256_olgusu = None
        for o in yontemler:
            if beklenen_sha256 in o["ifade"]:
                sha256_olgusu = o
                break

        self.assertIsNotNone(sha256_olgusu,
                            f"veri SHA-256 '{beklenen_sha256}' hiçbir yöntem olgusunda bulunmadı")

    def test_sinirliliklar_kapidan_turer(self):
        """
        Gate kararları ve veri kalitesi uyarıları, olgu_listesi çıktısında
        tur='sinirlilik' olgularına dönüştürülür (TÜRETİLİR, uydurulmaz).
        """
        # Veri kalitesi profili ve gate kararı ile veri_bagla.
        self.d.veri_bagla(
            {"n": 338, "uyarilar": ["koordinat eksikligi"]},
            uygunluk={"uygun": True, "sebepler": ["ornek sayisi sinirli"]}
        )

        # Olgu listesini üret.
        olgular = makale.olgu_listesi(self.d.manifesto)

        # Sınırlılık olgularını filtrele.
        sinirliliklar = [o for o in olgular if o["tur"] == "sinirlilik"]
        sinirlilik_ifadeleri = [o["ifade"] for o in sinirliliklar]

        # Gate sebebi ve veri uyarısı ifadelerde olmalı.
        self.assertTrue(
            any("ornek sayisi sinirli" in s for s in sinirlilik_ifadeleri),
            "gate sebebi 'ornek sayisi sinirli' olgularında bulunmadı"
        )
        self.assertTrue(
            any("koordinat eksikligi" in s for s in sinirlilik_ifadeleri),
            "veri uyarısı 'koordinat eksikligi' olgularında bulunmadı"
        )

    def test_kesifsel_calismaya_sinirlilik_eklenir(self):
        """
        amac='operasyonel' ve kilit olmayan oturumda, olgu_listesi
        çıktısında "doğrulayıcı yorum yapılamaz" mesajı içeren bir
        tur='sinirlilik' olgusu bulunmalıdır.

        Buna karşı, amac='dogrulayici' ve kilit'li oturumda bu olgu
        BULUNMAMALIDIR.
        """
        # Kase 1: operasyonel, kilitlenmemiş (varsayılan).
        d1 = dongu.AnalizDongusu(
            {"soran": "X"},
            amac="operasyonel",
            mod="kesif"
        )
        d1.planla()
        d1.veri_bagla({"n": 10, "uyarilar": []})

        olgular1 = makale.olgu_listesi(d1.manifesto)
        sinirliliklar1 = [o["ifade"] for o in olgular1 if o["tur"] == "sinirlilik"]

        self.assertTrue(
            any("doğrulayıcı yorum yapılamaz" in s for s in sinirliliklar1),
            "operasyonel çalışma: 'doğrulayıcı yorum yapılamaz' olgusunda bulunmadı"
        )

        # Kase 2: doğrulayıcı, kilitli.
        d2 = dongu.AnalizDongusu(
            {"soran": "Y"},
            amac="dogrulayici",
            mod="kesif"
        )
        d2.planla()
        d2.protokol_kilitle("bir hipotez", "Sener")
        d2.veri_bagla({"n": 10, "uyarilar": []})

        olgular2 = makale.olgu_listesi(d2.manifesto)
        sinirliliklar2 = [o["ifade"] for o in olgular2 if o["tur"] == "sinirlilik"]

        self.assertFalse(
            any("doğrulayıcı yorum yapılamaz" in s for s in sinirliliklar2),
            "doğrulayıcı çalışma: 'doğrulayıcı yorum yapılamaz' olgusunda olmamalı"
        )

    def test_kimlikler_benzersiz(self):
        """
        olgu_listesi çıktısındaki tüm 'kimlik' değerleri benzersiz olmalıdır.
        """
        # Çeşitli adımlarla oturum doldur.
        self.d.protokol_kilitle("hipotez", "Sener")
        self.d.veri_bagla(
            {"n": 100, "uyarilar": ["bir uyari", "iki uyari"]},
            uygunluk={"uygun": True, "sebepler": ["sebep_a", "sebep_b"]}
        )
        self.d.analize_gec({"uygun": True, "sebepler": []})
        self.d.analiz_kaydet("arac1", "sonuc1")
        self.d.analiz_kaydet("arac2", "sonuc2")

        # Olgu listesi.
        olgular = makale.olgu_listesi(self.d.manifesto)

        # Kimlik benzersizliğini kontrol et.
        kimlikler = [o["kimlik"] for o in olgular]
        benzersiz_kimlikler = set(kimlikler)

        self.assertEqual(len(kimlikler), len(benzersiz_kimlikler),
                        f"kimlik tekrarları: {[k for k in kimlikler if kimlikler.count(k) > 1]}")


class AnlatiDogrulaTestleri(unittest.TestCase):
    """
    anlati_dogrula() fonksiyonunun rakam yasağı, dayanak zorunluluğu,
    atıf doğrulama ve paragraf sayma işlevlerini sınar.
    """

    def setUp(self):
        """Her test için oturum ve olgu listesi hazırla."""
        self.d = dongu.AnalizDongusu(
            {"soran": "Test", "urun_turu": "taktik"},
            amac="operasyonel",
            mod="kesif"
        )
        self.d.planla()
        self.d.veri_bagla({"n": 100, "uyarilar": []})
        self.d.analize_gec({"uygun": True, "sebepler": []})
        self.d.analiz_kaydet("arac_test", "ozet")

        # Olguları üret.
        self.olgular = makale.olgu_listesi(self.d.manifesto)
        self.bulgu_kimligi = next(
            (o["kimlik"] for o in self.olgular if o["tur"] == "bulgu"),
            "F001"
        )

    def test_gecerli_anlati_kabul(self):
        """
        Atıf içeren ve atıflar dışında rakam taşımayan paragraf geçerli
        kabul edilir.
        """
        metin = f"Yogunlasma belirli bir hucrede toplanmaktadir [{self.bulgu_kimligi}]."

        sonuc = makale.anlati_dogrula(metin, self.olgular)

        self.assertTrue(sonuc["gecerli"], "anlatı geçerli olmalı")
        self.assertEqual(len(sonuc["ihlaller"]), 0, "ihlal olmamalı")

    def test_rakam_reddedilir(self):
        """
        Paragrafta atıflar dışında rakam taşıyorsa tur='rakam' ihlali
        üretilir ve gecerli=False olur.
        """
        metin = f"Sicak noktada belirgin artis gozlendi 37 kez [{self.bulgu_kimligi}]."

        sonuc = makale.anlati_dogrula(metin, self.olgular)

        self.assertFalse(sonuc["gecerli"], "rakam içeren anlatı geçersiz")
        ihlaller = [i for i in sonuc["ihlaller"] if i["tur"] == "rakam"]
        self.assertGreater(len(ihlaller), 0, "rakam ihlali üretilmedi")

    def test_sozel_nicelik_reddedilir(self):
        """
        Paragrafta sözel nicelik ifadesi (yarısı, katı, yüzde vb.)
        taşıyorsa tur='rakam' ihlali üretilir.
        """
        metin = f"Olaylarin yarısı bu bolgede toplanmistir [{self.bulgu_kimligi}]."

        sonuc = makale.anlati_dogrula(metin, self.olgular)

        self.assertFalse(sonuc["gecerli"], "sözel nicelik geçersiz")
        ihlaller = [i for i in sonuc["ihlaller"] if i["tur"] == "rakam"]
        self.assertGreater(len(ihlaller), 0, "rakam ihlali üretilmedi")

    def test_dayanaksiz_paragraf_reddedilir(self):
        """
        Hiçbir olgu kimliğine atıf yapmayan paragraf tur='dayanaksiz'
        ihlali üretir.
        """
        metin = "Bu paragraf dayanaksiz bir iddia iceriyor."

        sonuc = makale.anlati_dogrula(metin, self.olgular)

        self.assertFalse(sonuc["gecerli"], "dayanaksiz anlatı geçersiz")
        ihlaller = [i for i in sonuc["ihlaller"] if i["tur"] == "dayanaksiz"]
        self.assertGreater(len(ihlaller), 0, "dayanaksiz ihlali üretilmedi")

    def test_bilinmeyen_kimlik_reddedilir(self):
        """
        Olgu listesinde olmayan bir kimliğe atıf yapılırsa tur='bilinmeyen_kimlik'
        ihlali üretilir.
        """
        metin = "Bu paragraf bilinmeyen bir kimlige atif yapiyor [F999]."

        sonuc = makale.anlati_dogrula(metin, self.olgular)

        self.assertFalse(sonuc["gecerli"], "bilinmeyen kimlik geçersiz")
        ihlaller = [i for i in sonuc["ihlaller"] if i["tur"] == "bilinmeyen_kimlik"]
        self.assertGreater(len(ihlaller), 0, "bilinmeyen_kimlik ihlali üretilmedi")

    def test_atif_icindeki_rakam_sayilmaz(self):
        """
        Atıf kimliğindeki rakamlar (örn. [F001] içindeki '001') sayı
        hesaplamalarında yer ALMAMALIDIR. Yalnız atıflar taşıyan paragraf
        rakam ihlali ÜRETMEMELİDİR.
        """
        metin = f"Sadece bu olgu atifi var [{self.bulgu_kimligi}]."

        sonuc = makale.anlati_dogrula(metin, self.olgular)

        # Geçerli olmalı (atıftaki rakamlar sayılmamalı).
        self.assertTrue(sonuc["gecerli"], "atıf içindeki rakamlar sayılmamalı")
        ihlaller = [i for i in sonuc["ihlaller"] if i["tur"] == "rakam"]
        self.assertEqual(len(ihlaller), 0, "rakam ihlali olmamalı")

    def test_bos_olgu_listesi_kullanim_hatasi(self):
        """
        Boş olgu listesiyle anlati_dogrula çağrılırsa KullanimHatasi
        fırlatılmalıdır.
        """
        metin = "Bir metin."

        with self.assertRaises(KullanimHatasi) as cm:
            makale.anlati_dogrula(metin, [])

        self.assertIn("olgu listesi", str(cm.exception).lower())

    def test_coklu_paragraf_sayilir(self):
        """
        Boş satırla ayrılmış iki paragraf, paragraf_sayisi=2 olarak
        sayılmalıdır.
        """
        metin = (
            f"Birinci paragraf bir bulgu icerir [{self.bulgu_kimligi}].\n\n"
            f"Ikinci paragraf da bir bulgu icerir [{self.bulgu_kimligi}]."
        )

        sonuc = makale.anlati_dogrula(metin, self.olgular)

        self.assertEqual(sonuc["paragraf_sayisi"], 2,
                        "iki paragraf sayılmalı")


if __name__ == "__main__":
    unittest.main()
