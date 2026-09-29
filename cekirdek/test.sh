#!/bin/sh
# test.sh — air-gap ortamında tek komutla tüm testler
set -e
cd "$(dirname "$0")"
echo "== birim testleri =="
python -m unittest discover -s tests
echo "== kapsam cırcır kapısı (H3.4) =="
python kapsam_olc.py
echo "== entegrasyon + güvenlik =="
python test_mcp.py
echo "== demolar =="
python demo.py > /dev/null && echo "demo.py OK"
python demo2.py > /dev/null && echo "demo2.py OK"
echo "TÜM TESTLER GEÇTİ"
