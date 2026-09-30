# -*- coding: utf-8 -*-
r"""
surec/makale.py — akademik anlatının deterministik dayanağı (v6.9).

MİMARİ İLKE: LLM bu pakete GİRMEZ. Paket iki şey yapar —

  olgu_listesi(manifesto)  Oturumdan kimliklendirilmiş OLGULAR üretir
                           (F=bulgu, M=yöntem, L=sınırlılık). Bunlar
                           anlatının tek meşru dayanağıdır.
  anlati_dogrula(...)      Dışarıda (ajan/model) yazılmış anlatının bu
                           olgulara bağlı olduğunu SINAR.

Anlatıyı kim yazarsa yazsın doğrulayıcı aynıdır; model değiştiğinde
akademik güvence değişmez. Doktrin (sıfır bağımlılık, LLM'siz çekirdek)
korunur.

İKİ KURAL:
  1. RAKAM YASAĞI — anlatı cümlesi sayı taşıyamaz. Sayılar yalnız
     deterministik katmandan (olgu ifadelerinden) gelir. Model "%37 artış"
     yazamaz; "[F003]" diyerek olguya işaret eder. Sözel nicelikler de
     (yüzde, iki katı, üçte biri…) sayı sayılır — rakam filtresini
     kelimeyle atlatmak mümkün olmasın.
  2. DAYANAK ZORUNLULUĞU — her paragraf en az bir olgu kimliğine
     atıf yapmalı; atıfsız paragraf "yorum" değil, dayanaksız iddiadır.

SINIRLILIKLARIN KAYNAĞI: L olguları uydurulmaz — fitness gate'in
sebepleri, veri kalitesi uyarıları ve amaç kipinden TÜRETİLİR. Böylece
"sınırlılıklar" bölümü kozmetik bir paragraf olmaktan çıkar.
"""

import re

from ..cekirdek.hatalar import KullanimHatasi
from . import kilit as kilit_mod

# Anlatıda olguya atıf biçimi: [F001] veya [F001, M002]
ATIF_DESENI = re.compile(r"\[([A-Z]\d{3}(?:\s*,\s*[A-Z]\d{3})*)\]")
KIMLIK_DESENI = re.compile(r"[A-Z]\d{3}")

# Rakamı kelimeyle taşıyan nicelik ifadeleri (rakam yasağının kaçağı).
SOZEL_NICELIK = (
    "yüzde", "yarısı", "yarısına", "çeyreği", "üçte", "dörtte", "beşte",
    "katı", "katına", "kat arttı", "kat azaldı", "iki kat", "üç kat",
    "misli", "yüzdelik",
)

# Manifesto geçmişinde ANALİZ bulgusu SAYILMAYAN adımlar.
BULGU_DISI = {"planla", "protokol_kilitle", "veri_bagla", "analize_gec",
              "sonucla", "izleme_plani"}


def _ekle(olgular, on_ek, sayac, tur, ifade, kaynak):
    """Olgu listesine kimliklendirilmiş tek kayıt ekler.

    Args:
        olgular: eklenecek liste (yerinde değiştirilir).
        on_ek: kimlik ön eki (F/M/L).
        sayac: bu ön ek için sıradaki numara.
        tur: olgu türü adı.
        ifade: olgunun metni.
        kaynak: olgunun manifestodaki kaynağı.

    Returns:
        Bir sonraki sayaç değeri.
    """
    olgular.append({"kimlik": f"{on_ek}{sayac:03d}", "tur": tur,
                    "ifade": ifade, "kaynak": kaynak})
    return sayac + 1


