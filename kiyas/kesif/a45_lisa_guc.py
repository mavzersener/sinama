# -*- coding: utf-8 -*-
"""kiyas/kesif/a45_lisa_guc.py — A4.5 sonrası KEŞİF (ÖN-KAYIT DIŞI).

LISA'ya FDR eklenince V4 gücü 1,00 → 0,47 düştü (K4.1). İki hipotez sınanır:
(1) odak hücre boyutundan küçük (tek hücrelik sivri) olduğu için mi?
(2) 999 permütasyonun p çözünürlüğü (en küçük p 0,001) yüzünden mi?
Hipotez üretir, ölçüm değildir; kilitli dosyalara dokunmaz.
Kullanım (depo kökünden): PYTHONUTF8=1 python kiyas/kesif/a45_lisa_guc.py
"""
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, "kiyas"))
sys.path.insert(0, os.path.join(KOK, "kiyas", "v1"))
import kos_v1  # noqa: E402  (ortamı depo dışına yönlendirir)
import uretec  # noqa: E402
from sinama.cekirdek import mekan, mekansal_istatistik as mi, veri  # noqa: E402

kos = kos_v1.kos
P = kos_v1.vaka_oku("v4_lisa.json")["uretec"]["parametreler"]
TOHUMLAR = range(101, 131)


def olc(sigma=P["odak_sigma_km"], perm=999):
    """Aracın boru hattını (500 m hücre, 750 m bant) doğrudan yeniden kurar."""
    q = dict(P, odak_sigma_km=sigma)
    guc, alarm, odak_p = [], [], []
    for t in TOHUMLAR:
        for v in ("odakli", "csr"):
            s, g = uretec.v1_kumelenme(q, t, v)
            h = mekan.grid_hotspot([veri.koordinat_al(r) for r in s], 0.5)
            r = mi.yerel_moran(h, 0.75, permutasyon=perm)["sonuclar"]
            if v == "odakli":
                olat, olon = g["odak"]
                yakin = [c for c in r if kos.km(c["lat"], c["lon"], olat, olon) <= 0.4]
                guc.append(any(c["kumeleme"] == "HH" for c in yakin))
                odak_p.append(min(c["p"] for c in yakin if c["p"] is not None))
            else:
                alarm.append(any(c["kumeleme"] in ("HH", "LL", "HL", "LH") for c in r))
    odak_p.sort()
    return kos.oran(guc), kos.oran(alarm), odak_p[len(odak_p) // 2]


print("H1 — odak boyutu (999 permütasyon):")
for sigma in (0.15, 0.40, 0.60):
    g, a, pm = olc(sigma=sigma)
    print(f"  σ={sigma} km: güç={g:.3f} yanlış_alarm={a:.3f} odak_p_medyan={pm}")
print("H2 — permütasyon çözünürlüğü (σ=0,15 km):")
for perm in (999, 9999):
    g, a, pm = olc(perm=perm)
    print(f"  permütasyon={perm}: güç={g:.3f} yanlış_alarm={a:.3f} odak_p_medyan={pm}")
