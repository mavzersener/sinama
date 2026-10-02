# -*- coding: utf-8 -*-
"""
test_atolye_sunucu.py — A6 Atölye arka ucu (ADR-004): tRPC karşılığı prosedürler (DataFlow
router davranışı: sahiplik, sürüm artışı, denetim izi, zod sınırları, katalog, geri
bildirim), veri seti HTTP uçları, suç analizi köprüsü (çekirdekle aynı boru hattı), kapsam
dışı uçların tipli 503'ü, yalnız-yerel kapısı, /atolye statik sunumu ve tek süreç (E5).
FastAPI kurulu değilse atlanır.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "cekirdek"))

try:
    from fastapi.testclient import TestClient
    from uygulama import atolye_sunucu, sunucu as uyg
except ImportError:   # pragma: no cover
    uyg = None


@unittest.skipIf(uyg is None, "fastapi kurulu değil")
class AtolyeTesti(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="atolye_")
        self.eski = {k: os.environ.get(k) for k in ("SINAMA_VERI_KOKU", "SINAMA_LOG_DIR")}
        self.app = uyg.uygulama_olustur(veri_koku=self.kok, dil_modeli_url=None)
        self.c = TestClient(self.app, client=("127.0.0.1", 50000))
        self.depo = self.app.state.atolye["depo"]

    def tearDown(self):
        self.depo.kapat()
        for k, v in self.eski.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        shutil.rmtree(self.kok, ignore_errors=True)

    def rpc(self, yol, girdi=None, durum=200):
        r = self.c.post(f"/api/atolye/rpc/{yol}", json={"girdi": girdi})
        self.assertEqual(r.status_code, durum, r.text)
        return r.json()


class TestProsedurler(AtolyeTesti):
    def test_kimlik(self):
        me = self.rpc("auth.me")
        self.assertEqual((me["id"], me["role"], me["name"]), (1, "admin", "Yerel analist"))
        self.assertEqual(self.rpc("auth.logout"), {"success": True})
        self.assertEqual(self.rpc("auth.me")["id"], 1)   # oturum yok: çıkış kimliği silmez

    def test_akis_yasam_dongusu(self):
        y = self.rpc("workflow.create", {"name": "Hat", "nodes": [{"id": "a"}], "tags": "t"})
        self.assertEqual(y, {"id": y["id"], "name": "Hat", "nodes": [{"id": "a"}], "edges": [],
                             "status": "draft", "isPublic": "false", "tags": "t"})
        self.assertEqual(self.rpc("workflow.getById", {"id": y["id"]})["version"], 1)
        self.assertEqual(self.rpc("workflow.update", {"id": y["id"], "name": "Hat 2", "status": "archived"}),
                         {"id": y["id"], "name": "Hat 2", "status": "archived"})
        g = self.rpc("workflow.getById", {"id": y["id"]})
        self.assertEqual((g["name"], g["status"], g["version"]), ("Hat 2", "archived", 2))
        liste = self.rpc("workflow.list", {"status": "archived"})
        self.assertEqual((liste["total"], [w["id"] for w in liste["items"]]), (1, [y["id"]]))
        self.assertEqual(self.rpc("workflow.list", {"status": "draft"})["total"], 0)
        self.assertEqual(self.rpc("workflow.delete", {"id": y["id"]}), {"success": True})
        self.assertEqual(self.rpc("workflow.getById", {"id": y["id"]}, durum=404)["hata"]["mesaj"], "Workflow not found")
        izler = [(x["action"], x["details"]) for x in self.rpc("audit.list")["items"]]
        self.assertEqual(izler, [("workflow_delete", "Deleted workflow: Hat 2"),
                                 ("workflow_update", "Updated workflow: Hat 2"),
                                 ("workflow_create", "Created workflow: Hat")])

    def test_sahiplik(self):
        baskasi = self.depo.akis_ekle(2, "Başkasının")
        self.rpc("workflow.getById", {"id": baskasi["id"]}, durum=404)
        self.rpc("workflow.update", {"id": baskasi["id"], "name": "x"}, durum=404)
        self.rpc("workflow.delete", {"id": baskasi["id"]}, durum=404)
        self.assertEqual(self.rpc("workflow.list")["total"], 0)
        self.assertEqual(self.depo.akis(baskasi["id"])["name"], "Başkasının")

    def test_zod_sinirlari(self):
        for girdi in ({"name": ""}, {"name": "x" * 256}, {"name": "a", "status": "archived"},
                      {"name": "a", "nodes": "değil"}, {"name": "a", "isPublic": True}, None):
            self.rpc("workflow.create", girdi, durum=400)
        self.rpc("workflow.list", {"limit": 101}, durum=400)
        self.rpc("workflow.list", {"limit": 0}, durum=400)
        self.rpc("workflow.list", {"offset": -1}, durum=400)
        self.rpc("workflow.list", {"status": "bilinmeyen"}, durum=400)
        self.rpc("workflow.executions", {"workflowId": 1, "limit": 51}, durum=400)
        self.rpc("audit.list", {"limit": 201}, durum=400)
        self.rpc("audit.log", {"action": "evidence_record", "entityType": "evidence"}, durum=400)
        self.rpc("dataset.create", {"name": "a", "filename": "b", "rowCount": -1}, durum=400)
        self.rpc("feedback.create", {"kind": "general"}, durum=400)
        self.rpc("feedback.create", {"kind": "general", "comment": "   "}, durum=400)
        self.rpc("catalog.promote", {"id": 1, "curatorNote": "x" * 2001}, durum=400)
        self.rpc("yok.prosedur", {}, durum=404)
        self.assertEqual(self.depo.akis_sayisi(), 0)

    def test_kosu(self):
        wf = self.rpc("workflow.create", {"name": "K"})
        k = self.rpc("workflow.execute", {"workflowId": wf["id"], "nodeCount": 3, "edgeCount": 2})
        self.assertEqual(self.rpc("workflow.completeExecution", {"executionId": k["executionId"], "status": "completed",
                                                                 "results": {"n": 1}}), {"success": True})
        self.rpc("workflow.completeExecution", {"executionId": k["executionId"], "status": "running"}, durum=400)
        kosular = self.rpc("workflow.executions", {"workflowId": wf["id"]})["items"]
        self.assertEqual([(x["status"], x["results"], x["nodeCount"]) for x in kosular], [("completed", {"n": 1}, 3)])
        self.assertIsNotNone(kosular[0]["completedAt"])
        self.assertEqual(self.rpc("audit.list", {"action": "workflow_execute"})["items"][0]["details"],
                         f"Started execution #{k['executionId']}")

    def test_kosu_provenans(self):
        yol = os.path.join(self.kok, "prov.jsonl")
        os.environ["ANLAM_PROVENANCE_FILE"] = yol
        try:
            k = self.rpc("workflow.execute", {"workflowId": 5})
            self.rpc("workflow.completeExecution", {"executionId": k["executionId"], "status": "failed", "error": "x"})
        finally:
            del os.environ["ANLAM_PROVENANCE_FILE"]
        with open(yol, encoding="utf-8") as f:
            kayit = json.loads(f.readline())
        self.assertEqual((kayit["kind"], kayit["workflowId"], kayit["status"]), ("dataflow_execution", 5, "failed"))

    def test_veri_seti_ve_denetim_log(self):
        d = self.rpc("dataset.create", {"name": "ds", "filename": "d.csv", "columns": ["a", "b"], "rowCount": 2})
        self.assertEqual(self.rpc("dataset.getById", {"id": d["id"]})["columns"], ["a", "b"])
        self.assertEqual(len(self.rpc("dataset.list")["items"]), 1)
        self.assertEqual(self.rpc("dataset.delete", {"id": d["id"]}), {"success": True})
        self.assertEqual(self.rpc("dataset.getById", {"id": d["id"]}, durum=404)["hata"]["mesaj"], "Dataset not found")
        log = self.rpc("audit.log", {"action": "node_add", "entityType": "node", "entityId": "n1"})
        self.assertGreater(log["id"], 0)

    def test_katalog(self):
        wf = self.rpc("workflow.create", {"name": "İyi", "nodes": [{"id": "x"}], "tags": "k"})
        self.rpc("catalog.clone", {"id": wf["id"]}, durum=404)   # kataloğa girmeden kopyalanamaz
        self.assertEqual(self.rpc("catalog.promote", {"id": wf["id"], "curatorNote": "örnek"}), {"success": True})
        k = self.rpc("catalog.list")["items"]
        self.assertEqual((len(k), k[0]["curatorNote"], k[0]["curatedBy"]), (1, "örnek", 1))
        kopya = self.depo.akis(self.rpc("catalog.clone", {"id": wf["id"]})["id"])
        self.assertEqual((kopya["name"], kopya["status"], kopya["nodes"], kopya["tags"], kopya["isBestPractice"]),
                         ("İyi (copy)", "draft", [{"id": "x"}], "k", "false"))
        self.rpc("catalog.retract", {"id": wf["id"]})
        self.assertEqual(self.rpc("catalog.list")["items"], [])
        self.rpc("catalog.promote", {"id": 9999}, durum=404)
        eylemler = [x["action"] for x in self.rpc("audit.list")["items"]]
        self.assertIn("catalog_promote", eylemler)
        self.assertIn("catalog_retract", eylemler)

    def test_yonetici_kapisi(self):
        p = atolye_sunucu.Prosedurler(self.depo)
        with self.assertRaises(atolye_sunucu.Yasak):
            p.cagir("catalog.promote", {"id": 1, "role": "user"}, {"id": 1})
        with self.assertRaises(atolye_sunucu.Yasak):
            p.cagir("feedback.summary", {"id": 1, "role": "user"}, None)

    def test_geri_bildirim(self):
        self.rpc("feedback.create", {"kind": "suggestion", "nodeType": "suc_frekans", "rating": "up"})
        self.rpc("feedback.create", {"kind": "suggestion", "nodeType": "suc_frekans", "rating": "down"})
        self.rpc("feedback.create", {"kind": "node_result", "nodeType": "suc_frekans", "rating": "up"})
        self.rpc("feedback.create", {"kind": "general", "comment": "iyi"})
        self.assertEqual(len(self.rpc("feedback.list", {"kind": "suggestion"})["items"]), 2)
        self.assertEqual(self.rpc("feedback.summary")["items"], [{"nodeType": "suc_frekans", "up": 2, "down": 1}])


class TestVeriSetiUclari(AtolyeTesti):
    def test_yukle_indir_sil(self):
        r = self.c.post("/api/datasets/upload", files={"file": ("olaylar ş.csv", "a;b\n1;2\n".encode(), "text/csv")},
                        data={"delimiter": ";", "name": "Olaylar"})
        self.assertEqual(r.status_code, 200, r.text)
        y = r.json()
        self.assertEqual((y["name"], y["filename"], y["columns"], y["rowCount"], y["sizeBytes"]),
                         ("Olaylar", "olaylar ş.csv", ["a", "b"], 1, 8))
        satir = self.depo.veri_seti(y["id"])
        self.assertTrue(satir["storageKey"].startswith("datasets/1/"))
        # Veri depo içinde değil, veri kökünde (ADR-001 md. 5).
        self.assertTrue(os.path.isfile(os.path.join(self.kok, "veri", "atolye", satir["storageKey"])))
        d = self.c.get(f"/api/datasets/{y['id']}/download")
        self.assertEqual((d.status_code, d.content), (200, "a;b\n1;2\n".encode()))
        self.assertIn("filename*=UTF-8''olaylar%20%C5%9F.csv", d.headers["content-disposition"])
        self.assertEqual(self.c.delete(f"/api/datasets/{y['id']}").json(), {"success": True})
        self.assertFalse(os.path.exists(os.path.join(self.kok, "veri", "atolye", satir["storageKey"])))
        self.assertEqual(self.c.get(f"/api/datasets/{y['id']}/download").status_code, 404)

    def test_hatalar(self):
        self.assertEqual(self.c.post("/api/datasets/upload", data={"name": "x"}).status_code, 400)
        self.assertEqual(self.c.get("/api/datasets/abc/download").status_code, 400)
        self.assertEqual(self.c.delete("/api/datasets/999").status_code, 404)
        baskasi = self.depo.veri_seti_ekle(2, "b", "b.csv", storageKey="datasets/2/x-b.csv")
        self.assertEqual(self.c.get(f"/api/datasets/{baskasi['id']}/download").status_code, 404)


class TestSucKoprusu(AtolyeTesti):
    SATIRLAR = [{"tur": "hırsızlık"}, {"tur": "gasp"}, {"tur": "hırsızlık"}]

    def test_manifest_cekirdek_kaydi(self):
        from sinama.arayuz.ortak import ARACLAR
        m = self.c.get("/api/ml/suc/manifest").json()
        self.assertEqual([a["ad"] for a in m], sorted(ARACLAR))
        self.assertTrue(all({"ad", "aciklama", "sema"} == set(a) for a in m))

    def test_mcp_ile_ayni_boru_hatti(self):
        from sinama.arayuz.sunucu import arac_calistir
        r = self.c.post("/api/ml/suc/frekans", json={"satirlar": self.SATIRLAR, "alan": "tur"})
        self.assertEqual(r.status_code, 200)
        dogrudan = arac_calistir("frekans", {"satirlar": self.SATIRLAR, "alan": "tur"})
        self.assertEqual(r.json()["sonuc"], dogrudan["sonuc"])
        self.assertEqual(r.json()["meta"]["arac"], "frekans")
        self.assertTrue(r.json()["meta"]["oturum_izlendi"])   # kanıt oturumu çekirdekte

    def test_hata_tipleri(self):
        r = self.c.post("/api/ml/suc/yok_boyle", json={})
        self.assertEqual((r.status_code, r.json()["tip"]), (404, "kullanim"))
        r = self.c.post("/api/ml/suc/frekans", json={"csv_yolu": "veri/x.csv", "alan": "tur"})
        self.assertEqual((r.status_code, r.json()["tip"]), (400, "kullanim"))
        r = self.c.post("/api/ml/suc/frekans", json={"satirlar": self.SATIRLAR})   # zorunlu alan yok
        self.assertEqual(r.status_code, 400)
        self.assertIn(r.json()["tip"], ("kullanim", "veri"))
        self.assertTrue(r.json()["mesaj"])

    def test_rehberli_calisma_dugumu(self):
        # Sınama'nın tek atımlık bilim aracı düğüm olarak da çalışır: kategorik hüküm, olasılık yok.
        import random
        rnd = random.Random(3)
        satirlar = [{"tarih": f"{2024 + a // 12}-{a % 12 + 1:02d}-{1 + rnd.randrange(28):02d}", "kanal": "karakol"}
                    for a in range(24) for _ in range(30 + (15 if a >= 12 else 0))]
        r = self.c.post("/api/ml/suc/rehberli_calisma",
                        json={"satirlar": satirlar, "soru_turu": "ARTIS", "amac": "kesifsel"})
        self.assertEqual(r.status_code, 200, r.text)
        sonuc = r.json()["sonuc"]
        self.assertEqual((sonuc["soru_turu"], sonuc["amac"]), ("ARTIS", "kesifsel"))
        self.assertTrue(any(h["kimlik"].startswith("R-") for h in sonuc["hipotezler"]))   # rakipler
        self.assertNotIn("olasilik", json.dumps(sonuc, ensure_ascii=False))


class TestKapsamDisiVeKapilar(AtolyeTesti):
    def test_kapsam_disi_503(self):
        for yol, yontem in (("/api/ml/ml/random_forest", "post"), ("/api/ml/health", "get"),
                            ("/api/science/api/research", "get"), ("/api/evidence/harp-esitle", "post")):
            r = getattr(self.c, yontem)(yol)
            self.assertEqual(r.status_code, 503, yol)
            self.assertEqual(r.json()["kapsam_disi"], "ADR-004 md. 4")
            self.assertTrue(r.json()["error"] and r.json()["detail"])

    def test_ajan_erisilemez(self):
        govde = {"question": "?", "context": {"inputs": [{"nodeType": "suc_frekans", "rowCount": 3, "data": {}}]}}
        atolye_sunucu_ajan = os.environ.get("SINAMA_AJAN_URL")
        r = self.c.post("/api/agent/insight", json=govde)
        if atolye_sunucu_ajan is None:   # varsayılan 8800'de servis yoksa 503 (çalışıyorsa 200/502)
            self.assertIn(r.status_code, (200, 502, 503))
        self.assertEqual(self.c.post("/api/agent/insight", json={"context": {}}).status_code, 400)
        self.assertEqual(self.c.post("/api/agent/insight", content=b"{x",
                                     headers={"content-type": "application/json"}).status_code, 400)

    def test_ajan_vekili(self):
        import http.server
        import threading

        class Ajan(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                govde = json.loads(self.rfile.read(int(self.headers["content-length"])))
                yanit = json.dumps({"insight": f"{len(govde['context']['inputs'])} girdi", "model": "sahte"}).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(yanit)

            def log_message(self, *a):
                pass
        s = http.server.HTTPServer(("127.0.0.1", 0), Ajan)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        try:
            kok2 = tempfile.mkdtemp(prefix="atolye_ajan_")
            os.environ["SINAMA_AJAN_URL"] = f"http://127.0.0.1:{s.server_address[1]}"
            app = uyg.uygulama_olustur(veri_koku=kok2, dil_modeli_url=None)
            c = TestClient(app, client=("127.0.0.1", 1))
            r = c.post("/api/agent/insight", json={"context": {"inputs": [{"nodeType": "a"}, {"nodeType": "b"}]}})
            self.assertEqual(r.json(), {"insight": "2 girdi", "model": "sahte"})
            self.assertEqual(app.state.atolye["depo"].denetim_sayisi(action="agent_insight"), 1)
            app.state.atolye["depo"].kapat()
        finally:
            os.environ.pop("SINAMA_AJAN_URL", None)
            s.shutdown()
            shutil.rmtree(kok2, ignore_errors=True)

    def test_yalniz_yerel(self):
        uzak = TestClient(self.app, client=("192.168.1.20", 5000))
        for yontem, yol in (("post", "/api/atolye/rpc/auth.me"), ("get", "/api/ml/suc/manifest"),
                            ("post", "/api/ml/suc/frekans"), ("get", "/api/evidence/public-key"),
                            ("post", "/api/datasets/upload"), ("post", "/api/agent/insight")):
            self.assertEqual(getattr(uzak, yontem)(yol).status_code, 403, yol)
        self.assertEqual(TestClient(self.app, client=("::1", 5000)).post("/api/atolye/rpc/auth.me",
                                                                           json={}).status_code, 200)

    def test_dev_login(self):
        r = self.c.get("/api/dev-login", follow_redirects=False)
        self.assertEqual((r.status_code, r.headers["location"]), (302, "/atolye/"))


class TestTekSurec(AtolyeTesti):
    """E5: Rehberli ve Atölye aynı süreçten, aynı porttan; MySQL/S3/ml-service/Kimi gerekmez."""

    def test_iki_yuz_bir_uygulama(self):
        self.assertEqual(self.c.get("/api/saglik").json()["durum"], "hazir")
        self.assertEqual(self.rpc("auth.me")["id"], 1)
        yollar = {getattr(r, "path", "") for r in self.app.routes}
        for y in ("/api/calisma", "/api/atolye/rpc/{yol}", "/api/ml/suc/{arac}", "/atolye/{yol:path}"):
            self.assertIn(y, yollar)
        # Kalıcılık tek dosya, veri kökünde (depo dışında).
        self.assertTrue(os.path.isfile(os.path.join(self.kok, "atolye.sqlite3")))
        self.assertFalse(uyg.depo_icinde_mi(os.path.join(self.kok, "atolye.sqlite3")))

    def test_atolye_statik(self):
        dist = os.path.join(KOK, "uygulama", "atolye", "dist")
        if not os.path.isfile(os.path.join(dist, "index.html")):
            self.assertEqual(self.c.get("/atolye/").status_code, 503)
            self.skipTest("Atölye derlenmemiş")
        r = self.c.get("/atolye/")
        self.assertEqual(r.status_code, 200)
        self.assertIn('src="/atolye/assets/', r.text)
        self.assertEqual(self.c.get("/atolye/login").text, r.text)   # SPA geri dönüşü
        self.assertEqual(self.c.get("/atolye/assets/yok.js").status_code, 404)
        self.assertNotEqual(self.c.get("/atolye/../sunucu.py").status_code, 200)
        self.assertEqual(self.c.get("/atolye", follow_redirects=False).status_code, 307)


if __name__ == "__main__":
    unittest.main()
