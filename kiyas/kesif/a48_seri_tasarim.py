# -*- coding: utf-8 -*-
"""kiyas/kesif/a48_seri_tasarim.py — A4.8 tasarım keşfi (ÖN-KAYIT DIŞI).

README kural 6: yöntem tasarımı ölçüm tohumlarıyla (201–230) değil 900+
tohumlarıyla denenir. Bu betik V8'in dört varyantını ve v0 V3 / v1 V7
parametrelerini 901–930 tohumlarında, kilitli v2 koşucusunun toplama
fonksiyonlarıyla (tohum_olc, ozetle) koşar. Ölçüm DEĞİLDİR; tasarımın
beklendiği gibi davranıp davranmadığını ve nedenlerini gösterir.
Kullanım (depo kökünden):
    PYTHONUTF8=1 python kiyas/kesif/a48_seri_tasarim.py
"""
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v2"))
import kos_v2  # noqa: E402  (ortamı depo dışına yönlendirir)
import uretec_v2  # noqa: E402

TOHUMLAR = range(901, 931)
vaka = kos_v2.vaka_oku("v8_seri_katman.json")
for varyant in kos_v2.VARYANTLAR:
    p = uretec_v2.parametreler(vaka, varyant)
    sayimlar, k_dagilim, bagli = [], {}, []
    for t in TOHUMLAR:
        satirlar, gercek = uretec_v2.v8_seri(p, t)
        ciftler = kos_v2.kos.arac("seri_eslestirme", satirlar, mo_alan="mo")["sonuc"]
        sayimlar.append(kos_v2.tohum_olc(ciftler, gercek))
        if varyant == "tutarsiz":   # kaçan doğru çiftlerde paylaşılan ayırt edici davranış sayısı
            kayit = {s["id"]: set(s["mo"].split()) & set(p["seri_mo"]) for s in satirlar}
            bulunan = {frozenset((c["id1"], c["id2"])) for c in ciftler}
            s = gercek["seri"]
            for i, a in enumerate(s):
                for b in s[i + 1:]:
                    k = len(kayit[a] & kayit[b])
                    d = k_dagilim.setdefault(k, [0, 0])
                    d[0] += 1
                    d[1] += frozenset((a, b)) in bulunan
        # grup düzeyi: bulunan çiftlerle 5 seri üyesinin hepsi tek bileşende mi
        s = gercek["seri"]
        if s:
            ata = {x: x for x in s}

            def kok(x):
                while ata[x] != x:
                    x = ata[x]
                return x
            for c in ciftler:
                if c["id1"] in ata and c["id2"] in ata:
                    ata[kok(c["id1"])] = kok(c["id2"])
            bagli.append(len({kok(x) for x in s}) == 1)
    o = {k: v for k, v in kos_v2.ozetle(sayimlar).items() if not k.startswith("_")}
    if bagli:
        o["seri_tek_bilesen_tohum_orani"] = round(sum(bagli) / len(bagli), 4)
    print(f"{varyant:9s} {json.dumps(o, ensure_ascii=False)}")
    if k_dagilim:
        print("  tutarsız — ortak ayırt edici davranış K: [çift, bulunan] ",
              dict(sorted(k_dagilim.items())))
