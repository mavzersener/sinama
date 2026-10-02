# -*- coding: utf-8 -*-
"""
uygulama/kanit_defteri.py — Atölye kanıt defteri (A6, ADR-004 md. 2).

DataFlow'un `api/lib/kanitDefteri.ts`'inin Python karşılığı; biçim BİREBİR
(`dataflow.kanit-defteri/1`): yalnız-ekle JSONL, her satır bir makbuz
{kayit, imza, anahtar_parmak_izi}. kayit.kayit_hash, kayit_hash hariç kanonik içeriğin
(RFC 8785) SHA-256'sı; onceki_hash bir önceki kaydın kayit_hash'i (ilk kayıtta 64 sıfır).
İmza Ed25519, kayit_hash'in UTF-8 baytları üzerine; parmak izi genel anahtarın SPKI DER
baytlarının SHA-256'sı. Kanonik biçim DataFlow'un kendi bağımsız doğrulayıcısından
(`atolye/scripts/kanit_dogrula.py`, hasat) alınır — iki yazım değil, tek tanım.

Sınır (DataFlow'daki gibi, dürüstçe): defter yerel dosyadır; dosyaya yazabilen biri
zinciri baştan üretebilir ama imzalayamaz (özel anahtar ayrı dosyada, 0600). Dış çapa
(HARP) Sınama'da kapsam dışı (ADR-004 md. 4).
"""
import base64
import datetime
import hashlib
import importlib.util
import json
import os
import threading

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, NoEncryption, PrivateFormat, PublicFormat, load_pem_private_key, load_pem_public_key)

_DOGRULAYICI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atolye", "scripts",
                            "kanit_dogrula.py")
_spec = importlib.util.spec_from_file_location("kanit_dogrula", _DOGRULAYICI)
kanit_dogrula = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kanit_dogrula)

kanonik = kanit_dogrula.kanonik
BASLANGIC_HASH = kanit_dogrula.BASLANGIC_HASH
DEFTER_SEMASI = kanit_dogrula.DEFTER_SEMASI


def sha256_hex(metin):
    """UTF-8 metnin SHA-256'sı (onaltılık)."""
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def kayit_hash_girdisi(kayit):
    """Zincir hash'inin girdisi: kayit_hash alanı hariç kanonik içerik."""
    return kanonik({a: v for a, v in kayit.items() if a != "kayit_hash"})


def parmak_izi(genel):
    """Genel anahtarın SPKI DER baytlarının SHA-256'sı."""
    return hashlib.sha256(genel.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)).hexdigest()


def satirlari_dogrula(satirlar, genel):
    """Makbuz satırlarının tüm zinciri: şema, sıra, bağ, hash, imza. Tespit eder; önlemez.

    Args:
        satirlar: JSONL'in boş olmayan satırları.
        genel: Ed25519 genel anahtarı (cryptography nesnesi).

    Returns:
        {gecerli, kayit_sayisi, son_hash, hatalar: [{sira, satir, neden}]} — DataFlow
        `dogrula()` ile aynı alanlar ve aynı neden metinleri.
    """
    beklenen_iz = parmak_izi(genel)
    hatalar, onceki, beklenen_sira = [], BASLANGIC_HASH, 1
    for i, s in enumerate(satirlar, 1):
        try:
            m = json.loads(s)
            k = m["kayit"]
            if not isinstance(k, dict):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            hatalar.append({"sira": None, "satir": i, "neden": "satır JSON değil"})
            continue
        sira = k.get("sira")
        if k.get("sema") != DEFTER_SEMASI:
            hatalar.append({"sira": sira, "satir": i, "neden": f"bilinmeyen şema {k.get('sema')}"})
        if sira != beklenen_sira:
            hatalar.append({"sira": sira, "satir": i, "neden": f"sıra {beklenen_sira} bekleniyordu"})
        if k.get("onceki_hash") != onceki:
            hatalar.append({"sira": sira, "satir": i, "neden": "önceki hash zinciri kopuk"})
        try:
            hash_tutar = sha256_hex(kayit_hash_girdisi(k)) == k.get("kayit_hash")
        except (TypeError, ValueError):
            hash_tutar = False
        if not hash_tutar:
            hatalar.append({"sira": sira, "satir": i,
                            "neden": "kayıt içeriği hash'iyle uyuşmuyor (değiştirilmiş)"})
        if m.get("anahtar_parmak_izi") != beklenen_iz:
            hatalar.append({"sira": sira, "satir": i,
                            "neden": "imza başka bir anahtarla (parmak izi farklı)"})
        else:
            try:
                genel.verify(base64.b64decode(m.get("imza") or ""),
                             str(k.get("kayit_hash")).encode("utf-8"))
            except (InvalidSignature, ValueError, TypeError):
                hatalar.append({"sira": sira, "satir": i, "neden": "imza geçersiz"})
        onceki = k.get("kayit_hash")
        beklenen_sira = (sira if isinstance(sira, int) else 0) + 1
    return {"gecerli": not hatalar, "kayit_sayisi": len(satirlar), "son_hash": onceki,
            "hatalar": hatalar}


