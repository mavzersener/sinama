# -*- coding: utf-8 -*-
"""
uygulama/atolye_depo.py — Atölye kalıcılığı (A6, ADR-004 md. 2).

DataFlow'un MySQL şemasının (db/schema.ts) SQLite karşılığı — users, workflows,
executions, audit_logs, datasets, feedback; alan adları ve enum değerleri BİREBİR —
ve yükleme ucunun iki yardımcısı: CSV üst veri ayrıştırıcısı (api/lib/csv.ts) ile yerel
dosya deposu (api/lib/storage.ts'in yerel arka ucu; S3 yok).

Yalnız standart kitaplık. Tarihler ISO-8601 UTC, milisaniyeli ("…Z") — DataFlow'da
superjson Date'i bu biçimde taşıyordu, ön yüz `new Date(...)` ile okur. JSON sütunları
(nodes, edges, results, columns) metin olarak saklanır, çözülüp döner. Enum'lar CHECK
kısıtıyla korunur: geçersiz değer sessizce yazılmaz (sqlite3.IntegrityError).
"""
import datetime
import json
import os
import re
import secrets
import sqlite3
import threading

DURUMLAR = ("draft", "published", "archived")
KOSU_DURUMLARI = ("running", "completed", "failed", "cancelled")
DENETIM_EYLEMLERI = (
    "workflow_create", "workflow_update", "workflow_delete", "workflow_execute",
    "workflow_publish", "node_add", "node_delete", "node_config", "connect", "disconnect",
    "user_login", "user_logout", "agent_insight", "catalog_promote", "catalog_retract",
    "evidence_record", "evidence_harp_sync")
VARLIK_TURLERI = ("workflow", "node", "edge", "execution", "user", "evidence")
VERI_SETI_DURUMLARI = ("uploading", "ready", "processing", "error")
GERI_BILDIRIM_TURLERI = ("suggestion", "node_result", "general")
# ADR-004 md. 3: tek yerel kullanıcı, oturum yok.
YEREL_KULLANICI = {"unionId": "sinama-yerel", "name": "Yerel analist", "email": None,
                   "avatar": None, "role": "admin"}


def _icinde(degerler):
    return "(" + ",".join(f"'{d}'" for d in degerler) + ")"


SEMA = f"""
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT, unionId TEXT NOT NULL UNIQUE, name TEXT, email TEXT,
  avatar TEXT, role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')),
  createdAt TEXT NOT NULL, updatedAt TEXT NOT NULL, lastSignInAt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS workflows (
  id INTEGER PRIMARY KEY AUTOINCREMENT, userId INTEGER NOT NULL, name TEXT NOT NULL,
  description TEXT, nodes TEXT NOT NULL, edges TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN {_icinde(DURUMLAR)}),
  isPublic TEXT NOT NULL DEFAULT 'false' CHECK (isPublic IN ('true','false')),
  version INTEGER NOT NULL DEFAULT 1, tags TEXT,
  isBestPractice TEXT NOT NULL DEFAULT 'false' CHECK (isBestPractice IN ('true','false')),
  curatorNote TEXT, curatedBy INTEGER, curatedAt TEXT,
  createdAt TEXT NOT NULL, updatedAt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS executions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, workflowId INTEGER NOT NULL, userId INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN {_icinde(KOSU_DURUMLARI)}),
  results TEXT, error TEXT, nodeCount INTEGER, edgeCount INTEGER,
  startedAt TEXT NOT NULL, completedAt TEXT);
CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, userId INTEGER NOT NULL,
  action TEXT NOT NULL CHECK (action IN {_icinde(DENETIM_EYLEMLERI)}),
  entityType TEXT NOT NULL CHECK (entityType IN {_icinde(VARLIK_TURLERI)}),
  entityId TEXT, details TEXT, ipAddress TEXT, userAgent TEXT, createdAt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS datasets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, userId INTEGER NOT NULL, name TEXT NOT NULL,
  filename TEXT NOT NULL, storageKey TEXT, columns TEXT NOT NULL, rowCount INTEGER NOT NULL,
  sizeBytes INTEGER,
  status TEXT NOT NULL DEFAULT 'ready' CHECK (status IN {_icinde(VERI_SETI_DURUMLARI)}),
  createdAt TEXT NOT NULL, updatedAt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT, userId INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN {_icinde(GERI_BILDIRIM_TURLERI)}),
  nodeType TEXT, workflowId INTEGER, rating TEXT CHECK (rating IN ('up','down')),
  comment TEXT, createdAt TEXT NOT NULL);
"""
_JSON_ALANLARI = {"workflows": ("nodes", "edges"), "executions": ("results",),
                  "datasets": ("columns",)}


