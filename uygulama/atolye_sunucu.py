# -*- coding: utf-8 -*-
"""
uygulama/atolye_sunucu.py — A6 Atölye arka ucu (ADR-004).

DataFlow'un Hono + tRPC + MySQL arka ucu, aynı FastAPI sürecine (A5) taşındı; HTTP
sözleşmeleri DataFlow'unkiyle aynıdır (hasat edilen ön yüz değişmeden çalışsın diye):

- tRPC prosedürleri (auth 2, workflow 8, audit 2, dataset 4, catalog 4, feedback 3) →
  `POST /api/atolye/rpc/<grup.prosedür>` gövde `{"girdi": ...}`; hata `{"hata": {"mesaj"}}`.
  Girdi denetimi DataFlow'un zod şemalarının karşılığıdır (sınırlar, varsayılanlar, enum'lar).
- `/api/datasets/upload|{id}/download|{id}` — yerel disk (`<veri kökü>/veri/atolye/`).
- `/api/evidence/record|public-key|verify` — Ed25519 imzalı kanıt defteri (kanit_defteri.py).
- `/api/ml/suc/manifest`, `/api/ml/suc/{arac}` — çekirdeğin `arac_calistir`'ı (MCP ve
  Rehberli ile aynı boru hattı, aynı motor kilidi).
- `/api/agent/insight` — YerelAjan vekili (opsiyonel; erişilemezse 503).
- Kapsam dışı (md. 4): `/api/ml/*` (tahminci ML), `/api/science/*` (Akademik Mod), HARP
  eşitleme → tipli 503 ve nedeni.

Kimlik (md. 3): tek yerel kullanıcı (rol admin), oturum yok. Sunucu yalnız 127.0.0.1'e
bağlanır; buna ek olarak Atölye uçları geri döngü dışından gelen isteği 403 ile reddeder —
aktör her zaman yerel kullanıcıdır, kanıt defterine başkası onun adına yazamamalı.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from . import atolye_depo
from .atolye_depo import AtolyeDeposu, DosyaDeposu, csv_ust_verisi, depolama_anahtari

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATOLYE_DIST = os.path.join(KOK, "uygulama", "atolye", "dist")
MAKS_YUKLEME = 50 * 1024 * 1024          # DataFlow env.maxUploadBytes varsayılanı
VARSAYILAN_AJAN = "http://localhost:8800"  # DataFlow env.agentServiceUrl varsayılanı
YEREL_ISTEMCILER = frozenset({"127.0.0.1", "::1"})
DENETIM_LOG_EYLEMLERI = atolye_depo.DENETIM_EYLEMLERI[:12]   # audit.log'un zod enum'u
DENETIM_LOG_VARLIKLARI = atolye_depo.VARLIK_TURLERI[:5]
KAPSAM_DISI = {
    "ml": "Sunucu taraflı ML algoritmaları Sınama'da kapalı: ADR-001 MVP dışı (tahminci kara "
          "kutu ML), ADR-004 md. 4. Suç analizi düğümleri (suc_*) sunucuda çalışır.",
    "science": "Akademik Mod (Science GPT) Sınama'da kapalı: halefi Rehberli yüz ve bilim "
               "katmanıdır (ön-kayıt, hipotez seti, kategorik hüküm) — ADR-004 md. 4.",
    "harp": "HARP dış çapası Sınama'da kapsam dışı (dış sistem) — ADR-004 md. 4.",
}


class GirdiHatasi(Exception):
    """Sözleşmeye uymayan girdi (tRPC BAD_REQUEST karşılığı)."""
    durum = 400


class Bulunamadi(Exception):
    """Kayıt yok ya da kullanıcının değil (DataFlow: "... not found")."""
    durum = 404


class Yasak(Exception):
    """Yalnız yönetici (adminQuery)."""
    durum = 403


# ── zod karşılığı küçük denetleyiciler ──────────────────────────────────
def _nesne(girdi, opsiyonel=False):
    if girdi is None and opsiyonel:
        return None
    if not isinstance(girdi, dict):
        raise GirdiHatasi("girdi bir nesne olmalı")
    return girdi


def _sayi(g, ad, zorunlu=True, en_az=None, en_cok=None, tam=False, varsayilan=None):
    v = (g or {}).get(ad)
    if v is None:
        if zorunlu:
            raise GirdiHatasi(f"{ad} gerekli")
        return varsayilan
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
        raise GirdiHatasi(f"{ad} sayı olmalı")
    if tam and not float(v).is_integer():
        raise GirdiHatasi(f"{ad} tam sayı olmalı")
    if en_az is not None and v < en_az:
        raise GirdiHatasi(f"{ad} en az {en_az} olmalı")
    if en_cok is not None and v > en_cok:
        raise GirdiHatasi(f"{ad} en çok {en_cok} olmalı")
    return int(v) if float(v).is_integer() else v


def _metin(g, ad, zorunlu=True, en_az=None, en_cok=None, kirp=False):
    v = (g or {}).get(ad)
    if v is None:
        if zorunlu:
            raise GirdiHatasi(f"{ad} gerekli")
        return None
    if not isinstance(v, str):
        raise GirdiHatasi(f"{ad} metin olmalı")
    if kirp:
        v = v.strip()
    if en_az is not None and len(v) < en_az:
        raise GirdiHatasi(f"{ad} en az {en_az} karakter olmalı")
    if en_cok is not None and len(v) > en_cok:
        raise GirdiHatasi(f"{ad} en çok {en_cok} karakter olmalı")
    return v


def _secim(g, ad, secenekler, zorunlu=True, varsayilan=None):
    v = (g or {}).get(ad)
    if v is None:
        if zorunlu:
            raise GirdiHatasi(f"{ad} gerekli")
        return varsayilan
    if v not in secenekler:
        raise GirdiHatasi(f"{ad} şunlardan biri olmalı: {', '.join(secenekler)}")
    return v


def _nesne_listesi(g, ad, zorunlu=False, varsayilan=None):
    v = (g or {}).get(ad)
    if v is None:
        if zorunlu:
            raise GirdiHatasi(f"{ad} gerekli")
        return varsayilan
    if not isinstance(v, list) or not all(isinstance(x, dict) for x in v):
        raise GirdiHatasi(f"{ad} nesne listesi olmalı")
    return v


def _secili(alanlar):
    """Yalnız verilmiş (None olmayan) alanlar — zod'un `optional` çıktısı gibi."""
    return {k: v for k, v in alanlar.items() if v is not None}


