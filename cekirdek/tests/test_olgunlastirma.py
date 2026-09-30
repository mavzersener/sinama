# -*- coding: utf-8 -*-
"""
test_olgunlastirma.py — v6.7 kanıtları (GELISME_PLANI H5 + H4-u):
  H5.1 seviyeli loglama (stdlib logging; audit akışı bağımsız)
  H5.2 doküman standardı: public imza %100 docstring, genel ≥%85
      (kayıtlı araç adaptörleri `_` hariç — belgeleri dekoratörde),
      birimli parametreler (_km/_km2/_gun/_saat/_mb/_tl/_oran/_yuzde/_m2)
      docstring'de anılır (DOKTRIN kural 25)
  H4-u katman bağımlılık yönü tek yönlüdür: cekirdek → yok,
      kalite → cekirdek, surec → +kalite, arayuz → hepsi
      (DOKTRIN kural 24)
"""
import ast
import os
import pathlib
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KOK = pathlib.Path(__file__).resolve().parent.parent
PAKET = KOK / "sinama"

BIRIM = re.compile(r"_(km|km2|gun|saat|dk|mb|tl|oran|yuzde|m2)$")


def _fonksiyonlar():
    for p in sorted(PAKET.rglob("*.py")):
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.FunctionDef):
                yield p, n


class TestDokumanStandardi(unittest.TestCase):
    """H5.2 / DOKTRIN 25: public imzalar belgeli ve birimlidir."""

    def test_public_docstring_yuzde_yuz(self):
        eksik = [f"{p.name}:{n.name}" for p, n in _fonksiyonlar()
                 if not n.name.startswith("_") and not ast.get_docstring(n)]
        self.assertEqual(eksik, [])

    def test_genel_docstring_esigi(self):
        # `_` adlı kayıtlı araç adaptörleri belgeyi dekoratörden alır
        toplam = belgeli = 0
        for p, n in _fonksiyonlar():
            if n.name == "_":
                continue
            toplam += 1
            if ast.get_docstring(n):
                belgeli += 1
        self.assertGreaterEqual(100 * belgeli / toplam, 85.0)

    def test_birimli_parametreler_docstringde(self):
        # birim taşıyan parametre adı docstring'de anılmalı — kollukta
        # birim belirsizliği yanlış rapordur
        kusurlar = []
        for p, n in _fonksiyonlar():
            if n.name.startswith("_"):
                continue
            doc = ast.get_docstring(n) or ""
            for a in n.args.args:
                if BIRIM.search(a.arg) and a.arg not in doc:
                    kusurlar.append(f"{p.name}:{n.name}({a.arg})")
        self.assertEqual(kusurlar, [])

    def test_arac_aciklamalari_dolu(self):
        from sinama.arayuz.ortak import ARACLAR
        bos = [ad for ad, t in ARACLAR.items()
               if not (t.get("aciklama") or "").strip()]
        self.assertEqual(bos, [])


class TestH51_Loglama(unittest.TestCase):
    """H5.1: seviyeli loglama; audit akışı loglayıcıdan bağımsız."""

    def test_hata_seviyesi_error(self):
        from sinama.arayuz import sunucu
        from sinama.arayuz.ortak import ARACLAR
        def fn(a):
            raise RuntimeError("iç ayrıntı")
        ARACLAR["sahte_h5"] = {"fn": fn, "aciklama": "t",
                               "sema": {"type": "object",
                                        "properties": {}},
                               "politika": {"sinif": "veri_hazirlama",
                                            "gate": None,
                                            "muafiyet_gerekcesi": "sentetik test",
                                            "insan_onayi": False,
                                            "iz_zorunlu": False,
                                            "veri_sinifi": "sentetik",
                                            "butce_turu": "dogrusal"}}
        self.addCleanup(lambda: ARACLAR.pop("sahte_h5", None))
        with self.assertLogs("sinama", level="ERROR") as cm:
            sunucu.isle({"method": "tools/call", "id": 1,
                         "params": {"name": "sahte_h5", "arguments": {}}})
        self.assertTrue(any("ARAÇ HATASI" in s for s in cm.output))

    def test_seviye_env_ile_ayarlanir(self):
        from sinama.arayuz.ortak import logger_kur
        import logging
        eski = os.environ.get("SINAMA_LOG_SEVIYE")
        os.environ["SINAMA_LOG_SEVIYE"] = "ERROR"
        try:
            self.assertEqual(logger_kur().level, logging.ERROR)
        finally:
            if eski is None:
                os.environ.pop("SINAMA_LOG_SEVIYE", None)
            else:
                os.environ["SINAMA_LOG_SEVIYE"] = eski
        logger_kur()  # varsayılan seviyeye geri

    def test_kurulum_idempotent(self):
        from sinama.arayuz.ortak import logger_kur
        logger_kur()
        n1 = len(logger_kur().handlers)
        logger_kur()
        self.assertEqual(len(logger_kur().handlers), n1)


