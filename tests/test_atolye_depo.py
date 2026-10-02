# -*- coding: utf-8 -*-
"""
test_atolye_depo.py — A6 eşdeğerlik E2 (ESDEGERLIK.md): DataFlow'un B sınıfı sunucu
testlerinin Python karşılıkları — workflow-router, dataset-router, audit-router,
integration, csv, storage.

DataFlow'da bu testler bir bellek içi test ikizini (tests/helpers.ts InMemoryDb) sınıyordu;
buradaki karşılıklar Atölye'nin GERÇEK deposunu (SQLite, uygulama/atolye_depo.py) aynı
senaryolarla sınar. Her test, karşılığı olduğu DataFlow testini `# DataFlow:` satırında
adıyla gösterir (betikler/a6_esdegerlik.py bu işaretleri sayar). Yalnız standart kitaplık.
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from uygulama.atolye_depo import AtolyeDeposu, DosyaDeposu, csv_ust_verisi  # noqa: E402

with open(os.path.join(KOK, "uygulama", "atolye_esdegerlik", "sentetik", "dataflow_fiksturleri.json"),
          encoding="utf-8") as _f:
    FIKSTUR = json.load(_f)
DEMO, POLIS, MINIMAL = FIKSTUR["demoWorkflow"], FIKSTUR["policeWorkflow"], FIKSTUR["minimalWorkflow"]
GUNCELLEME, ORNEK_VS, POLIS_VS = FIKSTUR["workflowUpdate"], FIKSTUR["sampleDataset"], FIKSTUR["policeDataset"]
DENETIM_EYLEMLERI = FIKSTUR["auditActions"]


def akis(db, userId=1, name="WF", nodes=(), edges=(), **ek):
    """DataFlow testlerindeki insertWorkflow çağrısının karşılığı."""
    return db.akis_ekle(userId, name, nodes, edges, ek.pop("description", ""), **ek)


def tarih(metin):
    return datetime.datetime.fromisoformat(metin.replace("Z", "+00:00"))


class DepoTesti(unittest.TestCase):
    def setUp(self):
        self.db = AtolyeDeposu(":memory:")

    def tearDown(self):
        self.db.kapat()


class TestWorkflowCRUD(DepoTesti):
    def test_tum_alanlarla_olusturma(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Create › should create a workflow with all fields
        wf = akis(self.db, 1, DEMO["name"], DEMO["nodes"], DEMO["edges"], description=DEMO["description"],
                  status="draft", isPublic="false", version=1, tags="sales,analytics")
        self.assertGreater(wf["id"], 0)
        self.assertEqual(wf["name"], DEMO["name"])
        self.assertEqual(wf["userId"], 1)
        self.assertEqual(len(wf["nodes"]), len(DEMO["nodes"]))
        self.assertEqual(len(wf["edges"]), len(DEMO["edges"]))
        self.assertEqual(wf["status"], "draft")
        self.assertEqual(wf["version"], 1)

    def test_asgari_alanlarla_olusturma(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Create › should create a workflow with minimal fields
        wf = akis(self.db, 1, MINIMAL["name"], MINIMAL["nodes"], MINIMAL["edges"],
                  description=MINIMAL["description"])
        self.assertGreater(wf["id"], 0)
        self.assertEqual(wf["name"], MINIMAL["name"])
        self.assertEqual(wf["nodes"], [])
        self.assertEqual(wf["edges"], [])

    def test_kolluk_akisi(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Create › should create a police workflow with KVKK metadata
        wf = akis(self.db, 1, POLIS["name"], POLIS["nodes"], POLIS["edges"],
                  description=POLIS["description"], tags="kolluk,istihbarat")
        self.assertEqual(wf["name"], POLIS["name"])
        turler = [(n.get("data") or {}).get("type") for n in wf["nodes"]]
        for t in ("pts_source", "anpr_source", "sna", "geo_hotspot", "evidence_export"):
            self.assertIn(t, turler)

    def test_kimlik_artar(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Create › should auto-increment version on creation
        wf1, wf2 = akis(self.db, name="WF 1"), akis(self.db, name="WF 2")
        self.assertGreater(wf2["id"], wf1["id"])

    def test_kullanicinin_akislari(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Read › should list workflows for a user
        akis(self.db, 1, "User 1 WF")
        akis(self.db, 1, "User 1 WF 2", status="published", isPublic="true")
        akis(self.db, 2, "User 2 WF")
        u1 = self.db.akislar(1)
        self.assertEqual(len(u1), 2)
        self.assertTrue(all(w["userId"] == 1 for w in u1))
        u2 = self.db.akislar(2)
        self.assertEqual(len(u2), 1)
        self.assertEqual(u2[0]["name"], "User 2 WF")

    def test_kimlikle_bulma(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Read › should get a workflow by ID
        wf = akis(self.db, 1, "Test WF", DEMO["nodes"], DEMO["edges"], description="Desc")
        bulunan = self.db.akis(wf["id"])
        self.assertIsNotNone(bulunan)
        self.assertEqual(bulunan["name"], "Test WF")
        self.assertEqual(bulunan["description"], "Desc")

    def test_olmayan_akis(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Read › should return undefined for non-existent workflow
        self.assertIsNone(self.db.akis(99999))

    def test_guncellenme_sirasi(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Read › should sort workflows by updatedAt descending
        akis(self.db, name="Older")
        time.sleep(0.01)
        akis(self.db, name="Newer")
        wfs = self.db.akislar(1)
        self.assertEqual([w["name"] for w in wfs], ["Newer", "Older"])

    def test_ad_aciklama_guncelleme(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Update › should update workflow name and description
        wf = akis(self.db, name="Original", description="Original desc")
        self.db.akis_guncelle(wf["id"], name=GUNCELLEME["name"], description=GUNCELLEME["description"])
        g = self.db.akis(wf["id"])
        self.assertEqual(g["name"], GUNCELLEME["name"])
        self.assertEqual(g["description"], GUNCELLEME["description"])

    def test_yayimlama(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Update › should update workflow status to published
        wf = akis(self.db, name="Draft WF")
        self.db.akis_guncelle(wf["id"], status="published", isPublic="true")
        g = self.db.akis(wf["id"])
        self.assertEqual(g["status"], "published")
        self.assertEqual(g["isPublic"], "true")

    def test_dugum_baglanti_guncelleme(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Update › should update nodes and edges
        wf = akis(self.db, name="Empty WF")
        self.db.akis_guncelle(wf["id"], nodes=DEMO["nodes"], edges=DEMO["edges"])
        g = self.db.akis(wf["id"])
        self.assertEqual(len(g["nodes"]), len(DEMO["nodes"]))
        self.assertEqual(len(g["edges"]), len(DEMO["edges"]))

    def test_guncelleme_zamani(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Update › should update updatedAt timestamp on modification
        wf = akis(self.db, name="Time Test")
        time.sleep(0.02)
        self.db.akis_guncelle(wf["id"], name="Updated")
        self.assertGreater(tarih(self.db.akis(wf["id"])["updatedAt"]), tarih(wf["updatedAt"]))

    def test_silme(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Delete › should delete a workflow
        wf = akis(self.db, name="To Delete")
        self.db.akis_sil(wf["id"])
        self.assertIsNone(self.db.akis(wf["id"]))

    def test_yalniz_belirtilen_silinir(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow CRUD › Delete › should only delete the specified workflow
        wf1, wf2 = akis(self.db, name="Keep"), akis(self.db, name="Delete")
        self.db.akis_sil(wf2["id"])
        self.assertIsNotNone(self.db.akis(wf1["id"]))
        self.assertIsNone(self.db.akis(wf2["id"]))


class TestWorkflowSahiplik(DepoTesti):
    def test_kullanici_yalitimi(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow Ownership › should enforce user isolation - users cannot see others workflows
        akis(self.db, 1, "User1 Private")
        akis(self.db, 2, "User2 Private")
        u1, u2 = self.db.akislar(1), self.db.akislar(2)
        self.assertEqual([w["name"] for w in u1], ["User1 Private"])
        self.assertEqual([w["name"] for w in u2], ["User2 Private"])
        # Sahiplik koşullu okuma (getById/update/delete'in yolu) başkasının akışını vermez.
        self.assertIsNone(self.db.akis(u2[0]["id"], userId=1))

    def test_sahiplik_kaydi(self):
        # DataFlow: tests/workflow-router.test.ts › Workflow Ownership › should track workflow ownership correctly
        self.assertEqual(akis(self.db, 42, "Owner Test")["userId"], 42)


class TestKosuIzleme(DepoTesti):
    def test_kosu_kaydi(self):
        # DataFlow: tests/workflow-router.test.ts › Execution Tracking › should record a workflow execution
        k = self.db.kosu_ekle(1, 1, "running", nodeCount=7, edgeCount=6,
                              startedAt=datetime.datetime.now(datetime.timezone.utc))
        self.assertGreater(k["id"], 0)
        self.assertEqual((k["status"], k["nodeCount"], k["edgeCount"]), ("running", 7, 6))

    def test_kosu_tamamlama(self):
        # DataFlow: tests/workflow-router.test.ts › Execution Tracking › should complete an execution with results
        k = self.db.kosu_ekle(1, 1, "running")
        self.db.kosu_guncelle(k["id"], status="completed",
                              results={"summary": "Execution completed successfully"},
                              completedAt=datetime.datetime.now(datetime.timezone.utc))
        g = self.db.kosular(1)[0]
        self.assertEqual(g["status"], "completed")
        self.assertEqual(g["results"], {"summary": "Execution completed successfully"})
        self.assertIsNotNone(g["completedAt"])

    def test_basarisiz_kosu(self):
        # DataFlow: tests/workflow-router.test.ts › Execution Tracking › should record a failed execution
        k = self.db.kosu_ekle(1, 1, "running")
        self.db.kosu_guncelle(k["id"], status="failed", error="Null value in column 'revenue'",
                              completedAt=datetime.datetime.now(datetime.timezone.utc))
        g = self.db.kosular(1)[0]
        self.assertEqual(g["status"], "failed")
        self.assertEqual(g["error"], "Null value in column 'revenue'")

    def test_kosu_sirasi(self):
        # DataFlow: tests/workflow-router.test.ts › Execution Tracking › should list executions sorted by startedAt descending
        for gun in ("2026-01-01", "2026-06-15", "2026-03-01"):
            self.db.kosu_ekle(1, 1, "completed", startedAt=datetime.date.fromisoformat(gun),
                              completedAt=datetime.datetime.now(datetime.timezone.utc))
        k = self.db.kosular(1)
        self.assertEqual(len(k), 3)
        self.assertEqual([x["startedAt"][:10] for x in k], ["2026-06-15", "2026-03-01", "2026-01-01"])


def veri_seti(db, userId=1, name="ds", filename="d.csv", columns=("a",), rowCount=1, **ek):
    """DataFlow testlerindeki insertDataset çağrısının karşılığı."""
    return db.veri_seti_ekle(userId, name, filename, columns, rowCount, **ek)


class TestVeriSetiCRUD(DepoTesti):
    def test_tum_ust_veriyle(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Create › should register a dataset with all metadata
        ds = veri_seti(self.db, 1, ORNEK_VS["name"], ORNEK_VS["filename"], ORNEK_VS["columns"],
                       ORNEK_VS["rowCount"], sizeBytes=ORNEK_VS["sizeBytes"])
        self.assertGreater(ds["id"], 0)
        for alan in ("name", "filename", "columns", "rowCount", "sizeBytes"):
            self.assertEqual(ds[alan], ORNEK_VS[alan])
        self.assertEqual(ds["userId"], 1)

    def test_boyutsuz(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Create › should register a dataset without sizeBytes
        ds = veri_seti(self.db, 1, ORNEK_VS["name"], ORNEK_VS["filename"], ORNEK_VS["columns"], 0)
        self.assertGreater(ds["id"], 0)
        self.assertEqual(ds["rowCount"], 0)
        self.assertIsNone(ds["sizeBytes"])

    def test_kolluk_veri_seti(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Create › should register a police dataset
        ds = veri_seti(self.db, 1, POLIS_VS["name"], POLIS_VS["filename"], POLIS_VS["columns"],
                       POLIS_VS["rowCount"], sizeBytes=POLIS_VS["sizeBytes"])
        self.assertEqual(ds["name"], POLIS_VS["name"])
        self.assertEqual(ds["rowCount"], 50000)
        for s in ("plate", "camera_id", "speed_kmh"):
            self.assertIn(s, ds["columns"])

    def test_buyuk_veri_seti(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Create › should handle large datasets
        ds = veri_seti(self.db, 1, "large_dataset", "data.csv", ["col1", "col2"], 1_000_000,
                       sizeBytes=500_000_000)
        self.assertEqual((ds["rowCount"], ds["sizeBytes"]), (1_000_000, 500_000_000))

    def test_kullanicinin_veri_setleri(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Read › should list datasets for a user
        veri_seti(self.db, 1, "ds1", "1.csv", ["a"], 100)
        veri_seti(self.db, 1, "ds2", "2.csv", ["b"], 200)
        veri_seti(self.db, 2, "ds3", "3.csv", ["c"], 300)
        u1 = self.db.veri_setleri(1)
        self.assertEqual(len(u1), 2)
        self.assertTrue(all(d["userId"] == 1 for d in u1))
        self.assertEqual(len(self.db.veri_setleri(2)), 1)

    def test_kimlikle_bulma(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Read › should get a dataset by ID
        ds = veri_seti(self.db, 1, "Find Me", "find.csv", ["x", "y", "z"], 500)
        b = self.db.veri_seti(ds["id"])
        self.assertEqual(b["name"], "Find Me")
        self.assertEqual(b["columns"], ["x", "y", "z"])

    def test_olmayan(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Read › should return undefined for non-existent dataset
        self.assertIsNone(self.db.veri_seti(99999))

    def test_olusturma_sirasi(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Read › should sort datasets by createdAt descending
        veri_seti(self.db, 1, "Old", "old.csv")
        time.sleep(0.01)
        veri_seti(self.db, 1, "New", "new.csv")
        self.assertEqual([d["name"] for d in self.db.veri_setleri(1)], ["New", "Old"])

    def test_silme(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Delete › should delete a dataset
        ds = veri_seti(self.db, name="To Delete")
        self.db.veri_seti_sil(ds["id"])
        self.assertIsNone(self.db.veri_seti(ds["id"]))

    def test_yalniz_belirtilen_silinir(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset CRUD › Delete › should only delete the specified dataset
        d1, d2 = veri_seti(self.db, name="Keep"), veri_seti(self.db, name="Delete")
        self.db.veri_seti_sil(d2["id"])
        self.assertIsNotNone(self.db.veri_seti(d1["id"]))
        self.assertIsNone(self.db.veri_seti(d2["id"]))

    def test_kullanici_yalitimi(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset Ownership › should enforce user isolation for datasets
        veri_seti(self.db, 1, "Private 1")
        veri_seti(self.db, 2, "Private 2")
        self.assertEqual([d["name"] for d in self.db.veri_setleri(1)], ["Private 1"])
        self.assertEqual([d["name"] for d in self.db.veri_setleri(2)], ["Private 2"])
        self.assertIsNone(self.db.veri_seti(self.db.veri_setleri(2)[0]["id"], userId=1))

    def test_sifir_satir(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset Validation › should handle datasets with zero rows
        ds = veri_seti(self.db, 1, "Empty", "empty.csv", [], 0)
        self.assertEqual((ds["rowCount"], ds["columns"]), (0, []))

    def test_cok_sutun(self):
        # DataFlow: tests/dataset-router.test.ts › Dataset Validation › should handle datasets with many columns
        ds = veri_seti(self.db, 1, "Wide", "wide.csv", [f"col_{i}" for i in range(100)], 1000)
        self.assertEqual(len(ds["columns"]), 100)
        self.assertEqual((ds["columns"][0], ds["columns"][99]), ("col_0", "col_99"))


class TestDenetimIzi(DepoTesti):
    def test_akis_olusturma_kaydi(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Create › should log a workflow creation event
        log = self.db.denetim_ekle(1, "workflow_create", "workflow", "123", "Created workflow: Sales Analysis")
        self.assertGreater(log["id"], 0)
        self.assertEqual((log["action"], log["entityType"], log["entityId"], log["details"]),
                         ("workflow_create", "workflow", "123", "Created workflow: Sales Analysis"))
        self.assertIsNotNone(log["createdAt"])

    def test_tum_eylemler(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Create › should log all workflow actions
        for e in DENETIM_EYLEMLERI:
            log = self.db.denetim_ekle(1, e["action"], e["entityType"], details=e["details"])
            self.assertEqual((log["action"], log["entityType"]), (e["action"], e["entityType"]))
        self.assertEqual(len(self.db.denetimler(1)), len(DENETIM_EYLEMLERI))

    def test_dugum_islemleri(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Create › should log node operations
        log = self.db.denetim_ekle(1, "node_add", "node", "csv-1", "Added CSV Source node to workflow #42")
        self.assertEqual((log["action"], log["entityId"]), ("node_add", "csv-1"))

    def test_baglantilar(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Create › should log edge connections
        log = self.db.denetim_ekle(1, "connect", "edge", "e1", "Connected csv-1 to stats-1")
        self.assertEqual((log["action"], log["entityType"]), ("connect", "edge"))

    def test_kimlik_olaylari(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Create › should log user authentication events
        log = self.db.denetim_ekle(1, "user_login", "user", "1", "User logged in from 192.168.1.100")
        self.assertEqual((log["action"], log["entityType"]), ("user_login", "user"))

    def test_opsiyonel_alanlar(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Create › should allow optional entityId and details
        log = self.db.denetim_ekle(1, "workflow_execute", "workflow")
        self.assertGreater(log["id"], 0)
        self.assertIsNone(log["entityId"])
        self.assertIsNone(log["details"])

    def test_kullanicinin_izi(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Read › should list audit logs for a user
        self.db.denetim_ekle(1, "workflow_create", "workflow")
        self.db.denetim_ekle(1, "workflow_execute", "workflow")
        self.db.denetim_ekle(2, "workflow_create", "workflow")
        u1 = self.db.denetimler(1)
        self.assertEqual(len(u1), 2)
        self.assertTrue(all(x["userId"] == 1 for x in u1))
        self.assertEqual(len(self.db.denetimler(2)), 1)

    def test_olusturma_sirasi(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Read › should sort audit logs by createdAt descending
        self.db.denetim_ekle(1, "workflow_create", "workflow", details="Older",
                             createdAt=datetime.date(2026, 1, 1))
        self.db.denetim_ekle(1, "workflow_execute", "workflow", details="Newer",
                             createdAt=datetime.date(2026, 6, 15))
        self.assertEqual([x["details"] for x in self.db.denetimler(1)], ["Newer", "Older"])

    def test_izi_olmayan_kullanici(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › Read › should return empty array for user with no audit logs
        self.assertEqual(self.db.denetimler(999), [])

    def test_kati_yalitim(self):
        # DataFlow: tests/audit-router.test.ts › Audit Log CRUD › User Isolation › should enforce strict user isolation for audit logs
        self.db.denetim_ekle(1, "workflow_create", "workflow", "1", "User 1 creates WF")
        self.db.denetim_ekle(1, "workflow_execute", "workflow", "1", "User 1 executes WF")
        self.db.denetim_ekle(2, "workflow_create", "workflow", "2", "User 2 creates WF")
        u1, u2 = self.db.denetimler(1), self.db.denetimler(2)
        self.assertEqual(len(u1), 2)
        self.assertFalse(any(x["userId"] == 2 for x in u1))
        self.assertEqual(len(u2), 1)
        self.assertFalse(any(x["userId"] == 1 for x in u2))

    def test_kvkk_hukuki_dayanak(self):
        # DataFlow: tests/audit-router.test.ts › KVKK Compliance Audit › should log all Kolluk data queries with legal basis
        sorgular = [("PTS", "5271-md-3", "Gizli"), ("ANPR", "2559-md-4", "Kisitli"),
                    ("MOBESE", "2559-md-4", "Kisitli"), ("Adli Sicil", "5271-md-3", "Cok Gizli")]
        for kaynak, dayanak, sinif in sorgular:
            self.db.denetim_ekle(1, "workflow_execute", "workflow",
                                 details=f"Queried {kaynak} with legal basis {dayanak}, KVKK: {sinif}")
        loglar = self.db.denetimler(1)
        self.assertEqual(len(loglar), 4)
        for sorgu in sorgular:
            self.assertTrue(any(all(p in (x["details"] or "") for p in sorgu) for x in loglar))

    def test_kanit_zinciri(self):
        # DataFlow: tests/audit-router.test.ts › KVKK Compliance Audit › should maintain complete audit chain for evidence export
        kanit, dosya, memur = "EVD-20260629-ABC123", "2026/1234", "PN-12345"
        self.db.denetim_ekle(1, "workflow_execute", "workflow", "wf-42", f"Data query: PTS source, case {dosya}")
        self.db.denetim_ekle(1, "workflow_execute", "workflow", "wf-42", "Analysis: SNA + Geo Hotspot completed")
        self.db.denetim_ekle(1, "workflow_publish", "workflow", "wf-42",
                             f"Evidence exported: {kanit}, officer: {memur}, case: {dosya}")
        loglar = self.db.denetimler(1)
        self.assertEqual(len(loglar), 3)
        # DataFlow ikizi aynı milisaniyedeki kayıtları ekleme sırasında bırakıp [2]'ye bakıyordu;
        # gerçek depo createdAt azalan sıralar → dışa aktarma kaydı EN YENİ olandır ([0]).
        for p in (kanit, dosya, memur):
            self.assertIn(p, loglar[0]["details"])


class TestButunlesik(DepoTesti):
    def test_satis_hatti(self):
        # DataFlow: tests/integration.test.ts › End-to-End: Sales Analysis Pipeline › should complete full lifecycle: create workflow, execute, audit, and register dataset
        u = 1
        wf = akis(self.db, u, DEMO["name"], DEMO["nodes"], DEMO["edges"], description=DEMO["description"],
                  tags="sales,analytics,q1")
        self.assertEqual((len(wf["nodes"]), len(wf["edges"])), (7, 6))
        self.assertEqual(self.db.denetim_ekle(u, "workflow_create", "workflow", str(wf["id"]),
                                              f"Created workflow: {wf['name']}")["action"], "workflow_create")
        k = self.db.kosu_ekle(wf["id"], u, "running", nodeCount=len(wf["nodes"]), edgeCount=len(wf["edges"]))
        self.assertEqual(k["status"], "running")
        self.db.denetim_ekle(u, "workflow_execute", "workflow", str(wf["id"]), f"Started execution #{k['id']}")
        self.db.kosu_guncelle(k["id"], status="completed", completedAt=datetime.datetime.now(datetime.timezone.utc),
                              results={"summary": "Execution completed",
                                       "nodeResults": {"csv-1": {"rowsProcessed": 15000},
                                                       "dq-1": {"qualityScore": 0.94}}})
        bitmis = self.db.kosular(wf["id"])[0]
        self.assertEqual(bitmis["status"], "completed")
        self.assertIn("summary", bitmis["results"])
        ds = veri_seti(self.db, u, ORNEK_VS["name"], ORNEK_VS["filename"], ORNEK_VS["columns"],
                       ORNEK_VS["rowCount"], sizeBytes=ORNEK_VS["sizeBytes"])
        self.assertEqual((ds["name"], ds["rowCount"]), (ORNEK_VS["name"], 15000))
        iz = self.db.denetimler(u)
        self.assertEqual(len(iz), 2)
        self.assertEqual({x["action"] for x in iz}, {"workflow_create", "workflow_execute"})
        self.assertEqual((self.db.akis_sayisi(), self.db.kosu_sayisi(), self.db.denetim_sayisi(),
                          self.db.veri_seti_sayisi()), (1, 1, 2, 1))

    def test_kolluk_sorusturmasi(self):
        # DataFlow: tests/integration.test.ts › End-to-End: Police Kolluk Investigation › should complete Kolluk investigation with KVKK compliance
        u = 42
        wf = akis(self.db, u, POLIS["name"], POLIS["nodes"], POLIS["edges"], description=POLIS["description"],
                  tags="kolluk,istihbarat,kvkk")
        self.assertEqual(len(wf["nodes"]), 5)
        turler = [(n.get("data") or {}).get("type") for n in wf["nodes"]]
        self.assertIn("pts_source", turler)
        self.assertIn("evidence_export", turler)
        for kaynak, dayanak, sinif in (("PTS", "5271-md-3", "Gizli"), ("ANPR", "2559-md-4", "Kisitli")):
            self.db.denetim_ekle(u, "workflow_execute", "workflow", str(wf["id"]),
                                 f"Queried {kaynak} with legal basis {dayanak}, KVKK: {sinif}")
        k = self.db.kosu_ekle(wf["id"], u, "running", nodeCount=5, edgeCount=len(wf["edges"]))
        self.db.kosu_guncelle(k["id"], status="completed", completedAt=datetime.datetime.now(datetime.timezone.utc),
                              results={"sna": {"nodeCount": 47}, "evidenceHash": "sha256:a1b2c3d4..."})
        self.db.denetim_ekle(u, "workflow_publish", "workflow", str(wf["id"]),
                             "Evidence exported: EVD-20260629-ABC123, officer: PN-12345, case: 2026/1234")
        iz = self.db.denetimler(u)
        self.assertEqual(len(iz), 3)
        kanit = next(x for x in iz if x["action"] == "workflow_publish")
        self.assertIn("EVD-20260629-ABC123", kanit["details"])
        self.assertIn("PN-12345", kanit["details"])
        self.assertEqual(len([x for x in iz if x["action"] == "workflow_execute"]), 2)
        self.assertEqual(self.db.denetimler(999), [])
        self.assertEqual(self.db.akislar(999), [])

    def test_cok_akisli_pano(self):
        # DataFlow: tests/integration.test.ts › End-to-End: Multi-Workflow User Dashboard › should support a user with multiple workflows, datasets, and audit history
        u = 7
        for i in range(1, 4):
            akis(self.db, u, f"Analysis Pipeline {i}", DEMO["nodes"][:i + 2], DEMO["edges"][:i + 1],
                 description=f"Pipeline #{i}", status="published" if i == 3 else "draft",
                 isPublic="true" if i == 3 else "false", version=i, tags=f"pipeline,batch{i}")
        veri_seti(self.db, u, "customers", "customers.csv", ["id", "name", "email", "region"], 5000, sizeBytes=256000)
        veri_seti(self.db, u, "transactions", "transactions.csv", ["id", "amount", "date", "customer_id"], 50000,
                  sizeBytes=2048000)
        for i in range(1, 4):
            self.db.kosu_ekle(i, u, "completed", nodeCount=i + 2, edgeCount=i + 1,
                              completedAt=datetime.datetime.now(datetime.timezone.utc))
            self.db.denetim_ekle(u, "workflow_execute", "workflow", details=f"Executed workflow #{i}")
        wfs = self.db.akislar(u)
        self.assertEqual(len(wfs), 3)
        self.assertTrue(any(w["status"] == "published" for w in wfs))
        dss = self.db.veri_setleri(u)
        self.assertEqual((len(dss), sum(d["rowCount"] for d in dss)), (2, 55000))
        self.assertEqual(len(self.db.denetimler(u)), 3)
        self.assertEqual((self.db.akis_sayisi(), self.db.veri_seti_sayisi(), self.db.kosu_sayisi(),
                          self.db.denetim_sayisi()), (3, 2, 3, 3))

    def test_eszamanli_kullanici_yalitimi(self):
        # DataFlow: tests/integration.test.ts › End-to-End: Concurrent User Isolation › should maintain strict isolation between multiple users
        akis(self.db, 1, "Sales Pipeline")
        veri_seti(self.db, 1, "sales.csv", "sales.csv", ["rev"], 1000)
        self.db.denetim_ekle(1, "workflow_create", "workflow", details="U1 creates")
        akis(self.db, 2, "SNA Analysis")
        veri_seti(self.db, 2, "anpr.csv", "anpr.csv", ["plate"], 5000)
        self.db.denetim_ekle(2, "workflow_create", "workflow", details="U2 creates")
        self.assertEqual([w["name"] for w in self.db.akislar(1)], ["Sales Pipeline"])
        self.assertEqual([w["name"] for w in self.db.akislar(2)], ["SNA Analysis"])
        self.assertEqual([d["name"] for d in self.db.veri_setleri(1)], ["sales.csv"])
        self.assertEqual([d["name"] for d in self.db.veri_setleri(2)], ["anpr.csv"])
        self.assertEqual([x["details"] for x in self.db.denetimler(1)], ["U1 creates"])
        self.assertEqual([x["details"] for x in self.db.denetimler(2)], ["U2 creates"])
        self.assertEqual((self.db.akislar(999), self.db.veri_setleri(999), self.db.denetimler(999)), ([], [], []))


class TestCsvUstVerisi(unittest.TestCase):
    def test_basit(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › parses a simple CSV with header
        self.assertEqual(csv_ust_verisi("a,b,c\n1,2,3\n4,5,6\n"), {"columns": ["a", "b", "c"], "rowCount": 2})

    def test_sondaki_bos_satirlar(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › ignores trailing blank lines
        self.assertEqual(csv_ust_verisi("a,b\n1,2\n\n\n")["rowCount"], 1)

    def test_tirnakli_virgul(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › handles quoted fields with embedded commas
        self.assertEqual(csv_ust_verisi('name,note\n"Smith, John","hello, world"\n'),
                         {"columns": ["name", "note"], "rowCount": 1})

    def test_tirnakli_satir_sonu(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › handles quoted fields with embedded newlines (single record)
        self.assertEqual(csv_ust_verisi('a,b\n"line1\nline2",x\ny,z\n'), {"columns": ["a", "b"], "rowCount": 2})

    def test_kacisli_tirnak(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › handles escaped quotes
        self.assertEqual(csv_ust_verisi('a\n"he said ""hi"""\n'), {"columns": ["a"], "rowCount": 1})

    def test_crlf(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › supports CRLF line endings
        self.assertEqual(csv_ust_verisi("a,b\r\n1,2\r\n3,4\r\n"), {"columns": ["a", "b"], "rowCount": 2})

    def test_ozel_ayrac(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › supports a custom delimiter
        self.assertEqual(csv_ust_verisi("a;b;c\n1;2;3\n", ayrac=";"), {"columns": ["a", "b", "c"], "rowCount": 1})

    def test_basliksiz(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › synthesizes column names when hasHeader is false
        self.assertEqual(csv_ust_verisi("1,2,3\n4,5,6\n", baslikli=False),
                         {"columns": ["col_0", "col_1", "col_2"], "rowCount": 2})

    def test_bos_girdi(self):
        # DataFlow: tests/csv.test.ts › parseCsvMeta › returns empty meta for empty input
        self.assertEqual(csv_ust_verisi(""), {"columns": [], "rowCount": 0})


class TestDosyaDeposu(unittest.TestCase):
    def setUp(self):
        self.kok = tempfile.mkdtemp(prefix="atolye_dosya_")
        self.depo = DosyaDeposu(self.kok)
        self.anahtar = f"datasets/test/{time.time_ns()}-roundtrip.csv"

    def tearDown(self):
        shutil.rmtree(self.kok, ignore_errors=True)

    def test_yerel_arka_uc(self):
        # DataFlow: tests/storage.test.ts › storage (local backend) › defaults to the local backend when S3 is not configured
        self.assertEqual(self.depo.arka_uc(), "local")

    def test_gidis_donus(self):
        # DataFlow: tests/storage.test.ts › storage (local backend) › round-trips bytes through save + read
        self.depo.kaydet(self.anahtar, "a,b\n1,2\n".encode("utf-8"))
        self.assertEqual(self.depo.oku(self.anahtar).decode("utf-8"), "a,b\n1,2\n")

    def test_silme(self):
        # DataFlow: tests/storage.test.ts › storage (local backend) › deletes an object
        self.depo.kaydet(self.anahtar, b"x")
        self.depo.sil(self.anahtar)
        with self.assertRaises(OSError):
            self.depo.oku(self.anahtar)
        # Sınama eki: anahtar kökten dışarı çıkamaz (DataFlow yalnız "../" ayıklıyordu).
        with self.assertRaises(ValueError):
            self.depo.kaydet("../../disari.csv", b"x")


if __name__ == "__main__":
    unittest.main()
