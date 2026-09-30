# -*- coding: utf-8 -*-
"""
hukum.py — Sürümlü, sıralı, deterministik hüküm kuralları (ADR-002 §6).

Girdi dondurulmuş bir KANIT PAKETİDİR; işlev saf: hipotez ya da kanıt yazmaz,
aynı paket + aynı kural sürümü = aynı hüküm. Kategoriler: DESTEKLENDİ,
KIRILGAN, BELİRSİZ, ÇELİŞKİLİ, ÇEKİMSER. Olasılık, yüzde ya da güven puanı
üretilmez (AGENTS kural 6); her hüküm "listelenen rakiplere göre"dir.

Kanıt paketi:
    {soru_turu, amac, kilitli, zincir_saglam,
     birincil: {durum: tutuldu|karşıt|belirsiz|sınanamadı, gerekce},
     rakipler: [{kod, durum, etki, gerekce, sonraki_kanit, olcum?}],
     sinama_surumu?: sınama mantığının sürümü (hükme aynen yansır)
     saglamlik: [uyarı metinleri]}
"""
import hashlib
import json

from . import rak

KURAL_SURUMU = "hukum-v1"
KATEGORILER = ("DESTEKLENDİ", "KIRILGAN", "BELİRSİZ", "ÇELİŞKİLİ", "ÇEKİMSER")
TAVANLI_AMACLAR = ("kesifsel", "operasyonel")
TAVANLI_TURLER = ("SERI",)
_DURUM_GUCU = {"destekleniyor": 3, "çözülmedi": 2, "dışlandı": 1}


def paket_hash(paket):
    """Kanıt paketinin kanonik SHA-256'sı (dondurma taahhüdü)."""
    govde = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()


def en_guclu_rakip(rakipler):
    """Uygulanabilir rakipler içinde en güçlüsü: destekleniyor > çözülmedi >
    dışlandı; eşitlikte etki (yüksek önce), sonra katalog sırası. Hepsi
    dışlandıysa None (listelenen hiçbir rakip ayakta değil)."""
    aday = [r for r in rakipler if r["durum"] in _DURUM_GUCU]
    if not aday:
        return None
    aday.sort(key=lambda r: (-_DURUM_GUCU[r["durum"]], r.get("etki") != "yüksek",
                             rak.SIRA.index(r["kod"]) if r["kod"] in rak.SIRA else len(rak.SIRA)))
    return None if aday[0]["durum"] == "dışlandı" else aday[0]["kod"]


def hukum_ver(paket):
    """Kanıt paketinden kategorik hüküm (saf işlev)."""
    iz = []

    def kural(kod, girdi, sonuc):
        """Tetiklenen kuralı ize ekler (HARP reasoning_trail fikri)."""
        iz.append({"kural": kod, "girdi": girdi, "sonuc": sonuc})

    b = paket["birincil"]["durum"]
    rakipler = paket["rakipler"]
    ayakta = [r for r in rakipler if r["durum"] == "destekleniyor"]
    cozulmemis = [r for r in rakipler if r["durum"] == "çözülmedi"]
    yuksek_destek = [r for r in ayakta if r.get("etki") == "yüksek"]

    if not paket.get("zincir_saglam", False):
        kategori = "ÇEKİMSER"
        kural("K1-zincir", "kanıt zinciri doğrulanamadı", kategori)
    elif b == "sınanamadı":
        kategori = "ÇEKİMSER"
        kural("K1-sinanamadi", "birincil öngörü sınanamadı: " + paket["birincil"].get("gerekce", ""),
              kategori)
    elif b == "karşıt":
        kategori = "ÇELİŞKİLİ"
        kural("K2-karsit", "birincil öngörünün yanlışlama koşulu gerçekleşti", kategori)
    elif b == "belirsiz":
        kategori = "BELİRSİZ"
        kural("K3-belirsiz", "birincil öngörü doğrulanmadı (doğrulanmadı ≠ yanlış)", kategori)
    elif yuksek_destek:
        kategori = "BELİRSİZ"
        kural("K3-rakip", "sınanmış yüksek etkili rakip destekleniyor: "
              + ", ".join(r["kod"] for r in yuksek_destek), kategori)
    elif cozulmemis or ayakta or paket.get("saglamlik"):
        kategori = "KIRILGAN"
        neden = [f"çözülmemiş rakip: {r['kod']}" for r in cozulmemis]
        neden += [f"orta etkili rakip destekleniyor: {r['kod']}" for r in ayakta]
        neden += [f"sağlamlık: {u}" for u in paket.get("saglamlik") or []]
        kural("K4-kirilgan", "; ".join(neden), kategori)
    else:
        kategori = "DESTEKLENDİ"
        kural("K5-destek", "birincil tutuldu; uygulanabilir her rakip dışlandı; sağlamlık temiz",
              kategori)

    if kategori == "DESTEKLENDİ" and not paket.get("kilitli"):
        kategori = "KIRILGAN"
        kural("T1-onkayit", "çalışma kilitli (doğrulayıcı ön-kayıt) değil", kategori)
    if kategori == "DESTEKLENDİ" and paket.get("amac") in TAVANLI_AMACLAR:
        kategori = "KIRILGAN"
        kural("T1-amac", f"{paket.get('amac')} çalışma en çok KIRILGAN", kategori)
    if kategori == "DESTEKLENDİ" and paket["soru_turu"] in TAVANLI_TURLER:
        kategori = "KIRILGAN"
        kural("T2-seri", "SERİ en çok KIRILGAN: desen ≠ fail; kimlik iddiası üretilmez",
              kategori)

    en_guclu = en_guclu_rakip(rakipler)
    sonraki = [{"rakip": r["kod"], "gereken": r.get("sonraki_kanit")}
               for r in sorted(cozulmemis, key=lambda r: (r.get("etki") != "yüksek",
                                                          rak.SIRA.index(r["kod"])
                                                          if r["kod"] in rak.SIRA else 99))]
    ifade = (f"Birincil hipotez, listelenen rakiplere göre {kategori}. "
             + (f"En güçlü rakip: {en_guclu}. " if en_guclu else "Listelenen rakiplerin hepsi dışlandı. ")
             + "Modellenmemiş açıklamalar (H_bilinmeyen) açık kalır. "
             + "Hüküm taslaktır; SONUÇ'a insan onayıyla geçer.")
    return {
        "kategori": kategori,
        "birincil_ongoru": b,
        "en_guclu_rakip": en_guclu,
        "rakipler": [{"kod": r["kod"], "durum": r["durum"], "gerekce": r.get("gerekce"),
                      **({"olcum": r["olcum"]} if r.get("olcum") is not None else {})}
                     for r in rakipler],
        "cozulmemis_rakipler": [r["kod"] for r in cozulmemis],
        "sonraki_en_iyi_kanit": sonraki,
        "saglamlik_uyarilari": list(paket.get("saglamlik") or []),
        "kurallar": iz,
        "ifade": ifade,
        "insan_onayi_gerekir": True,
        "kisi_baglantisi": paket["soru_turu"] in TAVANLI_TURLER,
        "durum": "taslak",
        "kural_surumu": KURAL_SURUMU,
        "sinama_surumu": paket.get("sinama_surumu"),
        "paket_hash": paket_hash(paket),
    }