def _hedef_yolu(dosya, dugum):
    """Göreli importun hedef yolunu parça listesi olarak çözümler
    (örn. ['sinama', 'kalite', 'profil']); stdlib/dış paket → None."""
    parcalar = list(dosya.parent.relative_to(KOK).parts)
    seviye = dugum.level or 0
    if seviye == 0:
        hedef = (dugum.module or "").split(".")
    else:
        kok_parcalar = parcalar[:len(parcalar) - (seviye - 1)]
        hedef = kok_parcalar + (dugum.module or "").split(".")
    if hedef[:1] == ["sinama"] and len(hedef) > 1:
        return hedef
    return None


IZINLI = {"cekirdek": {"cekirdek"},
          "kalite": {"cekirdek", "kalite"},
          "surec": {"cekirdek", "kalite", "surec"},
          "bilim": {"cekirdek", "kalite", "surec", "bilim"},   # ADR-002
          "arayuz": {"cekirdek", "kalite", "surec", "bilim", "arayuz"}}


# Bilinen, daraltılmış istisnalar: veri.py'deki iki GERİYE UYUMLULUK
# sarmalayıcısı (v6.1 şimleri, v7'de kaldırılacak). Küme SABİTTİR —
# büyümesi bu testi kırar (yeni ters bağımlılık yapısal olarak yasak).
KALICI_ISTISNA = {("veri.py", "kalite.profil"), ("veri.py", "kalite.kapi")}


class TestKatmanIhlali(unittest.TestCase):
    """H4-u / DOKTRIN 24: bağımlılık yönü cekirdek → arayuz tek yönlü."""

    def test_import_yonu(self):
        ihlaller = []
        for p in sorted(PAKET.rglob("*.py")):
            katman = p.parent.name
            if katman not in IZINLI:
                continue
            for dugum in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(dugum, ast.ImportFrom):
                    yol = _hedef_yolu(p, dugum)
                elif isinstance(dugum, ast.Import):
                    yol = None
                    for a in dugum.names:
                        hs = a.name.split(".")
                        if hs[:1] == ["sinama"] and len(hs) > 1:
                            yol = hs
                else:
                    continue
                if not yol:
                    continue
                hedef = yol[1]
                if hedef and hedef not in IZINLI[katman]:
                    if (p.name, ".".join(yol[1:])) in KALICI_ISTISNA:
                        continue
                    ihlaller.append(f"{p}: → {hedef}")
        self.assertEqual(ihlaller, [])

    def test_istisna_kumesi_buyumez(self):
        # veri.py'de şimler dışında kalite importu varsa yakala
        dosya = PAKET / "cekirdek" / "veri.py"
        kaynak = dosya.read_text(encoding="utf-8")
        hedefler = set()
        for dugum in ast.walk(ast.parse(kaynak)):
            if isinstance(dugum, ast.ImportFrom):
                yol = _hedef_yolu(dosya, dugum)
                if yol and yol[1] not in IZINLI["cekirdek"]:
                    hedefler.add(("veri.py", ".".join(yol[1:])))
        self.assertEqual(hedefler, KALICI_ISTISNA)


if __name__ == "__main__":
    unittest.main()
