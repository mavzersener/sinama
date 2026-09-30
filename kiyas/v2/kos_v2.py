# -*- coding: utf-8 -*-
r"""
kiyas/v2/kos_v2.py — Bilimsel Muhakeme Kıyası v2 koşucusu (A4, seri bağlantısı).

v2, v0 ve v1'e DOKUNMADAN eklenen üçüncü ön-kayıtlı settir. Yardımcılar (arac,
degerlendir; depo dışı ortam; bu depodan sinama) v0 koşucusundan değiştirilmeden
içe aktarılır; bağımlı olunan v0 dosyaları v2 kilidine dahildir.

Kullanım (depo kökünden):
    python kiyas/v2/kos_v2.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v2/kos_v2.py --kaydet     # + kiyas/v2/sonuclar/v2.json
    python kiyas/v2/kos_v2.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v2/kos_v2.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)

Başarısız ölçüt bir BULGUDUR; kıyas kapı değildir (kiyas/README.md).
"""
import argparse
import hashlib
import json
import os
import platform
import statistics
import sys

V2 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V2)
sys.path.insert(0, KIYAS)
sys.path.insert(0, V2)

import kos  # noqa: E402  (v0 koşucusu — kilitli, değiştirilmez)
import uretec_v2  # noqa: E402

KOK = kos.KOK
KILIT = os.path.join(V2, "kilit.json")
SONUC = os.path.join(V2, "sonuclar", "v2.json")
KILITLI = ["kiyas/v2/vakalar/v8_seri_katman.json", "kiyas/v2/uretec_v2.py",
           "kiyas/v2/kos_v2.py", "kiyas/uretec.py", "kiyas/kos.py"]
