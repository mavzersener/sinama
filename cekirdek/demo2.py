# -*- coding: utf-8 -*-
"""
demo2.py — Yeni modüllerin uçtan uca testi
(orneklem, iliski, olcek, degerlendirme, ileri + ag genişletmeleri).
Çalıştırma: python demo2.py
"""

import random
from datetime import datetime, timedelta

from sinama import (orneklem, iliski, olcek, degerlendirme,
                         ileri, ag, zaman, mekan)

random.seed(7)

# --- Sentetik veri: 180 günlük olay serisi ---
HOTSPOTLAR = [(41.035, 28.975), (41.065, 29.01)]
kayitlar = []
for i in range(600):
    hs = random.choice(HOTSPOTLAR) if random.random() < 0.55 else None
    lat = (hs[0] + random.gauss(0, 0.004)) if hs else 41.03 + random.uniform(0, 0.06)
    lon = (hs[1] + random.gauss(0, 0.004)) if hs else 28.96 + random.uniform(0, 0.07)
    gun = random.randint(0, 179)
    saat = random.choice([21, 22, 23]) if random.random() < 0.5 else random.randint(0, 23)
    kayitlar.append({
        "id": f"O{i:04d}",
        "tarih": datetime(2026, 1, 18) + timedelta(days=gun, hours=saat),
        "lat": round(lat, 6), "lon": round(lon, 6),
        "tur": random.choices(["hırsızlık", "kapkaç", "dolandırıcılık", "kavga"],
                              weights=[40, 25, 20, 15])[0],
        "mahalle": random.choice(["merkez", "liman", "istasyon", "çarşı"]),
        "kacakci_mi": random.random() < 0.3,
    })

print("=" * 60)
print("1) ÖRNEKLEME (Kitap Bölüm 8)")
orn = orneklem.tabakali(kayitlar, "mahalle", 40, seed=1)
print("tabakalı örneklem n =", len(orn))
p = sum(1 for k in orn if k["tur"] == "hırsızlık") / len(orn)
print("hırsızlık oranı %95 GA:", orneklem.guven_araligi_oran(p, len(orn)))
print("±%3 hata için gerekli n:", orneklem.orneklem_buyuklugu(0.03))

print("=" * 60)
print("2) SUÇ ORANLARI + İLİŞKİ ÖLÇÜLERİ (Bölüm 6/14)")
bolgeler = [{"bolge": "merkez", "olay": 320, "nufus": 85000},
            {"bolge": "liman", "olay": 180, "nufus": 120000},
            {"bolge": "istasyon", "olay": 260, "nufus": 40000}]
print(iliski.oran_tablosu(bolgeler))
print("tür x mahalle ki-kare:",
      {k: v for k, v in iliski.capraz_ki_kare(kayitlar, "tur", "mahalle").items()
       if k in ("ki_kare", "df", "p_degeri", "cramer_v")})
print("lambda (mahalle -> tür):", iliski.lambda_(kayitlar, "mahalle", "tur"))
print("Pearson (lat vs lon):", iliski.pearson_r(
    [k["lat"] for k in kayitlar], [k["lon"] for k in kayitlar]))

print("=" * 60)
print("3) ENDEKS + GÜVENİLİRLİK (Bölüm 5)")
mahalle_veri = [
    {"mahalle": "merkez", "terk_bina": 12, "aydinlatma_ariza": 40, "sikayet": 90},
    {"mahalle": "liman", "terk_bina": 30, "aydinlatma_ariza": 25, "sikayet": 55},
    {"mahalle": "istasyon", "terk_bina": 22, "aydinlatma_ariza": 35, "sikayet": 120},
    {"mahalle": "çarşı", "terk_bina": 8, "aydinlatma_ariza": 10, "sikayet": 45},
]
print("düzensizlik endeksi:",
      olcek.endeks_kur(mahalle_veri, ["terk_bina", "aydinlatma_ariza", "sikayet"],
                       agirliklar={"sikayet": 2}))