def simdi():
    """Şimdiki an, JS `Date.toISOString()` biçiminde (UTC, milisaniye, Z)."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds") \
        .replace("+00:00", "Z")


def iso(deger):
    """datetime/date → ISO-8601 UTC metin; metin aynen; None aynen."""
    if deger is None or isinstance(deger, str):
        return deger
    if isinstance(deger, datetime.datetime):
        if deger.tzinfo is None:
            deger = deger.replace(tzinfo=datetime.timezone.utc)
        return deger.astimezone(datetime.timezone.utc).isoformat(timespec="milliseconds") \
            .replace("+00:00", "Z")
    if isinstance(deger, datetime.date):
        return f"{deger.isoformat()}T00:00:00.000Z"
    raise TypeError(f"tarih değil: {type(deger).__name__}")


class AtolyeDeposu:
    """DataFlow tablolarının SQLite deposu; tek bağlantı, kilitle sıralı yazım."""

    def __init__(self, yol):
        self.yol = yol
        if yol != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
        self._db = sqlite3.connect(yol, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._kilit = threading.Lock()
        self._son_an = ""
        with self._kilit:
            self._db.executescript(SEMA)
            self._db.commit()
        self._yerel = self._yerel_kullaniciyi_kur()

    def kapat(self):
        """Bağlantıyı kapatır."""
        self._db.close()

    # ── iç yardımcılar ──────────────────────────────────────────────────
    def _an(self):
        """Kesin artan an: aynı milisaniyedeki iki yazım sıralamayı bozmasın."""
        an = simdi()
        if an <= self._son_an:
            t = datetime.datetime.fromisoformat(self._son_an.replace("Z", "+00:00"))
            an = iso(t + datetime.timedelta(milliseconds=1))
        self._son_an = an
        return an

    def _satir(self, tablo, r):
        if r is None:
            return None
        d = dict(r)
        for alan in _JSON_ALANLARI.get(tablo, ()):
            if d.get(alan) is not None:
                d[alan] = json.loads(d[alan])
        return d

    def _ekle(self, tablo, degerler):
        alanlar = list(degerler)
        with self._kilit:
            imlec = self._db.execute(
                f"INSERT INTO {tablo} ({','.join(alanlar)}) VALUES ({','.join('?' * len(alanlar))})",
                [degerler[a] for a in alanlar])
            self._db.commit()
            kimlik = imlec.lastrowid
        return self._bul(tablo, kimlik)

    def _bul(self, tablo, kimlik, **kosul):
        sql, arg = f"SELECT * FROM {tablo} WHERE id = ?", [kimlik]
        for alan, deger in kosul.items():
            if deger is not None:
                sql += f" AND {alan} = ?"
                arg.append(deger)
        return self._satir(tablo, self._db.execute(sql, arg).fetchone())

    def _liste(self, tablo, kosul, sira, limit=None, offset=0):
        sql, arg = f"SELECT * FROM {tablo}", []
        if kosul:
            sql += " WHERE " + " AND ".join(f"{a} = ?" for a in kosul)
            arg = list(kosul.values())
        sql += f" ORDER BY {sira}, id DESC"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            arg += [int(limit), int(offset or 0)]
        return [self._satir(tablo, r) for r in self._db.execute(sql, arg).fetchall()]

    def _say(self, tablo, kosul=None):
        sql, arg = f"SELECT count(*) FROM {tablo}", []
        if kosul:
            sql += " WHERE " + " AND ".join(f"{a} = ?" for a in kosul)
            arg = list(kosul.values())
        return self._db.execute(sql, arg).fetchone()[0]

    def _guncelle(self, tablo, kimlik, alanlar, **kosul):
        if not alanlar:
            return 0
        alanlar = {a: (json.dumps(v, ensure_ascii=False) if a in _JSON_ALANLARI.get(tablo, ())
                       and v is not None else v) for a, v in alanlar.items()}
        sql = f"UPDATE {tablo} SET " + ", ".join(f"{a} = ?" for a in alanlar) + " WHERE id = ?"
        arg = list(alanlar.values()) + [kimlik]
        for alan, deger in kosul.items():
            if deger is not None:
                sql += f" AND {alan} = ?"
                arg.append(deger)
        with self._kilit:
            n = self._db.execute(sql, arg).rowcount
            self._db.commit()
        return n

    def _sil(self, tablo, kimlik, **kosul):
        sql, arg = f"DELETE FROM {tablo} WHERE id = ?", [kimlik]
        for alan, deger in kosul.items():
            if deger is not None:
                sql += f" AND {alan} = ?"
                arg.append(deger)
        with self._kilit:
            n = self._db.execute(sql, arg).rowcount
            self._db.commit()
        return n

    # ── kullanıcı ───────────────────────────────────────────────────────
    def _yerel_kullaniciyi_kur(self):
        r = self._db.execute("SELECT * FROM users WHERE unionId = ?",
                             (YEREL_KULLANICI["unionId"],)).fetchone()
        if r is not None:
            return dict(r)
        an = self._an()
        return self._ekle("users", {**YEREL_KULLANICI, "createdAt": an, "updatedAt": an,
                                    "lastSignInAt": an})

    def yerel_kullanici(self):
        """ADR-004 md. 3: Atölye'nin tek kullanıcısı (rol admin)."""
        return dict(self._yerel)

    # ── workflows ───────────────────────────────────────────────────────
    def akis_ekle(self, userId, name, nodes=(), edges=(), description=None, status="draft",
                  isPublic="false", version=1, tags=None):
        """Yeni akış satırı (DataFlow insert workflows)."""
        an = self._an()
        return self._ekle("workflows", {
            "userId": userId, "name": name, "description": description,
            "nodes": json.dumps(list(nodes), ensure_ascii=False),
            "edges": json.dumps(list(edges), ensure_ascii=False), "status": status,
            "isPublic": isPublic, "version": version, "tags": tags, "createdAt": an,
            "updatedAt": an})

    def akis(self, kimlik, userId=None):
        """Akış (userId verilirse sahiplik koşuluyla); yoksa None."""
        return self._bul("workflows", kimlik, userId=userId)

    def akislar(self, userId, status="all", limit=None, offset=0):
        """Kullanıcının akışları, updatedAt azalan."""
        kosul = {"userId": userId, **({"status": status} if status and status != "all" else {})}
        return self._liste("workflows", kosul, "updatedAt DESC", limit, offset)

    def akis_sayisi(self, userId=None, status="all"):
        """Akış sayısı (userId None → tümü)."""
        kosul = {**({"userId": userId} if userId is not None else {}),
                 **({"status": status} if status and status != "all" else {})}
        return self._say("workflows", kosul)

    def akis_guncelle(self, kimlik, **alanlar):
        """Alanları günceller; updatedAt her değişiklikte yenilenir ($onUpdate)."""
        return self._guncelle("workflows", kimlik, {**alanlar, "updatedAt": self._an()})

    def akis_sil(self, kimlik, userId=None):
        """Akışı siler (userId verilirse yalnız sahibininkini)."""
        return self._sil("workflows", kimlik, userId=userId)

    def katalog(self, limit=None, offset=0):
        """İyi uygulama kataloğu: isBestPractice='true', curatedAt azalan."""
        return self._liste("workflows", {"isBestPractice": "true"}, "curatedAt DESC", limit, offset)

    # ── executions ──────────────────────────────────────────────────────
    def kosu_ekle(self, workflowId, userId, status="running", nodeCount=None, edgeCount=None,
                  startedAt=None, completedAt=None, results=None, error=None):
        """Koşu kaydı (DataFlow insert executions)."""
        return self._ekle("executions", {
            "workflowId": workflowId, "userId": userId, "status": status,
            "results": None if results is None else json.dumps(results, ensure_ascii=False),
            "error": error, "nodeCount": nodeCount, "edgeCount": edgeCount,
            "startedAt": iso(startedAt) or self._an(), "completedAt": iso(completedAt)})

    def kosu_guncelle(self, kimlik, userId=None, **alanlar):
        """Koşuyu günceller (userId verilirse sahiplik koşuluyla)."""
        if "completedAt" in alanlar:
            alanlar["completedAt"] = iso(alanlar["completedAt"])
        return self._guncelle("executions", kimlik, alanlar, userId=userId)

    def kosu(self, kimlik):
        """Koşu satırı ya da None."""
        return self._bul("executions", kimlik)

    def kosular(self, workflowId, userId=None, limit=None, offset=0):
        """Akışın koşuları, startedAt azalan."""
        kosul = {"workflowId": workflowId, **({"userId": userId} if userId is not None else {})}
        return self._liste("executions", kosul, "startedAt DESC", limit, offset)

    def kosu_sayisi(self):
        """Toplam koşu sayısı."""
        return self._say("executions")

    # ── audit_logs ──────────────────────────────────────────────────────
    def denetim_ekle(self, userId, action, entityType, entityId=None, details=None,
                     createdAt=None, ipAddress=None, userAgent=None):
        """Denetim izi satırı."""
        return self._ekle("audit_logs", {
            "userId": userId, "action": action, "entityType": entityType, "entityId": entityId,
            "details": details, "ipAddress": ipAddress, "userAgent": userAgent,
            "createdAt": iso(createdAt) or self._an()})

    def denetimler(self, userId, action=None, entityType=None, limit=None, offset=0):
        """Kullanıcının denetim izi, createdAt azalan."""
        kosul = {"userId": userId, **({"action": action} if action else {}),
                 **({"entityType": entityType} if entityType else {})}
        return self._liste("audit_logs", kosul, "createdAt DESC", limit, offset)

    def denetim_sayisi(self, userId=None, action=None, entityType=None):
        """Denetim satırı sayısı (koşullar opsiyonel)."""
        kosul = {**({"userId": userId} if userId is not None else {}),
                 **({"action": action} if action else {}),
                 **({"entityType": entityType} if entityType else {})}
        return self._say("audit_logs", kosul)

    # ── datasets ────────────────────────────────────────────────────────
    def veri_seti_ekle(self, userId, name, filename, columns=(), rowCount=0, sizeBytes=None,
                       storageKey=None, status="ready"):
        """Veri seti üst verisi."""
        an = self._an()
        return self._ekle("datasets", {
            "userId": userId, "name": name, "filename": filename, "storageKey": storageKey,
            "columns": json.dumps(list(columns), ensure_ascii=False), "rowCount": rowCount,
            "sizeBytes": sizeBytes, "status": status, "createdAt": an, "updatedAt": an})

    def veri_seti(self, kimlik, userId=None):
        """Veri seti (userId verilirse sahiplik koşuluyla) ya da None."""
        return self._bul("datasets", kimlik, userId=userId)

    def veri_setleri(self, userId, limit=None, offset=0):
        """Kullanıcının veri setleri, createdAt azalan."""
        return self._liste("datasets", {"userId": userId}, "createdAt DESC", limit, offset)

    def veri_seti_sil(self, kimlik, userId=None):
        """Veri seti satırını siler."""
        return self._sil("datasets", kimlik, userId=userId)

    def veri_seti_sayisi(self):
        """Toplam veri seti sayısı."""
        return self._say("datasets")

    # ── feedback ────────────────────────────────────────────────────────
    def geri_bildirim_ekle(self, userId, kind, nodeType=None, workflowId=None, rating=None,
                           comment=None):
        """Açık kullanıcı geri bildirimi."""
        return self._ekle("feedback", {
            "userId": userId, "kind": kind, "nodeType": nodeType, "workflowId": workflowId,
            "rating": rating, "comment": comment, "createdAt": self._an()})

    def geri_bildirimler(self, kind="all", limit=None, offset=0):
        """Ham geri bildirim listesi, createdAt azalan."""
        kosul = {"kind": kind} if kind and kind != "all" else {}
        return self._liste("feedback", kosul, "createdAt DESC", limit, offset)

    def geri_bildirim_ozeti(self):
        """nodeType başına up/down sayıları (DataFlow feedback.summary)."""
        ozet = {}
        for r in self._db.execute("SELECT nodeType, rating, count(*) AS n FROM feedback "
                                  "WHERE nodeType IS NOT NULL GROUP BY nodeType, rating"):
            girdi = ozet.setdefault(r["nodeType"], {"up": 0, "down": 0})
            if r["rating"] in ("up", "down"):
                girdi[r["rating"]] += r["n"]
        return [{"nodeType": t, **s} for t, s in ozet.items()]


