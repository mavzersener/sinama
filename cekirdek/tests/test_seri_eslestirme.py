# -*- coding: utf-8 -*-
"""
test_seri_eslestirme.py — seri ADAYI eşleştirme (A4.2).

BMK v0 (K3.2–K3.4): düz Jaccard, çok yaygın bir MO ifadesini paylaşan BAĞIMSIZ
olayları seri sayıyordu (kesinlik %5); çıktı uyarı taşımıyor, insan onayı
istemiyordu. Test verisi elle yazılmış ve sentetiktir.
"""
import datetime
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sinama.cekirdek import tekrar  # noqa: E402
from sinama.arayuz import sunucu  # noqa: E402
from sinama.arayuz.ortak import ARAC_POLITIKALARI  # noqa: E402

GUN0 = datetime.date(2025, 1, 1)
YAYGIN = "kapi kirilarak girildi"
AYIRT_EDICI = "balkon kapisi levye ile zorlanmis yalniz altin alinmis"
DOLGU = ["pencere cam nakit", "bahce merdiven telefon", "garaj bisiklet esya",
         "cati bodrum saat"]


def kayit(i, mo, dlat=0.0, gun=0, konum=True):
    """Tek sentetik kayıt; dlat derece kaydırma (0,01° ≈ 1,1 km)."""
    k = {"id": f"k{i}", "mo": mo}
    if konum:
        k.update({"lat": 41.0 + dlat, "lon": 29.0,
                  "tarih": (GUN0 + datetime.timedelta(days=gun)).isoformat()})
    return k


class TestTabanOrani(unittest.TestCase):
    def test_yaygin_mo_paylasan_bagimsizlar_aday_olmaz(self):
        # 6 bağımsız olay yaygın MO + kendine özgü bir kelime; birbirine YAKIN
        # (uzay-zaman süzgeci bunları elemesin — yalnız taban oranı sınanır).
        kayitlar = [kayit(i, f"{YAYGIN} ozel{i}", dlat=0.001 * i, gun=i) for i in range(6)]
        kayitlar += [kayit(10 + i, d, dlat=0.5, gun=200) for i, d in enumerate(DOLGU)]
        # düz Jaccard bu 15 çiftin HEPSİNİ 3/5 = 0,6 ile işaretlerdi
        adaylar = tekrar.seri_eslestirme(kayitlar, "mo")
        self.assertEqual(adaylar, [], "yaygın MO'yu paylaşan bağımsızlar aday sayıldı")

    def test_her_kayitta_gecen_kelime_agirliksizdir(self):
        # tek ortak kelime her kayıtta varsa bilgi taşımaz: benzerlik tanımsız → aday yok
        kayitlar = [kayit(0, "ev"), kayit(1, "ev")]
        self.assertEqual(tekrar.seri_eslestirme(kayitlar, "mo"), [])


class TestUzayZaman(unittest.TestCase):
    def _seri(self, dlat, gun):
        kayitlar = [kayit(0, AYIRT_EDICI), kayit(1, AYIRT_EDICI + " nakit", dlat=dlat, gun=gun)]
        kayitlar += [kayit(10 + i, d, dlat=0.3, gun=100) for i, d in enumerate(DOLGU)]
        return kayitlar

    def test_ayirt_edici_mo_ve_yakinlik_aday_olur(self):
        adaylar = tekrar.seri_eslestirme(self._seri(dlat=0.002, gun=5), "mo")
        self.assertEqual(len(adaylar), 1)
        a = adaylar[0]
        self.assertEqual({a["id1"], a["id2"]}, {"k0", "k1"})
        self.assertEqual(a["uzay_zaman"], "yakin")
        self.assertIs(a["ayni_fail_cikarimi"], False)
        self.assertLess(a["mesafe_km"], 0.3)
        self.assertEqual(a["gun_farki"], 5)

    def test_ayni_mo_uzakta_aday_olmaz_parametre_genisletir(self):
        uzak = self._seri(dlat=0.09, gun=5)      # ~10 km
        self.assertEqual(tekrar.seri_eslestirme(uzak, "mo"), [])
        self.assertEqual(len(tekrar.seri_eslestirme(uzak, "mo", mesafe_km=20)), 1)
        gec = self._seri(dlat=0.002, gun=120)    # 120 gün
        self.assertEqual(tekrar.seri_eslestirme(gec, "mo"), [])
        self.assertEqual(len(tekrar.seri_eslestirme(gec, "mo", gun=180)), 1)

    def test_konum_ya_da_tarih_yoksa_bilinmiyor_olarak_doner(self):
        kayitlar = [kayit(0, AYIRT_EDICI, konum=False), kayit(1, AYIRT_EDICI, konum=False)]
        kayitlar += [kayit(10 + i, d, konum=False) for i, d in enumerate(DOLGU)]
        adaylar = tekrar.seri_eslestirme(kayitlar, "mo")
        self.assertEqual(len(adaylar), 1)
        self.assertEqual(adaylar[0]["uzay_zaman"], "bilinmiyor")
        self.assertIsNone(adaylar[0]["mesafe_km"])

    def test_siralama_girdi_sirasindan_bagimsiz(self):
        kayitlar = self._seri(dlat=0.002, gun=5)
        self.assertEqual(tekrar.seri_eslestirme(kayitlar, "mo"),
                         tekrar.seri_eslestirme(list(reversed(kayitlar)), "mo"))


class TestKisiBaglantisiSozlesmesi(unittest.TestCase):
    """Benzerlik ya da bağlantı kimlik değildir: insan onayı + açık uyarı."""

    def test_uc_arac_da_insan_onayi_ister(self):
        for ad in ("seri_eslestirme", "bulanik_eslesme", "ag_analizi"):
            self.assertTrue(ARAC_POLITIKALARI[ad]["insan_onayi"], ad)

    def test_seri_eslestirme_meta_uyari_ve_onay_tasir(self):
        kayitlar = [kayit(0, AYIRT_EDICI), kayit(1, AYIRT_EDICI, dlat=0.001, gun=2)]
        kayitlar += [kayit(10 + i, d, dlat=0.3, gun=100) for i, d in enumerate(DOLGU)]
        paket = sunucu.arac_calistir("seri_eslestirme", {"satirlar": kayitlar, "mo_alan": "mo"})
        self.assertTrue(paket["meta"]["insan_onayi_gerekir"])
        metin = " ".join(paket["meta"]["uyarilar"]).lower()
        self.assertIn("kimlik", metin)
        self.assertIn("fail", metin)
        self.assertTrue(all(c["ayni_fail_cikarimi"] is False for c in paket["sonuc"]))


if __name__ == "__main__":
    unittest.main()
