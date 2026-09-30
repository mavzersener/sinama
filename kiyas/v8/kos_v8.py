# -*- coding: utf-8 -*-
r"""
kiyas/v8/kos_v8.py — Bilimsel Muhakeme Kıyası v8 koşucusu (V14 NNI, V15 CUSUM).

v8 önceki sürümlere DOKUNMADAN eklenir; v0'ın araç çağrısını ve değerlendiricisini
(kos.arac, kos.degerlendir, kos.oran) ve v3'ün tablo yazıcısını içe aktarır — hepsi
v8 kilidindedir. Araçlar resmi yoldan ve VARSAYILAN argümanlarla çağrılır (sade
kullanıcının göreceği hâl); araç hatası o tohumda iddia/alarm/uyarı YOK sayılır.

Kullanım (depo kökünden):
    python kiyas/v8/kos_v8.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v8/kos_v8.py --kaydet     # + kiyas/v8/sonuclar/v8.json
    python kiyas/v8/kos_v8.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v8/kos_v8.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)
"""
import argparse
import hashlib
import json
import os
import platform
import statistics
import sys

V8 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V8)
sys.path.insert(0, KIYAS)
sys.path.insert(0, os.path.join(KIYAS, "v3"))
sys.path.insert(0, V8)

import kos  # noqa: E402  (v0 — kilitli)
import kos_v3  # noqa: E402  (v3 tablo yazıcısı — kilitli)
import uretec_v8  # noqa: E402

