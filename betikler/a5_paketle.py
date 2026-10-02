# -*- coding: utf-8 -*-
r"""
a5_paketle.py — internetsiz (air-gap) kurulum paketi (A5, ADR-003 "Sonuçlar").

Paket: depo kaynağı (`git archive HEAD` — yalnız izlenen dosyalar; çalışma ağacındaki
veri, .env ve oturumlar ASLA girmez), derlenmiş ön yüzler (`uygulama/web/dist` Rehberli,
`uygulama/atolye/dist` Atölye — A6), Python
tekerlekleri (`pip download`; paketleme anında internet gerekir, kurulumda gerekmez),
KURULUM.md, Windows başlatıcısı ve her dosyanın SHA-256 listesi. Çıktı depo DIŞINDA
olmalıdır (depo içine yazmayı reddeder).

Tekerlekler paketlemeyi yapan yorumlayıcının sürümü ve platformu içindir; hedef farklıysa
--python-surumu ve --platform verin (pip download --only-binary=:all:).

Kullanım (depo kökünden):
    python betikler/a5_paketle.py --cikti C:/paketler [--python-surumu 3.14 --platform win_amd64]
"""
import argparse
import datetime
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(KOK, "uygulama", "web", "dist")
ATOLYE_DIST = os.path.join(KOK, "uygulama", "atolye", "dist")   # A6 (ADR-004): /atolye/
GEREKSINIMLER = os.path.join(KOK, "uygulama", "gereksinimler.txt")

KURULUM = """# Sınama — internetsiz kurulum (A5)

Paket: `{ad}` · commit `{commit}` · {tarih} · tekerlekler: Python {py}, {platform}

1. Python {py} kurulu olmalı (python.org kurulum dosyası; internet gerekmez).
2. Paketi bir dizine açın (ör. `C:\\sinama`), sonra o dizinde:

       python -m pip install --no-index --find-links tekerlekler -r sinama/uygulama/gereksinimler.txt

3. Veri kökü depo dışında bir dizin olmalı (ör. `C:\\suc_veri`); CSV'leri `veri\\` altına koyun
   ya da arayüzden yükleyin.
4. Başlatma: `baslat.bat` (veri kökünü sorar) ya da

       cd sinama
       set PYTHONUTF8=1
       python -m uygulama --veri-koku C:\\suc_veri --ac

   Tarayıcı http://127.0.0.1:8810 adresinde açılır (Rehberli); düğüm editörü Atölye
   http://127.0.0.1:8810/atolye/ adresindedir. Yalnız bu bilgisayardan erişilir.
5. Dil modeli opsiyoneldir (`--dil-modeli http://127.0.0.1:8080`); yoksa `--dil-modeli yok`.
6. Bütünlük: `SHA256SUMS.txt` her dosyanın özetini taşır.
"""

BASLAT = r"""@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set /p VERI=Veri koku (depo disi dizin, or. C:\suc_veri):
cd /d "%~dp0sinama"
python -m uygulama --veri-koku "%VERI%" --ac
pause
"""


def depo_icinde_mi(yol):
    """Yol bu deponun içinde mi."""
    yol, kok = os.path.realpath(yol), os.path.realpath(KOK)
    try:
        return os.path.commonpath([yol, kok]) == kok
    except ValueError:
        return False


def git(*arg, girdi=None):
    """git komutu (depo kökünde); stdout baytları."""
    return subprocess.run(["git", "-C", KOK, *arg], check=True, capture_output=True, input=girdi).stdout


def kaynak_ac(hedef):
    """HEAD'in izlenen dosyalarını hedef/sinama altına açar (git archive → zip)."""
    arsiv = git("archive", "--format=zip", "HEAD")
    with zipfile.ZipFile(io.BytesIO(arsiv)) as z:
        z.extractall(os.path.join(hedef, "sinama"))