def olgu_listesi(manifesto):
    """Oturumdan akademik anlatının dayanacağı olguları üretir.

    Args:
        manifesto: AnalizDongusu manifestosu.

    Returns:
        [{'kimlik', 'tur', 'ifade', 'kaynak'}] listesi.
        F=bulgu, M=yöntem, L=sınırlılık.
    """
    olgular = []

    # --- F: bulgular (ANALİZ fazı adımlarının özetleri) ---
    f = 1
    for adim in manifesto.get("gecmis", []):
        if adim.get("faz") != "ANALIZ":
            continue
        arac = adim.get("arac")
        if arac in BULGU_DISI:
            continue
        f = _ekle(olgular, "F", f, "bulgu",
                  f"{arac}: {adim.get('ozet')}", "gecmis")

    # --- M: yöntem ---
    m = 1
    plan = manifesto.get("plan") or {}
    if plan.get("urun_turu"):
        m = _ekle(olgular, "M", m, "yontem",
                  f"Ürün türü: {plan['urun_turu']}; hedef kitle: "
                  f"{plan.get('hedef_kitle', 'belirtilmedi')}.", "plan")
    kimlik = manifesto.get("veri_kimligi")
    if kimlik:
        m = _ekle(olgular, "M", m, "yontem",
                  f"Veri dosyası {kimlik['dosya_adi']}; SHA-256 "
                  f"{kimlik['sha256']}; {kimlik['boyut']} bayt.",
                  "veri_kimligi")
    kilit = manifesto.get("kilit")
    if kilit:
        m = _ekle(olgular, "M", m, "yontem",
                  f"Protokol {kilit['zaman']} tarihinde {kilit['onaylayan']} "
                  f"tarafından kilitlendi; kilit özeti {kilit['hash']}.",
                  "kilit")
    profil = manifesto.get("veri_kalitesi") or {}
    if profil.get("n") is not None:
        m = _ekle(olgular, "M", m, "yontem",
                  f"Analiz edilen kayıt sayısı: {profil['n']}.",
                  "veri_kalitesi")

    # --- L: sınırlılıklar (TÜRETİLİR, uydurulmaz) ---
    lim, gorulen = 1, set()
    for karar in manifesto.get("gate_kararlari", []):
        for sebep in karar.get("sebepler", []):
            if sebep not in gorulen:
                gorulen.add(sebep)
                lim = _ekle(olgular, "L", lim, "sinirlilik",
                            sebep, "gate_kararlari")
    for uyari in profil.get("uyarilar", []) or []:
        if uyari not in gorulen:
            gorulen.add(uyari)
            lim = _ekle(olgular, "L", lim, "sinirlilik",
                        uyari, "veri_kalitesi")

    amac = manifesto.get("amac", "operasyonel")
    # kilidin VARLIĞI değil geçerliliği (bütünlük + sıra) doğrulayıcı yorumu açar
    if not kilit_mod.dogrula(manifesto)["dogrulayici_iddia_edilebilir"]:
        lim = _ekle(
            olgular, "L", lim, "sinirlilik",
            "Çalışma keşifseldir; hipotez veriden önce kilitlenmediği için "
            "doğrulayıcı yorum yapılamaz.", "amac")

    return olgular


def _rakam_ihlali(metin):
    """Cümlede sayı taşıyan ifade var mı (rakam veya sözel nicelik).

    Args:
        metin: sınanacak paragraf metni (atıflar çıkarılmış olmalı).

    Returns:
        İhlal açıklaması (str) veya None.
    """
    if re.search(r"\d", metin):
        return "rakam içeriyor"
    dusuk = metin.lower()
    for kelime in SOZEL_NICELIK:
        if kelime in dusuk:
            return f"sözel nicelik içeriyor: '{kelime}'"
    return None


def anlati_dogrula(metin, olgular):
    """Anlatının olgulara dayandığını ve sayı taşımadığını sınar.

    Paragraflar boş satırla ayrılır. Her paragraf en az bir olgu
    kimliğine atıf yapmalı ([F001] biçiminde) ve atıflar dışında sayı
    içermemelidir.

    Args:
        metin: doğrulanacak anlatı (dışarıda üretilmiş).
        olgular: olgu_listesi() çıktısı.

    Returns:
        {'gecerli': bool, 'paragraf_sayisi': int, 'ihlaller': [...]}.

    Raises:
        KullanimHatasi: olgu listesi boşsa (doğrulanacak dayanak yok).
    """
    if not olgular:
        raise KullanimHatasi(
            "olgu listesi boş; dayanaksız anlatı doğrulanamaz",
            oneri="önce olgu_listesi(manifesto) ile olguları üretin")

    gecerli_kimlikler = {o["kimlik"] for o in olgular}
    paragraflar = [p.strip() for p in re.split(r"\n\s*\n", metin or "")
                   if p.strip()]
    ihlaller = []

    for i, p in enumerate(paragraflar, start=1):
        atifli = ATIF_DESENI.findall(p)
        kimlikler = set()
        for grup in atifli:
            kimlikler.update(KIMLIK_DESENI.findall(grup))

        if not kimlikler:
            ihlaller.append({"paragraf": i, "tur": "dayanaksiz",
                             "aciklama": "hiçbir olgu kimliğine atıf yok"})

        bilinmeyen = sorted(kimlikler - gecerli_kimlikler)
        if bilinmeyen:
            ihlaller.append({"paragraf": i, "tur": "bilinmeyen_kimlik",
                             "aciklama": "olgu listesinde yok: "
                                         + ", ".join(bilinmeyen)})

        # Atıflar metinden çıkarılır; kimliklerdeki rakamlar sayılmasın.
        atifsiz = ATIF_DESENI.sub("", p)
        sorun = _rakam_ihlali(atifsiz)
        if sorun:
            ihlaller.append({"paragraf": i, "tur": "rakam",
                             "aciklama": sorun + "; sayılar yalnız olgu "
                                                 "ifadelerinden gelmelidir"})

    if not paragraflar:
        ihlaller.append({"paragraf": 0, "tur": "bos",
                         "aciklama": "anlatı boş"})

    return {"gecerli": not ihlaller, "paragraf_sayisi": len(paragraflar),
            "ihlaller": ihlaller}
