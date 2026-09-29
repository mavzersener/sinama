#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kapsam_olc.py — stdlib `trace` ile satır kapsamı ölçümü (v6.6, H3.4).
Sıfır bağımlılık: geliştirme aracı da standart kütüphanedendir.

Çalıştırma:  python kapsam_olc.py [--coverdir DIZIN] [--taban-guncelle]
Çıktı:       cekirdek modülü başına kapsam yüzdesi + genel özet.
Eşik:        varsayılan %80; bir cekirdek modülü eşiğin altındaysa
             çıkış kodu 1 (test.sh bunu raporlar; yeni kod normu %80).
Not:         yalnız birim testleri ölçer (test_mcp.py ayrı süreçte
             çalıştığı için arayuz katmanı burada düşük görünebilir —
             rapor kapsamı bilinçli olarak cekirdek ile sınırlıdır).
"""
import argparse
import os
import re
import sys
import trace
import unittest
import tempfile


def olc(hedef_paket="suc_analizi/cekirdek", coverdir=None):
    """Test raporu ve unittest sonucu döner; her ölçüm ayrı dizindedir.

    coverdir verilirse altında benzersiz rapor dizini tutulur. Varsayılan
    geçici dizin ölçüm bitince temizlenir; mevcut raporlara dokunulmaz.
    """
    if coverdir is not None:
        os.makedirs(coverdir, exist_ok=True)
        hedef = tempfile.mkdtemp(prefix="kapsam_", dir=coverdir)
        print(f"kapsam çıktısı: {hedef}")
        return _olc_dizinde(hedef_paket, hedef)
    with tempfile.TemporaryDirectory(prefix="kapsam_") as hedef:
        return _olc_dizinde(hedef_paket, hedef)


def _olc_dizinde(hedef_paket, coverdir):
    """Yalnız bu çağrıya ait boş dizinde ölçüm yapar."""
    kok = os.path.dirname(os.path.abspath(__file__))
    onceki_path = sys.path[:]
    sys.path.insert(0, os.path.join(kok, "tests"))  # discover ile aynı
    tracer = trace.Trace(count=1, trace=0,
                         ignoredirs=[sys.prefix, sys.exec_prefix])

    def _calistir():
        # suite İZLEME ALTINDA kurulur — aksi hâlde modül üst düzeyi
        # (def/class) import önbelleğinden gelir ve "kaçırıldı" sayılır
        yukleyici = unittest.TestLoader()
        paket = unittest.TestSuite()
        for modul in sorted(os.listdir(os.path.join(kok, "tests"))):
            if modul.startswith("test_") and modul.endswith(".py"):
                paket.addTests(yukleyici.loadTestsFromName(modul[:-3]))
        return unittest.TextTestRunner(verbosity=0).run(paket)

    try:
        test_sonucu = tracer.runfunc(_calistir)
    finally:
        sys.path[:] = onceki_path
    tracer.results().write_results(show_missing=True, coverdir=coverdir)

    # .cover ayrıştırma: dosya adı = noktalı modül adı;
    # "sayi:" önekli satır = çalıştı; ">>>>>>" = kaçırıldı
    rapor = {}
    for fn in sorted(os.listdir(coverdir)):
        if not fn.endswith(".cover"):
            continue
        modul_yolu = fn[:-6].replace(".", "/") + ".py"
        calisti, kacirildi = 0, 0
        with open(os.path.join(coverdir, fn), encoding="utf-8") as f:
            for satir in f:
                if satir.startswith(">>>>>>"):
                    kacirildi += 1
                elif re.match(r"^\s*\d+:", satir):
                    calisti += 1
        if modul_yolu.startswith(hedef_paket):
            rapor[modul_yolu] = (calisti, kacirildi)
    return rapor, test_sonucu


TABAN_DOSYA = "kapsam_taban.json"
YENI_MODUL_ESIK = 80.0   # yeni kod normu (GELISME_PLANI H3.4)


def main(argv=None):
    """CLI: başarı 0, test/kapsam reddi 1, kullanım/I/O hatası 2."""
    import json
    parser = argparse.ArgumentParser(description="Birim testi ve kapsam kapısı")
    parser.add_argument("--coverdir", help="Benzersiz rapor alt dizininin üst dizini")
    parser.add_argument("--taban-guncelle", action="store_true")
    args = parser.parse_args(argv)
    kok = os.path.dirname(os.path.abspath(__file__))
    try:
        rapor, test_sonucu = olc(coverdir=args.coverdir) if args.coverdir else olc()
    except OSError as exc:
        print(f"KAPSAM I/O HATASI: {exc}", file=sys.stderr)
        return 2
    taban_yolu = os.path.join(kok, TABAN_DOSYA)

    if not test_sonucu.wasSuccessful():
        print("KAPSAM TESTLERİ BAŞARISIZ: taban güncellenmedi")
        return 1

    if not rapor:
        print("KAPSAM KAPISI BAŞARISIZ: boş rapor")
        return 1

    taban = {}
    try:
        if os.path.isfile(taban_yolu):
            with open(taban_yolu, encoding="utf-8") as f:
                taban = json.load(f)
        if not isinstance(taban, dict) or any(
                not isinstance(v, (int, float)) or isinstance(v, bool)
                or not 0 <= v <= 100 for v in taban.values()):
            raise ValueError("geçersiz kapsam tabanı")
    except (OSError, ValueError) as exc:
        print(f"KAPSAM TABAN HATASI: {exc}", file=sys.stderr)
        return 2

    print(f"{'modül':45s} {'kapsam':>7s} {'sınır':>6s}  (çalışan/toplamlı)")
    dusuk = []
    toplam_c, toplam_k = 0, 0
    for yol, (c, k) in sorted(rapor.items()):
        toplam = c + k
        yuzde = 100.0 * c / toplam if toplam else 100.0
        toplam_c += c
        toplam_k += k
        # cırcır kapısı: eski modül tabanının altına inemez;
        # tabanda OLMAYAN (yeni) modül %80 normuna tabidir
        sinir = taban.get(yol, YENI_MODUL_ESIK)
        kaynak = "taban" if yol in taban else "yeni"
        if yuzde < sinir - 0.15:  # ondalık yuvarlama toleransı
            dusuk.append((yol, yuzde, sinir, kaynak))
            isaret = f"  <-- {kaynak} sınırı altı"
        else:
            isaret = ""
        print(f"{yol:45s} {yuzde:6.1f}% {sinir:5.1f}%  ({c}/{toplam}){isaret}")
    kayip = sorted(set(taban) - set(rapor))
    for yol in kayip:
        dusuk.append((yol, 0.0, taban[yol], "taban"))
        print(f"{yol:45s} MODÜL YOK — taban bayat; --taban-guncelle")
    genel_toplam = toplam_c + toplam_k
    genel = 100.0 * toplam_c / genel_toplam if genel_toplam else 100.0
    print(f"{'CEKIRDEK GENEL':45s} {genel:6.1f}%")
    if dusuk:
        print(f"KAPSAM KAPISI BAŞARISIZ: {len(dusuk)} modül sınır altı")
        return 1
    if args.taban_guncelle:
        # Başarısız/eşik altı ölçüm taban üretemez; eski sınır azalmaz.
        yeni = {yol: max(taban.get(yol, 0), round(100.0 * c / (c + k), 1))
                for yol, (c, k) in sorted(rapor.items()) if c + k}
        try:
            with open(taban_yolu, "w", encoding="utf-8") as f:
                json.dump(yeni, f, indent=1, ensure_ascii=False)
        except OSError as exc:
            print(f"KAPSAM TABAN YAZMA HATASI: {exc}", file=sys.stderr)
            return 2
        print(f"taban güncellendi: {len(yeni)} modül → {TABAN_DOSYA}")
    print("kapsam kapısı: geçti (cırcır — gerileme yok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
