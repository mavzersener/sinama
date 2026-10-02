# -*- coding: utf-8 -*-
"""
e2e/sunucu.py — Atölye uçtan uca testi (A6 E3) için arka uç: A5/A6 tek süreç, geçici (depo
dışı) veri kökü, dil modeli kapalı, YerelAjan adresi kapalı bir porta, 127.0.0.1:8813.
Playwright webServer olarak başlatır. Veri kökü yolu `GET /api/saglik`'te görünür.
"""
import atexit
import os
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, KOK)

import uvicorn  # noqa: E402
from uygulama.sunucu import uygulama_olustur  # noqa: E402


def main():
    """Veri kökünü kurar ve sunucuyu başlatır."""
    kok = tempfile.mkdtemp(prefix="sinama_atolye_e2e_")
    atexit.register(shutil.rmtree, kok, ignore_errors=True)
    os.environ["SINAMA_AJAN_URL"] = "http://127.0.0.1:9"   # ajan yok: vekil 503 vermeli
    uvicorn.run(uygulama_olustur(veri_koku=kok, dil_modeli_url=None), host="127.0.0.1", port=8813,
                log_level="warning")


if __name__ == "__main__":
    main()
