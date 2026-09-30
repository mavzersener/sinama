# -*- coding: utf-8 -*-
r"""
kiyas/v4/kos_v4.py — Bilimsel Muhakeme Kıyası v4 koşucusu (V10, hüküm sağlamlığı).

v4 önceki sürümlere DOKUNMADAN eklenir. Rehberli akışı v3'ün sözleşme kodunu
(kos_v3.cagir, kos_v3.ozet_cikar — kilitli ve testli) içe aktararak çağırır; v3
ve bağımlılıkları v4 kilidine dahildir. Araç yoksa ya da hata verirse hüküm
YOK sayılır; YOK hiçbir ölçütte doğru değildir.

Kullanım (depo kökünden):
    python kiyas/v4/kos_v4.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v4/kos_v4.py --kaydet     # + kiyas/v4/sonuclar/v4.json
    python kiyas/v4/kos_v4.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v4/kos_v4.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)
"""
import argparse
import hashlib
import json
import os
import platform
import sys

V4 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V4)
sys.path.insert(0, KIYAS)
sys.path.insert(0, os.path.join(KIYAS, "v3"))
sys.path.insert(0, V4)

import kos  # noqa: E402  (v0 koşucusu — kilitli)
import kos_v3  # noqa: E402  (v3 sözleşme kodu — kilitli)
import uretec_v4  # noqa: E402

KOK = kos.KOK
KILIT = os.path.join(V4, "kilit.json")
SONUC = os.path.join(V4, "sonuclar", "v4.json")
KILITLI = ["kiyas/v4/vakalar/v10_hukum_saglamligi.json", "kiyas/v4/uretec_v4.py",
           "kiyas/v4/kos_v4.py", "kiyas/v3/kos_v3.py", "kiyas/v3/uretec_v3.py",
           "kiyas/v2/uretec_v2.py", "kiyas/uretec.py", "kiyas/kos.py"]
SENARYOLAR = ("saf_artefakt", "kismi_artefakt", "karma", "gercek_artis_kucuk_kanal",
              "gercek_artis")
YENI_KANALLI = ("saf_artefakt", "kismi_artefakt", "karma", "gercek_artis_kucuk_kanal")
DESTEKSIZ = {"KIRILGAN", "BELİRSİZ", "ÇELİŞKİLİ"}


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256 (CRLF checkout'u bozmasın)."""
    with open(os.path.join(KOK, yol), "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v4 ön-kayıt kilidi yok: önce `python kiyas/v4/kos_v4.py --kilitle`")
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
    """v4 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v4 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v4",
             "ilke": "Bu dosyalar ilk v4 ölçümünden ve v1.1 değişikliğinden ÖNCE kilitlendi; "
                     "değişirlerse koşucu ölçmeyi reddeder. v0/v2/v3 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v4 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku():
    with open(os.path.join(V4, "vakalar", "v10_hukum_saglamligi.json"), encoding="utf-8") as f:
        return json.load(f)


def tohumlar(vaka, adet=None):
    t = vaka["tohumlar"]
    return list(range(t["bas"], t["bas"] + (adet or t["adet"])))


def bildirim_olcumu_var(sonuc):
    """R-BILDIRIM kaydında sayısal etki büyüklüğü (olcum.surekli_artis_payi) var mı."""
    if sonuc is None:
        return False
    for r in sonuc["hukum"].get("rakipler") or []:
        if isinstance(r, dict) and r.get("kod") == "R-BILDIRIM":
            deger = (r.get("olcum") or {}).get("surekli_artis_payi")
            return isinstance(deger, (int, float)) and not isinstance(deger, bool)
    return False


def bildirim_durumu(sonuc):
    if sonuc is None:
        return "YOK"
    for r in sonuc["hukum"].get("rakipler") or []:
        if isinstance(r, dict) and r.get("kod") == "R-BILDIRIM":
            return str(r.get("durum"))
    return "yok"


def degerler_uret(k):
    """k: {senaryo: [(ozet, olcum_var)]} → ön-kayıtlı ölçüt değerleri."""
    def ozetler(s):
        return [o for o, _ in k[s]]
    tutulan_kismi = [o for o in ozetler("kismi_artefakt") if o["birincil"] == "tutuldu"]
    olcum = [var for s in YENI_KANALLI for o, var in k[s] if o["birincil"] == "tutuldu"]
    return {
        "K10.1": kos_v3.oran([o["kategori"] in DESTEKSIZ for o in ozetler("saf_artefakt")]),
        "K10.2": kos_v3.oran([o["kategori"] in DESTEKSIZ for o in ozetler("kismi_artefakt")]),
        "K10.3": kos_v3.oran([o["rakip"] == "R-BILDIRIM" for o in tutulan_kismi]),
        "K10.4": kos_v3.oran([o["kategori"] in DESTEKSIZ for o in ozetler("karma")]),
        "K10.5": kos_v3.oran([o["kategori"] == "DESTEKLENDİ" for o in ozetler("gercek_artis_kucuk_kanal")]),
        "K10.6": kos_v3.oran([o["kategori"] == "DESTEKLENDİ" for o in ozetler("gercek_artis")]),
        "K10.7": kos_v3.oran(olcum),
    }


# ---------------------------------------------------------------- vaka

def v10(adet=None):
    vaka = vaka_oku()
    k, hatalar, bildirim = {}, {}, {}
    for senaryo in SENARYOLAR:
        p = uretec_v4.parametreler(vaka, senaryo)
        k[senaryo] = []
        for t in tohumlar(vaka, adet):
            satirlar, _ = uretec_v4.v10_kanallar(p, t)
            sonuc, hata = kos_v3.cagir(vaka, senaryo, satirlar)
            if hata:
                hatalar.setdefault(senaryo, {}).setdefault(hata, 0)
                hatalar[senaryo][hata] += 1
            d = bildirim.setdefault(senaryo, {})
            d[bildirim_durumu(sonuc)] = d.get(bildirim_durumu(sonuc), 0) + 1
            k[senaryo].append((kos_v3.ozet_cikar(sonuc), bildirim_olcumu_var(sonuc)))
    ek = {"kategori_dagilimi": {s: kos_v3.dagilim([o for o, _ in k[s]], "kategori")
                                for s in SENARYOLAR},
          "r_bildirim_durumu": {s: dict(sorted(v.items())) for s, v in bildirim.items()},
          "hata_ya_da_yok": hatalar}
    return vaka, kos.degerlendir(vaka, degerler_uret(k)), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    vaka, olcutler, ek = v10(adet)
    return [{"kimlik": vaka["kimlik"], "ad": vaka["ad"],
             "tohum_adedi": adet or vaka["tohumlar"]["adet"],
             "olcutler": olcutler, "ek_olcumler": ek}]


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v4")
    ap.add_argument("--kilitle", action="store_true", help="v4 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v4/sonuclar/ altına yaz")
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
