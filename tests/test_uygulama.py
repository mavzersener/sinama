# -*- coding: utf-8 -*-
"""
test_uygulama.py — A5 arka ucu (ADR-003): HTTP uçları MCP ile aynı boru hattından,
veri kökü depo dışında, kural tabanlı öneri, dosya yükleme güvenliği, insan onayı.
FastAPI kurulu değilse atlanır (çekirdek standart kitaplıkla çalışır).
"""
import datetime
import glob
import os
import random
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "cekirdek"))

try:
    from fastapi.testclient import TestClient
    from uygulama import sunucu as uyg
except ImportError:   # pragma: no cover — CI'nın paketsiz işleri
    uyg = None


def aylik_kayitlar(tohum=1, artis=1.3):
    """24 ay, iki kanal; 13. aydan itibaren karakol × artis (sentetik)."""
    r = random.Random(tohum)
    satirlar = []
    for ay in range(24):
        y, m = 2024 + ay // 12, ay % 12 + 1
        for kanal, lam in (("karakol", 40 * (artis if ay >= 12 else 1)), ("cevrimici", 10)):
            for _ in range(int(lam + r.gauss(0, lam ** 0.5))):
                satirlar.append({"tarih": datetime.date(y, m, 1 + r.randrange(28)).isoformat(),
                                 "kanal": kanal})
    for i, s in enumerate(satirlar):
        s["id"] = f"u{i}"
    return satirlar