# ── tRPC prosedürleri (DataFlow api/*-router.ts) ────────────────────────
class Prosedurler:
    """Her prosedür (depo, kullanıcı, girdi) → JSON yanıt; DataFlow'daki davranışla aynı."""

    def __init__(self, depo, kanit_provenans=None):
        self.depo = depo
        self.provenans = kanit_provenans

    def cagir(self, yol, kullanici, girdi):
        """`grup.prosedür` → sonuç. Bilinmeyen yol: Bulunamadi."""
        ad = "p_" + yol.replace(".", "_")
        if "." not in yol or not hasattr(self, ad):
            raise Bulunamadi(f"bilinmeyen prosedür: {yol}")
        return getattr(self, ad)(kullanici, girdi)

    @staticmethod
    def _yonetici(k):
        if k.get("role") != "admin":
            raise Yasak("yalnız yönetici")

    # auth
    def p_auth_me(self, k, g):
        return k

    def p_auth_logout(self, k, g):
        # Oturum yok (ADR-004 md. 3): çıkış bir şey silmez; ön yüz giriş sayfasına döner.
        return {"success": True}

    # workflow
    def p_workflow_list(self, k, g):
        g = _nesne(g, opsiyonel=True) or {}
        durum = _secim(g, "status", ("all",) + atolye_depo.DURUMLAR, zorunlu=False, varsayilan="all")
        _metin(g, "search", zorunlu=False)   # DataFlow da aramayı uygulamıyor (yalnız kabul)
        limit = _sayi(g, "limit", zorunlu=False, en_az=1, en_cok=100, varsayilan=20)
        offset = _sayi(g, "offset", zorunlu=False, en_az=0, varsayilan=0)
        return {"items": self.depo.akislar(k["id"], durum, limit, offset),
                "total": self.depo.akis_sayisi(k["id"], durum)}

    def p_workflow_getById(self, k, g):
        kimlik = _sayi(_nesne(g), "id")
        akis = self.depo.akis(kimlik, userId=k["id"])
        if not akis:
            raise Bulunamadi("Workflow not found")
        return akis

    def p_workflow_create(self, k, g):
        g = _nesne(g)
        girdi = {"name": _metin(g, "name", en_az=1, en_cok=255),
                 "description": _metin(g, "description", zorunlu=False),
                 "nodes": _nesne_listesi(g, "nodes", varsayilan=[]),
                 "edges": _nesne_listesi(g, "edges", varsayilan=[]),
                 "status": _secim(g, "status", ("draft", "published"), zorunlu=False, varsayilan="draft"),
                 "isPublic": _secim(g, "isPublic", ("true", "false"), zorunlu=False, varsayilan="false"),
                 "tags": _metin(g, "tags", zorunlu=False)}
        girdi = _secili(girdi)
        akis = self.depo.akis_ekle(k["id"], **girdi)
        self.depo.denetim_ekle(k["id"], "workflow_create", "workflow", str(akis["id"]),
                               f"Created workflow: {girdi['name']}")
        return {"id": akis["id"], **girdi}

    def p_workflow_update(self, k, g):
        g = _nesne(g)
        kimlik = _sayi(g, "id")
        guncel = _secili({"name": _metin(g, "name", zorunlu=False, en_az=1, en_cok=255),
                          "description": _metin(g, "description", zorunlu=False),
                          "nodes": _nesne_listesi(g, "nodes"),
                          "edges": _nesne_listesi(g, "edges"),
                          "status": _secim(g, "status", atolye_depo.DURUMLAR, zorunlu=False),
                          "isPublic": _secim(g, "isPublic", ("true", "false"), zorunlu=False),
                          "tags": _metin(g, "tags", zorunlu=False)})
        mevcut = self.depo.akis(kimlik, userId=k["id"])
        if not mevcut:
            raise Bulunamadi("Workflow not found")
        self.depo.akis_guncelle(kimlik, **guncel, version=(mevcut["version"] or 1) + 1)
        self.depo.denetim_ekle(k["id"], "workflow_update", "workflow", str(kimlik),
                               f"Updated workflow: {guncel.get('name', mevcut['name'])}")
        return {"id": kimlik, **guncel}

    def p_workflow_delete(self, k, g):
        kimlik = _sayi(_nesne(g), "id")
        mevcut = self.depo.akis(kimlik, userId=k["id"])
        if not mevcut:
            raise Bulunamadi("Workflow not found")
        self.depo.akis_sil(kimlik)
        self.depo.denetim_ekle(k["id"], "workflow_delete", "workflow", str(kimlik),
                               f"Deleted workflow: {mevcut['name']}")
        return {"success": True}

    def p_workflow_execute(self, k, g):
        g = _nesne(g)
        akis_id = _sayi(g, "workflowId")
        kosu = self.depo.kosu_ekle(akis_id, k["id"], "running",
                                   nodeCount=_sayi(g, "nodeCount", zorunlu=False),
                                   edgeCount=_sayi(g, "edgeCount", zorunlu=False))
        self.depo.denetim_ekle(k["id"], "workflow_execute", "workflow", str(akis_id),
                               f"Started execution #{kosu['id']}")
        return {"executionId": kosu["id"]}

    def p_workflow_completeExecution(self, k, g):
        g = _nesne(g)
        kosu_id = _sayi(g, "executionId")
        durum = _secim(g, "status", ("completed", "failed", "cancelled"))
        sonuclar = g.get("results")
        if sonuclar is not None and not isinstance(sonuclar, dict):
            raise GirdiHatasi("results bir nesne olmalı")
        hata = _metin(g, "error", zorunlu=False)
        bitis = atolye_depo.simdi()
        self.depo.kosu_guncelle(kosu_id, userId=k["id"], status=durum, results=sonuclar,
                                error=hata, completedAt=bitis)
        if self.provenans:
            self.provenans(kosu_id, durum, sonuclar, bitis)
        return {"success": True}

    def p_workflow_executions(self, k, g):
        g = _nesne(g)
        return {"items": self.depo.kosular(
            _sayi(g, "workflowId"), userId=k["id"],
            limit=_sayi(g, "limit", zorunlu=False, en_az=1, en_cok=50, varsayilan=10),
            offset=_sayi(g, "offset", zorunlu=False, en_az=0, varsayilan=0))}

    # audit
    def p_audit_list(self, k, g):
        g = _nesne(g, opsiyonel=True) or {}
        eylem = _metin(g, "action", zorunlu=False)
        varlik = _metin(g, "entityType", zorunlu=False)
        return {"items": self.depo.denetimler(
                    k["id"], eylem, varlik,
                    limit=_sayi(g, "limit", zorunlu=False, en_az=1, en_cok=200, varsayilan=50),
                    offset=_sayi(g, "offset", zorunlu=False, en_az=0, varsayilan=0)),
                "total": self.depo.denetim_sayisi(k["id"], eylem, varlik)}

    def p_audit_log(self, k, g):
        g = _nesne(g)
        satir = self.depo.denetim_ekle(
            k["id"], _secim(g, "action", DENETIM_LOG_EYLEMLERI),
            _secim(g, "entityType", DENETIM_LOG_VARLIKLARI),
            _metin(g, "entityId", zorunlu=False), _metin(g, "details", zorunlu=False))
        return {"id": satir["id"]}

    # dataset
    def p_dataset_list(self, k, g):
        g = _nesne(g, opsiyonel=True) or {}
        return {"items": self.depo.veri_setleri(
            k["id"], limit=_sayi(g, "limit", zorunlu=False, en_az=1, en_cok=100, varsayilan=20),
            offset=_sayi(g, "offset", zorunlu=False, en_az=0, varsayilan=0))}

    def p_dataset_create(self, k, g):
        g = _nesne(g)
        sutunlar = g.get("columns", [])
        if sutunlar is None:
            sutunlar = []
        if not isinstance(sutunlar, list) or not all(isinstance(s, str) for s in sutunlar):
            raise GirdiHatasi("columns metin listesi olmalı")
        satir = self.depo.veri_seti_ekle(
            k["id"], _metin(g, "name", en_az=1, en_cok=255), _metin(g, "filename", en_az=1, en_cok=255),
            sutunlar, _sayi(g, "rowCount", en_az=0), _sayi(g, "sizeBytes", zorunlu=False))
        return {"id": satir["id"]}

    def p_dataset_getById(self, k, g):
        satir = self.depo.veri_seti(_sayi(_nesne(g), "id"), userId=k["id"])
        if not satir:
            raise Bulunamadi("Dataset not found")
        return satir

    def p_dataset_delete(self, k, g):
        self.depo.veri_seti_sil(_sayi(_nesne(g), "id"), userId=k["id"])
        return {"success": True}

    # catalog
    def p_catalog_list(self, k, g):
        g = _nesne(g, opsiyonel=True) or {}
        return {"items": self.depo.katalog(
            limit=_sayi(g, "limit", zorunlu=False, en_az=1, en_cok=100, varsayilan=50),
            offset=_sayi(g, "offset", zorunlu=False, en_az=0, varsayilan=0))}

    def p_catalog_clone(self, k, g):
        kaynak = self.depo.akis(_sayi(_nesne(g), "id"))
        if not kaynak or kaynak["isBestPractice"] != "true":
            raise Bulunamadi("Catalog entry not found")
        yeni = self.depo.akis_ekle(k["id"], f"{kaynak['name']} (copy)", kaynak["nodes"],
                                   kaynak["edges"], kaynak["description"], "draft",
                                   tags=kaynak["tags"])
        return {"id": yeni["id"]}

    def p_catalog_promote(self, k, g):
        self._yonetici(k)
        g = _nesne(g)
        kimlik = _sayi(g, "id")
        not_ = _metin(g, "curatorNote", zorunlu=False, en_cok=2000)
        mevcut = self.depo.akis(kimlik)
        if not mevcut:
            raise Bulunamadi("Workflow not found")
        self.depo.akis_guncelle(kimlik, isBestPractice="true", curatorNote=not_,
                                curatedBy=k["id"], curatedAt=atolye_depo.simdi())
        self.depo.denetim_ekle(k["id"], "catalog_promote", "workflow", str(kimlik),
                               f'Promoted "{mevcut["name"]}" to the best-practice catalog')
        return {"success": True}

    def p_catalog_retract(self, k, g):
        self._yonetici(k)
        kimlik = _sayi(_nesne(g), "id")
        mevcut = self.depo.akis(kimlik)
        if not mevcut:
            raise Bulunamadi("Workflow not found")
        self.depo.akis_guncelle(kimlik, isBestPractice="false")
        self.depo.denetim_ekle(k["id"], "catalog_retract", "workflow", str(kimlik),
                               f'Retracted "{mevcut["name"]}" from the best-practice catalog')
        return {"success": True}

    # feedback
    def p_feedback_create(self, k, g):
        g = _nesne(g)
        girdi = _secili({"kind": _secim(g, "kind", atolye_depo.GERI_BILDIRIM_TURLERI),
                         "nodeType": _metin(g, "nodeType", zorunlu=False, en_cok=64),
                         "workflowId": _sayi(g, "workflowId", zorunlu=False),
                         "rating": _secim(g, "rating", ("up", "down"), zorunlu=False),
                         "comment": _metin(g, "comment", zorunlu=False, en_cok=4000)})
        if "rating" not in girdi and not (girdi.get("comment") or "").strip():
            raise GirdiHatasi("Provide a rating and/or a comment")
        return {"id": self.depo.geri_bildirim_ekle(k["id"], **girdi)["id"]}

    def p_feedback_list(self, k, g):
        self._yonetici(k)
        g = _nesne(g, opsiyonel=True) or {}
        return {"items": self.depo.geri_bildirimler(
            _secim(g, "kind", ("all",) + atolye_depo.GERI_BILDIRIM_TURLERI, zorunlu=False, varsayilan="all"),
            limit=_sayi(g, "limit", zorunlu=False, en_az=1, en_cok=200, varsayilan=50),
            offset=_sayi(g, "offset", zorunlu=False, en_az=0, varsayilan=0))}

    def p_feedback_summary(self, k, g):
        self._yonetici(k)
        return {"items": self.depo.geri_bildirim_ozeti()}