VARYANTLAR = ("siki", "yayilmis", "tutarsiz", "seri_yok")
KATMANLAR = {"güçlü", "zayıf"}
KANIT_HATLARI = {"mo", "uzay", "zaman"}


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256 (CRLF checkout'u bozmasın)."""
    with open(os.path.join(KOK, yol), "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v2 ön-kayıt kilidi yok: önce `python kiyas/v2/kos_v2.py --kilitle`")
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
    """v2 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v2 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v2",
             "ilke": "Bu dosyalar ilk v2 ölçümünden ÖNCE kilitlendi; sonuç görüldükten "
                     "sonra değişirlerse koşucu ölçmeyi reddeder. v0 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v2 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku(ad):
    with open(os.path.join(V2, "vakalar", ad), encoding="utf-8") as f:
        return json.load(f)


def tohumlar(vaka, adet=None):
    t = vaka["tohumlar"]
    return list(range(t["bas"], t["bas"] + (adet or t["adet"])))


def ortalama(x):
    return round(statistics.mean(x), 4) if x else 0.0


def havuz_oran(pay, payda):
    return round(pay / payda, 4) if payda else 0.0


def sozlesmeye_uyar(c):
    """Çift v2 çıktı sözleşmesine uyuyor mu: katman + üç kanıt hattı."""
    kanit = c.get("kanit")
    return (c.get("katman") in KATMANLAR and isinstance(kanit, dict)
            and KANIT_HATLARI <= set(kanit))


def tohum_olc(ciftler, gercek):
    """Tek tohumun ham sayımları. ciftler: aracın sonuc listesi.

    'katman' alanı olmayan çift GÜÇLÜ sayılır (vaka tanımı: derecelendirilmemiş
    aday analiste tam ağırlıkla sunulur)."""
    C = {frozenset((c["id1"], c["id2"])) for c in ciftler}
    G = {frozenset((c["id1"], c["id2"])) for c in ciftler
         if c.get("katman", "güçlü") == "güçlü"}
    seri = gercek["seri"]
    dogru = {frozenset((a, b)) for i, a in enumerate(seri) for b in seri[i + 1:]}
    grup = gercek["grup"]
    return {
        "geri": len(C & dogru) / len(dogru) if dogru else None,
        "c": len(C), "c_dogru": len(C & dogru),
        "g": len(G), "g_dogru": len(G & dogru),
        "g_ortak_yanlis": sum(1 for x in G if all(grup[k] == "ortak_mo" for k in x)),
        "sozlesme_uyan": sum(1 for c in ciftler if sozlesmeye_uyar(c)),
        "cift": len(ciftler),
    }


def ozetle(sayimlar):
    """Bir varyantın tohum sayımlarından ölçüt değerleri ve ek ölçümler."""
    toplam = {k: sum(s[k] for s in sayimlar)
              for k in ("c", "c_dogru", "g", "g_dogru", "sozlesme_uyan", "cift")}
    geri = [s["geri"] for s in sayimlar if s["geri"] is not None]
    return {
        "geri_cagirma": ortalama(geri),
        "kesinlik_c": havuz_oran(toplam["c_dogru"], toplam["c"]),
        "kesinlik_g": havuz_oran(toplam["g_dogru"], toplam["g"]),
        "g_ortak_yanlis": ortalama([s["g_ortak_yanlis"] for s in sayimlar]),
        "g_dolu_tohum": round(sum(1 for s in sayimlar if s["g"]) / len(sayimlar), 4),
        "ort_c": ortalama([s["c"] for s in sayimlar]),
        "ort_g": ortalama([s["g"] for s in sayimlar]),
        "dogru_g_katmaninda": toplam["g_dogru"],
        "dogru_zayif_katmanda": toplam["c_dogru"] - toplam["g_dogru"],
        "_sozlesme": (toplam["sozlesme_uyan"], toplam["cift"]),
    }


def degerler_uret(ozetler):
    """Varyant özetlerinden ön-kayıtlı ölçüt değerleri."""
    s, y, t, n = (ozetler[v] for v in VARYANTLAR)
    uyan = sum(o["_sozlesme"][0] for o in ozetler.values())
    tum = sum(o["_sozlesme"][1] for o in ozetler.values())
    return {"K8.1": s["geri_cagirma"], "K8.2": s["kesinlik_g"], "K8.3": s["kesinlik_c"],
            "K8.4": y["geri_cagirma"], "K8.5": y["kesinlik_c"], "K8.6": y["g_ortak_yanlis"],
            "K8.7": t["geri_cagirma"], "K8.8": t["kesinlik_c"],
            "K8.9": n["g_dolu_tohum"], "K8.10": havuz_oran(uyan, tum)}


# ---------------------------------------------------------------- vaka

def v8(adet=None):
    """Dört varyant × tohumlar: seri_eslestirme resmi yoldan, varsayılan argümanlarla."""
    vaka = vaka_oku("v8_seri_katman.json")
    ozetler = {}
    for varyant in VARYANTLAR:
        p = uretec_v2.parametreler(vaka, varyant)
        sayimlar = []
        for t in tohumlar(vaka, adet):
            satirlar, gercek = uretec_v2.v8_seri(p, t)
            paket = kos.arac("seri_eslestirme", satirlar, mo_alan="mo")
            sayimlar.append(tohum_olc(paket["sonuc"], gercek))
        ozetler[varyant] = ozetle(sayimlar)
    ek = {v: {k: x for k, x in o.items() if not k.startswith("_")}
          for v, o in ozetler.items()}
    return vaka, kos.degerlendir(vaka, degerler_uret(ozetler)), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    vaka, olcutler, ek = v8(adet)
    return [{"kimlik": vaka["kimlik"], "ad": vaka["ad"],
             "tohum_adedi": adet or vaka["tohumlar"]["adet"],
             "olcutler": olcutler, "ek_olcumler": ek}]


def _ongoru_etiketi(o):
    """Öngörünün yönünü metninden okur ('GEÇER' / 'BAŞARISIZ' ile başlar)."""
    if not o["ongoru"]:
        return ""
    beklenen_gecer = o["ongoru"].lstrip().upper().startswith("GEÇER")
    tuttu = o["gecti"] == beklenen_gecer
    return f"  [öngörü: {'geçer' if beklenen_gecer else 'başarısız'} → {'DOĞRULANDI' if tuttu else 'YANLIŞ ÇIKTI'}]"


def tablo_yaz(vakalar):
    for v in vakalar:
        gecen = sum(1 for o in v["olcutler"] if o["gecti"])
        print(f"\n{v['kimlik']} — {v['ad']}  ({gecen}/{len(v['olcutler'])} ölçüt, "
              f"{v['tohum_adedi']} tohum)")
        for o in v["olcutler"]:
            isaret = "GEÇTİ " if o["gecti"] else "KALDI "
            print(f"  {o['kimlik']:6s} {isaret} değer={o['deger']:<7} eşik {o['yon']} {o['esik']}"
                  f"{_ongoru_etiketi(o)}")
        for varyant, ek in v["ek_olcumler"].items():
            print(f"  ek [{varyant}]: {json.dumps(ek, ensure_ascii=False)}")


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v2")
    ap.add_argument("--kilitle", action="store_true", help="v2 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v2/sonuclar/ altına yaz")
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
    tablo_yaz(vakalar)
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
