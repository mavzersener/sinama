# -*- coding: utf-8 -*-
"""kiyas/kesif/v1_nedenler.py — BMK v1 sonrası KEŞİF (ÖN-KAYIT DIŞI).

Öngörülmeyen K5.1 başarısızlığının (emerging hotspot gücü %70) nedenini araştırır.
Hipotez üretir, ölçüm değildir. Kilitli dosyalara dokunmaz.
Kullanım (depo kökünden): PYTHONUTF8=1 python kiyas/kesif/v1_nedenler.py
"""
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v1"))
import kos_v1  # noqa: E402  (ortamı depo dışına yönlendirir)
import uretec_v1  # noqa: E402
from sinama.cekirdek import mekansal_istatistik as mi  # noqa: E402

p = kos_v1.vaka_oku("v5_yukselen.json")["uretec"]["parametreler"]
kategoriler, kusursuz, mk_anlamli = {}, 0, 0
for t in range(101, 131):
    satirlar, g = uretec_v1.v5_yukselen(p, t, "artan")
    r = kos_v1.kos.arac("yukselen_sicak_nokta", satirlar, bolge_alan="bolge", zaman_alan="tarih")["sonuc"]
    kat = {s["bolge"]: s["kategori"] for s in r["sonuclar"]}[g["artan"]]
    kategoriler[kat] = kategoriler.get(kat, 0) + 1
    # aynı bölgenin 4 dönemlik serisi, araçla aynı bölme (en erken..en geç tarih)
    from sinama.arayuz.araclar import _bolge_donem_serileri
    from sinama.cekirdek import veri
    kayitlar = [dict(s, tarih=veri.tarih_coz(s["tarih"])) for s in satirlar]
    seri = _bolge_donem_serileri(kayitlar, "bolge", "tarih", 4)[0][g["artan"]]
    mk = mi._mann_kendall(seri)
    kusursuz += all(seri[i] < seri[i + 1] for i in range(3))
    mk_anlamli += mk["yon"] == "artan"
print("artan bölgenin kategorileri:", kategoriler)
print(f"4 dönemlik seri kusursuz artan: {kusursuz}/30 | Mann-Kendall 'artan' (p<0,10): {mk_anlamli}/30")
print("n=4'te MK'nın ulaşabileceği en küçük p (S=6):", round(mi._mann_kendall([1, 2, 3, 4])["p"], 4),
      "| S=4 (tek ters çift):", round(mi._mann_kendall([1, 3, 2, 4])["p"], 4))
