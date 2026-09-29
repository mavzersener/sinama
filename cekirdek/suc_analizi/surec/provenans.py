# -*- coding: utf-8 -*-
r"""
surec/provenans.py — uçtan uca kaynak zinciri ve ONUN BOŞLUKLARI (v6.9).

NEDEN VAR: Bir akademik iddianın arkasındaki zincir tek parça değildir.
Bazı halkalar makineyle KANITLANIR (SHA-256, hash zinciri), bazıları
yalnızca BEYAN edilir (verinin pakete girmeden önce nasıl derlendiği).
Bu ikisini aynı görsel dille sunmak, kanıtlanmamış olanı kanıtlanmış
göstermektir.

Bu modül zinciri kurmaz — zaten kurulmuş halkaları TOPLAR ve her birinin
kanıt türünü açıkça etiketler. Eksik halkayı da açıkça söyler.

BEŞ HALKA:
  1. HAZIRLIK    Ham kaynaklardan analiz dosyasına (birleştirme, geokodlama,
                 filtreleme). Bu paket dışında olur → İNSAN BEYANI.
  2. VERİ        Analize giren dosyanın SHA-256'sı → MAKİNE.
  3. ÖN-KAYIT    Protokol kilidi + kilitten önce analiz yapılmadığı → MAKİNE.
  4. ANALİZ      Olay akışının hash zinciri (kanit.dogrula) → MAKİNE.
  5. AKADEMİK    Dış sistemin (ör. Science GPT) denetim doğrulaması → MAKİNE,
                 ancak o sistem tarafından üretilir; burada yalnız BAĞLANIR.

DÜRÜSTLÜK KURALI: 1. halka hiçbir zaman "doğrulandı" diye gösterilmez.
Araştırmacı beyanı da bir kayıttır, ama farklı türden bir kayıttır.
"""

import time

from ..cekirdek.hatalar import KullanimHatasi
from . import kanit, kilit

# Kanıt türleri — görsel/anlamsal ayrım bu etiketten türer.
MAKINE = "makine"   # hash/zincir ile sınanabilir
BEYAN = "beyan"     # insan beyanı; doğrulanamaz, ama kayıt altındadır
EKSIK = "eksik"     # halka hiç kurulmamış

HALKALAR = ("hazirlik", "veri", "onkayit", "analiz", "akademik")


def _simdi():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def hazirlik_beyani(manifesto, adimlar, beyan_eden):
    """Verinin pakete girmeden önceki hazırlığını BEYAN olarak kaydeder.

    Bu adımlar (kaynak birleştirme, geokodlama, filtreleme) paketin
    dışında yapılır; hiçbir hash bunları kapsamaz. Otomatik provenans
    taklidi yapmak yerine beyan olarak, beyan edenin adıyla saklanır.

    Args:
        manifesto: AnalizDongusu manifestosu.
        adimlar: [{'islem': ..., 'aciklama': ..., 'kaynak': ...}] listesi.
        beyan_eden: beyanın sorumlusu.

    Returns:
        Kaydedilen beyan sözlüğü.

    Raises:
        KullanimHatasi: adım listesi boşsa veya zorunlu alan eksikse.
    """
    if not adimlar:
        raise KullanimHatasi(
            "hazırlık beyanı boş olamaz",
            oneri="veriyi nasıl derlediğinizi en az bir adımla yazın; "
                  "hiç işlem yapılmadıysa 'ham veri değiştirilmedi' deyin")
    if not (beyan_eden or "").strip():
        raise KullanimHatasi("beyan_eden zorunludur")

    temiz = []
    for i, adim in enumerate(adimlar, start=1):
        islem = (adim.get("islem") or "").strip()
        if not islem:
            raise KullanimHatasi(f"{i}. adımda 'islem' alanı boş")
        temiz.append({"islem": islem,
                      "aciklama": (adim.get("aciklama") or "").strip(),
                      "kaynak": (adim.get("kaynak") or "").strip()})

    beyan = {"zaman": _simdi(), "beyan_eden": beyan_eden,
             "adimlar": temiz, "kanit_turu": BEYAN,
             "not": "Bu adımlar paket dışında yapılmıştır; hiçbir hash "
                    "bunları kapsamaz."}
    manifesto["hazirlik_beyani"] = beyan
    return beyan


