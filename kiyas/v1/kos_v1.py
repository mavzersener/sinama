# -*- coding: utf-8 -*-
r"""
kiyas/v1/kos_v1.py — Bilimsel Muhakeme Kıyası v1 koşucusu (A4).

v1, v0'a DOKUNMADAN eklenen ikinci ön-kayıtlı settir: v0'ın kilitli dosyaları,
sonuçları ve CI denetimi olduğu gibi kalır. Yardımcılar (arac, oran, km,
degerlendir; depo dışı ortam; bu depodan sinama) v0 koşucusundan DEĞİŞTİRİLMEDEN
içe aktarılır. Bağımlı olunan v0 dosyaları da v1 kilidine dahildir.

Kullanım (depo kökünden):
    python kiyas/v1/kos_v1.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v1/kos_v1.py --kaydet     # + kiyas/v1/sonuclar/v1.json
    python kiyas/v1/kos_v1.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v1/kos_v1.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)

Başarısız ölçüt bir BULGUDUR; kıyas kapı değildir (kiyas/README.md).
"""
import argparse
import hashlib
import json
import os
import platform
import statistics
import sys

V1 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V1)
sys.path.insert(0, KIYAS)
sys.path.insert(0, V1)

import kos  # noqa: E402  (v0 koşucusu — kilitli, değiştirilmez)
import uretec  # noqa: E402
import uretec_v1  # noqa: E402

KOK = kos.KOK
KILIT = os.path.join(V1, "kilit.json")
SONUC = os.path.join(V1, "sonuclar", "v1.json")
KILITLI = ["kiyas/v1/vakalar/v2b_kanal.json", "kiyas/v1/vakalar/v4_lisa.json",
           "kiyas/v1/vakalar/v5_yukselen.json", "kiyas/v1/vakalar/v6_anomali.json",
           "kiyas/v1/vakalar/v7_yayilan_seri.json", "kiyas/v1/uretec_v1.py",
           "kiyas/v1/kos_v1.py", "kiyas/uretec.py", "kiyas/kos.py"]
