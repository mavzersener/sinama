# -*- coding: utf-8 -*-
r"""
kiyas/v10/kos_v10.py — Bilimsel Muhakeme Kıyası v10 koşucusu (V17, A5 Rehberli arka uç).

v10 önceki sürümlere DOKUNMADAN eklenir; v3/v7 vakalarını ve üreteçlerini, v0'ın
değerlendiricisini ve v3'ün tablo yazıcısını içe aktarır — hepsi v10 kilidindedir.
Arka uç (`uygulama.sunucu`) süreç içinde FastAPI TestClient ile çağrılır; aynı veriyle
MCP `rehberli_calisma` başvuru hükmünü verir. Modül ya da uç yoksa ilgili ölçüt
başarısızdır (hata bir bulgudur, koşucuyu durdurmaz).

Kullanım (depo kökünden):
    python kiyas/v10/kos_v10.py              # kilidi doğrula, ölç, tabloyu yaz
    python kiyas/v10/kos_v10.py --kaydet     # + kiyas/v10/sonuclar/v10.json
    python kiyas/v10/kos_v10.py --dogrula    # yeniden ölç, kayıtlı sonuçla BİREBİR karşılaştır (CI)
    python kiyas/v10/kos_v10.py --kilitle    # ön-kayıt kilidini yaz (yalnız ilk kez)
"""
import argparse
import glob
import hashlib
import importlib
import json
import os
import platform
import re
import shutil
import sys
import tempfile

V10 = os.path.dirname(os.path.abspath(__file__))
KIYAS = os.path.dirname(V10)
for _alt in ("", "v3", "v4", "v7"):
    sys.path.insert(0, os.path.join(KIYAS, _alt))
sys.path.insert(0, V10)

import kos  # noqa: E402  (v0 — kilitli; ortamı depo dışına yönlendirir)
import kos_v3  # noqa: E402  (v3 — kilitli)
import kos_v7  # noqa: E402  (v7 — kilitli)
import uretec_v3  # noqa: E402
import uretec_v7  # noqa: E402
from sinama.bilim import hukum, rak, sablon  # noqa: E402
from sinama.surec import kilit as kilit_mod  # noqa: E402

KOK = kos.KOK
sys.path.insert(0, KOK)
KILIT = os.path.join(V10, "kilit.json")
SONUC = os.path.join(V10, "sonuclar", "v10.json")
KILITLI = ["kiyas/v10/vakalar/v17_rehberli_arka_uc.json", "kiyas/v10/kos_v10.py",
           "kiyas/v7/kos_v7.py", "kiyas/v7/uretec_v7.py", "kiyas/v7/vakalar/v13_etki.json",
           "kiyas/v4/kos_v4.py", "kiyas/v4/uretec_v4.py", "kiyas/v3/kos_v3.py",
           "kiyas/v3/uretec_v3.py", "kiyas/v3/vakalar/v9_hukum.json", "kiyas/v2/uretec_v2.py",
           "kiyas/uretec.py", "kiyas/kos.py"]
YASAK = kos_v3.YASAK
KARSILASTIR = ("kategori", "en_guclu_rakip", "rakipler", "kurallar", "paket_hash")
CEVIRI = os.path.join(KOK, "uygulama", "web", "src", "i18n")
KAYNAK = os.path.join(KOK, "uygulama", "web", "src")


# ---------------------------------------------------------------- kilit

def _ozet(yol):
    """Satır sonu normalleştirilmiş SHA-256, 8'li gruplar ("sha256:xxxxxxxx:…")."""
    with open(os.path.join(KOK, yol), "rb") as f:
        h = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    return "sha256:" + ":".join(h[i:i + 8] for i in range(0, 64, 8))