# ── kanıt kaydı isteği (DataFlow api/evidence.ts KayitIstegi) ─────────────
def kayit_istegi(ham):
    """zod KayitIstegi karşılığı: tanımlı alanlar denetlenir, bilinmeyenler ATILIR.

    İstemcinin gönderdiği aktör/sıra/önceki_hash gibi alanlar bu yüzden deftere giremez.
    """
    g = _nesne(ham)
    sha = r"^[0-9a-f]{64}$"
    istek = {"kanit_id": _metin(g, "kanit_id", en_az=8, en_cok=64),
             "dosya_no": _metin(g, "dosya_no", en_az=1, en_cok=100, kirp=True)}
    for ad in ("veri_sha256", "paket_sha256"):
        v = _metin(g, ad)
        if not re.match(sha, v):
            raise GirdiHatasi(f"{ad}: 64 haneli küçük harf onaltılık SHA-256")
        istek[ad] = v
    istek["satir"] = _sayi(g, "satir", en_az=0, tam=True)
    istek["sutun"] = _sayi(g, "sutun", en_az=0, tam=True)
    istek["beyan_eden"] = _metin(g, "beyan_eden", en_cok=100)
    zincir = g.get("kaynak_zinciri")
    if not isinstance(zincir, list) or len(zincir) > 50:
        raise GirdiHatasi("kaynak_zinciri en çok 50 öğelik liste olmalı")
    istek["kaynak_zinciri"] = [{"tip": _metin(_nesne(o), "tip", en_cok=60),
                                "etiket": _metin(_nesne(o), "etiket", en_cok=200)} for o in zincir]
    return istek


