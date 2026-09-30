# -*- coding: utf-8 -*-
"""
test_bilim.py — bilim katmanı v1 (ADR-002): hüküm kuralları, şablon
değişmezleri, sınamalar ve Rehberli akış. Test verisi elle kurulmuş,
deterministik ve sentetiktir.
"""
import calendar
import datetime
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sinama.arayuz import sunucu  # noqa: E402
from sinama.bilim import hukum, rak, sablon, sinamalar  # noqa: E402
from sinama.cekirdek.hatalar import KullanimHatasi  # noqa: E402
from sinama.kalite.kapi import KapiRed  # noqa: E402
from sinama.surec import dongu  # noqa: E402

YASAK = ("olasilik", "olasılık", "guven", "güven", "yuzde", "yüzde", "confidence",
         "probability", "posterior", "skor", "destek_orani")


def paket(**kw):
    """Varsayılanı 'her şey temiz' olan ARTIŞ kanıt paketi."""
    p = {"soru_turu": "ARTIS", "amac": "dogrulayici", "kilitli": True, "zincir_saglam": True,
         "birincil": {"durum": "tutuldu", "gerekce": "g"},
         "rakipler": [sinamalar._rakip(k, "dışlandı", "g") for k in rak.uygulanabilir("ARTIS")],
         "saglamlik": []}
    p.update(kw)
    return p


def rakip_durumu(p, kod, durum):
    for r in p["rakipler"]:
        if r["kod"] == kod:
            r["durum"] = durum
    return p


def anahtarlar(nesne):
    if isinstance(nesne, dict):
        for k, v in nesne.items():
            yield str(k).lower()
            yield from anahtarlar(v)
    elif isinstance(nesne, list):
        for v in nesne:
            yield from anahtarlar(v)


def degerler(nesne):
    if isinstance(nesne, dict):
        for v in nesne.values():
            yield from degerler(v)
    elif isinstance(nesne, list):
        for v in nesne:
            yield from degerler(v)
    else:
        yield nesne


class TestHukumKurallari(unittest.TestCase):
    def kat(self, p):
        return hukum.hukum_ver(p)["kategori"]

    def test_temiz_dogrulayici_destekler(self):
        h = hukum.hukum_ver(paket())
        self.assertEqual((h["kategori"], h["en_guclu_rakip"]), ("DESTEKLENDİ", None))
        self.assertEqual(h["kurallar"][-1]["kural"], "K5-destek")

    def test_sirali_kurallar(self):
        self.assertEqual(self.kat(paket(zincir_saglam=False)), "ÇEKİMSER")
        self.assertEqual(self.kat(paket(birincil={"durum": "sınanamadı", "gerekce": "kapı"})), "ÇEKİMSER")
        self.assertEqual(self.kat(paket(birincil={"durum": "karşıt"})), "ÇELİŞKİLİ")
        self.assertEqual(self.kat(paket(birincil={"durum": "belirsiz"})), "BELİRSİZ")
        # bozuk zincir, karşıt öngörüden önce gelir
        self.assertEqual(self.kat(paket(zincir_saglam=False, birincil={"durum": "karşıt"})), "ÇEKİMSER")

    def test_yuksek_etkili_rakip_desteklenirse_belirsiz(self):
        h = hukum.hukum_ver(rakip_durumu(paket(), "R-BILDIRIM", "destekleniyor"))
        self.assertEqual((h["kategori"], h["en_guclu_rakip"]), ("BELİRSİZ", "R-BILDIRIM"))

    def test_orta_etkili_rakip_desteklenirse_kirilgan(self):
        p = paket(soru_turu="SERI",
                  rakipler=[sinamalar._rakip(k, "dışlandı", "g") for k in rak.uygulanabilir("SERI")])
        h = hukum.hukum_ver(rakip_durumu(p, "R-TESADUF-YAKINLIK", "destekleniyor"))
        self.assertEqual(h["kategori"], "KIRILGAN")

    def test_cozulmemis_rakip_ya_da_saglamlik_kirilgan(self):
        h = hukum.hukum_ver(rakip_durumu(paket(), "R-MEVSIM", "çözülmedi"))
        self.assertEqual((h["kategori"], h["en_guclu_rakip"]), ("KIRILGAN", "R-MEVSIM"))
        self.assertEqual(h["sonraki_en_iyi_kanit"][0]["rakip"], "R-MEVSIM")
        self.assertEqual(self.kat(paket(saglamlik=["kısa seri"])), "KIRILGAN")

    def test_tavanlar(self):
        self.assertEqual(self.kat(paket(kilitli=False)), "KIRILGAN")
        for amac in ("kesifsel", "operasyonel"):
            h = hukum.hukum_ver(paket(amac=amac))
            self.assertEqual(h["kategori"], "KIRILGAN")
            self.assertIn("T1-amac", [k["kural"] for k in h["kurallar"]])
        s = paket(soru_turu="SERI",
                  rakipler=[sinamalar._rakip(k, "dışlandı", "g") for k in rak.uygulanabilir("SERI")])
        h = hukum.hukum_ver(s)
        self.assertEqual((h["kategori"], h["kisi_baglantisi"]), ("KIRILGAN", True))
        self.assertIn("T2-seri", [k["kural"] for k in h["kurallar"]])
        # tavan yalnız destekli hükmü düşürür
        self.assertEqual(self.kat(paket(amac="kesifsel", birincil={"durum": "karşıt"})), "ÇELİŞKİLİ")

    def test_en_guclu_rakip_sirasi(self):
        r = [sinamalar._rakip("R-VERI", "çözülmedi", "g"), sinamalar._rakip("R-MEVSIM", "destekleniyor", "g")]
        self.assertEqual(hukum.en_guclu_rakip(r), "R-MEVSIM")
        r = [sinamalar._rakip("R-TESADUF-YAKINLIK", "çözülmedi", "g"),
             sinamalar._rakip("R-VERI", "çözülmedi", "g")]
        self.assertEqual(hukum.en_guclu_rakip(r), "R-VERI")          # etki: yüksek önce
        # etki, katalog sırasından ÖNCE gelir (v1 kataloğunda ikisi hiç ayrışmıyor)
        r = [{"kod": "R-ORTAK-MO", "durum": "çözülmedi", "etki": "orta"},
             {"kod": "R-TESADUF-YAKINLIK", "durum": "çözülmedi", "etki": "yüksek"}]
        self.assertEqual(hukum.en_guclu_rakip(r), "R-TESADUF-YAKINLIK")
        r = [sinamalar._rakip("R-VERI", "çözülmedi", "g"), sinamalar._rakip("R-BILDIRIM", "çözülmedi", "g")]
        self.assertEqual(hukum.en_guclu_rakip(r), "R-BILDIRIM")      # katalog sırası
        r = [sinamalar._rakip("R-VERI", "uygulanamaz", "g"), sinamalar._rakip("R-BILDIRIM", "dışlandı", "g")]
        self.assertIsNone(hukum.en_guclu_rakip(r))

    def test_belirlenimci_olasiliksiz_taslak(self):
        p = rakip_durumu(paket(), "R-MEVSIM", "çözülmedi")
        a, b = hukum.hukum_ver(json.loads(json.dumps(p))), hukum.hukum_ver(p)
        self.assertEqual(a, b)
        self.assertNotEqual(a["paket_hash"], hukum.hukum_ver(paket())["paket_hash"])
        self.assertFalse([k for k in anahtarlar(a) for y in YASAK if y in k])
        self.assertFalse([v for v in degerler(a) if isinstance(v, float)])
        self.assertEqual((a["insan_onayi_gerekir"], a["durum"]), (True, "taslak"))
        self.assertIn("listelenen rakiplere göre", a["ifade"])


