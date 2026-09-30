# -*- coding: utf-8 -*-
"""
test_seri_eslestirme.py — seri ADAYI eşleştirme (A4.2, A4.8).

BMK v0 (K3.2–K3.4): düz Jaccard, çok yaygın bir MO ifadesini paylaşan BAĞIMSIZ
olayları seri sayıyordu (kesinlik %5); çıktı uyarı taşımıyor, insan onayı
istemiyordu. BMK v2 (K8.4, K8.7, K8.9, K8.10): oran eşiği + ikili süzgeç
tutarsız ve yayılmış seriyi kaçırıyordu; A4.8 MO ayırt edicilik testi (FDR, iki
aile) ve katmanlı kanıt hatları. Test verisi elle yazılmış ve sentetiktir.
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

    def test_ayni_mo_uzakta_zayif_aday_parametre_gucluye_ceker(self):
        # A4.8: pencere dışı ama MO'su ayırt edici çift ATILMAZ (A4.2 atıyordu —
        # yayılmış seride geri çağırma %20); zayıf katmanda, gerekçesiyle döner.
        uzak = self._seri(dlat=0.09, gun=5)      # ~10 km
        a = tekrar.seri_eslestirme(uzak, "mo")
        self.assertEqual([(c["katman"], c["uzay_zaman"]) for c in a], [("zayıf", "uzak")])
        self.assertEqual((a[0]["kanit"]["uzay"]["durum"], a[0]["kanit"]["zaman"]["durum"]),
                         ("uzak", "yakın"))
        self.assertEqual(tekrar.seri_eslestirme(uzak, "mo", mesafe_km=20)[0]["katman"], "güçlü")
        gec = self._seri(dlat=0.002, gun=120)    # 120 gün
        a = tekrar.seri_eslestirme(gec, "mo")
        self.assertEqual((a[0]["katman"], a[0]["kanit"]["zaman"]["durum"]), ("zayıf", "uzak"))
        self.assertEqual(tekrar.seri_eslestirme(gec, "mo", gun=180)[0]["katman"], "güçlü")

    def test_konum_ya_da_tarih_yoksa_bilinmiyor_olarak_doner(self):
        kayitlar = [kayit(0, AYIRT_EDICI, konum=False), kayit(1, AYIRT_EDICI, konum=False)]
        kayitlar += [kayit(10 + i, d, konum=False) for i, d in enumerate(DOLGU)]
        adaylar = tekrar.seri_eslestirme(kayitlar, "mo")
        self.assertEqual(len(adaylar), 1)
        self.assertEqual(adaylar[0]["uzay_zaman"], "bilinmiyor")
        self.assertEqual(adaylar[0]["katman"], "zayıf")   # tek kanıt hattı
        self.assertIsNone(adaylar[0]["mesafe_km"])

    def test_siralama_girdi_sirasindan_bagimsiz(self):
        kayitlar = self._seri(dlat=0.002, gun=5)
        self.assertEqual(tekrar.seri_eslestirme(kayitlar, "mo"),
                         tekrar.seri_eslestirme(list(reversed(kayitlar)), "mo"))


def dolgu(n, bas=100):
    """Birbirine benzemeyen, zamanca uzak dolgu kayıtları (her biri kendine özgü)."""
    return [kayit(100 + i, f"f{i} g{i}", dlat=0.2, gun=bas + 100 * i) for i in range(n)]


class TestAyirtEdicilikTesti(unittest.TestCase):
    """A4.8: MO kanıtı bir anlamlılık testidir; çoklu test iki ailede."""

    def _orta_kanit(self, yakin):
        # r0-r1 iki orta nadirlikte davranış paylaşır (x, y: 30 kaydın 3'ünde)
        gun1 = 0 if yakin else 300
        kayitlar = [kayit(0, "x y a0", gun=0), kayit(1, "x y a1", gun=gun1),
                    kayit(2, "x b2", gun=5000), kayit(3, "y b3", gun=6000)]
        return kayitlar + dolgu(26)

    def test_ayni_mo_kaniti_yalniz_uzay_zamanla_ortusurse_aday(self):
        # p < 0,05 ama 435 çiftlik ailede FDR'yi geçmez; pencere içindeyse
        # MO'dan bağımsız seçilmiş küçük ailede geçer → güçlü.
        yakin = tekrar.seri_eslestirme(self._orta_kanit(True), "mo")
        self.assertEqual([(c["id1"], c["id2"], c["katman"]) for c in yakin],
                         [("k0", "k1", "güçlü")])
        p = yakin[0]["kanit"]["mo"]["p"]
        self.assertLess(p, 0.05)
        self.assertGreater(yakin[0]["kanit"]["mo"]["q_tum"], 0.05)
        self.assertLessEqual(yakin[0]["kanit"]["mo"]["q_pencere"], 0.05)
        # aynı MO kanıtı, pencere dışında: çoklu testten geçemez → aday yok
        self.assertEqual(tekrar.seri_eslestirme(self._orta_kanit(False), "mo"), [])

    def test_tutarsiz_seri_uc_ayirt_edici_davranisla_baglanir(self):
        # her olay 6 davranıştan 4'ünü + kendine özgü bir kelimeyi kullanır; k0 ile
        # k1 ve k2 üçer davranış paylaşır: Ružička 0,6'nın altında (A4.2 kaçırırdı)
        kayitlar = [kayit(0, "b0 b1 b2 b3 g0"), kayit(1, "b0 b1 b2 b4 g1", dlat=0.001, gun=3),
                    kayit(2, "b1 b2 b3 b5 g2", dlat=0.002, gun=6)] + dolgu(20)
        adaylar = tekrar.seri_eslestirme(kayitlar, "mo")
        bulunan = {(c["id1"], c["id2"]): c for c in adaylar}
        self.assertTrue({("k0", "k1"), ("k0", "k2")} <= set(bulunan), set(bulunan))
        for cift in (("k0", "k1"), ("k0", "k2")):
            self.assertEqual(bulunan[cift]["katman"], "güçlü")
            self.assertLess(bulunan[cift]["benzerlik"], 0.6)
        self.assertTrue(all(c["id1"] in {"k0", "k1", "k2"} for c in adaylar))

    @staticmethod
    def _asimetrik():
        """k1, k0'ın 8 davranışına bir kelime ekler (iki yönün kuyruğu farklı)."""
        kayitlar = [kayit(0, AYIRT_EDICI), kayit(1, AYIRT_EDICI + " nakit", dlat=0.002, gun=5)]
        return kayitlar + [kayit(10 + i, d, dlat=0.3, gun=100) for i, d in enumerate(DOLGU)]

    def test_istege_bagli_benzerlik_esigi_ek_suzgectir(self):
        kayitlar = self._asimetrik()
        a = tekrar.seri_eslestirme(kayitlar, "mo")
        self.assertEqual(len(a), 1)
        self.assertLess(a[0]["benzerlik"], 0.99)
        self.assertEqual(tekrar.seri_eslestirme(kayitlar, "mo", benzerlik_esik=0.99), [])

    def test_iki_yonun_ihtiyatli_olani_raporlanir(self):
        kayitlar = self._asimetrik()
        c = tekrar.seri_eslestirme(kayitlar, "mo")[0]
        import math
        n = len(kayitlar)
        df = {}
        for k in kayitlar:
            for t in set(k["mo"].split()):
                df[t] = df.get(t, 0) + 1
        ortak = set(kayitlar[0]["mo"].split()) & set(kayitlar[1]["mo"].split())
        bilgi = sum(math.log(n / df[t]) for t in ortak)   # kanit'teki değer yuvarlanmış

        def yon(mo):
            ts = [t for t in set(mo.split()) if df[t] < n]
            return tekrar._kuyruk_olasiligi([math.log(n / df[t]) for t in ts],
                                            [df[t] / n for t in ts], bilgi)[0]
        pa, pb = yon(kayitlar[0]["mo"]), yon(kayitlar[1]["mo"])
        self.assertNotAlmostEqual(pa, pb, places=12)
        # elle: k0 8 kelimenin hepsi (1/3)^8; k1 9 kelimeden ≥ 8'i
        self.assertAlmostEqual(pb, 9 * (1 / 3) ** 8 * (2 / 3) + (1 / 3) ** 9, places=10)
        self.assertAlmostEqual(c["kanit"]["mo"]["p"], max(pa, pb), places=8)

    def test_cikti_sozlesmesi(self):
        adaylar = tekrar.seri_eslestirme(self._orta_kanit(True), "mo")
        for c in adaylar:
            self.assertIn(c["katman"], {"güçlü", "zayıf"})
            self.assertTrue({"mo", "uzay", "zaman"} <= set(c["kanit"]))
            self.assertEqual(c["kanit"]["uzay"]["esik_km"], tekrar.SERI_MESAFE_KM)

    def test_q_esik_arac_dogrulamasi(self):
        from sinama.cekirdek.hatalar import KullanimHatasi
        with self.assertRaises(KullanimHatasi):
            sunucu.arac_calistir("seri_eslestirme", {"satirlar": self._orta_kanit(True),
                                                      "mo_alan": "mo", "q_esik": 1.5})