def kilit_dogrula():
    """Kilitli dosyalar değişmişse açıklamayla çıkar (kod 2)."""
    if not os.path.exists(KILIT):
        sys.exit("v10 ön-kayıt kilidi yok: önce `python kiyas/v10/kos_v10.py --kilitle`")
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
    """v10 ön-kayıt kilidini yazar; varsa üzerine yazmaz."""
    if os.path.exists(KILIT):
        sys.exit("v10 kilidi zaten var; ön-kayıt değiştirilemez (yeni sürüm gerekir)")
    kilit = {"surum": "v10",
             "ilke": "Bu dosyalar ilk v10 ölçümünden ve A5 arka ucundan ÖNCE kilitlendi; değişirlerse "
                     "koşucu ölçmeyi reddeder. v0/v2/v3/v4/v7 bağımlılıkları dahildir.",
             "dosyalar": {y: _ozet(y) for y in KILITLI}}
    with open(KILIT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kilit, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"v10 kilidi yazıldı: {len(KILITLI)} dosya")


# ---------------------------------------------------------------- yardımcılar

def vaka_oku():
    with open(os.path.join(V10, "vakalar", "v17_rehberli_arka_uc.json"), encoding="utf-8") as f:
        return json.load(f)


def akislar(vaka):
    """[(etiket, argümanlar, satırlar)] — v3 ve v7 senaryolarından, sabit tohumlarla."""
    sonuc = []
    v3 = kos_v3.vaka_oku()
    t3 = vaka["akislar"]["v3"]["tohumlar"]
    for s, d in v3["senaryolar"].items():
        for t in range(t3["bas"], t3["bas"] + t3["adet"]):
            arg = {"soru_turu": d["soru_turu"], "amac": d["amac"], **d["argumanlar"]}
            if d["amac"] == "dogrulayici":
                arg["onaylayan"] = vaka["akislar"]["onaylayan"]
            sonuc.append((f"v3/{s}/{t}", arg, uretec_v3.uret(v3, s, t)[0]))
    v7 = kos_v7.vaka_oku()
    cv = kos_v7.cagri_vakasi(v7)
    t7 = vaka["akislar"]["v7"]["tohumlar"]
    for s in vaka["akislar"]["v7"]["senaryolar"]:
        d = cv["senaryolar"][s]
        for t in range(t7["bas"], t7["bas"] + t7["adet"]):
            arg = {"soru_turu": d["soru_turu"], "amac": d["amac"], **d["argumanlar"]}
            if d["amac"] == "dogrulayici":
                arg["onaylayan"] = vaka["akislar"]["onaylayan"]
            satirlar, _ = uretec_v7.v13_bolgeler(uretec_v7.parametreler(v7, s), t)
            sonuc.append((f"v7/{s}/{t}", arg, satirlar))
    return sonuc


def depo_goruntusu():
    """Depodaki dosyaların (yol → (boyut, değişme zamanı)) görüntüsü; .git, node_modules,
    __pycache__ ve bu sürümün sonuç dizini hariç."""
    haric = {".git", "node_modules", "__pycache__"}
    sonuc_dizini = os.path.join(V10, "sonuclar")
    goruntu = {}
    for kok_, dizinler, dosyalar in os.walk(KOK):
        dizinler[:] = [d for d in dizinler if d not in haric
                       and os.path.join(kok_, d) != sonuc_dizini]
        for ad in dosyalar:
            if ad.endswith((".pyc", ".pyo")):
                continue
            yol = os.path.join(kok_, ad)
            try:
                st = os.stat(yol)
            except OSError:
                continue
            goruntu[os.path.relpath(yol, KOK).replace(os.sep, "/")] = (st.st_size, st.st_mtime_ns)
    return goruntu


def yasak_yok(nesne):
    """JSON yanıtının hiçbir anahtarında yasak sözcük yok mu."""
    return not any(y in a for a in kos_v3._anahtarlar(nesne) for y in YASAK)


def plan_tam(plan):
    """Plan ekranı alanları."""
    return (isinstance(plan, dict) and plan.get("ulasilabilir_en_ust") in hukum.KATEGORILER
            and isinstance(plan.get("rakipler"), list)
            and all(isinstance(r.get("cozulebilir"), bool) and r.get("kod") for r in plan["rakipler"]))


