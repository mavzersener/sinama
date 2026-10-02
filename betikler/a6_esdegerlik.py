# -*- coding: utf-8 -*-
"""
betikler/a6_esdegerlik.py — A6 eşdeğerlik ölçümü (ADR-004 md. 6, ön-kayıt
`uygulama/atolye_esdegerlik/ESDEGERLIK.md`, commit 93fd618).

    python betikler/a6_esdegerlik.py [--olcut E2 ...] [--e2e-atla] [--yaz]

E1  A sınıfı: Atölye'de `vitest run`, dosya dosya geçen sayısı = DataFlow başlangıcı, kalan 0.
E2  B sınıfı: her DataFlow testinin `# DataFlow: <dosya> › <ad>` işaretli Python karşılığı var
    ve geçiyor (tests/test_atolye_*.py; işaret, testin gövdesindeki yorum satırıdır).
E3  Atölye uçtan uca (Playwright, uygulama/atolye/e2e): hepsi geçer.
E4  Kanıt defteri biçim uyumu (iki yön): tests/test_atolye_kanit.TestBicimUyumuE4.
E5  Tek süreç: tests/test_atolye_sunucu.TestTekSurec.

Ölçütler sonradan gevşetilmez; betik yalnız ölçer ve raporlar. `--yaz` sonucu
`uygulama/atolye_esdegerlik/sonuc.json`'a yazar. Çıkış kodu: hepsi eşikte 0, değilse 1.
"""
import argparse
import ast
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ATOLYE = os.path.join(KOK, "uygulama", "atolye")
ES = os.path.join(KOK, "uygulama", "atolye_esdegerlik")
ISARET = "# DataFlow: "
sys.path.insert(0, KOK)


def taban():
    """DataFlow@5ea8652 başlangıç ölçümü."""
    with open(os.path.join(ES, "taban_dataflow_5ea8652.json"), encoding="utf-8") as f:
        return json.load(f)


def npx():
    return shutil.which("npx")


def e1(t):
    """A sınıfı dosyaların geçen sayıları Sınama'da (vitest JSON raporu)."""
    with tempfile.TemporaryDirectory() as d:
        rapor = os.path.join(d, "v.json")
        subprocess.run([npx(), "vitest", "run", "--reporter=json", f"--outputFile={rapor}"], cwd=ATOLYE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       shell=sys.platform == "win32", timeout=900)
        with open(rapor, encoding="utf-8") as f:
            v = json.load(f)
    sinama = {}
    for dosya in v["testResults"]:
        ad = os.path.relpath(dosya["name"], ATOLYE).replace("\\", "/")
        sinama[ad] = {"gecen": sum(a["status"] == "passed" for a in dosya["assertionResults"]),
                      "kalan": sum(a["status"] == "failed" for a in dosya["assertionResults"])}
    satirlar, toplam_taban, toplam = [], 0, 0
    for ad, b in t["dosyalar"].items():
        if b["sinif"] != "A":
            continue
        s = sinama.get(ad, {"gecen": 0, "kalan": 0})
        toplam_taban += b["gecen"]
        toplam += min(s["gecen"], b["gecen"]) if s["kalan"] == 0 else 0
        if s["gecen"] != b["gecen"] or s["kalan"]:
            satirlar.append(f"{ad}: Sınama {s['gecen']} geçti / {s['kalan']} kaldı, DataFlow {b['gecen']}")
    return {"olcut": f"{toplam}/{toplam_taban}", "esik": f"{toplam_taban}/{toplam_taban}",
            "gecti": toplam == toplam_taban and not satirlar, "sapmalar": satirlar}


def _isaretler():
    """tests/test_atolye_*.py → {(modül, sınıf, yöntem): DataFlow adı}."""
    isaret = {}
    for yol in sorted(glob.glob(os.path.join(KOK, "tests", "test_atolye_*.py"))):
        modul = "tests." + os.path.splitext(os.path.basename(yol))[0]
        with open(yol, encoding="utf-8") as f:
            kaynak = f.read()
        satirlar = kaynak.splitlines()
        for sinif in ast.parse(kaynak).body:
            if not isinstance(sinif, ast.ClassDef):
                continue
            for y in sinif.body:
                if isinstance(y, ast.FunctionDef) and y.name.startswith("test"):
                    for s in satirlar[y.lineno - 1:y.end_lineno]:
                        if s.strip().startswith(ISARET):
                            isaret[(modul, sinif.name, y.name)] = s.strip()[len(ISARET):]
    return isaret


