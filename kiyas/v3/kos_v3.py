# -*- coding: utf-8 -*-
r"""
kiyas/v3/kos_v3.py — Bilimsel Muhakeme Kıyası v3 koşucusu (ADR-002, kategorik hüküm).

v3 önceki sürümlere DOKUNMADAN eklenir. Rehberli akışı (rehberli_calisma) resmi
yoldan çağırır ve yalnız çıktı sözleşmesindeki alanları okur. Araç yoksa ya da
hata verirse hüküm YOK sayılır; YOK hiçbir ölçütte doğru değildir.

Kullanım (depo kökünden):
    python kiyas/v3/kos_v3.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v3/kos_v3.py --kaydet     # + kiyas/v3/sonuclar/v3.json
    python kiyas/v3/kos_v3.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v3/kos_v3.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)
"""
import argparse
import hashlib
import json
import os
import platform
import sys

V3 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V3)
sys.path.insert(0, KIYAS)
sys.path.insert(0, V3)

import kos  # noqa: E402  (v0 koşucusu — kilitli, değiştirilmez)
import uretec_v3  # noqa: E402

KOK = kos.KOK
KILIT = os.path.join(V3, "kilit.json")
SONUC = os.path.join(V3, "sonuclar", "v3.json")
KILITLI = ["kiyas/v3/vakalar/v9_hukum.json", "kiyas/v3/uretec_v3.py", "kiyas/v3/kos_v3.py",
           "kiyas/v2/uretec_v2.py", "kiyas/uretec.py", "kiyas/kos.py"]
SENARYOLAR = ("artefakt", "gercek_artis", "gercek_artis_kesifsel", "odakli", "csr",
              "seri", "seri_yok")
