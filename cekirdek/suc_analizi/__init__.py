# -*- coding: utf-8 -*-
"""
suc_analizi — Saf Python suç analizi paketi (sıfır dış bağımlılık).

Katmanlı mimari (v6.1, G1):
  cekirdek/  saf istatistik + veri erişimi
  kalite/    profil + TEK gate otoritesi + güvenli yol
  surec/     PPDAC döngüsü + analiz ürünleri
  arayuz/    ince MCP transportu (sunucu) + araç adaptörleri

Geriye uyumluluk: eski düz modül yolları (from suc_analizi import mekan,
import suc_analizi.sunucu vb.) sys.modules takma adlarıyla korunur.
"""

__version__ = "6.8.0"

import sys as _sys

from .cekirdek import (veri, istatistik, zaman, mekan, tekrar, ag, kume,
                       skor, orneklem, iliski, olcek, degerlendirme, ileri,
                       hipotez, regresyon, zarar)
from . import kalite
from .surec import dongu, rapor
from .arayuz import sunucu

_CEKTEN = {"veri": veri, "istatistik": istatistik, "zaman": zaman,
           "mekan": mekan, "tekrar": tekrar, "ag": ag, "kume": kume,
           "skor": skor, "orneklem": orneklem, "iliski": iliski,
           "olcek": olcek, "degerlendirme": degerlendirme, "ileri": ileri,
           "hipotez": hipotez, "regresyon": regresyon, "zarar": zarar,
           "dongu": dongu, "rapor": rapor, "sunucu": sunucu}
for _ad, _mod in _CEKTEN.items():
    _sys.modules.setdefault(f"{__name__}.{_ad}", _mod)

__all__ = list(_CEKTEN) + ["kalite"]