# ── CSV üst verisi (DataFlow api/lib/csv.ts'den birebir taşındı) ─────────
def _kayit_ayristir(metin, bas, ayrac):
    """`bas`tan başlayan tek CSV kaydı; tırnaklı alanlar, "" kaçışı, CRLF."""
    alanlar, alan, i, tirnakta = [], [], bas, False
    while i < len(metin):
        ch = metin[i]
        if tirnakta:
            if ch == '"':
                if i + 1 < len(metin) and metin[i + 1] == '"':
                    alan.append('"')
                    i += 2
                    continue
                tirnakta = False
                i += 1
                continue
            alan.append(ch)
            i += 1
            continue
        if ch == '"':
            tirnakta = True
            i += 1
            continue
        if ch == ayrac:
            alanlar.append("".join(alan))
            alan = []
            i += 1
            continue
        if ch in ("\n", "\r"):
            if ch == "\r" and i + 1 < len(metin) and metin[i + 1] == "\n":
                i += 1
            i += 1
            alanlar.append("".join(alan))
            return alanlar, i
        alan.append(ch)
        i += 1
    alanlar.append("".join(alan))
    return alanlar, i


def csv_ust_verisi(metin, ayrac=",", baslikli=True):
    """Başlık sütunları ve satır sayısı: {"columns": [...], "rowCount": n}."""
    if len(metin) == 0:
        return {"columns": [], "rowCount": 0}
    ilk, imlec = _kayit_ayristir(metin, 0, ayrac)
    if baslikli:
        sutunlar = [re.sub(r'^"|"$', "", h.strip()) or f"col_{i}" for i, h in enumerate(ilk)]
    else:
        sutunlar = [f"col_{i}" for i in range(len(ilk))]
    satir = 0 if baslikli else 1
    while imlec < len(metin):
        alanlar, imlec = _kayit_ayristir(metin, imlec, ayrac)
        if not (len(alanlar) == 1 and alanlar[0].strip() == ""):   # boş satırlar sayılmaz
            satir += 1
    return {"columns": sutunlar, "rowCount": satir}


