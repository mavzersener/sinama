# -*- coding: utf-8 -*-
r"""
kiyas/v9/kos_v9.py — Bilimsel Muhakeme Kıyası v9 koşucusu (V16, CUSUM kalibrasyonu).

v9 önceki sürümlere DOKUNMADAN eklenir; v8'in üretecini ve yardımcılarını (cagir,
ilk_alarm_farki), v0'ın değerlendiricisini ve v3'ün tablo yazıcısını içe aktarır —
hepsi v9 kilidindedir. Araç resmi yoldan ve VARSAYILAN argümanlarla çağrılır.

Kullanım (depo kökünden):
    python kiyas/v9/kos_v9.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v9/kos_v9.py --kaydet     # + kiyas/v9/sonuclar/v9.json
    python kiyas/v9/kos_v9.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v9/kos_v9.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)
"""
import argparse
import hashlib
import json
import os
import platform
import statistics
import sys

V9 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V9)
sys.path.insert(0, KIYAS)
sys.path.insert(0, os.path.join(KIYAS, "v3"))
sys.path.insert(0, os.path.join(KIYAS, "v8"))

import kos  # noqa: E402  (v0 — kilitli)
import kos_v3  # noqa: E402  (v3 tablo yazıcısı — kilitli)
import kos_v8  # noqa: E402  (v8 yardımcıları — kilitli)
import uretec_v8  # noqa: E402  (v8 üreteci — kilitli)

KOK = kos.KOK
KILIT = os.path.join(V9, "kilit.json")
SONUC = os.path.join(V9, "sonuclar", "v9.json")
KILITLI = ["kiyas/v9/vakalar/v16_cusum_kalibrasyon.json", "kiyas/v9/kos_v9.py",
           "kiyas/v8/kos_v8.py", "kiyas/v8/uretec_v8.py", "kiyas/v3/kos_v3.py",
           "kiyas/v3/uretec_v3.py", "kiyas/v2/uretec_v2.py", "kiyas/uretec.py", "kiyas/kos.py"]
DEGISIMSIZ = ("sabit", "sabit_nb", "sabit_dusuk")


def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256, 8'li gruplar ("sha256:xxxxxxxx:…")."""
    with open(os.path.join(KOK, yol), "rb") as f:
        h = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    return "sha256:" + ":".join(h[i:i + 8] for i in range(0, 64, 8))


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v9 ön-kayıt kilidi yok: önce `python kiyas/v9/kos_v9.py --kilitle`")
    with open(KILIT, encoding="utf-8") as f:
        kilit = json.load(f)
    degisen = [y for y, h in kilit["dosyalar"].items() if _ozet(y) != h]
    if degisen:
        print("KİLİT BOZUK — ön-kayıttan sonra değişen dosyalar: " + ", ".join(degisen),
              file=sys.stderr)
        print("Eşik ya da gerçek sonuç görüldükten sonra değiştirilemez; gerekiyorsa "
              "yeni sürüm açıp gerekçesini yazın.", file=sys.stderr)
        sys.exit(2)
    return kilit


def kilitle():
    """v9 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v9 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v9",
             "ilke": "Bu dosyalar ilk v9 ölçümünden ve CUSUM kalibrasyon düzeltmesinden ÖNCE "
                     "kilitlendi; değişirlerse koşucu ölçmeyi reddeder. v0/v3/v8 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v9 kilidi yazıldı: {len(KILITLI)} dosya")


def vaka_oku():
    with open(os.path.join(V9, "vakalar", "v16_cusum_kalibrasyon.json"), encoding="utf-8") as f:
        return json.load(f)


def v16_degerler(f):
    """f: {senaryo: [ilk alarm farkı ya da None]} → ön-kayıtlı ölçüt değerleri."""
    return {
        "K16.1": kos.oran([x is not None for x in f["sabit"]]),
        "K16.2": kos.oran([x is not None for x in f["sabit_nb"]]),
        "K16.3": kos.oran([x is not None for x in f["sabit_dusuk"]]),
        "K16.4": kos.oran([x is not None and -15 <= x <= 180 for x in f["artis30"]]),
        "K16.5": kos.oran([x is not None and -15 <= x <= 90 for x in f["artis50"]]),
        "K16.6": kos.oran([x is None or x >= -15 for x in f["artis30_nb"]]),
        "K16.7": kos.oran([x is not None for s in DEGISIMSIZ for x in f[s]]),
    }


def v16(adet=None):
    vaka = vaka_oku()
    f, hatalar = {}, {}
    for senaryo in vaka["senaryolar"]:
        p = uretec_v8.parametreler(vaka, senaryo)
        f[senaryo] = []
        for t in kos_v8.tohumlar(vaka, senaryo, adet):
            satirlar, gercek = uretec_v8.v15_seri(p, t)
            yanit, hata = kos_v8.cagir("cusum", satirlar)
            if hata:
                hatalar.setdefault(senaryo, {}).setdefault(hata, 0)
                hatalar[senaryo][hata] += 1
            f[senaryo].append(kos_v8.ilk_alarm_farki(yanit, gercek["kesinti_gunu"]))
    ek = {"alarm_yok": {s: kos.oran([x is None for x in f[s]]) for s in f},
          "once_alarm": {s: kos.oran([x is not None and x < -15 for x in f[s]]) for s in f},
          "ilk_alarm_gecikme_medyan_gun": {s: statistics.median([x for x in f[s] if x is not None])
                                           for s in f if any(x is not None for x in f[s])},
          "hata": hatalar}
    return vaka, kos.degerlendir(vaka, v16_degerler(f)), ek


def olc(adet=None):
    vaka, olcutler, ek = v16(adet)
    return [{"kimlik": vaka["kimlik"], "ad": vaka["ad"],
             "tohum_adedi": adet or {s: d["tohumlar"]["adet"] for s, d in vaka["senaryolar"].items()},
             "olcutler": olcutler, "ek_olcumler": ek}]


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v9")
    ap.add_argument("--kilitle", action="store_true", help="v9 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v9/sonuclar/ altına yaz")
    ap.add_argument("--dogrula", action="store_true",
                    help="yeniden ölç ve kayıtlı sonuçla birebir karşılaştır")
    ap.add_argument("--tohum-adet", type=int, help="duman koşusu için az tohum (kaydedilmez)")
    a = ap.parse_args()
    if a.kilitle:
        return kilitle()
    kilit = kilit_dogrula()
    if a.tohum_adet and (a.kaydet or a.dogrula):
        sys.exit("--tohum-adet yalnız duman koşusu içindir; kaydet/doğrula ile kullanılamaz")
    vakalar = olc(a.tohum_adet)
    kos_v3.tablo_yaz(vakalar)
    if a.dogrula:
        with open(SONUC, encoding="utf-8") as f:
            kayitli = json.load(f)["vakalar"]
        if kayitli != vakalar:
            print("\nDOĞRULAMA BAŞARISIZ: yeniden ölçüm kayıtlı sonuçtan farklı "
                  "(determinizm bozuk ya da kod değişti)", file=sys.stderr)
            return 1
        print("\nDOĞRULAMA: yeniden ölçüm kayıtlı sonuçla birebir aynı")
    if a.kaydet:
        os.makedirs(os.path.dirname(SONUC), exist_ok=True)
        kayit = {"surum": kilit["surum"], "kilit": kilit["dosyalar"],
                 "ortam": {"python": platform.python_version(), "sistem": platform.system()},
                 "vakalar": vakalar}
        with open(SONUC, "w", encoding="utf-8", newline="\n") as f:
            json.dump(kayit, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\nkaydedildi: {os.path.relpath(SONUC, KOK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