class TestKuyrukOlasiligi(unittest.TestCase):
    def test_kesin_degerler(self):
        k = tekrar._kuyruk_olasiligi
        self.assertEqual(k([1, 1], [0.5, 0.5], 1.0), (0.75, True))
        self.assertEqual(k([1, 1], [0.5, 0.5], 2.0), (0.25, True))
        self.assertAlmostEqual(k([3, 2, 1], [0.1, 0.2, 0.3], 3)[0], 0.154)

    def test_toplama_sirasindan_gelen_kayan_nokta_farki(self):
        # (0,1+0,2)+0,3 = 0,6000000000000001 > 0,3+0,2+0,1 = 0,6
        p, _ = tekrar._kuyruk_olasiligi([0.1, 0.2, 0.3], [0.5] * 3, (0.1 + 0.2) + 0.3)
        self.assertAlmostEqual(p, 0.125)

    def test_butce_asilinca_chernoff_ihtiyatli(self):
        w, p = [1.2, 0.9, 0.8, 0.7, 0.5, 0.4, 0.3], [0.2, 0.3, 0.1, 0.4, 0.2, 0.3, 0.5]
        kesin, _ = tekrar._kuyruk_olasiligi(w, p, 2.5)
        eski = tekrar._KUYRUK_BUTCE
        tekrar._KUYRUK_BUTCE = 2
        try:
            sinir, kesin_mi = tekrar._kuyruk_olasiligi(w, p, 2.5)
        finally:
            tekrar._KUYRUK_BUTCE = eski
        self.assertFalse(kesin_mi)
        self.assertGreaterEqual(sinir, kesin)
        self.assertLess(sinir, 1.0)


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