def hukum_tam(h):
    """Hüküm ekranı alanları."""
    return (isinstance(h, dict) and h.get("kategori") in hukum.KATEGORILER
            and isinstance(h.get("kurallar"), list) and len(h["kurallar"]) > 0
            and isinstance(h.get("rakipler"), list)
            and isinstance(h.get("sonraki_en_iyi_kanit"), list)
            and h.get("durum") == "taslak" and h.get("insan_onayi_gerekir") is True
            and "H_bilinmeyen" in str(h.get("ifade")))


def ceviri_denetle():
    """(tam mı, eksikler) — iki sözlük aynı anahtar kümesinde ve gerekli aileleri kapsıyor mu."""
    eksik = []
    sozluk = {}
    for dil in ("tr", "en"):
        yol = os.path.join(CEVIRI, f"{dil}.json")
        if not os.path.isfile(yol):
            return False, [f"{dil}.json yok"]
        with open(yol, encoding="utf-8") as f:
            sozluk[dil] = json.load(f)
    with open(hukum.__file__, encoding="utf-8") as f:
        kurallar = sorted(set(re.findall(r'kural\("([A-Za-z0-9-]+)"', f.read())))
    gerekli = ([f"kategori.{k}" for k in hukum.KATEGORILER] + [f"durum.{d}" for d in rak.DURUMLAR]
               + [f"birincil.{d}" for d in ("tutuldu", "karşıt", "belirsiz", "sınanamadı")]
               + [f"rakip.{k}" for k in rak.KATALOG] + [f"soru_turu.{t}" for t in sablon.TURLER]
               + [f"amac.{a}" for a in kilit_mod.AMACLAR] + [f"kural.{k}" for k in kurallar])
    for yol in sorted(glob.glob(os.path.join(KAYNAK, "**", "*.ts*"), recursive=True)):
        with open(yol, encoding="utf-8") as f:
            gerekli += re.findall(r"""\bt\(\s*['"]([^'"]+)['"]""", f.read())
    for dil, s in sozluk.items():
        eksik += [f"{dil}:{k}" for k in sorted(set(gerekli)) if not str(s.get(k) or "").strip()]
    fark = set(sozluk["tr"]) ^ set(sozluk["en"])
    eksik += [f"yalnız birinde:{k}" for k in sorted(fark)]
    return not eksik, eksik


# ---------------------------------------------------------------- vaka

