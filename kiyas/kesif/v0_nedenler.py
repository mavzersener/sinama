# -*- coding: utf-8 -*-
"""kiyas/kesif/v0_nedenler.py — BMK v0 sonrası KEŞİF (ÖN-KAYIT DIŞI).

Öngörülmeyen başarısızlıkların (K1.1, K2.1, K2.4) nedenlerini araştırır.
Sonuçları kiyas/sonuclar/v0_bulgular.md "keşif" bölümündedir; bunlar ön-kayıtlı
ölçüm DEĞİLDİR, hipotez üretir. Kullanım (depo kökünden):
    PYTHONUTF8=1 python kiyas/kesif/v0_nedenler.py

Kilitli dosyalara ve kayıtlı sonuca dokunmaz; yalnız okur ve ek ölçer."""
import os
import statistics
import sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
import kos  # noqa: E402  (ortamı depo dışına yönlendirir)
import uretec  # noqa: E402

v1p = kos.vaka_oku("v1_kumelenme.json")["uretec"]["parametreler"]
v2p = kos.vaka_oku("v2_bildirim.json")["uretec"]["parametreler"]
T = range(1, 31)

print("=== K1.1 NNI: kenar düzeltmesi etkisi (aynı veri)")
for kd in (False, True):
    guc, fa, ort = [], [], {"odakli": [], "csr": []}
    for t in T:
        for v in ("odakli", "csr"):
            s, _ = uretec.v1_kumelenme(v1p, t, v)
            r = kos.arac("nni", s, kenar_duzeltme=kd)["sonuc"]
            anlamli = r["nni"] < 1 and r["p"] < 0.05
            (guc if v == "odakli" else fa).append(anlamli)
            ort[v].append(r["nni"])
    print(f"  kenar_duzeltme={kd!s:5s} güç={kos.oran(guc):.3f} yanlış_alarm={kos.oran(fa):.3f} "
          f"ort_nni odaklı={statistics.mean(ort['odakli']):.4f} csr={statistics.mean(ort['csr']):.4f}")

print("=== K2.1 CUSUM: ilk alarm gecikmelerinin dağılımı (gün; kesinti=0)")
gecikmeler = []
for t in T:
    s, g = uretec.v2_bildirim(v2p, t)
    a = kos.arac("cusum", s)["sonuc"]
    gecikmeler.append(a[0]["gun"] - g["kesinti_gunu"] if a else None)
erken = [x for x in gecikmeler if x is not None and x < -15]
gec = [x for x in gecikmeler if x is not None and x > 60]
print(f"  erken(<-15): {len(erken)}  pencerede: {sum(1 for x in gecikmeler if x is not None and -15 <= x <= 60)}  geç(>60): {len(gec)}")
print(f"  sıralı: {sorted(x for x in gecikmeler if x is not None)}")

print("=== K2.4 çapraz tablo: hangi koşul düşüyor (araç sayımı mı, ölçüt mü)")
k_sapma, pay_dusuk = 0, 0
for t in T:
    s, _ = uretec.v2_bildirim(v2p, t)
    tb = kos.arac("capraz_tablo", s, a="kanal", b="yil")["sonuc"]
    # aracın sayımı ham veriyle birebir mi?
    elle = {}
    for r in s:
        elle.setdefault(r["kanal"], {}).setdefault(r["yil"], 0)
        elle[r["kanal"]][r["yil"]] += 1
    assert tb == elle, "capraz_tablo sayımı ham veriden farklı"
    k0, k1 = tb["karakol"]["2024"], tb["karakol"]["2025"]
    c1 = tb["cevrimici"].get("2025", 0)
    artis = (k1 + c1) - k0
    if abs(k1 - k0) / k0 > 0.15:
        k_sapma += 1
    if not c1 >= 0.8 * artis:
        pay_dusuk += 1
print(f"  araç sayımı 30/30 tohumda ham veriyle birebir; karakol ±%15 dışı: {k_sapma}, yeni kanal payı <%80: {pay_dusuk}")
