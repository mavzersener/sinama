# -*- coding: utf-8 -*-
"""
test_atolye_kanit.py — A6 eşdeğerlik E2 + E4: kanıt defteri ve /api/evidence uçları.

DataFlow'un kanit-defteri (13) ve kanit-rota (6) testlerinin Python karşılıkları
(`# DataFlow:` işaretli) ve E4 biçim uyumu: DataFlow'un kendi koduyla üretilmiş defter
Sınama'nın Python defteriyle, Sınama'nın yazdığı defter DataFlow'un bağımsız
doğrulayıcısıyla (`kanit_dogrula.py`) doğrulanır. `cryptography` (ve uçlar için FastAPI)
kurulu değilse atlanır.
"""
import base64
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "cekirdek"))

try:
    from uygulama import kanit_defteri as kd
except ImportError:   # pragma: no cover — paketsiz CI işi
    kd = None
try:
    from fastapi.testclient import TestClient
    from uygulama import sunucu as uyg
except ImportError:   # pragma: no cover
    uyg = None

SENTETIK = os.path.join(KOK, "uygulama", "atolye_esdegerlik", "sentetik", "dataflow_defteri")
DOGRULAYICI = os.path.join(KOK, "uygulama", "atolye", "scripts", "kanit_dogrula.py")


def istek(i):
    """DataFlow testindeki `istek(i)`."""
    return {"kanit_id": f"kanit-{i:04d}", "dosya_no": "2026/1234", "veri_sha256": "a" * 64,
            "paket_sha256": "b" * 64, "satir": 10 + i, "sutun": 3, "beyan_eden": "PN-1",
            "kaynak_zinciri": [{"tip": "csv_source", "etiket": "src"}]}


AKTOR = {"id": 7, "ad": "Test Memur"}