class _Toplayici(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.durum = {}

    def _yaz(self, test, d):
        self.durum[test.id()] = d

    def addSuccess(self, test):
        super().addSuccess(test)
        self._yaz(test, "gecti")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._yaz(test, "kaldi")

    def addError(self, test, err):
        super().addError(test, err)
        self._yaz(test, "hata")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._yaz(test, "atlandi")


def unittest_kos(adlar):
    """Verilen test adlarını koşar → {test_id: durum}."""
    os.environ.setdefault("PYTHONUTF8", "1")
    takim = unittest.defaultTestLoader.loadTestsFromNames(adlar)
    kosucu = unittest.TextTestRunner(stream=io.StringIO(), resultclass=_Toplayici, verbosity=0)
    return kosucu.run(takim).durum


def e2(t):
    """B sınıfı DataFlow testlerinin işaretli Python karşılıkları."""
    isaret = _isaretler()
    durum = unittest_kos(sorted({m for m, _, _ in isaret}))
    beklenen = {f"{ad} › {test}" for ad, b in t["dosyalar"].items() if b["sinif"] == "B" for test in b["testler"]}
    karsilik = {}
    for (m, s, y), ad in isaret.items():
        karsilik.setdefault(ad, []).append(durum.get(f"{m}.{s}.{y}", "kosmadi"))
    gecen = sorted(a for a in beklenen if karsilik.get(a) and all(d == "gecti" for d in karsilik[a]))
    eksik = sorted(beklenen - set(karsilik))
    basarisiz = sorted(a for a in beklenen if a in karsilik and a not in gecen)
    fazla = sorted(set(karsilik) - beklenen)   # adı başlangıçta olmayan işaret (yazım hatası)
    return {"olcut": f"{len(gecen)}/{len(beklenen)}", "esik": f"{len(beklenen)}/{len(beklenen)}",
            "gecti": len(gecen) == len(beklenen) and not fazla,
            "eksik": eksik, "basarisiz": basarisiz, "bilinmeyen_isaret": fazla}


def e3():
    """Atölye Playwright uçtan uca testi."""
    r = subprocess.run([npx(), "playwright", "test", "-c", "e2e/playwright.config.ts", "--reporter=json"],
                       cwd=ATOLYE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       shell=sys.platform == "win32", timeout=900,
                       env={**os.environ, "SINAMA_PY": os.environ.get("SINAMA_PY", sys.executable)})
    try:
        rapor = json.loads(r.stdout)
        st = rapor["stats"]
        gecen, kalan = st["expected"], st["unexpected"] + st.get("flaky", 0)
    except (ValueError, KeyError):
        return {"olcut": 0, "esik": 1, "gecti": False, "cikti": (r.stdout + r.stderr)[-2000:]}
    return {"olcut": int(gecen > 0 and kalan == 0), "esik": 1, "gecti": gecen > 0 and kalan == 0,
            "senaryo": f"{gecen} geçti, {kalan} kaldı"}


def _sinif_kos(ad):
    durum = unittest_kos([ad])
    ok = bool(durum) and all(d == "gecti" for d in durum.values())
    return {"olcut": int(ok), "esik": 1, "gecti": ok, "testler": durum}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--e2e-atla", action="store_true", help="E3'ü koşma (Playwright tarayıcısı yoksa)")
    ap.add_argument("--yaz", action="store_true", help="sonucu atolye_esdegerlik/sonuc.json'a yaz")
    ap.add_argument("--olcut", action="append", choices=("E1", "E2", "E3", "E4", "E5"),
                    help="yalnız bu ölçüt(ler) (varsayılan: hepsi)")
    a = ap.parse_args(argv)
    t = taban()
    secili = a.olcut or ["E1", "E2", "E3", "E4", "E5"]
    sonuc = {"on_kayit": "93fd618 (ESDEGERLIK.md)", "taban": t["kaynak"]}
    olcer = {"E1": lambda: e1(t), "E2": lambda: e2(t),
             "E3": lambda: ({"olcut": None, "esik": 1, "gecti": False, "not": "atlandı (--e2e-atla)"}
                            if a.e2e_atla else e3()),
             "E4": lambda: _sinif_kos("tests.test_atolye_kanit.TestBicimUyumuE4"),
             "E5": lambda: _sinif_kos("tests.test_atolye_sunucu.TestTekSurec")}
    for k in secili:
        sonuc[k] = olcer[k]()
    for k in secili:
        r = sonuc[k]
        print(f"{k}: {r['olcut']} (eşik {r['esik']}) — {'GEÇTİ' if r['gecti'] else 'GEÇMEDİ'}")
        for alan in ("sapmalar", "eksik", "basarisiz", "bilinmeyen_isaret"):
            for s in r.get(alan) or []:
                print(f"    {alan}: {s}")
    if a.yaz:
        with open(os.path.join(ES, "sonuc.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(sonuc, f, ensure_ascii=False, indent=1)
            f.write("\n")
    return 0 if all(sonuc[k]["gecti"] for k in secili) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
