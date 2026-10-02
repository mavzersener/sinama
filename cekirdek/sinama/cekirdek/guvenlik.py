# -*- coding: utf-8 -*-
r"""
cekirdek/guvenlik.py — güvenli dosya erişimi primitifleri.
Yol hapsi (path jail) + izinli kök + uzantı/boyut tavanları.
v6.7: kalite/ altından cekirdek/ altına TAŞINDI — güvenlik primitifi
en alt katmandır (katman ihlali düzeltmesi, H4-u). Eski yol
kalite/guvenlik.py, sys.modules yönlendirmesiyle uyumluluk sağlar.
"""

import os

from .hatalar import GuvenlikHatasi

IZINLI_UZANTILAR = {".csv", ".tsv", ".txt"}


MAKS_DOSYA_MB = 50


def varsayilan_veri_koku():
    """Ortam değişkeni yoksa veri kökü (ADR-003 md. 3): Windows'ta
    %LOCALAPPDATA%\\sinama, diğerlerinde $XDG_DATA_HOME/sinama ya da
    ~/.local/share/sinama. Çalışma dizinine DÜŞÜLMEZ: depo içinden çalışan bir
    araç çağrısı oturum ve kanıt kaydını depoya yazıyordu (A3 bulgusu; A4.15
    testleri cekirdek/oturumlar'a 35 oturum bırakmıştı)."""
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        taban = os.environ["LOCALAPPDATA"]
    else:
        taban = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share")
    return os.path.join(taban, "sinama")


def veri_koku():
    """İzinli kök dizin: SINAMA_VERI_KOKU, yoksa varsayilan_veri_koku()."""
    return os.path.realpath(os.environ.get("SINAMA_VERI_KOKU") or varsayilan_veri_koku())


def guvenli_yol(yol, kok=None, izinli_uzantilar=None):
    """
    Yolu izinli köke kilitler. Kaçış girişiminde ValueError fırlatır.
    izinli_uzantilar verilirse varsayılan whitelist yerine o kullanılır
    (ör. CHI ağırlık tablosu için {'.json'} — v6.4 düzeltmesi).
    Dönüş: güvenli mutlak yol.
    """
    if not yol or not isinstance(yol, str):
        raise GuvenlikHatasi("geçersiz dosya yolu")
    kok_gercek = os.path.realpath(kok) if kok else veri_koku()
    # göreli yollar veri köküne göre çözümlenir; realpath sembolik
    # bağları ve ".." çözümler
    if not os.path.isabs(yol):
        yol = os.path.join(kok_gercek, yol)
    gercek = os.path.realpath(yol)
    try:
        ortak = os.path.commonpath([gercek, kok_gercek])
    except ValueError:
        raise GuvenlikHatasi(
            "yol izinli veri kökünün dışında",
            oneri="dosyayı veri kökü dizinine kopyalayıp göreli yol verin")
    if ortak != kok_gercek:
        raise GuvenlikHatasi(
            "yol izinli veri kökünün dışında",
            oneri="dosyayı veri kökü dizinine kopyalayıp göreli yol verin")
    uzantilar = izinli_uzantilar if izinli_uzantilar is not None \
        else IZINLI_UZANTILAR
    if os.path.splitext(gercek)[1].lower() not in uzantilar:
        raise GuvenlikHatasi(
            f"izin verilmeyen uzantı; yalnızca {sorted(uzantilar)}",
            oneri="dosyayı CSV/TSV/TXT olarak dışa aktarın")
    if not os.path.isfile(gercek):
        raise GuvenlikHatasi("dosya bulunamadı veya dosya değil",
                             oneri="dosya adını ve dizini denetleyin")
    boyut_mb = os.path.getsize(gercek) / (1024 * 1024)
    if boyut_mb > MAKS_DOSYA_MB:
        raise GuvenlikHatasi(
            f"dosya çok büyük ({boyut_mb:.1f} MB > {MAKS_DOSYA_MB} MB)",
            oneri="dosyayı dönem/bölge bazında bölerek yükleyin")
    return gercek
