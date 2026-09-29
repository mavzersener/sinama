# -*- coding: utf-8 -*-
r"""
surec/kilit.py — protokol kilidi / ön-kayıt (v6.9).

NEDEN VAR: Bir çalışma "doğrulayıcı" (confirmatory) sayılabilmek için
hipotezin VERİYE BAKILMADAN ÖNCE yazıldığının gösterilebilmesi gerekir.
Aksi hâlde bulguya göre hipotez yazılır ve buna literatürde HARKing
(Hypothesizing After the Results are Known) denir; sonuç istatistiksel
olarak geçerli görünse bile çıkarım geçersizdir.

Dış bir ön-kayıt servisine "şimdi kilitledim" demek, yalnız kilit ANINI
kanıtlar — o ana kadar hangi analizlerin yapıldığını kanıtlamaz. Bu modül
farklı bir şey yapar: kilit olayı, analiz adımlarıyla AYNI kanıt zincirine
yazılır. Böylece "kilitten önce bu veriye hiçbir analiz dokunmadı" iddiası
zincirin kendisinden okunabilir hâle gelir — beyan değil, kayıt.

ÜÇ AMAÇ KİPİ (manifesto['amac']):
  operasyonel  — varsayılan. Kilit istenmez; günlük polislik analizi
                 akademik iddia taşımaz. Mevcut davranış aynen korunur.
  dogrulayici  — kilit ZORUNLU ve veri bağlanmadan ÖNCE alınmalıdır.
  kesifsel     — kilit sonradan alınabilir; ürün "keşifsel" etiketi taşır
                 ve doğrulayıcı yorum yapılamaz.

Kilit gövdesi yalnız talep + plan + hipotezdir; veriye ait hiçbir şey
girmez (veri kimliği ayrı alandır, kanit.dosya_kimligi).
"""

import hashlib
import json

from ..cekirdek.hatalar import SucAnaliziHatasi

AMACLAR = ("operasyonel", "dogrulayici", "kesifsel")

# Kilit gövdesine giren manifesto alanları. Sıra önemsizdir (sort_keys),
# ama KÜME sabittir: buraya alan eklemek geçmiş kilitleri geçersizler.
KILIT_ALANLARI = ("talep", "plan")

# Kilitten sonra değişmesi yasak olan alanlar (dogrula bunu sınar).
ANALIZ_OLAYLARI_DISI = {"planla", "protokol_kilitle", "veri_bagla"}


class KilitHatasi(SucAnaliziHatasi):
    """Ön-kayıt ihlali: kilitsiz doğrulayıcı çalışma, çift kilit,
    kilit sonrası protokol değişikliği."""
    tip = "kilit"


def govde(manifesto, hipotez):
    """Kilitlenecek protokol gövdesi (kanonik alt küme).

    Args:
        manifesto: AnalizDongusu manifestosu.
        hipotez: araştırmacının veriye bakmadan yazdığı hipotez metni.

    Returns:
        Kilit hash'inin hesaplanacağı sözlük.
    """
    g = {alan: manifesto.get(alan) for alan in KILIT_ALANLARI}
    g["hipotez"] = hipotez
    return g


