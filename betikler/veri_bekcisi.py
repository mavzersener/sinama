# -*- coding: utf-8 -*-
r"""
veri_bekcisi.py — özel veri ve sır depoya GİREMEZ (ADR-001 md.5).

Birinci savunma hattı .gitignore değil bu betiktir: .gitignore yalnız
izlenmeyen dosyayı gizler; `git add -f` ya da gözden kaçan bir desen onu
aşar. Bekçi depoya girecek İÇERİĞİ (index'teki ya da itilecek commit'lerdeki
blob'u) denetler; çalışma ağacına bakmaz.

Kipler:
  --staged          pre-commit: index'e alınmış (eklenen/değişen) dosyalar.
  --push UZAK URL   pre-push: stdin'deki ref satırlarından itilecek TÜM
                    commit'ler — ara bir commit'te eklenip sonra silinen sır
                    da yakalanır. Yerel yol URL'li uzaklar (D: yedeği)
                    atlanır: kural "GitHub'a özel veri gitmez"dir; yerel
                    yedeği engellemek iş kaybettirir.
  --gecmis          elle denetim: tüm geçmişteki her commit.

Kurallar:
  1. Anahtar/sır dosyası her yerde yasak (.pem, .key, .env ...;
     .env.ornek gibi şablonlar serbest).
  2. Veri ve belge dosyaları yalnız bir `sentetik/` dizini altında serbest.
  3. Oturum/yükleme/log dizinleri (oturumlar/, uploads/, loglar/ ...) yasak.
  4. BOYUT_SINIRI üstü dosya yasak (veri dökümü belirtisi).
  5. İçerik — özel anahtar bloğu, bilinen token biçimleri, parolalı
     bağlantı adresi, sır ortam değişkeni ataması: HER ZAMAN yasak.
  6. İçerik — TC kimlik no (sağlama toplamı geçerli), Türk cep telefonu,
     e-posta: kişisel veri şüphesi; satırda `bekci:izin` varsa atlanır.

İzin listesi (betikler/bekci_izinleri.txt): tam yol eşleşmesi 1-4'ü atlar,
5'i ASLA atlamaz. Her satır gerekçe taşımak zorundadır.

Çıkış kodu: 0 temiz, 1 ihlal, 2 kullanım/ortam hatası. Raporda bulunan
değer maskelenir — rapor da bir sızıntı kanalı olmamalı.
"""

import argparse
import os
import re
import subprocess
import sys

BOYUT_SINIRI = 2 * 1024 * 1024
ICERIK_TARAMA_SINIRI = 20 * 1024 * 1024
SIFIR = "0" * 40
SENTETIK = "sentetik"
IZIN_DOSYASI = "betikler/bekci_izinleri.txt"

ANAHTAR_UZANTILARI = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".kdbx", ".ppk"})
ANAHTAR_ADLARI = frozenset({
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "auth.json"})
ENV_SABLONLARI = frozenset({".env.ornek", ".env.example", ".env.sample"})
VERI_UZANTILARI = frozenset({
    ".csv", ".tsv", ".xlsx", ".xls", ".xlsm", ".ods", ".jsonl", ".ndjson",
    ".parquet", ".feather", ".db", ".sqlite", ".sqlite3", ".geojson",
    ".shp", ".shx", ".dbf", ".gpkg", ".kml", ".kmz", ".mbtiles", ".sav",
    ".dta", ".rds", ".rdata", ".h5", ".hdf5", ".pkl", ".pickle", ".npy",
    ".npz"})
BELGE_UZANTILARI = frozenset({
    ".docx", ".doc", ".pptx", ".ppt", ".pdf", ".odt", ".rtf", ".msg",
    ".eml", ".mhtml", ".mht"})
YASAK_DIZINLER = frozenset({
    "oturumlar", "uploads", "loglar", "llm_runs", "dis_kanit"})