# ── yerel dosya deposu (api/lib/storage.ts, yerel arka uç) ───────────────
class DosyaDeposu:
    """Yüklenen veri setleri `kok` altında; anahtar kökten dışarı çıkamaz."""

    def __init__(self, kok):
        self.kok = os.path.realpath(kok)

    def arka_uc(self):
        """DataFlow storageBackend(): Sınama'da her zaman yerel disk."""
        return "local"

    def _yol(self, anahtar):
        yol = os.path.realpath(os.path.join(self.kok, anahtar))
        if os.path.commonpath([yol, self.kok]) != self.kok or yol == self.kok:
            raise ValueError(f"geçersiz depolama anahtarı: {anahtar}")
        return yol

    def kaydet(self, anahtar, veri):
        """Baytları yazar (dizinleri kurar)."""
        yol = self._yol(anahtar)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "wb") as f:
            f.write(veri)

    def oku(self, anahtar):
        """Baytları okur; yoksa FileNotFoundError."""
        with open(self._yol(anahtar), "rb") as f:
            return f.read()

    def sil(self, anahtar):
        """Dosyayı siler (yoksa sessiz — DataFlow `rm force`)."""
        try:
            os.remove(self._yol(anahtar))
        except FileNotFoundError:
            pass


def depolama_anahtari(kullanici_id, dosya_adi):
    """`datasets/<uid>/<rastgele>-<güvenli ad>` (DataFlow nanoid + safeName)."""
    guvenli = re.sub(r"[^\w.-]+", "_", dosya_adi, flags=re.ASCII)
    return f"datasets/{kullanici_id}/{secrets.token_urlsafe(16)[:21]}-{guvenli}"
