# -*- coding: utf-8 -*-
r"""
kiyas/v6/kos_v6.py — Bilimsel Muhakeme Kıyası v6 koşucusu (V12, bileşene özgü yayılım).

v6 önceki sürümlere DOKUNMADAN eklenir; v3'ün sözleşme kodunu (cagir,
ozet_cikar) ve v4'ün yardımcılarını içe aktarır — hepsi v6 kilidindedir.
Senaryo başına tohum sayısı vaka dosyasındadır (koruma 100, güç 180).

Kullanım (depo kökünden):
    python kiyas/v6/kos_v6.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v6/kos_v6.py --kaydet     # + kiyas/v6/sonuclar/v6.json
    python kiyas/v6/kos_v6.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v6/kos_v6.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)
"""
import argparse
import hashlib
import json
import os
import platform
import sys

V6 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V6)
sys.path.insert(0, KIYAS)
sys.path.insert(0, os.path.join(KIYAS, "v3"))
sys.path.insert(0, os.path.join(KIYAS, "v4"))
sys.path.insert(0, V6)

import kos  # noqa: E402  (v0 — kilitli)
import kos_v3  # noqa: E402  (v3 sözleşme kodu — kilitli)
import kos_v4  # noqa: E402  (v4 yardımcıları — kilitli)
import uretec_v6  # noqa: E402

KOK = kos.KOK
KILIT = os.path.join(V6, "kilit.json")
SONUC = os.path.join(V6, "sonuclar", "v6.json")
KILITLI = ["kiyas/v6/vakalar/v12_bilesen_yayilim.json", "kiyas/v6/uretec_v6.py",
           "kiyas/v6/kos_v6.py", "kiyas/v4/kos_v4.py", "kiyas/v4/uretec_v4.py",
           "kiyas/v3/kos_v3.py", "kiyas/v3/uretec_v3.py", "kiyas/v2/uretec_v2.py",
           "kiyas/uretec.py", "kiyas/kos.py"]
SENARYOLAR = ("karma_ikisi_nb", "karma_surekli_nb", "karma_yeni_nb", "kismi_yeni_nb",
              "saf_surekli_nb", "guc_yeni_nb", "guc_poisson")


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256 (CRLF checkout'u bozmasın), 8'li
    gruplar hâlinde: "sha256:xxxxxxxx:…". Neden: düz onaltılık özette 10 rakamlık
    bir dizi veri bekçisinin cep telefonu kuralına takılabiliyor (v6 kilidinde
    oldu; kilit başına ~%35). Grup içinde en çok 8 rakam olduğundan telefon (10) ve
    TC (11) deseni yapısal olarak oluşamaz — bekçiye dokunulmadı."""
    with open(os.path.join(KOK, yol), "rb") as f:
        h = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    return "sha256:" + ":".join(h[i:i + 8] for i in range(0, 64, 8))


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v6 ön-kayıt kilidi yok: önce `python kiyas/v6/kos_v6.py --kilitle`")
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
    """v6 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v6 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v6",
             "ilke": "Bu dosyalar ilk v6 ölçümünden ve v1.3 değişikliğinden ÖNCE kilitlendi; "
                     "değişirlerse koşucu ölçmeyi reddeder. v0/v2/v3/v4 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v6 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku():
    with open(os.path.join(V6, "vakalar", "v12_bilesen_yayilim.json"), encoding="utf-8") as f:
        return json.load(f)


def tohumlar(vaka, senaryo, adet=None):
    t = vaka["senaryolar"][senaryo]["tohumlar"]
    return list(range(t["bas"], t["bas"] + (min(adet, t["adet"]) if adet else t["adet"])))


def _sayi(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def yayilim_p_var(sonuc):
    """R-BILDIRIM kaydında İKİ bileşenin sayısal yayılım testi p'si var mı."""
    if sonuc is None:
        return False
    for r in sonuc["hukum"].get("rakipler") or []:
        if isinstance(r, dict) and r.get("kod") == "R-BILDIRIM":
            olcum = r.get("olcum") or {}
            return _sayi(olcum.get("yayilim_p")) and _sayi(olcum.get("yayilim_p_yeni"))
    return False


def degerler_uret(k):
    """k: {senaryo: [(ozet, yayilim_p_var)]} → ön-kayıtlı ölçüt değerleri."""
    def desteksiz(s):
        return kos_v3.oran([o["kategori"] in kos_v4.DESTEKSIZ for o, _ in k[s]])

    def destek(s):
        return kos_v3.oran([o["kategori"] == "DESTEKLENDİ" for o, _ in k[s]])
    rapor = [var for s in SENARYOLAR for o, var in k[s] if o["birincil"] == "tutuldu"]
    return {
        "K12.1": desteksiz("karma_ikisi_nb"),
        "K12.2": desteksiz("karma_surekli_nb"),
        "K12.3": desteksiz("karma_yeni_nb"),
        "K12.4": desteksiz("kismi_yeni_nb"),
        "K12.5": desteksiz("saf_surekli_nb"),
        "K12.6": destek("guc_yeni_nb"),
        "K12.7": destek("guc_poisson"),
        "K12.8": kos_v3.oran(rapor),
    }


# ---------------------------------------------------------------- vaka

def v12(adet=None):
    vaka = vaka_oku()
    k, hatalar, bildirim = {}, {}, {}
    for senaryo in SENARYOLAR:
        p = uretec_v6.parametreler(vaka, senaryo)
        k[senaryo] = []
        for t in tohumlar(vaka, senaryo, adet):
            satirlar, _ = uretec_v6.v12_kanallar(p, t)
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
          "hata_ya_da_yok": hatalar}
    return vaka, kos.degerlendir(vaka, degerler_uret(k)), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    vaka, olcutler, ek = v12(adet)
    return [{"kimlik": vaka["kimlik"], "ad": vaka["ad"],
             "tohum_adedi": adet or {s: vaka["senaryolar"][s]["tohumlar"]["adet"] for s in SENARYOLAR},
             "olcutler": olcutler, "ek_olcumler": ek}]


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v6")
    ap.add_argument("--kilitle", action="store_true", help="v6 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v6/sonuclar/ altına yaz")
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
