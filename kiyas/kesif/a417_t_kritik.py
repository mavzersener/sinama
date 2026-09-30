# -*- coding: utf-8 -*-
"""kiyas/kesif/a417_t_kritik.py — sınama v1.4 keşfi (ÖN-KAYIT DIŞI).

Soru: v1.3'ün aşırı iddiası (BMK v6 karma_yeni_nb 8/100, nominal %5) gerçek mi, ve
kaynağı yayılım çarpanının KESTİRİM belirsizliği mi (φ az sayıda aydan tahmin
ediliyor, ama kritik değer z)? Aday v1.4: kritik değer, iki bileşenin φ serbestlik
derecelerinden Satterthwaite ile t.

A4.12 dersi: betik yama YAPMAZ — depodaki çekirdek o an ne ise onu resmi Rehberli
akıştan koşar; karşılaştırma iki kod durumunda ayrı koşularla yapılır. Tohumlar
tasarım aralığında (2000+; ölçüm tohumları görülmez).

Kullanım (depo kökünden):
    PYTHONUTF8=1 python kiyas/kesif/a417_t_kritik.py [etiket]
"""
import os
import sys
from collections import Counter

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for alt in ("kiyas", os.path.join("kiyas", "v3"), os.path.join("kiyas", "v6")):
    sys.path.insert(0, os.path.join(KOK, alt))
import kos_v3  # noqa: E402  (ortamı depo dışına yönlendirir; sözleşme kodu)
import uretec_v6  # noqa: E402
from sinama.bilim import sinamalar  # noqa: E402

TEMEL = {"baslangic": "2024-01-01", "ay_sayisi": 24, "kesinti_ayi": 13,
         "karakol_lambda": 40, "cevrimici_lambda": 12, "cevrimici": "kesinti"}
SENARYOLAR = {   # ad: (değişen, tohumlar, ölçü)
    "karma_y_nb": ({"karakol_carpani": 1.3, "yayilim_k": {"karakol": None, "cevrimici": 1}},
                   range(2000, 2400), "asiri"),
    "karma_nb_ikisi": ({"karakol_carpani": 1.3, "yayilim_k": {"karakol": 8, "cevrimici": 8}},
                       range(2000, 2200), "asiri"),
    "karma_poisson": ({"karakol_carpani": 1.3, "yayilim_k": {}}, range(2000, 2200), "asiri"),
    "guc_y_nb": ({"karakol_carpani": 1.3, "cevrimici_lambda": 2,
                  "yayilim_k": {"karakol": None, "cevrimici": 1}}, range(2000, 2200), "guc"),
    "guc_poisson": ({"karakol_carpani": 1.3, "cevrimici_lambda": 2, "yayilim_k": {}},
                    range(2000, 2200), "guc"),
}
VAKA = {"arac": "rehberli_calisma",
        "senaryolar": {ad: {"soru_turu": "ARTIS", "amac": "dogrulayici",
                            "argumanlar": {"kanal_alan": "kanal"}} for ad in SENARYOLAR}}


def main():
    etiket = sys.argv[1] if len(sys.argv) > 1 else sinamalar.SINAMA_SURUMU
    for ad, (degisen, tohumlar, olcu) in SENARYOLAR.items():
        p = {**TEMEL, **degisen}
        dag, ayrinti = Counter(), Counter()
        for t in tohumlar:
            s, hata = kos_v3.cagir(VAKA, ad, uretec_v6.v12_kanallar(p, t)[0])
            if hata:
                dag["HATA"] += 1
                continue
            h = s["hukum"]
            dag[h["kategori"]] += 1
            b = next((r for r in h["rakipler"] if r["kod"] == "R-BILDIRIM"), None)
            o = (b or {}).get("olcum") or {}
            if h["kategori"] == "DESTEKLENDİ" and olcu == "asiri":
                ayrinti["phi_yeni_kapili" if (o.get("yayilim_yeni") or 1) > 1 else "phi_yeni_1"] += 1
        n = sum(dag.values())
        deger = dag["DESTEKLENDİ"] / n
        print(f"[{etiket}] {ad:15s} n={n} {'aşırı iddia' if olcu == 'asiri' else 'güç'} {deger:.3f} "
              f"{dict(sorted(dag.items()))} {dict(ayrinti)}", flush=True)


if __name__ == "__main__":
    for akis in (sys.stdout, sys.stderr):
        akis.reconfigure(encoding="utf-8")
    main()
