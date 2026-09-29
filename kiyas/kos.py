# -*- coding: utf-8 -*-
r"""
kiyas/kos.py — Bilimsel Muhakeme Kıyası (BMK) koşucusu (A3, v0: çekirdek düzeyi).

Kullanım (depo kökünden):
    python kiyas/kos.py                 # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/kos.py --kaydet        # + kiyas/sonuclar/<surum>.json
    python kiyas/kos.py --dogrula       # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/kos.py --kilitle       # ön-kayıt kilidini yaz (yalnız ilk kez)

Ön-kayıt: vakalar, üreteç ve bu koşucu ilk ölçümden ÖNCE kiyas/kilit.json'da
SHA-256 ile kilitlenir. Kilitli bir dosya değişmişse koşucu ölçmeyi reddeder:
eşikleri ya da gerçeği sonucu gördükten sonra ayarlamak bu kıyası
anlamsızlaştırır. Değişiklik gerekiyorsa yeni sürüm açılır ve gerekçesi yazılır.

Başarısız bir ölçüt bir BULGUDUR, koşucunun hatası değil: kıyas ölçer,
kapı değildir. CI yalnız koşucunun çalıştığını, kilidin sağlam olduğunu ve
sonuçların kayıtlı olanla birebir aynı (deterministik) olduğunu denetler.

Araçlar MCP ile BİREBİR aynı boru hattından çağrılır: sinama.arayuz.sunucu.
arac_calistir (şema + gate + istek bağlamı + meta). Oturum/log yazımı depo
dışında geçici bir dizine yönlendirilir.
"""
import argparse
import atexit
import hashlib
import json
import os
import platform
import shutil
import statistics
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIYAS = os.path.join(KOK, "kiyas")
KILIT = os.path.join(KIYAS, "kilit.json")
SONUC_DIZINI = os.path.join(KIYAS, "sonuclar")
KILITLI = ["kiyas/vakalar/v1_kumelenme.json", "kiyas/vakalar/v2_bildirim.json",
           "kiyas/vakalar/v3_seri.json", "kiyas/uretec.py", "kiyas/kos.py"]

_GECICI = tempfile.mkdtemp(prefix="bmk_")
atexit.register(shutil.rmtree, _GECICI, ignore_errors=True)
os.environ["SINAMA_LOG_DIR"] = os.path.join(_GECICI, "log")
os.environ["SINAMA_VERI_KOKU"] = os.path.join(_GECICI, "veri")
os.makedirs(os.environ["SINAMA_LOG_DIR"], exist_ok=True)
os.makedirs(os.environ["SINAMA_VERI_KOKU"], exist_ok=True)
sys.path.insert(0, os.path.join(KOK, "cekirdek"))
sys.path.insert(0, KIYAS)

import sinama  # noqa: E402
from sinama.arayuz import sunucu  # noqa: E402
from sinama.arayuz.ortak import ARACLAR  # noqa: E402
import uretec  # noqa: E402