def _icerik_basligi(dosya_adi):
    """`attachment` başlığı: ASCII yedek ad + RFC 5987 UTF-8 ad (Türkçe ad başlığı bozmasın)."""
    yedek = "".join(c if 32 <= ord(c) < 127 and c not in '"\\' else "_" for c in dosya_adi) or "veri.csv"
    return f"attachment; filename=\"{yedek}\"; filename*=UTF-8''{urllib.parse.quote(dosya_adi)}"


def bagla(app: FastAPI, kok, arac_calistir, motor, hata_sinifi, ajan_url=None, kanit_dizini=None):
    """Atölye uçlarını ve `/atolye/` statik ön yüzünü A5 uygulamasına ekler.

    Rehberli'nin `/` bağlamasından ÖNCE çağrılmalı (Starlette rotaları sırayla eşler).

    Args:
        app: A5 FastAPI uygulaması.
        kok: depo dışı veri kökü.
        arac_calistir: çekirdeğin kamusal aracı (`sinama.arayuz.sunucu.arac_calistir`).
        motor: tek motor kilidi (A5 ile ortak — çekirdek çağrıları sırayla).
        hata_sinifi: çekirdeğin alan hatası kök sınıfı (`SucAnaliziHatasi`).
        ajan_url: YerelAjan servisi; None → SINAMA_AJAN_URL ya da DataFlow varsayılanı.
        kanit_dizini: kanıt defteri dizini; None → `<kök>/kanit`.

    Returns:
        {"depo", "kanit": {"defter"}, "dosyalar"} — testler için (defter değiştirilebilir).
    """
    from .kanit_defteri import KanitDefteri

    depo = AtolyeDeposu(os.path.join(kok, "atolye.sqlite3"))
    dosyalar = DosyaDeposu(os.path.join(kok, "veri", "atolye"))
    os.makedirs(dosyalar.kok, exist_ok=True)
    durum = {"defter": KanitDefteri(kanit_dizini or os.path.join(kok, "kanit"))}
    ajan = (ajan_url or os.environ.get("SINAMA_AJAN_URL") or VARSAYILAN_AJAN).rstrip("/")
    kullanici = depo.yerel_kullanici()

    def provenans(kosu_id, durum_, sonuclar, bitis):
        """Anlam Çekirdeği koşu kaydı (opt-in: ANLAM_PROVENANCE_FILE); akışı asla bozmaz."""
        yol = os.environ.get("ANLAM_PROVENANCE_FILE")
        if not yol:
            return
        try:
            kosu = depo.kosu(kosu_id)
            if kosu:
                with open(yol, "a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps({"kind": "dataflow_execution", "executionId": kosu_id,
                                        "workflowId": kosu["workflowId"], "status": durum_,
                                        "startedAt": kosu["startedAt"], "completedAt": bitis,
                                        "nodeResults": sonuclar}, ensure_ascii=False) + "\n")
        except OSError:
            pass

    prosedurler = Prosedurler(depo, provenans)

    def yerel_istemci(request: Request):
        """Atölye uçları yalnız bu bilgisayardan (aktör = yerel kullanıcı)."""
        if not request.client or request.client.host not in YEREL_ISTEMCILER:
            raise HTTPException(status_code=403, detail="Atölye yalnız bu bilgisayardan kullanılır (127.0.0.1)")

    r = APIRouter(dependencies=[Depends(yerel_istemci)])

    def denetim(eylem, varlik, kimlik=None, ayrinti=None):
        try:   # ikincil iz: asıl işlem bunun yüzünden düşmez (DataFlow'daki gibi)
            depo.denetim_ekle(kullanici["id"], eylem, varlik, kimlik, ayrinti)
        except Exception:   # noqa: BLE001
            pass

    # ── tRPC karşılığı ────────────────────────────────────────────────
    @r.post("/api/atolye/rpc/{yol}")
    def rpc(yol: str, govde: dict = Body(default={})):
        """`grup.prosedür` çağrısı; gövde {"girdi": ...}."""
        try:
            return prosedurler.cagir(yol, kullanici, (govde or {}).get("girdi"))
        except (GirdiHatasi, Bulunamadi, Yasak) as e:
            return JSONResponse(status_code=e.durum, content={"hata": {"mesaj": str(e)}})

    # ── veri setleri (DataFlow api/datasets-http.ts) ─────────────────────
    @r.post("/api/datasets/upload")
    async def yukle(request: Request):
        """Çok parçalı CSV yükleme: dosya + üst veri kaydı."""
        async with request.form() as form:   # geçici dosyalar blok sonunda kapanır
            dosya = form.get("file")
            if dosya is None or isinstance(dosya, str):
                return JSONResponse(status_code=400, content={"error": "A 'file' field is required"})
            veri = await dosya.read()
            dosya_adi = dosya.filename or "veri.csv"
            ad = str(form.get("name") or dosya_adi)
            ayrac = str(form.get("delimiter") or ",")
            baslikli = str(form.get("hasHeader") or "true") != "false"
        if len(veri) > MAKS_YUKLEME:
            return JSONResponse(status_code=413, content={"error": "File exceeds the maximum allowed size"})
        ust = csv_ust_verisi(veri.decode("utf-8", errors="replace"), ayrac[:1] or ",", baslikli)
        anahtar = depolama_anahtari(kullanici["id"], dosya_adi)
        dosyalar.kaydet(anahtar, veri)
        satir = depo.veri_seti_ekle(kullanici["id"], ad, dosya_adi, ust["columns"],
                                    ust["rowCount"], len(veri), storageKey=anahtar, status="ready")
        return {"id": satir["id"], "name": ad, "filename": satir["filename"], "columns": ust["columns"],
                "rowCount": ust["rowCount"], "sizeBytes": len(veri)}

    def _veri_seti(kimlik):
        try:
            kimlik = int(kimlik)
        except ValueError:
            return None, JSONResponse(status_code=400, content={"error": "Invalid id"})
        satir = depo.veri_seti(kimlik, userId=kullanici["id"])
        if not satir:
            return None, JSONResponse(status_code=404, content={"error": "Not found"})
        return satir, None

    @r.get("/api/datasets/{kimlik}/download")
    def indir(kimlik: str):
        """Kullanıcının veri setinin ham CSV'si."""
        satir, hata = _veri_seti(kimlik)
        if hata:
            return hata
        if not satir["storageKey"]:
            return JSONResponse(status_code=404, content={"error": "Not found"})
        try:
            veri = dosyalar.oku(satir["storageKey"])
        except (OSError, ValueError):
            return JSONResponse(status_code=404, content={"error": "Not found"})
        return Response(veri, media_type="text/csv",
                        headers={"content-disposition": _icerik_basligi(satir["filename"])})

    @r.delete("/api/datasets/{kimlik}")
    def sil(kimlik: str):
        """Veri seti satırı + saklanan dosya."""
        satir, hata = _veri_seti(kimlik)
        if hata:
            return hata
        if satir["storageKey"]:
            try:
                dosyalar.sil(satir["storageKey"])
            except (OSError, ValueError):
                pass   # en iyi çaba: satır yine silinir
        depo.veri_seti_sil(satir["id"])
        return {"success": True}

    # ── kanıt defteri (DataFlow api/evidence.ts) ─────────────────────────
    @r.post("/api/evidence/record")
    async def kanit_kaydet(request: Request):
        """Kayıt isteği → imzalı makbuz; aktör yerel kullanıcı (istemci beyanı değil)."""
        try:
            ham = json.loads(await request.body())
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Geçersiz JSON gövdesi"})
        try:
            istek = kayit_istegi(ham)
        except GirdiHatasi as e:
            return JSONResponse(status_code=400, content={"error": "Geçersiz kanıt kaydı", "issues": [str(e)]})
        try:
            makbuz = durum["defter"].ekle(istek, {"id": kullanici["id"], "ad": kullanici["name"]})
        except Exception:   # noqa: BLE001 — defter yazılamadıysa kayıt YOKTUR
            return JSONResponse(status_code=500, content={"error": "Kanıt defterine yazılamadı; kayıt OLUŞMADI"})
        harp = {"durum": "yapilandirilmamis"}
        denetim("evidence_record", "evidence", istek["kanit_id"],
                f"Kanıt #{makbuz['kayit']['sira']} dosya={istek['dosya_no']} satır={istek['satir']} "
                f"veri_sha256={istek['veri_sha256'][:16]}… harp={harp['durum']}")
        return {**makbuz, "harp": harp}

    @r.get("/api/evidence/public-key")
    def genel_anahtar():
        """İmza doğrulaması için genel anahtar (açık)."""
        a = durum["defter"].anahtar()
        return {"algoritma": "Ed25519", "pem": a["genel_pem"], "parmak_izi": a["parmak_izi"]}

    @r.get("/api/evidence/verify")
    def kanit_dogrula():
        """Tüm zincir: sıra, bağ, hash, imza. Dış çapa yok (HARP kapsam dışı)."""
        return {**durum["defter"].dogrula(), "harp_capa": {"durum": "yapilandirilmamis"}}

    @r.post("/api/evidence/harp-esitle")
    def harp_esitle():
        """HARP dış çapası kapsam dışı (ADR-004 md. 4)."""
        return JSONResponse(status_code=503, content={"error": KAPSAM_DISI["harp"], "detail": KAPSAM_DISI["harp"],
                                                      "kapsam_disi": "ADR-004 md. 4"})

    # ── suç analizi köprüsü (DataFlow ml-service suc_analizi_koprusu.py) ──
    @r.get("/api/ml/suc/manifest")
    def suc_manifest():
        """Araç kataloğu: ad, açıklama, JSON şema."""
        from sinama.arayuz.ortak import ARACLAR
        return [{"ad": ad, "aciklama": k["aciklama"], "sema": k["sema"]} for ad, k in sorted(ARACLAR.items())]

    @r.post("/api/ml/suc/{arac}")
    def suc_calistir(arac: str, arg: dict = Body(...)):
        """Tek araç, kapı + kanıt boru hattından; veri yalnız satır içi `satirlar`."""
        from sinama.arayuz.ortak import ARACLAR
        if arac not in ARACLAR:
            return JSONResponse(status_code=404, content={"tip": "kullanim", "mesaj": f"bilinmeyen araç: {arac}"})
        if "csv_yolu" in arg:
            return JSONResponse(status_code=400, content={
                "tip": "kullanim", "mesaj": "csv_yolu bu köprüde kapalı; veriyi 'satirlar' ile gönderin"})
        try:
            with motor:
                return arac_calistir(arac, arg)
        except hata_sinifi as e:
            tip = getattr(e, "tip", "sistem")
            durum_kodu = {"kapi": 422, "sistem": 500}.get(tip, 400)
            return JSONResponse(status_code=durum_kodu, content={
                "tip": tip, "mesaj": str(e), "oneri": getattr(e, "oneri", None)})
        except Exception as e:   # noqa: BLE001 — beklenmeyen: yine de tipli (iç ayrıntı sızmaz)
            return JSONResponse(status_code=500, content={
                "tip": "sistem", "mesaj": f"beklenmeyen hata: {type(e).__name__}"})

    @r.api_route("/api/ml/{yol:path}", methods=["GET", "POST"])
    def ml_kapali(yol: str):
        """Tahminci ML algoritmaları kapsam dışı."""
        return JSONResponse(status_code=503, content={"error": KAPSAM_DISI["ml"], "detail": KAPSAM_DISI["ml"],
                                                      "kapsam_disi": "ADR-004 md. 4"})

    @r.api_route("/api/science/{yol:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def bilim_kapali(yol: str):
        """Akademik Mod kapsam dışı."""
        return JSONResponse(status_code=503, content={"error": KAPSAM_DISI["science"],
                                                      "detail": KAPSAM_DISI["science"],
                                                      "kapsam_disi": "ADR-004 md. 4"})

    # ── ajan vekili (DataFlow api/agent-proxy.ts) ───────────────────────
    @r.post("/api/agent/insight")
    async def ajan_yorumu(request: Request):
        """Denetlenen, iletilen, yanıtı denetlenen ve denetim izine yazılan ajan yorumu."""
        try:
            ham = json.loads(await request.body())
            g = _nesne(ham)
            _metin(g, "question", zorunlu=False, en_cok=4000)
            _secim(g, "tone", ("concise", "detailed", "executive"), zorunlu=False)
            _metin(g, "language", zorunlu=False, en_cok=40)
            girdiler = _nesne_listesi(_nesne(g.get("context")), "inputs", zorunlu=True)
            if len(girdiler) > 64:
                raise GirdiHatasi("context.inputs en çok 64 öğe")
            for o in girdiler:
                _metin(o, "nodeType")
                _sayi(o, "rowCount", zorunlu=False)
                if o.get("data") is not None and not isinstance(o["data"], dict):
                    raise GirdiHatasi("data nesne ya da null olmalı")
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
        except GirdiHatasi as e:
            return JSONResponse(status_code=400, content={"error": "Invalid insight request", "issues": [str(e)]})
        basliklar = {"content-type": "application/json"}
        if os.environ.get("SINAMA_AJAN_TOKEN"):
            basliklar["x-agent-token"] = os.environ["SINAMA_AJAN_TOKEN"]
        istek = urllib.request.Request(f"{ajan}/insight", method="POST", headers=basliklar,
                                       data=json.dumps(g, ensure_ascii=False).encode("utf-8"))
        acici = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # yerel; vekil yok
        try:
            with acici.open(istek, timeout=120) as y:
                metin = y.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            ayrinti = e.read().decode("utf-8", errors="replace")[:300]
            return JSONResponse(status_code=502, content={"error": "Agent error", "upstreamStatus": e.code,
                                                          "detail": ayrinti})
        except Exception:   # noqa: BLE001 — erişilemeyen servis (bozuk adres dahil)
            return JSONResponse(status_code=503, content={"error": "Agent service unavailable", "target": ajan})
        try:
            cikti = json.loads(metin)
            if not isinstance(cikti.get("insight"), str) or ("model" in cikti and not isinstance(cikti["model"], str)):
                raise ValueError
        except (ValueError, AttributeError):
            return JSONResponse(status_code=502, content={"error": "Agent returned an unexpected response"})
        denetim("agent_insight", "node", None,
                f"Agent insight: {len(girdiler)} input(s), model={cikti.get('model') or '?'}")
        return {"insight": cikti["insight"], **({"model": cikti["model"]} if "model" in cikti else {})}

    app.include_router(r)

    @app.get("/api/dev-login")
    def dev_login():
        """Oturum yok (ADR-004 md. 3): giriş düğmesi doğrudan Atölye'ye döner."""
        return RedirectResponse("/atolye/", status_code=302)

    # ── /atolye/ statik ön yüz (SPA geri dönüşlü) ───────────────────────
    @app.get("/atolye", include_in_schema=False)
    def atolye_kok():
        return RedirectResponse("/atolye/", status_code=307)

    @app.get("/atolye/{yol:path}", include_in_schema=False)
    def atolye(yol: str):
        """Derlenmiş Atölye; bilinmeyen yol → index.html (istemci yönlendirmesi)."""
        dist = os.path.realpath(ATOLYE_DIST)
        index = os.path.join(dist, "index.html")
        if not os.path.isfile(index):
            return JSONResponse(status_code=503, content={
                "durum": "hazir", "not": "Atölye derlenmemiş: uygulama/atolye içinde npm run build"})
        hedef = os.path.realpath(os.path.join(dist, yol))
        if yol and os.path.commonpath([hedef, dist]) == dist and os.path.isfile(hedef):
            return FileResponse(hedef)
        if yol.startswith("assets/"):
            return JSONResponse(status_code=404, content={"error": "Not Found"})
        return FileResponse(index)

    return {"depo": depo, "kanit": durum, "dosyalar": dosyalar}