def v17(adet=None):
    vaka = vaka_oku()
    hatalar = {}

    def hata(tur):
        hatalar[tur] = hatalar.get(tur, 0) + 1

    liste = akislar(vaka)
    if adet:
        liste = liste[:adet]
    once = depo_goruntusu()
    veri_koku = tempfile.mkdtemp(prefix="bmk_v10_")
    esdeger, ekran, yanitlar, tamam = [], [], [], []
    saglik, oneri_dogru, red, mod = None, 0, False, None
    try:
        mod = importlib.import_module("uygulama.sunucu")
        from fastapi.testclient import TestClient
        c = TestClient(mod.uygulama_olustur(veri_koku=veri_koku,
                                            dil_modeli_url=vaka["akislar"]["dil_modeli_url"]))
        r = c.get("/api/saglik")
        saglik = r.json() if r.status_code == 200 else None
        for soru, tur in vaka["oneri_sorulari"].items():
            r = c.post("/api/oneri", json={"soru": soru})
            if r.status_code == 200:
                yanitlar.append(r.json())
                oneri_dogru += r.json().get("soru_turu") == tur and r.json().get("kaynak") == "kural"
    except Exception as e:   # noqa: BLE001
        hata(type(e).__name__)
        c = None
    for etiket, arg, satirlar in liste:
        if c is None:
            esdeger.append(False), ekran.append(False), tamam.append(False)
            continue
        try:
            ref = kos.arac("rehberli_calisma", satirlar, **arg)["sonuc"]["hukum"]
            r1 = c.post("/api/calisma", json=arg)
            oid = r1.json()["oturum_id"]
            r2 = c.get(f"/api/calisma/{oid}/plan")
            r3 = c.post(f"/api/calisma/{oid}/kanit", json={"satirlar": satirlar})
            r4 = c.post(f"/api/calisma/{oid}/hukum")
            r5 = c.post(f"/api/calisma/{oid}/sonuc", json={"sonuc_turu": "izlemeye_alindi"})
            for r in (r1, r2, r3, r4):
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                yanitlar.append(r.json())
            h = r4.json()["hukum"]
            hip = r1.json().get("hipotezler") or []
            esdeger.append(all(h.get(k) == ref.get(k) for k in KARSILASTIR))
            ekran.append(bool(hip) and hip[-1].get("kimlik") == "H_bilinmeyen"
                         and plan_tam(r1.json().get("plan")) and plan_tam(r2.json())
                         and hukum_tam(h) and 400 <= r5.status_code < 500)
            tamam.append(True)
        except Exception as e:   # noqa: BLE001
            hata(type(e).__name__)
            esdeger.append(False), ekran.append(False), tamam.append(False)
    sonra = depo_goruntusu()
    yeni = sorted(y for y in sonra if once.get(y) != sonra[y])
    oturum_dosyasi = len(glob.glob(os.path.join(veri_koku, "oturumlar", "*.json")))
    if mod is not None:
        try:
            mod.uygulama_olustur(veri_koku=KOK, dil_modeli_url=None)
        except Exception:   # noqa: BLE001 — beklenen: depo içi veri kökü reddi
            try:
                mod.uygulama_olustur(veri_koku=os.path.join(KOK, "kiyas"), dil_modeli_url=None)
            except Exception:   # noqa: BLE001
                red = True
    shutil.rmtree(veri_koku, ignore_errors=True)
    ceviri_tam, eksik_ceviri = ceviri_denetle()
    n = len(liste)
    degerler = {
        "K17.1": kos.oran(esdeger),
        "K17.2": 1.0 if (mod is not None and not yeni and oturum_dosyasi >= n and red) else 0.0,
        "K17.3": kos.oran(ekran),
        "K17.4": kos.oran([yasak_yok(y) for y in yanitlar]),
        "K17.5": 1.0 if ceviri_tam else 0.0,
        "K17.6": 1.0 if (isinstance(saglik, dict) and saglik.get("dil_modeli") is False
                         and oneri_dogru == len(vaka["oneri_sorulari"]) and all(tamam) and n) else 0.0,
        "K17.7": 1.0 if (mod is not None and getattr(mod, "VARSAYILAN_HOST", None) == "127.0.0.1"
                         and getattr(mod, "VARSAYILAN_PORT", None) == 8810) else 0.0,
    }
    ek = {"akis_sayisi": n, "yanit_sayisi": len(yanitlar), "oturum_dosyasi": oturum_dosyasi,
          "depoda_yeni_ya_da_degisen": yeni[:20], "eksik_ceviri": eksik_ceviri[:20],
          "esdeger_olmayan": [e for (e, _, _), ok in zip(liste, esdeger) if not ok][:20],
          "hata": dict(sorted(hatalar.items()))}
    return vaka, kos.degerlendir(vaka, degerler), ek


# ---------------------------------------------------------------- ana akış

def olc(adet=None):
    vaka, olcutler, ek = v17(adet)
    return [{"kimlik": vaka["kimlik"], "ad": vaka["ad"], "tohum_adedi": adet or ek["akis_sayisi"],
             "olcutler": olcutler, "ek_olcumler": ek}]


def main():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Bilimsel Muhakeme Kıyası (BMK) v10")
    ap.add_argument("--kilitle", action="store_true", help="v10 ön-kayıt kilidini yaz (bir kez)")
    ap.add_argument("--kaydet", action="store_true", help="sonucu kiyas/v10/sonuclar/ altına yaz")
    ap.add_argument("--dogrula", action="store_true",
                    help="yeniden ölç ve kayıtlı sonuçla birebir karşılaştır")
    ap.add_argument("--tohum-adet", type=int, help="duman koşusu için az akış (kaydedilmez)")
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