class TestSablon(unittest.TestCase):
    def test_her_turde_tek_birincil_ve_zorunlu_bilinmeyen(self):
        for tur in sablon.TURLER:
            hs = sablon.hipotez_seti(tur)
            turler = [h["tur"] for h in hs]
            self.assertEqual(turler.count("BIRINCIL"), 1, tur)
            self.assertEqual(turler[-1], "BILINMEYEN", tur)
            self.assertEqual(turler.count("BILINMEYEN"), 1, tur)
            self.assertEqual([h["kimlik"] for h in hs if h["tur"] == "RAKIP"],
                             rak.uygulanabilir(tur))

    def test_seri_birincil_kimlik_iddiasi_degil(self):
        self.assertIn("aynı fail iddiası değildir", sablon.SABLONLAR["SERI"]["birincil"])


def aylik(sayimlar_by_kanal, bas=(2024, 1)):
    """Deterministik kayıtlar: {kanal: [ay başına sayı]} → ay içine yayılmış günler."""
    satirlar = []
    for kanal, sayimlar in sayimlar_by_kanal.items():
        for ay, n in enumerate(sayimlar):
            y, m = bas[0] + (bas[1] - 1 + ay) // 12, (bas[1] - 1 + ay) % 12 + 1
            gun_sayisi = calendar.monthrange(y, m)[1]
            for i in range(n):
                g = datetime.date(y, m, 1 + (i * gun_sayisi) // n)
                satirlar.append({"tarih": g.isoformat(), "kanal": kanal})
    satirlar.sort(key=lambda s: (s["tarih"], s["kanal"]))
    for i, s in enumerate(satirlar):
        s["id"] = f"k{i}"
    return satirlar


class SahteYurut:
    """Araç adına göre hazır cevap; çağrıları kaydeder."""

    def __init__(self, **cevap):
        self.cevap, self.cagrilar = cevap, []

    def __call__(self, ad, arg, hipotez, amac):
        self.cagrilar.append((ad, hipotez, arg))
        c = self.cevap[ad]
        if isinstance(c, Exception):
            raise c
        return c(arg) if callable(c) else c


def durumlar(rakipler):
    return {r["kod"]: r["durum"] for r in rakipler}


class TestSinamalarArtis(unittest.TestCase):
    ARTEFAKT = aylik({"karakol": [30] * 24, "cevrimici": [0] * 12 + [15] * 12})

    def test_azalan_karsit_ve_rakipler_uygulanamaz(self):
        b, r, _ = sinamalar.artis({"satirlar": self.ARTEFAKT}, self.ARTEFAKT,
                                  SahteYurut(trend={"yorum": "azalan"}), "kanal")
        self.assertEqual(b["durum"], "karşıt")
        self.assertEqual(durumlar(r)["R-BILDIRIM"], "uygulanamaz")
        self.assertEqual(durumlar(r)["R-MEVSIM"], "uygulanamaz")

    def test_kapi_reddi_sinanamadi(self):
        b, _, _ = sinamalar.artis({"satirlar": []}, self.ARTEFAKT,
                                  SahteYurut(trend=KapiRed("kapı")), "kanal")
        self.assertEqual(b["durum"], "sınanamadı")

    def test_kanal_yoksa_bildirim_cozulmedi(self):
        _, r, _ = sinamalar.artis({}, self.ARTEFAKT, SahteYurut(
            trend={"yorum": "artan"}, t_testi={"p": 0.001, "ortalama": 15}), None)
        self.assertEqual(durumlar(r)["R-BILDIRIM"], "çözülmedi")

    def _bildirim(self, veri):
        """R-BILDIRIM kaydı + yerel adım kayıtları (birincil tutulmuş varsayılır)."""
        yurut = SahteYurut(trend={"yorum": "artan"}, t_testi={"p": 0.001, "ortalama": 15})
        adimlar = []
        _, r, _ = sinamalar.artis({}, veri, yurut, "kanal",
                                  lambda ad, ozet, h, a: adimlar.append((ad, h, ozet)))
        return next(x for x in r if x["kod"] == "R-BILDIRIM"), adimlar, yurut

    def test_saf_artefakt_ayristirma_destekler(self):
        r, adimlar, yurut = self._bildirim(self.ARTEFAKT)
        self.assertEqual(r["durum"], "destekleniyor")
        self.assertLess(r["olcum"]["z"], -1.645)
        self.assertAlmostEqual(r["olcum"]["surekli_artis_payi"], 0.0, delta=0.05)
        self.assertEqual([a[0] for a in adimlar], ["bildirim_ayristirma"])
        self.assertEqual([c[0] for c in yurut.cagrilar], ["trend", "t_testi"])  # ikinci trend yok

    def test_kismi_artefakt_anlamli_kucuk_artisa_ragmen_destekler(self):
        # v1'in kusuru: sürekli kanaldaki küçük GERÇEK artış anlamlıysa rakip dışlanıyordu
        r, _, _ = self._bildirim(aylik({"karakol": [30] * 12 + [33] * 12,
                                        "cevrimici": [0] * 12 + [15] * 12}))
        self.assertEqual(r["durum"], "destekleniyor")
        self.assertLess(r["olcum"]["surekli_artis_payi"], 0.3)

    def test_karma_cozulmedi_kucuk_kanal_dislanir(self):
        karma, _, _ = self._bildirim(aylik({"karakol": [30] * 12 + [45] * 12,
                                            "cevrimici": [0] * 12 + [15] * 12}))
        self.assertEqual(karma["durum"], "çözülmedi")
        self.assertAlmostEqual(karma["olcum"]["surekli_artis_payi"], 0.5, delta=0.05)
        # hafif negatif z (−1,645 < z < 0) de "çözülmedi"dir; yalnız anlamlı negatif destekler
        eksi, _, _ = self._bildirim(aylik({"karakol": [30] * 12 + [43] * 12,
                                           "cevrimici": [0] * 12 + [15] * 12}))
        self.assertTrue(-1.645 < eksi["olcum"]["z"] < 0, eksi["olcum"])
        self.assertEqual(eksi["durum"], "çözülmedi")
        kucuk, _, _ = self._bildirim(aylik({"karakol": [30] * 12 + [45] * 12,
                                            "cevrimici": [0] * 12 + [3] * 12}))
        self.assertEqual(kucuk["durum"], "dışlandı")
        self.assertGreater(kucuk["olcum"]["z"], 1.645)

    def test_tek_erken_kacak_kayit_ayrim_noktasini_bozmaz(self):
        veri = aylik({"karakol": [30] * 24, "cevrimici": [1] + [0] * 11 + [15] * 12})
        r, _, _ = self._bildirim(veri)
        self.assertEqual(r["durum"], "destekleniyor")
        self.assertTrue(r["olcum"]["ayrim_tarihi"].startswith("2025-01"), r["olcum"])

    def test_asiri_yayilim_z_yi_daraltir(self):
        # sürekli kanal aşırı yayılımlı: φ_s = havuz T/sd (öncesi 12 tam ay T = 160,
        # sonrası 10 tam ay T = 4000/45; sd 20); yeni kanal sabit → φ_y = 1
        dalgali = [10, 50] * 6
        veri = aylik({"karakol": dalgali + [x + 15 for x in dalgali], "cevrimici": [0] * 12 + [3] * 12})
        r, adimlar, _ = self._bildirim(veri)
        self.assertAlmostEqual(r["olcum"]["yayilim"], (160 + 4000 / 45) / 20, delta=0.01)
        self.assertEqual(r["olcum"]["yayilim_yeni"], 1.0)
        self.assertLess(r["olcum"]["yayilim_p"], 0.05)
        self.assertEqual(r["durum"], "çözülmedi")        # Poisson varsayımıyla dışlanırdı
        self.assertGreater(adimlar[0][2]["dispersiyon"], 5)

    def test_yayilim_bilesene_ozgu(self):
        # v1.3: yeni kanal çok yayılımlı, sürekli kanal Poisson benzeri → φ_s = 1 kalır
        # (v1.1 büyük φ'yi sürekli kanalın terimlerine de uyguluyordu — BMK v6 K12.6)
        veri = aylik({"karakol": [30] * 12 + [45] * 12, "cevrimici": [0] * 12 + [1, 25] * 6})
        r, adimlar, _ = self._bildirim(veri)
        self.assertEqual(r["olcum"]["yayilim"], 1.0)
        self.assertGreater(r["olcum"]["yayilim_yeni"], 5)
        self.assertLess(r["olcum"]["yayilim_p_yeni"], 0.05)
        self.assertEqual((adimlar[0][2]["dispersiyon"], adimlar[0][2]["dispersiyon_b"]),
                         (1.0, r["olcum"]["yayilim_yeni"]))

    def test_yayilim_sinamasi(self):
        import datetime as dt
        bas, bit = dt.datetime(2024, 1, 1), dt.datetime(2025, 1, 1)

        def veri(sayim):
            return [(dt.datetime(2024, a + 1, 1), "k") for a, n in enumerate(sayim) for _ in range(n)]
        phi, p, ki, sd = sinamalar._yayilim_sinamasi(
            veri([26, 34, 30, 28, 32, 30, 27, 33, 29, 31, 30, 30]), [({"k"}, bas, bit)])
        self.assertEqual((phi, sd), (1.0, 11))
        self.assertGreater(p, 0.05)
        # φ̂ > 1 ama test reddetmiyor (p ≈ 0,17): φ = 1 — gürültülü φ̂ kullanılmaz
        phi, p, ki, sd = sinamalar._yayilim_sinamasi(
            veri([22, 38, 30, 21, 39, 30, 23, 37, 30, 24, 36, 30]), [({"k"}, bas, bit)])
        self.assertGreater(ki / sd, 1.3)
        self.assertGreater(p, 0.05)
        self.assertEqual(phi, 1.0)
        phi, p, ki, sd = sinamalar._yayilim_sinamasi(veri([10, 50] * 6), [({"k"}, bas, bit)])
        self.assertLess(p, 0.05)
        self.assertAlmostEqual(ki, 12 * 400 / 30)
        self.assertAlmostEqual(phi, ki / sd)
        self.assertEqual(sinamalar._yayilim_sinamasi(veri([20] * 12), [({"k"}, bas, bit)])[:2], (1.0, 1.0))
        self.assertEqual(sinamalar._yayilim_sinamasi([], [({"k"}, bas, bit)])[:2], (1.0, None))

    def test_kanal_bileseni_degismediyse_ek_sinama_yok(self):
        veri = aylik({"karakol": [30] * 24, "cevrimici": [10] * 24})
        yurut = SahteYurut(trend={"yorum": "artan"}, t_testi={"p": 0.001, "ortalama": 5})
        _, r, _ = sinamalar.artis({}, veri, yurut, "kanal")
        self.assertEqual(durumlar(r)["R-BILDIRIM"], "dışlandı")
        self.assertEqual([c[0] for c in yurut.cagrilar], ["trend", "t_testi"])

    def test_mevsim_durumlari(self):
        kisa = aylik({"karakol": [30] * 12})
        _, r, _ = sinamalar.artis({}, kisa, SahteYurut(trend={"yorum": "artan"}), None)
        self.assertEqual(durumlar(r)["R-MEVSIM"], "çözülmedi")
        for tt, beklenen in (({"p": 0.01, "ortalama": -3}, "destekleniyor"),
                             ({"p": 0.30, "ortalama": 2}, "çözülmedi"),
                             ({"p": None, "ortalama": 0, "not": "varyans sıfır"}, "çözülmedi")):
            _, r, _ = sinamalar.artis({}, self.ARTEFAKT, SahteYurut(trend={"yorum": "artan"}, t_testi=tt), None)
            self.assertEqual(durumlar(r)["R-MEVSIM"], beklenen, tt)

    def test_gecersiz_tarih_veri_rakibini_cozmez(self):
        bozuk = [dict(s) for s in self.ARTEFAKT]
        for s in bozuk[::8]:
            s["tarih"] = "bilinmiyor"
        _, r, _ = sinamalar.artis({}, bozuk, SahteYurut(trend={"yorum": "artan"},
                                                        t_testi={"p": 0.001, "ortalama": 15}), None)
        self.assertEqual(durumlar(r)["R-VERI"], "çözülmedi")

    def test_tek_erken_kayit_kanali_surekli_yapmaz(self):
        veri = aylik({"karakol": [30] * 24, "cevrimici": [1] + [0] * 11 + [15] * 12})
        tarihli = sinamalar._tarihli(veri, "kanal")
        self.assertEqual(sinamalar._surekli_kanallar(tarihli), ["karakol"])


class TestOranDegisimiAyristirma(unittest.TestCase):
    def test_degerler_ve_sinirlar(self):
        from sinama.cekirdek import degerlendirme as dg
        r = dg.oran_degisimi_ayristirma(100, 100, 0, 100, 100, 100)
        self.assertEqual((r["degisim_a"], r["degisim_b"], r["pay_a"]), (0.0, 1.0, 0.0))
        self.assertAlmostEqual(r["z"], -1 / (300 / 100 ** 2) ** 0.5, places=3)
        r2 = dg.oran_degisimi_ayristirma(100, 100, 0, 100, 100, 100, dispersiyon=4)
        self.assertAlmostEqual(r2["z"], r["z"] / 2, places=2)
        # v1.3: bileşene özgü çarpan — B'ninki yalnız B'nin terimlerine
        r3 = dg.oran_degisimi_ayristirma(100, 100, 0, 100, 100, 100, dispersiyon=1, dispersiyon_b=4)
        self.assertAlmostEqual(r3["se"], (0.02 + 4 * 0.01) ** 0.5, places=4)
        self.assertEqual((r3["dispersiyon"], r3["dispersiyon_b"]), (1.0, 4.0))
        self.assertEqual(r2["dispersiyon_b"], 4.0)                 # None → A'nınki
        self.assertEqual(dg.oran_degisimi_ayristirma(1, 1, 0, 0, 10, 10, dispersiyon=0.2)["dispersiyon"], 1.0)
        self.assertIsNone(dg.oran_degisimi_ayristirma(0, 0, 0, 0, 10, 10)["z"])
        self.assertIsNone(dg.oran_degisimi_ayristirma(50, 40, 0, 5, 10, 10)["pay_a"])   # toplam düştü
        self.assertIsNone(dg.oran_degisimi_ayristirma(1, 1, 1, 1, 0, 10))


JITTER = [2, -1, -2, 1, 0, 1, -1, 2, -2, 0, 1, -1]


def bolgesel(aylik_sayim, bas=(2024, 1)):
    """{bölge: [ay başına sayı]} → ay içine yayılmış deterministik kayıtlar."""
    satirlar = []
    for bolge, sayimlar in aylik_sayim.items():
        for ay, n in enumerate(sayimlar):
            y_, m_ = bas[0] + (bas[1] - 1 + ay) // 12, (bas[1] - 1 + ay) % 12 + 1
            gun_sayisi = calendar.monthrange(y_, m_)[1]
            for i in range(n):
                satirlar.append({"tarih": datetime.date(y_, m_, 1 + (i * gun_sayisi) // n).isoformat(),
                                 "bolge": bolge})
    satirlar.sort(key=lambda s: (s["tarih"], s["bolge"]))
    for i, s in enumerate(satirlar):
        s["id"] = f"b{i}"
    return satirlar


def seviye(once, sonra):
    """24 ay: 12 ay 'once', 12 ay 'sonra' + deterministik dalgalanma."""
    return [once + j for j in JITTER] + [sonra + j for j in JITTER]


class TestOranOrani(unittest.TestCase):
    def test_degerler(self):
        from sinama.cekirdek import degerlendirme as dg
        r = dg.oran_orani_farki(480, 312, 480, 480)
        self.assertEqual((r["oran"], r["z"]), (0.65, -4.43))
        self.assertLess(r["ga_alt"], 0.65)
        self.assertGreater(r["ga_ust"], 0.65)
        r4 = dg.oran_orani_farki(480, 312, 480, 480, dispersiyon_a=4, dispersiyon_b=4)
        self.assertAlmostEqual(r4["z"], r["z"] / 2, delta=0.01)
        self.assertIsNone(dg.oran_orani_farki(0, 10, 10, 10))
        t = dg.oran_farki_log(270, 162, 270, 90)
        self.assertEqual((t["oran"], t["z"]), (1.8, 5.914))
        self.assertIsNone(dg.oran_farki_log(10, 10, 0, 10))


class TestEtki(unittest.TestCase):
    """ETKİ (A4.13) resmi yoldan, deterministik veride."""
    TAM = {"bolge_alan": "bolge", "mudahale": "M", "kontrol": "K", "tampon": "T",
           "kesinti_tarihi": "2025-01-01"}

    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="etki_")
        self.eski = os.environ.get("SINAMA_LOG_DIR")
        os.environ["SINAMA_LOG_DIR"] = self.gecici

    def tearDown(self):
        if self.eski is None:
            os.environ.pop("SINAMA_LOG_DIR", None)
        else:
            os.environ["SINAMA_LOG_DIR"] = self.eski

    def hukum(self, veri, **arg):
        a = {"soru_turu": "ETKI", "amac": "dogrulayici", "onaylayan": "test", **self.TAM, **arg}
        return sunucu.arac_calistir("rehberli_calisma", {"satirlar": veri, **a})["sonuc"]

    def test_gercek_etki_desteklenir_ve_adimlar_zincirde(self):
        s = self.hukum(bolgesel({"M": seviye(40, 26), "K": seviye(40, 40), "T": seviye(25, 25)}))
        h = s["hukum"]
        self.assertEqual((h["kategori"], h["birincil_ongoru"]), ("DESTEKLENDİ", "tutuldu"), h["kurallar"])
        self.assertEqual([x["arac"] for x in s["sinamalar"]],
                         ["etki_oran_orani", "ortalamaya_donus", "yer_degistirme"])

    def test_yer_degistirme_rakibi_destekler(self):
        h = self.hukum(bolgesel({"M": seviye(40, 26), "K": seviye(40, 40), "T": seviye(25, 39)}))["hukum"]
        self.assertEqual((h["kategori"], h["en_guclu_rakip"]), ("BELİRSİZ", "R-YER-DEGISTIRME"))
        r = next(x for x in h["rakipler"] if x["kod"] == "R-YER-DEGISTIRME")
        self.assertGreater(r["olcum"]["tampon_orani"], 1.3)

    ZIRVE = [40 + j for j in JITTER[:9]] + [90, 90, 90] + [40 + j for j in JITTER]

    def test_ortalamaya_donus_desteklenmez(self):
        # öncesi zirve bölgenin aylık yayılımını büyütür → φ büyür → birincil çoğu
        # zaman anlamlılığa ulaşmaz (yayılım kapısının koruyucu yan etkisi)
        h = self.hukum(bolgesel({"M": self.ZIRVE, "K": seviye(40, 40), "T": seviye(25, 25)}))["hukum"]
        self.assertIn(h["kategori"], ("BELİRSİZ", "KIRILGAN"))

    def test_ortalamaya_donus_rakip_mantigi(self):
        # birincil TUTULDUĞUNDA rakip mantığı: φ = 1 (Poisson varsayımı) ile yalıtılmış sınama
        veri = bolgesel({"M": self.ZIRVE, "K": seviye(40, 40), "T": seviye(25, 25)})
        eski = sinamalar._yayilim_sinamasi
        sinamalar._yayilim_sinamasi = lambda tarihli, parcalar: (1.0, 1.0, 0.0, 1)
        try:
            b, r, _ = sinamalar.etki({}, veri, None, None, "bolge", "M", "2025-01-01",
                                     kontrol="K", tampon="T")
        finally:
            sinamalar._yayilim_sinamasi = eski
        self.assertEqual(b["durum"], "tutuldu")
        durum = durumlar(r)
        self.assertEqual(durum["R-ORTALAMAYA-DONUS"], "destekleniyor")
        self.assertEqual(hukum.en_guclu_rakip(r), "R-ORTALAMAYA-DONUS")

    def test_genel_dusus_desteklenmez(self):
        h = self.hukum(bolgesel({"M": seviye(40, 26), "K": seviye(40, 26), "T": seviye(25, 16)}))["hukum"]
        self.assertEqual((h["kategori"], h["birincil_ongoru"]), ("BELİRSİZ", "belirsiz"))

    def test_kontrolsuz_tavan_kirilgan(self):
        veri = bolgesel({"M": seviye(40, 26), "K": seviye(40, 40)})
        h = self.hukum(veri, kontrol="", tampon="")["hukum"]
        self.assertEqual((h["kategori"], h["en_guclu_rakip"]), ("KIRILGAN", "R-ESZAMANLI"), h["kurallar"])
        durum = {r["kod"]: r["durum"] for r in h["rakipler"]}
        self.assertEqual(durum["R-YER-DEGISTIRME"], "çözülmedi")

    def test_kontrolsuz_kucuk_dusus_belirsiz(self):
        # ITS tahmini negatif ama GA 0'ı kapsıyor → belirsiz (yön tek başına yetmez)
        h = self.hukum(bolgesel({"M": seviye(40, 38)}), kontrol="", tampon="")["hukum"]
        self.assertEqual((h["kategori"], h["birincil_ongoru"]), ("BELİRSİZ", "belirsiz"), h["kurallar"])

    def test_kisa_donem_cekimser_ve_kullanim_hatalari(self):
        kisa = bolgesel({"M": [40, 40, 26, 26], "K": [40] * 4}, bas=(2024, 11))
        h = self.hukum(kisa)["hukum"]
        self.assertEqual((h["kategori"], h["birincil_ongoru"]), ("ÇEKİMSER", "sınanamadı"))
        with self.assertRaises(KullanimHatasi):
            sunucu.arac_calistir("rehberli_calisma", {"satirlar": kisa, "soru_turu": "ETKI",
                                                      "amac": "kesifsel", "bolge_alan": "bolge"})
        with self.assertRaises(KullanimHatasi):
            self.hukum(kisa, kesinti_tarihi="bilinmiyor")


class TestSinamalarDiger(unittest.TestCase):
    def test_yigilma_veri_rakibini_cozmez(self):
        noktalar = [{"lat": 41.0 + i * 0.001, "lon": 29.0} for i in range(40)]
        noktalar += [{"lat": 41.5, "lon": 29.5}] * 10
        _, r, _ = sinamalar.yogunlasma({}, noktalar, SahteYurut(sicak_nokta_gi={"sicak": 2}))
        self.assertEqual(durumlar(r)["R-VERI"], "çözülmedi")
        self.assertEqual(durumlar(r)["R-PAYDA"], "çözülmedi")

    def test_gi_hatasi_sinanamadi(self):
        b, r, _ = sinamalar.yogunlasma({}, [], SahteYurut(sicak_nokta_gi={"hata": "az hücre"}))
        self.assertEqual(b["durum"], "sınanamadı")
        self.assertEqual(durumlar(r)["R-PAYDA"], "uygulanamaz")

    def test_yalniz_zayif_aday_belirsiz(self):
        kayit = [{"mo": "a b"}] * 30
        b, r, _ = sinamalar.seri({}, kayit, SahteYurut(seri_eslestirme=[{"katman": "zayıf"}]), "mo")
        self.assertEqual(b["durum"], "belirsiz")
        self.assertEqual(durumlar(r)["R-ORTAK-MO"], "uygulanamaz")

    def test_bos_mo_veri_rakibini_cozmez(self):
        kayit = [{"mo": "a b"}] * 20 + [{"mo": ""}] * 10
        _, r, s = sinamalar.seri({}, kayit, SahteYurut(seri_eslestirme=[{"katman": "güçlü"}]), "mo")
        self.assertEqual(durumlar(r)["R-VERI"], "çözülmedi")
        self.assertEqual(s, [])


class TestRehberliUctan(unittest.TestCase):
    """Resmi yoldan (sunucu.arac_calistir) uçtan uca."""

    def setUp(self):
        self.gecici = tempfile.mkdtemp(prefix="bilim_")
        self.eski = os.environ.get("SINAMA_LOG_DIR")
        os.environ["SINAMA_LOG_DIR"] = self.gecici

    def tearDown(self):
        if self.eski is None:
            os.environ.pop("SINAMA_LOG_DIR", None)
        else:
            os.environ["SINAMA_LOG_DIR"] = self.eski

    def cagir(self, satirlar, **arg):
        return sunucu.arac_calistir("rehberli_calisma", {"satirlar": satirlar, **arg})

    def test_artefakt_belirsiz_bildirim_ve_kanit_zinciri(self):
        veri = aylik({"karakol": [30] * 24, "cevrimici": [0] * 12 + [15] * 12})
        p = self.cagir(veri, soru_turu="ARTIS", amac="dogrulayici", onaylayan="test",
                       kanal_alan="kanal")
        h = p["sonuc"]["hukum"]
        self.assertEqual((h["kategori"], h["en_guclu_rakip"], h["birincil_ongoru"]),
                         ("BELİRSİZ", "R-BILDIRIM", "tutuldu"))
        bildirim = next(r for r in h["rakipler"] if r["kod"] == "R-BILDIRIM")
        self.assertIn("surekli_artis_payi", bildirim["olcum"])
        self.assertEqual(h["sinama_surumu"], "sinama-v1.3")
        self.assertIn("yayilim_p", bildirim["olcum"])
        self.assertIn("yayilim_p_yeni", bildirim["olcum"])
        self.assertTrue(p["meta"]["insan_onayi_gerekir"])
        self.assertIn("taslak", " ".join(p["meta"]["uyarilar"]).lower())
        d = dongu.yukle(p["sonuc"]["oturum_id"], self.gecici)
        adimlar = [g["arac"] for g in d.manifesto["gecmis"]]
        self.assertLess(adimlar.index("protokol_kilitle"), adimlar.index("veri_bagla"))
        self.assertLess(adimlar.index("hipotez_seti"), adimlar.index("protokol_kilitle"))
        self.assertEqual(adimlar[-1], "hukum")
        self.assertIn("bildirim_ayristirma", adimlar)       # yerel sınama da zincirde
        b = d.manifesto["bilimsel"]
        self.assertEqual(hukum.hukum_ver(b["paket"]), b["hukum"])     # bağımsız yeniden hesap
        zincir = sunucu.arac_calistir("kanit_dogrula", {"oturum_id": p["sonuc"]["oturum_id"]})
        self.assertTrue(zincir["sonuc"]["saglam"])

    def test_gercek_artis_dogrulayici_destekler_kesifsel_tavan(self):
        veri = aylik({"karakol": [30] * 12 + [39] * 12, "cevrimici": [10] * 12 + [13] * 12})
        d = self.cagir(veri, soru_turu="ARTIS", amac="dogrulayici", onaylayan="test",
                       kanal_alan="kanal")["sonuc"]
        self.assertEqual(d["hukum"]["kategori"], "DESTEKLENDİ", d["hukum"]["kurallar"])
        self.assertIsNotNone(d["kilit_hash"])
        k = self.cagir(veri, soru_turu="ARTIS", amac="kesifsel", kanal_alan="kanal")["sonuc"]
        self.assertEqual(k["hukum"]["kategori"], "KIRILGAN")
        self.assertIsNone(k["kilit_hash"])

    def test_odakli_yogunlasma_kirilgan_payda_cozulmedi(self):
        import random
        r = random.Random(7)
        veri = [{"lat": 41.0 + r.random() * 0.027, "lon": 29.0 + r.random() * 0.036}
                for _ in range(140)]
        veri += [{"lat": 41.0135 + r.gauss(0, 0.0012), "lon": 29.018 + r.gauss(0, 0.0015)}
                 for _ in range(60)]
        for i, s in enumerate(veri):
            s.update({"id": f"n{i}", "tarih": "2025-06-01"})
        s = self.cagir(veri, soru_turu="YOGUNLASMA", amac="dogrulayici", onaylayan="test")["sonuc"]
        h = s["hukum"]
        self.assertEqual((h["kategori"], h["en_guclu_rakip"]), ("KIRILGAN", "R-PAYDA"),
                         h["kurallar"])
        self.assertEqual(h["sonraki_en_iyi_kanit"][0]["rakip"], "R-PAYDA")
        self.assertFalse(h["kisi_baglantisi"])

    def test_seri_tavan_ve_kisi_baglantisi(self):
        ayirt = "balkon kapisi levye ile zorlanmis yalniz altin alinmis"
        veri = [{"id": f"s{i}", "mo": ayirt + f" genel{i}", "lat": 41.0 + 0.001 * i,
                 "lon": 29.0, "tarih": f"2025-03-{10 + i:02d}"} for i in range(3)]
        veri += [{"id": f"d{i}", "mo": f"f{i} g{i} h{i}", "lat": 41.2 + 0.03 * i,
                  "lon": 29.2, "tarih": f"2025-0{1 + i % 9}-01"} for i in range(22)]
        s = self.cagir(veri, soru_turu="SERI", amac="dogrulayici", onaylayan="test",
                       mo_alan="mo")["sonuc"]
        h = s["hukum"]
        self.assertEqual((h["kategori"], h["birincil_ongoru"], h["kisi_baglantisi"]),
                         ("KIRILGAN", "tutuldu", True), h["kurallar"])
        self.assertIn("T2-seri", [k["kural"] for k in h["kurallar"]])
        self.assertEqual([x["arac"] for x in s["sinamalar"]], ["seri_eslestirme"])

    def test_koordinatsiz_yogunlasma_cekimser(self):
        veri = [{"tarih": "2025-01-01", "id": f"k{i}"} for i in range(40)]
        s = self.cagir(veri, soru_turu="YOGUNLASMA", amac="kesifsel")["sonuc"]
        self.assertEqual((s["hukum"]["kategori"], s["hukum"]["birincil_ongoru"]),
                         ("ÇEKİMSER", "sınanamadı"))
        self.assertEqual(s["sinamalar"], [])
        self.assertEqual(dongu.yukle(s["oturum_id"], self.gecici).manifesto["faz"], "VERI")

    def test_dongu_veri_arac_adini_kapi_adina_cevirir(self):
        # aynı sınıf (A4.9): araç adıyla çağrılan oturum kapısı mekânsal kuralı atlıyordu
        oid = sunucu.arac_calistir("dongu_baslat", {"karar": "k"})["sonuc"]["oturum_id"]
        veri = [{"tarih": "2025-01-01", "id": f"k{i}"} for i in range(40)]
        s = sunucu.arac_calistir("dongu_veri", {"oturum_id": oid, "satirlar": veri,
                                                "analiz": "sicak_nokta_gi"})["sonuc"]
        self.assertEqual(s["kapi_analizi"], "grid_hotspot")
        self.assertFalse(s["uygunluk"]["uygun"])

    def test_kullanim_hatalari(self):
        veri = aylik({"karakol": [5] * 3})
        with self.assertRaises(KullanimHatasi):
            self.cagir(veri, soru_turu="ARTIS", amac="dogrulayici")
        with self.assertRaises(KullanimHatasi):
            self.cagir(veri, soru_turu="SERI", amac="kesifsel")


if __name__ == "__main__":
    unittest.main()