SICAK_TURLER = {"yeni sıcak nokta", "yoğunlaşan", "kalıcı"}
LISA_ANLAMLI = {"HH", "LL", "HL", "LH"}


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256 (CRLF checkout'u bozmasın)."""
    with open(os.path.join(KOK, yol), "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v1 ön-kayıt kilidi yok: önce `python kiyas/v1/kos_v1.py --kilitle`")
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
    """v1 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v1 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v1",
             "ilke": "Bu dosyalar ilk v1 ölçümünden ÖNCE kilitlendi; sonuç görüldükten "
                     "sonra değişirlerse koşucu ölçmeyi reddeder. v0 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v1 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku(ad):
    with open(os.path.join(V1, "vakalar", ad), encoding="utf-8") as f:
        return json.load(f)


def tohumlar(vaka, adet=None):
    t = vaka["tohumlar"]
    return list(range(t["bas"], t["bas"] + (adet or t["adet"])))


def ortalama(x):
    return round(statistics.mean(x), 4) if x else 0.0


# ---------------------------------------------------------------- vakalar

def v2b(adet=None):
    """K2.4'ün yerine: çapraz tablo sayımı ham sayımla birebir mi."""
    vaka = vaka_oku("v2b_kanal.json")
    p = vaka["uretec"]["parametreler"]
    esit = []
    for t in tohumlar(vaka, adet):
        satirlar, _ = uretec.v2_bildirim(p, t)
        tablo = kos.arac("capraz_tablo", satirlar, a="kanal", b="yil")["sonuc"]
        elle = {}
        for s in satirlar:
            elle.setdefault(s["kanal"], {}).setdefault(s["yil"], 0)
            elle[s["kanal"]][s["yil"]] += 1
        esit.append(tablo == elle)
    return vaka, kos.degerlendir(vaka, {"K2b.1": kos.oran(esit)}), {}


def v4(adet=None):
    """LISA gücü ve rastgele desende sahte küme/aykırı değer."""
    vaka = vaka_oku("v4_lisa.json")
    p = vaka["uretec"]["parametreler"]
    guc, alarm, sayilar, turler = [], [], [], {}
    for t in tohumlar(vaka, adet):
        for varyant in ("odakli", "csr"):
            satirlar, gercek = uretec.v1_kumelenme(p, t, varyant)
            sonuc = kos.arac("yerel_kumeleme", satirlar)["sonuc"]
            hucreler = sonuc.get("sonuclar", [])
            if varyant == "odakli":
                olat, olon = gercek["odak"]
                guc.append(any(h["kumeleme"] == "HH" and kos.km(h["lat"], h["lon"], olat, olon) <= 0.4
                               for h in hucreler))
            else:
                anlamli = [h for h in hucreler if h["kumeleme"] in LISA_ANLAMLI]
                alarm.append(bool(anlamli))
                sayilar.append(len(anlamli))
                for h in anlamli:
                    turler[h["kumeleme"]] = turler.get(h["kumeleme"], 0) + 1
    ek = {"csr_ortalama_anlamli_hucre": ortalama(sayilar), "csr_tur_dagilimi": turler}
    return vaka, kos.degerlendir(vaka, {"K4.1": kos.oran(guc), "K4.2": kos.oran(alarm)}), ek


def v5(adet=None):
    """Emerging hotspot: artan bölgeyi bulma ve homojende sahte sıcak nokta."""
    vaka = vaka_oku("v5_yukselen.json")
    p = vaka["uretec"]["parametreler"]
    guc, alarm, sayilar, dagilim, artan_disi = [], [], [], {}, []
    for t in tohumlar(vaka, adet):
        for varyant in ("homojen", "artan"):
            satirlar, gercek = uretec_v1.v5_yukselen(p, t, varyant)
            sonuc = kos.arac("yukselen_sicak_nokta", satirlar,
                             bolge_alan="bolge", zaman_alan="tarih")["sonuc"]
            kategori = {s["bolge"]: s["kategori"] for s in sonuc.get("sonuclar", [])}
            sicaklar = [b for b, k in kategori.items() if k in SICAK_TURLER]
            if varyant == "homojen":
                alarm.append(bool(sicaklar))
                sayilar.append(len(sicaklar))
                for b in sicaklar:
                    dagilim[kategori[b]] = dagilim.get(kategori[b], 0) + 1
            else:
                guc.append(kategori.get(gercek["artan"]) in ("yeni sıcak nokta", "yoğunlaşan"))
                artan_disi.append(any(b != gercek["artan"] for b in sicaklar))
    ek = {"homojen_ortalama_sicak_bolge": ortalama(sayilar), "homojen_kategori_dagilimi": dagilim,
          "artanda_gercek_disi_sicak_bolge_tohum_orani": kos.oran(artan_disi)}
    return vaka, kos.degerlendir(vaka, {"K5.1": kos.oran(guc), "K5.2": kos.oran(alarm)}), ek


def v6(adet=None):
    """Bölge anomalisi: gerçek anomaliyi bulma ve homojende sahte 'anlamli'."""
    vaka = vaka_oku("v6_anomali.json")
    p = vaka["uretec"]["parametreler"]
    guc, alarm, sayilar = [], [], []
    for t in tohumlar(vaka, adet):
        for varyant in ("homojen", "anomali"):
            satirlar, gercek = uretec_v1.v6_anomali(p, t, varyant)
            sonuc = kos.arac("bolge_anomali", satirlar, bolge_alan="bolge")["sonuc"]
            anlamli = {x["bolge"] for x in sonuc.get("anlamli", [])}
            if varyant == "homojen":
                alarm.append(bool(anlamli))
                sayilar.append(len(anlamli))
            else:
                guc.append(gercek["anomali"] in anlamli)
    ek = {"homojen_ortalama_anlamli_bolge": ortalama(sayilar)}
    return vaka, kos.degerlendir(vaka, {"K6.1": kos.oran(guc), "K6.2": kos.oran(alarm)}), ek


def v7(adet=None):
    """Yayılmış seri: varsayılan uzay-zaman süzgecinin geri çağırma bedeli."""
    vaka = vaka_oku("v7_yayilan_seri.json")
    p = vaka["uretec"]["parametreler"]
    geri, yanlis_ortak, isaret = [], [], []
    for t in tohumlar(vaka, adet):
        satirlar, gercek = uretec.v3_seri(p, t)
        paket = kos.arac("seri_eslestirme", satirlar, mo_alan="mo")
        ciftler = {frozenset((c["id1"], c["id2"])) for c in paket["sonuc"]}
        seri = gercek["seri"]
        dogru = {frozenset((a, b)) for i, a in enumerate(seri) for b in seri[i + 1:]}
        geri.append(len(ciftler & dogru) / len(dogru))
        yanlis_ortak.append(sum(1 for c in ciftler
                                if all(gercek["grup"][x] == "ortak_mo" for x in c)))
        isaret.append(len(ciftler))
    ek = {"ortalama_isaretlenen_cift": ortalama(isaret)}
    return vaka, kos.degerlendir(vaka, {"K7.1": ortalama(geri), "K7.2": ortalama(yanlis_ortak)}), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    """Beş vakayı koşar; kayıt biçiminde sonuç döner."""
    vakalar = []
    for islev in (v2b, v4, v5, v6, v7):
        vaka, olcutler, ek = islev(adet)
        vakalar.append({"kimlik": vaka["kimlik"], "ad": vaka["ad"],
                        "tohum_adedi": adet or vaka["tohumlar"]["adet"],
                        "olcutler": olcutler, "ek_olcumler": ek})
    return vakalar


def _ongoru_etiketi(o):
    """Öngörünün yönünü metninden okur (v1'de 'GEÇER beklenir' öngörüleri de var)."""
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
        if v["ek_olcumler"]:
            print(f"  ek: {json.dumps(v['ek_olcumler'], ensure_ascii=False)}")


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v1")
    ap.add_argument("--kilitle", action="store_true", help="v1 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v1/sonuclar/ altına yaz")
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