def tekerlekler(hedef, python_surumu=None, platform=None):
    """pip download → hedef/tekerlekler."""
    komut = [sys.executable, "-m", "pip", "download", "-r", GEREKSINIMLER, "-d", os.path.join(hedef, "tekerlekler")]
    if python_surumu or platform:
        komut += ["--only-binary=:all:"]
        komut += ["--python-version", python_surumu] if python_surumu else []
        komut += ["--platform", platform] if platform else []
    subprocess.run(komut, check=True)


def ozet_listesi(kok):
    """Kök altındaki her dosyanın SHA-256'sı (sıralı, '/' ayırıcılı)."""
    satirlar = []
    for dizin, _, dosyalar in os.walk(kok):
        for ad in dosyalar:
            yol = os.path.join(dizin, ad)
            with open(yol, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            satirlar.append(f"{h}  {os.path.relpath(yol, kok).replace(os.sep, '/')}")
    return sorted(satirlar, key=lambda s: s.split("  ", 1)[1])


def ozet_yaz(kok):
    """SHA256SUMS.txt'i yazar — liste dosya AÇILMADAN hesaplanır (kendini içermez)."""
    satirlar = ozet_listesi(kok)
    with open(os.path.join(kok, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(satirlar) + "\n")
    return satirlar


def paketle(cikti, python_surumu=None, platform=None, tekerlek=True):
    """Paketi üretir; zip yolunu döner."""
    if depo_icinde_mi(cikti):
        raise SystemExit(f"çıktı depo içinde olamaz: {cikti}")
    if not os.path.isfile(os.path.join(DIST, "index.html")):
        raise SystemExit("ön yüz derlenmemiş: cd uygulama/web && npm ci && npm run build")
    if not os.path.isfile(os.path.join(ATOLYE_DIST, "index.html")):
        raise SystemExit("Atölye derlenmemiş: cd uygulama/atolye && npm ci && npm run build")
    if git("status", "--porcelain", "--untracked-files=no").strip():
        raise SystemExit("izlenen dosyalarda commit'lenmemiş değişiklik var: paket HEAD'i yansıtmaz")
    commit = git("rev-parse", "--short", "HEAD").decode().strip()
    ad = f"sinama-a5-{commit}"
    with tempfile.TemporaryDirectory(prefix="sinama_paket_") as gecici:
        hedef = os.path.join(gecici, ad)
        kaynak_ac(hedef)
        shutil.copytree(DIST, os.path.join(hedef, "sinama", "uygulama", "web", "dist"))
        shutil.copytree(ATOLYE_DIST, os.path.join(hedef, "sinama", "uygulama", "atolye", "dist"))
        if tekerlek:
            tekerlekler(hedef, python_surumu, platform)
        py = python_surumu or f"{sys.version_info.major}.{sys.version_info.minor}"
        with open(os.path.join(hedef, "KURULUM.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(KURULUM.format(ad=ad, commit=commit, tarih=datetime.date.today().isoformat(), py=py,
                                   platform=platform or sys.platform))
        with open(os.path.join(hedef, "baslat.bat"), "w", encoding="utf-8", newline="\r\n") as f:
            f.write(BASLAT)
        ozet_yaz(hedef)
        os.makedirs(cikti, exist_ok=True)
        zip_yolu = shutil.make_archive(os.path.join(cikti, ad), "zip", gecici, ad)
    return zip_yolu


def main(argv=None):
    """Komut satırı."""
    ap = argparse.ArgumentParser(description="Sınama A5 internetsiz kurulum paketi")
    ap.add_argument("--cikti", required=True, help="depo DIŞI çıktı dizini")
    ap.add_argument("--python-surumu", help="tekerlek hedefi, ör. 3.12")
    ap.add_argument("--platform", help="tekerlek hedefi, ör. win_amd64, manylinux2014_x86_64")
    ap.add_argument("--tekerleksiz", action="store_true", help="tekerlekleri indirme (yalnız sınama)")
    a = ap.parse_args(argv)
    yol = paketle(a.cikti, a.python_surumu, a.platform, tekerlek=not a.tekerleksiz)
    print(f"paket: {yol} ({os.path.getsize(yol) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