class KanitDefteri:
    """`dizin`/defter.jsonl + imza_anahtari.pem (0600) + imza_anahtari.pub.pem."""

    def __init__(self, dizin):
        self.dizin = dizin
        self.defter_yolu = os.path.join(dizin, "defter.jsonl")
        self.ozel_yolu = os.path.join(dizin, "imza_anahtari.pem")
        self.genel_yolu = os.path.join(dizin, "imza_anahtari.pub.pem")
        self._anahtar = None
        self._kilit = threading.Lock()

    def anahtar(self):
        """Anahtar çifti: varsa yüklenir, yoksa üretilir (özel anahtar 0600, üzerine yazılmaz).

        Returns:
            {"ozel", "genel", "genel_pem", "parmak_izi"}.
        """
        if self._anahtar:
            return self._anahtar
        os.makedirs(self.dizin, exist_ok=True)
        if not os.path.exists(self.ozel_yolu):
            pem = Ed25519PrivateKey.generate().private_bytes(Encoding.PEM, PrivateFormat.PKCS8,
                                                             NoEncryption())
            try:   # O_EXCL: yarışta ikinci üretici mevcut anahtarın üzerine YAZAMAZ (DataFlow "wx")
                fd = os.open(self.ozel_yolu, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | getattr(os, "O_BINARY", 0), 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(pem)
            except FileExistsError:
                pass
        with open(self.ozel_yolu, "rb") as f:
            ozel = load_pem_private_key(f.read(), password=None)
        genel = ozel.public_key()
        genel_pem = genel.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("ascii")
        with open(self.genel_yolu, "w", encoding="ascii", newline="\n") as f:
            f.write(genel_pem)
        self._anahtar = {"ozel": ozel, "genel": genel, "genel_pem": genel_pem,
                         "parmak_izi": parmak_izi(genel)}
        return self._anahtar

    def _satirlar(self):
        try:
            with open(self.defter_yolu, encoding="utf-8", newline="") as f:
                return [s for s in f.read().split("\n") if s.strip()]
        except FileNotFoundError:
            return []

    def makbuzlar(self):
        """Çözümlenebilir makbuzlar (sırayla); bozuk satır atlanır — raporlamak dogrula()'nın işi."""
        sonuc = []
        for s in self._satirlar():
            try:
                m = json.loads(s)
            except ValueError:
                continue
            if isinstance(m, dict) and isinstance(m.get("kayit"), dict) \
                    and isinstance(m["kayit"].get("sira"), int):
                sonuc.append(m)
        return sonuc

    def ekle(self, istek, aktor):
        """Kaydı zincire ekler; eşzamanlı çağrılar sıraya girer. Hata çağırana yayılır.

        Args:
            istek: doğrulanmış kayıt isteği (KayitIstegi alanları).
            aktor: {"id", "ad"} — oturumdan (Sınama'da yerel kullanıcı), istemciden DEĞİL.

        Returns:
            makbuz {kayit, imza, anahtar_parmak_izi}.

        Raises:
            ValueError: son kayıt kendi hash'iyle tutarsız (bozulmuş zincire eklenmez).
        """
        with self._kilit:
            a = self.anahtar()
            satirlar = self._satirlar()
            son = json.loads(satirlar[-1]) if satirlar else None
            if son is not None and sha256_hex(kayit_hash_girdisi(son["kayit"])) != son["kayit"]["kayit_hash"]:
                raise ValueError("kanıt defterinin son kaydı değiştirilmiş; yeni kayıt eklenmeden "
                                 "önce defter incelenmeli")
            govde = {**istek, "sema": DEFTER_SEMASI,
                     "sira": son["kayit"]["sira"] + 1 if son else 1,
                     "sunucu_zamani": datetime.datetime.now(datetime.timezone.utc)
                     .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                     "aktor": aktor,
                     "onceki_hash": son["kayit"]["kayit_hash"] if son else BASLANGIC_HASH}
            kayit = {**govde, "kayit_hash": sha256_hex(kanonik(govde))}
            makbuz = {"kayit": kayit,
                      "imza": base64.b64encode(a["ozel"].sign(kayit["kayit_hash"].encode("utf-8"))).decode("ascii"),
                      "anahtar_parmak_izi": a["parmak_izi"]}
            with open(self.defter_yolu, "ab") as f:   # ikili kip: Windows'ta CRLF'e çevrilmez
                f.write((kanonik(makbuz) + "\n").encode("utf-8"))
                f.flush()
                os.fsync(f.fileno())
            return makbuz

    def dogrula(self):
        """Tüm zinciri bu defterin anahtarıyla doğrular."""
        return satirlari_dogrula(self._satirlar(), self.anahtar()["genel"])


def genel_anahtar_yukle(pem):
    """PEM metninden Ed25519 genel anahtarı."""
    return load_pem_public_key(pem.encode("ascii") if isinstance(pem, str) else pem)