def hash_hesapla(g):
    """Kilit gövdesinin kanonik JSON SHA-256'sı.

    Args:
        g: govde() çıktısı.

    Returns:
        64 karakterlik onaltılık özet.
    """
    metin = json.dumps(g, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def kilitle(manifesto, hipotez, onaylayan):
    """Protokolü dondurur ve kilit kaydını üretir.

    Args:
        manifesto: AnalizDongusu manifestosu (PLAN fazında olmalı).
        hipotez: veriye bakılmadan yazılmış hipotez; boş olamaz.
        onaylayan: kilidi alan araştırmacının adı; boş olamaz.

    Returns:
        {'zaman', 'onaylayan', 'hipotez', 'hash'} sözlüğü.

    Raises:
        KilitHatasi: faz uygun değilse, alanlar boşsa veya zaten kilitliyse.
    """
    if manifesto.get("kilit"):
        raise KilitHatasi(
            "protokol zaten kilitli; ön-kayıt tek seferliktir",
            oneri="protokolü değiştirmeniz gerekiyorsa yeni bir oturum açın")
    if manifesto.get("faz") != "PLAN":
        raise KilitHatasi(
            f"kilit yalnız PLAN fazında alınır; mevcut faz: "
            f"{manifesto.get('faz')}",
            oneri="önce planla() çağırın; kilit veriden ÖNCE alınmalıdır")
    if not (hipotez or "").strip():
        raise KilitHatasi(
            "hipotez boş olamaz — ön-kaydın kilitlediği şey hipotezdir",
            oneri="beklediğiniz ilişkiyi bir cümleyle yazın")
    if not (onaylayan or "").strip():
        raise KilitHatasi("kilit için 'onaylayan' zorunludur")

    import time
    g = govde(manifesto, hipotez)
    return {"zaman": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "onaylayan": onaylayan, "hipotez": hipotez,
            "hash": hash_hesapla(g)}


def dogrula(manifesto, olaylar=None):
    """Ön-kayıt bütünlüğünü sınar.

    İki ayrı şey doğrulanır:
      1. BÜTÜNLÜK — protokol kilitten sonra değişmemiş mi (hash yeniden
         hesaplanır ve saklanan hash ile karşılaştırılır).
      2. SIRA — kilit olayı, analiz olaylarının HEPSİNDEN önce mi geliyor.
         Doğrulayıcı iddianın kanıtı budur.

    Args:
        manifesto: AnalizDongusu manifestosu.
        olaylar: kanit.oku() çıktısı (kanıt zinciri). Verilmezse
            manifesto['gecmis'] kullanılır.

    Returns:
        {'kilitli', 'amac', 'butunluk', 'sira_saglam', 'onceki_analiz',
         'dogrulayici_iddia_edilebilir', 'not'} sözlüğü.
    """
    kilit = manifesto.get("kilit")
    amac = manifesto.get("amac", "operasyonel")
    if not kilit:
        return {"kilitli": False, "amac": amac, "butunluk": None,
                "sira_saglam": None, "onceki_analiz": [],
                "dogrulayici_iddia_edilebilir": False,
                "not": "protokol kilitlenmemiş; doğrulayıcı iddia yapılamaz"}

    beklenen = hash_hesapla(govde(manifesto, kilit["hipotez"]))
    butunluk = (beklenen == kilit["hash"])

    adimlar = olaylar if olaylar is not None else manifesto.get("gecmis", [])
    kilit_indeksi = None
    onceki_analiz = []
    for i, a in enumerate(adimlar):
        ad = a.get("arac") or a.get("olay")
        if ad == "protokol_kilitle":
            kilit_indeksi = i
            break
        if ad not in ANALIZ_OLAYLARI_DISI:
            onceki_analiz.append(ad)

    sira_saglam = (kilit_indeksi is not None and not onceki_analiz)
    iddia = bool(butunluk and sira_saglam and amac == "dogrulayici")

    if not butunluk:
        aciklama = ("protokol kilitten SONRA değiştirilmiş; kilit geçersiz")
    elif not sira_saglam:
        aciklama = ("kilitten önce analiz adımı var: "
                    + ", ".join(onceki_analiz) + " — çalışma keşifseldir")
    elif amac != "dogrulayici":
        aciklama = f"kilit sağlam ancak amaç '{amac}'"
    else:
        aciklama = "ön-kayıt sağlam; doğrulayıcı yorum yapılabilir"

    return {"kilitli": True, "amac": amac, "butunluk": butunluk,
            "sira_saglam": sira_saglam, "onceki_analiz": onceki_analiz,
            "dogrulayici_iddia_edilebilir": iddia, "not": aciklama}
