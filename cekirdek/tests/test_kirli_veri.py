# -*- coding: utf-8 -*-
"""
Kirli-veri gold-set testleri (Faz 1.5, Değişiklik 5):
kısmen eksik koordinat, karışık tarih formatı, duplikat, aşırı yayılım,
seyrek hücre, tek-nokta koordinat — doğru bayraklar kalkıyor mu,
uygunsuz analiz reddediliyor mu, sessiz filtreleme raporlanıyor mu?
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from suc_analizi import veri, ileri, istatistik


KIRLI = [
    # karışık tarih formatları + bazıları bozuk + eksik koordinat + duplikat
    {"id": "1", "tarih": "2026-05-01 10:00", "lat": "41.01", "lon": "29.01", "tur": "hırsızlık", "zarar": "1500"},
    {"id": "2", "tarih": "02.05.2026 11:00", "lat": "41.02", "lon": "29.02", "tur": "kapkaç", "zarar": "25000"},
    {"id": "3", "tarih": "BOZUK", "lat": "41.03", "lon": "29.03", "tur": "kavga", "zarar": "300"},
    {"id": "4", "tarih": "2026-05-04", "lat": "", "lon": "", "tur": "hırsızlık", "zarar": "1500000"},
    {"id": "4", "tarih": "2026-05-04", "lat": "", "lon": "", "tur": "hırsızlık", "zarar": "1500000"},  # tam duplikat
    {"id": "5", "tarih": "2026-05-05 09:00", "lat": "91.0", "lon": "29.05", "tur": "dolandırıcılık", "zarar": "4000"},  # geçersiz lat
]

TEK_NOKTA = [{"id": str(i), "tarih": "2026-05-01", "lat": "41.0", "lon": "29.0"}
             for i in range(40)]


class TestKirliVeri(unittest.TestCase):
    def setUp(self):
        veri.son_okuma["kesildi"] = False

    def test_profil_bayraklari(self):
        k = veri.tiplendir(KIRLI)
        prof = veri.veri_profili(k, sayisal_alan="zarar")
        self.assertAlmostEqual(prof["duplikat_oran"], round(1 / 6, 3), places=3)
        self.assertAlmostEqual(prof["tarih_basari_oran"], round(5 / 6, 3), places=3)
        # geçerli koordinat: 1,2,3 → 3/6 (4 boş, 5 geçersiz lat)
        self.assertAlmostEqual(prof["koordinat_gecerli_oran"], 0.5, places=3)
        self.assertFalse(prof["koordinat_tek_nokta"])
        self.assertIn("zaman_kapsam", prof)

    def test_tek_nokta_reddedilir(self):
        prof = veri.veri_profili(veri.tiplendir(TEK_NOKTA))
        self.assertTrue(prof["koordinat_tek_nokta"])
        karar = veri.analiz_uygun_mu(prof, "kde_yogunluk")
        self.assertFalse(karar["uygun"])

    def test_paydasiz_oran_reddedilir(self):
        karar = veri.analiz_uygun_mu({"n": 5}, "suc_oranlari", payda_var=False)
        self.assertFalse(karar["uygun"])
        self.assertTrue(any("payda" in s for s in karar["sebepler"]))

    def test_benford_mertebe_reddedilir(self):
        # tek mertebeli veri (100-999)
        k = [{"v": str(100 + i)} for i in range(50)]
        prof = veri.veri_profili(k, sayisal_alan="v")
        karar = veri.analiz_uygun_mu(prof, "benford")
        self.assertFalse(karar["uygun"])

    def test_asiri_yayilim_bayragi(self):
        # var >> mean sayım dağılımı
        sayim = {f"b{i}": (200 if i == 0 else 2) for i in range(12)}
        sonuc = ileri.bolge_anomali(sayim)
        self.assertTrue(any("yayılım" in n for n in sonuc["notlar"]))
        self.assertTrue(any("FDR" in n or "q" in n for n in sonuc["notlar"]))
        self.assertIn("q", sonuc["tum_sonuclar"][0])

    def test_fdr_kontrolu(self):
        qs = ileri.fdr_benjamini_hochberg([0.001, 0.01, 0.04, 0.5])
        self.assertEqual(len(qs), 4)
        self.assertLessEqual(qs[0], 0.01)   # en küçük p güçlü kalır
        self.assertGreater(qs[3], 0.4)      # büyük p şişirilir

    def test_duplikat_silinmez(self):
        sonuc = veri.duplikat_isaretle(KIRLI)
        self.assertEqual(len(sonuc["kayitlar"]), len(KIRLI))  # silme YOK
        self.assertEqual(sonuc["duplikat_sayisi"], 1)
        self.assertTrue(sonuc["kayitlar"][4]["_duplikat"])

    def test_duyarlilik_iki_ozet(self):
        degerler = [10, 11, 9, 10, 12, 11, 10, 9, 10, 11, 9, 10] + [500]
        s = istatistik.duyarlilik_analizi(degerler)
        self.assertEqual(s["aykiri_sayisi"], 1)
        self.assertGreater(s["dahil"]["ortalama"], s["haric"]["ortalama"])

    def test_otokorelasyon_haftalik(self):
        seri = [10 + (5 if i % 7 == 0 else 0) for i in range(70)]
        r7 = ileri.otokorelasyon(seri, 7)
        r3 = ileri.otokorelasyon(seri, 3)
        self.assertGreater(r7, r3)  # haftalık desen lag=7'de güçlü

    def test_nominal_ortalama_engellenir(self):
        karar = veri.analiz_uygun_mu({"n": 100}, "ozet",
                                     olcum_duzeyi="nominal-ikili")
        self.assertFalse(karar["uygun"])

    def test_ki_kare_gate_cochran(self):
        karar = veri.analiz_uygun_mu(
            {"n": 20}, "ki_kare_testi", beklenen_hucreler=[1, 2, 1, 3, 30, 40])
        self.assertTrue(any("Cochran" in s for s in karar["sebepler"]))


if __name__ == "__main__":
    unittest.main()
