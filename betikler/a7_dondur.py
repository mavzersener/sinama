# -*- coding: utf-8 -*-
"""
betikler/a7_dondur.py — kaynak depoların dondurulması (ADR-001 A7; DataFlow için ADR-004 md. 7).

Kaynak depolar salt okunurdur (AGENTS kural 3); dondurma onlara YAZAR. Bu yüzden:
- varsayılan KURU ÇALIŞTIRMADIR: ön koşulları denetler, yazılacak metni ve komutları gösterir,
  hiçbir şeyi değiştirmez;
- yazmak için `--uygula` ve her depo için ayrıca `--depo <ad>` gerekir ve yalnız proje sahibinin
  açık onayıyla çalıştırılır. Uzak depoya hiçbir şey gönderilmez (push yok, AGENTS kural 8).

Dondurma, kaynak deponun kendi kancalarıyla TEK commit'tir: README'nin başına yönlendirme
bloğu + `DONDURULDU.md`; ardından o commit'e açıklamalı `sinama-dondurma` etiketi. Kod silinmez,
depo çalışır kalır. Geri dönüş: `git revert <commit>` ve `git tag -d sinama-dondurma`.

    python betikler/a7_dondur.py                         # kuru çalıştırma (hepsi)
    python betikler/a7_dondur.py --uygula --depo DataFlow   # proje sahibinin onayıyla
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETIKET = "sinama-dondurma"
SINAMA = "C:\\Projects\\sinama (github.com/mavzersener/sinama, özel)"

# Dondurulacaklar: kodu Sınama'ya TAŞINAN (yalnız kavramı alınan değil) depolar.
DEPOLAR = {
    "suc_analizi": {
        "yol": r"C:\Projects\suc_analizi", "readme": "README.md", "taban": "20d6e2c",
        "halef": "`cekirdek/` (A2; paket adı `sinama`, P06 mahremiyet ve zincir v2 birleşik)",
        "tasinmayan": "yok — izlenen ağacın tamamı hasat edildi (HASAT.md 29.09.2026 satırları)",
        "not": "HARP hâlâ bu paketi kullanır; dondurma onu bozmaz (kod yerinde kalır), ancak P06 "
               "mahremiyet düzeltmesi yalnız Sınama'dadır (ADR-001 açık konu).",
    },
    "DataFlow": {
        "yol": r"C:\Projects\DataFlow", "readme": "README.md", "taban": "5ea8652",
        "halef": "Atölye — `uygulama/atolye/` (ön yüz, `/atolye/`) + `uygulama/atolye_sunucu.py` (arka uç, "
                 "tek FastAPI süreci) — A6, ADR-004",
        "tasinmayan": "ml-service algoritmaları (MVP dışı), Akademik Mod / Science GPT (halefi Rehberli), "
                      "HARP iletimi, Kimi OAuth, MySQL, S3",
        "kosul": "A6 eşdeğerliği E1–E5 (`uygulama/atolye_esdegerlik/sonuc.json`)",
    },
}
# Dondurulmayanlar ve nedeni (ADR-001 md. 6; yalnız kavram hasadı).
DONDURULMAYAN = {
    "science_gpt": "yalnız kavram hasadı (ADR-002); ayrı motor — dondurma kararı proje sahibinde",
    "harp_pol_x": "dış sistem (HARP denetim otoritesi); yalnız kavram hasadı — çalışmaya devam eder",
    "AnlamCekirdegi": "ADR-001 md. 6: ayrı yaşar (MCP/dışa aktarımla bağlanır)",
    "YerelAjan_v2": "ADR-001 md. 6: ayrı yaşar",
    "duzeltme_suc_analizi": "git'siz hazırlık kopyası; A2'de birleştirildi — etiketlenemez, dokunulmaz",
}


def git(yol, *arg, kontrol=True):
    r = subprocess.run(["git", "-C", yol, *arg], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if kontrol and r.returncode:
        raise RuntimeError(f"git {' '.join(arg)}: {r.stderr.strip()}")
    return r.stdout.strip()


def readme_blogu(ad, d, sinama_commit, tarih):
    return (f"> **DONDURULDU — {tarih}.** Bu proje Sınama programına taşındı: {d['halef']}. "
            f"Kaynak `{d['taban']}`, Sınama `{sinama_commit}`. Burada geliştirme yapılmaz; değişiklik "
            f"Sınama deposunda yapılır ({SINAMA}). Ayrıntı ve geri dönüş: `DONDURULDU.md`.\n\n")


def dondurma_belgesi(ad, d, sinama_commit, tarih):
    return f"""# {ad} — DONDURULDU ({tarih})

Bu depo Sınama programına taşındı ve donduruldu (ADR-001 A7{', ADR-004 md. 7' if ad == 'DataFlow' else ''}).

| | |
|---|---|
| Halef | {d['halef']} |
| Hasat edilen commit | `{d['taban']}` (Sınama `HASAT.md`) |
| Sınama commit'i (dondurma anında) | `{sinama_commit}` |
| Taşınmayan | {d['tasinmayan']} |
| Sınama deposu | {SINAMA} |

