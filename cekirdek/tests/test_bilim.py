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

    def test_yeni_kanal_ve_duz_surekli_kanal_bildirimi_destekler(self):
        yurut = SahteYurut(
            trend=lambda arg: {"yorum": "artan"} if "satirlar" not in arg or len(arg["satirlar"]) > 720
            else {"yorum": "anlamlı trend yok"},
            t_testi={"p": 0.001, "ortalama": 15})
        _, r, _ = sinamalar.artis({}, self.ARTEFAKT, yurut, "kanal")
        self.assertEqual(durumlar(r)["R-BILDIRIM"], "destekleniyor")
        alt = [c for c in yurut.cagrilar if c[1] == "R-BILDIRIM"][0][2]["satirlar"]
        self.assertEqual({s["kanal"] for s in alt}, {"karakol"})

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
        self.assertTrue(p["meta"]["insan_onayi_gerekir"])
        self.assertIn("taslak", " ".join(p["meta"]["uyarilar"]).lower())
        d = dongu.yukle(p["sonuc"]["oturum_id"], self.gecici)
        adimlar = [g["arac"] for g in d.manifesto["gecmis"]]
        self.assertLess(adimlar.index("protokol_kilitle"), adimlar.index("veri_bagla"))
        self.assertLess(adimlar.index("hipotez_seti"), adimlar.index("protokol_kilitle"))
        self.assertEqual(adimlar[-1], "hukum")
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
