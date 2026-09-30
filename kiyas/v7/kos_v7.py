# -*- coding: utf-8 -*-
r"""
kiyas/v7/kos_v7.py — Bilimsel Muhakeme Kıyası v7 koşucusu (V13, ETKİ).

v7 önceki sürümlere DOKUNMADAN eklenir; v3'ün sözleşme kodunu (cagir,
ozet_cikar, oran, dagilim, tablo_yaz) ve v4'ün DESTEKSIZ kümesini içe aktarır —
hepsi v7 kilidindedir. Senaryonun "argumanlar" alanı "tam" ya da "kontrolsuz"
başvurusudur; koşucu çağrıdan önce vaka dosyasındaki argumanlar_tam'dan çözer.

Kullanım (depo kökünden):
    python kiyas/v7/kos_v7.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v7/kos_v7.py --kaydet     # + kiyas/v7/sonuclar/v7.json
    python kiyas/v7/kos_v7.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v7/kos_v7.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)
"""
import argparse
import hashlib
import json
import os
import platform
import sys

V7 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V7)
sys.path.insert(0, KIYAS)
sys.path.insert(0, os.path.join(KIYAS, "v3"))
sys.path.insert(0, os.path.join(KIYAS, "v4"))
sys.path.insert(0, V7)

import kos  # noqa: E402  (v0 — kilitli)
import kos_v3  # noqa: E402  (v3 sözleşme kodu — kilitli)
import kos_v4  # noqa: E402  (v4 yardımcıları — kilitli)
import uretec_v7  # noqa: E402

KOK = kos.KOK
KILIT = os.path.join(V7, "kilit.json")
SONUC = os.path.join(V7, "sonuclar", "v7.json")
KILITLI = ["kiyas/v7/vakalar/v13_etki.json", "kiyas/v7/uretec_v7.py", "kiyas/v7/kos_v7.py",
           "kiyas/v4/kos_v4.py", "kiyas/v4/uretec_v4.py", "kiyas/v3/kos_v3.py",
           "kiyas/v3/uretec_v3.py", "kiyas/v2/uretec_v2.py", "kiyas/uretec.py", "kiyas/kos.py"]
SENARYOLAR = ("gercek_etki", "genel_dusus", "ortalamaya_donus", "yer_degistirme",
              "kontrolsuz", "etkisiz", "etkisiz_nb")


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256, 8'li gruplar ("sha256:xxxxxxxx:…") —
    düz onaltılık özet veri bekçisinin telefon kuralına takılabiliyor (v6)."""
    with open(os.path.join(KOK, yol), "rb") as f:
        h = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    return "sha256:" + ":".join(h[i:i + 8] for i in range(0, 64, 8))


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v7 ön-kayıt kilidi yok: önce `python kiyas/v7/kos_v7.py --kilitle`")
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
    """v7 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v7 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v7",
             "ilke": "Bu dosyalar ilk v7 ölçümünden ve ETKİ uygulamasından ÖNCE kilitlendi; "
                     "değişirlerse koşucu ölçmeyi reddeder. v0/v2/v3/v4 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v7 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku():
    with open(os.path.join(V7, "vakalar", "v13_etki.json"), encoding="utf-8") as f:
        return json.load(f)


def cagri_vakasi(vaka):
    """Senaryoların argüman başvurularını ("tam"/"kontrolsuz") çözer (kos_v3.cagir için)."""
    tam = vaka["argumanlar_tam"]
    kontrolsuz = {k: tam[k] for k in ("bolge_alan", "mudahale", "kesinti_tarihi")}
    return {"arac": vaka["arac"],
            "senaryolar": {s: {**d, "argumanlar": tam if d["argumanlar"] == "tam" else kontrolsuz}
                           for s, d in vaka["senaryolar"].items()}}


def tohumlar(vaka, senaryo, adet=None):
    t = vaka["senaryolar"][senaryo]["tohumlar"]
    return list(range(t["bas"], t["bas"] + (min(adet, t["adet"]) if adet else t["adet"])))


def degerler_uret(k):
    """k: {senaryo: [ozet]} → ön-kayıtlı ölçüt değerleri."""
    def desteksiz(s):
        return kos_v3.oran([o["kategori"] in kos_v4.DESTEKSIZ for o in k[s]])

    def tutulan(s):
        return [o for o in k[s] if o["birincil"] == "tutuldu"]
    return {
        "K13.1": kos_v3.oran([o["kategori"] == "DESTEKLENDİ" for o in k["gercek_etki"]]),
        "K13.2": desteksiz("genel_dusus"),
        "K13.3": desteksiz("ortalamaya_donus"),
        "K13.4": kos_v3.oran([o["rakip"] == "R-ORTALAMAYA-DONUS" for o in tutulan("ortalamaya_donus")]),
        "K13.5": desteksiz("yer_degistirme"),
        "K13.6": kos_v3.oran([o["rakip"] == "R-YER-DEGISTIRME" for o in tutulan("yer_degistirme")]),
        "K13.7": kos_v3.oran([o["kategori"] != "DESTEKLENDİ" for o in tutulan("kontrolsuz")]),
        "K13.8": desteksiz("etkisiz"),
        "K13.9": desteksiz("etkisiz_nb"),
    }


# ---------------------------------------------------------------- vaka

def v13(adet=None):
    vaka = vaka_oku()
    cv = cagri_vakasi(vaka)
    k, hatalar = {}, {}
    for senaryo in SENARYOLAR:
        p = uretec_v7.parametreler(vaka, senaryo)
        k[senaryo] = []
        for t in tohumlar(vaka, senaryo, adet):
            satirlar, _ = uretec_v7.v13_bolgeler(p, t)
            sonuc, hata = kos_v3.cagir(cv, senaryo, satirlar)
            if hata:
                hatalar.setdefault(senaryo, {}).setdefault(hata, 0)
                hatalar[senaryo][hata] += 1
            k[senaryo].append(kos_v3.ozet_cikar(sonuc))
    ek = {"kategori_dagilimi": {s: kos_v3.dagilim(k[s], "kategori") for s in SENARYOLAR},
          "en_guclu_rakip": {s: kos_v3.dagilim(k[s], "rakip") for s in SENARYOLAR},
          "kontrolsuz_kirilgan_orani": kos_v3.oran([o["kategori"] == "KIRILGAN" for o in k["kontrolsuz"]]),
          "hata_ya_da_yok": hatalar}
    return vaka, kos.degerlendir(vaka, degerler_uret(k)), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    vaka, olcutler, ek = v13(adet)
    return [{"kimlik": vaka["kimlik"], "ad": vaka["ad"],
             "tohum_adedi": adet or {s: vaka["senaryolar"][s]["tohumlar"]["adet"] for s in SENARYOLAR},
             "olcutler": olcutler, "ek_olcumler": ek}]


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v7")
    ap.add_argument("--kilitle", action="store_true", help="v7 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v7/sonuclar/ altına yaz")
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