- Burada yeni geliştirme yapılmaz; kod ve geçmiş yerinde kalır, depo çalışır durumdadır.
- Dondurma tek commit ve `{ETIKET}` etiketidir. Geri dönüş: `git revert <bu commit>` ve
  `git tag -d {ETIKET}`.
{('- Not: ' + d['not'] + chr(10)) if d.get('not') else ''}"""


def denetle(ad, d, sinama_commit):
    """Ön koşullar → (hazır mı, satırlar)."""
    satirlar, hazir = [], True
    if not os.path.isdir(os.path.join(d["yol"], ".git")):
        return False, [f"  ✗ depo yok: {d['yol']}"]
    bas = git(d["yol"], "rev-parse", "--short", "HEAD")
    kirli = git(d["yol"], "status", "--porcelain", "--untracked-files=no")
    etiket = git(d["yol"], "tag", "--list", ETIKET)
    readme = os.path.isfile(os.path.join(d["yol"], d["readme"]))
    yeni = git(d["yol"], "rev-list", "--count", f"{d['taban']}..HEAD")
    for kosul, metin in ((bas, f"HEAD {bas}"), (not kirli, "izlenen dosyalarda değişiklik yok"),
                         (not etiket, f"'{ETIKET}' etiketi yok"), (readme, f"{d['readme']} var"),
                         (yeni == "0", f"hasattan sonra yeni commit yok (taban {d['taban']}, +{yeni})")):
        satirlar.append(f"  {'✓' if kosul else '✗'} {metin}")
        hazir &= bool(kosul)
    if ad == "DataFlow":
        try:
            with open(os.path.join(KOK, "uygulama", "atolye_esdegerlik", "sonuc.json"), encoding="utf-8") as f:
                s = json.load(f)
            tamam = all(s[k]["gecti"] for k in ("E1", "E2", "E3", "E4", "E5"))
        except (OSError, KeyError, ValueError):
            tamam = False
        satirlar.append(f"  {'✓' if tamam else '✗'} {d['kosul']}")
        hazir &= tamam
    return hazir, satirlar


def uygula(ad, d, sinama_commit, tarih):
    yol = d["yol"]
    readme = os.path.join(yol, d["readme"])
    with open(readme, encoding="utf-8", newline="") as f:
        eski = f.read()
    with open(readme, "w", encoding="utf-8", newline="") as f:
        f.write(readme_blogu(ad, d, sinama_commit, tarih) + eski)
    with open(os.path.join(yol, "DONDURULDU.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(dondurma_belgesi(ad, d, sinama_commit, tarih))
    git(yol, "add", d["readme"], "DONDURULDU.md")
    r = subprocess.run(["git", "-C", yol, "commit", "-m",
                        f"Donduruldu: halefi Sınama ({sinama_commit})\n\nADR-001 A7. Ayrıntı: DONDURULDU.md"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:   # kaynak deponun kancası reddetti: değişikliği geri al, iz bırakma
        git(yol, "reset", "-q", "HEAD", "--", d["readme"], "DONDURULDU.md", kontrol=False)
        git(yol, "checkout", "--", d["readme"], kontrol=False)
        os.remove(os.path.join(yol, "DONDURULDU.md"))
        raise RuntimeError(f"commit reddedildi (kaynak deponun kancası?):\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    git(yol, "tag", "-a", ETIKET, "-m", f"Sınama'ya taşındı; Sınama {sinama_commit}")
    return git(yol, "rev-parse", "--short", "HEAD")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kaynak depoların dondurulması (A7) — varsayılan kuru çalıştırma")
    ap.add_argument("--uygula", action="store_true", help="GERÇEKTEN yaz (proje sahibinin açık onayıyla)")
    ap.add_argument("--depo", action="append", choices=sorted(DEPOLAR), help="--uygula ile: dondurulacak depo")
    a = ap.parse_args(argv)
    if a.uygula and not a.depo:
        ap.error("--uygula için en az bir --depo gerekir (toplu dondurma yok)")
    sinama_commit = git(KOK, "rev-parse", "--short", "HEAD")
    tarih = datetime.date.today().strftime("%d.%m.%Y")
    print(f"Sınama {sinama_commit} — {'UYGULA' if a.uygula else 'KURU ÇALIŞTIRMA (hiçbir şey yazılmaz)'}\n")
    kod = 0
    for ad, d in DEPOLAR.items():
        hazir, satirlar = denetle(ad, d, sinama_commit)
        print(f"{ad} ({d['yol']}): {'HAZIR' if hazir else 'HAZIR DEĞİL'}")
        print("\n".join(satirlar))
        if not a.uygula:
            print(f"  yazılacak: {d['readme']} başına blok + DONDURULDU.md; commit; etiket '{ETIKET}'")
            print("  README bloğu: " + readme_blogu(ad, d, sinama_commit, tarih).strip())
        elif ad in (a.depo or []):
            if not hazir:
                print("  → ATLANDI: ön koşullar sağlanmıyor")
                kod = 1
                continue
            try:
                print(f"  → donduruldu: commit {uygula(ad, d, sinama_commit, tarih)}, etiket {ETIKET}")
            except RuntimeError as e:
                print(f"  → BAŞARISIZ: {e}")
                kod = 1
        print()
    print("Dondurulmayanlar:")
    for ad, neden in DONDURULMAYAN.items():
        print(f"  - {ad}: {neden}")
    return kod


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
