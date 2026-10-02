#!/usr/bin/env python3
"""DataFlow kanıt paketi doğrulayıcısı (dataflow.kanit/1) — DataFlow'dan BAĞIMSIZ.

Kullanım:
    python kanit_dogrula.py PAKET.json --genel-anahtar imza_anahtari.pub.pem [--defter defter.jsonl]

Denetler:
  1. veri_sha256  = SHA-256(RFC 8785 kanonik JSON(paket.veri))   — verinin TAMAMI
  2. paket_sha256 = SHA-256(kanonik(paket))
  3. makbuz: kayıt paketi gösteriyor mu (kanıt_id, dosya_no, iki hash),
     kayit_hash kaydın kanonik içeriğiyle uyuşuyor mu, Ed25519 imzası genel
     anahtarla geçerli mi, anahtar parmak izi eşleşiyor mu
  4. --defter verilirse: tüm zincir (sıra, önceki_hash, kayıt hash'i, imza) ve
     makbuzun defterde aynı sırada/hash'le bulunması

Çıkış kodu: 0 = tüm denetimler geçti; 1 = en az bir denetim BAŞARISIZ
(kurcalama belirtisi); 2 = eksik doğrulama (KAYITSIZ paket, genel anahtar ya
da `cryptography` paketi yok).

Kanonik biçim JS tarafıyla (contracts/kanit.ts) bayt bayt aynıdır: anahtarlar
UTF-16 kod birimi sırasıyla, ayraçsız boşluk, sayılar ECMAScript
Number→String kuralıyla (Python json.dumps 1.0'ı "1.0" yazar, JS "1" — bu
yüzden json.dumps DOĞRUDAN kullanılamaz).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import sys
from decimal import Decimal

BASLANGIC_HASH = "0" * 64
DEFTER_SEMASI = "dataflow.kanit-defteri/1"
KANIT_SEMASI = "dataflow.kanit/1"


def es_sayi(x) -> str:
    """ECMAScript Number::toString (RFC 8785 §3.2.2.3)."""
    if isinstance(x, bool):
        raise TypeError("bool sayı değildir")
    if isinstance(x, int):
        x = float(x)
    if not math.isfinite(x):
        raise ValueError(f"sonlu olmayan sayı: {x}")
    if x == 0:
        return "0"
    if x < 0:
        return "-" + es_sayi(-x)
    # repr: en kısa gidiş-dönüş basamakları; Decimal ile basamak + üs.
    isaret, basamaklar, us = Decimal(repr(x)).as_tuple()
    b = list(basamaklar)
    while len(b) > 1 and b[-1] == 0:
        b.pop()
        us += 1
    while len(b) > 1 and b[0] == 0:
        b.pop(0)
    s = "".join(map(str, b))
    k = len(s)
    n = k + us  # x = 0.s × 10^n  ⇔  s × 10^(n-k)
    if k <= n <= 21:
        return s + "0" * (n - k)
    if 0 < n <= 21:
        return s[:n] + "." + s[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + s
    e = n - 1
    us_metni = ("+" if e >= 0 else "-") + str(abs(e))
    return (s if k == 1 else s[0] + "." + s[1:]) + "e" + us_metni


def kanonik(deger) -> str:
    """RFC 8785 (JCS) kanonik JSON."""
    if deger is None:
        return "null"
    if deger is True:
        return "true"
    if deger is False:
        return "false"
    if isinstance(deger, (int, float)):
        return es_sayi(deger)
    if isinstance(deger, str):
        return json.dumps(deger, ensure_ascii=False)
    if isinstance(deger, list):
        return "[" + ",".join(kanonik(v) for v in deger) + "]"
    if isinstance(deger, dict):
        anahtarlar = sorted(deger, key=lambda a: a.encode("utf-16-be"))
        return "{" + ",".join(json.dumps(a, ensure_ascii=False) + ":" + kanonik(deger[a]) for a in anahtarlar) + "}"
    raise TypeError(f"desteklenmeyen tip: {type(deger).__name__}")


def sha256(metin: str) -> str:
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def kayit_hash(kayit: dict) -> str:
    return sha256(kanonik({a: v for a, v in kayit.items() if a != "kayit_hash"}))


class Rapor:
    def __init__(self):
        self.basarisiz = 0
        self.eksik = 0

    def denetle(self, kosul: bool, mesaj: str):
        print(("  ✓ " if kosul else "  ✗ ") + mesaj)
        if not kosul:
            self.basarisiz += 1

    def eksik_kaldi(self, mesaj: str):
        print("  ? " + mesaj)
        self.eksik += 1


def genel_anahtar_yukle(yol: str):
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat
    except ImportError:
        return None, None
    with open(yol, "rb") as f:
        anahtar = load_pem_public_key(f.read())
    der = anahtar.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    return anahtar, hashlib.sha256(der).hexdigest()


def imza_gecerli(anahtar, kayit_hash_hex: str, imza_b64: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    try:
        anahtar.verify(base64.b64decode(imza_b64), kayit_hash_hex.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError):
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paket")
    ap.add_argument("--genel-anahtar", help="imza_anahtari.pub.pem (sunucu: GET /api/evidence/public-key)")
    ap.add_argument("--defter", help="defter.jsonl — zincirin tamamını da doğrula")
    a = ap.parse_args(argv)
    r = Rapor()

    with open(a.paket, encoding="utf-8") as f:
        dosya = json.load(f)
    paket, makbuz = dosya.get("paket") or {}, dosya.get("makbuz")
    print(f"Paket: {a.paket}")
    r.denetle(paket.get("sema") == KANIT_SEMASI, f"şema {paket.get('sema')}")
    r.denetle(sha256(kanonik(paket.get("veri"))) == paket.get("veri_sha256"),
              f"veri SHA-256 (tüm {len((paket.get('veri') or {}).get('rows') or [])} satır)")
    paket_sha = sha256(kanonik(paket))
    r.denetle(paket_sha == dosya.get("paket_sha256"), "paket SHA-256")

    anahtar = parmak = None
    if a.genel_anahtar:
        anahtar, parmak = genel_anahtar_yukle(a.genel_anahtar)
        if anahtar is None:
            r.eksik_kaldi("imza doğrulanamadı: `cryptography` paketi kurulu değil")

    if not makbuz:
        r.eksik_kaldi("makbuz YOK — paket kanıt defterine kaydedilmemiş (KAYITSIZ)")
    else:
        k = makbuz["kayit"]
        print(f"Makbuz: defter #{k.get('sira')} · {k.get('sunucu_zamani')} · aktör {k.get('aktor')}")
        r.denetle(k.get("kanit_id") == paket.get("kanit_id") and k.get("dosya_no") == paket.get("dosya_no"),
                  "makbuz bu paketi gösteriyor (kanıt_id, dosya_no)")
        r.denetle(k.get("veri_sha256") == paket.get("veri_sha256") and k.get("paket_sha256") == paket_sha,
                  "makbuzdaki hash'ler paketle aynı")
        r.denetle(kayit_hash(k) == k.get("kayit_hash"), "defter kaydının kendi hash'i")
        if anahtar is not None:
            r.denetle(parmak == makbuz.get("anahtar_parmak_izi"), "genel anahtar parmak izi eşleşiyor")
            r.denetle(imza_gecerli(anahtar, k["kayit_hash"], makbuz["imza"]), "Ed25519 imzası geçerli")
        elif not a.genel_anahtar:
            r.eksik_kaldi("imza denetlenmedi: --genel-anahtar verilmedi")

    if a.defter:
        print(f"Defter: {a.defter}")
        onceki, beklenen, bulundu = BASLANGIC_HASH, 1, False
        with open(a.defter, encoding="utf-8") as f:
            satirlar = [s for s in f.read().splitlines() if s.strip()]
        hata = 0
        for i, satir in enumerate(satirlar, 1):
            m = json.loads(satir)
            k = m["kayit"]
            sorun = []
            if k.get("sema") != DEFTER_SEMASI:
                sorun.append("şema")
            if k.get("sira") != beklenen:
                sorun.append("sıra")
            if k.get("onceki_hash") != onceki:
                sorun.append("zincir")
            if kayit_hash(k) != k.get("kayit_hash"):
                sorun.append("içerik")
            if anahtar is not None and (m.get("anahtar_parmak_izi") != parmak or not imza_gecerli(anahtar, k["kayit_hash"], m["imza"])):
                sorun.append("imza")
            if sorun:
                hata += 1
                print(f"  ✗ satır {i} (#{k.get('sira')}): {', '.join(sorun)}")
            if makbuz and k.get("sira") == makbuz["kayit"].get("sira") and k.get("kayit_hash") == makbuz["kayit"].get("kayit_hash"):
                bulundu = True
            onceki, beklenen = k.get("kayit_hash"), (k.get("sira") or 0) + 1
        r.denetle(hata == 0, f"defter zinciri ({len(satirlar)} kayıt)")
        if makbuz:
            r.denetle(bulundu, "makbuz defterde aynı sıra ve hash'le kayıtlı")

    if r.basarisiz:
        print(f"SONUÇ: BAŞARISIZ ({r.basarisiz} denetim) — kurcalama ya da uyuşmazlık")
        return 1
    if r.eksik:
        print(f"SONUÇ: EKSİK ({r.eksik} denetim yapılamadı)")
        return 2
    print("SONUÇ: GEÇERLİ")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
