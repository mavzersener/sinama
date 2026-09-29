# -*- coding: utf-8 -*-
"""
demo.py — Sentetik veriyle tüm analizlerin uçtan uca testi.
Çalıştırma:  python demo.py
"""

import random
from datetime import datetime, timedelta

from suc_analizi import (veri, istatistik, zaman, mekan, tekrar, ag,
                         kume, skor)

random.seed(42)

# --- 1) Sentetik olay verisi: iki hotspot + rastgele arka plan ---
HOTSPOTLAR = [(41.035, 28.975), (41.065, 29.01)]  # iki yoğun bölge
TUR = ["hırsızlık", "kapkaç", "dolandırıcılık", "mala zarar verme", "kavga"]
MAHALLE = ["merkez", "liman", "istasyon", "çarşı", "sanayi"]

kayitlar = []
for i in range(400):
    if random.random() < 0.6:
        hs = random.choice(HOTSPOTLAR)
        lat = hs[0] + random.gauss(0, 0.003)
        lon = hs[1] + random.gauss(0, 0.003)
    else:
        lat = 41.03 + random.uniform(0, 0.06)
        lon = 28.96 + random.uniform(0, 0.07)
    gun_geri = int(random.expovariate(1 / 25)) % 90
    saat = random.choice([20, 21, 22, 23, 0, 1]) if random.random() < 0.55 else random.randint(0, 23)
    t = datetime(2026, 7, 17) - timedelta(days=gun_geri, hours=24 - saat)
    kayitlar.append({
        "id": f"OLAY-{i:04d}",
        "tarih": t,
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "tur": random.choices(TUR, weights=[35, 25, 15, 15, 10])[0],
        "mahalle": random.choice(MAHALLE),
        "adres": f"sokak-{random.randint(1, 60)}",
        "zarar_tl": random.randint(500, 80000),
    })

print("=" * 60)
print("1) VERİ KALİTESİ")
print("eksik alanlar:", veri.eksik_raporu(kayitlar))

print("=" * 60)
print("2) TEMEL İSTATİSTİK")
print("suç türü frekansı:", dict(istatistik.frekans(kayitlar, "tur")))
print("zarar özeti:", istatistik.ozet([k["zarar_tl"] for k in kayitlar]))
print("tür x mahalle (ilk 2 satır):",
      dict(list(istatistik.capraz_tablo(kayitlar, "tur", "mahalle").items())[:2]))
print("zarar anomalileri (|z|>=2):", len(istatistik.z_skor_anomali(kayitlar, "zarar_tl")), "kayıt")

print("=" * 60)
print("3) ZAMAN ANALİZİ")
print("saat dağılımı:", zaman.saat_dagilimi(kayitlar))
print("hafta günü:", zaman.gun_dagilimi(kayitlar))
aylar = zaman.ay_dagilimi(kayitlar)
print("ay serisi:", aylar)
print("trend:", istatistik.dogrusal_trend(list(aylar.values())))
_, gunluk = zaman.gunluk_seri(kayitlar)
print("7 günlük kayan ortalama (son 5):", istatistik.kayan_ortalama(gunluk, 7)[-5:])

print("=" * 60)
print("4) MEKÂNSAL ANALİZ")
noktalar = [(k["lat"], k["lon"]) for k in kayitlar]
grid = mekan.grid_hotspot(noktalar, 0.5)
print("en yoğun 3 grid hücresi:", grid[:3])
hs = mekan.hotspot_hucreler(grid, 80)
print("80. yüzdelik hotspot hücre sayısı:", len(hs))
kde = mekan.kde_yogunluk(noktalar, 0.4, 0.3)
print("KDE en yüksek 3 hücre:", kde[:3])
print("NNI (<1 kümelenme):", mekan.nni(noktalar))

print("=" * 60)
print("5) TEKRAR / YAKIN-TEKRAR")
mk = tekrar.mukerrer_magduriyet(kayitlar, "adres")
print("mükerrer adres sayısı:", len(mk), "| örnek:", dict(list(mk.items())[:3]))
yt = tekrar.yakin_tekrar_ciftleri(kayitlar, 0.3, 7)
print("yakın-tekrar çifti (300m/7gün):", len(yt), "| örnek:", yt[:2])
print("Knox tablosu:", tekrar.knox_tablosu(kayitlar))

print("=" * 60)
print("6) SERİ EŞLEŞTİRME (MO benzerliği)")
mo_kayitlar = [
    {"id": "A1", "mo": "gece cam kırma motosiklet"},
    {"id": "A2", "mo": "gece cam kırma otomobil"},
    {"id": "A3", "mo": "gündüz zil çalma kargo bahanesi"},
    {"id": "A4", "mo": "gece cam kırma motosiklet kaçış"},
]
print(tekrar.seri_eslestirme(mo_kayitlar, "mo", 0.5))

print("=" * 60)
print("7) AĞ ANALİZİ (birlikte olaya karışma)")
supheli = []
for o in range(60):
    kisiler = random.sample([f"K{i:02d}" for i in range(20)], random.randint(2, 4))
    for ki in kisiler:
        supheli.append({"olay": f"V{o:03d}", "kisi": ki})
kenarlar = ag.birlikte_olay_ag(supheli, "olay", "kisi")
g = ag.ag_kur(kenarlar)
print("derece merkeziyeti (ilk 3):", ag.derece_merkeziyeti(g)[:3])
print("bağlı bileşenler (boyut):", [len(b) for b in ag.bagli_bilesenler(g)])
print("aracılık (ilk 3):", ag.aracilik_merkeziyeti(g)[:3])

print("=" * 60)
print("8) KÜME İŞLEMLERİ + BULANIK EŞLEŞME")
liste_a = [{"isim": "Ahmet Yılmaz"}, {"isim": "Mehmet Demir"}, {"isim": "Ayşe Kaya"}]
liste_b = [{"isim": "Mehmet Demir"}, {"isim": "Ayşe Kaya"}, {"isim": "Fatma Şahin"}]
print("kesişim:", kume.kesisim(liste_a, liste_b, "isim"))
print("fark (A-B):", kume.fark(liste_a, liste_b, "isim"))
print("bulanık ('ahmet yilmaz' -> 'ahmet yılmaz'):",
      kume.benzerlik_orani("ahmet yilmaz", "ahmet yılmaz"))
print("levenshtein('istasyon','istasyon cd'):", kume.levenshtein("istasyon", "istasyon cd"))

print("=" * 60)
print("9) RİSK SKORLAMA + EŞİK UYARISI")
kurallar = [
    {"alan": "tur", "kosul": "==", "deger": "kapkaç", "agirlik": 3},
    {"alan": "zarar_tl", "kosul": ">=", "deger": 30000, "agirlik": 2},
    {"alan": "mahalle", "kosul": "==", "deger": "istasyon", "agirlik": 1},
]
skorlar = skor.toplu_skorla(kayitlar[:50], kurallar)
print("en riskli 3 olay:", skorlar[:3])
mahalle_zarar = [{"mahalle": m, "zarar": sum(k["zarar_tl"] for k in kayitlar if k["mahalle"] == m)}
                 for m in MAHALLE]
print("toplam zarar >1.5M olan mahalleler:",
      skor.esik_uyarilari(mahalle_zarar, "zarar", 1_500_000, grupla="mahalle"))

print("=" * 60)
print("TÜM ANALİZLER BAŞARIYLA TAMAMLANDI")