KOK = kos.KOK
KILIT = os.path.join(V8, "kilit.json")
SONUC = os.path.join(V8, "sonuclar", "v8.json")
KILITLI = ["kiyas/v8/vakalar/v14_nni.json", "kiyas/v8/vakalar/v15_cusum.json",
           "kiyas/v8/uretec_v8.py", "kiyas/v8/kos_v8.py", "kiyas/v3/kos_v3.py",
           "kiyas/v3/uretec_v3.py", "kiyas/v2/uretec_v2.py", "kiyas/uretec.py", "kiyas/kos.py"]


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256, 8'li gruplar ("sha256:xxxxxxxx:…")."""
    with open(os.path.join(KOK, yol), "rb") as f:
        h = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    return "sha256:" + ":".join(h[i:i + 8] for i in range(0, 64, 8))


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v8 ön-kayıt kilidi yok: önce `python kiyas/v8/kos_v8.py --kilitle`")
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
    """v8 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v8 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v8",
             "ilke": "Bu dosyalar ilk v8 ölçümünden ve NNI/CUSUM uygulamasından ÖNCE kilitlendi; "
                     "değişirlerse koşucu ölçmeyi reddeder. v0/v3 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v8 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku(ad):
    with open(os.path.join(V8, "vakalar", ad), encoding="utf-8") as f:
        return json.load(f)


def tohumlar(vaka, senaryo, adet=None):
    t = vaka["senaryolar"][senaryo]["tohumlar"]
    return list(range(t["bas"], t["bas"] + (min(adet, t["adet"]) if adet else t["adet"])))


def cagir(ad, satirlar):
    """Aracı varsayılan argümanlarla çağırır. Returns: ({sonuc, meta} ya da None, hata türü)."""
    try:
        return kos.arac(ad, satirlar), None
    except Exception as e:   # noqa: BLE001 — hata bir bulgudur, koşucuyu durdurmaz
        return None, type(e).__name__


def nni_ozeti(yanit):
    """{nni, iddia: kümelenme|düzgün|None, uyari} — araç hatasında nni None, iddia/uyarı yok."""
    if yanit is None:
        return {"nni": None, "iddia": None, "uyari": False}
    s = yanit["sonuc"] or {}
    nni, p = s.get("nni"), s.get("p")
    iddia = None
    if nni is not None and p is not None and p < 0.05:
        iddia = "kümelenme" if nni < 1 else "düzgün" if nni > 1 else None
    return {"nni": nni, "iddia": iddia,
            "uyari": any("yerel" in u for u in yanit["meta"].get("uyarilar", []))}


def ilk_alarm_farki(yanit, kesinti_gunu):
    """İlk alarmın kesintiye göre gün farkı; alarm yoksa ya da hata varsa None."""
    if yanit is None or not yanit["sonuc"]:
        return None
    return yanit["sonuc"][0]["gun"] - kesinti_gunu


def v14_degerler(k):
    """k: {senaryo: [nni_ozeti]} → ön-kayıtlı ölçüt değerleri."""
    csr = [o["nni"] for o in k["csr"] if o["nni"] is not None]
    return {
        "K14.1": kos.oran([o["iddia"] is not None for o in k["csr"]]),
        "K14.2": round(abs(statistics.fmean(csr) - 1), 4) if csr else 1.0,
        "K14.3": kos.oran([o["iddia"] is not None for o in k["csr_kucuk"]]),
        "K14.4": kos.oran([o["iddia"] == "kümelenme" for o in k["kume"]]),
        "K14.5": kos.oran([o["iddia"] == "kümelenme" for o in k["kume_kucuk"]]),
        "K14.6": kos.oran([o["uyari"] for o in k["odak"]]),
    }


def v15_degerler(f):
    """f: {senaryo: [ilk alarm farkı ya da None]} → ön-kayıtlı ölçüt değerleri."""
    return {
        "K15.1": kos.oran([x is not None for x in f["sabit"]]),
        "K15.2": kos.oran([x is not None for x in f["sabit_nb"]]),
        "K15.3": kos.oran([x is not None for x in f["sabit_dusuk"]]),
        "K15.4": kos.oran([x is not None and -15 <= x <= 180 for x in f["artis30"]]),
        "K15.5": kos.oran([x is not None and -15 <= x <= 90 for x in f["artis50"]]),
        "K15.6": kos.oran([x is None or x >= -15 for x in f["artis30_nb"]]),
    }


# ---------------------------------------------------------------- vakalar

def v14(adet=None):
    vaka = vaka_oku("v14_nni.json")
    k, hatalar = {}, {}
    for senaryo in vaka["senaryolar"]:
        p = uretec_v8.parametreler(vaka, senaryo)
        k[senaryo] = []
        for t in tohumlar(vaka, senaryo, adet):
            yanit, hata = cagir("nni", uretec_v8.v14_noktalar(p, t)[0])
            if hata:
                hatalar.setdefault(senaryo, {}).setdefault(hata, 0)
                hatalar[senaryo][hata] += 1
            k[senaryo].append(nni_ozeti(yanit))
    ek = {"ortalama_nni": {s: round(statistics.fmean([o["nni"] for o in k[s] if o["nni"] is not None]), 4)
                           for s in k if any(o["nni"] is not None for o in k[s])},
          "duzgun_iddiasi": {s: kos.oran([o["iddia"] == "düzgün" for o in k[s]]) for s in k},
          "kumelenme_iddiasi": {s: kos.oran([o["iddia"] == "kümelenme" for o in k[s]]) for s in k},
          "hata": hatalar}
    return vaka, kos.degerlendir(vaka, v14_degerler(k)), ek


def v15(adet=None):
    vaka = vaka_oku("v15_cusum.json")
    f, hatalar = {}, {}
    for senaryo in vaka["senaryolar"]:
        p = uretec_v8.parametreler(vaka, senaryo)
        f[senaryo] = []
        for t in tohumlar(vaka, senaryo, adet):
            satirlar, gercek = uretec_v8.v15_seri(p, t)
            yanit, hata = cagir("cusum", satirlar)
            if hata:
                hatalar.setdefault(senaryo, {}).setdefault(hata, 0)
                hatalar[senaryo][hata] += 1
            f[senaryo].append(ilk_alarm_farki(yanit, gercek["kesinti_gunu"]))
    ek = {"alarm_yok": {s: kos.oran([x is None for x in f[s]]) for s in f},
          "once_alarm": {s: kos.oran([x is not None and x < -15 for x in f[s]]) for s in f},
          "ilk_alarm_gecikme_medyan_gun": {s: statistics.median([x for x in f[s] if x is not None])
                                           for s in f if any(x is not None for x in f[s])},
          "hata": hatalar}
    return vaka, kos.degerlendir(vaka, v15_degerler(f)), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    sonuc = []
    for islev in (v14, v15):
        vaka, olcutler, ek = islev(adet)
        sonuc.append({"kimlik": vaka["kimlik"], "ad": vaka["ad"],
                      "tohum_adedi": adet or {s: d["tohumlar"]["adet"] for s, d in vaka["senaryolar"].items()},
                      "olcutler": olcutler, "ek_olcumler": ek})
    return sonuc


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v8")
    ap.add_argument("--kilitle", action="store_true", help="v8 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v8/sonuclar/ altına yaz")
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
