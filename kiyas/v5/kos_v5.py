# -*- coding: utf-8 -*-
r"""
kiyas/v5/kos_v5.py — Bilimsel Muhakeme Kıyası v5 koşucusu (V11, yayılım çarpanı).

v5 önceki sürümlere DOKUNMADAN eklenir; v3'ün sözleşme kodunu (cagir,
ozet_cikar) ve v4'ün yardımcılarını içe aktarır — hepsi v5 kilidindedir.
Senaryo başına tohum sayısı vaka dosyasındadır (güç senaryosu 200).

Kullanım (depo kökünden):
    python kiyas/v5/kos_v5.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v5/kos_v5.py --kaydet     # + kiyas/v5/sonuclar/v5.json
    python kiyas/v5/kos_v5.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v5/kos_v5.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)
"""
import argparse
import hashlib
import json
import os
import platform
import sys

V5 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V5)
sys.path.insert(0, KIYAS)
sys.path.insert(0, os.path.join(KIYAS, "v3"))
sys.path.insert(0, os.path.join(KIYAS, "v4"))
sys.path.insert(0, V5)

import kos  # noqa: E402  (v0 — kilitli)
import kos_v3  # noqa: E402  (v3 sözleşme kodu — kilitli)
import kos_v4  # noqa: E402  (v4 yardımcıları — kilitli)
import uretec_v5  # noqa: E402

KOK = kos.KOK
KILIT = os.path.join(V5, "kilit.json")
SONUC = os.path.join(V5, "sonuclar", "v5.json")
KILITLI = ["kiyas/v5/vakalar/v11_yayilim.json", "kiyas/v5/uretec_v5.py", "kiyas/v5/kos_v5.py",
           "kiyas/v4/kos_v4.py", "kiyas/v4/uretec_v4.py", "kiyas/v3/kos_v3.py",
           "kiyas/v3/uretec_v3.py", "kiyas/v2/uretec_v2.py", "kiyas/uretec.py", "kiyas/kos.py"]
OLCUT_SENARYOLARI = ("kismi_artefakt", "karma", "gercek_artis_kucuk_kanal",
                     "saf_artefakt_nb", "kismi_artefakt_nb", "karma_nb")
SENARYOLAR = OLCUT_SENARYOLARI + ("gercek_artis_kucuk_kanal_nb",)


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256 (CRLF checkout'u bozmasın)."""
    with open(os.path.join(KOK, yol), "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v5 ön-kayıt kilidi yok: önce `python kiyas/v5/kos_v5.py --kilitle`")
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
    """v5 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v5 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v5",
             "ilke": "Bu dosyalar ilk v5 ölçümünden ve v1.2 değişikliğinden ÖNCE kilitlendi; "
                     "değişirlerse koşucu ölçmeyi reddeder. v0/v2/v3/v4 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v5 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku():
    with open(os.path.join(V5, "vakalar", "v11_yayilim.json"), encoding="utf-8") as f:
        return json.load(f)


def tohumlar(vaka, senaryo, adet=None):
    t = vaka["senaryolar"][senaryo]["tohumlar"]
    return list(range(t["bas"], t["bas"] + (min(adet, t["adet"]) if adet else t["adet"])))


def yayilim_p_var(sonuc):
    """R-BILDIRIM kaydında sayısal yayılım testi p'si (olcum.yayilim_p) var mı."""
    if sonuc is None:
        return False
    for r in sonuc["hukum"].get("rakipler") or []:
        if isinstance(r, dict) and r.get("kod") == "R-BILDIRIM":
            deger = (r.get("olcum") or {}).get("yayilim_p")
            return isinstance(deger, (int, float)) and not isinstance(deger, bool)
    return False


def degerler_uret(k):
    """k: {senaryo: [(ozet, yayilim_p_var)]} → ön-kayıtlı ölçüt değerleri."""
    def desteksiz(s):
        return kos_v3.oran([o["kategori"] in kos_v4.DESTEKSIZ for o, _ in k[s]])
    rapor = [var for s in OLCUT_SENARYOLARI for o, var in k[s] if o["birincil"] == "tutuldu"]
    return {
        "K11.1": desteksiz("kismi_artefakt"),
        "K11.2": desteksiz("karma"),
        "K11.3": kos_v3.oran([o["kategori"] == "DESTEKLENDİ" for o, _ in k["gercek_artis_kucuk_kanal"]]),
        "K11.4": desteksiz("saf_artefakt_nb"),
        "K11.5": desteksiz("kismi_artefakt_nb"),
        "K11.6": desteksiz("karma_nb"),
        "K11.7": kos_v3.oran(rapor),
    }


# ---------------------------------------------------------------- vaka

def v11(adet=None):
    vaka = vaka_oku()
    k, hatalar, bildirim = {}, {}, {}
    for senaryo in SENARYOLAR:
        p = uretec_v5.parametreler(vaka, senaryo)
        k[senaryo] = []
        for t in tohumlar(vaka, senaryo, adet):
            satirlar, _ = uretec_v5.v11_kanallar(p, t)
            sonuc, hata = kos_v3.cagir(vaka, senaryo, satirlar)
            if hata:
                hatalar.setdefault(senaryo, {}).setdefault(hata, 0)
                hatalar[senaryo][hata] += 1
            durum = kos_v4.bildirim_durumu(sonuc)
            bildirim.setdefault(senaryo, {})[durum] = bildirim.get(senaryo, {}).get(durum, 0) + 1
            k[senaryo].append((kos_v3.ozet_cikar(sonuc), yayilim_p_var(sonuc)))
    ek = {"kategori_dagilimi": {s: kos_v3.dagilim([o for o, _ in k[s]], "kategori")
                                for s in SENARYOLAR},
          "r_bildirim_durumu": {s: dict(sorted(v.items())) for s, v in bildirim.items()},
          "nb_guc_destek_orani": kos_v3.oran([o["kategori"] == "DESTEKLENDİ"
                                              for o, _ in k["gercek_artis_kucuk_kanal_nb"]]),
          "hata_ya_da_yok": hatalar}
    return vaka, kos.degerlendir(vaka, degerler_uret(k)), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    vaka, olcutler, ek = v11(adet)
    return [{"kimlik": vaka["kimlik"], "ad": vaka["ad"],
             "tohum_adedi": adet or {s: vaka["senaryolar"][s]["tohumlar"]["adet"] for s in SENARYOLAR},
             "olcutler": olcutler, "ek_olcumler": ek}]


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v5")
    ap.add_argument("--kilitle", action="store_true", help="v5 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v5/sonuclar/ altına yaz")
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