@unittest.skipIf(kd is None, "cryptography kurulu değil")
class TestKanonikJson(unittest.TestCase):
    def test_anahtar_sirasi(self):
        # DataFlow: tests/kanit-defteri.test.ts › kanonikJson (RFC 8785) › anahtarlar UTF-16 kod birimi sırasıyla, iç içe, boşluksuz
        self.assertEqual(kd.kanonik({"b": 1, "a": {"d": [3, {"z": 1, "y": 2}], "c": None}}),
                         '{"a":{"c":null,"d":[3,{"y":2,"z":1}]},"b":1}')
        self.assertEqual(kd.kanonik({"ı": 1, "i": 2, "I": 3, "Z": 4}), '{"I":3,"Z":4,"i":2,"ı":1}')

    def test_sayi_bicimi(self):
        # DataFlow: tests/kanit-defteri.test.ts › kanonikJson (RFC 8785) › sayılar ECMAScript biçiminde (Python json.dumps 1.0 yazar; burada 1)
        self.assertEqual(kd.kanonik([1.0, -0.0, 0.1 + 0.2, 1e21, 1e-7, 123456789012345680000, 5e-324]),
                         "[1,0,0.30000000000000004,1e+21,1e-7,123456789012345680000,5e-324]")

    def test_sonlu_olmayan_ve_desteklenmeyen(self):
        # DataFlow: tests/kanit-defteri.test.ts › kanonikJson (RFC 8785) › sonlu olmayan sayı ve desteklenmeyen tip hata atar (sessiz düşürme yok)
        with self.assertRaisesRegex(ValueError, "sonlu olmayan"):
            kd.kanonik({"a": math.nan})
        with self.assertRaisesRegex(ValueError, "sonlu olmayan"):
            kd.kanonik([math.inf])
        with self.assertRaisesRegex(TypeError, "desteklenmeyen"):
            kd.kanonik({"f": lambda: 1})

    def test_zaman_bicimi(self):
        # DataFlow: tests/kanit-defteri.test.ts › kanonikJson (RFC 8785) › undefined alan atlanır; Date ISO metne döner (indirilen JSON ile aynı)
        # Python'da "undefined" yok; karşılığı: defter tarihi JS Date.toISOString biçiminde METİN
        # yazar (kanonik metin JSON gidiş-dönüşüyle aynı) ve tarih NESNESİ sessizce yazılmaz.
        import datetime
        with tempfile.TemporaryDirectory() as d:
            m = kd.KanitDefteri(d).ekle(istek(1), AKTOR)
        self.assertRegex(m["kayit"]["sunucu_zamani"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
        self.assertEqual(kd.kanonik(m), kd.kanonik(json.loads(json.dumps(m))))
        with self.assertRaisesRegex(TypeError, "desteklenmeyen"):
            kd.kanonik({"t": datetime.datetime(2026, 1, 2)})

    def test_metin_kacisi(self):
        # DataFlow: tests/kanit-defteri.test.ts › kanonikJson (RFC 8785) › metin kaçışı JSON.stringify ile aynı; Türkçe karakter kaçırılmaz
        self.assertEqual(kd.kanonik('şİ"\\\n\u0001'), '"şİ\\"\\\\\\n\\u0001"')

    def test_hash_deterministik(self):
        # DataFlow: tests/kanit-defteri.test.ts › kanonikJson (RFC 8785) › hash deterministik ve anahtar sırasından bağımsız
        self.assertEqual(kd.sha256_hex(kd.kanonik({"a": 1, "b": 2})), kd.sha256_hex(kd.kanonik({"b": 2, "a": 1})))
        self.assertRegex(kd.sha256_hex(kd.kanonik({"a": 1})), r"^[0-9a-f]{64}$")


@unittest.skipIf(kd is None, "cryptography kurulu değil")
class TestKanitDefteri(unittest.TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp(prefix="kanit_defteri_")
        self.yol = os.path.join(self.dizin, "defter.jsonl")

    def tearDown(self):
        shutil.rmtree(self.dizin, ignore_errors=True)

    def satirlar(self):
        with open(self.yol, encoding="utf-8", newline="") as f:
            return f.read().split("\n")

    def yaz(self, satirlar):
        with open(self.yol, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(satirlar))

    def test_zincir(self):
        # DataFlow: tests/kanit-defteri.test.ts › KanitDefteri — hash zinciri + Ed25519 › zincir kurar ve doğrular; ilk kayıt 64 sıfıra bağlanır
        d = kd.KanitDefteri(self.dizin)
        m1, m2 = d.ekle(istek(1), AKTOR), d.ekle(istek(2), AKTOR)
        self.assertEqual(m1["kayit"]["sira"], 1)
        self.assertEqual(m1["kayit"]["onceki_hash"], kd.BASLANGIC_HASH)
        self.assertEqual(m2["kayit"]["onceki_hash"], m1["kayit"]["kayit_hash"])
        self.assertEqual(m2["kayit"]["aktor"], AKTOR)
        s = d.dogrula()
        self.assertEqual((s["gecerli"], s["kayit_sayisi"], s["son_hash"]), (True, 2, m2["kayit"]["kayit_hash"]))

    def test_kalici_anahtar(self):
        # DataFlow: tests/kanit-defteri.test.ts › KanitDefteri — hash zinciri + Ed25519 › anahtar kalıcı: yeni örnek aynı parmak izini ve zinciri görür
        m1 = kd.KanitDefteri(self.dizin).ekle(istek(1), AKTOR)
        d2 = kd.KanitDefteri(self.dizin)
        m2 = d2.ekle(istek(2), AKTOR)
        self.assertEqual(m2["anahtar_parmak_izi"], m1["anahtar_parmak_izi"])
        self.assertTrue(d2.dogrula()["gecerli"])

    def test_eszamanli(self):
        # DataFlow: tests/kanit-defteri.test.ts › KanitDefteri — hash zinciri + Ed25519 › eşzamanlı eklemeler sıraya girer (yarış yok)
        d = kd.KanitDefteri(self.dizin)
        makbuzlar = []
        iplikler = [threading.Thread(target=lambda i=i: makbuzlar.append(d.ekle(istek(i), AKTOR))) for i in range(20)]
        for t in iplikler:
            t.start()
        for t in iplikler:
            t.join()
        self.assertEqual(sorted(m["kayit"]["sira"] for m in makbuzlar), list(range(1, 21)))
        self.assertTrue(d.dogrula()["gecerli"])

    def test_icerik_degisikligi(self):
        # DataFlow: tests/kanit-defteri.test.ts › KanitDefteri — hash zinciri + Ed25519 › kayıt içeriği değiştirilirse tespit edilir
        d = kd.KanitDefteri(self.dizin)
        for i in range(1, 4):
            d.ekle(istek(i), AKTOR)
        s = self.satirlar()
        s[1] = s[1].replace('"satir":12', '"satir":999')
        self.yaz(s)
        sonuc = kd.KanitDefteri(self.dizin).dogrula()
        self.assertFalse(sonuc["gecerli"])
        self.assertIn("değiştirilmiş", " ".join(h["neden"] for h in sonuc["hatalar"]))

    def test_ortadan_silme(self):
        # DataFlow: tests/kanit-defteri.test.ts › KanitDefteri — hash zinciri + Ed25519 › ortadan kayıt silinirse zincir kopukluğu tespit edilir
        d = kd.KanitDefteri(self.dizin)
        for i in range(1, 4):
            d.ekle(istek(i), AKTOR)
        s = self.satirlar()
        del s[1]
        self.yaz(s)
        sonuc = kd.KanitDefteri(self.dizin).dogrula()
        self.assertFalse(sonuc["gecerli"])
        self.assertRegex(" ".join(h["neden"] for h in sonuc["hatalar"]), "zinciri kopuk|sıra")

    def test_imza_sahteciligi(self):
        # DataFlow: tests/kanit-defteri.test.ts › KanitDefteri — hash zinciri + Ed25519 › hash yeniden hesaplansa bile imza sahteciliği tespit edilir
        kd.KanitDefteri(self.dizin).ekle(istek(1), AKTOR)
        m = json.loads(self.satirlar()[0])
        m["kayit"]["satir"] = 999
        m["kayit"]["kayit_hash"] = kd.sha256_hex(kd.kayit_hash_girdisi(m["kayit"]))   # saldırgan hash'i düzeltir…
        self.yaz([kd.kanonik(m), ""])
        sonuc = kd.KanitDefteri(self.dizin).dogrula()
        self.assertFalse(sonuc["gecerli"])
        self.assertIn("imza geçersiz", [h["neden"] for h in sonuc["hatalar"]])   # …ama imzalayamaz

    def test_bozuk_deftere_ekleme_yok(self):
        # DataFlow: tests/kanit-defteri.test.ts › KanitDefteri — hash zinciri + Ed25519 › son kaydı bozulmuş deftere sessizce ekleme yapılmaz
        kd.KanitDefteri(self.dizin).ekle(istek(1), AKTOR)
        self.yaz([s.replace('"satir":11', '"satir":12') for s in self.satirlar()])
        with self.assertRaisesRegex(ValueError, "değiştirilmiş"):
            kd.KanitDefteri(self.dizin).ekle(istek(2), AKTOR)
        self.assertEqual(len([s for s in self.satirlar() if s.strip()]), 1)


@unittest.skipIf(kd is None, "cryptography kurulu değil")
class TestBicimUyumuE4(unittest.TestCase):
    """E4: kanıt defteri biçimi iki yönde de uyumlu."""

    def test_dataflow_defteri_sinamada_gecerli(self):
        with open(os.path.join(SENTETIK, "genel_anahtar.json"), encoding="utf-8") as f:
            genel = kd.genel_anahtar_yukle(json.load(f)["pem"])
        with open(os.path.join(SENTETIK, "defter.jsonl"), encoding="utf-8") as f:
            satirlar = [s for s in f.read().splitlines() if s.strip()]
        sonuc = kd.satirlari_dogrula(satirlar, genel)
        self.assertEqual((sonuc["gecerli"], sonuc["kayit_sayisi"], sonuc["hatalar"]), (True, 3, []))
        # Mutasyon: tek alan değişince aynı Python doğrulayıcısı yakalar.
        bozuk = list(satirlar)
        bozuk[1] = bozuk[1].replace('"sutun":', '"sutun":1', 1)
        self.assertFalse(kd.satirlari_dogrula(bozuk, genel)["gecerli"])

    def test_sinama_defteri_dataflow_dogrulayicisinda_gecerli(self):
        with tempfile.TemporaryDirectory() as d:
            defter = kd.KanitDefteri(d)
            veri = {"columns": ["olay_id", "il", "oran"],
                    "rows": [{"olay_id": "E1", "il": "İstanbul", "oran": 0.1},
                             {"olay_id": "E2", "il": "Iğdır", "oran": 1e21}]}
            paket = {"sema": kd.kanit_dogrula.KANIT_SEMASI, "kanit_id": "0f8e7d6c-aaaa-bbbb",
                     "dosya_no": "2026/5", "beyan_eden": "PN-9", "veri": veri,
                     "veri_sha256": kd.sha256_hex(kd.kanonik(veri)), "uyarilar": []}
            paket_sha = kd.sha256_hex(kd.kanonik(paket))
            makbuz = defter.ekle({"kanit_id": paket["kanit_id"], "dosya_no": "2026/5",
                                  "veri_sha256": paket["veri_sha256"], "paket_sha256": paket_sha,
                                  "satir": 2, "sutun": 3, "beyan_eden": "PN-9", "kaynak_zinciri": []}, AKTOR)
            yol = os.path.join(d, "paket.json")
            with open(yol, "w", encoding="utf-8") as f:
                json.dump({"paket": paket, "paket_sha256": paket_sha, "makbuz": makbuz}, f, ensure_ascii=False, indent=2)
            r = subprocess.run([sys.executable, DOGRULAYICI, yol, "--genel-anahtar", defter.genel_yolu,
                                "--defter", defter.defter_yolu], capture_output=True, text=True,
                               encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("SONUÇ: GEÇERLİ", r.stdout)
            # Satır sonu: Windows'ta bile LF (DataFlow defteriyle bayt düzeyinde aynı biçim).
            with open(defter.defter_yolu, "rb") as f:
                self.assertNotIn(b"\r\n", f.read())


GECERLI = {"kanit_id": "0f8e7d6c-aaaa-bbbb", "dosya_no": "2026/5", "veri_sha256": "c" * 64,
           "paket_sha256": "d" * 64, "satir": 12, "sutun": 4, "beyan_eden": "PN-9",
           "kaynak_zinciri": [{"tip": "csv_source", "etiket": "src"}]}


@unittest.skipIf(kd is None or uyg is None, "cryptography ya da fastapi kurulu değil")
class TestKanitUclari(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="kanit_rota_")
        self.eski = {k: os.environ.get(k) for k in ("SINAMA_VERI_KOKU", "SINAMA_LOG_DIR")}
        self.app = uyg.uygulama_olustur(veri_koku=self.kok, dil_modeli_url=None)
        self.c = TestClient(self.app, client=("127.0.0.1", 50000))
        self.depo = self.app.state.atolye["depo"]

    def tearDown(self):
        self.depo.kapat()
        for k, v in self.eski.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        shutil.rmtree(self.kok, ignore_errors=True)

    def kayit_sayisi(self):
        return self.app.state.atolye["kanit"]["defter"].dogrula()["kayit_sayisi"]

    def test_gecerli_istek(self):
        # DataFlow: tests/kanit-rota.test.ts › /api/evidence › geçerli istek → imzalı makbuz; aktör OTURUMDAN (istemci beyanından değil)
        r = self.c.post("/api/evidence/record", json=GECERLI)
        self.assertEqual(r.status_code, 200)
        k = r.json()["kayit"]
        self.assertEqual((k["sira"], k["aktor"], k["beyan_eden"], k["veri_sha256"]),
                         (1, {"id": 1, "ad": "Yerel analist"}, "PN-9", GECERLI["veri_sha256"]))
        self.assertRegex(r.json()["imza"], r"^[A-Za-z0-9+/=]+$")
        self.assertEqual(self.depo.denetim_sayisi(action="evidence_record"), 1)

    def test_istemci_aktor_sira(self):
        # DataFlow: tests/kanit-rota.test.ts › /api/evidence › istemci aktör/sıra gönderse de sunucu kendi değerini yazar
        self.c.post("/api/evidence/record", json=GECERLI)
        m = self.c.post("/api/evidence/record", json={**GECERLI, "aktor": {"id": 999, "ad": "sahte"}, "sira": 1,
                                                      "onceki_hash": "0" * 64}).json()
        self.assertEqual(m["kayit"]["aktor"], {"id": 1, "ad": "Yerel analist"})
        self.assertEqual(m["kayit"]["sira"], 2)

    def test_yerel_olmayan_istemci(self):
        # DataFlow: tests/kanit-rota.test.ts › /api/evidence › oturumsuz → 401, deftere yazılmaz
        # Sınama'da oturum yok (ADR-004 md. 3); aktör hep yerel kullanıcıdır. Karşılık: geri
        # döngü dışından gelen istek reddedilir (403) ve deftere hiçbir şey yazılmaz.
        once = self.kayit_sayisi()
        uzak = TestClient(self.app, client=("10.1.2.3", 50000))
        self.assertEqual(uzak.post("/api/evidence/record", json=GECERLI).status_code, 403)
        self.assertEqual(self.kayit_sayisi(), once)

    def test_gecersiz_govde(self):
        # DataFlow: tests/kanit-rota.test.ts › /api/evidence › geçersiz gövde → 400 (hash biçimi, boş dosya no, bozuk JSON)
        self.assertEqual(self.c.post("/api/evidence/record", json={**GECERLI, "veri_sha256": "ABC"}).status_code, 400)
        self.assertEqual(self.c.post("/api/evidence/record", json={**GECERLI, "dosya_no": "   "}).status_code, 400)
        r = self.c.post("/api/evidence/record", content=b"{bozuk", headers={"content-type": "application/json"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.kayit_sayisi(), 0)

    def test_defter_yazilamazsa(self):
        # DataFlow: tests/kanit-rota.test.ts › /api/evidence › defter yazılamazsa 500 ve makbuz YOK (audit ikincil, kayıt sayılmaz)
        durum = self.app.state.atolye["kanit"]
        asil = durum["defter"]

        class Bozuk:
            def ekle(self, *a):
                raise OSError("disk dolu")
        durum["defter"] = Bozuk()
        try:
            r = self.c.post("/api/evidence/record", json=GECERLI)
        finally:
            durum["defter"] = asil
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("kayit", r.json())
        self.assertEqual(self.depo.denetim_sayisi(action="evidence_record"), 0)

    def test_genel_anahtar_ve_dogrulama(self):
        # DataFlow: tests/kanit-rota.test.ts › /api/evidence › genel anahtar açık; doğrulama uç noktası oturum ister
        k = self.c.get("/api/evidence/public-key").json()
        self.assertEqual(k["algoritma"], "Ed25519")
        self.assertIn("BEGIN PUBLIC KEY", k["pem"])
        uzak = TestClient(self.app, client=("10.1.2.3", 50000))
        self.assertEqual(uzak.get("/api/evidence/verify").status_code, 403)
        self.assertTrue(self.c.get("/api/evidence/verify").json()["gecerli"])
        # Anahtar biçimi: imza genel anahtarla doğrulanır (dışarıdan, sunucunun sırrı olmadan).
        self.c.post("/api/evidence/record", json=GECERLI)
        with open(os.path.join(self.kok, "kanit", "defter.jsonl"), encoding="utf-8") as f:
            m = json.loads(f.readline())
        kd.genel_anahtar_yukle(k["pem"]).verify(base64.b64decode(m["imza"]), m["kayit"]["kayit_hash"].encode())


if __name__ == "__main__":
    unittest.main()
