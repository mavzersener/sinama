# -*- coding: utf-8 -*-
"""
python -m uygulama [--port 8810] [--veri-koku DIZIN] [--dil-modeli URL|yok]

Yalnız geri döngü adresine bağlanır (AGENTS: sunucuyu 0.0.0.0'a bağlama).
"""
import argparse
import sys

from .sunucu import VARSAYILAN_DIL_MODELI, VARSAYILAN_HOST, VARSAYILAN_PORT, uygulama_olustur


def main(argv=None):
    """Arka ucu uvicorn ile başlatır."""
    ap = argparse.ArgumentParser(prog="python -m uygulama", description="Sınama arka ucu (A5)")
    ap.add_argument("--port", type=int, default=VARSAYILAN_PORT)
    ap.add_argument("--veri-koku", default=None, help="depo dışı veri kökü (SINAMA_VERI_KOKU)")
    ap.add_argument("--dil-modeli", default=VARSAYILAN_DIL_MODELI,
                    help="OpenAI uyumlu yerel sunucu; 'yok' → dil modeli kapalı")
    a = ap.parse_args(argv)
    import uvicorn
    app = uygulama_olustur(veri_koku=a.veri_koku,
                           dil_modeli_url=None if a.dil_modeli == "yok" else a.dil_modeli)
    uvicorn.run(app, host=VARSAYILAN_HOST, port=a.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