def dis_denetim_kaydet(manifesto, sistem, kimlik, dogrulama):
    """Dış sistemin denetim doğrulamasını yerli manifestoya bağlar.

    Science GPT'nin `GET /api/research/{id}/audit/verify` çıktısı buraya
    yazılır; böylece akademik çıktının denetim durumu, analizin yapıldığı
    oturumdan da okunabilir. İki zincir uçlarından bağlanır.

    Args:
        manifesto: AnalizDongusu manifestosu.
        sistem: dış sistemin adı (ör. 'science_gpt').
        kimlik: dış sistemdeki araştırma kimliği.
        dogrulama: {'valid': bool, 'event_count': int, 'last_hash': str|None}.

    Returns:
        Kaydedilen bağ sözlüğü.

    Raises:
        KullanimHatasi: sistem/kimlik boşsa veya doğrulama 'valid' taşımıyorsa.
    """
    if not (sistem or "").strip() or not (kimlik or "").strip():
        raise KullanimHatasi("sistem ve kimlik zorunludur")
    if "valid" not in (dogrulama or {}):
        raise KullanimHatasi(
            "doğrulama çıktısı 'valid' alanı taşımalıdır",
            oneri="dış sistemin audit/verify yanıtını olduğu gibi geçirin")

    bag = {"zaman": _simdi(), "sistem": sistem, "kimlik": kimlik,
           "valid": bool(dogrulama.get("valid")),
           "olay_sayisi": dogrulama.get("event_count"),
           "son_hash": dogrulama.get("last_hash"),
           "kanit_turu": MAKINE}
    manifesto.setdefault("dis_denetimler", []).append(bag)
    return bag


def _halka(ad, kurulu, kanit_turu, ozet, ayrinti=None):
    """Tek bir zincir halkasının standart görünümü."""
    return {"halka": ad, "kurulu": kurulu, "kanit_turu": kanit_turu,
            "ozet": ozet, "ayrinti": ayrinti or {}}


def zincir_ozeti(manifesto, log_dir=None):
    """Uçtan uca provenans görünümü; kanıtlanan ile beyan edileni ayırır.

    Args:
        manifesto: AnalizDongusu manifestosu.
        log_dir: kanıt zinciri kökü; verilirse hash zinciri fiilen sınanır.

    Returns:
        {'halkalar': [...], 'kopukluklar': [...], 'tam_makine_zinciri': bool,
         'not': ...} sözlüğü.
    """
    halkalar = []

    # 1) HAZIRLIK — her zaman beyan; asla "doğrulandı" denmez.
    hz = manifesto.get("hazirlik_beyani")
    halkalar.append(_halka(
        "hazirlik", bool(hz), BEYAN if hz else EKSIK,
        (f"{len(hz['adimlar'])} adım beyan edildi ({hz['beyan_eden']})"
         if hz else "veri hazırlığı beyan edilmemiş"),
        {"adimlar": hz["adimlar"]} if hz else None))

    # 2) VERİ — dosya kimliği.
    vk = manifesto.get("veri_kimligi")
    halkalar.append(_halka(
        "veri", bool(vk), MAKINE if vk else EKSIK,
        (f"{vk['dosya_adi']} · SHA-256 {vk['sha256'][:12]}…"
         if vk else "analiz dosyasının kimliği alınmamış"),
        vk))

    # 3) ÖN-KAYIT — kilit bütünlüğü ve sırası.
    ok = kilit.dogrula(manifesto)
    halkalar.append(_halka(
        "onkayit", bool(ok["kilitli"]), MAKINE if ok["kilitli"] else EKSIK,
        ok["not"], ok))

    # 4) ANALİZ — olay akışı hash zinciri.
    if log_dir:
        zincir = kanit.dogrula(log_dir, manifesto.get("oturum_id"))
        halkalar.append(_halka(
            "analiz", zincir["olay_sayisi"] > 0, MAKINE,
            (f"{zincir['olay_sayisi']} olay, zincir "
             + ("sağlam" if zincir["saglam"] else "BOZUK")),
            zincir))
    else:
        adim = len(manifesto.get("gecmis", []))
        halkalar.append(_halka(
            "analiz", adim > 0, MAKINE if adim else EKSIK,
            f"{adim} adım (zincir sınanmadı; log_dir verilmedi)"))

    # 5) AKADEMİK — dış sistemin denetimi.
    dis = manifesto.get("dis_denetimler") or []
    gecerli = [d for d in dis if d.get("valid")]
    halkalar.append(_halka(
        "akademik", bool(dis), MAKINE if dis else EKSIK,
        (f"{len(dis)} dış denetim bağlı, {len(gecerli)} geçerli"
         if dis else "akademik çıktı bağlanmamış"),
        {"denetimler": dis}))

    kopukluklar = []
    for h in halkalar:
        if h["kanit_turu"] == EKSIK:
            kopukluklar.append(f"{h['halka']}: {h['ozet']}")
    if hz:
        kopukluklar.append(
            "hazirlik: beyan makineyle doğrulanamaz — zincirin bu halkası "
            "araştırmacı sorumluluğundadır")

    makine_halkalari = [h for h in halkalar if h["halka"] != "hazirlik"]
    tam = all(h["kanit_turu"] == MAKINE for h in makine_halkalari)

    return {"halkalar": halkalar, "kopukluklar": kopukluklar,
            "tam_makine_zinciri": tam,
            "not": ("Hazırlık halkası dışındaki tüm halkalar makineyle "
                    "sınanabilir." if tam else
                    "Zincirde eksik halka var; kopukluklar listesine bakın.")}
