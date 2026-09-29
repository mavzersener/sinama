# -*- coding: utf-8 -*-
"""
kalite — profil + TEK gate otoritesi + güvenli yol (v6.1, G1/G2).
Birleşik mimari §4.1-4.2: gate mantığı yalnız kapi.py'de tanımlıdır.
"""
from .guvenlik import (IZINLI_UZANTILAR, MAKS_DOSYA_MB, guvenli_yol, veri_koku)
from .kapi import KapiRed, kapi
from .profil import veri_profili

__all__ = ["kapi", "KapiRed", "veri_profili", "guvenli_yol", "veri_koku",
           "IZINLI_UZANTILAR", "MAKS_DOSYA_MB"]
