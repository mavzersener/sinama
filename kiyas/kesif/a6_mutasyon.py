# -*- coding: utf-8 -*-
"""
kiyas/kesif/a6_mutasyon.py — A6 eşdeğerlik ölçümünün duyarlılığı (keşif, CI dışı).

Her mutasyon kaynağa bilinçli bir hata sokar, ilgili ölçütü `betikler/a6_esdegerlik.py`'nin
KENDİ işlevleriyle yeniden ölçer ve dosyayı git'ten geri yükler. Ölçüt hatayı görmezse
(mutasyon "kaçtıysa") ölçüm o hataya kör demektir. Çalışma ağacı temiz değilse başlamaz.

    python kiyas/kesif/a6_mutasyon.py
"""
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, "betikler"))
sys.path.insert(0, KOK)
import a6_esdegerlik as es  # noqa: E402 — yalnız npx() ve ATOLYE için

ATOLYE = os.path.join(KOK, "uygulama", "atolye")

# (kimlik, dosya, eski, yeni, ölçüt, derleme gerekir mi)
MUTASYONLAR = [
    ("M1 depo sırası", "uygulama/atolye_depo.py", '"updatedAt DESC"', '"updatedAt ASC"', "E2", False),
    ("M2 imza yanlış baytlara", "uygulama/kanit_defteri.py",
     'a["ozel"].sign(kayit["kayit_hash"].encode("utf-8"))', 'a["ozel"].sign(b"x")', "E2", False),
    ("M3 yalnız-yerel kapısı yok", "uygulama/atolye_sunucu.py",
     "if not request.client or request.client.host not in YEREL_ISTEMCILER:", "if False:", "E2", False),
    ("M4 CSV boş satırı sayar", "uygulama/atolye_depo.py",
     'if not (len(alanlar) == 1 and alanlar[0].strip() == ""):', "if True:", "E2", False),
    ("M5 kanonik olmayan kayıt hash'i", "uygulama/kanit_defteri.py",
     'kayit = {**govde, "kayit_hash": sha256_hex(kanonik(govde))}',
     'kayit = {**govde, "kayit_hash": sha256_hex(json.dumps(govde, sort_keys=True))}', "E4", False),
    ("M6 önizleme işareti yok", "uygulama/atolye/src/components/ResultsPanel.tsx",
     "  return 'onizleme';\n}", "  return 'sunucu';\n}", "E3", True),
    ("M7 suç köprüsü yanlış yolda", "uygulama/atolye_sunucu.py",
     '@r.post("/api/ml/suc/{arac}")', '@r.post("/api/ml/suc2/{arac}")', "E3", False),
    ("M8 suç düğümü kayboldu", "uygulama/atolye/src/nodes/sucAnaliziNodes.generated.ts",
     '"type": "suc_sicak_nokta_gi"', '"type": "suc_sicak_nokta_gx"', "E1", False),
    ("M9 Atölye bağlanmadı", "uygulama/sunucu.py",
     "    app.state.atolye = atolye_sunucu.bagla(", "    app.state.atolye = {} or (lambda *a, **k: {})(", "E5", False),
]


def olc(olcut):
    """Ölçütü TAZE bir süreçte ölçer: aynı süreçte içe aktarılmış modüller önbellekte
    kalır ve mutasyonu (ya da önceki mutasyonun kalıntısını) gizler — ilk sürümde bu yüzden
    iki mutasyon "kaçmış", yakalananların da bir kısmı önceki mutasyondan etkilenmişti."""
    r = subprocess.run([sys.executable, "-W", "ignore", os.path.join(KOK, "betikler", "a6_esdegerlik.py"),
                        "--olcut", olcut], cwd=KOK, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    return r.returncode == 0


def derle():
    subprocess.run([es.npx(), "vite", "build"], cwd=ATOLYE, capture_output=True,
                   shell=sys.platform == "win32", check=True)


def main():
    if subprocess.run(["git", "-C", KOK, "diff", "--quiet"]).returncode != 0:
        sys.exit("çalışma ağacı temiz değil; mutasyon ölçümü başlamaz")
    yakalanan = 0
    for kimlik, dosya, eski, yeni, olcut, derleme in MUTASYONLAR:
        yol = os.path.join(KOK, dosya)
        with open(yol, encoding="utf-8", newline="") as f:
            metin = f.read()
        if metin.count(eski) != 1:
            print(f"{kimlik}: KURULAMADI (desen {metin.count(eski)} kez)")
            continue
        try:
            with open(yol, "w", encoding="utf-8", newline="") as f:
                f.write(metin.replace(eski, yeni))
            if derleme:
                derle()
            gecti = olc(olcut)
        finally:
            subprocess.run(["git", "-C", KOK, "checkout", "--", dosya], check=True)
            if derleme:
                derle()
        yakalanan += not gecti
        print(f"{kimlik} [{olcut}]: {'YAKALANDI' if not gecti else 'KAÇTI'}")
    print(f"Toplam: {yakalanan}/{len(MUTASYONLAR)} mutasyon yakalandı")
    return 0 if yakalanan == len(MUTASYONLAR) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
