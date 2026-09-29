# -*- coding: utf-8 -*-
"""
test_provenans.py — Provenans (kaynak zinciri) testleri (v6.9).

SINIF 1 — HazirlikBeyaniTestleri:
  hazirlik_beyani() fonksiyonunun beyan kaydedilmesi, alanlara
  doğru yazılması, validation ve trimming sınanır.

SINIF 2 — DisDenetimTestleri:
  dis_denetim_kaydet() dış sistemin denetim doğrulamasını
  manifestoya bağlama işlemi sınanır.

SINIF 3 — ZincirOzetiTestleri:
  zincir_ozeti() beş halka görünümü, kopukluk tespiti, makine
  zinciri durumu ve halka kanıt türleri sınanır.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi.surec import dongu, provenans, kilit
from suc_analizi.cekirdek.hatalar import KullanimHatasi


class HazirlikBeyaniTestleri(unittest.TestCase):
    """
    hazirlik_beyani() fonksiyonunun beyan kaydedilmesi,
    validation, alan trimming'i ve kanıt türü sınaması.
    """

    def setUp(self):
        """Her test için boş manifesto oluştur."""
        self.manifesto = {}

    def test_beyan_kaydedilir(self):
        """
        İki adımlı beyan verildikten sonra manifesto['hazirlik_beyani']
        alanı doldurulur, adımlar listesi 2 elemanlı olur ve beyan_eden
        doğru kayıt edilir.
        """
        adimlar = [
            {"islem": "veri toplama", "aciklama": "kaynak A'dan", "kaynak": "A"},
            {"islem": "filtreleme", "aciklama": "uygunsuz veriler", "kaynak": "B"}
        ]
        beyan = provenans.hazirlik_beyani(self.manifesto, adimlar, "Araştırmacı X")

        # Manifesto kaydedildi mi?
        self.assertIn("hazirlik_beyani", self.manifesto)
        self.assertEqual(self.manifesto["hazirlik_beyani"], beyan)

        # Adımlar doğru mu?
        self.assertEqual(len(beyan["adimlar"]), 2)
        self.assertEqual(beyan["beyan_eden"], "Araştırmacı X")

    def test_kanit_turu_her_zaman_beyan(self):
        """
        Dönen beyanın kanit_turu alanı provenans.BEYAN olmalı.
        Hazırlık asla MAKİNE sayılmaz.
        """
        adimlar = [{"islem": "veri hazırlanması", "aciklama": "", "kaynak": ""}]
        beyan = provenans.hazirlik_beyani(self.manifesto, adimlar, "X")

        self.assertEqual(beyan["kanit_turu"], provenans.BEYAN)
        self.assertNotEqual(beyan["kanit_turu"], provenans.MAKINE)

    def test_bos_adim_listesi_reddedilir(self):
        """
        Boş adımlar listesi (adimlar=[]) KullanimHatasi fırlatır.
        """
        with self.assertRaises(KullanimHatasi) as cm:
            provenans.hazirlik_beyani(self.manifesto, [], "X")

        self.assertIn("boş", str(cm.exception).lower())

    def test_beyan_eden_bos_reddedilir(self):
        """
        Beyan eden boş veya yalnız whitespace ise KullanimHatasi fırlatır.
        """
        adimlar = [{"islem": "test", "aciklama": "", "kaynak": ""}]

        with self.assertRaises(KullanimHatasi):
            provenans.hazirlik_beyani(self.manifesto, adimlar, "   ")

    def test_islem_alani_bos_reddedilir(self):
        """
        İşlem alanı boş olan adım KullanimHatasi fırlatır.
        """
        adimlar = [{"islem": "", "aciklama": "x", "kaynak": "y"}]

        with self.assertRaises(KullanimHatasi) as cm:
            provenans.hazirlik_beyani(self.manifesto, adimlar, "X")

        self.assertIn("islem", str(cm.exception).lower())

    def test_alanlar_kirpilir(self):
        """
        İslem/aciklama/kaynak alanlarının başında-sonunda boşluk varsa
        kaydedilen adımda trim edilmiş olmalı.
        """
        adimlar = [
            {"islem": "  trim testi  ", "aciklama": "  x  ", "kaynak": "  y  "}
        ]
        beyan = provenans.hazirlik_beyani(self.manifesto, adimlar, "X")

        adim = beyan["adimlar"][0]
        self.assertEqual(adim["islem"], "trim testi")
        self.assertEqual(adim["aciklama"], "x")
        self.assertEqual(adim["kaynak"], "y")


class DisDenetimTestleri(unittest.TestCase):
    """
    dis_denetim_kaydet() fonksiyonunun dış systemin denetim
    doğrulamasını manifestoya bağlama işlemi sınaması.
    """

    def setUp(self):
        """Her test için boş manifesto oluştur."""
        self.manifesto = {}

    def test_denetim_baglanir(self):
        """
        Denetim verileri manifestoya kaydedilir ve uygun alanları
        taşır: valid, olay_sayisi, son_hash.
        """
        dogrulama = {"valid": True, "event_count": 74, "last_hash": "a" * 64}
        bag = provenans.dis_denetim_kaydet(
            self.manifesto, "science_gpt", "res_x", dogrulama
        )

        # Manifesto kaydedildi mi?
        self.assertIn("dis_denetimler", self.manifesto)
        self.assertEqual(len(self.manifesto["dis_denetimler"]), 1)

        # Alanlar doğru mu?
        self.assertEqual(bag["valid"], True)
        self.assertEqual(bag["olay_sayisi"], 74)
        self.assertEqual(bag["son_hash"], "a" * 64)

    def test_birden_cok_denetim_birikir(self):
        """
        İki kez denetim kaydedilirse liste 2 elemanlı olur.
        """
        dogrulama1 = {"valid": True, "event_count": 50, "last_hash": "a" * 64}
        dogrulama2 = {"valid": False, "event_count": 0, "last_hash": None}

        provenans.dis_denetim_kaydet(
            self.manifesto, "sistem_1", "id_1", dogrulama1
        )
        provenans.dis_denetim_kaydet(
            self.manifesto, "sistem_2", "id_2", dogrulama2
        )

        self.assertEqual(len(self.manifesto["dis_denetimler"]), 2)

    def test_valid_alani_yoksa_reddedilir(self):
        """
        Doğrulama sözlüğünde 'valid' alanı yoksa KullanimHatasi fırlatır.
        """
        dogrulama = {"event_count": 10}  # 'valid' yok

        with self.assertRaises(KullanimHatasi) as cm:
            provenans.dis_denetim_kaydet(self.manifesto, "test", "id", dogrulama)

        self.assertIn("valid", str(cm.exception).lower())

    def test_sistem_veya_kimlik_bos_reddedilir(self):
        """
        Sistem boş ise KullanimHatasi; kimlik boş ise KullanimHatasi.
        """
        dogrulama = {"valid": True}

        # Sistem boş.
        with self.assertRaises(KullanimHatasi):
            provenans.dis_denetim_kaydet(self.manifesto, "", "id", dogrulama)

        # Kimlik boş.
        with self.assertRaises(KullanimHatasi):
            provenans.dis_denetim_kaydet(self.manifesto, "sistem", "", dogrulama)

    def test_kanit_turu_makine(self):
        """
        Dış denetim bağının kanit_turu provenans.MAKINE olmalı.
        """
        dogrulama = {"valid": True, "event_count": 5, "last_hash": "x" * 64}
        bag = provenans.dis_denetim_kaydet(
            self.manifesto, "sys", "id", dogrulama
        )

        self.assertEqual(bag["kanit_turu"], provenans.MAKINE)


class ZincirOzetiTestleri(unittest.TestCase):
    """
    zincir_ozeti() fonksiyonunun beş halka görünümü, kopukluk
    tespiti, makine zinciri durumu ve halka kanıt türleri sınaması.
    """

    def setUp(self):
        """Her test için oturum ve manifesto oluştur."""
        self.tmp = tempfile.mkdtemp()

    def _oturum(self, kilitli=False, amac="operasyonel"):
        """
        Yardımcı: temel oturum oluştur.
        kilitli=True ise protokol kilitler.
        """
        d = dongu.AnalizDongusu(
            {"soran": "X", "karar": "devriye", "urun_turu": "taktik"},
            amac=amac,
            mod="kesif"
        )
        d.planla()
        if kilitli:
            d.protokol_kilitle("bir hipotez", "Sener")
        return d

    def test_bes_halka_dondurur(self):
        """
        zincir_ozeti() başarı durumunda halkalar listesi 5 elemanlı
        ve halka adları provenans.HALKALAR ile aynı sırada olmalı.
        """
        d = self._oturum()
        manifesto = d.manifesto

        ozet = provenans.zincir_ozeti(manifesto)

        self.assertIn("halkalar", ozet)
        self.assertEqual(len(ozet["halkalar"]), 5)

        halka_adlari = [h["halka"] for h in ozet["halkalar"]]
        self.assertEqual(halka_adlari, list(provenans.HALKALAR))

    def test_bos_oturumda_eksikler_isaretlenir(self):
        """
        Sadece planla() çağrılmış bir oturumda hazirlik/veri/akademik
        halkalarının kanit_turu provenans.EKSIK olmalı.
        """
        d = self._oturum()
        manifesto = d.manifesto

        ozet = provenans.zincir_ozeti(manifesto)

        halkalar = {h["halka"]: h for h in ozet["halkalar"]}

        # Hazırlık beyani verilmediği için EKSIK.
        self.assertEqual(halkalar["hazirlik"]["kanit_turu"], provenans.EKSIK)

        # Veri kimliği yazılmadığı için EKSIK.
        self.assertEqual(halkalar["veri"]["kanit_turu"], provenans.EKSIK)

        # Akademik denetim bağlanmadığı için EKSIK.
        self.assertEqual(halkalar["akademik"]["kanit_turu"], provenans.EKSIK)

    def test_hazirlik_beyan_olarak_gorunur(self):
        """
        Hazırlık beyani verildikten sonra hazirlik halkasının
        kanit_turu BEYAN olmalı, MAKINE OLMAMALI.
        """
        d = self._oturum()
        manifesto = d.manifesto

        adimlar = [{"islem": "test", "aciklama": "", "kaynak": ""}]
        provenans.hazirlik_beyani(manifesto, adimlar, "X")

        ozet = provenans.zincir_ozeti(manifesto)
        halkalar = {h["halka"]: h for h in ozet["halkalar"]}

        self.assertEqual(halkalar["hazirlik"]["kanit_turu"], provenans.BEYAN)
        self.assertNotEqual(halkalar["hazirlik"]["kanit_turu"], provenans.MAKINE)

    def test_hazirlik_beyani_her_zaman_kopukluk_uretir(self):
        """
        Hazırlık beyani verilmiş olsa bile kopukluklar listesinde
        'hazirlik' geçen bir madde bulunmalı (beyan makineyle doğrulanamaz).
        """
        d = self._oturum()
        manifesto = d.manifesto

        adimlar = [{"islem": "hazırlık", "aciklama": "x", "kaynak": "y"}]
        provenans.hazirlik_beyani(manifesto, adimlar, "X")

        ozet = provenans.zincir_ozeti(manifesto)

        # kopukluklar listesinde 'hazirlik' geçen bir madde var mı?
        hazirlik_kopukluk = any(
            "hazirlik" in k.lower() for k in ozet["kopukluklar"]
        )
        self.assertTrue(hazirlik_kopukluk,
                       "kopukluklar'da hazirlik uyarısı olmalı")

    def test_onkayit_halkasi_kilitten_sonra_makine(self):
        """
        amac='dogrulayici' oturumda planla()+protokol_kilitle() sonrası
        onkayit halkasının kanit_turu MAKINE olmalı.
        """
        d = dongu.AnalizDongusu(
            {"soran": "X", "karar": "devriye", "urun_turu": "taktik"},
            amac="dogrulayici",
            mod="kesif"
        )
        d.planla()
        d.protokol_kilitle("hipotez", "Sener")
        manifesto = d.manifesto

        ozet = provenans.zincir_ozeti(manifesto)
        halkalar = {h["halka"]: h for h in ozet["halkalar"]}

        self.assertEqual(halkalar["onkayit"]["kanit_turu"], provenans.MAKINE)

    def test_tam_makine_zinciri_eksikken_false(self):
        """
        Eksik halka varken tam_makine_zinciri False olmalı.
        """
        d = self._oturum()
        manifesto = d.manifesto

        ozet = provenans.zincir_ozeti(manifesto)

        # Hazırlık, veri, akademik eksik olduğundan tam_makine_zinciri False.
        self.assertFalse(ozet["tam_makine_zinciri"])

    def test_veri_halkasi_kimlikle_makine_olur(self):
        """
        veri_bagla(..., veri_yolu=<dosya>) çağrılması sonrası
        veri halkasının kanit_turu MAKINE olmalı ve özetinde
        dosya adı geçmeli.
        """
        # Geçici dosya oluştur.
        veri_dosya = os.path.join(self.tmp, "test_veri.csv")
        with open(veri_dosya, "wb") as f:
            f.write(b"test data")

        d = self._oturum()
        d.veri_bagla({"n": 100, "uyarilar": []}, veri_yolu=veri_dosya)
        manifesto = d.manifesto

        ozet = provenans.zincir_ozeti(manifesto)
        halkalar = {h["halka"]: h for h in ozet["halkalar"]}

        # Veri halkası MAKINE olmalı.
        self.assertEqual(halkalar["veri"]["kanit_turu"], provenans.MAKINE)

        # Özetinde dosya adı geçmeli.
        self.assertIn("test_veri.csv", halkalar["veri"]["ozet"])


if __name__ == "__main__":
    unittest.main()