@unittest.skipIf(uyg is None, "fastapi kurulu değil")
class TestArkaUc(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="uyg_")
        self.eski = {k: os.environ.get(k) for k in ("SINAMA_VERI_KOKU", "SINAMA_LOG_DIR")}
        self.c = TestClient(uyg.uygulama_olustur(veri_koku=self.kok, dil_modeli_url=None))

    def tearDown(self):
        for k, v in self.eski.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.kok, ignore_errors=True)

    def akis(self, arg, satirlar):
        oid = self.c.post("/api/calisma", json=arg).json()["oturum_id"]
        self.assertEqual(self.c.post(f"/api/calisma/{oid}/kanit", json={"satirlar": satirlar}).status_code, 200)
        return oid, self.c.post(f"/api/calisma/{oid}/hukum").json()

    def test_depo_ici_veri_koku_reddedilir(self):
        for yol in (KOK, os.path.join(KOK, "cekirdek", "oturumlar")):
            with self.assertRaises(ValueError):
                uyg.uygulama_olustur(veri_koku=yol, dil_modeli_url=None)
        self.assertEqual((uyg.VARSAYILAN_HOST, uyg.VARSAYILAN_PORT), ("127.0.0.1", 8810))

    def test_saglik_ve_oturum_veri_kokunde(self):
        s = self.c.get("/api/saglik").json()
        self.assertEqual((s["durum"], s["dil_modeli"], s["veri_koku"]),
                         ("hazir", False, os.path.realpath(self.kok)))
        oid, _ = self.akis({"soru_turu": "ARTIS", "amac": "kesifsel", "kanal_alan": "kanal"},
                           aylik_kayitlar())
        self.assertTrue(os.path.isfile(os.path.join(self.kok, "oturumlar", f"{oid}.json")))

    def test_bozuk_dil_modeli_adresi_akisi_dusurmez(self):
        c = TestClient(uyg.uygulama_olustur(veri_koku=self.kok, dil_modeli_url="http://127.0.0.1:9 (yok)"))
        self.assertIs(c.get("/api/saglik").json()["dil_modeli"], False)
        self.assertEqual(c.post("/api/oneri", json={"soru": "arttı mı"}).json()["kaynak"], "kural")

    def test_onceki_log_dizini_ezilir(self):
        # ortamda başka bir SINAMA_LOG_DIR olsa da oturumlar veri kökünün altına yazılır
        os.environ["SINAMA_LOG_DIR"] = tempfile.mkdtemp(prefix="eski_log_")
        c = TestClient(uyg.uygulama_olustur(veri_koku=self.kok, dil_modeli_url=None))
        oid = c.post("/api/calisma", json={"soru_turu": "ARTIS", "amac": "kesifsel"}).json()["oturum_id"]
        self.assertEqual(glob.glob(os.path.join(self.kok, "oturumlar", f"{oid}.json")),
                         [os.path.join(self.kok, "oturumlar", f"{oid}.json")])

    def test_mcp_ile_ayni_hukum(self):
        from sinama.arayuz import sunucu as mcp
        satirlar = aylik_kayitlar(3)
        arg = {"soru_turu": "ARTIS", "amac": "dogrulayici", "onaylayan": "test", "kanal_alan": "kanal"}
        _, h = self.akis(arg, satirlar)
        ref = mcp.arac_calistir("rehberli_calisma", {"satirlar": satirlar, **arg})["sonuc"]["hukum"]
        for alan in ("kategori", "en_guclu_rakip", "rakipler", "kurallar", "paket_hash"):
            self.assertEqual(h["hukum"][alan], ref[alan], alan)
        self.assertTrue(h["uyarilar"])

    def test_plan_hipotez_ve_insan_onayi(self):
        r = self.c.post("/api/calisma", json={"soru_turu": "ARTIS", "amac": "kesifsel"}).json()
        oid = r["oturum_id"]
        self.assertEqual(r["hipotezler"][-1]["kimlik"], "H_bilinmeyen")
        self.assertEqual(r["plan"]["ulasilabilir_en_ust"], "KIRILGAN")
        e = self.c.post(f"/api/calisma/{oid}/hipotez", json={"ifade": "devriye değişti"}).json()
        self.assertEqual(e["eklenen"]["kimlik"], "R-SERBEST-1")
        self.assertIn("R-SERBEST-1", [x["kod"] for x in self.c.get(f"/api/calisma/{oid}/plan").json()["rakipler"]])
        self.c.post(f"/api/calisma/{oid}/kanit", json={"satirlar": aylik_kayitlar()})
        self.c.post(f"/api/calisma/{oid}/hukum")
        yok = self.c.post(f"/api/calisma/{oid}/sonuc", json={"sonuc_turu": "izlemeye_alindi"})
        self.assertEqual(yok.status_code, 400)
        self.assertEqual(yok.json()["hata"]["tur"], "kullanim")
        var = self.c.post(f"/api/calisma/{oid}/sonuc", json={"sonuc_turu": "izlemeye_alindi",
                                                            "onaylayan": "analist"})
        self.assertEqual((var.status_code, var.json()["faz"]), (200, "SONUC"))
        self.assertEqual(self.c.get(f"/api/calisma/{oid}").json()["faz"], "SONUC")

    def test_kullanim_hatalari_tipli(self):
        r = self.c.post("/api/calisma", json={"soru_turu": "BILINMEYEN", "amac": "kesifsel"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("hata", r.json())
        r = self.c.post("/api/calisma", json={"soru_turu": "ARTIS", "amac": "dogrulayici"})
        self.assertEqual((r.status_code, r.json()["hata"]["tur"]), (400, "kullanim"))
        self.assertEqual(self.c.get("/api/calisma/yok123/plan").status_code, 400)
        self.assertEqual(self.c.post("/api/calisma/x/sade").status_code, 400)

    def test_kural_onerisi(self):
        beklenen = {"Son 12 ayda hırsızlık arttı mı?": "ARTIS",
                    "Devriye artırımı bölgedeki suçları azalttı mı?": "ETKI",
                    "Olaylar belirli yerlerde yoğunlaşıyor mu?": "YOGUNLASMA",
                    "Bu hırsızlıklar aynı seriden mi?": "SERI",
                    "İSTANBUL'DA SICAK NOKTA VAR MI?": "YOGUNLASMA",
                    "Merhaba": None}
        for soru, tur in beklenen.items():
            self.assertEqual(self.c.post("/api/oneri", json={"soru": soru}).json(),
                             {"soru_turu": tur, "kaynak": "kural"}, soru)

    def test_veri_yukleme_ve_dosyayla_kanit(self):
        csv = "tarih,kanal\n" + "".join(f"{s['tarih']},{s['kanal']}\n" for s in aylik_kayitlar())
        r = self.c.post("/api/veri?ad=olaylar.csv", content=csv.encode("utf-8"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.post("/api/veri?ad=olaylar.csv", content=b"x").status_code, 409)
        for kotu in ("../kacis.csv", "alt/kacis.csv", ".gizli.csv", "veri.exe"):
            self.assertEqual(self.c.post(f"/api/veri?ad={kotu}", content=b"x").status_code, 400, kotu)
        self.assertEqual([d["ad"] for d in self.c.get("/api/veri").json()["dosyalar"]], ["olaylar.csv"])
        o = self.c.get("/api/veri/olaylar.csv/onizleme").json()
        self.assertEqual((o["sutunlar"], len(o["ilk"])), (["tarih", "kanal"], 5))
        self.assertEqual(o["degerler"]["kanal"], ["cevrimici", "karakol"])
        self.assertIsNone(o["degerler"]["tarih"])          # 30'dan çok farklı değer
        oid = self.c.post("/api/calisma", json={"soru_turu": "ARTIS", "amac": "kesifsel",
                                                "kanal_alan": "kanal"}).json()["oturum_id"]
        self.assertEqual(self.c.post(f"/api/calisma/{oid}/kanit", json={"dosya": "olaylar.csv"}).status_code, 200)
        self.assertIn(self.c.post(f"/api/calisma/{oid}/hukum").json()["hukum"]["kategori"],
                      ("KIRILGAN", "BELİRSİZ", "ÇELİŞKİLİ"))
        self.assertEqual(self.c.get("/api/veri/yok.csv/onizleme").status_code, 400)

    def test_kapi_reddi_422(self):
        oid = self.c.post("/api/calisma", json={"soru_turu": "YOGUNLASMA", "amac": "kesifsel"}).json()["oturum_id"]
        r = self.c.post(f"/api/calisma/{oid}/kanit", json={"satirlar": [{"tarih": "2025-01-01"}] * 5})
        self.assertEqual(r.status_code, 200)   # kapı reddi Rehberli akışta hükme işlenir (ÇEKİMSER)
        r = self.c.get("/api/calisma/yok/plan")
        self.assertEqual((r.status_code, r.json()["hata"]["tur"]), (400, "dongu"))
        from sinama.kalite.kapi import KapiRed
        self.assertEqual(uyg._hata_yaniti(KapiRed("ret")).status_code, 422)
        from sinama.cekirdek.hatalar import SucAnaliziHatasi
        self.assertEqual(uyg._hata_yaniti(SucAnaliziHatasi("iç")).status_code, 500)

    def test_dil_modeli_yokken_sade_503(self):
        oid, _ = self.akis({"soru_turu": "ARTIS", "amac": "kesifsel"}, aylik_kayitlar())
        self.assertEqual(self.c.post(f"/api/calisma/{oid}/sade", json={"dil": "en"}).status_code, 503)
        oid2 = self.c.post("/api/calisma", json={"soru_turu": "ARTIS", "amac": "kesifsel"}).json()["oturum_id"]
        self.assertEqual(self.c.post(f"/api/calisma/{oid2}/sade").status_code, 409)

    def test_on_yuz_yoksa_bilgi(self):
        if os.path.isfile(os.path.join(uyg.WEB_DIST, "index.html")):
            self.assertEqual(self.c.get("/").status_code, 200)
        else:
            self.assertIn("npm run build", self.c.get("/").json()["not"])


if __name__ == "__main__":
    unittest.main()