# --- Kural 5: her zaman yasak içerik ---
ANAHTAR_BLOGU = re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----")
TOKENLAR = (
    ("GitHub token", re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("Anthropic anahtarı", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI anahtarı", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}")),
    ("AWS erişim anahtarı", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("Google API anahtarı", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
)
# Ad sır çağrıştırır VE değer gerçek bir sır gibi görünür (≥16 karakter,
# ≥2 rakam). Rakam şartı `X_SECRET = ayarlar.gizli_deger` gibi kod
# atamalarını dışarıda bırakır; gerçek token/hash neredeyse hep rakam taşır.
SIR_ATAMA = re.compile(
    r"\b([A-Za-z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|PAROLA|SIFRE|API_?KEY|"
    r"PRIVATE_KEY|AUTH_KEY)[A-Za-z0-9_]*)\s*[:=]\s*['\"]?"
    r"([A-Za-z0-9_\-.+/=]{16,})", re.IGNORECASE)
PAROLALI_URL = re.compile(
    r"\b(?:mysql|mariadb|postgres(?:ql)?|mongodb(?:\+srv)?|redis|amqp)"
    r"(?:\+\w+)?://([^:/\s@]+):([^@/\s]+)@")
YER_TUTUCU = re.compile(
    r"^(?:<[^>]*>|\*+|\$\{[^}]*\}|x+|parola|password|pass|sifre|şifre|"
    r"secret|changeme)$", re.IGNORECASE)

# --- Kural 6: kişisel veri şüphesi (bekci:izin ile atlanabilir) ---
IZIN_ISARETI = "bekci:izin"
TC_ADAY = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
CEP = re.compile(
    r"(?<![\d+])(?:\+90[\s\-]?|0)?5\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)")
EPOSTA = re.compile(
    r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@(?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,}")
SERBEST_EPOSTA_ALANLARI = frozenset({
    "example.com", "example.org", "example.net", "localhost"})
SERBEST_EPOSTALAR = frozenset({"noreply@anthropic.com"})


class BekciHatasi(Exception):
    """Bekçi çalışamadı (git hatası, bozuk izin dosyası) — ihlal değil."""


# ---------------------------------------------------------------- saf kurallar

def _env_mi(ad):
    """Dosya adı bir ortam/sır dosyası mı (.env, .env.x, x.env; şablon hariç)."""
    if ad in ENV_SABLONLARI:
        return False
    return ad == ".env" or ad.startswith(".env.") or ad.endswith(".env")


def yol_denetle(yol, boyut, izinli=frozenset()):
    """Kural 1-4: yol, uzantı, dizin ve boyut denetimi.

    Args:
        yol: depo köküne göre POSIX yol.
        boyut: bayt cinsinden blob boyutu (bilinmiyorsa None).
        izinli: izin listesindeki tam yollar (kural 1-4'ü atlar).

    Returns:
        İhlal açıklamaları listesi (boşsa temiz).
    """
    if yol in izinli:
        return []
    parcalar = yol.split("/")
    ad = parcalar[-1].lower()
    uzanti = os.path.splitext(ad)[1]
    dizinler = [p.lower() for p in parcalar[:-1]]
    sentetik = SENTETIK in dizinler
    ihlaller = []
    if uzanti in ANAHTAR_UZANTILARI or ad in ANAHTAR_ADLARI or _env_mi(ad):
        ihlaller.append("anahtar/sır dosyası depoya giremez")
    if uzanti in VERI_UZANTILARI and not sentetik:
        ihlaller.append("veri dosyası yalnız bir 'sentetik/' dizininde olabilir")
    if uzanti in BELGE_UZANTILARI and not sentetik:
        ihlaller.append("belge dosyası (docx/pdf ...) yalnız 'sentetik/' altında olabilir")
    yasak = sorted(YASAK_DIZINLER.intersection(dizinler))
    if yasak:
        ihlaller.append(f"yasak dizin '{yasak[0]}/' (oturum/yükleme/log verisi)")
    if boyut is not None and boyut > BOYUT_SINIRI:
        ihlaller.append(f"{boyut // 1024} KB > {BOYUT_SINIRI // 1024} KB sınırı "
                        "(veri dökümü belirtisi)")
    return ihlaller


def tc_gecerli(s):
    """11 haneli dizge TC kimlik no sağlama toplamını geçiyor mu."""
    if len(s) != 11 or not s.isdigit() or s[0] == "0":
        return False
    d = [int(c) for c in s]
    if (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10 != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


def eposta_serbest(adres):
    """Örnek/test alan adları ve bilinen kamu adresleri kişisel veri sayılmaz."""
    yerel, _, alan = adres.lower().rpartition("@")
    if yerel == "git" or adres.lower() in SERBEST_EPOSTALAR:
        return True
    return (alan in SERBEST_EPOSTA_ALANLARI
            or alan.endswith((".example", ".test", ".invalid",
                              "users.noreply.github.com")))


def maskele(deger):
    """Bulunan değerin yalnız ilk 4 karakterini ve uzunluğunu gösterir."""
    return f"{deger[:4]}… ({len(deger)} karakter)"


def icerik_denetle(veri):
    """Kural 5-6: metin içeriğini satır satır denetler.

    NUL bayt içeren (ikili) içerik taranmaz; boyut kuralı ayrıca geçerlidir.

    Args:
        veri: blob baytları.

    Returns:
        [(satir_no, kural, maskeli_deger)] listesi.
    """
    if b"\x00" in veri[:8000]:
        return []
    metin = veri.decode("utf-8", "replace")
    bulgular = []
    for no, satir in enumerate(metin.splitlines(), 1):
        if ANAHTAR_BLOGU.search(satir):
            bulgular.append((no, "özel anahtar bloğu", "BEGIN … PRIVATE KEY"))
        for ad, desen in TOKENLAR:
            m = desen.search(satir)
            if m:
                bulgular.append((no, ad, maskele(m.group(0))))
                break
        m = SIR_ATAMA.search(satir)
        if m and sum(c.isdigit() for c in m.group(2)) >= 2:
            bulgular.append((no, f"sır ataması ({m.group(1)})", maskele(m.group(2))))
        for m in PAROLALI_URL.finditer(satir):
            if not YER_TUTUCU.match(m.group(2)):
                bulgular.append((no, "parolalı bağlantı adresi", maskele(m.group(0))))
        if IZIN_ISARETI in satir:
            continue
        for m in TC_ADAY.finditer(satir):
            if tc_gecerli(m.group(0)):
                bulgular.append((no, "TC kimlik no (sağlama geçerli)", maskele(m.group(0))))
        for m in CEP.finditer(satir):
            bulgular.append((no, "cep telefonu", maskele(m.group(0))))
        for m in EPOSTA.finditer(satir):
            if not eposta_serbest(m.group(0)):
                bulgular.append((no, "e-posta adresi", maskele(m.group(0))))
    return bulgular


def yerel_url_mi(url):
    """Uzak adres yerel bir yol mu (D: yedeği gibi) — ağ uzağı değil."""
    return bool(re.match(r"^[A-Za-z]:[\\/]", url)
                or url.startswith(("/", "file://", "\\\\")))


# ---------------------------------------------------------------- git katmanı

def _git(kok, *arg):
    s = subprocess.run(["git", "-C", kok, *arg], capture_output=True)
    if s.returncode != 0:
        raise BekciHatasi(f"git {' '.join(arg)}: "
                          f"{s.stderr.decode('utf-8', 'replace').strip()}")
    return s.stdout


def _yollar(cikti):
    return [p.decode("utf-8") for p in cikti.split(b"\0") if p]


def izinleri_oku(kok):
    """İzin listesini okur; gerekçesiz satır BekciHatasi'dır."""
    yol = os.path.join(kok, IZIN_DOSYASI)
    if not os.path.exists(yol):
        return frozenset()
    izinli = set()
    with open(yol, encoding="utf-8") as f:
        for no, satir in enumerate(f, 1):
            ham = satir.strip()
            if not ham or ham.startswith("#"):
                continue
            dosya, ayrac, gerekce = ham.partition("#")
            if not ayrac or not gerekce.strip():
                raise BekciHatasi(f"{IZIN_DOSYASI}:{no}: gerekçesiz izin "
                                  "('<yol>  # gerekçe' biçiminde yazın)")
            izinli.add(dosya.strip())
    return frozenset(izinli)


def _blob_denetle(kok, konum, yol, blob_ref, izinli):
    boyut = int(_git(kok, "cat-file", "-s", blob_ref).strip())
    ihlaller = [(konum, None, k) for k in yol_denetle(yol, boyut, izinli)]
    if boyut <= ICERIK_TARAMA_SINIRI:
        veri = _git(kok, "cat-file", "blob", blob_ref)
        ihlaller += [(konum, no, f"{kural}: {deger}")
                     for no, kural, deger in icerik_denetle(veri)]
    return ihlaller


def staged_denetle(kok, izinli=frozenset()):
    """Index'teki eklenen/değişen dosyaları denetler (pre-commit)."""
    yollar = _yollar(_git(kok, "diff", "--cached", "--name-only", "-z",
                          "--diff-filter=ACMR"))
    ihlaller = []
    for yol in yollar:
        ihlaller += _blob_denetle(kok, yol, yol, ":" + yol, izinli)
    return ihlaller


def commitler_denetle(kok, commitler, izinli=frozenset()):
    """Her commit'in ilk ebeveynine göre eklediği/değiştirdiği dosyaları denetler.

    Aynı blob bir kez taranır; kök commit'te ağacın tamamı taranır.
    """
    gorulen = set()
    ihlaller = []
    for c in commitler:
        ebeveynler = _git(kok, "rev-list", "--parents", "-n1", c).split()[1:]
        if ebeveynler:
            cikti = _git(kok, "diff-tree", "-r", "-z", "--name-only",
                         "--diff-filter=ACMR", ebeveynler[0].decode(), c)
        else:
            cikti = _git(kok, "ls-tree", "-r", "-z", "--name-only", c)
        for yol in _yollar(cikti):
            blob = _git(kok, "rev-parse", f"{c}:{yol}").strip().decode()
            if blob in gorulen:
                continue
            gorulen.add(blob)
            ihlaller += _blob_denetle(kok, f"{c[:7]}:{yol}", yol, blob, izinli)
    return ihlaller


def push_denetle(kok, uzak, ref_satirlari, izinli=frozenset()):
    """pre-push stdin satırlarından itilecek commit'leri bulup denetler."""
    commitler = []
    for satir in ref_satirlari:
        p = satir.split()
        if len(p) != 4 or p[1] == SIFIR:
            continue  # biçimsiz satır ya da dal silme
        yerel_sha, uzak_sha = p[1], p[3]
        bilinen = uzak_sha != SIFIR and subprocess.run(
            ["git", "-C", kok, "cat-file", "-e", uzak_sha + "^{commit}"],
            capture_output=True).returncode == 0
        aralik = ([f"{uzak_sha}..{yerel_sha}"] if bilinen
                  else [yerel_sha, "--not", f"--remotes={uzak}"])
        for c in _git(kok, "rev-list", *aralik).decode().split():
            if c not in commitler:
                commitler.append(c)
    return commitler_denetle(kok, commitler, izinli)


def rapor(ihlaller, akis=sys.stderr):
    """İhlalleri okunur biçimde yazar; çıkış kodunu döndürür."""
    if not ihlaller:
        return 0
    print(f"[bekçi] REDDEDİLDİ — {len(ihlaller)} ihlal "
          "(özel veri/sır depoya giremez, ADR-001 md.5)", file=akis)
    for konum, satir, aciklama in ihlaller:
        yer = f"{konum}:{satir}" if satir else konum
        print(f"  {yer}: {aciklama}", file=akis)
    print("Çözüm: dosyayı depodan çıkarın (git rm --cached <yol>) ve veri kökünde "
          "tutun. Kişisel veri kuralında yanlış pozitifse satıra 'bekci:izin' "
          f"yazın; yol kuralında gerekçeli satırı {IZIN_DOSYASI}'e ekleyin. "
          "Sır kuralları hiçbir yolla atlanamaz.", file=akis)
    return 1


def main(argv=None):
    """Komut satırı girişi (kancalar bunu çağırır)."""
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Özel veri ve sır bekçisi (ADR-001 md.5)")
    kip = ap.add_mutually_exclusive_group(required=True)
    kip.add_argument("--staged", action="store_true", help="index'i denetle (pre-commit)")
    kip.add_argument("--push", nargs=2, metavar=("UZAK", "URL"),
                     help="itilecek commit'leri denetle (pre-push; ref satırları stdin'den)")
    kip.add_argument("--gecmis", action="store_true", help="tüm geçmişi denetle")
    ap.add_argument("--kok", help="depo kökü (varsayılan: bulunduğun depo)")
    a = ap.parse_args(argv)
    try:
        kok = a.kok or _git(os.getcwd(), "rev-parse", "--show-toplevel").decode().strip()
        izinli = izinleri_oku(kok)
        if a.staged:
            ihlaller = staged_denetle(kok, izinli)
        elif a.push:
            uzak, url = a.push
            if yerel_url_mi(url):
                return 0  # yerel yedek: kural GitHub içindir
            ihlaller = push_denetle(kok, uzak, sys.stdin.read().splitlines(), izinli)
        else:
            tumu = _git(kok, "rev-list", "--all").decode().split()
            ihlaller = commitler_denetle(kok, tumu, izinli)
    except BekciHatasi as e:
        print(f"[bekçi] HATA: {e}", file=sys.stderr)
        return 2
    return rapor(ihlaller)


if __name__ == "__main__":
    sys.exit(main())