yanitlar = [[4, 4, 5, 4], [2, 3, 2, 3], [5, 5, 5, 4], [1, 2, 1, 2], [3, 3, 4, 3]]
print("Cronbach alfa:", olcek.cronbach_alfa(yanitlar))

print("=" * 60)
print("4) DEĞERLENDİRME (Bölüm 13)")
print("öncesi-sonrası:", degerlendirme.oncesi_sonrasi(120, 88))
print("DiD:", degerlendirme.farklarin_farki(120, 88, 100, 105))
seri = [10, 11, 9, 10, 12, 11, 10, 6, 5, 7, 6, 5, 6, 7]
print("kesinti analizi:", degerlendirme.kesinti_analizi(seri, 7))

print("=" * 60)
print("5) İLERİ ANALİZLER")
_, gunluk = zaman.gunluk_seri(kayitlar)
print("kontrol grafiği:", {k: v for k, v in ileri.kontrol_grafigi(gunluk).items() if k != "asim_gunleri"},
      "| aşım günü:", len(ileri.kontrol_grafigi(gunluk)["asim_gunleri"]))
print("CUSUM alarmları:", ileri.cusum(gunluk)[:3])
mahalle_sayim = {}
for k in kayitlar:
    mahalle_sayim[k["mahalle"]] = mahalle_sayim.get(k["mahalle"], 0) + 1
print("Poisson anomali:", ileri.bolge_anomali(mahalle_sayim))
m = ileri.gun_saat_matrisi(kayitlar)
print("en riskli 3 gün-saat dilimi:", ileri.en_riskli_dilimler(m, 3))
noktalar = [(k["lat"], k["lon"]) for k in kayitlar]
ilk90 = [(k["lat"], k["lon"]) for k in kayitlar if (k["tarih"] - datetime(2026, 1, 18)).days < 90]
son90 = [(k["lat"], k["lon"]) for k in kayitlar if (k["tarih"] - datetime(2026, 1, 18)).days >= 90]
donem = ileri.donemsel_hotspot_karsilastirma(
    mekan.grid_hotspot(ilk90, 0.5), mekan.grid_hotspot(son90, 0.5))
from collections import Counter as C2
print("dönemsel hotspot sınıfları:", dict(C2(d["sinif"] for d in donem)))
print("coğrafi profil (en olası 2 üs bölgesi):",
      ileri.cografi_profil(HOTSPOTLAR + [(41.04, 28.99)])[:2])
katmanlar = {"bar": [(41.035, 28.975)], "park": [(41.065, 29.01)],
             "otopark": [(41.045, 28.99)]}
print("RTM en riskli 2 hücre:", ileri.risk_arazi(katmanlar, 0.5, 0.6)[:2])
seri_tarih = sorted(k["tarih"] for k in kayitlar if k["tur"] == "kapkaç")[:50]
print("kapkaç ritmi (olaylar arası süre):", ileri.olaylar_arasi_sure(seri_tarih))
print("Benford (rastgele zarar):", ileri.benford_testi(
    [random.randint(100, 99999) for _ in range(300)])["uyum"])
km = ileri.k_means([[k["lat"], k["lon"]] for k in kayitlar[:200]], k=3, seed=3)
print("k-means küme büyüklükleri:", km["kume_buyuklukleri"])
print("Holt-Winters 7 gün tahmini:", ileri.holt_winters(gunluk, 7, ileri=7))

print("=" * 60)
print("6) AĞ GENİŞLETMELERİ")
kenarlar = [("A", "B", 3), ("B", "C", 2), ("A", "C", 1),
            ("D", "E", 4), ("E", "F", 2), ("C", "D", 1), ("F", "G", 3)]
g = ag.ag_kur(kenarlar)
print("topluluklar:", ag.topluluk_tespiti(g, seed=5))
print("PageRank (ilk 3):", ag.pagerank(g)[:3])
print("A'nın 1 adımlık ego ağı düğümleri:", sorted(ag.ego_agi(g, "A", 1).keys()))
print("A -> G en kısa yol:", ag.en_kisa_yol(g, "A", "G"))

print("=" * 60)
print("YENİ MODÜLLER BAŞARIYLA TAMAMLANDI")