if os.path.commonpath([os.path.abspath(sinama.__file__), KOK]) != KOK:
    sys.exit(f"sinama bu depodan gelmiyor: {sinama.__file__}")


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Dosyanın satır sonu normalleştirilmiş SHA-256'sı (CRLF checkout'u bozmasın)."""
    with open(os.path.join(KOK, yol), "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("ön-kayıt kilidi yok: önce `python kiyas/kos.py --kilitle`")
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
    """Ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("kilit zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v0",
             "ilke": "Bu dosyalar ilk ölçümden ÖNCE kilitlendi; sonuç görüldükten "
                     "sonra değişirlerse koşucu ölçmeyi reddeder.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"kilit yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku(ad):
    with open(os.path.join(KIYAS, "vakalar", ad), encoding="utf-8") as f:
        return json.load(f)


def tohumlar(vaka, adet=None):
    t = vaka["tohumlar"]
    return list(range(t["bas"], t["bas"] + (adet or t["adet"])))


def arac(ad, satirlar, **arg):
    """Aracı resmi gömülü giriş noktasından çağırır; {sonuc, meta} döner."""
    return sunucu.arac_calistir(ad, {"satirlar": satirlar, **arg})


def km(a_lat, a_lon, b_lat, b_lon):
    """Şehir ölçeğinde eşdikdörtgen uzaklık (km)."""
    return (((a_lat - b_lat) / uretec.KM_ENLEM) ** 2
            + ((a_lon - b_lon) / uretec.KM_BOYLAM_41) ** 2) ** 0.5


def oran(bayraklar):
    return round(sum(1 for b in bayraklar if b) / len(bayraklar), 4) if bayraklar else 0.0


def degerlendir(vaka, degerler):
    """Ölçülen değerleri spesifikasyondaki eşiklerle karşılaştırır."""
    sonuc = []
    for o in vaka["cekirdek_olcutleri"]:
        d = degerler[o["kimlik"]]
        gecti = d >= o["esik"] if o["yon"] == ">=" else d <= o["esik"]
        sonuc.append({"kimlik": o["kimlik"], "deger": d, "yon": o["yon"],
                      "esik": o["esik"], "gecti": gecti,
                      "ongoru": vaka.get("ongoruler", {}).get(o["kimlik"])})
    return sonuc


# ---------------------------------------------------------------- vakalar

def v1(adet=None):
    vaka = vaka_oku("v1_kumelenme.json")
    p = vaka["uretec"]["parametreler"]
    b = {k: [] for k in ("nni_o", "nni_c", "mor_o", "mor_c", "gi_o", "gi_c")}
    sicak_c, hucre_c, nni_ort = [], [], {"odakli": [], "csr": []}
    for t in tohumlar(vaka, adet):
        for varyant in ("odakli", "csr"):
            satirlar, gercek = uretec.v1_kumelenme(p, t, varyant)
            k = "o" if varyant == "odakli" else "c"
            nni = arac("nni", satirlar)["sonuc"]
            b["nni_" + k].append(nni["nni"] < 1 and nni["p"] < 0.05)
            nni_ort[varyant].append(nni["nni"])
            mor = arac("mekansal_kumelenme", satirlar)["sonuc"]
            b["mor_" + k].append("I" in mor and mor["I"] > mor["beklenen"] and mor["p"] < 0.05)
            gi = arac("sicak_nokta_gi", satirlar)["sonuc"]
            sicaklar = [h for h in gi.get("sonuclar", []) if h["tur"] == "sıcak"]
            if varyant == "odakli":
                olat, olon = gercek["odak"]
                b["gi_o"].append(any(km(h["lat"], h["lon"], olat, olon) <= 0.4 for h in sicaklar))
            else:
                b["gi_c"].append(len(sicaklar) > 0)
                sicak_c.append(len(sicaklar))
                hucre_c.append(gi.get("n", 0))
    degerler = {"K1.1": oran(b["nni_o"]), "K1.2": oran(b["nni_c"]),
                "K1.3": oran(b["mor_o"]), "K1.4": oran(b["mor_c"]),
                "K1.5": oran(b["gi_o"]), "K1.6": oran(b["gi_c"])}
    ek = {"csr_ortalama_sicak_hucre": round(statistics.mean(sicak_c), 4),
          "csr_ortalama_test_edilen_hucre": round(statistics.mean(hucre_c), 4),
          "ortalama_nni": {v: round(statistics.mean(x), 4) for v, x in nni_ort.items()}}
    return vaka, degerlendir(vaka, degerler), ek


def v2(adet=None):
    vaka = vaka_oku("v2_bildirim.json")
    p = vaka["uretec"]["parametreler"]
    k21, k22, k23, k24, gecikmeler = [], [], [], [], []
    for t in tohumlar(vaka, adet):
        satirlar, gercek = uretec.v2_bildirim(p, t)
        alarmlar = arac("cusum", satirlar)["sonuc"]
        ilk = alarmlar[0]["gun"] if alarmlar else None
        gecikme = None if ilk is None else ilk - gercek["kesinti_gunu"]
        gecikmeler.append(gecikme)
        k21.append(gecikme is not None and -15 <= gecikme <= 60)
        k22.append(arac("trend", satirlar)["sonuc"].get("yorum") == "artan")
        karakol = [s for s in satirlar if s["kanal"] == "karakol"]
        k23.append(arac("trend", karakol)["sonuc"].get("yorum") in ("artan", "azalan"))
        tablo = arac("capraz_tablo", satirlar, a="kanal", b="yil")["sonuc"]
        yillar = sorted({y for d in tablo.values() for y in d})
        y0, y1 = yillar[0], yillar[-1]
        kar0, kar1 = tablo.get("karakol", {}).get(y0, 0), tablo.get("karakol", {}).get(y1, 0)
        cev1 = tablo.get("cevrimici", {}).get(y1, 0) - tablo.get("cevrimici", {}).get(y0, 0)
        artis = (kar1 + tablo.get("cevrimici", {}).get(y1, 0)) - (kar0 + tablo.get("cevrimici", {}).get(y0, 0))
        k24.append(kar0 > 0 and abs(kar1 - kar0) / kar0 <= 0.15 and artis > 0 and cev1 >= 0.8 * artis)
    its_acik = 1.0 if any(ad in ARACLAR for ad in ("kesinti_analizi", "kesintili_zaman_serisi")) else 0.0
    degerler = {"K2.1": oran(k21), "K2.2": oran(k22), "K2.3": oran(k23),
                "K2.4": oran(k24), "K2.5": its_acik}
    gecerli = [g for g in gecikmeler if g is not None]
    ek = {"cusum_ilk_alarm_gecikme_medyan_gun": statistics.median(gecerli) if gecerli else None,
          "cusum_alarm_vermeyen_tohum": sum(1 for g in gecikmeler if g is None)}
    return vaka, degerlendir(vaka, degerler), ek


def _uyari_var(paket):
    """Sonuç ya da meta, benzerliğin aynı fail/kimlik anlamına gelmediğini söylüyor mu."""
    metin = json.dumps(paket["meta"].get("uyarilar", []), ensure_ascii=False).lower()
    if isinstance(paket["sonuc"], dict):
        metin += json.dumps(paket["sonuc"], ensure_ascii=False).lower()
    return "fail" in metin or "kimlik" in metin


def v3(adet=None):
    vaka = vaka_oku("v3_seri.json")
    p = vaka["uretec"]["parametreler"]
    geri, kesin, isaret, yanlis_ortak, uyari, onay = [], [], [], [], [], []
    for t in tohumlar(vaka, adet):
        satirlar, gercek = uretec.v3_seri(p, t)
        paket = arac("seri_eslestirme", satirlar, mo_alan="mo")
        ciftler = {frozenset((c["id1"], c["id2"])) for c in paket["sonuc"]}
        seri = gercek["seri"]
        dogru = {frozenset((a, b)) for i, a in enumerate(seri) for b in seri[i + 1:]}
        bulunan = ciftler & dogru
        geri.append(len(bulunan) / len(dogru))
        kesin.append(len(bulunan) / len(ciftler) if ciftler else 0.0)
        isaret.append(len(ciftler))
        yanlis_ortak.append(sum(1 for c in ciftler
                                if all(gercek["grup"][x] == "ortak_mo" for x in c)))
        uyari.append(_uyari_var(paket))
        onay.append(bool(paket["meta"].get("insan_onayi_gerekir")))
    degerler = {"K3.1": round(statistics.mean(geri), 4), "K3.2": round(statistics.mean(kesin), 4),
                "K3.3": 1.0 if all(uyari) else 0.0, "K3.4": 1.0 if all(onay) else 0.0}
    ek = {"ortalama_isaretlenen_cift": round(statistics.mean(isaret), 4),
          "ortalama_ortak_mo_yanlis_cift": round(statistics.mean(yanlis_ortak), 4)}
    return vaka, degerlendir(vaka, degerler), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    """Üç vakayı koşar; kayıt biçiminde sonuç döner."""
    vakalar = []
    for islev in (v1, v2, v3):
        vaka, olcutler, ek = islev(adet)
        vakalar.append({"kimlik": vaka["kimlik"], "ad": vaka["ad"],
                        "tohum_adedi": adet or vaka["tohumlar"]["adet"],
                        "olcutler": olcutler, "ek_olcumler": ek})
    return vakalar


def tablo_yaz(vakalar):
    for v in vakalar:
        gecen = sum(1 for o in v["olcutler"] if o["gecti"])
        print(f"\n{v['kimlik']} — {v['ad']}  ({gecen}/{len(v['olcutler'])} ölçüt, "
              f"{v['tohum_adedi']} tohum)")
        for o in v["olcutler"]:
            isaret = "GEÇTİ " if o["gecti"] else "KALDI "
            ong = ""
            if o["ongoru"]:
                ong = "  [öngörü: başarısız → " + ("DOĞRULANDI]" if not o["gecti"] else "YANLIŞ ÇIKTI]")
            print(f"  {o['kimlik']:5s} {isaret} değer={o['deger']:<7} eşik {o['yon']} {o['esik']}{ong}")
        print(f"  ek: {json.dumps(v['ek_olcumler'], ensure_ascii=False)}")


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v0")
    ap.add_argument("--kilitle", action="store_true", help="ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/sonuclar/ altına yaz")
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
    yol = os.path.join(SONUC_DIZINI, f"{kilit['surum']}.json")
    if a.dogrula:
        with open(yol, encoding="utf-8") as f:
            kayitli = json.load(f)["vakalar"]
        if kayitli != vakalar:
            print("\nDOĞRULAMA BAŞARISIZ: yeniden ölçüm kayıtlı sonuçtan farklı "
                  "(determinizm bozuk ya da kod değişti)", file=sys.stderr)
            return 1
        print("\nDOĞRULAMA: yeniden ölçüm kayıtlı sonuçla birebir aynı")
    if a.kaydet:
        os.makedirs(SONUC_DIZINI, exist_ok=True)
        kayit = {"surum": kilit["surum"], "kilit": kilit["dosyalar"],
                 "ortam": {"python": platform.python_version(), "sistem": platform.system()},
                 "vakalar": vakalar}
        with open(yol, "w", encoding="utf-8", newline="\n") as f:
            json.dump(kayit, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\nkaydedildi: {os.path.relpath(yol, KOK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
