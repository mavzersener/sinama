# Kancaların ortak Python seçimi (kaynak olarak okunur, kanca değildir).
# SINAMA_PY verilmişse o kullanılır.
# DİKKAT: Windows'ta 'python3' çoğu zaman Microsoft Store yönlendiricisidir
# (WindowsApps\python3) — gerçek yorumlayıcı değildir; bilerek aday değil.
PY="${SINAMA_PY:-}"
if [ -z "$PY" ]; then
  for aday in python py; do
    if command -v "$aday" >/dev/null 2>&1; then PY="$aday"; break; fi
  done
fi
if [ -z "$PY" ]; then
  echo "[kanca] HATA: Python bulunamadı; SINAMA_PY=<yorumlayıcı yolu> verin" >&2
  exit 1
fi
