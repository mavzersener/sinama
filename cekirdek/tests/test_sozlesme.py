# -*- coding: utf-8 -*-
"""
test_sozlesme.py — araç sözleşme testi jeneratörü (v6.6, H3.3).

Her araç için minimal geçerli çağrı: şema iyi biçimli, isle() hatasız
döner, {sonuc, meta} sözleşmesi sağlanır, meta.uyarilar listedir.
Kayıt ARACLAR üzerinden TARANIR — yeni araç otomatik kapsanır; özel
argüman gerekiyorsa bu test düşer ve ARG_OZEL tablosu güncellenir
(yapısal zorlama). Döngü ailesi (dongu_*, muhakeme_izi, kanit_dogrula)
PPDAC sırasıyla ayrı testte uçtan uca koşar.
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TMP_VERI = tempfile.mkdtemp()
TMP_LOG = tempfile.mkdtemp()
os.environ["SINAMA_VERI_KOKU"] = TMP_VERI
os.environ["SINAMA_LOG_DIR"] = TMP_LOG

from sinama.arayuz import sunucu            # noqa: E402
from sinama.arayuz.ortak import ARACLAR     # noqa: E402


def _ortami_kur():
    """setUpClass çağırır — başka testlerin tearDown'u ortam değişkenini
    kaldırırsa (import sırası kırılgandır) tekrar kurar."""
    os.environ["SINAMA_VERI_KOKU"] = TMP_VERI
    os.environ["SINAMA_LOG_DIR"] = TMP_LOG


def _kayitlar(n=120, gun=45):
    """Standart sözleşme verisi: 3 tür, 3 mahalle, 45 gün, geniş
    mertebe aralıklı zarar (benford), benzer MO metinleri."""
    k = []
    turler = ["hırsızlık", "kapkaç", "dolandırıcılık"]
    mahalleler = ["merkez", "liman", "istasyon"]
    molar = ["cam kırılarak girildi", "cam kırarak girildi",
             "kapı zorlandı", "kilidi kırarak"]
    for i in range(n):
        t = datetime(2026, 5, 1) + timedelta(days=i % gun,
                                             hours=i % 24)
        k.append({
            "id": f"O{i}",
            "tarih": t.strftime("%Y-%m-%d %H:%M"),
            "lat": 41.03 + (i % 7) * 0.01,
            "lon": 28.97 + (i % 5) * 0.01,
            "tur": turler[i % 3],
            "mahalle": mahalleler[i % 3],
            "adet": 1 + i % 5,
            "zarar_tl": 100 + (i * 377) % 900000,
            "mo": molar[i % 4],
        })
    return k


KAYITLAR = _kayitlar()
X2 = [[i, i % 3] for i in range(1, 13)]   # iki kolineer olmayan değişken
Y2 = [2 * r[0] + r[1] for r in X2]

# Özel argüman gereken araçlar; gerisi {"satirlar": KAYITLAR} alır.
ARG_OZEL = {
    "frekans": {"alan": "tur"},
    "esitlik_analizi": {"alan": "mahalle"},
    "capraz_tablo": {"a": "tur", "b": "mahalle"},
    "dagilim_olculeri": {"alan": "adet"},
    "ki_kare_testi": {"a": "tur", "b": "mahalle"},
    "fisher_exact": {"a": 8, "b": 3, "c": 2, "d": 9},
    "phi": {"a": 8, "b": 3, "c": 2, "d": 9},
    "iki_oran_testi": {"x1": 8, "n1": 40, "x2": 3, "n2": 40},
    "binomial_test": {"x": 7, "n": 20, "p0": 0.5},
    "oran_karsilastir": {"k1": 12, "e1": 1000, "k2": 4, "e2": 1000},
    "t_testi": {"tip": "bagimsiz", "x": [1, 2, 3, 4, 5],
                "y": [2, 3, 4, 5, 6]},
    "mann_whitney": {"x": [1, 2, 3, 4, 5], "y": [3, 4, 5, 6, 7]},
    "spearman": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]},
    "kendall": {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]},
    "randomizasyon_testi": {"x": [1, 2, 3, 4, 5], "y": [3, 4, 5, 6, 7]},
    "pearson": {"x": "adet", "y": "zarar_tl"},
    "anova": {"gruplar": {"a": [1, 2, 3], "b": [2, 3, 4], "c": [3, 4, 5]}},
    "kruskal_wallis": {"gruplar": {"a": [1, 2, 3], "b": [2, 3, 4],
                                   "c": [3, 4, 5]}},
    "coklu_regresyon": {"X": X2, "y": Y2},
    "lojistik_regresyon": {"X": X2, "y": [i % 2 for i in range(12)]},
    "guc_analizi": {"tip": "oran", "p1": 0.3, "p2": 0.5},
    "benford": {"alan": "zarar_tl"},
    "mukerrer_magduriyet": {"alan": "mahalle"},
    "power_few": {"grup_alan": "mahalle"},
    "hacim_zarar_karsilastir": {"grup_alan": "mahalle"},
    "bolge_anomali": {"bolge_alan": "mahalle"},
    "suc_oranlari": {"bolgeler": [{"bolge": "merkez", "olay": 15,
                                   "nufus": 10000},
                                  {"bolge": "liman", "olay": 8,
                                   "nufus": 12000}]},
    "ag_analizi": {"kenarlar": [["A", "B", 3], ["B", "C", 2],
                                ["C", "A", 1]], "analiz": "pagerank"},
    "seri_eslestirme": {"mo_alan": "mo"},
    "bulanik_eslesme": {"alan": "mahalle", "hedef": "merkez"},
    "endeks_hesapla": {"gostergeler": ["adet", "zarar_tl"]},
    "orneklem_cek": {"yontem": "tabakali", "n": 10,
                     "tabaka_alan": "mahalle"},
    "risk_skorla": {"kurallar": [{"alan": "tur", "kosul": "==",
                                  "deger": "hırsızlık", "agirlik": 2}]},
    "degerlendirme_did": {"mudahale_once": 20, "mudahale_sonra": 10,
                          "kontrol_once": 18, "kontrol_sonra": 16},
    "wdd_testi": {"t_once": 100, "t_sonra": 60, "k_once": 100, "k_sonra": 98},
    "yukselen_sicak_nokta": {"bolge_alan": "mahalle", "zaman_alan": "tarih",
                             "donem_sayisi": 4},
    "konsantrasyon_dagilimi": {"bolge_alan": "mahalle", "zaman_alan": "tarih"},
    "mekansal_regresyon": {"hedef": "zarar_tl", "degiskenler": ["adet"]},
    "risk_arazi": {"faktor_alan": "tur"},
    "bolge_oran": {"bolge_alan": "mahalle"},
    "teori_yorumu": {"bulgu": "kalici_sicak_nokta"},
    "brifing_uret": {"urun_turu": "taktik",
                     "belirsizlik": ["sözleşme testi verisi"]},
}

# Oturum tabanlı araçlar: jenerik {satirlar} çağrısıyla sınanamazlar,
# canlı bir PPDAC oturumu isterler. Kendi test dosyalarında kapsanırlar
# (test_dongu*.py, test_kanit_muhakeme.py, test_provenans.py).
DONGU_AILESI = {"dongu_baslat", "dongu_veri", "dongu_analize_gec",
                "dongu_analiz", "dongu_sonuc", "dongu_izleme",
                "dongu_durum", "muhakeme_izi", "kanit_dogrula",
                "provenans_hazirlik", "provenans_dis_denetim",
                "provenans_ozet"}


def _cagir(ad, argumanlar):
    r = sunucu.isle({"method": "tools/call", "id": 1,
                     "params": {"name": ad, "arguments": argumanlar}})
    return r["result"]


class TestSozlesmeTumAraclar(unittest.TestCase):
    """Registry üzerinden TÜM araçlar: şema + çalıştırma + {sonuc, meta}."""

    @classmethod
    def setUpClass(cls):
        _ortami_kur()

    def test_her_arac_sozlesme_kapsaminda(self):
        for ad in sorted(ARACLAR):
            if ad in DONGU_AILESI:
                continue
            with self.subTest(arac=ad):
                t = ARACLAR[ad]
                # 1) şema iyi biçimli
                self.assertEqual(t["sema"].get("type"), "object")
                self.assertIsInstance(t["sema"].get("properties"), dict)
                # 2) minimal geçerli çağrı -32602'siz çalışır
                arg = {"satirlar": KAYITLAR}
                arg.update(ARG_OZEL.get(ad, {}))
                r = _cagir(ad, arg)
                self.assertFalse(r.get("isError", False),
                                 f"{ad}: {r['content'][0]['text'][:200]}")
                # 3) {sonuc, meta} sözleşmesi
                paket = json.loads(r["content"][0]["text"])
                self.assertIn("sonuc", paket)
                self.assertIn("meta", paket)
                self.assertEqual(paket["meta"]["arac"], ad)
                self.assertIsInstance(paket["meta"]["uyarilar"], list)

    def test_registry_bos_degil_ve_tablo_tutarli(self):
        self.assertGreaterEqual(len(ARACLAR), 60)
        for ad in ARG_OZEL:
            self.assertIn(ad, ARACLAR, f"ARG_OZEL'de ölü araç: {ad}")
        self.assertTrue(DONGU_AILESI <= set(ARACLAR))


class TestSozlesmeDonguAilesi(unittest.TestCase):
    """Döngü araçları PPDAC sırasıyla uçtan uca; her adımda sözleşme."""

    @classmethod
    def setUpClass(cls):
        _ortami_kur()

    def _paket(self, ad, arg):
        r = _cagir(ad, arg)
        self.assertFalse(r.get("isError", False),
                         f"{ad}: {r['content'][0]['text'][:200]}")
        paket = json.loads(r["content"][0]["text"])
        self.assertIn("sonuc", paket)
        self.assertIn("meta", paket)
        return paket["sonuc"]

    def test_tam_ppdac_turu(self):
        s = self._paket("dongu_baslat", {"karar": "sözleşme testi",
                                         "urun_turu": "taktik"})
        oid = s["oturum_id"]
        veri_sonucu = self._paket("dongu_veri", {"oturum_id": oid,
                                  "satirlar": KAYITLAR, "analiz": "frekans"})
        self._paket("dongu_analize_gec",
                    {"oturum_id": oid,
                     "uygunluk": veri_sonucu["uygunluk"]})
        self._paket("dongu_analiz",
                    {"oturum_id": oid, "arac": "frekans",
                     "gerekce": {"hipotez": "h", "yorum": "y"},
                     "argumanlar": {"alan": "tur", "satirlar": KAYITLAR}})
        self._paket("muhakeme_izi", {"oturum_id": oid})
        self._paket("dongu_sonuc",
                    {"oturum_id": oid, "sonuc_turu": "sorun_dogrulandi",
                     "onaylayan": "sözleşme testi"})
        self._paket("dongu_izleme",
                    {"oturum_id": oid, "metrik": "haftalık olay",
                     "esik": 20, "kontrol_tarihi": "2026-08-01"})
        self._paket("dongu_durum", {"oturum_id": oid})
        d = self._paket("kanit_dogrula", {"oturum_id": oid})
        self.assertTrue(d["saglam"])

    def test_dongu_ailesi_kapsam_tam(self):
        # Muafiyet listesi kendiliğinden büyüyemez: oturum tabanlı araçlar
        # AÇIKÇA sayılır. Yeni bir araç sessizce muaf edilirse bu test kırılır.
        kayitli = {a for a in ARACLAR if a.startswith("dongu_")}
        kayitli |= {a for a in ARACLAR if a.startswith("provenans_")}
        self.assertEqual(kayitli | {"muhakeme_izi", "kanit_dogrula"},
                         DONGU_AILESI,
                         "yeni oturum tabanlı araç eklendiyse aile testine girer")


if __name__ == "__main__":
    unittest.main()
