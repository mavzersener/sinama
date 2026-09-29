# -*- coding: utf-8 -*-
"""
kalite/guvenlik.py — GERİYE UYUMLULUK yönlendirmesi (v6.7).
Modül cekirdek/guvenlik.py'ye taşındı; bu dosya sys.modules'ta kendini
hedef modülle DEĞİŞTİRİR — `from suc_analizi.kalite import guvenlik`
diyen herkes (monkeypatch dahil) gerçek modülü görür.
"""
import sys as _sys
from ..cekirdek import guvenlik as _guvenlik

_sys.modules[__name__] = _guvenlik