DESTEK_YOK = {"BELİRSİZ", "ÇELİŞKİLİ"}
YASAK = ("olasilik", "olasılık", "guven", "güven", "yuzde", "yüzde", "confidence",
         "probability", "posterior", "skor", "destek_orani")


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256 (CRLF checkout'u bozmasın)."""
    with open(os.path.join(KOK, yol), "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v3 ön-kayıt kilidi yok: önce `python kiyas/v3/kos_v3.py --kilitle`")
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
    """v3 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v3 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v3",
             "ilke": "Bu dosyalar ilk v3 ölçümünden ve bilim katmanının uygulanmasından ÖNCE "
                     "kilitlendi; değişirlerse koşucu ölçmeyi reddeder. v0/v2 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v3 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku(ad="v9_hukum.json"):
    with open(os.path.join(V3, "vakalar", ad), encoding="utf-8") as f:
        return json.load(f)


def tohumlar(vaka, adet=None):
    t = vaka["tohumlar"]
    return list(range(t["bas"], t["bas"] + (adet or t["adet"])))


def oran(bayraklar):
    return round(sum(1 for b in bayraklar if b) / len(bayraklar), 4) if bayraklar else 0.0


def cagir(vaka, senaryo, satirlar):
    """Rehberli akışı resmi yoldan çağırır. Returns: (sonuc ya da None, hata türü ya da None)."""
    s = vaka["senaryolar"][senaryo]
    arg = {"soru_turu": s["soru_turu"], "amac": s["amac"], **s["argumanlar"]}
    if s["amac"] == "dogrulayici":
        arg["onaylayan"] = "BMK v3"
    try:
        sonuc = kos.arac(vaka["arac"], satirlar, **arg)["sonuc"]
    except Exception as e:   # noqa: BLE001 — hata bir bulgudur, koşucuyu durdurmaz
        return None, type(e).__name__
    if not isinstance(sonuc, dict) or not isinstance(sonuc.get("hukum"), dict):
        return None, "sozlesme_disi"
    return sonuc, None


def _anahtarlar(nesne):
    """İç içe tüm sözlük anahtarları (küçük harfle)."""
    if isinstance(nesne, dict):
        for k, v in nesne.items():
            yield str(k).lower()
            yield from _anahtarlar(v)
    elif isinstance(nesne, list):
        for v in nesne:
            yield from _anahtarlar(v)


def ozet_cikar(sonuc):
    """Sözleşmedeki alanlardan tek koşunun özeti (sonuc None ise hüküm YOK)."""
    if sonuc is None:
        return {"kategori": "YOK", "birincil": None, "rakip": None, "rakipler": None,
                "onay": False, "bilinmeyen": False, "yasak_yok": False}
    h = sonuc["hukum"]
    rakipler = tuple(sorted((str(r.get("kod")), str(r.get("durum")))
                            for r in h.get("rakipler") or [] if isinstance(r, dict)))
    return {"kategori": h.get("kategori"), "birincil": h.get("birincil_ongoru"),
            "rakip": h.get("en_guclu_rakip"), "rakipler": rakipler,
            "onay": h.get("insan_onayi_gerekir") is True,
            "bilinmeyen": any(isinstance(x, dict) and x.get("tur") == "BILINMEYEN"
                              for x in sonuc.get("hipotezler") or []),
            "yasak_yok": not any(y in a for a in _anahtarlar(h) for y in YASAK)}


def cekirdek(o):
    """Belirlenimcilik için karşılaştırılan çekirdek hüküm."""
    return (o["kategori"], o["birincil"], o["rakip"], o["rakipler"])


def tavanli(ozetler, kategori):
    """Herhangi bir tohumda DESTEKLENDİ varsa 0, yoksa verilen kategorinin oranı."""
    if any(o["kategori"] == "DESTEKLENDİ" for o in ozetler):
        return 0.0
    return oran([o["kategori"] == kategori for o in ozetler])


def degerler_uret(kosular, ikinci_artefakt):
    """Senaryo özetlerinden ön-kayıtlı ölçüt değerleri."""
    k = kosular
    tutulan = [o for o in k["artefakt"] if o["birincil"] == "tutuldu"]
    hepsi = [o for s in SENARYOLAR for o in k[s]]
    return {
        "K9.1": oran([o["kategori"] in DESTEK_YOK for o in k["artefakt"]]),
        "K9.2": oran([o["rakip"] == "R-BILDIRIM" for o in tutulan]),
        "K9.3": oran([o["kategori"] == "DESTEKLENDİ" for o in k["gercek_artis"]]),
        "K9.4": tavanli(k["gercek_artis_kesifsel"], "KIRILGAN"),
        "K9.5": oran([o["kategori"] in ("DESTEKLENDİ", "KIRILGAN") for o in k["odakli"]]),
        "K9.6": oran([o["kategori"] in DESTEK_YOK for o in k["csr"]]),
        "K9.7": tavanli(k["seri"], "KIRILGAN"),
        "K9.8": oran([o["onay"] for o in k["seri"]]),
        "K9.9": oran([o["kategori"] in DESTEK_YOK for o in k["seri_yok"]]),
        "K9.10": oran([o["bilinmeyen"] for o in hepsi]),
        "K9.11": oran([o["kategori"] != "YOK" and o["yasak_yok"] for o in hepsi]),
        "K9.12": oran([a["kategori"] != "YOK" and cekirdek(a) == cekirdek(b)
                       for a, b in zip(k["artefakt"], ikinci_artefakt)]),
    }


def dagilim(ozetler, alan):
    d = {}
    for o in ozetler:
        d[str(o[alan])] = d.get(str(o[alan]), 0) + 1
    return dict(sorted(d.items()))


# ---------------------------------------------------------------- vaka

def v9(adet=None):
    vaka = vaka_oku()
    kosular, hatalar = {}, {}
    for senaryo in SENARYOLAR:
        kosular[senaryo] = []
        for t in tohumlar(vaka, adet):
            satirlar, _ = uretec_v3.uret(vaka, senaryo, t)
            sonuc, hata = cagir(vaka, senaryo, satirlar)
            if hata:
                hatalar.setdefault(senaryo, {}).setdefault(hata, 0)
                hatalar[senaryo][hata] += 1
            kosular[senaryo].append(ozet_cikar(sonuc))
    ikinci = []
    for t in tohumlar(vaka, adet):
        satirlar, _ = uretec_v3.uret(vaka, "artefakt", t)
        ikinci.append(ozet_cikar(cagir(vaka, "artefakt", satirlar)[0]))
    ek = {"kategori_dagilimi": {s: dagilim(kosular[s], "kategori") for s in SENARYOLAR},
          "artefakt_en_guclu_rakip": dagilim(kosular["artefakt"], "rakip"),
          "hata_ya_da_yok": hatalar}
    return vaka, kos.degerlendir(vaka, degerler_uret(kosular, ikinci)), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    vaka, olcutler, ek = v9(adet)
    return [{"kimlik": vaka["kimlik"], "ad": vaka["ad"],
             "tohum_adedi": adet or vaka["tohumlar"]["adet"],
             "olcutler": olcutler, "ek_olcumler": ek}]


def _ongoru_etiketi(o):
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
        for ad, ek in v["ek_olcumler"].items():
            print(f"  ek [{ad}]: {json.dumps(ek, ensure_ascii=False)}")


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v3")
    ap.add_argument("--kilitle", action="store_true", help="v3 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v3/sonuclar/ altına yaz")
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
